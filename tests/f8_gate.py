# f8_gate.py - cft-debris M1 (DEBRIS-F), gate F8: reproducibility in the real frame, and the regression against
# DEBRIS-E in the uniform-rotation mode.
# cft-debris, MIT licence (see LICENSE at the repository root). Written by DEBRIS-F, 2026-11-16.
#
#   python -I -B tests/f8_gate.py [table]
import math
import os
import sys
from fractions import Fraction

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import f_lib as F  # noqa: E402

CRITERIA = """
THE REAL FRAME: E8's arc - its eight lanes (tests/m1f.c, DEBRIS-E's LANES8), 100 rk4 steps of 60 s - from origin
  t0 = 1,000,000 s TDB (2026-10-27, inside the window's table), every force at degree 20, ending on one short step of
  37.5 s (tests/m1f.c traj --short 37.5), at native64, cft64 and cft128 (and native32 and cft32 for R1 and R2).
R1 two runs of the same build agree bit for bit at every step (the NaN rule).
R2 -O0 equals -O2 bit for bit at every step.
R3 five segments of 20 steps, each restarted from the previous boundary's hex state (--step0, --from), the last one
   ending on the short step, equal the continuous run at every step, at native64, cft64 and cft128.
C1 NEGATIVE CONTROL: segment 3 restarted from a boundary state with one ulp added to lane 3's z must differ from the
   continuous run in lane 3, at every step from its start to the end, and in no other lane; at native64, cft64 and
   cft128.
THE REGRESSION, uniform-rotation mode (model.frame = 0, t0 = 0): DEBRIS-E's own driver, tests/m1run.c, unchanged,
  built against this src/ (m1run_O2.exe) against the same driver built from DEBRIS-E's sources as they stood at
  commit 183c7049 (this round's scratch build build/e_baseline, made before any src/ change; its build log lists the
  sources' SHA-256, which are compared here with DEBRIS-E's build.003.log):
G1 E2's trajectories: traj, 100 steps of 60 s, 8 lanes, at native64, native32, cft64, cft32, cft128 and native64 --cr:
   the output files identical byte for byte.
G2 E4's outputs at a sample of epochs: lasser (gravity, degrees 2..180) and lasser3 (the tides) at native64 over all
   2,880 epochs and at cft64 every 30th epoch: identical byte for byte; and, from native64's, the maxima E4's log
   prints are reproduced to its printed digits: gravity 2.281e-15 m/s^2 at epoch 1789, the Sun 1.263e-17 at 388, the
   Moon 4.342e-16 at 208 (studies/debris-e/logs/e4_gate.001.log).
C2 NEGATIVE CONTROL: E2's trajectory at native64 with E2's own plant (one ulp in lane 3's z, --plant 3 --plant-comp 2)
   from the new build must differ from the baseline's unplanted run.
"""

TABLE = sys.argv[1] if len(sys.argv) > 1 else F.DATA + "/tables/frame_main.bin"
T0 = "1000000"
BASE = F.SCRATCH + "/build/e_baseline"


def traj_rows(path):
    out = {}
    for ln in open(path):
        if ln.startswith("S "):
            p = ln.split()
            out[(int(p[1]), int(p[3]))] = p[4:10]
    return out


def same_rows(a, b, nb, keys=None):
    keys = keys if keys is not None else sorted(set(a) | set(b))
    bad = [k for k in keys if k not in a or k not in b or not all(F.G.same(x, y, nb) for x, y in zip(a[k], b[k]))]
    return bad


def main():
    log = F.Log("f8_gate", os.path.abspath(__file__), CRITERIA)
    W = F.WORK + "/f8"
    os.makedirs(W, exist_ok=True)
    ex = {v: F.BUILD + "/m1f_%s.exe" % v for v in ("O2", "O0")}
    for v, p in ex.items():
        log.w("# m1f_%s.exe sha256 %s" % (v, F.sha256(p)))
    log.w("# table %s sha256 %s" % (TABLE, F.sha256(TABLE)))
    nb = {"native64": 64, "cft64": 64, "cft128": 128, "native32": 32, "cft32": 32}
    # R1, R2
    for kind in ("native64", "cft64", "cft128", "native32", "cft32"):
        runs = {}
        for tag, exe in (("a", ex["O2"]), ("b", ex["O2"]), ("O0", ex["O0"])):
            o = W + "/real_%s_%s.txt" % (kind, tag)
            F.run([exe, "traj", kind, TABLE, T0, "100", "60", o, "--short", "37.5"], log, cpu_label="f8_%s_%s" % (kind, tag))
            runs[tag] = traj_rows(o)
        n = len(runs["a"])
        log.check(n == 102 * 8, "%s: the run holds 102 boundaries x 8 lanes, the short step's included (%d)" % (kind, n))
        last = max(k[0] for k in runs["a"])
        tlast = [ln.split()[2] for ln in open(W + "/real_%s_a.txt" % kind) if ln.startswith("S %d " % last)][0]
        log.check(float.fromhex(tlast) == 1000000.0 + 6000.0 + 37.5, "%s: the last state lands on t0 + 6000 + 37.5 s exactly (%s)" % (kind, tlast))
        log.check(not same_rows(runs["a"], runs["b"], nb[kind]), "R1 %s: two runs agree at every step" % kind)
        log.check(not same_rows(runs["a"], runs["O0"], nb[kind]), "R2 %s: -O0 equals -O2 at every step" % kind)
        if kind in ("native64", "cft64", "cft128"):
            # R3: five segments
            seg = {}
            prev = None
            for s in range(5):
                o = W + "/seg_%s_%d.txt" % (kind, s)
                args = [ex["O2"], "traj", kind, TABLE, T0, "20", "60", o, "--step0", str(20 * s)]
                if s:
                    args += ["--from", prev]
                if s == 4:
                    args += ["--short", "37.5"]
                F.run(args, log, cpu_label="f8_%s_seg%d" % (kind, s))
                seg.update(traj_rows(o))
                prev = o
            log.check(not same_rows(seg, runs["a"], nb[kind]) and len(seg) == n, "R3 %s: five restarted segments equal the continuous run at every step" % kind)
            # C1: segment 3 from a planted boundary
            src = W + "/seg_%s_2.txt" % kind
            pl = W + "/seg_%s_2_planted.txt" % kind
            esz = {64: 8, 128: 16}[nb[kind]]
            with open(src) as f, open(pl, "w", newline="\n") as g:
                for ln in f:
                    p = ln.split()
                    if ln.startswith("S 60 ") and p[3] == "3":
                        v = int(p[6], 16) + 1      # one ulp up in z (positive, finite)
                        p[6] = "%0*x" % (2 * esz, v)
                        ln = " ".join(p) + "\n"
                    g.write(ln)
            o = W + "/seg_%s_3_planted.txt" % kind
            F.run([ex["O2"], "traj", kind, TABLE, T0, "20", "60", o, "--step0", "60", "--from", pl], log, cpu_label="f8_%s_ctl" % kind)
            c = traj_rows(o)
            lanes_bad = sorted({k[1] for k in same_rows(c, runs["a"], nb[kind], keys=sorted(c))})
            steps3 = sorted({k[0] for k in same_rows(c, runs["a"], nb[kind], keys=sorted(c)) if k[1] == 3})
            log.check(lanes_bad == [3] and steps3 == list(range(60, 81)),
                      "C1 %s FAILS as specified: the planted restart differs in lane 3 alone, at every step 60..80" % kind)
    # THE REGRESSION
    blog = open(F.WORK + "/build_e_baseline.log").read()
    elog = open(os.path.join(F.REPO, "studies", "debris-e", "logs", "build.003.log")).read()
    def src_hashes(txt):
        out = {}
        for ln in txt.splitlines():
            p = ln.split()
            name = p[1].lstrip("*") if len(p) == 2 else ""
            if len(p[0]) == 64 and (name.startswith("src/") or name.startswith("tests/")):
                out[name] = p[0]
        return out
    hb, he = src_hashes(blog), src_hashes(elog)
    log.w("# the baseline build compiled %d sources; DEBRIS-E's build.003.log lists %d" % (len(hb), len(he)))
    log.check(len(hb) > 10 and hb == he, "the baseline's sources are DEBRIS-E's final build's, hash for hash")
    newx, oldx = F.BUILD + "/m1run_O2.exe", BASE + "/m1run_O2.exe"
    log.w("# m1run_O2.exe (new) sha256 %s; baseline m1run_O2.exe sha256 %s" % (F.sha256(newx), F.sha256(oldx)))
    for kind, extra in (("native64", []), ("native32", []), ("cft64", []), ("cft32", []), ("cft128", []), ("native64", ["--cr"])):
        tag = kind + ("_cr" if extra else "")
        a, b = W + "/e2_new_%s.txt" % tag, W + "/e2_old_%s.txt" % tag
        F.run([newx, "traj", kind, "100", "60", a] + extra, log, cpu_label="f8_e2_new_%s" % tag)
        F.run([oldx, "traj", kind, "100", "60", b] + extra, log, cpu_label="f8_e2_old_%s" % tag)
        log.check(open(a, "rb").read() == open(b, "rb").read(), "G1 E2 %s: the new build's trajectory equals the baseline's byte for byte" % tag)
    for mode, kind, stride in (("lasser", "native64", 1), ("lasser3", "native64", 1), ("lasser", "cft64", 30), ("lasser3", "cft64", 30)):
        a, b = W + "/e4_new_%s_%s.txt" % (mode, kind), W + "/e4_old_%s_%s.txt" % (mode, kind)
        args = [mode, kind, str(stride)] + (["2", "180"] if mode == "lasser" else [])
        F.run([newx] + args + [a], log, cpu_label="f8_e4_new_%s_%s" % (mode, kind))
        F.run([oldx] + args + [b], log, cpu_label="f8_e4_old_%s_%s" % (mode, kind))
        log.check(open(a, "rb").read() == open(b, "rb").read(), "G2 E4 %s %s (every %d epoch): identical byte for byte" % (mode, kind, stride))
    # DEBRIS-E's read_lasser and maxdiff (tests/e4_gate.py, cft-debris's own, MIT), copied here: version 1 of this script
    # imported e4_gate, whose module-level os.makedirs pointed at DEBRIS-E's scratch (an existing folder; nothing was
    # written there: its modification time stayed 2026-11-13 06:33:07)
    class E4:
        @staticmethod
        def read_lasser(path):
            rows = []
            for ln in open(path, "r", encoding="ascii", errors="replace"):
                t = ln.split()
                if len(t) == 4 and not ln.startswith("#"):
                    try:
                        rows.append((t[0], Fraction(t[1]), Fraction(t[2]), Fraction(t[3])))
                    except ValueError:
                        pass
            return rows

        @staticmethod
        def maxdiff(rows, ref, nb, cols):
            worst, at = 0.0, None
            for r in rows:
                e = int(r[0])
                a = [F.G.value(h, nb) for h in r[2 + cols[0]:2 + cols[1]]]
                d = [a[i] - ref[e][1 + i] for i in range(3)]
                n = math.sqrt(float(sum(x * x for x in d)))
                if n > worst:
                    worst, at = n, e
            return worst, at
    D = F.DOWNLOADS
    LG = E4.read_lasser(D + "02gravityfield_itrf.txt/02gravityfield_itrf.txt")
    LS = E4.read_lasser(D + "03directTideSun_icrf.txt/03directTideSun_icrf.txt")
    LM = E4.read_lasser(D + "03directTideMoon_icrf.txt/03directTideMoon_icrf.txt")
    rg, _ = F.G.read_rows(W + "/e4_new_lasser_native64.txt")
    rt, _ = F.G.read_rows(W + "/e4_new_lasser3_native64.txt")
    dg, eg = E4.maxdiff(rg, LG, 64, (0, 3))
    ds, es = E4.maxdiff(rt, LS, 64, (0, 3))
    dm, em = E4.maxdiff(rt, LM, 64, (3, 6))
    got = ("%.3e" % dg, eg, "%.3e" % ds, es, "%.3e" % dm, em)
    log.w("# G2 recomputed from the new build: gravity %s at epoch %s, Sun %s at %s, Moon %s at %s" % got)
    log.check(got == ("2.281e-15", 1789, "1.263e-17", 388, "4.342e-16", 208), "G2 the maxima E4's log prints are reproduced to its digits")
    # C2
    a, b = W + "/e2_new_native64_planted.txt", W + "/e2_old_native64.txt"
    F.run([newx, "traj", "native64", "100", "60", a, "--plant", "3", "--plant-comp", "2"], log, cpu_label="f8_c2")
    log.check(open(a, "rb").read() != open(b, "rb").read(), "C2 FAILS as specified: the planted run differs from the baseline's")
    return log.close()


if __name__ == "__main__":
    sys.exit(main())
