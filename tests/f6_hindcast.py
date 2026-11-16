# f6_hindcast.py - cft-debris M1 (DEBRIS-F), F6: the first hindcast - a measurement, with its sample, statistics,
# bins and controls fixed here before S1 is read.
# cft-debris, MIT licence (see LICENSE at the repository root). Written by DEBRIS-F, 2026-11-16, before S1 existed.
#
#   python -I -B tests/f6_hindcast.py [table] [--no-c]
#
# Per-object results go to the ledger's debris-f\ only (decision 11); this log holds counts and aggregates.
import json
import math
import os
import random
import statistics
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import f_lib as F  # noqa: E402
import f_fit as FF  # noqa: E402
import f5_sample as S  # noqa: E402

CRITERIA = """
A MEASUREMENT (no pass condition), fixed before S1 is read; the CONTROLS are asserted.
THE PAIRS: objects in both S0 and S1 (by NORAD_CAT_ID; ephemeris type 0; built by Orekit in both), whose S1 set has an
  epoch e1 later than their S0 set's e0 by no more than 3 days (0 < e1 - e0 <= 259200 s, from the EPOCH strings, exact).
  If there are more than 200, every `stations` pair is kept and the rest drawn to 200 in all from the other groups in
  proportion to their pair counts (largest remainders, ties to the earlier group), by random.Random(0xF6).sample over
  each group's pairs in catalogue order. e0q and e1q are e0 and e1 rounded to 2^-20 s (tests/f_fit.py).
THE METHODS, each a GCRF position at e1q:
  (A) M1 fitted as B4 to the S0 set's pseudo-observations (a fit of F5(d) reused where the object is in its sample:
      the same S0 set, inputs and build), then propagated from its origin O = e0q - 1 day to e1q (native64, the window's
      table; whole 15 s steps, then one short step landing on e1q);
  (B) SGP4 from the S0 set at e1q;
  (C) Orekit fitted on its own (tests/f6_orekit_fit.js: BatchLSEstimator on the same pseudo-observations, estimating
      the Cartesian state and the drag coefficient; NRLMSISE00 with CelesTrak's SW-Last5Years.txt, Holmes-Featherstone
      20x20 from the same EIGEN-6C4, the Sun and the Moon from the same DE421, radiation pressure with the conical
      shadow and cram 0.01 m^2/kg), propagated to e1q with the same forces; on 50 pairs drawn by
      random.Random(0xF6C).sample from the pairs in catalogue order (all of them if 50 or fewer), and stopped early when
      its JVM's own CPU time reaches 8 minutes (the cycle count, charged by tests/cpurun.py, is kept under 10 minutes).
THE REFERENCE: SGP4 from the S1 set at e1q (at most 0.48 us from e1; the S1 set's own error is part of every miss).
THE MISS: the GCRF distance, and its radial, along-track and cross-track parts in the reference's frame (R along
  r_ref, C along r_ref x v_ref, A = C x R).
THE STATISTICS, per method: the median and the 90th percentile (the ceil(0.9 n)-th smallest) of the miss distance,
  overall and in each cell of perigee band (the S0 set's a(1 - e) - 6378.137 km: under 500, 500 to 800, 800 and over)
  by horizon (e1 - e0: under 6 h, 6 to 24 h, 24 h and over); a cell of fewer than 20 pairs gives its count and median
  only. The share of pairs in which (A) misses less than (B) - the pairs cluster by breakup and by update time, so the
  share is not a sample of independent trials. The ten largest misses of each method, by object, go to the ledger.
CONTROLS, asserted:
  T1 THE TIME TAG, every pair, every method: with the reference moved to e1q + 1 s and the method's position kept at
     e1q, the change in the Cartesian GCRF miss vector must equal the reference's velocity times 1 s within 1% of that
     velocity's size.
  T2 EQUAL SETS: every object (built in both) whose S1 row equals its S0 row in every field gives (B) a miss of exactly
     0 at its epoch.
  T3 SWAPPED IDENTITIES, every pair: (B)'s position against the S1 reference of the next pair in catalogue order
     (cyclically) whose S1 mean motion differs from its own by more than 1e-3 rev/day must miss by more than 100 km.
"""

SEED, SEED_C = 0xF6, 0xF6C
NMAX, NC = 200, 50


def quant(vals, f):
    v = sorted(vals)
    return v[min(len(v) - 1, int(math.ceil(f * len(v))) - 1)]


def ric(dp, r, v):
    rn = math.sqrt(sum(x * x for x in r))
    R = [x / rn for x in r]
    c = [r[1] * v[2] - r[2] * v[1], r[2] * v[0] - r[0] * v[2], r[0] * v[1] - r[1] * v[0]]
    cn = math.sqrt(sum(x * x for x in c))
    C = [x / cn for x in c]
    A = [C[1] * R[2] - C[2] * R[1], C[2] * R[0] - C[0] * R[2], C[0] * R[1] - C[1] * R[0]]
    return [sum(a * b for a, b in zip(dp, R)), sum(a * b for a, b in zip(dp, A)), sum(a * b for a, b in zip(dp, C))]


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    table = args[0] if args else F.DATA + "/tables/frame_main.bin"
    do_c = "--no-c" not in sys.argv
    log = F.Log("f6_hindcast", os.path.abspath(__file__), CRITERIA,
                extra_files=[os.path.join(F.REPO, "tests", "f_fit.py"), os.path.join(F.REPO, "tests", "f5_sgp4.js"),
                             os.path.join(F.REPO, "tests", "f6_orekit_fit.js")])
    exe = F.BUILD + "/m1f_O2.exe"
    log.w("# m1f_O2.exe sha256 %s; table %s sha256 %s" % (F.sha256(exe), table, F.sha256(table)))
    for g in S.GROUPS:
        for tag in ("S0", "S1"):
            p = F.gp_csv(g, tag)
            log.w("# %s sha256 %s" % (os.path.basename(p), F.sha256(p)))
    W = F.WORK + ("/dry/f6" if F.DRY else "/f6")
    os.makedirs(W, exist_ok=True)
    s0, s1 = FF.rows_by_key("S0"), FF.rows_by_key("S1")
    built0 = {ln.split()[1] for ln in open(F.WORK + "/gp/S0_built.txt") if ln.startswith("B ")}
    # S1's build check, as S0's (tests/f5_sample.py S1 must have run)
    built1 = {ln.split()[1] for ln in open(F.gp_dir("S1") + "/S1_built.txt") if ln.startswith("B ")}
    both = sorted((k for k in s0 if k in s1 and k in built0 and k in built1 and s0[k]["EPHEMERIS_TYPE"] == "0" and s1[k]["EPHEMERIS_TYPE"] == "0"), key=int)
    log.w("# objects in both snapshots and built in both: %d" % len(both))

    def secs(d):
        m, s = F.parse_epoch(d["EPOCH"])
        return (m - F.MJD_E) * 86400 + s
    pairs, equal = [], []
    for k in both:
        dt = secs(s1[k]) - secs(s0[k])
        if all(s0[k][c] == s1[k][c] for c in S.COLUMNS):
            equal.append(k)
        if 0 < dt <= 259200:
            pairs.append(k)
    log.w("# candidate pairs (0 < e1 - e0 <= 3 days): %d (%s); equal sets: %d" %
          (len(pairs), ", ".join("%s %d" % (g, sum(1 for k in pairs if s0[k]["GROUP"] == g)) for g in S.GROUPS), len(equal)))
    later = sum(1 for k in both if secs(s1[k]) - secs(s0[k]) > 259200)
    log.w("# excluded as more than 3 days later: %d; S1 not later: %d" % (later, sum(1 for k in both if secs(s1[k]) - secs(s0[k]) <= 0)))
    if len(pairs) > NMAX:
        st = [k for k in pairs if s0[k]["GROUP"] == "stations"]
        rest = NMAX - len(st)
        others = S.GROUPS[1:]
        pool = {g: [k for k in pairs if s0[k]["GROUP"] == g] for g in others}
        tot = sum(len(v) for v in pool.values())
        quota = {g: rest * len(pool[g]) // tot for g in others}
        rema = sorted(others, key=lambda g: (-((rest * len(pool[g])) % tot), S.GROUPS.index(g)))
        for g in rema[:rest - sum(quota.values())]:
            quota[g] += 1
        rng = random.Random(SEED)
        pairs = st + sum((rng.sample(pool[g], quota[g]) for g in others), [])
        pairs = sorted(pairs, key=int)
        log.w("# drawn to %d: %s" % (len(pairs), ", ".join("%s %d" % (g, sum(1 for k in pairs if s0[k]["GROUP"] == g)) for g in S.GROUPS)))
    log.check(len(pairs) > 0, "F6 has pairs (%d)" % len(pairs))
    n = len(pairs)
    e0q = {k: FF.epoch_q(s0[k]) for k in pairs}
    e1q = {k: FF.epoch_q(s1[k]) for k in pairs}
    # (A): fits - F5(d)'s reused where possible
    f5 = {}
    f5log = sorted(p for p in os.listdir(F.LOGS) if p.startswith("f5_gate.") and p.endswith(".log"))
    reuse_path = F.WORK + "/f5/d_fit.txt"
    if os.path.exists(reuse_path):
        for ln in open(reuse_path):
            p = ln.split()
            if p and p[0] == "FIT":
                f5[p[1]] = p
    todo = [k for k in pairs if k not in f5]
    log.w("# (A) fits reused from F5(d) (%s, %s): %d; new fits: %d" % (f5log[-1] if f5log else "-", reuse_path, n - len(todo), len(todo)))
    pv = FF.decode([(k, s0[k], [e0q[k] - 86400.0 + 120.0 * j for j in range(FF.NOBS)]) for k in todo], W, "a", log, cpu_label="f6_decode") if todo else {}
    newfit = FF.fit([(k, s0[k], e0q[k] - 86400.0) for k in todo], pv, W, "a", table, exe, log, cpu_label="f6_fit") if todo else {}
    fits = {}
    for k in pairs:
        if k in f5:
            p = f5[k]
            fits[k] = {"conv": int(p[2]), "t0": float.fromhex(p[8]), "y": [float.fromhex(x) for x in p[9:15]], "bc": float.fromhex(p[15])}
        else:
            fits[k] = newfit[k]
        assert abs(fits[k]["t0"] - (e0q[k] - 86400.0)) == 0.0
    nconv = sum(1 for k in pairs if fits[k]["conv"])
    log.w("# (A) fits converged: %d of %d" % (nconv, n))
    # for F7, written now so that F7 may start while (C) runs (the scratch: derived object by object, never the repository)
    with open(W + "/f6_pairs.json", "w", newline="\n") as f:
        json.dump([{"key": k, "group": s0[k]["GROUP"], "perigee": FF.perigee_alt_km(s0[k]), "e0q": e0q[k], "e1q": e1q[k],
                    "t0": fits[k]["t0"], "y": fits[k]["y"], "bc": fits[k]["bc"], "conv": fits[k]["conv"]} for k in pairs], f)
    log.w("# F7's record written: f6/f6_pairs.json in the scratch (%d pairs)" % n)
    pa = FF.predict([(k, fits[k]["t0"], fits[k]["y"], fits[k]["bc"], [e1q[k]]) for k in pairs], W, "a", table, exe, log=log, cpu_label="f6_prop")
    # (B) and the references at e1q and e1q + 1 s
    pb = FF.decode([(k, s0[k], [e1q[k]]) for k in pairs], W, "b", log, cpu_label="f6_sgp4_b")
    pr = FF.decode([(k, s1[k], [e1q[k], e1q[k] + 1.0]) for k in pairs], W, "ref", log, cpu_label="f6_sgp4_ref")
    # (C)
    pc = {}
    if do_c:
        nc = int(os.environ.get("M1F_DRY_NC", NC)) if F.DRY else NC
        csub = sorted(random.Random(SEED_C).sample(sorted(pairs, key=int), min(nc, n)), key=int)
        # guards from the lead's stage-3 ruling on the space-weather copy (DEBRIS-F's ledger): (C) evaluates the density
        # only from 60 h before a fit span's start (NRLMSISE-00's ap history) to e1, and that must lie inside the span the
        # two-fill check covered (2026-10-14 to 2026-11-18 UTC), and so before 2026-12-30, where the monthly fills reach
        # the inputs
        lo = min(e0q[k] - 86400.0 for k in csub) - 60 * 3600.0
        hi = max(e1q[k] for k in csub)
        t_lo = float(F.utc_to_tdb(F.mjd_of(2026, 10, 14), 0))
        t_hi = float(F.utc_to_tdb(F.mjd_of(2026, 11, 18), 0))
        t_dec30 = float(F.utc_to_tdb(F.mjd_of(2026, 12, 30), 0))
        log.check(hi < t_dec30, "(C) evaluates no density after 2026-12-30 (its latest e1 is %.0f s TDB, 2026-12-30 is %.0f s)" % (hi, t_dec30))
        log.check(t_lo <= lo and hi <= t_hi, "(C)'s dates, ap history included, lie inside the two-fill check's span (%.0f to %.0f s TDB)" % (lo, hi))
        cin = W + "/c_in.txt"
        pvc = FF.decode([(k, s0[k], [e0q[k] - 86400.0 + 120.0 * j for j in range(FF.NOBS)]) for k in csub], W, "c", log, cpu_label="f6_decode_c")
        with open(cin, "w", newline="\n") as f:
            for k in csub:
                f.write("OBJ %s %s %s %s %d\n" % (k, FF.tai_hex(e0q[k] - 86400.0), FF.tai_hex(e1q[k]), " ".join(float.hex(x) for x in pvc[k][0]), FF.NOBS))
                for j in range(FF.NOBS):
                    f.write("O %d %s %s\n" % (j, FF.tai_hex(e0q[k] - 86400.0 + 120.0 * j), " ".join(float.hex(x) for x in pvc[k][j][:3])))
        F.orekit(os.path.join(F.REPO, "tests", "f6_orekit_fit.js"), [cin, W + "/c_out.txt", F.DATA + "/orekit_c3", F.DATA + "/gfc_dedup", F.DATA + "/de421", "480"],
                 log, cpu_label="f6_orekit_C")
        for ln in open(W + "/c_out.txt"):
            p = ln.split()
            if p and p[0] == "C":
                pc[p[1]] = {"pos": [float.fromhex(x) for x in p[2:5]], "iters": p[5], "cd": float.fromhex(p[6])}
            elif ln.startswith("#"):
                log.w("# (C) " + ln.strip())
        log.w("# (C) subset %d pairs; fitted and propagated %d" % (len(csub), len(pc)))
    # misses and controls
    rows, t1bad, nt1 = [], 0, 0
    for k in pairs:
        ref, ref1 = pr[k][0], pr[k][1]
        vref = ref[3:6]
        vn = math.sqrt(sum(x * x for x in vref))
        meth = {"A": pa[k][0][1][:3], "B": pb[k][0][:3]}
        if k in pc:
            meth["C"] = pc[k]["pos"]
        row = {"key": k, "group": s0[k]["GROUP"], "perigee": FF.perigee_alt_km(s0[k]), "horizon_h": (e1q[k] - e0q[k]) / 3600.0}
        for m, p in meth.items():
            dp = [a - b for a, b in zip(p, ref[:3])]
            dp1 = [a - b for a, b in zip(p, ref1[:3])]
            ch = [a - b for a, b in zip(dp, dp1)]
            err = math.sqrt(sum((a - b) ** 2 for a, b in zip(ch, vref)))
            nt1 += 1
            if not err <= 0.01 * vn:
                t1bad += 1
            row[m] = math.sqrt(sum(x * x for x in dp))
            row[m + "_ric"] = ric(dp, ref[:3], vref)
        rows.append(row)
    log.check(t1bad == 0, "T1 the time tag: all %d pair-methods moved by v x 1 s within 1%% of |v|" % nt1)
    # T2 equal sets
    if equal:
        pe0 = FF.decode([(k, s0[k], [FF.epoch_q(s0[k])]) for k in equal], W, "eq0", log)
        pe1 = FF.decode([(k, s1[k], [FF.epoch_q(s1[k])]) for k in equal], W, "eq1", log)
        nz = sum(1 for k in equal if pe0[k][0][:3] != pe1[k][0][:3])
        log.check(nz == 0, "T2 equal sets: all %d objects with equal S0 and S1 rows give (B) a miss of exactly 0 (%d do not)" % (len(equal), nz))
    else:
        log.w("# T2: no object has equal S0 and S1 rows; the control had nothing to check")
    # T3 swapped identities
    srt = sorted(pairs, key=int)
    t3bad = 0
    for i, k in enumerate(srt):
        j = (i + 1) % n
        while srt[j] != k and abs(float(s1[srt[j]]["MEAN_MOTION"]) - float(s1[k]["MEAN_MOTION"])) <= 1e-3:
            j = (j + 1) % n
        if srt[j] == k:
            continue
        d = math.sqrt(sum((a - b) ** 2 for a, b in zip(pb[k][0][:3], pr[srt[j]][0][:3])))
        if not d > 100e3:
            t3bad += 1
    log.check(n < 2 or t3bad == 0, "T3 swapped identities: every pair's (B) misses another's S1 reference by more than 100 km (%d do not)" % t3bad)
    # the statistics
    bands = [("under 500 km", -1e9, 500), ("500 to 800 km", 500, 800), ("800 km and over", 800, 1e9)]
    hors = [("under 6 h", -1, 6), ("6 to 24 h", 6, 24), ("24 h and over", 24, 1e9)]
    for m in ("A", "B", "C"):
        v = [r[m] for r in rows if m in r]
        if not v:
            continue
        log.w("MEASURED %s overall: n %d, median %.3f km, 90th %.3f km" % (m, len(v), statistics.median(v) / 1e3, quant(v, 0.9) / 1e3))
        for bn, b0, b1 in bands:
            for hn, h0, h1 in hors:
                c = [r[m] for r in rows if m in r and b0 <= r["perigee"] < b1 and h0 <= r["horizon_h"] < h1]
                if not c:
                    log.w("MEASURED %s perigee %s, horizon %s: n 0" % (m, bn, hn))
                elif len(c) < 20:
                    log.w("MEASURED %s perigee %s, horizon %s: n %d, median %.3f km" % (m, bn, hn, len(c), statistics.median(c) / 1e3))
                else:
                    log.w("MEASURED %s perigee %s, horizon %s: n %d, median %.3f km, 90th %.3f km" % (m, bn, hn, len(c), statistics.median(c) / 1e3,
                                                                                            quant(c, 0.9) / 1e3))
        rc = [abs(r[m + "_ric"][i]) for r in rows if m in r for i in range(3)]
        log.w("MEASURED %s median |radial| %.3f km, |along| %.3f km, |cross| %.3f km" % (
            m, statistics.median([abs(r[m + "_ric"][0]) for r in rows if m in r]) / 1e3,
            statistics.median([abs(r[m + "_ric"][1]) for r in rows if m in r]) / 1e3,
            statistics.median([abs(r[m + "_ric"][2]) for r in rows if m in r]) / 1e3))
    share = sum(1 for r in rows if r["A"] < r["B"]) / n
    log.w("MEASURED the share of pairs in which (A) misses less than (B): %d of %d = %.3f (the pairs cluster by breakup and update time: not independent trials)"
          % (sum(1 for r in rows if r["A"] < r["B"]), n, share))
    if any("C" in r for r in rows):
        rcs = [r for r in rows if "C" in r]
        log.w("MEASURED on (C)'s subset of %d: (A) median %.3f km, (B) %.3f km, (C) %.3f km; (A) < (C) in %d" % (
            len(rcs), statistics.median([r["A"] for r in rcs]) / 1e3, statistics.median([r["B"] for r in rcs]) / 1e3,
            statistics.median([r["C"] for r in rcs]) / 1e3, sum(1 for r in rcs if r["A"] < r["C"])))
    # per object, ledger only
    os.makedirs(F.LEDGER_F, exist_ok=True)
    per = F.LEDGER_F + "/f6_pairs.%03d.tsv" % log.n
    with open(per, "w", newline="\n") as f:
        f.write("# F6 per-pair misses (derived object by object from CelesTrak's S0 and S1; decision 11: ledger only). log %s\n" % os.path.basename(log.path))
        f.write("key\tgroup\tperigee_km\thorizon_h\tA_m\tA_R\tA_A\tA_C\tB_m\tB_R\tB_A\tB_C\tC_m\tA_fit_converged\n")
        for r in rows:
            f.write("%s\t%s\t%.1f\t%.4f\t%.3f\t%.3f\t%.3f\t%.3f\t%.3f\t%.3f\t%.3f\t%.3f\t%s\t%d\n" % (
                r["key"], r["group"], r["perigee"], r["horizon_h"], r["A"], *r["A_ric"], r["B"], *r["B_ric"],
                ("%.3f" % r["C"]) if "C" in r else "", fits[r["key"]]["conv"]))
        for m in ("A", "B", "C"):
            top = sorted((r for r in rows if m in r), key=lambda r: -r[m])[:10]
            f.write("# ten largest misses of (%s): %s\n" % (m, ", ".join("%s %.1f km" % (r["key"], r[m] / 1e3) for r in top)))
    log.w("# per-pair table and the ten largest misses: the ledger's debris-f\\%s, sha256 %s" % (os.path.basename(per), F.sha256(per)))
    return log.close()


if __name__ == "__main__":
    sys.exit(main())
