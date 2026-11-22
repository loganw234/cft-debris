# h2_gate.py - cft-debris M1 (DEBRIS-H), gate H2: the service's determinism - a kill and restart, a changed worker
# count and a pause leave every checkpoint bit for bit as an unbroken run's. Standard library only; on amd-arc-box (the
# lead's) and on the desktop (a functional test at a small size).
# cft-debris, MIT licence (see LICENSE at the repository root). Written by DEBRIS-H, 2026-11-18.
#
#   python3 -I -B in/tests/h2_gate.py <root> --size box|desktop [--logs DIR] [--keep DIR] [--cpu TSV]
# Works from <root> (in/ and build/), through tests/h_service.py and tests/m1h.c; the runs go to <root>/h2/.
import argparse
import json
import os
import shutil
import signal
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import h_lib as H  # noqa: E402

SCRIPT = os.path.abspath(__file__)
SIZES = {
    # objects, steps, checkpoint interval, the kill's step, the pause's step, workers for R2
    "box": {"n": 16, "steps": 120, "ck": 40, "kill": 57, "pause": 50, "w2": 4},
    "desktop": {"n": 4, "steps": 12, "ck": 4, "kill": 6, "pause": 6, "w2": 2},
}
KINDS = [("H2c", "cft256"), ("H2n", "native64")]
PAUSE_S = 30.0

CRITERIA = """
H2 (DEBRIS-H's brief), at the size given: box - the test seed's first 16 objects, 120 steps from T_s, checkpoints
every 40, the kill after step 57, the pause after step 50, R2 with 4 workers; desktop (a functional test) - 4 objects,
12 steps, checkpoints every 4, the kill after step 6, the pause after step 6, R2 with 2 workers. Each kind runs in its own
service (on the desktop the gate, the supervisor and its workers stay within 4 processes; and one PAUSE file serves a run). Every run is tests/h_service.py
with the clock map in the past (every step due at once), cft256 and native64 tracks from seed1.txt, the fetcher off.
  R0 unbroken, one worker a kind;
  R1 the worker killed by SIGKILL right after the fixed step (between the first and second checkpoints; the driver's
     --test-kill-after delivers it to itself, since a native64 worker passes the run in well under a second), and
     restarted by the supervisor from the first checkpoint;
  R2 run to the second checkpoint and ended (start --stop-at), then restarted from it with more workers (start --workers);
  R3 paused for 30 s after the fixed step (the gate's PAUSE file, created before the start and honoured from the step
     after the fixed one, --test-pause-from; the gate removes it 30 s after the worker logs the pause), then resumed.
CRITERION: the checkpoints at 1, 2 and 3 intervals (40, 80 and 120 on the box) are bit-identical across R0 to R3, at
  each kind: every object's state in the kind's bytes, as binary64, its decay mark, bc and cram (the NaN rule); and R1's
  supervisor restarted from the first checkpoint, R2's from the second with the larger worker count.
CONTROLS, each must fail as specified:
  C2 a copy of R2's run folder after its first half, with one byte of the cft256 track's second checkpoint changed:
     the supervisor refuses that file by its hash and starts that track from the first checkpoint, never the second;
  C3 a restart planted one step off - checkpoint 1's states given as step (1 interval + 1), run to 3 intervals by
     tests/m1h.c directly - must give a checkpoint at 3 intervals whose bytes differ from R0's for every object;
  C4 R3's pause must appear in its step log as a pause record of 25 to 45 s between the fixed step and the next, and
     as lag: lag(next) - lag(fixed) + 15 s - compute(next) >= 25 s.
"""


def py():
    return sys.executable


def svc(args, wait=True, timeout=3600):
    argv = [py(), "-I", "-B", os.path.join(HERE, "h_service.py")] + [str(a) for a in args]
    if not wait:
        return H.popen(argv, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    p = H.popen(argv, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    out, _ = p.communicate(timeout=timeout)
    return p.returncode, out.decode("utf-8", "replace")


def ckpt_states(run, track, k):
    """every object's line at step k from the run's manifest (all files listed for that step, each matching its hash)"""
    out = {}
    for ln in open(os.path.join(run, "manifest.tsv"), encoding="ascii"):
        if ln.startswith("#"):
            continue
        q = ln.rstrip("\n").split("\t")
        if q[1] == track and int(q[2]) == k:
            assert H.sha256(q[3]) == q[4], "a checkpoint changed after the manifest: %s" % q[3]
            for i, row in H.read_ckpt(q[3])[1].items():
                out.setdefault(i, row)
    return out


def same_rows(a, b, nb):
    if set(a) != set(b) or not a:
        return False
    for i in a:
        x, y = a[i], b[i]
        if x[0] != y[0] or x[3] != y[3] or x[4] != y[4]:
            return False
        if not all(H.same(p, q, nb) for p, q in zip(x[1], y[1])) or not all(H.same(p, q, 64) for p, q in zip(x[2], y[2])):
            return False
    return True


def service_log(run):
    out = []
    d = os.path.join(run, "logs")
    for f in sorted(os.listdir(d)):
        if f.startswith("service."):
            out += open(os.path.join(d, f), encoding="utf-8").read().splitlines()
    return out


def main():
    global HERE
    ap = argparse.ArgumentParser()
    ap.add_argument("root")
    ap.add_argument("--size", choices=sorted(SIZES), required=True)
    ap.add_argument("--logs", default="logs")
    ap.add_argument("--keep")
    ap.add_argument("--cpu")
    a = ap.parse_args()
    os.chdir(a.root)
    HERE = os.path.relpath(os.path.dirname(SCRIPT))
    S = SIZES[a.size]
    n, K, C = S["n"], S["steps"], S["ck"]
    cpu = H.CpuAccount("h2_gate_%s" % a.size, a.cpu)
    log = H.Log("h2_gate_%s" % a.size, a.logs, SCRIPT, CRITERIA, extra=[os.path.join(HERE, "h_service.py")], keep_dir=a.keep)
    exe = "build/m1h" + (".exe" if H.WIN else "")
    seedp = "in/testseed/seed1.txt"
    for p in (exe, seedp, "in/frame_h0.bin"):
        log.w("# %s sha256 %s" % (p, H.sha256(p)))
    _, base = H.next_numbered("h2", "gate", "")
    os.makedirs(base)
    # the sub-seed: the test seed's first n objects
    lines = open(seedp, encoding="ascii").read().splitlines()
    head = [ln for ln in lines if ln.startswith("#")]
    body = [ln for ln in lines if ln and not ln.startswith("#")][:n]
    sub = os.path.join(base, "seed_h2.txt")
    H.write_new(sub, ("\n".join(head + ["# H2: the first %d objects of %s (sha256 %s)" % (n, seedp, H.sha256(seedp))] + body) + "\n").encode("ascii"))
    log.w("# the sub-seed: %d objects, sha256 %s" % (n, H.sha256(sub)))
    groups = [[k] for k in KINDS]  # each kind in its own service (the pause file is the run's, and the desktop's 4 processes)
    nb = {"H2c": 256, "H2n": 64}
    results = {}

    def init(run, kinds, extra=()):
        args = ["init", ".", run, "--kend", K, "--ckpt-every", C, "--clock", "past", "--lanes", 64] + list(extra)
        for name, kind in kinds:
            args += ["--track", "%s:%s:%s:1" % (name, kind, sub)]
        rc, out = svc(args)
        if rc != 0:
            log.w("#   " + out.replace("\n", "\n#   "))
        return rc == 0

    for kinds in groups:
        tag = "+".join(k for _, k in kinds)
        # R0
        r0 = os.path.join(base, "R0_" + tag)
        init(r0, kinds)
        rc, _ = svc(["start", ".", r0])
        log.check(rc == 0, "R0 %s: the service ran to its end (exit %d)" % (tag, rc))
        # R1
        r1 = os.path.join(base, "R1_" + tag)
        init(r1, kinds, sum((["--test-kill-after", "%s=%d" % (nm, S["kill"])] for nm, _ in kinds), []))
        rc, _ = svc(["start", ".", r1])
        sl = service_log(r1)
        for nm, kd in kinds:
            killed = [ln for ln in sl if ("EXIT %s worker 0 of 1" % nm) in ln and "code 0" not in ln]
            restart = [ln for ln in sl if ("START %s " % nm) in ln and "RESTART 1" in ln]
            log.check(len(killed) == 1 and len(restart) == 1 and ("from checkpoint %d " % C) in restart[0],
                      "R1 %s: the worker killed after step %d exited abnormally (%s) and the supervisor restarted it from checkpoint %d" % (
                          nm, S["kill"], killed[0].split("code")[-1].strip() if killed else "?", C))
            stl = [f for f in os.listdir(os.path.join(r1, "steps", nm)) if f.endswith(".log")]
            first = [os.path.join(r1, "steps", nm, f) for f in stl if ".k000000." in f]
            lastk = [ln.split()[1] for ln in open(first[0]) if ln.startswith("S ")][-1] if first else None
            log.check(lastk == str(S["kill"]), "R1 %s: the killed worker's last step was %s (fixed: %d, between %d and %d)" % (nm, lastk, S["kill"], C + 1, 2 * C - 1))
        # R2
        r2 = os.path.join(base, "R2_" + tag)
        init(r2, kinds)
        rc, _ = svc(["start", ".", r2, "--stop-at", 2 * C])
        log.check(rc == 0, "R2 %s: the first half ran to checkpoint %d" % (tag, 2 * C))
        c2 = os.path.join(base, "C2_" + tag)
        shutil.copytree(r2, c2)
        wargs = sum((["--workers", "%s=%d" % (nm, S["w2"])] for nm, _ in kinds), [])
        rc, _ = svc(["start", ".", r2] + wargs)
        sl = service_log(r2)
        for nm, kd in kinds:
            st = [ln for ln in sl if ("START %s " % nm) in ln]
            log.check(len(st) == 2 and ("%d workers from checkpoint %d " % (S["w2"], 2 * C)) in st[1],
                      "R2 %s: restarted from checkpoint %d with %d workers" % (nm, 2 * C, S["w2"]))
        # C2: one byte of the cft256 track's second checkpoint changed, in a copy
        nmc = [nm for nm, kd in kinds if kd == "cft256"]
        if nmc:
            nm = nmc[0]
            f80 = os.path.join(c2, "ckpt", nm, "k%06d.w00of01.txt" % (2 * C))
            # the manifest names the original run folder's files; the copy's must name its own
            man = open(os.path.join(c2, "manifest.tsv"), encoding="ascii").read().replace(r2.replace("\\", "/") + "/", c2.replace("\\", "/") + "/")
            with open(os.path.join(c2, "manifest.tsv"), "wb") as f:
                f.write(man.encode("ascii"))
            b = bytearray(open(f80, "rb").read())
            pos = b.index(b"\n", b.index(b"\n") + 1) + 5  # inside the first object's line
            b[pos] = ord("0") if b[pos] != ord("0") else ord("1")
            with open(f80, "wb") as f:
                f.write(bytes(b))
            p = svc(["start", ".", c2], wait=False)
            t0 = time.time()
            started = []
            while time.time() - t0 < 120 and not started:
                time.sleep(0.5)
                try:
                    started = [ln for ln in service_log(c2) if ("START %s " % nm) in ln][1:]
                except OSError:
                    pass
            if H.WIN:
                H.write_new(os.path.join(c2, "STOP"), b"C2 done\n")
            else:
                os.kill(p.pid, signal.SIGTERM)
            p.wait(timeout=600)
            sl = service_log(c2)
            refused = [ln for ln in sl if "REFUSED %s k %d" % (nm, 2 * C) in ln]
            log.check(bool(refused) and started and ("from checkpoint %d " % C) in started[0] and "k%06d" % (2 * C) not in started[0],
                      "C2 the changed checkpoint %d of %s is refused by its hash and the track starts from checkpoint %d - failed as specified" % (2 * C, nm, C))
        # R3
        r3 = os.path.join(base, "R3_" + tag)
        init(r3, kinds, sum((["--test-pause-from", "%s=%d" % (nm, S["pause"])] for nm, _ in kinds), []))
        H.write_new(os.path.join(r3, "PAUSE"), b"H2 R3\n")
        p = svc(["start", ".", r3], wait=False)
        t0 = time.time()
        seen = set()
        while time.time() - t0 < 900 and len(seen) < len(kinds):
            time.sleep(0.2)
            for nm, _ in kinds:
                d = os.path.join(r3, "steps", nm)
                if os.path.isdir(d):
                    for f in os.listdir(d):
                        if any(ln.startswith("p ") for ln in open(os.path.join(d, f))):
                            seen.add(nm)
        t_seen = time.time()
        time.sleep(max(0.0, PAUSE_S - (time.time() - t_seen)))
        os.remove(os.path.join(r3, "PAUSE"))  # the gate's own pause file
        p.wait(timeout=3600)
        for nm, _ in kinds:
            d = os.path.join(r3, "steps", nm)
            L = [ln.split() for f in sorted(os.listdir(d)) for ln in open(os.path.join(d, f))]
            S_ = {int(x[1]): x for x in L if x[0] == "S"}
            P_ = [x for x in L if x[0] == "P"]
            iP = [i for i, x in enumerate(L) if x[0] == "P"]
            iA = [i for i, x in enumerate(L) if x[0] == "S" and x[1] == str(S["pause"])]
            iB = [i for i, x in enumerate(L) if x[0] == "S" and x[1] == str(S["pause"] + 1)]
            ok_place = len(iP) == 1 and iA and iB and iA[0] < iP[0] < iB[0]
            dur = float(P_[0][3]) if P_ else 0.0
            a_, b_ = S_.get(S["pause"]), S_.get(S["pause"] + 1)
            extra = (float(b_[5]) - float(a_[5]) + 15.0 - float(b_[6])) if a_ and b_ else 0.0
            log.check(ok_place and 25.0 <= dur <= 45.0 and extra >= 25.0,
                      "C4 R3 %s: the pause is in the step log between steps %d and %d (%.1f s), and as lag (%.1f s added beyond the step) - as specified" % (
                          nm, S["pause"], S["pause"] + 1, dur, extra))
        # the criterion
        for nm, kd in kinds:
            for kk in (C, 2 * C, 3 * C):
                ref = ckpt_states(r0, nm, kk)
                for rn, rr in (("R1", r1), ("R2", r2), ("R3", r3)):
                    ok = same_rows(ref, ckpt_states(rr, nm, kk), nb[nm])
                    results[(nm, kk, rn)] = ok
            log.check(all(results[(nm, kk, rn)] for kk in (C, 2 * C, 3 * C) for rn in ("R1", "R2", "R3")),
                      "H2 %s (%s): checkpoints %d, %d and %d bit-identical across R0, R1, R2 and R3 for all %d objects" % (nm, kd, C, 2 * C, 3 * C, n))
        # C3: checkpoint C's states as step C + 1, run to 3 C directly
        for nm, kd in kinds:
            src = os.path.join(r0, "ckpt", nm, "k%06d.w00of01.txt" % C)
            d3 = os.path.join(base, "C3_" + nm)
            os.makedirs(d3)
            txt = open(src, encoding="ascii").read().replace(" k %d ts " % C, " k %d ts " % (C + 1), 1)
            cp = os.path.join(d3, "planted_k%d_as_%d.txt" % (C, C + 1))
            H.write_new(cp, txt.encode("ascii"))
            cm = json.load(open(os.path.join(r0, "clock_map.json"), encoding="ascii"))
            env = dict(os.environ)
            env["M1_DOWNLOADS"] = "in/dl/"
            H.run([exe, "run", "--kind", kd, "--table", "in/frame_h0.bin", "--track", nm, "--run", d3, "--first", 0, "--count", n, "--lanes", 64,
                   "--k0", C + 1, "--kend", 3 * C, "--unix-ref", "%.6f" % cm["unix_ref"], "--t-ref", float.hex(cm["t_ref"]), "--allow", 4,
                   "--ckpt-every", C, "--worker", 0, "--nworkers", 1, "--init", "%s:%s" % (cp, H.sha256(cp))], log, env=env)
            planted = H.read_ckpt(os.path.join(d3, "ckpt", nm, "k%06d.w00of01.txt" % (3 * C)))[1]
            ref = ckpt_states(r0, nm, 3 * C)
            ndiff = sum(1 for i in ref if i in planted and planted[i][1] != ref[i][1])
            log.check(ndiff == n == len(planted), "C3 %s: the restart planted one step off gives checkpoint %d different from R0's for %d of %d objects - failed as specified" % (
                nm, 3 * C, ndiff, n))
    c_ = cpu.close("h2_gate log %03d" % log.n)
    if c_ is not None:
        log.w("# CPU: %.2f s by cycles / 2.5e9 (this script and every process it started)" % c_)
    return log.close()


if __name__ == "__main__":
    sys.exit(main())
