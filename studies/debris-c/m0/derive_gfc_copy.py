#!/usr/bin/env python3
"""DEBRIS-C: derive the de-duplicated copy of the benchmark's EIGEN6-C4.gfc
(the lead's ruling, lead.md 2026-11-12 18:07).

  python -I -B derive_gfc_copy.py

- Reads the approved original in the downloads folder (never writes there)
  and checks its SHA-256 against lead.md's.
- The copy is the original with line 16 removed, and nothing else: line 16 is
  the second "gfc 0 0" line (0.10000000000E+01; line 15 holds
  1.00000000000E+00, the same value).
- ASSERTED (criteria written before the run), by check():
    1. the copy differs from the original by exactly that line;
    2. every (L, M) key appears once in the copy;
    3. no value changed: every key keeps its C, S, sigma C and sigma S, and
       no key is lost.
- CONTROL (asserted): two planted second changes, one value changed on
  another line and one other line removed, must each fail check().
- Writes the copy once, into its own directory in DEBRIS-C's scratch, and
  prints the SHA-256 of the original and of the copy. If the copy already
  exists it is not rewritten: its bytes must equal the derived bytes.
"""
import collections
import difflib
import hashlib
import os
import sys

ORIG = "C:/Users/logan/source/repos/cft-debris-downloads/EIGEN6-C4.gfc/EIGEN6-C4.gfc"
ORIG_SHA = "b5d58320c9ee03ff4ad258e65ea2bade002c477081df08c30e72f4d864737715"
COPY_DIR = "C:/Users/logan/source/repos/cft-debris-scratch/DEBRIS-C/gfc_dedup"
COPY = COPY_DIR + "/EIGEN6-C4.gfc"
REMOVE = 16  # 1-based line number


def parse(lines):
    """(L, M) -> list of value tuples, for every gfc line after end_of_head"""
    vals = collections.defaultdict(list)
    head = True
    for ln in lines:
        t = ln.split()
        if head:
            if t and t[0].startswith(b"end_of_head"):
                head = False
            continue
        if not t:
            continue
        assert t[0] == b"gfc", ("non-gfc data line", ln)
        key = (int(t[1]), int(t[2]))
        vals[key].append(tuple(float(x) for x in t[3:7]))
    return vals


def check(orig, copy):
    # 1. the copy differs from the original by exactly line REMOVE
    assert copy == orig[:REMOVE - 1] + orig[REMOVE:], "copy is not the original minus line %d" % REMOVE
    ops = [op for op in difflib.SequenceMatcher(a=orig, b=copy, autojunk=False).get_opcodes() if op[0] != "equal"]
    assert len(ops) == 1 and ops[0][0] == "delete" and ops[0][2] - ops[0][1] == 1, ("diff is not one deleted line", ops)
    # 2. every key once
    pc = parse(copy)
    dup = [k for k, v in pc.items() if len(v) != 1]
    assert not dup, ("keys not unique in the copy", dup[:5])
    # 3. no value changed, no key lost
    po = parse(orig)
    assert set(po) == set(pc), "key sets differ"
    for k, vs in po.items():
        assert all(v == vs[0] for v in vs), ("original's duplicates disagree", k)
        assert pc[k][0] == vs[0], ("value changed", k)
    return len(pc)


def main():
    raw = open(ORIG, "rb").read()
    h = hashlib.sha256(raw).hexdigest()
    print("# original: %s sha256 %s (%d bytes)" % (ORIG, h, len(raw)))
    assert h == ORIG_SHA, "the original's SHA-256 is not lead.md's"
    orig = raw.splitlines(keepends=True)
    assert orig[REMOVE - 2].split()[:3] == [b"gfc", b"0", b"0"], orig[REMOVE - 2]
    assert orig[REMOVE - 1].split()[:3] == [b"gfc", b"0", b"0"], orig[REMOVE - 1]
    print("# line %d removed: %r" % (REMOVE, orig[REMOVE - 1]))
    print("# line %d kept:    %r" % (REMOVE - 1, orig[REMOVE - 2]))
    copy = orig[:REMOVE - 1] + orig[REMOVE:]
    po = parse(orig)
    print("# original: %d gfc lines, %d distinct keys, duplicated keys: %s" %
          (sum(len(v) for v in po.values()), len(po), sorted(k for k, v in po.items() if len(v) > 1)))
    nkeys = check(orig, copy)
    print("# check on the copy: PASS (exactly line %d removed; %d keys, each once; no value changed)" % (REMOVE, nkeys))

    # control: two planted second changes must each fail check()
    i180 = max(i for i, ln in enumerate(copy) if ln.startswith(b"gfc  180  180"))
    planted_value = list(copy)
    planted_value[i180] = planted_value[i180].replace(b"-0.22147242139E-09", b"-0.22147242138E-09")
    assert planted_value[i180] != copy[i180], "the value plant did not apply"
    i20 = next(i for i, ln in enumerate(copy) if ln.split()[:3] == [b"gfc", b"2", b"0"])
    planted_line = copy[:i20] + copy[i20 + 1:]
    for name, bad in (("a changed value on the (180,180) line", planted_value), ("the (2,0) line removed too", planted_line)):
        try:
            check(orig, bad)
        except AssertionError as e:
            print("# control, %s: check() FAILED as it must (%s)" % (name, e.args[0] if e.args else e))
        else:
            raise SystemExit("CONTROL FAILED: check() accepted %s" % name)

    data = b"".join(copy)
    hc = hashlib.sha256(data).hexdigest()
    os.makedirs(COPY_DIR, exist_ok=True)
    if os.path.exists(COPY):
        old = open(COPY, "rb").read()
        assert old == data, "an existing copy differs from the derived bytes"
        print("# copy already present; bytes equal the derived bytes; not rewritten")
    else:
        assert os.listdir(COPY_DIR) == [], "the copy's directory must hold the copy only"
        with open(COPY, "wb") as f:
            f.write(data)
    again = open(COPY, "rb").read()
    assert hashlib.sha256(again).hexdigest() == hc
    assert os.listdir(COPY_DIR) == ["EIGEN6-C4.gfc"], os.listdir(COPY_DIR)
    print("# copy: %s sha256 %s (%d bytes)" % (COPY, hc, len(data)))
    print("# DERIVE PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
