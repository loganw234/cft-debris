"""i_analyze.py - cft-debris DEBRIS-I: I3's criteria and measurements, the model gap and I5's statistics, from the
records of the program's driver (tests/i_run.c) and of M1's side (tests/m1i.c), on the desktop or from the box.

cft-debris, MIT licence (see LICENSE at the repository root). Written by DEBRIS-I, 2026-11-23.

I3's criterion (the plan's, fixed before the data): at every segment boundary (every 40 steps), for every object,
    |program at p - M1 at the matching kind| <= T_round(p, n) + T_frame, component by component,
    T_round(p, n) = 64 n 2^-p S, n the steps so far, p = 53, 113 or 237;
    positions S = 7e6 m, T_frame = 1e-3 m; velocities S = 8e3 m/s, T_frame = 1e-6 m/s;
    pairs: binary64 / cft64, binary128 / cft128, binary256 / cft256; binary64 / native64 reported beside.
    t: at every boundary, the program's t equals M1's host stage time, exactly.
The NaN rule: NaN results agree as NaNs; a NaN on one side alone fails.
The measurements (fixed now): the share of each tolerance used (median and largest over objects and boundaries); the
program's binary64 against its binary256 (median and largest position difference at 1, 6 and 24 hours). The model gap:
M1 with the program's forces against M1's full model, position differences at 1, 6 and 24 hours, median and largest,
their radial, along-track and cross-track parts, by perigee band, and one force at a time. No figure of the gap is an
error of either model: it is a difference between two models.
"""
import os
import struct
import sys
from fractions import Fraction

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import i_vals as V  # noqa: E402

P_OF = {"fp64": 53, "fp128": 113, "fp256": 237}
KIND_OF = {"fp64": "cft64", "fp128": "cft128", "fp256": "cft256"}
ESZ_KIND = {"native64": 8, "cft64": 8, "cft128": 16, "cft256": 32, "native32": 4, "cft32": 4}
FMT_OF_KIND = {"native64": "fp64", "cft64": "fp64", "cft128": "fp128", "cft256": "fp256", "native32": "fp32",
               "cft32": "fp32"}
S_POS, S_VEL = Fraction(7 * 10 ** 6), Fraction(8 * 10 ** 3)
TF_POS, TF_VEL = Fraction(1, 1000), Fraction(1, 10 ** 6)


# ------------------------------------------------------------------ exact decoding (standard library)

def decode(fmt, bits):
    """The exact value of an IEEE encoding, or None for a NaN, or +-inf as a float."""
    eb, mb = {"fp32": (8, 23), "fp64": (11, 52), "fp128": (15, 112), "fp256": (19, 236)}[fmt]
    sign = bits >> (eb + mb)
    e = (bits >> mb) & ((1 << eb) - 1)
    m = bits & ((1 << mb) - 1)
    bias = (1 << (eb - 1)) - 1
    if e == (1 << eb) - 1:
        if m:
            return None
        return float("-inf") if sign else float("inf")
    if e == 0:
        v = Fraction(m) / Fraction(2) ** (bias - 1 + mb)
    else:
        v = Fraction((1 << mb) | m) * Fraction(2) ** (e - bias - mb)
    return -v if sign else v


def read_m1_traj(path):
    """m1i traj's lines 'S idx step t x y z vx vy vz': {(idx, step): (t as Fraction, [6 encodings])}, and the kind."""
    out, kind = {}, None
    for raw in open(path, "rb"):
        line = raw.decode("ascii")
        if line.startswith("# m1i kind"):
            kind = line.split()[3]
        if not line.startswith("S "):
            continue
        w = line.split()
        out[(int(w[1]), int(w[2]))] = (Fraction(float.fromhex(w[3])), [int(x, 16) for x in w[4:10]])
    return out, kind


def read_prog_segs(path, lane_idx, nstate, esz, steps_seg=40):
    """i_run's segment file: {(idx, step): [7 encodings: t, x, y, z, vx, vy, vz]} and the marks' lane bytes."""
    segs = V.read_segs(path, len(lane_idx), nstate, esz)
    out, bytes_ = {}, {}
    k = 0
    for (_r, _s, st, lb) in segs:
        k += 1
        for li, idx in enumerate(lane_idx):
            out[(idx, steps_seg * k)] = st[li]
            bytes_[(idx, steps_seg * k)] = lb[li]
    return out, bytes_


# ------------------------------------------------------------------ I3's criterion

def i3_compare(prog, pfmt, m1, kfmt, steps, objects, p_bits):
    """Every boundary and object: (failures, shares list, t mismatches, NaN notes)."""
    fails, shares, tbad, nan_pairs = [], [], [], 0
    for idx in objects:
        for n in steps:
            if (idx, n) not in prog or (idx, n) not in m1:
                fails.append((idx, n, "missing"))
                continue
            ps = prog[(idx, n)]
            t_m1, ms = m1[(idx, n)]
            if decode(pfmt, ps[0]) != t_m1:
                tbad.append((idx, n))
            for c in range(6):
                pv, mv = decode(pfmt, ps[1 + c]), decode(kfmt, ms[c])
                if pv is None and mv is None:
                    nan_pairs += 1
                    continue
                S, TF = (S_POS, TF_POS) if c < 3 else (S_VEL, TF_VEL)
                tol = 64 * n * S / Fraction(2) ** p_bits + TF
                if pv is None or mv is None or isinstance(pv, float) or isinstance(mv, float):
                    fails.append((idx, n, "nan-or-inf c%d" % c))
                    shares.append(float("inf"))
                    continue
                d = abs(pv - mv)
                shares.append(float(d / tol))
                if d > tol:
                    fails.append((idx, n, "c%d share %.3g" % (c, float(d / tol))))
    return fails, shares, tbad, nan_pairs


def pos_diff(a, afmt, b, bfmt):
    """|position(a) - position(b)| as a float (m), exact differences first."""
    import math
    s = 0.0
    for c in range(3):
        x, y = decode(afmt, a[c]), decode(bfmt, b[c])
        if x is None or y is None or isinstance(x, float) or isinstance(y, float):
            return float("nan")
        s += float(x - y) ** 2
    return math.sqrt(s)


def rtn(state_ref, fmt_ref, state_other, fmt_other):
    """The position difference (other - ref) in the reference's radial, along-track and cross-track directions."""
    import math
    r = [float(decode(fmt_ref, state_ref[c])) for c in range(3)]
    v = [float(decode(fmt_ref, state_ref[3 + c])) for c in range(3)]
    d = [float(decode(fmt_other, state_other[c]) - decode(fmt_ref, state_ref[c])) for c in range(3)]

    def unit(a):
        n = math.sqrt(sum(x * x for x in a))
        return [x / n for x in a]

    def cross(a, b):
        return [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]]
    R = unit(r)
    C = unit(cross(r, v))
    A = cross(C, R)
    return tuple(sum(x * y for x, y in zip(d, u)) for u in (R, A, C))


def stats(v):
    s = sorted(x for x in v if x == x)
    if not s:
        return (float("nan"), float("nan"), 0)
    n = len(s)
    med = s[n // 2] if n % 2 else 0.5 * (s[n // 2 - 1] + s[n // 2])
    return med, s[-1], n


if __name__ == "__main__":
    print(__doc__)
