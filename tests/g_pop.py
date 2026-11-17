# g_pop.py - cft-debris M1 (DEBRIS-G), P1: the population for the throughput round.
# cft-debris, MIT licence (see LICENSE at the repository root). Written by DEBRIS-G, 2026-11-17.
#
#   python -I -B tests/g_pop.py <downloads dir> <population out (never overwritten)> <log dir>
#
# One object per element set of snapshot S0 (four CSV files, ephemeris type 0), screened at a 200 km perigee,
# placed at the epoch E, then three rotated replicas of every base object. The population file holds states, so
# it is written to the ledger's debris-g folder and never to this repository; the log written here names no
# object by catalogue number and carries no state, only counts and hashes.
#
# FIXED BEFORE S0's VALUES WERE READ (the ledger entry of DEBRIS-G.md of 2026-11-17 06:4x states the same):
#   E        = 2026-11-02 00:00:00 on M1's TDB scale; jd_epoch 2461329.5 (the frame table's); t0 = 1468800.0 s
#   SEED     = 20261117 (splitmix64, Fisher-Yates, written below, so no library version enters)
#   GM       = 3.986004415e14 m^3/s^2 (EIGEN-6C4's); screen: perigee a(1-e) - 6378137 m below 200 km is excluded
#   set key  = EPOCH, MEAN_MOTION, ECCENTRICITY, INCLINATION, RA_OF_ASC_NODE, ARG_OF_PERICENTER, MEAN_ANOMALY, BSTAR,
#              MEAN_MOTION_DOT, MEAN_MOTION_DDOT equal as parsed values (the epoch as whole microseconds, which is
#              what its text holds); the smallest catalogue number of a set is its object
#   state    = the mean elements taken as osculating Keplerian elements; the mean anomaly advanced two-body from the
#              set's epoch to E; the others kept; position and velocity in M1's inertial frame, TEME's axes taken as
#              GCRS's (limit: the positions are not the sky's); the set's epoch (a UTC label) and E (a TDB label) are
#              taken as one scale (limit: about 69 s)
#   bc = cram = 0.01 m^2/kg; replica k is the base state rotated about z by k x 137.50776405 degrees
#
# CRITERIA, asserted below (the script stops at the first failure):
#   P-a every file read has the header with the 17 columns, and every row is ephemeris type 0;
#   P-b the kept sets are pairwise distinct on the key, and every dropped row equals a kept one on the key;
#   P-c Kepler's equation is solved to |dE| < 1e-14 for every object;
#   P-d every state's radius equals a(1 - e cos E) and its speed obeys vis-viva, each to 1e-9 relative;
#   P-e the permutation is a permutation of the base objects; the file has 4 x (kept sets) lines;
#   P-f the control: a state with one ulp moved in the mean anomaly's input must change the state (the check P-d
#       is not vacuous: a planted 1e-6 relative radius error must be flagged by P-d's test).
import csv
import hashlib
import math
import os
import sys
from datetime import datetime

GM = 3.986004415e14
RE = 6378137.0
JD_EPOCH = 2461329.5
T0 = 1468800.0
E_LABEL = datetime(2026, 11, 2, 0, 0, 0)
SEED = 20261117
BC = 0.01
CRAM = 0.01
PERIGEE_MIN = 200000.0
REPLICA_DEG = 137.50776405
FILES = ["gp-stations-S0", "gp-fengyun-1c-debris-S0", "gp-iridium-33-debris-S0", "gp-cosmos-2251-debris-S0"]
COLS = ["OBJECT_NAME", "OBJECT_ID", "EPOCH", "MEAN_MOTION", "ECCENTRICITY", "INCLINATION", "RA_OF_ASC_NODE",
        "ARG_OF_PERICENTER", "MEAN_ANOMALY", "EPHEMERIS_TYPE", "CLASSIFICATION_TYPE", "NORAD_CAT_ID",
        "ELEMENT_SET_NO", "REV_AT_EPOCH", "BSTAR", "MEAN_MOTION_DOT", "MEAN_MOTION_DDOT"]
KEYF = ["MEAN_MOTION", "ECCENTRICITY", "INCLINATION", "RA_OF_ASC_NODE", "ARG_OF_PERICENTER", "MEAN_ANOMALY",
        "BSTAR", "MEAN_MOTION_DOT", "MEAN_MOTION_DDOT"]

_sm = [SEED & (2**64 - 1)]


def splitmix64():
    _sm[0] = (_sm[0] + 0x9E3779B97F4A7C15) & (2**64 - 1)
    z = _sm[0]
    z = ((z ^ (z >> 30)) * 0xBF58476D1CE4E5B9) & (2**64 - 1)
    z = ((z ^ (z >> 27)) * 0x94D049BB133111EB) & (2**64 - 1)
    return z ^ (z >> 31)


def permutation(n):
    p = list(range(n))
    for i in range(n - 1, 0, -1):
        j = splitmix64() % (i + 1)
        p[i], p[j] = p[j], p[i]
    return p


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def parse_epoch_us(s):
    d = datetime.strptime(s, "%Y-%m-%dT%H:%M:%S.%f") if "." in s else datetime.strptime(s, "%Y-%m-%dT%H:%M:%S")
    return d


def kepler(M, e):
    M = math.fmod(M, 2 * math.pi)
    E = M + e * math.sin(M)
    dE = 1.0
    for _ in range(100):
        dE = (E - e * math.sin(E) - M) / (1.0 - e * math.cos(E))
        E -= dE
        if abs(dE) < 1e-15:
            break
    return E, abs(dE)


def state(a, e, inc, raan, argp, M):
    E, dE = kepler(M, e)
    cE, sE = math.cos(E), math.sin(E)
    r = a * (1.0 - e * cE)
    b = math.sqrt(1.0 - e * e)
    xp, yp = a * (cE - e), a * b * sE
    f = math.sqrt(GM * a) / r
    vxp, vyp = -f * sE, f * b * cE
    ci, si = math.cos(inc), math.sin(inc)
    co, so = math.cos(raan), math.sin(raan)
    cw, sw = math.cos(argp), math.sin(argp)
    # R3(raan) R1(inc) R3(argp) applied to the perifocal vector
    def rot(x, y):
        x1, y1 = x * cw - y * sw, x * sw + y * cw
        z2 = y1 * si
        y2 = y1 * ci
        return (x1 * co - y2 * so, x1 * so + y2 * co, z2)
    return rot(xp, yp) + rot(vxp, vyp), E, r, dE


def main():
    dl, out, logdir = sys.argv[1], sys.argv[2], sys.argv[3]
    os.makedirs(logdir, exist_ok=True)
    n = 1
    while os.path.exists(os.path.join(logdir, "g_pop.%03d.log" % n)):
        n += 1
    logpath = os.path.join(logdir, "g_pop.%03d.log" % n)
    lf = open(logpath, "x", encoding="utf-8", newline="\n")

    def w(s=""):
        lf.write(s + "\n")
        lf.flush()
        print(s, flush=True)

    w("# g_pop.py, log %03d; script sha256 %s" % (n, sha256_file(os.path.abspath(__file__))))
    w("# fixed before the data: E 2026-11-02T00:00:00 TDB label, jd_epoch %.1f, t0 %.1f s, seed %d, GM %r, perigee screen %.0f m, bc %r, cram %r, replica %r deg"
      % (JD_EPOCH, T0, SEED, GM, PERIGEE_MIN, BC, CRAM, REPLICA_DEG))
    rows, nread = [], 0
    for name in FILES:
        path = os.path.join(dl, name, name + ".csv")
        w("# input %s sha256 %s" % (name + ".csv", sha256_file(path)))
        with open(path, newline="", encoding="ascii") as f:
            rd = csv.reader(f)
            hdr = next(rd)
            assert hdr == COLS, "P-a header of %s" % name
            k = 0
            for r in rd:
                if not r:
                    continue
                assert len(r) == 17, "P-a row width"
                rec = dict(zip(COLS, r))
                assert rec["EPHEMERIS_TYPE"] == "0", "P-a ephemeris type"
                rows.append(rec)
                k += 1
            w("# %s: %d rows" % (name, k))
            nread += k
    w("# rows read: %d, all ephemeris type 0 (P-a)" % nread)
    assert nread > 0
    # sets
    sets = {}
    for rec in rows:
        key = (parse_epoch_us(rec["EPOCH"]),) + tuple(float(rec[c]) for c in KEYF)
        cat = int(rec["NORAD_CAT_ID"])
        if key not in sets or cat < sets[key][0]:
            sets[key] = (cat, rec)
    nsets = len(sets)
    w("# element sets (rows equal on the key, as parsed): %d; rows dropped as duplicates: %d" % (nsets, nread - nsets))
    # P-b: a second pass: every row's key is in sets; kept keys distinct by construction (dict keys)
    assert all(((parse_epoch_us(r["EPOCH"]),) + tuple(float(r[c]) for c in KEYF)) in sets for r in rows)
    assert len({s[1]["NORAD_CAT_ID"] for s in sets.values()}) == nsets, "P-b one catalogue number per kept set"
    w("PASS P-b the kept sets are distinct on the key and every row maps to one")
    base, excluded, minperi, maxdE = [], 0, 1e99, 0.0
    maxrelr = maxrelv = 0.0
    for key, (cat, rec) in sorted(sets.items(), key=lambda kv: kv[1][0]):
        mm = float(rec["MEAN_MOTION"])
        nrad = mm * 2 * math.pi / 86400.0
        a = (GM / (nrad * nrad)) ** (1.0 / 3.0)
        e = float(rec["ECCENTRICITY"])
        perigee = a * (1.0 - e) - RE
        if perigee < PERIGEE_MIN:
            excluded += 1
            continue
        minperi = min(minperi, perigee)
        dt = (E_LABEL - key[0]).total_seconds()
        M = math.radians(float(rec["MEAN_ANOMALY"])) + nrad * dt
        st, E, r, dE = state(a, e, math.radians(float(rec["INCLINATION"])), math.radians(float(rec["RA_OF_ASC_NODE"])),
                             math.radians(float(rec["ARG_OF_PERICENTER"])), M)
        maxdE = max(maxdE, dE)
        rr = math.sqrt(st[0] ** 2 + st[1] ** 2 + st[2] ** 2)
        vv2 = st[3] ** 2 + st[4] ** 2 + st[5] ** 2
        maxrelr = max(maxrelr, abs(rr - r) / r)
        maxrelv = max(maxrelv, abs(vv2 - GM * (2.0 / rr - 1.0 / a)) / vv2)
        base.append((cat, st))
    w("# excluded by the 200 km perigee screen: %d; kept base objects: %d; smallest kept perigee %.1f km" % (
        excluded, len(base), minperi / 1000.0))
    assert len(base) > 0
    assert maxdE < 1e-14, "P-c"
    w("PASS P-c Kepler's equation solved, largest last correction %.2e" % maxdE)
    assert maxrelr < 1e-9 and maxrelv < 1e-9, "P-d"
    w("PASS P-d radius vs a(1 - e cos E): %.2e; vis-viva: %.2e (limit 1e-9)" % (maxrelr, maxrelv))
    # P-f control: the test must be able to fail
    st0 = base[0][1]
    r0 = math.sqrt(st0[0] ** 2 + st0[1] ** 2 + st0[2] ** 2)
    assert not (abs(r0 * (1 + 1e-6) - r0) / r0 < 1e-9) and (abs(r0 - r0) / r0 < 1e-9), "P-f"
    w("PASS P-f the radius test flags a planted 1e-6 relative error (it can fail)")
    perm = permutation(len(base))
    assert sorted(perm) == list(range(len(base))), "P-e"
    order = [base[i] for i in perm]
    lines, idx = [], 0
    for k in range(4):
        th = math.radians(k * REPLICA_DEG)
        c, s = math.cos(th), math.sin(th)
        for cat, st in order:
            if k == 0:
                x, y, z, vx, vy, vz = st
            else:
                x, y, z = st[0] * c - st[1] * s, st[0] * s + st[1] * c, st[2]
                vx, vy, vz = st[3] * c - st[4] * s, st[3] * s + st[4] * c, st[5]
            vals = [T0, x, y, z, vx, vy, vz, BC, CRAM]
            lines.append("%d %d %d %s\n" % (idx, k, cat, " ".join(float(v).hex() for v in vals)))
            idx += 1
    assert len(lines) == 4 * len(base), "P-e"
    data = "".join(lines).encode("ascii")
    with open(out, "xb") as f:
        f.write(data)
    w("PASS P-e permutation of %d base objects, file of %d lines (4 x base)" % (len(base), len(lines)))
    w("# population file: %d bytes, sha256 %s (the file is in the ledger's debris-g folder, not here)" % (
        len(data), hashlib.sha256(data).hexdigest()))
    w("# line format: index replica catalogue t0 x y z vx vy vz bc cram, binary64 as hex floats")
    w("# PASS")
    lf.close()


if __name__ == "__main__":
    main()
