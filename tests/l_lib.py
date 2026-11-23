# l_lib.py - cft-debris (DEBRIS-L): shared pieces of the visual presentation parcel: paths from arguments, the seed's
# reader, the groups and their colours, a numbered log that names no tool or home path, and the CPU account.
# cft-debris, MIT licence (see LICENSE at the repository root). Written by DEBRIS-L, 2026-11-23. Reuses, from the same
# repository (MIT): tests/k_lib.py's CpuAccount, read_seed, run and sha256.
#
# A log is <logdir>/<name>.<NNN>.log (NNN the next free number in the repository's dir AND the ledger's detail dir, so
# the two carry the same number); no log is overwritten. Its text goes through redact(): tool and root paths become
# <python>, <ffmpeg>, <msys> and <root>/..., and any remaining user folder becomes "~".
import os
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import k_lib as K  # noqa: E402

TESTS = os.path.dirname(os.path.abspath(__file__))
HERE_REPO = os.path.normpath(os.path.join(TESTS, ".."))

GROUPS = ["fengyun-1c-debris", "cosmos-2251-debris", "iridium-33-debris", "stations"]
GROUP_LABEL = {"fengyun-1c-debris": "FENGYUN-1C DEBRIS", "cosmos-2251-debris": "COSMOS-2251 DEBRIS",
               "iridium-33-debris": "IRIDIUM-33 DEBRIS", "stations": "STATIONS"}
GROUP_COLOR = {"fengyun-1c-debris": (255, 159, 67), "cosmos-2251-debris": (80, 200, 255),
               "iridium-33-debris": (120, 255, 140), "stations": (255, 80, 90)}
EARTH_R_KM = 6378.137
DELTA_S = 60.0
NFRAMES = 181
TS_EXPECT = 2933400.0

_SUBS = []  # (compiled regex, replacement), longest first


def set_roots(**kw):
    """kw: python, ffmpeg, msys, scratch, ledger, repo -> their paths; later logs show them as placeholders"""
    pairs = []
    for key, rep in (("python", "<python>"), ("ffmpeg", "<ffmpeg>"), ("msys", "<msys>"), ("scratch", "<root>/scratch"),
                     ("ledger", "<root>/ledger"), ("repo", "<root>/repo"), ("downloads", "<root>/downloads")):
        p = kw.get(key)
        if p:
            pairs.append((os.path.abspath(p).replace("\\", "/"), rep))
    pairs.sort(key=lambda t: -len(t[0]))
    _SUBS[:] = [(re.compile(re.escape(a), re.IGNORECASE), b) for a, b in pairs]


def redact(s):
    s = s.replace("\\", "/")
    for rx, rep in _SUBS:
        s = rx.sub(rep, s)
    return K.redact(s)


def sha256(path):
    return K.sha256(path)


def read_group_table(meta_path):
    """seed_meta.tsv: {idx: group} (read from the file's columns idx and group)"""
    grp = {}
    with open(meta_path, "r", encoding="utf-8") as f:
        head = None
        for ln in f:
            if ln.startswith("#") or not ln.strip():
                continue
            q = ln.rstrip("\n").split("\t")
            if head is None:
                head = q
                ci, cg = head.index("idx"), head.index("group")
                continue
            grp[int(q[ci])] = q[cg]
    return grp


def next_number(*dirs, name):
    n = 1
    while any(os.path.exists(os.path.join(d, "%s.%03d.log" % (name, n))) for d in dirs if d):
        n += 1
    return n


class Log:
    """criteria first (before data), then lines; check() records PASS/FAIL; close() prints the verdict.
    detail (optional) is a second file in the ledger with per-object lines, same number, never redacted into the repository."""

    def __init__(self, name, logdir, script, criteria, keep_dir, detail_dir=None, modules=()):
        os.makedirs(logdir, exist_ok=True)
        if detail_dir:
            os.makedirs(detail_dir, exist_ok=True)
        self.n = next_number(logdir, detail_dir, name=name)
        self.path = os.path.join(logdir, "%s.%03d.log" % (name, self.n))
        self.f = open(self.path, "x", encoding="utf-8", newline="\n")
        self.df = open(os.path.join(detail_dir, "%s.%03d.log" % (name, self.n)), "x", encoding="utf-8", newline="\n") if detail_dir else None
        self.fails, self.checks, self.name = [], 0, name
        self.w("# %s, log %03d, written %s" % (name, self.n, time.strftime("%Y-%m-%d %H:%M:%S %z")))
        self.w("# script %s sha256 %s" % (os.path.basename(script), K.keep_version(script, keep_dir)))
        for m in modules:
            self.w("# module %s sha256 %s" % (os.path.basename(m), K.keep_version(m, keep_dir) if m.endswith(".py") else K.sha256(m)))
        self.w("# python %s" % sys.version.split()[0])
        self.w("# CRITERIA (fixed in the script before the data, asserted in code):")
        for line in criteria.strip("\n").split("\n"):
            self.w("#   " + line)

    def w(self, s=""):
        s = redact(s)
        self.f.write(s + "\n")
        self.f.flush()
        try:
            print(s, flush=True)
        except UnicodeEncodeError:
            print(s.encode("ascii", "replace").decode(), flush=True)

    def d(self, s=""):
        if self.df:
            self.df.write(s + "\n")
            self.df.flush()

    def check(self, ok, what):
        ok = bool(ok)
        self.checks += 1
        self.w(("PASS " if ok else "FAIL ") + what)
        if not ok:
            self.fails.append(what)
        return ok

    def close(self, extra=""):
        self.w("# %s (%d checks, %d failed) %s" % ("PASS" if not self.fails else "FAIL", self.checks, len(self.fails), extra))
        self.f.close()
        if self.df:
            self.df.close()
        return 0 if not self.fails else 1


def argparse_common(ap):
    for o in ("--scratch", "--ledger", "--logs", "--keep", "--cpu"):
        ap.add_argument(o, required=True)
    ap.add_argument("--python", default=sys.executable)
    return ap
