# e7_rebound.py - cft-debris M1, gate E7: REBOUND's IAS15 as a referee of our
# integrator. Our force model at native64 (tests/m1x.c, a DLL) is called from
# IAS15 through a ctypes callback, and the result is held to our own rk4.
# cft-debris, MIT licence (see LICENSE at the repository root). Written by
# DEBRIS-E, 2026-11-13. REBOUND (GPL-3.0) is imported as installed, never copied.
#
#   python -I -B tests/e7_rebound.py
import ctypes
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gatelib as g  # noqa: E402

CRITERIA = """
The run: one object-day (86,400 s) from E2's lane 0 (400 km circular, inclination 51.6 degrees; bc 0.011,
   cram 0.02 m^2/kg), our whole model at native64 with the C library's transcendentals: the central term,
   EIGEN-6C4 degrees 2..20 in the uniformly turning Earth, the Sun and the Moon from DE421, the 28-band
   exponential atmosphere, radiation pressure with the conical shadow; epoch 2008-07-03 00:00 TDB.
I1 our rk4 at h = 5 s (chosen before the data) against IAS15 at epsilon 1e-9 (REBOUND 5.1.1, gravity "none",
   force_is_velocity_dependent = 1, every acceleration from our callback): |r_rk4 - r_IAS15| <= TOL = 0.5 m at
   the day's end. Basis: DEBRIS-D's rk4 table, 0.148 m an object-day at 7.5 s (degree 20 with drag, a similar
   LEO orbit), times (5/7.5)^4 = 0.029 m by rk4's h^4 law; IAS15 itself 4.0e-7 m (DEBRIS-D); a margin of 17 for
   the forces DEBRIS-D's run lacked (the Sun, the Moon, radiation pressure and its shadow's kinks) and the
   different orbit.
C1 NEGATIVE CONTROL: J2 planted 1e-3 off relatively (C20-bar x 1.001) in the IAS15 run alone must break TOL.
REPORTED: IAS15's steps and evaluations; rk4 at 2.5 s against rk4 at 5 s (the h^4 law predicts a ratio near
   16 between 5 s's and 2.5 s's errors).
"""
TOL = 0.5
Y0 = ["6778136.3", "0.0", "0.0", "-0.0", "4763.308132757748", "6009.79917725315"]
BC, CRAM = 0.011, 0.02
DAY = 86400.0


def load():
    os.add_dll_directory("C:/msys64/mingw64/bin")
    dll = ctypes.CDLL(os.path.join(g.BUILD, "m1x.dll"))
    dll.m1x_init.argtypes = [ctypes.c_char_p, ctypes.c_int, ctypes.c_double, ctypes.c_double, ctypes.c_double]
    dll.m1x_init.restype = ctypes.c_int
    dll.m1x_accel.argtypes = [ctypes.c_double, ctypes.POINTER(ctypes.c_double), ctypes.POINTER(ctypes.c_double)]
    dll.m1x_rk4.argtypes = [ctypes.c_char_p, ctypes.c_long, ctypes.POINTER(ctypes.c_double)]
    dll.m1x_rk4.restype = ctypes.c_int
    dll.m1x_nevals.restype = ctypes.c_longlong
    return dll


def rk4(dll, h):
    assert dll.m1x_init(g.DOWNLOADS.encode(), 20, BC, CRAM, 0.0) == 0
    y = (ctypes.c_double * 6)(*[float(s) for s in Y0])
    n = int(round(DAY / float(h)))
    assert dll.m1x_rk4(h.encode(), n, y) == 0
    return list(y), 4 * n  # rk4: four evaluations a step


def ias15(dll, c20rel):
    import rebound
    assert dll.m1x_init(g.DOWNLOADS.encode(), 20, BC, CRAM, c20rel) == 0
    yin = (ctypes.c_double * 6)()
    aout = (ctypes.c_double * 3)()

    def f(simp):
        s = simp.contents
        p = s.particles[0]
        yin[0], yin[1], yin[2], yin[3], yin[4], yin[5] = p.x, p.y, p.z, p.vx, p.vy, p.vz
        dll.m1x_accel(s.t, yin, aout)
        p.ax, p.ay, p.az = aout[0], aout[1], aout[2]

    sim = rebound.Simulation()
    sim.gravity = "none"
    y0 = [float(s) for s in Y0]
    sim.add(m=0.0, x=y0[0], y=y0[1], z=y0[2], vx=y0[3], vy=y0[4], vz=y0[5])
    sim.additional_forces = f
    sim.force_is_velocity_dependent = 1
    sim.integrator = "ias15"
    sim.integrator.epsilon = 1e-9  # REBOUND 5: the integrator's configuration takes its fields
    sim.dt = 60.0
    sim.exact_finish_time = 1
    sim.integrate(DAY)
    p = sim.particles[0]
    return [p.x, p.y, p.z, p.vx, p.vy, p.vz], dll.m1x_nevals(), sim.steps_done, sim.t, sim.integrator.epsilon, rebound.__version__


def dist(a, b):
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a[:3], b[:3])))


def main():
    log = g.Log("e7_rebound", os.path.abspath(__file__), CRITERIA)
    log.w("# m1x.dll sha256 %s" % g.sha256(os.path.join(g.BUILD, "m1x.dll")))
    dll = load()
    yr, ner = rk4(dll, "5")
    log.w("# rk4 h 5 s: %d evaluations; final r %s" % (ner, ["%.6f" % v for v in yr[:3]]))
    yi, nei, steps, t, eps, ver = ias15(dll, 0.0)
    log.w("# IAS15 (REBOUND %s, epsilon %g): %d steps, %d evaluations, t %.3f s; final r %s" %
          (ver, eps, steps, nei, t, ["%.6f" % v for v in yi[:3]]))
    log.check(abs(t - DAY) < 1e-6 and eps == 1e-9, "IAS15 ran to t = 86400 s at epsilon 1e-9")
    d = dist(yr, yi)
    log.check(d <= TOL, "I1 |r_rk4(5 s) - r_IAS15| = %.4e m <= %.1f m at the day's end" % (d, TOL))
    yc, nec, stc, tc, _, _ = ias15(dll, 1e-3)
    dc = dist(yr, yc)
    log.check(dc > TOL, "C1 control: J2 planted 1e-3 off in IAS15 alone gives %.4e m > %.1f m (%.0f TOL)" % (dc, TOL, dc / TOL))
    y2, ne2 = rk4(dll, "2.5")
    log.w("REPORTED rk4 2.5 s (%d evaluations) against rk4 5 s: %.4e m; against IAS15: %.4e m; ratio of rk4 5 s's "
          "and 2.5 s's distances from IAS15: %.1f" % (ne2, dist(y2, yr), dist(y2, yi), d / max(dist(y2, yi), 1e-300)))
    return log.close()


if __name__ == "__main__":
    sys.exit(main())
