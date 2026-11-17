# g_f9data.py - cft-debris M1 (DEBRIS-G), phase 2: does the cost of a step depend on the objects' states?
# cft-debris, MIT licence (see LICENSE at the repository root). Written by DEBRIS-G, 2026-11-17.
#
#   python -I -B tests/g_f9data.py <root with in/ and build/m1g> <out>
#
# WHY: G4's W=1, L=64 runs came out at 0.917 to 0.951 of F9's figures for native64-cr and the cft kinds. F9 (tests/m1f.c's
# time mode) filled its lanes from the 8 hand-set states of DEBRIS-E's LANES8, repeated, several with exact zeros; G4's
# lanes are the population's. This runs m1g (the G4 driver) at 1 worker and 64 lanes on (a) the first 64 population objects and
# (b) LANES8 repeated 8 times, with the same t0, so that only the states, bc and cram differ; alternating the order, twice.
# A DESKTOP, FUNCTIONAL comparison: only the RATIO of two back-to-back runs on the same machine is read, and no time here is
# a measurement of M1's speed. CRITERION fixed before the data: the cost ratio (population / LANES8, per step, by the
# process's cycles) is reported with its two repeats; "the states move the cost" is read only if both repeats of a kind
# agree on the side of 1.0 and differ from 1.0 by more than the repeats differ from each other.
import os
import subprocess
import sys

LANES8 = [
    (("6778136.3", "0.0", "0.0", "-0.0", "4763.308132757748", "6009.79917725315"), "0.011", "0.02"),
    (("4727067.458866317", "3431293.8886403306", "3338992.8961416413", "-2427.16246539213", "-3097.617308706853", "6619.419907658179"), "0.005", "0.01"),
    (("-4558081.580743138", "4295834.082553983", "2842263.3234511204", "-4439.039075485846", "-5911.6932581067085", "1816.2114308748667"), "0.02", "0.03"),
    (("903678.4634067558", "521739.0041087581", "6899676.7944407435", "3777.043324987265", "-6542.030941266833", "4.573536163795741e-13"), "0.008", "0.015"),
    (("2353437.148945508", "-3516052.054593197", "5359305.632890503", "6769.953149445514", "-745.9542878719845", "-3462.2905682322225"), "0.015", "0.025"),
    (("6970601.661523341", "-1229100.4045408047", "6176.8360310422495", "1304.412232270023", "7397.660848372243", "-11.354062572265523"), "0.012", "0.012"),
    (("3464068.150000003", "5999942.036681126", "8.401949178997247e-10", "-914.2113563995073", "527.82017271347", "-7511.271351578038"), "0.006", "0.028"),
    (("-3369375.9914005348", "5348893.427315517", "-2389362.0029564826", "-3964.7088578513403", "-4598.271207866931", "-4702.9574373125815"), "0.018", "0.018"),
]
CASES = [("native64-cr", 20), ("cft64", 3), ("cft256", 2)]


def run(root, kind, pop, steps, tag, out):
    k = kind.replace("-cr", "")
    argv = [os.path.abspath(os.path.join(root, "build", "m1g.exe")), "run", "--kind", k, "--table", os.path.join(root, "in", "frame_main.bin"),
            "--pop", pop, "--first", "0", "--count", "64", "--lanes", "64", "--steps", str(steps), "--out", out, "--tag", tag]
    if kind.endswith("-cr"):
        argv.append("--cr")
    env = dict(os.environ)
    env["M1_DOWNLOADS"] = os.path.join(root, "in", "dl") + "/"
    p = subprocess.Popen(argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE, env=env)
    while True:
        ln = p.stdout.readline().decode().strip()
        if ln == "READY":
            break
        if not ln and p.poll() is not None:
            raise SystemExit("worker died")
    p.stdin.write(b"G")
    p.stdin.flush()
    rep = {}
    for raw in p.stdout:
        ln = raw.decode().strip()
        if ln == "TIMED_DONE":
            p.stdin.write(b"Q")
            p.stdin.flush()
        if ln.startswith("REPORT "):
            a, _, b = ln[7:].partition(" ")
            rep[a] = b
    p.wait()
    assert p.returncode == 0 and rep.get("end_checks_ok") == "1"
    return (int(rep["cpu_end_ns"]) - int(rep["cpu_start_ns"])) / 1e9 / steps


def main():
    root, out = sys.argv[1], sys.argv[2]
    os.makedirs(out, exist_ok=True)
    l8 = os.path.join(out, "lanes8_pop.txt")
    with open(l8, "xb") as f:
        for i in range(64):
            y, bc, cram = LANES8[i % 8]
            v = [1468800.0] + [float(x) for x in y] + [float(bc), float(cram)]
            f.write(("%d 0 0 %s\n" % (i, " ".join(x.hex() for x in v))).encode("ascii"))
    pop = os.path.join(root, "in", "population.001.txt")
    print("# g_f9data: per-step process CPU (cycles/2.5e9; desktop, functional; read only as a ratio)")
    for kind, steps in CASES:
        res = {"pop": [], "l8": []}
        for rep in range(2):
            order = ("pop", "l8") if rep == 0 else ("l8", "pop")
            for w in order:
                res[w].append(run(root, kind, pop if w == "pop" else l8, steps, "%s_%s_%d" % (kind, w, rep), out))
        r = [res["pop"][i] / res["l8"][i] for i in range(2)]
        print("RESULT %s: population %.4f, %.4f s/step; LANES8 %.4f, %.4f s/step; ratio population/LANES8 %.4f, %.4f (steps %d)" % (
            kind, res["pop"][0], res["pop"][1], res["l8"][0], res["l8"][1], r[0], r[1], steps))


if __name__ == "__main__":
    main()
