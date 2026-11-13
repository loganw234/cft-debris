# e7_diag.py - cft-debris M1, a diagnosis beside gate E7 (no gate): does our rk4
# converge on IAS15 as its step shrinks, and does IAS15 move with its epsilon?
# cft-debris, MIT licence (see LICENSE at the repository root). Written by
# DEBRIS-E, 2026-11-13, after e7_rebound.001.log reported rk4 at 2.5 s and at
# 5 s both about 0.1 m from IAS15 (ratio 1.2 where the h^4 law predicts ~16).
#
#   python -I -B tests/e7_diag.py
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gatelib as g  # noqa: E402
import e7_rebound as e7  # noqa: E402

CRITERIA = """
No pass condition (a diagnosis). The same day and model as E7. Reported: rk4 at 5, 2.5, 1.25 and 0.625 s against
   one another (does rk4 converge, and at what order?) and against IAS15 at epsilon 1e-9 and 1e-10 (does IAS15
   move with its epsilon?).
Version 2 adds, with m1x_init2: the same comparisons (rk4 at 1.25 s; IAS15 at 1e-9 and 1e-10) for the model made
   smooth in turn - radiation pressure off, the atmosphere one continuous band, and both - to see which of the
   model's non-smooth parts (the shadow's edges, the 28-band table's density steps) IAS15 does not resolve.
Version 3 adds, for the smooth model (radiation off, one band): rk4 at 0.625 s against rk4 at 1.25 s and against
   IAS15, to see whether the 5.9e-5 m left between rk4 at 1.25 s and IAS15 there is rk4's own truncation.
"""


def init(dll, srp=1, nb=28):
    import ctypes
    dll.m1x_init2.argtypes = [ctypes.c_char_p, ctypes.c_int, ctypes.c_double, ctypes.c_double, ctypes.c_double,
                              ctypes.c_int, ctypes.c_int]
    dll.m1x_init2.restype = ctypes.c_int
    assert dll.m1x_init2(g.DOWNLOADS.encode(), 20, e7.BC, e7.CRAM, 0.0, srp, nb) == 0


def rk4c(dll, h, srp, nb):
    import ctypes
    init(dll, srp, nb)
    y = (ctypes.c_double * 6)(*[float(s) for s in e7.Y0])
    assert dll.m1x_rk4(h.encode(), int(round(e7.DAY / float(h))), y) == 0
    return list(y)


def ias(dll, eps, srp=1, nb=28):
    import rebound
    import ctypes
    init(dll, srp, nb)
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
    y0 = [float(s) for s in e7.Y0]
    sim.add(m=0.0, x=y0[0], y=y0[1], z=y0[2], vx=y0[3], vy=y0[4], vz=y0[5])
    sim.additional_forces = f
    sim.force_is_velocity_dependent = 1
    sim.integrator = "ias15"
    sim.integrator.epsilon = eps
    sim.dt = 60.0
    sim.exact_finish_time = 1
    sim.integrate(e7.DAY)
    p = sim.particles[0]
    return [p.x, p.y, p.z], sim.steps_done, dll.m1x_nevals()


def main():
    log = g.Log("e7_diag", os.path.abspath(__file__), CRITERIA)
    dll = e7.load()
    R = {}
    for h in ("5", "2.5", "1.25", "0.625"):
        R[h] = e7.rk4(dll, h)[0]
    for a, b in (("5", "2.5"), ("2.5", "1.25"), ("1.25", "0.625")):
        log.w("MEASURED rk4 %s s against %s s: %.4e m" % (a, b, e7.dist(R[a], R[b])))
    I = {}
    for eps in (1e-9, 1e-10):
        I[eps] = ias(dll, eps)
        log.w("MEASURED IAS15 epsilon %g: %d steps, %d evaluations" % (eps, I[eps][1], I[eps][2]))
    log.w("MEASURED IAS15 1e-9 against 1e-10: %.4e m" % e7.dist(I[1e-9][0], I[1e-10][0]))
    for h in R:
        log.w("MEASURED rk4 %s s against IAS15 1e-9: %.4e m; against IAS15 1e-10: %.4e m" %
              (h, e7.dist(R[h], I[1e-9][0]), e7.dist(R[h], I[1e-10][0])))
    for srp, nb, label in ((0, 28, "radiation off, 28 bands"), (1, 1, "radiation on, one band"),
                           (0, 1, "radiation off, one band")):
        r = rk4c(dll, "1.25", srp, nb)
        a9, a10 = ias(dll, 1e-9, srp, nb), ias(dll, 1e-10, srp, nb)
        log.w("MEASURED %s: IAS15 1e-9 against 1e-10 %.4e m (%d and %d steps); rk4 1.25 s against IAS15 1e-9 "
              "%.4e m, against 1e-10 %.4e m" % (label, e7.dist(a9[0], a10[0]), a9[1], a10[1], e7.dist(r, a9[0]),
                                                e7.dist(r, a10[0])))
    r1, r2 = rk4c(dll, "1.25", 0, 1), rk4c(dll, "0.625", 0, 1)
    a9 = ias(dll, 1e-9, 0, 1)
    log.w("MEASURED radiation off, one band: rk4 1.25 s against 0.625 s %.4e m; rk4 0.625 s against IAS15 1e-9 %.4e m; "
          "rk4 1.25 s against IAS15 1e-9 %.4e m" % (e7.dist(r1, r2), e7.dist(r2, a9[0]), e7.dist(r1, a9[0])))
    return log.close()


if __name__ == "__main__":
    sys.exit(main())
