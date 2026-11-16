# f5_gate.py - cft-debris M1 (DEBRIS-F), gate F5: the decoder and the fit.
# cft-debris, MIT licence (see LICENSE at the repository root). Written by DEBRIS-F, 2026-11-16.
#
#   python -I -B tests/f5_gate.py [table]
#
# Per-object results (derived object by object from GP data) go to the ledger's debris-f\ only (decision 11); this
# log holds counts and aggregate statistics.
import math
import os
import statistics
import sys
from fractions import Fraction

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import f_lib as F  # noqa: E402
import f_fit as FF  # noqa: E402
import f5_sample as S  # noqa: E402

CRITERIA = """
(a) THE DECODER'S INPUT: for every S0 row Orekit built (tests/f5_sample.py), each number converted to Orekit's units
    (f5_sample.py: n, ndot, nddot, e, i, argp, raan, M, bstar) equals, as a binary64, what the TLE's getter returns;
    the catalogue number equals getSatelliteNumber() (6-digit ones included); and the epoch, Orekit's parse of the
    EPOCH string, lies within 1e-9 s of ours (exact UTC to TAI from tai-utc.dat; binary64 holds 3e6 s to 4.7e-10 s).
(b) SENSITIVITY CONTROL: for the ISS (25544), SGP4 from its S0 set with the mean motion planted 1e-6 rev/day high
    (+7.272e-11 rad/s): at e0 - 1 day the position must move by a dn |dt| within 5% (a = (mu/n^2)^(1/3), the
    along-track drift of the mean anomaly over |dt| = 86400 s; COMPUTED in the log before the run), and at e0 by at
    most 1 m (only the semi-major axis's -2/3 a dn/n, about 0.3 m).
(c) SYNTHETIC TRUTH: M1 itself (m1f prop, native64, the window's table) makes 721 positions every 120 s over a day
    from the state chosen here - r = (6778137, 0, 0) m, v = (0, 4768.2, 6013.4) m/s (about 400 km, 51.6 degrees), at
    t0 = 1,000,000 s TDB from JD 2461329.5, bc = 0.005 m^2/kg, cram 0.01 - and B4's fit recovers them from a start
    1 km and 0.6 m/s off ((+1000, -500, +300) m, (+0.5, -0.3, +0.2) m/s) with bc starting at 0.01: it must converge
    within 10 iterations, and recover |dr| <= 1e-3 m, |dv| <= 1e-6 m/s and |dbc|/bc <= 1e-6 (the pseudo-observations
    are the fit model's own, so only rounding and the stopping threshold are left).
(d) THE FIT ON S0's SAMPLE (a measurement, no pass condition): the 100 objects of tests/f5_sample.py; pseudo-
    observations from SGP4 at the S0 set; the fit as B4; reported: the counts of fits that converged and that stopped
    on the iteration limit, the counts fitting bc (perigee under 1,000 km), and the post-fit RMS of the position
    residuals' lengths (median, 90th percentile, largest), overall and by group.
"""


def main():
    table = sys.argv[1] if len(sys.argv) > 1 else F.DATA + "/tables/frame_main.bin"
    log = F.Log("f5_gate", os.path.abspath(__file__), CRITERIA,
                extra_files=[os.path.join(F.REPO, "tests", "f5_sgp4.js"), os.path.join(F.REPO, "tests", "f_fit.py"),
                             os.path.join(F.REPO, "tests", "f5_sample.py")])
    exe = F.BUILD + "/m1f_O2.exe"
    log.w("# m1f_O2.exe sha256 %s; table %s sha256 %s" % (F.sha256(exe), table, F.sha256(table)))
    W = F.WORK + "/f5"
    os.makedirs(W, exist_ok=True)
    G = F.WORK + "/gp"
    rows = FF.rows_by_key("S0")
    # (a)
    built = {}
    for ln in open(G + "/S0_built.txt"):
        p = ln.split()
        if p and p[0] == "B":
            built[p[1]] = p
    log.check(len(built) == 2696, "(a) the S0 build run holds 2696 objects")
    ref = (F.MJD_E - F.MJD_E) * 86400  # TAI seconds from MJD 61329.0 TAI
    bad, worst_ep = 0, 0.0
    for key, p in built.items():
        d = rows[key]
        _, vals = S.orekit_line(d, key)
        bstar = float(d["BSTAR"])
        got = [float.fromhex(x) for x in p[4:13]]
        ok = got[:8] == vals and got[8] == bstar and int(p[3]) == int(d["NORAD_CAT_ID"])
        mjd, sec = F.parse_epoch(d["EPOCH"])
        tai = (mjd - F.MJD_E) * 86400 + sec + F.dat(Fraction(mjd) + sec / 86400) - ref
        de = abs(float(Fraction(float.fromhex(p[13])) - tai))
        worst_ep = max(worst_ep, de)
        if not ok or de > 1e-9:
            bad += 1
    log.w("# (a) objects with any mismatch: %d of %d; largest epoch difference %.3e s" % (bad, len(built), worst_ep))
    log.check(bad == 0, "(a) every getter equals our converted value, and every epoch within 1e-9 s")
    # (b)
    key = "25544"
    d = rows[key]
    e0 = FF.epoch_q(d)
    n = float(d["MEAN_MOTION"]) * math.pi / 43200.0
    a = (FF.MU / (n * n)) ** (1.0 / 3.0)
    dn = 1e-6 * math.pi / 43200.0
    expect = a * dn * 86400.0
    log.w("# (b) COMPUTED before the run: a = %.1f m, dn = %.4e rad/s, expected |dr| at e0 - 1 day = %.3f m (5%%: %.3f to %.3f)"
          % (a, dn, expect, 0.95 * expect, 1.05 * expect))
    ts = [e0 - 86400.0, e0]
    p0 = FF.decode([(key, d, ts)], W, "b_plain", log)
    p1 = FF.decode([(key, d, ts)], W, "b_plant", log, plant_dn=dn)
    dr = [math.sqrt(sum((x - y) ** 2 for x, y in zip(u[:3], v[:3]))) for u, v in zip(p0[key], p1[key])]
    log.w("# (b) measured |dr|: %.3f m at e0 - 1 day, %.3f m at e0" % (dr[0], dr[1]))
    log.check(0.95 * expect <= dr[0] <= 1.05 * expect and dr[1] <= 1.0, "(b) the planted mean motion moved SGP4 as computed")
    # (c)
    t0 = 1000000.0
    truth = [6778137.0, 0.0, 0.0, 0.0, 4768.2, 6013.4]
    bct = 0.005
    obs_t = [t0 + 120.0 * k for k in range(FF.NOBS)]
    gen = FF.predict([("SYN", t0, truth, bct, obs_t)], W, "c_truth", table, exe, log=log, cpu_label="f5c_truth")
    pos = [s for _, s, _ in gen["SYN"]]
    log.check(len(pos) == FF.NOBS, "(c) M1 made %d pseudo-observations" % len(pos))
    start = [truth[0] + 1000, truth[1] - 500, truth[2] + 300, truth[3] + 0.5, truth[4] - 0.3, truth[5] + 0.2]
    path_in = W + "/c_fit_in.txt"
    with open(path_in, "w", newline="\n") as f:
        f.write("OBJ SYN %s %s %s %s 1 %d 0\n" % (float.hex(t0), " ".join(float.hex(x) for x in start), float.hex(0.01), float.hex(FF.CRAM), FF.NOBS))
        for k in range(FF.NOBS):
            f.write("O %d %s\n" % (k, " ".join(float.hex(x) for x in pos[k][:3])))
    F.run([exe, "fit", table, path_in, W + "/c_fit.txt"], log, cpu_label="f5c_fit")
    fr = [ln.split() for ln in open(W + "/c_fit.txt") if ln.startswith("FIT")][0]
    yv = [float.fromhex(x) for x in fr[9:15]]
    bcf = float.fromhex(fr[15])
    ddr = math.sqrt(sum((yv[i] - truth[i]) ** 2 for i in range(3)))
    ddv = math.sqrt(sum((yv[i] - truth[i]) ** 2 for i in range(3, 6)))
    log.w("# (c) converged %s after %s iterations; |dr| %.3e m, |dv| %.3e m/s, dbc/bc %.3e; post-fit RMS %.3e m" %
          (fr[2], fr[3], ddr, ddv, (bcf - bct) / bct, float.fromhex(fr[4])))
    log.check(fr[2] == "1" and int(fr[3]) <= 10 and ddr <= 1e-3 and ddv <= 1e-6 and abs(bcf - bct) / bct <= 1e-6,
              "(c) the synthetic truth recovered within its tolerances")
    # (d)
    keys = [ln.strip() for ln in open(G + "/f5d_sample.txt") if ln.strip()]
    log.check(len(keys) == 100, "(d) the sample holds 100 keys")
    objs, fobj = [], []
    for k in keys:
        dd = rows[k]
        e0 = FF.epoch_q(dd)
        O = e0 - 86400.0
        objs.append((k, dd, [O + 120.0 * j for j in range(FF.NOBS)]))
        fobj.append((k, dd, O))
    pv = FF.decode(objs, W, "d", log, cpu_label="f5d_decode")
    nok = sum(1 for k in keys if pv.get(k) and len(pv[k]) == FF.NOBS)
    log.check(nok == 100, "(d) the decoder gave 721 states for each of the 100 (%d)" % nok)
    res = FF.fit(fobj, pv, W, "d", table, exe, log, cpu_label="f5d_fit")
    log.check(len(res) == 100, "(d) 100 fits returned")
    conv = [k for k in keys if res[k]["conv"]]
    nbc = sum(1 for k in keys if res[k]["fitbc"])
    rms = sorted(res[k]["rms"] for k in keys)
    def q(v, f):
        return v[min(len(v) - 1, int(math.ceil(f * len(v))) - 1)]
    log.w("MEASURED (d): converged %d, stopped on the iteration limit %d; fitting bc %d; post-fit RMS median %.1f m, 90th %.1f m, largest %.1f m"
          % (len(conv), 100 - len(conv), nbc, statistics.median(rms), q(rms, 0.9), rms[-1]))
    for g in S.GROUPS:
        r = sorted(res[k]["rms"] for k in keys if rows[k]["GROUP"] == g)
        if r:
            log.w("MEASURED (d) %s: %d objects, converged %d, RMS median %.1f m, largest %.1f m" %
                  (g, len(r), sum(1 for k in keys if rows[k]["GROUP"] == g and res[k]["conv"]), statistics.median(r), r[-1]))
    its = sorted(res[k]["iter"] for k in keys)
    log.w("MEASURED (d): iterations median %d, largest %d" % (statistics.median(its), its[-1]))
    os.makedirs(F.LEDGER_F, exist_ok=True)
    per = F.LEDGER_F + "/f5d_fits.%03d.tsv" % log.n
    with open(per, "w", newline="\n") as f:
        f.write("# F5(d) per-object fits (derived object by object from CelesTrak's S0; decision 11: ledger only). log %s\n" % os.path.basename(log.path))
        f.write("key\tgroup\tperigee_km\tfitbc\tconverged\titerations\trms_m\tmaxres_m\tbc\tt0_tdb\n")
        for k in keys:
            r = res[k]
            f.write("%s\t%s\t%.1f\t%d\t%d\t%d\t%.3f\t%.3f\t%.6g\t%s\n" % (k, rows[k]["GROUP"], FF.perigee_alt_km(rows[k]), r["fitbc"], r["conv"], r["iter"],
                                                                     r["rms"], r["maxres"], r["bc"], float.hex(r["t0"])))
    log.w("# per-object table: the ledger's debris-f\\%s, sha256 %s" % (os.path.basename(per), F.sha256(per)))
    return log.close()


if __name__ == "__main__":
    sys.exit(main())
