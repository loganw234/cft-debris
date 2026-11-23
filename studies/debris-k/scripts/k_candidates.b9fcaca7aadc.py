# k_candidates.py - cft-debris (DEBRIS-K), Q1: a rule that picks LEO objects likely to decay within the prediction
# windows (1, 3, 7 and 30 days) from element sets alone, applied to the ledger's sets (S_H0 and DEBRIS-H's slots).
# Standard library only; the desktop. Reads; writes one numbered log (counts only) and a per-object table (the ledger).
# cft-debris, MIT licence (see LICENSE at the repository root). Written by DEBRIS-K, 2026-11-23, before the rule was
# applied to any set. The scale heights are read at run time from M1's own table, src/m1_consts.h (DEBRIS-B's), not
# copied.
#
#   python -I -B k_candidates.py --r2 DIR --downloads DIR --consts src/m1_consts.h --leaps FILE --out DIR --logs DIR
#        --keep DIR --cpu TSV
import argparse
import math
import os
import re
import sys
from fractions import Fraction

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import k_lib as H  # noqa: E402

SCRIPT = os.path.abspath(__file__)
GM = 3.986004415e14
RE = 6378137.0
WINDOWS = [1, 3, 7, 30]

CRITERIA = """
Q1's RULE, fixed before it is applied (a measurement with no pass condition):
SETS: every catalogue number's sets in S_H0 (the downloads' gp-*-SH0) and in DEBRIS-H's slot folders 1 to 20, ephemeris
  type 0, taken in that order; a set is kept if its epoch is later than the object's previous kept set's (as the pilot).
LOOKS: S_H0's (the run's start), then each slot's fetch; at each look every object's latest kept set so far.
FROM THE LATEST SET: n (rev/day) and e; a = (GM / n^2)^(1/3) with n in rad/s, GM = 3.986004415e14 m^3/s^2; perigee
  hp = a(1 - e) - 6,378,137 m and apogee ha = a(1 + e) - 6,378,137 m. LEO: ha under 2,000 km.
THE DECAY RATE: ndot_tle = 2 x MEAN_MOTION_DOT (rev/day^2; the TLE's ndot/2, DEBRIS-F's belief); ndot_emp = the change
  of mean motion between the object's earliest and latest kept sets so far, over their epochs, where these lie at least
  12 h apart; ndot = the larger of those that exist. No decay signal where ndot <= 0 (counted; BSTAR <= 0 counted beside).
THE ESTIMATE: adot = -(2/3) a ndot / n; tau = (a e + Hs) / |adot|, Hs the scale height of M1's 28-band table in the band
  holding hp (src/m1_consts.h): a circular orbit's H/|adot| plus the time for the apogee to come down at the same rate.
  An ESTIMATE of the time to re-entry from one scale height and one rate; its range is taken as a factor of 3 either way.
CANDIDATES for each window W of 1, 3, 7 and 30 days: 'point' where tau <= W; 'wide' where tau <= 3 W.
COUNTS: per look and window (point and wide); the union over the looks; at the first look, how many wide candidates
  later left their group's files (absent from a later fetch that holds the group); and seed indices 1595 and 1178 with
  their tau at the first look (two validation points, not a measure of skill: one SATCAT decay, one M1 decay).
"""


def bands(path):
    txt = open(path, encoding="ascii").read()

    def arr(name):
        m = re.search(r"%s\[28\]\s*=\s*\{([^}]*)\}" % name, txt)
        assert m, name
        return [float(x) for x in re.findall(r'"([^"]+)"', m.group(1))]
    h0, hs = arr("M1_ATM_H0"), arr("M1_ATM_HS")
    assert len(h0) == 28 and len(hs) == 28
    return h0, hs


def hs_at(h, h0, hs):
    k = 0
    for i, b in enumerate(h0):
        if h >= b:
            k = i
    return hs[k]


def elems(r):
    n = float(r["MEAN_MOTION"])
    nr = n * 2 * math.pi / 86400.0
    a = (GM / (nr * nr)) ** (1.0 / 3.0)
    e = float(r["ECCENTRICITY"])
    return n, nr, a, e, a * (1 - e) - RE, a * (1 + e) - RE


def main():
    ap = argparse.ArgumentParser()
    for o in ("--r2", "--downloads", "--consts", "--leaps", "--out", "--logs", "--keep", "--cpu"):
        ap.add_argument(o, required=True)
    a = ap.parse_args()
    cpu = H.CpuAccount("k_candidates", a.cpu)
    log = H.Log("k_candidates", a.logs, SCRIPT, CRITERIA, keep_dir=a.keep)
    H.load_leaps(a.leaps)
    h0, hsb = bands(a.consts)
    log.w("# %s sha256 %s (the 28 bands' bases and scale heights read from it)" % (os.path.basename(a.consts), H.sha256(a.consts)))
    meta = {}
    head = None
    mp = os.path.join(a.r2, "seed", "seed_meta.tsv")
    for ln in open(mp, encoding="ascii"):
        if ln.startswith("#"):
            continue
        q = ln.rstrip("\n").split("\t")
        if head is None:
            head = q
            continue
        d = dict(zip(head, q))
        meta[int(d["cat"])] = int(d["idx"])
    fetch = os.path.join(a.r2, "svc", "fetch")
    looks = [("SH0", None)] + [("slot%02d" % j, j) for j in range(1, 21) if os.path.isdir(os.path.join(fetch, "slot%02d" % j))]
    hist = {}
    present = {}   # look -> {group: set of catalogue numbers}
    res = {}
    for name, j in looks:
        rows = []
        present[name] = {}
        if j is None:
            for g in H.GROUPS:
                p = os.path.join(a.downloads, "gp-%s-SH0" % g, "gp-%s-SH0.csv" % g)
                rg = H.read_gp(p, g)
                present[name][g] = {int(r["NORAD_CAT_ID"]) for r in rg}
                rows += rg
                log.w("# %s/%s sha256 %s" % (name, os.path.basename(p), H.sha256(p)))
        else:
            for g, (p, rg) in sorted(H.read_slot(fetch, j).items()):
                present[name][g] = {int(r["NORAD_CAT_ID"]) for r in rg}
                rows += rg
                log.w("# %s/%s sha256 %s" % (name, os.path.basename(p), H.sha256(p)))
        for r in sorted((r for r in rows if r["EPHEMERIS_TYPE"] == "0"), key=lambda r: (int(r["NORAD_CAT_ID"]), H.epoch_tdb(r))):
            c = int(r["NORAD_CAT_ID"])
            e = H.epoch_tdb(r)
            if c in hist and not e > hist[c][-1][0]:
                continue
            hist.setdefault(c, []).append((e, r))
        out = {}
        for c, hs in hist.items():
            e1, r1 = hs[-1]
            n, nr, aa, ee, hp, ha = elems(r1)
            if not ha < 2000e3:
                continue
            nd_t = 2.0 * float(r1["MEAN_MOTION_DOT"])
            nd_e = None
            e0, r0 = hs[0]
            if float(e1 - e0) >= 12 * 3600:
                nd_e = (n - float(r0["MEAN_MOTION"])) / (float(e1 - e0) / 86400.0)
            nd = max(x for x in (nd_t, nd_e) if x is not None)
            tau = None
            if nd > 0:
                ndr = nd * 2 * math.pi / 86400.0 ** 2
                adot = -(2.0 / 3.0) * aa * ndr / nr
                tau = (aa * ee + hs_at(hp, h0, hsb)) / abs(adot) / 86400.0
            out[c] = {"tau": tau, "hp": hp, "ha": ha, "bstar": float(r1["BSTAR"]), "nd_t": nd_t, "nd_e": nd_e, "nsets": len(hs)}
        res[name] = out
    for name, _ in looks:
        o = res[name]
        nosig = sum(1 for v in o.values() if v["tau"] is None)
        nb = sum(1 for v in o.values() if v["bstar"] <= 0)
        log.w("MEASURED look %s: %d LEO objects with a set; no decay signal (ndot <= 0) %d; BSTAR <= 0 %d; %s" % (
            name, len(o), nosig, nb, "; ".join("%d d: point %d, wide %d" % (W, sum(1 for v in o.values() if v["tau"] is not None and v["tau"] <= W),
                                                                             sum(1 for v in o.values() if v["tau"] is not None and v["tau"] <= 3 * W))
                                                for W in WINDOWS)))
    for W in WINDOWS:
        up = set()
        uw = set()
        for name, _ in looks:
            for c, v in res[name].items():
                if v["tau"] is not None and v["tau"] <= W:
                    up.add(c)
                if v["tau"] is not None and v["tau"] <= 3 * W:
                    uw.add(c)
        log.w("MEASURED union over the %d looks, window %d d: point %d objects, wide %d" % (len(looks), W, len(up), len(uw)))
    # departures of the first look's wide candidates
    first = res["SH0"]

    def group_of(c):
        for g in H.GROUPS:
            if c in present["SH0"].get(g, set()):
                return g
        return None
    for W in WINDOWS:
        wide = [c for c, v in first.items() if v["tau"] is not None and v["tau"] <= 3 * W]
        gone = 0
        for c in wide:
            g = group_of(c)
            later = [name for name, _ in looks[1:] if g in present[name]]
            if later and c not in present[later[-1]][g]:
                gone += 1
        log.w("MEASURED first look's wide candidates for %d d: %d; of them absent from the last fetch holding their group: %d" % (W, len(wide), gone))
    for idx in (1595, 1178):
        c = [k for k, v in meta.items() if v == idx][0]
        v = first.get(c)
        if v and v["tau"] is not None:
            log.w("MEASURED seed index %d at the first look: tau %.2f d (perigee %.1f km, apogee %.1f km, ndot from the set %.3g, across sets %s rev/day^2)" % (
                idx, v["tau"], v["hp"] / 1e3, v["ha"] / 1e3, v["nd_t"], ("%.3g" % v["nd_e"]) if v["nd_e"] is not None else "-"))
        else:
            log.w("MEASURED seed index %d at the first look: no decay signal or not LEO" % idx)
    # per-object table (the ledger)
    os.makedirs(a.out, exist_ok=True)
    n, outp = H.next_numbered(a.out, "candidates", ".tsv")
    lines = ["# k_candidates: tau per object at each look (DEBRIS-K, the ledger only); log %s" % os.path.basename(log.path),
             "look\tcat\tseed_idx\tperigee_km\tapogee_km\tbstar\tndot_tle\tndot_emp\tnsets\ttau_d"]
    for name, _ in looks:
        for c, v in sorted(res[name].items()):
            if v["tau"] is not None and v["tau"] <= 90:
                lines.append("\t".join([name, str(c), str(meta.get(c, "")), "%.1f" % (v["hp"] / 1e3), "%.1f" % (v["ha"] / 1e3), "%.4g" % v["bstar"], "%.4g" % v["nd_t"],
                                        ("%.4g" % v["nd_e"]) if v["nd_e"] is not None else "", str(v["nsets"]), "%.3f" % v["tau"]]))
    H.write_new(outp, ("\n".join(lines) + "\n").encode("ascii"))
    log.w("# per-object table (tau up to 90 d) %s, %d rows, sha256 %s" % (os.path.basename(outp), len(lines) - 2, H.sha256(outp)))
    c_ = cpu.close("k_candidates log %03d" % log.n)
    if c_ is not None:
        log.w("# CPU: %.2f s by cycles / 2.5e9" % c_)
    return log.close()


if __name__ == "__main__":
    sys.exit(main())
