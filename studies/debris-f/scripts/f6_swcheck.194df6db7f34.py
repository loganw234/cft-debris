# f6_swcheck.py - cft-debris M1 (DEBRIS-F): the two-fill check of the lead's ruling on the space-weather copy, before
# F6's comparator (C) runs.
# cft-debris, MIT licence (see LICENSE at the repository root). Written by DEBRIS-F, 2026-11-16.
#
#   python -I -B tests/f6_swcheck.py
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import f_lib as F  # noqa: E402

START, HOURS = "2026-10-14T00:00:00.000", 840
CRITERIA = """
The copies (tests/f6_swcopy.py): the approved SW-Last5Years.txt with its 45 blank DAILY_PREDICTED qualifiers (column
  100) filled with 0, or with 4 (the two codes the OBSERVED section uses); and the 0 copy with 2026-11-16's F10.7 set to
  150.0 in the adjusted and the observed columns (the control).
Each copy is loaded through Orekit 13.1.9's own CssiSpaceWeatherData (tests/f6_swcheck.js), and getDailyFlux,
  getAverageFlux and getAp's seven values are read at every hour from 2026-10-14 00:00 to 2026-11-18 00:00 UTC (841
  epochs). The span covers every date (C) can evaluate the density: S0's earliest epoch is 2026-10-18 22:43 UTC, a fit
  span starts a day before and NRLMSISE-00's ap history reaches 57 hours further back, to 2026-10-15; and every S1
  epoch is before 2026-11-17, which F6 asserts for (C)'s pairs.
K1 the 0 copy and the 4 copy give identical values, bit for bit, at all 841 epochs (all 9 values each).
K2 CONTROL: the planted copy must change at least one compared value against the 0 copy.
Both copies must load (Orekit's loader must not fail on the MONTHLY_PREDICTED lines, left as served).
"""


def main():
    log = F.Log("f6_swcheck", os.path.abspath(__file__), CRITERIA, extra_files=[os.path.join(F.REPO, "tests", "f6_swcheck.js"),
                                                                               os.path.join(F.REPO, "tests", "f6_swcopy.py")])
    W = F.WORK + "/f6sw"
    os.makedirs(W, exist_ok=True)
    vals = {}
    for name in ("sw_fill0", "sw_fill4", "sw_plant"):
        d = F.DATA + "/" + name
        log.w("# %s/SW-Last5Years.txt sha256 %s" % (name, F.sha256(d + "/SW-Last5Years.txt")))
        o = W + "/%s.txt" % name
        F.orekit(os.path.join(F.REPO, "tests", "f6_swcheck.js"), [d, o, START, str(HOURS)], log, cpu_label="f6_swcheck_%s" % name)
        rows = [ln.split() for ln in open(o) if not ln.startswith("#")]
        log.w("# " + [ln.strip() for ln in open(o) if ln.startswith("#")][0])
        log.check(len(rows) == HOURS + 1 and all(len(r) == 10 for r in rows), "%s loaded; %d epochs of 9 values" % (name, len(rows)))
        vals[name] = rows
    nd = sum(1 for a, b in zip(vals["sw_fill0"], vals["sw_fill4"]) if a != b)
    log.check(nd == 0, "K1 the 0 and 4 fills give identical inputs at all %d epochs (%d differ)" % (HOURS + 1, nd))
    npd = sum(1 for a, b in zip(vals["sw_fill0"], vals["sw_plant"]) if a != b)
    log.check(npd > 0, "K2 the planted F10.7 changes the inputs at %d epochs (at least one required)" % npd)
    return log.close()


if __name__ == "__main__":
    sys.exit(main())
