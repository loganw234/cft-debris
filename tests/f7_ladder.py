# f7_ladder.py - cft-debris M1 (DEBRIS-F), gate F7: the precision ladder on real objects.
# cft-debris, MIT licence (see LICENSE at the repository root). Written by DEBRIS-F, 2026-11-16, before F6 had run.
#
#   python -I -B tests/f7_ladder.py [table]
#
# Per-object values stay in the scratch and the ledger's debris-f\ (decision 11); this log holds the aggregates.
import json
import math
import os
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import f_lib as F  # noqa: E402
import f_fit as FF  # noqa: E402

CRITERIA = """
THE OBJECTS: 10 of F6's pairs, the lowest S0 perigees first among those whose (A) fit converged (F6's scratch record
  f6/f6_pairs.json); the 3 lowest also at cft256.
THE START: one native64 run carries each object from its fit (origin O, F6's (A) fit) to e0q = O + 86400 s exactly
  (5,760 steps of 15 s); that binary64 state, with the fitted bc and cram 0.01, goes to every kind exactly.
THE ARC: from origin e0q, 1,440 rk4 steps of 15 s (6 hours), the full model of B4 in the window's table, at native64
  (the C library's transcendentals), cft64, cft128 and (3 objects) cft256; states sampled every hour. Each object runs
  as its own batch of one lane: their e0q differ, so no common start epoch exists without a further run.
L1 MEASURED: each kind's |r - r_widest| at each hour, the widest being cft256 where it ran, else cft128.
L2 THE BOUND for cft128, stated before the data as DEBRIS-E's E3: B = N_ops x u128 x R x G, with N_ops the run's own
   count of lane-operations, u128 = 2^-113, R = 7.1e6 m and G = 120 (E3's linearised Kepler growth of 30 over one orbit,
   times the four orbits of 6 hours); an ESTIMATE-based bound, not a rigorous one. Every |r_cft128 - r_cft256| over the 3
   objects and 6 hours must be <= B.
C1 NEGATIVE CONTROL (E3's): the lowest object at cft128 with the central term's -GM/r^3 rounded to binary64 at every
   evaluation (m1f prop --round64) must exceed B against cft256 at 6 hours.
"""

TABLE = sys.argv[1] if len(sys.argv) > 1 else F.DATA + "/tables/frame_main.bin"


def run_many(jobs, log, nmax=4):
    """jobs: (label, args); at most nmax at once, each through cpurun"""
    running, done = [], []
    pend = list(jobs)
    while pend or running:
        while pend and len(running) < nmax:
            label, args = pend.pop(0)
            cmd = [F.PY, "-I", "-B", os.path.join(F.REPO, "tests", "cpurun.py"), label, F.CPU_TSV, "--"] + [str(a) for a in args]
            running.append((label, subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE), time.perf_counter()))
        time.sleep(0.5)
        for r in list(running):
            if r[1].poll() is not None:
                out, err = r[1].communicate()
                log.w("# ran %s (%.1f s wall, exit %d) %s" % (r[0], time.perf_counter() - r[2], r[1].returncode, err.decode("utf-8", "replace").strip()[-160:]))
                if r[1].returncode != 0:
                    raise RuntimeError("%s failed: %s" % (r[0], err.decode("utf-8", "replace")))
                running.remove(r)
                done.append(r[0])
    return done


BITS = {"native64": 64, "cft64": 64, "cft128": 128, "cft256": 256}


def read_prop(path, kind):
    """the states at each target, exact: the kind's own encoding (the hex columns), not their binary64 roundings"""
    out, ops = {}, None
    for ln in open(path):
        p = ln.split()
        if p and p[0] == "P":
            out.setdefault(p[1], []).append((float.fromhex(p[2]), [F.value(x, BITS[kind]) for x in p[9:15]]))
        elif ln.startswith("# lane-ops"):
            ops = sum(int(x.split("=")[1]) for x in p[2:])
    return out, ops


def main():
    log = F.Log("f7_ladder", os.path.abspath(__file__), CRITERIA)
    exe = F.BUILD + "/m1f_O2.exe"
    log.w("# m1f_O2.exe sha256 %s; table %s sha256 %s" % (F.sha256(exe), TABLE, F.sha256(TABLE)))
    W = F.WORK + ("/dry/f7" if F.DRY else "/f7")
    F6W = F.WORK + ("/dry/f6" if F.DRY else "/f6")
    NSEL, STEP_H = (3, 60.0) if F.DRY else (10, 3600.0)   # a dry run: 3 objects, 6 minutes
    os.makedirs(W, exist_ok=True)
    pairs = json.load(open(F6W + "/f6_pairs.json"))
    log.w("# F6's record: %d pairs (sha256 %s)" % (len(pairs), F.sha256(F6W + "/f6_pairs.json")))
    sel = sorted((p for p in pairs if p["conv"]), key=lambda p: p["perigee"])[:NSEL]
    log.check(len(sel) == NSEL, "%d objects selected (perigees %.0f to %.0f km)" % (NSEL, sel[0]["perigee"], sel[-1]["perigee"]))
    # the start: native64 from the fit to e0q
    items = [("o%d" % i, p["t0"], p["y"], p["bc"], [p["e0q"]]) for i, p in enumerate(sel)]
    for i, p in enumerate(sel):
        assert p["e0q"] == p["t0"] + 86400.0
    st = FF.predict(items, W, "start", TABLE, exe, kind="native64", log=log, cpu_label="f7_start")
    starts = {k: v[0][1] for k, v in st.items()}
    log.check(len(starts) == NSEL, "every object carried to e0q")
    # the arcs
    tg = lambda e0: [e0 + STEP_H * h for h in range(1, 7)]
    kinds = {i: ["native64", "cft64", "cft128"] + (["cft256"] if i < 3 else []) for i in range(NSEL)}
    jobs = []
    for i, p in enumerate(sel):
        path = W + "/arc_o%d_in.txt" % i
        with open(path, "w", newline="\n") as f:
            f.write("OBJ o%d %s %s %s %s 0 0 6\n" % (i, float.hex(p["e0q"]), " ".join(float.hex(x) for x in starts["o%d" % i]), float.hex(p["bc"]), float.hex(FF.CRAM)))
            for k, T in enumerate(tg(p["e0q"])):
                f.write("T %d %s\n" % (k, float.hex(T)))
        for kind in kinds[i]:
            jobs.append(("f7_o%d_%s" % (i, kind), [exe, "prop", kind, TABLE, path, W + "/arc_o%d_%s.txt" % (i, kind)]))
    jobs.append(("f7_ctl_round64", [exe, "prop", "cft128", TABLE, W + "/arc_o0_in.txt", W + "/arc_o0_cft128_r64.txt", "--round64"]))
    # the widest first, so that the long runs start early
    jobs.sort(key=lambda j: 0 if "cft256" in j[0] else 1 if "cft128" in j[0] else 2)
    run_many(jobs, log, nmax=4)
    res, ops = {}, {}
    for i in range(NSEL):
        for kind in kinds[i]:
            r, o = read_prop(W + "/arc_o%d_%s.txt" % (i, kind), kind)
            res[(i, kind)] = r["o%d" % i]
            ops[(i, kind)] = o
    rc, _ = read_prop(W + "/arc_o0_cft128_r64.txt", "cft128")
    def dr(a, b):
        return [math.sqrt(float(sum((x - y) ** 2 for x, y in zip(u[1][:3], v[1][:3])))) for u, v in zip(a, b)]
    nops = max(ops[(i, "cft128")] for i in range(3))
    B = nops * 2.0 ** -113 * 7.1e6 * 120
    log.w("# L2 bound: N_ops %d (cft128's own count, the largest of the 3) x 2^-113 x 7.1e6 m x 120 = %.3e m" % (nops, B))
    for kind in ("native64", "cft64", "cft128"):
        for h in range(6):
            v = []
            for i in range(NSEL):
                wid = "cft256" if i < 3 else "cft128"
                if kind == wid:
                    continue
                v.append(dr(res[(i, kind)], res[(i, wid)])[h])
            if v:
                log.w("MEASURED L1 %s against the widest at %d h: max %.3e m, median %.3e m over %d objects" % (kind, h + 1, max(v), sorted(v)[len(v) // 2], len(v)))
    l2 = [d for i in range(3) for d in dr(res[(i, "cft128")], res[(i, "cft256")])]
    log.check(max(l2) <= B, "L2 cft128 within B of cft256 over 3 objects and 6 hours (max %.3e m; B %.3e m; %.1e of B)" % (max(l2), B, max(l2) / B))
    c = dr(rc["o0"], res[(0, "cft256")])[-1]
    log.check(c > B, "C1 the round64 control exceeds B at 6 hours (%.3e m = %.1e B)" % (c, c / B))
    os.makedirs(F.LEDGER_F, exist_ok=True)
    per = F.LEDGER_F + "/f7_ladder.%03d.tsv" % log.n
    with open(per, "w", newline="\n") as f:
        f.write("# F7 per-object differences from the widest run (derived from CelesTrak's S0; decision 11: ledger only). log %s\n" % os.path.basename(log.path))
        f.write("object\tkey\tperigee_km\tkind\t" + "\t".join("dr_%dh_m" % (h + 1) for h in range(6)) + "\n")
        for i, p in enumerate(sel):
            wid = "cft256" if i < 3 else "cft128"
            for kind in kinds[i]:
                if kind != wid:
                    f.write("o%d\t%s\t%.1f\t%s\t%s\n" % (i, p["key"], p["perigee"], kind, "\t".join("%.3e" % d for d in dr(res[(i, kind)], res[(i, wid)]))))
    log.w("# per-object table: the ledger's debris-f\\%s, sha256 %s" % (os.path.basename(per), F.sha256(per)))
    return log.close()


if __name__ == "__main__":
    sys.exit(main())
