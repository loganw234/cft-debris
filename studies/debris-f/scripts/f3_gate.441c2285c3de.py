# f3_gate.py - cft-debris M1 (DEBRIS-F), gate F3: the Earth's orientation against Orekit 13.1.9 (IERS 2010,
# simple EOP), and the node table's interpolation against the node routine.
# cft-debris, MIT licence (see LICENSE at the repository root). Written by DEBRIS-F, 2026-11-16.
#
#   python -I -B tests/f3_gate.py [table]
#
# Ours: (a) and (c) tests/m1nodes.c "direct" (src/m1_nodes.c at binary256, no table); (b) tests/m1f.c "frames" at
# native64, the table interpolated as M1 uses it; (c) the table interpolated at u = 1/2 in exact arithmetic.
# Orekit's: tests/f_orekit.js "frames", the GCRF <- ITRF transform of getITRF(IERS_2010, true).
import math
import os
import random
import sys
from fractions import Fraction

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import f_lib as F  # noqa: E402

CRITERIA = """
The angle between two GCRS <- ITRS rotations A and B is asin(|D - D^T|_F / (2 sqrt 2)), D = A^T B, in exact
arithmetic from their elements (tests/f_lib.py rot_angle).
(a) THE MODEL: at each of the Earth orientation file's dates MJD 61270 to 61430 at 0h UTC (161 dates; the Phase 0
    ruling: no epoch at or past the rows with blank dX, dY from MJD 61438), the node routine at binary256 with no
    table against Orekit: every angle <= 50 uas (the brief's bound, used as the tolerance).
(b) THE TABLE AS M1 USES IT: at 1,000 TDB times uniform over the window's table (random.Random(0xF3B), multiples of
    2^-21 s inside [0, 34 days)), native64 interpolating the table against Orekit: every angle <= 1 mas. Basis: the
    two interpolation schemes - our 4-point Lagrange of the daily rows against Orekit's (the same scheme for UT1-UTC,
    F2: 5.6e-17 s; between rows Orekit's pole differs from ours by up to about 12 uas, a development check at three
    epochs that are not this gate's), Orekit's own interpolation of its precession-nutation, our table's interpolation
    (part (c)'s bound, under a uas) and binary64 rounding (1e-16 rad).
(c) THE TABLE'S INTERPOLATION: at the midpoints of 200 fine intervals (random.Random(0xF3C)) of the table, its
    6-point Lagrange interpolant in exact arithmetic from the binary256 nodes against the node routine's direct
    evaluation there: every angle <= B_theta and every |Omega_table - Omega_direct| <= B_Omega, both computed below
    before any data from the IERS tables, the EOP rows and the scheme (coarse 8-point Lagrange at H = 16384 s, fine
    6-point at h = 256 s): the Lagrange remainder with derivative bounds from the series' amplitudes and frequencies,
    the EOP interpolants' slope breaks at 0h UTC (their fourth differences), and the Lebesgue constant. Reported too:
    native64's interpolation against the direct value (no criterion).
NEGATIVE CONTROL C1: the node routine with dX planted +1 mas (4.84813681e-9 rad, twenty times (a)'s tolerance) must
    FAIL (a), with its largest angle within 0.9 to 1.1 mas (expected: the CIP moved by 1 mas, so about 1 mas, plus
    or minus (a)'s own differences of at most 50 uas).
NaN: none of our values may be NaN.
"""

TABLE = sys.argv[1] if len(sys.argv) > 1 else F.DATA + "/tables/frame_main.bin"
H_FINE = 256.0
H_COARSE = 16384.0
OMEGA_MAX = 7.2921151467064e-5 * (1 + 1e-7)
JC = 3155760000.0
AS = math.pi / 648000.0
UASR = AS / 1e6


def lag_coef(nodes):
    out = []
    for j in nodes:
        d = Fraction(1)
        for i in nodes:
            if i != j:
                d *= (j - i)
        out.append(1 / d)
    return out


def pmax(nodes, ngrid=20001):
    best = 0.0
    for q in range(ngrid):
        u = q / (ngrid - 1)
        p = 1.0
        for i in nodes:
            p *= (u - i)
        best = max(best, abs(p))
    return best * 1.001


def lebesgue(nodes, ngrid=20001):
    c = lag_coef(nodes)
    best = 0.0
    for q in range(ngrid):
        u = q / (ngrid - 1)
        s = 0.0
        for j, cj in zip(nodes, c):
            p = float(cj)
            for i in nodes:
                if i != j:
                    p *= (u - i)
            s += abs(p)
        best = max(best, s)
    return best * 1.001


def read_series(path):
    terms = []
    j = None
    for ln in open(path, "r", encoding="ascii", errors="replace"):
        t = ln.split()
        if ln.strip().startswith("j = "):
            j = int(ln.split("=")[1].split()[0])
            continue
        if j is None or len(t) != 17:
            continue
        try:
            m = [int(x) for x in t[3:]]
            terms.append((j, float(t[1]), float(t[2]), m))
        except ValueError:
            pass
    return terms


def bounds(log):
    """the computed bounds of (c), before any data"""
    T = 0.28
    # fundamental argument rates (rad/s) and their uncertainty over |t| <= 0.28 from the higher powers
    dl = [(1717915923.2178, 31.8792, 0.051635, -0.00024470), (129596581.0481, -0.5532, 0.000136, -0.00001149),
          (1739527262.8478, -12.7512, -0.001037, 0.00000417), (1602961601.2090, -6.3706, 0.006593, -0.00003169),
          (-6962890.5431, 7.4722, 0.007702, -0.00005939)]
    rates, drates = [], []
    for c1, c2, c3, c4 in dl:
        rates.append(c1 * AS / JC)
        drates.append((2 * abs(c2) * T + 3 * abs(c3) * T * T + 4 * abs(c4) * T ** 3) * AS / JC)
    for c1 in (2608.7903141574, 1021.3285546211, 628.3075849991, 334.0612426700, 52.9690962641, 21.3299104960,
               7.4781598567, 3.8133035638):
        rates.append(c1 / JC)
        drates.append(0.0)
    rates.append(0.02438175 / JC)
    drates.append(2 * 0.00000538691 * T / JC)
    bc = {}
    for name, f in (("X", "tab5.2a.txt"), ("Y", "tab5.2b.txt"), ("S", "tab5.2d.txt")):
        f8 = 0.0
        for j, a_s, a_c, m in read_series(F.DOWNLOADS + f + "/" + f):
            w = abs(sum(mi * r for mi, r in zip(m, rates))) + sum(abs(mi) * d for mi, d in zip(m, drates))
            amp = (abs(a_s) + abs(a_c)) * UASR
            s = 0.0
            for k in range(0, min(8, j) + 1):
                s += math.comb(8, k) * (math.factorial(j) / math.factorial(j - k)) * T ** (j - k) * (1.0 / JC) ** k * w ** (8 - k)
            f8 += amp * s
        bc[name] = pmax(range(-3, 5)) * H_COARSE ** 8 / math.factorial(8) * f8
    e_c = 2.0 * (bc["X"] + bc["Y"] + bc["S"])
    e_f = pmax(range(-2, 4)) * H_FINE ** 6 / math.factorial(6) * 2.0 * OMEGA_MAX ** 6 * (1 + 1e-5)
    lam = lebesgue(range(-2, 4))
    # the EOP interpolants' breaks at the rows inside the window (MJD 61328..61364): the left and right cubics
    # differ by c (t-d+1)(t-d)(t-d-1), c = (4th difference)/6 per day^3
    rows = {}
    for ln in open(F.DOWNLOADS + "finals2000A.daily/finals2000A.daily", "r", encoding="ascii"):
        if len(ln) < 20 or not ln[7:15].strip():
            continue
        mjd = int(round(float(ln[7:15])))
        def fld(a, b):
            v = ln[a - 1:b].strip() if len(ln) >= a else ""
            return v
        vals = []
        for (a1, b1), (a2, b2), unit in (((19, 27), (135, 144), AS), ((38, 46), (145, 154), AS), ((59, 68), (155, 165), 1.0),
                                          ((98, 106), (166, 175), AS / 1000), ((117, 125), (176, 185), AS / 1000)):
            v = fld(a2, b2) or fld(a1, b1) or "0"
            vals.append(Fraction(v) * Fraction(unit))
        rows[mjd] = vals
    w = 5 * H_FINE / 86400.0
    sens = [2.0, 2.0, 2.0 * OMEGA_MAX, 2.0, 2.0]
    gk, sk = 0.0, [0.0] * 5
    for d in range(61328, 61365):
        for q in range(5):
            d4 = rows[d + 2][q] - 4 * rows[d + 1][q] + 6 * rows[d][q] - 4 * rows[d - 1][q] + rows[d - 2][q]
            g = abs(float(d4)) / 6.0 * w * (1 + w * w)
            gk = max(gk, sens[q] * g)
            sk[q] = max(sk[q], abs(float(d4)) / 6.0 / 86400.0)
    e_k = (1 + lam) * 5 * gk
    e = e_c + e_f + e_k + 1e-60
    btheta = 2.13 * e
    bomega = (1 + lam) * (OMEGA_MAX * sk[2] + 2 * (sk[0] + sk[1] + sk[3] + sk[4])) * 1.01 + 1e-20
    log.w("# (c) bounds: coarse X %.3e, Y %.3e, S %.3e rad; fine smooth %.3e; EOP breaks %.3e (Lebesgue %.4f); element bound %.3e rad"
          % (bc["X"], bc["Y"], bc["S"], e_f, e_k, lam, e))
    log.w("# (c) B_theta = 2.13 x element bound = %.4e rad = %.4f uas; B_Omega = %.3e rad/s" % (btheta, btheta / F.UAS, bomega))
    return btheta, bomega


def read_table(path):
    raw = open(path, "rb").read()
    i = raw.index(b"END\n")
    head = raw[:i].decode()
    meta = {}
    for ln in head.split("\n"):
        p = ln.split(None, 1)
        if len(p) == 2:
            meta[p[0]] = p[1]
    return float.fromhex(meta["t0"]), float.fromhex(meta["h"]), int(meta["nk"]), raw[i + 4:]


def node_vals(payload, k):
    out = []
    for c in range(12):
        b = payload[(k * 12 + c) * 32:(k * 12 + c + 1) * 32]
        out.append(F.value(b[::-1].hex(), 256))
    return out


def ours_direct(exe, ts, tag, W, log, extra=()):
    with open(W + "/%s_t.txt" % tag, "w", newline="\n") as f:
        for t in ts:
            f.write(float.hex(t) + "\n")
    F.run([exe, "direct", W + "/%s_t.txt" % tag, W + "/%s_direct.txt" % tag] + list(extra), log, cpu_label="f3_%s" % tag)
    return [ln.split() for ln in open(W + "/%s_direct.txt" % tag) if not ln.startswith("#")]


def orekit_frames(ts, tag, W, log, exe):
    F.run([exe, "times", W + "/%s_t.txt" % tag, W + "/%s_times.txt" % tag], log)
    tai = [float.fromhex(ln.split()[1]) for ln in open(W + "/%s_times.txt" % tag) if not ln.startswith("#")]
    with open(W + "/%s_tai.txt" % tag, "w", newline="\n") as f:
        for x in tai:
            f.write(repr(x) + "\n")
    F.orekit(os.path.join(F.REPO, "tests", "f_orekit.js"), ["frames", F.DATA + "/orekit", W + "/%s_tai.txt" % tag, W + "/%s_ore.txt" % tag],
             log, cpu_label="f3_%s_orekit" % tag)
    for h in open(W + "/%s_ore.txt" % tag):
        if h.startswith("# EOP"):
            log.w("# orekit: " + h.strip())
    return [ln.split() for ln in open(W + "/%s_ore.txt" % tag) if not ln.startswith("#")]


def main():
    log = F.Log("f3_gate", os.path.abspath(__file__), CRITERIA, extra_files=[os.path.join(F.REPO, "tests", "f_orekit.js")])
    nodes_exe = F.BUILD + "/m1nodes.exe"
    m1f = F.BUILD + "/m1f_O2.exe"
    log.w("# m1nodes.exe sha256 %s; m1f_O2.exe sha256 %s; table %s sha256 %s" % (F.sha256(nodes_exe), F.sha256(m1f), TABLE, F.sha256(TABLE)))
    btheta, bomega = bounds(log)
    W = F.WORK + "/f3"
    os.makedirs(W, exist_ok=True)
    # (a)
    ts = [float(F.utc_to_tdb(d, 0)) for d in range(61270, 61431)]
    log.check(len(ts) == 161, "(a) 161 dates, MJD 61270..61430")
    ou = ours_direct(nodes_exe, ts, "a", W, log)
    oo = orekit_frames(ts, "a", W, log, nodes_exe)
    log.check(len(ou) == len(oo) == 161, "(a) both sides gave 161 rotations")
    angs, nan = [], 0
    for a, b in zip(ou, oo):
        Mu = [F.value(x, 256) for x in a[1:10]]
        nan += sum(1 for x in Mu if x is None)
        Mo = [Fraction(float.fromhex(x)) for x in b[1:10]]
        angs.append(F.rot_angle(Mu, Mo))
    ia = max(range(len(angs)), key=lambda i: angs[i])
    log.w("# (a) angle: max %.3f uas (MJD %d), median %.3f uas, min %.3f uas" % (angs[ia] / F.UAS, 61270 + ia,
          sorted(angs)[len(angs) // 2] / F.UAS, min(angs) / F.UAS))
    log.check(nan == 0, "(a) no NaN")
    log.check(max(angs) <= 50 * F.UAS, "(a) every angle <= 50 uas (max %.3f uas)" % (max(angs) / F.UAS))
    # C1
    oc = ours_direct(nodes_exe, ts, "a_plant", W, log, ["--plant-dx", repr(4.84813681109536e-9)])
    angc = []
    for a, b in zip(oc, oo):
        angc.append(F.rot_angle([F.value(x, 256) for x in a[1:10]], [Fraction(float.fromhex(x)) for x in b[1:10]]))
    log.w("# C1 (dX + 1 mas): angle max %.4f mas, min %.4f mas" % (max(angc) / F.MAS, min(angc) / F.MAS))
    log.check(max(angc) > 50 * F.UAS and 0.9 * F.MAS <= max(angc) <= 1.1 * F.MAS,
              "C1 FAILS (a) as specified: largest angle %.4f mas, within 0.9 to 1.1 mas" % (max(angc) / F.MAS))
    # (b)
    rng = random.Random(0xF3B)
    tb = [math.floor(rng.random() * 34 * 86400 * 2097152) / 2097152 for _ in range(1000)]
    with open(W + "/b_t.txt", "w", newline="\n") as f:
        for t in tb:
            f.write(float.hex(t) + "\n")
    F.run([m1f, "frames", "native64", TABLE, W + "/b_t.txt", W + "/b_ours.txt"], log, cpu_label="f3_b_ours")
    ub = [ln.split() for ln in open(W + "/b_ours.txt") if not ln.startswith("#")]
    ob = orekit_frames(tb, "b", W, log, nodes_exe)
    log.check(len(ub) == len(ob) == 1000, "(b) both sides gave 1000 rotations")
    angb, nan = [], 0
    for a, b in zip(ub, ob):
        Mu = [F.value(x, 64) for x in a[1:10]]
        nan += sum(1 for x in Mu if x is None)
        angb.append(F.rot_angle(Mu, [Fraction(float.fromhex(x)) for x in b[1:10]]))
    log.w("# (b) angle: max %.3f uas, median %.3f uas" % (max(angb) / F.UAS, sorted(angb)[500] / F.UAS))
    log.check(nan == 0, "(b) no NaN")
    log.check(max(angb) <= 1000 * F.UAS, "(b) every angle <= 1 mas (max %.3f uas)" % (max(angb) / F.UAS))
    # (c)
    t0, h, nk, payload = read_table(TABLE)
    log.check(h == H_FINE, "(c) the table's h is %g s, as the bound assumes" % h)
    rng = random.Random(0xF3C)
    ks = []
    while len(ks) < 200:
        k = rng.randrange(0, nk)
        t = t0 + (k + 0.5) * h
        if 2 <= k and k + 3 < nk and 0 <= t < 34 * 86400:
            ks.append(k)
    tc = [t0 + (k + 0.5) * h for k in ks]
    uc = ours_direct(nodes_exe, tc, "c", W, log)
    with open(W + "/c_t64.txt", "w", newline="\n") as f:
        for t in tc:
            f.write(float.hex(t) + "\n")
    F.run([m1f, "frames", "native64", TABLE, W + "/c_t64.txt", W + "/c_n64.txt"], log, cpu_label="f3_c_n64")
    n64 = [ln.split() for ln in open(W + "/c_n64.txt") if not ln.startswith("#")]
    w = lag_coef(range(-2, 4))
    wt = []
    for j, cj in zip(range(-2, 4), w):
        p = cj
        for i in range(-2, 4):
            if i != j:
                p *= (Fraction(1, 2) - i)
        wt.append(p)
    angc2, dom, ang64 = [], [], []
    for k, a, b in zip(ks, uc, n64):
        vals = [node_vals(payload, k - 2 + i) for i in range(6)]
        interp = [sum(wt[i] * vals[i][c] for i in range(6)) for c in range(12)]
        direct = [F.value(x, 256) for x in a[1:13]]
        angc2.append(F.rot_angle(interp[:9], direct[:9]))
        dom.append(math.sqrt(sum(float(interp[9 + i] - direct[9 + i]) ** 2 for i in range(3))))
        ang64.append(F.rot_angle([F.value(x, 64) for x in b[1:10]], direct[:9]))
    log.w("# (c) table (exact interpolation) against direct: angle max %.4e rad (%.6f uas), median %.4e rad; |dOmega| max %.3e rad/s"
          % (max(angc2), max(angc2) / F.UAS, sorted(angc2)[100], max(dom)))
    log.w("# (c) REPORTED: native64's interpolation against direct: angle max %.4e rad (%.4f uas)" % (max(ang64), max(ang64) / F.UAS))
    log.check(max(angc2) <= btheta, "(c) every angle <= B_theta = %.4e rad (max %.4e)" % (btheta, max(angc2)))
    log.check(max(dom) <= bomega, "(c) every |dOmega| <= B_Omega = %.3e rad/s (max %.3e)" % (bomega, max(dom)))
    return log.close()


if __name__ == "__main__":
    sys.exit(main())
