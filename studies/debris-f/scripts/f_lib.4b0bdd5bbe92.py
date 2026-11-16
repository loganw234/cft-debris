# f_lib.py - cft-debris M1 (DEBRIS-F): what DEBRIS-F's gate scripts share.
# cft-debris, MIT licence (see LICENSE at the repository root). Written by DEBRIS-F, 2026-11-16, from
# DEBRIS-E's tests/gatelib.py (cft-debris's own, MIT): the numbered log headed by script hashes and criteria,
# run() by full path with bytes in and out, and the exact decoding of binary encodings, now writing into
# studies/debris-f/. Added: the host time scales in exact arithmetic (B1), Orekit through Nashorn, and the
# angle between two rotations.
import hashlib
import math
import os
import subprocess
import sys
import time
from fractions import Fraction

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gatelib as G  # noqa: E402  (DEBRIS-E's: value(), is_nan(), same(), host_load())

REPO = G.REPO
STUDY = os.path.join(REPO, "studies", "debris-f")
LOGS = os.path.join(STUDY, "logs")
SCRIPTS = os.path.join(STUDY, "scripts")
SCRATCH = "C:/Users/logan/source/repos/cft-debris-scratch/DEBRIS-F"
BUILD = os.environ.get("M1F_BUILD", SCRATCH + "/build/main")
WORK = SCRATCH + "/work"
DATA = SCRATCH + "/data"
DOWNLOADS = "C:/Users/logan/source/repos/cft-debris-downloads/"
LEDGER_F = "C:/Users/logan/source/repos/cft-debris-ledger/debris-f"
PY = "C:/Users/logan/AppData/Local/Programs/Miniconda3/python.exe"
JAVA = "C:/Program Files/Java/jre-1.8/bin/java.exe"
JARS = [DOWNLOADS + j + "/" + j for j in (
    "orekit-13.1.9.jar", "hipparchus-core-4.0.3.jar", "hipparchus-geometry-4.0.3.jar", "hipparchus-ode-4.0.3.jar",
    "hipparchus-fitting-4.0.3.jar", "hipparchus-optim-4.0.3.jar", "hipparchus-filtering-4.0.3.jar",
    "hipparchus-stat-4.0.3.jar")]
CPU_TSV = os.path.join(STUDY, "records", "cpu.tsv")

JD_EPOCH = 2461329.5          # MJD 61329.0 TDB: M1's t = 0 for the whole round
MJD_E = 61329
Q_TIME = Fraction(1, 1 << 20)  # every run's origin and end are multiples of 2^-20 s


def sha256(path):
    return G.sha256(path)


def keep_version(path):
    h = sha256(path)
    stem, ext = os.path.splitext(os.path.basename(path))
    os.makedirs(SCRIPTS, exist_ok=True)
    dst = os.path.join(SCRIPTS, "%s.%s%s" % (stem, h[:12], ext))
    if not os.path.exists(dst):
        with open(path, "rb") as a, open(dst, "wb") as b:
            b.write(a.read())
    return h


class Log:
    """a numbered log that never overwrites, headed by the hashes of the script, this file and gatelib.py,
    and by the criteria the script states before its data"""

    def __init__(self, gate, script_path, criteria, extra_files=()):
        os.makedirs(LOGS, exist_ok=True)
        n = 1
        while os.path.exists(os.path.join(LOGS, "%s.%03d.log" % (gate, n))):
            n += 1
        self.n = n
        self.path = os.path.join(LOGS, "%s.%03d.log" % (gate, n))
        self.f = open(self.path, "w", encoding="utf-8", newline="\n")
        self.fails = []
        self.w("# %s, log %03d, written %s" % (gate, n, time.strftime("%Y-%m-%d %H:%M:%S %z")))
        self.w("# script %s sha256 %s" % (os.path.basename(script_path), keep_version(script_path)))
        self.w("# f_lib.py sha256 %s" % keep_version(os.path.abspath(__file__)))
        self.w("# gatelib.py sha256 %s (DEBRIS-E's, unchanged)" % sha256(os.path.join(REPO, "tests", "gatelib.py")))
        for p in extra_files:
            self.w("# %s sha256 %s" % (os.path.basename(p), keep_version(p)))
        self.w("# build %s" % BUILD)
        self.w("# host load at start: %.0f%% (Windows CPU %%, 0.5 s sample)" % G.host_load())
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


def run(args, log=None, check=True, cpu_label=None):
    """start a program by its full path, bytes in and out; with cpu_label, charged through tests/cpurun.py"""
    args = [str(a) for a in args]
    if cpu_label:
        args = [PY, "-I", "-B", os.path.join(REPO, "tests", "cpurun.py"), cpu_label, CPU_TSV, "--"] + args
    t0 = time.perf_counter()
    p = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    dt = time.perf_counter() - t0
    if log:
        log.w("# ran (%.2f s): %s" % (dt, " ".join(args[-12:])))
    if check and p.returncode != 0:
        msg = "command failed (%d): %s\n%s\n%s" % (p.returncode, " ".join(args), p.stdout.decode("utf-8", "replace")[-2000:],
                                                 p.stderr.decode("utf-8", "replace")[-2000:])
        if log:
            log.w("FAIL " + msg)
        raise RuntimeError(msg)
    return p


def orekit(script, args, log=None, cpu_label=None):
    return run([JAVA, "-cp", ";".join(JARS), "jdk.nashorn.tools.Shell", script, "--"] + list(args), log, True, cpu_label)


# ------------------------------------------------------------------ B1, the host time scales, exact
def leaps(path=DOWNLOADS + "tai-utc.dat/tai-utc.dat"):
    """tai-utc.dat: (MJD of the change, A, MJD0, rate), TAI-UTC = A + (MJD - MJD0) rate"""
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
    return out


LEAPS = None


def dat(mjd_utc, table=None):
    global LEAPS
    if table is None:
        if LEAPS is None:
            LEAPS = leaps()
        table = LEAPS
    k = None
    for i, e in enumerate(table):
        if e[0] <= mjd_utc:
            k = i
    if k is None:
        return Fraction(0)
    m, a, m0, r = table[k]
    return a + (Fraction(mjd_utc) - m0) * r


def tdb_minus_tt(T):
    """USNO Circular 179, eq. (2.6); T in Julian centuries of TT from J2000.0; seconds"""
    return (0.001657 * math.sin(628.3076 * T + 6.2401) + 0.000022 * math.sin(575.3385 * T + 4.2970) +
            0.000014 * math.sin(1256.6152 * T + 6.1969) + 0.000005 * math.sin(606.9777 * T + 4.0212) +
            0.000005 * math.sin(52.9691 * T + 0.4444) + 0.000002 * math.sin(21.3299 * T + 5.5431) +
            0.000010 * T * math.sin(628.3076 * T + 4.2490))


def mjd_of(y, m, d):
    """the MJD of a Gregorian calendar date (exact integer arithmetic)"""
    a = (14 - m) // 12
    yy = y + 4800 - a
    mm = m + 12 * a - 3
    jdn = d + (153 * mm + 2) // 5 + 365 * yy + yy // 4 - yy // 100 + yy // 400 - 32045
    return jdn - 2400001


def utc_to_tdb(mjd_day, sec_of_day):
    """TDB seconds from JD_EPOCH (exact Fraction but for TDB-TT, a binary64 from eq. 2.6) of a UTC instant
    given as an integer MJD and Fraction seconds of that day (no leap second inside the day)"""
    sec = Fraction(sec_of_day)
    tai = (mjd_day - MJD_E) * 86400 + sec + dat(Fraction(mjd_day) + sec / 86400)
    tt = tai + Fraction("32.184")
    T = float(((MJD_E - Fraction("51544.5")) * 86400 + tt) / 3155760000)
    return tt + Fraction(tdb_minus_tt(T))


def tdb_to_tai(t):
    """TAI seconds from MJD 61329.0 TAI of TDB t (seconds from JD_EPOCH): TT = TDB - (TDB-TT) by two fixed-point
    passes of eq. (2.6), as src/m1_nodes.c; returns a Fraction"""
    t = Fraction(t)
    T0 = float(((MJD_E - Fraction("51544.5")) * 86400 + t) / 3155760000)
    g = tdb_minus_tt(T0)
    g = tdb_minus_tt(T0 - g / 3155760000.0)
    return t - Fraction(g) - Fraction("32.184")


def tai_to_utc_mjd(tai):
    """UTC MJD (Fraction) of TAI seconds from MJD 61329.0 TAI, with TAI-UTC from the table"""
    approx = Fraction(MJD_E) + (Fraction(tai) - 37) / 86400
    d = dat(approx)
    return Fraction(MJD_E) + (Fraction(tai) - d) / 86400


def quantize(x, q=Q_TIME):
    """x rounded to the nearest multiple of q (ties to even); a binary64 exactly"""
    k = x / q
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


# ------------------------------------------------------------------ exact values and rotations
def value(h, nb):
    return G.value(h, nb)


def rot_angle(A, B):
    """the angle (rad, float) of the rotation A^T B for two 3x3 matrices given as row-major lists of Fractions
    or floats: theta = asin(|D - D^T|_F / (2 sqrt 2)), D = A^T B, with D's off-diagonal parts in exact arithmetic"""
    D = [[sum(Fraction(A[3 * k + i]) * Fraction(B[3 * k + j]) for k in range(3)) for j in range(3)] for i in range(3)]
    s = sum((D[i][j] - D[j][i]) ** 2 for i in range(3) for j in range(3))
    x = math.sqrt(float(s)) / (2.0 * math.sqrt(2.0))
    return math.asin(min(1.0, x))


MAS = math.pi / (180 * 3600 * 1000)
UAS = MAS / 1000
