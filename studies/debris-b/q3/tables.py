#!/usr/bin/env python3
"""DEBRIS-B: the COMPUTED tables of the study, from labelled inputs.

Every input below names its source: MEASURED in this study (log named),
READ (source named), or DEBRIS-A's (reproduced by verifier-A per lead.md
16:08). Nothing is measured here; this is arithmetic.

  python -I -B tables.py
"""
import math

GM = 398600.4418e9          # m^3/s^2
TWO_PI = 2 * math.pi

# ---------------------------------------------------------------- Q3 inputs
# binary64 arithmetic error, two transfer coefficients:
# low: LEO 400 km + J2, binary64 against binary128 at one day on the same
#      864 fixed 100 s steps: 1.175e-8 m (DEBRIS-A port_fullday.log;
#      reproduced by verifier-A), a single draw, at 15.56 orbits.
# high: HORIZON.md's p90 law for the e = 1/2 Kepler ensemble at REBOUND's
#      default epsilon: phase = 2.11e-16 * orbits^1.525 (in orbits).
A400 = 6778.137e3
N1 = 86400 / (TWO_PI * math.sqrt(A400 ** 3 / GM))
PHI1 = 1.175e-8 / (TWO_PI * A400) # orbits of phase at N1 orbits
REGIMES = [("LEO 400 km", 6778.137e3), ("LEO 800 km", 7178.137e3), ("MEO / GNSS disposal", 26560e3),
           ("GEO", 42164e3), ("GEO graveyard +300 km", 42464e3)]
HORIZONS = [("a week", 7.0), ("a year", 365.25), ("30 years", 30 * 365.25)]


def period(a):
    return TWO_PI * math.sqrt(a ** 3 / GM)


def b64_err(a, days):
    n = days * 86400 / period(a)
    low = PHI1 * (n / N1) ** 1.5 * TWO_PI * a
    high = 2.11e-16 * n ** 1.525 * TWO_PI * a
    # the equivalent error in a/a at the start, from phase = 1.5 (da/a) n
    eq = 2.11e-16 * n ** 1.525 / (1.5 * n)
    return n, low, high, eq


def q3():
    print("Q3. binary64 arithmetic error (along-track, metres), COMPUTED")
    print("    low: DEBRIS-A's LEO one-day binary64-vs-binary128 difference, grown as t^1.5")
    print("    high: HORIZON.md's p90 law 2.11e-16 * orbits^1.525 (Kepler e = 1/2)")
    print("%-22s %-9s %10s %11s %11s %13s" % ("regime", "horizon", "orbits", "low (m)", "high (m)",
                                              "equiv. da/a"))
    for name, a in REGIMES:
        for hname, days in HORIZONS:
            n, lo, hi, eq = b64_err(a, days)
            print("%-22s %-9s %10.0f %11.2e %11.2e %13.1e" % (name, hname, n, lo, hi, eq))
    print("    N1 = %.2f orbits a day at 400 km; PHI1 = %.3e orbits" % (N1, PHI1))
    # the drag displacement law, held against q3_physics.log
    rho, B, a = 3.725e-12, 0.022, A400
    adot = rho * B * math.sqrt(GM * a)
    nmot = TWO_PI / period(a)
    ds = 0.75 * 0.2 * nmot * adot * 86400 ** 2
    print("    drag law: 20%% density error at 400 km, one day: 0.75 f n |da/dt| t^2 = %.0f m"
          " (|da/dt| = %.3g m/s); q3_physics.log measured 4991 m" % (ds, adot))
    a8 = 7178.137e3
    adot8 = 1.170e-14 * B * math.sqrt(GM * a8)
    ds8 = 0.75 * 0.2 * (TWO_PI / period(a8)) * adot8 * 86400 ** 2
    print("    same at 800 km: %.1f m a day (measured 15.56 m)" % ds8)
    # binary64 error of the drag term itself: a relative 2^-53 in rho*B
    u = 2.0 ** -53
    print("    a relative 2^-53 error in the drag term at 400 km for a year (if the object lived): %.1e m"
          % (0.75 * u * nmot * adot * (365.25 * 86400) ** 2))


# ---------------------------------------------------------------- Q2 inputs
# per-call costs, ns, minimum of 5 repetitions (q2_time.log, host load 13-69%)
COST = dict(grav8=183.0, grav20=864.0, grav36=2617.8, grav70=10038.6, cheb=129.4, frame_full=146936.4,
            frame_interp=511.8, srp=34.6, srp_pen=74.9, atmos=79.5)
# REBOUND's C IAS15, point mass, no callback: 2.887 ms per LEO object-day,
# 558.4 steps a day (ias15_evals_sh_meogeo.log); spread over the J2 count
# of 12,410 evaluations a day (ias15_evals.log) that is the integrator's own
# cost per evaluation, BELIEVED to carry over per evaluation
OVERHEAD = 2.887e6 / 12410.0
# evaluations per object-day (MEASURED: ias15_evals_sh.log, ias15_evals_sh_meogeo.log)
EVALS = dict(leo8=13852, leo20=16463, leo36=17912, leo70=20159, meo=1598.9, geo=802.1)
# catalogued objects, ESA DISCOS statistics page, last update 2 November 2026
# (READ via WebFetch 2026-11-12): LEO 28,149, MEO 1,290, GEO 939, all 47,393;
# MASTER-8 (02/2026) estimate of objects > 10 cm: 68,450
COUNT = dict(leo=28149, meo=1290, geo=939, other=47393 - 28149 - 1290 - 939)


def q2():
    print("\nQ2. per-evaluation cost and the catalogue-year budget, COMPUTED from MEASURED inputs")
    other = COST["frame_interp"] + COST["cheb"] + COST["srp"]
    rows = []
    for N in (8, 20, 36, 70):
        per = OVERHEAD + COST["grav%d" % N] + other + COST["atmos"]
        day = per * EVALS["leo%d" % N] * 1e-9
        rows.append(("LEO, degree %d, exponential air" % N, per, EVALS["leo%d" % N], day, COUNT["leo"]))
    per_mg = OVERHEAD + COST["grav8"] + other
    rows.append(("MEO, degree 8", per_mg, EVALS["meo"], per_mg * EVALS["meo"] * 1e-9, COUNT["meo"]))
    rows.append(("GEO, degree 8", per_mg, EVALS["geo"], per_mg * EVALS["geo"] * 1e-9, COUNT["geo"]))
    print("%-34s %12s %10s %14s %8s %16s" % ("regime and model", "ns per eval", "evals/day", "ms/object-day",
                                              "objects", "CPU-hours a year"))
    for name, per, ev, day, cnt in rows:
        print("%-34s %12.0f %10.0f %14.2f %8d %16.2f" % (name, per, ev, day * 1e3, cnt, day * cnt * 365 / 3600))
    print("    per-evaluation terms: integrator %.0f ns (BELIEVED split of a MEASURED per-day cost), frame %.0f,"
          " Sun+Moon %.0f, radiation pressure %.0f, exponential air %.0f" % (OVERHEAD, COST["frame_interp"],
                                                                              COST["cheb"], COST["srp"],
                                                                              COST["atmos"]))
    leo20 = rows[1]
    print("    the other %d catalogued objects (GTO, HEO and the rest), priced at LEO degree 20 as an upper bound:"
          " %.1f CPU-hours a year" % (COUNT["other"], leo20[3] * COUNT["other"] * 365 / 3600))
    tot20 = sum(r[3] * r[4] for r in (rows[1], rows[4], rows[5])) * 365 / 3600
    print("    LEO-20 + MEO + GEO catalogued: %.1f CPU-hours a year; x 68,450/47,393 for MASTER-8's > 10 cm"
          " estimate (BELIEVED same regime mix): %.1f" % (tot20, tot20 * 68450 / 47393))
    # the atmosphere's break-even: the cost X at which a density model doubles LEO-20's per-evaluation cost
    print("    a density model costing X ns a call adds X to each LEO evaluation; it doubles LEO degree 20's"
          " cost at X = %.0f ns" % leo20[1])
    for X in (1e3, 1e4, 1e5):
        day = (leo20[1] + X) * EVALS["leo20"] * 1e-9
        print("      X = %6.0f ns: %.0f ms per object-day, %.0f CPU-hours a year for LEO" % (
            X, day * 1e3, day * COUNT["leo"] * 365 / 3600))
    # the full frame series, if it were evaluated at every evaluation instead
    print("    the full IAU 2006/2000A series at every evaluation instead of interpolating: %.0f ns, x%.0f the"
          " interpolated transform" % (COST["frame_full"], COST["frame_full"] / COST["frame_interp"]))
    print("    the series once an hour for a whole catalogue: %.2f CPU-seconds a year" % (
        COST["frame_full"] * 1e-9 * 24 * 365))
    # DEBRIS-A's BELIEVED 10-100 us an evaluation against these
    print("    DEBRIS-A's BELIEVED 10-100 us an evaluation: measured here %.1f to %.1f us without a full"
          " density model" % (rows[0][1] / 1e3, rows[3][1] / 1e3))


def q3_price():
    print("\nQ3 prices, COMPUTED")
    q = dict(N8=32397.9, N20=184820.8, N36=539250.4, N70=1954158.8)
    d = dict(N8=183.0, N20=864.0, N36=2617.8, N70=10038.6)
    for k in q:
        print("    libquadmath binary128 SH gravity %s: %.0fx binary64" % (k, q[k] / d[k]))
    # tile, READ from cft-rebound docs/VALIDATION.md entries 37 and 45 (Kepler point mass)
    for label, rate in (("binary256, E = 512 (entry 45)", 512 * 20 / 50.10),
                        ("binary128, E = 512 (entry 45)", 512 * 20 / 17.77),
                        ("binary128, E = 4,096 (entry 37)", 562.3), ("binary64, E = 4,096 (entry 37)", 1405.6)):
        sec = 559 / rate
        print("    tile %-32s %7.1f system-steps/s: a LEO object-day (559 steps) = %.2f tile-s;"
              " the LEO catalogue for a year = %.2f tile-years (point-mass floor)" % (
                  label, rate, sec, sec * COUNT["leo"] * 365 / (365.25 * 86400)))
    sw256 = 62.0  # HARDWARE.md: software backend, binary256, E = 1,024, one core
    print("    software backend binary256 (62 system-steps/s, E = 1,024): the LEO catalogue for a year ="
          " %.1f core-years (point-mass floor)" % (559 / sw256 * COUNT["leo"] * 365 / (365.25 * 86400)))


if __name__ == "__main__":
    q3()
    q2()
    q3_price()
