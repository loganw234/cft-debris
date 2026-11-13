# e1_gate.py - cft-debris M1, gate E1: native against cft, kernel by kernel,
# at binary64 and binary32. cft-debris, MIT licence (see LICENSE at the
# repository root). Written by DEBRIS-E, 2026-11-13.
#
#   python -I -B tests/e1_gate.py [nlanes=10000]
#
# What varies between lanes (each lane an independent draw of a fixed-seed
# splitmix64, seed 0xE1; tests/m1run.c mode e1 states each kernel's ranges):
# positions (direction uniform on the sphere; radius per kernel), velocities,
# the Sun's and the Moon's positions, epochs over DE421's whole coverage,
# rotation times over ten days, ballistic and radiation coefficients.
import os
import sys
from fractions import Fraction

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gatelib as g  # noqa: E402

CRITERIA = """
C1 constants and derived tables (to degree 180): native64's every entry equals cft64's, and native32's
   equals cft32's, bit for bit - so every constant's C-library conversion (strtod, strtof) equals libcft's
   correctly rounded cft_from_decimal_char, and every derived table matches across kinds.
C2 kernels of +, -, x, FMA, / and sqrt only - gravity at degree 2 and 20 (N lanes), gravity at degree 180
   (64 lanes), the central term, the third body, the Chebyshev reader with its body sums, the shadow geometry
   before its inverse trigonometry: native equals cft bit for bit on every lane and output, at binary64 and
   binary32 (the NaN rule: NaNs agree as NaNs).
C3 kernels that call transcendentals - drag (exp), the rotation (sin, cos), radiation pressure (asin, acos):
   with the C library, each differing output is REPORTED in ulps (a measurement, no pass condition); in the
   control, where the native kinds route those calls to libcft's correctly rounded host functions, native
   equals cft bit for bit on every lane and output.
C4 the NaN report: every lane with a NaN output is reported (counted per kernel); none is expected.
C5 hand check: gravity at degree 2 (native64 and cft64) within 1e-13 x |a| of an independent evaluation
   (the closed-form degree-2 potential's gradient, in exact rational arithmetic from the same decimal
   coefficients) on the first 100 lanes; native32 and cft32 within 1e-5 x |a|.
C6 NEGATIVE CONTROL: the negctl build reorders one division in the native kinds alone (cos C =
   (r.d/|r|)/|d| instead of r.d/(|r||d|)). It must break bit-identity in the shadow geometry at binary64
   and at binary32 (at least one lane), every differing shadow-geometry output must be cos C (column 3),
   and the gate must say where (kernel, column, first lane, count); the kernels that do not use the
   geometry (gravity 20, central, third body, reader, drag, rotation) must stay bit-identical.
"""

N = int(sys.argv[1]) if len(sys.argv) > 1 else 10000
SEED = "0xE1"
W = os.path.join(g.WORK, "e1")
os.makedirs(W, exist_ok=True)
PAIRS = [("native64", "cft64"), ("native32", "cft32")]
EXACT = ["grav2", "grav20", "grav180", "central", "third", "cheb", "shadowgeom"]
TRANSC = ["drag", "rot", "srp"]


def kargs(kern, n):
    if kern == "grav2":
        return ["grav", n, ["--nmin", "2", "--nmax", "2"]]
    if kern == "grav20":
        return ["grav", n, ["--nmin", "2", "--nmax", "20"]]
    if kern == "grav180":
        return ["grav", 64, ["--nmin", "2", "--nmax", "180"]]
    return [kern, n, []]


def produce(log, variant, kern, kind, cr):
    k, n, extra = kargs(kern, N)
    out = os.path.join(W, "%s_%s_%s%s.txt" % (variant, kern, kind, "_cr" if cr else ""))
    g.run([g.exe(variant), "e1", k, kind, n, SEED, out] + extra + (["--cr"] if cr else []), log)
    rows, head = g.read_rows(out)
    return rows


def compare(rows_a, rows_b, nb):
    """(lanes differing, per-column [count, max ulps, first lane], NaN lanes a, NaN lanes b)"""
    assert len(rows_a) == len(rows_b) and len(rows_a) > 0
    ncol = len(rows_a[0]) - 1
    cols = [[0, 0, None] for _ in range(ncol)]
    lanes = 0
    nan_a = nan_b = 0
    for ra, rb in zip(rows_a, rows_b):
        assert ra[0] == rb[0]
        diff = False
        na = nb_ = False
        for j in range(ncol):
            ha, hb = ra[1 + j], rb[1 + j]
            na |= g.is_nan(ha, nb)
            nb_ |= g.is_nan(hb, nb)
            if not g.same(ha, hb, nb):
                diff = True
                c = cols[j]
                c[0] += 1
                if not (g.is_nan(ha, nb) or g.is_nan(hb, nb)):
                    c[1] = max(c[1], g.ulps(ha, hb, nb))
                if c[2] is None:
                    c[2] = int(ra[0])
        lanes += diff
        nan_a += na
        nan_b += nb_
    return lanes, cols, nan_a, nan_b


def describe(cols):
    return "; ".join("col %d: %d lanes, max %d ulps, first lane %s" % (j + 1, c[0], c[1], c[2])
                     for j, c in enumerate(cols) if c[0])


# ------------------------------------------------------------- the hand check
def dec_coeffs():
    """C20..S22 and GM, RE as the .gfc file writes them (exact decimals)"""
    want = {(2, 0), (2, 1), (2, 2)}
    co = {}
    gm = re = None
    head = True
    for ln in open(g.DOWNLOADS + "EIGEN6-C4.gfc/EIGEN6-C4.gfc", "r", encoding="ascii", errors="replace"):
        t = ln.split()
        if not t:
            continue
        if head:
            if t[0].startswith("end_of_head"):
                head = False
            elif t[0] == "earth_gravity_constant":
                gm = Fraction(t[1])
            elif t[0] == "radius":
                re = Fraction(t[1])
            continue
        if t[0] == "gfc" and (int(t[1]), int(t[2])) in want:
            co[(int(t[1]), int(t[2]))] = (Fraction(t[3]), Fraction(t[4]))
    return gm, re, co


def isqrt_frac(q, bitsprec=200):
    """sqrt of a positive Fraction to about bitsprec bits (a Fraction)"""
    import math
    s = math.isqrt(q.numerator * (1 << (2 * bitsprec)) // q.denominator)
    return Fraction(s, 1 << bitsprec)


def deg2_accel(x, y, z, gm, re, co):
    """gradient of U2 = GM Re^2/r^5 [C20 (3z^2 - r^2)/2 + 3z(C21 x + S21 y) + 3(C22 (x^2 - y^2) + 2 S22 x y)]
    with C2m = N2m C2m-bar, N20 = sqrt5, N21 = sqrt(5/3), N22 = sqrt(5/12); exact but for the square roots
    (200 bits) and r = sqrt(r^2) (200 bits)"""
    n20, n21, n22 = isqrt_frac(Fraction(5)), isqrt_frac(Fraction(5, 3)), isqrt_frac(Fraction(5, 12))
    C20 = n20 * co[(2, 0)][0]
    C21, S21 = n21 * co[(2, 1)][0], n21 * co[(2, 1)][1]
    C22, S22 = n22 * co[(2, 2)][0], n22 * co[(2, 2)][1]
    r2 = x * x + y * y + z * z
    r = isqrt_frac(r2)
    r5 = r2 * r2 * r
    k = gm * re * re
    P = C20 * (3 * z * z - r2) / 2 + 3 * z * (C21 * x + S21 * y) + 3 * (C22 * (x * x - y * y) + 2 * S22 * x * y)
    dP = [C20 * (-x) + 3 * z * C21 + 3 * (2 * C22 * x + 2 * S22 * y),
          C20 * (-y) + 3 * z * S21 + 3 * (-2 * C22 * y + 2 * S22 * x),
          C20 * (2 * z) + 3 * (C21 * x + S21 * y)]
    # grad (P / r^5) = dP / r^5 - 5 P r_vec / r^7
    r7 = r5 * r2
    return [k * (dP[0] / r5 - 5 * P * x / r7), k * (dP[1] / r5 - 5 * P * y / r7), k * (dP[2] / r5 - 5 * P * z / r7)]


def lane_positions(n):
    """the positions the degree-2 gravity kernel was given: the e1 mode's sidecar of binary64 inputs"""
    rows = g.read_rows(os.path.join(W, "O2_grav2_native64.txt.in"))[0][:n]
    return [tuple(g.value(h, 64) for h in r[1:4]) for r in rows]


def main():
    log = g.Log("e1_gate", os.path.abspath(__file__), CRITERIA)
    log.w("# lanes: %d per kernel (gravity at degree 180: 64), seed %s" % (N, SEED))
    # C1
    for a, b in PAIRS:
        ta, tb = os.path.join(W, "tables_%s.txt" % a), os.path.join(W, "tables_%s.txt" % b)
        g.run([g.exe("O2"), "tables", a, 180, ta], log)
        g.run([g.exe("O2"), "tables", b, 180, tb], log)
        ra, _ = g.read_rows(ta)
        rb, _ = g.read_rows(tb)
        nb = g.FMT[a]
        diffs = [(x[0], x[1]) for x, y in zip(ra, rb) if x[:2] != y[:2] or not g.same(x[2], y[2], nb)]
        names = sorted(set(x[0] for x in ra))
        log.w("# tables %s/%s: %d entries in %d tables (%s)" % (a, b, len(ra), len(names), " ".join(names)))
        log.check(len(ra) == len(rb) and len(ra) > 0 and not diffs,
                  "C1 %s = %s on all %d entries%s" % (a, b, len(ra), "" if not diffs else "; differ at %s" % diffs[:10]))
    # hand-checked values: pi and sqrt(3) correctly rounded at binary64
    t64 = {(x[0], x[1]): x[2] for x in g.read_rows(os.path.join(W, "tables_cft64.txt"))[0]}
    log.check(t64[("PI", "0")] == "400921fb54442d18", "C1 hand value: PI at binary64 is 0x400921fb54442d18")
    log.check(t64[("Dg", "1")] == "3ffbb67ae8584caa", "C1 hand value: Dg[1] = sqrt(3) at binary64 is 0x3ffbb67ae8584caa")
    # C2, C3, C4
    res = {}
    for a, b in PAIRS:
        nb = g.FMT[a]
        for kern in EXACT + TRANSC:
            ra = produce(log, "O2", kern, a, False)
            rb = produce(log, "O2", kern, b, False)
            lanes, cols, na, nbn = compare(ra, rb, nb)
            res[(kern, a, "libm")] = (ra, rb)
            log.w("# %s %s/%s, C library: %d lanes, %d differ%s; NaN lanes %d/%d" %
                  (kern, a, b, len(ra), lanes, (" (" + describe(cols) + ")") if lanes else "", na, nbn))
            log.check(na == 0 and nbn == 0, "C4 %s %s/%s: no NaN output (%d, %d lanes)" % (kern, a, b, na, nbn))
            if kern in EXACT:
                log.check(lanes == 0, "C2 %s %s = %s bit for bit on %d lanes" % (kern, a, b, len(ra)))
            else:
                log.w("MEASURED C3 %s %s against %s with the C library's transcendentals: %d of %d lanes differ%s"
                      % (kern, a, b, lanes, len(ra), (": " + describe(cols)) if lanes else ""))
                rc = produce(log, "O2", kern, a, True)
                lanes2, cols2, na2, _ = compare(rc, rb, nb)
                log.check(lanes2 == 0, "C3 control %s %s (libcft's transcendentals) = %s bit for bit on %d lanes%s"
                          % (kern, a, b, len(rc), "" if not lanes2 else ": " + describe(cols2)))
    # C5: the hand check at degree 2
    gm, re, co = dec_coeffs()
    pos = lane_positions(100)
    for kind, tol in (("native64", Fraction(1, 10 ** 13)), ("cft64", Fraction(1, 10 ** 13)),
                      ("native32", Fraction(1, 10 ** 5)), ("cft32", Fraction(1, 10 ** 5))):
        rows = g.read_rows(os.path.join(W, "O2_grav2_%s.txt" % kind))[0][:100]
        nb = g.FMT[kind]
        worst = Fraction(0)
        for (x, y, z), r in zip(pos, rows):
            ex = deg2_accel(x, y, z, gm, re, co)
            got = [g.value(h, nb) for h in r[1:4]]
            na = isqrt_frac(sum(e * e for e in ex))
            dd = isqrt_frac(sum((u - v) ** 2 for u, v in zip(got, ex)))
            worst = max(worst, dd / na)
        log.check(worst <= tol, "C5 hand check, degree 2, %s: worst |da|/|a| %.3e <= %.0e on 100 lanes"
                  % (kind, float(worst), float(tol)))
    # C6: the negative control
    for a, b in PAIRS:
        nb = g.FMT[a]
        for kern in ["shadowgeom", "srp", "grav20", "central", "third", "cheb", "drag", "rot"]:
            cr = kern in TRANSC
            ra = produce(log, "negctl", kern, a, cr)
            rb = produce(log, "O2", kern, b, False) if not cr else res[(kern, a, "libm")][1]
            lanes, cols, _, _ = compare(ra, rb, nb)
            where = describe(cols) if lanes else "none"
            log.w("# negctl %s %s against %s: %d lanes differ (%s)" % (kern, a, b, lanes, where))
            if kern == "shadowgeom":
                log.check(lanes >= 1 and cols[0][0] == 0 and cols[1][0] == 0 and cols[2][0] >= 1,
                          "C6 negative control breaks bit-identity in the shadow geometry, %s: %d lanes, all in "
                          "column 3 (cos C); first lane %s" % (a, lanes, cols[2][2]))
            elif kern == "srp":
                log.w("# C6 (reported) radiation pressure uses the geometry: %d lanes differ" % lanes)
            else:
                log.check(lanes == 0, "C6 negative control leaves %s untouched at %s" % (kern, a))
    return log.close()


if __name__ == "__main__":
    sys.exit(main())
