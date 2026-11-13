#!/usr/bin/env python3
"""DEBRIS-B Q3: the physical uncertainties binary64's arithmetic error is set
against, measured on simple models with this study's own code (REBOUND
5.1.1 IAS15, epsilon 1e-9, binary64):

- LEO drag: a co-rotating exponential atmosphere (Vallado-like band values,
  BELIEVED as recalled: 400 km rho0 3.725e-12, H 58.515; 800 km rho0
  1.170e-14, H 124.64), B = Cd A/m = 0.022 m^2/kg, J2. The density times
  1.2 (or equally B times 1.2; drag depends on rho B only) against nominal:
  position difference after 1 and 7 days, 400 and 800 km; 30 days at 800 km.
- MEO (a 26,560 km, e 0.01, i 55) and GEO (a 42,164, e 0.0005, i 0.1):
  J2, an analytic circular Sun (1 AU, 365.25636 d, ecliptic 23.44 deg) as a
  third body, and cannonball radiation pressure (P 4.56e-6 N/m^2 at 1 AU,
  C_R A/m 0.026 m^2/kg, no shadow); C_R A/m times 1.2 against nominal:
  position difference after 7 and 365 days (end and maximum over daily samples).

  python -I -B q3_physics.py
"""
import math
import sys

import rebound

GM = 398600.4418
RE = 6378.137
J2 = 1.08262668e-3
WE = 7.292115e-5
GMS = 1.32712440018e11
AU = 149597870.7
NS = 2 * math.pi / (365.25636 * 86400.0)
ECL = math.radians(23.44)
PSRP = 4.56e-6
BANDS = {400: (400.0, 3.725e-12, 58.515), 800: (800.0, 1.170e-14, 124.64)}


def force(drag_band, rho_scale, cram, sun):
    k2 = -1.5 * J2 * GM * RE * RE

    def f(simp):
        s = simp.contents
        e, p = s.particles[0], s.particles[1]
        x, y, z = p.x - e.x, p.y - e.y, p.z - e.z
        r2 = x * x + y * y + z * z
        r = math.sqrt(r2)
        q = k2 / (r2 * r2 * r)
        w = 5.0 * z * z / r2
        ax, ay, az = q * x * (1 - w), q * y * (1 - w), q * z * (3 - w)
        if drag_band:
            h0, rho0, hs = drag_band
            rho = rho_scale * rho0 * math.exp(-(r - RE - h0) / hs)
            vx, vy, vz = p.vx + WE * y, p.vy - WE * x, p.vz
            v = math.sqrt(vx * vx + vy * vy + vz * vz)
            kd = -0.5e3 * rho * 0.022 * v
            ax += kd * vx
            ay += kd * vy
            az += kd * vz
        if sun:
            t = s.t
            c, sn = math.cos(NS * t), math.sin(NS * t)
            xs, ys, zs = AU * c, AU * sn * math.cos(ECL), AU * sn * math.sin(ECL)
            dx, dy, dz = xs - x, ys - y, zs - z
            d3 = (dx * dx + dy * dy + dz * dz) ** 1.5
            rs3 = AU ** 3
            ax += GMS * (dx / d3 - xs / rs3)
            ay += GMS * (dy / d3 - ys / rs3)
            az += GMS * (dz / d3 - zs / rs3)
            if cram:
                dn = math.sqrt(dx * dx + dy * dy + dz * dz)
                ks = -PSRP * cram * (AU / dn) ** 2 * 1e-3 / dn   # away from the Sun, km/s^2
                ax += ks * dx
                ay += ks * dy
                az += ks * dz
        p.ax += ax
        p.ay += ay
        p.az += az
    return f


def make(a, e, inc, drag_band=None, rho_scale=1.0, cram=0.0, sun=False):
    sim = rebound.Simulation()
    sim.G = 1.0
    sim.add(m=GM)
    sim.add(primary=sim.particles[0], m=0.0, a=a, e=e, inc=math.radians(inc), Omega=math.radians(30.0),
            omega=math.radians(40.0), M=math.radians(10.0))
    sim.N_active = 1
    sim.testparticle_type = 0
    sim.additional_forces = force(drag_band, rho_scale, cram, sun)
    if drag_band:
        sim.force_is_velocity_dependent = 1
    sim.integrator = "ias15"
    sim.integrator.epsilon = 1e-9
    sim.dt = 60.0
    return sim


def pos(sim):
    p = sim.particles[1]
    return (p.x, p.y, p.z)


def diff_run(kw_a, kw_b, orbit, days, sample_days=1.0):
    A = make(*orbit, **kw_a)
    B = make(*orbit, **kw_b)
    worst = 0.0
    t = 0.0
    while t < days * 86400.0 - 1e-6:
        t = min(t + sample_days * 86400.0, days * 86400.0)
        A.integrate(t)
        B.integrate(t)
        d = math.dist(pos(A), pos(B)) * 1e3
        worst = max(worst, d)
    return d, worst


def main():
    print("# REBOUND %s, IAS15 epsilon 1e-9; position differences in metres" % rebound.__version__)
    for alt, days in ((400, 1), (400, 7), (800, 1), (800, 7), (800, 30)):
        orbit = (RE + alt, 0.001, 51.6 if alt == 400 else 98.6)
        end, worst = diff_run(dict(drag_band=BANDS[alt]), dict(drag_band=BANDS[alt], rho_scale=1.2), orbit, days)
        print("LEO %d km, density (or B) x1.2, %3d days: %.4g m at the end, %.4g m max" % (alt, days, end, worst),
              flush=True)
    for name, orbit in (("MEO", (26560.0, 0.01, 55.0)), ("GEO", (42164.0, 0.0005, 0.1))):
        for days in (7, 365):
            end, worst = diff_run(dict(cram=0.026, sun=True), dict(cram=0.026 * 1.2, sun=True), orbit, days)
            print("%s, C_R A/m x1.2, %3d days: %.4g m at the end, %.4g m max over daily samples" %
                  (name, days, end, worst), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
