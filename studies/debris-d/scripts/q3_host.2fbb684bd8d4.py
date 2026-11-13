"""q3_host.py - DEBRIS-D, Q3's host timings (cft-debris, MIT).

Run inside the sensitive window B0024 (desktop, 2026-11-12 21:15-21:50 -0700).
  A. the load: timesheet.py list desktop, and Windows' CPU load percentage
     sampled before and after every block;
  B. cft-bench.exe (cft-fp256's tool, from DEBRIS-D's build of the archive)
     at fp64, fp128 and fp256: FMA, multiply and add;
  C. tools/opbench.c on the software backend, cft_open(NULL, ...): add, mul,
     fma, div, sqrt, exp, log, pow, sin, cos and atan2 at fp64, fp128 and
     fp256, 1,000 arguments a call;
  D. tools/seqrun.c --time on Q2's images and the degree-8 field's: the
     software executor's lane-steps and lane-instructions a second.
CRITERIA are stated in the log before any data, and asserted.

usage: python -I -B q3_host.py [quick]
  quick: a functional test outside the window (tiny times), whose log is
         marked "quick" and whose timings are not results.
"""
import json
import os
import random
import subprocess
import sys
import time
from fractions import Fraction

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tools"))
import dd  # noqa: E402

import mpmath  # noqa: E402
from mpmath import mp, mpf  # noqa: E402

QUICK = len(sys.argv) > 1 and sys.argv[1] == "quick"
FMTS = {"fp64": (53, 11), "fp128": (113, 15), "fp256": (237, 19)}
OPS = ["add", "mul", "fma", "div", "sqrt", "exp", "log", "pow", "sin", "cos", "atan2"]
NARGS = {"add": 2, "mul": 2, "fma": 3, "div": 2, "sqrt": 1, "exp": 1, "log": 1, "pow": 2,
         "sin": 1, "cos": 1, "atan2": 2}
N = 1000
MIN_SECONDS = 0.05 if QUICK else 0.5
RATIO_MIN = 10.0
BUILD = dd.SCRATCH + "/build"
WORK = dd.SCRATCH + "/work/q3"
BENCH = dd.FP256 + "/host/cft-bench.exe"
TIMESHEET = "C:/Users/logan/source/repos/TimeSheet/timesheet.py"


T_CLOSE = time.mktime(time.strptime("2026-11-12 21:50:00", "%Y-%m-%d %H:%M:%S"))


def load_sample(log, tag):
    if not QUICK and time.time() > T_CLOSE:
        log.check(False, "inside window B0024 at '%s' (it closed at 21:50)" % tag)
    vals = []
    for _ in range(3):
        r = subprocess.run(["wmic", "cpu", "get", "loadpercentage"], capture_output=True, text=True)
        nums = [int(x) for x in r.stdout.split() if x.isdigit()]
        vals.append(nums[0] if nums else -1)
        time.sleep(0.3)
    log.w("load %s: Windows CPU load %% sampled 3 times: %s" % (tag, vals))
    return vals


# ---- an encoder of our own, independent of cft-fp256's golden model ----
def to_bits(fmt, sign, man, exp):
    """bits of sign * man * 2^exp, man > 0 already rounded to <= p bits, normal range"""
    p, eb = FMTS[fmt]
    bl = man.bit_length()
    e_unb = exp + bl - 1
    bias = (1 << (eb - 1)) - 1
    biased = e_unb + bias
    assert 1 <= biased <= (1 << eb) - 2, "outside the normal range"
    frac = (man << (p - bl)) - (1 << (p - 1))
    return (sign << (eb + p - 1)) | (biased << (p - 1)) | frac


def from_bits(fmt, bits):
    p, eb = FMTS[fmt]
    sign = bits >> (eb + p - 1)
    biased = (bits >> (p - 1)) & ((1 << eb) - 1)
    frac = bits & ((1 << (p - 1)) - 1)
    bias = (1 << (eb - 1)) - 1
    if biased == 0:
        v = Fraction(frac) * Fraction(2) ** (1 - bias - (p - 1))
    else:
        assert biased != (1 << eb) - 1, "inf or nan"
        v = Fraction(frac + (1 << (p - 1))) * Fraction(2) ** (biased - bias - (p - 1))
    return -v if sign else v


def exact_bits(fmt, value):
    """bits of an exact rational that the format holds exactly (a binary64 value)"""
    v = Fraction(value)
    if v == 0:
        return 0
    sign = 1 if v < 0 else 0
    v = abs(v)
    num, den = v.numerator, v.denominator
    assert den & (den - 1) == 0
    e = -(den.bit_length() - 1)
    while num % 2 == 0:
        num //= 2
        e += 1
    return to_bits(fmt, sign, num, e)


def rne_bits(fmt, y):
    """y an mpf at high precision: its round-to-nearest-even into fmt"""
    p, _ = FMTS[fmt]
    sign, man, exp, _bc = y._mpf_
    if man == 0:
        return sign << (sum(FMTS[fmt]) - 1)
    bl = man.bit_length()
    if bl > p:
        sh = bl - p
        q = man >> sh
        r = man - (q << sh)
        half = 1 << (sh - 1)
        if r > half or (r == half and (q & 1)):
            q += 1
        if q == (1 << p):
            q >>= 1
            sh += 1
        man, exp = q, exp + sh
    return to_bits(fmt, sign, man, exp)


def mp_of(fmt, bits):
    v = from_bits(fmt, bits)
    return mpf(v.numerator) / mpf(v.denominator)


def gen_args(op, rng):
    def lu(lo, hi):
        return 10 ** rng.uniform(lo, hi)

    def sg():
        return rng.choice((-1.0, 1.0))
    A = []
    for _ in range(N):
        if op in ("add", "mul", "fma", "div"):
            row = [sg() * lu(-1, 7) for _ in range(NARGS[op])]
        elif op == "sqrt":
            row = [lu(-2, 14)]
        elif op == "exp":
            row = [rng.uniform(-20.0, 2.0)]
        elif op == "log":
            row = [lu(-6, 6)]
        elif op == "pow":
            row = [lu(-3, 3), rng.uniform(-4.0, 4.0)]
        elif op in ("sin", "cos"):
            row = [rng.uniform(-10.0, 10.0)]
        elif op == "atan2":
            row = [sg() * lu(-3, 7), sg() * lu(-3, 7)]
        A.append(row)
    return A


def reference(op, fmt, row):
    p, _ = FMTS[fmt]
    with mp.workprec(p + 192):
        a = [mpf(Fraction(v).numerator) / mpf(Fraction(v).denominator) for v in row]
        if op == "add":
            y = a[0] + a[1]
        elif op == "mul":
            y = a[0] * a[1]
        elif op == "fma":
            y = a[0] * a[1] + a[2]
        elif op == "div":
            y = a[0] / a[1]
        elif op == "sqrt":
            y = mpmath.sqrt(a[0])
        elif op == "exp":
            y = mpmath.exp(a[0])
        elif op == "log":
            y = mpmath.log(a[0])
        elif op == "pow":
            y = mpmath.power(a[0], a[1])
        elif op == "sin":
            y = mpmath.sin(a[0])
        elif op == "cos":
            y = mpmath.cos(a[0])
        elif op == "atan2":
            y = mpmath.atan2(a[0], a[1])
        return rne_bits(fmt, y)


def main():
    log = dd.Log(__file__, "q3_host" + ("_quick" if QUICK else ""))
    log.criteria(
        "C1. opbench: every one of the 1,000 results a (function, format) equals mpmath's correctly rounded "
        "value (computed at p + 192 bits, rounded to nearest-even by this script's own encoder), bit for bit",
        "C2. opbench: the timed loop takes at least %.0f times as long as the same loop with the operation "
        "removed (the fold alone)" % RATIO_MIN,
        "C3. seqrun --time: the timed runs take at least %.0f times as long as the fold alone" % RATIO_MIN,
        "C4. seqrun --time: the timing run's segment-1 output equals the first segment's output of the "
        "plain run (the checksum's input is the computation timed)",
        "Load is stated beside every block; booking B0024 (sensitive, desktop, 21:15-21:50 -0700).")
    if QUICK:
        log.w("QUICK functional run: timings here are not results")
    else:
        # B0024: wait for the window to open, and refuse to time after it closes
        t_open = time.mktime(time.strptime("2026-11-12 21:15:05", "%Y-%m-%d %H:%M:%S"))
        while time.time() < t_open:
            time.sleep(1)
        log.w("window B0024 open: %s local" % time.strftime("%H:%M:%S"))
    os.makedirs(WORK, exist_ok=True)
    r = subprocess.run([dd.PY, "-I", "-B", TIMESHEET, "list", "desktop"], capture_output=True, text=True)
    log.w("timesheet.py list desktop (exit %d):" % r.returncode)
    for ln in (r.stdout + r.stderr).strip().splitlines():
        log.w("  | " + ln)
    load_sample(log, "start")
    # ---- B. cft-bench
    for fmt in FMTS:
        load_sample(log, "before cft-bench %s" % fmt)
        r = subprocess.run([BENCH, "-f", fmt, "-t", "0.2" if QUICK else "1"], capture_output=True, text=True)
        log.w("cft-bench -f %s -t %s (exit %d):" % (fmt, "0.2" if QUICK else "1", r.returncode))
        for ln in (r.stdout + r.stderr).strip().splitlines():
            log.w("  | " + ln)
    # ---- C. opbench
    rng = random.Random(20261112)
    results = {}
    for op in OPS:
        args = gen_args(op, rng)
        for fmt in FMTS:
            width = sum(FMTS[fmt]) // 8
            cols = list(zip(*args))
            blob = b"".join(exact_bits(fmt, v).to_bytes(width, "little") for col in cols for v in col)
            ap = os.path.join(WORK, "args-%s-%s.bin" % (op, fmt))
            open(ap, "wb").write(blob)
            op_out = os.path.join(WORK, "out-%s-%s.bin" % (op, fmt))
            ld = load_sample(log, "before %s %s" % (op, fmt))
            rr = subprocess.run([BUILD + "/opbench.exe", op, fmt, ap, str(N), str(MIN_SECONDS), op_out],
                                capture_output=True, text=True)
            if rr.returncode:
                log.w("opbench %s %s FAILED to run: %s" % (op, fmt, rr.stderr.strip()))
                log.check(False, "opbench %s %s ran" % (op, fmt))
                continue
            line = rr.stdout.strip()
            log.w("  " + line)
            kv = line.split()
            d = {kv[i]: kv[i + 1] for i in range(0, len(kv) - 1, 2)}
            ratio = float(d["ratio"])
            log.check(ratio >= RATIO_MIN, "C2 %s %s timed/fold-only ratio %.1f >= %.0f" % (op, fmt, ratio, RATIO_MIN))
            out = open(op_out, "rb").read()
            got = [int.from_bytes(out[i * width:(i + 1) * width], "little") for i in range(N)]
            bad = 0
            first = None
            for i in range(N):
                ref = reference(op, fmt, args[i])
                if got[i] != ref:
                    bad += 1
                    if first is None:
                        first = (i, args[i], hex(got[i]), hex(ref))
            log.check(bad == 0, "C1 %s %s: %d of %d results differ from mpmath's correct rounding%s"
                      % (op, fmt, bad, N, "" if first is None else "; first %r" % (first,)))
            results[(op, fmt)] = (float(d["ns_per_element"]), ld)
    log.w("")
    log.w("TABLE opbench ns per element (software backend, one thread, n = %d a call):" % N)
    log.w("  op      " + "  ".join("%12s" % f for f in FMTS))
    for op in OPS:
        log.w("  %-7s " % op + "  ".join("%12.1f" % results.get((op, f), (float("nan"), 0))[0] for f in FMTS))
    # ---- D. program rates
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    progs = [("q2", "j2-rk4", f) for f in FMTS] + [("q2", "j2dragrot-rk4", f) for f in FMTS] + \
            [("fields", "field8-rk4", f) for f in FMTS] + [("fields", "field20lane-rk4", "fp64")]
    lanes = 8 if QUICK else 32
    reps = 1 if QUICK else 3
    for sub, system, fmt in progs:
        stem = "%s-%s" % (system, fmt)
        img = dd.SCRATCH + "/images/%s/%s.cftp" % (sub, stem)
        if not os.path.exists(img):
            log.w("program %s: no image, skipped" % stem)
            continue
        man = json.load(open(dd.SCRATCH + "/images/%s/%s.manifest.json" % (sub, stem)))
        per_step = man["per_step"]["instructions"]
        steps = man["steps"]
        q2in = dd.SCRATCH + "/work/q2/%s.in.bin" % stem
        width = sum(FMTS[fmt]) // 8
        if os.path.exists(q2in):
            base = open(q2in, "rb").read()
        else:
            # the field: the j2dragrot lanes' states and bc, the field having the same layout
            base = open(dd.SCRATCH + "/work/q2/j2dragrot-rk4-%s.in.bin" % fmt, "rb").read()
        if system == "field20lane-rk4":
            # its lane params are the field's coefficients: each lane gets the graph's defaults
            gj = json.load(open(dd.SCRATCH + "/images/%s/%s.graph.json" % (sub, stem)))
            lane_bits = b"".join(int(e[2], 16).to_bytes(width, "little") for e in gj["lane"])
            pl = len(base) // 8
            nst = 7
            base = b"".join(base[k * pl:k * pl + nst * width] + lane_bits for k in range(8))
        per_lane = len(base) // 8
        blob = b"".join(base[(k % 8) * per_lane:(k % 8 + 1) * per_lane] for k in range(lanes))
        sp = os.path.join(WORK, "prog-%s.in.bin" % stem)
        open(sp, "wb").write(blob)
        L = lanes if not system.startswith("field") else 8
        R = reps if not system.startswith("field") else (1 if QUICK else 2)
        blob = blob[:L * per_lane]
        open(sp, "wb").write(blob)
        ld = load_sample(log, "before program %s" % stem)
        pre = os.path.join(WORK, "prog-%s" % stem)
        depth = int(man["target"]["scratch_depth"])
        extra = ["--depth", str(depth)] if depth != 256 else []
        rr = subprocess.run([BUILD + "/seqrun.exe", img, img.replace(".cftp", ".bank"), sp, str(L), "1", pre,
                             "--time", str(R)] + extra, capture_output=True, text=True)
        if rr.returncode:
            log.check(False, "seqrun --time %s ran: %s" % (stem, rr.stderr.strip()))
            continue
        tl = [ln for ln in rr.stdout.splitlines() if ln.startswith("time ")][0]
        log.w("  %s: %s" % (stem, tl))
        kv = tl.split()
        tr, tf = float(kv[4]), float(kv[6])
        log.check(tr >= RATIO_MIN * tf, "C3 %s timed %.4f s >= %.0f x fold-only %.6f s" % (stem, tr, RATIO_MIN, tf))
        # C4: segment 1's output of this run equals the plain run's first segment, for Q2's 8 lanes
        if os.path.exists(q2in):
            mine = open(pre + ".seg1.bin", "rb").read()
            ref = open(dd.SCRATCH + "/work/q2/%s.seg1.bin" % stem, "rb").read()
            nb = len(ref)
            log.check(mine[:nb] == ref, "C4 %s: the timed program's first 8 lanes equal Q2's segment 1" % stem)
        lane_steps = steps * L * R / tr
        log.w("  RATE %s: lanes %d runs %d steps/run %d: %.1f lane-steps/s, %.3e lane-instructions/s "
              "(%d instructions a step), %.1f ns a lane-instruction; load before %s"
              % (stem, L, R, steps, lane_steps, lane_steps * per_step, per_step, 1e9 / (lane_steps * per_step), ld))
    load_sample(log, "end")
    rc = log.close()
    sys.exit(1 if rc else 0)


if __name__ == "__main__":
    main()
