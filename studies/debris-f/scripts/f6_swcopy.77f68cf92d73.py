# f6_swcopy.py - cft-debris M1 (DEBRIS-F): the derived copies of CelesTrak's SW-Last5Years.txt for F6's comparator (C),
# under the lead's rulings (DEBRIS-F's ledger, 07:49:22 and after; lead.md): Orekit 13.1.9's CssiSpaceWeatherData refuses
# the approved file as served.
# cft-debris, MIT licence (see LICENSE at the repository root). Written by DEBRIS-F, 2026-11-16.
#
#   python -I -B tests/f6_swcopy.py [--monthly [--stage3]]
#
# Three normalisations, each taken only when the one before was shown not to suffice:
#   1. (always) the flux qualifier, the I2 field at columns 99-100, is blank in the 45 DAILY_PREDICTED lines: the
#      placeholder digit goes in column 100;
#   2. (--monthly, the ruling's condition b: Orekit's loader then failed with "empty String" in parseDouble, inside the
#      MONTHLY_PREDICTED section) each wholly blank field of the FORMAT line in each of the 178 MONTHLY_PREDICTED lines
#      (they leave Kp, Ap, Cp, C9 and the qualifier blank) gets the placeholder digit in its last column;
#   3. (--stage3, the lead's ruling after its probe: Orekit 13.1.9's loader knows the section markers "BEGIN
#      DAILY_PREDICTED" and "BEGIN MONTHLY_FIT" only, so it never records where the daily predictions end and every getter
#      throws) the one line "BEGIN MONTHLY_PREDICTED" becomes "BEGIN MONTHLY_FIT".
# Reads the approved file in the downloads (never writes there) and writes, into DEBRIS-F's scratch, for the stage
# (prefix sw_, sw2_ or sw3_):
#   data/<prefix>fill0/SW-Last5Years.txt  the placeholder 0
#   data/<prefix>fill4/SW-Last5Years.txt  the placeholder 4 (0 and 4 are the two codes the OBSERVED section uses)
#   data/<prefix>plant/SW-Last5Years.txt  fill0 with 2026-11-16's F10.7 changed to 150.0 in the adjusted (93-98) and
#                                         observed (113-118) columns: the two-fill check's control
#   (each of those folders also gets a copy of tai-utc.dat, for Orekit's UTC)
#   data/orekit_c/, orekit_c2/, orekit_c3/ the folder (C) would crawl: finals2000A.daily, tai-utc.dat and fill0's copy
#                                         (never the original)
# ASSERTED (stated before the run): each copy has the original's line count and CRLF endings; every line equals the
# original's but (a) the filled lines, which differ only at the fill positions, each blank in the original, and (b) with
# --stage3, exactly one more line, "BEGIN MONTHLY_PREDICTED" become "BEGIN MONTHLY_FIT". CONTROL: a second change
# planted into the finished copy (one digit of the first OBSERVED line) must fail that check.
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import f_lib as F  # noqa: E402

SRC = F.DOWNLOADS + "SW-Last5Years.txt/SW-Last5Years.txt"
SRC_SHA = "718bae83ef2786d77b5e5d11647bf5b984986f0d0213b1080c5d4d6b514948fb"
MONTHLY = "--monthly" in sys.argv or "--stage3" in sys.argv
STAGE3 = "--stage3" in sys.argv
MARK_OLD, MARK_NEW = b"BEGIN MONTHLY_PREDICTED", b"BEGIN MONTHLY_FIT"
# the FORMAT line's fields, 1-based inclusive: I4,I3,I3,I5,I3,8I3,I4,8I4,I4,F4.1,I2,I4,F6.1,I2,5F6.1
FIELDS = ([(1, 4), (5, 7), (8, 10), (11, 15), (16, 18)] + [(19 + 3 * i, 21 + 3 * i) for i in range(8)] + [(43, 46)] +
          [(47 + 4 * i, 50 + 4 * i) for i in range(8)] + [(79, 82), (83, 86), (87, 88), (89, 92), (93, 98), (99, 100)] +
          [(101 + 6 * i, 106 + 6 * i) for i in range(5)])


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


def main():
    stage = 3 if STAGE3 else 2 if MONTHLY else 1
    print("f6_swcopy.py sha256 %s (kept as studies/debris-f/scripts/f6_swcopy.%s.py), stage %d" % (
        F.keep_version(os.path.abspath(__file__)), F.sha256(os.path.abspath(__file__))[:12], stage))
    orig = open(SRC, "rb").read()
    h = F.sha256(SRC)
    print("original %s sha256 %s (%d bytes, %d lines, %d CRLF)" % (SRC, h, len(orig), orig.count(b"\n"), orig.count(b"\r\n")))
    assert h == SRC_SHA, "the approved file's sha256"
    lines = orig.split(b"\n")
    dl = daily_lines(lines)
    print("DAILY_PREDICTED data lines: %d (%s to %s)" % (len(dl), lines[dl[0]][:10].decode(), lines[dl[-1]][:10].decode()))
    assert len(dl) == 45 and all(lines[k][98:100] == b"  " for k in dl), "45 lines, each qualifier blank"
    npos = len(line_positions(orig))
    if MONTHLY:
        print("MONTHLY_PREDICTED data lines: %d; bytes the fill sets in them: %d" % (len(section(lines, b"MONTHLY_PREDICTED")), npos - 45))
    if STAGE3:
        print("the marker line %d: %r becomes %r" % (marker_line(lines) + 1, MARK_OLD.decode(), MARK_NEW.decode()))
    out = {}
    for digit in ("0", "4"):
        c = normalise(orig, digit)
        assert check(orig, c), "placeholder %s: the check" % digit
        out[digit] = c
        print("placeholder %s: PASS the check (%d filled bytes, each blank in the original%s; line count and CRLF unchanged)" %
              (digit, npos, "; and the one marker line renamed" if STAGE3 else ""))
    # the control: a second change planted into the finished copy must fail the check
    bad = out["0"].split(b"\n")
    i = next(k for k, l in enumerate(bad) if l.startswith(b"BEGIN OBSERVED")) + 1
    l = bytearray(bad[i])
    l[3] = ord("9") if l[3] != ord("9") else ord("8")
    bad[i] = bytes(l)
    assert not check(orig, b"\n".join(bad)), "the planted second change must fail"
    print("control: a second change planted into the finished copy (the first OBSERVED line, column 4) FAILS the check, as it must")
    # the F10.7 plant on 2026-11-16 for the two-fill check's control
    pl = out["0"].split(b"\n")
    k = next(k for k in dl if pl[k].startswith(b"2026 11 16"))
    l = bytearray(pl[k])
    l[92:98] = b" 150.0"
    l[112:118] = b" 150.0"
    pl[k] = bytes(l)
    planted = b"\n".join(pl)
    pre = {1: "sw_", 2: "sw2_", 3: "sw3_"}[stage]
    for name, data in ((pre + "fill0", out["0"]), (pre + "fill4", out["4"]), (pre + "plant", planted)):
        d = F.DATA + "/" + name
        os.makedirs(d, exist_ok=True)
        p = d + "/SW-Last5Years.txt"
        if os.path.exists(p):
            assert open(p, "rb").read() == data, "%s exists with other bytes" % p
        else:
            with open(p, "wb") as f:
                f.write(data)
        print("%s sha256 %s (%d bytes)" % (p, F.sha256(p), len(data)))
        tu = d + "/tai-utc.dat"
        if not os.path.exists(tu):
            with open(tu, "wb") as f:
                f.write(open(F.DOWNLOADS + "tai-utc.dat/tai-utc.dat", "rb").read())
        assert F.sha256(tu) == F.sha256(F.DOWNLOADS + "tai-utc.dat/tai-utc.dat")
    oc = F.DATA + {1: "/orekit_c", 2: "/orekit_c2", 3: "/orekit_c3"}[stage]
    os.makedirs(oc, exist_ok=True)
    for src, name in ((F.DOWNLOADS + "finals2000A.daily/finals2000A.daily", "finals2000A.daily"), (F.DOWNLOADS + "tai-utc.dat/tai-utc.dat", "tai-utc.dat"),
                      (F.DATA + "/" + pre + "fill0/SW-Last5Years.txt", "SW-Last5Years.txt")):
        data = open(src, "rb").read()
        p = oc + "/" + name
        if not os.path.exists(p):
            with open(p, "wb") as f:
                f.write(data)
        assert open(p, "rb").read() == data
        print("%s/%s sha256 %s" % (os.path.basename(oc), name, F.sha256(p)))
    assert sorted(os.listdir(oc)) == ["SW-Last5Years.txt", "finals2000A.daily", "tai-utc.dat"], "the folder holds the three files only"
    assert F.sha256(oc + "/SW-Last5Years.txt") != SRC_SHA, "the folder holds the copy, not the original"
    print("PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
