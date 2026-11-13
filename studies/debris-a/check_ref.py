#!/usr/bin/env python3
"""DEBRIS-A: the binary64 references of leo_roundtrip.py against the port's
binary128 one-day state (port_fp128_n864_fwd.rec), J2 only."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import leo_roundtrip as L  # noqa: E402
import port_roundtrip as P  # noqa: E402

rec = open(os.path.join(HERE, "port_fp128_n864_fwd.rec")).read()
sat_hex, _, t, _ = P.last_state(rec)
ref128 = [float(P.hexfrac(h)) for h in sat_hex]
s0 = L.initial_state()
for label, integ, opts, dt, n in [
        ("IAS15 dt20 fixed (the table's reference)", "ias15", {"epsilon": 0.0}, 20.0, 4320),
        ("IAS15 dt100 fixed, binary64 (= port fp64)", "ias15", {"epsilon": 0.0}, 100.0, 864),
        ("IAS15 eps1e-9 adaptive", "ias15", {"epsilon": 1e-9}, 60.0, None),
        ("IAS15 eps1e-6 adaptive", "ias15", {"epsilon": 1e-6}, 60.0, None),
        ("BS eps1e-13", "bs", {"eps_abs": 1e-13, "eps_rel": 1e-13}, 60.0, None),
        ("SABA(10,6,4) dt30", "saba", {"type": "10_6_4"}, 30.0, 2880),
        ("JANUS o6 dt10", "janus", {"order": 6, "scale_pos": 1e-14, "scale_vel": 1e-17}, 10.0, 8640)]:
    sim, _ = L.build(s0, ("j2",), integ, opts, dt)
    if n:
        sim.steps(n)
    else:
        sim.integrate(L.T)
    print("%-44s against port binary128 at one day: %.3e m" % (label, L.dpos_m(L.state_of(sim), ref128)))
