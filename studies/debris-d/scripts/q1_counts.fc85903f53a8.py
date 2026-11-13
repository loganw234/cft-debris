"""q1_counts.py - DEBRIS-D, Q1's counting builds and their two controls
(cft-debris, MIT).

Builds (or reuses) build/count_ops.exe and build/count_ops_plant.exe from
count_ops.cpp and make_count_build.py's two count_kernels.inc, runs both,
and asserts:
  C1. the hand count for degree 2 (J2 and the degree-2 tesserals in
      DEBRIS-C's normalised kernel), derived by hand from m1a_grav.c's
      grav() before the build was first run: 104 multiplications, 37
      additions and subtractions, 3 divisions, 1 square root, nothing else;
  C2. the planted build differs from the plain one by exactly 2
      multiplications and 1 subtraction a degree summed (n = 2..N), and in
      nothing else, for every degree counted; every other kernel's line is
      unchanged.
The hand count, per piece (m1a_grav.c's grav() with nmin = nmax = 2, L = 3):
  preamble   r2: 3 mul 2 add; ir2: 1 div; rho: 2 mul; x0, y0, z0: 6 mul;
             V00: 1 sqrt 1 div
  recursion  m=0: 3 mul, then n=2,3: 6 mul 2 sub each; m=1: 6 mul 2 add,
             3 mul, n=3: 6 mul 2 sub; m=2: 6 mul 2 add, 3 mul; m=3: 6 mul
             2 add -> 45 mul 12 add
  sums       n=2, m=0: 6 mul 3 sub; m=1,2: 19 mul 10 add each -> 44 mul 23 add
  scale      k: 1 mul 1 div; a: 3 mul
  total      104 mul, 37 add, 3 div, 1 sqrt
The build was first run once by hand at about 21:10 while its compile
errors were fixed; this script, with the criteria above, was written after
that run and re-runs both builds.
"""
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tools"))
import dd  # noqa: E402

HAND = {"add": 37, "mul": 104, "div": 3, "sqrt": 1}
KEYS = ["add", "mul", "div", "sqrt", "neg", "cmp", "exp", "log", "pow", "sin", "cos", "tan", "asin", "acos",
        "atan", "atan2", "fmod"]


def parse(out):
    rows = {}
    for ln in out.strip().splitlines():
        m = re.match(r"(.+?)\s+fma_class\s+(\d+) \(add (\d+) mul (\d+)\)(.*)", ln)
        name = m.group(1).strip()
        d = {"add": int(m.group(3)), "mul": int(m.group(4))}
        for k, v in re.findall(r"(\w+) (\d+)", m.group(5)):
            d[k] = int(v)
        rows[name] = d
    return rows


def main():
    log = dd.Log(__file__, "q1_counts")
    log.criteria("C1 degree 2 equals the hand count: add 37, mul 104, div 3, sqrt 1, every other class 0",
                 "C2 the planted build adds exactly 2 mul and 1 add per degree summed (n = 2..N) to each gravity "
                 "line, changes no other class, and leaves every non-gravity line unchanged")
    b = dd.SCRATCH + "/build"
    for exe in ("count_ops.exe", "count_ops_plant.exe"):
        log.w("%s sha256 %s" % (exe, dd.sha256_file(b + "/" + exe)))
    for inc in ("q1/count_kernels.inc", "q1/plant/count_kernels.inc"):
        log.w("%s sha256 %s" % (inc, dd.sha256_file(dd.SCRATCH + "/" + inc)))
    for src in ("count_ops.cpp", "make_count_build.py"):
        log.w("%s sha256 %s" % (src, dd.sha256_file(os.path.join(os.path.dirname(os.path.abspath(__file__)), src))))
    plain = subprocess.run([b + "/count_ops.exe"], capture_output=True, text=True).stdout
    plant = subprocess.run([b + "/count_ops_plant.exe"], capture_output=True, text=True).stdout
    for ln in plain.strip().splitlines():
        log.w("  " + ln)
    P, Q = parse(plain), parse(plant)
    d2 = P["gravity degree 2 (2..2)"]
    ok = all(d2.get(k, 0) == HAND.get(k, 0) for k in KEYS)
    log.check(ok, "C1 degree 2: counted %s against the hand count %s" %
              ({k: d2.get(k, 0) for k in KEYS if d2.get(k, 0)}, HAND))
    for name in P:
        m = re.match(r"gravity degree (\d+)", name)
        if m:
            N = int(m.group(1))
            nd = N - 1
            exp = dict(P[name])
            exp["mul"] += 2 * nd
            exp["add"] += nd
            log.check(Q[name] == exp, "C2 %s: plant adds %d mul and %d add (got mul +%d add +%d, other classes %s)"
                      % (name, 2 * nd, nd, Q[name]["mul"] - P[name]["mul"], Q[name]["add"] - P[name]["add"],
                         "unchanged" if all(Q[name][k] == P[name][k] for k in KEYS if k not in ("add", "mul"))
                         else "CHANGED"))
        else:
            log.check(Q[name] == P[name], "C2 %s unchanged by the plant" % name)
    rc = log.close()
    sys.exit(1 if rc else 0)


if __name__ == "__main__":
    main()
