# k_build.py - cft-debris (DEBRIS-K): libcft from the ledger's archive, M1 through DEBRIS-F's tests/build_f.sh, and
# DEBRIS-K's tests/k_fit.c, all in DEBRIS-K's scratch. Windows (the desktop) only.
# cft-debris, MIT licence (see LICENSE at the repository root). Written by DEBRIS-K, 2026-11-23, after DEBRIS-F's build
# (studies/DEBRIS-F-build.md section 3) and DEBRIS-H's tests/h_build.py (cft-debris's own, MIT).
#
#   python -I -B tests/k_build.py --archive TAR --scratch DIR --logs DIR --keep DIR --cpu TSV
#        [--msys C:/msys64] [--sha-archive HEX]
# Every path comes from the arguments; the scratch receives cft-fp256's sources, libcft, M1's builds and k_fit.exe.
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import k_lib as H  # noqa: E402

SCRIPT = os.path.abspath(__file__)
TESTS = os.path.dirname(SCRIPT)
LIBCFT_SHA = "f0eec4f25f53521006526ba3376dd616997b90c7223145c66f6ddbc6aaca67a5"  # DEBRIS-F's and DEBRIS-H's (their logs)

CRITERIA = """
B1 the archive's SHA-256 equals the one lead.md records for it (e01003cc...29b8, the --sha-archive default);
B2 with <msys>/mingw64/bin first on PATH, gcc -dumpmachine prints x86_64-w64-mingw32;
B3 libcft.a builds from the archive (make -C cft-fp256/host CC=gcc OS=Windows_NT libcft.a) and its SHA-256 equals
   DEBRIS-F's and DEBRIS-H's, f0eec4f2...a67a5;
B4 tests/build_f.sh, unchanged, prints BUILD PASS (its own criteria 1 to 5, asserted by it);
B5 tests/k_fit.c compiles with build_f.sh's O2 flags for a test program (-std=c11 -O2 -ffp-contract=off -Wall -Wextra)
   with no warning, and links against build_f.sh's O2 objects and libcft.a;
B6 every executable's SHA-256 is printed.
"""


def main():
    ap = argparse.ArgumentParser()
    for o in ("--archive", "--scratch", "--logs", "--keep", "--cpu"):
        ap.add_argument(o, required=True)
    ap.add_argument("--msys", default="C:/msys64")
    ap.add_argument("--sha-archive", default="e01003cc0b984864b065ce3395f56fa189451fcb0cd98cce5b11b3c17a9c29b8")
    a = ap.parse_args()
    cpu = H.CpuAccount("k_build", a.cpu)
    log = H.Log("k_build", a.logs, SCRIPT, CRITERIA, extra=[os.path.join(TESTS, "build_f.sh"), os.path.join(TESTS, "k_fit.c")], keep_dir=a.keep)
    ms = a.msys.rstrip("/")
    env = dict(os.environ)
    env["PATH"] = ms + "/mingw64/bin;" + ms + "/usr/bin;" + env.get("PATH", "")
    gcc, make, tar, bash = ms + "/mingw64/bin/gcc.exe", ms + "/usr/bin/make.exe", ms + "/usr/bin/tar.exe", ms + "/usr/bin/bash.exe"
    h = H.sha256(a.archive)
    log.w("# archive %s sha256 %s" % (os.path.basename(a.archive), h))
    if not log.check(h == a.sha_archive, "B1 the archive's SHA-256 is as recorded"):
        return log.close()
    _, out, _ = H.run([gcc, "-dumpmachine"], log, env=env)
    m = out.decode().strip()
    if not log.check(m == "x86_64-w64-mingw32", "B2 gcc -dumpmachine prints %s" % m):
        return log.close()
    _, out, _ = H.run([gcc, "--version"], None, env=env)
    log.w("# %s" % out.decode().splitlines()[0])
    cft = os.path.join(a.scratch, "cft-fp256")
    tmp = os.path.join(a.scratch, "tmp")
    os.makedirs(tmp, exist_ok=True)
    if not os.path.isdir(cft):
        os.makedirs(cft)
        H.run([tar, "-xf", a.archive.replace("\\", "/"), "-C", cft.replace("\\", "/")], log, env=env)
    else:
        log.w("# cft-fp256's sources already extracted in the scratch (kept)")
    lib = os.path.join(cft, "host", "libcft.a")
    if not os.path.exists(lib):
        H.run([make, "--no-print-directory", "-C", (cft + "/host").replace("\\", "/"), "CC=gcc", "OS=Windows_NT",
               "TMP=" + tmp.replace("\\", "/"), "TEMP=" + tmp.replace("\\", "/"), "libcft.a"], log, env=env)
    hl = H.sha256(lib)
    if not log.check(hl == LIBCFT_SHA, "B3 libcft.a sha256 %s, DEBRIS-F's and DEBRIS-H's" % hl):
        return log.close()
    bdir = os.path.join(a.scratch, "build", "f")
    if not os.path.exists(os.path.join(bdir, "m1f_O2.exe")):
        rc, out, err = H.run([bash, (os.path.join(TESTS, "build_f.sh")).replace("\\", "/"), (cft + "/host").replace("\\", "/"), bdir.replace("\\", "/")],
                             log, env=env, check=False)
        txt = out.decode("utf-8", "replace")
        for ln in txt.splitlines():
            if "CRITERION" in ln or "BUILD" in ln or ln.startswith("gcc") or "libcft.a:" in ln:
                log.w("#   build_f.sh: " + ln)
        if not log.check(rc == 0 and "BUILD PASS" in txt, "B4 tests/build_f.sh prints BUILD PASS (exit %d)" % rc):
            log.w(err.decode("utf-8", "replace")[-2000:])
            return log.close()
    else:
        log.check(True, "B4 build_f.sh's build already present in the scratch (its log above in an earlier run)")
    o2 = os.path.join(bdir, "O2")
    inc = os.path.join(cft, "host", "include")
    src = os.path.join(TESTS, "..", "src")
    flags = ["-std=c11", "-O2", "-ffp-contract=off", "-Wall", "-Wextra"]
    kobj = os.path.join(o2, "k_fit.o")
    rc, out, err = H.run([gcc] + flags + ["-I" + inc, "-I" + src, "-c", os.path.join(TESTS, "k_fit.c"), "-o", kobj], log, env=env, check=False)
    warn = err.decode("utf-8", "replace").strip()
    if not log.check(rc == 0 and warn == "", "B5 k_fit.c compiles with no warning (exit %d%s)" % (rc, ("; " + warn[:400]) if warn else "")):
        return log.close()
    objs = sorted(os.path.join(o2, f) for f in os.listdir(o2) if f.startswith("kind_") and f.endswith(".o"))
    objs += [os.path.join(o2, f + ".o") for f in ("m1_common", "gfc", "de421", "m1_ftab", "m1_nodes")]
    exe = os.path.join(a.scratch, "build", "k_fit.exe")
    rc, _, err = H.run([gcc, "-o", exe, kobj] + objs + [lib, "-lm"], log, env=env, check=False)
    if not log.check(rc == 0 and os.path.exists(exe), "B5 k_fit.exe links (exit %d)" % rc):
        return log.close()
    for p in (os.path.join(bdir, "m1f_O2.exe"), exe):
        log.w("# B6 %s sha256 %s" % (os.path.basename(p), H.sha256(p)))
    c_ = cpu.close("k_build log %03d" % log.n)
    if c_ is not None:
        log.w("# CPU: %.2f s by cycles / 2.5e9 (this script and every process it started)" % c_)
    return log.close()


if __name__ == "__main__":
    sys.exit(main())
