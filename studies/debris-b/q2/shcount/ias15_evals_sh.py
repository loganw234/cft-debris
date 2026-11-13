#!/usr/bin/env python3
"""DEBRIS-B Q2: does a richer force model change IAS15's force evaluations
per object-day? The LEO orbit of ias15_evals.py (400 km, e 0.001, i 51.6,
Omega 30, omega 40, M 10 deg), one day, epsilon 1e-9, the same counter.

The force is the Earth-fixed spherical-harmonic field of q2bench.c (the
same synthetic Kaula-rule coefficients, C20 at its real value), degrees 2..N
(REBOUND supplies the central term), evaluated in C through gravdll.dll, in
a frame turning at the Earth's rate: r_ef = Rz(theta) r, a = Rz(-theta) a_ef,
theta = 0.3 + 7.292115e-5 t. Optionally an exponential drag (Vallado-like
400 km band, B = 0.022 m^2/kg, co-rotating air), velocity-dependent.
The kernel's own gravity is checked in q2_check.py; this script only counts.

  python -I -B ias15_evals_sh.py
"""
import ctypes
import math
import os
import sys

import rebound

HERE = os.path.dirname(os.path.abspath(__file__))
os.add_dll_directory(r"C:\msys64\mingw64\bin")
DLL = ctypes.CDLL(os.path.join(HERE, "gravdll.dll"))
DLL.grav_init.argtypes = [ctypes.c_int]
DLL.grav_eval.argtypes = [ctypes.POINTER(ctypes.c_double), ctypes.c_int, ctypes.c_int, ctypes.POINTER(ctypes.c_double)]
GM = 398600.4418
WE = 7.292115e-5
RE = 6378.137
RHO0, H0, HS, BC = 3.725e-12, 400.0, 58.515, 0.022


def make_force(N, drag, calls):
    rin = (ctypes.c_double * 3)()
    aout = (ctypes.c_double * 3)()

    def f(simp):
        s = simp.contents
        calls.append(s.t)
        e, p = s.particles[0], s.particles[1]
        x, y, z = p.x - e.x, p.y - e.y, p.z - e.z
        th = 0.3 + WE * s.t
        c, sn = math.cos(th), math.sin(th)
        rin[0] = c * x + sn * y
        rin[1] = -sn * x + c * y
        rin[2] = z
        DLL.grav_eval(rin, 2, N, aout)
        ax = c * aout[0] - sn * aout[1]
        ay = sn * aout[0] + c * aout[1]
        az = aout[2]
        if drag:
            r = math.sqrt(x * x + y * y + z * z)
            rho = RHO0 * math.exp(-(r - RE - H0) / HS)
            vx, vy, vz = p.vx + WE * y, p.vy - WE * x, p.vz
            v = math.sqrt(vx * vx + vy * vy + vz * vz)
            k = -0.5e3 * rho * BC * v
            ax += k * vx
            ay += k * vy
            az += k * vz
        p.ax += ax
        p.ay += ay
        p.az += az
    return f


def run(N, drag=False, eps=1e-9):
    assert DLL.grav_init(N) == 0
    sim = rebound.Simulation()
    sim.G = 1.0
    sim.add(m=GM)
    sim.add(primary=sim.particles[0], m=0.0, a=6778.137, e=0.001, inc=math.radians(51.6),
            Omega=math.radians(30.0), omega=math.radians(40.0), M=math.radians(10.0))
    sim.N_active = 1
    sim.testparticle_type = 0
    calls = []
    sim.additional_forces = make_force(N, drag, calls)
    if drag:
        sim.force_is_velocity_dependent = 1
    sim.integrator = "ias15"
    sim.integrator.epsilon = eps
    sim.dt = 60.0
    sim.integrate(86400.0)
    return len(calls), sim.steps_done


def main():
    print("# REBOUND %s; LEO 400 km, one day, epsilon 1e-9; Earth-fixed SH field, degrees 2..N" % rebound.__version__)
    for N in (2, 8, 20, 36, 70):
        n, st = run(N)
        print("SH N=%2d            : %6d force evaluations, %4d steps" % (N, n, st), flush=True)
    for N in (20, 70):
        n, st = run(N, drag=True)
        print("SH N=%2d + exp. drag: %6d force evaluations, %4d steps" % (N, n, st), flush=True)
    n, st = run(20, eps=1e-6)
    print("SH N=20, epsilon 1e-6: %6d force evaluations, %4d steps" % (n, st), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
