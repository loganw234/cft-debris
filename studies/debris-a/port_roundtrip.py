#!/usr/bin/env python3
"""DEBRIS-A: the LEO + J2 round trip on the port (cft-rebound's ias15_cft,
the round4-int5 build in ../cft-rebound-seam, which has the zonal term) at
binary64, binary128 and binary256, and REBOUND 5.1.1's own IAS15 on the same
fixed steps from Python, for a bitwise comparison at binary64.

Fixed step (--epsilon 0), N steps forward, then N steps back with -dt from
the exact recorded turn-around state (the method of tools/reversal.py, with
the problem's `active` and `zonal` lines carried into the turn-around file,
which tools/state_to_problem.py does not do). Everything is written here.

  python port_roundtrip.py --dt 100 --steps 864 [--formats fp64,fp128,fp256] [--calibrate]
"""
import argparse
import math
import os
import subprocess
import sys
import time
from fractions import Fraction

HERE = os.path.dirname(os.path.abspath(__file__))
EXE = r"C:\Users\logan\source\repos\cft-rebound-seam\build\ias15_cft.exe"
sys.path.insert(0, HERE)
import leo_roundtrip as L  # noqa: E402

MAXITER = {"fp64": "12", "fp128": "24", "fp256": "60"}


def hexfrac(t):
    """An exact hex float of any width as a Fraction."""
    t = t.strip()
    sign = -1 if t.startswith("-") else 1
    t = t.lstrip("+-")
    assert t.startswith("0x"), t
    mant, _, ex = t[2:].partition("p")
    ip, _, fp = mant.partition(".")
    num = int(ip + fp, 16) if (ip + fp) else 0
    den = 16 ** len(fp)
    e = int(ex) if ex else 0
    v = Fraction(num, den) * (Fraction(2) ** e)
    return sign * v


def header(state_hex):
    return ["name leo_j2",
            "G 0x1p+0",
            "active 1",
            "zonal 0 %s %s 0x0p+0" % (L.RE.hex(), L.J2.hex()),
            "body earth %s 0x0p+0 0x0p+0 0x0p+0 0x0p+0 0x0p+0 0x0p+0" % L.GM.hex(),
            "body sat 0x0p+0 %s" % " ".join(state_hex)]


def write_problem(path, state_hex, comment):
    with open(path, "w", newline="\n") as f:
        f.write("# %s\n" % comment)
        f.write("\n".join(header(state_hex)) + "\n")


def run(fmt, prob, dt, steps):
    env = dict(os.environ)
    env["PATH"] = r"C:\msys64\mingw64\bin;" + env.get("PATH", "")
    cmd = [EXE, "--format", fmt, "--problem", prob, "--dt", dt, "--epsilon", "0",
           "--steps", str(steps), "--sample", str(steps), "--max-iter", MAXITER[fmt], "--quiet"]
    t0 = time.perf_counter()
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env)
    wall = time.perf_counter() - t0
    if p.returncode != 0:
        raise SystemExit("failed (%d): %s\n%s" % (p.returncode, " ".join(cmd), p.stderr[-2000:]))
    return p.stdout, wall, cmd


def last_state(rec):
    """the sat's six hex tokens at the last sample, and the trailer's numbers"""
    lines = [l for l in rec.splitlines() if l.startswith("sample ")]
    toks = lines[-1].split()
    body = toks[7:toks.index("|")] if "|" in toks else toks[7:]
    assert len(body) == 12, len(body)
    trailer = {}
    for l in rec.splitlines():
        if l.startswith("# steps_done="):
            for kv in l[2:].split():
                k, _, v = kv.partition("=")
                trailer[k] = v
    return body[6:12], body[0:6], toks[3], trailer


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dt", default="100")
    ap.add_argument("--steps", type=int, default=864)
    ap.add_argument("--formats", default="fp64,fp128,fp256")
    ap.add_argument("--calibrate", action="store_true")
    a = ap.parse_args()
    s0 = L.initial_state()
    s0hex = [q.hex() for q in s0]
    prob = os.path.join(HERE, "leo_j2.txt")
    write_problem(prob, s0hex, "DEBRIS-A: LEO 400 km, i = 51.6 deg, about a point-mass Earth with J2 (J4 = 0); km, s, G = 1")
    s0f = [Fraction(q) for q in s0]
    results = {}
    for fmt in a.formats.split(","):
        fwd, w1, cmd1 = run(fmt, prob, a.dt, a.steps)
        open(os.path.join(HERE, "port_%s_n%d_fwd.rec" % (fmt, a.steps)), "w", newline="\n").write(fwd)
        sat_hex, earth_hex, t_turn, tr1 = last_state(fwd)
        if a.calibrate:
            print("calibrate %s: %d steps, wall %.2f s, trailer seconds=%s steps_per_s=%s mean_pc=%s" %
                  (fmt, a.steps, w1, tr1.get("seconds"), tr1.get("steps_per_s"), tr1.get("mean_pc_iterations")))
            continue
        assert all(hexfrac(t) == 0 for t in earth_hex), "Earth moved"
        turn = os.path.join(HERE, "port_%s_n%d_turn.txt" % (fmt, a.steps))
        write_problem(turn, sat_hex, "turn-around state of %s at t = %s" % (fmt, t_turn))
        back, w2, cmd2 = run(fmt, turn, "-" + a.dt, a.steps)
        open(os.path.join(HERE, "port_%s_n%d_back.rec" % (fmt, a.steps)), "w", newline="\n").write(back)
        ret_hex, earth2, t_end, tr2 = last_state(back)
        ret = [hexfrac(t) for t in ret_hex]
        same = all(r == s for r, s in zip(ret, s0f))
        dx = math.sqrt(float(sum((ret[i] - s0f[i]) ** 2 for i in range(3)))) * 1e3
        dv = math.sqrt(float(sum((ret[i] - s0f[i]) ** 2 for i in range(3, 6)))) * 1e6
        rel = dx / 1e3 / math.sqrt(sum(q * q for q in s0[:3]))
        results[fmt] = dict(turn=[hexfrac(t) for t in sat_hex], turn_hex=sat_hex, ret_hex=ret_hex)
        print("PORT %-5s dt=%s steps=%d: round trip %.3e m, %.3e mm/s (|dx|/r %.2e) bits_identical=%s | "
              "fwd %.1f s wall (trailer %s s, %s steps/s, mean_pc %s), back %.1f s wall | t_turn=%s t_end=%s" %
              (fmt, a.dt, a.steps, dx, dv, rel, same, w1, tr1.get("seconds"), tr1.get("steps_per_s"),
               tr1.get("mean_pc_iterations"), w2, t_turn, t_end))
        print("   cmd: %s" % " ".join(cmd1))
    if a.calibrate:
        return 0
    # REBOUND's own IAS15 from Python, the same fixed steps, the J2 force in
    # the order the port states; backward from a fresh simulation at the
    # turn-around state, as the port's backward run is.
    dt = float(a.dt)
    sim, cnt = L.build(s0, ("j2",), "ias15", {"epsilon": 0.0}, dt)
    t0 = time.perf_counter()
    sim.steps(a.steps)
    wpy = time.perf_counter() - t0
    py_turn = L.state_of(sim)
    sim2, _ = L.build(py_turn, ("j2",), "ias15", {"epsilon": 0.0}, -dt)
    sim2.steps(a.steps)
    py_ret = L.state_of(sim2)
    py_dx = L.dpos_m(py_ret, s0)
    print("REBOUND 5.1.1 IAS15 (Python J2), same steps: round trip %.3e m; forward %.3f s wall" % (py_dx, wpy))
    if "fp64" in results:
        tb = all(Fraction(p) == q for p, q in zip(py_turn, results["fp64"]["turn"]))
        rb = all(p.hex() == q or Fraction(p) == hexfrac(q) for p, q in zip(py_ret, results["fp64"]["ret_hex"]))
        print("bitwise, port fp64 against REBOUND 5.1.1 + Python J2: turn-around %s, return %s" %
              ("IDENTICAL" if tb else "DIFFERENT", "IDENTICAL" if rb else "DIFFERENT"))
        if not tb:
            d = L.dpos_m(py_turn, [float(q) for q in results["fp64"]["turn"]])
            print("   turn-around differs by %.3e m" % d)
    for f1, f2 in (("fp64", "fp128"), ("fp128", "fp256"), ("fp64", "fp256")):
        if f1 in results and f2 in results:
            d = math.sqrt(float(sum((results[f1]["turn"][i] - results[f2]["turn"][i]) ** 2 for i in range(3)))) * 1e3
            print("forward state at the turn, %s against %s: %.3e m" % (f1, f2, d))
    return 0


if __name__ == "__main__":
    sys.exit(main())
