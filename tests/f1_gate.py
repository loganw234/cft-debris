# f1_gate.py - cft-debris M1 (DEBRIS-F), gate F1: native against cft, the new kernels (the frame table's
# interpolation, the frame's application, drag co-rotating with the table's Omega), at binary64 and binary32.
# cft-debris, MIT licence (see LICENSE at the repository root). Written by DEBRIS-F, 2026-11-16.
#
#   python -I -B tests/f1_gate.py [table]
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import f_lib as F  # noqa: E402

CRITERIA = """
Lanes: 10,000 (tests/m1f.c mode f1, splitmix64 seed 0xF1), each with its own stage time (uniform over the table's
  interior, a multiple of 2^-21 s), position r (6,600 to 8,000 km), vector b (1e-6 to 1e-1), velocity v (7 to 8 km/s)
  and bc (0.002 to 0.05 m^2/kg). Columns: the 12 interpolated values (M row-major, Omega), M^T r, M b, and drag at
  (r, v, bc) with the lane's Omega and the 28-band atmosphere.
G1 THE GATE: native64 equals cft64 and native32 equals cft32 bit for bit (the NaN rule) in every lane and in the 18
   columns of interpolation and application, which use only addition, multiplication and FMA (and a conversion of u
   from binary64), in the default configuration.
G2 drag (one exp a lane): native equals cft bit for bit in every lane, in the control configuration (--cr: the native
   kinds route exp to libcft's correctly rounded host function). With the C library's exp the differing lanes are
   REPORTED (no pass condition).
NEGATIVE CONTROL C1: the negctl build (tests/build_f.sh: -DM1_NEGCTL_FRAME, the native kinds only, M00 accumulated
   from the last node down) against cft at each width: it must break bit-identity, the first differing column must be
   M00 and the gate names it with its lane count, and the 11 other interpolated values must stay identical in every
   lane (only M00 and the columns built from it may differ).
"""

TABLE = sys.argv[1] if len(sys.argv) > 1 else F.DATA + "/tables/frame_main.bin"
COLS = ["M00", "M01", "M02", "M10", "M11", "M12", "M20", "M21", "M22", "Om0", "Om1", "Om2", "MTr0", "MTr1", "MTr2",
        "Mb0", "Mb1", "Mb2", "drag0", "drag1", "drag2"]
N = 10000


def rows(path):
    return [ln.split() for ln in open(path) if not ln.startswith("#")]


def compare(a, b, nb, cols):
    """per column: lanes differing under the NaN rule"""
    diff = {c: 0 for c in cols}
    first = {}
    for ra, rb in zip(a, b):
        for j, c in enumerate(cols):
            if not F.G.same(ra[1 + j], rb[1 + j], nb):
                diff[c] += 1
                first.setdefault(c, int(ra[0]))
    return diff, first


def main():
    log = F.Log("f1_gate", os.path.abspath(__file__), CRITERIA)
    W = F.WORK + "/f1"
    os.makedirs(W, exist_ok=True)
    exe = {v: F.BUILD + "/m1f_%s.exe" % v for v in ("O2", "negctl")}
    for v, p in exe.items():
        log.w("# m1f_%s.exe sha256 %s" % (v, F.sha256(p)))
    log.w("# table %s sha256 %s" % (TABLE, F.sha256(TABLE)))
    out = {}
    for kind in ("native64", "cft64", "native32", "cft32"):
        out[(kind, "O2", "")] = W + "/%s.txt" % kind
        F.run([exe["O2"], "f1", kind, TABLE, N, "0xF1", out[(kind, "O2", "")]], log, cpu_label="f1_%s" % kind)
    for kind in ("native64", "native32"):
        out[(kind, "O2", "cr")] = W + "/%s_cr.txt" % kind
        F.run([exe["O2"], "f1", kind, TABLE, N, "0xF1", out[(kind, "O2", "cr")], "--cr"], log, cpu_label="f1_%s_cr" % kind)
        out[(kind, "negctl", "")] = W + "/%s_negctl.txt" % kind
        F.run([exe["negctl"], "f1", kind, TABLE, N, "0xF1", out[(kind, "negctl", "")]], log, cpu_label="f1_%s_negctl" % kind)
    for w, (nk, ck) in ((64, ("native64", "cft64")), (32, ("native32", "cft32"))):
        a = rows(out[(nk, "O2", "")])
        b = rows(out[(ck, "O2", "")])
        acr = rows(out[(nk, "O2", "cr")])
        neg = rows(out[(nk, "negctl", "")])
        log.check(len(a) == len(b) == len(acr) == len(neg) == N, "binary%d: %d lanes on every side" % (w, N))
        ina = open(out[(nk, "O2", "")] + ".in").read()
        log.check(ina == open(out[(ck, "O2", "")] + ".in").read(), "binary%d: native and cft drew the same inputs" % w)
        nan = sum(1 for r in a for x in r[1:] if F.G.is_nan(x, w))
        log.w("# binary%d: NaN values in native's output: %d" % (w, nan))
        d, first = compare(a, b, w, COLS)
        g1 = sum(d[c] for c in COLS[:18])
        log.check(g1 == 0, "G1 binary%d: interpolation and application bit for bit in all %d lanes x 18 columns (%d differ)" % (w, N, g1))
        dlib = sum(d[c] for c in COLS[18:])
        log.w("REPORTED binary%d drag with the C library's exp: %d lane-columns differ (%s)" %
              (w, dlib, ", ".join("%s %d" % (c, d[c]) for c in COLS[18:])))
        dcr, _ = compare(acr, b, w, COLS)
        log.check(sum(dcr.values()) == 0, "G2 binary%d (--cr): all 21 columns bit for bit in all %d lanes (%d differ)" % (w, N, sum(dcr.values())))
        dn, fn = compare(neg, b, w, COLS)
        firstcol = next((c for c in COLS if dn[c]), None)
        log.w("# C1 binary%d: columns differing: %s; first differing column %s (first lane %s)" %
              (w, ", ".join("%s %d" % (c, dn[c]) for c in COLS if dn[c]) or "none", firstcol, fn.get(firstcol)))
        others = sum(dn[c] for c in COLS[1:12])
        log.check(dn["M00"] > 0 and firstcol == "M00" and others == 0,
                  "C1 binary%d FAILS as specified: M00 differs in %d lanes, named first; the other 11 interpolated values identical" % (w, dn["M00"]))
    return log.close()


if __name__ == "__main__":
    sys.exit(main())
