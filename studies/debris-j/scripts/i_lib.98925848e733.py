"""i_lib.py - cft-debris DEBRIS-I: the harness's shared pieces, standard library only (the box runs them).

cft-debris, MIT licence (see LICENSE at the repository root). Written by DEBRIS-I, 2026-11-23. Its log follows the
logs of DEBRIS-D to DEBRIS-H (studies/debris-d/tools/dd.py and tests/g_harness.py, cft-debris's own, MIT).

A log is studies/debris-i/logs/<name>.<NNN>.log (NNN the next free number: no log is ever overwritten). Its first lines
name the script that wrote it and its SHA-256, the time (with its scale), and the criteria the script asserts, written
before any data. Before the first line, the script's current version is kept as scripts/<stem>.<sha12>.py beside the
logs, unless a copy of that version is there already, so every version that wrote a log is kept.
"""
import hashlib
import os
import shutil
import sys
import time


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def sha256_bytes(b):
    return hashlib.sha256(b).hexdigest()


class Log:
    def __init__(self, logdir, name, script, criteria, keep_dir=None, modules=()):
        os.makedirs(logdir, exist_ok=True)
        k = 1
        while os.path.exists(os.path.join(logdir, "%s.%03d.log" % (name, k))):
            k += 1
        self.path = os.path.join(logdir, "%s.%03d.log" % (name, k))
        self.f = open(self.path, "x", encoding="ascii", newline="\n")
        self.fails = 0
        self.checks = 0
        sha = sha256_file(script)
        mods = [(m, sha256_file(m)) for m in modules]
        if keep_dir:
            os.makedirs(keep_dir, exist_ok=True)
            for path, h in [(script, sha)] + mods:
                stem = os.path.splitext(os.path.basename(path))[0]
                kept = os.path.join(keep_dir, "%s.%s.py" % (stem, h[:12]))
                if not os.path.exists(kept):
                    shutil.copyfile(path, kept)
                    os.chmod(kept, 0o444)
        self.w("# %s, written by %s (SHA-256 %s)" % (os.path.basename(self.path), os.path.basename(script), sha))
        for path, h in mods:
            self.w("# with %s (SHA-256 %s)" % (os.path.basename(path), h))
        self.w("# started %s local (%s UTC)" % (time.strftime("%Y-%m-%d %H:%M:%S %z"),
                                               time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())))
        self.w("# python %s on %s" % (sys.version.split()[0], sys.platform))
        self.w("# CRITERIA (fixed before the data, asserted in code):")
        for c in criteria:
            for line in c.strip("\n").splitlines():
                self.w("#   " + line)

    def w(self, line=""):
        self.f.write(line + "\n")
        self.f.flush()
        try:
            print(line)
        except UnicodeEncodeError:
            print(line.encode("ascii", "replace").decode())

    def check(self, ok, text):
        self.checks += 1
        if not ok:
            self.fails += 1
        self.w("%s %s" % ("PASS" if ok else "FAIL", text))
        return ok

    def close(self):
        self.w("# %d checks, %d failed; ended %s local" % (self.checks, self.fails, time.strftime("%Y-%m-%d %H:%M:%S %z")))
        self.f.close()
        return self.fails


# ------------------------------------------------------------------ CPU accounting (Windows), from tests/cpurun.py
# DEBRIS-D's studies/debris-d/tools/cpurun.py, as DEBRIS-E copied it to tests/cpurun.py (cft-debris's own, MIT): the
# process joins a fresh job object, every process it starts joins it too, and at the end the cycles of every process
# caught are summed (QueryProcessCycleTime) and divided by 2.5e9 (the part's base clock; taking it as the counter's
# rate is BELIEVED), with the job's GetProcessTimes-kind total beside it. Done inside the harness, so that no wrapper
# process counts against the desktop's four.
class Cpu:
    def __init__(self, label, ledger):
        self.label, self.ledger, self.on = label, ledger, (sys.platform == "win32" and ledger)
        self.t0 = time.time()
        if not self.on:
            return
        import ctypes
        import ctypes.wintypes as w
        self.ct, self.w = ctypes, w
        k = ctypes.WinDLL("kernel32", use_last_error=True)
        k.CreateJobObjectW.restype = w.HANDLE
        k.CreateJobObjectW.argtypes = [ctypes.c_void_p, w.LPCWSTR]
        k.GetCurrentProcess.restype = w.HANDLE
        k.AssignProcessToJobObject.argtypes = [w.HANDLE, w.HANDLE]
        k.QueryInformationJobObject.argtypes = [w.HANDLE, ctypes.c_int, ctypes.c_void_p, w.DWORD, ctypes.POINTER(w.DWORD)]
        k.OpenProcess.argtypes = [w.DWORD, w.BOOL, w.DWORD]
        k.OpenProcess.restype = w.HANDLE
        k.QueryProcessCycleTime.argtypes = [w.HANDLE, ctypes.POINTER(ctypes.c_ulonglong)]
        self.k = k
        self.job = k.CreateJobObjectW(None, None)
        if not self.job or not k.AssignProcessToJobObject(self.job, k.GetCurrentProcess()):
            raise SystemExit("Cpu: the job object could not be made")
        self.handles = {}
        import threading
        self.stop = False
        self.th = threading.Thread(target=self._poll, daemon=True)
        self.th.start()

    def _pids(self):
        ct = self.ct
        n = 1024
        buf = (ct.c_byte * (8 + 8 * n))()
        if not self.k.QueryInformationJobObject(self.job, 3, buf, ct.sizeof(buf), None):
            return []
        count = ct.cast(buf, ct.POINTER(self.w.DWORD))[1]
        ids = ct.cast(ct.addressof(buf) + 8, ct.POINTER(ct.c_size_t))
        return [ids[i] for i in range(count)]

    def _poll(self):
        while not self.stop:
            for pid in self._pids():
                if pid not in self.handles:
                    h = self.k.OpenProcess(0x1000, False, pid)
                    if h:
                        self.handles[pid] = h
            time.sleep(0.01)

    def close(self):
        wall = time.time() - self.t0
        if not self.on:
            return
        self.stop = True
        self.th.join()
        for pid in self._pids():
            if pid not in self.handles:
                h = self.k.OpenProcess(0x1000, False, pid)
                if h:
                    self.handles[pid] = h
        cyc = 0
        for h in self.handles.values():
            c = self.ct.c_ulonglong(0)
            if self.k.QueryProcessCycleTime(h, self.ct.byref(c)):
                cyc += c.value

        class ACCT(self.ct.Structure):
            _fields_ = [("TotalUserTime", self.ct.c_longlong), ("TotalKernelTime", self.ct.c_longlong),
                        ("a", self.ct.c_longlong), ("b", self.ct.c_longlong), ("c", self.w.DWORD),
                        ("TotalProcesses", self.w.DWORD), ("d", self.w.DWORD), ("e", self.w.DWORD)]
        acct = ACCT()
        self.k.QueryInformationJobObject(self.job, 1, self.ct.byref(acct), self.ct.sizeof(acct), None)
        job_s = (acct.TotalUserTime + acct.TotalKernelTime) / 1e7
        line = "\t".join([time.strftime("%Y-%m-%d %H:%M:%S"), self.label, "%.3f" % wall, "%d" % cyc, "%.3f" % (cyc / 2.5e9),
                          "%.3f" % job_s, "%.3f" % job_s, "%d" % acct.TotalProcesses, "%d" % len(self.handles), "0",
                          "i_harness (in-process)"])
        with open(self.ledger, "a", encoding="utf-8", newline="\n") as f:
            f.write(line + "\n")
        sys.stderr.write("[cpu] %s wall %.1fs cycles/2.5e9 %.1fs job %.1fs processes %d\n" % (
            self.label, wall, cyc / 2.5e9, job_s, acct.TotalProcesses))
