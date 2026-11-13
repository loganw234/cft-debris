"""q2_degree_sweep.py - DEBRIS-D, Q2 (cft-debris, MIT): the largest degree of
gen_field.py's field (coefficients as params, in the 512-slot bank) that cftc
compiles for the `sw` target at its 256 scratch slots - the depth hip:N fixes
- at fp64, fp128 and fp256, with each refusal by name.

Each compile runs under a 120 s timeout (the lead's condition: cheap, each well
under a minute; a timeout is reported, not retried).
CRITERION (stated before the data): none is asserted on the outcome, which is
the measurement; the script asserts only that every compile either succeeds
(exit 0, a manifest with scratch_declared 256) or is refused by name (exit 3,
a `cftc: refused <name>` line), and reports anything else as a failure.

usage: python -I -B q2_degree_sweep.py <degree> [<degree> ...]
"""
import json
import os
import re
import subprocess
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tools"))
import dd  # noqa: E402

GEN = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gen_field.py")
SYSDIR = os.path.join(dd.ROOT, "systems")
OUT = dd.SCRATCH + "/images/sweep"


def main():
    degs = [int(x) for x in sys.argv[1:]]
    log = dd.Log(__file__, "q2_degree_sweep")
    log.criteria("every compile ends in exit 0 with a manifest declaring 256 scratch slots, or in exit 3 with a "
                 "refusal named on a `cftc: refused <name>` line; a timeout (120 s) or anything else is a FAIL")
    os.makedirs(OUT, exist_ok=True)
    for N in degs:
        src = os.path.join(SYSDIR, "field%d-rk4.cftl" % N)
        if not os.path.exists(src):
            subprocess.run([dd.PY, "-I", "-B", GEN, str(N), src], check=True, capture_output=True)
        log.w("degree %d: source %s sha256 %s" % (N, os.path.basename(src), dd.sha256_file(src)))
        for fmt in ("fp64", "fp128", "fp256"):
            stem = "field%d-rk4-%s-sw256" % (N, fmt)
            cmd = [dd.PY, "-I", "-B", dd.FP256 + "/python/cftc", src, "--steps", "24", "--format", fmt,
                   "--out", OUT, "--stem", stem]
            t0 = time.perf_counter()
            try:
                r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            except subprocess.TimeoutExpired:
                log.check(False, "degree %d %s: timed out at 120 s" % (N, fmt))
                continue
            dt = time.perf_counter() - t0
            if r.returncode == 0:
                m = json.load(open(os.path.join(OUT, stem + ".manifest.json")))
                u = m["uses"]
                ok = u["scratch_declared"] == 256
                log.check(ok, "degree %d %s: COMPILES in %.1f s: %d instructions a step, scratch %d of %d, bank %d of 512, "
                          "features %s" % (N, fmt, dt, m["per_step"]["instructions"], u["scratch_slots"],
                                           u["scratch_declared"], u["bank_slots"], ",".join(u["features"])))
            elif r.returncode == 3:
                mm = re.search(r"cftc: refused ([a-z0-9-]+): [^:]+(?::\d+)?: (.*)", r.stderr.strip().replace("\n", " "))
                log.check(mm is not None, "degree %d %s: REFUSED %s in %.1f s: %s" %
                          (N, fmt, mm.group(1) if mm else "?", dt, mm.group(2) if mm else r.stderr.strip()))
            else:
                log.check(False, "degree %d %s: exit %d: %s" % (N, fmt, r.returncode, r.stderr.strip()[:300]))
    rc = log.close()
    sys.exit(1 if rc else 0)


if __name__ == "__main__":
    main()
