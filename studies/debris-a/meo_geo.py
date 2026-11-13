#!/usr/bin/env python3
"""DEBRIS-A: the nearly conservative regimes. One year of a GPS-like MEO
orbit and of GEO about a point-mass Earth with J2, an analytic circular
Moon and Sun (time-dependent tides), and cannonball solar radiation
pressure without a shadow (C_R A/m = 0.026 m^2/kg). Forward error against
an IAS15 fixed-step reference, the round trip, force evaluations and wall
time, for IAS15, WHFast, SABA(10,6,4) and LEAPFROG o6. Units km, s, G = 1.

  python meo_geo.py
"""
import math
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import rebound  # noqa: E402
import leo_roundtrip as L  # noqa: E402

GMS = 1.32712440018e11            # km^3/s^2
AU = 149597870.7                  # km
NS = 2 * math.pi / (365.25636 * 86400.0)
PSRP = 4.56e-6                    # N/m^2 at 1 AU
CRAM = 1.3 * 0.02                 # m^2/kg
YEAR = 365.25 * 86400.0


def make_force(cnt):
    rm3 = L.RM ** 3
    rs3 = AU ** 3
    ce, se = math.cos(L.ECL), math.sin(L.ECL)
    ksrp = PSRP * CRAM * 1e-3     # km/s^2 at 1 AU

    def f(simp):
        cnt[0] += 1
        s = simp.contents
        ps = s.particles
        e, p = ps[0], ps[1]
        dx, dy, dz = p.x - e.x, p.y - e.y, p.z - e.z
        r2 = dx * dx + dy * dy + dz * dz
        r = math.sqrt(r2)
        c2 = dz * dz / r2
        pre = 3. * L.J2 * L.RE * L.RE / r2 / r2 / r / 2.
        fac = 5. * c2 - 1.
        ax = L.GM * pre * fac * dx
        ay = L.GM * pre * fac * dy
        az = L.GM * pre * (fac - 2.) * dz
        t = s.t
        # Moon
        c, sn = math.cos(L.NM * t), math.sin(L.NM * t)
        xm, ym, zm = L.RM * c, L.RM * sn * ce, L.RM * sn * se
        qx, qy, qz = xm - dx, ym - dy, zm - dz
        q3 = (qx * qx + qy * qy + qz * qz) ** 1.5
        ax += L.GMM * (qx / q3 - xm / rm3)
        ay += L.GMM * (qy / q3 - ym / rm3)
        az += L.GMM * (qz / q3 - zm / rm3)
        # Sun, tide and SRP
        c, sn = math.cos(NS * t), math.sin(NS * t)
        xs, ys, zs = AU * c, AU * sn * ce, AU * sn * se
        qx, qy, qz = xs - dx, ys - dy, zs - dz
        q2 = qx * qx + qy * qy + qz * qz
        q = math.sqrt(q2)
        q3 = q2 * q
        ax += GMS * (qx / q3 - xs / rs3)
        ay += GMS * (qy / q3 - ys / rs3)
        az += GMS * (qz / q3 - zs / rs3)
        k = ksrp * (AU * AU / q2) / q
        ax -= k * qx
        ay -= k * qy
        az -= k * qz
        p.ax += ax
        p.ay += ay
        p.az += az
    return f


ORBITS = {
    "MEO (GPS-like)": dict(a=26560.0, e=0.01, inc=math.radians(55.0), Omega=0.4, omega=0.9, M=0.2),
    "GEO": dict(a=42164.0, e=0.0005, inc=math.radians(0.1), Omega=0.4, omega=0.9, M=0.2),
}


def start(el):
    sim = rebound.Simulation()
    sim.G = 1.0
    sim.add(m=L.GM)
    sim.add(primary=sim.particles[0], m=0.0, **el)
    p = sim.particles[1]
    return (p.x, p.y, p.z, p.vx, p.vy, p.vz)


def build(state, integ, opts, dt):
    sim = rebound.Simulation()
    sim.G = 1.0
    sim.add(m=L.GM)
    x, y, z, vx, vy, vz = state
    sim.add(m=0.0, x=x, y=y, z=z, vx=vx, vy=vy, vz=vz)
    sim.N_active = 1
    cnt = [0]
    sim.additional_forces = make_force(cnt)
    sim.integrator = integ
    for k, v in opts.items():
        setattr(sim.integrator, k, v)
    sim.dt = dt
    return sim, cnt


for name, el in ORBITS.items():
    s0 = start(el)
    ref, _ = build(s0, "ias15", {"epsilon": 0.0}, 300.0)
    ref.steps(int(round(YEAR / 300.0)))
    rstate = L.state_of(ref)
    print("\n=== %s, one year, J2 + Moon(t) + Sun(t) + SRP; reference IAS15 fixed 300 s, t=%r" % (name, ref.t))
    for label, integ, opts, dt, nfix in [
            ("IAS15 eps1e-9 (adaptive)", "ias15", {"epsilon": 1e-9}, 600.0, None),
            ("WHFast dt600", "whfast", {}, 600.0, None),
            ("WHFast dt1800", "whfast", {}, 1800.0, None),
            ("SABA(10,6,4) dt1800", "saba", {"type": "10_6_4"}, 1800.0, None),
            ("SABA(10,6,4) dt3600", "saba", {"type": "10_6_4"}, 3600.0, None),
            ("LEAPFROG o6 dt600", "leapfrog", {"order": 6}, 600.0, None)]:
        sim, cnt = build(s0, integ, opts, dt)
        n = int(round(YEAR / dt))
        t0 = time.perf_counter()
        if integ == "ias15":
            sim.integrate(YEAR)
        else:
            sim.steps(n)
        w = time.perf_counter() - t0
        fe = cnt[0]
        st = sim.steps_done
        turn = L.state_of(sim)
        tt = sim.t
        if integ == "ias15":
            sim.integrate(0.0)
        else:
            sim.dt = -dt
            sim.steps(n)
        print("%-26s fwd_err %10.3e m | round trip %10.3e m | %6.2f s, %7d fevals, %6d steps | t=%r" %
              (label, L.dpos_m(turn, rstate), L.dpos_m(L.state_of(sim), s0), w, fe, st, tt))
