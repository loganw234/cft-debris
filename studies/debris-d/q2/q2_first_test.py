"""q2_first_test.py - DEBRIS-D, Q2's first test (cft-debris, MIT).

For each system (j2-rk4, j2dragrot-rk4) and format (fp64, fp128, fp256):
  1. compile with cftc from the archive of cft-fp256 at 0aa997a3, --steps 24
     (one segment = 24 rk4 steps of 60 s), into DEBRIS-D's scratch;
  2. run the image on libcft's software executor (tools/seqrun.c), 8 lanes,
     4 segments chained (96 steps), keeping each segment's states and lane
     bytes;
  3. hold it to
     (a) the reference interpreter lang.run, bit for bit, segment by segment
         and lane by lane, states and the lane byte's five IEEE flags
         (the marked-lane rule: a marked lane is replayed by the definition
         and its guess only counted);
     (b) an independent reference: mpmath at 120 digits, the same rk4 and
         steps from the same exact initial states, with the params as the
         format rounds them, within the tolerance stated below;
     (c) a negative control: lang.run of the source with mu planted one ulp
         (of the format) above its rounded value must FAIL (a).
  4. record each image's SHA-256, its manifest's counts and the command that
     rebuilds it, and the lanes the routines marked.
Sizes are the first test's: degree 2, 96 steps, 4 segments, 8 lanes.

usage: python -I -B q2_first_test.py <system> <fmt> [<fmt> ...]
"""
import json
import os
import subprocess
import sys
import time
from fractions import Fraction

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tools"))
import dd  # noqa: E402

sys.path.insert(0, dd.FP256 + "/python")
from cft_golden import lang  # noqa: E402
from cft_golden.lang import constants as C  # noqa: E402

import mpmath  # noqa: E402
from mpmath import mp, mpf  # noqa: E402

SYSDIR = os.path.join(dd.ROOT, "systems")
IMGDIR = dd.SCRATCH + "/images/q2"
WORK = dd.SCRATCH + "/work/q2"
SEQRUN = dd.SCRATCH + "/build/seqrun.exe"
STEPS_SEG, SEGMENTS, LANES = 24, 4, 8
P = {"fp64": 53, "fp128": 113, "fp256": 237}
WIDTH = {"fp64": 8, "fp128": 16, "fp256": 32}
ARCHIVE_SHA = "e01003cc0b984864b065ce3395f56fa189451fcb0cd98cce5b11b3c17a9c29b8"
TOL_K = 64           # (b): |image - mpmath| <= TOL_K * N * 2^-p * scale
SCALE_POS, SCALE_VEL = 7.0e6, 8.0e3
MP_DPS = 120


def initial_states():
    """8 lanes: near-circular LEO orbits at 380-420 km, Keplerian elements
    turned into Cartesian states with mpmath, each rounded to binary64. The
    same binary64 values are every format's initial state (exact in each)."""
    mp.dps = 50
    mu = mpf(398600441800000)
    incl = [5, 28.5, 45, 51.6, 63.4, 82, 97.8, 135]
    out = []
    for k in range(LANES):
        a = mpf(6378137) + mpf(380000) + mpf(5000) * k
        e = mpf("0.0005") * k
        i = mpmath.radians(incl[k])
        raan = mpmath.radians(30 * k)
        argp = mpmath.radians(15 * k)
        nu = mpmath.radians(40 * k)
        p = a * (1 - e * e)
        rr = p / (1 + e * mpmath.cos(nu))
        xo, yo = rr * mpmath.cos(nu), rr * mpmath.sin(nu)
        vxo = -mpmath.sqrt(mu / p) * mpmath.sin(nu)
        vyo = mpmath.sqrt(mu / p) * (e + mpmath.cos(nu))
        cO, sO = mpmath.cos(raan), mpmath.sin(raan)
        cw, sw = mpmath.cos(argp), mpmath.sin(argp)
        ci, si = mpmath.cos(i), mpmath.sin(i)
        R = [[cO * cw - sO * sw * ci, -cO * sw - sO * cw * ci],
             [sO * cw + cO * sw * ci, -sO * sw + cO * cw * ci],
             [sw * si, cw * si]]
        pos = [R[j][0] * xo + R[j][1] * yo for j in range(3)]
        vel = [R[j][0] * vxo + R[j][1] * vyo for j in range(3)]
        out.append([float(v) for v in pos + vel])
    return out


def lane_bc(k):
    return Fraction(5, 1000) + Fraction(2, 1000) * k


def enc(fmt, rnd, value):
    bits, _ = C.round_once(fmt, rnd, Fraction(value))
    return bits


def val(fmt, bits):
    return C.value_of(fmt, bits)


def pack(encs, width):
    return b"".join(int(e).to_bytes(width, "little") for e in encs)


def unpack(blob, width):
    return [int.from_bytes(blob[i:i + width], "little") for i in range(0, len(blob), width)]


def compile_image(system, fmt, log):
    os.makedirs(IMGDIR, exist_ok=True)
    stem = "%s-%s" % (system, fmt)
    src = os.path.join(SYSDIR, system + ".cftl")
    cmd = [dd.PY, "-I", "-B", dd.FP256 + "/python/cftc", src, "--steps", str(STEPS_SEG),
           "--format", fmt, "--out", IMGDIR, "--stem", stem]
    t0 = time.perf_counter()
    r = subprocess.run(cmd, capture_output=True, text=True)
    log.w("compile %s: exit %d in %.2f s; %s" % (stem, r.returncode, time.perf_counter() - t0,
                                                 (r.stderr.strip() or "no stderr").replace("\n", " | ")))
    if r.returncode != 0:
        raise SystemExit("compile refused")
    man = json.load(open(os.path.join(IMGDIR, stem + ".manifest.json")))
    rec = {"image": stem, "cftp_sha256": dd.sha256_file(os.path.join(IMGDIR, stem + ".cftp")),
           "bank_sha256": dd.sha256_file(os.path.join(IMGDIR, stem + ".bank")),
           "half_bank_sha256": dd.sha256_file(os.path.join(IMGDIR, stem + ".half.bank")),
           "manifest_sha256": dd.sha256_file(os.path.join(IMGDIR, stem + ".manifest.json")),
           "source_sha256": dd.sha256_file(src),
           "instructions": man["uses"]["instructions"], "per_step": man["per_step"],
           "registers": man["uses"]["registers"], "scratch_slots": man["uses"]["scratch_slots"],
           "scratch_declared": man["uses"]["scratch_declared"], "bank_slots": man["uses"]["bank_slots"],
           "features": man["uses"]["features"], "graph_by_op": man["lowering"]["graph_by_op"],
           "graph_step_nodes": man["lowering"]["graph_step_nodes"],
           "accepted_by": man["accepted_by"],
           "rebuild": "python -I -B <archive %s extracted>/python/cftc studies/debris-d/systems/%s.cftl "
                      "--steps %d --format %s --out <dir> --stem %s" % (ARCHIVE_SHA[:12], system, STEPS_SEG, fmt, stem)}
    log.w("image " + json.dumps(rec, sort_keys=True))
    return stem, man


def mp_reference(system, graph, states0, bcs, checkpoints):
    """rk4 at MP_DPS digits, with every param as the format rounded it."""
    mp.dps = MP_DPS
    fmt = graph.fmt
    pv = {name: mpf(val(fmt, bits).numerator) / mpf(val(fmt, bits).denominator)
          for name, _exact, bits, _flags in graph.param}
    h = mpf(60)

    def field(Y, bc):
        if system == "j2-rk4":
            x, y, z, vx, vy, vz = Y
            t = None
        else:
            t, x, y, z, vx, vy, vz = Y
        r2 = x * x + y * y + z * z
        r = mpmath.sqrt(r2)
        ir = 1 / r
        ir2 = ir * ir
        ir3 = ir2 * ir
        g = pv["mu"] * ir3
        zr2 = (z * ir) ** 2
        f = pv["kj2"] * ir2
        gxy = g * (f * (1 - 5 * zr2) + 1)
        gz = g * (f * (3 - 5 * zr2) + 1)
        ax, ay, az = -gxy * x, -gxy * y, -gz * z
        if system == "j2-rk4":
            return [vx, vy, vz, ax, ay, az]
        th = pv["w"] * t
        c, s = mpmath.cos(th), mpmath.sin(th)
        xb, yb = c * x + s * y, c * y - s * x
        wq = pv["c22"] * (xb * xb - yb * yb) + 2 * pv["s22"] * xb * yb
        q = 5 * wq * ir2
        g5 = pv["k22"] * ir3 * ir2
        axb = g5 * (2 * (pv["c22"] * xb + pv["s22"] * yb) - q * xb)
        ayb = g5 * (2 * (pv["s22"] * xb - pv["c22"] * yb) - q * yb)
        az2 = -g5 * q * z
        ax2, ay2 = c * axb - s * ayb, s * axb + c * ayb
        rho = pv["rho0"] * mpmath.exp(pv["a0"] - r * pv["ih"])
        vrx, vry = vx + pv["w"] * y, vy - pv["w"] * x
        vr = mpmath.sqrt(vrx * vrx + vry * vry + vz * vz)
        kd = bc * rho * vr
        return [mpf(1), vx, vy, vz, ax + ax2 - kd * vrx, ay + ay2 - kd * vry, az + az2 - kd * vz]

    res = {}
    for k, st in enumerate(states0):
        Y = [mpf(v.numerator) / mpf(v.denominator) for v in st]
        bc = mpf(bcs[k].numerator) / mpf(bcs[k].denominator) if bcs else None
        for n in range(1, checkpoints[-1] + 1):
            k1 = field(Y, bc)
            k2 = field([a + h / 2 * b for a, b in zip(Y, k1)], bc)
            k3 = field([a + h / 2 * b for a, b in zip(Y, k2)], bc)
            k4 = field([a + h * b for a, b in zip(Y, k3)], bc)
            Y = [a + h / 6 * (b + 2 * c2 + 2 * c3 + d) for a, b, c2, c3, d in zip(Y, k1, k2, k3, k4)]
            if n in checkpoints:
                res.setdefault(n, []).append(list(Y))
    return res


def main():
    system, fmts = sys.argv[1], sys.argv[2:]
    log = dd.Log(__file__, "q2_first_test_%s" % system)
    log.criteria(
        "(a) every lane's state after each of the 4 segments equals lang.run's, bit for bit, and each "
        "unmarked lane's byte is [7:5] clear with [4:0] equal to lang.run's flags for that lane and segment; "
        "a marked lane (bit 7) is replayed by lang.run and its guess counted, not required",
        "(b) |image - mpmath(%d digits)| <= %d * N * 2^-p * S per component, N the steps so far, "
        "S = %.1e m for positions and %.1e m/s for velocities; t must be exact (0)" % (MP_DPS, TOL_K, SCALE_POS, SCALE_VEL),
        "(c) control: lang.run of the source with mu one ulp (of the format) above its rounded value "
        "must differ from the image's states somewhere (so (a) can fail); identical = control FAILED",
        "(d) the planted source's mu encoding is the original's plus one (the plant is what it says)")
    os.makedirs(WORK, exist_ok=True)
    s64 = initial_states()
    src_text = open(os.path.join(SYSDIR, system + ".cftl"), "rb").read()
    for fmt in fmts:
        log.w("")
        log.w("== %s at %s ==" % (system, fmt))
        stem, man = compile_image(system, fmt, log)
        sysobj = lang.compile_text(src_text, system + ".cftl", fmt)
        g = sysobj.graph
        fmtobj, rnd = g.fmt, g.rnd
        width = WIDTH[fmt]
        has_t = (system != "j2-rk4")
        states0 = []
        for k in range(LANES):
            row = ([Fraction(0)] if has_t else []) + [Fraction(v) for v in s64[k]]
            states0.append(row)
        bcs = [val(fmtobj, enc(fmtobj, rnd, lane_bc(k))) for k in range(LANES)] if has_t else None
        enc0 = [[enc(fmtobj, rnd, v) for v in row] for row in states0]
        lp = [[enc(fmtobj, rnd, lane_bc(k))] for k in range(LANES)] if has_t else None
        n_state = g.n_state
        # --- the image on the software executor
        sin = b"".join(pack(enc0[k] + (lp[k] if lp else []), width) for k in range(LANES))
        sin_path = os.path.join(WORK, stem + ".in.bin")
        open(sin_path, "wb").write(sin)
        prefix = os.path.join(WORK, stem)
        t0 = time.perf_counter()
        r = subprocess.run([SEQRUN, os.path.join(IMGDIR, stem + ".cftp"), os.path.join(IMGDIR, stem + ".bank"),
                            sin_path, str(LANES), str(SEGMENTS), prefix], capture_output=True, text=True)
        log.w("seqrun exit %d in %.2f s" % (r.returncode, time.perf_counter() - t0))
        for ln in r.stdout.strip().splitlines():
            log.w("  " + ln)
        if r.returncode:
            log.w(r.stderr)
            raise SystemExit("seqrun failed")
        img = {}
        lanes = {}
        for s in range(1, SEGMENTS + 1):
            blob = open("%s.seg%d.bin" % (prefix, s), "rb").read()
            vals = unpack(blob, width)
            m = len(vals) // LANES
            img[s] = [vals[k * m:k * m + n_state] for k in range(LANES)]
            lanes[s] = list(open("%s.seg%d.lanes" % (prefix, s), "rb").read())
        # --- (a) lang.run, segment by segment, lane by lane
        t0 = time.perf_counter()
        a_ok = True
        marked = 0
        wrong_guesses = 0
        cur = [list(e) for e in enc0]
        for s in range(1, SEGMENTS + 1):
            nxt = []
            for k in range(LANES):
                rr = lang.run(g, [cur[k]], STEPS_SEG, lane_params=[lp[k]] if lp else None)
                ref_state, ref_flags = rr.states[0], rr.flags
                byte = lanes[s][k]
                if byte & 0x80:
                    marked += 1
                    if img[s][k] != ref_state:
                        wrong_guesses += 1
                    nxt.append(ref_state)
                    continue
                if img[s][k] != ref_state:
                    a_ok = False
                    log.w("  (a) lane %d segment %d: state differs from lang.run" % (k, s))
                fl = ref_flags if isinstance(ref_flags, int) else int(ref_flags)
                if (byte & 0xE0) or (byte & 0x1F) != (fl & 0x1F):
                    a_ok = False
                    log.w("  (a) lane %d segment %d: lane byte 0x%02x, lang.run flags 0x%02x" % (k, s, byte, fl))
                nxt.append(img[s][k])
            cur = nxt
        log.w("lang.run: %d segments x %d lanes in %.1f s; marked lanes %d (of %d lane-segments), wrong guesses %d"
              % (SEGMENTS, LANES, time.perf_counter() - t0, marked, SEGMENTS * LANES, wrong_guesses))
        log.check(a_ok, "%s %s (a) image equals lang.run bit for bit, states and lane flags, 4 segments x 8 lanes"
                  % (system, fmt))
        # --- (b) mpmath
        t0 = time.perf_counter()
        cps = [STEPS_SEG * s for s in range(1, SEGMENTS + 1)]
        ref = mp_reference(system, g, states0, bcs, cps)
        p = P[fmt]
        worst = {}
        b_ok = True
        for s in range(1, SEGMENTS + 1):
            N = STEPS_SEG * s
            for k in range(LANES):
                for j in range(n_state):
                    v = val(fmtobj, img[s][k][j])
                    d = abs(mpf(v.numerator) / mpf(v.denominator) - ref[N][k][j])
                    if has_t and j == 0:
                        if d != 0:
                            b_ok = False
                            log.w("  (b) t not exact: lane %d seg %d diff %s" % (k, s, mpmath.nstr(d, 5)))
                        continue
                    jj = j - (1 if has_t else 0)
                    S = SCALE_POS if jj < 3 else SCALE_VEL
                    tol = TOL_K * N * mpf(2) ** (-p) * S
                    kind = "pos" if jj < 3 else "vel"
                    rel = d / tol
                    if rel > worst.get((s, kind), (mpf(-1), 0))[0]:
                        worst[(s, kind)] = (rel, d)
                    if d > tol:
                        b_ok = False
        for (s, kind), (rel, d) in sorted(worst.items()):
            log.w("  (b) segment %d %s: largest |image - mpmath| %s (%s of the tolerance)"
                  % (s, kind, mpmath.nstr(d, 4), mpmath.nstr(rel, 3)))
        log.w("mpmath reference in %.1f s" % (time.perf_counter() - t0))
        log.check(b_ok, "%s %s (b) within %d*N*2^-%d*S of mpmath at %d digits" % (system, fmt, TOL_K, p, MP_DPS))
        # --- (c) negative control: mu one ulp up
        mu_bits = [b for name, _e, b, _f in g.param if name == "mu"][0]
        ulp = val(fmtobj, mu_bits + 1) - val(fmtobj, mu_bits)
        planted_val = val(fmtobj, mu_bits) + ulp
        line_old = b"param  mu = 398600441800000"
        line_new = ("param  mu = 398600441800000 + %d/%d" % ((planted_val - 398600441800000).numerator,
                                                             (planted_val - 398600441800000).denominator)).encode()
        if src_text.count(line_old) != 1:
            raise SystemExit("plant site not unique")
        planted = lang.compile_text(src_text.replace(line_old, line_new), system + "-planted.cftl", fmt).graph
        pbits = [b for name, _e, b, _f in planted.param if name == "mu"][0]
        log.check(pbits == mu_bits + 1, "%s %s (d) planted mu encoding = original + 1 (0x%x -> 0x%x)"
                  % (system, fmt, mu_bits, pbits))
        t0 = time.perf_counter()
        rr = lang.run(planted, enc0, STEPS_SEG * SEGMENTS, lane_params=lp, at=tuple(cps))
        ndiff = 0
        for s in range(1, SEGMENTS + 1):
            st_s = rr.at[STEPS_SEG * s][0]
            for k in range(LANES):
                ndiff += sum(1 for a, b in zip(st_s[k], img[s][k]) if a != b)
        log.w("planted run in %.1f s: %d of %d values differ from the image's" %
              (time.perf_counter() - t0, ndiff, SEGMENTS * LANES * n_state))
        log.check(ndiff > 0, "%s %s (c) control: the planted source fails (a)" % (system, fmt))
        # --- marks
        nev = LANES * STEPS_SEG * SEGMENTS * 4
        tm = sum(1 for s in lanes for b in lanes[s] if b & 0x80)
        log.w("marks: %d marked lane-segments; %d lane-evaluations (8 lanes x 96 steps x 4 stages)" % (tm, nev))
    rc = log.close()
    sys.exit(1 if rc else 0)


if __name__ == "__main__":
    main()
