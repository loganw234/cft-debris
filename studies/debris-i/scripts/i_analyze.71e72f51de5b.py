"""i_analyze.py - cft-debris DEBRIS-I: I3's criteria and measurements, the model gap and I5's statistics, from the
records of the program's driver (tests/i_run.c) and of M1's side (tests/m1i.c), on the desktop or from the box.

cft-debris, MIT licence (see LICENSE at the repository root). Written by DEBRIS-I, 2026-11-23.

I3's criterion (the plan's, fixed before the data): at every segment boundary (every 40 steps), for every object,
    |program at p - M1 at the matching kind| <= T_round(p, n) + T_frame, component by component,
    T_round(p, n) = 64 n 2^-p S, n the steps so far, p = 53, 113 or 237;
    positions S = 7e6 m, T_frame = 1e-3 m; velocities S = 8e3 m/s, T_frame = 1e-6 m/s;
    pairs: binary64 / cft64, binary128 / cft128, binary256 / cft256; binary64 / native64 reported beside.
    t: at every boundary, the program's t equals M1's host stage time, exactly.
The NaN rule: NaN results agree as NaNs; a NaN on one side alone fails.
The measurements (fixed now): the share of each tolerance used (median and largest over objects and boundaries); the
program's binary64 against its binary256 (median and largest position difference at 1, 6 and 24 hours). The model gap:
M1 with the program's forces against M1's full model, position differences at 1, 6 and 24 hours, median and largest,
their radial, along-track and cross-track parts, by perigee band, and one force at a time. No figure of the gap is an
error of either model: it is a difference between two models.
"""
import os
import struct
import sys
from fractions import Fraction

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import i_vals as V  # noqa: E402

P_OF = {"fp64": 53, "fp128": 113, "fp256": 237}
KIND_OF = {"fp64": "cft64", "fp128": "cft128", "fp256": "cft256"}
ESZ_KIND = {"native64": 8, "cft64": 8, "cft128": 16, "cft256": 32, "native32": 4, "cft32": 4}
FMT_OF_KIND = {"native64": "fp64", "cft64": "fp64", "cft128": "fp128", "cft256": "fp256", "native32": "fp32",
               "cft32": "fp32"}
S_POS, S_VEL = Fraction(7 * 10 ** 6), Fraction(8 * 10 ** 3)
TF_POS, TF_VEL = Fraction(1, 1000), Fraction(1, 10 ** 6)


# ------------------------------------------------------------------ exact decoding (standard library)

def decode(fmt, bits):
    """The exact value of an IEEE encoding, or None for a NaN, or +-inf as a float."""
    eb, mb = {"fp32": (8, 23), "fp64": (11, 52), "fp128": (15, 112), "fp256": (19, 236)}[fmt]
    sign = bits >> (eb + mb)
    e = (bits >> mb) & ((1 << eb) - 1)
    m = bits & ((1 << mb) - 1)
    bias = (1 << (eb - 1)) - 1
    if e == (1 << eb) - 1:
        if m:
            return None
        return float("-inf") if sign else float("inf")
    if e == 0:
        v = Fraction(m) / Fraction(2) ** (bias - 1 + mb)
    else:
        v = Fraction((1 << mb) | m) * Fraction(2) ** (e - bias - mb)
    return -v if sign else v


def read_m1_traj(path):
    """m1i traj's lines 'S idx step t x y z vx vy vz': {(idx, step): (t as Fraction, [6 encodings])}, and the kind."""
    out, kind = {}, None
    for raw in open(path, "rb"):
        line = raw.decode("ascii")
        if line.startswith("# m1i kind"):
            kind = line.split()[3]
        if not line.startswith("S "):
            continue
        w = line.split()
        out[(int(w[1]), int(w[2]))] = (Fraction(float.fromhex(w[3])), [int(x, 16) for x in w[4:10]])
    return out, kind


def read_prog_segs(path, lane_idx, nstate, esz, steps_seg=40):
    """i_run's segment file: {(idx, step): [7 encodings: t, x, y, z, vx, vy, vz]} and the marks' lane bytes."""
    segs = V.read_segs(path, len(lane_idx), nstate, esz)
    out, bytes_ = {}, {}
    k = 0
    for (_r, _s, st, lb) in segs:
        k += 1
        for li, idx in enumerate(lane_idx):
            out[(idx, steps_seg * k)] = st[li]
            bytes_[(idx, steps_seg * k)] = lb[li]
    return out, bytes_


# ------------------------------------------------------------------ I3's criterion

def i3_compare(prog, pfmt, m1, kfmt, steps, objects, p_bits):
    """Every boundary and object: (failures, shares list, t mismatches, NaN notes)."""
    fails, shares, tbad, nan_pairs = [], [], [], 0
    for idx in objects:
        for n in steps:
            if (idx, n) not in prog or (idx, n) not in m1:
                fails.append((idx, n, "missing"))
                continue
            ps = prog[(idx, n)]
            t_m1, ms = m1[(idx, n)]
            if decode(pfmt, ps[0]) != t_m1:
                tbad.append((idx, n))
            for c in range(6):
                pv, mv = decode(pfmt, ps[1 + c]), decode(kfmt, ms[c])
                if pv is None and mv is None:
                    nan_pairs += 1
                    continue
                S, TF = (S_POS, TF_POS) if c < 3 else (S_VEL, TF_VEL)
                tol = 64 * n * S / Fraction(2) ** p_bits + TF
                if pv is None or mv is None or isinstance(pv, float) or isinstance(mv, float):
                    fails.append((idx, n, "nan-or-inf c%d" % c))
                    shares.append(float("inf"))
                    continue
                d = abs(pv - mv)
                shares.append(float(d / tol))
                if d > tol:
                    fails.append((idx, n, "c%d share %.3g" % (c, float(d / tol))))
    return fails, shares, tbad, nan_pairs


def pos_diff(a, afmt, b, bfmt):
    """|position(a) - position(b)| as a float (m), exact differences first."""
    import math
    s = 0.0
    for c in range(3):
        x, y = decode(afmt, a[c]), decode(bfmt, b[c])
        if x is None or y is None or isinstance(x, float) or isinstance(y, float):
            return float("nan")
        s += float(x - y) ** 2
    return math.sqrt(s)


def rtn(state_ref, fmt_ref, state_other, fmt_other):
    """The position difference (other - ref) in the reference's radial, along-track and cross-track directions."""
    import math
    r = [float(decode(fmt_ref, state_ref[c])) for c in range(3)]
    v = [float(decode(fmt_ref, state_ref[3 + c])) for c in range(3)]
    d = [float(decode(fmt_other, state_other[c]) - decode(fmt_ref, state_ref[c])) for c in range(3)]

    def unit(a):
        n = math.sqrt(sum(x * x for x in a))
        return [x / n for x in a]

    def cross(a, b):
        return [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]]
    R = unit(r)
    C = unit(cross(r, v))
    A = cross(C, R)
    return tuple(sum(x * y for x, y in zip(d, u)) for u in (R, A, C))


def stats(v):
    s = sorted(x for x in v if x == x)
    if not s:
        return (float("nan"), float("nan"), 0)
    n = len(s)
    med = s[n // 2] if n % 2 else 0.5 * (s[n // 2 - 1] + s[n // 2])
    return med, s[-1], n


# ------------------------------------------------------------------ phase 2: the box's records

G4 = {  # DEBRIS-G's G4 (MEASURED there, studies/DEBRIS-G-build.md section 3's table): M1's full model, L = 64, X at
        # W = 1, 18 and 36 (W = 36 the median of 3), object-seconds a second, in its sensitive window B0107
    "native64": (1291561, 17613716, 18259424), "cft64": (1137, 15929, 15322), "cft128": (684, 9587, 9564),
    "cft256": (299, 4176, 4332)}

PHASE2_CRIT = """Phase 2 (DEBRIS-I's, on the desktop, from the box's records as the lead copied them to the ledger):
M  READY's rule for marks: every marks file of the box's runs (out/i3/prog-*.marks.bin, out/i5/*.marks.bin) is read;
   each record is replayed by lang.run from its boundary state, and a lane whose replay differs is voided from that
   segment and redone on the desktop. A gate is evaluated only on unmarked or replayed-equal states.
I3 the criterion of this module's docstring, at every one of the 144 boundaries (every 40 steps of 5,760) for each of the
   64 objects, binary64 / cft64, binary128 / cft128, binary256 / cft256 (binary64 / native64 beside); t exact.
   Measurements (fixed in the plan): the share of each tolerance used (median and largest over objects and boundaries);
   the marks by format and routine; the program's binary64 against its binary256, position, median and largest at 1, 6
   and 24 hours.
GAP the model gap (M1 alone, native64 and cft64; no criterion; a difference between two models, never an error): M1 with
   the program's forces against its full model at 1, 6 and 24 hours, median and largest position difference, and its
   radial, along-track and cross-track parts (full - prog, in the prog run's radial / along-track / cross-track frame:
   R along r, C along r x v, A = C x R); by perigee band (i3_sample.tsv's bands); one force at a time: degree 7
   against 20 (srp off: --nmax 20 against prog), radiation pressure off against on (degree 7: --srp 1 against prog).
   The program has M1's 28 bands, so the one-band comparison does not arise.
I5 statistics (fixed in the plan and box_i5's criteria): X per configuration and W, with its validity and foreign load;
   the ratios, each a rate against a rate (X / X, never CPU times): the program against M1 at the program's forces
   (binary64 / cft64, binary128 / cft128, binary256 / cft256; binary64 / native64 beside), and against M1's full model
   (DEBRIS-G's G4 figures, same W); M1 at the program's forces against its full model; X(18) / (18 X(1)) and
   X(36) / X(18). X at W = 36 is the configuration's capacity at real time, an extrapolation past the 2,304 objects run."""


def read_tsv_sample(path):
    out = {}
    for raw in open(path, "rb"):
        line = raw.decode("ascii")
        if line.startswith("#") or not line.strip():
            continue
        i, b, n = line.split()
        out[int(i)] = (int(b), int(n))
    return out


def phase2(a):
    import json
    import i_lib
    here = os.path.dirname(os.path.abspath(__file__))
    log = i_lib.Log(os.path.join(a.repo, "studies", "debris-i", "logs"), "phase2", os.path.abspath(__file__),
                    [PHASE2_CRIT, __doc__], keep_dir=os.path.join(a.repo, "studies", "debris-i", "scripts"),
                    modules=[os.path.join(here, m) for m in ("i_vals.py", "i_lib.py")])
    box, stage, led = a.box, a.stage, a.ledger
    plan = json.load(open(os.path.join(stage, "i3", "plan.json"), "rb"))
    sample = read_tsv_sample(os.path.join(led, "i3_sample.tsv"))
    log.w("records: the box's out/ in the ledger, MANIFEST.box-001.sha256 %s; the staged plan %s; the sample %s" % (
        i_lib.sha256_file(os.path.join(box, "MANIFEST.box-001.sha256")),
        i_lib.sha256_file(os.path.join(stage, "i3", "plan.json")), i_lib.sha256_file(os.path.join(led, "i3_sample.tsv"))))
    # M: the marks
    nmarks, nfiles = {}, 0
    for sub in ("i3", "i5"):
        for fn in sorted(os.listdir(os.path.join(box, "out", sub))):
            if fn.endswith(".marks.bin"):
                nfiles += 1
                sz = os.path.getsize(os.path.join(box, "out", sub, fn))
                fmt = [f for f in ("fp64", "fp128", "fp256") if "-%s-" % f in fn][0]
                rec = 12 + plan["nscr"][fmt] * V.ESZ[fmt] + 7 * V.ESZ[fmt]
                if sz % rec:
                    raise SystemExit("%s: not whole records" % fn)
                nmarks[(sub, fmt)] = nmarks.get((sub, fmt), 0) + sz // rec
    for k in sorted(nmarks):
        log.w("marks in %s at %s: %d marked lane-segments" % (k[0], k[1], nmarks[k]))
    total = sum(nmarks.values())
    log.check(nfiles == 24 + 3 * (1 + 18 + 36) and total == 0, "M: %d marks files read (I3's 24, I5's 165); %d marks, so nothing "
              "to replay and no lane to redo" % (nfiles, total))
    if total:
        raise SystemExit("marks to replay: the replay is not built into this version")
    # I3
    steps = list(range(40, 5761, 40))
    objs = sorted(sample)
    prog, m1 = {}, {}
    for fmt in ("fp64", "fp128", "fp256"):
        rec = {}
        for b in plan["batches"]:
            r_, _lb = read_prog_segs(os.path.join(box, "out", "i3", "prog-%s-b%d.seg.bin" % (fmt, b["n"])), b["idx"], 7,
                                     V.ESZ[fmt])
            rec.update(r_)
        prog[fmt] = rec
    for vn in ("prog", "full", "deg20", "srp"):
        for kind in (("native64", "cft64", "cft128", "cft256") if vn == "prog" else ("native64", "cft64")):
            rec = {}
            for b in plan["batches"]:
                r_, _k = read_m1_traj(os.path.join(box, "out", "i3", "m1-%s-%s-b%d.txt" % (vn, kind, b["n"])))
                rec.update(r_)
            m1[(vn, kind)] = rec
    log.w("read: the program's boundary states at 3 formats and M1's at %d model-kind pairs, %d objects x %d boundaries"
          % (len(m1), len(objs), len(steps)))
    per_obj = {}
    for fmt in ("fp64", "fp128", "fp256"):
        for kind in ([KIND_OF[fmt]] + (["native64"] if fmt == "fp64" else [])):
            fails, shares, tbad, nanp = i3_compare(prog[fmt], fmt, m1[("prog", kind)], FMT_OF_KIND[kind], steps, objs,
                                                   P_OF[fmt])
            med, big, n = stats(shares)
            text = ("I3 %s against %s: %d values at %d boundaries x %d objects; share of the tolerance median %.3g, "
                    "largest %.3g; t mismatches %d; NaN pairs %d; over %d" % (fmt, kind, n, len(steps), len(objs), med, big,
                                                                             len(tbad), nanp, len(fails)))
            if kind == KIND_OF[fmt]:
                log.check(not fails and not tbad and n == len(steps) * len(objs) * 6, text)
                for o in objs:
                    _f, sh, _t, _n = i3_compare(prog[fmt], fmt, m1[("prog", kind)], FMT_OF_KIND[kind], steps, [o], P_OF[fmt])
                    per_obj.setdefault(o, {})[fmt] = max(sh)
            else:
                log.w("(beside) " + text)
    for n in (240, 1440, 5760):
        d = [pos_diff(prog["fp64"][(i, n)][1:4], "fp64", prog["fp256"][(i, n)][1:4], "fp256") for i in objs]
        med, big, k = stats(d)
        log.w("I3 measurement: the program's binary64 against its binary256 at %2d h: position median %.3e m, largest "
              "%.3e m (%d objects)" % (n // 240, med, big, k))
    # the model gap
    bands = sorted(set(b for b, _n in sample.values()))
    gap_rows = []
    for kind in ("native64", "cft64"):
        fk = FMT_OF_KIND[kind]
        for (x, y, what) in (("prog", "full", "the program's forces against the full model"),
                             ("prog", "deg20", "degree 7 against 20 (radiation pressure off)"),
                             ("prog", "srp", "radiation pressure off against on (degree 7)")):
            for n in (240, 1440, 5760):
                d, R_, A_, C_ = [], [], [], []
                for i in objs:
                    s0, s1 = m1[(x, kind)][(i, n)][1], m1[(y, kind)][(i, n)][1]
                    d.append(pos_diff(s1[:3], fk, s0[:3], fk))
                    if d[-1] == d[-1]:
                        r, al, c = rtn(s0, fk, s1, fk)
                        R_.append(abs(r))
                        A_.append(abs(al))
                        C_.append(abs(c))
                    gap_rows.append((kind, x, y, n, i, d[-1]))
                med, big, k = stats(d)
                rm, rb, _ = stats(R_)
                am, ab, _ = stats(A_)
                cm, cb, _ = stats(C_)
                log.w("GAP %s, %s, at %2d h: position median %.4g m, largest %.4g m (%d objects); radial median %.3g "
                      "largest %.3g; along-track median %.3g largest %.3g; cross-track median %.3g largest %.3g" % (
                          kind, what, n // 240, med, big, k, rm, rb, am, ab, cm, cb))
                if y == "full":
                    for bd in bands:
                        db = [d[j] for j, i in enumerate(objs) if sample[i][0] == bd]
                        m_, b_, k_ = stats(db)
                        log.w("GAP %s, %s, at %2d h, perigee band %d: median %.4g m, largest %.4g m (%d objects)" % (
                            kind, what, n // 240, bd, m_, b_, k_))
    # the ledger's per-object tables
    pdir = os.path.join(led, "phase2")
    os.makedirs(pdir, exist_ok=True)
    p1 = os.path.join(pdir, "i3_per_object.%s.tsv" % time.strftime("%Y%m%d-%H%M%S"))
    with open(p1, "x", encoding="ascii", newline="\n") as f:
        f.write("# seed index, band, largest share of I3's tolerance at fp64, fp128, fp256 (over the 144 boundaries)\n")
        for o in objs:
            f.write("%d\t%d\t%.4g\t%.4g\t%.4g\n" % (o, sample[o][0], per_obj[o]["fp64"], per_obj[o]["fp128"], per_obj[o]["fp256"]))
    p2 = os.path.join(pdir, "gap_per_object.%s.tsv" % time.strftime("%Y%m%d-%H%M%S"))
    with open(p2, "x", encoding="ascii", newline="\n") as f:
        f.write("# kind, model a, model b, step, seed index, |r_b - r_a| (m)\n")
        for row in gap_rows:
            f.write("%s\t%s\t%s\t%d\t%d\t%.6g\n" % row)
    log.w("per-object tables in the ledger: %s %s, %s %s" % (os.path.basename(p1), i_lib.sha256_file(p1),
                                                            os.path.basename(p2), i_lib.sha256_file(p2)))
    # I5
    jp = [f for f in os.listdir(os.path.join(box, "logs")) if f.startswith("box_i5.runs.") and f.endswith(".json")]
    if len(jp) != 1:
        raise SystemExit("I5: %d runs files" % len(jp))
    rows = json.load(open(os.path.join(box, "logs", jp[0]), "rb"))
    log.w("I5: %s SHA-256 %s, %d runs" % (jp[0], i_lib.sha256_file(os.path.join(box, "logs", jp[0])), len(rows)))
    X = {(r["name"], r["W"]): r for r in rows}
    log.check(len(rows) == 21 and all(r["valid"] for r in rows), "I5: 21 runs, every one valid")
    fl = [r["foreign_share"] for r in rows]
    log.w("I5: foreign load per run %.3f%% to %.3f%%; wall time per run %.1f s to %.1f s" % (
        100 * min(fl), 100 * max(fl), min(r["wall_s"] for r in rows), max(r["wall_s"] for r in rows)))
    for r in rows:
        log.w("I5 X %s W=%d: %.1f object-seconds a second (wall %.1f s, %.0f object-seconds, foreign load %.3f%%)" % (
            r["name"], r["W"], r["X"], r["wall_s"], r["objsec"], 100 * r["foreign_share"]))
    for fmt, kind in (("fp64", "cft64"), ("fp128", "cft128"), ("fp256", "cft256"), ("fp64", "native64")):
        for wi, W in enumerate((1, 18, 36)):
            p, m = X[("prog-" + fmt, W)]["X"], X[("m1-" + kind, W)]["X"]
            log.w("I5 ratio W=%2d: program %s / M1 %s at the program's forces %.3f; / M1 %s full model (G4) %.3f; M1 %s "
                  "program's forces / full model (G4) %.3f" % (W, fmt, kind, p / m, kind, p / G4[kind][wi], kind,
                                                               m / G4[kind][wi]))
    for nm in sorted(set(r["name"] for r in rows)):
        x1, x18, x36 = X[(nm, 1)]["X"], X[(nm, 18)]["X"], X[(nm, 36)]["X"]
        log.w("I5 %s: X(18)/(18 X(1)) %.3f, X(36)/X(18) %.3f; capacity at real time (X at W=36, an extrapolation past "
              "the 2,304 objects run) %.0f objects" % (nm, x18 / (18 * x1), x36 / x18, x36))
    sys.exit(1 if log.close() else 0)


if __name__ == "__main__":
    import argparse
    import time
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=("phase2", "doc"))
    ap.add_argument("--repo")
    ap.add_argument("--box")
    ap.add_argument("--stage")
    ap.add_argument("--ledger")
    a = ap.parse_args()
    if a.mode == "doc":
        print(__doc__)
    else:
        phase2(a)
