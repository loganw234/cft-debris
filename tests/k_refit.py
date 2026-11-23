# k_refit.py - cft-debris (DEBRIS-K): (R)'s fit, DEBRIS-F's fit rule as DEBRIS-H's tests/h_seed.py fit runs it, made
# callable on any list of element sets (the pilot's latest sets from the ledger's slot folders), and its regression on
# DEBRIS-H's test seed (the downloads' S0 layout). Standard library only; the desktop.
# cft-debris, MIT licence (see LICENSE at the repository root). Copied by DEBRIS-K, 2026-11-23, from DEBRIS-H's
# tests/h_seed.py (cft-debris's own, MIT; SHA-256 d43000d54299f28773b6db57bb923eb4b7caad29ff81a075e3345f7a52acc22d).
# What changed (and nothing else):
#   - the body of h_seed.py's mode_fit from the decode through the catch-up is now the function refit(), unchanged in its
#     steps and their order: e0q, O = e0q - 86,400 s, the decode in --jprocs contiguous chunks of the given order (one JVM
#     each), the 721 pseudo-observations, tests/m1f.c fit (seed 1's rule: bc estimated where the perigee by
#     tests/f_fit.py's formula is under 1,000 km), and the optional catch-up to T_s by tests/m1f.c prop;
#   - objects are keyed by a string (the catalogue number's digits in mode fit, as h_seed.py writes them, so its input
#     files are byte for byte h_seed.py's; the pilot's own keys elsewhere);
#   - mode fit (the regression) keeps h_seed.py's selection, its --test-sample draw and its fit table's columns; seed 1
#     only; no combine;
#   - logs go through k_lib.py (a copy of h_lib.py whose Log redacts the home folder).
# The pilot (tests/k_pilot.py) calls refit() with the latest set of each object at each forecast time.
#
#   fit: python -I -B k_refit.py fit --gp DIR --tag TAG --ts T_s --table TABLE --m1f EXE --java JAVA --jars DIR --orekit DIR
#            --decoder f5_sgp4.js --leaps tai-utc.dat --downloads DIR --out DIR --logs DIR [--procs 1] [--jprocs 1]
#            [--test-sample N] [--test] [--keep DIR] [--cpu TSV] [--expect-pv-in SHA256] [--compare TABLE:SHA256]
import argparse
import math
import os
import random
import sys
import time
from fractions import Fraction

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import k_lib as H  # noqa: E402

SCRIPT = os.path.abspath(__file__)
TEST_SEED = 0x7E57
PERIGEE_MIN = 200000.0
MAX_AGE = 30 * 86400.0
LEAD_MIN = 1200.0
MAXIT = 10

RULES = """
(R)'s FIT, DEBRIS-H's h_seed.py fit (seed 1) unchanged in its rules, applied to any list of element sets:
  e0q = the set's epoch in TDB rounded to 2^-20 s; O = e0q - 86,400 s; 721 pseudo-observations at O + 120 k (k = 0 to
  720) from Orekit's SGP4 (tests/f5_sgp4.js, GCRF, through DEBRIS-F's Earth orientation file), decoded in --jprocs
  contiguous chunks of the given order, one JVM each (the decoder's output depends on what its JVM decoded before:
  DEBRIS-H's finding 1); tests/m1f.c fit at native64 with its iteration limit of 10; the start state the first
  pseudo-observation's, bc from 0.01 m^2/kg, cram fixed at 0.01 m^2/kg; bc estimated where the perigee by tests/f_fit.py's
  formula (MU = 3.986004418e14) is under 1,000 km, held at 0.01 m^2/kg above; a fit that stops on the iteration limit, or
  on a singular matrix, keeps its last iterate and is flagged; an object Orekit refuses is excluded and counted.
THE CATCH-UP (mode fit): tests/m1f.c prop at native64 from O to T_s, whole steps of 15 s then one short step landing on
  T_s; a stopped run, a state not finite or at or below 6,498.137 km from the centre is marked so.
MODE FIT (the regression), h_seed.py's selection: the four groups' CSV files with their 17 columns asserted; ephemeris
  type 0; one object per element set by DEBRIS-G's key, the smallest catalogue number kept; the screens (perigee under
  200 km, epoch more than 30 days before T_s, origin after T_s) counted; --test-sample N by random.Random(0x7E57).sample
  over the kept catalogue numbers in ascending order. Its fit table has h_seed.py's columns.
ASSERTED in mode fit, besides h_seed.py's own checks: with --expect-pv-in, the decode batch's input file has that SHA-256
  (the batch's composition and order replayed, as the plan's regression requires).
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
    """h_seed.py's: the rows, the set key, the screens and the test selection; returns [(cat, row)] in catalogue order"""
    rows = []
    for g in H.GROUPS:
        p = gp_path(a.gp, g, a.tag)
        rg = H.read_gp(p, g)
        log.w("# %s: %d rows, sha256 %s" % (os.path.basename(p), len(rg), H.sha256(p)))
        rows += rg
    nt = sum(1 for r in rows if r["EPHEMERIS_TYPE"] != "0")
    rows0 = [r for r in rows if r["EPHEMERIS_TYPE"] == "0"]
    log.w("# rows read %d; excluded as ephemeris type not 0: %d" % (len(rows), nt))
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
    if a.test_sample:
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


def refit(cfg, log, items, W, ts_val=None, quiet_names=True):
    """h_seed.py's mode_fit from the decode through the catch-up. items: [(key, row)] in decode order (keys strings).
    cfg: java, jars (list), orekit, decoder, m1f, table, env (for m1f), procs, jprocs. Returns a dict with e0q, O, fits,
    singular, catch (if ts_val), refused, batches [(file, sha)]."""
    os.makedirs(W, exist_ok=True)
    e0q = {c: H.epoch_q(r) for c, r in items}
    O = {c: e0q[c] - 86400.0 for c, _ in items}
    for c, _ in items:
        assert Fraction(O[c]) == Fraction(e0q[c]) - 86400
    log.w("# the decode: %d objects in %d JVM run(s), in the given order" % (len(items), min(cfg["jprocs"], len(items))))
    parts = chunks(items, cfg["jprocs"])
    cmds, batches = [], []
    for i, part in enumerate(parts):
        pin, pout = os.path.join(W, "pv_in.%02d.txt" % i), os.path.join(W, "pv.%02d.txt" % i)
        H.decode_input(pin, [(str(c), r, [O[c] + 120.0 * j for j in range(H.NOBS)]) for c, r in part])
        cmds.append((H.java_argv(cfg["java"], cfg["jars"], cfg["decoder"], ["pv", cfg["orekit"], pin, pout]), pout))
        batches.append((pin, H.sha256(pin)))
        log.w("# decode batch %02d (--jprocs %d): %d objects x %d instants, in the order of %s/%s, sha256 %s" % (
            i, cfg["jprocs"], len(part), H.NOBS, os.path.basename(W), os.path.basename(pin), H.sha256(pin)))
    codes = H.run_pool(cmds, cfg["jprocs"], log)
    if not log.check(all(x == 0 for x in codes), "every decoder run exited 0 (%s)" % codes):
        raise RuntimeError("decoder failed")
    pv = {}
    for _, pout in cmds:
        pv.update(H.read_decoded(pout))
    refused = [c for c, _ in items if pv.get(str(c)) is None]
    log.w("# Orekit refused %d objects (excluded)" % len(refused))
    fitset = [(c, r) for c, r in items if pv.get(str(c)) is not None]
    log.check(all(len(pv[str(c)]) == H.NOBS for c, _ in fitset), "every decoded object has its 721 pseudo-observations")
    fitbc = {c: (1 if H.perigee_alt_km_f(r) < 1000.0 else 0) for c, r in fitset}
    parts = chunks(fitset, cfg["procs"])
    cmds = []
    for i, part in enumerate(parts):
        fin, fout = os.path.join(W, "fit_in.%02d.txt" % i), os.path.join(W, "fit.%02d.txt" % i)
        with open(fin, "w", newline="\n") as f:
            for c, r in part:
                s = pv[str(c)]
                f.write("OBJ %s %s %s %s %s %d %d 0\n" % (c, float.hex(O[c]), " ".join(float.hex(x) for x in s[0]), float.hex(H.BC0), float.hex(H.CRAM), fitbc[c], H.NOBS))
                for k in range(H.NOBS):
                    q = list(s[k][:3])
                    f.write("O %d %s\n" % (k, " ".join(float.hex(x) for x in q)))
        cmds.append(([cfg["m1f"], "fit", cfg["table"], fin, fout, "--maxit", str(MAXIT)], fout))
    codes = H.run_pool(cmds, cfg["procs"], log, env=cfg["env"])
    for (cmd, fout), code in zip(cmds, codes):
        if code != 0 and os.path.exists(fout + ".stderr"):
            log.w("# m1f fit exited %d: %s" % (code, open(fout + ".stderr", "rb").read().decode("utf-8", "replace").strip()[:300]))
    if not log.check(all(x == 0 for x in codes), "every fit run exited 0 (%s)" % codes):
        raise RuntimeError("fit failed")
    fits, singular = {}, set()
    for _, fout in cmds:
        for ln in open(fout, encoding="ascii"):
            p = ln.split()
            if p and p[0] == "FIT":
                v = [float.fromhex(x) for x in p[4:6]] + [float.fromhex(x) for x in p[8:16]]
                fits[p[1]] = {"conv": int(p[2]), "iter": int(p[3]), "rms": v[0], "maxres": v[1], "fitbc": int(p[7]), "t0": v[2], "y": v[3:9], "bc": v[9],
                              "line": ln.rstrip("\n")}
            elif p and p[0] == "ITER" and len(p) >= 4 and p[3] == "singular":
                singular.add(p[1])
    log.check(set(fits) == {str(c) for c, _ in fitset}, "every object fitted has a FIT line (%d of %d)" % (len(fits), len(fitset)))
    for c, _ in fitset:
        assert fits[str(c)]["t0"] == O[c] and fits[str(c)]["fitbc"] == fitbc[c]
    nconv = sum(1 for c in fits if fits[c]["conv"])
    nsing = sum(1 for c in fits if not fits[c]["conv"] and c in singular)
    nlim = sum(1 for c in fits if not fits[c]["conv"] and c not in singular)
    log.w("# fits: %d converged, %d stopped on the iteration limit, %d stopped on a singular matrix (flagged); bc estimated in %d" % (
        nconv, nlim, nsing, sum(fitbc.values())))
    if fits:
        rms = sorted(fits[c]["rms"] for c in fits)
        iters = sorted(fits[c]["iter"] for c in fits)
        log.w("# post-fit RMS of the position residual's length: median %.1f m, 90th %.1f m, largest %.1f m; iterations median %d" % (
            H.median(rms), H.quant(rms, 0.9), rms[-1], H.median(iters)))
        bcs = [fits[c]["bc"] for c in fits if fitbc[c]]
        if bcs:
            log.w("# fitted bc (where estimated): %d of %d negative; from %.4g to %.4g m^2/kg, median %.4g" % (
                sum(1 for b in bcs if b < 0), len(bcs), min(bcs), max(bcs), H.median(bcs)))
    catch = {}
    if ts_val is not None:
        order = sorted(fits, key=lambda c: (len(c), c))

        def prop_run(objs, tag):
            pin, pout = os.path.join(W, "prop_in.%s.txt" % tag), os.path.join(W, "prop.%s.txt" % tag)
            with open(pin, "w", newline="\n") as f:
                for c in objs:
                    ft = fits[c]
                    bc = ft["bc"]
                    f.write("OBJ %s %s %s %s %s 0 0 1\nT 0 %s\n" % (c, float.hex(ft["t0"]), " ".join(float.hex(x) for x in ft["y"]), float.hex(bc), float.hex(H.CRAM),
                                                                float.hex(ts_val)))
            return ([cfg["m1f"], "prop", "native64", cfg["table"], pin, pout], pout)
        parts = chunks(order, cfg["procs"])
        cmds = [prop_run(p, "%02d" % i) for i, p in enumerate(parts)]
        codes = H.run_pool(cmds, cfg["procs"], log, env=cfg["env"])
        got = {}
        for (cmd, pout), code, part in zip(cmds, codes, parts):
            res = {}
            if os.path.exists(pout):
                for ln in open(pout, encoding="ascii"):
                    p = ln.split()
                    if p and p[0] == "P":
                        res[p[1]] = [float.fromhex(x) for x in p[3:9]]
            if code == 0:
                got.update(res)
            else:
                log.w("# a catch-up run exited %d; its %d objects are re-run one by one" % (code, len(part)))
                for c in part:
                    cmd1, pout1 = prop_run([c], "one.%s" % c)
                    rc, _, _ = H.run(cmd1, None, check=False, env=cfg["env"])
                    if rc == 0:
                        for ln in open(pout1, encoding="ascii"):
                            p = ln.split()
                            if p and p[0] == "P":
                                got[p[1]] = [float.fromhex(x) for x in p[3:9]]
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
    return {"e0q": e0q, "O": O, "fits": fits, "singular": singular, "catch": catch, "refused": refused, "batches": batches,
            "fitbc": fitbc}


def mode_fit(a):
    cpu = H.CpuAccount("k_refit_fit", a.cpu)
    a.ts_val = parse_ts(a.ts)
    t_run = time.time()
    log = H.Log("k_refit_fit", a.logs, SCRIPT, RULES, extra=[a.decoder], keep_dir=a.keep)
    try:
        H.load_leaps(a.leaps)
        log.w("# T_s %r s TDB = %s (%s); table %s sha256 %s; m1f sha256 %s; leaps sha256 %s" % (
            a.ts_val, float.hex(a.ts_val), H.tdb_label(a.ts_val), os.path.basename(a.table), H.sha256(a.table), H.sha256(a.m1f), H.sha256(a.leaps)))
        for f in sorted(os.listdir(a.orekit)):
            log.w("# orekit data %s sha256 %s" % (f, H.sha256(os.path.join(a.orekit, f))))
        jars = sorted(os.path.join(a.jars, j) for j in os.listdir(a.jars) if j.endswith(".jar"))
        for j in jars:
            log.w("# jar %s sha256 %s" % (os.path.basename(j), H.sha256(j)))
        menv = dict(os.environ)
        menv["M1_DOWNLOADS"] = a.downloads
        for f in ("EIGEN6-C4.gfc", "lnxp1900p2053.421", "header.421"):
            p = os.path.join(a.downloads, f, f)
            log.w("# m1f's downloads: %s sha256 %s" % (f, H.sha256(p) if os.path.exists(p) else "(absent)"))
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
        n_out, outp = H.next_numbered(a.out, "fit1", ".tsv")
        W = os.path.join(a.out, "work_fit1_%d" % log.n)
        cfg = {"java": a.java, "jars": jars, "orekit": a.orekit, "decoder": a.decoder, "m1f": a.m1f, "table": a.table, "env": menv,
               "procs": a.procs, "jprocs": a.jprocs}
        res = refit(cfg, log, [(str(c), r) for c, r in kept], W, ts_val=a.ts_val)
        if a.expect_pv_in:
            log.check(len(res["batches"]) == 1 and res["batches"][0][1] == a.expect_pv_in,
                      "the decode batch's input has the expected SHA-256 (%s)" % ", ".join(h for _, h in res["batches"]))
        fits, singular, catch, e0q, O = res["fits"], res["singular"], res["catch"], res["e0q"], res["O"]
        rowmap = {str(c): r for c, r in kept}
        lines = ["# k_refit fit1: seed 1, T_s %s, log %s; per object (the ledger only)" % (float.hex(a.ts_val), os.path.basename(log.path)),
                 "cat\tgroup\tepoch\te0q\tO\tperigee_km\tage_s\tfitbc\tconv\titer\tsingular\trms_m\tmaxres_m\tbc\ty_O\tcatch\ty_Ts"]
        for c in sorted(fits, key=int):
            ft, r = fits[c], rowmap[c]
            cs, y = catch.get(c, ("skipped", None))
            lines.append("\t".join([c, r["GROUP"], r["EPOCH"], float.hex(e0q[c]), float.hex(O[c]), "%.3f" % (H.perigee_g(r) / 1000.0),
                                    "%.3f" % float(Fraction(a.ts_val) - H.epoch_tdb(r)), str(ft["fitbc"]), str(ft["conv"]), str(ft["iter"]),
                                    str(int(c in singular)), "%.3f" % ft["rms"], "%.3f" % ft["maxres"], float.hex(ft["bc"]),
                                    ",".join(float.hex(x) for x in ft["y"]), cs, ",".join(float.hex(x) for x in y) if y else "-"]))
        H.write_new(outp, ("\n".join(lines) + "\n").encode("ascii"))
        log.w("# per-object fit table: %s (%d objects), sha256 %s" % (os.path.basename(outp), len(fits), H.sha256(outp)))
        if a.compare:
            # THE REGRESSION'S CRITERION (the plan, stated before this run): the target's table reproduced, the same
            # objects, convergence and iterations, and every printed value equal (string equality, field by field).
            tp, tsha = a.compare.rsplit(":", 1)
            log.check(H.sha256(tp) == tsha, "the target %s has its recorded SHA-256 %s" % (os.path.basename(tp), tsha))
            mine = [ln for ln in open(outp, encoding="ascii").read().split("\n") if ln and not ln.startswith("#")]
            theirs = [ln for ln in open(tp, encoding="ascii").read().split("\n") if ln and not ln.startswith("#")]
            log.check(len(mine) > 1 and mine[0] == theirs[0], "the same columns (%d)" % len(mine[0].split("\t")))
            dm = {ln.split("\t")[0]: ln.split("\t") for ln in mine[1:]}
            dt = {ln.split("\t")[0]: ln.split("\t") for ln in theirs[1:]}
            log.check(set(dm) == set(dt) and len(dm) > 0, "the same %d objects" % len(dt))
            head = mine[0].split("\t")
            bad = {}
            for c in sorted(set(dm) & set(dt), key=int):
                for i, (x, y) in enumerate(zip(dm[c], dt[c])):
                    if x != y:
                        bad.setdefault(head[i], 0)
                        bad[head[i]] += 1
            nfield = sum(len(dt[c]) for c in dt)
            log.check(not bad, "REGRESSION: every printed value equal, %d fields of %d objects (columns differing: %s)" % (
                nfield, len(dt), ", ".join("%s %d" % kv for kv in sorted(bad.items())) or "none"))
            cv = sum(1 for c in dt if dm.get(c, [None] * 10)[8] == dt[c][8] and dm.get(c, [None] * 10)[9] == dt[c][9])
            log.w("# convergence and iterations equal in %d of %d objects" % (cv, len(dt)))
    finally:
        c_ = cpu.close("k_refit fit log %03d" % log.n)
        if c_ is not None:
            log.w("# CPU: %.2f s by cycles / 2.5e9 (this script and every process it started)" % c_)
    return log.close()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["fit"])
    for o in ("--gp", "--tag", "--ts", "--table", "--m1f", "--java", "--jars", "--orekit", "--decoder", "--leaps", "--out", "--logs",
              "--keep", "--cpu", "--downloads", "--expect-pv-in", "--compare"):
        ap.add_argument(o)
    ap.add_argument("--procs", type=int, default=1)
    ap.add_argument("--jprocs", type=int, default=1)
    ap.add_argument("--test-sample", type=int, default=0)
    ap.add_argument("--test", action="store_true")
    a = ap.parse_args()
    for o in ("gp", "tag", "ts", "table", "m1f", "java", "jars", "orekit", "decoder", "leaps", "out", "logs", "downloads"):
        if getattr(a, o) is None:
            raise SystemExit("--%s is required" % o)
    return mode_fit(a)


if __name__ == "__main__":
    sys.exit(main())
