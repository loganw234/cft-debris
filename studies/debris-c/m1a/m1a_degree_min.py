#!/usr/bin/env python3
"""DEBRIS-C, M1a: COMPUTED check behind the study's sentence "each degree's own
RMS signal at the orbit's largest radius exceeds the tolerance". The same
formula and inputs as m1a_control_degree.py, which printed only a sample of
degrees; this prints the smallest per-degree signal over n = 2..180.

  python -I -B m1a_degree_min.py

ASSERTED: the smallest per-degree RMS signal at the largest radius is >= TOL.
"""
import math

GFC = "C:/Users/logan/source/repos/cft-debris-downloads/EIGEN6-C4.gfc/EIGEN6-C4.gfc"
ORB = "C:/Users/logan/source/repos/cft-debris-downloads/00orbit_itrf.txt/00orbit_itrf.txt"
TOL = 1e-11


def main():
    gm = R = None
    sig2 = [0.0] * 181
    seen = set()
    head = True
    for ln in open(GFC):
        t = ln.split()
        if head:
            if t and t[0] == "earth_gravity_constant":
                gm = float(t[1])
            if t and t[0] == "radius":
                R = float(t[1])
            if t and t[0].startswith("end_of_head"):
                head = False
            continue
        if not t or t[0] != "gfc":
            continue
        n, m = int(t[1]), int(t[2])
        if (n, m) in seen:
            continue
        seen.add((n, m))
        sig2[n] += float(t[3]) ** 2 + float(t[4]) ** 2
    rmax = max(math.sqrt(sum(float(x) ** 2 for x in ln.split()[1:4]))
               for ln in open(ORB) if len(ln.split()) == 10 and not ln.startswith("#"))
    sig = {n: (gm / rmax ** 2) * (R / rmax) ** n * math.sqrt((n + 1) * (2 * n + 1) * sig2[n]) for n in range(2, 181)}
    nmin = min(sig, key=sig.get)
    print("# largest radius %.1f m; smallest per-degree RMS signal over n = 2..180: degree %d, %.3e m/s^2 (TOL %.0e)"
          % (rmax, nmin, sig[nmin], TOL))
    low = sorted(sig, key=sig.get)[:5]
    print("# the five smallest: " + ", ".join("n %d %.3e" % (n, sig[n]) for n in low))
    assert sig[nmin] >= TOL
    print("# COMPUTED PASS: every degree's own RMS signal at the largest radius is >= TOL")


if __name__ == "__main__":
    main()
