#!/usr/bin/env python3
"""DEBRIS-B Q3: the binary64 positive control as a distribution, not a draw.

The sweep's binary64 legs are single runs, and HORIZON.md says a single run
is one draw of the round-off walk. Here each dt gets an ensemble: the same
quarter-day round trip (N steps forward, N back from a fresh simulation at
the exact turn-around state, as port_roundtrip.py does), from 32 initial
states whose x differs by k = 0..31 ulps. The engine is REBOUND 5.1.1's
IAS15 with the Python J2 of DEBRIS-A's leo_roundtrip.py, imported from an
unchanged copy in sweep/dt25 (checked by SHA-256 below), at epsilon 0; the
sweep showed it bit-identical to the port's binary64 at dt = 50 and 25 s,
and member k = 0 must reproduce the port's figures here.

  python -I -B fp64_ensemble.py
"""
import hashlib
import math
import os
import statistics
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
COPY = os.path.join(HERE, "dt25")
SUMS = r"C:\Users\logan\source\repos\cft-debris\studies\SHA256SUMS"
want = [l.split(" *")[0] for l in open(SUMS) if l.strip().endswith("debris-a/leo_roundtrip.py")][0]
got = hashlib.sha256(open(os.path.join(COPY, "leo_roundtrip.py"), "rb").read()).hexdigest()
assert got == want, (got, want)
sys.path.insert(0, COPY)
import leo_roundtrip as L  # noqa: E402

PORT_FP64 = {100.0: 3.827e-08, 50.0: 5.211e-08, 25.0: 6.318e-09}  # port_quarterday.log and this sweep's logs


def roundtrip(s0, dt, n):
    sim, _ = L.build(s0, ("j2",), "ias15", {"epsilon": 0.0}, dt)
    sim.steps(n)
    turn = L.state_of(sim)
    sim2, _ = L.build(turn, ("j2",), "ias15", {"epsilon": 0.0}, -dt)
    sim2.steps(n)
    return L.dpos_m(L.state_of(sim2), s0)


def main():
    s0 = L.initial_state()
    print("# copy of leo_roundtrip.py in %s matches SHA256SUMS" % COPY)
    for dt in (100.0, 50.0, 25.0, 12.5):
        n = int(round(21600.0 / dt))
        errs = []
        x = s0[0]
        for k in range(32):
            s = (x,) + tuple(s0[1:])
            errs.append(roundtrip(s, dt, n))
            x = math.nextafter(x, math.inf)
        if dt in PORT_FP64:
            assert abs(errs[0] - PORT_FP64[dt]) <= 1e-3 * PORT_FP64[dt], (dt, errs[0])
        e = sorted(errs)
        p90 = e[int(math.ceil(0.9 * len(e))) - 1]
        print("dt=%5.1f steps=%4d: member0 %.3e m | median %.3e  p90 %.3e  min %.3e  max %.3e  (32 members, x + k ulps)"
              % (dt, n, errs[0], statistics.median(e), p90, e[0], e[-1]), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
