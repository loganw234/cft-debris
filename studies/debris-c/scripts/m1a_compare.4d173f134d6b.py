#!/usr/bin/env python3
"""DEBRIS-C, M1a: the gravity field (layer 3) held to Lasser et al. 2020.

  python -I -B m1a_compare.py

CONVENTIONS (established before any comparison; sources in brackets):
- coefficient file: models/EIGEN6-C4.gfc of the benchmark [README "02 gravity
  field"], SHA-256 b5d58320... (lead.md). Header [the file]: icgem2.0,
  EIGEN-6C4_180, max_degree 180, fully_normalized.
- GM 0.3986004415E+15 m^3/s^2 and reference radius 0.6378136460E+07 m, from the
  file's header; all three use the file's values.
- tide system: tide_free [header]. Nobody converts it, so all three use the
  coefficients as written.
- degrees: the benchmark's accelerations use degree/order 2..180 [README], so
  the central term (degree 0) is excluded; degree 1 is absent from the file
  (MEASURED, m1a_grav's count: 2 missing terms, both degree 1) and so zero.
  The custom kernel sums 2..180. Orekit's gradient() is "the gradient of the
  non-central part" with sums from n = max(2, m) [READ via WebFetch,
  HolmesFeatherstoneAttractionModel.java at tag 13.1.9], so 2..180 too:
  nothing is added or subtracted.
- time-variable terms: none. The file's data keys are all "gfc" (MEASURED:
  no gfct, trnd, acos or asin lines), so the field is static and evaluates
  the same on 3 July 2008 as on any day.
- frame: Lasser et al.'s TRF accelerations at the TRF positions of
  00orbit_itrf.txt, the same 2,880 epochs; everyone evaluates in the
  Earth-fixed frame, so no rotation enters.
- files read: the custom kernel reads the download; Orekit reads the
  de-duplicated copy (lead.md 18:07). The kernel's output from the copy is
  bit-identical to its output from the download (asserted below).

TOLERANCE (stated before the run): TOL = 1e-11 m/s^2 on the maximum over the
day of |delta a|, the Euclidean norm of the vector difference at each epoch.
Basis: 1e-11 m/s^2 is the threshold the COST-G packages met for each force
(READ via WebFetch, Lasser et al. 2020). Applied to the norm, which is
stricter than per component. The same TOL is applied to custom vs Orekit,
which is two of ours agreeing, not an authority.

NEGATIVE CONTROL (stated before the run): truncation at D = 173, chosen
before any comparison by m1a_control_degree.py (its log
m1a_control_degree.001.log: omitted RMS 1.09e-10 m/s^2 at the orbit's
largest radius, 10.9 x TOL). PASS iff the comparison with Lasser et al.
REPORTS it, max |delta a| > TOL, for the custom kernel and for Orekit alike.
"""
import hashlib
import math
import sys

D = "C:/Users/logan/source/repos/cft-debris-downloads/"
LASSER = D + "02gravityfield_itrf.txt/02gravityfield_itrf.txt"
OUT = "C:/Users/logan/source/repos/cft-debris/studies/debris-c/m1a/out/"
TOL = 1e-11
CONTROL_D = 173


def read_lasser(path):
    rows = []
    for ln in open(path):
        t = ln.split()
        if len(t) == 4 and not ln.startswith("#"):
            try:
                rows.append((float(t[0]), float(t[1]), float(t[2]), float(t[3])))
            except ValueError:
                pass
    return rows


def read_hex(path, cols=(1, 2, 3)):
    rows = []
    for ln in open(path):
        t = ln.split()
        rows.append((float(t[0]),) + tuple(float.fromhex(t[c]) for c in cols))
    return rows


def compare(a, b, name):
    assert len(a) == len(b) == 2880, (name, len(a), len(b))
    dmax, s2, imax = 0.0, 0.0, -1
    cmax = [0.0, 0.0, 0.0]
    amax = 0.0
    for i, (ra, rb) in enumerate(zip(a, b)):
        assert abs(ra[0] - rb[0]) < 1e-9, ("epoch mismatch", name, i, ra[0], rb[0])
        d = [ra[k] - rb[k] for k in (1, 2, 3)]
        n = math.sqrt(sum(x * x for x in d))
        amax = max(amax, math.sqrt(sum(x * x for x in ra[1:])))
        for k in range(3):
            cmax[k] = max(cmax[k], abs(d[k]))
        s2 += n * n
        if n > dmax:
            dmax, imax = n, i
    rms = math.sqrt(s2 / len(a))
    print("%-44s max |da| %.3e m/s^2 (epoch %4d), RMS %.3e; per component max %.2e %.2e %.2e; max |a| %.3e"
          % (name, dmax, imax, rms, cmax[0], cmax[1], cmax[2], amax))
    return dmax, rms


def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def main():
    print("# M1a: TOL = %.0e m/s^2 on max |delta a| over the day (vector norm); control: truncation at D = %d"
          % (TOL, CONTROL_D))
    for p in (LASSER, OUT + "c_O2_2_180.txt", OUT + "c_O2_2_180_copy.txt", OUT + "c_O2_2_173.txt",
              OUT + "orekit_2_180.txt", OUT + "orekit_2_173.txt"):
        print("# input %s sha256 %s" % (p, sha(p)))
    assert sha(OUT + "c_O2_2_180.txt") == sha(OUT + "c_O2_2_180_copy.txt"), "kernel output differs between download and copy"
    print("# the custom kernel's output from the copy is bit-identical to its output from the download")
    L = read_lasser(LASSER)
    C = read_hex(OUT + "c_O2_2_180.txt")
    O = read_hex(OUT + "orekit_2_180.txt")
    Ct = read_hex(OUT + "c_O2_2_173.txt")
    Ot = read_hex(OUT + "orekit_2_173.txt")
    res = {}
    res["c"] = compare(C, L, "custom C (2..180) vs Lasser et al.")
    res["o"] = compare(O, L, "Orekit HF (2..180) vs Lasser et al.")
    res["co"] = compare(C, O, "custom C vs Orekit (two of ours)")
    res["ct"] = compare(Ct, L, "CONTROL custom C (2..173) vs Lasser et al.")
    res["ot"] = compare(Ot, L, "CONTROL Orekit HF (2..173) vs Lasser et al.")
    res["ctot"] = compare(Ct, Ot, "custom C (2..173) vs Orekit (2..173)")
    ok = True
    for k, label in (("c", "custom vs Lasser"), ("o", "Orekit vs Lasser"), ("co", "custom vs Orekit")):
        p = res[k][0] < TOL
        ok &= p
        print("%s %s: max %.3e %s TOL %.0e" % ("PASS" if p else "FAIL", label, res[k][0], "<" if p else ">=", TOL))
    for k, label in (("ct", "control, custom truncated at 173"), ("ot", "control, Orekit truncated at 173")):
        p = res[k][0] > TOL
        ok &= p
        print("%s %s: the comparison %s it (max %.3e = %.1f x TOL)"
              % ("PASS" if p else "FAIL", label, "reports" if p else "does NOT report", res[k][0], res[k][0] / TOL))
    print("# M1a %s" % ("PASS" if ok else "FAIL"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
