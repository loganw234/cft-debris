# h6_gate.py - cft-debris M1 (DEBRIS-H), gate H6: the check against F6. Standard library only; the desktop first, then
# amd-arc-box (the lead's, with Java 8 there, decision 2(a)).
# cft-debris, MIT licence (see LICENSE at the repository root). Written by DEBRIS-H, 2026-11-18.
#
#   python3 -I -B in/tests/h6_gate.py <root> --java JAVA [--procs P] [--compare in/desktop/h6_pairs.tsv]
#       [--logs DIR] [--keep DIR] [--cpu TSV] [--limit N (development only)]
# Works from <root> with relative paths (in/ as tests/h_stage.py lays it out, build/ as tests/h_build.py builds it). Its
# per-pair table holds states: it goes to the ledger's debris-h\, never the repository; the log holds counts and
# aggregates.
import argparse
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import h_lib as H  # noqa: E402
import h_check as HC  # noqa: E402

SCRIPT = os.path.abspath(__file__)
CK = 40
TOL = 1e-3

CRITERIA = """
H6, the check against F6 (DEBRIS-H's brief). For each of F6's 200 pairs (the keys of the ledger's f6_pairs.001.tsv):
  the object is fitted from its S0 set by tests/h_seed.py's fit (DEBRIS-F's B4, --select-any: each pair's object with
  its own row, as F6 fitted it, the set rule and screens not applied) with DEBRIS-F's table (in/frame_f.bin) and Earth
  orientation file, replaying the decode F6's fit used (--decode-order: F5(d)'s 100 objects in its order for the 13
  pairs F6 reused from F5(d), F6's 187 new objects in catalogue order for the rest; the decoder's output depends on
  what its JVM decoded before, DEBRIS-H's finding before this gate ran); then run alone from its origin O by the service's driver (tests/m1h.c run, native64, checkpoints
  every 40 steps, the clock map in the past, so every step is due at once) to the last checkpoint at or before e1q;
  then tests/m1h.c seg from that checkpoint to e1q (whole steps, then one short step); then the check (tests/h_check.py's
  miss(): F6's reference, SGP4 from the S1 set at e1q; (B), SGP4 from the S0 set at e1q).
CRITERION: for every pair, (A)'s and (B)'s misses and their three parts (8 values) equal f6_pairs.001.tsv's within
  1 mm (the file prints them to the millimetre); and T1 (every pair-method) and T3 (every pair) pass, and T2 (every
  object whose S1 row equals its S0 row in all 17 fields gives (B) a miss of exactly 0 at its epoch), as F6 defines them.
CONTROL C16: the first pair in catalogue order with its e1 moved by 1 s (the method, (B) and the reference all at
  e1q + 1 s) must fail the criterion for that pair: at least one of its 8 values more than 1 mm from F6's.
THE BOX (--compare the desktop's per-pair table): every pair's 8 values equal the desktop's within 1 mm; each
  difference is reported (the fit's native64 uses each machine's C library). A second run on the box with
  --fits-from in/desktop (the desktop's fit tables, not fitted again) compares the driver, seg and the check alone,
  against the same two references.
"""


def rows_by_key(tag):
    """DEBRIS-F's rows_by_key: every group's rows, the last one read for a catalogue number kept"""
    out = {}
    for g in H.GROUPS:
        for r in H.read_gp(os.path.join("in/gp", "gp-%s-%s.csv" % (g, tag)), g):
            out[r["NORAD_CAT_ID"]] = r
    return out


def read_f6(path):
    rows, head = {}, None
    for ln in open(path, encoding="ascii"):
        if ln.startswith("#"):
            continue
        p = ln.rstrip("\n").split("\t")
        if head is None:
            head = p
            continue
        rows[p[0]] = dict(zip(head, p))
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root")
    ap.add_argument("--java", required=True)
    ap.add_argument("--procs", type=int, default=3)
    ap.add_argument("--compare")
    ap.add_argument("--logs", default="logs")
    ap.add_argument("--keep")
    ap.add_argument("--cpu")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--fits-from", help="a folder with h6_fit_f5d.tsv and h6_fit_f6.tsv: another run's fits (the box's second run)")
    a = ap.parse_args()
    os.chdir(a.root)
    HERE = os.path.relpath(os.path.dirname(SCRIPT))
    cpu = H.CpuAccount("h6_gate", a.cpu)
    log = H.Log("h6_gate", a.logs, SCRIPT, CRITERIA, extra=[os.path.join(HERE, "h_check.py"), os.path.join(HERE, "h_seed.py"), "in/tests/f5_sgp4.js"], keep_dir=a.keep)
    H.load_leaps("in/orekit/tai-utc.dat")
    exe = "build/m1h" + (".exe" if H.WIN else "")
    m1f = "build/m1f" + (".exe" if H.WIN else "")
    table = "in/frame_f.bin"
    f6p = "in/ledger/f6_pairs.001.tsv"
    for p in [exe, m1f, table, f6p] + ["in/gp/gp-%s-%s.csv" % (g, t) for g in H.GROUPS for t in ("S0", "S1")]:
        log.w("# %s sha256 %s" % (p, H.sha256(p)))
    log.check(H.sha256(table) == "1d997961111f720b2dc275bacb848b3191cbd8997251692ba5b6fe10ef82cf69", "the table is DEBRIS-F's (frame_main.bin)")
    log.check(H.sha256(f6p) == "b548b943a3f4df198e449be29bafd6d4f3c2705db80b759fbf3777c46a7ae84b", "f6_pairs.001.tsv is the ledger's")
    f6 = read_f6(f6p)
    keys = sorted(f6, key=int)
    if a.limit:
        keys = keys[:a.limit]
        log.w("# DEVELOPMENT ONLY: --limit %d (never a gate result)" % a.limit)
    log.check(a.limit or len(keys) == 200, "F6's 200 pairs (%d)" % len(keys))
    s0, s1 = rows_by_key("S0"), rows_by_key("S1")
    e0q = {k: H.epoch_q(s0[k]) for k in keys}
    e1q = {k: H.epoch_q(s1[k]) for k in keys}
    n_root, W = H.next_numbered("h6", "run", "")
    os.makedirs(W)
    env = dict(os.environ)
    env["M1_DOWNLOADS"] = "in/dl/"
    jars = sorted(os.path.join("in/jars", j) for j in os.listdir("in/jars") if j.endswith(".jar"))
    # 1. the fits. The decoder's output depends on what its JVM decoded before (DEBRIS-H's finding), so each fit replays
    #    the decode F6 used: its 13 pairs fitted in F5(d) from F5(d)'s decode (F5(d)'s 100 objects in its table's order,
    #    one JVM), its 187 new fits from F6's own decode (those objects in catalogue order, one JVM)
    f5order = []
    for ln in open("in/ledger/f5d_fits.001.tsv", encoding="ascii"):
        p = ln.split("\t")
        if not ln.startswith("#") and p[0] != "key":
            f5order.append(p[0])
    log.w("# in/ledger/f5d_fits.001.tsv sha256 %s (F5(d)'s decode order)" % H.sha256("in/ledger/f5d_fits.001.tsv"))
    reused = [k for k in keys if k in set(f5order)]
    new = [k for k in keys if k not in set(f5order)]
    log.w("# pairs fitted in F5(d) and reused by F6: %d; fitted anew by F6: %d" % (len(reused), len(new)))
    fits = {}
    for tag, sel, order in (("f5d", reused, f5order), ("f6", new, new)):
        if not sel:
            continue
        if a.fits_from:
            # the box's second run: another machine's fits, so that the driver, seg and the check are compared alone
            tp = os.path.join(a.fits_from, "h6_fit_%s.tsv" % tag)
            log.w("# FITS FROM %s, sha256 %s (not fitted here)" % (tp.replace("\\", "/"), H.sha256(tp)))
        else:
            fitdir = os.path.join(W, "fit_" + tag)
            H.run([sys.executable, "-I", "-B", os.path.join(HERE, "h_seed.py"), "fit", "--seed", "1", "--gp", "in/gp", "--tag", "S0", "--ts", "2026-11-17T00:00:00",
                   "--table", table, "--m1f", m1f, "--java", a.java, "--jars", "in/jars", "--orekit", "in/orekit", "--decoder", "in/tests/f5_sgp4.js",
                   "--leaps", "in/orekit/tai-utc.dat", "--out", fitdir, "--logs", os.path.join(W, "logs"), "--procs", str(max(1, a.procs - 1)), "--test",
                   "--no-catchup", "--select-any", ",".join(sel), "--decode-order", ",".join(order), "--jprocs", "1"], log)
            tp = os.path.join(fitdir, "fit1.001.tsv")
            log.w("# fit table %s, sha256 %s" % (tp.replace("\\", "/"), H.sha256(tp)))
        head = None
        for ln in open(tp, encoding="ascii"):
            if ln.startswith("#"):
                continue
            p = ln.rstrip("\n").split("\t")
            if head is None:
                head = p
                continue
            d = dict(zip(head, p))
            fits[d["cat"]] = d
    log.check(sorted(fits, key=int) == keys, "every pair's object fitted (%d)" % len(fits))
    log.check(all(float.fromhex(fits[k]["O"]) == e0q[k] - 86400.0 for k in keys), "every fit's origin is e0q - 1 day")
    nconv = sum(1 for k in keys if fits[k]["conv"] == "1")
    log.w("# fits converged %d of %d (F6 reported 178 of 200 converged); F6's own column agrees for %d pairs" % (
        nconv, len(keys), sum(1 for k in keys if fits[k]["conv"] == f6[k]["A_fit_converged"])))
    # 2. the runs from O, alone, checkpoints every 40 steps, the clock map in the past
    cmds, plan = [], {}
    for k in keys:
        d = fits[k]
        O = float.fromhex(d["O"])
        N = int(math.floor((e1q[k] - O) / 15.0))
        K = CK * (N // CK)
        rd = os.path.join(W, "runs", k)
        os.makedirs(rd)
        sp = os.path.join(rd, "seed.txt")
        y = [float.fromhex(x) for x in d["y_O"].split(",")]
        H.write_new(sp, ("# m1h seed (H6, one object): T_s is the fit's origin O\n0 %s 0 %s %s %s %s\n" % (
            k, float.hex(O), " ".join(float.hex(v) for v in y), float.hex(float.fromhex(d["bc"])), float.hex(H.CRAM))).encode("ascii"))
        plan[k] = (O, N, K, rd)
        cmds.append(([exe, "run", "--kind", "native64", "--table", table, "--track", "H6", "--run", rd, "--first", 0, "--count", 1, "--lanes", 1,
                      "--k0", 0, "--kend", K, "--unix-ref", "0", "--t-ref", float.hex(O), "--allow", 4, "--ckpt-every", CK, "--worker", 0,
                      "--nworkers", 1, "--seed", "%s:%s" % (sp, H.sha256(sp)), "--no-sync"], os.path.join(rd, "run")))
    codes = H.run_pool(cmds, a.procs, None, env=env)
    log.check(all(c == 0 for c in codes), "every run from O exited 0 (%d runs)" % len(codes))
    nck = sum(len([f for f in os.listdir(os.path.join(plan[k][3], "ckpt", "H6")) if f.endswith(".txt")]) for k in keys)
    log.w("# the runs wrote %d checkpoints (every 40 steps from O); steps from O to the last checkpoint: %d to %d" % (
        nck, min(plan[k][2] for k in keys), max(plan[k][2] for k in keys)))
    # 3. seg from the last checkpoint to e1q (and C16's e1q + 1 s)
    c16 = keys[0]
    cmds = []
    for k in keys:
        O, N, K, rd = plan[k]
        cp = os.path.join(rd, "ckpt", "H6", "k%06d.w00of01.txt" % K)
        for tag, e in (("e1", e1q[k]), ("c16", e1q[k] + 1.0)):
            if tag == "c16" and k != c16:
                continue
            tp = os.path.join(rd, "%s_targets.txt" % tag)
            with open(tp, "w", newline="\n") as f:
                f.write("0 %d E %s\n" % (K, float.hex(e)))
            cmds.append(([exe, "seg", "--kind", "native64", "--table", table, "--init", "%s:%s" % (cp, H.sha256(cp)), "--targets", tp,
                          "--out", os.path.join(rd, "%s_seg.txt" % tag), "--lanes", 1], os.path.join(rd, "%s_seg" % tag)))
    codes = H.run_pool(cmds, a.procs, None, env=env)
    log.check(all(c == 0 for c in codes), "every seg exited 0 (%d)" % len(codes))
    posA = {}
    for k in keys:
        rd = plan[k][3]
        for tag in ("e1", "c16"):
            p = os.path.join(rd, "%s_seg.txt" % tag)
            if os.path.exists(p):
                r = [ln.split() for ln in open(p, encoding="ascii") if ln.startswith("R ")][0]
                posA[(k, tag)] = ([H.f64(x) for x in r[13:16]], float.fromhex(r[4]))
    log.check(all(posA[(k, "e1")][1] == e1q[k] for k in keys), "every seg landed on its e1q exactly")
    # 4. SGP4: the references, (B), and T2's equal sets
    both = sorted((k for k in s0 if k in s1 and s0[k]["EPHEMERIS_TYPE"] == "0" and s1[k]["EPHEMERIS_TYPE"] == "0"), key=int)
    equal = [k for k in both if all(s0[k][c] == s1[k][c] for c in H.COLUMNS)]
    items = []
    for k in keys:
        items.append(("R" + k, s1[k], [e1q[k], e1q[k] + 1.0, e1q[k] + 2.0]))
        items.append(("B" + k, s0[k], [e1q[k], e1q[k] + 1.0]))
    for k in equal:
        e = H.epoch_q(s0[k])
        items.append(("E0" + k, s0[k], [e]))
        items.append(("E1" + k, s1[k], [e]))
    pv = HC.decode(a.java, jars, "in/orekit", "in/tests/f5_sgp4.js", items, W, "sgp4", log)
    # 5. the misses
    rows, nbad, t1bad, nt1, worst = [], 0, 0, 0, 0.0
    names = ["A_m", "A_R", "A_A", "A_C", "B_m", "B_R", "B_A", "B_C"]
    for k in keys:
        ref, ref1 = pv["R" + k][0], pv["R" + k][1]
        vals = []
        for m, p in (("A", posA[(k, "e1")][0]), ("B", pv["B" + k][0][:3])):
            d, rc, err, vn = HC.miss(p, ref, ref1)
            nt1 += 1
            if not err <= 0.01 * vn:
                t1bad += 1
            vals += [d] + rc
        diffs = [abs(v - float(f6[k][n])) for v, n in zip(vals, names)]
        ok = all(x <= TOL for x in diffs)
        nbad += not ok
        worst = max(worst, max(diffs))
        rows.append((k, vals, diffs, ok, posA[(k, "e1")][0], pv["B" + k][0][:3], ref))
    log.w("# the 8 values of every pair against F6's: largest difference %.4f m (tolerance 0.001 m)" % worst)
    log.check(nbad == 0, "H6 criterion: every pair's (A) and (B) misses and parts equal F6's within 1 mm (%d of %d pairs do not)" % (nbad, len(keys)))
    log.check(t1bad == 0, "T1 the time tag: all %d pair-methods moved by v x 1 s within 1%% of |v|" % nt1)
    nz = sum(1 for k in equal if pv["E0" + k][0][:3] != pv["E1" + k][0][:3])
    log.check(len(equal) > 0 and nz == 0, "T2 equal sets: all %d objects with equal S0 and S1 rows give (B) a miss of exactly 0 (%d do not)" % (len(equal), nz))
    nn = {k: float(s1[k]["MEAN_MOTION"]) for k in keys}
    done, bad = HC.t3(keys, {k: pv["B" + k][0][:3] for k in keys}, {k: pv["R" + k][0] for k in keys}, nn)
    log.check(len(keys) < 2 or (done > 0 and bad == 0), "T3 swapped identities: %d pairs compared, %d within 100 km" % (done, bad))
    # C16
    k = c16
    ref, ref1 = pv["R" + k][1], pv["R" + k][2]
    vals = []
    for m, p in (("A", posA[(k, "c16")][0]), ("B", pv["B" + k][1][:3])):
        d, rc, err, vn = HC.miss(p, ref, ref1)
        vals += [d] + rc
    cd = [abs(v - float(f6[k][n])) for v, n in zip(vals, names)]
    log.w("# C16: with e1 moved by 1 s, the first pair's largest difference from F6's values is %.4f m" % max(cd))
    log.check(max(cd) > TOL and posA[(k, "c16")][1] == e1q[k] + 1.0, "C16 the first pair with e1 moved by 1 s fails the 1 mm criterion - failed as specified")
    # the per-pair table (the ledger's)
    lines = ["# h6_gate per-pair results (per object: the ledger only); log %s" % os.path.basename(log.path),
             "\t".join(["key", "ok"] + names + ["d_" + n for n in names] + ["A_pos", "B_pos", "ref_state"])]
    for k, vals, diffs, ok, pa, pb, ref in rows:
        lines.append("\t".join([k, str(int(ok))] + ["%.6f" % v for v in vals] + ["%.6f" % v for v in diffs] +
                               [",".join(float.hex(x) for x in pa), ",".join(float.hex(x) for x in pb), ",".join(float.hex(x) for x in ref)]))
    tp = os.path.join(W, "h6_pairs.tsv")
    H.write_new(tp, ("\n".join(lines) + "\n").encode("ascii"))
    log.w("# per-pair table %s, sha256 %s" % (tp.replace("\\", "/"), H.sha256(tp)))
    if a.compare:
        other = {}
        for ln in open(a.compare, encoding="ascii"):
            if ln.startswith("#") or ln.startswith("key"):
                continue
            p = ln.rstrip("\n").split("\t")
            other[p[0]] = [float(x) for x in p[2:10]]
        log.w("# compared with %s, sha256 %s" % (a.compare, H.sha256(a.compare)))
        nd, wd, nbits = 0, 0.0, 0
        for k, vals, diffs, ok, pa, pb, ref in rows:
            dd = [abs(x - y) for x, y in zip(vals, other[k])]
            wd = max(wd, max(dd))
            nd += max(dd) > TOL
            nbits += any(x != y for x, y in zip(vals, other[k]))
        log.w("# against the other machine: %d pairs differ in any value at the printed micrometre, the largest difference %.6f m" % (nbits, wd))
        log.check(nd == 0 and len(other) == len(rows), "H6 on two machines: every pair's 8 values equal the other machine's within 1 mm (%d do not)" % nd)
    c_ = cpu.close("h6_gate log %03d" % log.n)
    if c_ is not None:
        log.w("# CPU: %.2f s by cycles / 2.5e9 (this script and every process it started)" % c_)
    return log.close()


if __name__ == "__main__":
    sys.exit(main())
