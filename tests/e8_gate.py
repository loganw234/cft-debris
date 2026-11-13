# e8_gate.py - cft-debris M1, gate E8: reproducibility of E2's run (eight LEO
# lanes, degree 20 and every force, rk4 at 60 s for 100 steps).
# cft-debris, MIT licence (see LICENSE at the repository root). Written by
# DEBRIS-E, 2026-11-13.
#
#   python -I -B tests/e8_gate.py
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gatelib as g  # noqa: E402

CRITERIA = """
R1 every kind's run reproduces bit for bit across two runs of the O2 build: native32 and native64 (both in
   the control configuration, libcft's transcendentals, and with the C library's), cft32, cft64, cft128 and
   cft256 - every step, lane and component.
R2 the O0 build (-O0, contraction off, the FMA instruction on) equals the O2 build bit for bit, every kind and
   configuration of R1.
R3 NEGATIVE CONTROL: the fast build (-ffp-contract=fast with -mfma; the build holds 23 vfmadd per native
   object against O2's 12) must DIFFER from the O2 build for native64 and for native32 (control
   configuration), in at least one component at the final step.
R4 the segments, designed for certificates: the run cut into five segments of 20 steps, each restarted from
   the previous segment's boundary state as written (hex) and its step index, equals the continuous run bit
   for bit at every step, at native64 (control configuration), cft64 and cft128.
"""
STEPS, H = 100, "60"
W = os.path.join(g.WORK, "e8")
os.makedirs(W, exist_ok=True)


def traj(log, variant, kind, tag, extra, steps=STEPS):
    out = os.path.join(W, "%s_%s_%s.txt" % (variant, kind, tag))
    g.run([g.exe(variant), "traj", kind, steps, H, out] + extra, log)
    rows, _ = g.read_rows(out, "S")
    return {(int(r[1]), int(r[3])): r[4:10] for r in rows}, out


def main():
    log = g.Log("e8_gate", os.path.abspath(__file__), CRITERIA)
    configs = [("native64", ["--cr"], "cr"), ("native64", [], "libm"), ("native32", ["--cr"], "cr"),
               ("native32", [], "libm"), ("cft32", [], "plain"), ("cft64", [], "plain"), ("cft128", [], "plain"),
               ("cft256", [], "plain")]
    first = {}
    for kind, extra, tag in configs:
        a, _ = traj(log, "O2", kind, tag + "_1", extra)
        b, _ = traj(log, "O2", kind, tag + "_2", extra)
        c, _ = traj(log, "O0", kind, tag, extra)
        first[(kind, tag)] = a
        log.check(a == b and len(a) == 8 * (STEPS + 1), "R1 %s (%s) reproduces bit for bit across two runs (%d lane-steps)"
                  % (kind, tag, len(a)))
        log.check(a == c, "R2 %s (%s): -O0 equals -O2 bit for bit" % (kind, tag))
    for kind in ("native64", "native32"):
        f, _ = traj(log, "fast", kind, "cr", ["--cr"])
        a = first[(kind, "cr")]
        nd = sum(1 for k in a if a[k] != f[k])
        fin = sum(1 for l in range(8) if a[(STEPS, l)] != f[(STEPS, l)])
        log.check(fin >= 1, "R3 control: the contracted build differs from O2 at %s: %d of %d lane-steps, %d of 8 "
                  "lanes at the final step" % (kind, nd, len(a), fin))
    for kind, extra in (("native64", ["--cr"]), ("cft64", []), ("cft128", [])):
        cont = first[(kind, "cr" if kind.startswith("native") else "plain")]
        prev = None
        seg_states = {}
        for s0 in range(0, STEPS, 20):
            ex = extra + (["--step0", str(s0), "--from", prev] if prev else [])
            st, out = traj(log, "O2", kind, "seg%03d" % s0, ex, steps=20)
            seg_states.update(st)
            prev = out
        same = all(seg_states.get(k) == v for k, v in cont.items())
        log.check(same and len(seg_states) >= len(cont), "R4 %s: five segments restarted from their boundary states "
                  "equal the continuous run at every step" % kind)
    return log.close()


if __name__ == "__main__":
    sys.exit(main())
