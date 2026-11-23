"""i_gen.py - cft-debris DEBRIS-I: the generator of the program's cft source and of its part systems.

cft-debris, MIT licence (see LICENSE at the repository root). Written by DEBRIS-I, 2026-11-23. Its unrolled
Cunningham recursion and the shape of its writer follow DEBRIS-D's studies/debris-d/q2/gen_field.py (cft-debris's
own, MIT), with M1's operation order (src/m1_physics.h, ph_grav) in place of DEBRIS-D's: M1's tables (An, Bn, Dg, Sd,
P1, PZ0, hFA, hFB, FZ, C, S) are the program's values, and each operation of ph_grav, ph_central, ph_third,
ph_series, ph_bodies, ph_frame_apply and ph_drag_g is one node here, in M1's order, but where M1 multiplies or adds an
exact zero (W(n, 0), the first Clenshaw step, the sums' starting 0), which is left out: those operations change no
nonzero value.

The program: state t, x, y, z, vx, vy, vz (TDB s from JD 2461329.5; m; m/s), rk4 at h = 15 s, and
    d/dt v = ((((central + harmonics) + Sun) + Moon) + drag)          (M1's sum, src/m1_physics.h ph_accel)
  - central: -GM r / |r|^3;
  - harmonics, degrees 2..N, in the Earth-fixed frame rb = M^T r, rotated back by M;
  - the Sun and the Moon as point masses at their geocentric positions from DE421's series for the run's
    sub-interval (tau from t, Clenshaw from the highest coefficient down, Earth = EMB - Moon/(1 + EMRAT));
  - drag through M1's exponential atmosphere (28 bands by selects, or one band), v_rel = v - Omega x r;
  - M (9, GCRS <- ITRS, row-major) and Omega (3, rad/s) as polynomials in s = t - tc, by Horner (fma), whose
    coefficients are the run's (the frame's form, DEBRIS-I's design; tests/i_vals.py fits them).
No radiation pressure.

EVERY DATA VALUE IS A PARAM OR A LANE PARAM, default 0, filled per run by the driver (tests/i_vals.py writes the
values). The source holds no number but the step, 15, and the formulas' own small exact numbers (1). So a generated
source carries no third-party data.

The layout: each group of values is put in the bank (param) or in the lanes (lane param):
    grav   M1's gravity tables to degree N (3 + 8 + 8 + 2 x 28 ... for N = 7: 222 values)
    bands  the atmosphere's bands (28 x 3, or 1 x 3)
    scal   gm, gms, gmm, rearth, km, fem
    de     DE421's coefficients for the run's sub-interval (Moon 13 x 3, Sun 11 x 3, EMB 13 x 3), the three
           sub-interval lengths and their starts (117 values)
    frame  the frame's polynomial coefficients and tc
bc is always a lane param.

usage:
  python -I -B i_gen.py program --degree N --format F --bands 28|1 --dm D --do D --layout L --out FILE
  python -I -B i_gen.py part --part central|grav|tides|bodies|frame|drag --degree N --format F --bands 28|1
                        --dm D --do D --out FILE
  python -I -B i_gen.py names --degree N --bands B --dm D --do D        (the value names, by group, as JSON)
  python -I -B i_gen.py program20 --format F --out FILE                  (I6: degree 20, every value a lane param)
The layout L is "bank:<group>,<group>;lane:<group>,..." and must name every group once.
"""
import argparse
import json
import sys

DE_NC = {"mo": 13, "su": 11, "em": 13}       # DE421's coefficients a component (header.421, GROUP 1050)
DE_ORDER = ("mo", "su", "em")                 # the Moon, the Sun, the EMB (M1's m1_ephq order)


# ------------------------------------------------------------------ the value names, by group

def grav_names(N):
    """M1's tables for degrees 2..N (src/m1_physics.h, ph_setup): their names in a fixed order."""
    L = N + 1
    out = ["re", "re2", "kacc"]
    out += ["dg%d" % m for m in range(1, L + 1)]
    out += ["sd%d" % m for m in range(0, L)]
    for m in range(0, L + 1):
        for n in range(m + 2, L + 1):
            out += ["an%d_%d" % (n, m), "bn%d_%d" % (n, m)]
    for n in range(2, N + 1):
        out += ["p1_%d" % n, "pz_%d" % n]
        for m in range(1, n + 1):
            out += ["c%d_%d" % (n, m), "s%d_%d" % (n, m), "ha%d_%d" % (n, m), "hb%d_%d" % (n, m),
                    "fz%d_%d" % (n, m)]
    return out


def band_names(nb):
    return ["bh%d" % b for b in range(nb)] + ["br%d" % b for b in range(nb)] + ["bs%d" % b for b in range(nb)]


SCAL = ["gm", "gms", "gmm", "rearth", "km", "fem"]


def de_names():
    out = []
    for k in DE_ORDER:
        for j in range(3):
            out += ["%s%d_%d" % (k, j, i) for i in range(DE_NC[k])]
    out += ["l" + k for k in DE_ORDER] + ["t" + k for k in DE_ORDER]
    return out


def frame_names(dm, do):
    out = []
    for e in range(9):
        out += ["fm%d_%d" % (e, k) for k in range(dm + 1)]
    for e in range(3):
        out += ["fo%d_%d" % (e, k) for k in range(do + 1)]
    return out + ["tc"]


def groups(N, nb, dm, do):
    return {"grav": grav_names(N), "bands": band_names(nb), "scal": list(SCAL), "de": de_names(),
            "frame": frame_names(dm, do)}


# ------------------------------------------------------------------ the writer

class W:
    def __init__(self):
        self.lines = []

    def let(self, name, expr):
        self.lines.append("let %s = %s" % (name, expr))
        return name


def poly(c, var):
    """Horner from the highest coefficient down: fma(fma(c_d, s, c_{d-1}), s, ...)."""
    e = c[-1]
    for k in range(len(c) - 2, -1, -1):
        e = "fma(%s, %s, %s)" % (e, var, c[k])
    return e


def w_frame(w, t, dm, do):
    """M (m0..m8, row-major, GCRS <- ITRS) and Omega (om0..om2) at s = t - tc."""
    s = w.let("fs", "%s - tc" % t)
    M = [w.let("m%d" % e, poly(["fm%d_%d" % (e, k) for k in range(dm + 1)], s)) for e in range(9)]
    O = [w.let("om%d" % e, poly(["fo%d_%d" % (e, k) for k in range(do + 1)], s)) for e in range(3)]
    return M, O


def w_apply(w, pre, M, v, inverse):
    """M1's ph_frame_apply: inverse 0 out = M^T v, inverse 1 out = M v; out_i = fma(a2, v2, fma(a1, v1, a0 v0))."""
    out = []
    for i in range(3):
        a0, a1, a2 = (M[3 * i], M[3 * i + 1], M[3 * i + 2]) if inverse else (M[i], M[3 + i], M[6 + i])
        out.append(w.let("%s%d" % (pre, i), "fma(%s, %s, fma(%s, %s, %s * %s))" % (a2, v[2], a1, v[1], a0, v[0])))
    return out


def w_central(w, r):
    """M1's ph_central: r2 = (x x + y y) + z z; k = -(GM / (r2 sqrt(r2))); a = k r. Returns (a, rn)."""
    w.let("r2", "%s * %s + %s * %s + %s * %s" % (r[0], r[0], r[1], r[1], r[2], r[2]))
    rn = w.let("rn", "sqrt(r2)")
    w.let("kc", "-(gm / (r2 * rn))")
    return [w.let("c%s" % a, "kc * %s" % r[i]) for i, a in enumerate("xyz")], rn


def w_grav(w, rb, N):
    """M1's ph_grav for degrees 2..N at the Earth-fixed position rb: KACC times the sums, Earth-fixed."""
    L = N + 1
    w.let("gr2", "%s * %s + %s * %s + %s * %s" % (rb[0], rb[0], rb[1], rb[1], rb[2], rb[2]))
    w.let("ir2", "1 / gr2")
    w.let("rho", "re2 * ir2")
    w.let("x0", "(re * %s) * ir2" % rb[0])
    w.let("y0", "(re * %s) * ir2" % rb[1])
    w.let("z0", "(re * %s) * ir2" % rb[2])
    w.let("V0_0", "re / sqrt(gr2)")

    def V(n, m):
        return "V%d_%d" % (n, m)

    def Wn(n, m):
        return None if m == 0 else "W%d_%d" % (n, m)

    for m in range(0, L + 1):
        if m > 0:
            pv, pw = V(m - 1, m - 1), Wn(m - 1, m - 1)
            if pw is None:      # W(0, 0) = 0: x0 V - y0 0 and x0 0 + y0 V, the zero terms left out
                w.let(V(m, m), "dg%d * (x0 * %s)" % (m, pv))
                w.let(Wn(m, m), "dg%d * (y0 * %s)" % (m, pv))
            else:
                w.let(V(m, m), "dg%d * (x0 * %s - y0 * %s)" % (m, pv, pw))
                w.let(Wn(m, m), "dg%d * (x0 * %s + y0 * %s)" % (m, pw, pv))
        if m < L:
            w.let("zs%d" % m, "sd%d * z0" % m)
            w.let(V(m + 1, m), "zs%d * %s" % (m, V(m, m)))
            if m > 0:
                w.let(Wn(m + 1, m), "zs%d * %s" % (m, Wn(m, m)))
        for n in range(m + 2, L + 1):
            w.let("p%d_%d" % (n, m), "an%d_%d * z0" % (n, m))
            w.let("q%d_%d" % (n, m), "bn%d_%d * rho" % (n, m))
            w.let(V(n, m), "p%d_%d * %s - q%d_%d * %s" % (n, m, V(n - 1, m), n, m, V(n - 2, m)))
            if m > 0:
                w.let(Wn(n, m), "p%d_%d * %s - q%d_%d * %s" % (n, m, Wn(n - 1, m), n, m, Wn(n - 2, m)))
    # the sums, in M1's order: per degree n, the zonal terms, then m = 1..n; ax and ay add, az subtracts
    acc = {"x": None, "y": None, "z": None}
    k = {"x": 0, "y": 0, "z": 0}

    def upd(a, op, term):
        cur = acc[a]
        if cur is None:     # M1 starts from 0: 0 - u is -u, 0 + u is u
            e = ("-(%s)" % term) if op == "-" else term
        else:
            e = "%s %s %s" % (cur, op, term)
        acc[a] = w.let("g%s%d" % (a, k[a]), e)
        k[a] += 1

    for n in range(2, N + 1):
        upd("x", "-", "p1_%d * %s" % (n, V(n + 1, 1)))
        upd("y", "-", "p1_%d * %s" % (n, Wn(n + 1, 1)))
        upd("z", "-", "pz_%d * %s" % (n, V(n + 1, 0)))
        for m in range(1, n + 1):
            C, S = "c%d_%d" % (n, m), "s%d_%d" % (n, m)
            vp, wp, vm, wm = V(n + 1, m + 1), Wn(n + 1, m + 1), V(n + 1, m - 1), Wn(n + 1, m - 1)
            vc, wc = V(n + 1, m), Wn(n + 1, m)
            t1 = w.let("t1_%d_%d" % (n, m), "%s * %s + %s * %s" % (C, vp, S, wp))
            t2 = w.let("t2_%d_%d" % (n, m), ("%s * %s + %s * %s" % (C, vm, S, wm)) if wm else ("%s * %s" % (C, vm)))
            t3 = w.let("t3_%d_%d" % (n, m), "%s * %s - %s * %s" % (S, vp, C, wp))
            t4 = w.let("t4_%d_%d" % (n, m), ("%s * %s - %s * %s" % (S, vm, C, wm)) if wm else ("%s * %s" % (S, vm)))
            t5 = w.let("t5_%d_%d" % (n, m), "%s * %s + %s * %s" % (C, vc, S, wc))
            # M1: u = nhFA t1 + hFB t2, nhFA = -hFA exactly; hb t2 - ha t1 is the same rounding of the same sum
            upd("x", "+", "(hb%d_%d * %s - ha%d_%d * %s)" % (n, m, t2, n, m, t1))
            upd("y", "+", "(ha%d_%d * %s + hb%d_%d * %s)" % (n, m, t3, n, m, t4))
            upd("z", "-", "fz%d_%d * %s" % (n, m, t5))
    return [w.let("f%s" % a, "kacc * %s" % acc[a]) for a in "xyz"]


def w_series(w, t, k):
    """M1's ph_series for one series k (mo, su, em): the position (km) at t from the run's sub-interval."""
    d = w.let("d%s" % k, "%s - t%s" % (t, k))
    tau = w.let("ta%s" % k, "(%s + %s) / l%s - 1" % (d, d, k))
    t2 = w.let("tt%s" % k, "%s + %s" % (tau, tau))
    nc = DE_NC[k]
    out = []
    for j in range(3):
        c = ["%s%d_%d" % (k, j, i) for i in range(nc)]
        b1, b2 = c[nc - 1], None     # M1's first step, fma(t2, 0, c) - 0, is c itself
        for i in range(nc - 2, 0, -1):
            e = "fma(%s, %s, %s)" % (t2, b1, c[i])
            if b2 is not None:
                e = "%s - %s" % (e, b2)
            b0 = w.let("b%s%d_%d" % (k, j, i), e)
            b2, b1 = b1, b0
        out.append(w.let("%s%d" % (k, j), "fma(%s, %s, %s) - %s" % (tau, b1, c[0], b2)))
    return out


def w_bodies(w, t):
    """M1's ph_bodies: the geocentric Sun and Moon (m) at t."""
    mo = w_series(w, t, "mo")
    su = w_series(w, t, "su")
    em = w_series(w, t, "em")
    sun, moon = [], []
    for i in range(3):
        e = w.let("ea%d" % i, "%s - fem * %s" % (em[i], mo[i]))
        sx = w.let("sx%d" % i, "%s - %s" % (su[i], e))
        sun.append(w.let("sun%d" % i, "km * %s" % sx))
        moon.append(w.let("mn%d" % i, "km * %s" % mo[i]))
    return sun, moon


def w_third(w, pre, gmb, r, s):
    """M1's ph_third: a = GM (d/|d|^3 - s/|s|^3), d = s - r."""
    d = [w.let("d%s%d" % (pre, i), "%s - %s" % (s[i], r[i])) for i in range(3)]
    w.let("dd%s" % pre, "%s * %s + %s * %s + %s * %s" % (d[0], d[0], d[1], d[1], d[2], d[2]))
    w.let("qd%s" % pre, "%s / (dd%s * sqrt(dd%s))" % (gmb, pre, pre))
    w.let("q2%s" % pre, "%s * %s + %s * %s + %s * %s" % (s[0], s[0], s[1], s[1], s[2], s[2]))
    w.let("qs%s" % pre, "%s / (q2%s * sqrt(q2%s))" % (gmb, pre, pre))
    return [w.let("a%s%d" % (pre, i), "qd%s * %s - qs%s * %s" % (pre, d[i], pre, s[i])) for i in range(3)]


def w_drag(w, r, v, om, rn, nb):
    """M1's ph_drag_g with Omega given: rho from the band whose base is the highest at or below h = |r| - R."""
    w.let("hh", "%s - rearth" % rn)
    h0, rh, hs = "bh0", "br0", "bs0"
    for b in range(1, nb):
        g = w.let("ge%d" % b, "bh%d <= hh" % b)
        h0 = w.let("h0_%d" % b, "select(%s, bh%d, %s)" % (g, b, h0))
        rh = w.let("rh%d" % b, "select(%s, br%d, %s)" % (g, b, rh))
        hs = w.let("hs%d" % b, "select(%s, bs%d, %s)" % (g, b, hs))
    w.let("ud", "-((hh - %s) / %s)" % (h0, hs))
    w.let("rhod", "%s * exp(ud)" % rh)
    vr = [w.let("vr0", "fma(%s, %s, fma(-%s, %s, %s))" % (om[2], r[1], om[1], r[2], v[0])),
          w.let("vr1", "fma(%s, %s, fma(-%s, %s, %s))" % (om[0], r[2], om[2], r[0], v[1])),
          w.let("vr2", "fma(%s, %s, fma(-%s, %s, %s))" % (om[1], r[0], om[0], r[1], v[2]))]
    w.let("vn", "sqrt(vr0 * vr0 + vr1 * vr1 + vr2 * vr2)")
    w.let("kd", "-((bc * rhod) * vn)")
    return [w.let("dr%s" % a, "kd * %s" % vr[i]) for i, a in enumerate("xyz")]


def head(system, fmt, comment, state, params, lanes):
    out = ["; cft-debris DEBRIS-I (MIT licence), written by tests/i_gen.py: %s" % comment,
           "; every data value is a param or a lane param, default 0, filled per run; no data is in this file",
           "system %s" % system, "format %s" % fmt, "round  rne", "state  %s" % ", ".join(state)]
    for i in range(0, len(params), 8):
        out.append("param  " + ", ".join("%s = 0" % p for p in params[i:i + 8]))
    for i in range(0, len(lanes), 8):
        out.append("lane param " + ", ".join("%s = 0" % p for p in lanes[i:i + 8]))
    return out


def parse_layout(layout, gr):
    where = {}
    for part in layout.split(";"):
        kind, _, names = part.partition(":")
        kind = kind.strip()
        if kind not in ("bank", "lane"):
            raise SystemExit("layout: %r is not bank or lane" % kind)
        for g in names.split(","):
            g = g.strip()
            if not g:
                continue
            if g not in gr or g in where:
                raise SystemExit("layout: group %r unknown or named twice" % g)
            where[g] = kind
    if set(where) != set(gr):
        raise SystemExit("layout: groups %s not placed" % sorted(set(gr) - set(where)))
    return where


def program(N, fmt, nb, dm, do, layout):
    gr = groups(N, nb, dm, do)
    where = parse_layout(layout, gr)
    params, lanes = [], []
    for g in ("grav", "bands", "scal", "de", "frame"):
        (params if where[g] == "bank" else lanes).extend(gr[g])
    lanes.append("bc")
    w = W()
    r, v = ["x", "y", "z"], ["vx", "vy", "vz"]
    M, O = w_frame(w, "t", dm, do)
    ac, rn = w_central(w, r)
    rb = w_apply(w, "rb", M, r, 0)
    f = w_grav(w, rb, N)
    hv = w_apply(w, "hv", M, f, 1)
    sun, moon = w_bodies(w, "t")
    asun = w_third(w, "s", "gms", r, sun)
    amoon = w_third(w, "m", "gmm", r, moon)
    dr = w_drag(w, r, v, O, rn, nb)
    eq = ["d/dt t  = 1", "d/dt x  = vx", "d/dt y  = vy", "d/dt z  = vz"]
    for i, a in enumerate("xyz"):
        eq.append("d/dt v%s = (((%s + %s) + %s) + %s) + %s" % (a, ac[i], hv[i], asun[i], amoon[i], dr[i]))
    eq.append("step   rk4, h = 15")
    comment = ("M1's force model without radiation pressure, degree %d, %d band%s, the frame as polynomials of "
               "degree %d (M) and %d (Omega); layout %s" % (N, nb, "s" if nb > 1 else "", dm, do, layout))
    text = head("debrisi%d" % N, fmt, comment, ["t", "x", "y", "z", "vx", "vy", "vz"], params, lanes) + w.lines + eq
    info = {"kind": "program", "degree": N, "bands": nb, "dm": dm, "do": do, "layout": layout,
            "state": ["t", "x", "y", "z", "vx", "vy", "vz"], "params": params, "lanes": lanes}
    return "\n".join(text) + "\n", info


PARTS = ("central", "grav", "tides", "bodies", "frame", "drag")


def part(which, N, fmt, nb, dm, do):
    """A map computing one part from given inputs (lane params), with the program's expressions; every data
    value of the part is a lane param, so that each lane may carry its own run's values."""
    gr = groups(N, nb, dm, do)
    w = W()
    if which == "central":
        ins, data = ["x", "y", "z"], ["gm"]
        out, _rn = w_central(w, ins)
    elif which == "grav":
        ins, data = ["rbx", "rby", "rbz"], gr["grav"]
        out = w_grav(w, ins, N)
    elif which == "tides":
        ins = ["x", "y", "z", "is0", "is1", "is2", "im0", "im1", "im2"]
        data = ["gms", "gmm"]
        out = w_third(w, "s", "gms", ins[:3], ins[3:6]) + w_third(w, "m", "gmm", ins[:3], ins[6:9])
    elif which == "bodies":
        ins, data = ["t"], gr["de"] + ["fem", "km"]
        sun, moon = w_bodies(w, "t")
        out = sun + moon
    elif which == "frame":
        ins, data = ["t"], gr["frame"]
        M, O = w_frame(w, "t", dm, do)
        out = M + O
    elif which == "drag":
        ins = ["x", "y", "z", "vx", "vy", "vz", "io0", "io1", "io2", "bc"]
        data = gr["bands"] + ["rearth"]
        w.let("r2", "x * x + y * y + z * z")
        rn = w.let("rn", "sqrt(r2)")
        out = w_drag(w, ins[:3], ins[3:6], ins[6:9], rn, nb)
    else:
        raise SystemExit("no part %r" % which)
    state = ["o%d" % i for i in range(len(out))]
    lanes = ins + data
    eq = ["next %s = %s" % (s, o) for s, o in zip(state, out)] + ["step   map"]
    comment = "part %s of the program (degree %d, %d bands, frame degrees %d and %d), a map" % (which, N, nb, dm, do)
    text = head("dpart_%s" % which, fmt, comment, state, [], lanes) + w.lines + eq
    info = {"kind": "part", "part": which, "degree": N, "bands": nb, "dm": dm, "do": do, "state": state,
            "inputs": ins, "params": [], "lanes": lanes, "outputs": out}
    return "\n".join(text) + "\n", info


def program20(fmt):
    """I6: degree 20 with the gravity tables as lane params (DEBRIS-D's Q2 route, M1's form); the rest of the model and
    its layout as the program's: 28 bands, the frame at degrees 7 and 3, the bands and scalars in the bank."""
    return program(20, fmt, 28, 7, 3, "bank:bands,scal;lane:grav,de,frame")


def write(path, text, info):
    with open(path, "w", newline="\n", encoding="ascii") as f:
        f.write(text)
    with open(path + ".json", "w", newline="\n", encoding="ascii") as f:
        json.dump(info, f, indent=1, sort_keys=True)
        f.write("\n")


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=("program", "part", "names", "program20"))
    ap.add_argument("--degree", type=int, default=7)
    ap.add_argument("--format", default="fp64")
    ap.add_argument("--bands", type=int, default=28)
    ap.add_argument("--dm", type=int, default=7)
    ap.add_argument("--do", type=int, default=3)
    ap.add_argument("--layout", default="bank:grav,bands,scal;lane:de,frame")
    ap.add_argument("--part")
    ap.add_argument("--out")
    a = ap.parse_args(argv)
    if a.bands not in (1, 28):
        raise SystemExit("--bands is 28 or 1")
    if a.mode == "names":
        json.dump(groups(a.degree, a.bands, a.dm, a.do), sys.stdout, indent=1)
        return 0
    if a.mode == "program":
        text, info = program(a.degree, a.format, a.bands, a.dm, a.do, a.layout)
    elif a.mode == "program20":
        text, info = program20(a.format)
    else:
        text, info = part(a.part, a.degree, a.format, a.bands, a.dm, a.do)
    write(a.out, text, info)
    print("%s: %d lines, %d params, %d lane params" % (a.out, text.count("\n"), len(info["params"]),
                                                       len(info["lanes"])))
    return 0


if __name__ == "__main__":
    sys.exit(main())
