#!/usr/bin/env python3
"""DEBRIS-B Q2: is the overlap count sensitive to the J2 expression's
operation order? The same setup and counter as ias15_evals.py, with J2
written in two orders:
  textbook  -(3/2) J2 GM R^2 / r^5 * (x (1 - 5 z^2/r^2), ...)  (ias15_evals.py's)
  2020      REBOUNDx's order as of 2020, which DEBRIS-A's leo_roundtrip.py
            uses (costheta2 = dz*dz/r2; prefac = 3*J2*R*R/r2/r2/r/2;
            fac = 5*costheta2 - 1; a = GM*prefac*fac*d, z with fac - 2),
            retyped here from that description, not imported.
The two are equal in exact arithmetic and differ in their roundings.

  python -I -B ias15_evals_order.py
"""
import math
import sys

import rebound

GM = 398600.4418
RE = 6378.137
J2 = 1.08262668e-3


def force(order, calls):
    k = -1.5 * J2 * GM * RE * RE

    def textbook(simp):
        s = simp.contents
        calls.append(s.t)
        e, p = s.particles[0], s.particles[1]
        x, y, z = p.x - e.x, p.y - e.y, p.z - e.z
        r2 = x * x + y * y + z * z
        r = math.sqrt(r2)
        q = k / (r2 * r2 * r)
        w = 5.0 * z * z / r2
        p.ax += q * x * (1.0 - w)
        p.ay += q * y * (1.0 - w)
        p.az += q * z * (3.0 - w)

    def order2020(simp):
        s = simp.contents
        calls.append(s.t)
        e, p = s.particles[0], s.particles[1]
        dx, dy, dz = p.x - e.x, p.y - e.y, p.z - e.z
        r2 = dx * dx + dy * dy + dz * dz
        r = math.sqrt(r2)
        costheta2 = dz * dz / r2
        prefac = 3. * J2 * RE * RE / r2 / r2 / r / 2.
        fac = 5. * costheta2 - 1.
        GMp = s.G * e.m
        p.ax += GMp * prefac * fac * dx
        p.ay += GMp * prefac * fac * dy
        p.az += GMp * prefac * (fac - 2.) * dz
    return textbook if order == "textbook" else order2020


def run(order):
    sim = rebound.Simulation()
    sim.G = 1.0
    sim.add(m=GM)
    sim.add(primary=sim.particles[0], m=0.0, a=6778.137, e=0.001, inc=math.radians(51.6),
            Omega=math.radians(30.0), omega=math.radians(40.0), M=math.radians(10.0))
    sim.N_active = 1
    sim.testparticle_type = 0
    calls = []
    sim.additional_forces = force(order, calls)
    sim.integrator = "ias15"
    sim.integrator.epsilon = 1e-9
    sim.dt = 60.0
    sim.integrate(86400.0)
    return len(calls), sim.steps_done


def main():
    for order in ("textbook", "2020"):
        n, steps = run(order)
        print("J2 in the %-8s order: %d force evaluations in one LEO day, %d steps" % (order, n, steps))
    return 0


if __name__ == "__main__":
    sys.exit(main())
