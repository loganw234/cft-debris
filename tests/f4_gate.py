# f4_gate.py - cft-debris M1 (DEBRIS-F), gate F4: the forces in the real frame against Orekit 13.1.9, with Orekit's
# ITRF (IERS 2010, simple EOP) as the body frame.
# cft-debris, MIT licence (see LICENSE at the repository root). Written by DEBRIS-F, 2026-11-16.
#
#   python -I -B tests/f4_gate.py [table]
import math
import os
import random
import sys
from fractions import Fraction

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import f_lib as F  # noqa: E402

CRITERIA = """
States: 1,000 LEO states (random.Random(0xF4)): 300 to 800 km up, direction uniform, speed circular times 0.99 to 1.01
  in a random direction perpendicular to r; area 0.5 to 20 m^2, mass 50 to 2,000 kg, Cd 2.0 to 2.4; bc = Cd A/(2 m).
  Epochs: 8 of the Earth orientation file's own dates inside the window, MJD 61330 to 61358 every 4th, at 0h UTC, 125
  states each (the window spans 34 days, not the week the plan assumed, so 8 of its 34 dates are used). F4 tests the
  forces given a frame; F3(a) tests the frame. Ours: tests/m1f.c mode f4 at native64 and cft64, the table interpolated
  at each state's epoch (TDB of 0h UTC, binary64); Orekit's: tests/f4_orekit.js at the same instant (our TAI).
D1 gravity, degrees 2 to 20, inertial: |a_ours - a_Orekit| <= 3.1e-12 m/s^2 at every state, at native64 and cft64.
   Basis: F3(a)'s tolerance, 50 uas = 2.42e-10 rad, turns J2's acceleration of about 1.25e-2 m/s^2 by 3.03e-12 m/s^2
   (COMPUTED); DEBRIS-E E6's gravity agreement, 7.35e-17 m/s^2, added; rounded up to 3.1e-12.
D2 drag, one band (3.725e-12 kg/m^3 at 400 km, scale height 58,515 m), co-rotating with each side's frame:
   |a_ours - a_Orekit| / |a_Orekit| <= 1e-7 at every state, at native64 and cft64. Basis: the co-rotation rates are
   defined differently - ours from central differences of our M (UT1-UTC's derivative, the precession-nutation rate),
   Orekit's from its LOD (its file column, filled where blank) and its interpolated precession-nutation rate; LOD of up
   to 3 ms is 3.5e-8 of omega and that rate at most 2e-11 rad/s; |omega x r|/|v| is about 0.07, and a ~ |v_rel| v_rel
   doubles a relative change, so one side lacking both would differ by at most about 4.5e-8; E6's drag agreement,
   6.8e-14, added.
C1 NEGATIVE CONTROL: bc planted 1% high on our side (m1f --plant-bc 0.01) must break D2 at every state (expected
   about 1e-2 relative).
C2 NEGATIVE CONTROL: a pole tilt of ten times F3(a)'s tolerance in our frame alone - a table built with xp + 500 uas
   (2.424e-9 rad) - must break D1 (expected largest difference about 3e-11 m/s^2, ten times D1's basis).
REPORTED: native64 against cft64 bit for bit (gravity has no transcendental; drag has exp, the C library's in native).
"""

TABLE = sys.argv[1] if len(sys.argv) > 1 else F.DATA + "/tables/frame_main.bin"
GFC_SHA_COPY = "bf296183bf9c9180e58c64a2fca22ece0124d6c7f82448508b8599a944010852"   # DEBRIS-C's and DEBRIS-E's copy


def gfc_copy(log):
    """the de-duplicated copy of the benchmark's EIGEN6-C4.gfc, derived into the scratch under the lead's ruling of
    2026-11-12 18:07 (DEBRIS-C's derive_gfc_copy.py, DEBRIS-E's e6_gfc_copy.py): line 16 removed, nothing else"""
    src = F.DOWNLOADS + "EIGEN6-C4.gfc/EIGEN6-C4.gfc"
    d = F.DATA + "/gfc_dedup"
    os.makedirs(d, exist_ok=True)
    lines = open(src, "rb").read().split(b"\n")
    log.check(lines[15].split()[:3] == [b"gfc", b"0", b"0"] and lines[14].split()[:3] == [b"gfc", b"0", b"0"],
              "the gfc file's lines 15 and 16 are both the (0, 0) coefficient")
    out = b"\n".join(lines[:15] + lines[16:])
    path = d + "/EIGEN6-C4.gfc"
    if not os.path.exists(path):
        with open(path, "wb") as f:
            f.write(out)
    log.check(open(path, "rb").read() == out, "the copy equals the original less line 16")
    h = F.sha256(path)
    log.check(h == GFC_SHA_COPY, "the copy's sha256 %s equals DEBRIS-C's and DEBRIS-E's" % h)
    return d


def main():
    log = F.Log("f4_gate", os.path.abspath(__file__), CRITERIA, extra_files=[os.path.join(F.REPO, "tests", "f4_orekit.js")])
    W = F.WORK + "/f4"
    os.makedirs(W, exist_ok=True)
    m1f, nodes = F.BUILD + "/m1f_O2.exe", F.BUILD + "/m1nodes.exe"
    log.w("# m1f_O2.exe sha256 %s; m1nodes.exe sha256 %s; table %s sha256 %s" % (F.sha256(m1f), F.sha256(nodes), TABLE, F.sha256(TABLE)))
    gdir = gfc_copy(log)
    rng = random.Random(0xF4)
    mu = 3.986004415e14
    days = list(range(61330, 61359, 4))
    log.check(len(days) == 8, "8 epochs: %s" % days)
    st = []
    for i in range(1000):
        t = float(F.utc_to_tdb(days[i // 125], 0))
        r = 6378136.3 + 3.0e5 + 5.0e5 * rng.random()
        z = 2 * rng.random() - 1
        ph = 2 * math.pi * rng.random()
        s = math.sqrt(1 - z * z)
        p = [r * s * math.cos(ph), r * s * math.sin(ph), r * z]
        z2 = 2 * rng.random() - 1
        ph2 = 2 * math.pi * rng.random()
        s2 = math.sqrt(1 - z2 * z2)
        u = [s2 * math.cos(ph2), s2 * math.sin(ph2), z2]
        dd = sum(a * b for a, b in zip(u, p)) / r
        u = [a - dd * b / r for a, b in zip(u, p)]
        un = math.sqrt(sum(a * a for a in u))
        v = math.sqrt(mu / r) * (0.99 + 0.02 * rng.random())
        vel = [v * a / un for a in u]
        area, mass, cd = 0.5 + 19.5 * rng.random(), 50 + 1950 * rng.random(), 2.0 + 0.4 * rng.random()
        st.append((t, p, vel, area, mass, cd, cd * area / (2 * mass)))
    with open(W + "/t.txt", "w", newline="\n") as f:
        for s in st:
            f.write(float.hex(s[0]) + "\n")
    F.run([nodes, "times", W + "/t.txt", W + "/times.txt"], log)
    tai = [float.fromhex(ln.split()[1]) for ln in open(W + "/times.txt") if not ln.startswith("#")]
    with open(W + "/ours_in.txt", "w", newline="\n") as f, open(W + "/ore_in.txt", "w", newline="\n") as g:
        for i, s in enumerate(st):
            f.write("%d %s %s %s %s\n" % (i, float.hex(s[0]), " ".join(float.hex(x) for x in s[1]), " ".join(float.hex(x) for x in s[2]), float.hex(s[6])))
            g.write("%d %s %s %s %s %s %s\n" % (i, float.hex(tai[i]), " ".join(float.hex(x) for x in s[1]), " ".join(float.hex(x) for x in s[2]),
                                                 float.hex(s[3]), float.hex(s[4]), float.hex(s[5])))
    F.orekit(os.path.join(F.REPO, "tests", "f4_orekit.js"), [W + "/ore_in.txt", W + "/ore.txt", F.DATA + "/orekit", gdir], log, cpu_label="f4_orekit")
    for h in open(W + "/ore.txt"):
        if h.startswith("# f4_orekit"):
            log.w("# " + h.strip())
    ore = [[float.fromhex(x) for x in ln.split()[1:]] for ln in open(W + "/ore.txt") if not ln.startswith("#")]
    log.check(len(ore) == 1000, "Orekit gave 1000 states")
    # the planted table (C2)
    ptab = F.DATA + "/tables/frame_plant_xp500uas.bin"
    if not os.path.exists(ptab):
        F.run([nodes, "build", "-1024", "256", "11484", ptab, "--plant-xp", repr(2.42406840554768e-9), "--note", "F4 C2: xp + 500 uas"], log, cpu_label="node_table_plant")
    log.w("# C2 table %s sha256 %s" % (ptab, F.sha256(ptab)))
    res = {}
    for kind in ("native64", "cft64"):
        for tag, extra, tab in (("plain", [], TABLE), ("bc", ["--plant-bc", "0.01"], TABLE), ("tilt", [], ptab)):
            o = W + "/ours_%s_%s.txt" % (kind, tag)
            F.run([m1f, "f4", kind, tab, W + "/ours_in.txt", o] + extra, log, cpu_label="f4_%s_%s" % (kind, tag))
            res[(kind, tag)] = [ln.split()[1:] for ln in open(o) if not ln.startswith("#")]
    for kind in ("native64", "cft64"):
        for tag in ("plain", "bc", "tilt"):
            dg, dd, nan = [], [], 0
            for a, b in zip(res[(kind, tag)], ore):
                va = [F.value(x, 64) for x in a]
                nan += sum(1 for x in va if x is None)
                g = [float(va[i] - Fraction(b[i])) for i in range(3)]
                dg.append(math.sqrt(sum(x * x for x in g)))
                d = [float(va[3 + i] - Fraction(b[3 + i])) for i in range(3)]
                dd.append(math.sqrt(sum(x * x for x in d)) / math.sqrt(sum(x * x for x in b[3:6])))
            log.w("# %s %s: gravity |da| max %.3e m/s^2 (median %.3e); drag relative max %.3e (median %.3e); NaN %d" %
                  (kind, tag, max(dg), sorted(dg)[500], max(dd), sorted(dd)[500], nan))
            if tag == "plain":
                log.check(nan == 0 and max(dg) <= 3.1e-12, "D1 %s gravity within 3.1e-12 m/s^2 at all 1000 states (max %.3e)" % (kind, max(dg)))
                log.check(nan == 0 and max(dd) <= 1e-7, "D2 %s drag within 1e-7 relative at all 1000 states (max %.3e)" % (kind, max(dd)))
            elif tag == "bc":
                log.check(min(dd) > 1e-7, "C1 %s FAILS D2 as specified at every state (min %.3e, max %.3e)" % (kind, min(dd), max(dd)))
            else:
                log.check(max(dg) > 3.1e-12, "C2 %s FAILS D1 as specified (max %.3e m/s^2 = %.1f x the tolerance)" % (kind, max(dg), max(dg) / 3.1e-12))
    same = sum(1 for a, b in zip(res[("native64", "plain")], res[("cft64", "plain")]) if all(F.G.same(x, y, 64) for x, y in zip(a, b)))
    log.w("REPORTED native64 against cft64: %d of 1000 states bit for bit in all six columns" % same)
    wo = [math.sqrt(sum(x * x for x in b[6:9])) for b in ore]
    log.w("# REPORTED Orekit's |omega| (ITRF in GCRF, as its transform gives it): %.12e to %.12e rad/s" % (min(wo), max(wo)))
    return log.close()


if __name__ == "__main__":
    sys.exit(main())
