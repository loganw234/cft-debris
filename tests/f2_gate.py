# f2_gate.py - cft-debris M1 (DEBRIS-F), gate F2: the host time scales (B1) against Orekit 13.1.9.
# cft-debris, MIT licence (see LICENSE at the repository root). Written by DEBRIS-F, 2026-11-16.
#
#   python -I -B tests/f2_gate.py
#
# Ours: tests/m1nodes.c's modes "times" and "leaps" (src/m1_nodes.c: tai-utc.dat, TT = TAI + 32.184 s, TDB - TT by
# USNO Circular 179 eq. (2.6), UT1 - UTC by 4-point Lagrange on the daily rows, computed at binary256).
# Orekit's: tests/f_orekit.js, modes "times" and "leaps", with the same tai-utc.dat and finals2000A.daily crawled.
import os
import random
import sys
from fractions import Fraction

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import f_lib as F  # noqa: E402

CRITERIA = """
Epochs: 1,000 UTC instants, MJD uniform in [61271, 61430) (random.Random(0xF2)), each turned into TDB seconds from
  JD 2461329.5 by tests/f_lib.py (exact but for eq. 2.6) and rounded to binary64. The file spans MJD 61270..61450;
  61271..61430 keeps every 4-point stencil inside the file and every epoch before the rows with blank dX, dY.
  At each: TAI-UTC, TT-TAI, TDB-TT and UT1-UTC, ours against Orekit's at the instant our TAI gives (TAI s from
  2026-10-16T00:00:00 TAI, binary64).
T1 TAI-UTC: equal exactly (both integers of seconds from the same tai-utc.dat).
T2 TT-TAI: equal exactly (32.184 s by definition on both sides, the same binary64).
T3 TDB-TT: |ours - Orekit's| <= 50 us. Basis, computed below before the data: Orekit's TDBScale sits about 1 us from
  the two-term series 0.001657 sin g + 0.000014 sin 2g (plan-verifier-F, MEASURED, eight dates of 2026), while eq. (2.6)
  carries five more terms, 22 + 5 + 5 + 2 us and 10 T us, and its annual and semiannual terms differ in rate and
  phase from the two-term series' g; the sum of those amplitudes and phase drifts over |T| <= 0.28, plus 1 us, is the
  basis, and it must come out under 50 us (asserted).
T4 UT1-UTC: |ours - Orekit's| <= 1e-9 s. Basis: the same scheme on both sides - Lagrange through the 4 nearest daily
  rows (Orekit's EOPHistory interpolation degree is 3, asserted from the Orekit run's header) - so only rounding
  differs (values of 0.1 s, binary64, about 1e-17 s).
L1 the leap seconds: TAI-UTC at 2015-06-30 23:59:59.5, 2015-07-01 00:00:00.5, 2016-12-31 23:59:59.5 and
  2017-01-01 00:00:00.5 UTC, ours (m1nodes leaps, at the UTC MJD) equal to Orekit's UTC (its own parser of the same
  tai-utc.dat), and the four are 35, 36, 36, 37 s.
NEGATIVE CONTROL C1: a copy of tai-utc.dat with its 2017-01-01 line removed (written to the scratch by this script,
  and asserted to differ from the original by exactly that line) must FAIL: TAI-UTC must then differ from Orekit's
  at 2017-01-01 00:00:00.5 and at every one of the 1,000 epochs (36 against 37), and agree at the three earlier
  leap epochs.
NaN: none of our values may be NaN.
"""


def tdbtt_basis_us():
    """the bound on |eq. (2.6) - Orekit's TDB - TT| in us, from amplitudes (T3's basis)"""
    Tmax = 0.28
    extra = 22 + 5 + 5 + 2 + 10 * Tmax
    # the two-term series: g = 357.53 deg + 0.98560028 deg/day (JD - 2451545), as rad and rad/century
    import math
    g0 = math.radians(357.53)
    g1 = math.radians(0.98560028) * 36525
    annual = 1657 * (abs(628.3076 - g1) * Tmax + abs(6.2401 - g0))
    semi = 14 * (abs(1256.6152 - 2 * g1) * Tmax + abs((6.1969 - (2 * g0 - 2 * math.pi))))
    return extra + annual + semi + 1.0, (extra, annual, semi)


def main():
    log = F.Log("f2_gate", os.path.abspath(__file__), CRITERIA, extra_files=[os.path.join(F.REPO, "tests", "f_orekit.js")])
    exe = F.BUILD + "/m1nodes.exe"
    log.w("# m1nodes.exe sha256 %s" % F.sha256(exe))
    basis, parts = tdbtt_basis_us()
    log.w("# T3 basis: %.2f us (extra terms %.2f, annual drift %.2f, semiannual %.3f, Orekit's 1 us)" % ((basis,) + parts))
    log.check(basis <= 50.0, "T3's basis %.2f us is under its tolerance of 50 us" % basis)
    W = F.WORK + "/f2"
    os.makedirs(W, exist_ok=True)
    rng = random.Random(0xF2)
    ts = []
    for _ in range(1000):
        mjd = 61271 + rng.random() * (61430 - 61271)
        d = int(mjd)
        sec = Fraction(round((mjd - d) * 86400 * 10**6), 10**6)
        ts.append(float(F.utc_to_tdb(d, sec)))
    with open(W + "/t.txt", "w", newline="\n") as f:
        for t in ts:
            f.write(float.hex(t) + "\n")
    F.run([exe, "times", W + "/t.txt", W + "/ours.txt"], log, cpu_label="f2_ours")
    ours = [ln.split() for ln in open(W + "/ours.txt") if not ln.startswith("#")]
    log.check(len(ours) == 1000, "our run gave 1000 epochs (%d)" % len(ours))
    with open(W + "/tai.txt", "w", newline="\n") as f:
        for r in ours:
            f.write(repr(float.fromhex(r[1])) + "\n")
    F.orekit(os.path.join(F.REPO, "tests", "f_orekit.js"), ["times", F.DATA + "/orekit", W + "/tai.txt", W + "/ore.txt"], log, cpu_label="f2_orekit")
    head = [ln for ln in open(W + "/ore.txt") if ln.startswith("#")]
    for h in head:
        log.w("# orekit: " + h.strip())
    log.check(any("interpolation degree 3" in h for h in head), "Orekit's EOP interpolation degree is 3 (4 points)")
    log.check(any("EOP loaded" in h for h in head), "Orekit asserted that the Earth orientation data loaded")
    ore = [ln.split() for ln in open(W + "/ore.txt") if not ln.startswith("#")]
    log.check(len(ore) == 1000, "Orekit gave 1000 epochs (%d)" % len(ore))
    worst = [0.0, 0.0, 0.0, 0.0]
    nan = 0
    nbad = [0, 0, 0, 0]
    for a, b in zip(ours, ore):
        va = [float.fromhex(x) for x in a[2:6]]
        vb = [float.fromhex(x) for x in b[1:5]]
        nan += sum(1 for x in va if x != x)
        for i in range(4):
            dlt = abs(va[i] - vb[i])
            worst[i] = max(worst[i], dlt)
        nbad[0] += va[0] != vb[0]
        nbad[1] += va[1] != vb[1]
        nbad[2] += abs(va[2] - vb[2]) > 50e-6
        nbad[3] += abs(va[3] - vb[3]) > 1e-9
    log.w("# worst |ours - Orekit|: TAI-UTC %.3e s, TT-TAI %.3e s, TDB-TT %.3e s (%.2f us), UT1-UTC %.3e s" %
          (worst[0], worst[1], worst[2], worst[2] * 1e6, worst[3]))
    log.check(nan == 0, "no NaN in our values")
    log.check(nbad[0] == 0, "T1 TAI-UTC equal at all 1000 epochs (%d differ)" % nbad[0])
    log.check(nbad[1] == 0, "T2 TT-TAI equal at all 1000 epochs (%d differ)" % nbad[1])
    log.check(nbad[2] == 0, "T3 TDB-TT within 50 us at all 1000 epochs (worst %.2f us; %d over)" % (worst[2] * 1e6, nbad[2]))
    log.check(nbad[3] == 0, "T4 UT1-UTC within 1e-9 s at all 1000 epochs (worst %.3e s; %d over)" % (worst[3], nbad[3]))
    # L1, the leap seconds
    LE = [("2015 6 30 23 59 59.5", 57203, Fraction(863995, 10), 35), ("2015 7 1 0 0 0.5", 57204, Fraction(1, 2), 36),
          ("2016 12 31 23 59 59.5", 57753, Fraction(863995, 10), 36), ("2017 1 1 0 0 0.5", 57754, Fraction(1, 2), 37)]
    with open(W + "/leaps_in.txt", "w", newline="\n") as f:
        for e in LE:
            f.write(e[0] + "\n")
    with open(W + "/leaps_mjd.txt", "w", newline="\n") as f:
        for e in LE:
            # the instant's UTC MJD (23:59:59.5 is 86399.5 s into its day)
            f.write(float.hex(float(e[1] + e[2] / 86400)) + "\n")
    F.orekit(os.path.join(F.REPO, "tests", "f_orekit.js"), ["leaps", F.DATA + "/orekit", W + "/leaps_in.txt", W + "/leaps_ore.txt"], log, cpu_label="f2_leaps_orekit")
    F.run([exe, "leaps", W + "/leaps_mjd.txt", W + "/leaps_ours.txt"], log, cpu_label="f2_leaps_ours")
    lo = [ln.split() for ln in open(W + "/leaps_ore.txt") if not ln.startswith("#")]
    lu = [ln.split() for ln in open(W + "/leaps_ours.txt") if not ln.startswith("#")]
    ok = len(lo) == 4 and len(lu) == 4
    for i, e in enumerate(LE):
        o = float.fromhex(lo[i][-1])
        u = float.fromhex(lu[i][-1])
        log.w("# leap epoch %s UTC: ours %.1f s, Orekit %.1f s, expected %d s" % (e[0], u, o, e[3]))
        ok = ok and o == u == e[3]
    log.check(ok, "L1 TAI-UTC at the four leap epochs: ours equal Orekit's, and 35, 36, 36, 37 s")
    # C1, the negative control
    orig = open(F.DOWNLOADS + "tai-utc.dat/tai-utc.dat", "rb").read().split(b"\n")
    cut = [ln for ln in orig if b"2017 JAN  1" not in ln]
    log.check(len(orig) - len(cut) == 1, "C1's copy differs from tai-utc.dat by exactly the 2017-01-01 line")
    with open(W + "/tai-utc-cut2017.dat", "wb") as f:
        f.write(b"\n".join(cut))
    F.run([exe, "times", W + "/t.txt", W + "/ours_cut.txt", "--leaps", W + "/tai-utc-cut2017.dat"], log, cpu_label="f2_ctl_times")
    F.run([exe, "leaps", W + "/leaps_mjd.txt", W + "/leaps_ours_cut.txt", "--leaps", W + "/tai-utc-cut2017.dat"], log, cpu_label="f2_ctl_leaps")
    cu = [ln.split() for ln in open(W + "/ours_cut.txt") if not ln.startswith("#")]
    lc = [ln.split() for ln in open(W + "/leaps_ours_cut.txt") if not ln.startswith("#")]
    ndiff = sum(1 for a, b in zip(cu, ore) if float.fromhex(a[2]) != float.fromhex(b[1]))
    lcd = [float.fromhex(r[-1]) for r in lc]
    lod = [float.fromhex(r[-1]) for r in lo]
    log.w("# C1: TAI-UTC differs from Orekit's at %d of %d epochs; at the leap epochs ours %s, Orekit's %s" % (ndiff, len(cu), lcd, lod))
    log.check(ndiff == 1000 and lcd[3] != lod[3] and lcd[:3] == lod[:3],
              "C1 FAILS as specified: all 1000 epochs and the 2017-01-01 epoch differ, the three earlier leap epochs agree")
    return log.close()


if __name__ == "__main__":
    sys.exit(main())
