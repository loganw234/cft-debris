#!/usr/bin/env python3
"""DEBRIS-C, M2: DEBRIS-B's LEO catalogue-year table again, with the measured
density-model costs added. COMPUTED; every input is labelled.

  python -I -B m2_table.py

Definitions are DEBRIS-B's (studies/debris-b/q3/tables.py, read, not run):
ns per evaluation = the integrator's 233 ns share (BELIEVED split) + gravity
+ interpolated frame 511.8 + Sun and Moon 129.4 + radiation pressure 34.6 +
exponential air 79.5; "a density model costing X ns a call adds X to each
LEO evaluation"; evaluations per object-day are IAS15's (13,852 / 16,463 /
17,912 / 20,159 at degrees 8 / 20 / 36 / 70); objects 28,149 (LEO, DISCOS,
2 November 2026); CPU-hours a year = ms per object-day x objects x 365 / 3600.
The script first reproduces DEBRIS-B's four LEO rows (asserted to the ns).

New inputs, MEASURED in this study (logs/m2_time.002.log and .003.log, the
minimum ns per call over 7 repetitions, two runs; run 001 is set aside
because its calibration ran cold and its density repetitions were 19-90 ms):
- NRLMSISE00 getDensity, ellipsoid on GCRF (variant A): 7529.05 / 7316.9 ns
- JB2008 getDensity, variant A: 31623.43 / 29914.2 ns
- Orekit HolmesFeatherstone gradient, degrees 8/20/36/70:
  572.61 / 541.2, 2162.24 / 1745.8, 5616.91 / 4477.5, 16010.65 / 14919.1 ns
- DEBRIS-B's C gravity kernel again, same hours (logs/m2_c_grav.001.log,
  min of 5): 165.297, 831.054, 2555.180, 9683.228 ns.
These are Java figures driven from Nashorn; the trivial-call overhead
(7.3 to 8.1 ns, a lower bound) and the script callbacks inside each density
call (5 or 14 at 15.5 to 23.7 ns) are not subtracted: together under 0.4 us.
"""
OVERHEAD = 2.887e6 / 12410.0
C_GRAV_B = {8: 183.0, 20: 864.0, 36: 2617.8, 70: 10038.6}    # DEBRIS-B q2_time.log
OTHER = 511.8 + 129.4 + 34.6
ATMOS = 79.5
EVALS = {8: 13852, 20: 16463, 36: 17912, 70: 20159}
LEO = 28149
DEBRIS_B_NS = {8: 1171, 20: 1852, 36: 3606, 70: 11027}       # DEBRIS-B tables.log, rounded to the ns
NRL = (7316.9, 7529.05)
JB = (29914.2, 31623.43)
HF = {8: (541.2, 572.61), 20: (1745.8, 2162.24), 36: (4477.5, 5616.91), 70: (14919.1, 16010.65)}
C_GRAV_NOW = {8: 165.297, 20: 831.054, 36: 2555.180, 70: 9683.228}
BREAK_EVEN = 1852.0


def cpu_hours(ns, deg):
    return ns * EVALS[deg] * 1e-9 * LEO * 365 / 3600


def main():
    print("# DEBRIS-C M2 table, COMPUTED (inputs in the header). Ranges are run 003 to run 002.")
    print("# check: DEBRIS-B's LEO rows reproduce")
    for d in (8, 20, 36, 70):
        per = OVERHEAD + C_GRAV_B[d] + OTHER + ATMOS
        assert round(per) == DEBRIS_B_NS[d], (d, per)
        print("  degree %2d: %.0f ns per evaluation, %.1f CPU-hours a year (DEBRIS-B: %d ns)" % (d, per, cpu_hours(per, d), DEBRIS_B_NS[d]))
    print("# the density models against DEBRIS-B's break-even (%.0f ns, degree 20):" % BREAK_EVEN)
    print("  NRLMSISE00 %.0f to %.0f ns a call = %.1f to %.1f x the break-even" % (NRL[0], NRL[1], NRL[0] / BREAK_EVEN, NRL[1] / BREAK_EVEN))
    print("  JB2008     %.0f to %.0f ns a call = %.1f to %.1f x the break-even" % (JB[0], JB[1], JB[0] / BREAK_EVEN, JB[1] / BREAK_EVEN))
    print("%-8s | %-22s | %-22s | %-22s | %-22s" % ("", "C gravity, exp. air", "C gravity + NRLMSISE00", "C gravity + JB2008",
                                                 "Orekit HF + NRLMSISE00"))
    print("%-8s | %-22s | %-22s | %-22s | %-22s" % ("degree", "ns/eval  CPU-h/yr", "ns/eval  CPU-h/yr", "ns/eval  CPU-h/yr", "ns/eval  CPU-h/yr"))
    for d in (8, 20, 36, 70):
        base = OVERHEAD + C_GRAV_B[d] + OTHER + ATMOS
        cols = [(base, base)]
        cols.append((base + NRL[0], base + NRL[1]))
        cols.append((base + JB[0], base + JB[1]))
        j0 = OVERHEAD + HF[d][0] + OTHER + ATMOS + NRL[0]
        j1 = OVERHEAD + HF[d][1] + OTHER + ATMOS + NRL[1]
        cols.append((j0, j1))
        cells = []
        for lo, hi in cols:
            if lo == hi:
                cells.append("%6.0f   %7.0f" % (lo, cpu_hours(lo, d)))
            else:
                cells.append("%5.0f-%5.0f %4.0f-%4.0f" % (lo, hi, cpu_hours(lo, d), cpu_hours(hi, d)))
        print("%-8d | %-22s | %-22s | %-22s | %-22s" % (d, cells[0], cells[1], cells[2], cells[3]))
    print("# Java figures: the density costs in columns 2-4, and the gravity in column 4. All else is DEBRIS-B's C or BELIEVED split.")
    print("# gravity alone, Orekit (Java) over DEBRIS-B's C kernel timed in the same hours (language and algorithm together):")
    for d in (8, 20, 36, 70):
        print("  degree %2d: Orekit %.0f-%.0f ns, C %.0f ns: %.1f-%.1f x" % (d, HF[d][0], HF[d][1], C_GRAV_NOW[d],
                                                                      HF[d][0] / C_GRAV_NOW[d], HF[d][1] / C_GRAV_NOW[d]))
    print("# COMPUTED PASS (DEBRIS-B's rows reproduced)")


if __name__ == "__main__":
    main()
