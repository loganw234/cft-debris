"""i_vals.py - cft-debris DEBRIS-I: every value the program's driver fills, at each format, and the driver's files.

cft-debris, MIT licence (see LICENSE at the repository root). Written by DEBRIS-I, 2026-11-23. The readers follow
M1's own (src/gfc.c, src/de421.c, src/m1_ftab.c; cft-debris's own, MIT).

What is filled, and how each value is rounded (the brief's rule: correctly rounded at the run's format, from its decimal
string or exactly from a binary value; never through binary64, never through a short literal):
  - from decimal strings, each rounded once (the language's own rounding, cft_golden.lang.constants.round_once, of the
    string's exact value): EIGEN-6C4's GM, radius and C, S (the .gfc's own strings, D written as e, as src/gfc.c does);
    M1's constants and the 28 bands (src/m1_consts.h's strings, read from that file);
  - exactly from binary64 values (exact at binary64 and wider; rounded once at binary32): DE421's coefficients and
    EMRAT (the binary's own);
  - M1's derived tables, computed at the format by M1's own operations in M1's order (src/m1_physics.h, ph_setup):
    RE2 = RE * RE, KACC = GM / RE2, FEM = 1 / (1 + EMRAT), An, Bn, Dg, Sd, F1, FA, FB, FZ = sqrt(num / den) of exact
    integers (one division, one root), P1 = F1 C(n,0), PZ0 = FZ(n,0) C(n,0), hFA = FA / 2, hFB = FB / 2 - each
    operation one IEEE rounding by the golden softfloat (cft_golden.softfloat), the same rounding libcft's does;
  - exact integers: the sub-intervals' lengths and starts (seconds);
  - the frame's form: each run's polynomial coefficients, the exact least-squares fit (rational arithmetic) of M1's own
    frame_at (cft256, from tests/m1i.c frames) over the run's stage times, each coefficient rounded once.

THE FRAME'S FORM (fixed before any fit was seen): for a run of stage times T0, T0 + 7.5, ..., T1 (the run's own
block), s = t - tc with tc = (T0 + T1) / 2; each of M's 9 elements a polynomial of degree DM = 7 in s, and each of
Omega's 3 of degree DO = 3, the least-squares fit at every stage time of the block (the 2J + 1 points 7.5 s apart),
solved exactly; evaluated in the program by Horner, each step one fma.

usage (desktop):
  python -I -B i_vals.py selftest --fp256 <cft-fp256 python dir> --downloads DIR
"""
import hashlib
import json
import os
import struct
import subprocess
import sys
from fractions import Fraction

JD_EPOCH = Fraction(4922659, 2)          # 2461329.5, M1's jd_epoch (TDB)
H = Fraction(15)                          # the step
DM, DO = 7, 3                             # the frame's degrees (above)
SER = {"mo": 9, "su": 10, "em": 2}        # DE421's series: the Moon, the Sun, the EMB (src/m1.h)
FMTS = ("fp32", "fp64", "fp128", "fp256")
ESZ = {"fp32": 4, "fp64": 8, "fp128": 16, "fp256": 32}
M1KIND = {"fp32": "cft32", "fp64": "cft64", "fp128": "cft128", "fp256": "cft256"}

_G = {}


def golden(fp256_python):
    """cft_golden from the archive's python/ folder (the desktop only)."""
    if "sf" not in _G:
        sys.path.insert(0, fp256_python)
        from cft_golden import formats, softfloat
        from cft_golden.lang import constants
        _G["sf"], _G["C"], _G["F"] = softfloat, constants, {
            "fp32": formats.FP32, "fp64": formats.FP64, "fp128": formats.FP128, "fp256": formats.FP256}
    return _G["sf"], _G["C"], _G["F"]


# ------------------------------------------------------------------ readers (standard library)

def dec(s):
    """A decimal string's exact value (D written as e)."""
    return Fraction(s.replace("D", "e").replace("d", "e"))


def read_gfc(path, nmax):
    """As src/gfc.c: the header's GM and radius strings; each gfc line's C and S strings, the first of a duplicate."""
    gm = re = None
    C, S = {}, {}
    head = True
    with open(path, "rb") as f:
        for raw in f:
            w = raw.decode("ascii").split()
            if not w:
                continue
            if head:
                if w[0].startswith("end_of_head"):
                    head = False
                elif w[0] == "earth_gravity_constant":
                    gm = w[1]
                elif w[0] == "radius":
                    re = w[1]
                continue
            if w[0] != "gfc":
                raise SystemExit("the .gfc holds a key other than gfc: %s" % w[0])
            n, m = int(w[1]), int(w[2])
            if n <= nmax and (n, m) not in C:
                C[(n, m)], S[(n, m)] = w[3].replace("D", "e").replace("d", "e"), w[4].replace("D", "e").replace("d", "e")
    for n in range(0, nmax + 1):
        for m in range(0, n + 1):
            C.setdefault((n, m), "0")
            S.setdefault((n, m), "0")
    return gm, re, C, S


def read_consts(path):
    """src/m1_consts.h's strings: M1_CONSTS {name, dec, source} and the three band tables."""
    txt = open(path, "rb").read().decode("ascii")
    import re as _re
    consts = {}
    for m in _re.finditer(r'\{"([A-Z_0-9]+)",\s*"([^"]+)",', txt):
        consts[m.group(1)] = m.group(2)
    bands = {}
    for name in ("M1_ATM_H0", "M1_ATM_RHO0", "M1_ATM_HS"):
        i = txt.index(name + "[28] = {")
        j = txt.index("};", i)
        bands[name] = _re.findall(r'"([^"]+)"', txt[i:j])
        if len(bands[name]) != 28:
            raise SystemExit("%s: %d values" % (name, len(bands[name])))
    return consts, bands


class DE:
    """DE421's binary and header, as src/de421.c reads them."""

    def __init__(self, bin_path, hdr_path):
        hdr = open(hdr_path, "rb").read().decode("ascii").split()
        self.ncoeff = int(hdr[hdr.index("NCOEFF=") + 1])
        g = hdr.index("1050", hdr.index("GROUP"))
        ipt_h = [int(x) for x in hdr[g + 1:g + 40]]
        self.raw = open(bin_path, "rb").read()
        rec = self.ncoeff * 8
        if len(self.raw) % rec:
            raise SystemExit("DE421: not whole records")
        self.nrec = len(self.raw) // rec - 2
        self.ss = struct.unpack_from("<3d", self.raw, 2652)
        self.au_km, self.emrat = struct.unpack_from("<2d", self.raw, 2680)
        self.ipt = [list(struct.unpack_from("<3i", self.raw, 2696 + 12 * k)) for k in range(12)]
        self.ipt.append(list(struct.unpack_from("<3i", self.raw, 2844)))
        for k in range(13):
            if self.ipt[k] != [ipt_h[k], ipt_h[13 + k], ipt_h[26 + k]]:
                raise SystemExit("DE421: pointers differ from header.421 at %d" % k)
        self.ss0 = Fraction(self.ss[0])
        self.reclen = Fraction(self.ss[2]) * 86400

    def record(self, i):
        o = (i + 2) * self.ncoeff * 8
        return struct.unpack_from("<%dd" % self.ncoeff, self.raw, o)

    def locate(self, k, sec):
        """m1_de_locate at t = sec s from JD_EPOCH: (record, sub-interval, its start in s from JD_EPOCH), exactly."""
        nsub = self.ipt[k][2]
        sublen = self.reclen / nsub
        s = (JD_EPOCH - self.ss0) * 86400 + Fraction(sec)
        r = (s / self.reclen).__floor__()
        if r == self.nrec and s == self.nrec * self.reclen:
            r = self.nrec - 1
        if r < 0 or r >= self.nrec:
            raise SystemExit("t = %s is outside DE421" % sec)
        w = s - r * self.reclen
        j = (w / sublen).__floor__()
        if j == nsub:
            j = nsub - 1
        start = r * self.reclen + j * sublen - (JD_EPOCH - self.ss0) * 86400
        return r, j, start, sublen

    def coeffs(self, k, r, j):
        """[component][i] binary64 values of series k, record r, sub-interval j."""
        off, nc, _ns = self.ipt[k]
        rec = self.record(r)
        return [[rec[off - 1 + nc * (c + 3 * j) + i] for i in range(nc)] for c in range(3)]


def read_ftab(path):
    """The frame table's header (src/m1_ftab.c)."""
    raw = open(path, "rb").read()
    i = raw.index(b"END\n")
    hdr = {}
    for line in raw[:i].decode("ascii").splitlines():
        w = line.split(None, 1)
        if len(w) == 2:
            hdr[w[0]] = w[1]
    def num(s):  # src/m1_ftab.c reads these with strtod, which takes a C99 hex float as well as a decimal
        s = s.strip()
        return float.fromhex(s) if s.lower().lstrip("+-").startswith("0x") else float(s)
    return {"t0": num(hdr["t0"]), "h": num(hdr["h"]), "nk": int(hdr["nk"]), "jd_epoch": num(hdr["jd_epoch"]),
            "sha256": hashlib.sha256(raw).hexdigest()}


def read_seed(path):
    """The seed's rows as (idx, T_s, [x y z vx vy vz], bc, cram), binary64; the catalogue number is not kept."""
    out = []
    with open(path, "rb") as f:
        for raw in f:
            line = raw.decode("ascii")
            if line.startswith("#") or not line.strip():
                continue
            w = line.split()
            v = [float.fromhex(x) for x in w[3:12]]
            out.append((int(w[0]), v[0], v[1:7], v[7], v[8]))
    for k, row in enumerate(out):
        if row[0] != k:
            raise SystemExit("seed row %d has index %d" % (k, row[0]))
    return out


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


# ------------------------------------------------------------------ the values at a format

class Vals:
    """Every static value of the program at one format, as encodings (ints), M1's way."""

    def __init__(self, fp256_python, fmt, downloads, consts_h, N):
        sf, C, F = golden(fp256_python)
        self.sf, self.C, self.fm, self.fmt, self.N = sf, C, F[fmt], fmt, N
        self.R = sf.RND_RNE
        gm, re, Cs, Ss = read_gfc(os.path.join(downloads, "EIGEN6-C4.gfc", "EIGEN6-C4.gfc"), max(N, 2))
        consts, bands = read_consts(consts_h)
        self.consts, self.bands_s = consts, bands
        self.gfc_strings = (gm, re)
        self.de = DE(os.path.join(downloads, "lnxp1900p2053.421", "lnxp1900p2053.421"),
                     os.path.join(downloads, "header.421", "header.421"))
        v = {}
        self.v = v
        d = self.d
        GM, RE = d(gm), d(re)
        v["gm"], v["re"] = GM, RE
        v["re2"] = self.mul(RE, RE)
        v["kacc"] = self.div(GM, v["re2"])
        v["gms"], v["gmm"] = d(consts["GM_SUN"]), d(consts["GM_MOON"])
        v["rearth"], v["km"] = d(consts["R_EARTH"]), d(consts["KM"])
        one = d("1")
        em = self.b64(self.de.emrat)
        v["fem"] = self.div(one, self.add(one, em))
        for b in range(28):
            v["bh%d" % b] = d(bands["M1_ATM_H0"][b])
            v["br%d" % b] = d(bands["M1_ATM_RHO0"][b])
            v["bs%d" % b] = d(bands["M1_ATM_HS"][b])
        self.Cs, self.Ss = Cs, Ss
        self.v.update(self.grav(Cs, Ss))

    # ---- the arithmetic, one IEEE rounding each (the golden softfloat)
    def d(self, s):
        return self.C.round_once(self.fm, self.R, dec(s))[0]

    def q(self, x):
        return self.C.round_once(self.fm, self.R, Fraction(x))[0]

    def b64(self, x):
        return self.C.round_once(self.fm, self.R, Fraction(x))[0]

    def i64(self, n):
        bits, fl = self.C.round_once(self.fm, self.R, Fraction(n))
        if fl:
            raise SystemExit("integer %d is not exact at %s" % (n, self.fmt))
        return bits

    def mul(self, a, b):
        return self.sf.mul(self.fm, a, b, self.R)[0]

    def div(self, a, b):
        return self.sf.div(self.fm, a, b, self.R)[0]

    def add(self, a, b):
        return self.sf.add(self.fm, a, b, self.R)[0]

    def sqrt(self, a):
        return self.sf.sqrt(self.fm, a, self.R)[0]

    def sqrt_ratio(self, num, den):
        return self.sqrt(self.div(self.i64(num), self.i64(den)))

    def value(self, bits):
        return self.C.value_of(self.fm, bits)

    def grav(self, Cs, Ss, conv=None):
        """M1's ph_setup tables to degree N, each in M1's order of operations; conv converts a coefficient's string
        (default: rounded once from its decimal value)."""
        conv = conv or self.d
        v, N = {}, self.N
        L = N + 1
        half = self.d("0.5")
        for m in range(1, L + 1):
            v["dg%d" % m] = self.sqrt_ratio(3, 1) if m == 1 else self.sqrt_ratio(2 * m + 1, 2 * m)
        for m in range(0, L):
            v["sd%d" % m] = self.sqrt_ratio(2 * m + 3, 1)
        for m in range(0, L + 1):
            for n in range(m + 2, L + 1):
                v["an%d_%d" % (n, m)] = self.sqrt_ratio((2 * n - 1) * (2 * n + 1), (n - m) * (n + m))
                v["bn%d_%d" % (n, m)] = self.sqrt_ratio((2 * n + 1) * (n + m - 1) * (n - m - 1),
                                                        (2 * n - 3) * (n + m) * (n - m))
        for n in range(2, N + 1):
            c0 = conv(Cs[(n, 0)])
            f1 = self.sqrt_ratio((2 * n + 1) * (n + 1) * (n + 2), 2 * (2 * n + 3))
            fz0 = self.sqrt_ratio((2 * n + 1) * (n + 1) * (n + 1), 2 * n + 3)
            v["p1_%d" % n] = self.mul(f1, c0)
            v["pz_%d" % n] = self.mul(fz0, c0)
            for m in range(1, n + 1):
                v["c%d_%d" % (n, m)] = conv(Cs[(n, m)])
                v["s%d_%d" % (n, m)] = conv(Ss[(n, m)])
                fa = self.sqrt_ratio((2 * n + 1) * (n + m + 1) * (n + m + 2), 2 * n + 3)
                fb = self.sqrt_ratio((2 if m == 1 else 1) * (2 * n + 1) * (n - m + 1) * (n - m + 2), 2 * n + 3)
                fz = self.sqrt_ratio((2 * n + 1) * (n + m + 1) * (n - m + 1), 2 * n + 3)
                v["ha%d_%d" % (n, m)] = self.mul(fa, half)
                v["hb%d_%d" % (n, m)] = self.mul(fb, half)
                v["fz%d_%d" % (n, m)] = fz
        return v

    # ---- a run's blocks
    def de_block(self, t_start):
        """DE421's values for the run starting at t_start: the sub-interval M1 takes at t_start (m1_de_locate)."""
        out, where = {}, {}
        for k, ser in SER.items():
            r, j, start, sublen = self.de.locate(ser, t_start)
            cs = self.de.coeffs(ser, r, j)
            for c in range(3):
                for i, x in enumerate(cs[c]):
                    out["%s%d_%d" % (k, c, i)] = self.b64(x)
            out["l" + k] = self.i64(int(sublen))
            out["t" + k] = self.i64(int(start))
            where[k] = (r, j, start, start + sublen)
        return out, where

    def frame_block(self, fit):
        """The frame's values from an exact fit (frame_fit's result)."""
        out = {"tc": self.q(fit["tc"])}
        for e in range(9):
            for k in range(DM + 1):
                out["fm%d_%d" % (e, k)] = self.q(fit["m"][e][k])
        for e in range(3):
            for k in range(DO + 1):
                out["fo%d_%d" % (e, k)] = self.q(fit["o"][e][k])
        return out


# ------------------------------------------------------------------ the frame's fit (exact)

def fit_poly(ts, fs, tc, deg):
    """The exact least-squares polynomial of degree deg in s = t - tc through (ts, fs): coefficients a_k of s^k
    (Fractions). ts are multiples of 7.5 s; the normal equations are formed in v = (t - tc)/3.75, an integer."""
    vs = [int((Fraction(t) - tc) / Fraction(15, 4)) for t in ts]
    for t, vv in zip(ts, vs):
        if Fraction(t) - tc != vv * Fraction(15, 4):
            raise SystemExit("a stage time off the 3.75 s grid")
    n = deg + 1
    pw = [[vv ** k for vv in vs] for k in range(2 * n - 1)]
    A = [[Fraction(sum(pw[i + j])) for j in range(n)] for i in range(n)]
    b = [sum((Fraction(f) * p for f, p in zip(fs, pw[i])), Fraction(0)) for i in range(n)]
    # Gauss-Jordan, exact
    M = [A[i] + [b[i]] for i in range(n)]
    for c in range(n):
        p = next(r for r in range(c, n) if M[r][c] != 0)
        M[c], M[p] = M[p], M[c]
        piv = M[c][c]
        M[c] = [x / piv for x in M[c]]
        for r in range(n):
            if r != c and M[r][c] != 0:
                f = M[r][c]
                M[r] = [x - f * y for x, y in zip(M[r], M[c])]
    cv = [M[i][n] for i in range(n)]
    return [cv[k] / Fraction(15, 4) ** k for k in range(n)]


def frame_fit(T0, T1, frames):
    """The run's frame form: frames maps each stage time (Fraction) to M1's 12 values (Fractions)."""
    J = int((T1 - T0) / Fraction(15, 2))
    ts = [T0 + Fraction(15, 2) * j for j in range(J + 1)]
    tc = (T0 + T1) / 2
    fit = {"T0": T0, "T1": T1, "tc": tc, "m": [], "o": []}
    for e in range(12):
        fs = [frames[t][e] for t in ts]
        a = fit_poly(ts, fs, tc, DM if e < 9 else DO)
        (fit["m"] if e < 9 else fit["o"]).append(a)
    return fit


def poly_eval(a, s):
    """The fit's exact value at s (no rounding)."""
    r = Fraction(0)
    for c in reversed(a):
        r = r * s + c
    return r


def read_frames(path, esz=32):
    """m1i frames' output at cft256: {t (Fraction): [12 Fractions]}, decoded as binary256."""
    out = {}
    for raw in open(path, "rb"):
        line = raw.decode("ascii")
        if line.startswith("#"):
            continue
        w = line.split()
        t = Fraction(float.fromhex(w[0]))
        out[t] = [b256_value(int(x, 16)) for x in w[1:13]]
    return out


def b256_value(bits):
    """The exact value of a binary256 encoding (finite)."""
    sign = bits >> 255
    e = (bits >> 236) & ((1 << 19) - 1)
    m = bits & ((1 << 236) - 1)
    if e == (1 << 19) - 1:
        raise SystemExit("not finite")
    if e == 0:
        v = Fraction(m, 1 << (262142 + 236))
    else:
        v = Fraction((1 << 236) | m) * Fraction(2) ** (e - 262143 - 236)
    return -v if sign else v


# ------------------------------------------------------------------ the driver's files

def manifest_slots(manifest_path):
    """The image's names: bank slot of each param, scratch slot of each state component and lane param."""
    m = json.load(open(manifest_path, "rb"))
    bank = {b["name"]: b["slot"] for b in m["bank"] if b["kind"] == "param"}
    scr = {e["name"]: e["slot"] for e in m["scratch"]["layout"]}
    nscr = m["scratch"]["in"]
    nstate = sum(1 for e in m["scratch"]["layout"] if e["kind"] == "state")
    return m, bank, scr, nscr, nstate


def bank_bytes(base_bank, esz, bank_slots, values):
    """The run's whole bank: cftc's .bank with every param replaced by its run value."""
    b = bytearray(base_bank)
    n = len(b) // esz
    for name, slot in bank_slots.items():
        if name not in values:
            raise SystemExit("no value for param %s" % name)
        if slot >= n:
            raise SystemExit("slot %d past the bank" % slot)
        b[slot * esz:(slot + 1) * esz] = values[name].to_bytes(esz, "little")
    return bytes(b)


def write_runs(path, esz, nconst, nscr, nstate, shared_slots, runs):
    """runs: [(nseg, t_slot or None, t_enc, bank_bytes, [shared values in shared_slots' order])]."""
    out = bytearray(b"DBIR")
    out += struct.pack("<7I", 1, esz, nconst, nscr, nstate, len(runs), len(shared_slots))
    out += struct.pack("<%dI" % len(shared_slots), *shared_slots)
    for nseg, tslot, tenc, bank, sh in runs:
        if len(bank) != nconst * esz or len(sh) != len(shared_slots):
            raise SystemExit("a run's bank or shared values are the wrong size")
        out += struct.pack("<2I", nseg, 0xffffffff if tslot is None else tslot)
        out += tenc.to_bytes(esz, "little") + bank
        for x in sh:
            out += x.to_bytes(esz, "little")
    with open(path, "wb") as f:
        f.write(out)


def write_init(path, esz, lanes):
    """lanes: [[n_scratch encodings]]."""
    with open(path, "wb") as f:
        for ln in lanes:
            for x in ln:
                f.write(x.to_bytes(esz, "little"))


def read_segs(path, n, nstate, esz):
    """i_run's segment file: [(run, seg, [[state encodings] a lane], [lane bytes])]."""
    raw = open(path, "rb").read()
    rec = 8 + n * nstate * esz + n
    if len(raw) % rec:
        raise SystemExit("%s: not whole segment records" % path)
    out = []
    for o in range(0, len(raw), rec):
        r, s = struct.unpack_from("<2I", raw, o)
        st = []
        p = o + 8
        for _l in range(n):
            st.append([int.from_bytes(raw[p + i * esz:p + (i + 1) * esz], "little") for i in range(nstate)])
            p += nstate * esz
        out.append((r, s, st, list(raw[p:p + n])))
    return out


def read_marks(path, nscr, nstate, esz):
    raw = open(path, "rb").read()
    rec = 12 + nscr * esz + nstate * esz
    if len(raw) % rec:
        raise SystemExit("%s: not whole mark records" % path)
    out = []
    for o in range(0, len(raw), rec):
        r, s, l = struct.unpack_from("<3I", raw, o)
        p = o + 12
        pre = [int.from_bytes(raw[p + i * esz:p + (i + 1) * esz], "little") for i in range(nscr)]
        p += nscr * esz
        post = [int.from_bytes(raw[p + i * esz:p + (i + 1) * esz], "little") for i in range(nstate)]
        out.append((r, s, l, pre, post))
    return out


if __name__ == "__main__":
    print(__doc__)
