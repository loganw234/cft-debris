"""q2_refusals.py - DEBRIS-D, Q2 (cft-debris, MIT): v1's refusals that bear on a
debris propagator, each compiled from a two-line source and held to the name
LANGUAGE.md gives it ("Refused in v1", lines 870-882):
  pow(x, 2)               -> transcendental
  sin(t), t undeclared    -> time-dependence
  x ^ 2                   -> power
  stormer-verlet with drag (systems/j2dragrot-sv.cftl) -> verlet-not-separable
CRITERION (before the data): each compile exits 3 with `cftc: refused <name>` and the name above.
usage: python -I -B q2_refusals.py
"""
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tools"))
import dd  # noqa: E402

CASES = [("transcendental", "state x\nd/dt x = pow(x, 2)\nstep rk4, h = 1\n"),
         ("time-dependence", "state x\nd/dt x = sin(t)\nstep rk4, h = 1\n"),
         ("power", "state x\nd/dt x = x ^ 2\nstep rk4, h = 1\n")]


def main():
    log = dd.Log(__file__, "q2_refusals")
    log.criteria("each compile exits 3 and names the refusal LANGUAGE.md gives: transcendental, time-dependence, "
                 "power, verlet-not-separable")
    work = dd.SCRATCH + "/work/refusals"
    os.makedirs(work, exist_ok=True)
    jobs = []
    for k, (name, body) in enumerate(CASES):
        p = "%s/case%d.cftl" % (work, k)
        open(p, "w", newline="\n").write("system c%d\nformat fp64\nround rne\n" % k + body)
        jobs.append((name, p))
    jobs.append(("verlet-not-separable", os.path.join(dd.ROOT, "systems", "j2dragrot-sv.cftl")))
    for name, p in jobs:
        r = subprocess.run([dd.PY, "-I", "-B", dd.FP256 + "/python/cftc", p, "--steps", "1", "--out", work],
                           capture_output=True, text=True)
        m = re.search(r"cftc: refused ([a-z0-9-]+): (.*)", r.stderr)
        got = m.group(1) if m else None
        log.check(r.returncode == 3 and got == name, "%s: exit %d, refused %s: %s" %
                  (os.path.basename(p), r.returncode, got, m.group(2).strip()[-140:] if m else r.stderr.strip()[:200]))
    rc = log.close()
    sys.exit(1 if rc else 0)


if __name__ == "__main__":
    main()
