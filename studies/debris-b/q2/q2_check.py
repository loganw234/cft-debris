#!/usr/bin/env python3
"""DEBRIS-B Q2, negative control 2: "a fast wrong answer is still wrong".

For each kernel, run `q2bench.exe check <kernel> <param>`, which prints its
inputs, the synthetic coefficients it used and its outputs as hex floats,
then evaluate the same quantities independently in mpmath (or numpy) and
ASSERT agreement to a stated tolerance. Any mismatch raises and the run
exits non-zero. A printed value does not count; only the assertion does.

The independent evaluations do not reuse the C code's method:
- gravity: the potential U = GM/r sum (R/r)^n P_nm(sin phi)(C cos m lam +
  S sin m lam) in spherical coordinates, with P_nm by the classical column
  recursion in mpmath at 60 digits (itself checked against mpmath.legenp,
  mpmath's hypergeometric Legendre function, with the Condon-Shortley phase
  removed), and the acceleration by central differences of U (h = 1e-25 km).
  The C kernel uses Cunningham's Cartesian V/W recursion and closed-form
  acceleration sums.
- Chebyshev: T_k(tau) = cos(k arccos tau) in mpmath, not Clenshaw.
- frame: the series term by term in mpmath at 30 digits; the rotation built
  from explicit numpy rotation matrices.
- radiation pressure: the shadow fraction from a numerical quadrature of the
  overlap of the two apparent discs (mpmath.quad), not the closed-form lens.

  python -I -B q2_check.py [kernel param] ...   (default: all)
"""
import os
import subprocess
import sys

import mpmath as mp
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
EXE = os.path.join(HERE, "q2bench.exe")
ENV = dict(os.environ)
ENV["PATH"] = r"C:\msys64\mingw64\bin;" + ENV.get("PATH", "")


def run_check(kernel, param):
    p = subprocess.run([EXE, "check", kernel, str(param)], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                       text=True, env=ENV)
    if p.returncode != 0:
        raise SystemExit("check run failed: %s" % p.stderr)
    return p.stdout.splitlines()


def hx(s):
    return float.fromhex(s)


def rel(a, b):
    """|a - b| / |b| for vectors (mpmath or float)"""
    num = mp.sqrt(sum((mp.mpf(x) - mp.mpf(y)) ** 2 for x, y in zip(a, b)))
    den = mp.sqrt(sum(mp.mpf(y) ** 2 for y in b))
    return num / den


RESULTS = []


def record(name, value, tol, what):
    ok = value <= tol
    RESULTS.append((name, float(value), tol, ok, what))
    print("%-34s %-40s %.3e  (tolerance %.1e)  %s" % (name, what, float(value), tol, "ok" if ok else "FAIL"))
    assert ok, "%s: %s = %.3e exceeds %.1e" % (name, what, float(value), tol)


# ------------------------------------------------------------------ gravity
def legendre_table(N, t):
    """unnormalised P_nm(t), no Condon-Shortley phase, by the column recursion"""
    c = mp.sqrt(1 - t * t)
    P = {(0, 0): mp.mpf(1)}
    for m in range(0, N + 1):
        if m > 0:
            P[(m, m)] = (2 * m - 1) * c * P[(m - 1, m - 1)]
        if m + 1 <= N:
            P[(m + 1, m)] = (2 * m + 1) * t * P[(m, m)]
        for n in range(m + 2, N + 1):
            P[(n, m)] = ((2 * n - 1) * t * P[(n - 1, m)] - (n + m - 1) * P[(n - 2, m)]) / (n - m)
    return P


def potential(x, y, z, GM, R, N, C, S, ranges):
    """U over each (nlo, nhi) of ranges, at Cartesian (x, y, z)"""
    r = mp.sqrt(x * x + y * y + z * z)
    t = z / r
    lam = mp.atan2(y, x)
    P = legendre_table(N, t)
    cm = [mp.cos(m * lam) for m in range(N + 1)]
    sm = [mp.sin(m * lam) for m in range(N + 1)]
    q = R / r
    out = []
    for nlo, nhi in ranges:
        tot = mp.mpf(0)
        qn = q ** nlo
        for n in range(nlo, nhi + 1):
            s = mp.mpf(0)
            for m in range(0, n + 1):
                s += P[(n, m)] * (C[(n, m)] * cm[m] + S[(n, m)] * sm[m])
            tot += qn * s
            qn *= q
        out.append(GM / r * tot)
    return out


def check_grav(N, quad=False):
    kernel = "gravq" if quad else "grav"
    lines = run_check(kernel, N)
    mp.mp.dps = 60
    C, S = {}, {}
    pts = []
    for ln in lines:
        tk = ln.split()
        if not tk or tk[0].startswith("#"):
            continue
        if tk[0] == "GM":
            GM, R = mp.mpf(hx(tk[1])), mp.mpf(hx(tk[3]))
        elif tk[0] == "CS":
            n, m = int(tk[1]), int(tk[2])
            C[(n, m)] = mp.mpf(hx(tk[3]))
            S[(n, m)] = mp.mpf(hx(tk[4]))
        elif tk[0] == "POS":
            pts.append({"pos": [mp.mpf(hx(v)) for v in tk[1:4]]})
        elif tk[0] in ("FULL", "PERT", "BAND"):
            pts[-1][tk[0]] = [mp.mpf(hx(v)) for v in tk[1:4]]
        elif tk[0] in ("FULLQ", "PERTQ", "BANDQ"):
            pts[-1][tk[0][:-1]] = [mp.mpf(v) for v in tk[1:4]]
        elif tk[0] == "BANDLO":
            pts[-1]["bandlo"] = int(tk[1])
    # the column recursion against mpmath's own Legendre function
    t0 = mp.mpf("0.3141592653589793238462643383")
    P = legendre_table(N, t0)
    worst = mp.mpf(0)
    for (n, m) in [(2, 0), (2, 2), (N, 0), (N, N // 2), (N, N), (N - 1, 1), (N // 2 + 1, 3)]:
        ref = (-1) ** m * mp.legenp(n, m, t0, type=2)
        worst = max(worst, abs(P[(n, m)] - ref) / abs(ref))
    record("%s N=%d" % (kernel, N), worst, 1e-45, "P_nm recursion vs mpmath.legenp, rel")
    h = mp.mpf("1e-25")
    tolp, tolb, tolf = (1e-28, 1e-27, 1e-31) if quad else (1e-12, 1e-11, 1e-14)
    wp = wb = wf = mp.mpf(0)
    for pt in pts:
        x, y, z = pt["pos"]
        lo = pt["bandlo"]
        ranges = [(2, N), (lo, N)]
        g = [[None, None, None] for _ in ranges]
        for ax in range(3):
            d = [mp.mpf(0)] * 3
            d[ax] = h
            up = potential(x + d[0], y + d[1], z + d[2], GM, R, N, C, S, ranges)
            dn = potential(x - d[0], y - d[1], z - d[2], GM, R, N, C, S, ranges)
            for k in range(len(ranges)):
                g[k][ax] = (up[k] - dn[k]) / (2 * h)
        r3 = mp.sqrt(x * x + y * y + z * z) ** 3
        central = [-GM * x / r3, -GM * y / r3, -GM * z / r3]
        full = [central[i] + g[0][i] for i in range(3)]
        wp = max(wp, rel(pt["PERT"], g[0]))
        wb = max(wb, rel(pt["BAND"], g[1]))
        wf = max(wf, rel(pt["FULL"], full))
    record("%s N=%d" % (kernel, N), wp, tolp, "degrees 2..N vs mpmath, rel, worst of 4")
    record("%s N=%d" % (kernel, N), wb, tolb, "degrees N/2+1..N vs mpmath, rel")
    record("%s N=%d" % (kernel, N), wf, tolf, "full field vs mpmath, rel")


# ---------------------------------------------------------------- Chebyshev
def check_cheb():
    lines = run_check("cheb", 0)
    mp.mp.dps = 30
    bodies = {}
    cases = []
    for ln in lines:
        tk = ln.split()
        if not tk or tk[0].startswith("#"):
            continue
        if tk[0] == "BODY":
            bodies[tk[1]] = dict(ncoef=int(tk[2]), nsub=int(tk[3]), nrec=int(tk[4]), rec_len=hx(tk[5]))
        elif tk[0] == "EMRAT":
            emrat = mp.mpf(hx(tk[1]))
        elif tk[0] == "T":
            cases.append({"t": hx(tk[1]), "coef": {}})
        elif tk[0] == "COEF":
            cases[-1]["coef"][tk[1]] = (int(tk[2]), [hx(v) for v in tk[3:]])
        elif tk[0] in ("MOON", "SUN"):
            cases[-1][tk[0]] = [hx(v) for v in tk[1:4]]
    worst = 0.0
    for cs in cases:
        val = {}
        for name, b in bodies.items():
            sub_len = mp.mpf(b["rec_len"]) / b["nsub"]
            u = mp.mpf(cs["t"]) / sub_len
            idx = int(mp.floor(u))
            cidx, coef = cs["coef"][name]
            assert idx == cidx, (name, idx, cidx)
            tau = 2 * (u - idx) - 1
            th = mp.acos(tau)
            n = b["ncoef"]
            comp = []
            scale = []
            for j in range(3):
                cj = coef[j * n:(j + 1) * n]
                comp.append(sum(mp.mpf(cj[k]) * mp.cos(k * th) for k in range(n)))
                scale.append(sum(abs(c) for c in cj))
            val[name] = (comp, scale)
        moon, ms = val["moon"]
        f = 1 / (1 + emrat)
        sun = [val["sun"][0][j] - (val["emb"][0][j] - f * moon[j]) for j in range(3)]
        ss = [val["sun"][1][j] + val["emb"][1][j] + ms[j] for j in range(3)]
        for j in range(3):
            worst = max(worst, float(abs(mp.mpf(cs["MOON"][j]) - moon[j]) / ms[j]))
            worst = max(worst, float(abs(mp.mpf(cs["SUN"][j]) - sun[j]) / ss[j]))
    record("cheb", worst, 1e-14, "vs cos(k acos tau) in mpmath, / sum|c|")


# -------------------------------------------------------------------- frame
UAS = mp.pi / (180 * 3600 * 10 ** 6)


def rx(a):
    c, s = np.cos(a), np.sin(a)
    return np.array([[1, 0, 0], [0, c, s], [0, -s, c]])


def ry(a):
    c, s = np.cos(a), np.sin(a)
    return np.array([[c, 0, -s], [0, 1, 0], [s, 0, c]])


def rz(a):
    c, s = np.cos(a), np.sin(a)
    return np.array([[c, s, 0], [-s, c, 0], [0, 0, 1]])


def parse_frame(lines):
    d = {"FA": [], "TERMS": [], "EOP": [], "cases": []}
    for ln in lines:
        tk = ln.split()
        if not tk or tk[0].startswith("#"):
            continue
        k = tk[0]
        if k == "FA":
            d["FA"].append([hx(v) for v in tk[1:]])
        elif k in ("PX", "PY", "PS"):
            d[k] = [hx(v) for v in tk[1:]]
        elif k == "TERM":
            d["TERMS"].append((int(tk[1]), int(tk[2]), [int(v) for v in tk[3:17]], hx(tk[17]), hx(tk[18])))
        elif k == "EOP":
            d["EOP"].append([hx(v) for v in tk[1:]])
        elif k == "TEPOCH":
            d["TEPOCH"] = hx(tk[1])
        elif k == "NODEDT":
            d["NODEDT"] = hx(tk[1])
        elif k == "NTERMS":
            d["NTERMS"] = int(tk[1])
        elif k == "T":
            d["cases"].append({"t": hx(tk[1]), "NODE": [], "ROW": []})
        elif k == "NODEI0":
            d["cases"][-1]["i0"] = int(tk[1])
        elif k in ("NODE", "ROW"):
            d["cases"][-1][k].append([hx(v) for v in tk[1:]])
        elif k in ("RG", "XYSE", "RI", "XYSFULL"):
            d["cases"][-1][k] = [hx(v) for v in tk[1:]]
    return d


def matrix_from(t, X, Y, s, eop, tepoch):
    """W Rz(era) C2I, built in numpy from explicit rotations; returns R, era"""
    day = t / 86400.0
    dd = min(max(int(day), 0), len(eop) - 2)
    f = day - dd
    xp, yp, dut1 = [eop[dd][k] + f * (eop[dd + 1][k] - eop[dd][k]) for k in range(3)]
    tu = (tepoch - 2451545.0) + (t - 69.184 + dut1) / 86400.0
    era = 2 * np.pi * (np.fmod(tu, 1.0) + 0.7790572732640 + 0.00273781191135448 * tu)
    era = np.fmod(era, 2 * np.pi)
    tc = (tepoch - 2451545.0 + t / 86400.0) / 36525.0
    sp = -47e-6 * 4.848136811095359935899141e-6 * tc
    r2 = X * X + Y * Y
    e = np.arctan2(Y, X)
    d = np.arctan(np.sqrt(r2 / (1 - r2)))
    c2i = rz(-(e + s)) @ ry(d) @ rz(e)
    w = rx(-yp) @ ry(-xp) @ rz(sp)
    return w @ rz(era) @ c2i, era


def check_frame(full):
    kernel = "frame_full" if full else "frame_interp"
    param = 0 if full else 3600
    d = parse_frame(run_check(kernel, param))
    mp.mp.dps = 30
    if full:
        assert d["NTERMS"] == len(d["TERMS"]) == 2941, (d["NTERMS"], len(d["TERMS"]))
    wx = wm = wr = we = 0.0
    winterp = 0.0
    we_rel = 0.0
    for cs in d["cases"]:
        t = cs["t"]
        X, Y, s, era_c = cs["XYSE"]
        if full:
            # (1) exact arguments: the series as defined, in mpmath, held to a
            #     forward error bound for binary64 argument formation;
            # (2) the kernel's own binary64 arguments (formed in Python floats
            #     in the C code's order), then sin, cos and every sum in mpmath:
            #     this isolates the summation code, to 1e-14 of sum|amp|.
            tcd = (d["TEPOCH"] - 2451545.0 + t / 86400.0) / 36525.0
            fad = []
            for c in d["FA"]:
                fad.append(c[0] + tcd * (c[1] + tcd * (c[2] + tcd * (c[3] + tcd * c[4]))))
            tc = mp.mpf(tcd)
            fa = [sum(mp.mpf(c[k]) * tc ** k for k in range(5)) for c in d["FA"]]
            acc = [mp.mpf(0)] * 3
            accd = [mp.mpf(0)] * 3
            amp = [mp.mpf(0)] * 3
            bound = [mp.mpf(0)] * 3
            u = mp.mpf(2) ** -53
            for out, pw, mult, a_s, a_c in d["TERMS"]:
                arg = sum(mult[k] * fa[k] for k in range(14))
                argd = 0.0
                for k in range(14):
                    argd += mult[k] * fad[k]
                tp = tc ** pw
                acc[out] += (a_s * mp.sin(arg) + a_c * mp.cos(arg)) * tp
                accd[out] += (a_s * mp.sin(mp.mpf(argd)) + a_c * mp.cos(mp.mpf(argd))) * tp
                amp[out] += (abs(a_s) + abs(a_c)) * abs(tp)
                darg = sum(abs(mult[k]) * abs(fa[k]) for k in range(14)) * 6 * u + abs(arg) * 14 * u
                bound[out] += (abs(a_s) + abs(a_c)) * abs(tp) * darg
            res, resd = [], []
            for o, key in enumerate(("PX", "PY", "PS")):
                p = d[key]
                poly = sum(mp.mpf(p[k]) * tc ** k for k in range(6))
                res.append(poly + acc[o])
                resd.append(poly + accd[o])
            for rr, store in ((res, "exact"), (resd, "kernel-args")):
                Xm, Ym = rr[0] * UAS, rr[1] * UAS
                sm = rr[2] * UAS - Xm * Ym / 2
                for o, (got, ref) in enumerate(((X, Xm), (Y, Ym), (s, sm))):
                    err = abs(mp.mpf(got) - ref)
                    if store == "kernel-args":
                        wx = max(wx, float(err / (amp[o] * UAS)))
                    else:
                        cs.setdefault("bound_ratio", 0.0)
                        cs["bound_ratio"] = max(cs["bound_ratio"], float(err / ((bound[o] + amp[o] * 4 * u) * UAS)))
                        cs.setdefault("exact_rel", 0.0)
                        cs["exact_rel"] = max(cs["exact_rel"], float(err / (amp[o] * UAS)))
            winterp = max(winterp, cs["bound_ratio"])
            we_rel = max(we_rel, cs["exact_rel"])
        else:
            i0 = cs["i0"]
            u = mp.mpf(t) / mp.mpf(d["NODEDT"]) - i0
            ref = []
            for c in range(3):
                v = mp.mpf(0)
                for i in range(6):
                    w = mp.mpf(1)
                    for k in range(6):
                        if k != i:
                            w *= (u - k) / (i - k)
                    v += w * cs["NODE"][i][c]
                ref.append(v)
            scale = max(abs(mp.mpf(n[c])) for n in cs["NODE"] for c in range(3))
            for got, rv in zip((X, Y, s), ref):
                wx = max(wx, float(abs(mp.mpf(got) - rv) / scale))
            winterp = max(winterp, max(abs(a - b) for a, b in zip((X, Y, s), cs["XYSFULL"])))
        R, era = matrix_from(t, X, Y, s, d["EOP"], d["TEPOCH"])
        we = max(we, abs(era - era_c))
        Rc = np.array(cs["ROW"])
        wm = max(wm, float(np.max(np.abs(R - Rc))))
        ri = R @ np.array(cs["RG"])
        wr = max(wr, float(np.max(np.abs(ri - np.array(cs["RI"]))) / np.linalg.norm(cs["RG"])))
        orth = float(np.max(np.abs(Rc @ Rc.T - np.eye(3))))
        wm = max(wm, orth)
    if full:
        record(kernel, wx, 1e-14, "X,Y,s (kernel's args) vs mpmath, /sum|amp|")
        record(kernel, winterp, 1.0, "X,Y,s (exact args): error / bound")
        print("%-34s %-40s %.3e (reported, not asserted)" % (kernel, "X,Y,s (exact args), / sum|amp|", we_rel))
    else:
        record(kernel, wx, 1e-15, "6-point Lagrange vs mpmath, / max node")
        print("%-34s %-40s %.3e rad (reported, not asserted)" % (kernel, "interpolated minus full series",
                                                                  winterp))
    record(kernel, we, 1e-9, "ERA vs numpy, rad")
    record(kernel, wm, 1e-14, "matrix vs numpy rotations; orthogonality")
    record(kernel, wr, 1e-14, "rotated vector vs numpy, / |r|")


# --------------------------------------------------------------- atmosphere
def check_atmos():
    lines = run_check("atmos", 16)
    mp.mp.dps = 30
    bands = []
    rvs, accs = [], []
    for ln in lines:
        tk = ln.split()
        if not tk or tk[0].startswith("#"):
            continue
        if tk[0] == "B":
            B, RE, OM = hx(tk[1]), hx(tk[3]), hx(tk[5])
        elif tk[0] == "BAND":
            bands.append([mp.mpf(hx(v)) for v in tk[1:4]])
        elif tk[0] == "RV":
            rvs.append([mp.mpf(hx(v)) for v in tk[1:7]])
        elif tk[0] == "ACC":
            accs.append([mp.mpf(hx(v)) for v in tk[1:4]])
    worst = mp.mpf(0)
    for rv, ac in zip(rvs, accs):
        r = mp.sqrt(rv[0] ** 2 + rv[1] ** 2 + rv[2] ** 2)
        h = r - mp.mpf(RE)
        i = max(k for k in range(len(bands)) if bands[k][0] <= h)
        rho = bands[i][1] * mp.exp(-(h - bands[i][0]) / bands[i][2])
        v = [rv[3] + OM * rv[1], rv[4] - OM * rv[0], rv[5]]
        vn = mp.sqrt(sum(c * c for c in v))
        k = -mp.mpf(500) * B * rho * vn
        worst = max(worst, rel(ac, [k * c for c in v]))
    record("atmos", worst, 1e-13, "drag vs mpmath, rel, worst of 16")


# ------------------------------------------------------ radiation pressure
def overlap_area(A, B, C):
    """area common to a disc of radius A at 0 and one of radius B at C, by
    quadrature of the chord: independent of the closed-form lens"""
    lo = max(-A, C - B)
    hi = min(A, C + B)
    if hi <= lo:
        return mp.mpf(0)

    def f(x):
        sa = A * A - x * x
        sb = B * B - (x - C) ** 2
        if sa <= 0 or sb <= 0:
            return mp.mpf(0)
        return 2 * min(mp.sqrt(sa), mp.sqrt(sb))
    pts = [lo]
    xs = (C * C + A * A - B * B) / (2 * C)
    if lo < xs < hi:
        pts.append(xs)
    pts.append(hi)
    return mp.quad(f, pts)


def check_srp(setn):
    lines = run_check("srp", setn)
    mp.mp.dps = 30
    cases = []
    for ln in lines:
        tk = ln.split()
        if not tk or tk[0].startswith("#"):
            continue
        if tk[0] == "RSUN":
            RS, RE, AU, PS, CR = (mp.mpf(hx(tk[i])) for i in (1, 3, 5, 7, 9))
        elif tk[0] == "SUNPOS":
            sun = [mp.mpf(hx(v)) for v in tk[1:4]]
        elif tk[0] == "R":
            cases.append({"r": [mp.mpf(hx(v)) for v in tk[1:4]]})
        elif tk[0] == "NU":
            cases[-1]["nu"] = mp.mpf(hx(tk[1]))
        elif tk[0] == "ACC":
            cases[-1]["acc"] = [mp.mpf(hx(v)) for v in tk[1:4]]
    wn = mp.mpf(0)
    wa = mp.mpf(0)
    wform = mp.mpf(0)
    wrel, nu_at_wrel = mp.mpf(0), None
    kinds = {"sunlit": 0, "umbra": 0, "penumbra": 0, "annular": 0}
    for cs in cases:
        r = cs["r"]
        dv = [r[i] - sun[i] for i in range(3)]
        rn = mp.sqrt(sum(c * c for c in r))
        dn = mp.sqrt(sum(c * c for c in dv))
        A = mp.asin(RS / dn)
        B = mp.asin(RE / rn)
        C = mp.acos(sum(r[i] * dv[i] for i in range(3)) / (rn * dn))
        nu = 1 - overlap_area(A, B, C) / (mp.pi * A * A)
        # classified by geometry (the quadrature's nu is not exactly 0 or 1)
        if C >= A + B:
            kinds["sunlit"] += 1
        elif C <= B - A:
            kinds["umbra"] += 1
        elif C <= A - B:
            kinds["annular"] += 1
        else:
            kinds["penumbra"] += 1
            # the kernel's closed-form lens, evaluated in mpmath: if it agrees
            # with the quadrature, the formula is right and any binary64
            # disagreement is the formula's roundoff, not a coding error
            x = (C * C + A * A - B * B) / (2 * C)
            y = mp.sqrt(A * A - x * x)
            lens = A * A * mp.acos(x / A) + B * B * mp.acos((C - x) / B) - C * y
            wform = max(wform, abs((1 - lens / (mp.pi * A * A)) - nu))
        wn = max(wn, abs(cs["nu"] - nu))
        k1 = PS * CR * (AU / dn) ** 2 / dn / 1000
        ref = [nu * k1 * c for c in dv]
        full_sun = k1 * dn
        err = mp.sqrt(sum((cs["acc"][i] - ref[i]) ** 2 for i in range(3)))
        wa = max(wa, err / full_sun)
        if nu > 0 and err / (nu * full_sun) > wrel:
            wrel, nu_at_wrel = err / (nu * full_sun), nu
    tag = "srp set %d %s" % (setn, ",".join("%s %d" % kv for kv in kinds.items() if kv[1]))
    if kinds["penumbra"]:
        record(tag, wform, 1e-20, "closed-form lens in mpmath vs quadrature")
    record(tag, wn, 1e-8, "shadow fraction vs quadrature, abs")
    record(tag, wa, 1e-8, "acceleration error / unshadowed force")
    print("%-34s %-40s %.3e at nu = %.3g (reported, not asserted)" % (tag, "acceleration, rel to itself",
                                                                      float(wrel), float(nu_at_wrel or 0)))


def main():
    todo = sys.argv[1:]
    jobs = [("grav", 8), ("grav", 20), ("grav", 36), ("grav", 70), ("gravq", 8), ("gravq", 20),
            ("cheb", 0), ("frame_full", 0), ("frame_interp", 3600), ("atmos", 16), ("srp", 0), ("srp", 1)]
    if todo:
        jobs = [(todo[i], int(todo[i + 1])) for i in range(0, len(todo), 2)]
    for k, p in jobs:
        if k in ("grav", "gravq"):
            check_grav(p, quad=(k == "gravq"))
        elif k == "cheb":
            check_cheb()
        elif k.startswith("frame"):
            check_frame(k == "frame_full")
        elif k == "atmos":
            check_atmos()
        elif k == "srp":
            check_srp(p)
    print("ALL %d ASSERTIONS PASSED" % len(RESULTS))
    return 0


if __name__ == "__main__":
    sys.exit(main())
