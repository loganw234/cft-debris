# g_stage.py - cft-debris M1 (DEBRIS-G): lays out the harness's input folder "in/" and its EXPECTED.sha256.
# cft-debris, MIT licence (see LICENSE at the repository root). Written by DEBRIS-G, 2026-11-17.
#
#   python -I -B tests/g_stage.py <repo root> <ledger root> <downloads dir> <destination root>
#
# Makes <destination>/in/ with: src/ (every file as commit 1646c96 holds it: the bytes come from `git show`, and
# the script stops if the working tree differs), m1g.c, g_calib.c, g_harness.py, cft-fp256-0aa997a3.tar, frame_main.bin,
# population.001.txt, dl/ in the downloads' layout (the gfc, DE421 and its header), and EXPECTED.sha256 listing every
# file in "in/" but itself ("<sha256>  <path relative to in/>", sorted). Nothing is overwritten: the destination's
# in/ must not exist. The archive and the frame table are checked against the SHA-256 the ledger records.
import hashlib
import os
import shutil
import subprocess
import sys

COMMIT = "1646c96"
TAR_SHA = "e01003cc0b984864b065ce3395f56fa189451fcb0cd98cce5b11b3c17a9c29b8"
TAB_SHA = "1d997961111f720b2dc275bacb848b3191cbd8997251692ba5b6fe10ef82cf69"
DL = [("EIGEN6-C4.gfc", "EIGEN6-C4.gfc"), ("lnxp1900p2053.421", "lnxp1900p2053.421"), ("header.421", "header.421")]
TESTS = ["m1g.c", "g_calib.c", "g_harness.py"]


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def main():
    repo, ledger, dl, dest = sys.argv[1:5]
    inn = os.path.join(dest, "in")
    assert not os.path.exists(inn), "in/ exists already"
    git = "git"
    names = subprocess.run([git, "-C", repo, "ls-tree", "--name-only", COMMIT, "src/"], stdout=subprocess.PIPE, check=True).stdout.decode().split()
    assert len(names) == 18, names
    os.makedirs(os.path.join(inn, "src"))
    for n in names:
        blob = subprocess.run([git, "-C", repo, "show", "%s:%s" % (COMMIT, n)], stdout=subprocess.PIPE, check=True).stdout
        with open(os.path.join(repo, n), "rb") as f:
            assert f.read() == blob, "working tree differs from %s: %s" % (COMMIT, n)
        with open(os.path.join(inn, n), "wb") as f:
            f.write(blob)
    for t in TESTS:
        shutil.copyfile(os.path.join(repo, "tests", t), os.path.join(inn, t))
    tar = os.path.join(ledger, "tools", "cft-fp256-0aa997a3.tar")
    tab = os.path.join(ledger, "tools", "frame-f", "frame_main.bin")
    assert sha(tar) == TAR_SHA and sha(tab) == TAB_SHA
    shutil.copyfile(tar, os.path.join(inn, "cft-fp256-0aa997a3.tar"))
    shutil.copyfile(tab, os.path.join(inn, "frame_main.bin"))
    shutil.copyfile(os.path.join(ledger, "debris-g", "population.001.txt"), os.path.join(inn, "population.001.txt"))
    for d, f in DL:
        os.makedirs(os.path.join(inn, "dl", d), exist_ok=True)
        shutil.copyfile(os.path.join(dl, d, f), os.path.join(inn, "dl", d, f))
    rows = []
    for dp, dn, fn in os.walk(inn):
        for f in fn:
            p = os.path.join(dp, f)
            rows.append((os.path.relpath(p, inn).replace("\\", "/"), sha(p)))
    rows.sort()
    with open(os.path.join(inn, "EXPECTED.sha256"), "wb") as f:
        for rel, h in rows:
            f.write(("%s  %s\n" % (h, rel)).encode("ascii"))
    print("staged %d files under %s/in; EXPECTED.sha256 sha256 %s" % (len(rows), dest, sha(os.path.join(inn, "EXPECTED.sha256"))))


if __name__ == "__main__":
    main()
