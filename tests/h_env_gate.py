# h_env_gate.py - cft-debris M1 (DEBRIS-H), control C17: m1f's downloads folder, whatever the caller's environment holds.
# Standard library only; on amd-arc-box (the lead's, before the seed) and on the desktop.
# cft-debris, MIT licence (see LICENSE at the repository root). Written by DEBRIS-H, 2026-11-18, after the box's first H6
# run, in which every m1f fit exited 3 ("gfc: cannot open" the desktop's path, the default compiled into tests/m1f.c),
# because tests/h_seed.py passed its children no M1_DOWNLOADS.
#
#   python3 -I -B in/tests/h_env_gate.py <root> --java JAVA [--logs DIR] [--keep DIR] [--cpu TSV]
import argparse
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import h_lib as H  # noqa: E402

SCRIPT = os.path.abspath(__file__)
BOGUS = "no-such-downloads/"

CRITERIA = """
C17 (the lead's request of 2026-11-18): tests/h_seed.py fit, on one object (the test seed's object 0, from S0, with
DEBRIS-F's table, --no-catchup), run three times from <root>:
 (i)   M1_DOWNLOADS=no-such-downloads/ in the environment it inherits: it must pass (every m1f fit exits 0), its m1f
       reading in/dl/, the default of its --downloads, which it gives every m1f as M1_DOWNLOADS;
 (ii)  no M1_DOWNLOADS in the environment it inherits: it must pass;
 (iii) as (i) with the fix withdrawn (--downloads-inherit: m1f inherits the environment as it is): it must FAIL, its
       log naming m1f's "gfc: cannot open" - the control that bites on the property itself;
 and (i) and (ii) must give the same fit, bit for bit.
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root")
    ap.add_argument("--java", required=True)
    ap.add_argument("--logs", default="logs")
    ap.add_argument("--keep")
    ap.add_argument("--cpu")
    a = ap.parse_args()
    os.chdir(a.root)
    here = os.path.relpath(os.path.dirname(SCRIPT))
    cpu = H.CpuAccount("h_env_gate", a.cpu)
    log = H.Log("h_env_gate", a.logs, SCRIPT, CRITERIA, extra=[os.path.join(here, "h_seed.py")], keep_dir=a.keep)
    cat = H.read_seed("in/testseed/seed1.txt")["rows"][0][0]
    _, W = H.next_numbered("c17", "run", "")
    os.makedirs(W)
    m1f = "build/m1f" + (".exe" if H.WIN else "")
    log.w("# m1f sha256 %s; in/dl/ holds %s" % (H.sha256(m1f), ", ".join(sorted(os.listdir("in/dl")))))
    res = {}
    for tag, env_dl, extra in (("i", BOGUS, []), ("ii", None, []), ("iii", BOGUS, ["--downloads-inherit"])):
        env = dict(os.environ)
        env.pop("M1_DOWNLOADS", None)
        if env_dl is not None:
            env["M1_DOWNLOADS"] = env_dl
        od = os.path.join(W, tag)
        argv = [sys.executable, "-I", "-B", os.path.join(here, "h_seed.py"), "fit", "--seed", "1", "--gp", "in/gp", "--tag", "S0", "--ts",
                "2026-11-17T00:00:00", "--table", "in/frame_f.bin", "--m1f", m1f, "--java", a.java, "--jars", "in/jars", "--orekit", "in/orekit",
                "--decoder", "in/tests/f5_sgp4.js", "--leaps", "in/orekit/tai-utc.dat", "--out", od, "--logs", os.path.join(W, "logs_" + tag),
                "--procs", "1", "--jprocs", "1", "--test", "--no-catchup", "--select", str(cat)] + extra
        p = subprocess.run(argv, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=env)
        out = p.stdout.decode("utf-8", "replace")
        fit = None
        tp = os.path.join(od, "fit1.001.tsv")
        if os.path.exists(tp):
            fit = [ln for ln in open(tp, encoding="ascii") if not ln.startswith("#")][1:]
        res[tag] = (p.returncode, out, fit)
        log.w("# (%s) inherited M1_DOWNLOADS %r%s: exit %d; %s" % (tag, env_dl, " and --downloads-inherit" if extra else "", p.returncode,
                                                               "a fit table" if fit else "no fit table"))
    log.check(res["i"][0] == 0 and res["i"][2] and "m1f's downloads in/dl/" in res["i"][1],
              "(i) with no-such-downloads/ inherited, the fix gives m1f in/dl/ and the fit passes")
    log.check(res["ii"][0] == 0 and res["ii"][2], "(ii) with no M1_DOWNLOADS inherited, the fit passes")
    log.check(res["i"][2] == res["ii"][2], "(i) and (ii) give the same fit, bit for bit")
    log.check(res["iii"][0] != 0 and "gfc: cannot open" in res["iii"][1] and not res["iii"][2],
              "C17 (iii) with the fix withdrawn, m1f reads the inherited no-such-downloads/ and the run fails (gfc: cannot open) - failed as specified")
    c_ = cpu.close("h_env_gate log %03d" % log.n)
    if c_ is not None:
        log.w("# CPU: %.2f s by cycles / 2.5e9 (this script and every process it started)" % c_)
    return log.close()


if __name__ == "__main__":
    sys.exit(main())
