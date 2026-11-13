#!/usr/bin/env python3
"""DEBRIS-C, M1b: the Sun and Moon (layer 4). A small DE421 reader of my own,
and Orekit's JPL reader (positions written by m1b_orekit.js), held to JPL's
testpo.421; then third-body accelerations on Lasser et al.'s CRF orbit.

  python -I -B m1b_check.py

THE READER (custom, written here from the JPL binary layout): header.421
gives NCOEFF and the coefficient pointers (GROUP 1050); the binary's first
record gives the coverage, AU and EMRAT, and its pointers must equal
header.421's (asserted). A position is a Chebyshev series in the normalised
time of its sub-interval, summed from the highest coefficient down; the
velocity is the derivative series times 2/(sub-interval length). Earth =
EMB - Moon/(1+EMRAT); the Moon is stored geocentric; (10,3) and (3,10) use it
directly. Units of testpo.421: AU and AU/day (AU from the binary), radians and
radians/day for nutations (14) and librations (15).

CRITERIA (stated before the run, asserted):
1. testpo, custom reader: every point inside the binary's coverage
   (JED 2414992.5 to 2469808.5; points outside are skipped and counted),
   |computed - testpo| < TOL_TESTPO = 1e-13 in the file's units.
   Basis: testpo.421 prints 17 significant digits, about binary64's
   resolution; a correct binary64 reader summing the same series in another
   order is expected within a few ulps of the coordinate (ulp of 50 AU is
   7.1e-15 AU), so 1e-13 leaves at least 14 ulps for the largest
   coordinates. (JPL's own testeph is BELIEVED to use the same 1e-13; its
   source is a .f file, outside the HTML-only rule, so that is not READ.)
2. testpo, Orekit: the same tolerance, for the points whose target and
   centre are bodies 1..13 (Orekit exposes no nutations or librations).
3. NEGATIVE CONTROL: the custom reader with the Chebyshev time argument
   shifted by one sub-interval (the series of the next sub-interval at the
   same normalised time) must FAIL criterion 1 (at least one point beyond
   TOL_TESTPO; the count is reported).
4. Third bodies on Lasser et al.'s CRF orbit (00orbit_icrf.txt, ICRF m),
   direct tides as point masses, a = GM (d/|d|^3 - s/|s|^3), s the
   geocentric body, d = s - r; GM values GROOPS's, from the README;
   ephemeris time TDB = TT + 0.001657 sin g + 0.000014 sin 2g s
   (g = 357.53 + 0.98560028 (JD - 2451545) deg), TT = GPS + 51.184 s.
   The TT-or-TDB choice moves the Moon's term by about 2e-16 m/s^2 on this
   day (COMPUTED: TDB-TT = 4.9e-5 s, times ~1 km/s, over 3.8e5 km, times
   1.2e-6 m/s^2), far below every tolerance here.
   - Sun and Moon: TOL = 1e-11 m/s^2 on max |delta a| over the day (the
     COST-G threshold, READ via WebFetch, Lasser et al. 2020).
   - Planets (Mercury, Venus, Mars, Jupiter and Saturn barycentres, summed):
     their whole signal is about 4e-12 m/s^2, below 1e-11, so 1e-11 could
     not fail. TOL_PL = 1e-16 m/s^2, 2.5e-5 of the signal, above the
     COMPUTED bounds of the convention differences (TT vs TDB < 1e-20).
   - the same tolerances for custom vs Orekit (two of ours).
5. CONTROLS for 4, each with its expected effect COMPUTED from my own model
   first and asserted to be at least 10 x the tolerance, then asserted to be
   REPORTED by the comparison with Lasser et al.:
   - the Moon's time argument shifted by +600 s;
   - Saturn left out of the planets.
"""
import hashlib
import math
import struct
import sys

D = "C:/Users/logan/source/repos/cft-debris-downloads/"
BIN = D + "lnxp1900p2053.421/lnxp1900p2053.421"
HDR = D + "header.421/header.421"
TESTPO = D + "testpo.421/testpo.421"
ORB = D + "00orbit_icrf.txt/00orbit_icrf.txt"
LSUN = D + "03directTideSun_icrf.txt/03directTideSun_icrf.txt"
LMOON = D + "03directTideMoon_icrf.txt/03directTideMoon_icrf.txt"
LPL = D + "03directTidePlanets_icrf.txt/03directTidePlanets_icrf.txt"
OUT = "C:/Users/logan/source/repos/cft-debris/studies/debris-c/m1b/out/"
TOL_TESTPO = 1e-13
TOL = 1e-11
TOL_PL = 1e-16
GM_SUN = 1.32712442076e20
GM_MOON = 0.49028010560e13
GM_PL = {1: GM_SUN / 6023600.0, 2: GM_SUN / 408523.71, 4: GM_SUN / 3098708.0, 5: GM_SUN / 1047.3486,
         6: GM_SUN / 3497.898}


class DE421:
    def __init__(self):
        tok = open(HDR).read().split()
        self.ncoeff = int(tok[tok.index("NCOEFF=") + 1])
        g = [i for i in range(len(tok) - 1) if tok[i] == "GROUP" and tok[i + 1] == "1050"][0]
        v = [int(x) for x in tok[g + 2:g + 2 + 39]]
        self.ipt = [(v[k], v[13 + k], v[26 + k]) for k in range(13)]  # 12 series + librations
        self.raw = open(BIN, "rb").read()
        self.rec = 8 * self.ncoeff
        assert len(self.raw) % self.rec == 0
        self.nrec = len(self.raw) // self.rec - 2
        self.ss = struct.unpack_from("<3d", self.raw, 2652)
        self.au, self.emrat = struct.unpack_from("<2d", self.raw, 2680)
        ib = struct.unpack_from("<36i", self.raw, 2696)
        lb = struct.unpack_from("<3i", self.raw, 2844)
        assert [tuple(ib[3 * k:3 * k + 3]) for k in range(12)] + [tuple(lb)] == self.ipt, "binary pointers != header.421"
        assert abs(self.nrec * self.ss[2] - (self.ss[1] - self.ss[0])) < 1e-9
        self.cache = {}

    def coeffs(self, i):
        c = self.cache.get(i)
        if c is None:
            c = struct.unpack_from("<%dd" % self.ncoeff, self.raw, (i + 2) * self.rec)
            self.cache[i] = c
        return c

    def series(self, k, jd_a, jd_b=0.0, shift=0):
        """series k (0..11 bodies/nutations, 12 librations) at JD = jd_a + jd_b:
        (values, rates per day)"""
        off, nc, ns = self.ipt[k]
        ncomp = 2 if k == 11 else 3
        t = (jd_a - self.ss[0]) + jd_b
        i = int(t // self.ss[2])
        if i == self.nrec:
            i -= 1
        assert 0 <= i < self.nrec, ("outside coverage", jd_a + jd_b)
        tin = (jd_a - self.ss[0] - i * self.ss[2]) + jd_b
        dt = self.ss[2] / ns
        j = int(tin // dt)
        if j == ns:
            j -= 1
        x = 2.0 * (tin - j * dt) / dt - 1.0
        c = self.coeffs(i)
        assert c[0] <= jd_a + jd_b <= c[1] + 1e-9, (c[0], c[1], jd_a + jd_b)
        j += shift
        while j >= ns:  # the control: the next sub-interval, across a record boundary if need be
            j -= ns
            i += 1
            c = self.coeffs(i)
        T = [1.0, x]
        Td = [0.0, 1.0]
        for n in range(2, nc):
            T.append(2.0 * x * T[n - 1] - T[n - 2])
            Td.append(2.0 * T[n - 1] + 2.0 * x * Td[n - 1] - Td[n - 2])
        pos, vel = [], []
        for comp in range(ncomp):
            b = off - 1 + nc * (comp + ncomp * j)
            p = 0.0
            v = 0.0
            for n in range(nc - 1, -1, -1):
                p += c[b + n] * T[n]
                v += c[b + n] * Td[n]
            pos.append(p)
            vel.append(v * 2.0 / dt)
        return pos, vel

    def ssb(self, body, jd_a, jd_b=0.0, shift=0):
        """body 1..13 relative to the SSB, km and km/day"""
        if body == 12:
            return [0.0] * 3, [0.0] * 3
        idx = {1: 0, 2: 1, 4: 3, 5: 4, 6: 5, 7: 6, 8: 7, 9: 8, 11: 10, 13: 2}
        if body in idx:
            return self.series(idx[body], jd_a, jd_b, shift)
        emb, embv = self.series(2, jd_a, jd_b, shift)
        mo, mov = self.series(9, jd_a, jd_b, shift)
        f = 1.0 / (1.0 + self.emrat)
        e = [emb[q] - f * mo[q] for q in range(3)]
        ev = [embv[q] - f * mov[q] for q in range(3)]
        if body == 3:
            return e, ev
        if body == 10:
            return [e[q] + mo[q] for q in range(3)], [ev[q] + mov[q] for q in range(3)]
        raise ValueError(body)

    def pleph(self, jed, t, c, shift=0):
        """testpo semantics: six numbers in AU and AU/day, or radians and radians/day"""
        if t == 14:
            p, v = self.series(11, jed, 0.0, shift)
            return p + v
        if t == 15:
            p, v = self.series(12, jed, 0.0, shift)
            return p + v
        if (t, c) in ((10, 3), (3, 10)):
            p, v = self.series(9, jed, 0.0, shift)
            s = 1.0 if t == 10 else -1.0
            p = [s * x for x in p]
            v = [s * x for x in v]
        else:
            pa, va = self.ssb(t, jed, 0.0, shift)
            pb, vb = self.ssb(c, jed, 0.0, shift)
            p = [pa[q] - pb[q] for q in range(3)]
            v = [va[q] - vb[q] for q in range(3)]
        return [x / self.au for x in p] + [x / self.au for x in v]


def read_testpo():
    rows = []
    lines = open(TESTPO).read().splitlines()
    started = False
    for i, ln in enumerate(lines):
        s = ln.strip()
        if not started:
            started = s == "EOT"
            continue
        t = s.split()
        if len(t) < 7:
            continue
        rows.append((i, float(t[2]), int(t[3]), int(t[4]), int(t[5]), float(t[6])))
    return rows


def testpo_check(de, rows, shift=0, label=""):
    lo, hi = de.ss[0], de.ss[1]
    worst = {"pos": 0.0, "vel": 0.0, "nut": 0.0, "lib": 0.0}
    nfail = nused = nskip = 0
    for (i, jed, t, c, x, val) in rows:
        if not (lo <= jed <= hi):
            nskip += 1
            continue
        got = de.pleph(jed, t, c, shift)[x - 1]
        d = abs(got - val)
        kind = "nut" if t == 14 else "lib" if t == 15 else ("pos" if x <= 3 else "vel")
        worst[kind] = max(worst[kind], d)
        nused += 1
        if d >= TOL_TESTPO:
            nfail += 1
    print("%-44s points %d, skipped (outside coverage) %d, failures (|d| >= %.0e) %d; max |d|: pos %.2e AU, "
          "vel %.2e AU/d, nut %.2e rad, lib %.2e rad" % (label, nused, nskip, TOL_TESTPO, nfail,
                                                        worst["pos"], worst["vel"], worst["nut"], worst["lib"]))
    return nfail, nused


def orekit_testpo_check(de, rows):
    bylin = {r[0]: r for r in rows}
    aum = de.au * 1000.0
    worst = {"pos": 0.0, "vel": 0.0}
    nfail = n = 0
    for ln in open(OUT + "orekit_testpo.txt"):
        t = ln.split()
        i = int(t[0])
        (_, jed, tg, ct, x, val) = bylin[i]
        p = [float.fromhex(z) / aum for z in t[1:4]]
        v = [float.fromhex(z) * 86400.0 / aum for z in t[4:7]]
        got = (p + v)[x - 1]
        d = abs(got - val)
        kind = "pos" if x <= 3 else "vel"
        worst[kind] = max(worst[kind], d)
        n += 1
        if d >= TOL_TESTPO:
            nfail += 1
    print("%-44s points %d, failures (|d| >= %.0e) %d; max |d|: pos %.2e AU, vel %.2e AU/d"
          % ("testpo, Orekit's JPL reader", n, TOL_TESTPO, nfail, worst["pos"], worst["vel"]))
    return nfail, n


def read_rows(path, ncol):
    rows = []
    for ln in open(path):
        t = ln.split()
        if len(t) == ncol and not ln.startswith("#"):
            try:
                rows.append([float(z) for z in t])
            except ValueError:
                pass
    return rows


def tide(gm, s, r):
    d = [s[q] - r[q] for q in range(3)]
    nd = math.sqrt(sum(x * x for x in d))
    ns = math.sqrt(sum(x * x for x in s))
    return [gm * (d[q] / nd ** 3 - s[q] / ns ** 3) for q in range(3)]


def tdb_minus_tt(jd):
    g = math.radians(357.53 + 0.98560028 * (jd - 2451545.0))
    return 0.001657 * math.sin(g) + 0.000014 * math.sin(2.0 * g)


def custom_bodies(de, k, moon_shift_s=0.0):
    """geocentric positions (m) at Lasser epoch k: Sun, Moon, planets 1, 2, 4, 5, 6"""
    ja = 2454650.5  # MJD 54650.0 GPS
    jb = (30.0 * k + 51.184) / 86400.0
    jb += tdb_minus_tt(ja + jb) / 86400.0
    e, _ = de.ssb(3, ja, jb)
    out = {}
    s, _ = de.ssb(11, ja, jb)
    out[11] = [1000.0 * (s[q] - e[q]) for q in range(3)]
    mo, _ = de.series(9, ja, jb + moon_shift_s / 86400.0)
    out[10] = [1000.0 * x for x in mo]
    for b in (1, 2, 4, 5, 6):
        p, _ = de.ssb(b, ja, jb)
        out[b] = [1000.0 * (p[q] - e[q]) for q in range(3)]
    return out


def maxdiff(A, B):
    m = 0.0
    s2 = 0.0
    for a, b in zip(A, B):
        n = math.sqrt(sum((a[q] - b[q]) ** 2 for q in range(3)))
        m = max(m, n)
        s2 += n * n
    return m, math.sqrt(s2 / len(A))


def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def main():
    ok = True
    print("# M1b criteria: TOL_TESTPO %.0e (file units), TOL %.0e m/s^2 (Sun, Moon), TOL_PL %.0e m/s^2 (planets)"
          % (TOL_TESTPO, TOL, TOL_PL))
    for p in (BIN, HDR, TESTPO, ORB, LSUN, LMOON, LPL, OUT + "orekit_testpo.txt", OUT + "orekit_bodies.txt"):
        print("# input %s sha256 %s" % (p, sha(p)))
    de = DE421()
    print("# DE421 binary: NCOEFF %d, coverage JED %.1f to %.1f, %d data records of %.0f days, AU %.10f km, EMRAT %.13f"
          % (de.ncoeff, de.ss[0], de.ss[1], de.nrec, de.ss[2], de.au, de.emrat))
    rows = read_testpo()
    nf, nu = testpo_check(de, rows, 0, "testpo, custom reader")
    p = nf == 0 and nu > 0
    ok &= p
    print("%s criterion 1 (custom reader vs testpo.421)" % ("PASS" if p else "FAIL"))
    nf2, nu2 = orekit_testpo_check(de, rows)
    p = nf2 == 0 and nu2 > 0
    ok &= p
    print("%s criterion 2 (Orekit's reader vs testpo.421)" % ("PASS" if p else "FAIL"))
    nf3, nu3 = testpo_check(de, rows, 1, "CONTROL: time shifted by one sub-interval")
    p = nf3 > 0
    ok &= p
    print("%s criterion 3 (control): the check %s the planted shift (%d of %d points fail)"
          % ("PASS" if p else "FAIL", "reports" if p else "does NOT report", nf3, nu3))

    # third bodies on Lasser et al.'s CRF orbit
    orb = read_rows(ORB, 10)
    ls = read_rows(LSUN, 4)
    lm = read_rows(LMOON, 4)
    lp = read_rows(LPL, 4)
    assert len(orb) == len(ls) == len(lm) == len(lp) == 2880
    ore = []
    for ln in open(OUT + "orekit_bodies.txt"):
        t = ln.split()
        v = [float.fromhex(z) for z in t[1:]]
        ore.append({11: v[0:3], 10: v[3:6], 1: v[6:9], 2: v[9:12], 4: v[12:15], 5: v[15:18], 6: v[18:21]})
    assert len(ore) == 2880
    cs, cm, cp, os_, om, op, cm_plant, cp_plant = [], [], [], [], [], [], [], []
    for k in range(2880):
        assert abs(orb[k][0] - (54650.0 + 30.0 * k / 86400.0)) < 1e-9
        r = orb[k][1:4]
        b = custom_bodies(de, k)
        bp = custom_bodies(de, k, moon_shift_s=600.0)
        cs.append(tide(GM_SUN, b[11], r))
        cm.append(tide(GM_MOON, b[10], r))
        cm_plant.append(tide(GM_MOON, bp[10], r))
        pl = [0.0, 0.0, 0.0]
        pl5 = [0.0, 0.0, 0.0]
        for q in (1, 2, 4, 5, 6):
            a = tide(GM_PL[q], b[q], r)
            pl = [pl[z] + a[z] for z in range(3)]
            if q != 6:
                pl5 = [pl5[z] + a[z] for z in range(3)]
        cp.append(pl)
        cp_plant.append(pl5)
        o = ore[k]
        os_.append(tide(GM_SUN, o[11], r))
        om.append(tide(GM_MOON, o[10], r))
        opl = [0.0, 0.0, 0.0]
        for q in (1, 2, 4, 5, 6):
            a = tide(GM_PL[q], o[q], r)
            opl = [opl[z] + a[z] for z in range(3)]
        op.append(opl)
    L_s = [x[1:4] for x in ls]
    L_m = [x[1:4] for x in lm]
    L_p = [x[1:4] for x in lp]
    sig = lambda A: max(math.sqrt(sum(z * z for z in a)) for a in A)  # noqa: E731
    print("# signal: max |a| Sun %.3e, Moon %.3e, planets %.3e m/s^2 (Lasser et al.)" % (sig(L_s), sig(L_m), sig(L_p)))
    checks = [("custom Sun vs Lasser", cs, L_s, TOL), ("custom Moon vs Lasser", cm, L_m, TOL),
              ("custom planets vs Lasser", cp, L_p, TOL_PL), ("Orekit-position Sun vs Lasser", os_, L_s, TOL),
              ("Orekit-position Moon vs Lasser", om, L_m, TOL), ("Orekit-position planets vs Lasser", op, L_p, TOL_PL),
              ("custom vs Orekit, Sun", cs, os_, TOL), ("custom vs Orekit, Moon", cm, om, TOL),
              ("custom vs Orekit, planets", cp, op, TOL_PL)]
    for name, A, B, tol in checks:
        m, rms = maxdiff(A, B)
        p = m < tol
        ok &= p
        print("%s %-36s max |da| %.3e, RMS %.3e m/s^2 (tolerance %.0e)" % ("PASS" if p else "FAIL", name, m, rms, tol))
    # controls: expected effect computed from my own model first, then the comparison must report it
    for name, P, A, L, tol in (("Moon time argument +600 s", cm_plant, cm, L_m, TOL),
                               ("Saturn left out of the planets", cp_plant, cp, L_p, TOL_PL)):
        e, _ = maxdiff(P, A)
        p1 = e >= 10 * tol
        m, _ = maxdiff(P, L)
        p2 = m > tol
        ok &= p1 and p2
        print("%s CONTROL %s: expected effect (own model) %.3e = %.0f x tolerance (needs >= 10); vs Lasser max %.3e: %s"
              % ("PASS" if (p1 and p2) else "FAIL", name, e, e / tol, m, "reported" if p2 else "NOT reported"))
    print("# M1b %s" % ("PASS" if ok else "FAIL"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
