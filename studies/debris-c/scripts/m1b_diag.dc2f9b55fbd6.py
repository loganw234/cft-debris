#!/usr/bin/env python3
"""DEBRIS-C, M1b diagnosis, written AFTER m1b_check.001.log failed criteria 1
and 2. It asserts nothing and changes no criterion: it only describes the
failures.
- criterion 1: for each failing point, its value, |d| and |d| in units of
  the ulp of the value;
- criterion 2: Orekit's failures grouped by target, centre and coordinate,
  with the largest |d| of each group, and |d| against the date.
It loads m1b_check.py by path (importlib), so it uses the identical reader.

  python -I -B m1b_diag.py
"""
import collections
import importlib.util
import math

spec = importlib.util.spec_from_file_location(
    "m1b_check", "C:/Users/logan/source/repos/cft-debris/studies/debris-c/m1b/m1b_check.py")
M = importlib.util.module_from_spec(spec)
spec.loader.exec_module(M)


def main():
    de = M.DE421()
    rows = M.read_testpo()
    print("# criterion 1 failures (custom reader), |d| >= %.0e:" % M.TOL_TESTPO)
    worst_ulp = 0.0
    for (i, jed, t, c, x, val) in rows:
        if not (de.ss[0] <= jed <= de.ss[1]):
            continue
        got = de.pleph(jed, t, c)[x - 1]
        d = abs(got - val)
        u = math.ulp(val)
        worst_ulp = max(worst_ulp, d / u if u > 0 else 0.0)
        if d >= M.TOL_TESTPO:
            print("  line %4d JED %.1f t %2d c %2d x %d value %.6f |d| %.3e = %.2f ulp(value)" % (i, jed, t, c, x, val, d, d / u))
    print("# largest |d| over all custom points, in ulps of the value: %.2f" % worst_ulp)

    bylin = {r[0]: r for r in rows}
    aum = de.au * 1000.0
    groups = collections.defaultdict(lambda: [0, 0, 0.0])
    bydate = collections.defaultdict(float)
    for ln in open(M.OUT + "orekit_testpo.txt"):
        t = ln.split()
        (_, jed, tg, ct, x, val) = bylin[int(t[0])]
        p = [float.fromhex(z) / aum for z in t[1:4]]
        v = [float.fromhex(z) * 86400.0 / aum for z in t[4:7]]
        got = (p + v)[x - 1]
        d = abs(got - val)
        own = de.pleph(jed, tg, ct)[x - 1]
        key = (tg, ct, "pos" if x <= 3 else "vel")
        g = groups[key]
        g[0] += 1
        g[1] += d >= M.TOL_TESTPO
        g[2] = max(g[2], d)
        bydate[int((jed - 2451545.0) / 3652.5)] = max(bydate[int((jed - 2451545.0) / 3652.5)], d if x <= 3 else 0.0)
        if d >= 3e-12:
            print("  Orekit line %4d JED %.1f t %2d c %2d x %d |d| vs testpo %.3e AU; Orekit - custom %.3e"
                  % (int(t[0]), jed, tg, ct, x, d, got - own))
    print("# Orekit vs testpo by (target, centre, kind): points, failures, max |d|")
    for k in sorted(groups):
        g = groups[k]
        print("  t %2d c %2d %s: %3d points, %3d fail, max %.2e" % (k[0], k[1], k[2], g[0], g[1], g[2]))
    print("# Orekit vs testpo, max position |d| by decade from J2000 (index = decades):")
    for k in sorted(bydate):
        print("  decade %3d: %.2e AU" % (k, bydate[k]))


if __name__ == "__main__":
    main()
