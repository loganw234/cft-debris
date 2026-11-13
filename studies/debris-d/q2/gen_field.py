"""gen_field.py - DEBRIS-D (cft-debris, MIT): write a v1 system for an
Earth-fixed spherical-harmonic field of degree N, with J2-to-N from
EIGEN-6C4, the Earth's rotation as forcing (cos and sin of w t), and drag
through the exponential atmosphere of j2dragrot-rk4.cftl, stepped by rk4.

The field is DEBRIS-C's normalised Cunningham V, W recursion
(studies/debris-c/m1a/m1a_grav.c, itself from DEBRIS-B's grav_body.inc),
unrolled: one let per V(n,m) and W(n,m) (W(n,0) = 0 is not formed), and
the acceleration sums written as fma chains. Every irrational recursion
coefficient, and every product of a normalisation ratio with C-bar or
S-bar, is a param (or a lane param with --lane), given to 40 significant
digits and rounded once by the language. Degrees 2..N are summed; the
central term is written apart, as -mu r / r^3.

usage: python -I -B gen_field.py <N> <out.cftl> [--lane]
  --lane: the field's coefficients are lane params (held in each lane's
          scratch) instead of params (the bank, 512 slots on every target).
"""
import sys
from mpmath import mp, mpf, sqrt

mp.dps = 60
GFC = "C:/Users/logan/source/repos/cft-debris-downloads/EIGEN6-C4.gfc/EIGEN6-C4.gfc"


def lit(v):
    s = mp.nstr(v, 40, min_fixed=-1, max_fixed=-1, strip_zeros=False)
    s = s.replace("e+", "e")
    if s.startswith("-"):
        return None
    return s


def read_gfc(N):
    C, S = {}, {}
    gm = re = None
    head = True
    for line in open(GFC):
        w = line.split()
        if not w:
            continue
        if head:
            if w[0] == "end_of_head":
                head = False
            elif w[0] == "earth_gravity_constant":
                gm = mpf(w[1])
            elif w[0] == "radius":
                re = mpf(w[1])
            continue
        if w[0] != "gfc":
            continue
        n, m = int(w[1]), int(w[2])
        if n <= N:
            C[(n, m)] = mpf(w[3].replace("D", "E"))
            S[(n, m)] = mpf(w[4].replace("D", "E"))
    return gm, re, C, S


def main():
    N = int(sys.argv[1])
    out = sys.argv[2]
    lane = "--lane" in sys.argv[3:]
    gm, re, C, S = read_gfc(N)
    L = N + 1
    params = []          # (name, value as mpf)

    def P(name, v):
        params.append((name, v))
        return name

    lines = []
    A = lines.append
    # recursion tables, as m1a_grav.c's tables()
    Dg = {m: (sqrt(3) if m == 1 else sqrt(mpf(2 * m + 1) / (2 * m))) for m in range(1, L + 1)}
    Sd = {m: sqrt(mpf(2 * m + 3)) for m in range(0, L)}
    An, Bn = {}, {}
    for n in range(0, L + 1):
        for m in range(0, n + 1):
            if n >= m + 2:
                An[(n, m)] = sqrt(mpf((2 * n - 1) * (2 * n + 1)) / ((n - m) * (n + m)))
                Bn[(n, m)] = sqrt(mpf((2 * n + 1) * (n + m - 1) * (n - m - 1)) / ((2 * n - 3) * (n + m) * (n - m)))
    F1, FA, FB, FZ = {}, {}, {}, {}
    for n in range(0, L):
        q = mpf(2 * n + 1) / (2 * n + 3)
        F1[n] = sqrt(mpf((2 * n + 1) * (n + 1) * (n + 2)) / (2 * (2 * n + 3)))
        for m in range(0, n + 1):
            FA[(n, m)] = sqrt(q * (n + m + 1) * (n + m + 2))
            FB[(n, m)] = mpf(0) if m == 0 else sqrt((2 if m == 1 else 1) * q * (n - m + 1) * (n - m + 2))
            FZ[(n, m)] = sqrt(q * (n + m + 1) * (n - m + 1))

    def sgn_param(name, v):
        """a param holding |v|, and whether the use must negate it"""
        if v == 0:
            return None, False
        return P(name, abs(v)), v < 0

    # the frame and the recursion's inputs
    A("let th  = w * t")
    A("let c   = cos(th)")
    A("let s   = sin(th)")
    A("let xb  = fma(c, x, s * y)")
    A("let yb  = fma(c, y, -(s * x))")
    A("let r2  = fma(x, x, fma(y, y, z * z))")
    A("let r   = sqrt(r2)")
    A("let ir  = 1 / r")
    A("let ir2 = ir * ir")
    A("let rho = re2 * ir2")
    A("let rir2 = re * ir2")
    A("let x0  = xb * rir2")
    A("let y0  = yb * rir2")
    A("let z0  = z * rir2")
    A("let V0_0 = re * ir")
    used = set()

    def V(n, m):
        return "V%d_%d" % (n, m)

    def W(n, m):
        return None if m == 0 else "W%d_%d" % (n, m)

    for m in range(0, L + 1):
        if m > 0:
            d = P("dg%d" % m, Dg[m])
            pv, pw = V(m - 1, m - 1), W(m - 1, m - 1)
            if pw is None:
                A("let %s = %s * (x0 * %s)" % (V(m, m), d, pv))
                A("let %s = %s * (y0 * %s)" % (W(m, m), d, pv))
            else:
                A("let %s = %s * fma(x0, %s, -(y0 * %s))" % (V(m, m), d, pv, pw))
                A("let %s = %s * fma(x0, %s, y0 * %s)" % (W(m, m), d, pw, pv))
        if m < L:
            sd = P("sd%d" % m, Sd[m])
            A("let zs%d = %s * z0" % (m, sd))
            A("let %s = zs%d * %s" % (V(m + 1, m), m, V(m, m)))
            if m > 0:
                A("let %s = zs%d * %s" % (W(m + 1, m), m, W(m, m)))
        for n in range(m + 2, L + 1):
            a = P("an%d_%d" % (n, m), An[(n, m)])
            b = P("bn%d_%d" % (n, m), Bn[(n, m)])
            A("let p%d_%d = %s * z0" % (n, m, a))
            A("let q%d_%d = %s * rho" % (n, m, b))
            A("let %s = fma(p%d_%d, %s, -(q%d_%d * %s))" % (V(n, m), n, m, V(n - 1, m), n, m, V(n - 2, m)))
            if m > 0:
                A("let %s = fma(p%d_%d, %s, -(q%d_%d * %s))" % (W(n, m), n, m, W(n - 1, m), n, m, W(n - 2, m)))
    # the sums, as fma chains
    ax, ay, az = [], [], []      # terms: (coef_param, negate, value_name)
    for n in range(2, N + 1):
        C0 = C[(n, 0)]
        p1, n1 = sgn_param("f1c%d" % n, F1[n] * C0)
        pz, nz = sgn_param("fzc%d_0" % n, FZ[(n, 0)] * C0)
        if p1:
            ax.append((p1, not n1, V(n + 1, 1)))      # ax -= F1 C0 V
            ay.append((p1, not n1, W(n + 1, 1)))
        if pz:
            az.append((pz, not nz, V(n + 1, 0)))
        for m in range(1, n + 1):
            Cnm, Snm = C[(n, m)], S[(n, m)]
            ha, hb = FA[(n, m)] / 2, FB[(n, m)] / 2
            a1, a1n = sgn_param("a1_%d_%d" % (n, m), ha * Cnm)
            a2, a2n = sgn_param("a2_%d_%d" % (n, m), ha * Snm)
            b1, b1n = sgn_param("b1_%d_%d" % (n, m), hb * Cnm)
            b2, b2n = sgn_param("b2_%d_%d" % (n, m), hb * Snm)
            z1, z1n = sgn_param("z1_%d_%d" % (n, m), FZ[(n, m)] * Cnm)
            z2, z2n = sgn_param("z2_%d_%d" % (n, m), FZ[(n, m)] * Snm)
            Vp, Wp = V(n + 1, m + 1), W(n + 1, m + 1)
            Vm, Wm = V(n + 1, m - 1), W(n + 1, m - 1)
            Vc, Wc = V(n + 1, m), W(n + 1, m)
            # ax += -(a1 Vp + a2 Wp) + (b1 Vm + b2 Wm)
            if a1: ax.append((a1, not a1n, Vp))
            if a2: ax.append((a2, not a2n, Wp))
            if b1: ax.append((b1, b1n, Vm))
            if b2 and Wm: ax.append((b2, b2n, Wm))
            # ay += (a2 Vp - a1 Wp) + (b2 Vm - b1 Wm)
            if a2: ay.append((a2, a2n, Vp))
            if a1: ay.append((a1, not a1n, Wp))
            if b2: ay.append((b2, b2n, Vm))
            if b1 and Wm: ay.append((b1, not b1n, Wm))
            # az -= z1 Vc + z2 Wc
            if z1: az.append((z1, not z1n, Vc))
            if z2: az.append((z2, not z2n, Wc))

    def chain(name, terms):
        cur = None
        for k, (pn, neg, v) in enumerate(terms):
            coef = ("-%s" % pn) if neg else pn
            nm = "%s%d" % (name, k)
            if cur is None:
                A("let %s = %s * %s" % (nm, coef, v))
            else:
                A("let %s = fma(%s, %s, %s)" % (nm, coef, v, cur))
            cur = nm
        return cur

    sx, sy, sz = chain("gx", ax), chain("gy", ay), chain("gz", az)
    A("let axb = kg * %s" % sx)
    A("let ayb = kg * %s" % sy)
    A("let azf = kg * %s" % sz)
    A("let axf = fma(c, axb, -(s * ayb))")
    A("let ayf = fma(s, axb, c * ayb)")
    A("let g   = mu * (ir2 * ir)")
    A("let rhoa = rho0 * exp(fma(-r, ih, a0))")
    A("let vrx = fma(w, y, vx)")
    A("let vry = fma(-w, x, vy)")
    A("let vr  = sqrt(fma(vrx, vrx, fma(vry, vry, vz * vz)))")
    A("let kd  = (bc * rhoa) * vr")
    A("d/dt t  = 1")
    A("d/dt x  = vx")
    A("d/dt y  = vy")
    A("d/dt z  = vz")
    A("d/dt vx = fma(-kd, vrx, fma(-g, x, axf))")
    A("d/dt vy = fma(-kd, vry, fma(-g, y, ayf))")
    A("d/dt vz = fma(-kd, vz, fma(-g, z, azf))")
    A("step   rk4, h = 60")
    head = ["; DEBRIS-D (cft-debris, MIT), written by gen_field.py: an Earth-fixed field",
            "; of degree %d (EIGEN-6C4, degrees 2..%d, normalised Cunningham recursion)," % (N, N),
            "; the central term, the Earth's rotation through cos and sin of w t, and",
            "; exponential drag, stepped by rk4 at 60 s. Coefficients as %s." % ("lane params" if lane else "params"),
            "system field%d" % N, "format fp64", "round  rne", "state  t, x, y, z, vx, vy, vz",
            "param  mu = 398600441800000",
            "param  w = 0.00007292115",
            "param  rho0 = 0.000000000003725",
            "param  ih = 1/58515",
            "param  a0 = 6778137/58515",
            "param  re = %s" % lit(re),
            "param  re2 = %s" % lit(re * re),
            "param  kg = %s" % lit(gm / (re * re)),
            "lane param bc = 0.011"]
    kw = "lane param" if lane else "param"
    for name, v in params:
        s = lit(v)
        assert s is not None
        head.append("%s %s = %s" % (kw, name, s))
    with open(out, "w", newline="\n") as f:
        f.write("\n".join(head + lines) + "\n")
    print("degree %d: %d coefficient %ss, %d lines" % (N, len(params), kw, len(head) + len(lines)))


if __name__ == "__main__":
    main()
