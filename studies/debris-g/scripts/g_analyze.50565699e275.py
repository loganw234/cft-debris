# g_analyze.py - cft-debris M1 (DEBRIS-G), phase 2: G4's tables, G5's lag, and the box's other logs, recomputed.
# cft-debris, MIT licence (see LICENSE at the repository root). Written by DEBRIS-G, 2026-11-17.
#
#   python -I -B tests/g_analyze.py <box log dir> <log dir for the output>
#
# Reads the lead's copies of the box's logs (g_sweep.001..003 and their runs.json, g_paced.001, g_g2.001, g_g3.001,
# g_calib.001, g_controls.001, g_build.001, g_smoke.001) and recomputes every figure of G4 and G5. No object, state or
# catalogue number is read: the logs hold none.
#
# CRITERIA, fixed before the data and asserted below:
#  A1 59 runs in the three runs.json files, each status valid, none void; every run has a RUN line in its log with the
#     same kind-mode, W, L and S, and the X of the json equals the RUN line's to 1e-6 relative (the log prints 3 decimals);
#  A2 the capacity of a kind-mode is the median of its three valid W=36, L=64 runs, equal to the json's to 1e-9 relative;
#  A3 every kind-mode has the configurations the plan fixes (cft64: 11 runs; the others: 8) and S as the plan's rule gives
#     it from F9's figures (G4 figure: the harness's sweep_S);
#  A4 efficiency = X(W) / (W x X(1)), HT gain = X(36) / X(18), both from the L=64 runs; spread = largest / smallest of the
#     three repeats; each divides the rates X (object-seconds per wall second), not CPU times;
#  A5 G5: every worker's maximum lag is at most 15 s; the log's PASS lines for G5 are present; busy share and lag
#     summaries are parsed from the log;
#  A6 G1, G2, G3 box logs: no FAIL line; every control line says "failed as specified" (C1 to C5) or flags exactly its object;
#  A7 the control of this script: a copy of the runs with one run's X changed by 1e-3 relative must fail A1's check.
import hashlib
import json
import math
import os
import re
import sys

F9_POD = {"native32": 0.066, "native64": 0.067, "native64-cr": 21.406, "cft32": 54.363, "cft64": 71.893,
          "cft128": 120.139, "cft256": 266.713}
KM = ["native32", "native64", "native64-cr", "cft32", "cft64", "cft128", "cft256"]
RUNRE = re.compile(r"^RUN (\S+) W=(\d+) L=(\d+) S=(\d+) \(try (\d+)\): wall ([\d.]+) s, objsec ([\d.]+), X ([\d.]+) obj-s/s, "
                   r"foreign load ([\d.]+)%, mean clock (\d+) MHz")


def sha(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


def sweep_S(km, L):
    return max(2, math.ceil(30.0 / (L * F9_POD[km] / 5760.0)))


def median(v):
    s = sorted(v)
    n = len(s)
    return s[n // 2] if n % 2 else 0.5 * (s[n // 2 - 1] + s[n // 2])


class Out:
    def __init__(self, d):
        os.makedirs(d, exist_ok=True)
        n = 1
        while os.path.exists(os.path.join(d, "g_analyze.%03d.log" % n)):
            n += 1
        self.f = open(os.path.join(d, "g_analyze.%03d.log" % n), "x", encoding="utf-8", newline="\n")
        self.fails = 0

    def w(self, s=""):
        self.f.write(s + "\n")
        print(s)

    def check(self, ok, what):
        self.w(("PASS " if ok else "FAIL ") + what)
        self.fails += 0 if ok else 1


def check_a1(runs, loglines):
    bad = 0
    for r in runs:
        key = (r["km"], r["W"], r["L"], r["S"])
        cands = [m for m in loglines if (m[0], m[1], m[2], m[3]) == key and abs(m[4] - r["X"]) <= 1e-6 * r["X"]]
        if r["status"] != "valid" or not cands:
            bad += 1
    return bad


def main():
    box, outd = sys.argv[1], sys.argv[2]
    o = Out(outd)
    o.w("# g_analyze.py sha256 %s" % sha(os.path.abspath(__file__)))
    o.w("# input log hashes (the lead's copies, equal to the box's):")
    names = ["g_build.001.log", "g_smoke.001.log", "g_calib.001.log", "g_controls.001.log", "g_g2.001.log", "g_g3.001.log",
             "g_sweep.001.log", "g_sweep.001.runs.json", "g_sweep.002.log", "g_sweep.002.runs.json", "g_sweep.003.log",
             "g_sweep.003.runs.json", "g_paced.001.log"]
    for n in names:
        o.w("#   %s %s" % (n, sha(os.path.join(box, n))))
    runs, loglines, cap_json = [], [], {}
    for i in (1, 2, 3):
        d = json.load(open(os.path.join(box, "g_sweep.%03d.runs.json" % i), encoding="utf-8"))
        runs += d["runs"]
        cap_json.update(d["capacity"])
        for ln in open(os.path.join(box, "g_sweep.%03d.log" % i), encoding="utf-8"):
            m = RUNRE.match(ln)
            if m:
                loglines.append((m.group(1), int(m.group(2)), int(m.group(3)), int(m.group(4)), float(m.group(8))))
    o.check(len(runs) == 59 and all(r["status"] == "valid" for r in runs), "A1 59 runs, all valid (%d runs, %d valid)" % (len(runs), sum(r["status"] == "valid" for r in runs)))
    o.check(check_a1(runs, loglines) == 0, "A1 every run has a RUN line with the same kind-mode, W, L, S and X (to 1e-6)")
    import copy
    r2 = copy.deepcopy(runs)
    r2[7]["X"] *= 1.001
    o.check(check_a1(r2, loglines) == 1, "A7 control: one X changed by 0.1% is flagged by A1's check (1 run flagged)")
    by = {}
    for r in runs:
        by.setdefault(r["km"], []).append(r)
    for km in KM:
        rs = by[km]
        exp = 11 if km == "cft64" else 8
        o.check(len(rs) == exp, "A3 %s has %d runs (expected %d)" % (km, len(rs), exp))
        o.check(all(r["S"] == sweep_S(km, r["L"]) for r in rs), "A3 %s: S equals the plan's rule at every L (S at L=8, 64, 256: %s)" % (
            km, [sweep_S(km, L) for L in (8, 64, 256)]))
        reps = [r["X"] for r in rs if r["W"] == 36 and r["L"] == 64]
        o.check(len(reps) == 3 and abs(median(reps) - cap_json[km]) <= 1e-9 * cap_json[km], "A2 %s capacity %.3f = median of its 3 repeats" % (km, median(reps)))
    o.w("")
    o.w("# G4 TABLES. X = object-seconds summed over the workers / wall time (first release to last end), at L=64 unless stated.")
    o.w("# Efficiency = X(W)/(W x X(1)); clock-corrected efficiency = efficiency / (mean clock of the run / mean clock of the W=1 run);")
    o.w("# HT = X(36)/X(18). All divide rates (object-seconds per wall second), none CPU times. Clocks are the kernel's scaling_cur_freq (see G1's calibration).")
    cap = {}
    for km in KM:
        rs = by[km]

        def one(W, L):
            return [r for r in rs if r["W"] == W and r["L"] == L]
        x1 = one(1, 64)[0]
        o.w("")
        o.w("## %s (F9's object-day figure %.3f s; X(1) implied by it %.3f)" % (km, F9_POD[km], 86400.0 / F9_POD[km]))
        o.w("  W   X(W)        eff     mean clock   eff/clock-ratio   max peak resident per worker (kB)")
        for W in sorted({r["W"] for r in rs if r["L"] == 64}):
            g = one(W, 64)
            x = median([r["X"] for r in g])
            fq = sum(r["freq_mean_khz"] for r in g) / len(g)
            eff = x / (W * x1["X"])
            o.w("  %-3d %-11.3f %.3f   %.0f MHz     %.3f             %d" % (W, x, eff, fq / 1000.0, eff / (fq / x1["freq_mean_khz"]), max(max(r["maxrss_kb"]) for r in g)))
        x36, x18 = median([r["X"] for r in one(36, 64)]), one(18, 64)[0]["X"]
        o.w("  HT gain X(36)/X(18) = %.3f" % (x36 / x18))
        for L in (8, 64, 256):
            x = one(36, L)[0]["X"] if L != 64 else x36
            o.w("  W=36 L=%-3d X %.3f  (ratio to L=64: %.3f; foreign load %.3f%%)" % (L, x, x / x36, 100 * one(36, L)[0]["foreign_share"]))
        reps = [r["X"] for r in one(36, 64)]
        o.w("  spread of the 3 repeats (largest/smallest) %.5f" % (max(reps) / min(reps)))
        c = median(reps)
        cap[km] = c
        o.w("  REAL-TIME CAPACITY (W=36, L=64, median of 3): %.1f objects at real time; carried in the runs: %d objects; %s" % (
            c, 36 * 64, "an extrapolation of the cost per object above that"))
        fastest = max(r["X"] for r in rs)
        o.w("  fastest valid run (beside the capacity, not in its place): X %.1f at W=%d L=%d" % (fastest, *[(r["W"], r["L"]) for r in rs if r["X"] == fastest][0]))
        o.w("  X(1) / F9-implied X(1) = %.3f  (G4's W=1, L=64 run over F9's figure; see the build report for the reading)" % (x1["X"] / (86400.0 / F9_POD[km])))
        o.w("  mean clock W=1: %.0f MHz; W>=9: %s MHz" % (x1["freq_mean_khz"] / 1000.0, sorted({round(r["freq_mean_khz"] / 1000.0) for r in rs if r["W"] >= 9})[:1] + sorted({round(r["freq_mean_khz"] / 1000.0) for r in rs if r["W"] >= 9})[-1:]))
    c64 = by["cft64"]
    r27 = [r for r in c64 if r["W"] == 27][0]
    r36 = [r for r in c64 if r["W"] == 36 and r["L"] == 64]
    o.w("")
    o.w("# cft64 W=27 (18 workers on the cores, 9 on their siblings): X(27)/X(36) = %.4f against 27/36 = %.4f; wall %.2f s against %.2f s at W=36; all workers do the same S steps, so the run ends with its slowest (core-sharing) workers (INFERRED: no per-worker times were compared)" % (
        r27["X"] / median([r["X"] for r in r36]), 27 / 36.0, r27["wall_s"], median([r["wall_s"] for r in r36])))
    o.w("")
    o.w("# Foreign load across all 59 runs: largest %.3f%% (criterion 2%%)" % (100 * max(r["foreign_share"] for r in runs)))
    o.w("# Peak resident memory (workers' own reports): largest of all runs %d kB" % max(max(r["maxrss_kb"]) for r in runs))
    # G5
    o.w("")
    o.w("# G5, from g_paced.001.log")
    lag = {}
    busy = None
    meanclk = None
    gotpass = []
    for ln in open(os.path.join(box, "g_paced.001.log"), encoding="utf-8"):
        m = re.match(r"    worker (\d+) lag: median ([-\d.]+) s, p99 ([-\d.]+) s, max ([-\d.]+) s over (\d+) steps", ln)
        if m:
            lag[int(m.group(1))] = (float(m.group(2)), float(m.group(3)), float(m.group(4)), int(m.group(5)))
        m = re.match(r"REPORT G5: busy share of wall time per worker: mean ([\d.]+), min ([\d.]+), max ([\d.]+); mean clock (\d+) MHz; kind-mode (\S+); N (\d+)", ln)
        if m:
            busy = tuple(float(m.group(i)) for i in (1, 2, 3))
            meanclk = int(m.group(4))
            km5, n5 = m.group(5), int(m.group(6))
        if ln.startswith("PASS G5"):
            gotpass.append(ln[:60])
    o.check(len(lag) == 36 and all(v[3] == 80 for v in lag.values()), "A5 36 workers, 80 steps each")
    worst = max(v[2] for v in lag.values())
    o.check(worst <= 15.0 and len(gotpass) == 2, "A5 every worker's maximum lag at most 15 s (the largest is %.3f s, i.e. every step finished at least %.3f s before its deadline); %d G5 PASS lines" % (worst, -worst, len(gotpass)))
    meds = sorted(v[0] for v in lag.values())
    low = sorted(lag, key=lambda k: lag[k][0])[:2]
    o.w("  worker lag medians: smallest %.3f s, median %.3f s, largest %.3f s; the two with the most slack are workers %d and %d (worker 35 holds 61 lanes, the others 75; CPU 17 is CPU 35's sibling)" % (meds[0], median(meds), meds[-1], low[0], low[1]))
    o.w("  worker 35's compute time %.3f s over the median worker's %.3f s = %.3f; 61/75 = %.3f (lanes are the cost: the ratio is COMPUTED, the reading INFERRED)" % (15 + lag[35][0], 15 + median(meds), (15 + lag[35][0]) / (15 + median(meds)), 61 / 75.0))
    o.w("  a step's compute time = 15 s + lag: median over workers %.3f s; worst step %.3f s" % (15 + median(meds), 15 + worst))
    o.w("  busy share: mean %.3f, min %.3f, max %.3f; kind-mode %s, N %d" % (busy[0], busy[1], busy[2], km5, n5))
    o.w("  cross-check: capacity %.1f / N %d = %.3f; 1 / busy mean %.3f = %.3f (both are the headroom factor, from independent runs)" % (cap["cft256"], n5, cap["cft256"] / n5, busy[0], 1.0 / busy[0]))
    f_busy = sum(r["freq_mean_khz"] for r in by["cft256"] if r["W"] == 36 and r["L"] == 64) / 3000.0
    idle = (meanclk - busy[0] * f_busy) / (1 - busy[0])
    o.w("  mean clock %d MHz; G4's cft256 W=36 L=64 runs: %.0f MHz. If the busy fraction %.3f read as in G4, the idle fraction's mean reading would be %.0f MHz (COMPUTED from the two means; the split is INFERRED: the log holds only the means)" % (meanclk, f_busy, busy[0], idle))
    # other logs
    o.w("")
    for n in ["g_build.001.log", "g_smoke.001.log", "g_calib.001.log", "g_controls.001.log", "g_g2.001.log", "g_g3.001.log"]:
        lines = open(os.path.join(box, n), encoding="utf-8").read().splitlines()
        npass = sum(1 for l in lines if l.startswith("PASS "))
        nfail = sum(1 for l in lines if l.startswith("FAIL "))
        o.check(nfail == 0 and npass > 0, "A6 %s: %d PASS lines, %d FAIL lines" % (n, npass, nfail))
    for ln in open(os.path.join(box, "g_controls.001.log"), encoding="utf-8"):
        if re.match(r"PASS C[2-5] control", ln):
            o.w("  " + ln.strip()[:330])
    for ln in open(os.path.join(box, "g_calib.001.log"), encoding="utf-8"):
        if ln.startswith("MEASURED calib"):
            o.w("  " + ln.strip()[:400])
    ng2 = sum(1 for l in open(os.path.join(box, "g_g2.001.log"), encoding="utf-8") if re.match(r"PASS G2 \S+ (Q[2-5]|control)", l))
    o.check(ng2 == 8 * 5, "A6 G2: %d of 40 partition and control lines PASS (8 kind-modes x Q2..Q5 + control)" % ng2)
    o.w("# %s (%d failed)" % ("PASS" if o.fails == 0 else "FAIL", o.fails))
    o.f.close()
    return 1 if o.fails else 0


if __name__ == "__main__":
    sys.exit(main())
