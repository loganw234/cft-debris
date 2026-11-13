# e3_lanes.py - cft-debris M1, a reading of E3's runs (no gate): binary64's
# difference from binary128 lane by lane, and the 28-band atmosphere's density
# step at each band edge. cft-debris, MIT licence (see LICENSE at the
# repository root). Written by DEBRIS-E, 2026-11-13.
#
#   python -I -B tests/e3_lanes.py   (after tests/e3_gate.py, on its outputs)
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gatelib as g  # noqa: E402

CRITERIA = """
No pass condition. (1) From E3's work files cft64_plain.txt and cft128_plain.txt: each lane's |r64 - r128| at
   steps 0, 1, 2, 5, 10, 20, 50 and 100, and each lane's altitude above R_EARTH = 6378136.3 m at step 0.
(2) COMPUTED from DEBRIS-B's table (src/m1_consts.h): at each band edge h_k, the density the band below
   gives there, rho_(k-1) exp(-(h_k - h_(k-1))/H_(k-1)), against the band's own base density rho_k, as a
   relative step.
"""
H0 = [0, 25, 30, 40, 50, 60, 70, 80, 90, 100, 110, 120, 130, 140, 150, 180, 200, 250, 300, 350, 400, 450, 500, 600, 700,
      800, 900, 1000]
RHO = [1.225, 3.899e-2, 1.774e-2, 3.972e-3, 1.057e-3, 3.206e-4, 8.770e-5, 1.905e-5, 3.396e-6, 5.297e-7, 9.661e-8,
       2.438e-8, 8.484e-9, 3.845e-9, 2.070e-9, 5.464e-10, 2.789e-10, 7.248e-11, 2.418e-11, 9.518e-12, 3.725e-12,
       1.585e-12, 6.967e-13, 1.454e-13, 3.614e-14, 1.170e-14, 5.245e-15, 3.019e-15]
HS = [7.249, 6.349, 6.682, 7.554, 8.382, 7.714, 6.549, 5.799, 5.382, 5.877, 7.263, 9.473, 12.636, 16.149, 22.523,
      29.740, 37.105, 45.546, 53.628, 53.298, 58.515, 60.828, 63.822, 71.835, 88.667, 124.64, 181.05, 268.00]


def main():
    log = g.Log("e3_lanes", os.path.abspath(__file__), CRITERIA)
    W = os.path.join(g.WORK, "e3")
    pa, pb = os.path.join(W, "cft64_plain.txt"), os.path.join(W, "cft128_plain.txt")
    log.w("# inputs: %s sha256 %s; %s sha256 %s" % (pa, g.sha256(pa), pb, g.sha256(pb)))
    a = {(int(r[1]), int(r[3])): r[4:10] for r in g.read_rows(pa, "S")[0]}
    b = {(int(r[1]), int(r[3])): r[4:10] for r in g.read_rows(pb, "S")[0]}
    for l in range(8):
        r0 = math.sqrt(sum(float(g.value(h, 128)) ** 2 for h in b[(0, l)][:3]))
        out = []
        for s in (0, 1, 2, 5, 10, 20, 50, 100):
            d = math.sqrt(float(sum((g.value(x, 64) - g.value(y, 128)) ** 2 for x, y in zip(a[(s, l)][:3], b[(s, l)][:3]))))
            out.append("%d:%.2e" % (s, d))
        log.w("MEASURED lane %d (altitude at t = 0: %.6f km): |r64 - r128| at steps %s" %
              (l, (r0 - 6378136.3) / 1e3, " ".join(out)))
    for k in range(1, 28):
        below = RHO[k - 1] * math.exp(-(H0[k] - H0[k - 1]) / HS[k - 1])
        log.w("COMPUTED band edge %4d km: the band below gives %.5e, the band %.5e; relative step %+.2e" %
              (H0[k], below, RHO[k], (RHO[k] - below) / below))
    return log.close()


if __name__ == "__main__":
    sys.exit(main())
