# h5_gate.py - cft-debris M1 (DEBRIS-H), gate H5: the seed. Standard library only; on the desktop (phase 1, on the
# test seed) and on amd-arc-box (the lead, on S_H0's seed at the launch).
# cft-debris, MIT licence (see LICENSE at the repository root). Written by DEBRIS-H, 2026-11-18.
#
#   python3 -I -B in/tests/h5_gate.py <root> --dir SEEDDIR --fit1 F1 --fit2 F2 --table TABLE --m1f EXE --gp DIR --tag TAG
#       --java JAVA [--regression] [--logs DIR] [--keep DIR] [--cpu TSV]
# SEEDDIR holds seed1.txt, seed2.txt and seed_meta.tsv (tests/h_seed.py combine); F1 and F2 are its fit tables; DIR/TAG
# the snapshot the seed was fitted from. Works from <root> with relative paths: in/ as tests/h_stage.py lays it out,
# build/ as tests/h_build.py builds it.
import argparse
import math
import os
import random
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import h_lib as H  # noqa: E402

SCRIPT = os.path.abspath(__file__)
HERE = os.path.dirname(SCRIPT)
REG_SEED = 0x45D5
C13_OBS, C13_DX = 360, 1000.0

CRITERIA = """
H5, for each seed (seed 1: bc fitted below 1,000 km of perigee; seed 2: bc held at 0.01 m^2/kg), all asserted:
 (1) every object fitted is counted as converged or flagged (stopped on the iteration limit, or on a singular matrix),
     and the counts add up to the objects fitted;
 (2) every object left out for its catch-up is counted (stopped early, not finite, or at or below 120 km at T_s), and
     the seed files hold exactly the objects whose catch-up succeeded in both seeds, in both files with the same
     indices and catalogue numbers;
 (3) every seed state is finite and lies more than 6,498.137 km from the centre;
 (4) the first seed's cft256 and native64 tracks start identical in binary64: tests/m1h.c run from seed1.txt at both
     kinds, k0 = kend = 0, writes checkpoint 0, and its binary64 columns agree bit for bit for every object;
 (5) in the second seed every bc is exactly 0.01 m^2/kg;
 (6) the clock map's TDB - UTC at T_s (h_lib.clock_map: tai-utc.dat and USNO Circular 179's eq. 2.6) equals Orekit's
     (tests/f_orekit.js times: TAI-UTC + TT-TAI + TDB-TT) within 1 ms. Basis: F2 measured Orekit's TDB - TT within
     25.35 us of eq. (2.6), and a millisecond is about 7.5 m of an orbit's motion, under every miss this round reports.
CONTROLS, each must fail as specified:
 C13 the first seed object's fit run twice (tests/h_seed.py fit --select, --no-catchup): as it is, and with its
     pseudo-observation 360 moved by 1 km in x; the fitted state at O must differ;
 C14 a copy of the second seed with object 0's bc moved to the next binary64 above must fail (5);
 C15 a copy of the native64 track's checkpoint 0 with object 0's x moved by one ulp must fail (4).
THE REGRESSION (--regression, the desktop): tests/h_seed.py's fits (--no-catchup) of five of F5(d)'s objects from S0,
 with DEBRIS-F's table (in/frame_f.bin) and Earth orientation file, reproduce the ledger's f5d_fits.001.tsv: the same
 iterations and convergence, and bc (%.6g) and the residuals' RMS and largest value (%.3f m) equal at the printed
 digits. The five: random.Random(0x45D5).sample over F5(d)'s keys that tests/h_seed.py's rules keep (one object per
 set) from S0 at T_s = 2026-11-17 00:00 TDB, in ascending order (fixed before the table's values were compared; its
 header and first row had been read once). The decoder's output depends on what its JVM decoded before (DEBRIS-H's
 finding, after this gate's log 001 failed), so the fit replays F5(d)'s decode: its 100 objects in its table's order in
 one JVM (h_seed.py --decode-order), and fits the five (--select-any).
"""


def seed_cmd(a, logs, extra):
    """tests/h_seed.py fit; its logs go to the gate's own folder (they describe one to five objects: the ledger's, not
    the repository's)"""
    return [sys.executable, "-I", "-B", os.path.join(HERE, "h_seed.py"), "fit", "--gp", a.gp, "--tag", a.tag, "--m1f", a.m1f, "--java", a.java,
            "--jars", "in/jars", "--orekit", "in/orekit", "--decoder", "in/tests/f5_sgp4.js", "--leaps", "in/orekit/tai-utc.dat",
            "--logs", logs, "--procs", "1", "--test"] + extra


def fit_table(path):
    rows, head = {}, None
    for ln in open(path, encoding="ascii"):
        if ln.startswith("#"):
            continue
        p = ln.rstrip("\n").split("\t")
        if head is None:
            head = p
            continue
        d = dict(zip(head, p))
        rows[int(d["cat"])] = d
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root")
    for o in ("--dir", "--fit1", "--fit2", "--table", "--m1f", "--gp", "--tag", "--java"):
        ap.add_argument(o, required=True)
    ap.add_argument("--regression", action="store_true")
    ap.add_argument("--logs", default="logs")
    ap.add_argument("--keep")
    ap.add_argument("--cpu")
    a = ap.parse_args()
    os.chdir(a.root)
    global HERE
    HERE = os.path.relpath(os.path.dirname(SCRIPT))
    cpu = H.CpuAccount("h5_gate", a.cpu)
    log = H.Log("h5_gate", a.logs, SCRIPT, CRITERIA, extra=[os.path.join(HERE, "h_seed.py"), "in/tests/f_orekit.js"], keep_dir=a.keep)
    H.load_leaps("in/orekit/tai-utc.dat")
    s1p, s2p, mp = [os.path.join(a.dir, f) for f in ("seed1.txt", "seed2.txt", "seed_meta.tsv")]
    for p in (s1p, s2p, mp, a.fit1, a.fit2, a.table, a.m1f, "build/m1h" + (".exe" if H.WIN else "")):
        log.w("# %s sha256 %s" % (p.replace("\\", "/"), H.sha256(p)))
    s1, s2 = H.read_seed(s1p), H.read_seed(s2p)
    f1, f2 = fit_table(a.fit1), fit_table(a.fit2)
    ts = s1["ts"]
    log.w("# T_s %s (%s); seed objects %d" % (float.hex(ts), H.tdb_label(ts), len(s1["rows"])))
    # (1) and (2)
    for s, f in ((1, f1), (2, f2)):
        n = len(f)
        conv = sum(1 for d in f.values() if d["conv"] == "1")
        lim = sum(1 for d in f.values() if d["conv"] == "0" and d["singular"] == "0")
        sing = sum(1 for d in f.values() if d["singular"] == "1")
        log.check(n > 0 and conv + lim + sing == n, "(1) seed %d: %d fitted = %d converged + %d flagged on the iteration limit + %d flagged singular" % (s, n, conv, lim, sing))
        cs = {k: sum(1 for d in f.values() if d["catch"] == k) for k in ("ok", "stopped", "nonfinite", "below", "skipped")}
        log.check(sum(cs.values()) == n and cs["skipped"] == 0, "(2) seed %d: catch-up ok %d, left out %d (stopped early %d, not finite %d, at or below 120 km %d)" % (
            s, cs["ok"], cs["stopped"] + cs["nonfinite"] + cs["below"], cs["stopped"], cs["nonfinite"], cs["below"]))
    both = sorted(c for c in f1 if f1[c]["catch"] == "ok" and c in f2 and f2[c]["catch"] == "ok")
    cats1 = [s1["rows"][i][0] for i in range(len(s1["rows"]))]
    cats2 = [s2["rows"][i][0] for i in range(len(s2["rows"]))]
    log.check(cats1 == both and cats2 == both, "(2) both seed files hold exactly the %d objects whose catch-up succeeded in both seeds, same indices" % len(both))
    # (3)
    for s, sd in ((1, s1), (2, s2)):
        okf = all(all(math.isfinite(x) for x in r[3]) for r in sd["rows"].values())
        rmin = min(math.sqrt(sum(x * x for x in r[3][:3])) for r in sd["rows"].values())
        log.check(okf and rmin > H.RMIN, "(3) seed %d: every state finite, the smallest distance from the centre %.3f km (> 6,498.137 km)" % (s, rmin / 1e3))
    # (5) and C14

    def bc_ok(sd):
        return all(r[4] == H.BC0 for r in sd["rows"].values())
    log.check(bc_ok(s2), "(5) seed 2: every bc is exactly 0.01 m^2/kg")
    import copy
    s2c = copy.deepcopy(s2)
    r = list(s2c["rows"][0])
    r[4] = math.nextafter(r[4], math.inf)
    s2c["rows"][0] = tuple(r)
    log.check(not bc_ok(s2c), "C14 a copy of seed 2 with object 0's bc moved to the next binary64 fails (5) - failed as specified")
    # (4) and C15
    n_root, rdir = H.next_numbered("h5", "identity", "")
    os.makedirs(rdir)
    env = dict(os.environ)
    env["M1_DOWNLOADS"] = "in/dl/"
    exe = "build/m1h" + (".exe" if H.WIN else "")
    files = {}
    for kind in ("cft256", "native64"):
        trk = "I" + kind
        H.run([exe, "run", "--kind", kind, "--table", a.table, "--track", trk, "--run", rdir, "--first", 0, "--count", len(s1["rows"]), "--lanes", 64,
               "--k0", 0, "--kend", 0, "--unix-ref", "0", "--t-ref", float.hex(ts), "--allow", 4, "--ckpt-every", 40, "--worker", 0, "--nworkers", 1,
               "--seed", "%s:%s" % (s1p, H.sha256(s1p))], log, env=env)
        files[kind] = os.path.join(rdir, "ckpt", trk, "k000000.w00of01.txt")
    ra, rb = H.read_ckpt(files["cft256"])[1], H.read_ckpt(files["native64"])[1]

    def ident(x, y):
        return len(x) == len(y) == len(s1["rows"]) and all(x[i][2] == y[i][2] for i in x)
    log.check(ident(ra, rb), "(4) checkpoint 0 of the first seed at cft256 and at native64: identical binary64 states for all %d objects" % len(ra))
    log.check(all(rb[i][2] == [H.h64(v) for v in s1["rows"][i][3]] for i in rb), "(4) and both equal the seed's own binary64 states")
    rbc = {i: (v[0], v[1], list(v[2]), v[3], v[4]) for i, v in rb.items()}
    x0 = H.f64(rbc[0][2][0])
    rbc[0][2][0] = H.h64(math.nextafter(x0, math.inf))
    log.check(not ident(ra, rbc), "C15 a copy of the native64 checkpoint 0 with object 0's x moved by one ulp fails (4) - failed as specified")
    # (6)
    u, tr = H.clock_map(ts)
    ours = H.tdb_minus_utc(ts)
    tai = float(H.tdb_to_tai(ts))
    tin = os.path.join(rdir, "ts_tai.txt")
    with open(tin, "w", newline="\n") as f:
        f.write(repr(tai) + "\n")
    tout = os.path.join(rdir, "ts_orekit.txt")
    jars = sorted(os.path.join("in/jars", j) for j in os.listdir("in/jars") if j.endswith(".jar"))
    H.run(H.java_argv(a.java, jars, "in/tests/f_orekit.js", ["times", "in/orekit", tin, tout]), log)
    row = [ln.split() for ln in open(tout) if not ln.startswith("#")][0]
    ore = float.fromhex(row[1]) + float.fromhex(row[2]) + float.fromhex(row[3])
    log.w("# clock map: unix_ref %.6f for T_s %s; TDB - UTC ours %.9f s, Orekit's %.9f s, difference %.3e s" % (u, float.hex(tr), ours, ore, ours - ore))
    log.check(abs(ours - ore) <= 1e-3, "(6) the clock map's TDB - UTC at T_s equals Orekit's within 1 ms (%.3e s)" % (ours - ore))
    # C13
    c0 = s1["rows"][0][0]
    wd = os.path.join(rdir, "c13")
    outs = []
    for tag, extra in (("as is", []), ("planted", ["--plant-obs", "%d:%d:%r" % (c0, C13_OBS, C13_DX)])):
        od = os.path.join(wd, "plant" if extra else "plain")
        H.run(seed_cmd(a, os.path.join(rdir, "logs"), ["--seed", "1", "--ts", float.hex(ts), "--table", a.table, "--out", od, "--select", str(c0),
                                                       "--no-catchup"] + extra), log)
        t = fit_table(os.path.join(od, "fit1.001.tsv"))
        outs.append(t[c0]["y_O"])
    log.check(outs[0] != outs[1], "C13 the planted pseudo-observation (1 km in x, observation %d) changes the fitted state at O - failed as specified" % C13_OBS)
    # the regression
    if a.regression:
        f5 = {}
        hd = None
        for ln in open("in/ledger/f5d_fits.001.tsv", encoding="ascii"):
            if ln.startswith("#"):
                continue
            p = ln.rstrip("\n").split("\t")
            if hd is None:
                hd = p
                continue
            f5[int(p[0])] = dict(zip(hd, p))
        rows = []
        for g in H.GROUPS:
            rows += H.read_gp(os.path.join("in/gp", "gp-%s-S0.csv" % g), g)
        sets = {}
        for r in rows:
            if r["EPHEMERIS_TYPE"] != "0":
                continue
            k = H.set_key(r)
            if k not in sets or int(r["NORAD_CAT_ID"]) < int(sets[k]["NORAD_CAT_ID"]):
                sets[k] = r
        kept = {int(r["NORAD_CAT_ID"]) for r in sets.values()}
        cand = sorted(c for c in f5 if c in kept)
        pick = sorted(random.Random(REG_SEED).sample(cand, 5))
        log.w("# regression: %d of F5(d)'s 100 keys are kept by the set rule; 5 drawn (their positions among the sorted candidates: %s)" % (
            len(cand), [cand.index(c) for c in pick]))
        od = os.path.join(rdir, "regression")
        # F5(d) decoded its 100 objects in one JVM in its table's order; the decoder's output depends on what the JVM
        # decoded before (DEBRIS-H's finding), so the regression replays that sequence and fits the five
        f5order = list(f5)
        H.run(seed_cmd(a, os.path.join(rdir, "logs"), ["--seed", "1", "--ts", "2026-11-17T00:00:00", "--table", "in/frame_f.bin", "--gp", "in/gp",
                                                       "--tag", "S0", "--out", od, "--select-any", ",".join(str(c) for c in pick), "--no-catchup",
                                                       "--decode-order", ",".join(str(c) for c in f5order), "--jprocs", "1"]), log)
        t = fit_table(os.path.join(od, "fit1.001.tsv"))
        nok = 0
        cmp_lines = ["# h5 regression: h_seed.py's fit against f5d_fits.001.tsv, per object (the ledger's, not the repository's)",
                     "\t".join(["cat", "equal", "iter", "f5_iter", "conv", "f5_conv", "rms_m", "f5_rms_m", "maxres_m", "f5_maxres_m", "bc", "f5_bc"])]
        for c in pick:
            d, e = t[c], f5[c]
            same = (d["conv"] == e["converged"] and d["iter"] == e["iterations"] and d["rms_m"] == e["rms_m"] and d["maxres_m"] == e["maxres_m"]
                    and "%.6g" % float.fromhex(d["bc"]) == e["bc"] and d["fitbc"] == e["fitbc"] and float.fromhex(d["O"]) == float.fromhex(e["t0_tdb"]))
            nok += same
            log.w("#   regression object %d of 5: %s" % (pick.index(c), "equal" if same else "DIFFERENT"))
            cmp_lines.append("\t".join([str(c), str(int(same)), d["iter"], e["iterations"], d["conv"], e["converged"], d["rms_m"], e["rms_m"],
                                        d["maxres_m"], e["maxres_m"], "%.6g" % float.fromhex(d["bc"]), e["bc"]]))
        cp = os.path.join(rdir, "regression.tsv")
        H.write_new(cp, ("\n".join(cmp_lines) + "\n").encode("ascii"))
        log.w("# the per-object comparison: %s, sha256 %s" % (cp.replace("\\", "/"), H.sha256(cp)))
        log.check(nok == 5, "REGRESSION h_seed.py's fits of 5 of F5(d)'s objects reproduce f5d_fits.001.tsv at its printed digits (%d of 5)" % nok)
    c_ = cpu.close("h5_gate log %03d" % log.n)
    if c_ is not None:
        log.w("# CPU: %.2f s by cycles / 2.5e9 (this script and every process it started)" % c_)
    return log.close()


if __name__ == "__main__":
    sys.exit(main())
