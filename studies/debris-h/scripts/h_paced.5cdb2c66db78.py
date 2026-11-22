# h_paced.py - cft-debris M1 (DEBRIS-H): the paced dry run and its control C5, through the service. Standard library
# only; amd-arc-box (the lead's, under a notice), and the desktop as a short functional test.
# cft-debris, MIT licence (see LICENSE at the repository root). Written by DEBRIS-H, 2026-11-18.
#
#   python3 -I -B in/tests/h_paced.py <root> [--minutes 30] [--n 64] [--c5-offset 600] [--c5-steps 80] [--logs DIR]
#       [--keep DIR] [--cpu TSV]
# The box's defaults are the brief's; the desktop's functional test passes smaller ones, and its log says so.
import argparse
import os
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import h_lib as H  # noqa: E402

SCRIPT = os.path.abspath(__file__)
TRACKS = [("P256", "cft256"), ("P64", "native64")]

CRITERIA = """
THE PACED DRY RUN (DEBRIS-H's brief): the test seed's objects (in/testseed/seed1.txt; 64 on the box) at cft256 on 1
worker and at native64 on 1, through tests/h_service.py, for the given minutes (30 on the box) at the real clock's
pace, the clock map shifted so that T_s falls a minute after the launch, the fetcher off.
  P1 no step starts more than 60 s before it is due (start >= due - 60 s, less 1 us for the log's resolution);
  P2 in every minute whose foreign load (the supervisor's LOAD line, /proc/stat less the service's own CPU, as a share
     of the machine's CPUs) is under 5%, no step finishing in that minute is late (lag <= 0);
  P2 is reported NOT DETERMINED (never passed) unless at least half the run's minutes qualify (fixed here, before the
     data: the brief sets no count). Reported beside: the share of late steps, the largest lag, by track.
CONTROL C5: the same run (the given steps; 80 on the box) with its clock map 600 s in the past must log late steps from
  its start, then catch up. r = 15 s x the late steps / their wall time (the first step's start to the last late
  step's finish); the first step that is not late must finish T = 600 / (r - 1) s after the first step's start, the
  measured time within 10% of T, for each track (the offset is the map's, D; T = D / (r - 1)). C5's run writes no
  checkpoint between T_s and its end (--ckpt-every 1000000): with D = 600 s and 15 s steps it catches up at step 40,
  a checkpoint step, and a native64 worker's whole late phase lasts about as long as one checkpoint's write (DEBRIS-H's
  desktop functional test, h_paced.002.log, before the box's run).
"""


def svc(args, wait=True):
    argv = [sys.executable, "-I", "-B", os.path.join(HERE, "h_service.py")] + [str(a) for a in args]
    p = H.popen(argv, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    out, _ = p.communicate()
    return p.returncode, out.decode("utf-8", "replace")


def steps(run, nm):
    d = os.path.join(run, "steps", nm)
    out = []
    for f in sorted(os.listdir(d)):
        for ln in open(os.path.join(d, f), encoding="ascii"):
            q = ln.split()
            if q and q[0] == "S":
                out.append((int(q[1]), float(q[2]), float(q[3]), float(q[4]), float(q[5]), float(q[6])))
    return out


def loads(run):
    out = []
    d = os.path.join(run, "logs")
    for f in sorted(os.listdir(d)):
        if f.startswith("service."):
            for ln in open(os.path.join(d, f), encoding="utf-8"):
                if " LOAD " in ln:
                    q = ln.split()
                    out.append((float(q[2]), float(q[3]), float(q[q.index("foreign_share") + 1])))
    return out


def main():
    global HERE
    ap = argparse.ArgumentParser()
    ap.add_argument("root")
    ap.add_argument("--minutes", type=float, default=30.0)
    ap.add_argument("--n", type=int, default=64)
    ap.add_argument("--c5-offset", type=float, default=600.0)
    ap.add_argument("--c5-steps", type=int, default=80)
    ap.add_argument("--skip-paced", action="store_true")
    ap.add_argument("--logs", default="logs")
    ap.add_argument("--keep")
    ap.add_argument("--cpu")
    a = ap.parse_args()
    os.chdir(a.root)
    HERE = os.path.relpath(os.path.dirname(SCRIPT))
    cpu = H.CpuAccount("h_paced", a.cpu)
    log = H.Log("h_paced", a.logs, SCRIPT, CRITERIA, extra=[os.path.join(HERE, "h_service.py")], keep_dir=a.keep)
    if (a.minutes, a.n, a.c5_offset, a.c5_steps) != (30.0, 64, 600.0, 80):
        log.w("# TEST ONLY: minutes %g, objects %d, C5 offset %g s, C5 steps %d (the brief's: 30, 64, 600, 80) - a functional test, never the gate" % (
            a.minutes, a.n, a.c5_offset, a.c5_steps))
    _, base = H.next_numbered("paced", "run", "")
    os.makedirs(base)
    seedp = "in/testseed/seed1.txt"
    lines = open(seedp, encoding="ascii").read().splitlines()
    head = [ln for ln in lines if ln.startswith("#")]
    body = [ln for ln in lines if ln and not ln.startswith("#")][:a.n]
    sub = os.path.join(base, "seed_paced.txt")
    H.write_new(sub, ("\n".join(head + ["# the first %d objects of %s (sha256 %s)" % (a.n, seedp, H.sha256(seedp))] + body) + "\n").encode("ascii"))
    log.w("# seed: %d objects, sha256 %s; m1h sha256 %s" % (len(body), H.sha256(sub), H.sha256("build/m1h" + (".exe" if H.WIN else ""))))
    tr = sum((["--track", "%s:%s:%s:1" % (nm, kd, sub)] for nm, kd in TRACKS), [])
    if not a.skip_paced:
        run = os.path.join(base, "paced")
        kend = int(round(a.minutes * 4))
        rc, out = svc(["init", ".", run, "--kend", kend, "--clock", "launch:+60"] + tr)
        log.check(rc == 0, "the paced run initialised (%s)" % out.strip())
        rc, out = svc(["start", ".", run])
        log.check(rc == 0, "the paced run ended (exit %d)" % rc)
        ld = loads(run)
        if H.WIN:
            log.w("# desktop: no /proc/stat, so no foreign load: P2 is NOT DETERMINED here")
        for nm, kd in TRACKS:
            st = steps(run, nm)
            early = [s for s in st if s[1] < s[3] - 60.0 - 1e-6]
            log.check(len(st) == kend and not early, "P1 %s: %d steps, none started more than 60 s before it was due (earliest start %.3f s before due)" % (
                nm, len(st), max(s[3] - s[1] for s in st)))
            late = [s for s in st if s[4] > 0]
            qual, bad = set(), 0
            for (t0, t1, sh) in ld:
                if sh < 0.05:
                    qual.add((t0, t1))
            ins = [s for s in st if any(t0 <= s[2] < t1 for t0, t1 in qual)]
            bad = [s for s in ins if s[4] > 0]
            minutes = len(ld)
            log.w("MEASURED %s (%s, 1 worker, %d lanes, nice 19): late steps %d of %d (%.4f); largest lag %.3f s; LOAD minutes %d, under 5%%: %d; steps in them %d" % (
                nm, kd, len(body), len(late), len(st), len(late) / max(1, len(st)), max(s[4] for s in st), minutes, len(qual), len(ins)))
            if not H.WIN and len(qual) * 2 >= max(1, int(a.minutes)):
                log.check(not bad, "P2 %s: in the %d minutes with foreign load under 5%%, no step late (%d late)" % (nm, len(qual), len(bad)))
            else:
                log.w("NOT DETERMINED P2 %s: %d qualifying minutes of %g (at least half needed)" % (nm, len(qual), a.minutes))
    # C5
    run = os.path.join(base, "c5")
    # no checkpoint between T_s and the end: with the 600 s offset and 15 s steps the run catches up at step 40, a
    # checkpoint step, and a native64 worker's whole late phase (tens of ms) is the size of one checkpoint's write
    rc, out = svc(["init", ".", run, "--kend", a.c5_steps, "--clock", "launch:-%g" % a.c5_offset, "--ckpt-every", 1000000] + tr)
    rc, out = svc(["start", ".", run])
    log.check(rc == 0, "C5's run ended (exit %d)" % rc)
    for nm, kd in TRACKS:
        st = steps(run, nm)
        if not st or st[0][4] <= 0:
            log.check(False, "C5 %s: the first step is late (lag %s)" % (nm, st[0][4] if st else None))
            continue
        L = 0
        while L < len(st) and st[L][4] > 0:
            L += 1
        if L == len(st):
            log.check(False, "C5 %s: the run never caught up in %d steps" % (nm, len(st)))
            continue
        s0 = st[0][1]
        wall_late = st[L - 1][2] - s0
        r = 15.0 * L / wall_late
        T = a.c5_offset / (r - 1.0)
        meas = st[L][2] - s0
        log.w("MEASURED C5 %s: %d late steps over %.3f s of wall time, r = %.3f; T = %.3f s; the first step not late (step %d) finished %.3f s after the first step's start (ratio %.4f)" % (
            nm, L, wall_late, r, T, st[L][0], meas, meas / T))
        log.check(abs(meas - T) <= 0.1 * T, "C5 %s: late from its start, then caught up, at T = D/(r - 1) within 10%% - as specified" % nm)
    c_ = cpu.close("h_paced log %03d" % log.n)
    if c_ is not None:
        log.w("# CPU: %.2f s by cycles / 2.5e9 (this script and every process it started)" % c_)
    return log.close()


if __name__ == "__main__":
    sys.exit(main())
