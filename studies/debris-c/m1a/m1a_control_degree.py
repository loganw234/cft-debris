#!/usr/bin/env python3
"""DEBRIS-C, M1a: COMPUTED before any comparison is run - the expected size
of the gravity signal along Lasser et al.'s orbit, by degree, and the
truncation degree D for the planted-error control.

  python -I -B m1a_control_degree.py

Inputs (labelled): the coefficient file (the download, read only), the TRF
orbit's radii (00orbit_itrf.txt), and Kaula's rule 1e-5/n^2 per normalised
coefficient for comparison.

Formula: for degree n, the mean over a sphere of radius r of |a_n|^2 is
  (GM/r^2)^2 (R/r)^(2n) (n+1)(2n+1) sigma_n^2,  sigma_n^2 = sum_m (C^2 + S^2)
(radial part (n+1)^2, horizontal part n(n+1), 4-pi-normalised harmonics), and
different degrees are orthogonal over the sphere, so truncating at D omits
an RMS of sqrt(sum_{n>D} ...).

CRITERION for the control (from the brief): the omitted degrees' expected
signal is at least 10 times the comparison's tolerance, TOL = 1e-11 m/s^2.
This script picks D as the largest degree whose omitted RMS signal, at the
orbit's largest radius over the day (where the signal is weakest), is at
least 10 * TOL, and asserts that choice. The max over the day is expected
to be a few times the RMS, so the RMS is the conservative figure.
"""
import math

GFC = "C:/Users/logan/source/repos/cft-debris-downloads/EIGEN6-C4.gfc/EIGEN6-C4.gfc"
ORB = "C:/Users/logan/source/repos/cft-debris-downloads/00orbit_itrf.txt/00orbit_itrf.txt"
TOL = 1e-11
NMAX = 180


def main():
    gm = R = None
    sig2 = [0.0] * (NMAX + 1)
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
            continue  # the duplicated (0,0) line
        seen.add((n, m))
        sig2[n] += float(t[3]) ** 2 + float(t[4]) ** 2
    radii = []
    for ln in open(ORB):
        t = ln.split()
        if len(t) == 10 and not ln.startswith("#"):
            radii.append(math.sqrt(sum(float(x) ** 2 for x in t[1:4])))
    rmin, rmax, rmean = min(radii), max(radii), sum(radii) / len(radii)
    print("# GM %.10e, R %.10e, epochs %d, radius min %.1f mean %.1f max %.1f m (altitude over R: %.1f to %.1f km)"
          % (gm, R, len(radii), rmin, rmean, rmax, (rmin - R) / 1e3, (rmax - R) / 1e3))
    print("# tolerance TOL = %.0e m/s^2; control needs omitted RMS >= %.0e" % (TOL, 10 * TOL))

    def deg_rms(n, r, kaula=False):
        s2 = (2 * n + 1) * (1e-5 / n ** 2) ** 2 if kaula else sig2[n]
        return (gm / r ** 2) * (R / r) ** n * math.sqrt((n + 1) * (2 * n + 1) * s2)

    def omitted(D, r, kaula=False):
        return math.sqrt(sum(deg_rms(n, r, kaula) ** 2 for n in range(D + 1, NMAX + 1)))

    print("# per-degree RMS signal |a_n| (m/s^2) at r = mean / max radius; Kaula at mean")
    for n in (2, 10, 50, 100, 120, 140, 150, 160, 170, 175, 178, 179, 180):
        print("n %3d  file: %.3e / %.3e   Kaula: %.3e" % (n, deg_rms(n, rmean), deg_rms(n, rmax), deg_rms(n, rmean, True)))
    print("# omitted RMS signal for truncation at D (degrees D+1..180), at mean / max radius; Kaula at mean")
    for D in (150, 155, 160, 165, 168, 170, 172, 175, 178, 179):
        print("D %3d  file: %.3e / %.3e   Kaula: %.3e   ratio to TOL at max radius: %.1f"
              % (D, omitted(D, rmean), omitted(D, rmax), omitted(D, rmean, True), omitted(D, rmax) / TOL))
    D = max(d for d in range(2, NMAX) if omitted(d, rmax) >= 10 * TOL)
    print("# per-degree: the highest degree whose own RMS signal at the max radius is >= TOL: %d"
          % max(n for n in range(2, NMAX + 1) if deg_rms(n, rmax) >= TOL))
    print("# CHOSEN control truncation D = %d: omitted RMS %.3e m/s^2 at max radius = %.1f x TOL (needs >= 10)"
          % (D, omitted(D, rmax), omitted(D, rmax) / TOL))
    assert omitted(D, rmax) >= 10 * TOL and omitted(D + 1, rmax) < 10 * TOL
    print("# D = %d also omits %.3e at the mean radius" % (D, omitted(D, rmean)))
    print("# COMPUTED PASS")


if __name__ == "__main__":
    main()
