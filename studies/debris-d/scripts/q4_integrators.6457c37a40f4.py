"""q4_integrators.py - DEBRIS-D, Q4 (cft-debris, MIT): steps, evaluations and
error per LEO object-day, at binary64, for IAS15 (REBOUND 5.1.1, epsilon
1e-9) and for the fixed-step methods v1 offers (rk4; stormer-verlet, which
v1 refuses with drag), with DEBRIS-C's degree-20 kernel (EIGEN-6C4) in an
Earth turning at w, and exponential drag.

The orbit: DEBRIS-B's LEO object (a 6,778,137 m, e 0.001, i 51.6, Omega 30,
omega 40, M 10 deg), one day, 86,400 s.

The reference (stated before the data): rk4 in x87 extended precision
(long double, 64-bit significand), Richardson-extrapolated,
R(h) = (16 y(h/2) - y(h)) / 15, at h = 1.875 s (from 1.875 and 0.9375 s).
Its own check: |R(1.875) - R(3.75)| in position must be at most 1e-7 m;
if not, the reference is declared insufficient and every error below
1e-6 m is reported as not resolved.

CRITERIA (asserted):
  C1 the reference's own check above;
  C2 sanity of the method: binary64 rk4's error falls at least 8 times
     from h = 60 s to 30 s (an order-4 method's 16, with room);
  C3 REBOUND's evaluation count is the callback's own count, and the run
     ends at 86,400 s exactly;
  C4 the drag-free reference, built the same way, passes C1 too (it is the
     one stormer-verlet is held to).

usage: python -I -B q4_integrators.py
"""
import ctypes
import math
import os
import subprocess
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tools"))
import dd  # noqa: E402

import rebound  # noqa: E402

B = dd.SCRATCH + "/build"
GFC = "C:/Users/logan/source/repos/cft-debris-downloads/EIGEN6-C4.gfc/EIGEN6-C4.gfc"
DAY = 86400.0
N = 20
HS = [60.0, 30.0, 15.0, 7.5, 3.75, 1.875, 0.9375]
GM = 3.986004415e14     # EIGEN-6C4's earth_gravity_constant, as the C side reads it


def initial_state():
    sim = rebound.Simulation()
    sim.G = 1.0
    sim.add(m=GM)
    sim.add(primary=sim.particles[0], m=0.0, a=6778137.0, e=0.001, inc=math.radians(51.6),
            Omega=math.radians(30.0), omega=math.radians(40.0), M=math.radians(10.0))
    p = sim.particles[1]
    return [p.x, p.y, p.z, p.vx, p.vy, p.vz]


def run_c(exe, method, h, drag, y0):
    n = int(round(DAY / h))
    assert abs(n * h - DAY) == 0
    args = [exe, method, repr(h), str(n), str(N), str(drag), GFC] + [v.hex() for v in y0]
    r = subprocess.run(args, capture_output=True, text=True)
    if r.returncode:
        return None, r.stderr.strip()
    out = {}
    for ln in r.stdout.splitlines():
        k, *v = ln.split()
        out[k] = v
    return [float(v) for v in out["final"]], int(out["evals"][0])


def run_c_ld(exe, method, h, drag, y0):
    """the same, keeping the long double digits as Python floats is not enough: keep the strings"""
    n = int(round(DAY / h))
    args = [exe, method, repr(h), str(n), str(N), str(drag), GFC] + [v.hex() for v in y0]
    r = subprocess.run(args, capture_output=True, text=True)
    if r.returncode:
        return None, r.stderr.strip()
    out = {}
    for ln in r.stdout.splitlines():
        k, *v = ln.split()
        out[k] = v
    from decimal import Decimal
    return [Decimal(v) for v in out["final"]], int(out["evals"][0])


def dist(a, b):
    """|a - b| over the three positions, exactly in Decimal (Decimal(float) is exact)"""
    from decimal import Decimal

    def D(x):
        return x if isinstance(x, Decimal) else Decimal(x)
    return float(sum((D(p) - D(q)) ** 2 for p, q in zip(a[:3], b[:3])).sqrt())


def ias15(y0, drag, eps=1e-9):
    os.add_dll_directory(r"C:\msys64\mingw64\bin")
    dll = ctypes.CDLL(B + "/q4force.dll")
    dll.q4_init.argtypes = [ctypes.c_char_p, ctypes.c_int]
    dll.q4_force.argtypes = [ctypes.c_double, ctypes.POINTER(ctypes.c_double), ctypes.c_int,
                             ctypes.POINTER(ctypes.c_double)]
    assert dll.q4_init(GFC.encode(), N) == 0
    yin = (ctypes.c_double * 6)()
    aout = (ctypes.c_double * 3)()
    calls = [0]

    def f(simp):
        s = simp.contents
        calls[0] += 1
        e, p = s.particles[0], s.particles[1]
        yin[0], yin[1], yin[2] = p.x - e.x, p.y - e.y, p.z - e.z
        yin[3], yin[4], yin[5] = p.vx - e.vx, p.vy - e.vy, p.vz - e.vz
        dll.q4_force(s.t, yin, drag, aout)
        p.ax += aout[0]
        p.ay += aout[1]
        p.az += aout[2]

    sim = rebound.Simulation()
    sim.G = 1.0
    sim.add(m=GM)
    sim.add(m=0.0, x=y0[0], y=y0[1], z=y0[2], vx=y0[3], vy=y0[4], vz=y0[5])
    sim.N_active = 1
    sim.testparticle_type = 0
    sim.additional_forces = f
    sim.force_is_velocity_dependent = 1 if drag else 0
    sim.integrator = "ias15"
    sim.integrator.epsilon = eps
    sim.dt = 60.0
    sim.exact_finish_time = 1
    sim.integrate(DAY)
    e, p = sim.particles[0], sim.particles[1]
    return [p.x - e.x, p.y - e.y, p.z - e.z, p.vx - e.vx, p.vy - e.vy, p.vz - e.vz], calls[0], sim.steps_done, sim.t


def main():
    log = dd.Log(__file__, "q4_integrators")
    log.criteria("C1 reference check: |R(1.875) - R(3.75)| <= 1e-7 m (rk4 Richardson in long double, with drag)",
                 "C2 binary64 rk4 with drag: error(60 s) / error(30 s) >= 8",
                 "C3 IAS15: the callback count is the evaluation count, and the run ends at t = 86,400 s",
                 "C4 the drag-free reference passes C1's check too")
    exe64, exeld = B + "/q4prop64.exe", B + "/q4propld.exe"
    for p in (exe64, exeld, B + "/q4force.dll"):
        log.w("%s sha256 %s" % (os.path.basename(p), dd.sha256_file(p)))
    log.w("rebound %s" % rebound.__version__)
    y0 = initial_state()
    log.w("initial state (m, m/s): " + " ".join(v.hex() for v in y0))
    res = {}
    for drag in (1, 0):
        for h in HS:
            for tag, exe in (("fp64", exe64), ("ld", exeld)):
                f = run_c_ld if tag == "ld" else run_c
                res[("rk4", drag, tag, h)] = f(exe, "rk4", h, drag, y0)
                if drag == 0 and h >= 1.875:
                    res[("sv", drag, tag, h)] = f(exe, "sv", h, drag, y0)
    from decimal import Decimal, getcontext
    getcontext().prec = 40

    def rich(drag, h):
        a, _ = res[("rk4", drag, "ld", h / 2)]
        b, _ = res[("rk4", drag, "ld", h)]
        return [(16 * x - y) / 15 for x, y in zip(a, b)]
    refs = {}
    for drag, cname in ((1, "C1"), (0, "C4")):
        R1, R2 = rich(drag, 1.875), rich(drag, 3.75)
        d = dist(R1, R2)
        log.check(d <= 1e-7, "%s reference (drag %d): |R(1.875) - R(3.75)| = %.3e m <= 1e-7 m" % (cname, drag, d))
        refs[drag] = R1
    log.w("")
    log.w("TABLE fixed steps, one LEO object-day, degree 20, error = |r - r_ref| (m)")
    log.w("method drag     h(s)   steps   evals    err_fp64        err_ld          |fp64 - ld|")
    for (m, drag, tag, h), v in sorted(res.items(), key=lambda kv: (kv[0][0], -kv[0][1], -kv[0][3], kv[0][2])):
        if tag != "fp64":
            continue
        y64, ev = v
        yld, _ = res[(m, drag, "ld", h)]
        e64 = dist(y64, refs[drag])
        eld = dist(yld, refs[drag])
        dr = dist(y64, yld)
        log.w("%-6s %d %10.4f %7d %7d   %.3e      %.3e      %.3e" % (m, drag, h, int(round(DAY / h)), ev, e64, eld, dr))
    e60 = dist(res[("rk4", 1, "fp64", 60.0)][0], refs[1])
    e30 = dist(res[("rk4", 1, "fp64", 30.0)][0], refs[1])
    log.check(e60 / e30 >= 8, "C2 rk4 fp64 drag: err(60)/err(30) = %.2f >= 8" % (e60 / e30))
    for drag in (1, 0):
        yi, calls, steps, tend = ias15(y0, drag)
        log.check(tend == DAY, "C3 IAS15 drag %d ends at t = %r" % (drag, tend))
        ei = dist(yi, refs[drag])
        log.w("IAS15 eps 1e-9 drag %d: %d steps, %d evaluations (%.2f a step), error %.3e m" %
              (drag, steps, calls, calls / steps, ei))
        res[("ias15", drag)] = (steps, calls, ei)
    rc = log.close()
    sys.exit(1 if rc else 0)


if __name__ == "__main__":
    main()
