# k_compute.py - cft-debris (DEBRIS-K), Q6: what a small set of objects with ensembles needs, COMPUTED from labelled
# inputs (no run of M1; nothing here is a timing). Standard library only.
# cft-debris, MIT licence (see LICENSE at the repository root). Written by DEBRIS-K, 2026-11-23.
#
#   python -I -B k_compute.py --logs DIR --keep DIR
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import k_lib as H  # noqa: E402

SCRIPT = os.path.abspath(__file__)
DAY = 86400.0
CRITERIA = """
COMPUTED, no pass condition. Inputs, each labelled:
  MEASURED in DEBRIS-G's G4 (box, M1's full model, 64 lanes, a sensitive window): native64 1,291,561 object-seconds a
    second on 1 worker; cft256 299 on 1 worker and 4,332 on 36.
  ESTIMATE in DEBRIS-I's plan: its cft program at binary256, 3,050 to 9,090 object-seconds a second a box worker, at a
    smaller model (degree 7).
  ESTIMATE in DEBRIS-D's Q5: device seconds an object-day at degree 20, rk4 15 s: RX 7600 binary64 0.16 to 0.23,
    binary256 0.42 to 0.60; RTX 5060 Ti binary64 0.071 to 0.098, binary256 0.32 to 0.47; times 1 to 3 for batches that
    do not fill the card (its own factor).
  MEASURED in this pilot: (R)'s fits took a median of 3 iterations (k_pilot rfit), (H)'s 146 iterations over 33 fits
    with 56,594 observations at 120 s (spans 2.38 days on average); new sets came at 55 over 17 objects between S_H0's
    fetch and slot 20's (2.21 days): 1.46 a day an object, with missed slots (a lower bound).
THE WORKLOAD of one object a day (ESTIMATE, from the inputs): c forecast cycles a day (c = 1.5, the pilot's rate, and
  c = 8, every 3-hour slot); each cycle one (R) fit (8 lanes x 1 day x 4 iterations = 32 lane-days), one (H) fit
  (8 lanes x 2.4 days x 4.4 iterations = 84 lane-days) and N members each propagated over a horizon of D days (D = 30,
  the decay window; D = 7 beside it). Lane-days a day = c (32 + 84 + N D).
THE NEED: CPU-seconds a day = lane-days x 86,400 / the rate; in box workers (one worker is 86,400 CPU-seconds a day;
  the box has 36 logical CPUs), or in cards (one card is 86,400 device-seconds a day).
"""

RATES = [("native64, M1 on a box worker (G4)", 1291561.0, 1291561.0),
         ("cft256, M1 on a box worker (G4, 1 worker)", 299.0, 299.0),
         ("binary256, DEBRIS-I's program on a box worker (ESTIMATE)", 3050.0, 9090.0)]
CARDS = [("RX 7600 binary64 (DEBRIS-D ESTIMATE)", 0.16, 0.23), ("RX 7600 binary256 (DEBRIS-D ESTIMATE)", 0.42, 0.60),
         ("RTX 5060 Ti binary64 (DEBRIS-D ESTIMATE)", 0.071, 0.098), ("RTX 5060 Ti binary256 (DEBRIS-D ESTIMATE)", 0.32, 0.47)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--logs", required=True)
    ap.add_argument("--keep", required=True)
    a = ap.parse_args()
    log = H.Log("k_compute", a.logs, SCRIPT, CRITERIA, keep_dir=a.keep)
    log.w("# the pilot's rate of new sets: 55 / 17 / 2.21 = %.2f a day an object" % (55 / 17 / 2.21))
    for c in (1.5, 8.0):
        for D in (30, 7):
            log.w("# cycles a day %.1f, horizon %d days" % (c, D))
            for nobj in (10, 100, 1000):
                for N in (1, 100, 1000):
                    ld = nobj * c * (32 + 84 + N * D)
                    parts = []
                    for name, lo, hi in RATES:
                        w_hi = ld * DAY / lo / DAY
                        w_lo = ld * DAY / hi / DAY
                        parts.append("%s %s workers" % (name.split(",")[0], ("%.3g" % w_hi) if lo == hi else "%.3g-%.3g" % (w_lo, w_hi)))
                    for name, lo, hi in CARDS:
                        parts.append("%s %.3g-%.3g cards" % (name.split(" (")[0], ld * lo / DAY, 3 * ld * hi / DAY))
                    log.w("COMPUTED objects %d, members %d: %.4g lane-days a day; %s" % (nobj, N, ld, "; ".join(parts)))
    # one forecast for one object, its cost on a box worker (COMPUTED)
    for name, lo, hi in RATES:
        f_r = 32 * DAY / lo
        f_h = 84 * DAY / lo
        p30 = 30 * DAY / lo
        log.w("COMPUTED one object, %s: (R) fit %.3g CPU-s, (H) fit %.3g CPU-s, one 30-day member %.3g CPU-s%s" % (
            name, f_r, f_h, p30, "" if lo == hi else " (to %.3g, %.3g, %.3g at the estimate's other end)" % (32 * DAY / hi, 84 * DAY / hi, 30 * DAY / hi)))
    return log.close()


if __name__ == "__main__":
    sys.exit(main())
