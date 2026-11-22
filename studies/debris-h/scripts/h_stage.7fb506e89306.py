# h_stage.py - cft-debris M1 (DEBRIS-H): lays out a run root's input folder "in/" and its EXPECTED.sha256, for the
# desktop's tests and for amd-arc-box. Standard library only; run on the desktop, where the repository, the ledger and
# the downloads are.
# cft-debris, MIT licence (see LICENSE at the repository root). Written by DEBRIS-H, 2026-11-18, from DEBRIS-G's
# tests/g_stage.py (cft-debris's own, MIT): src/ from commit 1646c96 by `git show`, checked against the working tree;
# the archive and DEBRIS-F's table checked against the hashes the ledger records; nothing overwritten.
#
#   python -I -B tests/h_stage.py <repo> <ledger> <downloads dir> <destination root> [--dev]
#
# <destination>/in/ gets (and <destination>/in must not exist):
#   src/              the 18 files of src/ as commit 1646c96 holds them (the script stops if the working tree differs)
#   tests/            this round's sources and scripts (TESTS below), and DEBRIS-F's m1f.c, f9_box_windows.h (the lead's
#                     Linux stand-in for <windows.h>), f5_sgp4.js and f_orekit.js, unchanged
#   cft-fp256-0aa997a3.tar, frame_h0.bin (H0's table, from the ledger's debris-h\), frame_f.bin (DEBRIS-F's table)
#   dl/               the gfc, DE421 and its header, in the downloads' layout (M1_DOWNLOADS)
#   orekit/           DEBRIS-F's finals2000A.daily and tai-utc.dat (Orekit's data folder, and the leap seconds)
#   jars/             Orekit 13.1.9 and Hipparchus 4.0.3, as DEBRIS-F's tests/f_lib.py lists them
#   gp/               DEBRIS-F's snapshots S0 and S1, the four groups each (per-object data: never the repository)
#   ledger/           DEBRIS-F's f6_pairs.001.tsv and f5d_fits.001.tsv (per-object data)
#   testseed/         the test seed and its meta table, from the ledger's debris-h\testseed\ (per-object data)
#   desktop/          the desktop's H4 decode and H6 per-pair results, for the box's comparisons (per-object data)
#   EXPECTED.sha256   "<sha256>  <path relative to in/>" for every file in in/ but itself, sorted
# --dev stages what exists and lists what is missing (development only; the lead's staging never uses it).
import hashlib
import os
import shutil
import subprocess
import sys

COMMIT = "1646c96"
TAR_SHA = "e01003cc0b984864b065ce3395f56fa189451fcb0cd98cce5b11b3c17a9c29b8"
TABF_SHA = "1d997961111f720b2dc275bacb848b3191cbd8997251692ba5b6fe10ef82cf69"
TESTS = ["m1h.c", "m1f.c", "f9_box_windows.h", "f5_sgp4.js", "f_orekit.js", "h_lib.py", "h_build.py", "h_seed.py",
         "h_service.py", "h_fetch.py", "h_check.py", "h2_gate.py", "h4_gate.py", "h5_gate.py", "h6_gate.py", "h_paced.py", "h_audit.py",
         "h3_gate.py", "h3_server.py"]
DL = ["EIGEN6-C4.gfc", "lnxp1900p2053.421", "header.421"]
JARS = ["orekit-13.1.9.jar", "hipparchus-core-4.0.3.jar", "hipparchus-geometry-4.0.3.jar", "hipparchus-ode-4.0.3.jar",
        "hipparchus-fitting-4.0.3.jar", "hipparchus-optim-4.0.3.jar", "hipparchus-filtering-4.0.3.jar", "hipparchus-stat-4.0.3.jar"]
GROUPS = ["stations", "fengyun-1c-debris", "iridium-33-debris", "cosmos-2251-debris"]


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def main():
    repo, ledger, dl, dest = sys.argv[1:5]
    dev = "--dev" in sys.argv[5:]
    inn = os.path.join(dest, "in")
    assert not os.path.exists(inn), "in/ exists already"
    names = subprocess.run(["git", "-C", repo, "ls-tree", "--name-only", COMMIT, "src/"], stdout=subprocess.PIPE, check=True).stdout.decode().split()
    assert len(names) == 18, names
    os.makedirs(os.path.join(inn, "src"))
    for n in names:
        blob = subprocess.run(["git", "-C", repo, "show", "%s:%s" % (COMMIT, n)], stdout=subprocess.PIPE, check=True).stdout
        with open(os.path.join(repo, n), "rb") as f:
            assert f.read() == blob, "working tree differs from %s: %s" % (COMMIT, n)
        with open(os.path.join(inn, n), "xb") as f:
            f.write(blob)
    missing = []

    def cp(src, rel):
        if not os.path.exists(src):
            if dev:
                missing.append(rel)
                return
            raise SystemExit("missing: %s" % src)
        d = os.path.join(inn, os.path.dirname(rel))
        os.makedirs(d, exist_ok=True)
        with open(src, "rb") as a, open(os.path.join(inn, rel), "xb") as b:
            shutil.copyfileobj(a, b)

    for t in TESTS:
        cp(os.path.join(repo, "tests", t), "tests/" + t)
    tar = os.path.join(ledger, "tools", "cft-fp256-0aa997a3.tar")
    tabf = os.path.join(ledger, "tools", "frame-f", "frame_main.bin")
    assert sha(tar) == TAR_SHA and sha(tabf) == TABF_SHA, "the archive or DEBRIS-F's table is not as the ledger records"
    cp(tar, "cft-fp256-0aa997a3.tar")
    cp(tabf, "frame_f.bin")
    cp(os.path.join(ledger, "debris-h", "frame_h0.bin"), "frame_h0.bin")
    for d in DL:
        cp(os.path.join(dl, d, d), "dl/%s/%s" % (d, d))
    for f in ("finals2000A.daily", "tai-utc.dat"):
        cp(os.path.join(dl, f, f), "orekit/" + f)
    for j in JARS:
        cp(os.path.join(dl, j, j), "jars/" + j)
    for g in GROUPS:
        for tag in ("S0", "S1"):
            cp(os.path.join(dl, "gp-%s-%s" % (g, tag), "gp-%s-%s.csv" % (g, tag)), "gp/gp-%s-%s.csv" % (g, tag))
    for f in ("f6_pairs.001.tsv", "f5d_fits.001.tsv"):
        cp(os.path.join(ledger, "debris-f", f), "ledger/" + f)
    for f in ("seed1.txt", "seed2.txt", "seed_meta.tsv"):
        cp(os.path.join(ledger, "debris-h", "testseed", f), "testseed/" + f)
    for f in ("h4_decode.txt", "h6_pairs.tsv", "h6_fit_f5d.tsv", "h6_fit_f6.tsv"):
        cp(os.path.join(ledger, "debris-h", "desktop", f), "desktop/" + f)
    rows = []
    for dp, dn, fn in os.walk(inn):
        for f in fn:
            p = os.path.join(dp, f)
            rows.append((os.path.relpath(p, inn).replace("\\", "/"), sha(p)))
    rows.sort()
    with open(os.path.join(inn, "EXPECTED.sha256"), "xb") as f:
        for rel, h in rows:
            f.write(("%s  %s\n" % (h, rel)).encode("ascii"))
    print("staged %d files under %s/in; EXPECTED.sha256 sha256 %s" % (len(rows), dest, sha(os.path.join(inn, "EXPECTED.sha256"))))
    if missing:
        print("DEV STAGE: missing %d: %s" % (len(missing), ", ".join(missing)))


if __name__ == "__main__":
    main()
