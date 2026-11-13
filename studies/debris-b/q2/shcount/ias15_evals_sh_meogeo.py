#!/usr/bin/env python3
"""DEBRIS-B Q2: ias15_evals_sh.py's counter for MEO and GEO with the
Earth-fixed field to degree 8, one day and ten days; and REBOUND's own C
IAS15 cost per object-day with no Python force (point mass, 30 days)."""
import math, os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rebound
import ias15_evals_sh as S

def run(a, e, inc, N, days):
    assert S.DLL.grav_init(N) == 0
    sim = rebound.Simulation(); sim.G = 1.0; sim.add(m=S.GM)
    sim.add(primary=sim.particles[0], m=0.0, a=a, e=e, inc=math.radians(inc), Omega=math.radians(30.0),
            omega=math.radians(40.0), M=math.radians(10.0))
    sim.N_active = 1; sim.testparticle_type = 0
    calls = []
    sim.additional_forces = S.make_force(N, False, calls)
    sim.integrator = "ias15"; sim.integrator.epsilon = 1e-9; sim.dt = 60.0
    sim.integrate(days * 86400.0)
    return len(calls) / days, sim.steps_done / days

for name, a, e, inc in (("MEO GPS-like", 26560.0, 0.01, 55.0), ("GEO", 42164.0, 0.0005, 0.1)):
    for N in (2, 8):
        ev, st = run(a, e, inc, N, 10.0)
        print("%-12s N=%d ten days: %7.1f evaluations per object-day, %5.1f steps a day" % (name, N, ev, st), flush=True)
# the C floor: point mass, no callback
sim = rebound.Simulation(); sim.G = 1.0; sim.add(m=S.GM)
sim.add(primary=sim.particles[0], m=0.0, a=6778.137, e=0.001, inc=math.radians(51.6), Omega=math.radians(30.0),
        omega=math.radians(40.0), M=math.radians(10.0))
sim.N_active = 1; sim.integrator = "ias15"; sim.integrator.epsilon = 1e-9; sim.dt = 60.0
t0 = time.perf_counter(); sim.integrate(30 * 86400.0); w = time.perf_counter() - t0
print("REBOUND C IAS15, point mass, LEO 400 km, 30 days: %.3f s wall, %d steps, %.3f ms per object-day, %.3f us per step"
      % (w, sim.steps_done, 1e3 * w / 30, 1e6 * w / sim.steps_done))
