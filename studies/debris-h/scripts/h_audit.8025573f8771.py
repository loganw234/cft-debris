# h_audit.py - cft-debris M1 (DEBRIS-H), H7(d): the long run's checkpoints audited. Standard library only; the lead runs
# it on amd-arc-box after the run (or at a visit), from the service's root.
# cft-debris, MIT licence (see LICENSE at the repository root). Written by DEBRIS-H, 2026-11-18, before the long run.
#
#   python3 -I -B in/tests/h_audit.py <root> <run> [--procs N] [--logs DIR] [--seed S (another sampler's seed: verifier-H)]
# Its sample is drawn by the seed below, fixed here before the run; --seed lets a verifier draw a sample of its own.
import argparse
import json
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import h_lib as H  # noqa: E402

SCRIPT = os.path.abspath(__file__)
SEED = 0xA0D17
NSEG = 10
NOBJ = 64

CRITERIA = """
H7(d), fixed before the long run (DEBRIS-H's brief):
 (d1) every 40 steps of each track, from 0 to the last step the track reached, a checkpoint whose files are all
      present, cover every object once, and each match the manifest's SHA-256 (a file listed twice for one step, a
      restart's rewrite, must match too);
 (d2) a sample of 10 segments per track - a segment is checkpoint k to checkpoint k + 40 - drawn by
      random.Random(0xA0D17) over the track's segments, always including every segment that follows a restart (a
      restart from checkpoint k: the segment k to k + 40), and in each 64 objects drawn by the same generator (all,
      if fewer); tests/m1h.c seg from checkpoint k by 40 whole steps (mode N, 64 lanes) must equal checkpoint k + 40's
      bytes for every object sampled: the kind's bytes, the binary64 bits and the decay mark (the NaN rule).
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root")
    ap.add_argument("run")
    ap.add_argument("--procs", type=int, default=10)
    ap.add_argument("--logs", default=None)
    ap.add_argument("--seed", type=lambda x: int(x, 0), default=SEED)
    a = ap.parse_args()
    os.chdir(a.root)
    run = a.run
    cfg = json.load(open(os.path.join(run, "service.json"), encoding="ascii"))
    log = H.Log("audit", a.logs or os.path.join(run, "logs"), SCRIPT, CRITERIA)
    if a.seed != SEED:
        log.w("# the sampler's seed is 0x%X, not the fixed 0x%X (a verifier's own sample)" % (a.seed, SEED))
    man = []
    for ln in open(os.path.join(run, "manifest.tsv"), encoding="ascii"):
        if ln.startswith("#") or not ln.strip():
            continue
        q = ln.rstrip("\n").split("\t")
        man.append({"track": q[1], "k": int(q[2]), "file": q[3], "sha": q[4], "first": int(q[5]), "count": int(q[6])})
    restarts = {}
    for f in sorted(os.listdir(os.path.join(run, "logs"))):
        if f.startswith("service."):
            for ln in open(os.path.join(run, "logs", f), encoding="utf-8"):
                if " START " in ln and "checkpoint" in ln and "workers from checkpoint" in ln:
                    p = ln.split()
                    trk = p[p.index("START") + 1]
                    k = int(ln.split("workers from checkpoint ")[1].split()[0])
                    restarts.setdefault(trk, set()).add(k)
    n = cfg["nobj"]
    ck = cfg["ckpt_every"]
    env = dict(os.environ)
    env["M1_DOWNLOADS"] = cfg["downloads"]
    rng = random.Random(a.seed)
    _, work = H.next_numbered(os.path.join(run, "audit"), "audit", "")
    os.makedirs(work)
    for t in cfg["tracks"]:
        trk, kind = t["name"], t["kind"]
        ks = sorted({m["k"] for m in man if m["track"] == trk})
        top = ks[-1] if ks else -1
        bad, cover = [], {}
        for k in range(0, top + 1, ck):
            rows = [m for m in man if m["track"] == trk and m["k"] == k]
            cov = [0] * n
            for m in rows:
                if H.sha256(m["file"]) != m["sha"]:
                    bad.append((k, m["file"]))
                for i in range(m["first"], m["first"] + m["count"]):
                    cov[i] += 1
            cover[k] = rows
            if not rows or min(cov) < 1:
                bad.append((k, "incomplete"))
        log.check(top >= 0 and not bad, "(d1) %s: every 40 steps from 0 to %d (%d checkpoints) complete, every file matching the manifest (%d problems%s)" % (
            trk, top, top // ck + 1 if top >= 0 else 0, len(bad), (": " + str(bad[:5])) if bad else ""))
        segs = [k for k in range(0, top, ck) if k + ck <= top]
        must = sorted(k for k in restarts.get(trk, set()) if k in segs)
        rest = [k for k in segs if k not in must]
        pick = must + sorted(rng.sample(rest, max(0, min(len(rest), NSEG - len(must)))))
        log.w("# %s: %d segments; the sample (%d): every segment after a restart %s, and %d drawn" % (trk, len(segs), len(pick), must, len(pick) - len(must)))
        cmds, plan = [], []
        for k in pick:
            objs = sorted(rng.sample(range(n), min(NOBJ, n)))
            tp = os.path.join(work, "%s_k%06d_targets.txt" % (trk, k))
            with open(tp, "w", newline="\n") as f:
                for i in objs:
                    f.write("%d %d N %d\n" % (i, k, ck))
            files = [m for m in cover[k] if any(m["first"] <= i < m["first"] + m["count"] for i in objs)]
            argv = [cfg["exe"], "seg", "--kind", kind, "--table", cfg["table"], "--targets", tp, "--out", os.path.join(work, "%s_k%06d_seg.txt" % (trk, k)),
                    "--lanes", 64]
            seen = set()
            for m in files:
                if m["file"] not in seen:
                    argv += ["--init", "%s:%s" % (m["file"], m["sha"])]
                    seen.add(m["file"])
            cmds.append((argv, os.path.join(work, "%s_k%06d" % (trk, k))))
            plan.append((k, objs))
        codes = H.run_pool(cmds, a.procs, log, env=env, nice=19 if not H.WIN else None)
        nb = 8 * H.ESZ[kind]
        okseg = 0
        for (k, objs), code in zip(plan, codes):
            if code != 0:
                log.w("# %s segment %d: seg failed (%d)" % (trk, k, code))
                continue
            got = {}
            for ln in open(os.path.join(work, "%s_k%06d_seg.txt" % (trk, k)), encoding="ascii"):
                p = ln.split()
                if p and p[0] == "R":
                    got[int(p[1])] = (int(p[6]), p[7:13], p[13:19])
            ref = {}
            for m in cover[k + ck]:
                for i, row in H.read_ckpt(m["file"])[1].items():
                    ref.setdefault(i, row)
            same = all(i in got and got[i][0] == ref[i][0] and all(H.same(x, y, nb) for x, y in zip(got[i][1], ref[i][1])) and
                       all(H.same(x, y, 64) for x, y in zip(got[i][2], ref[i][2])) for i in objs)
            okseg += same
            log.w("# %s segment %d to %d, %d objects: %s" % (trk, k, k + ck, len(objs), "equal" if same else "DIFFERENT"))
        log.check(len(pick) > 0 and okseg == len(pick), "(d2) %s: %d of %d sampled segments re-propagated by seg equal the next checkpoint's bytes" % (trk, okseg, len(pick)))
    return log.close()


if __name__ == "__main__":
    sys.exit(main())
