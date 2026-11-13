# e4_gate.py - cft-debris M1, gate E4: Lasser et al.'s benchmark - gravity,
# degrees 2 to 180, and the direct tides of the Sun and the Moon.
# cft-debris, MIT licence (see LICENSE at the repository root). Written by
# DEBRIS-E, 2026-11-13; the conventions are DEBRIS-C's (m1a_compare.py,
# m1b_check.py), which held the binary64 kernels to the same files.
#
#   python -I -B tests/e4_gate.py
#
# Inputs (the downloads, SHA-256 in lead.md): 00orbit_itrf.txt and
# 02gravityfield_itrf.txt (TRF positions and accelerations), 00orbit_icrf.txt,
# 03directTideSun_icrf.txt and 03directTideMoon_icrf.txt (CRF), EIGEN6-C4.gfc,
# DE421. 2,880 epochs 30 s apart on 2008-07-03 (GPS).
import math
import os
import sys
from fractions import Fraction

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gatelib as g  # noqa: E402

CRITERIA = """
TOL = 1e-11 m/s^2 on max over the epochs of |a - a_Lasser| (the vector difference's norm): DEBRIS-C's
   tolerance, the threshold the COST-G packages met for each force (READ via WebFetch by DEBRIS-C, Lasser et
   al. 2020).
T1 gravity, degrees 2..180, Earth-fixed, at the TRF positions (each kind converts the file's decimal
   positions): native64 and cft64 at every epoch (2,880), cft128 and cft256 at every tenth epoch (288):
   max |da| < TOL for each.
T2 the direct tides of the Sun and the Moon as point masses, a = GM (d/|d|^3 - s/|s|^3), at the CRF
   positions, GROOPS's GM values (the README), DE421, TDB = TT + 0.001657 sin g + 0.000014 sin 2g s and
   TT = GPS + 51.184 s (DEBRIS-C's convention): the same kinds and epochs: max |da| < TOL for the Sun and for
   the Moon, each.
T3 REPORTED, no pass condition: cft32 at every tenth epoch, gravity and tides; native64 against cft64,
   bit for bit or not.
C1 NEGATIVE CONTROL (DEBRIS-C's): the field truncated at degree 173 (degrees 2..173) must FAIL, max
   |da| > TOL, at native64 (every epoch) and at cft64 (every tenth epoch).
"""
TOL = Fraction(1, 10 ** 11)
D = g.DOWNLOADS
W = os.path.join(g.WORK, "e4")
os.makedirs(W, exist_ok=True)


def read_lasser(path):
    rows = []
    for ln in open(path, "r", encoding="ascii", errors="replace"):
        t = ln.split()
        if len(t) == 4 and not ln.startswith("#"):
            try:
                rows.append((t[0], Fraction(t[1]), Fraction(t[2]), Fraction(t[3])))
            except ValueError:
                pass
    return rows


def ours(log, mode, kind, stride, nmin=None, nmax=None, tag=""):
    out = os.path.join(W, "%s_%s_s%d%s.txt" % (mode, kind, stride, tag))
    args = [g.exe("O2"), mode, kind, stride] + ([nmin, nmax] if mode == "lasser" else []) + [out]
    g.run(args, log)
    rows, _ = g.read_rows(out)
    return rows


def maxdiff(rows, ref, nb, cols):
    """max over epochs of |a - a_ref| (exact differences, the norm in float)"""
    worst, at = 0.0, None
    for r in rows:
        e = int(r[0])
        a = [g.value(h, nb) for h in r[2 + cols[0]:2 + cols[1]]]
        d = [a[i] - ref[e][1 + i] for i in range(3)]
        n = math.sqrt(float(sum(x * x for x in d)))
        if n > worst:
            worst, at = n, e
    return worst, at


def main():
    log = g.Log("e4_gate", os.path.abspath(__file__), CRITERIA)
    for p in ("00orbit_itrf.txt", "02gravityfield_itrf.txt", "00orbit_icrf.txt", "03directTideSun_icrf.txt",
              "03directTideMoon_icrf.txt", "EIGEN6-C4.gfc", "lnxp1900p2053.421"):
        log.w("# input %s sha256 %s" % (p, g.sha256(D + p + "/" + p)))
    LG = read_lasser(D + "02gravityfield_itrf.txt/02gravityfield_itrf.txt")
    LS = read_lasser(D + "03directTideSun_icrf.txt/03directTideSun_icrf.txt")
    LM = read_lasser(D + "03directTideMoon_icrf.txt/03directTideMoon_icrf.txt")
    log.check(len(LG) == len(LS) == len(LM) == 2880, "the benchmark files hold 2,880 epochs each")
    plan = [("native64", 1, True), ("cft64", 1, True), ("cft128", 10, True), ("cft256", 10, True),
            ("cft32", 10, False)]
    grav, tide = {}, {}
    for kind, stride, gate in plan:
        nb = g.FMT[kind]
        rg = ours(log, "lasser", kind, stride, 2, 180)
        grav[kind] = rg
        n_exp = len(range(0, 2880, stride))
        dg, eg = maxdiff(rg, LG, nb, (0, 3))
        rt = ours(log, "lasser3", kind, stride)
        tide[kind] = rt
        ds, es = maxdiff(rt, LS, nb, (0, 3))
        dm, em = maxdiff(rt, LM, nb, (3, 6))
        if gate:
            log.check(len(rg) == n_exp and dg < TOL, "T1 %s gravity 2..180 against Lasser et al.: max |da| %.3e m/s^2 "
                      "(epoch %s) < 1e-11 over %d epochs" % (kind, dg, eg, len(rg)))
            log.check(len(rt) == n_exp and ds < TOL, "T2 %s Sun: max |da| %.3e m/s^2 (epoch %s) < 1e-11 over %d epochs"
                      % (kind, ds, es, len(rt)))
            log.check(dm < TOL, "T2 %s Moon: max |da| %.3e m/s^2 (epoch %s) < 1e-11" % (kind, dm, em))
        else:
            log.w("REPORTED T3 %s (every tenth epoch): gravity max |da| %.3e m/s^2, Sun %.3e, Moon %.3e"
                  % (kind, dg, ds, dm))
    same_g = [r[2:] for r in grav["native64"]] == [r[2:] for r in grav["cft64"]]
    same_t = [r[2:] for r in tide["native64"]] == [r[2:] for r in tide["cft64"]]
    log.w("REPORTED T3 native64 against cft64 over 2,880 epochs: gravity %s, tides %s" %
          ("bit for bit" if same_g else "DIFFER", "bit for bit" if same_t else "DIFFER"))
    for kind, stride in (("native64", 1), ("cft64", 10)):
        rc = ours(log, "lasser", kind, stride, 2, 173, tag="_d173")
        dc, ec = maxdiff(rc, LG, g.FMT[kind], (0, 3))
        log.check(dc > TOL, "C1 control: %s truncated at degree 173 is REPORTED, max |da| %.3e m/s^2 = %.1f x TOL"
                  % (kind, dc, dc / 1e-11))
    return log.close()


if __name__ == "__main__":
    sys.exit(main())
