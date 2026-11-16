# f5_sample.py - cft-debris M1 (DEBRIS-F), B3: CelesTrak's CSV, the decoder's build check, and F5(d)'s sample.
# cft-debris, MIT licence (see LICENSE at the repository root). Written by DEBRIS-F, 2026-11-16, before S0's values
# were read (the header and the first two `stations` rows had been printed once; both objects are in the sample by
# its rule whatever their values).
#
#   python -I -B tests/f5_sample.py <snapshot tag, e.g. S0>
#
# Writes, into the scratch (GP data and anything derived object by object stay out of the repository):
#   <tag>_objects.tsv  every row parsed, with its group, its key, and whether Orekit built it;
#   <tag>_orekit_in.txt the decoder's input lines (Orekit's units);
#   S0 only: f5d_sample.txt  the 100 keys of F5(d)'s sample.
# The log, in studies/debris-f/logs/, holds counts only.
import os
import random
import sys
from fractions import Fraction

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import f_lib as F  # noqa: E402

GROUPS = ["stations", "fengyun-1c-debris", "iridium-33-debris", "cosmos-2251-debris"]
COLUMNS = ["OBJECT_NAME", "OBJECT_ID", "EPOCH", "MEAN_MOTION", "ECCENTRICITY", "INCLINATION", "RA_OF_ASC_NODE",
           "ARG_OF_PERICENTER", "MEAN_ANOMALY", "EPHEMERIS_TYPE", "CLASSIFICATION_TYPE", "NORAD_CAT_ID", "ELEMENT_SET_NO",
           "REV_AT_EPOCH", "BSTAR", "MEAN_MOTION_DOT", "MEAN_MOTION_DDOT"]
SEED = 0xF5D
NSAMPLE = 100

CRITERIA = """
THE PARSER: each snapshot file's header must be exactly CelesTrak's 17 columns, in this order: OBJECT_NAME, OBJECT_ID,
  EPOCH, MEAN_MOTION, ECCENTRICITY, INCLINATION, RA_OF_ASC_NODE, ARG_OF_PERICENTER, MEAN_ANOMALY, EPHEMERIS_TYPE,
  CLASSIFICATION_TYPE, NORAD_CAT_ID, ELEMENT_SET_NO, REV_AT_EPOCH, BSTAR, MEAN_MOTION_DOT, MEAN_MOTION_DDOT; every row is
  read by those names (the csv module; OBJECT_NAME may hold commas inside quotes); NORAD_CAT_ID is read as an integer
  of any width (6-digit numbers included); every number is kept as its decimal string.
THE UNITS Orekit's TLE constructor takes (by reflection and a probe of its own TLE parser, DEBRIS-F's scratch):
  n = MEAN_MOTION x pi / 43200 rad/s; ndot = MEAN_MOTION_DOT x pi / 1.86624e9 rad/s^2 (the field is ndot/2 in
  rev/day^2, as in the TLE); nddot = MEAN_MOTION_DDOT x pi / 5.3747712e13 rad/s^3 (the field is nddot/6 in rev/day^3);
  angles x pi / 180; BSTAR as given (1/earth radii); e as given; each a binary64 from Python float arithmetic in that
  order; the epoch is the EPOCH string itself, parsed by Orekit as UTC.
THE SAMPLE (F5(d)), fixed here before S0's values are read:
  - ephemeris type 0 only; rows of another type are excluded and counted;
  - an object in two groups is kept once, in the first of stations, fengyun-1c-debris, iridium-33-debris,
    cosmos-2251-debris (counted);
  - any object Orekit cannot build (its TLE constructor or TLEPropagator.selectExtrapolator throws) is excluded and
    counted;
  - 100 objects: every remaining `stations` object, and the rest drawn from the other three groups in proportion to
    their remaining sizes (largest remainders, ties to the earlier group), each group's share drawn by
    random.Random(0xF5D).sample over its keys in file order.
"""


def parse(tag):
    rows = []
    for g in GROUPS:
        path = F.gp_csv(g, tag)
        import csv
        with open(path, "r", encoding="utf-8", newline="") as f:
            rd = csv.reader(f)
            head = next(rd)
            if head != COLUMNS:
                raise SystemExit("header of %s is %s" % (path, head))
            for r in rd:
                if not r:
                    continue
                d = dict(zip(COLUMNS, r))
                d["GROUP"] = g
                rows.append(d)
    return rows


def orekit_line(d, key):
    pi = 3.141592653589793
    oid = d["OBJECT_ID"]
    try:
        ly = int(oid[:4]) if len(oid) >= 4 else 0
        ln = int(oid[5:8]) if len(oid) >= 8 else 0
        lp = oid[8:] if len(oid) > 8 else "A"
    except ValueError:
        ly, ln, lp = 0, 0, "A"
    lp = lp or "A"
    vals = [float(d["MEAN_MOTION"]) * pi / 43200.0, float(d["MEAN_MOTION_DOT"]) * pi / 1.86624e9,
            float(d["MEAN_MOTION_DDOT"]) * pi / 5.3747712e13, float(d["ECCENTRICITY"]),
            float(d["INCLINATION"]) * pi / 180.0, float(d["ARG_OF_PERICENTER"]) * pi / 180.0,
            float(d["RA_OF_ASC_NODE"]) * pi / 180.0, float(d["MEAN_ANOMALY"]) * pi / 180.0]
    return ("OBJ %s %d %s %d %d %s %d %d %s %s %d %s" % (key, int(d["NORAD_CAT_ID"]), d["CLASSIFICATION_TYPE"] or "U", ly, ln, lp,
            int(d["EPHEMERIS_TYPE"]), int(d["ELEMENT_SET_NO"]), d["EPOCH"], " ".join(float.hex(v) for v in vals),
            int(d["REV_AT_EPOCH"]), float.hex(float(d["BSTAR"])))), vals


def main():
    tag = sys.argv[1] if len(sys.argv) > 1 else "S0"
    log = F.Log("f5_sample_%s" % tag, os.path.abspath(__file__), CRITERIA, extra_files=[os.path.join(F.REPO, "tests", "f5_sgp4.js")])
    W = F.gp_dir(tag)
    os.makedirs(W, exist_ok=True)
    rows = parse(tag)
    log.w("# %s rows read: %d (%s)" % (tag, len(rows), ", ".join("%s %d" % (g, sum(1 for r in rows if r["GROUP"] == g)) for g in GROUPS)))
    seen, keep, nt, ndup = set(), [], 0, 0
    for d in rows:
        if d["EPHEMERIS_TYPE"] != "0":
            nt += 1
            continue
        cat = int(d["NORAD_CAT_ID"])
        if cat in seen:
            ndup += 1
            continue
        seen.add(cat)
        keep.append(d)
    log.w("# excluded: ephemeris type not 0: %d; duplicates across groups: %d; largest catalogue number %d (digits %d)"
          % (nt, ndup, max(seen), len(str(max(seen)))))
    with open(W + "/%s_orekit_in.txt" % tag, "w", newline="\n") as f:
        for d in keep:
            line, _ = orekit_line(d, d["NORAD_CAT_ID"])
            f.write(line + " 0\n")
    F.orekit(os.path.join(F.REPO, "tests", "f5_sgp4.js"), ["build", F.DATA + "/orekit", W + "/%s_orekit_in.txt" % tag, W + "/%s_built.txt" % tag],
             log, cpu_label="f5_build_%s" % tag)
    ok, fail = set(), {}
    for ln in open(W + "/%s_built.txt" % tag):
        p = ln.split()
        if p and p[0] == "B":
            ok.add(p[1])
        elif p and p[0] == "F":
            fail[p[1]] = p[2] if len(p) > 2 else ""
    log.w("# Orekit built %d; refused %d" % (len(ok), len(fail)))
    for k, why in sorted(fail.items())[:20]:
        log.w("#   refused: %s" % why[:120])
    log.check(len(ok) + len(fail) == len(keep), "every kept row was tried (%d + %d = %d)" % (len(ok), len(fail), len(keep)))
    with open(W + "/%s_objects.tsv" % tag, "w", newline="\n") as f:
        f.write("key\tgroup\tname\tepoch\tbuilt\n")
        for d in keep:
            f.write("%s\t%s\t%s\t%s\t%d\n" % (d["NORAD_CAT_ID"], d["GROUP"], d["OBJECT_NAME"], d["EPOCH"], d["NORAD_CAT_ID"] in ok))
    if tag == "S0":
        pool = {g: [d["NORAD_CAT_ID"] for d in keep if d["GROUP"] == g and d["NORAD_CAT_ID"] in ok] for g in GROUPS}
        sample = list(pool["stations"])
        rest = NSAMPLE - len(sample)
        others = GROUPS[1:]
        tot = sum(len(pool[g]) for g in others)
        quota = {g: rest * len(pool[g]) // tot for g in others}
        rema = sorted(others, key=lambda g: (-((rest * len(pool[g])) % tot), GROUPS.index(g)))
        for g in rema[:rest - sum(quota.values())]:
            quota[g] += 1
        rng = random.Random(SEED)
        for g in others:
            sample += rng.sample(pool[g], quota[g])
        log.w("# sample: stations %d, %s; total %d" % (len(pool["stations"]), ", ".join("%s %d of %d" % (g, quota[g], len(pool[g])) for g in others), len(sample)))
        log.check(len(sample) == NSAMPLE and len(set(sample)) == NSAMPLE, "F5(d)'s sample holds 100 distinct objects")
        with open(W + "/f5d_sample.txt", "w", newline="\n") as f:
            for k in sample:
                f.write(k + "\n")
        log.w("# sample keys written to the scratch (gp/f5d_sample.txt), sha256 %s" % F.sha256(W + "/f5d_sample.txt"))
    return log.close()


if __name__ == "__main__":
    sys.exit(main())
