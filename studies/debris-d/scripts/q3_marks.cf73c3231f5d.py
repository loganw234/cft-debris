"""q3_marks.py - DEBRIS-D, Q3's replay budget (cft-debris, MIT): how often the
compiled routines mark a lane, from the software executor's lane bytes (bit 7).

Part A, the propagator's own arguments: the j2dragrot-rk4 images of Q2 (fp64,
fp128, fp256; 24 steps a segment), 512 lanes of random LEO states (perigee
and apogee altitudes 200 to 1,000 km, every inclination, Cd A / 2m 0.005 to
0.05 m^2/kg), 4 segments (96 steps): marked lane-segments counted. Each
lane-evaluation calls exp, sin and cos once.
Part B, the edges: one-call maps next x = f(x) for f = exp, sin, cos, at the
three formats, 1,024 lanes an argument class:
  exp: typical U[-20, 2]; tiny +-[2^-40, 2^-20]; deep U[-745, -708] (binary64's
       underflow, which the density exp(-(r - r0)/H) reaches above about
       41,000 km);
  sin, cos: typical U[-10, 10]; tiny +-[2^-40, 2^-20]; large U[1e5, 1e6].
CRITERIA (stated before the data, asserted):
  C1 (Part B) every UNMARKED lane's result equals mpmath's correctly rounded
     value (p + 700 bits in version 2, rounded to nearest-even by q3_host.py's
     encoder),
     bit for bit; a marked lane's guess is counted, never required;
  C2 (Part A) every segment runs, and its lane bytes are n bytes;
  C3 positive control for the mark count (version 2): exp's "edge" class,
     x = c 2^-p with c odd below 2^11 and p the format's precision (53, 113,
     237), where 1 + x lands next to a rounding midpoint (LANGUAGE.md's "1 + c
     ulp" exact cases), marks at least one lane at fp64. If it marks none,
     every "0 marks" below is reported as not shown able to see a mark.
     Version 1 (log q3_marks.001.log) used the tiny class +-[2^-40, 2^-20] for
     this control, and it FAILED as stated (0 marks): those arguments are not
     next to an exact case.
Reference interpreter: not run (no lang.run; the stop rule's sizes are not
reached, and none is needed to count marks).

usage: python -I -B q3_marks.py
"""
import math
import os
import random
import subprocess
import sys
from fractions import Fraction

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "tools"))
sys.path.insert(0, HERE)
import dd  # noqa: E402
import q3_host as Q  # noqa: E402  (its encoder and reference rounding; QUICK is False on import)

import mpmath  # noqa: E402
from mpmath import mp, mpf  # noqa: E402

B = dd.SCRATCH + "/build"
IMG = dd.SCRATCH + "/images/marks"
WORK = dd.SCRATCH + "/work/marks"
FMTS = ["fp64", "fp128", "fp256"]
WIDTH = {"fp64": 8, "fp128": 16, "fp256": 32}
LANES_A, SEG = 512, 4


def kepler_states(rng, n):
    mp.dps = 40
    mu = mpf(398600441800000)
    out = []
    for _ in range(n):
        hp = rng.uniform(200e3, 1000e3)
        ha = rng.uniform(hp, 1000e3)
        rp, ra = 6378137 + hp, 6378137 + ha
        a = mpf(rp + ra) / 2
        e = (mpf(ra) - rp) / (mpf(ra) + rp)
        i = mpmath.radians(rng.uniform(0, 180))
        raan, argp, nu = (mpmath.radians(rng.uniform(0, 360)) for _ in range(3))
        p = a * (1 - e * e)
        rr = p / (1 + e * mpmath.cos(nu))
        xo, yo = rr * mpmath.cos(nu), rr * mpmath.sin(nu)
        vxo, vyo = -mpmath.sqrt(mu / p) * mpmath.sin(nu), mpmath.sqrt(mu / p) * (e + mpmath.cos(nu))
        cO, sO, cw, sw, ci, si = (mpmath.cos(raan), mpmath.sin(raan), mpmath.cos(argp), mpmath.sin(argp),
                                  mpmath.cos(i), mpmath.sin(i))
        R = [[cO * cw - sO * sw * ci, -cO * sw - sO * cw * ci], [sO * cw + cO * sw * ci, -sO * sw + cO * cw * ci],
             [sw * si, cw * si]]
        pos = [R[j][0] * xo + R[j][1] * yo for j in range(3)]
        vel = [R[j][0] * vxo + R[j][1] * vyo for j in range(3)]
        out.append([0.0] + [float(v) for v in pos + vel] + [rng.uniform(0.005, 0.05)])
    return out


def refhp(f, fmt, v):
    """the correctly rounded value at p + 700 bits (version 2: the edge class's last term, x^2/2, lies
    below p + 192 bits at fp256, so q3_host's precision is not enough there)"""
    p = Q.FMTS[fmt][0]
    with mp.workprec(p + 700):
        a = mpf(Fraction(v).numerator) / mpf(Fraction(v).denominator)
        y = {"exp": mpmath.exp, "sin": mpmath.sin, "cos": mpmath.cos}[f](a)
        return Q.rne_bits(fmt, y)


def compile_probe(f, fmt, log):
    os.makedirs(IMG, exist_ok=True)
    src = os.path.join(dd.ROOT, "systems", "probe-%s-map.cftl" % f)
    stem = "probe-%s-%s" % (f, fmt)
    r = subprocess.run([dd.PY, "-I", "-B", dd.FP256 + "/python/cftc", src, "--steps", "1", "--format", fmt,
                        "--out", IMG, "--stem", stem], capture_output=True, text=True)
    if r.returncode:
        raise SystemExit("probe compile refused: " + r.stderr)
    log.w("probe image %s: cftp sha256 %s (source sha256 %s)" % (stem, dd.sha256_file(IMG + "/" + stem + ".cftp"),
                                                                 dd.sha256_file(src)))
    return IMG + "/" + stem


def main():
    log = dd.Log(__file__, "q3_marks")
    log.criteria("C1 Part B: every unmarked lane equals mpmath's correct rounding bit for bit; a marked lane's guess "
                 "is counted, not required",
                 "C2 Part A: every segment runs and returns n lane bytes",
                 "C3 (version 2) positive control: exp's edge class x = c 2^-p (c odd < 2^11) marks >= 1 lane at fp64; "
                 "if not, '0 marks' is reported as not shown able to see a mark")
    log.w("version 1 (log 001) FAILED its C3 as stated: the tiny class marked 0 lanes at fp64")
    os.makedirs(WORK, exist_ok=True)
    rng = random.Random(20261112)
    # ---- Part A
    states = kepler_states(rng, LANES_A)
    for fmt in FMTS:
        stem = "j2dragrot-rk4-%s" % fmt
        img = dd.SCRATCH + "/images/q2/" + stem
        w = WIDTH[fmt]
        blob = b"".join(Q.exact_bits(fmt, v).to_bytes(w, "little") for row in states for v in row)
        sp = WORK + "/A-%s.in.bin" % stem
        open(sp, "wb").write(blob)
        pre = WORK + "/A-%s" % stem
        r = subprocess.run([B + "/seqrun.exe", img + ".cftp", img + ".bank", sp, str(LANES_A), str(SEG), pre],
                           capture_output=True, text=True)
        ok = r.returncode == 0
        marks = 0
        for s in range(1, SEG + 1):
            lb = open("%s.seg%d.lanes" % (pre, s), "rb").read() if ok else b""
            ok = ok and len(lb) == LANES_A
            marks += sum(1 for b in lb if b & 0x80)
        log.check(ok, "C2 Part A %s: %d segments of %d lanes ran" % (fmt, SEG, LANES_A))
        nev = LANES_A * 24 * SEG * 4
        log.w("  Part A %s: %d marked lane-segments of %d; %d lane-evaluations (each one exp, one sin, one cos); "
              "seqrun lines: %s" % (fmt, marks, LANES_A * SEG, nev,
                                    " | ".join(ln for ln in r.stdout.splitlines() if ln.startswith("seg"))[:400]))
    # ---- Part B
    classes = {
        "exp": [("typical", lambda: rng.uniform(-20.0, 2.0)),
                ("tiny", lambda: rng.choice((-1, 1)) * 2.0 ** rng.uniform(-40, -20)),
                ("deep", lambda: rng.uniform(-745.0, -708.0))],
        "sin": [("typical", lambda: rng.uniform(-10.0, 10.0)),
                ("tiny", lambda: rng.choice((-1, 1)) * 2.0 ** rng.uniform(-40, -20)),
                ("large", lambda: rng.uniform(1e5, 1e6))],
    }
    classes["cos"] = classes["sin"]
    tiny_marks_fp64 = None
    PREC = {"fp64": 53, "fp128": 113, "fp256": 237}
    for f in ("exp", "sin", "cos"):
        args0 = [(name, [gen() for _ in range(1024)]) for name, gen in classes[f]]
        for fmt in FMTS:
            args = list(args0)
            if f == "exp":
                args.append(("edge", [rng.choice((-1, 1)) * (2 * rng.randrange(1024) + 1) * 2.0 ** (-PREC[fmt])
                                      for _ in range(1024)]))
            base = compile_probe(f, fmt, log)
            w = WIDTH[fmt]
            flat = [v for _, vs in args for v in vs]
            sp = WORK + "/B-%s-%s.in.bin" % (f, fmt)
            open(sp, "wb").write(b"".join(Q.exact_bits(fmt, v).to_bytes(w, "little") for v in flat))
            pre = WORK + "/B-%s-%s" % (f, fmt)
            r = subprocess.run([B + "/seqrun.exe", base + ".cftp", base + ".bank", sp, str(len(flat)), "1", pre],
                               capture_output=True, text=True)
            if r.returncode:
                log.check(False, "probe %s %s ran: %s" % (f, fmt, r.stderr.strip()))
                continue
            out = open(pre + ".seg1.bin", "rb").read()
            lb = open(pre + ".seg1.lanes", "rb").read()
            k = 0
            for name, vs in args:
                nm = nwrong_marked = nbad_unmarked = 0
                for v in vs:
                    got = int.from_bytes(out[k * w:(k + 1) * w], "little")
                    ref = refhp(f, fmt, v) if not (f == "exp" and fmt == "fp64" and v < -708.39) \
                        else None
                    marked = bool(lb[k] & 0x80)
                    if ref is None:
                        # binary64 subnormal results: our encoder handles the normal range only;
                        # compare through mpmath's own rounding to the subnormal grid instead
                        with mp.workprec(300):
                            y = mpmath.exp(mpf(Fraction(v).numerator) / mpf(Fraction(v).denominator))
                        q = int(mpmath.nint(y * mpf(2) ** 1074))
                        rem = y * mpf(2) ** 1074 - int(mpmath.floor(y * mpf(2) ** 1074))
                        fl = int(mpmath.floor(y * mpf(2) ** 1074))
                        q = fl + (1 if (rem > 0.5 or (rem == 0.5 and fl % 2 == 1)) else 0)
                        ref = q   # a binary64 subnormal (or the least normal) encoding is its integer
                    if marked:
                        nm += 1
                        if got != ref:
                            nwrong_marked += 1
                    elif got != ref:
                        nbad_unmarked += 1
                    k += 1
                log.check(nbad_unmarked == 0, "C1 %s %s %s: %d of 1024 unmarked lanes differ from mpmath"
                          % (f, fmt, name, nbad_unmarked))
                log.w("  MARKS %s %s %-7s: %4d of 1024 lanes marked, %d of those guesses wrong" %
                      (f, fmt, name, nm, nwrong_marked))
                if f == "exp" and fmt == "fp64" and name == "edge":
                    tiny_marks_fp64 = nm
    log.check((tiny_marks_fp64 or 0) >= 1, "C3 positive control: exp fp64 edge class marked %s lanes (>= 1)"
              % tiny_marks_fp64)
    rc = log.close()
    sys.exit(1 if rc else 0)


if __name__ == "__main__":
    main()
