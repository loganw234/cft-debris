# k_swcheck.py - cft-debris (DEBRIS-K): the two-fill check of the lead's ruling on the space-weather copy, over the dates
# the pilot's comparator (C) can evaluate the density, before (C) runs.
# cft-debris, MIT licence (see LICENSE at the repository root). Copied by DEBRIS-K, 2026-11-23, from DEBRIS-F's
# tests/f6_swcheck.py (cft-debris's own, MIT), with DEBRIS-F's tests/f6_swcheck.js run unchanged. What changed: the
# span (DEBRIS-K's dates), every path from the arguments, and the log through k_lib.py; the criteria are DEBRIS-F's.
#
#   python -I -B k_swcheck.py --data DIR (holding sw3_fill0, sw3_fill4, sw3_plant) --js f6_swcheck.js --java JAVA
#        --jars DIR --work DIR --logs DIR --keep DIR --cpu TSV
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import k_lib as H  # noqa: E402

SCRIPT = os.path.abspath(__file__)
START, HOURS = "2026-11-01T00:00:00.000", 504
CRITERIA = """
The copies (tests/k_swcopy.py, DEBRIS-F's three normalisations): the approved SW-Last5Years.txt with its blank fields
  filled with 0, or with 4, and the 0 copy with 2026-11-16's F10.7 set to 150.0 in the adjusted and observed columns.
Each copy is loaded through Orekit 13.1.9's own CssiSpaceWeatherData (tests/f6_swcheck.js, unchanged), and
  getDailyFlux, getAverageFlux and getAp's seven values are read at every hour from 2026-11-01 00:00 to 2026-11-22 00:00
  UTC (505 epochs). The span is chosen to cover every date (C) can evaluate the density in the pilot: a fit span starts
  a day before its set's epoch (the oldest seed set expected near 2026-11-05), NRLMSISE-00's ap history reaches 57 hours
  further back, and the last reference is from slot 20, fetched 2026-11-21 03:00 UTC. (C) asserts that its own dates,
  60 hours of history included, lie inside this span, and is not run otherwise.
K1 the 0 copy and the 4 copy give identical values, bit for bit, at all 505 epochs (all 9 values each).
K2 CONTROL: the planted copy must change at least one compared value against the 0 copy.
"""


def main():
    ap = argparse.ArgumentParser()
    for o in ("--data", "--js", "--java", "--jars", "--work", "--logs", "--keep", "--cpu"):
        ap.add_argument(o, required=True)
    a = ap.parse_args()
    cpu = H.CpuAccount("k_swcheck", a.cpu)
    log = H.Log("k_swcheck", a.logs, SCRIPT, CRITERIA, extra=[a.js], keep_dir=a.keep)
    jars = sorted(os.path.join(a.jars, j) for j in os.listdir(a.jars) if j.endswith(".jar"))
    os.makedirs(a.work, exist_ok=True)
    vals = {}
    for name in ("sw3_fill0", "sw3_fill4", "sw3_plant"):
        d = os.path.join(a.data, name)
        log.w("# %s/SW-Last5Years.txt sha256 %s" % (name, H.sha256(os.path.join(d, "SW-Last5Years.txt"))))
        o = os.path.join(a.work, "swcheck_%s.txt" % name)
        H.run(H.java_argv(a.java, jars, a.js, [d, o, START, str(HOURS)]), log)
        rows = [ln.split() for ln in open(o) if not ln.startswith("#")]
        log.w("# " + [ln.strip() for ln in open(o) if ln.startswith("#")][0])
        log.check(len(rows) == HOURS + 1 and all(len(r) == 10 for r in rows), "%s loaded; %d epochs of 9 values" % (name, len(rows)))
        vals[name] = rows
    nd = sum(1 for x, y in zip(vals["sw3_fill0"], vals["sw3_fill4"]) if x != y)
    log.check(nd == 0, "K1 the 0 and 4 fills give identical inputs at all %d epochs (%d differ)" % (HOURS + 1, nd))
    npd = sum(1 for x, y in zip(vals["sw3_fill0"], vals["sw3_plant"]) if x != y)
    log.check(npd > 0, "K2 the planted F10.7 changes the inputs at %d epochs (at least one required)" % npd)
    c_ = cpu.close("k_swcheck log %03d" % log.n)
    if c_ is not None:
        log.w("# CPU: %.2f s by cycles / 2.5e9" % c_)
    return log.close()


if __name__ == "__main__":
    sys.exit(main())
