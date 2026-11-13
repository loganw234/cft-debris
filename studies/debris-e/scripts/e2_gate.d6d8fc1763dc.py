# e2_gate.py - cft-debris M1, gate E2: native against cft, whole rk4 runs.
# cft-debris, MIT licence (see LICENSE at the repository root). Written by
# DEBRIS-E, 2026-11-13.
#
#   python -I -B tests/e2_gate.py
#
# The run: tests/m1run.c's eight lanes (near-circular LEO orbits 350 to 700 km
# up, inclinations 0.1 to 98.6 degrees, periods 5,492 to 5,926 s), the whole
# force model (central term, EIGEN-6C4 degrees 2 to 20 in a uniformly turning
# Earth, the Sun and the Moon from DE421, the 28-band exponential atmosphere,
# radiation pressure with a conical shadow), rk4 at 60 s for 100 steps
# (6,000 s, at least one orbit of every lane), epoch 2008-07-03 00:00 TDB.
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gatelib as g  # noqa: E402

CRITERIA = """
G1 THE GATE: in the control configuration (the native kinds route exp, sin, cos, asin and acos to libcft's
   correctly rounded host functions), native64's state equals cft64's bit for bit at every step (100 steps,
   8 lanes, 6 components, the NaN rule), and native32's equals cft32's.
M1 MEASUREMENT (no pass condition): with the C library's transcendentals, native against cft at each step:
   the lanes that differ, and the largest position difference |dr| (m) - how the difference grows.
C1 NEGATIVE CONTROL: native64 (control configuration) with one ulp planted in lane 3's x (one step up)
   against cft64 unplanted: lane 3 differs at the start and at every step from the first on, and every
   other lane is identical at every step. The same at native32 against cft32.
"""
STEPS, H, PLANT = 100, "60", 3
W = os.path.join(g.WORK, "e2")
os.makedirs(W, exist_ok=True)


def traj(log, kind, tag, extra):
    out = os.path.join(W, "%s_%s.txt" % (kind, tag))
    g.run([g.exe("O2"), "traj", kind, STEPS, H, out] + extra, log)
    rows, head = g.read_rows(out, "S")
    st = {}
    for r in rows:
        st[(int(r[1]), int(r[3]))] = r[4:10]
    return st


def compare(a, b, nb, log=None, label=""):
    """per step: (lanes differing, max |dr| m); every lane-step compared"""
    steps = sorted(set(k[0] for k in a))
    assert steps == list(range(STEPS + 1)) and set(a) == set(b)
    per = []
    for s in steps:
        nd, dr = 0, 0.0
        lanes = []
        for l in range(8):
            ha, hb = a[(s, l)], b[(s, l)]
            if not all(g.same(x, y, nb) for x, y in zip(ha, hb)):
                nd += 1
                lanes.append(l)
                d = [float(g.value(x, nb) - g.value(y, nb)) for x, y in zip(ha[:3], hb[:3])]
                dr = max(dr, sum(t * t for t in d) ** 0.5)
        per.append((s, nd, dr, lanes))
    return per


def main():
    log = g.Log("e2_gate", os.path.abspath(__file__), CRITERIA)
    log.w("# run: %d steps of %s s, 8 lanes, degree 20 and every force" % (STEPS, H))
    ok_all = True
    for a, b in (("native64", "cft64"), ("native32", "cft32")):
        nb = g.FMT[a]
        tb = traj(log, b, "plain", [])
        tcr = traj(log, a, "cr", ["--cr"])
        per = compare(tcr, tb, nb)
        bad = [(s, nd) for s, nd, dr, _ in per if nd]
        log.check(not bad, "G1 %s (control) = %s bit for bit at all %d steps x 8 lanes x 6 components%s"
                  % (a, b, STEPS + 1, "" if not bad else "; first differing step %s" % (bad[0],)))
        tl = traj(log, a, "libm", [])
        per = compare(tl, tb, nb)
        first = next((s for s, nd, _, _ in per if nd), None)
        log.w("MEASURED M1 %s (C library) against %s: first differing step %s" % (a, b, first))
        for s, nd, dr, lanes in per:
            if s % 10 == 0 or (first is not None and s in (first, first + 1, first + 2)):
                log.w("#   step %3d (t = %5d s): %d lanes differ, max |dr| %.3e m" % (s, s * int(H), nd, dr))
        tp = traj(log, a, "plant", ["--cr", "--plant", str(PLANT)])
        per = compare(tp, tb, nb)
        lane3 = all(PLANT in lanes for s, nd, dr, lanes in per)
        others = all(lanes == [PLANT] for s, nd, dr, lanes in per)
        log.w("# control %s: lanes differing per step: %s" % (a, sorted(set(tuple(l) for _, _, _, l in per))))
        log.w("# control %s: |dr| of lane %d at steps 0, 1, 10, 100: %s" %
              (a, PLANT, ", ".join("%.3e" % per[s][2] for s in (0, 1, 10, 100))))
        log.check(lane3 and others, "C1 control %s: one ulp planted in lane %d breaks bit-identity in that lane "
                  "alone, from the start and at every step" % (a, PLANT))
    return log.close()


if __name__ == "__main__":
    sys.exit(main())
