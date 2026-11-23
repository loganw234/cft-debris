# k_pilot.py - cft-debris (DEBRIS-K), K3: the pilot hindcast as DEBRIS-K's plan fixes it (studies/DEBRIS-K-plan.md,
# draft 3, "The pilot hindcast (K3), fixed before the data"). Standard library only; the desktop.
# cft-debris, MIT licence (see LICENSE at the repository root). Written by DEBRIS-K, 2026-11-23, before any miss of the
# pilot's objects was computed or read. Reuses, by copy (cft-debris's own, MIT): DEBRIS-H's tests/h_check.py's miss()
# and t3() (with DEBRIS-F's F6 rules for T1, T2 and T3, tests/f6_hindcast.py), and through k_lib.py DEBRIS-H's h_lib.py;
# (R)'s fit is tests/k_refit.py's refit(), (H)'s is tests/k_fit.c's fit, predictions are tests/m1f.c's prop.
#
#   python -I -B k_pilot.py <stage> --r2 DIR --downloads DIR --work DIR --logs DIR --keep DIR --cpu TSV --m1f EXE
#       --kfit EXE --table TABLE --java JAVA --jars DIR --orekit DIR --decoder f5_sgp4.js --leaps FILE [--h-times 5,9,13]
#       [--c-data DIR --c-gfc DIR --c-de DIR --c-limit S]   (cfit: tests/k_swcopy.py's orekit_c3, k_gfc_copy.py's copy, DE421)
# stages, in order: prep, bprime, rfit, hfit, decay, cfit (only if the budget allows: the plan's decision 3), stats. Each writes one numbered log (the repository's), and its
# per-object outputs (sets, states, fits, misses) under --work, which is the ledger's debris-k\ (never the repository).
import argparse
import json
import math
import os
import sys
import time
from fractions import Fraction

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import k_lib as H  # noqa: E402
import k_refit as KR  # noqa: E402

SCRIPT = os.path.abspath(__file__)
TS_EXPECT = 2933400.0                 # DEBRIS-H's T_s, 2026-11-18 22:50:00 TDB (seed1.txt's header)
GM_SEL, R_SEL = 3.986004415e14, 6378136.46
FT_SLOTS = [1, 5, 9, 13]              # forecast times besides T_s, for (B'), (R) and (C)
H_SLOTS_DEFAULT = [5, 9, 13]          # (H)'s forecast times
IDX_1595, IDX_1178 = 1595, 1178
DAY = 86400.0
CELLS = [("under 6 h", 0.0, 6.0), ("6 to 24 h", 6.0, 24.0), ("1 to 2 d", 24.0, 48.0), ("2 d and over", 48.0, 1e99)]
LC_BINS = [("1", 1, 1), ("2", 2, 2), ("3 or 4", 3, 4), ("5 to 8", 5, 8), ("9 or more", 9, 10 ** 9)]

CRITERIA = """
THE PILOT (K3), as DEBRIS-K's plan, draft 3, fixes it; written into this script before any miss of the pilot's objects.
OBJECTS: every object of DEBRIS-H's seed (debris-h/box/r2/seed/seed1.txt) whose perigee at T_s is under 400 km: the
  osculating a and e of the seed's binary64 state at T_s, GM = 3.986004415e14 m^3/s^2, perigee a(1 - e) - 6,378,136.46 m.
  (The plan counts 17; the count found is logged and checked against it.) Seed index 1595 is a reconstruction only: its
  one output is a decay prediction from fits to sets with epochs before 2026-11-18 00:00 UTC; no miss of it is computed.
SETS: each object's sets in S_H0 (the downloads' gp-*-SH0) and in DEBRIS-H's slot folders 1 to 20 (svc/fetch/slotNN),
  taken in that order (S_H0, then slot 1, 2, ...), ephemeris type 0, by catalogue number; a set whose epoch is no later
  than the object's previous kept set's is skipped and counted (as a copy where it equals that set in every field).
  The first kept set must be the seed's own (seed_meta.tsv's epoch). A slot's sets are fetched at its t_end in
  slots.tsv (POSIX, to TDB through tai-utc.dat); S_H0's before T_s.
FORECAST TIMES: T_s, and the t_end of slots 1, 5, 9 and 13 for (B'), (R) and (C); slots 5, 9 and 13 for (H). A forecast
  uses only the sets fetched by its time; its latest set is the one of latest epoch among them.
REFERENCES: each later kept set of the object (epoch after the latest set's), fetched through slot 20, at its own epoch
  e rounded to 2^-20 s (e_q, DEBRIS-F's B1), through SGP4 (tests/f5_sgp4.js, GCRF); and at e_q + 1 s for T1.
HORIZON, every variant: the reference's epoch less the epoch of the latest set the forecast used (for (A) and (B) the
  seed's set, as DEBRIS-H recorded it: its tables' horizon_h).
VARIANTS: (A) A64's misses with A256's beside them, and (B), read from DEBRIS-H's check tables (status checked);
  (B') SGP4 from the latest set at each reference's e_q; (R) M1 native64 refitted from the latest set by DEBRIS-F's
  rule (tests/k_refit.py's refit(), h_seed.py's seed 1 rule) and propagated by tests/m1f.c prop from its origin to e_q;
  (H) M1 native64 fitted by tests/k_fit.c to every set so far: over the grid O_H + 120 k, O_H = e_q(oldest) - 86,400 s,
  to the last grid time at or before e_q(latest), each grid time's pseudo-observation from SGP4 of the earliest set whose
  e_q is at or after it; start state the first pseudo-observation's, bc from 0.01, cram 0.01 fixed, bc estimated
  (perigee by f_fit.py's formula under 1,000 km), maxit 10; propagated by m1f prop from O_H; (C) only if the budget
  allows: DEBRIS-F's route (C), tests/k_orekit_fit.js (f6_orekit_fit.js with several targets), fitted to (R)'s own
  721 pseudo-observations of each latest set and propagated to that set's references; NRLMSISE00 through Orekit's
  CssiSpaceWeatherData from the 0-filled copy (tests/k_swcopy.py), its dates asserted inside tests/k_swcheck.py's span
  (stage cfit, added before (C) ran and before any miss of (C) existed).
THE MISS: the GCRF distance to the reference and its radial, along-track and cross-track parts in the reference's
  frame (R along r_ref, C along r_ref x v_ref, A = C x R), as h_check.py.
A CHECK is a distinct (object, set or sets used, reference): forecasts at two times that use the same latest set (and
  so the same history) give one check, counted once; the rows per forecast time are kept in the ledger's table.
DECAY PREDICTIONS: for seed index 1178 and every pilot object with perigee under 300 km, from each forecast time of (R)
  and (H), M1's rule (tests/m1h.c's RMIN 6,498,137.0 m, carried in tests/k_fit.c decay): from the fit's origin, whole
  rk4 steps of 15 s, the first step at whose end the distance from the centre is not above RMIN; up to 30 days after the
  forecast time (else "no decay within 30 days"). For seed index 1595, from (R)'s and (H)'s rules applied to its sets
  with epochs before 2026-11-18 00:00 UTC, set beside SATCAT's date taken as the whole UTC day 2026-11-18.
STATISTICS (no pass condition): for each variant and horizon cell (under 6 h, 6 to 24 h, 1 to 2 d, 2 d and over) and
  overall, with n: the miss's median and 90th percentile (the ceil(0.9 n)-th smallest, h_check.py's quant), the same for
  the along-track part's size with its signed median beside; a cell of fewer than 5 checks gives its count and median
  only; with the flagged fits in (an (R) or (H) fit stopped on its iteration limit or a singular matrix; for (A) and (B)
  the seed's flags1 & 3), and again without them. The main comparisons, cell by cell on the same checks: (R) against
  (B'), and (H) against (B'); (A) against (B) restating DEBRIS-H's on these objects. Per object (by seed index), the
  same over all horizons. For (H), the learning curve: the median miss at horizons of 12 to 36 h by the number of sets
  in the fit (1, 2, 3 or 4, 5 to 8, 9 or more), (B')'s median on the same checks beside it. The share of checks in which
  (R), (H) each miss less than (B') (checks cluster by object: not a share of independent trials). The decay
  predictions, each with its rule, its forecast time and the sets it used.
CONTROLS, each asserted (FAIL is reported as failed):
  T1 every check and variant (B'), (R), (H): with the reference moved to e_q + 1 s, the change in the miss vector equals
     the reference's velocity x 1 s within 1% of that velocity's size (F6, h_check.py);
  T2 every latest set that a later slot repeats equal in every field: decoded at its own e_q in one JVM and the copy in
     another, in the same order, (B')'s miss is exactly 0 (F6's T2);
  T3 every forecast time and reference slot, over its (B') checks in seed-index (= catalogue) order: (B')'s position
     against the reference of the next check (cyclically) whose reference mean motion differs by more than 1e-3
     rev/day must miss by more than 100 km; EXCEPT where the two references' orbital planes (the normals r x v of their
     GCRF states) lie within 0.1 deg of each other: such a pair is listed, not tested;
  K1 (tests/k_fit.c a faithful copy) k_fit's fit, given (R)'s 721 pseudo-observations of its first object at T_s with
     their times O + 120 k, prints the same FIT line, character for character, as tests/m1f.c fit did in (R);
  K2 (the frame, the time and the set) on every check-table row of a pilot object: (B') at T_s and the reference agree
     with DEBRIS-H's B_pos and ref_state within 1e-3 m in position (basis: the decoder's batch dependence, up to
     1.7e-5 m, DEBRIS-H's finding 1), and e_q is equal;
  PLANTED BC: the lowest-perigee pilot object other than 1595 that has a reference 12 to 36 h after a forecast time
     (the reference's epoch less the forecast time), at the first such forecast time and its earliest such reference,
     and that M1 (k_fit decay from (R)'s fit) does not decay before that reference: (R)'s bc doubled in the pipeline's
     prediction must give, bit for bit, the state tests/m1f.c prop gives when run directly with the doubled bc and the
     same inputs, and must move the predicted position at that reference by at least 100 m;
  PLANTED IDENTITY: (H) at slot 5 for the planted-bc object X fitted to another object's sets (Y, the next pilot object
     in seed-index order, cyclically, but 1595, whose latest set at slot 5 has a mean motion more than 1e-3 rev/day from
     X's): every miss at X's references from slot 5 must exceed ten times (H)'s own median over all its checks, or the
     fit be refused (singular matrix or a non-finite state).
REGRESSION (tests/k_refit.py fit, its own log): (R)'s code on DEBRIS-H's test seed must reproduce
  debris-h/testseed/repro/fit1.001.tsv, every printed value equal.
MEASURED besides: the 17 seed sets refitted on the desktop against the box's seed fits (fit1.001.tsv), and (R) at T_s
  against (A64) on their common checks; no tolerance (DEBRIS-H's H6: the machines differ in the fit).
"""


# ------------------------------------------------------------------ small helpers
def jload(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def jsave(p, obj):
    H.write_new(p, json.dumps(obj, sort_keys=True).encode("utf-8"))


def perigee_osc(y):
    r = y[:3]
    v = y[3:6]
    rn = math.sqrt(sum(x * x for x in r))
    v2 = sum(x * x for x in v)
    a = 1.0 / (2.0 / rn - v2 / GM_SEL)
    h = [r[1] * v[2] - r[2] * v[1], r[2] * v[0] - r[0] * v[2], r[0] * v[1] - r[1] * v[0]]
    vxh = [v[1] * h[2] - v[2] * h[1], v[2] * h[0] - v[0] * h[2], v[0] * h[1] - v[1] * h[0]]
    ev = [vxh[i] / GM_SEL - r[i] / rn for i in range(3)]
    e = math.sqrt(sum(x * x for x in ev))
    return a * (1.0 - e) - R_SEL


def normal(st):
    r, v = st[:3], st[3:6]
    return [r[1] * v[2] - r[2] * v[1], r[2] * v[0] - r[0] * v[2], r[0] * v[1] - r[1] * v[0]]


def angle_deg(a, b):
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(x * x for x in b))
    c = sum(x * y for x, y in zip(a, b)) / (na * nb)
    return math.degrees(math.acos(max(-1.0, min(1.0, c))))


def miss(p, ref, ref1):
    """h_check.py's (F6's) miss: |p - ref|, its RIC parts, and T1's error (|(p - ref) - (p - ref1) - v_ref|, |v_ref|)"""
    dp = [a - b for a, b in zip(p[:3], ref[:3])]
    dp1 = [a - b for a, b in zip(p[:3], ref1[:3])]
    ch = [a - b for a, b in zip(dp, dp1)]
    v = ref[3:6]
    vn = math.sqrt(sum(x * x for x in v))
    t1 = math.sqrt(sum((a - b) ** 2 for a, b in zip(ch, v)))
    return math.sqrt(sum(x * x for x in dp)), H.ric(dp, ref[:3], v), t1, vn


def utc_label(t_tdb):
    u = float(H.tdb_to_unix(t_tdb))
    return time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime(u))


def menv(a):
    e = dict(os.environ)
    e["M1_DOWNLOADS"] = a.downloads.rstrip("/\\") + "/"
    return e


def jars_of(a):
    return sorted(os.path.join(a.jars, j) for j in os.listdir(a.jars) if j.endswith(".jar"))


def decode(a, log, items, W, tag):
    """items: (key, row, [TDB instants]); one JVM; returns {key: [state6]} (None for a refused set)"""
    pin, pout = os.path.join(W, "%s_pv_in.txt" % tag), os.path.join(W, "%s_pv.txt" % tag)
    H.decode_input(pin, items)
    log.w("# decode batch %s: one JVM, %d sets, %d instants, in the order of %s, sha256 %s" % (
        tag, len(items), sum(len(t) for _, _, t in items), os.path.basename(pin), H.sha256(pin)))
    H.run(H.java_argv(a.java, jars_of(a), a.decoder, ["pv", a.orekit, pin, pout]), log)
    out = H.read_decoded(pout)
    for k, _, ts in items:
        assert out.get(k) is None or len(out[k]) == len(ts), "decode %s: %s has %d states for %d instants" % (tag, k, len(out[k]), len(ts))
    return out


def m1f_prop(a, log, W, tag, objs, bc_scale=None):
    """objs: [(id, t0, y6, bc, cram, [targets ascending])]; tests/m1f.c prop native64; returns {id: [(T, state6, hex6)]}.
    bc_scale {id: factor} multiplies an object's bc before it is written (the planted control only)."""
    pin, pout = os.path.join(W, "%s_prop_in.txt" % tag), os.path.join(W, "%s_prop.txt" % tag)
    with open(pin, "w", newline="\n") as f:
        for oid, t0, y, bc, cram, tg in objs:
            b = bc * bc_scale[oid] if bc_scale and oid in bc_scale else bc
            f.write("OBJ %s %s %s %s %s 0 0 %d\n" % (oid, float.hex(t0), " ".join(float.hex(x) for x in y), float.hex(b), float.hex(cram), len(tg)))
            for k, T in enumerate(tg):
                f.write("T %d %s\n" % (k, float.hex(T)))
    log.w("# m1f prop %s: %d objects, %d targets, input sha256 %s" % (tag, len(objs), sum(len(o[5]) for o in objs), H.sha256(pin)))
    H.run([a.m1f, "prop", "native64", a.table, pin, pout], log, env=menv(a))
    out = {}
    for ln in open(pout, encoding="ascii"):
        p = ln.split()
        if p and p[0] == "P":
            out.setdefault(p[1], []).append((float.fromhex(p[2]), [float.fromhex(x) for x in p[3:9]], p[9:15]))
    for oid, _, _, _, _, tg in objs:
        assert len(out.get(oid, [])) == len(tg), "prop %s: %s" % (tag, oid)
    return out, pout


def kfit_fit(a, log, W, tag, objs):
    """objs: [(id, t0, y0[6], fitbc, [(t, pos3)])]; tests/k_fit.c fit; returns {id: fit}"""
    pin, pout = os.path.join(W, "%s_kfit_in.txt" % tag), os.path.join(W, "%s_kfit.txt" % tag)
    with open(pin, "w", newline="\n") as f:
        for oid, t0, y0, fitbc, obs in objs:
            f.write("OBJ %s %s %s %s %s %d %d 0\n" % (oid, float.hex(t0), " ".join(float.hex(x) for x in y0), float.hex(H.BC0), float.hex(H.CRAM), fitbc, len(obs)))
            for k, (t, q) in enumerate(obs):
                f.write("O %d %s %s\n" % (k, float.hex(t), " ".join(float.hex(x) for x in q[:3])))
    log.w("# k_fit fit %s: %d objects, %d observations, input sha256 %s" % (tag, len(objs), sum(len(o[4]) for o in objs), H.sha256(pin)))
    H.run([a.kfit, "fit", a.table, pin, pout, "--maxit", "10"], log, env=menv(a))
    fits, singular = {}, set()
    for ln in open(pout, encoding="ascii"):
        p = ln.split()
        if p and p[0] == "FIT":
            v = [float.fromhex(x) for x in p[4:6]] + [float.fromhex(x) for x in p[8:16]]
            fits[p[1]] = {"conv": int(p[2]), "iter": int(p[3]), "rms": v[0], "maxres": v[1], "fitbc": int(p[7]), "t0": v[2], "y": v[3:9], "bc": v[9],
                          "line": ln.rstrip("\n")}
        elif p and p[0] == "ITER" and len(p) >= 4 and p[3] == "singular":
            singular.add(p[1])
    for oid in fits:
        fits[oid]["singular"] = int(oid in singular)
    assert set(fits) == {o[0] for o in objs}, "k_fit %s: every object has a FIT line" % tag
    return fits


def kfit_decay(a, log, W, tag, objs):
    """objs: [(id, t0, y6, bc, cram, tend)]; returns {id: (kind, step, t, r)}"""
    pin, pout = os.path.join(W, "%s_decay_in.txt" % tag), os.path.join(W, "%s_decay.txt" % tag)
    with open(pin, "w", newline="\n") as f:
        for oid, t0, y, bc, cram, tend in objs:
            f.write("OBJ %s %s %s %s %s %s\n" % (oid, float.hex(t0), " ".join(float.hex(x) for x in y), float.hex(bc), float.hex(cram), float.hex(tend)))
    log.w("# k_fit decay %s: %d runs, input sha256 %s" % (tag, len(objs), H.sha256(pin)))
    H.run([a.kfit, "decay", "native64", a.table, pin, pout], log, env=menv(a))
    out = {}
    for ln in open(pout, encoding="ascii"):
        p = ln.split()
        if p and p[0] in ("DECAY", "LIVE"):
            out[p[1]] = (p[0], int(p[2]), float.fromhex(p[3]), float(p[4]))
        elif p and p[0] == "NONFINITE":
            out[p[1]] = (p[0], int(p[2]), float.fromhex(p[3]), float("nan"))
    assert set(out) == {o[0] for o in objs}, "decay %s: every run has a result" % tag
    return out


def flagged(fit):
    return int((not fit["conv"]) or fit.get("singular", 0) == 1)


def open_stage(a, stage):
    H.load_leaps(a.leaps)
    cpu = H.CpuAccount("k_pilot_%s" % stage, a.cpu)
    log = H.Log("k_pilot_%s" % stage, a.logs, SCRIPT, CRITERIA, extra=[os.path.join(os.path.dirname(SCRIPT), "k_refit.py"),
                                                                     os.path.join(os.path.dirname(SCRIPT), "k_fit.c"), a.decoder], keep_dir=a.keep)
    for p in (a.m1f, a.kfit, a.table, a.leaps):
        log.w("# %s sha256 %s" % (os.path.basename(p), H.sha256(p)))
    W = os.path.join(a.work, "work")
    os.makedirs(W, exist_ok=True)
    return cpu, log, W


def close_stage(cpu, log, stage):
    c_ = cpu.close("k_pilot %s log %03d" % (stage, log.n))
    if c_ is not None:
        log.w("# CPU: %.2f s by cycles / 2.5e9 (this stage: the script and every process it started)" % c_)
    return log.close()


# ------------------------------------------------------------------ stage prep: objects, sets, forecast times, checks
def stage_prep(a):
    cpu, log, W = open_stage(a, "prep")
    try:
        seedp = os.path.join(a.r2, "seed", "seed1.txt")
        metap = os.path.join(a.r2, "seed", "seed_meta.tsv")
        slotsp = os.path.join(a.r2, "svc", "fetch", "slots.tsv")
        for p in (seedp, metap, slotsp):
            log.w("# %s sha256 %s" % (os.path.basename(p), H.sha256(p)))
        seed = H.read_seed(seedp)
        ts = seed["ts"]
        log.check(ts == TS_EXPECT, "T_s is DEBRIS-H's, %r s TDB (%s)" % (ts, H.tdb_label(ts)))
        meta = {}
        head = None
        for ln in open(metap, encoding="ascii"):
            if ln.startswith("#"):
                continue
            q = ln.rstrip("\n").split("\t")
            if head is None:
                head = q
                continue
            d = dict(zip(head, q))
            meta[int(d["idx"])] = d
        per = {i: perigee_osc(r[3]) for i, r in seed["rows"].items()}
        pilot = sorted(i for i in per if per[i] < 400e3)
        log.w("# pilot objects (perigee at T_s under 400 km): %d; under 250 km %d, under 300 km %d, under 350 km %d" % (
            len(pilot), sum(1 for i in pilot if per[i] < 250e3), sum(1 for i in pilot if per[i] < 300e3), sum(1 for i in pilot if per[i] < 350e3)))
        log.check(len(pilot) == 17, "the count equals the plan's 17 (a consistency check of the sample's rule)")
        log.check(IDX_1595 in pilot and IDX_1178 in pilot, "seed indices 1595 and 1178 are among them")
        log.w("# pilot seed indices: %s" % ", ".join(str(i) for i in pilot))
        log.w("# their perigees at T_s (km), in index order: %s" % ", ".join("%d %.1f" % (i, per[i] / 1e3) for i in pilot))
        cat2i = {int(seed["rows"][i][0]): i for i in pilot}
        # S_H0, then the slots
        slots = H.read_slots_table(slotsp)
        fetch = os.path.join(a.r2, "svc", "fetch")
        sources = [("SH0", None)] + [("slot%02d" % j, j) for j in range(1, 21) if os.path.isdir(os.path.join(fetch, "slot%02d" % j))]
        log.w("# sources in order: %s" % ", ".join(s for s, _ in sources))
        hist = {i: [] for i in pilot}
        skipped = {i: {"copy": 0, "not_later": 0} for i in pilot}
        copies = {}
        files_read = []
        for name, j in sources:
            if j is None:
                rows = []
                for g in H.GROUPS:
                    p = os.path.join(a.downloads, "gp-%s-SH0" % g, "gp-%s-SH0.csv" % g)
                    files_read.append((name + "/" + os.path.basename(p), H.sha256(p)))
                    rows += H.read_gp(p, g)
            else:
                rows = []
                for g, (p, rg) in sorted(H.read_slot(fetch, j).items()):
                    files_read.append((name + "/" + os.path.basename(p), H.sha256(p)))
                    rows += rg
            mine = [r for r in rows if r["EPHEMERIS_TYPE"] == "0" and int(r["NORAD_CAT_ID"]) in cat2i]
            mine.sort(key=lambda r: (int(r["NORAD_CAT_ID"]), H.epoch_tdb(r)))
            for r in mine:
                i = cat2i[int(r["NORAD_CAT_ID"])]
                e = H.epoch_tdb(r)
                if hist[i] and not e > Fraction(hist[i][-1]["e"]):
                    if any(all(r[c] == s["row"][c] for c in H.COLUMNS) for s in hist[i]):
                        skipped[i]["copy"] += 1
                        same = [s for s in hist[i] if all(r[c] == s["row"][c] for c in H.COLUMNS)][0]
                        copies.setdefault(same["key"], []).append({"src": name, "row": r})
                    else:
                        skipped[i]["not_later"] += 1
                    continue
                n = len(hist[i])
                hist[i].append({"key": "%d_%d" % (i, n), "src": name, "slot": 0 if j is None else j, "row": {c: r[c] for c in H.COLUMNS + ["GROUP"]},
                                "e": str(e.numerator) + "/" + str(e.denominator), "eq": H.quantize(e)})
        for nm, h in files_read:
            log.w("# read %s sha256 %s" % (nm, h))
        for i in pilot:
            log.check(len(hist[i]) >= 1 and hist[i][0]["src"] == "SH0" and hist[i][0]["row"]["EPOCH"] == meta[i]["epoch"],
                      "idx %d: the first kept set is the seed's own, from S_H0" % i)
        log.w("# sets per object (seed index: new sets after the seed's, copies skipped, not later skipped):")
        for i in pilot:
            log.w("#   %d: %d new, %d copies, %d not later" % (i, len(hist[i]) - 1, skipped[i]["copy"], skipped[i]["not_later"]))
        # forecast times
        F = {"Ts": ts}
        for j in FT_SLOTS:
            log.check(slots[j]["status"] == "ok", "slot %d fetched all four groups (status %s)" % (j, slots[j]["status"]))
            F["s%02d" % j] = H.posix_to_tdb(slots[j]["t_end"])
        log.w("# forecast times: %s" % ", ".join("%s %s (%.4f h after T_s)" % (k, utc_label(v), (v - ts) / 3600.0) for k, v in F.items()))

        def avail(i, lab):
            j = 0 if lab == "Ts" else int(lab[1:])
            return [s for s in hist[i] if s["slot"] <= j]
        plan = {}
        for lab in F:
            plan[lab] = {}
            for i in pilot:
                if i == IDX_1595:
                    continue
                av = avail(i, lab)
                L = av[-1]
                refs = [s["key"] for s in hist[i] if Fraction(s["e"]) > Fraction(L["e"])]
                jf = 0 if lab == "Ts" else int(lab[1:])
                assert all(s["slot"] > jf for s in hist[i] if s["key"] in refs), "every reference was fetched after the forecast time"
                plan[lab][str(i)] = {"latest": L["key"], "hist": [s["key"] for s in av], "refs": refs}
        # (H)'s history is fixed by its latest set (assert)
        hl = {}
        for lab in plan:
            for i, d in plan[lab].items():
                k = (i, d["latest"])
                assert hl.setdefault(k, tuple(d["hist"])) == tuple(d["hist"]), "a latest set with two histories"
        rows_n = sum(len(d["refs"]) for lab in plan for d in plan[lab].values())
        distinct = {(i, d["latest"], r) for lab in plan for i, d in plan[lab].items() for r in d["refs"]}
        log.w("# checks for (B') and (R): %d rows over the 5 forecast times, %d distinct (object, latest set, reference)" % (rows_n, len(distinct)))
        for lab in plan:
            log.w("#   %s: %d rows, objects with no reference %d" % (lab, sum(len(d["refs"]) for d in plan[lab].values()),
                                                                  sum(1 for d in plan[lab].values() if not d["refs"])))
        # 1595's sets for its decay reconstruction
        cut = float(H.utc_to_tdb(H.mjd_of(2026, 11, 18), 0))
        s95 = [s["key"] for s in hist[IDX_1595] if Fraction(s["e"]) < Fraction(cut)]
        log.w("# seed index 1595: %d kept sets, %d with epochs before 2026-11-18 00:00 UTC (its decay prediction's)" % (len(hist[IDX_1595]), len(s95)))
        log.check(len(s95) >= 1, "1595 has a set before 2026-11-18 00:00 UTC")
        out = {"ts": ts, "pilot": pilot, "perigee": {str(i): per[i] for i in pilot}, "cat": {str(i): int(seed["rows"][i][0]) for i in pilot},
               "hist": {str(i): hist[i] for i in pilot}, "copies": copies, "F": F, "plan": plan, "s1595": s95, "cut1595": cut,
               "meta": {str(i): meta[i] for i in pilot}, "seed_y": {str(i): seed["rows"][i][3] for i in pilot},
               "seed_bc": {str(i): seed["rows"][i][4] for i in pilot}, "skipped": {str(i): skipped[i] for i in pilot}}
        p = os.path.join(a.work, "plan.json")
        jsave(p, out)
        log.w("# plan.json (ledger) sha256 %s" % H.sha256(p))
    finally:
        pass
    return close_stage(cpu, log, "prep")


# ------------------------------------------------------------------ stage bprime: references, (B'), T2's decodes
def stage_bprime(a):
    cpu, log, W = open_stage(a, "bprime")
    P = jload(os.path.join(a.work, "plan.json"))
    log.w("# plan.json sha256 %s" % H.sha256(os.path.join(a.work, "plan.json")))
    sets = {s["key"]: s for i in P["hist"] for s in P["hist"][i]}
    refkeys = sorted({r for lab in P["plan"] for d in P["plan"][lab].values() for r in d["refs"]}, key=lambda k: (int(k.split("_")[0]), int(k.split("_")[1])))
    items = [("F" + k, sets[k]["row"], [sets[k]["eq"], sets[k]["eq"] + 1.0]) for k in refkeys]
    ref = decode(a, log, items, W, "ref")
    log.check(all(ref.get("F" + k) is not None for k in refkeys), "Orekit decoded every reference (%d)" % len(refkeys))
    lat = sorted({(int(i), d["latest"]) for lab in P["plan"] for i, d in P["plan"][lab].items() if d["refs"]})
    bitems, btargets = [], {}
    for i, L in lat:
        rk = [s["key"] for s in P["hist"][str(i)] if Fraction(s["e"]) > Fraction(sets[L]["e"])]
        btargets[L] = rk
        bitems.append(("B" + L, sets[L]["row"], [sets[k]["eq"] for k in rk]))
    bp = decode(a, log, bitems, W, "bprime")
    log.check(all(bp.get("B" + L) is not None for _, L in lat), "Orekit decoded every latest set (%d)" % len(lat))
    # T2: latest sets that a later slot repeats equal in every field
    t2 = [(L, P["copies"][L][0]) for _, L in lat if L in P["copies"]]
    t2res = {}
    if t2:
        da = decode(a, log, [("T" + L, sets[L]["row"], [sets[L]["eq"]]) for L, _ in t2], W, "t2a")
        db = decode(a, log, [("T" + L, c["row"], [sets[L]["eq"]]) for L, c in t2], W, "t2b")
        nz = sum(1 for L, _ in t2 if da["T" + L][0][:3] != db["T" + L][0][:3])
        log.check(nz == 0, "T2 equal sets: all %d latest sets repeated by a later slot give (B') a miss of exactly 0 (%d do not)" % (len(t2), nz))
        t2res = {L: H.dist(da["T" + L][0][:3], db["T" + L][0][:3]) for L, _ in t2}
    else:
        log.w("# T2: no latest set is repeated by a later slot; the control had nothing to check")
    out = {"ref": {k: ref["F" + k] for k in refkeys}, "bp": {L: dict(zip(btargets[L], bp["B" + L])) for _, L in lat}, "t2": t2res}
    p = os.path.join(a.work, "bprime.json")
    jsave(p, out)
    log.w("# bprime.json (ledger) sha256 %s" % H.sha256(p))
    return close_stage(cpu, log, "bprime")


def rcfg(a):
    return {"java": a.java, "jars": jars_of(a), "orekit": a.orekit, "decoder": a.decoder, "m1f": a.m1f, "table": a.table, "env": menv(a),
            "procs": 1, "jprocs": 1}


# ------------------------------------------------------------------ stage rfit: (R), K1, the planted bc
def stage_rfit(a):
    cpu, log, W = open_stage(a, "rfit")
    P = jload(os.path.join(a.work, "plan.json"))
    log.w("# plan.json sha256 %s" % H.sha256(os.path.join(a.work, "plan.json")))
    sets = {s["key"]: s for i in P["hist"] for s in P["hist"][i]}
    ts = P["ts"]
    seedkeys = ["%d_0" % i for i in P["pilot"]]
    lat = sorted({d["latest"] for lab in P["plan"] for d in P["plan"][lab].values()} - set(seedkeys),
                 key=lambda k: (int(k.split("_")[0]), int(k.split("_")[1])))
    log.w("# (R) fits: the %d seed sets (T_s, with the catch-up to T_s) and %d later latest sets" % (len(seedkeys), len(lat)))
    r0 = KR.refit(rcfg(a), log, [(k, sets[k]["row"]) for k in seedkeys], os.path.join(W, "r_ts"), ts_val=ts)
    r1 = KR.refit(rcfg(a), log, [(k, sets[k]["row"]) for k in lat], os.path.join(W, "r_later")) if lat else {"fits": {}, "singular": set(), "batches": []}
    fits = {}
    for res in (r0, r1):
        for k, ft in res["fits"].items():
            ft = dict(ft)
            ft["singular"] = int(k in res["singular"])
            fits[k] = ft
    log.check(set(fits) == set(seedkeys) | set(lat), "every (R) set has a fit (%d)" % len(fits))
    catch = {k: v for k, v in r0["catch"].items()}
    log.w("# (R) fits flagged (iteration limit or singular): %d of %d" % (sum(flagged(f) for f in fits.values()), len(fits)))
    # predictions at every reference of each latest set
    objs = []
    for k in sorted(fits, key=lambda k: (int(k.split("_")[0]), int(k.split("_")[1]))):
        i = int(k.split("_")[0])
        if i == IDX_1595:
            continue
        rk = [s["key"] for s in P["hist"][str(i)] if Fraction(s["e"]) > Fraction(sets[k]["e"])]
        if not rk:
            continue
        ft = fits[k]
        objs.append(("R" + k, ft["t0"], ft["y"], ft["bc"], H.CRAM, [sets[x]["eq"] for x in rk]))
    pr, _ = m1f_prop(a, log, W, "r", objs)
    pred = {o[0][1:]: {x: st for x, (_, st, _) in zip([s["key"] for s in P["hist"][o[0][1:].split("_")[0]] if Fraction(s["e"]) > Fraction(sets[o[0][1:]]["e"])],
                                                    pr[o[0]])} for o in objs}
    # K1: k_fit's fit on (R)'s first T_s object's 721 observations, with their times, against m1f's FIT line
    k1key = seedkeys[0] if seedkeys[0].split("_")[0] != str(IDX_1595) else seedkeys[1]
    fin = os.path.join(W, "r_ts", "fit_in.00.txt")
    obs, cur, t0k, y0k, fitbck = [], None, None, None, None
    for ln in open(fin, encoding="ascii"):
        p = ln.split()
        if p[0] == "OBJ":
            cur = p[1]
            if cur == k1key:
                t0k = float.fromhex(p[2])
                y0k = [float.fromhex(x) for x in p[3:9]]
                fitbck = int(p[11])
        elif p[0] == "O" and cur == k1key:
            obs.append((t0k + 120.0 * int(p[1]), [float.fromhex(x) for x in p[2:5]]))
    k1 = kfit_fit(a, log, W, "k1", [(k1key, t0k, y0k, fitbck, obs)])
    log.check(len(obs) == 721 and k1[k1key]["line"] == fits[k1key]["line"],
              "K1 k_fit's FIT line equals m1f's, character for character, for seed index %s (%d observations)" % (k1key.split("_")[0], len(obs)))
    # the planted bc: the object, its forecast time and reference
    order = sorted((i for i in P["pilot"] if i != IDX_1595), key=lambda i: P["perigee"][str(i)])
    chosen = None
    tried = []
    for i in order:
        for lab in ["Ts"] + ["s%02d" % j for j in FT_SLOTS]:
            d = P["plan"][lab][str(i)]
            Ft = P["F"][lab]
            cand = sorted((sets[r]["eq"], r) for r in d["refs"] if 12 * 3600.0 <= Fraction(sets[r]["e"]) - Fraction(Ft) <= 36 * 3600.0)
            if not cand:
                continue
            eqr, rkey = cand[0]
            L = d["latest"]
            ft = fits[L]
            dec = kfit_decay(a, log, W, "plant_check_%d" % i, [("D" + L, ft["t0"], ft["y"], ft["bc"], H.CRAM, eqr)])["D" + L]
            tried.append((i, lab, dec[0]))
            if dec[0] == "LIVE":
                chosen = (i, lab, L, rkey, eqr)
            break
        if chosen:
            break
    log.w("# planted bc: candidates tried (seed index, forecast time, M1 to the reference): %s" % "; ".join("%d %s %s" % t for t in tried))
    plant = {}
    if log.check(chosen is not None, "planted bc: an object qualifies"):
        i, lab, L, rkey, eqr = chosen
        ft = fits[L]
        pp, _ = m1f_prop(a, log, W, "plant_pipeline", [("R" + L, ft["t0"], ft["y"], ft["bc"], H.CRAM, [eqr])], bc_scale={"R" + L: 2.0})
        # the direct run: written here by hand, not through m1f_prop
        din, dout = os.path.join(W, "plant_direct_in.txt"), os.path.join(W, "plant_direct_out.txt")
        with open(din, "w", newline="\n") as f:
            f.write("OBJ %s %s %s %s %s 0 0 1\n" % ("R" + L, float.hex(ft["t0"]), " ".join(float.hex(x) for x in ft["y"]), float.hex(2.0 * ft["bc"]), float.hex(H.CRAM)))
            f.write("T 0 %s\n" % float.hex(eqr))
        H.run([a.m1f, "prop", "native64", a.table, din, dout], log, env=menv(a))
        dl = [ln.split() for ln in open(dout, encoding="ascii") if ln.startswith("P ")]
        pT, pst, phx = pp["R" + L][0]
        same = (len(dl) == 1 and dl[0][1] == "R" + L and float.fromhex(dl[0][2]) == pT and [float.fromhex(x) for x in dl[0][3:9]] == pst
                and dl[0][9:15] == phx)
        moved = H.dist(pp["R" + L][0][1][:3], pred[L][rkey][:3])
        log.check(same, "PLANTED BC (seed index %d, %s, reference %.2f h after it): the pipeline's state with bc doubled equals m1f prop run directly, bit for bit" % (
            i, lab, (eqr - P["F"][lab]) / 3600.0))
        log.check(moved >= 100.0, "PLANTED BC: the doubled bc moves the predicted position at that reference by %.1f m (at least 100 m)" % moved)
        plant = {"idx": i, "lab": lab, "latest": L, "ref": rkey, "moved_m": moved, "bc": ft["bc"]}
    out = {"fits": fits, "catch": catch, "pred": pred, "plant": plant, "batches": [b for r in (r0, r1) for b in r["batches"]]}
    p = os.path.join(a.work, "rfit.json")
    jsave(p, out)
    log.w("# rfit.json (ledger) sha256 %s" % H.sha256(p))
    return close_stage(cpu, log, "rfit")


# ------------------------------------------------------------------ stage hfit: (H) and the planted identity
def h_grid(sets, keys):
    """(H)'s rule: the grid O_H + 120 k to the last grid time at or before e_q(latest); each time from the earliest set
    whose e_q is at or after it. Returns O_H and [(key, [times])] in set order."""
    eqs = [sets[k]["eq"] for k in keys]
    OH = eqs[0] - DAY
    K = int((Fraction(eqs[-1]) - Fraction(OH)) // 120)
    assign = {k: [] for k in keys}
    n = 0
    for k in range(K + 1):
        g = OH + 120.0 * k
        assert Fraction(g) == Fraction(OH) + 120 * k
        while eqs[n] < g:
            n += 1
        assign[keys[n]].append(g)
    return OH, [(k, assign[k]) for k in keys if assign[k]]


def stage_hfit(a):
    cpu, log, W = open_stage(a, "hfit")
    P = jload(os.path.join(a.work, "plan.json"))
    R = jload(os.path.join(a.work, "rfit.json"))
    log.w("# plan.json sha256 %s; rfit.json sha256 %s" % (H.sha256(os.path.join(a.work, "plan.json")), H.sha256(os.path.join(a.work, "rfit.json"))))
    sets = {s["key"]: s for i in P["hist"] for s in P["hist"][i]}
    hs = [int(x) for x in a.h_times.split(",")]
    log.w("# (H)'s forecast times: slots %s" % ", ".join(str(j) for j in hs))
    hists = {}
    for j in hs:
        for i, d in P["plan"]["s%02d" % j].items():
            hists[d["latest"]] = d["hist"]
    hists["1595_h"] = P["s1595"]
    keys = sorted(hists, key=lambda k: (int(k.split("_")[0]), 10 ** 6 if k.endswith("_h") else int(k.split("_")[1])))
    items, grids = [], {}
    for L in keys:
        OH, parts = h_grid(sets, hists[L])
        grids[L] = (OH, parts)
        for k, tt in parts:
            items.append(("H%s.%s" % (L, k), sets[k]["row"], tt))
    span = {L: (sets[hists[L][-1]]["eq"] - grids[L][0]) / DAY for L in keys}
    log.w("# (H) fits: %d distinct histories; sets in the fit from %d to %d; spans from %.2f to %.2f days" % (
        len(keys), min(len(hists[L]) for L in keys), max(len(hists[L]) for L in keys), min(span.values()), max(span.values())))
    pv = decode(a, log, items, W, "h")
    log.check(all(pv.get(it[0]) is not None for it in items), "Orekit decoded every set of every history")
    objs = []
    for L in keys:
        OH, parts = grids[L]
        obs = []
        for k, tt in parts:
            st = pv["H%s.%s" % (L, k)]
            obs += [(t, s[:3]) for t, s in zip(tt, st)]
        first = pv["H%s.%s" % (L, parts[0][0])][0]
        fitbc = 1 if H.perigee_alt_km_f(sets[hists[L][-1]]["row"]) < 1000.0 else 0
        objs.append(("H" + L, OH, first, fitbc, obs))
    fits = kfit_fit(a, log, W, "h", objs)
    fits = {k[1:]: v for k, v in fits.items()}
    log.w("# (H) fits flagged (iteration limit or singular): %d of %d" % (sum(flagged(f) for f in fits.values()), len(fits)))
    pobjs = []
    for L in keys:
        if L.endswith("_h"):
            continue
        i = L.split("_")[0]
        rk = [s["key"] for s in P["hist"][i] if Fraction(s["e"]) > Fraction(sets[L]["e"])]
        if rk:
            ft = fits[L]
            pobjs.append(("H" + L, ft["t0"], ft["y"], ft["bc"], H.CRAM, [sets[x]["eq"] for x in rk]))
    pr, _ = m1f_prop(a, log, W, "h", pobjs)
    pred = {}
    for o in pobjs:
        L = o[0][1:]
        rk = [s["key"] for s in P["hist"][L.split("_")[0]] if Fraction(s["e"]) > Fraction(sets[L]["e"])]
        pred[L] = {x: st for x, (_, st, _) in zip(rk, pr[o[0]])}
    # the planted identity: X's references from slot 5, predicted by Y's (H) fit at slot 5
    ident = {}
    if 5 in hs and R.get("plant"):
        X = R["plant"]["idx"]
        dx = P["plan"]["s05"][str(X)]
        nX = float(sets[dx["latest"]]["row"]["MEAN_MOTION"])
        cyc = [i for i in P["pilot"] if i != IDX_1595]
        k0 = cyc.index(X)
        Y = None
        for s in range(1, len(cyc)):
            c = cyc[(k0 + s) % len(cyc)]
            if abs(float(sets[P["plan"]["s05"][str(c)]["latest"]]["row"]["MEAN_MOTION"]) - nX) > 1e-3:
                Y = c
                break
        if log.check(Y is not None and dx["refs"], "planted identity: X = seed index %s has references from slot 5 (%d); Y = seed index %s" % (
                X, len(dx["refs"]), Y)):
            LY = P["plan"]["s05"][str(Y)]["latest"]
            fy = fits[LY]
            refused = bool(flagged(fy) and fy.get("singular")) or not all(math.isfinite(x) for x in fy["y"])
            pi, _ = m1f_prop(a, log, W, "ident", [("I" + LY, fy["t0"], fy["y"], fy["bc"], H.CRAM, [sets[x]["eq"] for x in dx["refs"]])])
            ident = {"X": X, "Y": Y, "refs": dx["refs"], "pos": [st for _, st, _ in pi["I" + LY]], "refused": refused}
    out = {"fits": fits, "pred": pred, "hists": hists, "ident": ident, "span": span}
    p = os.path.join(a.work, "hfit.json")
    jsave(p, out)
    log.w("# hfit.json (ledger) sha256 %s" % H.sha256(p))
    return close_stage(cpu, log, "hfit")


# ------------------------------------------------------------------ stage decay
def stage_decay(a):
    cpu, log, W = open_stage(a, "decay")
    P = jload(os.path.join(a.work, "plan.json"))
    R = jload(os.path.join(a.work, "rfit.json"))
    Hf = jload(os.path.join(a.work, "hfit.json"))
    log.w("# plan.json %s; rfit.json %s; hfit.json %s (sha256)" % tuple(H.sha256(os.path.join(a.work, f)) for f in ("plan.json", "rfit.json", "hfit.json")))
    who = sorted(i for i in P["pilot"] if (P["perigee"][str(i)] < 300e3 or i == IDX_1178) and i != IDX_1595)
    log.w("# decay predictions for seed indices %s (perigee under 300 km, and 1178), and 1595's reconstruction" % ", ".join(str(i) for i in who))
    runs = {}
    for i in who:
        for lab in P["plan"]:
            L = P["plan"][lab][str(i)]["latest"]
            runs.setdefault(("R", L), []).append(lab)
            if lab in ("s%02d" % j for j in [5, 9, 13]) and L in Hf["fits"]:
                runs.setdefault(("H", L), []).append(lab)
    objs = []
    for (v, L), labs in sorted(runs.items()):
        ft = R["fits"][L] if v == "R" else Hf["fits"][L]
        tend = max(P["F"][x] for x in labs) + 30 * DAY
        objs.append((v + L, ft["t0"], ft["y"], ft["bc"], H.CRAM, tend))
    k95 = P["s1595"][-1]
    objs.append(("R" + k95, R["fits"][k95]["t0"], R["fits"][k95]["y"], R["fits"][k95]["bc"], H.CRAM, P["ts"] + 30 * DAY))
    objs.append(("H1595_h", Hf["fits"]["1595_h"]["t0"], Hf["fits"]["1595_h"]["y"], Hf["fits"]["1595_h"]["bc"], H.CRAM, P["ts"] + 30 * DAY))
    res = kfit_decay(a, log, W, "decay", objs)
    out = {"runs": {v + L: labs for (v, L), labs in runs.items()}, "res": res, "k95": k95}
    p = os.path.join(a.work, "decay.json")
    jsave(p, out)
    log.w("# decay.json (ledger) sha256 %s" % H.sha256(p))
    return close_stage(cpu, log, "decay")


# ------------------------------------------------------------------ stage cfit: (C), DEBRIS-F's route (C) with (R)'s rule
C_CHECK_LO = "2026-11-01T00:00:00"   # tests/k_swcheck.py's span (its log must PASS before this stage runs)
C_CHECK_HI = "2026-11-22T00:00:00"
C_FILL0_SHA = "47acbcc2c5bb5bb8c6425d0f7873e77a82f44d57cac5c655bdf6ae05a2c88c9a"


def utc_iso_to_tdb(s):
    d, t = s.split("T")
    y, mo, dd = (int(x) for x in d.split("-"))
    hh, mi, ss = (int(x) for x in t.split(":"))
    return float(H.utc_to_tdb(H.mjd_of(y, mo, dd), hh * 3600 + mi * 60 + ss))


def read_fit_in(path):
    """(R)'s fit input (k_refit.py's): {key: (O, y0[6], [(k, pos3)])}"""
    out, cur = {}, None
    for ln in open(path, encoding="ascii"):
        q = ln.split()
        if q[0] == "OBJ":
            cur = q[1]
            out[cur] = (float.fromhex(q[2]), [float.fromhex(x) for x in q[3:9]], [])
        elif q[0] == "O":
            out[cur][2].append((int(q[1]), [float.fromhex(x) for x in q[2:5]]))
    return out


def stage_cfit(a):
    cpu, log, W = open_stage(a, "cfit")
    P = jload(os.path.join(a.work, "plan.json"))
    R = jload(os.path.join(a.work, "rfit.json"))
    log.w("# plan.json %s; rfit.json %s (sha256)" % (H.sha256(os.path.join(a.work, "plan.json")), H.sha256(os.path.join(a.work, "rfit.json"))))
    js = os.path.join(os.path.dirname(SCRIPT), "k_orekit_fit.js")
    log.w("# k_orekit_fit.js sha256 %s" % H.keep_version(js, a.keep))
    swp = os.path.join(a.c_data, "SW-Last5Years.txt")
    log.check(H.sha256(swp) == C_FILL0_SHA, "(C)'s folder holds the 0-filled copy, 47acbcc2...c9a (tests/k_swcopy.py)")
    for f in sorted(os.listdir(a.c_data)):
        log.w("# (C) data %s sha256 %s" % (f, H.sha256(os.path.join(a.c_data, f))))
    log.w("# (C) gravity %s sha256 %s; DE421 folder %s" % (os.listdir(a.c_gfc), H.sha256(os.path.join(a.c_gfc, "EIGEN6-C4.gfc")), os.listdir(a.c_de)))
    sets = {s_["key"]: s_ for i in P["hist"] for s_ in P["hist"][i]}
    fin = {}
    for sub in ("r_ts", "r_later"):
        pth = os.path.join(W, sub, "fit_in.00.txt")
        if os.path.exists(pth):
            log.w("# (R)'s pseudo-observations %s/fit_in.00.txt sha256 %s" % (sub, H.sha256(pth)))
            fin.update(read_fit_in(pth))
    keys = sorted((k for k in R["pred"]), key=lambda k: (int(k.split("_")[0]), int(k.split("_")[1])))
    los, his, items = [], [], []
    for L in keys:
        O, y0, obs = fin[L]
        assert O == R["fits"][L]["t0"] and len(obs) == H.NOBS
        rk = list(R["pred"][L].keys())
        rk.sort(key=lambda k: sets[k]["eq"])
        items.append((L, O, y0, obs, rk))
        los.append(O - 60 * 3600.0)
        his.append(max(sets[k]["eq"] for k in rk))
    lo, hi = min(los), max(his)
    c_lo, c_hi = utc_iso_to_tdb(C_CHECK_LO), utc_iso_to_tdb(C_CHECK_HI)
    ok_span = log.check(c_lo <= lo and hi <= c_hi, "(C)'s dates, 60 h of ap history included, lie inside the two-fill check's span (%s to %s UTC)" % (
        utc_label(lo), utc_label(hi)))
    log.check(hi < utc_iso_to_tdb("2026-12-30T00:00:00"), "(C) evaluates no density after 2026-12-30")
    out = {}
    if ok_span:
        cin, cout = os.path.join(W, "c_in.txt"), os.path.join(W, "c_out.txt")
        with open(cin, "w", newline="\n") as f:
            for L, O, y0, obs, rk in items:
                f.write("OBJ %s %s %s %d %d\n" % (L, H.tai_hex(O), " ".join(float.hex(x) for x in y0), len(obs), len(rk)))
                for k, q in obs:
                    f.write("O %d %s %s\n" % (k, H.tai_hex(O + 120.0 * k), " ".join(float.hex(x) for x in q)))
                for j, k in enumerate(rk):
                    f.write("T %d %s\n" % (j, H.tai_hex(sets[k]["eq"])))
        log.w("# (C) input: %d fits, %d targets, sha256 %s; the JVM's own CPU limit %s s" % (len(items), sum(len(x[4]) for x in items), H.sha256(cin), a.c_limit))
        H.run(H.java_argv(a.java, jars_of(a), js, [cin, cout, a.c_data, a.c_gfc, a.c_de, a.c_limit]), log)
        res, refused = {}, []
        for ln in open(cout, encoding="ascii"):
            q = ln.split()
            if q and q[0] == "C":
                res.setdefault(q[1], {})[int(q[2])] = ([float.fromhex(x) for x in q[3:6]], int(q[6]), float.fromhex(q[7]), float.fromhex(q[8]))
            elif q and q[0] == "X":
                refused.append(q[1])
            elif ln.startswith("#"):
                log.w("# (C) " + ln.strip())
        for L, O, y0, obs, rk in items:
            if L in res:
                assert sorted(res[L]) == list(range(len(rk)))
                out[L] = {"pos": {k: res[L][j][0] for j, k in enumerate(rk)}, "iters": res[L][0][1], "cd": res[L][0][2], "rms": res[L][0][3]}
        log.w("# (C) fitted and propagated %d of %d; refused by Orekit %d" % (len(out), len(items), len(refused)))
        cds = sorted(v["cd"] for v in out.values())
        if cds:
            log.w("# (C) fitted Cd: from %.3g to %.3g, median %.3g; negative in %d; post-fit RMS median %.1f m" % (
                cds[0], cds[-1], H.median(cds), sum(1 for c in cds if c < 0), H.median([v["rms"] for v in out.values()])))
    pth = os.path.join(a.work, "cfit.json")
    jsave(pth, {"fits": out})
    log.w("# cfit.json (ledger) sha256 %s" % H.sha256(pth))
    return close_stage(cpu, log, "cfit")


# ------------------------------------------------------------------ stage stats
def cell_of(h):
    for nm, lo, hi in CELLS:
        if lo <= h < hi:
            return nm
    raise ValueError(h)


def stat_lines(log, label, rows, flagged_note):
    """rows: dicts with m, A (signed along-track), h; logs the overall and per-cell statistics"""
    def one(name, rr):
        if not rr:
            log.w("MEASURED %s %s, %s: n 0" % (label, name, flagged_note))
            return
        m = sorted(r["m"] for r in rr)
        aa = sorted(abs(r["A"]) for r in rr)
        sa = sorted(r["A"] for r in rr)
        if len(rr) < 5:
            log.w("MEASURED %s %s, %s: n %d, median %.3f km" % (label, name, flagged_note, len(rr), H.median(m) / 1e3))
        else:
            log.w("MEASURED %s %s, %s: n %d, median %.3f km, 90th %.3f km; |along| median %.3f km, 90th %.3f km; signed along median %.3f km" % (
                label, name, flagged_note, len(rr), H.median(m) / 1e3, H.quant(m, 0.9) / 1e3, H.median(aa) / 1e3, H.quant(aa, 0.9) / 1e3, H.median(sa) / 1e3))
    one("overall", rows)
    for nm, lo, hi in CELLS:
        one("horizon " + nm, [r for r in rows if lo <= r["h"] < hi])


def stage_stats(a):
    cpu, log, W = open_stage(a, "stats")
    files = ["plan.json", "bprime.json", "rfit.json", "hfit.json", "decay.json"]
    D = {}
    for f in files:
        p = os.path.join(a.work, f)
        D[f] = jload(p)
        log.w("# %s (ledger) sha256 %s" % (f, H.sha256(p)))
    P, B, R, Hf, DC = (D[f] for f in files)
    cp = os.path.join(a.work, "cfit.json")
    Cf = jload(cp)["fits"] if os.path.exists(cp) else {}
    log.w("# cfit.json %s" % (("(ledger) sha256 %s, %d fits" % (H.sha256(cp), len(Cf))) if os.path.exists(cp) else "absent: (C) not run"))
    sets = {s["key"]: s for i in P["hist"] for s in P["hist"][i]}
    ref = B["ref"]
    hslots = ["s%02d" % int(j) for j in a.h_times.split(",")]
    rows, seen = [], set()
    t1bad = nt1 = 0
    for lab in P["plan"]:
        for i, d in sorted(P["plan"][lab].items(), key=lambda x: int(x[0])):
            L = d["latest"]
            for rk in d["refs"]:
                rs = ref[rk]
                base = {"F": lab, "idx": int(i), "used": L, "nsets": len(d["hist"]), "ref": rk, "ref_slot": sets[rk]["slot"],
                        "h": float(Fraction(sets[rk]["e"]) - Fraction(sets[L]["e"])) / 3600.0}
                for v, pos, fl in (("B'", B["bp"][L][rk], 0), ("R", R["pred"][L][rk], flagged(R["fits"][L])),
                                   ("H", Hf["pred"].get(L, {}).get(rk) if lab in hslots else None, flagged(Hf["fits"][L]) if L in Hf["fits"] else 0),
                                   ("C", Cf[L]["pos"].get(rk) if L in Cf else None, 0)):
                    if pos is None:
                        continue
                    dm, rc, err, vn = miss(pos, rs[0], rs[1])
                    key = (v, int(i), L, rk)
                    first = key not in seen
                    seen.add(key)
                    if first:
                        nt1 += 1
                        if not err <= 0.01 * vn:
                            t1bad += 1
                    r = dict(base)
                    r.update({"v": v, "m": dm, "R": rc[0], "A": rc[1], "C": rc[2], "flag": fl, "distinct": int(first), "pos": pos})
                    rows.append(r)
    log.check(nt1 > 0 and t1bad == 0, "T1 the time tag: all %d distinct check-variants moved by v x 1 s within 1%% of |v| (%d do not)" % (nt1, t1bad))
    # T2's result was asserted in stage bprime; restated
    log.w("# T2 (stage bprime): %d latest sets repeated by a later slot, largest miss %s m" % (len(B["t2"]), ("%.3g" % max(B["t2"].values())) if B["t2"] else "-"))
    # T3 per forecast time and reference slot, over (B')
    t3n = t3bad = 0
    exc = []
    for lab in P["plan"]:
        bl = [r for r in rows if r["F"] == lab and r["v"] == "B'"]
        for js in sorted({r["ref_slot"] for r in bl}):
            g = sorted([r for r in bl if r["ref_slot"] == js], key=lambda r: (r["idx"], r["ref"]))
            n = len(g)
            for q, r in enumerate(g):
                nn = float(sets[r["ref"]]["row"]["MEAN_MOTION"])
                j = (q + 1) % n
                while g[j] is not r and abs(float(sets[g[j]["ref"]]["row"]["MEAN_MOTION"]) - nn) <= 1e-3:
                    j = (j + 1) % n
                if g[j] is r:
                    continue
                o = g[j]
                ang = angle_deg(normal(ref[r["ref"]][0]), normal(ref[o["ref"]][0]))
                if ang <= 0.1:
                    exc.append((lab, js, r["idx"], o["idx"], ang))
                    continue
                t3n += 1
                if not H.dist(r["pos"][:3], ref[o["ref"]][0][:3]) > 100e3:
                    t3bad += 1
    log.check(t3n > 0 and t3bad == 0, "T3 swapped identities: %d (B') checks compared, %d within 100 km; co-planar exceptions (within 0.1 deg) %d" % (t3n, t3bad, len(exc)))
    for e in exc:
        log.w("#   T3 exception: %s, reference slot %d, seed index %d against %d, planes %.4f deg apart" % e)
    # K2: (B') at T_s and the references against DEBRIS-H's check tables
    cat2i = {v: int(k) for k, v in P["cat"].items()}
    tab = []
    cdir = os.path.join(a.r2, "svc", "checks")
    for f in sorted(os.listdir(cdir)):
        if not (f.startswith("slot") and f.endswith(".tsv")):
            continue
        log.w("# check table %s sha256 %s" % (f, H.sha256(os.path.join(cdir, f))))
        head = None
        for ln in open(os.path.join(cdir, f), encoding="ascii"):
            if ln.startswith("#"):
                continue
            q = ln.rstrip("\n").split("\t")
            if head is None:
                head = q
                continue
            d = dict(zip(head, q))
            if d["status"] == "checked" and int(d["cat"]) in cat2i:
                d["slot"] = int(f[4:6])
                tab.append(d)
    log.w("# check-table rows of pilot objects (status checked): %d, over %d objects" % (len(tab), len({d["idx"] for d in tab})))
    k2n = k2bad = 0
    k2max = 0.0
    for d in tab:
        i = cat2i[int(d["cat"])]
        assert int(d["idx"]) == i
        mk = [s["key"] for s in P["hist"][str(i)] if s["row"]["EPOCH"] == d["new_epoch"]]
        if not mk:
            k2bad += 1
            en = H.epoch_tdb({"EPOCH": d["new_epoch"]})
            later_kept = [s for s in P["hist"][str(i)] if Fraction(s["e"]) > en and s["slot"] < d["slot"]]
            log.w("#   K2 unmatched: seed index %d, check-table slot %d: no kept set has its epoch; kept sets with later epochs fetched before that slot: %d (from slots %s)" % (
                i, d["slot"], len(later_kept), ", ".join(str(s["slot"]) for s in later_kept) or "-"))
            continue
        rk = mk[0]
        eqt = float.fromhex(d["e_q"])
        bpos = [float.fromhex(x) for x in d["B_pos"].split(",")]
        rst = [float.fromhex(x) for x in d["ref_state"].split(",")]
        mine_b = B["bp"]["%d_0" % i][rk]
        mine_r = ref[rk][0]
        dd = max(H.dist(bpos[:3], mine_b[:3]), H.dist(rst[:3], mine_r[:3]))
        k2max = max(k2max, dd)
        k2n += 1
        if not (eqt == sets[rk]["eq"] and dd <= 1e-3):
            k2bad += 1
    log.check(k2n > 0 and k2bad == 0, "K2 (B') at T_s and the references equal DEBRIS-H's within 1e-3 m and e_q equal: %d rows, %d not; largest %.3g m" % (
        k2n, k2bad, k2max))
    # the planted identity
    ident = Hf.get("ident") or {}
    dist_h = [r for r in rows if r["v"] == "H" and r["distinct"]]
    medH = H.median([r["m"] for r in dist_h]) if dist_h else float("nan")
    if ident:
        X = ident["X"]
        ms = []
        for rk, pos in zip(ident["refs"], ident["pos"]):
            ms.append(miss(pos, ref[rk][0], ref[rk][1])[0])
        ok = ident["refused"] or (ms and min(ms) > 10 * medH)
        log.check(bool(ok), "PLANTED IDENTITY: (H) for seed index %d fitted to seed index %d's sets at slot 5: %d misses, smallest %.1f km, against 10 x (H)'s median %.3f km%s" % (
            X, ident["Y"], len(ms), min(ms) / 1e3 if ms else float("nan"), 10 * medH / 1e3, " (refused)" if ident["refused"] else ""))
    else:
        log.check(False, "PLANTED IDENTITY: not run")
    # (A) and (B) from the tables
    for d in tab:
        i = cat2i[int(d["cat"])]
        fl = int(int(d["flags1"]) & 3 != 0)
        for v, col in (("A64", "A64"), ("A256", "A256"), ("B", "B")):
            rows.append({"v": v, "F": "seed", "idx": i, "used": "%d_0" % i, "nsets": 1, "ref": d["new_epoch"], "ref_slot": d["slot"], "h": float(d["horizon_h"]),
                         "m": float(d[col + "_m"]), "R": float(d[col + "_R"]), "A": float(d[col + "_A"]), "C": float(d[col + "_C"]), "flag": fl, "distinct": 1,
                         "pos": [float.fromhex(x) for x in d[col + "_pos"].split(",")]})
    # the skipped rows' kinds, from the slot folders again (a description of the data, no pass condition)
    fetch = os.path.join(a.r2, "svc", "fetch")
    kinds = {"same_epoch_other_fields": 0, "older_epoch": 0, "copy": 0}
    byobj = {}
    for j in range(1, 21):
        if not os.path.isdir(os.path.join(fetch, "slot%02d" % j)):
            continue
        for g, (pth, rg) in sorted(H.read_slot(fetch, j).items()):
            for r in rg:
                c = int(r["NORAD_CAT_ID"])
                if r["EPHEMERIS_TYPE"] != "0" or c not in cat2i:
                    continue
                i = cat2i[c]
                kept = [s for s in P["hist"][str(i)] if s["slot"] <= j]
                if any(s["row"]["EPOCH"] == r["EPOCH"] and all(r[x] == s["row"][x] for x in H.COLUMNS) for s in kept):
                    if not any(s["slot"] == j and s["row"]["EPOCH"] == r["EPOCH"] for s in kept):
                        kinds["copy"] += 1
                    continue
                if any(s["row"]["EPOCH"] == r["EPOCH"] for s in kept):
                    if not any(s["slot"] == j and s["row"]["EPOCH"] == r["EPOCH"] for s in kept):
                        kinds["same_epoch_other_fields"] += 1
                        byobj.setdefault(i, [0, 0])[0] += 1
                    continue
                if H.epoch_tdb(r) < Fraction(kept[-1]["e"]):
                    kinds["older_epoch"] += 1
                    byobj.setdefault(i, [0, 0])[1] += 1
    log.w("MEASURED the slot rows of pilot objects not kept: %s; by seed index (same epoch, other fields; an older epoch again): %s" % (
        kinds, "; ".join("%d: %d, %d" % (i, v[0], v[1]) for i, v in sorted(byobj.items())) or "none"))
    # the statistics
    pilot = [i for i in P["pilot"] if i != IDX_1595]
    log.w("# new sets per object after the seed's (seed index: count): %s" % ", ".join("%d: %d" % (i, len(P["hist"][str(i)]) - 1) for i in P["pilot"]))
    none = [i for i in pilot if len(P["hist"][str(i)]) == 1]
    log.w("# objects with no new set (their (R) is the seed set's refit, and they have no reference): %s" % (", ".join(str(i) for i in none) or "none"))
    for v in ("A64", "A256", "B", "B'", "R", "H", "C"):
        dv = [r for r in rows if r["v"] == v and r["distinct"]]
        stat_lines(log, "(%s)" % v, dv, "flagged fits in")
        stat_lines(log, "(%s)" % v, [r for r in dv if not r["flag"]], "without flagged fits")
    # main comparisons, cell by cell, on the same checks
    for v in ("R", "H", "C"):
        dv = {(r["idx"], r["used"], r["ref"]): r for r in rows if r["v"] == v and r["distinct"]}
        db = {(r["idx"], r["used"], r["ref"]): r for r in rows if r["v"] == "B'" and r["distinct"]}
        common = sorted(set(dv) & set(db))
        log.check(len(common) == len(dv) and (len(dv) > 0 or v == "C"), "(%s)'s checks are all (B') checks (%d)" % (v, len(dv)))
        for nm, lo, hi in [("overall", -1, 1e99)] + CELLS:
            cc = [k for k in common if lo <= dv[k]["h"] < hi]
            if not cc:
                log.w("MEASURED (%s) against (B'), horizon %s: n 0" % (v, nm))
                continue
            mv = H.median([dv[k]["m"] for k in cc])
            mb = H.median([db[k]["m"] for k in cc])
            less = sum(1 for k in cc if dv[k]["m"] < db[k]["m"])
            log.w("MEASURED (%s) against (B'), horizon %s, flagged fits in: n %d, medians %.3f km and %.3f km; (%s) misses less in %d of %d (%.3f)" % (
                v, nm, len(cc), mv / 1e3, mb / 1e3, v, less, len(cc), less / len(cc)))
    ab = [r for r in rows if r["v"] in ("A64", "B")]
    pa = {(r["idx"], r["ref"]): r for r in ab if r["v"] == "A64"}
    pb = {(r["idx"], r["ref"]): r for r in ab if r["v"] == "B"}
    less = sum(1 for k in pa if pa[k]["m"] < pb[k]["m"])
    log.w("MEASURED (A64) against (B) on these objects' check-table rows: n %d; (A64) misses less in %d (DEBRIS-H's restated)" % (len(pa), less))
    # per object
    for v in ("A64", "B", "B'", "R", "H", "C"):
        for i in pilot:
            dv = sorted(r["m"] for r in rows if r["v"] == v and r["distinct"] and r["idx"] == i)
            if not dv:
                continue
            if len(dv) < 5:
                log.w("MEASURED per object (%s) idx %d, all horizons, flagged in: n %d, median %.3f km" % (v, i, len(dv), H.median(dv) / 1e3))
            else:
                log.w("MEASURED per object (%s) idx %d, all horizons, flagged in: n %d, median %.3f km, 90th %.3f km" % (v, i, len(dv), H.median(dv) / 1e3, H.quant(dv, 0.9) / 1e3))
    # the learning curve
    hb = {(r["idx"], r["used"], r["ref"]): r for r in rows if r["v"] == "B'" and r["distinct"]}
    for nm, lo, hi in LC_BINS:
        cc = [r for r in rows if r["v"] == "H" and r["distinct"] and 12.0 <= r["h"] <= 36.0 and lo <= r["nsets"] <= hi]
        if not cc:
            log.w("MEASURED (H) learning curve, horizons 12 to 36 h, sets in the fit %s: n 0" % nm)
            continue
        mb = H.median([hb[(r["idx"], r["used"], r["ref"])]["m"] for r in cc])
        log.w("MEASURED (H) learning curve, horizons 12 to 36 h, sets in the fit %s: n %d, (H) median %.3f km; (B') on the same checks %.3f km; flagged in" % (
            nm, len(cc), H.median([r["m"] for r in cc]) / 1e3, mb / 1e3))
    # desktop refits of the seed sets against the box's seed fits
    boxp = os.path.join(a.r2, "seed", "fit1.001.tsv")
    log.w("# the box's seed fits %s sha256 %s" % (os.path.basename(boxp), H.sha256(boxp)))
    box = KR_read_fit_table(boxp)
    dif = []
    for i in P["pilot"]:
        c = P["cat"][str(i)]
        bx = box[c]
        ft = R["fits"]["%d_0" % i]
        yb = [float.fromhex(x) for x in bx["y_O"].split(",")]
        yt = [float.fromhex(x) for x in bx["y_Ts"].split(",")] if bx["y_Ts"] != "-" else None
        ct = R["catch"].get("%d_0" % i)
        dpos = H.dist(ft["y"][:3], yb[:3])
        dvel = H.dist(ft["y"][3:6], yb[3:6])
        dts = H.dist(ct[1][:3], yt[:3]) if (ct and ct[1] and yt) else float("nan")
        dif.append((i, int(bx["conv"]) == ft["conv"] and int(bx["iter"]) == ft["iter"], dpos, dvel, ft["bc"] - float.fromhex(bx["bc"]), dts))
    log.w("MEASURED desktop refits of the %d seed sets against the box's: convergence and iterations equal in %d; |dr(O)| median %.3g m, largest %.3g m; |dv(O)| largest %.3g m/s; |dbc| largest %.3g m^2/kg; |dr(T_s)| median %.3g m, largest %.3g m" % (
        len(dif), sum(1 for d in dif if d[1]), H.median([d[2] for d in dif]), max(d[2] for d in dif), max(d[3] for d in dif), max(abs(d[4]) for d in dif),
        H.median([d[5] for d in dif if not math.isnan(d[5])]), max(d[5] for d in dif if not math.isnan(d[5]))))
    for d in dif:
        log.w("#   seed index %d: conv/iter equal %s, |dr(O)| %.3g m, |dv(O)| %.3g m/s, dbc %.3g, |dr(T_s)| %.3g m" % (d[0], d[1], d[2], d[3], d[4], d[5]))
    # (R) at T_s against (A64), common checks
    ra = []
    for r in rows:
        if r["v"] == "R" and r["F"] == "Ts" and r["distinct"]:
            m = [x for x in rows if x["v"] == "A64" and x["idx"] == r["idx"] and x["ref"] == sets[r["ref"]]["row"]["EPOCH"]]
            if m:
                ra.append((abs(r["m"] - m[0]["m"]), H.dist(r["pos"][:3], m[0]["pos"][:3]), r["h"]))
    if ra:
        log.w("MEASURED (R) at T_s against (A64) on %d common checks: |d miss| median %.3f m, largest %.3f m; |d position| median %.3f m, largest %.3f m" % (
            len(ra), H.median([x[0] for x in ra]), max(x[0] for x in ra), H.median([x[1] for x in ra]), max(x[1] for x in ra)))
    # the decay predictions
    res = DC["res"]
    sat_lo = float(H.utc_to_tdb(H.mjd_of(2026, 11, 18), 0))
    sat_hi = float(H.utc_to_tdb(H.mjd_of(2026, 11, 19), 0))
    for key, labs in sorted(DC["runs"].items(), key=lambda kv: (int(kv[0][1:].split("_")[0]), kv[0])):
        v, L = key[0], key[1:]
        i = int(L.split("_")[0])
        kind, step, t, rr = res[key]
        nsets = len(Hf["hists"][L]) if v == "H" else 1
        for lab in labs:
            Ft = P["F"][lab]
            within = kind == "DECAY" and t <= Ft + 30 * DAY
            txt = ("decays at %s (%.2f h after the forecast time)" % (utc_label(t), (t - Ft) / 3600.0)) if within else "no decay within 30 days of the forecast time"
            log.w("MEASURED decay (%s) seed index %d, forecast time %s, sets used %d (latest %.2f h before the forecast time), M1's rule (RMIN 6,498,137.0 m): %s; fit %s" % (
                v, i, lab, nsets, (Ft - sets[L]["eq"]) / 3600.0, txt, "flagged" if flagged((R["fits"] if v == "R" else Hf["fits"])[L]) else "converged"))
    for key in ("R" + DC["k95"], "H1595_h"):
        kind, step, t, rr = res[key]
        if kind == "DECAY":
            rel = "within" if sat_lo <= t < sat_hi else ("%.2f h before" % ((sat_lo - t) / 3600.0) if t < sat_lo else "%.2f h after" % ((t - sat_hi) / 3600.0))
            log.w("MEASURED decay reconstruction (%s) seed index 1595 from %d set(s) with epochs before 2026-11-18 00:00 UTC: decays at %s, %s SATCAT's date taken as the UTC day 2026-11-18 (%.2f h after the day's start)" % (
                key[0], len(P["s1595"]), utc_label(t), rel, (t - sat_lo) / 3600.0))
        else:
            log.w("MEASURED decay reconstruction (%s) seed index 1595: %s at %s" % (key[0], kind, utc_label(t)))
    # (C) against (R) on (C)'s checks
    dc = {(r["idx"], r["used"], r["ref"]): r for r in rows if r["v"] == "C" and r["distinct"]}
    dr = {(r["idx"], r["used"], r["ref"]): r for r in rows if r["v"] == "R" and r["distinct"]}
    if dc:
        cc = sorted(dc)
        log.w("MEASURED (C) against (R) on (C)'s %d checks: medians %.3f km and %.3f km; (C) misses less in %d" % (
            len(cc), H.median([dc[k]["m"] for k in cc]) / 1e3, H.median([dr[k]["m"] for k in cc]) / 1e3, sum(1 for k in cc if dc[k]["m"] < dr[k]["m"])))
    # shares
    for v in ("R", "H", "C"):
        dv = {(r["idx"], r["used"], r["ref"]): r for r in rows if r["v"] == v and r["distinct"]}
        less = sum(1 for k in dv if dv[k]["m"] < hb[k]["m"])
        log.w("MEASURED the share of checks in which (%s) misses less than (B'): %d of %d (checks cluster by object: not independent trials)" % (v, less, len(dv)))
    # the per-check table (ledger)
    n, outp = H.next_numbered(a.work, "checks", ".tsv")
    lines = ["# k_pilot stats: per check (DEBRIS-K, the ledger only); log %s" % os.path.basename(log.path),
             "variant\tF\tidx\tused\tnsets\tref\tref_slot\thorizon_h\tmiss_m\tR_m\tA_m\tC_m\tflagged\tdistinct"]
    for r in rows:
        lines.append("\t".join([r["v"], r["F"], str(r["idx"]), r["used"], str(r["nsets"]), r["ref"], str(r["ref_slot"]), "%.4f" % r["h"], "%.3f" % r["m"],
                                "%.3f" % r["R"], "%.3f" % r["A"], "%.3f" % r["C"], str(r["flag"]), str(r["distinct"])]))
    H.write_new(outp, ("\n".join(lines) + "\n").encode("utf-8"))
    log.w("# per-check table (ledger) %s, %d rows, sha256 %s" % (os.path.basename(outp), len(rows), H.sha256(outp)))
    return close_stage(cpu, log, "stats")


def KR_read_fit_table(path):
    rows, head = {}, None
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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", choices=["prep", "bprime", "rfit", "hfit", "decay", "cfit", "stats"])
    for o in ("--r2", "--downloads", "--work", "--logs", "--keep", "--cpu", "--m1f", "--kfit", "--table", "--java", "--jars", "--orekit", "--decoder", "--leaps"):
        ap.add_argument(o, required=True)
    ap.add_argument("--h-times", default="5,9,13")
    for o in ("--c-data", "--c-gfc", "--c-de"):
        ap.add_argument(o)
    ap.add_argument("--c-limit", default="600")
    a = ap.parse_args()
    os.makedirs(a.work, exist_ok=True)
    return {"prep": stage_prep, "bprime": stage_bprime, "rfit": stage_rfit, "hfit": stage_hfit, "decay": stage_decay, "cfit": stage_cfit,
            "stats": stage_stats}[a.stage](a)


if __name__ == "__main__":
    sys.exit(main())
