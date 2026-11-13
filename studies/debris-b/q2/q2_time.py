#!/usr/bin/env python3
"""DEBRIS-B Q2: time each kernel at binary64 (and SH gravity at binary128),
with negative control 1: "the compiler can discard work whose result is
never used".

- q2bench.exe folds every output component of every call into a checksum it
  prints, so the force build cannot drop the work.
- q2bench_noforce.exe is the same source with every kernel call compiled out
  (-DNO_FORCE). The same loop, the same ncall, must time at least 10 times
  faster; the assertion below fails the run otherwise.
- For the exponential atmosphere, which may be too cheap for that at one
  object a call, K objects a call is raised (1, 4, 16, 64) until it passes;
  every K tried is reported.

Each figure is the minimum over 5 repetitions of about 0.25 s; the median,
the thread's CPU time and cycles, and the host load during each repetition
(GetSystemTimes, all 12 logical CPUs) are printed beside it.

  python -I -B q2_time.py > q2_time.log
"""
import os
import statistics
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
FORCE = os.path.join(HERE, "q2bench.exe")
NOFORCE = os.path.join(HERE, "q2bench_noforce.exe")
ENV = dict(os.environ)
ENV["PATH"] = r"C:\msys64\mingw64\bin;" + ENV.get("PATH", "")
TARGET_S = 0.25
REPS = 5


def run(exe, kernel, param, ncall, reps):
    cmd = [exe, "time", kernel, str(param), str(ncall), str(reps)]
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=ENV)
    if p.returncode != 0:
        raise SystemExit("failed: %s\n%s" % (" ".join(cmd), p.stderr))
    rows = []
    for ln in p.stdout.splitlines():
        if ln.startswith("rep "):
            tk = ln.split()
            d = {tk[i]: tk[i + 1] for i in range(2, len(tk) - 1, 2)}
            rows.append(dict(wall=float(d["wall_ns_per_call"]), cpu=float(d["cpu_ns_per_call"]),
                             cyc=float(d["cycles_per_call"]), load=float(d["host_load_pct"]),
                             wall_s=float(d["wall_s"]), cs=d["checksum"]))
    return rows


def measure(kernel, param, label, per=1):
    """returns the force row summary; asserts the control unless soft"""
    cal = run(FORCE, kernel, param, 200, 1)[0]
    ncall = max(1000, int(TARGET_S / max(cal["wall"] * 1e-9, 1e-12)))
    f = run(FORCE, kernel, param, ncall, REPS)
    n = run(NOFORCE, kernel, param, ncall, REPS)
    fmin = min(r["wall"] for r in f)
    nmin = min(r["wall"] for r in n)
    ratio = fmin / nmin if nmin > 0 else float("inf")
    sums = sorted(set(r["cs"] for r in f))
    out = dict(kernel=kernel, param=param, label=label, ncall=ncall, per=per,
               wall_min=fmin, wall_med=statistics.median(r["wall"] for r in f),
               cpu_min=min(r["cpu"] for r in f), cyc_min=min(r["cyc"] for r in f),
               load=[r["load"] for r in f], nf_min=nmin, ratio=ratio, checksums=sums,
               nf_load=[r["load"] for r in n])
    print("%-28s ncall %8d | force: min %10.1f ns, median %10.1f ns, cpu %10.1f ns, %9.0f cycles a call"
          " | per unit %9.2f ns | no-force min %8.2f ns | ratio %8.1f | load %% %s | checksums %s" %
          (label, ncall, fmin, out["wall_med"], out["cpu_min"], out["cyc_min"], fmin / per, nmin, ratio,
           "/".join("%.0f" % x for x in out["load"]), " ".join(sums)), flush=True)
    return out


def main():
    print("# %s q2_time.py: binary64 kernels (gravq at binary128), %d reps of ~%.2f s; host i5-12400F, 12 threads"
          % (time.strftime("%Y-%m-%d %H:%M:%S %z"), REPS, TARGET_S), flush=True)
    results = []
    failures = []
    jobs = [("grav", 8, "grav N=8"), ("grav", 20, "grav N=20"), ("grav", 36, "grav N=36"),
            ("grav", 70, "grav N=70"), ("cheb", 0, "cheb Sun+Moon"), ("frame_full", 0, "frame full series"),
            ("frame_interp", 3600, "frame interp 3600 s"), ("srp", 0, "srp LEO orbit points"),
            ("srp", 1, "srp penumbra band"), ("gravq", 8, "gravq N=8 binary128"),
            ("gravq", 20, "gravq N=20 binary128"), ("gravq", 36, "gravq N=36 binary128"),
            ("gravq", 70, "gravq N=70 binary128")]
    for k, p, lab in jobs:
        r = measure(k, p, lab)
        results.append(r)
        if not r["ratio"] >= 10.0:
            failures.append(lab)
    # the atmosphere: K objects a call until the control passes
    for K in (1, 4, 16, 64):
        r = measure("atmos", K, "atmos K=%d" % K, per=K)
        results.append(r)
        if r["ratio"] >= 10.0:
            print("# atmosphere: the control passes at K = %d objects a call" % K, flush=True)
            break
        print("# atmosphere: K = %d fails the 10x control (ratio %.1f); raising K" % (K, r["ratio"]), flush=True)
    else:
        failures.append("atmos at every K")
    for r in results:
        if len(r["checksums"]) != 1:
            failures.append("%s: checksum differs between repetitions" % r["label"])
    if failures:
        print("CONTROL FAILED: %s" % "; ".join(failures))
        return 1
    print("ALL CONTROLS PASSED (every force/no-force ratio >= 10; checksums identical across repetitions)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
