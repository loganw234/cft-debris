#!/usr/bin/env python3
"""DEBRIS-C, M4: the acceptance bands of the designed covariance-realism test,
COMPUTED (mpmath, exact distributions), so the criteria are numbers before
any data exists.

  python -I -B m4_criteria.py

For one prediction method and one horizon bin with N passes, z is the
normalised range residual (one per pass). Under a realistic covariance
z ~ N(0, 1). The test PASSES iff both:
  (a) the count with |z| <= 2 lies inside the two-sided 99% binomial
      interval for p = P(|z| <= 2) and N;
  (b) the mean of z^2 lies inside [q_0.005, q_0.995] of chi-square(N) / N.
Also printed: P(|z| <= k) in 1-D, and P(d^2 <= k^2) for a 3-D position
chi-square(3), for reference.
"""
import mpmath as mp

mp.mp.dps = 30


def binom_cdf(k, n, p):
    return mp.fsum(mp.binomial(n, i) * p ** i * (1 - p) ** (n - i) for i in range(0, k + 1))


def binom_interval(n, p, conf=0.99):
    a = (1 - conf) / 2
    lo = next(k for k in range(n + 1) if binom_cdf(k, n, p) > a)
    hi = next(k for k in range(n + 1) if binom_cdf(k, n, p) >= 1 - a)
    return lo, hi


def chi2_ppf(q, n):
    return mp.findroot(lambda x: mp.gammainc(n / 2.0, 0, x / 2.0, regularized=True) - q, n)


def main():
    for k in (1, 2, 3):
        p1 = mp.erf(k / mp.sqrt(2))
        p3 = mp.gammainc(1.5, 0, k * k / 2.0, regularized=True)
        print("k = %d: P(|z| <= k) 1-D = %.4f; P(d^2 <= k^2) 3-D = %.4f" % (k, p1, p3))
    p2 = mp.erf(2 / mp.sqrt(2))
    for n in (50, 86, 200, 500):
        lo, hi = binom_interval(n, p2)
        q0, q1 = chi2_ppf(0.005, n), chi2_ppf(0.995, n)
        print("N = %3d: (a) |z| <= 2 count in [%d, %d] (fraction %.3f to %.3f); (b) mean z^2 in [%.3f, %.3f]"
              % (n, lo, hi, lo / n, hi / n, q0 / n, q1 / n))
    print("# COMPUTED")


if __name__ == "__main__":
    main()
