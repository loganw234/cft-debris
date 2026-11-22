# h_check.py - cft-debris M1 (DEBRIS-H), H-e: the check of M1 against each new element set. Standard library only.
# cft-debris, MIT licence (see LICENSE at the repository root). Written by DEBRIS-H, 2026-11-18. Its method is DEBRIS-F's
# F6 (tests/f6_hindcast.py, cft-debris's own, MIT): the reference, the miss and its parts, and the controls T1 and T3,
# with ric() and quant() copied into h_lib.py; the decoder is DEBRIS-F's tests/f5_sgp4.js, unchanged.
#
#   python3 -I -B in/tests/h_check.py slot <run> <j> [--procs N]
# run from the service's root (tests/h_service.py runs it at nice 19 after the fetcher's slot j).
#
# THE CHECK, for every object of the seed whose new set (slot j's files, ephemeris type 0, the same catalogue number)
# is ELIGIBLE: its epoch e later than the epoch of the last set checked for that object (at first the seed's set),
# no earlier than T_s, the object not decayed in any track at the checkpoint used, and the fetcher not stopped:
#   THE REFERENCE: SGP4 from the new set at e (rounded to 2^-20 s as DEBRIS-F's B1 rounds), GCRF (tests/f5_sgp4.js);
#   (A256), (A64), (A64f): each track's state at e, re-propagated by tests/m1h.c seg from the track's latest complete
#     checkpoint at or before e (whole steps, then one short step landing on e); every checkpoint file used is first
#     held to its SHA-256 in the run's manifest, and a file that does not match is never read (the check is then
#     listed with that reason);
#   (B): SGP4 from the seed's set at e (F6's (B));
#   THE MISS: the GCRF distance to the reference, and its radial, along-track and cross-track parts in the reference's
#     frame (R along r_ref, C along r_ref x v_ref, A = C x R);
#   T1, THE TIME TAG, every check and method: with the reference moved to e + 1 s, the change in the miss vector equals
#     the reference's velocity times 1 s within 1% of that velocity's size;
#   T3, SWAPPED IDENTITIES, every check: (B)'s position against the reference of the next check in catalogue order
#     (cyclically) whose new mean motion differs from its own by more than 1e-3 rev/day misses by more than 100 km.
#   T2 (equal sets) cannot fire here: a set equal to the seed's has e = e0, before T_s, and is counted, not checked.
# Sets with e before T_s, sets not later than the last checked, decayed objects, objects absent from the slot's files
# and objects the seed does not hold are counted. The per-object table (states included) goes to <run>/checks/ (the
# ledger's, never the repository's); the log holds counts and aggregates and names objects by seed index only.
import argparse
import json
import math
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import h_lib as H  # noqa: E402

SCRIPT = os.path.abspath(__file__)
METHODS_A = ["A256", "A64", "A64f"]

CRITERIA = """
H-e, the check (DEBRIS-F's F6 repeated at each slot): the eligibility, the reference, the methods, the miss and its
parts as this script's header states them. ASSERTED for every check: T1 (every method's miss vector moves by the
reference's velocity x 1 s within 1% of |v|) and T3 (each (B) misses the next check's reference, mean motion more
than 1e-3 rev/day apart, by more than 100 km); every checkpoint file used matches the manifest's SHA-256.
MEASURED (no pass condition), per method: the count, median and 90th percentile (the ceil(0.9 n)-th smallest) of the
miss, with and without the flagged fits; the medians of its parts' sizes.
"""


# ------------------------------------------------------------------ shared with tests/h6_gate.py
def decode(java, jars, orekit, decoder, items, work, tag, log=None):
    """items: (key, row, [TDB instants]); one JVM; returns {key: [state6]} (None for a refused set)"""
    pin, pout = os.path.join(work, "%s_pv_in.txt" % tag), os.path.join(work, "%s_pv.txt" % tag)
    H.decode_input(pin, items)
    if log:
        # the batch's composition and order, for a replay (the decoder's output depends on what its JVM decoded before)
        log.w("# decode batch %s: one JVM, %d sets, %d instants, in the order of %s, sha256 %s" % (
            tag, len(items), sum(len(t) for _, _, t in items), os.path.basename(pin), H.sha256(pin)))
    H.run(H.java_argv(java, jars, decoder, ["pv", orekit, pin, pout]), log)
    return H.read_decoded(pout)


def seg_run(exe, kind, table, targets, inits, work, tag, procs, log=None, nice=None, env=None):
    """targets: [(idx, kc, e)]; inits: {(idx, kc): (file, sha)}; returns {(idx, e): (decay, kind hex6, f64 hex6)}"""
    chunks = [targets[i::procs] for i in range(procs)] if len(targets) >= procs else [targets]
    cmds, outs = [], []
    for c, part in enumerate(chunks):
        if not part:
            continue
        tp, op = os.path.join(work, "%s_t%02d.txt" % (tag, c)), os.path.join(work, "%s_seg%02d.txt" % (tag, c))
        files = sorted({inits[(i, kc)] for i, kc, _ in part})
        with open(tp, "w", newline="\n") as f:
            for i, kc, e in part:
                f.write("%d %d E %s\n" % (i, kc, float.hex(e)))
        if log:
            log.w("# seg batch %s %02d (%s): %d targets, %s sha256 %s" % (tag, c, kind, len(part), os.path.basename(tp), H.sha256(tp)))
        argv = [exe, "seg", "--kind", kind, "--table", table, "--targets", tp, "--out", op, "--lanes", "1"]
        for fp, sha in files:
            argv += ["--init", "%s:%s" % (fp, sha)]
        cmds.append((argv, op + ".run"))
        outs.append(op)
    codes = H.run_pool(cmds, procs, log, env=env, nice=nice)
    res = {}
    for op, code in zip(outs, codes):
        if code != 0:
            raise RuntimeError("m1h seg failed (%d): %s" % (code, op))
        for ln in open(op, encoding="ascii"):
            p = ln.split()
            if p and p[0] == "R":
                res[(int(p[1]), float.fromhex(p[4]))] = (int(p[6]), p[7:13], p[13:19])
    return res


def miss(p, ref, ref1):
    """F6's miss: |p - ref|, its RIC parts, and T1's error (|(p - ref) - (p - ref1) - v_ref|, |v_ref|)"""
    dp = [a - b for a, b in zip(p[:3], ref[:3])]
    dp1 = [a - b for a, b in zip(p[:3], ref1[:3])]
    ch = [a - b for a, b in zip(dp, dp1)]
    v = ref[3:6]
    vn = math.sqrt(sum(x * x for x in v))
    t1 = math.sqrt(sum((a - b) ** 2 for a, b in zip(ch, v)))
    return math.sqrt(sum(x * x for x in dp)), H.ric(dp, ref[:3], v), t1, vn


def t3(order, bpos, refs, nn):
    """F6's T3 over checks in catalogue order: returns (checked, failed)"""
    n = len(order)
    bad = done = 0
    for i, k in enumerate(order):
        j = (i + 1) % n
        while order[j] != k and abs(nn[order[j]] - nn[k]) <= 1e-3:
            j = (j + 1) % n
        if order[j] == k:
            continue
        done += 1
        if not H.dist(bpos[k], refs[order[j]][:3]) > 100e3:
            bad += 1
    return done, bad


# ------------------------------------------------------------------ the long run's slot
def load_manifest(run):
    rows = []
    for ln in open(os.path.join(run, "manifest.tsv"), encoding="ascii"):
        if ln.startswith("#") or not ln.strip():
            continue
        q = ln.rstrip("\n").split("\t")
        rows.append({"track": q[1], "k": int(q[2]), "file": q[3], "sha": q[4], "first": int(q[5]), "count": int(q[6])})
    return rows


def read_meta(path):
    rows, head = {}, None
    for ln in open(path, encoding="ascii"):
        if ln.startswith("#"):
            continue
        p = ln.rstrip("\n").split("\t")
        if head is None:
            head = p
            continue
        d = dict(zip(head, p))
        rows[int(d["idx"])] = d
    return rows


def cmd_slot(a):
    run = a.run
    cfg = json.load(open(os.path.join(run, "service.json"), encoding="ascii"))
    os.makedirs(os.path.join(run, "logs"), exist_ok=True)
    log = H.Log("check_slot%02d" % a.j, os.path.join(run, "logs"), SCRIPT, CRITERIA, quiet=True)
    H.load_leaps(cfg["leaps"])
    ts, ck = cfg["ts"], cfg["ckpt_every"]
    fdir = os.path.join(run, "fetch")
    if os.path.exists(os.path.join(fdir, "STOP")):
        log.w("# the fetcher has stopped: no check (eligibility needs the fetcher not stopped)")
        log.check(True, "nothing to check")
        return log.close()
    meta = read_meta(cfg["seed_meta"])
    by_cat = {int(d["cat"]): i for i, d in meta.items()}
    sh0 = {}
    for g in H.GROUPS:
        for p in (os.path.join(cfg["sh0_dir"], "gp-%s-SH0.csv" % g), os.path.join(cfg["sh0_dir"], "gp-%s-SH0" % g, "gp-%s-SH0.csv" % g)):
            if os.path.exists(p):
                for r in H.read_gp(p, g):
                    sh0.setdefault(int(r["NORAD_CAT_ID"]), []).append(r)
                break
    # the seed's own set for each object: the row of S_H0 with the seed's epoch
    seedrow = {}
    for i, d in meta.items():
        c = int(d["cat"])
        cand = [r for r in sh0.get(c, []) if r["EPOCH"] == d["epoch"] and r["EPHEMERIS_TYPE"] == "0"]
        if cand:
            seedrow[i] = cand[0]
    log.check(len(seedrow) == len(meta), "every seed object's set is found in S_H0 (%d of %d)" % (len(seedrow), len(meta)))
    new = {}
    files = []
    for g in H.GROUPS:
        p = os.path.join(fdir, "slot%02d" % a.j, "gp-%s.csv" % g)
        if os.path.exists(p):
            files.append(p)
            for r in H.read_gp(p, g):
                if r["EPHEMERIS_TYPE"] != "0":
                    continue
                c = int(r["NORAD_CAT_ID"])
                if c in new and H.epoch_tdb(new[c]) >= H.epoch_tdb(r):
                    continue
                new[c] = r
    log.w("# slot %d: %d files (%s), %d objects of ephemeris type 0" % (a.j, len(files), ", ".join("%s sha256 %s" % (os.path.basename(f), H.sha256(f)) for f in files), len(new)))
    # the last set checked for each object: the seed's, then every earlier slot's table
    last = {i: H.epoch_tdb(seedrow[i]) for i in seedrow}
    cdir = os.path.join(run, "checks")
    os.makedirs(cdir, exist_ok=True)
    for f in sorted(os.listdir(cdir)):
        if f.startswith("slot") and f.endswith(".tsv") and int(f[4:6]) < a.j:
            head = None
            for ln in open(os.path.join(cdir, f), encoding="ascii"):
                if ln.startswith("#"):
                    continue
                q = ln.rstrip("\n").split("\t")
                if head is None:
                    head = q
                    continue
                d = dict(zip(head, q))
                if d.get("status") == "checked":
                    i = int(d["idx"])
                    last[i] = max(last[i], H.epoch_tdb({"EPOCH": d["new_epoch"]}))
    man = load_manifest(run)
    tracks = {t["name"]: t for t in cfg["tracks"]}
    counts = {"absent": 0, "not_later": 0, "before_ts": 0, "decayed": 0, "no_checkpoint": 0, "hash_refused": 0, "eligible": 0}
    arrivals = sum(1 for c in new if c not in by_cat)
    elig = []
    for i in sorted(meta):
        c = int(meta[i]["cat"])
        r = new.get(c)
        if r is None:
            counts["absent"] += 1
            continue
        e = H.epoch_tdb(r)
        if not e > last[i]:
            counts["not_later"] += 1
            continue
        if e < ts:
            counts["before_ts"] += 1
            continue
        elig.append((i, r, H.quantize(e)))
    counts["eligible"] = len(elig)
    # the checkpoint for each track and object
    sha_ok = {}

    def ck_file(trk, idx, eq):
        best = None
        for m in man:
            if m["track"] == trk and m["first"] <= idx < m["first"] + m["count"] and ts + 15.0 * m["k"] <= eq:
                if best is None or m["k"] > best["k"]:
                    best = m
        if best is None:
            return None
        if best["file"] not in sha_ok:
            sha_ok[best["file"]] = H.sha256(best["file"]) == best["sha"]
        return best if sha_ok[best["file"]] else "refused"
    work = os.path.join(run, "checks", "work%02d" % a.j)
    os.makedirs(work, exist_ok=True)
    plan, rows_out, ck_rows = {}, {}, {}
    for i, r, eq in elig:
        use = {}
        why = None
        for trk in METHODS_A:
            if trk not in tracks:
                continue
            m = ck_file(trk, i, eq)
            if m is None:
                why = "no checkpoint of %s at or before e" % trk
                counts["no_checkpoint"] += 1
                break
            if m == "refused":
                why = "the checkpoint of %s does not match its manifest hash (not read)" % trk
                counts["hash_refused"] += 1
                break
            use[trk] = m
        if why:
            rows_out[i] = {"status": "listed", "why": why}
            continue
        # decayed at the checkpoint used, in any track?
        dec = False
        for trk, m in use.items():
            if m["file"] not in ck_rows:
                ck_rows[m["file"]] = H.read_ckpt(m["file"])[1]
            if ck_rows[m["file"]][i][0] >= 0:
                dec = True
        if dec:
            counts["decayed"] += 1
            rows_out[i] = {"status": "decayed"}
            continue
        plan[i] = (r, eq, use)
    log.w("# counts: %s; new sets of objects the seed does not hold: %d" % (counts, arrivals))
    env = dict(os.environ)
    env["M1_DOWNLOADS"] = cfg["downloads"]
    nice = 19 if not H.WIN else None
    states = {}
    for trk in METHODS_A:
        if trk not in tracks or not plan:
            continue
        t = tracks[trk]
        targets = [(i, plan[i][2][trk]["k"], plan[i][1]) for i in sorted(plan)]
        inits = {(i, plan[i][2][trk]["k"]): (plan[i][2][trk]["file"], plan[i][2][trk]["sha"]) for i in plan}
        states[trk] = seg_run(cfg["exe"], t["kind"], cfg["table"], targets, inits, work, trk, a.procs if t["kind"] == "cft256" else 1, log, nice=nice, env=env)
    jars = sorted(os.path.join(cfg["jars"], j) for j in os.listdir(cfg["jars"]) if j.endswith(".jar"))
    items = []
    for i in sorted(plan):
        r, eq, _ = plan[i]
        items.append(("N%d" % i, r, [eq, eq + 1.0]))
        items.append(("B%d" % i, seedrow[i], [eq]))
    pv = decode(cfg["java"], jars, cfg["orekit"], cfg["decoder"], items, work, "sgp4", log) if items else {}
    t1bad = nt1 = 0
    res = {}
    for i in sorted(plan):
        r, eq, use = plan[i]
        if pv.get("N%d" % i) is None or pv.get("B%d" % i) is None:
            rows_out[i] = {"status": "listed", "why": "Orekit refused a set"}
            continue
        ref, ref1 = pv["N%d" % i][0], pv["N%d" % i][1]
        out = {"ref": ref}
        meth = {"B": pv["B%d" % i][0][:3]}
        for trk in METHODS_A:
            if trk in states:
                st = states[trk][(i, eq)]
                meth[trk] = [H.f64(x) for x in st[2][:3]]
        for m, p in meth.items():
            d, rc, err, vn = miss(p, ref, ref1)
            nt1 += 1
            if not err <= 0.01 * vn:
                t1bad += 1
            out[m] = (d, rc, p)
        res[i] = out
        rows_out[i] = {"status": "checked"}
    log.check(t1bad == 0, "T1 the time tag: all %d check-methods moved by v x 1 s within 1%% of |v| (%d do not)" % (nt1, t1bad))
    order = sorted(res, key=lambda i: int(meta[i]["cat"]))
    nn = {i: float(plan[i][0]["MEAN_MOTION"]) for i in res}
    done, bad = t3(order, {i: res[i]["B"][2] for i in res}, {i: res[i]["ref"] for i in res}, nn)
    log.check(len(order) < 2 or bad == 0, "T3 swapped identities: %d of %d checks compared, %d within 100 km" % (done, len(order), bad))
    # the per-object table (the ledger's)
    head = ["idx", "cat", "group", "status", "why", "seed_epoch", "new_epoch", "e_q", "horizon_h", "age_h", "perigee_km", "seed_age_d", "flags1", "bc1"]
    for m in METHODS_A + ["B"]:
        head += ["%s_kc" % m, "%s_m" % m, "%s_R" % m, "%s_A" % m, "%s_C" % m, "%s_pos" % m]
    head += ["ref_state"]
    lines = ["# h_check slot %d, log %s; per object (decision 13: the ledger only)" % (a.j, os.path.basename(log.path)), "\t".join(head)]
    for i in sorted(rows_out):
        d = meta[i]
        st = rows_out[i]
        row = [str(i), d["cat"], d["group"], st["status"], st.get("why", "")]
        if i in plan:
            r, eq, use = plan[i]
            e0 = H.epoch_tdb(seedrow[i])
            row += [seedrow[i]["EPOCH"], r["EPOCH"], float.hex(eq), "%.4f" % (float(H.epoch_tdb(r) - e0) / 3600.0), "%.4f" % ((eq - ts) / 3600.0),
                    d["perigee_km"], "%.4f" % (float(d["age_s"]) / 86400.0), d["flags1"], d["bc1"]]
        else:
            row += [""] * 9
        for m in METHODS_A + ["B"]:
            if i in res and m in res[i]:
                dd, rc, p = res[i][m]
                kc = str(plan[i][2][m]["k"]) if m in plan[i][2] else ""
                row += [kc, "%.3f" % dd, "%.3f" % rc[0], "%.3f" % rc[1], "%.3f" % rc[2], ",".join(float.hex(x) for x in p)]
            else:
                row += [""] * 6
        row += [",".join(float.hex(x) for x in res[i]["ref"]) if i in res else ""]
        lines.append("\t".join(row))
    tp = os.path.join(cdir, "slot%02d.tsv" % a.j)
    H.write_new(tp, ("\n".join(lines) + "\n").encode("ascii"))
    log.w("# per-object table %s, %d rows, sha256 %s" % (os.path.basename(tp), len(lines) - 2, H.sha256(tp)))
    for m in METHODS_A + ["B"]:
        for lab, keep in (("all", lambda i: True), ("without flagged fits", lambda i: not (int(meta[i]["flags1"]) & 3))):
            v = sorted(res[i][m][0] for i in res if m in res[i] and keep(i))
            if v:
                log.w("MEASURED slot %d %s %s: n %d, median %.3f km, 90th %.3f km; parts' medians |R| %.3f |A| %.3f |C| %.3f km" % (
                    a.j, m, lab, len(v), H.median(v) / 1e3, H.quant(v, 0.9) / 1e3,
                    H.median([abs(res[i][m][1][0]) for i in res if m in res[i] and keep(i)]) / 1e3,
                    H.median([abs(res[i][m][1][1]) for i in res if m in res[i] and keep(i)]) / 1e3,
                    H.median([abs(res[i][m][1][2]) for i in res if m in res[i] and keep(i)]) / 1e3))
            else:
                log.w("MEASURED slot %d %s %s: n 0" % (a.j, m, lab))
    return log.close()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["slot"])
    ap.add_argument("run")
    ap.add_argument("j", type=int)
    ap.add_argument("--procs", type=int, default=4)
    a = ap.parse_args()
    return cmd_slot(a)


if __name__ == "__main__":
    sys.exit(main())
