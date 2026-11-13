#!/usr/bin/env python3
"""DEBRIS-C, M1b diagnosis 2, written AFTER m1b_check.001.log failed
criterion 2 (Orekit vs testpo.421). Asserts nothing; changes no criterion.

Is Orekit's difference a time offset? For every testpo point Orekit wrote,
it takes Orekit's full position vector minus the custom reader's (which
agrees with testpo.421 to 1.4e-14 AU for bodies), splits it into the part
along the relative velocity and the part across it, and prints the implied
time offset dt = (dp . v) / |v|^2, with where the date falls inside the
target's and the centre's Chebyshev sub-intervals.

  python -I -B m1b_diag2.py
"""
import importlib.util
import math

spec = importlib.util.spec_from_file_location(
    "m1b_check", "C:/Users/logan/source/repos/cft-debris/studies/debris-c/m1b/m1b_check.py")
M = importlib.util.module_from_spec(spec)
spec.loader.exec_module(M)

IDX = {1: 0, 2: 1, 3: 2, 4: 3, 5: 4, 6: 5, 7: 6, 8: 7, 9: 8, 10: 9, 11: 10, 13: 2}


def frac_in_sub(de, body, jed):
    if body == 12:
        return float("nan")
    off, nc, ns = de.ipt[IDX[body]]
    dt = de.ss[2] / ns
    return ((jed - de.ss[0]) % dt) / dt


def main():
    de = M.DE421()
    rows = M.read_testpo()
    bylin = {r[0]: r for r in rows}
    aum = de.au * 1000.0
    res = []
    for ln in open(M.OUT + "orekit_testpo.txt"):
        t = ln.split()
        (_, jed, tg, ct, x, val) = bylin[int(t[0])]
        po = [float.fromhex(z) for z in t[1:4]]
        six = de.pleph(jed, tg, ct)
        pc = [six[q] * aum for q in range(3)]
        vc = [six[3 + q] * aum / 86400.0 for q in range(3)]
        dp = [po[q] - pc[q] for q in range(3)]
        v2 = sum(z * z for z in vc)
        dt = sum(dp[q] * vc[q] for q in range(3)) / v2 if v2 > 0 else 0.0
        along = [dt * vc[q] for q in range(3)]
        across = math.sqrt(sum((dp[q] - along[q]) ** 2 for q in range(3)))
        res.append((math.sqrt(sum(z * z for z in dp)), across, dt, jed, tg, ct, math.sqrt(v2)))
    res.sort(reverse=True)
    print("# Orekit - custom, full position vectors (m): |dp|, across-velocity part, implied dt (s), |v| (m/s)")
    for r in res[:25]:
        print("  |dp| %.3f m, across %.3e m, dt %+.3e s, JED %.1f, t %2d c %2d, |v| %.0f m/s, sub-interval fraction t %.3f c %.3f"
              % (r[0], r[1], r[2], r[3], r[4], r[5], r[6], frac_in_sub(de, r[4], r[3]), frac_in_sub(de, r[5], r[3])))
    big = [r for r in res if r[0] > 0.1]
    if big:
        fr = max(r[1] / r[0] for r in big)
        print("# over the %d points with |dp| > 0.1 m: largest across/|dp| = %.3e; implied |dt| from %.2e to %.2e s"
              % (len(big), fr, min(abs(r[2]) for r in big), max(abs(r[2]) for r in big)))


if __name__ == "__main__":
    main()
