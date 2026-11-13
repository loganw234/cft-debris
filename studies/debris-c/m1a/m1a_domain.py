#!/usr/bin/env python3
"""DEBRIS-C, M1a: which degrees the comparison actually tests, measured.
Written after m1a_compare.001.log; it changes no M1a criterion.

  python -I -B m1a_domain.py

EXPECTATIONS (stated before these runs, asserted):
1. Version 2 of the kernel, unplanted, reproduces version 1's output bit for
   bit (c_v2_2_180.txt = c_O2_2_180.txt).
2. Degree 180 removed (2..179): the 1e-11 comparison REPORTS it. Basis:
   m1a_control_degree.001.log puts degree 180's own RMS signal at 3.2e-11
   (largest radius) to 5.2e-11 (mean radius) m/s^2, above TOL.
3. One degree-180 coefficient changed, C-bar(180,90) + 3.09e-10 (Kaula's
   per-coefficient size at n = 180): the 1e-11 comparison does NOT report it
   (plan-verifier-C COMPUTED about 1.5e-12 m/s^2 for one changed degree-180
   coefficient), but the measured residual rises at least 10 times above the
   unplanted maximum (2.278e-15, m1a_compare.001.log).
"""
import hashlib
import math
import sys

D = "C:/Users/logan/source/repos/cft-debris-downloads/"
LASSER = D + "02gravityfield_itrf.txt/02gravityfield_itrf.txt"
OUT = "C:/Users/logan/source/repos/cft-debris/studies/debris-c/m1a/out/"
TOL = 1e-11
UNPLANTED_MAX = 2.278e-15


def rows_hex(p):
    return [[float(t[0])] + [float.fromhex(z) for z in t[1:4]] for t in (ln.split() for ln in open(p))]


def rows_lasser(p):
    out = []
    for ln in open(p):
        t = ln.split()
        if len(t) == 4 and not ln.startswith("#"):
            try:
                out.append([float(z) for z in t])
            except ValueError:
                pass
    return out


def maxd(a, b):
    m, s2 = 0.0, 0.0
    for x, y in zip(a, b):
        assert abs(x[0] - y[0]) < 1e-9
        n = math.sqrt(sum((x[q] - y[q]) ** 2 for q in (1, 2, 3)))
        m = max(m, n)
        s2 += n * n
    return m, math.sqrt(s2 / len(a))


def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def main():
    ok = True
    p1 = sha(OUT + "c_v2_2_180.txt") == sha(OUT + "c_O2_2_180.txt")
    print("%s 1. version 2 unplanted reproduces version 1 bit for bit" % ("PASS" if p1 else "FAIL"))
    ok &= p1
    L = rows_lasser(LASSER)
    m179, r179 = maxd(rows_hex(OUT + "c_v2_2_179.txt"), L)
    p2 = m179 > TOL
    print("%s 2. degree 180 removed: max |da| %.3e, RMS %.3e m/s^2 vs TOL %.0e: %s"
          % ("PASS" if p2 else "FAIL", m179, r179, TOL, "reported" if p2 else "NOT reported"))
    ok &= p2
    mc, rc = maxd(rows_hex(OUT + "c_v2_2_180_coef180_90.txt"), L)
    p3 = mc < TOL and mc >= 10 * UNPLANTED_MAX
    print("%s 3. C(180,90) + 3.09e-10: max |da| %.3e, RMS %.3e m/s^2: %s by the 1e-11 criterion; %.0f x the unplanted maximum"
          % ("PASS" if p3 else "FAIL", mc, rc, "not reported" if mc < TOL else "REPORTED", mc / UNPLANTED_MAX))
    ok &= p3
    print("# M1a domain %s" % ("PASS" if ok else "FAIL"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
