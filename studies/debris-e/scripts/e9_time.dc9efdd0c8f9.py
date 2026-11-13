# e9_time.py - cft-debris M1, E9: cost. For each number kind, the wall time of a
# force evaluation at degree 20 (the whole model) and of an object-day of rk4 at
# 15 s, at batches of 1, 8 and 64 lanes. Run only inside a `sensitive` window
# the lead books; nothing else of DEBRIS-E's runs meanwhile.
# cft-debris, MIT licence (see LICENSE at the repository root). Written by
# DEBRIS-E, 2026-11-13.
#
#   python -I -B tests/e9_time.py <booking id> [min_seconds=2]
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gatelib as g  # noqa: E402

CRITERIA = """
A measurement, with no pass condition. For each kind (native32 and native64 with the C library's
   transcendentals and, separately, with libcft's; cft32, cft64, cft128, cft256) and each batch (1, 8, 64
   lanes): m1run's time mode repeats the whole force evaluation (central, degrees 2..20, Sun, Moon, 28-band
   drag, radiation pressure; the Sun, the Moon and the frame once a batch) for at least min_seconds, then rk4
   steps at 15 s for at least min_seconds. Reported: wall microseconds a lane-evaluation, and wall seconds an
   object-day (5,760 steps of 15 s) a lane, COMPUTED from the measured time a step. The host load is sampled
   before and after each run and stated beside it. Beside them, DEBRIS-D's Q3 prices (MEASURED then, its log
   q3_host.001.log): FMA 195, 235 and 313 ns at binary64, 128 and 256; and an ESTIMATE of this kernel's cost,
   our measured lane-ops an evaluation times that FMA price (basis: DEBRIS-D's FMA price for every operation;
   range: x 1 for add and multiply, which DEBRIS-D did not time, to x 20 for divide).
The sanity checks (asserted): every run ends 0 and prints both lines.
"""
KINDS = [("native32", []), ("native32", ["--cr"]), ("native64", []), ("native64", ["--cr"]), ("cft32", []),
         ("cft64", []), ("cft128", []), ("cft256", [])]
LANES = [1, 8, 64]
FMA_NS = {"cft64": 195, "cft128": 235, "cft256": 313}
W = os.path.join(g.WORK, "e9")
os.makedirs(W, exist_ok=True)


def main():
    if len(sys.argv) < 2:
        sys.exit("usage: e9_time.py <booking id> [min_seconds]")
    booking = sys.argv[1]
    mins = sys.argv[2] if len(sys.argv) > 2 else "2"
    log = g.Log("e9_time", os.path.abspath(__file__), CRITERIA)
    log.w("# TimeSheet booking %s; min_seconds %s" % (booking, mins))
    for kind, extra in KINDS:
        for n in LANES:
            out = os.path.join(W, "time_%s%s_%d.txt" % (kind, "_cr" if extra else "", n))
            l0 = g.host_load(0.5)
            g.run([g.exe("O2"), "time", kind, n, mins, out] + extra, log)
            l1 = g.host_load(0.5)
            rows, head = g.read_rows(out)
            acc = [r for r in rows if r[0] == "accel"][0]
            rk = [r for r in rows if r[0] == "rk4"][0]
            us = float(acc[acc.index("per_lane_eval_us") + 1])
            day = float(rk[rk.index("per_object_day_s") + 1])
            ops = [h for h in head if h.startswith("# lane-ops")][0]
            tot = sum(int(t.split("=")[1]) for t in ops.split()[2:])
            ne = int(acc[acc.index("evals") + 1])
            st = int(rk[rk.index("steps") + 1])
            per_eval_ops = tot / float(n * (ne + 4 * st))
            est = ""
            if kind in FMA_NS:
                est = "; ESTIMATE from DEBRIS-D's FMA price: %.0f us" % (per_eval_ops * FMA_NS[kind] / 1000.0)
            log.check(len(acc) > 0 and len(rk) > 0, "%s%s lanes %d: %.1f us a lane-evaluation (%d evaluations), "
                      "%.1f s an object-day a lane (from %d rk4 steps); about %.0f lane-ops an evaluation%s; load "
                      "%.0f%% before, %.0f%% after" % (kind, " (libcft transcendentals)" if extra else "", n, us, ne,
                                                     day, st, per_eval_ops, est, l0, l1))
    return log.close()


if __name__ == "__main__":
    sys.exit(main())
