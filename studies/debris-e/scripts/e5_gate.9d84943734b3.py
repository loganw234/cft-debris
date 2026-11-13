# e5_gate.py - cft-debris M1, gate E5: the DE421 reader against JPL's
# testpo.421. cft-debris, MIT licence (see LICENSE at the repository root).
# Written by DEBRIS-E, 2026-11-13.
#
#   python -I -B tests/e5_gate.py
import os
import sys
from fractions import Fraction

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gatelib as g  # noqa: E402

CRITERIA = """
TOL = 1e-13 AU on |computed - testpo| for each coordinate, DEBRIS-C's tolerance (testpo.421 prints 17
   significant digits, so E5 tests the reader, not the formats' precision).
The points: every line of testpo.421 whose target and centre are both among the Earth (3), the Moon (10),
   the Sun (11), the solar-system barycentre (12) and the Earth-Moon barycentre (13), coordinates 1 to 3
   (positions; the propagator uses no velocity of a body), inside the binary's coverage (JED 2414992.5 to
   2469808.5); points outside it are counted and skipped. Librations and nutations are left out (the
   propagator uses neither; DEBRIS-C's failures were librations). (10, 3) and (3, 10) use the geocentric Moon
   directly; every other pair is target minus centre, each relative to the barycentre.
P1 at cft64, cft128 and cft256: every point within TOL.
P2 NEGATIVE CONTROL: the Moon's first x coefficient, in the sub-interval of the first selected point that
   involves the Moon, raised by 1e-3 km in the record (6.7e-12 AU, 67 TOL): the check must fail (at least one
   point beyond TOL) at cft64, and the failures must all lie in that record.
REPORTED: native64 at every point (not gated by E5; E1 holds it to cft64 bit for bit).
"""
TOL = Fraction(1, 10 ** 13)
W = os.path.join(g.WORK, "e5")
os.makedirs(W, exist_ok=True)


def run(log, kind, plant=False):
    out = os.path.join(W, "testpo_%s%s.txt" % (kind, "_plant" if plant else ""))
    g.run([g.exe("O2"), "testpo", kind, out] + (["--plant"] if plant else []), log)
    rows, head = g.read_rows(out)
    return rows, head


def check(rows, nb):
    worst, nfail, recs = Fraction(0), 0, set()
    for r in rows:
        # line jed t c x value hex "rec" record
        want = Fraction(r[5].replace("D", "e").replace("d", "e"))
        got = g.value(r[6], nb)
        d = abs(got - want)
        worst = max(worst, d)
        if d >= TOL:
            nfail += 1
            recs.add(int(r[8]))
    return worst, nfail, recs


def main():
    log = g.Log("e5_gate", os.path.abspath(__file__), CRITERIA)
    for p in ("testpo.421", "lnxp1900p2053.421", "header.421"):
        log.w("# input %s sha256 %s" % (p, g.sha256(g.DOWNLOADS + p + "/" + p)))
    for kind in ("cft64", "cft128", "cft256", "native64"):
        rows, head = run(log, kind)
        log.w("# %s: %s" % (kind, [h for h in head if h.startswith("# testpo")][0]))
        worst, nfail, _ = check(rows, g.FMT[kind])
        pairs = sorted(set((r[2], r[3]) for r in rows))
        if kind == "native64":
            log.w("REPORTED native64: %d points, worst %.3e AU, %d beyond TOL" % (len(rows), float(worst), nfail))
            continue
        log.check(len(rows) > 0 and nfail == 0, "P1 %s: %d points (pairs %s), worst |d| %.3e AU < 1e-13"
                  % (kind, len(rows), " ".join("%s-%s" % p for p in pairs), float(worst)))
    rows, head = run(log, "cft64", plant=True)
    hp = [h for h in head if h.startswith("# testpo")][0]
    prec = int(hp.split("(record ")[1].split()[0])
    worst, nfail, recs = check(rows, 64)
    log.check(nfail >= 1 and recs == {prec}, "P2 control: the planted coefficient is REPORTED - %d points beyond TOL, "
              "all in record %s (planted in record %d), worst %.3e AU" % (nfail, sorted(recs), prec, float(worst)))
    return log.close()


if __name__ == "__main__":
    sys.exit(main())
