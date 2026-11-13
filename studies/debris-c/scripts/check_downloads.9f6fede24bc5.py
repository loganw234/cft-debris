#!/usr/bin/env python3
"""DEBRIS-C: every downloaded file this study reads, against the SHA-256 and
byte count lead.md records for it (the entries of 17:48 and 17:54).

  python -I -B check_downloads.py

CRITERION (asserted): all 19 files present, each with lead.md's byte count
and SHA-256. CONTROL (asserted): the same check with one recorded hash
altered by one hex digit must report exactly one mismatch.
"""
import hashlib
import os
import re
import sys

LEAD = "C:/Users/logan/source/repos/cft-debris-ledger/lead.md"
DOWN = "C:/Users/logan/source/repos/cft-debris-downloads/"


def recorded():
    rec = {}
    for ln in open(LEAD, encoding="utf-8"):
        m = re.match(r"\s*- `([^`]+)`: (\d+) bytes, SHA-256 `([0-9a-f]{64})`", ln)
        if m:
            rec[m.group(1)] = (int(m.group(2)), m.group(3))
    return rec


def check(rec):
    bad = []
    for name, (size, h) in sorted(rec.items()):
        p = os.path.join(DOWN, name, name)
        data = open(p, "rb").read()
        got = hashlib.sha256(data).hexdigest()
        ok = len(data) == size and got == h
        if not ok:
            bad.append(name)
    return bad


def main():
    rec = recorded()
    print("# lead.md records %d files" % len(rec))
    assert len(rec) == 19, len(rec)
    bad = check(rec)
    for name, (size, h) in sorted(rec.items()):
        print("  %-32s %9d bytes  %s  %s" % (name, size, h, "MISMATCH" if name in bad else "ok"))
    p = not bad
    print("%s criterion: all 19 files match lead.md" % ("PASS" if p else "FAIL"))
    planted = dict(rec)
    k = "EIGEN6-C4.gfc"
    size, h = planted[k]
    planted[k] = (size, ("0" if h[0] != "0" else "1") + h[1:])
    c = check(planted) == [k]
    print("%s control: a recorded hash altered by one hex digit is reported (exactly one mismatch)" % ("PASS" if c else "FAIL"))
    return 0 if (p and c) else 1


if __name__ == "__main__":
    sys.exit(main())
