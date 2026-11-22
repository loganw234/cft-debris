# h_analyze.py - cft-debris M1 (DEBRIS-H), phase 2: H7's criteria and measurements from the long run's records.
# Standard library only.
# cft-debris, MIT licence (see LICENSE at the repository root). Written by DEBRIS-H, 2026-11-21.
#
#   python -I -B tests/h_analyze.py --box studies/debris-h/box --r2 <ledger>/debris-h/box/r2 --leaps <tai-utc.dat>
#          --out <ledger>/debris-h/phase2 [--logdir studies/debris-h/logs] [--keep studies/debris-h/scripts]
#          [--cpu studies/debris-h/records/cpu.tsv] [--no-d1]
#
# Read-only on the records. It writes one numbered log (aggregates; objects named by seed index only, no catalogue
# number, group, designator or state) and, in the ledger's --out, a folder of the same number holding the per-object
# tables (catalogue numbers, groups and designators there only).
import argparse
import ast
import collections
import hashlib
import json
import math
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import h_lib as H  # noqa: E402

SCRIPT = os.path.abspath(__file__)
METHODS = ["A256", "A64", "A64f", "B"]
NCPU = 36
TZ = -7 * 3600          # the box's local time (-0700), for labels; whole clock hours are the same in UTC
LEAPS_SHA = "3524e1ae34d67e858873a89e59983bbc5bd100221da898e796c1b36036a310c3"   # the stage's in/orekit/tai-utc.dat
SEED_META_SHA = "c229529c76f557074a667182ea67b7fa26199b83e4d5f59f937a4a15b9ca9f3e"

CRITERIA = """
INPUTS, before any data is used: the repository's copies (studies/debris-h/box/) equal SHA256SUMS.box; every file read
  from the ledger's r2/svc/ but the checkpoints equals MANIFEST.copy-003.sha256, and those folders hold no file it does
  not list; every checkpoint equals the run's own svc/manifest.tsv (and copy-003 where it lists it); seed_meta.tsv and
  the leap-second file equal their recorded SHA-256.
H7, as the plan fixed it before the run (studies/DEBRIS-H-plan.md, "H7. The long run"):
 (a) the fetches: every slot's requests logged; at most one request per file per slot; every 200's body archived with
     its SHA-256; any other response stopped the fetcher at once, with no later request. Read from requests.tsv,
     slots.tsv, the service log's FETCH and SLOTS lines, the slot folders and the stop files. A request that got no
     response is not a response; the plan's fetcher rule stops the fetcher at the second slot in a row without one,
     held here to the same terms (stop file, no later request), and a slot ends at its first request without one.
     Fetching after a stop resumed only on Logan's word (--resumed; lead.md 2026-11-20 19:11 and 21:03).
 (b) the checks: every eligible new set checked, or listed with its reason. Eligible means a later epoch than the last
     set checked for that object, an epoch no earlier than T_s, the object not decayed, and the fetcher not stopped.
     T1 and T3 pass on every check. Recomputed here: per catalogue number, the latest ephemeris-type-0 set in the
     slot's archived files (h_check.py's rule); the last set checked from the seed's epoch and the earlier tables; a
     decay from the step logs' D lines, at the checkpoint the check used; T1 from the check logs; T3 recomputed from
     the tables' (B) positions and references and the files' mean motions, as h_check.py's t3().
 (c) the sanity bound: over the run, (A256)'s median miss at horizons e - e0 under 24 hours is at most 5 km, over at
     least 20 checks; with fewer, NOT DETERMINED, never passed. Every check, flagged fits in; e - e0 from the epochs.
 (d) the checkpoints: every 40 steps of each track, all files present, each hash matching the manifest (re-checked
     here on the ledger's copies, with the files' object ranges tiling the seed). A sample of 10 segments per track
     re-propagated by seg equals checkpoint k + 1's bytes (the box's audit.001.log, read here).
 (e) the pacing: in every clock hour with foreign load under 5% of 36 CPUs and no pause, no step of any track is late,
     over at least 6 such hours; with fewer, NOT DETERMINED. A clock hour is [H, H + 3600 s) for a whole hour H, every
     hour in which some step is due (the first and last are partial); its foreign load is the sum of foreign_cpu_s of
     the service log's LOAD lines whose interval begins in it, over 36 times the sum of their lengths (the lead's
     visit7b/8b rule); a pause is any p or P line of a step log or a pause-file line of the service log. A step is late
     when it finishes after its due time (lag > 0) and belongs to the hour of its due time. Elsewhere, measured: the
     share of late steps, the largest lag, and each late stretch (per track, the union over its workers of [due,
     finish] of every late step) with its length: the time the track took to be on time again.
 (f) the kinds: at T_s the cft256 and native64 positions of the first seed are equal (the service's DIV line at k 0,
     and recomputed here from the k 0 checkpoints). After that, a measurement: every DIV line's median and largest
     distance over the objects (recomputed here at the last checkpoint).
MEASUREMENTS (the plan's statistics, fixed before the run), for (A256), (A64), (A64f) and (B), per slot and over the
  run: the miss's median and 90th percentile (the ceil(0.9n)-th smallest), and the same for |R|, |A| and |C|; by horizon
  e - e0 (<6 h, 6-24 h, 1-2 d, 2-3 d, 3-7 d, >=7 d), the run's age e - T_s (<6 h, 6-24 h, 1-2 d, 2-3 d), perigee
  band (<500, 500-800, >=800 km), the seed set's age at T_s (<=1 d, 1-3, 3-7, >7) and the sign of the fitted bc;
  with and without the flagged fits (flags1 & 3); a cell of fewer than 20 checks gives its count and median only; the
  share of checks in which (A256) misses less than (B) (checks cluster by object and update: not independent
  trials); the distinct objects checked, and the checks per object; the kinds' divergence at every checkpoint.
  Every check's reference is the catalogue's new set through SGP4, not the truth: a miss is a distance from it.
DEFINED AFTER THE DATA (no pass condition; beside verdicts they do not change; Logan's rulings, lead.md 2026-11-19
  05:08 and 15:10):
 (e) split: a qualifying hour begins on time if at its first second every worker of every track has finished every
     step due before that second, else it begins behind; per qualifying hour, its kind, late steps and largest lag.
 (b) split: per T3 hit, its slot, the two objects (seed indices here; catalogue numbers, groups and designators in the
     ledger only), the T3 distance, the two references' distance, each object's own (B) miss, each new set's argument
     of perigee plus mean anomaly at its epoch, and the differences of inclination and RAAN; per group over the run,
     the share of checked sets whose argp + M lies within 5 and within 1 degree of the ascending node.
"""


def lt(u):
    return time.strftime("%m-%d %H:%M:%S", time.gmtime(u + TZ))


def hl(u):
    return time.strftime("%m-%d %H", time.gmtime(u + TZ))


def sha_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def read_sums(path):
    d = {}
    for ln in open(path, encoding="utf-8"):
        ln = ln.rstrip("\r\n")
        if not ln or ln.startswith("#"):
            continue
        h, p = ln.split(" ", 1)
        d[p.lstrip(" ").lstrip("*")] = h
    return d


def read_tsv_hashhead(path):
    """a table whose header is its first line, after '# '"""
    head, rows = None, []
    for ln in open(path, encoding="utf-8"):
        ln = ln.rstrip("\r\n")
        if head is None:
            head = ln.lstrip("#").strip().split("\t")
            continue
        if not ln or ln.startswith("#"):
            continue
        rows.append(dict(zip(head, ln.split("\t"))))
    return head, rows


def read_table(path):
    head, rows = None, []
    for ln in open(path, encoding="ascii"):
        if ln.startswith("#"):
            continue
        q = ln.rstrip("\n").split("\t")
        if head is None:
            head = q
            continue
        rows.append(dict(zip(head, q)))
    return head, rows


def hexv(s):
    return [float.fromhex(x) for x in s.split(",")]


def u_node(r):
    """the argument of perigee plus the mean anomaly (deg, mod 360), and its distance from the ascending node"""
    x = (float(r["ARG_OF_PERICENTER"]) + float(r["MEAN_ANOMALY"])) % 360.0
    return x, min(x, 360.0 - x)


def wrap180(x):
    return (x + 180.0) % 360.0 - 180.0


# ------------------------------------------------------------------ inputs
def check_inputs(a, log):
    sums_p = os.path.join(a.box, "SHA256SUMS.box")
    sums = read_sums(sums_p)
    bad = [p for p, h in sorted(sums.items()) if not os.path.isfile(os.path.join(a.box, p)) or sha_file(os.path.join(a.box, p)) != h]
    on_disk = set()
    for d, _, fs in os.walk(a.box):
        for f in fs:
            on_disk.add(os.path.relpath(os.path.join(d, f), a.box).replace(os.sep, "/"))
    extra = sorted(on_disk - set(sums) - {"SHA256SUMS.box"})
    log.check(not bad and not extra, "inputs: the repository's %d copies equal SHA256SUMS.box (sha256 %s); %d differ or are missing, %d unlisted" % (
        len(sums), sha_file(sums_p), len(bad), len(extra)))
    c3p = os.path.join(a.r2, "MANIFEST.copy-003.sha256")
    c3 = read_sums(c3p)
    want = sorted(p for p in c3 if p.startswith(("svc/checks/slot", "svc/steps/", "svc/fetch/")) and not (p.startswith("svc/checks/") and not p.endswith(".tsv")))
    want = [p for p in want if not (p.startswith("svc/checks/") and "/" in p[len("svc/checks/"):])]
    bad = [p for p in want if not os.path.isfile(os.path.join(a.r2, p)) or sha_file(os.path.join(a.r2, p)) != c3[p]]
    have = set()
    for sub in ("svc/steps", "svc/fetch"):
        for d, _, fs in os.walk(os.path.join(a.r2, sub)):
            for f in fs:
                have.add(os.path.relpath(os.path.join(d, f), a.r2).replace(os.sep, "/"))
    for f in os.listdir(os.path.join(a.r2, "svc", "checks")):
        if os.path.isfile(os.path.join(a.r2, "svc", "checks", f)):
            have.add("svc/checks/" + f)
    extra = sorted(have - set(want))
    log.check(not bad and not extra, "inputs: the ledger's %d files read from svc/checks (tables), svc/steps and svc/fetch equal MANIFEST.copy-003.sha256 (sha256 %s, %d entries); %d differ or are missing, %d unlisted" % (
        len(want), sha_file(c3p), len(c3), len(bad), len(extra)))
    sm = os.path.join(a.r2, "seed", "seed_meta.tsv")
    log.check(sha_file(sm) == SEED_META_SHA, "inputs: seed/seed_meta.tsv sha256 %s (recorded %s)" % (sha_file(sm), SEED_META_SHA[:16]))
    log.check(sha_file(a.leaps) == LEAPS_SHA, "inputs: the leap-second file sha256 %s (the stage's %s)" % (sha_file(a.leaps), LEAPS_SHA[:16]))
    return c3


def read_meta(path):
    meta = {}
    head = None
    for ln in open(path, encoding="ascii"):
        if ln.startswith("#"):
            continue
        q = ln.rstrip("\n").split("\t")
        if head is None:
            head = q
            continue
        d = dict(zip(head, q))
        meta[int(d["idx"])] = d
    return meta


def service_lines(a):
    out = []
    for ln in open(os.path.join(a.box, "svc", "logs", "service.001.log"), encoding="utf-8"):
        if ln.startswith("#"):
            continue
        t = ln.rstrip("\n").split(" ", 2)
        if len(t) >= 2:
            out.append((t[0], t[1], t[2] if len(t) > 2 else ""))
    return out


# ------------------------------------------------------------------ (a) the fetches
def eval_a(a, log, sl):
    log.w("\n# ---- H7(a) the fetches")
    _, req = read_tsv_hashhead(os.path.join(a.box, "svc", "fetch", "requests.tsv"))
    _, slots = read_tsv_hashhead(os.path.join(a.box, "svc", "fetch", "slots.tsv"))
    ok = True
    oc = collections.Counter(r["outcome"] for r in req)
    log.w("MEASURED requests: %d (%s); slots attempted %d: %s" % (len(req), ", ".join("%s %d" % kv for kv in sorted(oc.items())), len(slots),
          ", ".join("%s %s" % (s["slot"], s["status"]) for s in slots)))
    # every slot's requests logged, consistent with slots.tsv, the archive and the service log
    started = {}
    ended = {}
    for t, kind, rest in sl:
        if kind == "FETCH":
            w = rest.split()
            if len(w) >= 3 and w[0] == "slot":
                (started if w[2] == "started" else ended)[int(w[1])] = (t, rest)
    sl_slots = [int(s["slot"]) for s in slots]
    c1 = set(started) == set(sl_slots) == set(ended)
    probs = []
    for s in slots:
        j = int(s["slot"])
        rr = [r for r in req if int(r["slot"]) == j]
        n200 = sum(1 for r in rr if r["outcome"] == "200")
        t0, t1 = float(s["t_start"]), float(s["t_end"])
        if n200 != int(s["bodies"]):
            probs.append("slot %d: %d bodies, %d answered 200" % (j, int(s["bodies"]), n200))
        if any(not (t0 <= float(r["t_request"]) <= t1) for r in rr):
            probs.append("slot %d: a request outside the slot's interval" % j)
        if j in ended and ("'bodies': %s" % s["bodies"]) not in ended[j][1]:
            probs.append("slot %d: the service log's FETCH ended line disagrees" % j)
        folder = os.path.join(a.r2, "svc", "fetch", "slot%02d" % j)
        files = sorted(os.listdir(folder)) if os.path.isdir(folder) else []
        want = sorted(os.path.basename(r["file"]) for r in rr if r["outcome"] == "200")
        if files != want:
            probs.append("slot %d: the archive holds %s, the 200s %s" % (j, files, want))
    tr = [float(r["t_request"]) for r in req]
    c1 = c1 and not probs and tr == sorted(tr)
    log.check(c1, "(a) every slot's requests logged: %d slots in slots.tsv, each with FETCH started and ended lines in the service log, its 200s equal to its bodies and its archive folder, every request inside its slot's interval, in time order (%d problems%s)" % (
        len(slots), len(probs), (": " + "; ".join(probs)) if probs else ""))
    ok = ok and c1
    # at most one request per file per slot
    cnt = collections.Counter((r["slot"], r["group"]) for r in req)
    dup = sum(1 for v in cnt.values() if v > 1)
    ok = log.check(dup == 0, "(a) at most one request per file per slot: %d (slot, group) pairs requested, %d more than once" % (len(cnt), dup)) and ok
    # every 200's body archived with its SHA-256
    bad = []
    for r in req:
        if r["outcome"] != "200":
            continue
        p = os.path.join(a.r2, "svc", "fetch", r["file"])
        if not os.path.isfile(p) or os.path.getsize(p) != int(r["body_bytes"]) or sha_file(p) != r["sha256"]:
            bad.append("%s %s" % (r["slot"], r["group"]))
    ok = log.check(not bad, "(a) every 200's body archived with its SHA-256: %d bodies, each present in the ledger's slot folder with the logged size and SHA-256 (%d not)" % (
        oc.get("200", 0), len(bad))) and ok
    # the stop files
    stops = {}
    fdir = os.path.join(a.r2, "svc", "fetch")
    for f in sorted(os.listdir(fdir)):
        if f.startswith("STOP"):
            txt = open(os.path.join(fdir, f), encoding="utf-8").read().strip()
            stops[f] = txt
            log.w("# stop file %s (sha256 %s): %s" % (f, sha_file(os.path.join(fdir, f)), txt))
    # any other response stopped the fetcher at once, with no later request; no response twice in a row likewise
    probs = []
    prev_nr = False
    order = sorted(req, key=lambda r: float(r["t_request"]))
    status = {int(s["slot"]): s["status"] for s in slots}
    for s in slots:
        j = int(s["slot"])
        rr = sorted((r for r in req if int(r["slot"]) == j), key=lambda r: float(r["t_request"]))
        for r in rr:
            if r["outcome"] == "200":
                continue
            tq = float(r["t_request"])
            later = [q for q in order if float(q["t_request"]) > tq]
            later_same = [q for q in later if int(q["slot"]) == j]
            if later_same:
                probs.append("slot %d: a request after its %s" % (j, r["outcome"]))
            named = [f for f, txt in stops.items() if ("slot %d " % j) in txt]
            if r["outcome"] == "noresponse":
                if prev_nr:
                    # the second slot in a row: a stop, and no request until a resume on Logan's word
                    resumed = [k for k in a.resumed if k > j]
                    nxt = min(resumed) if resumed else None
                    early = [q for q in later if nxt is None or int(q["slot"]) < nxt]
                    if not named or early:
                        probs.append("slot %d: second slot without a response, stop file %s, %d requests before the resume" % (j, named, len(early)))
                    log.w("# slot %d: the second slot in a row without a response: stop file %s; the next request is slot %s's (resumed on Logan's word)" % (
                        j, ",".join(named) or "none", later[0]["slot"] if later else "none"))
                else:
                    log.w("# slot %d: a request without a response (%s), the first slot in a row: the slot ends, the fetcher goes on" % (j, r["group"]))
            else:
                if not named or later:
                    probs.append("slot %d: response %s: stop file %s, %d later requests" % (j, r["outcome"], named, len(later)))
                log.w("# slot %d: response %s for %s: stop file %s; later requests %d" % (j, r["outcome"], r["group"], ",".join(named) or "none", len(later)))
        prev_nr = status[j] == "noresponse"
    slines = [rest for t, kind, rest in sl if kind == "SLOTS"]
    for x in slines:
        log.w("# service log: SLOTS %s" % x)
    last_slot = max(sl_slots)
    ok = log.check(not probs, "(a) any other response stopped the fetcher at once, with no later request (and the second slot in a row without a response likewise, until the resume on Logan's word at slot(s) %s); slots after %d: none attempted (%d problems%s)" % (
        ",".join(str(x) for x in a.resumed), last_slot, len(probs), (": " + "; ".join(probs)) if probs else "")) and ok
    fnd = collections.Counter(r["findings"] for r in req if r["findings"])
    for k, v in sorted(fnd.items()):
        log.w("# requests.tsv findings: %d x '%s'" % (v, k))
    log.w("RESULT H7(a): %s" % ("PASS" if ok else "FAIL"))
    return ok, req, slots


# ------------------------------------------------------------------ the step logs
def read_steps(a):
    steps = {}
    pauses, decays, xs, ck = [], [], [], collections.Counter()
    sdir = os.path.join(a.r2, "svc", "steps")
    for tr in sorted(os.listdir(sdir)):
        if not os.path.isdir(os.path.join(sdir, tr)):
            continue
        for f in sorted(os.listdir(os.path.join(sdir, tr))):
            w = f.split(".")[0]
            L = steps.setdefault((tr, w), {})
            for ln in open(os.path.join(sdir, tr, f), encoding="ascii"):
                t = ln.split()
                if not t:
                    continue
                if t[0] == "S":
                    k = int(t[1])
                    if k in L:
                        L.setdefault("_dup", 0)
                    L[k] = (float(t[2]), float(t[3]), float(t[4]), float(t[5]))
                elif t[0] in ("p", "P"):
                    pauses.append((tr, w, ln.strip()))
                elif t[0] == "D":
                    decays.append((tr, w, int(t[1]), int(t[2]), float(t[3])))
                elif t[0] == "X":
                    xs.append((tr, w, ln.strip()))
                elif t[0] == "C":
                    ck[tr] += 1
    return steps, pauses, decays, xs, ck


# ------------------------------------------------------------------ (b) the checks, and the measurements' rows
def slot_sets(a, j):
    new, files = {}, []
    for g in H.GROUPS:
        p = os.path.join(a.r2, "svc", "fetch", "slot%02d" % j, "gp-%s.csv" % g)
        if os.path.exists(p):
            files.append(g)
            for r in H.read_gp(p, g):
                if r["EPHEMERIS_TYPE"] != "0":
                    continue
                c = int(r["NORAD_CAT_ID"])
                if c in new and H.epoch_tdb(new[c]) >= H.epoch_tdb(r):
                    continue
                new[c] = r
    return new, files


def eval_b(a, log, meta, cfg, sl, slots, decays):
    log.w("\n# ---- H7(b) the checks")
    ts = cfg["ts"]
    ck = cfg["ckpt_every"]
    checked_slots = sorted(int(rest.split()[1]) for t, kind, rest in sl if kind == "CHECK" and rest.split()[2] == "started")
    fetched = [int(s["slot"]) for s in slots]
    stopped_slots = [j for j in fetched if j not in checked_slots]
    log.w("# slots fetched %s; checked %s; fetched but not checked (the fetcher stopped in that slot): %s" % (fetched, checked_slots, stopped_slots))
    dec = {}
    for tr, w, k, i, r in decays:
        dec[(tr, i)] = min(k, dec.get((tr, i), k))
    e0 = {i: H.epoch_tdb({"EPOCH": d["epoch"]}) for i, d in meta.items()}
    last = dict(e0)
    rows = []
    probs = []
    t1n = t1bad = 0
    t3hits = []
    t3log = {}
    elig_total = 0
    present = {}     # slot -> set of seed idx present in their group's file (the group's file fetched)
    sets_by = {}
    for j in fetched:
        new, files = slot_sets(a, j)
        sets_by[j] = (new, files)
        present[j] = set(i for i, d in meta.items() if d["group"] in files and int(d["cat"]) in new)
    for j in checked_slots:
        new, files = sets_by[j]
        cnt = collections.Counter()
        elig = {}
        for i in sorted(meta):
            r = new.get(int(meta[i]["cat"]))
            if r is None:
                cnt["absent"] += 1
                continue
            e = H.epoch_tdb(r)
            if not e > last[i]:
                cnt["not_later"] += 1
                continue
            if e < ts:
                cnt["before_ts"] += 1
                continue
            elig[i] = (r, e)
        cnt["eligible"] = len(elig)
        lp = os.path.join(a.box, "svc", "logs", "check_slot%02d.001.log" % j)
        lc = None
        t3line = None
        for ln in open(lp, encoding="utf-8"):
            if ln.startswith("# counts: "):
                lc = ast.literal_eval(ln[len("# counts: "):].split("}")[0] + "}")
            elif ln.startswith(("PASS T1", "FAIL T1")):
                w = ln.split()
                t1n += int(w[6])
                t1bad += int(w[-3].lstrip("("))
                if ln.startswith("FAIL"):
                    probs.append("slot %d: T1 failed" % j)
            elif ln.startswith(("PASS T3", "FAIL T3")):
                t3line = ln.strip()
        if lc is None or any(lc.get(k, 0) != cnt[k] for k in ("absent", "not_later", "before_ts", "eligible")):
            probs.append("slot %d: counts %s, the check's %s" % (j, dict(cnt), lc))
        tp = os.path.join(a.r2, "svc", "checks", "slot%02d.tsv" % j)
        _, tab = read_table(tp)
        tab = {int(q["idx"]): q for q in tab}
        if set(tab) != set(elig):
            probs.append("slot %d: table %d rows, eligible %d, %d differ" % (j, len(tab), len(elig), len(set(tab) ^ set(elig))))
        st = collections.Counter()
        for i, q in sorted(tab.items()):
            st[q["status"]] += 1
            if i not in elig:
                continue
            r, e = elig[i]
            if q["new_epoch"] != r["EPOCH"]:
                probs.append("slot %d idx %d: the table's set is not the latest" % (j, i))
            eq = float.fromhex(q["e_q"]) if q["e_q"] else float(H.quantize(e))
            kc = int(q["A256_kc"]) if q.get("A256_kc") else int(math.floor((eq - ts) / (15.0 * ck))) * ck
            want_dec = any(dec.get((tr, i), 10 ** 9) <= kc for tr in ("A256", "A64", "A64f"))
            if want_dec != (q["status"] == "decayed"):
                probs.append("slot %d idx %d: status %s, decayed at kc %d: %s" % (j, i, q["status"], kc, want_dec))
            if q["status"] == "listed" and not q["why"]:
                probs.append("slot %d idx %d: listed without a reason" % (j, i))
            if q["status"] not in ("checked", "listed", "decayed"):
                probs.append("slot %d idx %d: status %s" % (j, i, q["status"]))
            if q["status"] == "checked":
                M = {}
                for m in METHODS:
                    M[m] = (float(q[m + "_m"]), float(q[m + "_R"]), float(q[m + "_A"]), float(q[m + "_C"]))
                rows.append({"slot": j, "idx": i, "M": M, "flagged": bool(int(q["flags1"]) & 3),
                             "hor_h": float(e - e0[i]) / 3600.0, "age_h": (eq - ts) / 3600.0,
                             "per": float(q["perigee_km"]), "sage": float(q["seed_age_d"]), "bc": float.fromhex(q["bc1"]),
                             "set": r, "bpos": hexv(q["B_pos"]), "ref": hexv(q["ref_state"]), "B_m": float(q["B_m"])})
        elig_total += len(elig)
        # T3, recomputed as h_check.py's t3()
        chk = [i for i in tab if tab[i]["status"] == "checked"]
        order = sorted(chk, key=lambda i: int(meta[i]["cat"]))
        nn = {i: float(elig[i][0]["MEAN_MOTION"]) for i in chk}
        bpos = {i: hexv(tab[i]["B_pos"]) for i in chk}
        refs = {i: hexv(tab[i]["ref_state"]) for i in chk}
        n = len(order)
        done = 0
        hits = []
        for p, k in enumerate(order):
            q2 = (p + 1) % n
            while order[q2] != k and abs(nn[order[q2]] - nn[k]) <= 1e-3:
                q2 = (q2 + 1) % n
            if order[q2] == k:
                continue
            done += 1
            d = H.dist(bpos[k], refs[order[q2]][:3])
            if not d > 100e3:
                hits.append((j, k, order[q2], d))
        want = "%s T3 swapped identities: %d of %d checks compared, %d within 100 km" % ("PASS" if not hits else "FAIL", done, n, len(hits))
        if t3line != want:
            probs.append("slot %d: T3 recomputed '%s', the check's '%s'" % (j, want, t3line))
        t3hits += hits
        t3log[j] = (done, n, len(hits))
        # the last set checked
        for i in chk:
            last[i] = max(last[i], elig[i][1])
        log.w("# slot %2d: files %s; recomputed absent %d, not later %d, before T_s %d, eligible %d; table %s; T3 %d of %d compared, %d within 100 km" % (
            j, ",".join(files), cnt["absent"], cnt["not_later"], cnt["before_ts"], cnt["eligible"], dict(st), done, n, len(hits)))
    # the fetched-but-stopped slots: nothing eligible; what an unstopped fetcher would have offered, for the record
    for j in stopped_slots:
        new, files = sets_by[j]
        n_new = 0
        for i in sorted(meta):
            r = new.get(int(meta[i]["cat"]))
            if r is not None and H.epoch_tdb(r) > last[i] and H.epoch_tdb(r) >= ts:
                n_new += 1
        log.w("# slot %2d: the fetcher stopped in this slot (files %s): no set eligible; %d sets there were later than the last checked and after T_s" % (j, ",".join(files), n_new))
    e_ok = not [p for p in probs if "T3" not in p and "T1" not in p]
    log.check(e_ok, "(b) every eligible new set checked, or listed with its reason: %d eligible sets over %d checked slots, recomputed from the archived files, equal the check tables' rows; %d checked, 0 listed, 0 decayed (%d problems%s)" % (
        elig_total, len(checked_slots), len(rows), len(probs), (": " + "; ".join(probs[:8])) if probs else ""))
    log.check(t1bad == 0, "(b) T1 on every check: %d check-methods over the slots' logs, %d outside 1%% of |v|" % (t1n, t1bad))
    log.check(not t3hits, "(b) T3 on every check: %d checks compared over the run (recomputed, equal to every check log's line), %d within 100 km, at slot(s) %s" % (
        sum(v[0] for v in t3log.values()), len(t3hits), ", ".join(str(h[0]) for h in t3hits) or "none"))
    ok = e_ok and t1bad == 0 and not t3hits
    log.w("RESULT H7(b): %s%s" % ("PASS" if ok else "FAIL", "" if ok else " (by its letter: %s)" % "; ".join(
        x for x in (("eligibility" if not e_ok else ""), ("T1" if t1bad else ""), ("T3 hit at slots %s" % ", ".join(str(h[0]) for h in t3hits) if t3hits else "")) if x)))
    # departures: seed objects absent from their group's fetched file
    first_abs = {}
    for j in fetched:
        new, files = sets_by[j]
        for i, d in meta.items():
            if d["group"] in files and i not in present[j] and i not in first_abs:
                first_abs[i] = j
    log.w("MEASURED departures: %d seed objects absent from their group's fetched file at some slot: %s" % (
        len(first_abs), ", ".join("idx %d from slot %d%s" % (i, j, " (back later)" if any(i in present[k] for k in fetched if k > j) else "")
                                   for i, j in sorted(first_abs.items(), key=lambda x: (x[1], x[0])))))
    return ok, rows, t3hits, sets_by, first_abs


def t3_split(a, log, meta, rows, t3hits, outdir):
    log.w("\n# ---- H7(b)'s split, DEFINED AFTER THE DATA (Logan's ruling, lead.md 2026-11-19 15:10): no pass condition")
    byk = {(r["slot"], r["idx"]): r for r in rows}
    lines = ["# h_analyze: the T3 hits, per object (the ledger only)", "\t".join([
        "slot", "idx1", "cat1", "group1", "intl_des1", "name1", "epoch1", "idx2", "cat2", "group2", "intl_des2", "name2", "epoch2",
        "t3_m", "refs_m", "B1_m", "B2_m", "u1_deg", "u2_deg", "d_incl_deg", "d_raan_deg"])]
    for j, i1, i2, d in t3hits:
        r1, r2 = byk[(j, i1)], byk[(j, i2)]
        s1, s2 = r1["set"], r2["set"]
        u1, u2 = u_node(s1)[0], u_node(s2)[0]
        di = float(s2["INCLINATION"]) - float(s1["INCLINATION"])
        dO = wrap180(float(s2["RA_OF_ASC_NODE"]) - float(s1["RA_OF_ASC_NODE"]))
        rd = H.dist(r1["ref"][:3], r2["ref"][:3])
        log.w("MEASURED T3 hit, slot %d: idx %d's (B) against idx %d's reference %.1f m; the references %.1f m apart; (B) misses %.1f m (idx %d) and %.1f m (idx %d); argp + M %.4f and %.4f deg; inclination differs by %.4f deg, RAAN by %.4f deg (second - first)" % (
            j, i1, i2, d, rd, r1["B_m"], i1, r2["B_m"], i2, u1, u2, di, dO))
        lines.append("\t".join(str(x) for x in [j, i1, meta[i1]["cat"], meta[i1]["group"], s1["OBJECT_ID"], s1["OBJECT_NAME"], s1["EPOCH"],
                                                i2, meta[i2]["cat"], meta[i2]["group"], s2["OBJECT_ID"], s2["OBJECT_NAME"], s2["EPOCH"],
                                                "%.1f" % d, "%.1f" % rd, "%.1f" % r1["B_m"], "%.1f" % r2["B_m"], "%.4f" % u1, "%.4f" % u2,
                                                "%.4f" % di, "%.4f" % dO]))
    H.write_new(os.path.join(outdir, "t3_hits.tsv"), ("\n".join(lines) + "\n").encode("utf-8"))
    G = collections.OrderedDict()
    for r in rows:
        x = u_node(r["set"])[1]
        c = G.setdefault(r["set"]["GROUP"], [0, 0, 0])
        c[0] += 1
        c[1] += x <= 5.0
        c[2] += x <= 1.0
    for g, c in sorted(G.items()):
        log.w("MEASURED node shares, group %s: %d checked sets; argp + M within 5 deg of the node %d (%.1f%%), within 1 deg %d (%.1f%%)" % (
            g, c[0], c[1], 100.0 * c[1] / c[0], c[2], 100.0 * c[2] / c[0]))


# ------------------------------------------------------------------ (c) and the measurements
HOR = [("<6 h", 0, 6), ("6-24 h", 6, 24), ("1-2 d", 24, 48), ("2-3 d", 48, 72), ("3-7 d", 72, 168), (">=7 d", 168, 1e30)]
AGE = [("<6 h", -1e30, 6), ("6-24 h", 6, 24), ("1-2 d", 24, 48), ("2-3 d", 48, 72), (">=3 d", 72, 1e30)]
PER = [("<500 km", -1e30, 500), ("500-800 km", 500, 800), (">=800 km", 800, 1e30)]


def cell(rows, m):
    v = [r["M"][m] for r in rows]
    n = len(v)
    if n == 0:
        return "n 0"
    d = [x[0] for x in v]
    if n < 20:
        return "n %d, median %.3f km (under 20: count and median only)" % (n, H.median(d) / 1e3)
    parts = []
    for c, lab in ((1, "|R|"), (2, "|A|"), (3, "|C|")):
        w = [abs(x[c]) for x in v]
        parts.append("%s %.3f/%.3f" % (lab, H.median(w) / 1e3, H.quant(w, 0.9) / 1e3))
    return "n %d, median %.3f km, 90th %.3f km; median/90th %s km" % (n, H.median(d) / 1e3, H.quant(d, 0.9) / 1e3, ", ".join(parts))


def eval_c(log, rows):
    log.w("\n# ---- H7(c) the sanity bound")
    v = [r["M"]["A256"][0] for r in rows if r["hor_h"] < 24.0]
    vf = [r["M"]["A256"][0] for r in rows if r["hor_h"] < 24.0 and not r["flagged"]]
    if len(v) < 20:
        log.w("RESULT H7(c): NOT DETERMINED (%d checks at horizons under 24 h)" % len(v))
        return None
    med = H.median(v)
    log.check(med <= 5000.0, "(c) (A256) median miss at horizons e - e0 under 24 h, every check (flagged fits in): n %d, median %.3f km (bound 5 km)" % (len(v), med / 1e3))
    log.w("# beside it, without the flagged fits: n %d, median %.3f km" % (len(vf), H.median(vf) / 1e3 if vf else float("nan")))
    log.w("RESULT H7(c): %s" % ("PASS" if med <= 5000.0 else "FAIL"))
    return med <= 5000.0


def measurements(log, rows, outdir, meta):
    log.w("\n# ---- the measurements (MEASURED; the reference is the catalogue's new set through SGP4, not the truth)")
    flags = (("all", lambda r: True), ("without flagged fits", lambda r: not r["flagged"]))
    for j in sorted(set(r["slot"] for r in rows)):
        rs = [r for r in rows if r["slot"] == j]
        for m in METHODS:
            for lab, keep in flags:
                log.w("MEASURED slot %d %s %s: %s" % (j, m, lab, cell([r for r in rs if keep(r)], m)))
    for m in METHODS:
        for lab, keep in flags:
            rk = [r for r in rows if keep(r)]
            log.w("MEASURED run %s %s: %s" % (m, lab, cell(rk, m)))
            for name, key, bins in (("horizon e-e0", "hor_h", HOR), ("run age e-T_s", "age_h", AGE), ("perigee", "per", PER)):
                for bl, lo, hi in bins:
                    sub = [r for r in rk if lo <= r[key] < hi]
                    if sub or bl not in (">=3 d",):
                        log.w("MEASURED run %s %s, %s %s: %s" % (m, lab, name, bl, cell(sub, m)))
            for bl, lo, hi in (("<=1 d", -1e30, 1), ("1-3 d", 1, 3), ("3-7 d", 3, 7), (">7 d", 7, 1e30)):
                sub = [r for r in rk if lo < r["sage"] <= hi]
                log.w("MEASURED run %s %s, seed set's age at T_s %s: %s" % (m, lab, bl, cell(sub, m)))
            for bl, f in (("bc > 0", lambda x: x > 0), ("bc < 0", lambda x: x < 0), ("bc = 0", lambda x: x == 0)):
                sub = [r for r in rk if f(r["bc"])]
                if sub or bl != "bc = 0":
                    log.w("MEASURED run %s %s, fitted %s: %s" % (m, lab, bl, cell(sub, m)))
    for lab, keep in flags:
        rk = [r for r in rows if keep(r)]
        k = sum(1 for r in rk if r["M"]["A256"][0] < r["M"]["B"][0])
        log.w("MEASURED (A256) misses less than (B), %s: %d of %d checks (%.1f%%); checks cluster by object and update, not independent trials" % (
            lab, k, len(rk), 100.0 * k / len(rk) if rk else float("nan")))
    per = collections.Counter(r["idx"] for r in rows)
    hist = collections.Counter(per.values())
    log.w("MEASURED distinct objects checked: %d of %d; checks per object: min %d, median %s, max %d; histogram %s" % (
        len(per), len(meta), min(per.values()), H.median(list(per.values())), max(per.values()),
        ", ".join("%d: %d" % kv for kv in sorted(hist.items()))))
    log.w("MEASURED flagged fits among the checks: %d of %d" % (sum(1 for r in rows if r["flagged"]), len(rows)))
    # the per-object table (the ledger only)
    lines = ["# h_analyze: per object over the run's checks (the ledger only)",
             "\t".join(["idx", "cat", "group", "checks", "slots"] + ["%s_median_m" % m for m in METHODS] + ["A256_lt_B"])]
    for i in sorted(per):
        rs = [r for r in rows if r["idx"] == i]
        lines.append("\t".join([str(i), meta[i]["cat"], meta[i]["group"], str(len(rs)), ",".join(str(r["slot"]) for r in rs)] +
                               ["%.3f" % H.median([r["M"][m][0] for r in rs]) for m in METHODS] +
                               [str(sum(1 for r in rs if r["M"]["A256"][0] < r["M"]["B"][0]))]))
    H.write_new(os.path.join(outdir, "objects.tsv"), ("\n".join(lines) + "\n").encode("utf-8"))


# ------------------------------------------------------------------ (d) the checkpoints
def eval_d(a, log, cfg, c3, no_d1):
    log.w("\n# ---- H7(d) the checkpoints")
    _, man = read_tsv_hashhead(os.path.join(a.box, "svc", "manifest.tsv"))
    ok = True
    nobj, kend, ce = cfg["nobj"], cfg["kend"], cfg["ckpt_every"]
    by = collections.defaultdict(list)
    for r in man:
        by[(r["track"], int(r["k"]))].append(r)
    probs = []
    nfile = 0
    for t in cfg["tracks"]:
        W = t["workers"]
        for k in range(0, kend + 1, ce):
            rs = by.get((t["name"], k), [])
            ws = sorted(int(r["worker"]) for r in rs)
            if ws != list(range(W)):
                probs.append("%s k %d: workers %s" % (t["name"], k, ws))
                continue
            spans = sorted((int(r["first"]), int(r["count"])) for r in rs)
            pos = 0
            for f0, n in spans:
                if f0 != pos:
                    probs.append("%s k %d: ranges do not tile" % (t["name"], k))
                pos = f0 + n
            if pos != nobj:
                probs.append("%s k %d: ranges cover %d" % (t["name"], k, pos))
            for r in rs:
                nfile += 1
                if c3.get(r["file"], r["sha256"]) != r["sha256"]:
                    probs.append("%s: copy-003 differs from the manifest" % r["file"])
                if no_d1:
                    continue
                p = os.path.join(a.r2, r["file"])
                if not os.path.isfile(p) or os.path.getsize(p) != int(r["bytes"]) or sha_file(p) != r["sha256"]:
                    probs.append("%s: missing or differs" % r["file"])
    listed = set(r["file"] for r in man)
    extra = []
    for t in cfg["tracks"]:
        d = os.path.join(a.r2, "svc", "ckpt", t["name"])
        for f in os.listdir(d):
            if "svc/ckpt/%s/%s" % (t["name"], f) not in listed:
                extra.append(f)
    expect = sum(t["workers"] for t in cfg["tracks"]) * (kend // ce + 1)
    ok = log.check(not probs and not extra and len(man) == expect, "(d1) re-checked on the ledger's copies%s: every 40 steps from 0 to %d of each track, the files present, their object ranges tiling the %d objects, each equal in size and SHA-256 to svc/manifest.tsv (%d files; manifest %d entries, expected %d; %d problems, %d files unlisted%s)" % (
        " (hashes NOT re-computed: --no-d1)" if no_d1 else "", kend, nobj, nfile, len(man), expect, len(probs), len(extra), (": " + "; ".join(probs[:5])) if probs else "")) and ok
    ap = os.path.join(a.box, "svc", "logs", "audit.001.log")
    res = []
    for ln in open(ap, encoding="utf-8"):
        if ln.startswith("# script ") or ln.startswith(("PASS (d", "FAIL (d")):
            res.append(ln.strip())
    for x in res:
        log.w("# audit.001.log (the box, 2026-11-21 15:57): %s" % x)
    d2 = [x for x in res if x.startswith(("PASS (d2)", "FAIL (d2)"))]
    tsha = sha_file(os.path.join(os.path.dirname(SCRIPT), "h_audit.py"))
    ok2 = len(d2) == len(cfg["tracks"]) and all(x.startswith("PASS") for x in d2) and any(tsha in x for x in res)
    ok = log.check(ok2, "(d2) the box's audit: %d of %d tracks with 10 of 10 sampled segments equal to the next checkpoint's bytes; its script's SHA-256 equals tests/h_audit.py's (%s)" % (
        sum(1 for x in d2 if x.startswith("PASS")), len(cfg["tracks"]), tsha[:12])) and ok
    rw = 0
    log.w("RESULT H7(d): %s" % ("PASS" if ok else "FAIL"))
    return ok, rw


# ------------------------------------------------------------------ (e) the pacing
def eval_e(a, log, cfg, cm, sl, steps, pauses):
    log.w("\n# ---- H7(e) the pacing")
    ur = cm["unix_ref"]
    kend = cfg["kend"]
    probs = []
    late = collections.defaultdict(list)     # track -> [(due, fin, lag, worker, k)]
    tot = collections.Counter()
    dev = 0.0
    hours = collections.defaultdict(lambda: [0, 0, 0.0])  # H -> [steps, late, max lag]
    for (tr, w), L in sorted(steps.items()):
        ks = sorted(k for k in L if isinstance(k, int))
        if ks != list(range(1, kend + 1)) or "_dup" in L:
            probs.append("%s %s: steps %d..%d, %d logged%s" % (tr, w, ks[0], ks[-1], len(ks), ", some twice" if "_dup" in L else ""))
        for k in ks:
            st, fi, du, lag = L[k]
            dev = max(dev, abs(du - (ur + 15.0 * k)))
            tot[tr] += 1
            Hh = int(du // 3600) * 3600
            c = hours[Hh]
            c[0] += 1
            if lag > 0:
                late[tr].append((du, fi, lag, w, k))
                c[1] += 1
                c[2] = max(c[2], lag)
    log.check(not probs, "(e) the step logs: %d workers, each with every step 1..%d once; due times equal unix_ref + 15 k within %.3g s (%d problems%s)" % (
        len(steps), kend, dev, len(probs), (": " + "; ".join(probs[:4])) if probs else ""))
    # the foreign load per clock hour
    loadh = collections.defaultdict(lambda: [0.0, 0.0, 0.0, 0])
    pfile = []
    for t, kind, rest in sl:
        if kind == "LOAD":
            w = rest.split()
            t0, t1 = float(w[0]), float(w[1])
            kv = dict(zip(w[2::2], w[3::2]))
            c = loadh[int(t0 // 3600) * 3600]
            c[0] += t1 - t0
            c[1] += float(kv["foreign_cpu_s"])
            c[2] = max(c[2], float(kv["foreign_share"]))
            c[3] += 1
            if int(kv["ncpu"]) != NCPU:
                probs.append("LOAD ncpu %s" % kv["ncpu"])
        elif kind.startswith("PAUSE"):
            pfile.append((t, kind, rest))
    log.w("# pauses: %d p/P lines in the step logs, %d pause-file lines in the service log" % (len(pauses), len(pfile)))
    pause_h = set()
    for x in pauses:
        w = x[2].split()
        for u in w[1:3]:
            try:
                pause_h.add(int(float(u) // 3600) * 3600)
            except ValueError:
                pass
    # behind at an hour's first second: a step due before it and unfinished at it
    behind = collections.defaultdict(lambda: [set(), 0.0])
    for tr, L in late.items():
        for du, fi, lag, w, k in L:
            Hn = (int(du // 3600) + 1) * 3600
            while Hn < fi:
                b = behind[Hn]
                b[0].add((tr, w))
                b[1] = max(b[1], Hn - du)
                Hn += 3600
    hs = sorted(hours)
    qual = []
    log.w("# every clock hour with a step due (local -0700): steps due, late, largest lag; foreign share; Q if under 5%% and no pause; at its first second, workers behind and the largest backlog")
    for Hh in hs:
        n, nl, ml = hours[Hh]
        c = loadh.get(Hh)
        fs = c[1] / (NCPU * c[0]) if c and c[0] > 0 else float("nan")
        q = c is not None and c[0] > 0 and fs < 0.05 and Hh not in pause_h
        b = behind.get(Hh, [set(), 0.0])
        if q:
            qual.append(Hh)
        log.w("#   %s  steps %5d late %5d max %7.1f s | foreign %.4f (max minute %.4f, %2d LOAD lines) %s | behind %2d (%.1f s)" % (
            hl(Hh), n, nl, ml, fs, c[2] if c else float("nan"), c[3] if c else 0, "Q" if q else "-", len(b[0]), b[1]))
    lq = sum(hours[h][1] for h in qual)
    per_h = 240 * len(steps)
    full = [h for h in qual if hours[h][0] == per_h]
    part = [h for h in qual if hours[h][0] != per_h]
    log.w("# qualifying hours: %d, of which %d full (%d steps due, every worker's 240) and %d partial (%s)" % (
        len(qual), len(full), per_h, len(part), ", ".join("%s: %d steps due" % (hl(h), hours[h][0]) for h in part) or "none"))
    if len(qual) < 6:
        log.w("RESULT H7(e): NOT DETERMINED (%d qualifying hours)" % len(qual))
        ok = None
    else:
        ok = log.check(lq == 0, "(e) no step of any track late in the %d qualifying hours (%d full, %d partial; foreign load under 5%% of 36 CPUs, no pause): %d late steps in %d of them (%s)" % (
            len(qual), len(full), len(part), lq, sum(1 for h in qual if hours[h][1]),
            ", ".join("%s: %d, largest lag %.1f s" % (hl(h), hours[h][1], hours[h][2]) for h in qual if hours[h][1])))
        log.w("RESULT H7(e): %s" % ("PASS" if ok else "FAIL (by its letter)"))
    # elsewhere, measured
    log.w("MEASURED late steps per track over the run: %s" % "; ".join(
        "%s %d of %d (%.1f%%), largest lag %.1f s" % (tr, len(late[tr]), tot[tr], 100.0 * len(late[tr]) / tot[tr], max([x[2] for x in late[tr]] or [0.0]))
        for tr in sorted(tot)))
    nq = [h for h in hs if h not in qual]
    log.w("MEASURED outside the qualifying hours (%d hours): %d of %d steps late (%.1f%%), largest lag %.1f s" % (
        len(nq), sum(hours[h][1] for h in nq), sum(hours[h][0] for h in nq), 100.0 * sum(hours[h][1] for h in nq) / max(1, sum(hours[h][0] for h in nq)),
        max([hours[h][2] for h in nq] or [0.0])))
    for tr in sorted(tot):
        if not late[tr]:
            log.w("MEASURED %s: no late step" % tr)
            continue
        mx = max(late[tr], key=lambda x: x[2])
        log.w("MEASURED %s: largest lag %.1f s, step %d of worker %s, due %s" % (tr, mx[2], mx[4], mx[3], lt(mx[0])))
        iv = sorted(late[tr])
        out = []
        for du, fi, lag, w, k in iv:
            if out and du <= out[-1][1]:
                o = out[-1]
                o[1] = max(o[1], fi)
                o[2] += 1
                o[3] = max(o[3], lag)
                o[4].add(w)
            else:
                out.append([du, fi, 1, lag, {w}])
        big = [o for o in out if o[1] - o[0] >= 60.0]
        small = [o for o in out if o[1] - o[0] < 60.0]
        log.w("MEASURED %s late stretches: %d; %d of 1 min or longer, listed; %d shorter (%d late steps, largest lag %.1f s, longest %.1f s)" % (
            tr, len(out), len(big), len(small), sum(o[2] for o in small), max([o[3] for o in small] or [0.0]), max([o[1] - o[0] for o in small] or [0.0])))
        for o in big:
            log.w("MEASURED   %s stretch from %s to %s: %.1f min to be on time again; %d late steps, %d workers, largest lag %.1f s" % (
                tr, lt(o[0]), lt(o[1]), (o[1] - o[0]) / 60.0, o[2], len(o[4]), o[3]))
    # the split, defined after the data
    log.w("\n# ---- H7(e)'s split, DEFINED AFTER THE DATA (Logan's ruling, lead.md 2026-11-19 05:08): no pass condition")
    for h in qual:
        b = behind.get(h, [set(), 0.0])
        log.w("MEASURED qualifying hour %s (%s): begins %s (%d workers behind at its first second, largest backlog %.1f s); late steps %d, largest lag %.1f s" % (
            hl(h), "full" if h in full else "partial, %d steps due" % hours[h][0], "behind" if b[0] else "on time", len(b[0]), b[1], hours[h][1], hours[h][2]))
    nb = [h for h in qual if behind.get(h)]
    log.w("MEASURED qualifying hours: %d; begun on time %d, with %d late steps; begun behind %d (%s), with %d late steps" % (
        len(qual), len(qual) - len(nb), sum(hours[h][1] for h in qual if h not in nb), len(nb), ", ".join(hl(h) for h in nb),
        sum(hours[h][1] for h in nb)))
    return ok


# ------------------------------------------------------------------ (f) the kinds
def ck_pos(paths):
    """binary64 positions of the objects not decayed (decay step -1), as h_service.py's divergence() reads them"""
    out = {}
    for p in paths:
        hdr, objs = H.read_ckpt(p)
        if not hdr["_complete"]:
            raise SystemExit("incomplete checkpoint file %s" % p)
        for i, o in objs.items():
            if o[0] < 0:
                out[i] = [H.f64(x) for x in o[2][:3]]
    return out


def eval_f(a, log, cfg, sl, man_rows):
    log.w("\n# ---- H7(f) the kinds")
    div = []
    for t, kind, rest in sl:
        if kind == "DIV":
            w = rest.split()
            kv = dict(zip(w[1::2], w[2::2]))
            div.append((int(kv["k"]), int(kv["n"]), float(kv["median_m"]), float(kv["max_m"]), int(kv["zero"])))
    div.sort()
    k0 = [d for d in div if d[0] == 0]
    ok = log.check(len(k0) == 1 and k0[0][1] == cfg["nobj"] and k0[0][4] == k0[0][1],
                   "(f) at T_s (k 0) the cft256 and native64 positions of the first seed equal: the service's DIV line n %d, zero distance %d" % (
                       k0[0][1] if k0 else -1, k0[0][4] if k0 else -1))
    # recomputed from the checkpoints at k 0 and at the last step
    for k in (0, cfg["kend"]):
        fa = [os.path.join(a.r2, r["file"]) for r in man_rows if r["track"] == "A256" and int(r["k"]) == k]
        fb = [os.path.join(a.r2, r["file"]) for r in man_rows if r["track"] == "A64" and int(r["k"]) == k]
        pa, pb = ck_pos(fa), ck_pos(fb)
        d = [H.dist(pa[i], pb[i]) for i in sorted(set(pa) & set(pb)) if all(math.isfinite(x) for x in pa[i] + pb[i])]
        row = [x for x in div if x[0] == k]
        same = row and len(d) == row[0][1] and "%.6e" % H.median(d) == "%.6e" % row[0][2] and "%.6e" % max(d) == "%.6e" % row[0][3] and sum(1 for x in d if x == 0.0) == row[0][4]
        ok = log.check(bool(same), "(f) recomputed from the ledger's checkpoints at k %d: n %d, median %.6e m, largest %.6e m, zero %d; the service's DIV line %s" % (
            k, len(d), H.median(d), max(d), sum(1 for x in d if x == 0.0), row[0] if row else "missing")) and ok
    log.w("MEASURED the kinds' divergence, |A256 - A64| over the objects, at every checkpoint (%d DIV lines); every 1440 steps (6 h):" % len(div))
    for k, n, md, mx, z in div:
        if k % 1440 == 0 or k == cfg["kend"]:
            log.w("MEASURED   k %5d (%5.1f h): n %d, median %.3e m, largest %.3e m, zero %d" % (k, k * 15.0 / 3600.0, n, md, mx, z))
    km = max(div, key=lambda x: x[3])
    kd = max(div, key=lambda x: x[2])
    log.w("MEASURED the largest distance over the run: %.3e m at k %d; the largest median: %.3e m at k %d; checkpoints %d, k %d to %d" % (
        km[3], km[0], kd[2], kd[0], len(div), div[0][0], div[-1][0]))
    log.w("RESULT H7(f): %s (at T_s; after it a measurement)" % ("PASS" if ok else "FAIL"))
    return ok


# ------------------------------------------------------------------ the timeline
def timeline(log, sl, cm, steps, decays, xs):
    log.w("\n# ---- the long run's timeline (the service log; local -0700)")
    keep = ("CLOCK", "START", "RESTART", "EXIT", "TRACK", "END:", "SLOTS", "PAUSEFILE", "PAUSE")
    for t, kind, rest in sl:
        if kind in keep or (kind in ("FETCH", "CHECK") and (" ended" in rest)):
            log.w("# %s %s %s" % (t, kind, rest[:200]))
    nrw = sum(1 for t, kind, rest in sl if kind == "REWRITE")
    ndiff = sum(1 for t, kind, rest in sl if kind == "REWRITE" and " 0 differ" not in rest)
    nrs = sum(1 for t, kind, rest in sl if kind == "RESTART")
    log.w("MEASURED restarts %d; REWRITE comparisons %d, with a difference %d" % (nrs, nrw, ndiff))
    for tr, w, k, i, r in sorted(set(decays)):
        log.w("MEASURED decay: track %s worker %s, idx %d below RMIN at step %d (due %s)" % (tr, w, i, k, lt(cm["unix_ref"] + 15.0 * k)))
    last = {}
    for (tr, w), L in steps.items():
        k = max(x for x in L if isinstance(x, int))
        st, fi, du, lag = L[k]
        if tr not in last or fi > last[tr][0]:
            last[tr] = (fi, lag, w)
    for tr in sorted(last):
        log.w("MEASURED %s: the last step %d finished at %s by %s, %.1f s after its due time" % (tr, max(x for x in steps[(tr, last[tr][2])] if isinstance(x, int)), lt(last[tr][0]), last[tr][2], last[tr][1]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--box", required=True)
    ap.add_argument("--r2", required=True)
    ap.add_argument("--leaps", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--logdir", default=os.path.join(os.path.dirname(SCRIPT), "..", "studies", "debris-h", "logs"))
    ap.add_argument("--keep", default=os.path.join(os.path.dirname(SCRIPT), "..", "studies", "debris-h", "scripts"))
    ap.add_argument("--cpu", default=None)
    ap.add_argument("--resumed", default="18")
    ap.add_argument("--no-d1", action="store_true")
    ap.add_argument("--note", default="")
    a = ap.parse_args()
    a.resumed = [int(x) for x in a.resumed.split(",") if x]
    acct = H.CpuAccount("h_analyze", a.cpu) if a.cpu else None
    log = H.Log("h_analyze", a.logdir, SCRIPT, CRITERIA, keep_dir=a.keep)
    outdir = os.path.join(a.out, "h_analyze.%03d" % log.n)
    os.makedirs(outdir)
    log.w("# per-object tables: %s (the ledger)" % outdir.replace(os.sep, "/"))
    H.load_leaps(a.leaps)
    c3 = check_inputs(a, log)
    cfg = json.load(open(os.path.join(a.box, "svc", "service.json"), encoding="ascii"))
    cm = json.load(open(os.path.join(a.box, "svc", "clock_map.json"), encoding="ascii"))
    meta = read_meta(os.path.join(a.r2, "seed", "seed_meta.tsv"))
    sl = service_lines(a)
    log.w("# the run: T_s %s TDB s (%s local), %d objects, steps 1..%d, tracks %s; unix_ref %.6f" % (
        float.hex(cfg["ts"]), lt(cm["unix_ref"]), cfg["nobj"], cfg["kend"], ", ".join("%s %s x%d" % (t["name"], t["kind"], t["workers"]) for t in cfg["tracks"]), cm["unix_ref"]))
    steps, pauses, decays, xs, ckc = read_steps(a)
    timeline(log, sl, cm, steps, decays, xs)
    res = {}
    res["a"], req, slots = eval_a(a, log, sl)
    res["b"], rows, t3hits, sets_by, first_abs = eval_b(a, log, meta, cfg, sl, slots, decays)
    t3_split(a, log, meta, rows, t3hits, outdir)
    res["c"] = eval_c(log, rows)
    _, man = read_tsv_hashhead(os.path.join(a.box, "svc", "manifest.tsv"))
    res["d"], _ = eval_d(a, log, cfg, c3, a.no_d1)
    res["e"] = eval_e(a, log, cfg, cm, sl, steps, pauses)
    res["f"] = eval_f(a, log, cfg, sl, man)
    measurements(log, rows, outdir, meta)
    # the departures and decays, per object, to the ledger
    lines = ["# h_analyze: departures (absent from the group's fetched file) and decays, per object (the ledger only)", "kind\tidx\tcat\tgroup\tslot_or_step\ttrack\tr_m"]
    for i, j in sorted(first_abs.items()):
        lines.append("\t".join(["departure", str(i), meta[i]["cat"], meta[i]["group"], str(j), "", ""]))
    for tr, w, k, i, r in sorted(set(decays)):
        lines.append("\t".join(["decay", str(i), meta[i]["cat"], meta[i]["group"], str(k), tr, "%.3f" % r]))
    H.write_new(os.path.join(outdir, "departures_decays.tsv"), ("\n".join(lines) + "\n").encode("utf-8"))
    for f in sorted(os.listdir(outdir)):
        log.w("# ledger table %s sha256 %s" % (f, sha_file(os.path.join(outdir, f))))
    lab = {True: "PASS", False: "FAIL", None: "NOT DETERMINED"}
    log.w("\n# H7: " + "; ".join("(%s) %s" % (k, lab[v]) for k, v in sorted(res.items())))
    cpu = acct.close("h_analyze log %s%s" % (os.path.basename(log.path), (" " + a.note) if a.note else "")) if acct else None
    if cpu is not None:
        log.w("# CPU (cycles / 2.5e9): %.1f s" % cpu)
    return log.close()


if __name__ == "__main__":
    sys.exit(main())
