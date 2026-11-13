"""q1_objectday.py - DEBRIS-D, Q1 (cft-debris, MIT): COMPUTED operation counts
for one LEO object-day, from labelled inputs; no criterion is asserted beyond
the arithmetic's own consistency (each total is the sum of its parts).

Inputs (labels as in the study):
  per evaluation, MEASURED by count_ops (logs/q1_counts.001.log): gravity
    degree 20 (DEBRIS-C's kernel) 8,160 FMA-class, 3 div, 1 sqrt; Sun and Moon
    by Chebyshev 355 FMA-class, 7 div; their point masses 54, 4 div, 4 sqrt;
    the interpolated frame 339, 12 div, 1 sqrt, 7 sin, 7 cos, 1 atan, 1 atan2,
    2 fmod; exponential drag 23, 1 div, 2 sqrt, 1 exp; radiation pressure,
    sunlit, 28, 5 div, 2 sqrt, 2 asin, 1 acos.
  evaluations an object-day, MEASURED (Q4, logs/q4_integrators.002.log): IAS15
    16,449 (559 steps; real EIGEN-6C4 degree 20 with drag, one LEO orbit);
    rk4 23,040 at 15 s and 11,520 at 30 s.
  the integrators' own arithmetic: rk4, 7 FMA-class a state component a step
    (READ, the template, LANGUAGE.md:1185-1197), 6 components; IAS15, READ
    from cft-rebound's ias15_cft.c at de376d8 (REBOUND's division form): 588
    FMA-class and 133 divisions a coordinate an iteration with a velocity-
    dependent force, 3 coordinates, (16,449 - 559) / 7 = 2,270 iterations.
  a lockstep batch (every object on the same fixed step) shares the Sun,
    Moon and frame between its lanes: they are counted once a stage for the
    whole batch, not an object; IAS15's per-object steps cannot share them.
usage: python -I -B q1_objectday.py
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tools"))
import dd  # noqa: E402

PARTS = {  # name: dict of class -> count per evaluation
    "gravity d20": {"fma": 8160, "div": 3, "sqrt": 1},
    "sun+moon chebyshev": {"fma": 355, "div": 7},
    "sun+moon point masses": {"fma": 54, "div": 4, "sqrt": 4},
    "frame interpolated": {"fma": 339, "div": 12, "sqrt": 1, "sin": 7, "cos": 7, "atan": 1, "atan2": 1, "fmod": 2},
    "drag exponential": {"fma": 23, "div": 1, "sqrt": 2, "exp": 1},
    "srp conical sunlit": {"fma": 28, "div": 5, "sqrt": 2, "asin": 2, "acos": 1},
}
SHARED = ("sun+moon chebyshev", "frame interpolated")
CLASSES = ["fma", "div", "sqrt", "exp", "sin", "cos", "asin", "acos", "atan", "atan2", "fmod"]


def total(parts, n, extra=None):
    t = {c: 0 for c in CLASSES}
    for p in parts:
        for c, v in PARTS[p].items():
            t[c] += v * n
    for c, v in (extra or {}).items():
        t[c] += v
    return t


def main():
    log = dd.Log(__file__, "q1_objectday")
    log.criteria("none asserted: COMPUTED arithmetic from the labelled inputs in the docstring")
    allp = list(PARTS)
    per_obj = [p for p in allp if p not in SHARED]
    ev = total(allp, 1)
    log.w("one evaluation, every part: " + ", ".join("%s %d" % (c, ev[c]) for c in CLASSES if ev[c]))
    it = (16449 - 559) / 7
    ias_own = {"fma": round(588 * 3 * it), "div": round(133 * 3 * it)}
    rows = [("IAS15 (16,449 evaluations; per object, nothing shared)", total(allp, 16449, ias_own)),
            ("rk4 15 s (23,040 evaluations), per object, Sun/Moon/frame shared by the batch",
             total(per_obj, 23040, {"fma": 7 * 6 * 5760})),
            ("rk4 30 s (11,520 evaluations), per object, shared as above", total(per_obj, 11520, {"fma": 7 * 6 * 2880})),
            ("rk4 15 s, if nothing were shared", total(allp, 23040, {"fma": 7 * 6 * 5760}))]
    log.w("IAS15's own arithmetic an object-day (REBOUND's division form): %d FMA-class, %d divisions (%.0f iterations)"
          % (ias_own["fma"], ias_own["div"], it))
    for name, t in rows:
        log.w("OBJECT-DAY %s: " % name + ", ".join("%s %.4g" % (c, t[c]) for c in CLASSES if t[c]))
    rc = log.close()
    sys.exit(1 if rc else 0)


if __name__ == "__main__":
    main()
