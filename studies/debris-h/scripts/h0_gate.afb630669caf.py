# h0_gate.py - cft-debris M1 (DEBRIS-H), gate H0: DEBRIS-F's F3 checks re-run on H0's frame table, at its own dates.
# cft-debris, MIT licence (see LICENSE at the repository root). Written by DEBRIS-H, 2026-11-18: a copy of DEBRIS-F's
# tests/f3_gate.py (cft-debris's own, MIT), repointed. What changed, and nothing else:
#   - every path comes from the command line, and logs go where it says (DEBRIS-F's f_lib.py hard-coded them);
#   - its library is tests/h_lib.py (the same functions, copied from f_lib.py and gatelib.py) and its CPU count is
#     h_lib.CpuAccount (DEBRIS-D's cpurun.py, in process);
#   - the window is H0's, TDB 2026-10-17 00:00 to 2026-12-28 00:00 (t from 86,400 to 6,307,200 s), so (a) takes the
#     Earth orientation file's dates MJD 61330 to 61402, (b) and (c) draw their times inside that window, and (c)'s
#     slope-break term reads the rows MJD 61329 to 61403; the tolerances, seeds, bounds' method and control are F3's.
#
#   python -I -B tests/h0_gate.py <table> --build <dir: m1nodes.exe, m1f_O2.exe> --downloads <dir/> --java <java>
#       --jars <dir> --orekit-data <dir> --work <dir> --logs <dir> [--keep <dir>] [--cpu <tsv>]
#
# Ours: (a) and (c) tests/m1nodes.c "direct" (src/m1_nodes.c at binary256, no table); (b) tests/m1f.c "frames" at
# native64, the table interpolated as M1 uses it; (c) the table interpolated at u = 1/2 in exact arithmetic.
# Orekit's: tests/f_orekit.js "frames", the GCRF <- ITRF transform of getITRF(IERS_2010, true).
import argparse
import math
import os
import random
import sys
from fractions import Fraction

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import h_lib as H  # noqa: E402

W0, W1 = 86400.0, 73 * 86400.0          # the window, TDB s from JD 2461329.5
MJD_A0, MJD_A1 = 61330, 61402           # (a)'s file dates inside it
MJD_B0, MJD_B1 = 61329, 61403           # (c)'s slope-break rows: the window's dates and one either side

CRITERIA = """
H0 is DEBRIS-F's F3 on H0's table (TDB 2026-10-17 00:00 to 2026-12-28 00:00), F3's tolerances and control unchanged.
The angle between two GCRS <- ITRS rotations A and B is asin(|D - D^T|_F / (2 sqrt 2)), D = A^T B, in exact
arithmetic from their elements (h_lib.rot_angle, F3's).
(a) THE MODEL: at each of the Earth orientation file's dates MJD 61330 to 61402 at 0h UTC (73 dates; all before the
    rows with blank dX, dY from MJD 61438), the node routine at binary256 with no table against Orekit: every angle
    <= 50 uas (F3's tolerance).
(b) THE TABLE AS M1 USES IT: at 1,000 TDB times uniform over the window (random.Random(0xF3B), multiples of 2^-21 s
    inside [86,400 s, 6,307,200 s)), native64 interpolating the table against Orekit: every angle <= 1 mas (F3's
    tolerance and basis: the two interpolation schemes, Orekit's own interpolation, our table's interpolation and
    binary64 rounding).
(c) THE TABLE'S INTERPOLATION: at the midpoints of 200 fine intervals (random.Random(0xF3C)) of the table inside the
    window, its 6-point Lagrange interpolant in exact arithmetic from the binary256 nodes against the node routine's
    direct evaluation there: every angle <= B_theta and every |Omega_table - Omega_direct| <= B_Omega, both computed
    below before any data, by F3's method, from the IERS tables, the EOP rows of MJD 61329 to 61403 and the scheme.
    Reported too: native64's interpolation against the direct value (no criterion).
NEGATIVE CONTROL C1 (F3's): the node routine with dX planted +1 mas (4.84813681e-9 rad, twenty times (a)'s tolerance)
    must FAIL (a), with its largest angle within 0.9 to 1.1 mas.
NaN: none of our values may be NaN.
"""

H_FINE = 256.0
H_COARSE = 16384.0
OMEGA_MAX = 7.2921151467064e-5 * (1 + 1e-7)
JC = 3155760000.0
AS = math.pi / 648000.0
UASR = AS / 1e6
MAS = math.pi / (180 * 3600 * 1000)
UAS = MAS / 1000


def rot_angle(A, B):
    """F3's: the angle (rad) of the rotation A^T B, D's off-diagonal parts in exact arithmetic"""
    D = [[sum(Fraction(A[3 * k + i]) * Fraction(B[3 * k + j]) for k in range(3)) for j in range(3)] for i in range(3)]
    s = sum((D[i][j] - D[j][i]) ** 2 for i in range(3) for j in range(3))
    x = math.sqrt(float(s)) / (2.0 * math.sqrt(2.0))
    return math.asin(min(1.0, x))


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


def bounds(log, dl):
    """the computed bounds of (c), before any data (F3's code; the EOP rows are the new window's)"""
    T = 0.28
    dl_ = [(1717915923.2178, 31.8792, 0.051635, -0.00024470), (129596581.0481, -0.5532, 0.000136, -0.00001149),
           (1739527262.8478, -12.7512, -0.001037, 0.00000417), (1602961601.2090, -6.3706, 0.006593, -0.00003169),
           (-6962890.5431, 7.4722, 0.007702, -0.00005939)]
    rates, drates = [], []
    for c1, c2, c3, c4 in dl_:
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
        for j, a_s, a_c, m in read_series(dl + f + "/" + f):
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
    rows = {}
    for ln in open(dl + "finals2000A.daily/finals2000A.daily", "r", encoding="ascii"):
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
    for d in range(MJD_B0, MJD_B1 + 1):
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
    log.w("# (c) B_theta = 2.13 x element bound = %.4e rad = %.4f uas; B_Omega = %.3e rad/s" % (btheta, btheta / UAS, bomega))
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
        out.append(H.value(b[::-1].hex(), 256))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("table")
    for a in ("--build", "--downloads", "--java", "--jars", "--orekit-data", "--work", "--logs"):
        ap.add_argument(a, required=True)
    ap.add_argument("--keep")
    ap.add_argument("--cpu")
    a = ap.parse_args()
    here = os.path.dirname(os.path.abspath(__file__))
    cpu = H.CpuAccount("h0_gate", a.cpu)
    js = os.path.join(here, "f_orekit.js")
    log = H.Log("h0_gate", a.logs, os.path.abspath(__file__), CRITERIA, extra=[js], keep_dir=a.keep)
    jars = sorted(os.path.join(a.jars, j) for j in os.listdir(a.jars) if j.endswith(".jar"))
    H.load_leaps(os.path.join(a.downloads, "tai-utc.dat", "tai-utc.dat"))
    env = dict(os.environ)
    env["M1_DOWNLOADS"] = a.downloads
    nodes_exe = os.path.join(a.build, "m1nodes.exe")
    m1f = os.path.join(a.build, "m1f_O2.exe")
    for p in (nodes_exe, m1f, a.table):
        log.w("# %s sha256 %s" % (os.path.basename(p), H.sha256(p)))
    for j in jars:
        log.w("# jar %s sha256 %s" % (os.path.basename(j), H.sha256(j)))
    for f in os.listdir(a.orekit_data):
        log.w("# orekit data %s sha256 %s" % (f, H.sha256(os.path.join(a.orekit_data, f))))
    W = a.work
    os.makedirs(W, exist_ok=True)

    def ours_direct(ts, tag, extra=()):
        with open(W + "/%s_t.txt" % tag, "w", newline="\n") as f:
            for t in ts:
                f.write(float.hex(t) + "\n")
        H.run([nodes_exe, "direct", W + "/%s_t.txt" % tag, W + "/%s_direct.txt" % tag] + list(extra), log, env=env)
        return [ln.split() for ln in open(W + "/%s_direct.txt" % tag) if not ln.startswith("#")]

    def orekit_frames(ts, tag):
        H.run([nodes_exe, "times", W + "/%s_t.txt" % tag, W + "/%s_times.txt" % tag], log, env=env)
        tai = [float.fromhex(ln.split()[1]) for ln in open(W + "/%s_times.txt" % tag) if not ln.startswith("#")]
        with open(W + "/%s_tai.txt" % tag, "w", newline="\n") as f:
            for x in tai:
                f.write(repr(x) + "\n")
        H.run(H.java_argv(a.java, jars, js, ["frames", a.orekit_data, W + "/%s_tai.txt" % tag, W + "/%s_ore.txt" % tag]), log)
        for h in open(W + "/%s_ore.txt" % tag):
            if h.startswith("# EOP"):
                log.w("# orekit: " + h.strip())
        return [ln.split() for ln in open(W + "/%s_ore.txt" % tag) if not ln.startswith("#")]

    btheta, bomega = bounds(log, a.downloads)
    t0, h, nk, payload = read_table(a.table)
    log.w("# the table: t0 %.1f s, h %g s, nk %d, last node %.1f s; the window [%.0f, %.0f) s" % (t0, h, nk, t0 + (nk - 1) * h, W0, W1))
    log.check(t0 + 2 * h <= W0 and W1 + 3 * h <= t0 + (nk - 1) * h, "the table's nodes cover the window with the 6-point stencil")
    # (a)
    ts = [float(H.utc_to_tdb(d, 0)) for d in range(MJD_A0, MJD_A1 + 1)]
    log.check(len(ts) == 73, "(a) 73 dates, MJD 61330..61402")
    ou = ours_direct(ts, "a")
    oo = orekit_frames(ts, "a")
    log.check(len(ou) == len(oo) == 73, "(a) both sides gave 73 rotations")
    angs, nan = [], 0
    for x, y in zip(ou, oo):
        Mu = [H.value(v, 256) for v in x[1:10]]
        nan += sum(1 for v in Mu if v is None)
        Mo = [Fraction(float.fromhex(v)) for v in y[1:10]]
        angs.append(rot_angle(Mu, Mo))
    ia = max(range(len(angs)), key=lambda i: angs[i])
    log.w("# (a) angle: max %.3f uas (MJD %d), median %.3f uas, min %.3f uas" % (angs[ia] / UAS, MJD_A0 + ia,
          sorted(angs)[len(angs) // 2] / UAS, min(angs) / UAS))
    log.check(nan == 0, "(a) no NaN")
    log.check(max(angs) <= 50 * UAS, "(a) every angle <= 50 uas (max %.3f uas)" % (max(angs) / UAS))
    # C1
    oc = ours_direct(ts, "a_plant", ["--plant-dx", repr(4.84813681109536e-9)])
    angc = []
    for x, y in zip(oc, oo):
        angc.append(rot_angle([H.value(v, 256) for v in x[1:10]], [Fraction(float.fromhex(v)) for v in y[1:10]]))
    log.w("# C1 (dX + 1 mas): angle max %.4f mas, min %.4f mas" % (max(angc) / MAS, min(angc) / MAS))
    log.check(max(angc) > 50 * UAS and 0.9 * MAS <= max(angc) <= 1.1 * MAS,
              "C1 FAILS (a) as specified: largest angle %.4f mas, within 0.9 to 1.1 mas" % (max(angc) / MAS))
    # (b)
    rng = random.Random(0xF3B)
    tb = [W0 + math.floor(rng.random() * (W1 - W0) * 2097152) / 2097152 for _ in range(1000)]
    log.check(all(W0 <= t < W1 for t in tb), "(b) 1,000 times inside the window")
    with open(W + "/b_t.txt", "w", newline="\n") as f:
        for t in tb:
            f.write(float.hex(t) + "\n")
    H.run([m1f, "frames", "native64", a.table, W + "/b_t.txt", W + "/b_ours.txt"], log, env=env)
    ub = [ln.split() for ln in open(W + "/b_ours.txt") if not ln.startswith("#")]
    ob = orekit_frames(tb, "b")
    log.check(len(ub) == len(ob) == 1000, "(b) both sides gave 1000 rotations")
    angb, nan = [], 0
    for x, y in zip(ub, ob):
        Mu = [H.value(v, 64) for v in x[1:10]]
        nan += sum(1 for v in Mu if v is None)
        angb.append(rot_angle(Mu, [Fraction(float.fromhex(v)) for v in y[1:10]]))
    log.w("# (b) angle: max %.3f uas, median %.3f uas" % (max(angb) / UAS, sorted(angb)[500] / UAS))
    log.check(nan == 0, "(b) no NaN")
    log.check(max(angb) <= 1000 * UAS, "(b) every angle <= 1 mas (max %.3f uas)" % (max(angb) / UAS))
    # (c)
    log.check(h == H_FINE, "(c) the table's h is %g s, as the bound assumes" % h)
    rng = random.Random(0xF3C)
    ks = []
    while len(ks) < 200:
        k = rng.randrange(0, nk)
        t = t0 + (k + 0.5) * h
        if 2 <= k and k + 3 < nk and W0 <= t < W1:
            ks.append(k)
    tc = [t0 + (k + 0.5) * h for k in ks]
    uc = ours_direct(tc, "c")
    with open(W + "/c_t64.txt", "w", newline="\n") as f:
        for t in tc:
            f.write(float.hex(t) + "\n")
    H.run([m1f, "frames", "native64", a.table, W + "/c_t64.txt", W + "/c_n64.txt"], log, env=env)
    n64 = [ln.split() for ln in open(W + "/c_n64.txt") if not ln.startswith("#")]
    wl = lag_coef(range(-2, 4))
    wt = []
    for j, cj in zip(range(-2, 4), wl):
        p = cj
        for i in range(-2, 4):
            if i != j:
                p *= (Fraction(1, 2) - i)
        wt.append(p)
    angc2, dom, ang64 = [], [], []
    for k, x, y in zip(ks, uc, n64):
        vals = [node_vals(payload, k - 2 + i) for i in range(6)]
        interp = [sum(wt[i] * vals[i][c] for i in range(6)) for c in range(12)]
        direct = [H.value(v, 256) for v in x[1:13]]
        angc2.append(rot_angle(interp[:9], direct[:9]))
        dom.append(math.sqrt(sum(float(interp[9 + i] - direct[9 + i]) ** 2 for i in range(3))))
        ang64.append(rot_angle([H.value(v, 64) for v in y[1:10]], direct[:9]))
    log.w("# (c) table (exact interpolation) against direct: angle max %.4e rad (%.6f uas), median %.4e rad; |dOmega| max %.3e rad/s"
          % (max(angc2), max(angc2) / UAS, sorted(angc2)[100], max(dom)))
    log.w("# (c) REPORTED: native64's interpolation against direct: angle max %.4e rad (%.4f uas)" % (max(ang64), max(ang64) / UAS))
    log.check(max(angc2) <= btheta, "(c) every angle <= B_theta = %.4e rad (max %.4e)" % (btheta, max(angc2)))
    log.check(max(dom) <= bomega, "(c) every |dOmega| <= B_Omega = %.3e rad/s (max %.3e)" % (bomega, max(dom)))
    c = cpu.close("h0_gate log %03d" % log.n)
    if c is not None:
        log.w("# CPU: %.2f s by cycles / 2.5e9 (this script and every process it started)" % c)
    return log.close()


if __name__ == "__main__":
    sys.exit(main())
