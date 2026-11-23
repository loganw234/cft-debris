# k_swcopy.py - cft-debris (DEBRIS-K): the derived copies of CelesTrak's SW-Last5Years.txt that the pilot's comparator
# (C) reads, made as DEBRIS-F made them under the lead's rulings (lead.md, 2026-11-16, and studies/DEBRIS-F-build.md
# section 6, finding 1): Orekit 13.1.9's CssiSpaceWeatherData refuses the approved file as served.
# cft-debris, MIT licence (see LICENSE at the repository root). Copied by DEBRIS-K, 2026-11-23, from DEBRIS-F's
# tests/f6_swcopy.py (cft-debris's own, MIT; version 77f68cf9..., the one DEBRIS-F's report names). What changed:
#   - every path comes from the arguments (DEBRIS-F's f_lib.py, which names DEBRIS-F's scratch, is not imported), and
#     the output is a numbered log through k_lib.py;
#   - only stage 3 is made (the three normalisations together): DEBRIS-F showed stages 1 and 2 insufficient (READ,
#     its finding 1), and the lead's stage-3 ruling is the one (C) ran under;
#   - ASSERTED in addition: the 0-filled copy's SHA-256 equals DEBRIS-F's, 47acbcc2...c9a, which the lead matched
#     independently (READ, DEBRIS-F's report).
# The functions section(), daily_lines(), line_positions(), marker_line(), normalise() and check() are DEBRIS-F's, as
# they were with --stage3 given.
#
#   python -I -B k_swcopy.py --src SW-Last5Years.txt --finals finals2000A.daily --leaps tai-utc.dat --data DIR
#        --logs DIR --keep DIR
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import k_lib as H  # noqa: E402

SCRIPT = os.path.abspath(__file__)
SRC_SHA = "718bae83ef2786d77b5e5d11647bf5b984986f0d0213b1080c5d4d6b514948fb"
FILL0_SHA_F = "47acbcc2c5bb5bb8c6425d0f7873e77a82f44d57cac5c655bdf6ae05a2c88c9a"
MONTHLY = True
STAGE3 = True
MARK_OLD, MARK_NEW = b"BEGIN MONTHLY_PREDICTED", b"BEGIN MONTHLY_FIT"
FIELDS = ([(1, 4), (5, 7), (8, 10), (11, 15), (16, 18)] + [(19 + 3 * i, 21 + 3 * i) for i in range(8)] + [(43, 46)] +
          [(47 + 4 * i, 50 + 4 * i) for i in range(8)] + [(79, 82), (83, 86), (87, 88), (89, 92), (93, 98), (99, 100)] +
          [(101 + 6 * i, 106 + 6 * i) for i in range(5)])
CRITERIA = """
ASSERTED (DEBRIS-F's, stated before the run): each copy has the original's line count and CRLF endings; every line
equals the original's but (a) the filled lines, which differ only at the fill positions, each blank in the original, and
(b) exactly one more line, "BEGIN MONTHLY_PREDICTED" become "BEGIN MONTHLY_FIT". CONTROL: a second change planted into
the finished copy (one digit of the first OBSERVED line) must fail that check. ADDED: the 0-filled copy's SHA-256 is
DEBRIS-F's 47acbcc2...c9a; the original's is the approved 718bae83...48fb.
"""


def section(lines, name):
    i = next(k for k, l in enumerate(lines) if l.startswith(b"BEGIN " + name))
    j = next(k for k, l in enumerate(lines) if l.startswith(b"END " + name))
    return list(range(i + 1, j))


def daily_lines(lines):
    return section(lines, b"DAILY_PREDICTED")


def line_positions(orig):
    """(line index, 0-based column) of every byte the fill sets"""
    lines = orig.split(b"\n")
    pos = [(k, 99) for k in daily_lines(lines)]
    if MONTHLY:
        for k in section(lines, b"MONTHLY_PREDICTED"):
            l = lines[k].rstrip(b"\r")
            assert len(l) >= 130, "a MONTHLY_PREDICTED line shorter than 130 columns"
            for a, b in FIELDS:
                if l[a - 1:b].strip() == b"":
                    pos.append((k, b - 1))
    return pos


def marker_line(lines):
    ks = [k for k, l in enumerate(lines) if l.rstrip(b"\r") == MARK_OLD]
    assert len(ks) == 1, "exactly one line BEGIN MONTHLY_PREDICTED"
    return ks[0]


def normalise(orig, digit):
    lines = orig.split(b"\n")
    for k, c in line_positions(orig):
        l = bytearray(lines[k])
        l[c] = ord(digit)
        lines[k] = bytes(l)
    if STAGE3:
        k = marker_line(lines)
        lines[k] = MARK_NEW + lines[k][len(MARK_OLD):]
    return b"\n".join(lines)


def check(orig, copy):
    """True when copy is orig with exactly the stage's normalisations (see the header)"""
    lo, lc = orig.split(b"\n"), copy.split(b"\n")
    if len(lo) != len(lc) or orig.count(b"\r\n") != copy.count(b"\r\n"):
        return False
    fills = {}
    for k, c in line_positions(orig):
        fills.setdefault(k, set()).add(c)
    mk = marker_line(lo) if STAGE3 else -1
    nfill = 0
    for k, (a, b) in enumerate(zip(lo, lc)):
        if k == mk:
            if b != MARK_NEW + a[len(MARK_OLD):]:
                return False
            continue
        if a == b and k not in fills:
            continue
        if len(a) != len(b) or k not in fills:
            return False
        diff = {i for i in range(len(a)) if a[i] != b[i]}
        if diff != fills[k] or any(a[i] != 32 for i in diff):
            return False
        nfill += len(diff)
    return nfill == sum(len(v) for v in fills.values())


def put(path, data):
    if os.path.exists(path):
        assert open(path, "rb").read() == data, "%s exists with other bytes" % path
    else:
        H.write_new(path, data)


def main():
    ap = argparse.ArgumentParser()
    for o in ("--src", "--finals", "--leaps", "--data", "--logs", "--keep"):
        ap.add_argument(o, required=True)
    a = ap.parse_args()
    log = H.Log("k_swcopy", a.logs, SCRIPT, CRITERIA, keep_dir=a.keep)
    orig = open(a.src, "rb").read()
    h = H.sha256(a.src)
    log.w("# original sha256 %s (%d bytes, %d lines, %d CRLF)" % (h, len(orig), orig.count(b"\n"), orig.count(b"\r\n")))
    log.check(h == SRC_SHA, "the approved file's SHA-256")
    lines = orig.split(b"\n")
    dl = daily_lines(lines)
    log.check(len(dl) == 45 and all(lines[k][98:100] == b"  " for k in dl), "45 DAILY_PREDICTED lines, each qualifier blank (%s to %s)" % (
        lines[dl[0]][:10].decode(), lines[dl[-1]][:10].decode()))
    npos = len(line_positions(orig))
    log.w("# MONTHLY_PREDICTED data lines: %d; bytes the fill sets in them: %d; the marker line %d renamed" % (
        len(section(lines, b"MONTHLY_PREDICTED")), npos - 45, marker_line(lines) + 1))
    out = {}
    for digit in ("0", "4"):
        c = normalise(orig, digit)
        log.check(check(orig, c), "placeholder %s: the copy is the original with exactly the three normalisations (%d filled bytes)" % (digit, npos))
        out[digit] = c
    bad = out["0"].split(b"\n")
    i = next(k for k, l in enumerate(bad) if l.startswith(b"BEGIN OBSERVED")) + 1
    l = bytearray(bad[i])
    l[3] = ord("9") if l[3] != ord("9") else ord("8")
    bad[i] = bytes(l)
    log.check(not check(orig, b"\n".join(bad)), "CONTROL: a second change planted into the finished copy fails the check")
    pl = out["0"].split(b"\n")
    k = next(k for k in dl if pl[k].startswith(b"2026 11 16"))
    l = bytearray(pl[k])
    l[92:98] = b" 150.0"
    l[112:118] = b" 150.0"
    pl[k] = bytes(l)
    planted = b"\n".join(pl)
    for name, data in (("sw3_fill0", out["0"]), ("sw3_fill4", out["4"]), ("sw3_plant", planted)):
        d = os.path.join(a.data, name)
        put(os.path.join(d, "SW-Last5Years.txt"), data)
        put(os.path.join(d, "tai-utc.dat"), open(a.leaps, "rb").read())
        log.w("# %s/SW-Last5Years.txt sha256 %s" % (name, H.sha256(os.path.join(d, "SW-Last5Years.txt"))))
    log.check(H.sha256(os.path.join(a.data, "sw3_fill0", "SW-Last5Years.txt")) == FILL0_SHA_F, "the 0-filled copy equals DEBRIS-F's, 47acbcc2...c9a")
    oc = os.path.join(a.data, "orekit_c3")
    for src, name in ((a.finals, "finals2000A.daily"), (a.leaps, "tai-utc.dat"), (os.path.join(a.data, "sw3_fill0", "SW-Last5Years.txt"), "SW-Last5Years.txt")):
        put(os.path.join(oc, name), open(src, "rb").read())
        log.w("# orekit_c3/%s sha256 %s" % (name, H.sha256(os.path.join(oc, name))))
    log.check(sorted(os.listdir(oc)) == ["SW-Last5Years.txt", "finals2000A.daily", "tai-utc.dat"], "the folder holds the three files only")
    log.check(H.sha256(os.path.join(oc, "SW-Last5Years.txt")) != SRC_SHA, "the folder holds the copy, not the original")
    return log.close()


if __name__ == "__main__":
    sys.exit(main())
