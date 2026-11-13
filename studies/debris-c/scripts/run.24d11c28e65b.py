#!/usr/bin/env python3
"""DEBRIS-C runner: runs one measurement command and writes a numbered log
that names the SHA-256 of the script that produced it.

  python -I -B run.py --label NAME --script FILE [--script FILE2] [--timing]
                      [--cwd DIR] -- command ...

What it does, and nothing else:
- hashes every --script file (SHA-256) and copies each into
  studies/debris-c/scripts/<stem>.<first 12 hex of its hash><ext> unless that
  exact version is already there, so every version that wrote a log is kept;
- with --timing, first runs the TimeSheet's read-only check
  (timesheet.py check desktop --short) and refuses to start unless it prints
  FREE; its output goes into the log;
- runs the command (never detached), samples the host's load once a second
  with GetSystemTimes (all logical CPUs), and after the child exits reads the
  child's own CPU time with GetProcessTimes;
- writes studies/debris-c/logs/<label>.NNN.log, with NNN one more than the
  highest existing number, so no log is ever overwritten.
The child's stdout and stderr are kept verbatim in the log, stdout first.
"""
import argparse
import ctypes
import ctypes.wintypes as W
import hashlib
import os
import shutil
import subprocess
import sys
import threading
import time

HERE = os.path.dirname(os.path.abspath(__file__))
LOGS = os.path.join(HERE, "logs")
SCRIPTS = os.path.join(HERE, "scripts")
PY = r"C:\Users\logan\AppData\Local\Programs\Miniconda3\python.exe"
TIMESHEET = r"C:\Users\logan\source\repos\TimeSheet\timesheet.py"
JAVA = "C:/Program Files/Java/jre-1.8/bin/java.exe"
_D = "C:/Users/logan/source/repos/cft-debris-downloads/"
CP = ";".join(_D + j + "/" + j for j in [
    "orekit-13.1.9.jar", "hipparchus-core-4.0.3.jar", "hipparchus-geometry-4.0.3.jar",
    "hipparchus-ode-4.0.3.jar", "hipparchus-fitting-4.0.3.jar", "hipparchus-optim-4.0.3.jar",
    "hipparchus-filtering-4.0.3.jar", "hipparchus-stat-4.0.3.jar"])

K32 = ctypes.WinDLL("kernel32", use_last_error=True)


class FILETIME(ctypes.Structure):
    _fields_ = [("lo", W.DWORD), ("hi", W.DWORD)]


def ft(t):
    return ((t.hi << 32) | t.lo) * 1e-7


def proc_cpu(handle):
    c, e, k, u = FILETIME(), FILETIME(), FILETIME(), FILETIME()
    ok = K32.GetProcessTimes(W.HANDLE(int(handle)), ctypes.byref(c), ctypes.byref(e),
                             ctypes.byref(k), ctypes.byref(u))
    if not ok:
        raise OSError(ctypes.get_last_error(), "GetProcessTimes failed")
    return ft(u), ft(k)


def proc_cycles(handle):
    """QueryProcessCycleTime: CPU cycles charged to all of the process's threads (version 2 of the
    runner, added after m2_cpu_check.001.log: GetProcessTimes is tick-sampled)"""
    c = ctypes.c_ulonglong(0)
    ok = K32.QueryProcessCycleTime(W.HANDLE(int(handle)), ctypes.byref(c))
    if not ok:
        raise OSError(ctypes.get_last_error(), "QueryProcessCycleTime failed")
    return c.value


def sys_times():
    i, k, u = FILETIME(), FILETIME(), FILETIME()
    if not K32.GetSystemTimes(ctypes.byref(i), ctypes.byref(k), ctypes.byref(u)):
        raise OSError(ctypes.get_last_error(), "GetSystemTimes failed")
    idle = ft(i)
    total = ft(k) + ft(u)  # kernel time includes idle time
    return idle, total


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        h.update(f.read())
    return h.hexdigest()


def keep_version(path):
    h = sha256(path)
    stem, ext = os.path.splitext(os.path.basename(path))
    os.makedirs(SCRIPTS, exist_ok=True)
    dst = os.path.join(SCRIPTS, "%s.%s%s" % (stem, h[:12], ext))
    if os.path.exists(dst):
        assert sha256(dst) == h, ("kept version differs from its name", dst)
    else:
        shutil.copyfile(path, dst)
        assert sha256(dst) == h
    return h, dst


def next_log(label):
    os.makedirs(LOGS, exist_ok=True)
    n = 0
    for f in os.listdir(LOGS):
        if f.startswith(label + ".") and f.endswith(".log"):
            mid = f[len(label) + 1:-4]
            if mid.isdigit():
                n = max(n, int(mid))
    path = os.path.join(LOGS, "%s.%03d.log" % (label, n + 1))
    assert not os.path.exists(path)
    return path


class LoadSampler(threading.Thread):
    def __init__(self):
        super().__init__(daemon=True)
        self.samples = []
        self.stop = threading.Event()

    def run(self):
        i0, t0 = sys_times()
        while not self.stop.wait(1.0):
            i1, t1 = sys_times()
            if t1 > t0:
                self.samples.append(100.0 * (1.0 - (i1 - i0) / (t1 - t0)))
            i0, t0 = i1, t1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--label", required=True)
    ap.add_argument("--script", action="append", default=[])
    ap.add_argument("--timing", action="store_true")
    ap.add_argument("--cwd", default=None)
    ap.add_argument("--timeout", type=float, default=590.0)
    ap.add_argument("cmd", nargs=argparse.REMAINDER)
    a = ap.parse_args()
    cmd = a.cmd[1:] if a.cmd and a.cmd[0] == "--" else a.cmd
    assert cmd, "no command"
    if cmd[0] == "JJS":
        # JJS [JVM options] script.js [script args]: Nashorn run through java itself, with the
        # eight approved jars on the classpath (the Rules' Java line)
        rest = cmd[1:]
        opts = []
        while rest and rest[0].startswith("-"):
            opts.append(rest.pop(0))
        cmd = [JAVA] + opts + ["-cp", CP, "jdk.nashorn.tools.Shell"] + rest
    head = []
    head.append("# DEBRIS-C log: %s" % a.label)
    rh, rkept = keep_version(os.path.abspath(__file__))
    head.append("# runner: %s sha256 %s (kept as %s)" % (os.path.abspath(__file__), rh, os.path.relpath(rkept, HERE)))
    for s in a.script:
        h, kept = keep_version(s)
        head.append("# script: %s sha256 %s (kept as %s)" % (os.path.abspath(s), h, os.path.relpath(kept, HERE)))
    head.append("# command: %s" % " ".join(cmd))
    head.append("# cwd: %s" % (a.cwd or os.getcwd()))
    if a.timing:
        ts = subprocess.run([PY, "-I", "-B", TIMESHEET, "check", "desktop", "--short"],
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        head.append("# timesheet check desktop --short (rc %d):" % ts.returncode)
        for ln in ts.stdout.splitlines():
            head.append("#   " + ln)
        if not ts.stdout.startswith("FREE"):
            print("\n".join(head))
            raise SystemExit("REFUSED: the TimeSheet check did not print FREE")
    log = next_log(a.label)
    head.append("# start: %s" % time.strftime("%Y-%m-%d %H:%M:%S %z"))
    sampler = LoadSampler()
    i0, t0 = sys_times()
    sampler.start()
    w0 = time.perf_counter()
    with subprocess.Popen(cmd, cwd=a.cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE) as p:
        try:
            out, err = p.communicate(timeout=a.timeout)
        except subprocess.TimeoutExpired:
            p.kill()  # only this child, by its own handle
            out, err = p.communicate()
            err = (err or b"") + b"\n# RUNNER: killed at timeout\n"
        cu, cs = proc_cpu(p._handle)
        cyc = proc_cycles(p._handle)
        rc = p.returncode
    wall = time.perf_counter() - w0
    sampler.stop.set()
    sampler.join()
    i1, t1 = sys_times()
    mean_load = 100.0 * (1.0 - (i1 - i0) / (t1 - t0)) if t1 > t0 else float("nan")
    s = sampler.samples
    tail = []
    tail.append("# end: %s" % time.strftime("%Y-%m-%d %H:%M:%S %z"))
    tail.append("# exit code: %d" % rc)
    tail.append("# wall: %.3f s; child CPU (GetProcessTimes): user %.3f s + kernel %.3f s = %.3f s"
                % (wall, cu, cs, cu + cs))
    tail.append("# child CPU cycles (QueryProcessCycleTime): %d = %.3f s at a 2.5 GHz reference clock (BELIEVED rate)"
                % (cyc, cyc / 2.5e9))
    tail.append("# host load (GetSystemTimes, all logical CPUs, includes this child): mean %.1f%%; "
                "1 s samples n=%d min %s max %s" % (mean_load, len(s),
                                                     ("%.0f%%" % min(s)) if s else "-",
                                                     ("%.0f%%" % max(s)) if s else "-"))
    with open(log, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(head) + "\n")
        f.write("# ---- stdout ----\n")
        f.write(out.decode("utf-8", "replace"))
        f.write("# ---- stderr ----\n")
        f.write(err.decode("utf-8", "replace"))
        f.write("\n".join(tail) + "\n")
    print("\n".join(head))
    print(out.decode("utf-8", "replace")[-6000:])
    e = err.decode("utf-8", "replace")
    if e.strip():
        print("# stderr (tail):\n" + e[-3000:])
    print("\n".join(tail))
    print("# log: %s" % log)
    return rc


if __name__ == "__main__":
    sys.exit(main())
