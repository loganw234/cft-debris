#!/usr/bin/env python3
"""DEBRIS-B Q2: IAS15's force evaluations per object-day, with this study's
own setup and counter (the plan's "One figure measured twice"; DEBRIS-A's
leo_roundtrip.py is neither imported nor run).

The physical setup is DEBRIS-A section 2's: REBOUND 5.1.1, a point-mass
Earth with J2 as a Python additional force, IAS15 at epsilon 1e-9, one day.
The LEO orbit: 400 km (a = 6778.137 km), e = 0.001, i = 51.6 deg. Omega,
omega and M are 30, 40 and 10 deg: the values in DEBRIS-A's leo_roundtrip.py
ELEMENTS, read there (not run), so the two counts describe the same orbit.

The J2 acceleration is written here in the textbook form
  a = -(3/2) J2 GM R^2 / r^5 * (x (1 - 5 z^2/r^2), y (1 - 5 z^2/r^2), z (3 - 5 z^2/r^2))
which is algebraically DEBRIS-A's but not its operation order.

Counter: every call of the additional force appends the simulation time to a
list; the count is the list's length, and the number of distinct times is
printed beside it. The integration is one call of sim.integrate(86400) from
sim.dt = 60 s, REBOUND's defaults otherwise (exact_finish_time = 1).

Besides the overlap figure, the same counter is run on:
- the LEO orbit at other mean anomalies and starting steps (the spread);
- MEO (GPS-like) and GEO orbits with J2, and over ten days (for Q2's budget).

  python -I -B ias15_evals.py
"""
import math
import sys
import time

import rebound

GM = 398600.4418
RE = 6378.137
J2 = 1.08262668e-3


def j2_force(counter):
    k = -1.5 * J2 * GM * RE * RE

    def f(simp):
        s = simp.contents
        counter.append(s.t)
        ps = s.particles
        e, p = ps[0], ps[1]
        x, y, z = p.x - e.x, p.y - e.y, p.z - e.z
        r2 = x * x + y * y + z * z
        r = math.sqrt(r2)
        q = k / (r2 * r2 * r)
        w = 5.0 * z * z / r2
        p.ax += q * x * (1.0 - w)
        p.ay += q * y * (1.0 - w)
        p.az += q * z * (3.0 - w)
    return f


def run(a, e, inc, Omega, omega, M, days=1.0, dt0=60.0, eps=1e-9):
    sim = rebound.Simulation()
    sim.G = 1.0
    sim.add(m=GM)
    sim.add(primary=sim.particles[0], m=0.0, a=a, e=e, inc=math.radians(inc), Omega=math.radians(Omega),
            omega=math.radians(omega), M=math.radians(M))
    sim.N_active = 1
    sim.testparticle_type = 0
    calls = []
    sim.additional_forces = j2_force(calls)
    sim.integrator = "ias15"
    sim.integrator.epsilon = eps
    sim.dt = dt0
    t0 = time.perf_counter()
    sim.integrate(days * 86400.0)
    w = time.perf_counter() - t0
    return dict(evals=len(calls), distinct=len(set(calls)), steps=sim.steps_done, t=sim.t, wall=w,
                per_day=len(calls) / days, adaptive_mode=str(sim.integrator.adaptive_mode))


def main():
    print("# REBOUND %s, IAS15 epsilon 1e-9, own J2 force and counter" % rebound.__version__)
    r = run(6778.137, 0.001, 51.6, 30.0, 40.0, 10.0)
    print("OVERLAP LEO 400 km one day: %d force evaluations (%d distinct times), %d steps, t_end=%r, "
          "adaptive_mode=%s, wall %.3f s" % (r["evals"], r["distinct"], r["steps"], r["t"], r["adaptive_mode"],
                                            r["wall"]))
    print("# the spread: other mean anomalies and starting steps, one day")
    for M in (0.0, 90.0, 180.0, 270.0):
        r = run(6778.137, 0.001, 51.6, 30.0, 40.0, M)
        print("LEO M=%5.1f dt0=60: %6d evaluations, %4d steps" % (M, r["evals"], r["steps"]))
    for dt0 in (10.0, 300.0):
        r = run(6778.137, 0.001, 51.6, 30.0, 40.0, 10.0, dt0=dt0)
        print("LEO M= 10.0 dt0=%3.0f: %6d evaluations, %4d steps" % (dt0, r["evals"], r["steps"]))
    print("# ten days, and the other regimes (J2 only), for the budget")
    rows = [("LEO 400 km", 6778.137, 0.001, 51.6), ("LEO 800 km", 7178.137, 0.001, 98.6),
            ("MEO GPS-like", 26560.0, 0.01, 55.0), ("GEO", 42164.0, 0.0005, 0.1),
            ("GEO graveyard +300 km", 42464.0, 0.0005, 0.1)]
    for name, a, e, inc in rows:
        r = run(a, e, inc, 30.0, 40.0, 10.0, days=10.0)
        print("%-22s ten days: %8d evaluations, %6d steps, %8.1f evaluations per object-day, %6.1f steps a day"
              % (name, r["evals"], r["steps"], r["per_day"], r["steps"] / 10.0))
    return 0


if __name__ == "__main__":
    sys.exit(main())
