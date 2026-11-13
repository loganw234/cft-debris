"""dd.py - DEBRIS-D's logging helper (cft-debris, MIT).

Every script that writes a log calls `Log(__file__, name)`:
  * it hashes the calling script (and this helper), and keeps a copy of the
    script under scripts/<stem>.<first 12 hex>.<ext> in studies/debris-d
    (READY: every version of a script that wrote a log is kept);
  * it opens logs/<name>.<NNN>.log with the next free number (never
    overwrites a log);
  * the log's first lines name the script's SHA-256, this helper's, and
    the criteria the script asserts, which the script states before it
    computes anything (`criteria(...)`).
"""
import hashlib
import os
import shutil
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)                 # studies/debris-d
SCRATCH = "C:/Users/logan/source/repos/cft-debris-scratch/DEBRIS-D"
FP256 = SCRATCH + "/fp256"
PY = "C:/Users/logan/AppData/Local/Programs/Miniconda3/python.exe"


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


class Log:
    def __init__(self, script, name):
        self.script = os.path.abspath(script)
        self.sha = sha256_file(self.script)
        self.helper_sha = sha256_file(os.path.abspath(__file__))
        stem, ext = os.path.splitext(os.path.basename(self.script))
        vdir = os.path.join(ROOT, "scripts")
        os.makedirs(vdir, exist_ok=True)
        vpath = os.path.join(vdir, "%s.%s%s" % (stem, self.sha[:12], ext))
        if not os.path.exists(vpath):
            shutil.copyfile(self.script, vpath)
        hpath = os.path.join(vdir, "dd.%s.py" % self.helper_sha[:12])
        if not os.path.exists(hpath):
            shutil.copyfile(os.path.abspath(__file__), hpath)
        ldir = os.path.join(ROOT, "logs")
        os.makedirs(ldir, exist_ok=True)
        k = 1
        while os.path.exists(os.path.join(ldir, "%s.%03d.log" % (name, k))):
            k += 1
        self.path = os.path.join(ldir, "%s.%03d.log" % (name, k))
        self.f = open(self.path, "w", encoding="utf-8", newline="\n")
        self.failures = []
        self.w("# log %s" % os.path.basename(self.path))
        self.w("# written by %s, sha256 %s" % (os.path.basename(self.script), self.sha))
        self.w("# helper dd.py sha256 %s" % self.helper_sha)
        self.w("# started %s (local)" % time.strftime("%Y-%m-%d %H:%M:%S"))
        self.w("# python %s" % sys.version.split()[0])

    def w(self, line=""):
        self.f.write(line + "\n")
        self.f.flush()
        print(line)

    def criteria(self, *lines):
        self.w("# CRITERIA (stated before any data):")
        for ln in lines:
            self.w("#   " + ln)

    def check(self, ok, what):
        self.w("%s: %s" % ("PASS" if ok else "FAIL", what))
        if not ok:
            self.failures.append(what)
        return ok

    def close(self):
        self.w("# failures: %d" % len(self.failures))
        for x in self.failures:
            self.w("#   FAILED: " + x)
        self.w("# finished %s (local)" % time.strftime("%Y-%m-%d %H:%M:%S"))
        self.f.close()
        return len(self.failures)
