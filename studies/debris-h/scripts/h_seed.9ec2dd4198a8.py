# h_seed.py - cft-debris M1 (DEBRIS-H), H-a: the seed - each object's state at the run's start T_s, from its own
# element set by DEBRIS-F's fit, carried to T_s at native64. Standard library only; on amd-arc-box and the desktop.
# cft-debris, MIT licence (see LICENSE at the repository root). Written by DEBRIS-H, 2026-11-18, before S_H0 existed.
# Its rules (RULES below) are fixed in this text before any of S_H0's values is read. It reuses DEBRIS-F's fit and
# predictions unchanged (tests/m1f.c fit and prop, through the orchestration of tests/f_fit.py, copied into h_lib.py)
# and DEBRIS-G's set key and perigee screen (tests/g_pop.py, copied into h_lib.py), all cft-debris's own, MIT.
#
#   fit:     python3 -I -B h_seed.py fit --seed 1|2 --gp DIR --tag TAG --ts T_s --table TABLE --m1f EXE --java JAVA
#                --jars DIR --orekit DIR --decoder f5_sgp4.js --leaps tai-utc.dat --out DIR --logs DIR
#                [--procs N] [--jprocs N] [--test-sample N] [--select CAT,CAT,...] [--no-catchup] [--test]
#                [--plant-obs CAT:K:DX] [--keep DIR] [--cpu TSV]
#   combine: python3 -I -B h_seed.py combine --fit1 FILE --fit2 FILE --out DIR --logs DIR [--keep DIR] [--cpu TSV]
#
# T_s is TDB seconds from JD 2461329.5 (a decimal or C99 hex float) or a TDB calendar label YYYY-MM-DDTHH:MM:SS.
# Per-object outputs (the fit tables, the seed files, the meta table) go to --out, which belongs in the ledger's
# debris-h\ and never in the repository; the log holds counts, hashes and aggregates, and names no object.
import argparse
import math
import os
import random
import sys
import time
from fractions import Fraction

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import h_lib as H  # noqa: E402

SCRIPT = os.path.abspath(__file__)
TEST_SEED = 0x7E57
PERIGEE_MIN = 200000.0
MAX_AGE = 30 * 86400.0
LEAD_MIN = 1200.0
MAXIT = 10

RULES = """
THE SEED, fixed before S_H0's values are read (DEBRIS-H's brief, H-a):
ROWS: the four groups' CSV files (stations, fengyun-1c-debris, iridium-33-debris, cosmos-2251-debris), each with the
  header's 17 columns in CelesTrak's order (asserted); ephemeris type 0 only, rows of another type excluded and counted.
ONE OBJECT PER ELEMENT SET, by DEBRIS-G's key (tests/g_pop.py): the epoch as whole microseconds and MEAN_MOTION,
  ECCENTRICITY, INCLINATION, RA_OF_ASC_NODE, ARG_OF_PERICENTER, MEAN_ANOMALY, BSTAR, MEAN_MOTION_DOT, MEAN_MOTION_DDOT as
  parsed values; the smallest catalogue number of each set is kept, the other rows counted as dropped.
THE SCREENS, in this order, each exclusion counted: perigee a(1 - e) - 6,378,137 m under 200 km, a from the mean motion
  with GM = 3.986004415e14 m^3/s^2 (DEBRIS-G's formula); the set's epoch more than 30 days before T_s (TDB); the fit's
  origin O after T_s (the set's epoch more than a day after T_s).
T_s: from the command line, a multiple of 600 s on M1's TDB axis, and (but with --test) at least 20 minutes after this
  run starts, by the clock of the machine, through the leap seconds of tai-utc.dat and USNO Circular 179's eq. (2.6).
THE FIT, DEBRIS-F's B4 unchanged in its rules: e0q = the epoch in TDB rounded to 2^-20 s; O = e0q - 86,400 s; 721
  pseudo-observations at O + 120 k (k = 0 to 720) from Orekit's SGP4 (tests/f5_sgp4.js, GCRF, through DEBRIS-F's Earth
  orientation file); tests/m1f.c fit at native64 with its iteration limit of 10; the start state the first
  pseudo-observation's, bc from 0.01 m^2/kg, cram fixed at 0.01 m^2/kg; an object Orekit refuses is excluded and counted.
  SEED 1: bc estimated where the perigee by tests/f_fit.py's formula (MU = 3.986004418e14) is under 1,000 km, held at
  0.01 m^2/kg above (fitbc = 1 or 0). SEED 2 (decision 4(b)): bc held at 0.01 m^2/kg for every object (fitbc = 0).
  A fit that stops on the iteration limit, or on a singular matrix, keeps its last iterate and is flagged.
FLAGS (an integer): 1 the fit stopped on the iteration limit; 2 it stopped on a singular matrix; 4 bc was estimated;
  8 the fitted bc is negative.
THE CATCH-UP: tests/m1f.c prop at native64 from O to T_s - whole steps of 15 s, then one short step landing on T_s.
  An object whose catch-up stops early (its m1f run fails), or whose state at T_s is not finite or lies 6,498.137 km
  or less from the centre (120 km), is left out; in combine, an object left out by either seed is left out of every
  track, and each is counted.
THE FILES: seed1.txt and seed2.txt, one line an object in ascending catalogue number, "idx cat flags T_s x y z vx vy vz
  bc cram", every real a C99 hex float (%a), the same objects and indices in both; seed_meta.tsv beside them.
"""


def parse_ts(s):
    if "T" in s and "-" in s:
        d, t = s.split("T")
        y, mo, dd = (int(x) for x in d.split("-"))
        hh, mi, ss = (int(x) for x in t.split(":"))
        return float((H.mjd_of(y, mo, dd) - H.MJD_E) * 86400 + hh * 3600 + mi * 60 + ss)
    return float.fromhex(s) if s.lower().startswith(("0x", "-0x")) else float(s)


def gp_path(d, g, tag):
    for p in (os.path.join(d, "gp-%s-%s.csv" % (g, tag)), os.path.join(d, "gp-%s-%s" % (g, tag), "gp-%s-%s.csv" % (g, tag))):
        if os.path.exists(p):
            return p
    raise SystemExit("no CSV for %s %s under %s" % (g, tag, d))


def select_objects(a, log):
    """the rows, the set key, the screens and the test selection; returns [(cat, row)] in catalogue order"""
    rows = []
    for g in H.GROUPS:
        p = gp_path(a.gp, g, a.tag)
        rg = H.read_gp(p, g)
        log.w("# %s: %d rows, sha256 %s" % (os.path.basename(p), len(rg), H.sha256(p)))
        rows += rg
    nt = sum(1 for r in rows if r["EPHEMERIS_TYPE"] != "0")
    rows0 = [r for r in rows if r["EPHEMERIS_TYPE"] == "0"]
    log.w("# rows read %d; excluded as ephemeris type not 0: %d" % (len(rows), nt))
    if a.select_any:
        # TEST ONLY (H6): the named objects, each with its own row (the last one read, as DEBRIS-F's rows_by_key keeps),
        # without the set rule or the screens: F6's pairs include objects that share an element set
        want = {int(x) for x in a.select_any.split(",")}
        byc = {}
        for r in rows0:
            if int(r["NORAD_CAT_ID"]) in want:
                byc[int(r["NORAD_CAT_ID"])] = r
        log.w("# TEST ONLY: --select-any names %d objects, %d found; no set rule, no screens" % (len(want), len(byc)))
        return sorted(byc.items())
    sets = {}
    for r in rows0:
        k = H.set_key(r)
        c = int(r["NORAD_CAT_ID"])
        if k not in sets or c < int(sets[k]["NORAD_CAT_ID"]):
            sets[k] = r
    log.w("# element sets %d; rows dropped as sharing a set with a smaller catalogue number (or repeated across groups): %d" % (len(sets), len(rows0) - len(sets)))
    log.check(len({r["NORAD_CAT_ID"] for r in sets.values()}) == len(sets), "one catalogue number per kept set")
    kept, n_peri, n_age, n_after = [], 0, 0, 0
    for r in sorted(sets.values(), key=lambda r: int(r["NORAD_CAT_ID"])):
        if H.perigee_g(r) < PERIGEE_MIN:
            n_peri += 1
            continue
        e0 = H.epoch_tdb(r)
        if Fraction(a.ts_val) - e0 > MAX_AGE:
            n_age += 1
            continue
        if H.quantize(e0) - 86400.0 > a.ts_val:
            n_after += 1
            continue
        kept.append((int(r["NORAD_CAT_ID"]), r))
    log.w("# excluded: perigee under 200 km %d; epoch more than 30 days before T_s %d; origin after T_s %d; kept %d" % (n_peri, n_age, n_after, len(kept)))
    if a.select:
        want = {int(x) for x in a.select.split(",")}
        sel = [(c, r) for c, r in kept if c in want]
        log.w("# TEST ONLY: --select names %d objects, %d of them kept by the rules above" % (len(want), len(sel)))
        kept = sel
    elif a.test_sample:
        cats = random.Random(TEST_SEED).sample(sorted(c for c, _ in kept), a.test_sample)
        cs = set(cats)
        kept = [(c, r) for c, r in kept if c in cs]
        log.w("# TEST ONLY: --test-sample %d by random.Random(0x%X).sample over the kept catalogue numbers in ascending order" % (a.test_sample, TEST_SEED))
    return kept


def chunks(seq, n):
    n = max(1, min(n, len(seq)))
    k, m = divmod(len(seq), n)
    out, i = [], 0
    for j in range(n):
        s = k + (1 if j < m else 0)
        out.append(seq[i:i + s])
        i += s
    return [c for c in out if c]


def mode_fit(a):
    cpu = H.CpuAccount("h_seed_fit%d" % a.seed, a.cpu)
    a.ts_val = parse_ts(a.ts)
    t_run = time.time()
    log = H.Log("h_seed_fit%d" % a.seed, a.logs, SCRIPT, RULES, extra=[a.decoder], keep_dir=a.keep)
    H.load_leaps(a.leaps)
    log.w("# seed %d; T_s %r s TDB = %s (%s); table %s sha256 %s; m1f sha256 %s; leaps sha256 %s" % (
        a.seed, a.ts_val, float.hex(a.ts_val), H.tdb_label(a.ts_val), os.path.basename(a.table), H.sha256(a.table), H.sha256(a.m1f), H.sha256(a.leaps)))
    for f in sorted(os.listdir(a.orekit)):
        log.w("# orekit data %s sha256 %s" % (f, H.sha256(os.path.join(a.orekit, f))))
    jars = sorted(os.path.join(a.jars, j) for j in os.listdir(a.jars) if j.endswith(".jar"))
    for j in jars:
        log.w("# jar %s sha256 %s" % (os.path.basename(j), H.sha256(j)))
    log.check(a.ts_val % 600.0 == 0.0, "T_s is a multiple of 600 s on M1's TDB axis (%r)" % a.ts_val)
    now_tdb = float(H.unix_to_tdb(t_run))
    lead = a.ts_val - now_tdb
    if a.test:
        log.w("# TEST ONLY: --test waives the 20-minute rule (T_s - now = %.0f s)" % lead)
    else:
        log.check(lead >= LEAD_MIN, "T_s is at least 20 minutes after this run started (%.0f s)" % lead)
    if log.fails:
        return log.close()
    kept = select_objects(a, log)
    if not log.check(len(kept) > 0, "objects to fit: %d" % len(kept)):
        return log.close()
    W = os.path.join(a.out, "work_fit%d_%d" % (a.seed, log.n))
    os.makedirs(W)
    e0q = {c: H.epoch_q(r) for c, r in kept}
    O = {c: e0q[c] - 86400.0 for c, _ in kept}
    for c, _ in kept:
        assert Fraction(O[c]) == Fraction(e0q[c]) - 86400
    # the pseudo-observations. The decoder's output depends, at the 1e-5 m level, on the instants the same JVM decoded
    # before (DEBRIS-H, MEASURED 2026-11-18; Orekit's frame caches are the BELIEVED cause), so the decode's chunks are a
    # recorded part of the input: the objects in catalogue order, cut into --jprocs contiguous chunks, one JVM each.
    # --decode-order (tests only) replays another run's sequence: those objects, in that order, in one JVM, of which
    # only the selected ones are fitted.
    dlist = kept
    if a.decode_order:
        allrows = {}
        for g in H.GROUPS:
            for r in H.read_gp(gp_path(a.gp, g, a.tag), g):
                if r["EPHEMERIS_TYPE"] == "0":
                    allrows[int(r["NORAD_CAT_ID"])] = r
        dlist = [(int(c), allrows[int(c)]) for c in a.decode_order.split(",")]
        for c, r in dlist:
            if c not in O:
                O[c] = H.epoch_q(r) - 86400.0
        log.check(a.jprocs == 1 and all(c in dict(dlist) for c, _ in kept), "TEST ONLY: --decode-order replays a sequence of %d objects in one JVM, holding the %d to fit" % (
            len(dlist), len(kept)))
    log.w("# the decode: %d objects in %d JVM run(s), in %s order" % (len(dlist), min(a.jprocs, len(dlist)), "the given" if a.decode_order else "catalogue"))
    parts = chunks(dlist, 1 if a.decode_order else a.jprocs)
    cmds = []
    for i, part in enumerate(parts):
        pin, pout = os.path.join(W, "pv_in.%02d.txt" % i), os.path.join(W, "pv.%02d.txt" % i)
        H.decode_input(pin, [(str(c), r, [O[c] + 120.0 * j for j in range(H.NOBS)]) for c, r in part])
        cmds.append((H.java_argv(a.java, jars, a.decoder, ["pv", a.orekit, pin, pout]), pout))
    codes = H.run_pool(cmds, a.jprocs, log)
    if not log.check(all(x == 0 for x in codes), "every decoder run exited 0 (%s)" % codes):
        return log.close()
    pv = {}
    for _, pout in cmds:
        pv.update(H.read_decoded(pout))
    refused = [c for c, _ in kept if pv.get(str(c)) is None]
    log.w("# Orekit refused %d objects (excluded)" % len(refused))
    fitset = [(c, r) for c, r in kept if pv.get(str(c)) is not None]
    log.check(all(len(pv[str(c)]) == H.NOBS for c, _ in fitset), "every decoded object has its 721 pseudo-observations")
    plant = None
    if a.plant_obs:
        pc, pk, pdx = a.plant_obs.split(":")
        plant = (int(pc), int(pk), float(pdx))
        log.w("# CONTROL C13 ONLY: pseudo-observation %d of the planted object moved by %r m in x" % (plant[1], plant[2]))
    # the fits
    fitbc = {c: (1 if (a.seed == 1 and H.perigee_alt_km_f(r) < 1000.0) else 0) for c, r in fitset}
    parts = chunks(fitset, a.procs)
    cmds = []
    for i, part in enumerate(parts):
        fin, fout = os.path.join(W, "fit_in.%02d.txt" % i), os.path.join(W, "fit.%02d.txt" % i)
        with open(fin, "w", newline="\n") as f:
            for c, r in part:
                s = pv[str(c)]
                f.write("OBJ %d %s %s %s %s %d %d 0\n" % (c, float.hex(O[c]), " ".join(float.hex(x) for x in s[0]), float.hex(H.BC0), float.hex(H.CRAM), fitbc[c], H.NOBS))
                for k in range(H.NOBS):
                    q = list(s[k][:3])
                    if plant and plant[0] == c and plant[1] == k:
                        q[0] += plant[2]
                    f.write("O %d %s\n" % (k, " ".join(float.hex(x) for x in q)))
        cmds.append(([a.m1f, "fit", a.table, fin, fout, "--maxit", str(MAXIT)], fout))
    codes = H.run_pool(cmds, a.procs, log)
    if not log.check(all(x == 0 for x in codes), "every fit run exited 0 (%s)" % codes):
        return log.close()
    fits, singular = {}, set()
    for _, fout in cmds:
        for ln in open(fout, encoding="ascii"):
            p = ln.split()
            if p and p[0] == "FIT":
                v = [float.fromhex(x) for x in p[4:6]] + [float.fromhex(x) for x in p[8:16]]
                fits[int(p[1])] = {"conv": int(p[2]), "iter": int(p[3]), "rms": v[0], "maxres": v[1], "fitbc": int(p[7]), "t0": v[2], "y": v[3:9], "bc": v[9]}
            elif p and p[0] == "ITER" and len(p) >= 4 and p[3] == "singular":
                singular.add(int(p[1]))
    log.check(set(fits) == {c for c, _ in fitset}, "every object fitted has a FIT line (%d of %d)" % (len(fits), len(fitset)))
    for c, _ in fitset:
        assert fits[c]["t0"] == O[c] and fits[c]["fitbc"] == fitbc[c]
    nconv = sum(1 for c in fits if fits[c]["conv"])
    nsing = sum(1 for c in fits if not fits[c]["conv"] and c in singular)
    nlim = sum(1 for c in fits if not fits[c]["conv"] and c not in singular)
    log.w("# fits: %d converged, %d stopped on the iteration limit, %d stopped on a singular matrix (flagged); bc estimated in %d" % (
        nconv, nlim, nsing, sum(fitbc.values())))
    if a.seed == 2:
        log.check(all(fits[c]["bc"] == H.BC0 for c in fits), "seed 2: every bc is exactly 0.01 m^2/kg")
    rms = sorted(fits[c]["rms"] for c in fits)
    iters = sorted(fits[c]["iter"] for c in fits)
    log.w("# post-fit RMS of the position residual's length: median %.1f m, 90th %.1f m, largest %.1f m; iterations median %d" % (
        H.median(rms), H.quant(rms, 0.9), rms[-1], H.median(iters)))
    if a.seed == 1:
        bcs = [fits[c]["bc"] for c in fits if fitbc[c]]
        if bcs:
            log.w("# fitted bc (where estimated): %d of %d negative; from %.4g to %.4g m^2/kg, median %.4g" % (
                sum(1 for b in bcs if b < 0), len(bcs), min(bcs), max(bcs), H.median(bcs)))
    # the catch-up
    catch = {}
    if not a.no_catchup:
        order = sorted(fits)

        def prop_run(objs, tag):
            pin, pout = os.path.join(W, "prop_in.%s.txt" % tag), os.path.join(W, "prop.%s.txt" % tag)
            with open(pin, "w", newline="\n") as f:
                for c in objs:
                    ft = fits[c]
                    bc = ft["bc"]
                    f.write("OBJ %d %s %s %s %s 0 0 1\nT 0 %s\n" % (c, float.hex(O[c]), " ".join(float.hex(x) for x in ft["y"]), float.hex(bc), float.hex(H.CRAM),
                                                                float.hex(a.ts_val)))
            return ([a.m1f, "prop", "native64", a.table, pin, pout], pout)
        parts = chunks(order, a.procs)
        cmds = [prop_run(p, "%02d" % i) for i, p in enumerate(parts)]
        codes = H.run_pool(cmds, a.procs, log)
        got = {}
        for (cmd, pout), code, part in zip(cmds, codes, parts):
            res = {}
            if os.path.exists(pout):
                for ln in open(pout, encoding="ascii"):
                    p = ln.split()
                    if p and p[0] == "P":
                        res[int(p[1])] = [float.fromhex(x) for x in p[3:9]]
            if code == 0:
                got.update(res)
            else:
                log.w("# a catch-up run exited %d; its %d objects are re-run one by one" % (code, len(part)))
                for c in part:
                    cmd1, pout1 = prop_run([c], "one.%d" % c)
                    rc, _, _ = H.run(cmd1, None, check=False)
                    if rc == 0:
                        for ln in open(pout1, encoding="ascii"):
                            p = ln.split()
                            if p and p[0] == "P":
                                got[int(p[1])] = [float.fromhex(x) for x in p[3:9]]
                    else:
                        catch[c] = ("stopped", None)
        for c in order:
            if c in catch:
                continue
            y = got.get(c)
            if y is None:
                catch[c] = ("stopped", None)
            elif not all(math.isfinite(x) for x in y):
                catch[c] = ("nonfinite", y)
            elif not math.sqrt(y[0] ** 2 + y[1] ** 2 + y[2] ** 2) > H.RMIN:
                catch[c] = ("below", y)
            else:
                catch[c] = ("ok", y)
        log.w("# catch-up to T_s: ok %d; stopped early %d; not finite %d; at or below 120 km %d" % tuple(
            sum(1 for v in catch.values() if v[0] == s) for s in ("ok", "stopped", "nonfinite", "below")))
        days = [(a.ts_val - O[c]) / 86400.0 for c in order]
        log.w("# catch-up spans from O: %.2f to %.2f days, median %.2f" % (min(days), max(days), H.median(days)))
    # the per-object table (ledger only)
    n_out, outp = H.next_numbered(a.out, "fit%d" % a.seed, ".tsv")
    rowmap = dict(fitset)
    lines = ["# h_seed fit%d: seed %d, T_s %s, log %s; per object (DEBRIS-H decision 13: the ledger only)" % (a.seed, a.seed, float.hex(a.ts_val), os.path.basename(log.path)),
             "cat\tgroup\tepoch\te0q\tO\tperigee_km\tage_s\tfitbc\tconv\titer\tsingular\trms_m\tmaxres_m\tbc\ty_O\tcatch\ty_Ts"]
    for c in sorted(fits):
        ft, r = fits[c], rowmap[c]
        cs, y = catch.get(c, ("skipped", None))
        lines.append("\t".join([str(c), r["GROUP"], r["EPOCH"], float.hex(e0q[c]), float.hex(O[c]), "%.3f" % (H.perigee_g(r) / 1000.0),
                                "%.3f" % float(Fraction(a.ts_val) - H.epoch_tdb(r)), str(ft["fitbc"]), str(ft["conv"]), str(ft["iter"]),
                                str(int(c in singular)), "%.3f" % ft["rms"], "%.3f" % ft["maxres"], float.hex(ft["bc"]),
                                ",".join(float.hex(x) for x in ft["y"]), cs, ",".join(float.hex(x) for x in y) if y else "-"]))
    H.write_new(outp, ("\n".join(lines) + "\n").encode("ascii"))
    log.w("# per-object fit table: %s (%d objects), sha256 %s" % (os.path.basename(outp), len(fits), H.sha256(outp)))
    c_ = cpu.close("h_seed fit%d log %03d" % (a.seed, log.n))
    if c_ is not None:
        log.w("# CPU: %.2f s by cycles / 2.5e9 (this script and every process it started)" % c_)
    return log.close()


def read_fit_table(path):
    rows = {}
    head = None
    for ln in open(path, encoding="ascii"):
        if ln.startswith("#"):
            continue
        p = ln.rstrip("\n").split("\t")
        if head is None:
            head = p
            continue
        d = dict(zip(head, p))
        rows[int(d["cat"])] = d
    return rows


def flags_of(d):
    f = 0
    if d["conv"] == "0" and d["singular"] == "0":
        f |= 1
    if d["singular"] == "1":
        f |= 2
    if d["fitbc"] == "1":
        f |= 4
    if float.fromhex(d["bc"]) < 0:
        f |= 8
    return f


def mode_combine(a):
    cpu = H.CpuAccount("h_seed_combine", a.cpu)
    log = H.Log("h_seed_combine", a.logs, SCRIPT, RULES, keep_dir=a.keep)
    f1, f2 = read_fit_table(a.fit1), read_fit_table(a.fit2)
    log.w("# fit tables: %s sha256 %s (%d objects); %s sha256 %s (%d objects)" % (os.path.basename(a.fit1), H.sha256(a.fit1), len(f1),
                                                                             os.path.basename(a.fit2), H.sha256(a.fit2), len(f2)))
    log.check(set(f1) == set(f2), "both seeds fitted the same objects")
    ok1 = {c for c, d in f1.items() if d["catch"] == "ok"}
    ok2 = {c for c, d in f2.items() if d["catch"] == "ok"}
    both = sorted(ok1 & ok2)
    for s, f, ok in ((1, f1, ok1), (2, f2, ok2)):
        log.w("# seed %d: left out for its catch-up: %d (%s)" % (s, len(f) - len(ok), ", ".join("%s %d" % (k, sum(1 for d in f.values() if d["catch"] == k))
                                                                                       for k in ("stopped", "nonfinite", "below", "skipped"))))
    log.w("# left out by either seed, and so of every track: %d; kept %d" % (len(set(f1) | set(f2)) - len(both), len(both)))
    hdrs = [[ln for ln in open(p, encoding="ascii") if ln.startswith("# h_seed fit")][0] for p in (a.fit1, a.fit2)]
    tss = [float.fromhex(h.split("T_s ")[1].split(",")[0]) for h in hdrs]
    log.check(tss[0] == tss[1], "both fit tables have one T_s (%r)" % tss[0])
    ts = tss[0]
    if not log.check(len(both) > 0, "objects in the seed: %d" % len(both)):
        return log.close()
    os.makedirs(a.out, exist_ok=True)
    out = {}
    for s, f in ((1, f1), (2, f2)):
        lines = ["# m1h seed %d: T_s %s (%s); objects %d; h_seed.py sha256 %s; fit table %s sha256 %s" % (
                     s, float.hex(ts), H.tdb_label(ts), len(both), H.sha256(SCRIPT), os.path.basename(a.fit1 if s == 1 else a.fit2), H.sha256(a.fit1 if s == 1 else a.fit2)),
                 "# columns: idx cat flags T_s x y z vx vy vz bc cram (every real a C99 hex float; flags 1 iteration limit, 2 singular, 4 bc estimated, 8 bc negative)"]
        for i, c in enumerate(both):
            d = f[c]
            y = [float.fromhex(x) for x in d["y_Ts"].split(",")]
            lines.append("%d %d %d %s %s %s %s" % (i, c, flags_of(d), float.hex(ts), " ".join(float.hex(x) for x in y), float.hex(float.fromhex(d["bc"])), float.hex(H.CRAM)))
        p = os.path.join(a.out, "seed%d.txt" % s)
        H.write_new(p, ("\n".join(lines) + "\n").encode("ascii"))
        out[s] = p
        log.w("# seed%d.txt: %d objects, sha256 %s" % (s, len(both), H.sha256(p)))
    meta = ["# h_seed combine: the seed's objects, per object (decision 13: the ledger only); log %s" % os.path.basename(log.path),
            "idx\tcat\tgroup\tepoch\te0q\tO\tperigee_km\tage_s\tflags1\tconv1\titer1\trms1_m\tbc1\tflags2\tconv2\titer2\trms2_m"]
    for i, c in enumerate(both):
        d1, d2 = f1[c], f2[c]
        meta.append("\t".join([str(i), str(c), d1["group"], d1["epoch"], d1["e0q"], d1["O"], d1["perigee_km"], d1["age_s"], str(flags_of(d1)), d1["conv"],
                               d1["iter"], d1["rms_m"], d1["bc"], str(flags_of(d2)), d2["conv"], d2["iter"], d2["rms_m"]]))
    mp = os.path.join(a.out, "seed_meta.tsv")
    H.write_new(mp, ("\n".join(meta) + "\n").encode("ascii"))
    log.w("# seed_meta.tsv sha256 %s" % H.sha256(mp))
    s1, s2 = H.read_seed(out[1]), H.read_seed(out[2])
    log.check(all(s2["rows"][i][4] == H.BC0 for i in s2["rows"]), "seed 2: every bc is exactly 0.01 m^2/kg")
    log.check(all(math.isfinite(x) for s in (s1, s2) for r in s["rows"].values() for x in r[3]) and
              all(math.sqrt(sum(x * x for x in r[3][:3])) > H.RMIN for s in (s1, s2) for r in s["rows"].values()),
              "every seed state finite and above 120 km")
    log.w("# flagged (iteration limit or singular): seed 1 %d, seed 2 %d; bc negative in seed 1: %d" % (
        sum(1 for r in s1["rows"].values() if r[1] & 3), sum(1 for r in s2["rows"].values() if r[1] & 3), sum(1 for r in s1["rows"].values() if r[1] & 8)))
    c_ = cpu.close("h_seed combine log %03d" % log.n)
    if c_ is not None:
        log.w("# CPU: %.2f s by cycles / 2.5e9" % c_)
    return log.close()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["fit", "combine"])
    ap.add_argument("--seed", type=int, choices=[1, 2])
    for o in ("--gp", "--tag", "--ts", "--table", "--m1f", "--java", "--jars", "--orekit", "--decoder", "--leaps", "--out", "--logs",
              "--keep", "--cpu", "--select", "--select-any", "--decode-order", "--plant-obs", "--fit1", "--fit2"):
        ap.add_argument(o)
    ap.add_argument("--procs", type=int, default=3)
    ap.add_argument("--jprocs", type=int, default=1)
    ap.add_argument("--test-sample", type=int, default=0)
    ap.add_argument("--no-catchup", action="store_true")
    ap.add_argument("--test", action="store_true")
    a = ap.parse_args()
    if a.mode == "fit":
        for o in ("seed", "gp", "tag", "ts", "table", "m1f", "java", "jars", "orekit", "decoder", "leaps", "out", "logs"):
            if getattr(a, o) is None:
                raise SystemExit("--%s is required" % o)
        return mode_fit(a)
    for o in ("fit1", "fit2", "out", "logs"):
        if getattr(a, o) is None:
            raise SystemExit("--%s is required" % o)
    return mode_combine(a)


if __name__ == "__main__":
    sys.exit(main())
