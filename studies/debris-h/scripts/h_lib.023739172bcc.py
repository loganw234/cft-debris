# h_lib.py - cft-debris M1 (DEBRIS-H): what DEBRIS-H's scripts share. Standard library only: it runs on amd-arc-box
# (Linux, Python 3.12) and on the desktop (Windows), and every path comes from its caller.
# cft-debris, MIT licence (see LICENSE at the repository root). Written by DEBRIS-H, 2026-11-18, from cft-debris's own
# earlier code (MIT), each piece copied with its rules unchanged:
#   - the host time scales, quantize() and parse_epoch(): DEBRIS-F's tests/f_lib.py (B1);
#   - the GP CSV's 17 columns and Orekit's units (orekit_line): DEBRIS-F's tests/f5_sample.py;
#   - the fit's perigee rule (MU 3.986004418e14), BC0, CRAM and NOBS: DEBRIS-F's tests/f_fit.py;
#   - the element-set key and the 200 km perigee formula (GM 3.986004415e14): DEBRIS-G's tests/g_pop.py;
#   - quant() and ric(): DEBRIS-F's tests/f6_hindcast.py;
#   - value(), is_nan() and same() (the NaN rule): DEBRIS-E's tests/gatelib.py;
#   - the Windows job-object CPU count: DEBRIS-D's cpurun.py (DEBRIS-E's tests/cpurun.py).
import csv
import hashlib
import math
import os
import platform
import re
import struct
import subprocess
import sys
import threading
import time
from fractions import Fraction

WIN = sys.platform == "win32"

# ------------------------------------------------------------------ constants
JD_EPOCH = 2461329.5            # MJD 61329.0 TDB: M1's t = 0 (DEBRIS-F, kept)
MJD_E = 61329
UNIX_MJD = 40587                # the MJD of 1970-01-01
Q_TIME = Fraction(1, 1 << 20)   # every run's origin and end are multiples of 2^-20 s (DEBRIS-F's B1)
RMIN = 6498137.0                # 120 km above 6,378.137 km
STEP = 15.0
GROUPS = ["stations", "fengyun-1c-debris", "iridium-33-debris", "cosmos-2251-debris"]
COLUMNS = ["OBJECT_NAME", "OBJECT_ID", "EPOCH", "MEAN_MOTION", "ECCENTRICITY", "INCLINATION", "RA_OF_ASC_NODE",
           "ARG_OF_PERICENTER", "MEAN_ANOMALY", "EPHEMERIS_TYPE", "CLASSIFICATION_TYPE", "NORAD_CAT_ID", "ELEMENT_SET_NO",
           "REV_AT_EPOCH", "BSTAR", "MEAN_MOTION_DOT", "MEAN_MOTION_DDOT"]
KEYF = ["MEAN_MOTION", "ECCENTRICITY", "INCLINATION", "RA_OF_ASC_NODE", "ARG_OF_PERICENTER", "MEAN_ANOMALY",
        "BSTAR", "MEAN_MOTION_DOT", "MEAN_MOTION_DDOT"]
MU_F = 3.986004418e14           # tests/f_fit.py: the fit's 1,000 km rule for estimating bc
GM_G = 3.986004415e14           # tests/g_pop.py: the 200 km perigee screen
RE = 6378137.0
BC0 = 0.01
CRAM = 0.01
NOBS = 721

# cft-fp256's night launcher refuses to start while a process matches this (the lead, 2026-11-18, from cft-fp256's
# lead): no command line of the service may contain any of these strings, nor be named exactly one of NAMES_FORBIDDEN.
PGREP_FORBIDDEN = re.compile(r"card_stress.py|card-stress.sh|divsqrt-soak|clause5-soak|chunk_card.py|verify/run.sh|cft_sched.py")
NAMES_FORBIDDEN = {"rate-probe", "routine-sweep"}


def assert_safe(argv):
    line = " ".join(str(a) for a in argv)
    if PGREP_FORBIDDEN.search(line) or os.path.basename(str(argv[0])) in NAMES_FORBIDDEN:
        raise SystemExit("refusing a command line that cft-fp256's night launcher matches: %s" % line)
    return argv


# ------------------------------------------------------------------ files
def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def sha256_bytes(b):
    return hashlib.sha256(b).hexdigest()


def write_new(path, data):
    """write bytes to a file that must not exist (never overwrite)"""
    d = os.path.dirname(path)
    if d:
        os.makedirs(d, exist_ok=True)
    with open(path, "xb") as f:
        f.write(data if isinstance(data, bytes) else data.encode("utf-8"))


def append_line(path, line):
    with open(path, "ab") as f:
        f.write((line.rstrip("\n") + "\n").encode("utf-8"))
        f.flush()
        try:
            os.fsync(f.fileno())
        except OSError:
            pass


def next_numbered(dirpath, stem, ext):
    os.makedirs(dirpath, exist_ok=True)
    n = 1
    while os.path.exists(os.path.join(dirpath, "%s.%03d%s" % (stem, n, ext))):
        n += 1
    return n, os.path.join(dirpath, "%s.%03d%s" % (stem, n, ext))


def keep_version(path, keep_dir):
    """copy a script into keep_dir as <stem>.<first 12 hex of its SHA-256><ext>, unless there already"""
    h = sha256(path)
    if keep_dir:
        os.makedirs(keep_dir, exist_ok=True)
        stem, ext = os.path.splitext(os.path.basename(path))
        dst = os.path.join(keep_dir, "%s.%s%s" % (stem, h[:12], ext))
        if not os.path.exists(dst):
            with open(path, "rb") as a, open(dst, "xb") as b:
                b.write(a.read())
    return h


class Log:
    """a numbered log that never overwrites, headed by the SHA-256 of the script that writes it and of this file, and
    by the criteria the script states before its data"""

    def __init__(self, name, logdir, script, criteria, extra=(), keep_dir=None, quiet=False):
        self.n, self.path = next_numbered(logdir, name, ".log")
        self.f = open(self.path, "x", encoding="utf-8", newline="\n")
        self.fails, self.quiet, self.name = [], quiet, name
        u = platform.uname()
        self.w("# %s, log %03d, written %s" % (name, self.n, time.strftime("%Y-%m-%d %H:%M:%S %z")))
        self.w("# script %s sha256 %s" % (os.path.basename(script), keep_version(script, keep_dir)))
        self.w("# h_lib.py sha256 %s" % keep_version(os.path.abspath(__file__), keep_dir))
        for p in extra:
            self.w("# %s sha256 %s" % (os.path.basename(p), keep_version(p, keep_dir) if p.endswith((".py", ".js")) else sha256(p)))
        self.w("# host %s %s %s; python %s" % (u.system, u.release, u.machine, platform.python_version()))
        if criteria:
            self.w("# CRITERIA (stated in the script before its data; asserted below):")
            for line in criteria.strip("\n").split("\n"):
                self.w("#   " + line)

    def w(self, s=""):
        self.f.write(s + "\n")
        self.f.flush()
        if not self.quiet:
            try:
                print(s, flush=True)
            except UnicodeEncodeError:
                print(s.encode("ascii", "replace").decode(), flush=True)

    def check(self, ok, what):
        self.w(("PASS " if ok else "FAIL ") + what)
        if not ok:
            self.fails.append(what)
        return ok

    def close(self, extra=""):
        self.w("# %s %s" % ("PASS" if not self.fails else "FAIL (%d)" % len(self.fails), extra))
        self.f.close()
        return 0 if not self.fails else 1


# ------------------------------------------------------------------ processes
def popen(argv, **kw):
    argv = [str(a) for a in assert_safe(argv)]
    if WIN and not os.path.isabs(argv[0]) and os.path.exists(argv[0]):
        argv[0] = os.path.abspath(argv[0])  # CreateProcess does not resolve a relative program path
    return subprocess.Popen(argv, **kw)


def run(argv, log=None, env=None, check=True, cwd=None, timeout=None):
    """start a program by its full path, bytes in and out; returns (returncode, stdout bytes, stderr bytes)"""
    t0 = time.monotonic()
    p = popen(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env, cwd=cwd)
    out, err = p.communicate(timeout=timeout)
    dt = time.monotonic() - t0
    if log:
        log.w("# ran (%.2f s wall, exit %d): %s" % (dt, p.returncode, " ".join(str(a) for a in argv[:14])))
    if check and p.returncode != 0:
        msg = "command failed (%d): %s\n%s\n%s" % (p.returncode, " ".join(str(a) for a in argv), out.decode("utf-8", "replace")[-1500:],
                                                 err.decode("utf-8", "replace")[-1500:])
        if log:
            log.w("FAIL " + msg.replace("\n", "\n#   "))
        raise RuntimeError(msg)
    return p.returncode, out, err


def run_pool(cmds, procs, log=None, env=None, nice=None):
    """run the commands (lists) with at most procs at once; returns their return codes in order. Each command's
    output goes to a file named by its last element + '.stdout' / '.stderr' only if given as (argv, out_path)."""
    pending = list(enumerate(cmds))
    running, codes = {}, [None] * len(cmds)
    while pending or running:
        while pending and len(running) < procs:
            i, c = pending.pop(0)
            argv, stem = c if isinstance(c, tuple) else (c, None)
            so = open(stem + ".stdout", "wb") if stem else subprocess.DEVNULL
            se = open(stem + ".stderr", "wb") if stem else subprocess.DEVNULL
            pre = None
            if nice is not None and not WIN:
                pre = (lambda n=nice: os.setpriority(os.PRIO_PROCESS, 0, n))
            p = popen(argv, stdout=so, stderr=se, env=env, preexec_fn=pre)
            running[i] = (p, so, se, argv, time.monotonic())
        time.sleep(0.05)
        for i in list(running):
            p, so, se, argv, t0 = running[i]
            if p.poll() is not None:
                codes[i] = p.returncode
                for h in (so, se):
                    if h is not subprocess.DEVNULL:
                        h.close()
                if log:
                    log.w("# ran (%.2f s wall, exit %d): %s" % (time.monotonic() - t0, p.returncode, " ".join(str(a) for a in argv[:12])))
                del running[i]
    return codes


def java_argv(java, jars, script, args):
    return [java, "-cp", os.pathsep.join(jars), "jdk.nashorn.tools.Shell", script, "--"] + [str(a) for a in args]


# ------------------------------------------------------------------ the desktop's CPU count (Windows only)
class CpuAccount:
    """Windows: put this process in a new job object, so that every process it starts joins it; poll the job's
    process list and keep a query handle on each process, then sum QueryProcessCycleTime over every process caught
    (this one included) and divide by 2.5e9 cycles a second (the part's base clock; taking it as the counter's rate
    is BELIEVED); beside it, GetProcessTimes and the job's own accounting. Elsewhere it records getrusage."""

    HZ = 2.5e9

    def __init__(self, label, tsv):
        self.label, self.tsv, self.t0 = label, tsv, time.monotonic()
        self.handles, self.stop, self.th = {}, threading.Event(), None
        if WIN and tsv:
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
            k.GetProcessTimes.argtypes = [w.HANDLE] + [ctypes.POINTER(w.FILETIME)] * 4
            self.k = k
            self.job = k.CreateJobObjectW(None, None)
            if not self.job or not k.AssignProcessToJobObject(self.job, k.GetCurrentProcess()):
                raise SystemExit("CpuAccount: cannot create or join a job object")
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
        while not self.stop.is_set():
            for pid in self._pids():
                if pid not in self.handles:
                    h = self.k.OpenProcess(0x1000, False, pid)
                    if h:
                        self.handles[pid] = h
            time.sleep(0.01)

    def close(self, note=""):
        wall = time.monotonic() - self.t0
        if not (WIN and self.tsv):
            return None
        self.stop.set()
        self.th.join()
        for pid in self._pids():
            if pid not in self.handles:
                h = self.k.OpenProcess(0x1000, False, pid)
                if h:
                    self.handles[pid] = h
        ct, w = self.ct, self.w
        cyc, pt = 0, 0.0
        for h in self.handles.values():
            c = ct.c_ulonglong(0)
            if self.k.QueryProcessCycleTime(h, ct.byref(c)):
                cyc += c.value
            a, b, kt, ut = w.FILETIME(), w.FILETIME(), w.FILETIME(), w.FILETIME()
            if self.k.GetProcessTimes(h, ct.byref(a), ct.byref(b), ct.byref(kt), ct.byref(ut)):
                pt += (((kt.dwHighDateTime << 32) | kt.dwLowDateTime) + ((ut.dwHighDateTime << 32) | ut.dwLowDateTime)) / 1e7

        class ACC(ct.Structure):
            _fields_ = [("TU", ct.c_longlong), ("TK", ct.c_longlong), ("PU", ct.c_longlong), ("PK", ct.c_longlong),
                        ("PF", w.DWORD), ("TP", w.DWORD), ("AP", w.DWORD), ("TT", w.DWORD)]
        acc = ACC()
        self.k.QueryInformationJobObject(self.job, 1, ct.byref(acc), ct.sizeof(acc), None)
        line = "\t".join([time.strftime("%Y-%m-%d %H:%M:%S"), self.label, "%.3f" % wall, "%d" % cyc, "%.3f" % (cyc / self.HZ),
                          "%.3f" % pt, "%.3f" % ((acc.TU + acc.TK) / 1e7), "%d" % acc.TP, "%d" % len(self.handles), "0", note])
        append_line(self.tsv, line)
        return cyc / self.HZ


# ------------------------------------------------------------------ B1, the host time scales (DEBRIS-F's f_lib.py)
_LEAPS = None


def load_leaps(path):
    """tai-utc.dat: (MJD of the change, A, MJD0, rate), TAI-UTC = A + (MJD - MJD0) rate"""
    global _LEAPS
    out = []
    with open(path, "r", encoding="ascii") as f:
        for ln in f:
            if "=JD" not in ln:
                continue
            jd = Fraction(ln.split("=JD")[1].split()[0])
            a = Fraction(ln.split("TAI-UTC=")[1].split()[0])
            m0 = Fraction(ln.split("MJD -")[1].split(")")[0].strip().rstrip("."))
            rate = Fraction(ln.split(") X")[1].split()[0].rstrip("S"))
            out.append((jd - Fraction("2400000.5"), a, m0, rate))
    assert out, "no leap-second rows in %s" % path
    _LEAPS = out
    return out


def dat(mjd_utc):
    assert _LEAPS is not None, "load_leaps() first"
    k = None
    for i, e in enumerate(_LEAPS):
        if e[0] <= mjd_utc:
            k = i
    if k is None:
        return Fraction(0)
    m, a, m0, r = _LEAPS[k]
    return a + (Fraction(mjd_utc) - m0) * r


def tdb_minus_tt(T):
    """USNO Circular 179, eq. (2.6); T in Julian centuries of TT from J2000.0; seconds"""
    return (0.001657 * math.sin(628.3076 * T + 6.2401) + 0.000022 * math.sin(575.3385 * T + 4.2970) +
            0.000014 * math.sin(1256.6152 * T + 6.1969) + 0.000005 * math.sin(606.9777 * T + 4.0212) +
            0.000005 * math.sin(52.9691 * T + 0.4444) + 0.000002 * math.sin(21.3299 * T + 5.5431) +
            0.000010 * T * math.sin(628.3076 * T + 4.2490))


def mjd_of(y, m, d):
    a = (14 - m) // 12
    yy = y + 4800 - a
    mm = m + 12 * a - 3
    jdn = d + (153 * mm + 2) // 5 + 365 * yy + yy // 4 - yy // 100 + yy // 400 - 32045
    return jdn - 2400001


def utc_to_tdb(mjd_day, sec_of_day):
    """TDB seconds from JD_EPOCH (exact Fraction but for TDB-TT, a binary64 from eq. 2.6) of a UTC instant"""
    sec = Fraction(sec_of_day)
    tai = (mjd_day - MJD_E) * 86400 + sec + dat(Fraction(mjd_day) + sec / 86400)
    tt = tai + Fraction("32.184")
    T = float(((MJD_E - Fraction("51544.5")) * 86400 + tt) / 3155760000)
    return tt + Fraction(tdb_minus_tt(T))


def tdb_to_tai(t):
    """TAI seconds from MJD 61329.0 TAI of TDB t: TT = TDB - (TDB-TT) by two fixed-point passes of eq. (2.6)"""
    t = Fraction(t)
    T0 = float(((MJD_E - Fraction("51544.5")) * 86400 + t) / 3155760000)
    g = tdb_minus_tt(T0)
    g = tdb_minus_tt(T0 - g / 3155760000.0)
    return t - Fraction(g) - Fraction("32.184")


def tai_to_utc_mjd(tai):
    approx = Fraction(MJD_E) + (Fraction(tai) - 37) / 86400
    d = dat(approx)
    return Fraction(MJD_E) + (Fraction(tai) - d) / 86400


def quantize(x, q=Q_TIME):
    """x rounded to the nearest multiple of q (ties to even); a binary64 exactly"""
    k = Fraction(x) / q
    n = math.floor(k)
    r = k - n
    if r > Fraction(1, 2) or (r == Fraction(1, 2) and n % 2 == 1):
        n += 1
    v = n * q
    f = float(v)
    assert Fraction(f) == v
    return f


def parse_epoch(s):
    """CelesTrak's EPOCH 'YYYY-MM-DDThh:mm:ss.ffffff' (UTC) -> (MJD, Fraction seconds of day)"""
    d, t = s.strip().split("T")
    y, mo, dd = (int(x) for x in d.split("-"))
    hh, mi, ss = t.split(":")
    return mjd_of(y, mo, dd), int(hh) * 3600 + int(mi) * 60 + Fraction(ss)


def epoch_tdb(row):
    m, s = parse_epoch(row["EPOCH"])
    return utc_to_tdb(m, s)


def epoch_q(row):
    return quantize(epoch_tdb(row))


def tai_hex(t):
    """an instant for Orekit: TAI seconds from 2026-10-16T00:00:00 TAI, as a Java/C99 hex float"""
    return float.hex(float(tdb_to_tai(Fraction(t))))


def tdb_to_unix(t):
    """the POSIX time (UTC) of TDB t, exact but for eq. (2.6)"""
    return (tai_to_utc_mjd(tdb_to_tai(t)) - UNIX_MJD) * 86400


def unix_to_tdb(u):
    mjd = UNIX_MJD + Fraction(u) / 86400
    day = math.floor(mjd)
    return utc_to_tdb(day, (mjd - day) * 86400)


def tdb_minus_utc(t):
    """TDB - UTC at TDB t (s): t less the UTC seconds from 2026-10-16 00:00 UTC"""
    return float(Fraction(t) - (tai_to_utc_mjd(tdb_to_tai(t)) - MJD_E) * 86400)


def clock_map(ts, shift=0.0):
    """the clock map (unix_ref, t_ref): step k of a run with origin ts is due at unix_ref + (ts + 15 k - t_ref). The
    long run's map is the UTC of ts (shift 0); tests may shift it (seconds added to unix_ref)."""
    return float(tdb_to_unix(ts)) + shift, float(ts)


def tdb_label(t):
    """a TDB time as a calendar label (TDB, not UTC), to the second"""
    s = Fraction(t) + (MJD_E - UNIX_MJD) * 86400
    return time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(float(s))) + " TDB"


# ------------------------------------------------------------------ GP data (DEBRIS-F's f5_sample.py, DEBRIS-G's g_pop.py)
def read_gp(path, group):
    """one group's CSV, by the header's own 17 names (asserted in order); every number kept as its decimal string"""
    rows = []
    with open(path, "r", encoding="utf-8", newline="") as f:
        rd = csv.reader(f)
        head = next(rd)
        if head != COLUMNS:
            raise SystemExit("header of %s is %s" % (path, head))
        for r in rd:
            if not r:
                continue
            if len(r) != 17:
                raise SystemExit("a row of %s has %d fields" % (path, len(r)))
            d = dict(zip(COLUMNS, r))
            d["GROUP"] = group
            rows.append(d)
    return rows


def set_key(row):
    """DEBRIS-G's key: the epoch as whole microseconds and the nine mean-element fields, as parsed values"""
    s = row["EPOCH"]
    d, t = s.split("T")
    hh, mi, ss = t.split(":")
    sec, _, frac = ss.partition(".")
    us = int((frac + "000000")[:6]) if frac else 0
    return (d, int(hh), int(mi), int(sec), us) + tuple(float(row[c]) for c in KEYF)


def perigee_g(row):
    """DEBRIS-G's perigee (m): a(1 - e) - 6378137 m, a from the mean motion with GM 3.986004415e14"""
    nrad = float(row["MEAN_MOTION"]) * 2 * math.pi / 86400.0
    a = (GM_G / (nrad * nrad)) ** (1.0 / 3.0)
    return a * (1.0 - float(row["ECCENTRICITY"])) - RE


def perigee_alt_km_f(row):
    """DEBRIS-F's fit rule (tests/f_fit.py): bc is estimated where this is under 1,000 km"""
    n = float(row["MEAN_MOTION"]) * math.pi / 43200.0
    a = (MU_F / (n * n)) ** (1.0 / 3.0)
    return (a * (1.0 - float(row["ECCENTRICITY"])) - 6378137.0) / 1000.0


def orekit_line(d, key):
    pi = 3.141592653589793
    oid = d["OBJECT_ID"]
    try:
        ly = int(oid[:4]) if len(oid) >= 4 else 0
        ln = int(oid[5:8]) if len(oid) >= 8 else 0
        lp = oid[8:] if len(oid) > 8 else "A"
    except ValueError:
        ly, ln, lp = 0, 0, "A"
    lp = lp or "A"
    vals = [float(d["MEAN_MOTION"]) * pi / 43200.0, float(d["MEAN_MOTION_DOT"]) * pi / 1.86624e9,
            float(d["MEAN_MOTION_DDOT"]) * pi / 5.3747712e13, float(d["ECCENTRICITY"]),
            float(d["INCLINATION"]) * pi / 180.0, float(d["ARG_OF_PERICENTER"]) * pi / 180.0,
            float(d["RA_OF_ASC_NODE"]) * pi / 180.0, float(d["MEAN_ANOMALY"]) * pi / 180.0]
    return ("OBJ %s %d %s %d %d %s %d %d %s %s %d %s" % (key, int(d["NORAD_CAT_ID"]), d["CLASSIFICATION_TYPE"] or "U", ly, ln, lp,
            int(d["EPHEMERIS_TYPE"]), int(d["ELEMENT_SET_NO"]), d["EPOCH"], " ".join(float.hex(v) for v in vals),
            int(d["REV_AT_EPOCH"]), float.hex(float(d["BSTAR"])))), vals


def decode_input(path, items, plant_n=None):
    """the decoder's input: items are (key, row, [TDB instants]); plant_n maps a key to a replacement mean motion
    (rad/s, a control)"""
    with open(path, "w", newline="\n") as f:
        for key, d, ts in items:
            line, vals = orekit_line(d, key)
            if plant_n and key in plant_n:
                p = line.split(" ")
                p[10] = float.hex(plant_n[key])
                line = " ".join(p)
            f.write(line + " %d\n" % len(ts))
            for k, t in enumerate(ts):
                f.write("I %d %s\n" % (k, tai_hex(t)))


def read_decoded(path):
    """the decoder's output: {key: [(x, y, z, vx, vy, vz)] in instant order}; a refused object maps to None"""
    out = {}
    with open(path, "r", encoding="ascii") as f:
        for ln in f:
            p = ln.split()
            if p and p[0] == "V":
                out.setdefault(p[1], []).append(tuple(float.fromhex(x) for x in p[4:10]))
            elif p and p[0] == "F":
                out[p[1]] = None
    return out


# ------------------------------------------------------------------ statistics and geometry (DEBRIS-F's f6_hindcast.py)
def quant(vals, f):
    v = sorted(vals)
    return v[min(len(v) - 1, int(math.ceil(f * len(v))) - 1)]


def median(vals):
    v = sorted(vals)
    n = len(v)
    if n == 0:
        return float("nan")
    return v[n // 2] if n % 2 else 0.5 * (v[n // 2 - 1] + v[n // 2])


def ric(dp, r, v):
    rn = math.sqrt(sum(x * x for x in r))
    R = [x / rn for x in r]
    c = [r[1] * v[2] - r[2] * v[1], r[2] * v[0] - r[0] * v[2], r[0] * v[1] - r[1] * v[0]]
    cn = math.sqrt(sum(x * x for x in c))
    C = [x / cn for x in c]
    A = [C[1] * R[2] - C[2] * R[1], C[2] * R[0] - C[0] * R[2], C[0] * R[1] - C[1] * R[0]]
    return [sum(a * b for a, b in zip(dp, R)), sum(a * b for a, b in zip(dp, A)), sum(a * b for a, b in zip(dp, C))]


def dist(a, b):
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))


# ------------------------------------------------------------------ encodings (DEBRIS-E's gatelib.py)
LAYOUT = {32: (8, 23), 64: (11, 52), 128: (15, 112), 256: (19, 236)}
ESZ = {"native64": 8, "cft256": 32, "cft128": 16, "cft64": 8, "native32": 4, "cft32": 4}


def is_nan(h, nb):
    e, f = LAYOUT[nb]
    v = int(h, 16)
    return ((v >> f) & ((1 << e) - 1)) == (1 << e) - 1 and (v & ((1 << f) - 1)) != 0


def value(h, nb):
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


def same(h1, h2, nb):
    """the NaN rule: non-NaN results agree bit for bit; NaN results agree as NaNs"""
    n1, n2 = is_nan(h1, nb), is_nan(h2, nb)
    if n1 or n2:
        return n1 and n2
    return h1 == h2


def f64(h):
    """a binary64 from its 16 hex digits (most significant first)"""
    return struct.unpack(">d", bytes.fromhex(h))[0]


def h64(x):
    return struct.pack(">d", x).hex()


# ------------------------------------------------------------------ the service's files
def read_seed(path):
    """a seed file: {'head': [...], 'ts': float, 'rows': {idx: (cat, flags, ts, y[6], bc, cram)}} in index order"""
    head, rows, ts = [], {}, None
    with open(path, "r", encoding="ascii") as f:
        for ln in f:
            if ln.startswith("#"):
                head.append(ln.rstrip("\n"))
                continue
            p = ln.split()
            if not p:
                continue
            assert len(p) == 12, "seed line of %d fields" % len(p)
            idx, cat, flags = int(p[0]), int(p[1]), int(p[2])
            v = [float.fromhex(x) for x in p[3:12]]
            assert idx == len(rows), "seed indices must run 0, 1, 2, ... (line %d has %d)" % (len(rows), idx)
            ts = v[0] if ts is None else ts
            assert v[0] == ts, "one T_s for every object"
            rows[idx] = (cat, flags, v[0], v[1:7], v[7], v[8])
    return {"head": head, "ts": ts, "rows": rows}


def read_ckpt(path):
    """a checkpoint file: its header fields and {idx: (decay_step, kind hex [6], binary64 hex [6], bc hex, cram hex)}"""
    hdr, rows, end = {}, {}, None
    with open(path, "r", encoding="ascii") as f:
        for ln in f:
            if ln.startswith("# m1h checkpoint"):
                p = ln.split()[3:]
                hdr = dict(zip(p[0::2], p[1::2]))
                continue
            if ln.startswith("# end"):
                end = int(ln.split()[2])
                continue
            if ln.startswith("#"):
                continue
            p = ln.split()
            if not p:
                continue
            rows[int(p[0])] = (int(p[1]), p[2:8], p[8:14], p[14], p[15])
    hdr["_complete"] = end is not None and end == len(rows)
    return hdr, rows


def cpu_count_stat():
    """the logical CPUs /proc/stat lists (Linux)"""
    n = 0
    with open("/proc/stat", encoding="ascii") as f:
        for ln in f:
            if re.match(r"cpu\d+ ", ln):
                n += 1
    return n


def stat_busy():
    """busy jiffies from /proc/stat's first line: user nice system irq softirq steal (idle and iowait excluded)"""
    with open("/proc/stat", encoding="ascii") as f:
        v = [int(x) for x in f.readline().split()[1:9]]
    return v[0] + v[1] + v[2] + v[5] + v[6] + v[7]
