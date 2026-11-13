#!/usr/bin/env python3
"""DEBRIS-C, M3: compare the Orekit runs, and the custom kernel's two builds.

  python -I -B m3_compare.py

CRITERION (stated before the data of every run but the first, jit1, whose log
m3_prop_jit1.001.log predates this script; this script fixes the criterion
for all of them): the runs
  jit1, jit2, jit3   default JIT (tiered C1 + C2), three times
  xint               -Xint (interpreter only)
  c1                 -XX:TieredStopAtLevel=1 (C1 only)
  c2                 -XX:-TieredCompilation (C2 only, after the interpreter);
                     added: it would catch a difference that only C2's
                     optimisations make, which the tiered default mixes in
must be bit-identical: the same per-step records (offset, position and
velocity of every step, as raw bits), the same SHA-256 over them, and the
same final state. Otherwise the result is the first step at which any run
differs, and the size of the difference (position, m).
NEGATIVE CONTROL (Orekit): the run "ulp" (default JIT, initial x moved up by
one ulp) must have a different step hash from jit1; reported with the first
step at which it differs and the size there and at the end.
CUSTOM SIDE: the M1a kernel's outputs over Lasser et al.'s day
(m1a/out, written by m1a/run_c.sh) for the -O2 build and the
-O2 -march=native -ffp-contract=fast build are compared by SHA-256; the
result is reported either way (this is the measurement, not a pass or fail).
Its CONTROL: the -O2 output with one ulp planted at epoch 1000 must hash
differently from the -O2 output, and differ there only. Each build's rerun
must reproduce its own hash exactly.
"""
import hashlib
import math
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out", "v2")  # version 2 runs (run_m3.sh version 2)
LOGS = os.path.join(os.path.dirname(HERE), "logs")
M1A = os.path.join(os.path.dirname(HERE), "m1a", "out")
RUNS = ["jit1", "jit2", "jit3", "xint", "c1", "c2"]


def latest_log(label):
    best = None
    for f in os.listdir(LOGS):
        m = re.match(r"%s\.(\d{3})\.log$" % re.escape("m3_prop_" + label), f)
        if m and (best is None or int(m.group(1)) > best[0]):
            best = (int(m.group(1)), f)
    assert best, label
    return os.path.join(LOGS, best[1])


def parse_log(path):
    txt = open(path, encoding="utf-8").read()
    h = re.search(r"^STEPHASH ([0-9a-f]{64})$", txt, re.M).group(1)
    fin = re.search(r"^FINAL (.*)$", txt, re.M).group(1)
    args = re.search(r"JVM args \[(.*?)\]", txt).group(1)
    sha = re.search(r"# script: .*m3_prop\.js sha256 ([0-9a-f]{64})", txt).group(1)
    return h, fin, args, sha


def steps(label):
    rows = []
    for ln in open(os.path.join(OUT, "steps_%s.txt" % label)):
        t = ln.split()
        rows.append([float.fromhex(z) for z in t[1:]])
    return rows


def first_diff(a, b):
    for k in range(min(len(a), len(b))):
        if a[k] != b[k]:
            return k
    return None if len(a) == len(b) else min(len(a), len(b))


def pos_diff(r1, r2):
    return math.sqrt(sum((r1[q] - r2[q]) ** 2 for q in (1, 2, 3)))


def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def main():
    ok = True
    info = {}
    for r in RUNS + ["ulp"]:
        lp = latest_log(r)
        h, fin, args, s = parse_log(lp)
        info[r] = (h, fin, args)
        print("%-5s %s JVM args [%s] step hash %s (%d steps; m3_prop.js %s...)"
              % (r, os.path.basename(lp), args, h, len(steps(r)), s[:12]))
    base = steps("jit1")
    print("# final state, jit1: %s" % info["jit1"][1])
    same = True
    for r in RUNS[1:]:
        s = steps(r)
        k = first_diff(base, s)
        if k is None and info[r][0] == info["jit1"][0] and info[r][1] == info["jit1"][1]:
            print("identical: %s = jit1 (every step, the hash and the final state)" % r)
        else:
            same = False
            print("DIFFERS: %s from jit1 first at step %s; |dr| there %.3e m; at the end %.3e m"
                  % (r, k, pos_diff(base[k], s[k]) if k is not None and k < len(s) else float("nan"),
                     pos_diff(base[-1], s[-1])))
    print("%s M3 Orekit criterion: the six runs are %s" % ("PASS" if same else "FAIL", "bit-identical" if same else "not bit-identical"))
    ok &= same
    u = steps("ulp")
    k = first_diff(base, u)
    ctl = info["ulp"][0] != info["jit1"][0] and k is not None
    print("%s M3 Orekit control: one ulp in the initial x %s the hash; first differing step %s (offset %s s); |dr| there %.3e m; "
          "at the end %.3e m" % ("PASS" if ctl else "FAIL", "changes" if ctl else "does NOT change", k,
                                 base[k][0] if k is not None else "-", pos_diff(base[k], u[k]) if k is not None else float("nan"),
                                 pos_diff(base[-1], u[-1])))
    ok &= ctl

    # the custom side
    f = {n: os.path.join(M1A, n) for n in ("c_O2_2_180.txt", "c_native_2_180.txt", "c_O2_2_180_rerun.txt",
                                           "c_native_2_180_rerun.txt", "c_O2_2_180_plant1000.txt")}
    h = {n: sha(p) for n, p in f.items()}
    for n in f:
        print("# %s sha256 %s" % (n, h[n]))
    rep = h["c_O2_2_180.txt"] == h["c_O2_2_180_rerun.txt"] and h["c_native_2_180.txt"] == h["c_native_2_180_rerun.txt"]
    print("%s custom: each build reproduces its own output exactly on a rerun" % ("PASS" if rep else "FAIL"))
    ok &= rep
    o2 = [ln.split() for ln in open(f["c_O2_2_180.txt"])]
    nat = [ln.split() for ln in open(f["c_native_2_180.txt"])]
    pl = [ln.split() for ln in open(f["c_O2_2_180_plant1000.txt"])]
    ndiff = sum(1 for a, b in zip(o2, nat) if a[1:4] != b[1:4])
    dmax = max(math.sqrt(sum((float.fromhex(a[q]) - float.fromhex(b[q])) ** 2 for q in (1, 2, 3))) for a, b in zip(o2, nat))
    print("MEASURED custom: -O2 and -O2 -march=native -ffp-contract=fast outputs are %s; epochs differing %d of %d; max |da| %.3e m/s^2"
          % ("bit-identical" if h["c_O2_2_180.txt"] == h["c_native_2_180.txt"] else "NOT bit-identical", ndiff, len(o2), dmax))
    pd = [i for i, (a, b) in enumerate(zip(o2, pl)) if a != b]
    ctl2 = h["c_O2_2_180.txt"] != h["c_O2_2_180_plant1000.txt"] and pd == [1000]
    print("%s custom control: the one-ulp plant at epoch 1000 changes the hash, and only epoch %s differs" % ("PASS" if ctl2 else "FAIL", pd))
    ok &= ctl2
    print("# M3 %s" % ("PASS" if ok else "FAIL"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
