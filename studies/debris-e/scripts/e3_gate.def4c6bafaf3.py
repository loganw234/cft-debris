# e3_gate.py - cft-debris M1, gate E3: the precision ladder. E2's run (eight
# LEO lanes, the whole model at degree 20, rk4 at 60 s for 100 steps = 6,000 s,
# one orbit of every lane) at cft32, cft64, cft128 and cft256.
# cft-debris, MIT licence (see LICENSE at the repository root). Written by
# DEBRIS-E, 2026-11-13.
#
#   python -I -B tests/e3_gate.py
import os
import sys
from fractions import Fraction

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gatelib as g  # noqa: E402

CRITERIA = """
The segment boundaries: every 20 steps (t = 0, 1200, 2400, 3600, 4800, 6000 s).
L1 THE BOUND, stated before the data: B = N_ops x u128 x R x G, where
   u128 = 2^-113 (binary128's unit roundoff);
   N_ops = the rounded operations one lane's trajectory performs, from the run's own lane-op counter divided
           by the 8 lanes (planned: about 3.05e6, from a 5-step trial at 30.5k a lane-step; asserted within 10%);
   R = 7.1e6 m, the largest position magnitude of the eight lanes (apogees under 7,080 km);
   G = 30, the growth of a state error over one orbit (linearised Kepler: 1 + 3 n t with n t <= 6.9 over
       6,000 s gives 22, rounded up).
   It treats every rounding as a worst-case-aligned relative error u of the state, amplified by G: an
   ESTIMATE-based bound (BELIEVED generous), not a rigorous one. The op counts at cft128 and cft256 must
   equal cft64's (one source, the same operations).
L2 max over lanes and boundaries of |r(cft128) - r(cft256)| <= B (position, Euclidean norm, m).
L3 NEGATIVE CONTROL: cft128 with one intermediate of the force model (the central term's factor -GM/r^3)
   rounded to binary64 and back at every evaluation (--round64) must break B: max |r - r(cft256)| > B.
REPORTED: each kind's max over lanes of |dr| (m) and |dv| (m/s) from cft256 at every boundary; binary64's
   growth against cft128 (|r(cft64) - r(cft128)| at each boundary), beside DEBRIS-D's 1.2e-6 to 1.3e-5 m an
   object-day (its definition: |fp64 - long double| of one object's final position after one object-day,
   rk4 at 60 to 0.9375 s, degree 20 with drag, no Sun, Moon or radiation pressure).
"""
STEPS, H, SEG = 100, "60", 20
U128 = Fraction(1, 2 ** 113)
R, G = Fraction(71, 10) * 10 ** 6, 30
NOPS_PLAN = 3.05e6
W = os.path.join(g.WORK, "e3")
os.makedirs(W, exist_ok=True)


def traj(log, kind, tag, extra):
    out = os.path.join(W, "%s_%s.txt" % (kind, tag))
    g.run([g.exe("O2"), "traj", kind, STEPS, H, out] + extra, log)
    rows, head = g.read_rows(out, "S")
    st = {(int(r[1]), int(r[3])): r[4:10] for r in rows}
    ops = [h for h in head if h.startswith("# lane-ops")][0]
    tot = sum(int(t.split("=")[1]) for t in ops.split()[2:])
    return st, tot


def diffs(a, nba, b, nbb, s):
    """max over lanes of |dr|, |dv| at step s, exact then rounded to float"""
    mr = mv = Fraction(0)
    for l in range(8):
        va = [g.value(h, nba) for h in a[(s, l)]]
        vb = [g.value(h, nbb) for h in b[(s, l)]]
        dr = sum((x - y) ** 2 for x, y in zip(va[:3], vb[:3]))
        dv = sum((x - y) ** 2 for x, y in zip(va[3:], vb[3:]))
        mr, mv = max(mr, dr), max(mv, dv)
    return float(mr) ** 0.5, float(mv) ** 0.5


def main():
    log = g.Log("e3_gate", os.path.abspath(__file__), CRITERIA)
    runs = {}
    for kind in ("cft256", "cft128", "cft64", "cft32"):
        runs[kind] = traj(log, kind, "plain", [])
    ctl = traj(log, "cft128", "round64", ["--round64"])
    nops = {k: v[1] for k, v in runs.items()}
    log.w("# lane-ops (all lanes, all steps): %s; control %d" % (nops, ctl[1]))
    n_lane = nops["cft64"] / 8.0
    log.check(abs(n_lane - NOPS_PLAN) <= 0.1 * NOPS_PLAN, "L1 N_ops = %.4e a lane, within 10%% of the planned %.3e"
              % (n_lane, NOPS_PLAN))
    log.check(nops["cft128"] == nops["cft64"] == nops["cft256"], "L1 the same operation count at cft64, cft128, cft256")
    B = Fraction(nops["cft64"], 8) * U128 * R * G
    log.w("# B = %.4e x 2^-113 x 7.1e6 m x 30 = %.3e m" % (n_lane, float(B)))
    ref = runs["cft256"][0]
    worst128 = Fraction(0)
    for s in range(0, STEPS + 1, SEG):
        line = []
        for kind in ("cft128", "cft64", "cft32"):
            dr, dv = diffs(runs[kind][0], g.FMT[kind], ref, 256, s)
            line.append("%s |dr| %.3e m |dv| %.3e m/s" % (kind, dr, dv))
            if kind == "cft128":
                worst128 = max(worst128, Fraction(dr))
        log.w("# boundary t = %5d s: %s" % (s * int(H), "; ".join(line)))
    log.check(worst128 <= B, "L2 max |r(cft128) - r(cft256)| = %.3e m <= B = %.3e m (ratio %.2e)"
              % (float(worst128), float(B), float(worst128 / B) if B else 0))
    worst_ctl = Fraction(0)
    for s in range(0, STEPS + 1, SEG):
        dr, dv = diffs(ctl[0], 128, ref, 256, s)
        worst_ctl = max(worst_ctl, Fraction(dr))
        log.w("# control boundary t = %5d s: |dr| %.3e m |dv| %.3e m/s" % (s * int(H), dr, dv))
    log.check(worst_ctl > B, "L3 control: cft128 with the central factor rounded to binary64 is %.3e m from "
              "cft256, beyond B = %.3e m (%.2e B)" % (float(worst_ctl), float(B), float(worst_ctl / B)))
    for s in range(0, STEPS + 1, SEG):
        dr, dv = diffs(runs["cft64"][0], 64, runs["cft128"][0], 128, s)
        log.w("MEASURED binary64 against binary128 at t = %5d s: max over 8 lanes |dr| %.3e m, |dv| %.3e m/s"
              % (s * int(H), dr, dv))
    return log.close()


if __name__ == "__main__":
    sys.exit(main())
