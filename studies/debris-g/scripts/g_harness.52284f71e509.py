# g_harness.py - cft-debris M1 (DEBRIS-G): the harness of the throughput round. Standard library only.
# cft-debris, MIT licence (see LICENSE at the repository root). Written by DEBRIS-G, 2026-11-17, from the lead's
# tests/f9_box.py (cft-debris's own, MIT): its Log, its build criteria B1 to B5, its source-hash list and its load read.
#
#   python3 -I -B in/g_harness.py <mode> <root> [options]
#   modes: build | smoke | g2 | g3 | g3cmp | calib | controls | sweep | paced
#
# <root>/in holds src/, m1g.c, g_calib.c, g_harness.py, cft-fp256-0aa997a3.tar, frame_main.bin, population.001.txt,
# dl/ (the downloads' layout) and EXPECTED.sha256 (tests/g_stage.py makes it). The script works from <root> with relative
# paths, so no home path reaches a log. It writes cft-fp256/, build/, logs/ and out/ beside in/, never overwrites a log,
# and deletes nothing. Per-object outputs go to out/ (they hold states: they go to the ledger, never to the repository);
# a log carries hashes, counts and aggregates, and names an object only by its index in the population file.
# On the desktop (Windows) the Linux-only parts are skipped, and each log line that skips one says so.
import hashlib
import json
import math
import os
import platform
import re
import shutil
import subprocess
import sys
import tarfile
import threading
import time

SCRIPT = os.path.abspath(__file__)  # before main() changes directory
WIN = sys.platform == "win32"
EXT = ".exe" if WIN else ""
GCC = "C:/msys64/mingw64/bin/gcc.exe" if WIN else "gcc"
MAKE = "C:/msys64/usr/bin/make.exe" if WIN else "make"
OBJDUMP = "C:/msys64/mingw64/bin/objdump.exe" if WIN else "objdump"
NM = "C:/msys64/mingw64/bin/nm.exe" if WIN else "nm"
MACHINE = "x86_64-w64-mingw32" if WIN else "x86_64-linux-gnu"

CRITERIA = """
Every criterion is fixed here, before any data, and asserted in code. The NaN rule holds throughout: non-NaN results
agree bit for bit, and NaN results agree as NaNs.
BUILD (mode build):
 B1 every file in in/EXPECTED.sha256 has its listed SHA-256 (the 18 files of src/ as commit 1646c96 holds them, the
    sources of this round, this script, the libcft archive and the inputs), each hash printed;
 B2 gcc -dumpmachine prints the platform's triple (x86_64-linux-gnu on the box, x86_64-w64-mingw32 on the desktop);
 B3 libcft.a builds from in/cft-fp256-0aa997a3.tar, one job;
 B4 M1 and the round's programs build at build_f.sh's O2 flags (-std=c11 -O2 -ffp-contract=off -Wall -Wextra; -mfma for
    the native kinds), every compile and link succeeding;
 B5 every native object holds at least one vfmadd and no undefined fma, fmaf, sqrt or sqrtf;
 B6 the clock loop's disassembly is kept in the log and holds at least 8 dependent adds and a store;
 C1 (control) a copy of one source with one byte changed must FAIL the source check of B1.
LINUX PRE-CHECK (before anything is pinned): this process's affinity is CPUs 0 to 35; for every c from 0 to 17,
 cpu c's thread_siblings_list is {c, c+18} and cpu c+18's is the same set.
G1 smoke: every kind-mode, 4 lanes, 2 steps, one worker: exit 0, end checks pass, 4 states of the right size.
G1 calibration (box): the loop's implied clock (additions / wall) beside the kernel's scaling_cur_freq reading, at 1 and
 at 36 busy workers; if they differ by more than 5% the clock is given as the kernel's reading only.
G1 controls, each of which must FAIL as specified (the harness asserts it), exempt from G4's repeat rule:
 C1 above; C2 (box) W=9, a busy loop pinned to CPU 35 for the whole run: void on foreign load; C3 (box) W=2, both
 workers on CPU 0: void on the CPU share; C4 the planted early clock: void on the start time; C5 a paced run of
 native64-cr, 1 worker, 64 lanes at 1,000 times real time: the lag criterion fails, within 120 s.
G2 (box): the first 64 objects, 40 steps, at every kind-mode, under Q1 (1 worker, 1 batch of 64), Q2 (8 workers of 8,
 object i in worker i mod 8), Q3 (36 workers, round-robin, 1 or 2 lanes), Q4 (1 worker, 64 batches of 1), Q5 (1 worker, 64
 lanes in reverse order). PASS: every object's final state equals Q1's, bit for bit, in Q2 to Q5. CONTROL: Q1 with object
 23's initial x moved by one ulp of the kind's input format: exactly object 23's final state differs, no other.
G3: the first 16 objects, 240 steps, every kind-mode, one worker, one batch of 16. The inputs' SHA-256 first (the
 population, the frame table, the gfc, DE421 and its header, and each driver's hash of the values it parsed) must be
 equal on the two machines. PASS: cft32, cft64, cft128, cft256, native32-cr and native64-cr equal bit for bit across the
 two machines; on each machine native64-cr equals cft64 and native32-cr equals cft32 bit for bit. NO pass condition for
 native32 and native64 with the C library: the count of objects that differ, and the largest position difference.
 CONTROL: the comparison on a copy of one machine's output with one bit flipped in one object's state flags exactly that
 object.
G4 (sweep): the validity criteria below; the configurations, S and the statistics are in this script (see CFG, FIG).
 A run is valid only if: V1 every worker exits 0 and its end checks pass; V2 every worker read its release byte within 50
 ms of the harness's release and no worker's timed region began before the release (start time); V3 each worker used under
 10 ms of CPU between READY and its release, and CPU for at least 95% of its timed wall time (cpu share); V4 each ran on
 its own CPU: affinity that CPU alone, on it at its start and at its end (pinning); V5 the foreign load is at most 2%
 (foreign load); V6 the wall time is at least 20 s. A run failing V5 alone is repeated once; failing again, it is void.
 Worker 0's slice's final-state SHA-256 is equal across all L=64 runs of a kind-mode (check D).
G5 (paced): decision 4's rule, asserted from G4's capacities; the population's base objects; 36 workers; real time; 20
 minutes. PASS: every worker's lag at most 15 s at every step; every worker exits 0; end checks pass; V2, V4, V5 and V6
 hold (V3's 95% share does not apply: a paced worker sleeps when ahead).
"""

KINDMODES = ["native32", "native32-cr", "native64", "native64-cr", "cft32", "cft64", "cft128", "cft256"]
F9KM = ["native32", "native64", "native64-cr", "cft32", "cft64", "cft128", "cft256"]
# F9's 64-lane object-day figures (s), the lead's box run f9_box.001.log (MEASURED there): they size G4's runs only
F9_POD = {"native32": 0.066, "native64": 0.067, "native64-cr": 21.406, "cft32": 54.363, "cft64": 71.893,
          "cft128": 120.139, "cft256": 266.713}
POP = "in/population.001.txt"
TABLE = "in/frame_main.bin"
DLDIR = "in/dl/"
EXE = "build/m1g" + EXT
CALIB = "build/g_calib" + EXT
O2 = ["-std=c11", "-O2", "-ffp-contract=off", "-Wall", "-Wextra"]
NATIVE = ["native32", "native64"]
CFT = ["cft32", "cft64", "cft128", "cft256"]
COMMON = ["m1_common", "gfc", "de421", "m1_ftab", "m1_nodes"]
CI = "cft-fp256/host/include"
LIB = "cft-fp256/host/libcft.a"
LAG_LIMIT_NS = 15_000_000_000
G2_BUMP = 23


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def tool_env():
    env = dict(os.environ)
    if WIN:
        env["PATH"] = "C:/msys64/mingw64/bin;C:/msys64/usr/bin;" + env.get("PATH", "")
    env["M1_DOWNLOADS"] = DLDIR
    return env


def first_line(args):
    p = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=tool_env())
    lines = p.stdout.decode("utf-8", "replace").splitlines()
    return lines[0].strip() if lines else "(nothing)"


def read1(path):
    try:
        with open(path, encoding="ascii") as f:
            return f.read().strip()
    except OSError:
        return "(absent)"


def now_ns():
    return time.monotonic_ns() if not WIN else time.perf_counter_ns()


def stat_busy():
    """(busy jiffies, time ns) from /proc/stat's first line: user nice system irq softirq steal (idle and iowait excluded;
    guest is inside user already)"""
    with open("/proc/stat", encoding="ascii") as f:
        v = [int(x) for x in f.readline().split()[1:9]]
    return v[0] + v[1] + v[2] + v[5] + v[6] + v[7], now_ns()


class Log:
    """a numbered log that never overwrites, headed by this script's hash, the host and the criteria"""

    def __init__(self, name):
        os.makedirs("logs", exist_ok=True)
        n = 1
        while os.path.exists("logs/%s.%03d.log" % (name, n)):
            n += 1
        self.n, self.name = n, name
        self.path = "logs/%s.%03d.log" % (name, n)
        self.f = open(self.path, "x", encoding="utf-8", newline="\n")
        self.fails = []
        u = platform.uname()
        self.w("# %s, log %03d, written %s" % (name, n, time.strftime("%Y-%m-%d %H:%M:%S %z")))
        self.w("# script g_harness.py sha256 %s" % sha256(SCRIPT))
        if os.path.exists(EXE):
            self.w("# driver m1g sha256 %s" % sha256(EXE))
        self.w("# host %s, %s %s %s" % (u.node, u.system, u.release, u.machine))
        self.w("# cpu %s; governor %s, driver %s, max %s kHz; python %s" % (
            cpu_model(), read1("/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor"),
            read1("/sys/devices/system/cpu/cpu0/cpufreq/scaling_driver"),
            read1("/sys/devices/system/cpu/cpu0/cpufreq/cpuinfo_max_freq"), platform.python_version()))
        if not WIN:
            self.w("# /proc/loadavg at start: %s" % read1("/proc/loadavg"))
        else:
            self.w("# desktop: the Linux-only parts (affinity, pinning, /proc, frequency, foreign load) are skipped in this log")
        self.w("# CRITERIA (stated in the script before its data; asserted below):")
        for line in CRITERIA.strip("\n").split("\n"):
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


def cpu_model():
    model = platform.processor() or "?"
    try:
        with open("/proc/cpuinfo", encoding="ascii", errors="replace") as f:
            for ln in f:
                if ln.startswith("model name"):
                    return ln.split(":", 1)[1].strip() + ", %d logical" % os.cpu_count()
    except OSError:
        pass
    return model + ", %d logical" % os.cpu_count()


def run(args, log, show_err=True, quiet_ok=False):
    args = [str(a) for a in args]
    t0 = time.perf_counter()
    p = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=tool_env())
    dt = time.perf_counter() - t0
    log.w("# ran (%.2f s wall, exit %d): %s" % (dt, p.returncode, " ".join(args)))
    if show_err:
        for ln in p.stderr.decode("utf-8", "replace").splitlines()[-40:]:
            log.w("#   stderr: " + ln)
    if p.returncode != 0:
        for ln in p.stdout.decode("utf-8", "replace").splitlines()[-40:]:
            log.w("#   stdout: " + ln)
        log.check(False, "the command above failed")
        sys.exit(log.close())
    return p, dt


# ------------------------------------------------------------------ the source check (B1, C1)
def check_sources(base, log=None, show=True):
    """every line of in/EXPECTED.sha256 against the files under base (default in/). Returns (n, bad)."""
    n = bad = 0
    with open("in/EXPECTED.sha256", encoding="ascii") as f:
        for ln in f:
            ln = ln.rstrip("\n")
            if not ln:
                continue
            h, rel = ln[:64], ln[66:]
            p = os.path.join(base, rel)
            got = sha256(p) if os.path.exists(p) else "(absent)"
            n += 1
            if got != h:
                bad += 1
                if log and show:
                    log.w("# MISMATCH %s: listed %s, found %s" % (rel, h, got))
            elif log and show:
                log.w("# %s sha256 %s" % (rel, got))
    return n, bad


def build():
    log = Log("g_build")
    n, bad = check_sources("in", log)
    if not log.check(n > 0 and bad == 0, "B1 %d files as listed, %d mismatched" % (n, bad)):
        return log.close()
    # C1: a copy with one byte changed must fail the check
    os.makedirs("build/c1", exist_ok=True)
    c1 = "build/c1/in"
    if os.path.exists(c1):
        log.check(False, "C1 refused: build/c1/in exists already (each build starts from clean, in a new root)")
        return log.close()
    shutil.copytree("in/src", c1 + "/src")
    shutil.copyfile("in/m1g.c", c1 + "/m1g.c")
    with open(c1 + "/src/m1_common.c", "r+b") as f:
        b = bytearray(f.read())
        b[10] ^= 1
        f.seek(0)
        f.write(bytes(b))
    # the check over the copy: lines whose files are absent from the copy count as mismatches, so look at the changed file alone
    exp = {}
    with open("in/EXPECTED.sha256", encoding="ascii") as f:
        for ln in f:
            ln = ln.rstrip("\n")
            if ln:
                exp[ln[66:]] = ln[:64]
    copy_ok = sha256(c1 + "/src/m1_common.c") == exp["src/m1_common.c"]
    other_ok = sha256(c1 + "/src/m1.h") == exp["src/m1.h"]
    log.check(other_ok and not copy_ok, "C1 control: the copy's changed source fails the source check (%s), its untouched one passes (%s) - failed as specified" % (
        "mismatch" if not copy_ok else "MATCH", "match" if other_ok else "MISMATCH"))
    m = first_line([GCC, "-dumpmachine"])
    if not log.check(m == MACHINE, "B2 gcc -dumpmachine prints %s" % m):
        return log.close()
    log.w("# " + first_line([GCC, "--version"]))
    if os.path.exists("cft-fp256") or os.path.exists("build/obj"):
        log.check(False, "B3 refused: cft-fp256/ or build/obj exists already (each build starts from clean, in a new root)")
        return log.close()
    with tarfile.open("in/cft-fp256-0aa997a3.tar") as t:
        try:
            t.extractall("cft-fp256", filter="data")
        except TypeError:
            t.extractall("cft-fp256")
    margs = ["--no-print-directory", "-C", "cft-fp256/host", "CC=gcc"] + (["OS=Windows_NT", "TMP=/tmp", "TEMP=/tmp"] if WIN else []) + ["libcft.a"]
    p, dt = run([MAKE] + margs, log, show_err=False)
    log.check(os.path.exists(LIB), "B3 libcft.a built (%.1f s wall), sha256 %s" % (dt, sha256(LIB) if os.path.exists(LIB) else "-"))
    os.makedirs("build/obj", exist_ok=True)
    for k in NATIVE:
        run([GCC] + O2 + ["-mfma", "-I" + CI, "-c", "in/src/kind_%s.c" % k, "-o", "build/obj/kind_%s.o" % k], log)
    for k in CFT:
        run([GCC] + O2 + ["-I" + CI, "-c", "in/src/kind_%s.c" % k, "-o", "build/obj/kind_%s.o" % k], log)
    for s in COMMON:
        run([GCC] + O2 + ["-I" + CI, "-c", "in/src/%s.c" % s, "-o", "build/obj/%s.o" % s], log)
    run([GCC] + O2 + ["-I" + CI, "-Iin/src", "-c", "in/m1g.c", "-o", "build/obj/m1g.o"], log)
    kinds = sorted("build/obj/kind_%s.o" % k for k in NATIVE + CFT)
    run([GCC, "-o", EXE, "build/obj/m1g.o"] + kinds + ["build/obj/%s.o" % s for s in COMMON] + [LIB, "-lm"] + (["-lpsapi"] if WIN else []), log)
    run([GCC, "-std=c11", "-O2", "-Wall", "-Wextra", "-o", CALIB, "in/g_calib.c"], log)
    log.check(True, "B4 every compile and link")
    for k in NATIVE:
        o = "build/obj/kind_%s.o" % k
        dis = subprocess.run([OBJDUMP, "-d", o], stdout=subprocess.PIPE, env=tool_env()).stdout.decode("utf-8", "replace")
        nf = sum(1 for ln in dis.splitlines() if "vfmadd" in ln)
        und = subprocess.run([NM, "-u", o], stdout=subprocess.PIPE, env=tool_env()).stdout.decode("utf-8", "replace").split()
        badu = sorted(set(und) & {"fma", "fmaf", "sqrt", "sqrtf"})
        log.check(nf >= 1 and not badu, "B5 %s: vfmadd instructions %d; undefined fma/fmaf/sqrt/sqrtf: %s" % (k, nf, ", ".join(badu) if badu else "none"))
    dis = subprocess.run([OBJDUMP, "-d", "--no-show-raw-insn", CALIB], stdout=subprocess.PIPE, env=tool_env()).stdout.decode("utf-8", "replace").splitlines()
    start = next((i for i, ln in enumerate(dis) if "<calib_loop>:" in ln), -1)
    body = []
    if start >= 0:
        for ln in dis[start + 1:]:
            if not ln.strip():
                break
            body.append(ln)
    nadd = sum(1 for ln in body if re.search(r"\badd\b", ln))
    nstore = sum(1 for ln in body if re.search(r"\bmov\b", ln) and "rip" in ln)
    log.w("# the clock loop's disassembly (objdump -d of calib_loop):")
    for ln in body:
        log.w("#   " + ln)
    log.check(nadd >= 8 and nstore >= 1, "B6 calib_loop holds %d add instructions and %d stores to memory" % (nadd, nstore))
    for f in (LIB, EXE, CALIB):
        log.w("# %s sha256 %s" % (f, sha256(f)))
    return log.close()


# ------------------------------------------------------------------ Linux pre-check
def linux_precheck(log):
    if WIN:
        log.w("# Linux pre-check skipped on the desktop (no affinity, no /sys topology)")
        return True
    ok = os.sched_getaffinity(0) == set(range(36))
    log.check(ok, "pre-check: this process's affinity is CPUs 0 to 35 (%s)" % sorted(os.sched_getaffinity(0)))
    good = 0
    for c in range(36):
        s = read1("/sys/devices/system/cpu/cpu%d/topology/thread_siblings_list" % c)
        sib = set()
        for part in s.split(","):
            if "-" in part:
                a, b = part.split("-")
                sib |= set(range(int(a), int(b) + 1))
            elif part.isdigit():
                sib.add(int(part))
        if sib == {c % 18, c % 18 + 18}:
            good += 1
        else:
            log.w("# cpu %d thread_siblings_list %r" % (c, s))
    ok2 = good == 36
    log.check(ok2, "pre-check: for every c in 0..17, cpu c and cpu c+18 are siblings (%d of 36 CPUs as expected)" % good)
    return ok and ok2


# ------------------------------------------------------------------ workers
class Worker:
    def __init__(self, name, argv, cpu, outdir):
        self.name, self.argv, self.cpu = name, argv, cpu
        self.lines, self.errs = [], []
        self.ev = {"READY": threading.Event(), "TIMED_DONE": threading.Event(), "DONE": threading.Event(), "EOF": threading.Event()}
        self.rep = {}
        argv = [str(a) for a in argv]
        if WIN:
            argv[0] = os.path.abspath(argv[0])  # CreateProcess does not resolve a relative program path
        self.p = subprocess.Popen(argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                  env=tool_env(), bufsize=0)
        if cpu is not None and not WIN:
            os.sched_setaffinity(self.p.pid, {cpu})
        self.t1 = threading.Thread(target=self._rd, daemon=True)
        self.t2 = threading.Thread(target=self._rde, daemon=True)
        self.t1.start()
        self.t2.start()

    def _rd(self):
        for raw in iter(self.p.stdout.readline, b""):
            ln = raw.decode("ascii", "replace").rstrip("\r\n")
            self.lines.append(ln)
            if ln in self.ev:
                self.ev[ln].set()
            if ln.startswith("REPORT "):
                k, _, v = ln[7:].partition(" ")
                self.rep[k] = v
        self.ev["EOF"].set()
        for e in self.ev.values():
            e.set()

    def _rde(self):
        for raw in iter(self.p.stderr.readline, b""):
            self.errs.append(raw.decode("utf-8", "replace").rstrip("\r\n"))

    def alive_ok(self, evname):
        return self.ev[evname].is_set() and (evname == "EOF" or self.lines.count(evname) > 0)

    def send(self, b):
        try:
            self.p.stdin.write(b)
            self.p.stdin.flush()
        except OSError:
            pass


def iv(rep, k, default=None):
    try:
        return int(rep[k])
    except (KeyError, ValueError):
        return default


def run_group(log, tag, specs, pin=True, foreign=True, freq=True, side_busy_cpu=None, timeout=3600):
    """specs: dicts with kind-mode 'km', first, count, stride, reverse, lanes, steps, speed, bump, plant, abort_lag, cpu.
    Starts every worker, waits for every READY, releases them together, waits for every TIMED_DONE, reads /proc/stat,
    sends Q, collects the reports. Returns a result dict (aggregates only, no state)."""
    outd = "out/%s" % tag
    os.makedirs(outd, exist_ok=True)
    workers = []
    for i, s in enumerate(specs):
        argv = [EXE, "run", "--kind", s["km"].replace("-cr", ""), "--table", TABLE, "--pop", POP, "--first", s["first"], "--count", s["count"],
                "--stride", s.get("stride", 1), "--lanes", s["lanes"], "--steps", s["steps"], "--out", outd, "--tag", "w%02d" % i]
        if s["km"].endswith("-cr"):
            argv.append("--cr")
        for flag, key in (("--reverse", "reverse"), ("--plant-early-clock", "plant"), ("--abort-on-lag", "abort_lag")):
            if s.get(key):
                argv.append(flag)
        if s.get("speed"):
            argv += ["--speed", s["speed"]]
        if s.get("bump") is not None:
            argv += ["--bump-x", s["bump"]]
        workers.append(Worker("w%02d" % i, argv, s.get("cpu") if pin else None, outd))
    res = {"tag": tag, "specs": specs, "ok_run": True, "problems": []}
    side = None
    try:
        t_dead = time.time() + timeout
        for w in workers:
            while not w.ev["READY"].wait(0.5):
                if time.time() > t_dead:
                    raise RuntimeError("timeout waiting for READY")
            if "READY" not in w.lines:
                raise RuntimeError("worker %s ended before READY: %s" % (w.name, " | ".join(w.errs[-3:] + w.lines[-3:])))
        loadavg = read1("/proc/loadavg") if not WIN else "NA"
        if side_busy_cpu is not None and not WIN:
            side = subprocess.Popen([sys.executable, "-I", "-B", "-c", "while True: pass"])
            os.sched_setaffinity(side.pid, {side_busy_cpu})
            time.sleep(0.3)
        samples, stop = {}, threading.Event()
        pins = [s.get("cpu") for s in specs if s.get("cpu") is not None] if (freq and not WIN and pin) else []

        def sampler():
            while not stop.is_set():
                for c in pins:
                    v = read1("/sys/devices/system/cpu/cpu%d/cpufreq/scaling_cur_freq" % c)
                    if v.isdigit():
                        samples.setdefault(c, []).append(int(v))
                stop.wait(1.0)

        th = threading.Thread(target=sampler, daemon=True)
        if pins:
            th.start()
        j0, ts0 = stat_busy() if (foreign and not WIN) else (0, 0)
        t_rel = now_ns()
        for w in workers:
            w.send(b"G")
        for w in workers:
            while not w.ev["TIMED_DONE"].wait(0.5):
                if time.time() > t_dead:
                    raise RuntimeError("timeout waiting for TIMED_DONE")
            if "TIMED_DONE" not in w.lines:
                raise RuntimeError("worker %s ended before TIMED_DONE: %s" % (w.name, " | ".join(w.errs[-3:] + w.lines[-3:])))
        j1, ts1 = stat_busy() if (foreign and not WIN) else (0, 0)
        stop.set()
        if pins:
            th.join()
        for w in workers:
            w.send(b"Q")
        for w in workers:
            w.ev["EOF"].wait(600)
            w.p.wait(timeout=600)
            w.t1.join()
            w.t2.join()
    finally:
        if side is not None:
            side.kill()  # by PID: this process was started here
            side.wait()
        for w in workers:
            if w.p.poll() is None:
                w.p.kill()
    wr = []
    for w in workers:
        r = dict(w.rep)
        r["exit"] = w.p.returncode
        r["name"] = w.name
        r["errs"] = w.errs[-3:]
        if "lag_ns" in r:
            r["lag_ns"] = [int(x) for x in r["lag_ns"].split()]
        wr.append(r)
    res["workers"] = wr
    res["t_release"] = t_rel
    res["loadavg"] = loadavg
    res["foreign_known"] = bool(foreign and not WIN)
    t0s = [iv(r, "t_release_read_ns") for r in wr]
    ends = [iv(r, "t_end_ns") for r in wr]
    ok = all(x is not None for x in t0s + ends)
    res["wall_s"] = (max(ends) - min(t0s)) / 1e9 if ok else None
    res["objsec"] = sum(float(r.get("objsec", 0)) for r in wr)
    res["X"] = res["objsec"] / res["wall_s"] if ok and res["wall_s"] else None
    if foreign and not WIN and ok:
        cpu_workers = sum(iv(r, "cpu_end_ns") - iv(r, "cpu_release_ns") for r in wr) / 1e9
        busy_s = (j1 - j0) / os.sysconf("SC_CLK_TCK")
        wall_stat = (ts1 - ts0) / 1e9
        res["foreign_cpu_s"] = busy_s - cpu_workers
        res["foreign_share"] = max(0.0, busy_s - cpu_workers) / (36.0 * wall_stat)
        res["stat_wall_s"] = wall_stat
        res["busy_cpu_s"] = busy_s
    if pins and samples:
        per = {c: sum(v) / len(v) for c, v in samples.items()}
        res["freq_mean_khz"] = sum(per.values()) / len(per)
        res["freq_nsamples"] = min(len(v) for v in samples.values())
    return res


def validate(res, paced=False, load_cap=0.02, min_wall=20.0):
    """the validity criteria V1 to V6; returns the list of failed criteria names"""
    f = []
    wr = res["workers"]
    if not all(r["exit"] == 0 and r.get("end_checks_ok") == "1" for r in wr):
        f.append("exit_or_end_checks")
    rel0 = res["t_release"]
    for r in wr:
        a, s = iv(r, "t_release_read_ns"), iv(r, "t_start_ns")
        if a is None or s is None or not (0 <= a - rel0 <= 50_000_000):
            f.append("release_within_50ms")
            break
    for r in wr:
        s = iv(r, "t_start_ns")
        if s is None or s < rel0:
            f.append("start_time")
            break
    for r in wr:
        c1 = iv(r, "cpu_release_ns", 0) - iv(r, "cpu_ready_ns", 0)
        if c1 >= 10_000_000:
            f.append("cpu_before_release")
            break
    if not paced:
        for r in wr:
            dt = iv(r, "t_end_ns", 0) - iv(r, "t_start_ns", 0)
            cu = iv(r, "cpu_end_ns", 0) - iv(r, "cpu_start_ns", 0)
            if dt <= 0 or cu < 0.95 * dt:
                f.append("cpu_share")
                break
    if not WIN:
        for r, s in zip(wr, res["specs"]):
            c = s.get("cpu")
            if c is None or r.get("affinity_start") != str(c) or r.get("affinity_end") != str(c) or iv(r, "cpu_at_start") != c or iv(r, "cpu_at_end") != c:
                f.append("pinning")
                break
        if res.get("foreign_share") is None or res["foreign_share"] > load_cap:
            f.append("foreign_load")
    if res.get("wall_s") is None or res["wall_s"] < min_wall:
        f.append("wall_time")
    return f


def lag_stats(res):
    out = []
    for r in res["workers"]:
        lg = sorted(r.get("lag_ns") or [])
        if not lg:
            out.append(None)
            continue
        out.append({"median": lg[len(lg) // 2], "p99": lg[min(len(lg) - 1, int(math.ceil(0.99 * len(lg))) - 1)], "max": lg[-1], "n": len(lg)})
    return out


def lag_ok(res):
    return all(r.get("lag_ns") and max(r["lag_ns"]) <= LAG_LIMIT_NS and r.get("aborted_on_lag") != "1" for r in res["workers"])


def describe(log, res, label):
    fr = res.get("foreign_share")
    fq = res.get("freq_mean_khz")
    log.w("RUN %s: wall %.2f s, objsec %.1f, X %.3f obj-s/s, foreign load %s, mean clock %s, loadavg before: %s" % (
        label, res["wall_s"] or -1, res["objsec"], res["X"] or -1, "%.3f%%" % (100 * fr) if fr is not None else "NA (desktop)",
        "%.0f MHz (%d samples a CPU)" % (fq / 1000.0, res["freq_nsamples"]) if fq else "NA", res["loadavg"]))
    mem = [iv(r, "maxrss_kb", -1) for r in res["workers"]]
    log.w("    workers %d, peak resident kB (own report) min %d max %d; final_states_sha256 of worker 0: %s" % (
        len(mem), min(mem), max(mem), res["workers"][0].get("final_states_sha256", "-")))


def km_args(km):
    return km


def spec(km, first, count, lanes, steps, cpu=None, **kw):
    d = {"km": km, "first": first, "count": count, "lanes": lanes, "steps": steps, "cpu": cpu}
    d.update(kw)
    return d


def parse_obj(path):
    """{index: (kind hex x6, binary64 bits x6)}"""
    out = {}
    with open(path, encoding="ascii") as f:
        for ln in f:
            if ln.startswith("#") or not ln.strip():
                continue
            p = ln.split()
            out[int(p[0])] = (tuple(p[1:7]), tuple(p[7:13]))
    return out


def is_nan_bits(h):
    u = int(h, 16)
    return (u >> 52) & 0x7FF == 0x7FF and (u & ((1 << 52) - 1)) != 0


def agree(a, b):
    """the NaN rule: equal bytes, or each differing component NaN in both"""
    if a[0] == b[0]:
        return True
    for i in range(6):
        if a[0][i] != b[0][i] and not (is_nan_bits(a[1][i]) and is_nan_bits(b[1][i])):
            return False
    return True


def collect(tag, nw):
    d = {}
    for i in range(nw):
        d.update(parse_obj("out/%s/w%02d.obj.txt" % (tag, i)))
    return d


def sweep_S(km, L):
    pod = F9_POD[km]
    return max(2, math.ceil(30.0 / (L * pod / 5760.0)))


# ------------------------------------------------------------------ modes
def need_build(log):
    for f in (EXE, CALIB):
        if not os.path.exists(f):
            log.check(False, "%s is missing: run the build mode first" % f)
            return False
    n, bad = check_sources("in", None, False)
    return log.check(n > 0 and bad == 0, "the sources still match in/EXPECTED.sha256 (%d files, %d mismatched)" % (n, bad))


def smoke(opts):
    log = Log("g_smoke")
    if not need_build(log):
        return log.close()
    linux_precheck(log)
    for km in KINDMODES:
        tag = "smoke_%03d_%s" % (log.n, km)
        res = run_group(log, tag, [spec(km, 0, 4, 4, 2, cpu=0 if not WIN else None)])
        r = res["workers"][0]
        objs = parse_obj("out/%s/w00.obj.txt" % tag)
        esz = {"native32": 8, "cft32": 8, "native64": 16, "cft64": 16, "cft128": 32, "cft256": 64}[km.replace("-cr", "")]
        good = (r["exit"] == 0 and r.get("end_checks_ok") == "1" and len(objs) == 4 and all(len(h) == esz for o in objs.values() for h in o[0])
                and r.get("steps_done") == "2")
        log.check(good, "smoke %s: 4 lanes, 2 steps, exit %s, end checks %s, %d states of %d hex digits; final_states_sha256 %s; maxrss %s kB" % (
            km, r["exit"], r.get("end_checks_ok"), len(objs), esz, r.get("final_states_sha256"), r.get("maxrss_kb")))
    return log.close()


def g2(opts):
    steps = int(opts.get("--steps", 40))
    kinds = opts.get("--kinds", ",".join(KINDMODES)).split(",")
    log = Log("g_g2")
    if not need_build(log):
        return log.close()
    linux_precheck(log)
    log.w("# G2: the first 64 objects, %d steps, kind-modes %s; the control bumps object %d's x" % (steps, kinds, G2_BUMP))
    for km in kinds:
        specs, names = [], []

        def add(q, **kw):
            names.append((q, len(specs)))
            specs.append(spec(km, **kw))

        add("Q1", first=0, count=64, lanes=64, steps=steps)
        q2 = len(specs)
        for w in range(8):
            specs.append(spec(km, first=w, count=8, stride=8, lanes=8, steps=steps))
        add("Q4", first=0, count=64, lanes=1, steps=steps)
        add("Q5", first=0, count=64, lanes=64, steps=steps, reverse=True)
        q3 = len(specs)
        for w in range(36):
            specs.append(spec(km, first=w, count=2 if w + 36 < 64 else 1, stride=36, lanes=2, steps=steps))
        add("CTL", first=0, count=64, lanes=64, steps=steps, bump=G2_BUMP)
        tag = "g2_%03d_%s" % (log.n, km)
        log.w("# %s: %d workers at once (not a timing), unpinned" % (km, len(specs)))
        res = run_group(log, tag, specs, pin=False, foreign=False, freq=False)
        bad = [r["name"] for r in res["workers"] if r["exit"] != 0 or r.get("end_checks_ok") != "1"]
        log.check(not bad, "G2 %s: every worker exited 0 and passed its end checks (%d workers; failing: %s)" % (km, len(specs), bad))
        D = {}
        for q, i in names:
            D[q] = parse_obj("out/%s/w%02d.obj.txt" % (tag, i))
        D["Q2"] = {}
        for w in range(8):
            D["Q2"].update(parse_obj("out/%s/w%02d.obj.txt" % (tag, q2 + w)))
        D["Q3"] = {}
        for w in range(36):
            D["Q3"].update(parse_obj("out/%s/w%02d.obj.txt" % (tag, q3 + w)))
        ref = D["Q1"]
        log.check(sorted(ref) == list(range(64)) and all(sorted(D[q]) == list(range(64)) for q in ("Q2", "Q3", "Q4", "Q5", "CTL")),
                  "G2 %s: every partition holds objects 0..63 exactly once" % km)
        for q in ("Q2", "Q3", "Q4", "Q5"):
            diff = [i for i in range(64) if not agree(ref[i], D[q][i])]
            log.check(not diff, "G2 %s %s: every object's final state equals Q1's (%d of 64 differ)" % (km, q, len(diff)))
        diff = [i for i in range(64) if not agree(ref[i], D["CTL"][i])]
        log.check(diff == [G2_BUMP], "G2 %s control (x of object %d moved one ulp of the input format): the objects that differ are %s; expected exactly [%d]" % (
            km, G2_BUMP, diff, G2_BUMP))
        log.w("# G2 %s Q1 final_states_sha256 %s" % (km, res["workers"][0].get("final_states_sha256")))
    return log.close()


def input_hashes():
    return {"population": sha256(POP), "frame_table": sha256(TABLE), "gfc": sha256(DLDIR + "EIGEN6-C4.gfc/EIGEN6-C4.gfc"),
            "de421": sha256(DLDIR + "lnxp1900p2053.421/lnxp1900p2053.421"), "de421_header": sha256(DLDIR + "header.421/header.421")}


BITWISE = ["native32-cr", "native64-cr", "cft32", "cft64", "cft128", "cft256"]
LIBM = ["native32", "native64"]


def g3cmp_core(log, A, B, label):
    """A, B: {km: {idx: state}}; applies G3's cross-machine criteria; returns nothing, logs PASS/FAIL"""
    for km in BITWISE:
        diff = [i for i in sorted(A[km]) if i not in B[km] or not agree(A[km][i], B[km][i])]
        log.check(not diff and sorted(A[km]) == sorted(B[km]), "G3 %s %s: every final state bit for bit equal across the two machines (%d of %d differ)" % (
            label, km, len(diff), len(A[km])))
    for km in LIBM:
        diff, worst = [], 0.0
        for i in sorted(A[km]):
            if not agree(A[km][i], B[km][i]):
                diff.append(i)
                p = [struct_f64(A[km][i][1][j]) - struct_f64(B[km][i][1][j]) for j in range(3)]
                worst = max(worst, math.sqrt(sum(x * x for x in p)))
        log.w("MEASURED G3 %s %s (C library's functions, no pass condition): %d of %d objects differ between the machines; largest position difference after 240 steps %.6g m" % (
            label, km, len(diff), len(A[km]), worst))


def struct_f64(h):
    import struct
    return struct.unpack("<d", struct.pack("<Q", int(h, 16)))[0]


def load_g3(d):
    out = {}
    for km in KINDMODES:
        out[km] = parse_obj(os.path.join(d, km + ".obj.txt"))
    return out


def g3_self_checks(log, A, label):
    for a, b in (("native64-cr", "cft64"), ("native32-cr", "cft32")):
        diff = [i for i in sorted(A[a]) if not agree(A[a][i], A[b][i])]
        log.check(not diff, "G3 %s: %s equals %s bit for bit on this machine (%d of %d differ)" % (label, a, b, len(diff), len(A[a])))


def g3_control(log, A):
    """one bit flipped in one object's state of a copy: the comparison must flag exactly that object"""
    import copy
    B = copy.deepcopy(A)
    km, idx = "cft64", 5
    h = B[km][idx][0][2]
    flipped = h[:-1] + "%x" % (int(h[-1], 16) ^ 1)
    kh = list(B[km][idx][0])
    kh[2] = flipped
    bits = list(B[km][idx][1])
    bits[2] = "%016x" % (int(bits[2], 16) ^ 1)
    B[km][idx] = (tuple(kh), tuple(bits))
    flagged = {(k, i) for k in BITWISE for i in A[k] if not agree(A[k][i], B[k][i])}
    log.check(flagged == {(km, idx)}, "G3 control (one bit flipped in object %d's z of %s in a copy): the comparison flags %s; expected exactly [('%s', %d)]" % (
        idx, km, sorted(flagged), km, idx))


def g3(opts):
    steps = int(opts.get("--steps", 240))
    nobj = int(opts.get("--objects", 16))
    kinds = opts.get("--kinds", ",".join(KINDMODES)).split(",")
    log = Log("g_g3")
    if not need_build(log):
        return log.close()
    ih = input_hashes()
    for k, v in ih.items():
        log.w("# input %s sha256 %s" % (k, v))
    log.w("# G3: first %d objects, %d steps, one worker, one batch; kind-modes %s" % (nobj, steps, kinds))
    specs = [spec(km, 0, nobj, nobj, steps) for km in kinds]
    tag = "g3_%03d" % log.n
    res = run_group(log, tag, specs, pin=False, foreign=False, freq=False)
    outd = "out/%s" % tag
    with open(outd + "/inputs.txt", "x", encoding="ascii", newline="\n") as f:
        for k, v in ih.items():
            f.write("input %s %s\n" % (k, v))
        for km, r in zip(kinds, res["workers"]):
            f.write("driver %s population_values_sha256 %s slice_values_sha256 %s frame_table_sha256 %s final_states_sha256 %s\n" % (
                km, r.get("population_values_sha256"), r.get("slice_values_sha256"), r.get("frame_table_sha256"), r.get("final_states_sha256")))
    for km, r in zip(kinds, res["workers"]):
        log.check(r["exit"] == 0 and r.get("end_checks_ok") == "1", "G3 %s: exit %s, end checks %s, final_states_sha256 %s, population_values_sha256 %s" % (
            km, r["exit"], r.get("end_checks_ok"), r.get("final_states_sha256"), r.get("population_values_sha256")))
    for i, km in enumerate(kinds):
        os.replace("%s/w%02d.obj.txt" % (outd, i), "%s/%s.obj.txt" % (outd, km))
    if set(kinds) == set(KINDMODES):
        A = load_g3(outd)
        g3_self_checks(log, A, "this machine")
        g3_control(log, A)
        if "--against" in opts:
            g3cmp_run(log, outd, opts["--against"])
    else:
        log.w("# fewer than all eight kind-modes: the self-checks and the control are skipped")
    return log.close()


def g3cmp_run(log, d1, d2):
    def rd(d):
        o = {}
        with open(os.path.join(d, "inputs.txt"), encoding="ascii") as f:
            for ln in f:
                p = ln.split()
                if p[0] == "input":
                    o[p[1]] = p[2]
                else:
                    o["driver " + p[1]] = tuple(p[3:9:2]) + (p[7],)
        return o
    a, b = rd(d1), rd(d2)
    for k in a:
        if k.startswith("driver "):
            log.check(a[k][:3] == b[k][:3], "G3 inputs: the driver's parsed-values hashes of %s agree (%s)" % (k[7:], a[k][:3]))
        else:
            log.check(a[k] == b[k], "G3 inputs: %s has the same SHA-256 on both machines (%s)" % (k, a[k]))
    A, B = load_g3(d1), load_g3(d2)
    g3cmp_core(log, A, B, "across the machines")
    g3_self_checks(log, A, "the first machine")
    g3_self_checks(log, B, "the second machine")
    g3_control(log, B)


def g3cmp(opts):
    log = Log("g_g3cmp")
    d1, d2 = opts["args"][0], opts["args"][1]
    log.w("# comparing %s with %s" % (d1, d2))
    g3cmp_run(log, d1, d2)
    return log.close()


def calib(opts):
    log = Log("g_calib")
    if not need_build(log):
        return log.close()
    linux_precheck(log)
    iters = int(opts.get("--iters", 4_000_000_000))
    log.w("# calibration: g_calib %d iterations of 8 dependent additions" % iters)
    big = int(opts.get("--nw", 36))
    if big != 36:
        log.w("# TEST ONLY: --nw %d: the second calibration runs %d workers, not 36 (a functional test, never the box's calibration)" % (big, big))
    for nw in (1, big):
        procs = []
        specs = []
        for w in range(nw):
            specs.append({"cpu": w if not WIN else None, "km": "calib"})
        res = run_calib(log, nw, iters, specs)
        if res is None:
            continue
        implied = []
        for r in res["workers"]:
            dt = (iv(r, "t_end_ns") - iv(r, "t_start_ns")) / 1e9
            implied.append(float(r["additions"]) / dt / 1e9)
        mi = sum(implied) / len(implied)
        fq = res.get("freq_mean_khz")
        log.check(all(r["exit"] == 0 and r.get("accumulator_ok") == "1" for r in res["workers"]), "calib %d workers: every loop finished with the right accumulator" % nw)
        if fq:
            rel = (mi * 1e6 - fq) / fq
            log.w("MEASURED calib %d workers: implied clock (additions per ns, at one addition a cycle, BELIEVED) mean %.4f GHz (min %.4f, max %.4f); kernel scaling_cur_freq mean %.4f GHz; difference %+.2f%%; %s" % (
                nw, mi, min(implied), max(implied), fq / 1e6, 100 * rel,
                "AGREE within 5%: the clock may be given as the loop's" if abs(rel) <= 0.05 else "DIFFER by more than 5%: the report gives the clock as the kernel's reading only"))
        else:
            log.w("MEASURED calib %d workers (desktop, no kernel reading): implied clock mean %.4f GHz (functional test only, never a measurement)" % (nw, mi))
        log.w("# calib %d workers: wall %.2f s" % (nw, res["wall_s"]))
    return log.close()


def run_calib(log, nw, iters, specs):
    """the calibration's workers speak m1g's protocol; run_group builds m1g's argv, so this builds its own"""
    global EXE
    save = EXE
    workers = []
    outs = []
    try:
        for i in range(nw):
            argv = [CALIB, iters]
            workers.append(Worker("w%02d" % i, argv, specs[i]["cpu"], None))
        for w in workers:
            if not w.ev["READY"].wait(300) or "READY" not in w.lines:
                raise RuntimeError("calib worker failed to start: %s" % w.errs[-3:])
        samples, stop = {}, threading.Event()
        pins = [s["cpu"] for s in specs if s["cpu"] is not None] if not WIN else []

        def sampler():
            while not stop.is_set():
                for c in pins:
                    v = read1("/sys/devices/system/cpu/cpu%d/cpufreq/scaling_cur_freq" % c)
                    if v.isdigit():
                        samples.setdefault(c, []).append(int(v))
                stop.wait(0.5)
        th = threading.Thread(target=sampler, daemon=True)
        if pins:
            th.start()
        t_rel = now_ns()
        for w in workers:
            w.send(b"G")
        for w in workers:
            if not w.ev["TIMED_DONE"].wait(3600):
                raise RuntimeError("calib timeout")
        stop.set()
        if pins:
            th.join()
        for w in workers:
            w.send(b"Q")
        for w in workers:
            w.p.wait(timeout=600)
            w.t1.join()
    finally:
        for w in workers:
            if w.p.poll() is None:
                w.p.kill()
    wr = []
    for w in workers:
        r = dict(w.rep)
        r["exit"] = w.p.returncode
        wr.append(r)
    res = {"workers": wr, "wall_s": (max(iv(r, "t_end_ns") for r in wr) - min(iv(r, "t_release_read_ns") for r in wr)) / 1e9}
    if samples:
        per = {c: sum(v) / len(v) for c, v in samples.items()}
        res["freq_mean_khz"] = sum(per.values()) / len(per)
    return res


def busy_run(log, tag, km, W, L, S, cpus, **kw):
    specs = [spec(km, first=w * L, count=L, lanes=L, steps=S, cpu=cpus[w]) for w in range(W)]
    return run_group(log, tag, specs, **kw)


def controls(opts):
    log = Log("g_controls")
    if not need_build(log):
        return log.close()
    linux_precheck(log)
    small = "--small" in opts
    S = int(opts.get("--steps", 2 if small else sweep_S("native64", 64)))
    cpus = list(range(36)) if not WIN else [None] * 36
    # C4: planted early clock (on both)
    specs = [spec("native64", first=w * 64, count=64, lanes=64, steps=S, cpu=cpus[w], plant=(w == 0)) for w in range(2)]
    res = run_group(log, "c4_%03d" % log.n, specs)
    f = validate(res)
    describe(log, res, "C4 planted early clock, W=2 native64 S=%d" % S)
    log.check("start_time" in f, "C4 control: the run with the planted early clock fails V2's start time (failed criteria: %s) - failed as specified" % f)
    # C5: paced, 1000x
    S5 = int(opts.get("--c5-steps", 400))
    t0 = time.time()
    res = run_group(log, "c5_%03d" % log.n, [spec("native64-cr", first=0, count=64, lanes=64, steps=S5, cpu=cpus[0], speed=1000, abort_lag=True)])
    dt = time.time() - t0
    r = res["workers"][0]
    log.check((not lag_ok(res)) and dt < 120, "C5 control: native64-cr, 1 worker, 64 lanes at 1000x real time fails the lag criterion (first step over 15 s: %s, steps done %s of %d, aborted %s) within %.1f s (limit 120) - failed as specified" % (
        r.get("first_step_over_15s"), r.get("steps_done"), S5, r.get("aborted_on_lag"), dt))
    if WIN:
        log.w("# C2 and C3 need /proc and CPU pinning: skipped on the desktop")
        return log.close()
    # C2: W=9, a busy loop on CPU 35
    res = busy_run(log, "c2_%03d" % log.n, "native64", 9, 64, S, cpus, side_busy_cpu=35)
    f = validate(res)
    describe(log, res, "C2 W=9 native64 with a busy loop pinned to CPU 35, S=%d" % S)
    log.check("foreign_load" in f, "C2 control: the run with a busy loop on CPU 35 is void on foreign load (foreign %.2f%% against 2%%; failed criteria: %s) - failed as specified" % (100 * res["foreign_share"], f))
    # C3: W=2 both on CPU 0
    specs = [spec("native64", first=w * 64, count=64, lanes=64, steps=S, cpu=0) for w in range(2)]
    res = run_group(log, "c3_%03d" % log.n, specs)
    f = validate(res)
    describe(log, res, "C3 W=2, both workers pinned to CPU 0, S=%d" % S)
    log.check("cpu_share" in f, "C3 control: both workers on CPU 0 is void on the CPU share (failed criteria: %s) - failed as specified" % f)
    return log.close()


# ------------------------------------------------------------------ G4
CFG_BASE = [(1, 64), (9, 64), (18, 64), (36, 64), (36, 64), (36, 64), (36, 8), (36, 256)]
CFG_CFT64 = [(2, 64), (4, 64), (27, 64)]


def cfgs(km):
    c = list(CFG_BASE)
    if km == "cft64":
        c = [(1, 64), (2, 64), (4, 64), (9, 64), (18, 64), (27, 64)] + c[3:]
    return c


def median(v):
    s = sorted(v)
    n = len(s)
    return s[n // 2] if n % 2 else 0.5 * (s[n // 2 - 1] + s[n // 2])


def sweep(opts):
    log = Log("g_sweep")
    booking = opts["args"][0] if opts.get("args") else "(none given)"
    kinds = opts.get("--kinds", ",".join(F9KM)).split(",")
    stepscale = float(opts.get("--stepscale", 1.0))
    if not need_build(log):
        return log.close()
    if not linux_precheck(log) and not WIN:
        return log.close()
    log.w("# G4 sweep; TimeSheet booking %s (sensitive, box); kind-modes %s" % (booking, kinds))
    log.w("# F9's 64-lane object-day figures (s) used for S: %s; S = max(2, ceil(30 / (L x figure/5760))) x %g" % (F9_POD, stepscale))
    runs = []
    for km in kinds:
        ref_hash = None
        for (W, L) in cfgs(km):
            S = max(2, math.ceil(sweep_S(km, L) * stepscale))
            cpus = list(range(W)) if not WIN else [None] * W
            tries = 0
            while True:
                tries += 1
                label = "%s W=%d L=%d S=%d (try %d)" % (km, W, L, S, tries)
                log.w("# about to run %s: %d workers, objects 0..%d, pinned to CPUs %s; S fixed before the run" % (label, W, W * L - 1, "0.." + str(W - 1) if not WIN else "none"))
                res = busy_run(log, "g4_%03d_%s_W%d_L%d_%d" % (log.n, km, W, L, len(runs)), km, W, L, S, cpus)
                f = validate(res)
                describe(log, res, label)
                log.w("    validity: %s" % ("VALID" if not f else "FAILED " + ",".join(f)))
                res["km"], res["W"], res["L"], res["S"], res["failed"] = km, W, L, S, f
                runs.append(res)
                if f == ["foreign_load"] and tries == 1:
                    log.w("    the run failed on foreign load alone: repeated once")
                    continue
                break
            res["status"] = "valid" if not f else "void"
            if L == 64:
                h = res["workers"][0].get("final_states_sha256")
                if ref_hash is None:
                    ref_hash = h
                log.check(h == ref_hash, "D %s W=%d L=64: worker 0's final-state SHA-256 equals the first run's (%s)" % (km, W, h))
    # figures
    summary = {"booking": booking, "runs": []}
    for r in runs:
        summary["runs"].append({"km": r["km"], "W": r["W"], "L": r["L"], "S": r["S"], "status": r["status"], "failed": r["failed"], "X": r["X"],
                                "wall_s": r["wall_s"], "foreign_share": r.get("foreign_share"), "freq_mean_khz": r.get("freq_mean_khz"),
                                "maxrss_kb": [iv(w, "maxrss_kb") for w in r["workers"]], "objsec": r["objsec"], "tag": r["tag"]})
    log.w("# FIGURES (X = object-seconds summed over the workers / wall time from the first release to the last end; a ratio divides X, a rate)")
    for km in kinds:
        valid = [r for r in runs if r["km"] == km and r["status"] == "valid"]

        def xs(W, L):
            return [r["X"] for r in valid if r["W"] == W and r["L"] == L]
        x1 = xs(1, 64)
        for W in sorted({r["W"] for r in valid if r["L"] == 64}):
            v = xs(W, 64)
            if v and x1:
                log.w("FIG %s W=%d L=64: X %.3f (n=%d valid); parallel efficiency X(W)/(W x X(1)) %.3f" % (km, W, median(v), len(v), median(v) / (W * x1[0])))
        if xs(36, 64) and xs(18, 64):
            log.w("FIG %s hyperthreads: X(36)/X(18) = %.3f (L=64, medians)" % (km, median(xs(36, 64)) / median(xs(18, 64))))
        for L in (8, 64, 256):
            v = xs(36, L)
            if v:
                log.w("FIG %s W=36 L=%d: X %.3f (n=%d valid)" % (km, L, median(v), len(v)))
        v = xs(36, 64)
        cap = median(v) if v else None
        if len(v) >= 2:
            log.w("FIG %s spread of the W=36 L=64 repeats: largest/smallest = %.4f over %d valid runs (one after another; says nothing of a later window)" % (km, max(v) / min(v), len(v)))
        log.w("CAPACITY %s: real-time capacity (W=36, L=64, median of %d valid repeats) = %s objects at real time (a throughput figure; above the %d objects the run carried it is an extrapolation of the run's cost per object)" % (
            km, len(v), "%.1f" % cap if cap else "NONE (no valid run)", 36 * 64))
        summary.setdefault("capacity", {})[km] = cap
        best = max([r["X"] for r in valid] or [0])
        log.w("# %s: the fastest valid configuration X %.3f (reported beside the capacity, never in its place)" % (km, best))
    nvoid = sum(1 for r in runs if r["status"] == "void")
    log.w("# runs: %d, valid %d, void %d" % (len(runs), len(runs) - nvoid, nvoid))
    jp = "logs/g_sweep.%03d.runs.json" % log.n
    with open(jp, "x", encoding="utf-8", newline="\n") as f:
        json.dump(summary, f, indent=1)
    log.w("# per-run aggregates written to %s, sha256 %s" % (jp, sha256(jp)))
    return log.close()


# ------------------------------------------------------------------ G5
def paced(opts):
    log = Log("g_paced")
    booking = opts["args"][0] if opts.get("args") else "(none given)"
    minutes = float(opts.get("--minutes", 20))
    if not need_build(log):
        return log.close()
    if not linux_precheck(log) and not WIN:
        return log.close()
    g4 = {"capacity": {}}
    for gp in opts["--g4"].split(","):  # one or several sweeps' runs.json files (a sweep may be run kind by kind)
        with open(gp, encoding="utf-8") as f:
            g4["capacity"].update(json.load(f)["capacity"])
        log.w("# G4 figures read from %s, sha256 %s" % (gp, sha256(gp)))
    with open(POP, encoding="ascii") as f:
        N = sum(1 for ln in f if ln.split()[1] == "0")
    if "--nbase" in opts:
        N = min(N, int(opts["--nbase"]))
        log.w("# TEST ONLY: --nbase limits N to %d (a functional test, never a G5 result)" % N)
    if minutes < 1:
        log.w("# TEST ONLY: --minutes %g: the wall-time criterion V6 is waived (a functional test, never a G5 result)" % minutes)
    cap = g4["capacity"]
    log.w("# G5 under decision 4: base objects N = %d; G4's capacities (W=36, L=64, median of valid repeats): %s" % (N, {k: cap.get(k) for k in ("cft256", "cft128", "cft64")}))
    km = None
    for k in ("cft256", "cft128", "cft64"):
        if cap.get(k) is not None and cap[k] >= 1.25 * N:
            km = k
            break
        log.w("# %s: capacity %s is under 1.25 x N = %.1f: the fallback rule moves down" % (k, cap.get(k), 1.25 * N))
    if km is None:
        log.check(False, "decision 4's rule finds no kind-mode (every capacity under 1.25 x N): G5 is not run")
        return log.close()
    if "--kind" in opts:
        log.check(opts["--kind"] == km, "the kind-mode given (%s) is the one the rule chooses (%s)" % (opts["--kind"], km))
        if opts["--kind"] != km:
            return log.close()
    nwk = int(opts.get("--workers", 36))
    if nwk != 36:
        log.w("# TEST ONLY: --workers %d, not 36 (a functional test, never a G5 result)" % nwk)
    lanes = -(-N // nwk)
    S = int(round(minutes * 60 / 15))
    cpus = list(range(36)) if not WIN else [None] * 36
    specs = []
    for w in range(nwk):
        first = w * lanes
        cnt = min(lanes, N - first)
        if cnt > 0:
            specs.append(spec(km, first=first, count=cnt, lanes=cnt, steps=S, cpu=cpus[w], speed=1))
    log.w("# G5: %s, %d workers, %d lanes each and %d on the last, real time, %d steps (%.1f minutes); booking %s" % (km, len(specs), lanes, specs[-1]["count"], S, minutes, booking))
    res = run_group(log, "g5_%03d" % log.n, specs, timeout=int(minutes * 60 * 3 + 3600))
    f = validate(res, paced=True, min_wall=20.0 if minutes >= 1 else 0.0)
    describe(log, res, "G5 %s" % km)
    st = lag_stats(res)
    for i, s in enumerate(st):
        if s:
            log.w("    worker %d lag: median %.3f s, p99 %.3f s, max %.3f s over %d steps" % (i, s["median"] / 1e9, s["p99"] / 1e9, s["max"] / 1e9, s["n"]))
    busy = [(iv(r, "cpu_end_ns") - iv(r, "cpu_start_ns")) / ((iv(r, "t_end_ns") - iv(r, "t_start_ns")) or 1) for r in res["workers"]]
    log.w("REPORT G5: busy share of wall time per worker: mean %.3f, min %.3f, max %.3f; mean clock %s; kind-mode %s; N %d" % (
        sum(busy) / len(busy), min(busy), max(busy), "%.0f MHz" % (res["freq_mean_khz"] / 1000.0) if res.get("freq_mean_khz") else "NA", km, N))
    log.check(lag_ok(res), "G5 lag criterion: every worker's lag at most 15 s at every step (worst %.3f s)" % (max(s["max"] for s in st if s) / 1e9))
    log.check(not f, "G5 validity (V1, V2, V4, V5, V6; not V3's share): failed criteria %s" % f)
    return log.close()


def main():
    a = sys.argv[1:]
    if len(a) < 2:
        raise SystemExit("usage: g_harness.py <build|smoke|g2|g3|g3cmp|calib|controls|sweep|paced> <root> [options]")
    mode, root = a[0], a[1]
    opts = {"args": []}
    i = 2
    while i < len(a):
        if a[i].startswith("--"):
            if i + 1 < len(a) and not a[i + 1].startswith("--") and a[i] not in ("--small",):
                opts[a[i]] = a[i + 1]
                i += 2
            else:
                opts[a[i]] = True
                i += 1
        else:
            opts["args"].append(a[i])
            i += 1
    os.chdir(root)
    fn = {"build": lambda o: build(), "smoke": smoke, "g2": g2, "g3": g3, "g3cmp": g3cmp, "calib": calib, "controls": controls, "sweep": sweep, "paced": paced}[mode]
    return fn(opts)


if __name__ == "__main__":
    sys.exit(main())
