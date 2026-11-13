# e1_penumbra.py - cft-debris M1, a reading of E1's radiation-pressure outputs
# (no gate): which lanes differ between native64 with the C library's asin and
# acos and cft64, and in which shadow class they lie.
# cft-debris, MIT licence (see LICENSE at the repository root). Written by
# DEBRIS-E, 2026-11-13.
#
#   python -I -B tests/e1_penumbra.py   (after tests/e1_gate.py, on its outputs)
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gatelib as g  # noqa: E402

CRITERIA = """
No pass condition. Reads E1's work files O2_srp_native64.txt and O2_srp_cft64.txt (seed 0xE1, 10,000 lanes) and
   reports: the number of penumbra lanes (0 < nu < 1 at cft64), the lanes whose outputs differ, each lane's nu at
   both kinds and the relative difference of nu.
"""


def main():
    log = g.Log("e1_penumbra", os.path.abspath(__file__), CRITERIA)
    W = os.path.join(g.WORK, "e1")
    pa, pb = os.path.join(W, "O2_srp_native64.txt"), os.path.join(W, "O2_srp_cft64.txt")
    log.w("# inputs: %s sha256 %s; %s sha256 %s" % (pa, g.sha256(pa), pb, g.sha256(pb)))
    a, _ = g.read_rows(pa)
    b, _ = g.read_rows(pb)
    pen = [rb[0] for rb in b if 0 < g.value(rb[4], 64) < 1]
    diff = [(ra, rb) for ra, rb in zip(a, b) if ra[1:] != rb[1:]]
    log.w("MEASURED %d lanes, %d in penumbra (0 < nu < 1 at cft64), %d differ" % (len(b), len(pen), len(diff)))
    inpen = 0
    for ra, rb in diff:
        nu_c, nu_n = g.value(rb[4], 64), g.value(ra[4], 64)
        inpen += 0 < nu_c < 1
        rel = float(abs(nu_n - nu_c) / nu_c) if nu_c else float("nan")
        log.w("MEASURED lane %s: nu cft64 %.12f, native64 (C library) %.12f, relative difference %.2e" %
              (ra[0], float(nu_c), float(nu_n), rel))
    log.w("MEASURED differing lanes in penumbra: %d of %d" % (inpen, len(diff)))
    return log.close()


if __name__ == "__main__":
    sys.exit(main())
