#!/usr/bin/env python3
"""DEBRIS-A: does REBOUND 5.1.1's first-order variational particle carry an
additional force? One column of the state transition matrix (d final state /
d initial x of the satellite), one day of LEO, IAS15, from the variational
particle and from a central finite difference, with and without the J2
callback of leo_roundtrip.py (which writes particles[1] only)."""
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import rebound  # noqa: E402
import leo_roundtrip as L  # noqa: E402


def a_j2(x, y, z):
    r2 = x * x + y * y + z * z
    r = math.sqrt(r2)
    c2 = z * z / r2
    pre = 3. * L.J2 * L.RE * L.RE / r2 / r2 / r / 2.
    fac = 5. * c2 - 1.
    return (L.GM * pre * fac * x, L.GM * pre * fac * y, L.GM * pre * (fac - 2.) * z)


def with_jacobian(base):
    """base's force on the real particle, plus J2's Jacobian (central
    differences, h = 1e-4 km) applied to the variational particle"""
    def f(simp):
        base(simp)
        s = simp.contents
        if not s.N_var_config:
            return
        e, p = s.particles[0], s.particles[1]
        r = [p.x - e.x, p.y - e.y, p.z - e.z]
        idx = s.var_config[0].index
        v0 = s._particles_var[idx + 0]
        v1 = s._particles_var[idx + 1]
        dr = [v1.x - v0.x, v1.y - v0.y, v1.z - v0.z]
        hh = 1e-4
        da = [0.0, 0.0, 0.0]
        for k in range(3):
            rp = list(r); rp[k] += hh
            rm = list(r); rm[k] -= hh
            ap, am = a_j2(*rp), a_j2(*rm)
            for i in range(3):
                da[i] += (ap[i] - am[i]) / (2 * hh) * dr[k]
        v1.ax += da[0]
        v1.ay += da[1]
        v1.az += da[2]
    return f


def sim_for(state, j2, jac=False):
    sim = rebound.Simulation()
    sim.G = 1.0
    sim.add(m=L.GM)
    x, y, z, vx, vy, vz = state
    sim.add(m=0.0, x=x, y=y, z=z, vx=vx, vy=vy, vz=vz)
    cnt = [0]
    if j2:
        f = L.make_force(("j2",), cnt)
        sim.additional_forces = with_jacobian(f) if jac else f
    sim.integrator = "ias15"
    sim.dt = 60.0
    return sim, cnt


def final(state, j2):
    sim, _ = sim_for(state, j2)
    sim.integrate(L.T)
    p = sim.particles[1]
    return [p.x, p.y, p.z, p.vx, p.vy, p.vz]


s0 = list(L.initial_state())
h = 1e-3  # km
for j2, jac in ((False, False), (True, False), (True, True)):
    sim, cnt = sim_for(s0, j2, jac)
    v = sim.add_variation()
    v.particles[1].x = 1.0
    sim.integrate(L.T)
    q = v.particles[1]
    col_var = [q.x, q.y, q.z, q.vx, q.vy, q.vz]
    sp = list(s0); sp[0] += h
    sm = list(s0); sm[0] -= h
    fp, fm = final(sp, j2), final(sm, j2)
    col_fd = [(a - b) / (2 * h) for a, b in zip(fp, fm)]
    num = math.sqrt(sum((a - b) ** 2 for a, b in zip(col_var[:3], col_fd[:3])))
    den = math.sqrt(sum(b * b for b in col_fd[:3]))
    print("J2 %-26s d(pos)/dx0 after one day: variational %s | finite difference %s | relative mismatch %.2e" %
          (("on, Jacobian supplied" if jac else "on, callback as written") if j2 else "off",
           " ".join("%.6f" % c for c in col_var[:3]),
           " ".join("%.6f" % c for c in col_fd[:3]), num / den))
