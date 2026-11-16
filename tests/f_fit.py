# f_fit.py - cft-debris M1 (DEBRIS-F): B3 and B4's orchestration, shared by F5 and F6 - each object's exact origin,
# the decoder's pseudo-observations, M1's fit (tests/m1f.c fit) and its predictions (tests/m1f.c prop).
# cft-debris, MIT licence (see LICENSE at the repository root). Written by DEBRIS-F, 2026-11-16.
#
# Each object's run (B1): e0 = the GP set's EPOCH (UTC) in TDB seconds from JD 2461329.5, exact but for eq. (2.6),
# rounded to the nearest multiple of 2^-20 s (e0q, at most 0.48 us away); the origin O = e0q - 86400 s, exactly; the
# pseudo-observations at O + 120 k, k = 0..720 (every 8th rk4 step of 15 s), ending on e0q exactly; a prediction to
# e1q (the same rounding of e1) runs whole steps to O + 15 N <= e1q and one short step hs = e1q - (O + 15 N), exact.
# Each instant goes to Orekit as TAI seconds from 2026-10-16T00:00:00 TAI (binary64, within 2.3e-10 s).
import math
import os
import sys
from fractions import Fraction

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import f_lib as F  # noqa: E402
import f5_sample as S  # noqa: E402

MU = 3.986004418e14
CRAM = 0.01          # radiation pressure: Cr A/m fixed at 0.01 m^2/kg for every object (a stated limit)
BC0 = 0.01           # the drag parameter's start, and its fixed value where perigee is 1,000 km or higher
NOBS = 721


def rows_by_key(tag):
    return {d["NORAD_CAT_ID"]: d for d in S.parse(tag)}


def epoch_q(d):
    mjd, sec = F.parse_epoch(d["EPOCH"])
    return F.quantize(F.utc_to_tdb(mjd, sec))


def perigee_alt_km(d):
    n = float(d["MEAN_MOTION"]) * math.pi / 43200.0
    a = (MU / (n * n)) ** (1.0 / 3.0)
    return (a * (1.0 - float(d["ECCENTRICITY"])) - 6378137.0) / 1000.0


def tai_hex(t):
    return float.hex(float(F.tdb_to_tai(Fraction(t))))


def decode(objs, W, tag, log=None, cpu_label=None, plant_dn=None):
    """objs: list of (key, row, [TDB instants]); returns {key: [(x, y, z, vx, vy, vz)] in instant order}"""
    path_in, path_out = W + "/%s_pv_in.txt" % tag, W + "/%s_pv.txt" % tag
    with open(path_in, "w", newline="\n") as f:
        for key, d, ts in objs:
            line, _ = S.orekit_line(d, key)
            f.write(line + " %d%s\n" % (len(ts), (" " + float.hex(plant_dn)) if plant_dn else ""))
            for k, t in enumerate(ts):
                f.write("I %d %s\n" % (k, tai_hex(t)))
    F.orekit(os.path.join(F.REPO, "tests", "f5_sgp4.js"), ["pv", F.DATA + "/orekit", path_in, path_out], log, cpu_label=cpu_label)
    out = {}
    for ln in open(path_out):
        p = ln.split()
        if p and p[0] == "V":
            out.setdefault(p[1], []).append(tuple(float.fromhex(x) for x in p[4:10]))
        elif p and p[0] == "F":
            out[p[1]] = None
    return out


def fit(objs, pv, W, tag, table, exe, log=None, cpu_label=None, maxit=10):
    """objs: list of (key, row, O); pv: {key: 721 states}; returns {key: dict}"""
    path_in, path_out = W + "/%s_fit_in.txt" % tag, W + "/%s_fit.txt" % tag
    with open(path_in, "w", newline="\n") as f:
        for key, d, O in objs:
            s = pv[key]
            fitbc = 1 if perigee_alt_km(d) < 1000.0 else 0
            f.write("OBJ %s %s %s %s %s %d %d 0\n" % (key, float.hex(O), " ".join(float.hex(x) for x in s[0]), float.hex(BC0), float.hex(CRAM),
                                                    fitbc, NOBS))
            for k in range(NOBS):
                f.write("O %d %s\n" % (k, " ".join(float.hex(x) for x in s[k][:3])))
    F.run([exe, "fit", table, path_in, path_out, "--maxit", str(maxit)], log, cpu_label=cpu_label)
    res = {}
    for ln in open(path_out):
        p = ln.split()
        if p and p[0] == "FIT":
            v = [float.fromhex(x) for x in p[4:6]] + [float.fromhex(x) for x in p[8:16]]
            res[p[1]] = {"conv": int(p[2]), "iter": int(p[3]), "rms": v[0], "maxres": v[1], "fitbc": int(p[7]), "t0": v[2],
                         "y": v[3:9], "bc": v[9]}
    return res


def predict(items, W, tag, table, exe, kind="native64", log=None, cpu_label=None):
    """items: list of (key, t0, y[6], bc, [targets]); returns {key: [(T, state6)]}"""
    path_in, path_out = W + "/%s_prop_in.txt" % tag, W + "/%s_prop_%s.txt" % (tag, kind)
    with open(path_in, "w", newline="\n") as f:
        for key, t0, y, bc, tg in items:
            f.write("OBJ %s %s %s %s %s 0 0 %d\n" % (key, float.hex(t0), " ".join(float.hex(x) for x in y), float.hex(bc), float.hex(CRAM), len(tg)))
            for k, T in enumerate(tg):
                f.write("T %d %s\n" % (k, float.hex(T)))
    F.run([exe, "prop", kind, table, path_in, path_out], log, cpu_label=cpu_label)
    out = {}
    for ln in open(path_out):
        p = ln.split()
        if p and p[0] == "P":
            out.setdefault(p[1], []).append((float.fromhex(p[2]), [float.fromhex(x) for x in p[3:9]], p[9:15]))
    return out
