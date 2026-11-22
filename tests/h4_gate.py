# h4_gate.py - cft-debris M1 (DEBRIS-H), gate H4: the decoder on amd-arc-box against the desktop's. Standard library only.
# cft-debris, MIT licence (see LICENSE at the repository root). Written by DEBRIS-H, 2026-11-18.
#
#   desktop: python -I -B tests/h4_gate.py <root> --java JAVA [--logs DIR] [--keep DIR] [--cpu TSV]
#   box:     python3 -I -B in/tests/h4_gate.py <root> --java java --compare in/desktop/h4_decode.txt
# Works from <root> (in/ as tests/h_stage.py lays it out). The decode's output holds states: it is the ledger's.
import argparse
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import h_lib as H  # noqa: E402

SCRIPT = os.path.abspath(__file__)

CRITERIA = """
H4 (DEBRIS-H's brief, decision 2(a)): every row of DEBRIS-F's S0 (the four groups' CSV files, in file order, the groups
in order), decoded by tests/f5_sgp4.js (Orekit 13.1.9's SGP4 through Nashorn, in/jars, in/orekit) at three instants
each - e0q - 1 day, e0q and e0q + 3 days (e0q the epoch in TDB rounded to 2^-20 s, as DEBRIS-F's B1) - in one JVM, so
that the sequence of requests is the same on both machines (the decoder's output depends on what its JVM decoded
before: DEBRIS-H's finding of 2026-11-18).
CRITERION (box, against the desktop's file): every GCRF state bit-identical. If not, the gate still passes when every
position agrees within 1 mm and every velocity within 1 um/s, and the differences are reported as a finding (basis:
1 mm is a twenty-thousandth of the smallest cell median F6 reported, (B)'s 20 m).
CONTROL C12: the first row with its mean motion moved by one ulp (the next binary64 above), decoded first in a JVM of
its own (the same history as the first row in the main run: none), must change its states at all three instants.
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root")
    ap.add_argument("--java", required=True)
    ap.add_argument("--compare")
    ap.add_argument("--logs", default="logs")
    ap.add_argument("--keep")
    ap.add_argument("--cpu")
    a = ap.parse_args()
    os.chdir(a.root)
    cpu = H.CpuAccount("h4_gate", a.cpu)
    log = H.Log("h4_gate", a.logs, SCRIPT, CRITERIA, extra=["in/tests/f5_sgp4.js"], keep_dir=a.keep)
    H.load_leaps("in/orekit/tai-utc.dat")
    jars = sorted(os.path.join("in/jars", j) for j in os.listdir("in/jars") if j.endswith(".jar"))
    for p in jars + ["in/orekit/finals2000A.daily", "in/orekit/tai-utc.dat"] + ["in/gp/gp-%s-S0.csv" % g for g in H.GROUPS]:
        log.w("# %s sha256 %s" % (p, H.sha256(p)))
    items = []
    for gi, g in enumerate(H.GROUPS):
        for r in H.read_gp("in/gp/gp-%s-S0.csv" % g, g):
            e = H.epoch_q(r)
            items.append(("%d_%s" % (gi, r["NORAD_CAT_ID"]), r, [e - 86400.0, e, e + 259200.0]))
    _, work = H.next_numbered("h4", "gate", "")
    os.makedirs(work)
    pin, pout = os.path.join(work, "h4_in.txt"), os.path.join(work, "h4_decode.txt")
    H.decode_input(pin, items)
    log.w("# the decode: %d rows x 3 instants, one JVM, in file order; input %s sha256 %s" % (len(items), os.path.basename(pin), H.sha256(pin)))
    rc, out, err = H.run(H.java_argv(a.java, jars, "in/tests/f5_sgp4.js", ["pv", "in/orekit", pin, pout]), log)
    log.w("# java: %s" % [ln for ln in open(pout) if ln.startswith("# f5_sgp4")][0].strip())
    mine = {}
    for ln in open(pout, encoding="ascii"):
        p = ln.split()
        if p and p[0] == "V":
            mine[(p[1], p[2])] = p[4:10]
    refused = sum(1 for ln in open(pout, encoding="ascii") if ln.startswith("F "))
    log.check(len(mine) == 3 * len(items) and refused == 0, "every row decoded at its three instants (%d states, %d refused)" % (len(mine), refused))
    log.w("# the decode's output: %s, sha256 %s (per object: the ledger's)" % (pout.replace("\\", "/"), H.sha256(pout)))
    # C12
    key0, r0, ts0 = items[0]
    _, vals = H.orekit_line(r0, key0)
    n1 = math.nextafter(vals[0], math.inf)
    pin2, pout2 = os.path.join(work, "c12_in.txt"), os.path.join(work, "c12_decode.txt")
    H.decode_input(pin2, [(key0, r0, ts0)], plant_n={key0: n1})
    H.run(H.java_argv(a.java, jars, "in/tests/f5_sgp4.js", ["pv", "in/orekit", pin2, pout2]), log)
    pl = {(p[1], p[2]): p[4:10] for p in (ln.split() for ln in open(pout2, encoding="ascii")) if p and p[0] == "V"}
    nchg = sum(1 for k in range(3) if pl.get((key0, str(k))) != mine[(key0, str(k))])
    log.check(nchg == 3 and float.fromhex(open(pin2).read().split()[10]) == n1, "C12 the first row's mean motion moved by one ulp changes its states at %d of 3 instants - failed as specified" % nchg)
    if a.compare:
        other = {}
        for ln in open(a.compare, encoding="ascii"):
            p = ln.split()
            if p and p[0] == "V":
                other[(p[1], p[2])] = p[4:10]
        log.w("# compared with %s, sha256 %s" % (a.compare, H.sha256(a.compare)))
        same = sum(1 for k in mine if other.get(k) == mine[k])
        dr = dv = 0.0
        for k in mine:
            if k in other and other[k] != mine[k]:
                x = [float.fromhex(v) for v in mine[k]]
                y = [float.fromhex(v) for v in other[k]]
                dr = max(dr, H.dist(x[:3], y[:3]))
                dv = max(dv, H.dist(x[3:], y[3:]))
        log.w("# bit-identical states: %d of %d; the largest differences: position %.3e m, velocity %.3e m/s" % (same, len(mine), dr, dv))
        if same == len(mine) == len(other):
            log.check(True, "H4 every GCRF state bit-identical on the two machines")
        else:
            log.check(set(mine) == set(other) and dr <= 1e-3 and dv <= 1e-6,
                      "H4 not bit-identical (FINDING: %d of %d states differ), and every position within 1 mm and velocity within 1 um/s" % (len(mine) - same, len(mine)))
    c_ = cpu.close("h4_gate log %03d" % log.n)
    if c_ is not None:
        log.w("# CPU: %.2f s by cycles / 2.5e9 (this script and every process it started)" % c_)
    return log.close()


if __name__ == "__main__":
    sys.exit(main())
