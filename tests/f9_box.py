# f9_box.py - cft-debris M1 (DEBRIS-F), F9 on amd-arc-box: the lead's Linux harness for F9's clean re-run.
# cft-debris, MIT licence (see LICENSE at the repository root). Written by the round's lead, 2026-11-16, from
# DEBRIS-F's tests/f9_time.py and tests/build_f.sh (cft-debris's own, MIT).
#
# Why: Logan, 2026-11-16, in chat: "You also have permission to run the tests on the 'amd-arc-box' ...".
# f9_time.py cannot run there unchanged: tests/m1f.c's time mode includes <windows.h> for its two timers, and
# f_lib.py, cpurun.py and gatelib.host_load() are Windows-only. This harness keeps every M1 source byte-identical
# (each SHA-256 is asserted against in/EXPECTED.sha256, which the lead checked against DEBRIS-F's build_f.004.log)
# and gives m1f.c's two timers Linux clocks through tests/f9_box_windows.h.
#
#   python3 -I -B in/f9_box.py build <root>
#   python3 -I -B in/f9_box.py time  <root> <booking id> [min_seconds]
#
# <root>/in holds src/, tests/m1f.c, tests/m1nodes.c, f9_box.py, f9_box_windows.h, cft-fp256-0aa997a3.tar,
# dl/ (the downloads' layout), frame_main.bin, d_fit_in.txt and EXPECTED.sha256. The script works from <root> with
# relative paths, so no home path reaches a log. It writes cft-fp256/, build/, work/ and logs/ beside in/, never
# overwrites a log or an output, and deletes nothing.
import hashlib
import os
import platform
import resource
import shutil
import subprocess
import sys
import tarfile
import time

CRITERIA_BUILD = """
The build, asserted; the script stops at the first failure:
B1 every file listed in in/EXPECTED.sha256 has its listed SHA-256 (the M1 sources as DEBRIS-F's build_f.004.log
   lists them, the shim, this script, the libcft archive and the inputs);
B2 gcc -dumpmachine prints x86_64-linux-gnu;
B3 libcft.a builds from in/cft-fp256-0aa997a3.tar by `make -C cft-fp256/host CC=gcc libcft.a`, one job, as DEBRIS-F
   built it on the desktop (there with OS=Windows_NT and mingw64's gcc 16.1.0);
B4 M1 builds at build_f.sh's O2 flags (-std=c11 -O2 -ffp-contract=off -Wall -Wextra; -mfma for the native kinds);
   m1f.c alone adds -Ibuild/shim (the shim, as windows.h) and -D_POSIX_C_SOURCE=199309L (clock_gettime under -std=c11);
B5 every native object holds at least one vfmadd and no undefined fma, fmaf, sqrt or sqrtf (build_f.sh's criterion 2).
"""

CRITERIA_TIME = """
A MEASUREMENT (no pass condition; the PASS lines say only that a run completed), single runs, as tests/f9_time.py
makes them, with the load stated per row: the busy share of all the box's logical processors over 0.5 s before and
after each run (/proc/stat; one busy thread of 36 is about 2.8%), and each run's CPU (getrusage, user + system).
T1 each kind's time per lane-force-evaluation with the real frame (m1f time), at 1 and 64 lanes, native32, native64
   (the C library's transcendentals and libcft's), cft32, cft64, cft128, cft256; and an object-day's time with rk4 at
   15 s, COMPUTED from the measured time of a step. On the box the columns m1f prints as thread_cycles and
   per_lane_eval_cycles hold the thread's CPU nanoseconds (the shim's CLOCK_THREAD_CPUTIME_ID), not cycles.
T2 the node table's build: m1nodes build of 2 days of data (675 fine nodes and their coarse nodes), wall time and CPU;
   reported per day of data.
T3 a fit's time per object at native64: m1f fit on the first 5 objects of F5(d)'s fit input, wall time per object,
   with the iteration counts.
Unlike f9_time.py, each program starts directly, without the cpurun.py wrapper, so T2's and T3's wall times hold no
Python start.
"""

O2 = ["-std=c11", "-O2", "-ffp-contract=off", "-Wall", "-Wextra"]
NATIVE = ["native32", "native64"]
CFT = ["cft32", "cft64", "cft128", "cft256"]
COMMON = ["m1_common", "gfc", "de421", "m1_ftab", "m1_nodes"]
CI = "cft-fp256/host/include"
LIB = "cft-fp256/host/libcft.a"
EXE = "build/m1f_O2"
NODES = "build/m1nodes"
TABLE = "in/frame_main.bin"
DL = "in/dl/"


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def first_line(args):
    p = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    lines = p.stdout.decode("utf-8", "replace").splitlines()
    return lines[0].strip() if lines else "(nothing)"


def read1(path):
    try:
        with open(path, encoding="ascii") as f:
            return f.read().strip()
    except OSError:
        return "(absent)"


def cpu_model():
    model, n = "?", 0
    with open("/proc/cpuinfo", encoding="ascii", errors="replace") as f:
        for ln in f:
            if ln.startswith("model name") and model == "?":
                model = ln.split(":", 1)[1].strip()
            if ln.startswith("processor"):
                n += 1
    return model, n


def stat():
    """(all jiffies, idle + iowait jiffies) from /proc/stat's first line: user nice system idle iowait irq softirq steal"""
    with open("/proc/stat", encoding="ascii") as f:
        v = [int(x) for x in f.readline().split()[1:9]]
    return sum(v), v[3] + v[4]


def host_load():
    t0, i0 = stat()
    time.sleep(0.5)
    t1, i1 = stat()
    return 100.0 * ((t1 - t0) - (i1 - i0)) / max(1, t1 - t0)


class Log:
    """a numbered log that never overwrites, headed by this script's hash, the host and the criteria"""

    def __init__(self, name, criteria):
        os.makedirs("logs", exist_ok=True)
        n = 1
        while os.path.exists("logs/%s.%03d.log" % (name, n)):
            n += 1
        self.n = n
        self.path = "logs/%s.%03d.log" % (name, n)
        self.f = open(self.path, "x", encoding="utf-8", newline="\n")
        self.fails = []
        u = platform.uname()
        model, nproc = cpu_model()
        self.w("# %s, log %03d, written %s" % (name, n, time.strftime("%Y-%m-%d %H:%M:%S %z")))
        self.w("# script f9_box.py sha256 %s" % sha256(os.path.abspath(__file__)))
        self.w("# host %s, %s %s %s" % (u.node, u.system, u.release, u.machine))
        self.w("# cpu %s, %d logical processors; governor %s, driver %s, max %s kHz, intel_pstate no_turbo %s" % (
            model, nproc, read1("/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor"),
            read1("/sys/devices/system/cpu/cpu0/cpufreq/scaling_driver"),
            read1("/sys/devices/system/cpu/cpu0/cpufreq/cpuinfo_max_freq"),
            read1("/sys/devices/system/cpu/intel_pstate/no_turbo")))
        self.w("# %s; gcc -dumpmachine %s; python %s" % (first_line(["gcc", "--version"]),
                                                      first_line(["gcc", "-dumpmachine"]), platform.python_version()))
        self.w("# host load at start: %.1f%% (/proc/stat, all logical processors, 0.5 s)" % host_load())
        self.w("# CRITERIA (stated in the script before its data; asserted below):")
        for line in criteria.strip("\n").split("\n"):
            self.w("#   " + line)

    def w(self, s=""):
        self.f.write(s + "\n")
        self.f.flush()
        print(s, flush=True)

    def check(self, ok, what):
        self.w(("PASS " if ok else "FAIL ") + what)
        if not ok:
            self.fails.append(what)
        return ok

    def close(self, extra=""):
        self.w("# %s %s" % ("PASS" if not self.fails else "FAIL (%d)" % len(self.fails), extra))
        self.f.close()
        return 0 if not self.fails else 1


def run(args, log, env=None, show_err=True):
    """start a program, bytes in and out; returns (process, wall s, CPU s of it and the children it waited for)"""
    args = [str(a) for a in args]
    r0 = resource.getrusage(resource.RUSAGE_CHILDREN)
    t0 = time.perf_counter()
    p = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
    dt = time.perf_counter() - t0
    r1 = resource.getrusage(resource.RUSAGE_CHILDREN)
    cpu = (r1.ru_utime - r0.ru_utime) + (r1.ru_stime - r0.ru_stime)
    log.w("# ran (%.2f s wall, %.2f s CPU, exit %d): %s" % (dt, cpu, p.returncode, " ".join(args)))
    if show_err:
        for ln in p.stderr.decode("utf-8", "replace").splitlines()[-40:]:
            log.w("#   stderr: " + ln)
    if p.returncode != 0:
        for ln in p.stdout.decode("utf-8", "replace").splitlines()[-40:]:
            log.w("#   stdout: " + ln)
        log.check(False, "the command above failed")
        sys.exit(log.close())
    return p, dt, cpu


def build():
    log = Log("f9_box_build", CRITERIA_BUILD)
    n, bad = 0, 0
    with open("in/EXPECTED.sha256", encoding="ascii") as f:
        for ln in f:
            ln = ln.rstrip("\n")
            if not ln:
                continue
            h, rel = ln[:64], ln[66:]
            got = sha256("in/" + rel)
            n += 1
            if got != h:
                bad += 1
                log.w("# MISMATCH in/%s: listed %s, found %s" % (rel, h, got))
            else:
                log.w("# in/%s sha256 %s" % (rel, got))
    if not log.check(n > 0 and bad == 0, "B1 %d files as listed, %d mismatched" % (n, bad)):
        return log.close()
    m = first_line(["gcc", "-dumpmachine"])
    if not log.check(m == "x86_64-linux-gnu", "B2 gcc -dumpmachine prints %s" % m):
        return log.close()
    if os.path.exists("cft-fp256") or os.path.exists("build"):
        log.check(False, "B3 refused: cft-fp256/ or build/ exists already (each build starts from clean, in a new root)")
        return log.close()
    with tarfile.open("in/cft-fp256-0aa997a3.tar") as t:
        t.extractall("cft-fp256", filter="data")
    p, dt, cpu = run(["make", "--no-print-directory", "-C", "cft-fp256/host", "CC=gcc", "libcft.a"], log, show_err=False)
    for ln in p.stdout.decode("utf-8", "replace").splitlines() + p.stderr.decode("utf-8", "replace").splitlines():
        log.w("#   make: " + ln)
    if not log.check(os.path.exists(LIB), "B3 libcft.a built (%.1f s wall, %.1f s CPU), sha256 %s" % (
            dt, cpu, sha256(LIB) if os.path.exists(LIB) else "-")):
        return log.close()
    os.makedirs("build/obj")
    os.makedirs("build/shim")
    shutil.copyfile("in/f9_box_windows.h", "build/shim/windows.h")
    for k in NATIVE:
        run(["gcc"] + O2 + ["-mfma", "-I" + CI, "-c", "in/src/kind_%s.c" % k, "-o", "build/obj/kind_%s.o" % k], log)
    for k in CFT:
        run(["gcc"] + O2 + ["-I" + CI, "-c", "in/src/kind_%s.c" % k, "-o", "build/obj/kind_%s.o" % k], log)
    for s in COMMON:
        run(["gcc"] + O2 + ["-I" + CI, "-c", "in/src/%s.c" % s, "-o", "build/obj/%s.o" % s], log)
    run(["gcc"] + O2 + ["-I" + CI, "-Iin/src", "-Ibuild/shim", "-D_POSIX_C_SOURCE=199309L", "-c", "in/tests/m1f.c",
                        "-o", "build/obj/m1f.o"], log)
    kinds = sorted("build/obj/kind_%s.o" % k for k in NATIVE + CFT)
    run(["gcc", "-o", EXE, "build/obj/m1f.o"] + kinds + ["build/obj/%s.o" % s for s in COMMON] + [LIB, "-lm"], log)
    run(["gcc"] + O2 + ["-I" + CI, "-Iin/src", "-o", NODES, "in/tests/m1nodes.c", "in/src/m1_nodes.c", LIB, "-lm"], log)
    log.check(True, "B4 every compile and link")
    for k in NATIVE:
        o = "build/obj/kind_%s.o" % k
        dis = subprocess.run(["objdump", "-d", o], stdout=subprocess.PIPE).stdout.decode("utf-8", "replace")
        nf = sum(1 for ln in dis.splitlines() if "vfmadd" in ln)
        und = subprocess.run(["nm", "-u", o], stdout=subprocess.PIPE).stdout.decode("utf-8", "replace").split()
        bad = sorted(set(und) & {"fma", "fmaf", "sqrt", "sqrtf"})
        log.check(nf >= 1 and not bad, "B5 %s: vfmadd instructions %d; undefined fma/fmaf/sqrt/sqrtf: %s" % (
            k, nf, ", ".join(bad) if bad else "none"))
    for f in (LIB, EXE, NODES):
        log.w("# %s sha256 %s" % (f, sha256(f)))
    return log.close()


def timing(booking, mins):
    log = Log("f9_box", CRITERIA_TIME)
    log.w("# TimeSheet booking %s (sensitive, box); min seconds per measurement %s" % (booking, mins))
    log.w("# m1f_O2 sha256 %s; m1nodes sha256 %s; table sha256 %s" % (sha256(EXE), sha256(NODES), sha256(TABLE)))
    env = dict(os.environ)
    env["M1_DOWNLOADS"] = DL
    W = "work/f9_%03d" % log.n
    os.makedirs(W)
    for kind, extra in (("native32", []), ("native64", []), ("native64", ["--cr"]), ("cft32", []), ("cft64", []),
                        ("cft128", []), ("cft256", [])):
        for n in (1, 64):
            tag = "%s%s_%d" % (kind, "_cr" if extra else "", n)
            o = "%s/time_%s.txt" % (W, tag)
            l0 = host_load()
            p, dt, cpu = run([EXE, "time", kind, TABLE, str(n), mins, o] + extra, log, env)
            l1 = host_load()
            with open(o, encoding="utf-8") as f:
                for ln in f:
                    if ln.startswith("accel") or ln.startswith("rk4"):
                        log.w("MEASURED T1 %s%s lanes %d (load %.1f%% / %.1f%%; the process %.2f s CPU in %.2f s): %s" % (
                            kind, " libcft-transc" if extra else "", n, l0, l1, cpu, dt, ln.strip()))
            log.check(True, "T1 %s completed" % tag)
    l0 = host_load()
    p, dt, cpu = run([NODES, "build", "1000000", "256", "675", W + "/table_2days.bin", "--note", "F9 T2"], log, env)
    l1 = host_load()
    log.w("MEASURED T2 a 2-day table (675 fine nodes): %.2f s wall, %.2f s CPU (load %.1f%% / %.1f%%), %.2f s a day of data" % (
        dt, cpu, l0, l1, dt / 2))
    out, nobj = [], 0
    with open("in/d_fit_in.txt", encoding="utf-8") as f:
        for ln in f:
            if ln.startswith("OBJ "):
                nobj += 1
                if nobj > 5:
                    break
            out.append(ln)
    with open(W + "/fit5_in.txt", "x", encoding="utf-8", newline="\n") as f:
        f.writelines(out)
    l0 = host_load()
    p, dt, cpu = run([EXE, "fit", TABLE, W + "/fit5_in.txt", W + "/fit5_out.txt"], log, env)
    l1 = host_load()
    with open(W + "/fit5_out.txt", encoding="utf-8") as f:
        its = [int(ln.split()[3]) for ln in f if ln.startswith("FIT")]
    log.w("MEASURED T3 5 fits at native64: %.2f s wall, %.2f s CPU (load %.1f%% / %.1f%%), %.2f s an object; iterations %s (%.2f s an iteration)" % (
        dt, cpu, l0, l1, dt / 5, its, dt / max(1, sum(its))))
    log.check(len(its) == 5, "T3 five fits reported")
    for fn in sorted(os.listdir(W)):
        log.w("# output %s/%s sha256 %s" % (W, fn, sha256(W + "/" + fn)))
    log.w("# host load at end: %.1f%%" % host_load())
    return log.close()


def main():
    if len(sys.argv) < 3 or sys.argv[1] not in ("build", "time"):
        raise SystemExit("usage: f9_box.py build <root> | time <root> <booking id> [min_seconds]")
    os.chdir(sys.argv[2])
    if sys.argv[1] == "build":
        return build()
    if len(sys.argv) < 4:
        raise SystemExit("usage: f9_box.py time <root> <booking id> [min_seconds]")
    return timing(sys.argv[3], sys.argv[4] if len(sys.argv) > 4 else "2")


if __name__ == "__main__":
    sys.exit(main())
