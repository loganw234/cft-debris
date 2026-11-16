# f6_swcopy.py - cft-debris M1 (DEBRIS-F): the derived copies of CelesTrak's SW-Last5Years.txt for F6's comparator (C),
# under the lead's ruling (DEBRIS-F's ledger, 07:49:22; lead.md): Orekit 13.1.9's CssiSpaceWeatherData refuses the
# approved file, whose 45 DAILY_PREDICTED lines leave the flux qualifier (the I2 field, columns 99-100) blank.
# cft-debris, MIT licence (see LICENSE at the repository root). Written by DEBRIS-F, 2026-11-16.
#
#   python -I -B tests/f6_swcopy.py [--monthly]
#
# Reads the approved file in the downloads (never writes there) and writes, into DEBRIS-F's scratch:
#   data/sw_fill0/SW-Last5Years.txt   column 100 of the 45 DAILY_PREDICTED lines set to "0"
#   data/sw_fill4/SW-Last5Years.txt   the same with "4" (0 and 4 are the two codes the OBSERVED section uses)
#   data/sw_plant/SW-Last5Years.txt   fill0 with 2026-11-16's F10.7 changed to 150.0 in the adjusted (93-98) and observed
#                                     (113-118) columns: the two-fill check's control
#   (each of those three folders also gets a copy of tai-utc.dat, for Orekit's UTC)
#   data/orekit_c/                    the folder (C) crawls: finals2000A.daily, tai-utc.dat and fill0's copy (not the
#                                     original)
# --monthly (the ruling's condition b, taken when Orekit's loader, given the DAILY_PREDICTED fill alone, failed with
# "empty String" in parseDouble; a diagnostic copy without the MONTHLY_PREDICTED data lines loaded but then failed in
# getAp): each entirely blank field of the FORMAT line in each of the 178 MONTHLY_PREDICTED lines (they leave Kp, Ap, Cp,
# C9 and the qualifier blank) also gets the placeholder digit in its last column; the copies go to data/sw2_fill0,
# sw2_fill4, sw2_plant and orekit_c2, and the check covers those positions too.
# ASSERTED (stated before the run): each fill copy differs from the original at exactly the expected bytes, each a blank
# in the original; the line count and the line endings (CRLF) are unchanged; without --monthly the MONTHLY_PREDICTED
# lines are left as served. CONTROL: a planted second change (one digit of the first OBSERVED line) must fail that check.
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import f_lib as F  # noqa: E402

SRC = F.DOWNLOADS + "SW-Last5Years.txt/SW-Last5Years.txt"
SRC_SHA = "718bae83ef2786d77b5e5d11647bf5b984986f0d0213b1080c5d4d6b514948fb"
MONTHLY = "--monthly" in sys.argv
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


def fill(orig, digit):
    lines = orig.split(b"\n")
    for k, c in line_positions(orig):
        l = bytearray(lines[k])
        l[c] = ord(digit)
        lines[k] = bytes(l)
    return b"\n".join(lines)


def expected_positions(orig):
    lines = orig.split(b"\n")
    starts, off = [], 0
    for l in lines:
        starts.append(off)
        off += len(l) + 1
    return sorted(starts[k] + c for k, c in line_positions(orig))


def check(orig, copy):
    """True when copy differs from orig at exactly the expected bytes (the 45 qualifiers, and with --monthly the blank
    fields' last columns in MONTHLY_PREDICTED), each blank in orig, with the line count and endings unchanged"""
    if len(orig) != len(copy):
        return False
    diff = [i for i in range(len(orig)) if orig[i] != copy[i]]
    exp = expected_positions(orig)
    return (diff == exp and len(exp) >= 45 and all(orig[i] == 32 for i in exp) and orig.count(b"\n") == copy.count(b"\n")
            and orig.count(b"\r\n") == copy.count(b"\r\n"))


def main():
    print("f6_swcopy.py sha256 %s (kept as studies/debris-f/scripts/f6_swcopy.%s.py)%s" % (
        F.keep_version(os.path.abspath(__file__)), F.sha256(os.path.abspath(__file__))[:12], " --monthly" if MONTHLY else ""))
    orig = open(SRC, "rb").read()
    h = F.sha256(SRC)
    print("original %s sha256 %s (%d bytes, %d lines, %d CRLF)" % (SRC, h, len(orig), orig.count(b"\n"), orig.count(b"\r\n")))
    assert h == SRC_SHA, "the approved file's sha256"
    lines = orig.split(b"\n")
    dl = daily_lines(lines)
    print("DAILY_PREDICTED data lines: %d (%s to %s)" % (len(dl), lines[dl[0]][:10].decode(), lines[dl[-1]][:10].decode()))
    assert len(dl) == 45 and all(lines[k][98:100] == b"  " for k in dl), "45 lines, each qualifier blank"
    if MONTHLY:
        ml = section(lines, b"MONTHLY_PREDICTED")
        print("MONTHLY_PREDICTED data lines: %d; bytes the fill sets in them: %d" % (len(ml), len(line_positions(orig)) - 45))
    out = {}
    for digit in ("0", "4"):
        c = fill(orig, digit)
        assert check(orig, c), "fill %s: the check" % digit
        out[digit] = c
        print("fill %s: PASS the check (%d bytes: the 45 qualifiers at column 100%s; each blank in the original; lines and CRLF unchanged)" %
              (digit, len(expected_positions(orig)), ", and the MONTHLY_PREDICTED lines' blank fields" if MONTHLY else ""))
    # the control: a planted second change must fail the check
    bad = bytearray(out["0"])
    i = next(k for k, l in enumerate(lines) if l.startswith(b"BEGIN OBSERVED")) + 1
    off = sum(len(l) + 1 for l in lines[:i]) + 3
    bad[off] = ord("9") if bad[off] != ord("9") else ord("8")
    assert not check(orig, bytes(bad)), "the planted second change must fail"
    print("control: a planted second change (the first OBSERVED line, column 4) FAILS the check, as it must")
    # the F10.7 plant on 2026-11-16 for the two-fill check's control
    pl = out["0"].split(b"\n")
    k = next(k for k in dl if pl[k].startswith(b"2026 11 16"))
    l = bytearray(pl[k])
    l[92:98] = b" 150.0"
    l[112:118] = b" 150.0"
    pl[k] = bytes(l)
    planted = b"\n".join(pl)
    pre = "sw2_" if MONTHLY else "sw_"
    for name, data in ((pre + "fill0", out["0"]), (pre + "fill4", out["4"]), (pre + "plant", planted)):
        d = F.DATA + "/" + name
        os.makedirs(d, exist_ok=True)
        p = d + "/SW-Last5Years.txt"
        if os.path.exists(p):
            assert open(p, "rb").read() == data, "%s exists with other bytes" % p
        else:
            with open(p, "wb") as f:
                f.write(data)
        print("%s sha256 %s" % (p, F.sha256(p)))
        tu = d + "/tai-utc.dat"
        if not os.path.exists(tu):
            with open(tu, "wb") as f:
                f.write(open(F.DOWNLOADS + "tai-utc.dat/tai-utc.dat", "rb").read())
        assert F.sha256(tu) == F.sha256(F.DOWNLOADS + "tai-utc.dat/tai-utc.dat")
    oc = F.DATA + ("/orekit_c2" if MONTHLY else "/orekit_c")
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
