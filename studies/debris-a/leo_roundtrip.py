#!/usr/bin/env python3
"""DEBRIS-A measurements with REBOUND 5.1.1 (the wheel in Miniconda3).

A LEO test particle about a point-mass Earth with J2 written as a Python
additional force (the expression in REBOUNDx's order, the one the port's
src/ias15_zonal.inc states it recalls), optionally with drag (exponential
atmosphere, co-rotating) and a time-dependent lunar tide (analytic Moon).

For each integrator: forward one day, then back to t = 0 in the same
simulation; the round-trip error, the forward error against a reference,
the wall time and the count of force evaluations.

Units km, s, G = 1, masses as GM. Every output goes to this script's own
directory (the DEBRIS-A scratch folder).

  python leo_roundtrip.py [--quick]
"""
import json
import math
import os
import sys
import time

import rebound

HERE = os.path.dirname(os.path.abspath(__file__))

GM = 398600.4418          # km^3/s^2  (WGS 84 / EGM96 value, as in Vallado)
RE = 6378.137             # km        (WGS 84 equatorial radius)
J2 = 1.08262668e-3        # EGM96 J2 (= -C20 unnormalised)
WE = 7.2921150e-5         # rad/s, Earth's rotation rate
RHO0, H0, HS = 3.725e-12, 400.0, 58.515   # kg/m^3, km, km: exponential band 400-450 km (Vallado table 8-4)
BC = 0.022                # m^2/kg: Cd 2.2 x A/m 0.01
GMM = 4902.800066         # km^3/s^2, Moon
RM = 384400.0             # km, circular analytic Moon
NM = 2.0 * math.pi / (27.321661 * 86400.0)
ECL = math.radians(23.44)
T = 86400.0               # one day

ELEMENTS = dict(a=6778.137, e=0.001, inc=math.radians(51.6), Omega=math.radians(30.0),
                omega=math.radians(40.0), M=math.radians(10.0))


def initial_state():
    sim = rebound.Simulation()
    sim.G = 1.0
    sim.add(m=GM)
    sim.add(primary=sim.particles[0], m=0.0, **ELEMENTS)
    p = sim.particles[1]
    return (p.x, p.y, p.z, p.vx, p.vy, p.vz)


def make_force(forces, cnt, rho_scale=1.0):
    drag = "drag" in forces
    moon = "moon" in forces
    rm3 = RM * RM * RM
    ce, se = math.cos(ECL), math.sin(ECL)

    def f(simp):
        cnt[0] += 1
        s = simp.contents
        ps = s.particles
        e = ps[0]
        p = ps[1]
        # J2, in the order src/ias15_zonal.inc says REBOUNDx uses
        dx = p.x - e.x
        dy = p.y - e.y
        dz = p.z - e.z
        r2 = dx * dx + dy * dy + dz * dz
        r = math.sqrt(r2)
        costheta2 = dz * dz / r2
        prefac = 3. * J2 * RE * RE / r2 / r2 / r / 2.
        fac = 5. * costheta2 - 1.
        GMp = s.G * e.m
        ax = GMp * prefac * fac * dx
        ay = GMp * prefac * fac * dy
        az = GMp * prefac * (fac - 2.) * dz
        if drag:
            h = r - RE
            rho = rho_scale * RHO0 * math.exp(-(h - H0) / HS)
            vrx = p.vx + WE * dy
            vry = p.vy - WE * dx
            vrz = p.vz
            vr = math.sqrt(vrx * vrx + vry * vry + vrz * vrz)
            k = 0.5 * rho * BC * 1e3 * vr        # km/s^2 per km/s
            ax -= k * vrx
            ay -= k * vry
            az -= k * vrz
        if moon:
            t = s.t
            c, sn = math.cos(NM * t), math.sin(NM * t)
            xm, ym, zm = RM * c, RM * sn * ce, RM * sn * se
            qx, qy, qz = xm - dx, ym - dy, zm - dz
            q3 = (qx * qx + qy * qy + qz * qz) ** 1.5
            ax += GMM * (qx / q3 - xm / rm3)
            ay += GMM * (qy / q3 - ym / rm3)
            az += GMM * (qz / q3 - zm / rm3)
        p.ax += ax
        p.ay += ay
        p.az += az
    return f


def build(state, forces, integrator, opts, dt, rho_scale=1.0):
    sim = rebound.Simulation()
    sim.G = 1.0
    sim.add(m=GM)
    x, y, z, vx, vy, vz = state
    sim.add(m=0.0, x=x, y=y, z=z, vx=vx, vy=vy, vz=vz)
    sim.N_active = 1
    sim.testparticle_type = 0
    cnt = [0]
    if forces:
        sim.additional_forces = make_force(forces, cnt, rho_scale)
        if "drag" in forces:
            sim.force_is_velocity_dependent = 1
    sim.integrator = integrator
    for k, v in opts.items():
        setattr(sim.integrator, k, v)
    sim.dt = dt
    return sim, cnt


def state_of(sim):
    p = sim.particles[1]
    return (p.x, p.y, p.z, p.vx, p.vy, p.vz)


def dpos_m(a, b):
    return 1e3 * math.sqrt(sum((a[i] - b[i]) ** 2 for i in range(3)))


def dvel_mms(a, b):
    return 1e6 * math.sqrt(sum((a[i] - b[i]) ** 2 for i in range(3, 6)))


def janus_lattice(state, sp, sv):
    """to_double(to_int(x)) exactly as integrator_janus.c does it."""
    out = []
    for i, q in enumerate(state):
        s = sp if i < 3 else sv
        out.append(float(int(q / s)) * s)
    return tuple(out)


def run_case(state, forces, integrator, opts, dt, fixed_steps=None, rho_scale=1.0):
    sim, cnt = build(state, forces, integrator, opts, dt, rho_scale)
    t0 = time.perf_counter()
    if fixed_steps:
        sim.steps(fixed_steps)
    else:
        sim.integrate(T)
    t_fwd = time.perf_counter() - t0
    n_fwd = cnt[0]
    steps_fwd = sim.steps_done
    turn = state_of(sim)
    t_turn = sim.t
    t0 = time.perf_counter()
    if fixed_steps:
        sim.dt = -dt
        sim.steps(fixed_steps)
    else:
        sim.integrate(0.0)
    t_back = time.perf_counter() - t0
    ret = state_of(sim)
    return dict(turn=turn, t_turn=t_turn, ret=ret, t_end=sim.t, wall_fwd=t_fwd, wall_back=t_back,
                fevals_fwd=n_fwd, fevals_total=cnt[0], steps_fwd=steps_fwd, steps_total=sim.steps_done)


CASES = [
    # label, integrator, opts, dt, fixed_steps (None = integrate to T)
    ("IAS15 eps1e-9 (adaptive)", "ias15", {"epsilon": 1e-9}, 60.0, None),
    ("IAS15 eps1e-6 (adaptive)", "ias15", {"epsilon": 1e-6}, 60.0, None),
    ("WHFast dt10", "whfast", {}, 10.0, 8640),
    ("WHFast dt30", "whfast", {}, 30.0, 2880),
    ("WHFast c11 dt30", "whfast", {"corrector": 11}, 30.0, 2880),
    ("SABA(10,6,4) dt30", "saba", {"type": "10_6_4"}, 30.0, 2880),
    ("EOS LF/LF n2 dt30", "eos", {}, 30.0, 2880),
    ("TRACE dt30", "trace", {}, 30.0, 2880),
    ("MERCURIUS dt30", "mercurius", {}, 30.0, 2880),
    ("JANUS o6 dt10", "janus", {"order": 6, "scale_pos": 1e-14, "scale_vel": 1e-17}, 10.0, 8640),
    ("JANUS o6 dt30", "janus", {"order": 6, "scale_pos": 1e-14, "scale_vel": 1e-17}, 30.0, 2880),
    ("BS eps1e-8 (adaptive)", "bs", {"eps_abs": 1e-8, "eps_rel": 1e-8}, 60.0, None),
    ("BS eps1e-12 (adaptive)", "bs", {"eps_abs": 1e-12, "eps_rel": 1e-12}, 60.0, None),
    ("LEAPFROG o2 dt10", "leapfrog", {"order": 2}, 10.0, 8640),
    ("LEAPFROG o6 dt10", "leapfrog", {"order": 6}, 10.0, 8640),
]


def cost_floor():
    """No Python callback: point-mass Earth, 30 days, so the C integrator's
    own cost per step shows. Host state is printed by the caller."""
    s0 = initial_state()
    rows = []
    for label, integ, opts, dt, nfix in [("IAS15 eps1e-9", "ias15", {"epsilon": 1e-9}, 60.0, None),
                                         ("WHFast dt10", "whfast", {}, 10.0, 259200),
                                         ("BS eps1e-12", "bs", {"eps_abs": 1e-12, "eps_rel": 1e-12}, 60.0, None),
                                         ("LEAPFROG o2 dt10", "leapfrog", {"order": 2}, 10.0, 259200),
                                         ("JANUS o6 dt10", "janus", {"order": 6, "scale_pos": 1e-14, "scale_vel": 1e-17}, 10.0, 259200)]:
        sim, _ = build(s0, (), integ, opts, dt)
        t0 = time.perf_counter()
        if nfix:
            sim.steps(nfix)
        else:
            sim.integrate(30 * T)
        w = time.perf_counter() - t0
        rows.append(dict(label=label, wall_s=w, steps=sim.steps_done, us_per_step=1e6 * w / sim.steps_done,
                         ms_per_object_day=1e3 * w / 30.0))
        print("cost floor %-18s 30 days: %8.3f s, %7d steps, %6.2f us/step, %7.3f ms per object-day" %
              (label, w, sim.steps_done, 1e6 * w / sim.steps_done, 1e3 * w / 30.0))
    return rows


def global_step():
    """REBOUND integrates every particle of a simulation on one step. Four
    test particles on LEO, GPS-like MEO, GEO and GTO orbits about a point
    mass: IAS15's steps for one day, each alone and all four together."""
    orbits = {
        "LEO 400 km": dict(a=6778.137, e=0.001, inc=math.radians(51.6)),
        "MEO (GPS-like)": dict(a=26560.0, e=0.01, inc=math.radians(55.0)),
        "GEO": dict(a=42164.0, e=0.0005, inc=math.radians(0.1)),
        "GTO": dict(a=(6578.137 + 42164.0) / 2, e=(42164.0 - 6578.137) / (42164.0 + 6578.137), inc=math.radians(27.0)),
    }
    res = {}

    def one(names):
        sim = rebound.Simulation()
        sim.G = 1.0
        sim.add(m=GM)
        for k, nm in enumerate(names):
            sim.add(primary=sim.particles[0], m=0.0, Omega=0.3 * k, omega=0.5 * k, M=0.7 * k, **orbits[nm])
        sim.N_active = 1
        sim.integrator = "ias15"
        sim.dt = 60.0
        t0 = time.perf_counter()
        sim.integrate(T)
        return sim.steps_done, time.perf_counter() - t0
    for nm in orbits:
        res[nm] = one([nm])
        print("global step: %-16s alone   %6d IAS15 steps a day" % (nm, res[nm][0]))
    allv = one(list(orbits))
    res["all four together"] = allv
    print("global step: all four together %6d IAS15 steps a day (each particle takes every one)" % allv[0])
    return {k: dict(steps=v[0], wall_s=v[1]) for k, v in res.items()}


def reference(state, forces):
    """IAS15 at a fixed 20 s step (278 steps an orbit) and BS at 1e-13, to
    one day; returns both, so their difference bounds the reference."""
    a, _ = build(state, forces, "ias15", {"epsilon": 0.0}, 20.0)
    a.steps(4320)
    b, _ = build(state, forces, "bs", {"eps_abs": 1e-13, "eps_rel": 1e-13}, 60.0)
    b.integrate(T)
    return state_of(a), state_of(b), a.t, b.t


def main():
    quick = "--quick" in sys.argv
    s0 = initial_state()
    out = {"initial": s0, "initial_hex": [q.hex() for q in s0], "rebound": rebound.__version__, "sets": {}}
    sets = [("J2", ("j2",)), ("J2+drag", ("j2", "drag")), ("J2+moon(t)", ("j2", "moon"))]
    for set_name, forces in sets:
        ref_a, ref_b, ta, tb = reference(s0, forces)
        print("\n=== %s  reference: IAS15 dt20 vs BS 1e-13 differ by %.3e m (t=%r, %r)" %
              (set_name, dpos_m(ref_a, ref_b), ta, tb))
        rows = []
        for label, integ, opts, dt, nfix in CASES:
            if quick and integ not in ("ias15", "whfast"):
                continue
            if set_name == "J2+moon(t)" and integ not in ("janus", "ias15", "leapfrog"):
                continue
            r = run_case(s0, forces, integ, opts, dt, nfix)
            fwd_err = dpos_m(r["turn"], ref_a)
            rt_pos = dpos_m(r["ret"], s0)
            rt_vel = dvel_mms(r["ret"], s0)
            bit = None
            if integ == "janus":
                lat = janus_lattice(s0, opts["scale_pos"], opts["scale_vel"])
                bit = all(a == b for a, b in zip(r["ret"], lat))
                rt_pos = dpos_m(r["ret"], lat)
                rt_vel = dvel_mms(r["ret"], lat)
            else:
                bit = all(a == b for a, b in zip(r["ret"], s0))
            row = dict(label=label, fwd_err_m=fwd_err, rt_pos_m=rt_pos, rt_vel_mms=rt_vel, bit_identical=bit,
                       wall_fwd_s=r["wall_fwd"], wall_back_s=r["wall_back"], fevals_fwd=r["fevals_fwd"],
                       steps_fwd=r["steps_fwd"], t_turn=r["t_turn"], t_end=r["t_end"])
            rows.append(row)
            print("%-26s fwd_err %10.3e m | round trip %10.3e m %10.3e mm/s bit=%s | fwd %6.2f s, %6d fevals, %6d steps | t_turn=%r t_end=%r" %
                  (label, fwd_err, rt_pos, rt_vel, bit, r["wall_fwd"], r["fevals_fwd"], r["steps_fwd"], r["t_turn"], r["t_end"]))
        out["sets"][set_name] = dict(ref_ias15_dt20=ref_a, ref_bs=ref_b, ref_diff_m=dpos_m(ref_a, ref_b), rows=rows)
    # the physics scale: what a 20% density error does in one day
    if not quick:
        base = build(s0, ("j2", "drag"), "ias15", {"epsilon": 1e-9}, 60.0)[0]
        base.integrate(T)
        hi = build(s0, ("j2", "drag"), "ias15", {"epsilon": 1e-9}, 60.0, rho_scale=1.2)[0]
        hi.integrate(T)
        nodrag = build(s0, ("j2",), "ias15", {"epsilon": 1e-9}, 60.0)[0]
        nodrag.integrate(T)
        d20 = dpos_m(state_of(base), state_of(hi))
        dall = dpos_m(state_of(base), state_of(nodrag))
        print("\nphysics scale, one day: drag on vs off moves the object %.1f m; density x1.2 moves it %.1f m" % (dall, d20))
        out["density_scale"] = dict(drag_vs_nodrag_m=dall, density_plus20pct_m=d20)
        print()
        out["cost_floor"] = cost_floor()
        print()
        out["global_step"] = global_step()
    with open(os.path.join(HERE, "leo_roundtrip.json"), "w") as fh:
        json.dump(out, fh, indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
