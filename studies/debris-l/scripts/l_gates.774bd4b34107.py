# l_gates.py - cft-debris (DEBRIS-L): the gates V0 to V4 of the visual presentation parcel, each with its control, and the manifest.
# cft-debris, MIT licence (see LICENSE at the repository root). Written by DEBRIS-L, 2026-11-23.
#
#   python -I -B l_gates.py <stage> --ledger DIR --scratch DIR --logs DIR --keep DIR --cpu TSV [--m1f EXE --downloads DIR --ffmpeg EXE]
# stages: v0 (PNG writer), v1 (positions), v2 (propagation), v3 (numbers and charts), v4 (repository scan; --trial for the trial run),
# manifest (writes studies/debris-l/MANIFEST.sha256 and checks it). Each gate writes a numbered log in --logs (aggregates, counts and
# no per-object data, tool paths as placeholders) and, with the same number, a detail log in the ledger's debris-l/logs/.
# The criteria are fixed in the CRIT_* strings below, before any data; the code asserts them.
import argparse
import base64
import collections
import csv
import hashlib
import io
import math
import os
import random
import re
import struct
import subprocess
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import k_lib as K  # noqa: E402
import k_pilot as KP  # noqa: E402
import l_draw as D  # noqa: E402
import l_lib as L  # noqa: E402
import l_panel as P  # noqa: E402
import l_png  # noqa: E402

SCRIPT = os.path.abspath(__file__)
REPO = L.HERE_REPO
MODS = [os.path.join(L.TESTS, f) for f in ("l_lib.py", "l_png.py", "l_draw.py", "l_font.py", "l_panel.py")]

CRIT_V0 = """
V0.1 a test image written by l_png.write_png and read back by l_png.read_png has the same pixels, and the CRC of every chunk checks;
V0.2 ffmpeg reads it: its stderr (ffmpeg -i exits 1 with no output named) has a stream line naming png and the image's width and height;
V0.3 CONTROL: one byte flipped in the image data (the IDAT chunk) must make read_png raise a CRC error; a flipped byte in IHDR as well;
V0.4 the same holds for a real frame of the video (frame 0): written, read back equal, every CRC good, ffmpeg names png 1280x720.
"""
CRIT_V1 = """
V1.1 for 20 objects drawn with random.Random(20261123) from the seed's 2,688, each object drawn alone (no Earth, no text) in a 1,280 x 720
     image of the 'both' layout lights exactly the 3 x 3 blocks centred on the pixels its seed state projects to, in the colour of its
     group; the pixels come from a separate function (ref_pixel) that reads seed1.txt itself and is written for this check;
V1.2 the sample has at least 15 objects whose block lies in the image in both views;
V1.3 CONTROL: a pair of objects (different groups, different pixels with blocks 4 pixels or more apart in both views, found first by ref_pixel),
     positions swapped: each object's colour must light the OTHER object's blocks, and not its own.
"""
CRIT_V2 = """
V2.1 (a) prop's output at its first target (T_s) equals seed1.txt's state for every object bit for bit (read from prop's own output file,
     not from the run's arrays); every frame time equals T_s + 60 k exactly; the l_prop log names m1f's and the frame table's SHA-256;
V2.2 (b) for 20 objects and 5 frames with k >= 1 drawn with random.Random(20261124): the renderer's recorded pixel equals ref_pixel of the P line's
     position in both views; the drawn flag equals the reference's (not behind the Earth's disc, inside the image); in the frame's PNG the centre
     pixel of every drawn block has a group's colour; the live display's decoded position is within 0.5 km of the P line's, per coordinate;
     every value finite;
V2.3 CONTROL: an input whose object A has x changed by one unit in the last place (nextafter) gives, for A, states that differ from the main run's
     at some k >= 1, and for every other object of the input states bit-for-bit equal to the main run's at every k.
"""
CRIT_V3 = """
V3.1 (a) every number in panel_table.tsv equals the one in its source file and line (cell and part as the table says); the table has the 29
     rows (7 + 6 + 10 + 6) of the four charts, once each; the sources' SHA-256 equal the sidecars'. CONTROL: one planted wrong number must fail;
V3.2 (b) each chart's bar tops, found by scanning the picture's pixel column at each bar's centre for the series colour, equal (within 1 pixel;
     the exact count is reported) the extent a separate function (bar_row) computes from the table's value and the axis limits. CONTROL: a chart
     drawn from a table with its smallest value doubled must fail, for each of the four charts.
"""
CRIT_V4 = """
V4.1 scope: tests/l_*.py and every file under studies/debris-l/; .png only under studies/debris-l/panel/ (each read by l_png with its CRC good);
     no other binary or data extension, no NUL byte, nothing over 2 MB;
V4.2 every .py and .c carries 'cft-debris, MIT licence' in its first 800 bytes;
V4.3 no pattern hit: third-party licence and data headers, email, a temp-scratch path, token-like strings, LAN address, box home path, Windows and MSYS
     user paths, an app-data folder, the owner's login name, the folder names of the local scratch, ledger and downloads; each pattern must hit its plant;
V4.4 no catalogue number: no 5-digit number outside a hexadecimal token of 12 or more characters equals a catalogue number of the seed or of the
     downloads' snapshots; the test must find a planted one, and must exempt a planted hash;
V4.5 no __pycache__ under tests/ or studies/debris-l/.
"""

TS = L.TS_EXPECT


# ------------------------------------------------------------------ shared
def common(a, name, crit, detail=True):
    L.set_roots(scratch=a.scratch, ledger=a.ledger, repo=REPO, ffmpeg=getattr(a, "ffmpeg", ""), downloads=getattr(a, "downloads", ""), msys="C:/msys64",
                python=sys.executable)
    cpu = K.CpuAccount(name, a.cpu)
    out = os.path.join(a.ledger, "debris-l")
    log = L.Log(name, a.logs, SCRIPT, crit, a.keep, detail_dir=os.path.join(out, "logs") if detail else None, modules=MODS)
    return cpu, log, out


def finish(cpu, log, name):
    c = cpu.close("%s log %03d" % (name, log.n))
    log.w("# CPU: %.2f s by cycles / 2.5e9 (this script and every process it started)" % c)
    return log.close()


def load_seed(a):
    p = os.path.join(a.ledger, "debris-h", "box", "r2", "seed", "seed1.txt")
    return K.read_seed(p)["rows"], p


def load_work(a):
    W = os.path.join(a.scratch, "work")
    return np.load(os.path.join(W, "states.npy")), np.load(os.path.join(W, "groups.npy")), W


VIEWS_BOTH = {"top": (320, 380, 0.04), "edge": (960, 380, 0.04)}  # the 'both' layout, written out here for the check


def ref_pixel(x_m, y_m, z_m, view):
    """V1's separate projection: metres in, (column, row) out, by plain Python floats"""
    cx, cy, s = VIEWS_BOTH[view]
    x, v = x_m / 1000.0, (y_m if view == "top" else z_m) / 1000.0
    return math.floor(cx + x * s + 0.5), math.floor(cy - v * s + 0.5)


def ref_hidden(x_m, y_m, z_m, view):
    x, y, z = x_m / 1000.0, y_m / 1000.0, z_m / 1000.0
    r2 = L.EARTH_R_KM ** 2
    return (z < 0 and x * x + y * y < r2) if view == "top" else (y > 0 and x * x + z * z < r2)


def in_image(c, r):
    return 1 <= c < D.W - 1 and 1 <= r < D.H - 1


def block(c, r):
    return {(rr, cc) for rr in range(r - 1, r + 2) for cc in range(c - 1, c + 2)}


def lit_set(img):
    nz = np.argwhere(img.any(axis=2))
    return {(int(r), int(c)) for r, c in nz}


def draw_alone(pos_m, gi):
    img, _ = D.render(np.array([pos_m], dtype=float) / 1000.0, np.array([gi]), "both", with_earth=False, bg=False, legend=False, labels=False)
    return img


def expected_blocks(pos_m):
    s = set()
    for v in ("top", "edge"):
        c, r = ref_pixel(*pos_m, v)
        if in_image(c, r):
            s |= block(c, r)
    return s


def parse_prop(path):
    out = {}
    with open(path, "r", encoding="ascii") as f:
        for ln in f:
            if ln.startswith("P "):
                p = ln.split()
                out.setdefault(int(p[1]), []).append((p[2], [p[i] for i in range(3, 9)]))
    return out


def hexf(s):
    return float.fromhex(s)


def bits(x):
    return struct.pack(">d", x)


# ------------------------------------------------------------------ V0
def stage_v0(a):
    cpu, log, out = common(a, "v0_png", CRIT_V0)
    W = os.path.join(a.scratch, "work")
    rng = np.random.RandomState(20261123)
    img = rng.randint(0, 256, size=(120, 200, 3)).astype(np.uint8)
    img[:60, :, 0] = np.arange(200, dtype=np.uint8)[None, :]
    p = os.path.join(W, "v0_test.png")
    b = l_png.write_png(p, img)
    back, ch = l_png.read_png(p)
    log.check(back.shape == img.shape and (back == img).all() and all(c[2] for c in ch) and [c[0] for c in ch] == ["IHDR", "IDAT", "IEND"],
              "V0.1 test image %dx%d: pixels equal after read-back, chunks %s all with a good CRC" % (img.shape[1], img.shape[0], [c[0] for c in ch]))
    rc, so, se = K.run([a.ffmpeg, "-hide_banner", "-i", p], log, check=False)
    st = [ln for ln in se.decode("utf-8", "replace").splitlines() if "Video:" in ln]
    log.check(bool(st) and "png" in st[0] and "200x120" in st[0], "V0.2 ffmpeg names the stream: %s" % (re.sub(r"\s+", " ", st[0]).strip()[:80] if st else "none"))
    # control: flip one byte of the IDAT data, then of IHDR
    idat_at = b.index(b"IDAT") + 4 + 10
    bad = bytearray(b)
    bad[idat_at] ^= 0x01
    try:
        l_png.read_png(bytes(bad))
        c1 = False
    except l_png.PngError as e:
        c1 = "CRC" in str(e)
    ihdr_at = b.index(b"IHDR") + 4
    bad2 = bytearray(b)
    bad2[ihdr_at] ^= 0x01
    try:
        l_png.read_png(bytes(bad2))
        c2 = False
    except l_png.PngError as e:
        c2 = "CRC" in str(e)
    log.check(c1, "V0.3 CONTROL: one byte flipped in the IDAT data makes read_png raise a CRC error")
    log.check(c2, "V0.3 CONTROL: one byte flipped in IHDR makes read_png raise a CRC error")
    f0 = os.path.join(a.scratch, "frames", "f0000.png")
    fi, fch = l_png.read_png(f0)
    rc, so, se = K.run([a.ffmpeg, "-hide_banner", "-i", f0], log, check=False)
    st = [ln for ln in se.decode("utf-8", "replace").splitlines() if "Video:" in ln]
    log.check(fi.shape == (720, 1280, 3) and all(c[2] for c in fch) and bool(st) and "png" in st[0] and "1280x720" in st[0],
              "V0.4 frame 0: read back, CRCs good, ffmpeg names png 1280x720")
    return finish(cpu, log, "v0")


# ------------------------------------------------------------------ V1
def stage_v1(a):
    cpu, log, out = common(a, "v1_positions", CRIT_V1)
    rows, _ = load_seed(a)
    st, gi, W = load_work(a)
    rnd = random.Random(20261123)
    sample = rnd.sample(range(2688), 20)
    ok_all, inboth = True, 0
    for i in sample:
        pos = rows[i][3][:3]
        img = draw_alone(pos, int(gi[i]))
        exp = expected_blocks(pos)
        lit = lit_set(img)
        col = tuple(L.GROUP_COLOR[L.GROUPS[gi[i]]])
        colours_ok = all(tuple(int(v) for v in img[r, c]) == col for r, c in lit)
        match = (lit == exp) and colours_ok
        ok_all &= match
        both = all(in_image(*ref_pixel(*pos, v)) for v in ("top", "edge"))
        inboth += both
        log.d("object %d group %s: lit %d pixels, expected %d, equal %s, colour ok %s; top %s edge %s" % (
            i, L.GROUPS[gi[i]], len(lit), len(exp), lit == exp, colours_ok, ref_pixel(*pos, "top"), ref_pixel(*pos, "edge")))
    log.check(ok_all, "V1.1 20 objects each drawn alone: lit pixels equal the reference's blocks in the group's colour")
    log.check(inboth >= 15, "V1.2 %d of 20 sampled objects lie in the image in both views" % inboth)
    # control
    pair = None
    cand = list(range(2688))
    random.Random(20261125).shuffle(cand)
    for x in range(0, len(cand) - 1):
        i, j = cand[x], cand[x + 1]
        if gi[i] == gi[j]:
            continue
        pi_, pj = rows[i][3][:3], rows[j][3][:3]
        good = True
        for v in ("top", "edge"):
            ci, cj = ref_pixel(*pi_, v), ref_pixel(*pj, v)
            good &= in_image(*ci) and in_image(*cj) and max(abs(ci[0] - cj[0]), abs(ci[1] - cj[1])) >= 4
        if good:
            pair = (i, j)
            break
    log.check(pair is not None, "V1.3 a pair with different groups and well-separated pixels was found by ref_pixel")
    i, j = pair
    pi_, pj = rows[i][3][:3], rows[j][3][:3]
    pos = np.array([pj, pi_], dtype=float) / 1000.0  # swapped: object i now carries j's position and vice versa
    img, _ = D.render(pos, np.array([gi[i], gi[j]]), "both", with_earth=False, bg=False, legend=False, labels=False)
    ci_, cj_ = tuple(L.GROUP_COLOR[L.GROUPS[gi[i]]]), tuple(L.GROUP_COLOR[L.GROUPS[gi[j]]])

    def colour_at(pixelpos, colour):
        ok = True
        for v in ("top", "edge"):
            c, r = ref_pixel(*pixelpos, v)
            ok &= tuple(int(t) for t in img[r, c]) == colour
        return ok
    on_other = colour_at(pj, ci_) and colour_at(pi_, cj_)
    on_own = colour_at(pi_, ci_) or colour_at(pj, cj_)
    log.check(on_other and not on_own, "V1.3 CONTROL: after the swap each object's colour lights the other's pixels (%s) and not its own (%s)" % (on_other, not on_own))
    log.d("control pair: %d (group %s) and %d (group %s)" % (i, L.GROUPS[gi[i]], j, L.GROUPS[gi[j]]))
    return finish(cpu, log, "v1")


# ------------------------------------------------------------------ V2
def stage_v2(a):
    cpu, log, out = common(a, "v2_propagation", CRIT_V2)
    rows, seedp = load_seed(a)
    st, gi, W = load_work(a)
    prop = parse_prop(os.path.join(W, "all_prop.txt"))
    nf = L.NFRAMES
    ok = len(prop) == 2688 and all(len(prop[i]) == nf for i in range(2688))
    bad0, badT = 0, 0
    for i in range(2688):
        for k in range(nf):
            if hexf(prop[i][k][0]) != TS + L.DELTA_S * k:
                badT += 1
        if any(bits(hexf(prop[i][0][1][c])) != bits(rows[i][3][c]) for c in range(6)):
            bad0 += 1
    log.check(ok and bad0 == 0 and badT == 0, "V2.1 (a) 2688 x %d P lines; first target equals the seed's state bit for bit for all but %d objects; %d frame times off T_s + 60 k" % (nf, bad0, badT))
    # the l_prop log names the hashes (the newest one)
    lp = sorted(f for f in os.listdir(a.logs) if f.startswith("l_prop.") and f.endswith(".log"))[-1]
    txt = open(os.path.join(a.logs, lp), encoding="utf-8").read()
    log.check(K.sha256(a.m1f) in txt and "dd69fe0bc21e903bb3af9f4ee6711a0487cc96d040629bf26e3a3b62a635c82f" in txt,
              "V2.1 %s names m1f's SHA-256 %s and the frame table's" % (lp, K.sha256(a.m1f)))
    # (b)
    rnd = random.Random(20261124)
    objs = rnd.sample(range(2688), 20)
    frames = sorted(rnd.sample(range(1, nf), 5))
    pix = np.load(os.path.join(W, "pix.npz"))
    dtxt = open(os.path.join(a.ledger, "debris-l", "live_display.html"), "r", encoding="utf-8").read()
    mm = re.search(r'const gb=dec\("([A-Za-z0-9+/=]+)"\), pb=dec\("([A-Za-z0-9+/=]+)"\)', dtxt)
    disp = np.frombuffer(base64.b64decode(mm.group(2)), dtype="<i2").reshape(nf, 2688, 3)
    pal = {tuple(c) for c in L.GROUP_COLOR.values()}
    nb_pix = nb_drawn = nb_col = nb_disp = nb_fin = 0
    ndrawn = 0
    for k in frames:
        fimg, _ = l_png.read_png(os.path.join(a.scratch, "frames", "f%04d.png" % k))
        for i in objs:
            p6 = [hexf(x) for x in prop[i][k][1]]
            nb_fin += int(not all(math.isfinite(v) for v in p6))
            for v in ("top", "edge"):
                c, r = ref_pixel(*p6[:3], v)
                got = (int(pix[v + "_col"][k][i]), int(pix[v + "_row"][k][i]))
                nb_pix += int(got != (c, r))
                exp_drawn = (not ref_hidden(*p6[:3], v)) and in_image(c, r)
                nb_drawn += int(bool(pix[v + "_drawn"][k][i]) != exp_drawn)
                if exp_drawn:
                    ndrawn += 1
                    nb_col += int(tuple(int(t) for t in fimg[r, c]) not in pal)
                log.d("k %d object %d view %s: ref pixel %s recorded %s drawn %s" % (k, i, v, (c, r), got, exp_drawn))
            err = max(abs(float(disp[k, i, q]) - p6[q] / 1000.0) for q in range(3))
            nb_disp += int(err > 0.5 + 1e-9)
            log.d("k %d object %d: display decode error %.3f km" % (k, i, err))
    log.check(nb_pix == 0, "V2.2 (b) %d objects x %d frames x 2 views: recorded pixel differs from ref_pixel in %d cases" % (len(objs), len(frames), nb_pix))
    log.check(nb_drawn == 0, "V2.2 the drawn flag differs from the reference's in %d cases" % nb_drawn)
    log.check(nb_col == 0 and ndrawn > 0, "V2.2 in the frames' PNGs %d drawn centre pixels checked, %d not in a group's colour" % (ndrawn, nb_col))
    log.check(nb_disp == 0, "V2.2 the display's decoded position is within 0.5 km of the P line's in all but %d of %d cases" % (nb_disp, len(objs) * len(frames)))
    log.check(nb_fin == 0, "V2.2 %d non-finite values among the sampled P lines" % nb_fin)
    # control: object A's x one ulp up
    ctrl = rnd.sample(range(2688), 5)
    A = ctrl[0]
    tgt = [TS + L.DELTA_S * k for k in range(nf)]
    objl = []
    for i in ctrl:
        y = list(rows[i][3])
        if i == A:
            y[0] = math.nextafter(y[0], math.inf)
        objl.append((str(i), TS, y, rows[i][4], rows[i][5], tgt))
    ns = type("A", (), {})()
    ns.m1f, ns.table, ns.downloads = a.m1f, os.path.join(a.ledger, "debris-h", "frame_h0.bin"), a.downloads
    res, pout = KP.m1f_prop(ns, log, W, "v2ctl", objs=objl)
    changedA = sum(1 for k in range(1, nf) if any(bits(res[str(A)][k][1][c]) != bits(hexf(prop[A][k][1][c])) for c in range(6)))
    others_same = all(bits(res[str(i)][k][1][c]) == bits(hexf(prop[i][k][1][c])) for i in ctrl[1:] for k in range(nf) for c in range(6))
    log.check(changedA >= 1 and others_same, "V2.3 CONTROL: object A's states change in %d of %d frames (k >= 1); the other 4 objects' are bit-for-bit the main run's at every frame: %s" % (changedA, nf - 1, others_same))
    log.d("control object A = %d, others %s" % (A, ctrl[1:]))
    return finish(cpu, log, "v2")


# ------------------------------------------------------------------ V3
def read_table(path):
    rows = []
    with open(path, "r", encoding="utf-8") as f:
        head = None
        for ln in f:
            if ln.startswith("#") or not ln.strip():
                continue
            q = ln.rstrip("\n").split("\t")
            if head is None:
                head = q
                continue
            rows.append(dict(zip(head, q)))
    return rows


def source_value(studies, r):
    """a separate reader: the cell's text in the source line, then its number (regex over the cell)"""
    line = open(os.path.join(studies, r["source"]), "r", encoding="utf-8").read().split("\n")[int(r["line"]) - 1]
    cells = [c.strip() for c in line.strip().strip("|").split("|")]
    cell = cells[int(r["cell"])]
    if r["part"] == "a":
        return re.search(r"([0-9][0-9,]*\.?[0-9]*) /", cell).group(1)
    return re.fullmatch(r"[0-9][0-9,]*\.?[0-9]*", cell).group(0)


def table_mismatches(studies, rows):
    return [(r["chart"], r["category"], r["series"], r["value"], source_value(studies, r)) for r in rows if source_value(studies, r) != r["value"]]


AXES = {"g": (True, 1e3, 1e8), "i": (False, 0.0, 1e5), "h": (True, 0.01, 100.0), "k": (False, 0.0, 35.0)}
SERCOL = [(255, 159, 67), (80, 200, 255), (120, 255, 140), (255, 80, 90), (190, 150, 255), (240, 230, 110)]


def bar_row(v, chart):
    log, lo, hi = AXES[chart]
    f = (math.log10(v) - math.log10(lo)) / (math.log10(hi) - math.log10(lo)) if log else (v - lo) / (hi - lo)
    return 590 - int(round(f * (590 - 150)))


def chart_mismatches(img, rows, chart):
    """compare each bar's top row in the picture with bar_row of the table's value; returns (n bars, n exact, list of misses > 1 px)"""
    rr = [r for r in rows if r["chart"] == chart]
    cats = list(dict.fromkeys(r["category"] for r in rr))
    sers = list(dict.fromkeys(r["series"] for r in rr))
    gw = (1240 - 170) / len(cats)
    bw = gw * 0.7 / len(sers)
    exact, miss = 0, []
    for r in rr:
        gi_, si = cats.index(r["category"]), sers.index(r["series"])
        x0 = int(round(170 + gi_ * gw + 0.15 * gw + si * bw))
        cxm = (x0 + x0 + int(bw) - 2) // 2
        y = 589
        while y > 0 and tuple(int(t) for t in img[y, cxm]) == SERCOL[si]:
            y -= 1
        top = y + 1
        want = bar_row(float(r["value"].replace(",", "")), chart)
        exact += int(top == want)
        if abs(top - want) > 1:
            miss.append((r["category"], r["series"], top, want))
    return len(rr), exact, miss


def stage_v3(a):
    cpu, log, out = common(a, "v3_numbers", CRIT_V3)
    studies = os.path.join(REPO, "studies")
    panel = os.path.join(studies, "debris-l", "panel")
    rows = read_table(os.path.join(panel, "panel_table.tsv"))
    keys = [(r["chart"], r["category"], r["series"]) for r in rows]
    log.check(len(rows) == 29 and len(set(keys)) == 29 and collections.Counter(r["chart"] for r in rows) == {"g": 7, "i": 6, "h": 10, "k": 6},
              "V3.1 the table has %d rows, %d distinct, by chart %s" % (len(rows), len(set(keys)), dict(collections.Counter(r["chart"] for r in rows))))
    mm = table_mismatches(studies, rows)
    log.check(not mm, "V3.1 (a) every one of %d numbers equals its source line's: %d mismatches" % (len(rows), len(mm)))
    import json
    shas_ok = True
    for cid in "gihk":
        sc = json.load(open(os.path.join(panel, "chart_%s.png.sidecar.json" % cid)))
        for f, h in sc["sources"].items():
            shas_ok &= (K.sha256(os.path.join(studies, f)) == h)
        shas_ok &= (sc["sha256"] == K.sha256(os.path.join(panel, "chart_%s.png" % cid)))
        shas_ok &= (sc["data"]["panel_table.tsv"] == K.sha256(os.path.join(panel, "panel_table.tsv")))
    log.check(shas_ok, "V3.1 the sidecars' SHA-256 of the sources, the charts and the table equal the files'")
    planted = [dict(r) for r in rows]
    planted[0]["value"] = planted[0]["value"][:-1] + str((int(planted[0]["value"][-1]) + 1) % 10)
    pm = table_mismatches(studies, planted)
    log.check(len(pm) == 1, "V3.1 CONTROL: one planted wrong number (%d mismatches found, 1 expected)" % len(pm))
    # (b)
    for cid in "gihk":
        img, _ = l_png.read_png(os.path.join(panel, "chart_%s.png" % cid))
        n, exact, miss = chart_mismatches(img, rows, cid)
        log.check(not miss, "V3.2 (b) chart %s: %d bars, %d at the exact row, %d off by more than 1 pixel" % (cid, n, exact, len(miss)))
        # control: smallest value doubled
        vals = {}
        for r in rows:
            if r["chart"] == cid:
                vals.setdefault(r["category"], {})[r["series"]] = (float(r["value"].replace(",", "")), r["value"])
        lo_key = min(((c, s) for c in vals for s in vals[c]), key=lambda t: vals[t[0]][t[1]][0])
        v0 = vals[lo_key[0]][lo_key[1]]
        vals[lo_key[0]][lo_key[1]] = (v0[0] * 2, v0[1])
        cimg = P.draw_chart(P.CHARTS[cid], vals)
        n2, e2, miss2 = chart_mismatches(cimg, rows, cid)
        log.check(len(miss2) == 1 and miss2[0][0] == lo_key[0], "V3.2 CONTROL chart %s: its smallest value doubled is found: %d bars off by more than 1 pixel (1 expected)" % (cid, len(miss2)))
    return finish(cpu, log, "v3")


# ------------------------------------------------------------------ V4
def j(*parts):
    """the pieces of a pattern or of its plant, joined: written in pieces so that this file does not hit its own scan"""
    return b"".join(parts)


PATTERNS = {
    "third-party SPDX": (j(rb"SPDX-Lic", rb"ense-Identifier:\s*Apa", rb"che"), j(b"/* SPDX-Lic", b"ense-Identifier: Apa", b"che-2.0 */")),
    "cft-fp256 copyright line": (j(rb"Copyr", rb"ight 2026 Lo", rb"gan W\."), j(b"/* Copyr", b"ight 2026 Lo", b"gan W.\n")),
    "GPL text": (j(rb"GNU (Lesser |Affero )?Gene", rb"ral Public Lic", rb"ense"), j(b"under the GNU Gene", b"ral Public Lic", b"ense")),
    "Orekit header": (j(rb"Licensed to CS ", rb"GROUP"), j(b"Licensed to CS ", b"GROUP (CS) under one")),
    "Hipparchus header": (j(rb"Licensed to the Hippar", rb"chus project"), j(b"Licensed to the Hippar", b"chus project under")),
    "REBOUND author": (j(rb"Hanno ", rb"Rein"), j(b"Copyright (C) 2011 Hanno ", b"Rein")),
    "EIGEN gfc header": (j(rb"product_type\s+gravity_", rb"field|modelname\s+EIG", rb"EN"), j(b"product_type    gravity_", b"field")),
    "JPL ephemeris header": (j(rb"JPL Planetary Ephem", rb"eris|KSIZ", rb"E\s*="), j(b"KSIZ", b"E= 2036")),
    "CelesTrak SW header": (j(rb"DATATYPE Cssi", rb"SpaceWeather"), j(b"DATATYPE Cssi", b"SpaceWeather\nVERSION 1.2")),
    "GP CSV header": (j(rb"OBJECT_NAME,OBJECT_", rb"ID,EPOCH"), j(b"OBJECT_NAME,OBJECT_", b"ID,EPOCH,MEAN_MOTION")),
    "SATCAT field": (j(rb"DECAY_", rb"DATE|OPS_STATUS_", rb"CODE"), j(b"OPS_STATUS_", b"CODE,DECAY_", b"DATE")),
    "email address": (j(rb"[A-Za-z0-9._%+-]+@", rb"[A-Za-z0-9-]+(\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}"), j(b"someone", b"@example.org")),
    "temp-scratch path": (j(rb"(?i)scratch", rb"pad"), j(b"C:/Temp/claude/x/scratch", b"pad/y")),
    "token-like": (j(rb"ghp_[A-Za-z0-9]{20,}|github_pat_\w{20,}|sk-[A-Za-z0-9_-]{20,}|AKIA[0-9A-Z]{16}|-----BEGIN [A-Z ]*PRIV", rb"ATE KEY-----|xox[abprs]-[A-Za-z0-9-]{10,}"),
                   j(b"token gh", b"p_abcdefghijklmnopqrstuvwxyz0123")),
    "LAN address": (j(rb"192\.168\.", rb"\d{1,3}\.\d{1,3}"), j(b"ssh someone@192.", b"168.7.9")),
    "box home path": (j(rb"/ho", rb"me/[a-z]"), j(b"cd /ho", b"me/someone/run")),
    "Windows user path": (j(rb"(?i)[A-Z]:[/\\]+Us", rb"ers[/\\]"), j(b"C:\\Us", b"ers\\someone\\x")),
    "MSYS user path": (j(rb"(?i)/[a-z]/Us", rb"ers/"), j(b"/c/Us", b"ers/someone/x")),
    "app-data folder": (j(rb"(?i)App", rb"Data"), j(b"C:/x/App", b"Data/Local")),
    "owner's login name": (j(rb"(?i)\blo", rb"gan\b"), j(b"owner Lo", b"gan here")),
    "local folder names": (j(rb"(?i)cft-debris-(scra", rb"tch|led", rb"ger|downloads)"), j(b"C:/x/cft-debris-led", b"ger/y")),
    "owner's domain": (j(rb"(?i)improper", rb"aperture"), j(b"mail at improper", b"aperture dot example")),
}
DATA_EXT = {".jpg", ".jpeg", ".gif", ".bmp", ".ico", ".pdf", ".bin", ".exe", ".dll", ".o", ".a", ".so", ".jar", ".class", ".zip", ".tar", ".gz", ".7z",
            ".gfc", ".421", ".csv", ".daily", ".dat", ".npy", ".npz", ".pkl", ".mp4", ".html"}
SOURCE_EXT = {".c", ".h", ".py", ".js", ".sh"}
HEXCH = set(b"0123456789abcdefABCDEF")
NUM = re.compile(rb"(?<![0-9.])([0-9]{5})(?![0-9])")


def in_hex_token(b, lo, hi):
    """is the span [lo, hi) inside a run of hexadecimal characters 12 or more long"""
    s, e = lo, hi
    while s > 0 and b[s - 1] in HEXCH:
        s -= 1
    while e < len(b) and b[e] in HEXCH:
        e += 1
    return e - s >= 12


def catalogue_numbers(a):
    norad = set()
    for ln in open(os.path.join(a.ledger, "debris-h", "box", "r2", "seed", "seed1.txt"), encoding="ascii"):
        if not ln.startswith("#") and ln.strip():
            norad.add(ln.split()[1].encode())
    if getattr(a, "downloads", None):
        for snap in ("S0", "S1", "SH0"):
            for g in L.GROUPS:
                p = os.path.join(a.downloads, "gp-%s-%s" % (g, snap), "gp-%s-%s.csv" % (g, snap))
                if os.path.exists(p):
                    norad |= {r["NORAD_CAT_ID"].encode() for r in csv.DictReader(io.StringIO(open(p, "rb").read().decode("utf-8"), newline=""))}
    return norad


def stage_v4(a):
    cpu, log, out = common(a, "v4_scan" if not a.trial else "v4_scan_trial", CRIT_V4, detail=False)
    log.w("# %s run" % ("TRIAL" if a.trial else "FINAL"))
    for name, (pat, plant) in PATTERNS.items():
        assert re.search(pat, plant), "control FAILED: %s" % name
    log.check(True, "V4.3 CONTROL: all %d patterns hit their plants" % len(PATTERNS))
    norad = catalogue_numbers(a)
    t_in = in_hex_token(b"sha 9a12cd" + b"25" + b"544ef0b3 x", 10, 15)
    t_out = in_hex_token(b"seed " + b"25" + b"544 x", 5, 10)
    log.check(t_in and not t_out, "V4.4 CONTROL: a planted 5-digit run inside a 16-character hash is exempt, outside one it is not")
    log.check(len(norad) >= 2688, "V4.4 %d catalogue numbers known (the seed's, and the downloads' snapshots where present)" % len(norad))
    fake = sorted(x for x in norad if len(x) == 5)[0]
    planted = b"planted number " + fake + b" here"
    hit = [m for m in NUM.finditer(planted) if m.group(1) in norad and not in_hex_token(planted, m.start(1), m.end(1))]
    log.check(len(hit) == 1, "V4.4 CONTROL: a planted known catalogue number is found")
    files = [os.path.join(L.TESTS, f) for f in sorted(os.listdir(L.TESTS)) if f.startswith("l_") and f.endswith(".py")]
    base = os.path.join(REPO, "studies", "debris-l")
    for dp, dn, fn in os.walk(base):
        for f in fn:
            files.append(os.path.join(dp, f))
    pyc = [p for p in (os.path.join(L.TESTS, "__pycache__"),) if os.path.exists(p)] + [dp for dp, dn, fn in os.walk(base) if os.path.basename(dp) == "__pycache__"]
    byext = collections.Counter(os.path.splitext(f)[1].lower() or "(none)" for f in files)
    log.w("# scope: %d files by extension %s" % (len(files), dict(sorted(byext.items()))))
    big, nul, dataext, noheader, pnghits, hits, ids = [], [], [], [], [], collections.defaultdict(list), []
    panel = os.path.normcase(os.path.join(base, "panel"))
    for f in files:
        rel = os.path.relpath(f, REPO).replace("\\", "/")
        b = open(f, "rb").read()
        ext = os.path.splitext(f)[1].lower()
        if len(b) > 2 * 1024 * 1024:
            big.append(rel)
        if ext == ".png":
            if not os.path.normcase(os.path.dirname(f)) == panel:
                dataext.append(rel)
            else:
                try:
                    l_png.read_png(b)
                except Exception as e:  # noqa: BLE001
                    pnghits.append((rel, str(e)))
            continue
        if b"\x00" in b:
            nul.append(rel)
        if ext in DATA_EXT:
            dataext.append(rel)
        if ext in SOURCE_EXT and not re.search(rb"cft-debris, MIT licen[cs]e", b[:800]):
            noheader.append(rel)
        for name, (pat, _) in PATTERNS.items():
            m = re.findall(pat, b)
            if m:
                hits[name].append((rel, len(m)))
        for m in NUM.finditer(b):
            if m.group(1) in norad and not in_hex_token(b, m.start(1), m.end(1)):
                ids.append(rel)
    log.check(not big, "V4.1 nothing over 2 MB (%s)" % big)
    log.check(not dataext and not nul and not pnghits, "V4.1 no binary or data extension outside panel PNGs %s, NUL %s, bad PNG %s" % (dataext, nul, pnghits))
    log.check(not noheader, "V4.2 every source has the cft-debris MIT line in its first 800 bytes (without: %s)" % noheader)
    for name in PATTERNS:
        log.check(not hits.get(name), "V4.3 pattern %s: %s" % (name, hits.get(name, [])))
    log.check(not ids, "V4.4 catalogue-number hits outside hexadecimal tokens: %d in %s" % (len(ids), sorted(set(ids))[:6]))
    log.check(not pyc, "V4.5 __pycache__: %s" % pyc)
    return finish(cpu, log, "v4")


# ------------------------------------------------------------------ the manifest
def stage_manifest(a):
    base = os.path.join(REPO, "studies", "debris-l")
    mp = os.path.join(base, "MANIFEST.sha256")
    if os.path.exists(mp):
        os.remove(mp)  # my own earlier manifest
    ents = []
    for dp, dn, fn in os.walk(base):
        dn.sort()
        for f in sorted(fn):
            p = os.path.join(dp, f)
            ents.append((K.sha256(p), os.path.relpath(p, base).replace("\\", "/")))
    ents.sort(key=lambda t: t[1])
    with open(mp, "x", encoding="utf-8", newline="\n") as f:
        for h, r in ents:
            f.write("%s *%s\n" % (h, r))
    ok = 0
    for ln in open(mp, encoding="utf-8"):
        h, r = ln.rstrip("\n").split(" *", 1)
        ok += int(K.sha256(os.path.join(base, r)) == h)
    present = sum(len(fn) for _, _, fn in os.walk(base)) - 1
    print("MANIFEST.sha256: %d lines, %d verified, %d files present besides it" % (len(ents), ok, present))
    return 0 if ok == len(ents) == present else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", choices=["v0", "v1", "v2", "v3", "v4", "manifest"])
    for o in ("--ledger", "--scratch", "--logs", "--keep", "--cpu"):
        ap.add_argument(o, required=True)
    ap.add_argument("--m1f", default="")
    ap.add_argument("--downloads", default="")
    ap.add_argument("--ffmpeg", default="")
    ap.add_argument("--trial", action="store_true")
    a = ap.parse_args()
    return {"v0": stage_v0, "v1": stage_v1, "v2": stage_v2, "v3": stage_v3, "v4": stage_v4, "manifest": stage_manifest}[a.stage](a)


if __name__ == "__main__":
    sys.exit(main())
