# e1_fma.py - cft-debris M1, E1's finding on record: this host's fma, the C
# library's routine against the instruction, each held to libcft's CFT_FMA and
# to exact rational arithmetic. A finding, not a gate.
# cft-debris, MIT licence (see LICENSE at the repository root). Written by
# DEBRIS-E, 2026-11-13.
#
#   python -I -B tests/e1_fma.py
#
# The cases are the lead's 20,000 (cft-debris-ledger\tools\fmacheck\fmacheck.c,
# a seeded xorshift64): its source is compiled here in the scratch, without and
# with -mfma, and tests/fmacheck.c (built by tests/build.sh the same two ways)
# regenerates the same cases and adds the unfused a*b + c and libcft's CFT_FMA.
import os
import sys
from fractions import Fraction

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gatelib as g  # noqa: E402

CRITERIA = """
F1 the cases are the lead's: tests/fmacheck.c's a, b, c equal, case for case, those of the lead's generator
   compiled here (20,000 cases), and each build's fma() result equals the lead's same build's.
F2 the reference: libcft's CFT_FMA equals round-to-nearest-even(a*b + c), computed exactly (Fraction), on
   every case. (If it did not, holding the native results to it would mean nothing.)
F3 CONTROL (the checker can fail): the unfused a*b + c, two roundings, must be reported not correctly rounded
   on at least one case, and the count is reported.
FINDING (no pass condition): for the build without -mfma (the C library's fma) and with it (vfmadd), the
   number of cases not correctly rounded, and the number that differ from CFT_FMA.
"""
LEAD_SRC = "C:/Users/logan/source/repos/cft-debris-ledger/tools/fmacheck/fmacheck.c"
GCC = "C:/msys64/mingw64/bin/gcc.exe"


def parse(text):
    rows = []
    for ln in text.splitlines():
        if not ln or ln.startswith("#"):
            continue
        rows.append([float.fromhex(t) for t in ln.split()])
    return rows


def main():
    log = g.Log("e1_fma", os.path.abspath(__file__), CRITERIA)
    wd = os.path.join(g.WORK, "e1_fma").replace("\\", "/")
    os.makedirs(wd, exist_ok=True)
    log.w("# the lead's generator %s sha256 %s" % (LEAD_SRC, g.sha256(LEAD_SRC)))
    env_path = "C:/msys64/mingw64/bin;" + os.environ.get("PATH", "")
    os.environ["PATH"] = env_path
    lead = {}
    for tag, flags in (("nofma", []), ("fma", ["-mfma"])):
        out = wd + "/lead_fmacheck_%s.exe" % tag
        g.run([GCC, "-O2", "-ffp-contract=off"] + flags + [LEAD_SRC, "-o", out, "-lm"], log)
        lead[tag] = parse(g.run([out], log).stdout.decode())
    ours = {}
    for tag in ("nofma", "fma"):
        p = g.run([os.path.join(g.BUILD, "fmacheck_%s.exe" % tag)], log)
        ours[tag] = parse(p.stdout.decode())
        log.w("# fmacheck_%s.exe sha256 %s" % (tag, g.sha256(os.path.join(g.BUILD, "fmacheck_%s.exe" % tag))))
    n = len(ours["fma"])
    ok1 = n == 20000 and all(len(ours[t]) == n and len(lead[t]) == n for t in ours)
    ok1 = ok1 and all(ours[t][i][:3] == lead[t][i][:3] and ours[t][i][3] == lead[t][i][3]
                      for t in ("nofma", "fma") for i in range(n))
    ok1 = ok1 and all(ours["nofma"][i][:3] == ours["fma"][i][:3] for i in range(n))
    log.check(ok1, "F1 the same %d cases as the lead's generator, and the same fma() results build for build" % n)
    wrong = {"nofma": 0, "fma": 0, "unfused": 0, "cft": 0}
    vs_cft = {"nofma": 0, "fma": 0}
    first = {}
    for i in range(n):
        a, b, c, r0, u, x = ours["nofma"][i]
        r1 = ours["fma"][i][3]
        want = float(Fraction(a) * Fraction(b) + Fraction(c))
        for tag, v in (("nofma", r0), ("fma", r1), ("unfused", u), ("cft", x)):
            if v != want:
                wrong[tag] += 1
                first.setdefault(tag, (a.hex(), b.hex(), c.hex(), v.hex(), want.hex()))
        vs_cft["nofma"] += r0 != x
        vs_cft["fma"] += r1 != x
    log.check(wrong["cft"] == 0, "F2 libcft's CFT_FMA is correctly rounded on %d of %d cases" % (n - wrong["cft"], n))
    log.check(wrong["unfused"] >= 1, "F3 control: the unfused a*b + c is reported wrong on %d of %d cases (first: %s)"
              % (wrong["unfused"], n, first.get("unfused")))
    log.w("MEASURED FINDING: without -mfma (the C library's fma): %d of %d not correctly rounded; %d differ from "
          "CFT_FMA; first: a b c got want = %s" % (wrong["nofma"], n, vs_cft["nofma"], first.get("nofma")))
    log.w("MEASURED FINDING: with -mfma (vfmadd): %d of %d not correctly rounded; %d differ from CFT_FMA"
          % (wrong["fma"], n, vs_cft["fma"]))
    return log.close()


if __name__ == "__main__":
    sys.exit(main())
