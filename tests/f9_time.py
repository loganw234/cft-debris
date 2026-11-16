# f9_time.py - cft-debris M1 (DEBRIS-F), F9: cost, in a `sensitive` window the lead books (nothing else of DEBRIS-F's
# runs during it).
# cft-debris, MIT licence (see LICENSE at the repository root). Written by DEBRIS-F, 2026-11-16.
#
#   python -I -B tests/f9_time.py <booking id> [min_seconds]
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import f_lib as F  # noqa: E402

CRITERIA = """
A MEASUREMENT (no pass condition; the PASS lines say only that a run completed), single runs, the load stated per row
(Windows CPU % over 0.5 s before and after each run; one busy thread of 12 logical processors is about 8%).
T1 each kind's time per lane-force-evaluation with the real frame (tests/m1f.c time: the whole model at degree 20, the
   28-band atmosphere, the Sun, the Moon, radiation pressure, the frame interpolated once a stage time), at 1 and 64
   lanes, native32, native64 (the C library's transcendentals and libcft's), cft32, cft64, cft128, cft256; and an
   object-day's time with rk4 at 15 s, COMPUTED from the measured time of a step; beside DEBRIS-E's E9 (uniform frame).
T2 the node table's build: m1nodes build of 2 days of data (675 fine nodes and their coarse nodes), wall time and
   cycles; reported per day of data.
T3 a fit's time per object at native64: tests/m1f.c fit on the first 5 objects of F5(d)'s fit input, wall time per
   object, with the iteration counts.
"""


def main():
    if len(sys.argv) < 2:
        raise SystemExit("usage: f9_time.py <booking id> [min_seconds]")
    booking = sys.argv[1]
    mins = sys.argv[2] if len(sys.argv) > 2 else "2"
    log = F.Log("f9_time", os.path.abspath(__file__), CRITERIA)
    log.w("# TimeSheet booking %s (sensitive, desktop); min seconds per measurement %s" % (booking, mins))
    exe, nodes = F.BUILD + "/m1f_O2.exe", F.BUILD + "/m1nodes.exe"
    table = F.DATA + "/tables/frame_main.bin"
    log.w("# m1f_O2.exe sha256 %s; m1nodes.exe sha256 %s; table sha256 %s" % (F.sha256(exe), F.sha256(nodes), F.sha256(table)))
    W = F.WORK + "/f9"
    os.makedirs(W, exist_ok=True)
    for kind, extra in (("native32", []), ("native64", []), ("native64", ["--cr"]), ("cft32", []), ("cft64", []), ("cft128", []), ("cft256", [])):
        for n in (1, 64):
            tag = "%s%s_%d" % (kind, "_cr" if extra else "", n)
            o = W + "/time_%s.txt" % tag
            l0 = F.G.host_load()
            F.run([exe, "time", kind, table, str(n), mins, o] + extra, log, cpu_label="f9_%s" % tag)
            l1 = F.G.host_load()
            for ln in open(o):
                if ln.startswith("accel") or ln.startswith("rk4"):
                    log.w("MEASURED T1 %s%s lanes %d (load %.0f%% / %.0f%%): %s" % (kind, " libcft-transc" if extra else "", n, l0, l1, ln.strip()))
            log.check(True, "T1 %s completed" % tag)
    # T2
    l0 = F.G.host_load()
    t0 = time.perf_counter()
    F.run([nodes, "build", "1000000", "256", "675", W + "/table_2days.bin", "--note", "F9 T2"], log, cpu_label="f9_table_2days")
    dt = time.perf_counter() - t0
    l1 = F.G.host_load()
    log.w("MEASURED T2 a 2-day table (675 fine nodes): %.2f s wall (load %.0f%% / %.0f%%), %.2f s a day of data; cycles in records/cpu.tsv (f9_table_2days)" % (dt, l0, l1, dt / 2))
    # T3
    src = F.WORK + "/f5/d_fit_in.txt"
    out, nobj = [], 0
    for ln in open(src):
        if ln.startswith("OBJ "):
            nobj += 1
            if nobj > 5:
                break
        out.append(ln)
    with open(W + "/fit5_in.txt", "w", newline="\n") as f:
        f.writelines(out)
    l0 = F.G.host_load()
    t0 = time.perf_counter()
    F.run([exe, "fit", table, W + "/fit5_in.txt", W + "/fit5_out.txt"], log, cpu_label="f9_fit5")
    dt = time.perf_counter() - t0
    l1 = F.G.host_load()
    its = [int(ln.split()[3]) for ln in open(W + "/fit5_out.txt") if ln.startswith("FIT")]
    log.w("MEASURED T3 5 fits at native64: %.2f s wall (load %.0f%% / %.0f%%), %.2f s an object; iterations %s (%.2f s an iteration)" %
          (dt, l0, l1, dt / 5, its, dt / max(1, sum(its))))
    return log.close()


if __name__ == "__main__":
    sys.exit(main())
