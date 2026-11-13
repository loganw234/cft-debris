# gatelib.py - cft-debris M1: what DEBRIS-E's gate scripts share.
# cft-debris, MIT licence (see LICENSE at the repository root). Written by
# DEBRIS-E, 2026-11-13.
#
# - paths: the repository, the build (M1_BUILD overrides it), the downloads;
# - Log: a numbered log that never overwrites, headed by the SHA-256 of the gate
#   script and of this file, and by the criteria the script states; every
#   version of both files is kept in studies/debris-e/scripts/ under a name
#   carrying the first 12 hex digits of its hash;
# - run(): start a program by its full path (never a bare name: System32 comes
#   before PATH from Python), with bytes in and out (no text-mode CR+LF);
# - exact decoding of binary32/64/128/256 encodings (hex, most significant
#   byte first) to Fractions, and distances in ulps.
import ctypes
import ctypes.wintypes as w
import hashlib
import os
import shutil
import subprocess
import sys
import time
from fractions import Fraction

REPO = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
STUDY = os.path.join(REPO, "studies", "debris-e")
LOGS = os.path.join(STUDY, "logs")
SCRIPTS = os.path.join(STUDY, "scripts")
BUILD = os.environ.get("M1_BUILD", "C:/Users/logan/source/repos/cft-debris-scratch/DEBRIS-E/build/main")
WORK = os.environ.get("M1_WORK", "C:/Users/logan/source/repos/cft-debris-scratch/DEBRIS-E/work")
DOWNLOADS = "C:/Users/logan/source/repos/cft-debris-downloads/"
PY = "C:/Users/logan/AppData/Local/Programs/Miniconda3/python.exe"
if os.environ.get("M1_DRY"):
    # a dry run: its logs and kept scripts go to the scratch, never to the records
    LOGS = os.path.join(WORK, "dry", "logs")
    SCRIPTS = os.path.join(WORK, "dry", "scripts")

FMT = {"native32": 32, "cft32": 32, "native64": 64, "cft64": 64, "cft128": 128, "cft256": 256}
# (exponent bits, fraction bits)
LAYOUT = {32: (8, 23), 64: (11, 52), 128: (15, 112), 256: (19, 236)}


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def exe(variant="O2"):
    return os.path.join(BUILD, "m1run_%s.exe" % variant).replace("\\", "/")


def keep_version(path):
    """copy path into studies/debris-e/scripts/<stem>.<hash12><ext> unless there already"""
    h = sha256(path)
    stem, ext = os.path.splitext(os.path.basename(path))
    os.makedirs(SCRIPTS, exist_ok=True)
    dst = os.path.join(SCRIPTS, "%s.%s%s" % (stem, h[:12], ext))
    if not os.path.exists(dst):
        shutil.copyfile(path, dst)
    return h


def host_load(sample_s=0.5):
    """Windows CPU % over sample_s, from GetSystemTimes (idle against kernel+user)"""
    k32 = ctypes.WinDLL("kernel32")
    def st():
        i, k, u = w.FILETIME(), w.FILETIME(), w.FILETIME()
        k32.GetSystemTimes(ctypes.byref(i), ctypes.byref(k), ctypes.byref(u))
        f = lambda x: (x.dwHighDateTime << 32) | x.dwLowDateTime
        return f(i), f(k) + f(u)
    i0, t0 = st()
    time.sleep(sample_s)
    i1, t1 = st()
    return 100.0 * (1.0 - (i1 - i0) / max(1, t1 - t0))


class Log:
    def __init__(self, gate, script_path, criteria):
        os.makedirs(LOGS, exist_ok=True)
        n = 1
        while os.path.exists(os.path.join(LOGS, "%s.%03d.log" % (gate, n))):
            n += 1
        self.path = os.path.join(LOGS, "%s.%03d.log" % (gate, n))
        self.f = open(self.path, "w", encoding="utf-8", newline="\n")
        self.fails = []
        hs = keep_version(script_path)
        hl = keep_version(os.path.abspath(__file__))
        self.w("# %s, log %03d, written %s" % (gate, n, time.strftime("%Y-%m-%d %H:%M:%S %z")))
        self.w("# script %s sha256 %s" % (os.path.basename(script_path), hs))
        self.w("# gatelib.py sha256 %s" % hl)
        self.w("# build %s" % BUILD)
        for v in ("O2", "O0", "fast", "negctl"):
            if os.path.exists(exe(v)):
                self.w("# m1run_%s.exe sha256 %s" % (v, sha256(exe(v))))
        self.w("# host load at start: %.0f%% (Windows CPU %%, 0.5 s sample)" % host_load())
        self.w("# CRITERIA (stated in the script before its data; asserted below):")
        for line in criteria.strip("\n").split("\n"):
            self.w("#   " + line)

    def w(self, s=""):
        self.f.write(s + "\n")
        self.f.flush()
        print(s)

    def check(self, ok, what):
        self.w(("PASS " if ok else "FAIL ") + what)
        if not ok:
            self.fails.append(what)
        return ok

    def close(self, extra=""):
        verdict = "PASS" if not self.fails else "FAIL (%d)" % len(self.fails)
        self.w("# %s %s" % (verdict, extra))
        self.f.close()
        return 0 if not self.fails else 1


def run(args, log=None, check=True):
    args = [str(a) for a in args]
    t0 = time.perf_counter()
    p = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    dt = time.perf_counter() - t0
    if log:
        log.w("# ran (%.2f s): %s" % (dt, " ".join(args)))
    if check and p.returncode != 0:
        msg = "command failed (%d): %s\n%s" % (p.returncode, " ".join(args), p.stderr.decode("utf-8", "replace"))
        if log:
            log.w("FAIL " + msg)
        raise RuntimeError(msg)
    return p


def read_rows(path, prefix=None):
    rows, head = [], []
    with open(path, "r", encoding="utf-8") as f:
        for ln in f:
            if ln.startswith("#"):
                head.append(ln.rstrip("\n"))
                continue
            t = ln.split()
            if not t:
                continue
            if prefix is not None and t[0] != prefix:
                continue
            rows.append(t)
    return rows, head


def bits(h):
    return int(h, 16)


def is_nan(h, nb):
    e, f = LAYOUT[nb]
    v = int(h, 16)
    return ((v >> f) & ((1 << e) - 1)) == (1 << e) - 1 and (v & ((1 << f) - 1)) != 0


def value(h, nb):
    """exact value of an encoding as a Fraction (None for NaN, +-inf as float)"""
    e, f = LAYOUT[nb]
    v = int(h, 16)
    s = v >> (e + f)
    ex = (v >> f) & ((1 << e) - 1)
    fr = v & ((1 << f) - 1)
    bias = (1 << (e - 1)) - 1
    if ex == (1 << e) - 1:
        return None if fr else float("-inf" if s else "inf")
    if ex == 0:
        x = Fraction(fr, 1 << f) * Fraction(2) ** (1 - bias)
    else:
        x = (1 + Fraction(fr, 1 << f)) * Fraction(2) ** (ex - bias)
    return -x if s else x


def ordered(h, nb):
    e, f = LAYOUT[nb]
    v = int(h, 16)
    sign = v >> (e + f)
    mag = v & ((1 << (e + f)) - 1)
    return -mag if sign else mag


def ulps(h1, h2, nb):
    return abs(ordered(h1, nb) - ordered(h2, nb))


def same(h1, h2, nb):
    """the NaN rule: non-NaN results agree bit for bit; NaN results agree as NaNs"""
    n1, n2 = is_nan(h1, nb), is_nan(h2, nb)
    if n1 or n2:
        return n1 and n2
    return h1 == h2
