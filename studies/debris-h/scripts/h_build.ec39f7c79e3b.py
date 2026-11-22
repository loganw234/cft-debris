# h_build.py - cft-debris M1 (DEBRIS-H), gate H1: the build of the service's programs, its source check, its control
# and its smoke runs. Standard library only; on amd-arc-box (Linux) and on the desktop (Windows).
# cft-debris, MIT licence (see LICENSE at the repository root). Written by DEBRIS-H, 2026-11-18, from DEBRIS-G's
# tests/g_harness.py (its build criteria B1 to B5 and its control C1) and the lead's tests/f9_box.py (m1f.c on Linux
# through the stand-in tests/f9_box_windows.h), both cft-debris's own, MIT.
#
#   python3 -I -B in/tests/h_build.py <root>
#
# <root>/in is tests/h_stage.py's. The script works from <root> with relative paths, writes cft-fp256/, build/, h1/
# and logs/ beside in/, never overwrites a log, and deletes nothing.
import os
import shutil
import subprocess
import sys
import tarfile
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import h_lib as H  # noqa: E402

SCRIPT = os.path.abspath(__file__)
WIN = H.WIN
EXT = ".exe" if WIN else ""
GCC = "C:/msys64/mingw64/bin/gcc.exe" if WIN else "gcc"
MAKE = "C:/msys64/usr/bin/make.exe" if WIN else "make"
OBJDUMP = "C:/msys64/mingw64/bin/objdump.exe" if WIN else "objdump"
NM = "C:/msys64/mingw64/bin/nm.exe" if WIN else "nm"
MACHINE = "x86_64-w64-mingw32" if WIN else "x86_64-linux-gnu"
O2 = ["-std=c11", "-O2", "-ffp-contract=off", "-Wall", "-Wextra"]
NATIVE = ["native32", "native64"]
CFT = ["cft32", "cft64", "cft128", "cft256"]
COMMON = ["m1_common", "gfc", "de421", "m1_ftab", "m1_nodes"]
CI = "cft-fp256/host/include"
LIB = "cft-fp256/host/libcft.a"
M1H = "build/m1h" + EXT
M1F = "build/m1f" + EXT
# src/ as commit 1646c96 holds it (git show 1646c96:src/<file> | sha256sum, DEBRIS-H 2026-11-18; DEBRIS-G's
# EXPECTED.sha256 lists the same 18)
SRC_1646C96 = {
    "src/de421.c": "36b0ab5c5b55e817b87cb8d98e9b11208088f98d0ef664fff9ba39e2595fb87c",
    "src/gfc.c": "d3192e915be6e040dee2fd359c1fa0afaf85336b68201c9a84bae638d346bd95",
    "src/kind_cft128.c": "65a6f301dc112679effc32edf11ba078abcfd521dbb33464af20d8b2d6185bf4",
    "src/kind_cft256.c": "1b806f0101832b6c8e681947cc7b910bb9c9051d6bfe63ce3c50028fea4df0da",
    "src/kind_cft32.c": "dc77c47aac8f8b624d7a7652c169d231d14bd54c86222723578d76b828fb7bcb",
    "src/kind_cft64.c": "6677f41632cb402be7835148fcbf6ba2ae8f2ccea19590c3942735cccfd74e32",
    "src/kind_native32.c": "f6f2ece4f64a74811e5de698cb3ac620817147c1027073da0968cb2d0b61bf14",
    "src/kind_native64.c": "4b7aea3af06b15426c4fc6323aa7e1307ec925d344f302136994a0f180276a16",
    "src/m1.h": "3475ef9f7422e0478fc2d6b7257e698c7609c1fba6cca813409bd61fce745590",
    "src/m1_common.c": "88355dd78365f23e45d5d4853539ca17afd214f61e9f4f6d11926ae1f62ecbd6",
    "src/m1_consts.h": "5de9502b33ea6822ec4507e0c4997c812b1027007219d2b875cf367ccd530e0a",
    "src/m1_ftab.c": "4704b2d34a1bd3fefb4cae3e4cf18921eb5feeba3e62c96a1722160016d0daab",
    "src/m1_kind.h": "091da3175594eda4f0a678877352ca578f32cc918a944ddd6e3a8c09cb156a3b",
    "src/m1_nodes.c": "778ec8402611711a2bba28fa1faf9f47ce466a536dbbbf5d5706502f669d82ce",
    "src/m1_nodes.h": "9aded1a0f98b904f3450df8c46c870ebd02b58fb4ccc195047ef7b3271205ec4",
    "src/m1_ops_cft.h": "4d20f2b9ee1d87c7582267798ada1d1fc001ac655d6a821e55ad155497a74c5c",
    "src/m1_ops_native.h": "5e2051705a645bd4383803a5154ae0fdb399ebefee42e7f34a1e0f1afcd654cf",
    "src/m1_physics.h": "014878b37f82cfc0ee93d4727dea737e38057fcb1d7721f9c65cbe5f197d428f",
}

CRITERIA = """
Every criterion is fixed here, before any data, and asserted in code; the script stops at the first failure of B1 to B5.
B1 every file in in/EXPECTED.sha256 has its listed SHA-256, each printed; and in/src/ holds exactly the 18 files of
   src/ with the SHA-256 that commit 1646c96 gives them (listed in this script), so src/ is byte-identical to 1646c96;
C1 (control) a copy of one source with one byte changed must FAIL the source check of B1, its untouched sibling pass;
B2 gcc -dumpmachine prints the platform's triple (x86_64-linux-gnu on the box, x86_64-w64-mingw32 on the desktop);
B3 libcft.a builds from in/cft-fp256-0aa997a3.tar (`make -C cft-fp256/host CC=gcc libcft.a`; on Windows with
   OS=Windows_NT TMP=/tmp TEMP=/tmp), one job;
B4 M1, m1h.c and m1f.c build at build_f.sh's O2 flags (-std=c11 -O2 -ffp-contract=off -Wall -Wextra; -mfma for the
   native kinds), every compile and link succeeding; on Linux m1f.c alone adds -Ibuild/shim (the lead's
   tests/f9_box_windows.h as windows.h) and -D_POSIX_C_SOURCE=199309L, as tests/f9_box.py built it;
B5 every native object holds at least one vfmadd and no undefined fma, fmaf, sqrt or sqrtf;
   the SHA-256 of every source compiled and of every program built is printed.
H1 SMOKE, at cft256 and at native64, 4 lanes, 2 steps, from the test seed's objects 0 to 3 (in/testseed/seed1.txt),
   the clock map 10^6 s in the past: m1h run exits 0, its step log holds steps 1 and 2, and it writes checkpoints 0
   and 2 of 4 objects each, every state finite; m1h seg from checkpoint 0 by 2 whole steps (mode N) gives checkpoint
   2's bytes for all 4 objects (the NaN rule), and m1h seg from checkpoint 2 to the epoch t_2 + 7.5 s (mode E) exits
   0 with 4 finite states.
"""


def env():
    e = dict(os.environ)
    if WIN:
        e["PATH"] = "C:/msys64/mingw64/bin;C:/msys64/usr/bin;" + e.get("PATH", "")
    e["M1_DOWNLOADS"] = "in/dl/"
    return e


def first_line(args):
    p = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=env())
    lines = p.stdout.decode("utf-8", "replace").splitlines()
    return lines[0].strip() if lines else "(nothing)"


def run(log, args):
    rc, out, err = H.run(args, log, env=env(), check=False)
    if rc != 0:
        for ln in (out + err).decode("utf-8", "replace").splitlines()[-30:]:
            log.w("#   " + ln)
        log.check(False, "the command above failed")
        sys.exit(log.close())
    return out


def check_sources(log, base="in", show=True):
    n = bad = 0
    with open("in/EXPECTED.sha256", encoding="ascii") as f:
        for ln in f:
            ln = ln.rstrip("\n")
            if not ln:
                continue
            h, rel = ln[:64], ln[66:]
            p = os.path.join(base, rel)
            got = H.sha256(p) if os.path.exists(p) else "(absent)"
            n += 1
            if got != h:
                bad += 1
                if show:
                    log.w("# MISMATCH %s: listed %s, found %s" % (rel, h, got))
            elif show:
                log.w("# %s sha256 %s" % (rel, got))
    return n, bad


def main():
    root = sys.argv[1]
    os.chdir(root)
    cpu = H.CpuAccount("h_build", os.environ.get("H_CPU_TSV"))
    log = H.Log("h_build", "logs", SCRIPT, CRITERIA)
    n, bad = check_sources(log)
    srcs = sorted("src/" + f for f in os.listdir("in/src"))
    src_ok = srcs == sorted(SRC_1646C96) and all(H.sha256("in/" + s) == SRC_1646C96[s] for s in srcs)
    if not log.check(n > 0 and bad == 0 and src_ok, "B1 %d files as listed, %d mismatched; in/src/ is the 18 files of commit 1646c96: %s" % (n, bad, src_ok)):
        return log.close()
    # C1
    c1 = "build/c1"
    if os.path.exists(c1):
        log.check(False, "C1 refused: build/c1 exists already (each build starts from clean, in a new root)")
        return log.close()
    os.makedirs(c1)
    for f in ("m1_common.c", "m1.h"):
        shutil.copyfile("in/src/" + f, c1 + "/" + f)
    with open(c1 + "/m1_common.c", "r+b") as f:
        b = bytearray(f.read())
        b[10] ^= 1
        f.seek(0)
        f.write(bytes(b))
    exp = {}
    with open("in/EXPECTED.sha256", encoding="ascii") as f:
        for ln in f:
            ln = ln.rstrip("\n")
            if ln:
                exp[ln[66:]] = ln[:64]
    copy_ok = H.sha256(c1 + "/m1_common.c") == exp["src/m1_common.c"] or H.sha256(c1 + "/m1_common.c") == SRC_1646C96["src/m1_common.c"]
    other_ok = H.sha256(c1 + "/m1.h") == exp["src/m1.h"] == SRC_1646C96["src/m1.h"]
    log.check(other_ok and not copy_ok, "C1 control: the copy's changed source fails the source check (%s), its untouched one passes (%s) - failed as specified"
              % ("mismatch" if not copy_ok else "MATCH", "match" if other_ok else "MISMATCH"))
    m = first_line([GCC, "-dumpmachine"])
    if not log.check(m == MACHINE, "B2 gcc -dumpmachine prints %s" % m):
        return log.close()
    log.w("# " + first_line([GCC, "--version"]))
    if os.path.exists("cft-fp256") or os.path.exists("build/obj"):
        log.check(False, "B3 refused: cft-fp256/ or build/obj exists already (each build starts from clean, in a new root)")
        return log.close()
    with tarfile.open("in/cft-fp256-0aa997a3.tar") as t:
        try:
            t.extractall("cft-fp256", filter="data")
        except TypeError:
            t.extractall("cft-fp256")
    margs = ["--no-print-directory", "-C", "cft-fp256/host", "CC=gcc"] + (["OS=Windows_NT", "TMP=/tmp", "TEMP=/tmp"] if WIN else []) + ["libcft.a"]
    t0 = time.monotonic()
    run(log, [MAKE] + margs)
    log.check(os.path.exists(LIB), "B3 libcft.a built (%.1f s wall), sha256 %s" % (time.monotonic() - t0, H.sha256(LIB) if os.path.exists(LIB) else "-"))
    os.makedirs("build/obj")
    srcs_compiled = ["in/src/" + f for f in sorted(os.listdir("in/src"))] + ["in/tests/m1h.c", "in/tests/m1f.c"]
    if not WIN:
        srcs_compiled.append("in/tests/f9_box_windows.h")
    log.w("# sources compiled (sha256):")
    for s in srcs_compiled:
        log.w("#   %s %s" % (H.sha256(s), s))
    for k in NATIVE:
        run(log, [GCC] + O2 + ["-mfma", "-I" + CI, "-c", "in/src/kind_%s.c" % k, "-o", "build/obj/kind_%s.o" % k])
    for k in CFT:
        run(log, [GCC] + O2 + ["-I" + CI, "-c", "in/src/kind_%s.c" % k, "-o", "build/obj/kind_%s.o" % k])
    for s in COMMON:
        run(log, [GCC] + O2 + ["-I" + CI, "-c", "in/src/%s.c" % s, "-o", "build/obj/%s.o" % s])
    run(log, [GCC] + O2 + ["-I" + CI, "-Iin/src", "-c", "in/tests/m1h.c", "-o", "build/obj/m1h.o"])
    fx = []
    if not WIN:
        os.makedirs("build/shim")
        shutil.copyfile("in/tests/f9_box_windows.h", "build/shim/windows.h")
        fx = ["-Ibuild/shim", "-D_POSIX_C_SOURCE=199309L"]
    run(log, [GCC] + O2 + fx + ["-I" + CI, "-Iin/src", "-c", "in/tests/m1f.c", "-o", "build/obj/m1f.o"])
    kinds = sorted("build/obj/kind_%s.o" % k for k in NATIVE + CFT)
    common = ["build/obj/%s.o" % s for s in COMMON]
    run(log, [GCC, "-o", M1H, "build/obj/m1h.o"] + kinds + common + [LIB, "-lm"])
    run(log, [GCC, "-o", M1F, "build/obj/m1f.o"] + kinds + common + [LIB, "-lm"])
    log.check(True, "B4 every compile and link")
    for k in NATIVE:
        o = "build/obj/kind_%s.o" % k
        dis = subprocess.run([OBJDUMP, "-d", o], stdout=subprocess.PIPE, env=env()).stdout.decode("utf-8", "replace")
        nf = sum(1 for ln in dis.splitlines() if "vfmadd" in ln)
        und = subprocess.run([NM, "-u", o], stdout=subprocess.PIPE, env=env()).stdout.decode("utf-8", "replace").split()
        badu = sorted(set(und) & {"fma", "fmaf", "sqrt", "sqrtf"})
        if not log.check(nf >= 1 and not badu, "B5 %s: vfmadd instructions %d; undefined fma/fmaf/sqrt/sqrtf: %s" % (k, nf, ", ".join(badu) if badu else "none")):
            return log.close()
    for f in (LIB, M1H, M1F):
        log.w("# %s sha256 %s" % (f, H.sha256(f)))
    # H1's smoke runs
    seed = "in/testseed/seed1.txt"
    sd = H.read_seed(seed)
    ts = sd["ts"]
    sseed = H.sha256(seed)
    n_s, smoke = H.next_numbered("h1", "smoke", "")
    os.makedirs(smoke)
    unix_ref = time.time() - 1e6
    for kind in ("cft256", "native64"):
        trk = "S" + kind
        a = [M1H, "run", "--kind", kind, "--table", "in/frame_h0.bin", "--track", trk, "--run", smoke, "--first", 0, "--count", 4,
             "--lanes", 4, "--k0", 0, "--kend", 2, "--unix-ref", "%.6f" % unix_ref, "--t-ref", float.hex(ts), "--allow", 4,
             "--ckpt-every", 2, "--worker", 0, "--nworkers", 1, "--seed", "%s:%s" % (seed, sseed)]
        run(log, a)
        cdir = "%s/ckpt/%s" % (smoke, trk)
        f0, f2 = cdir + "/k000000.w00of01.txt", cdir + "/k000002.w00of01.txt"
        ok = os.path.exists(f0) and os.path.exists(f2)
        h0, r0 = H.read_ckpt(f0) if ok else ({}, {})
        h2, r2 = H.read_ckpt(f2) if ok else ({}, {})
        fin = ok and all(all(abs(H.f64(x)) < float("inf") for x in r[2]) for r in list(r0.values()) + list(r2.values()))
        steps = [ln.split()[1] for ln in open([os.path.join(smoke, "steps", trk, f) for f in os.listdir(os.path.join(smoke, "steps", trk))][0]) if ln.startswith("S ")]
        log.check(ok and len(r0) == 4 and len(r2) == 4 and h0.get("_complete") and h2.get("_complete") and fin and steps == ["1", "2"],
                  "H1 smoke %s run: checkpoints 0 and 2 of 4 objects, every state finite, steps %s" % (kind, steps))
        tg = "%s/%s_seg_targets.txt" % (smoke, kind)
        with open(tg, "w", newline="\n") as f:
            for i in range(4):
                f.write("%d 0 N 2\n" % i)
        out = "%s/%s_seg_n2.txt" % (smoke, kind)
        run(log, [M1H, "seg", "--kind", kind, "--table", "in/frame_h0.bin", "--init", "%s:%s" % (f0, H.sha256(f0)), "--targets", tg, "--out", out, "--lanes", 4])
        segr = {int(ln.split()[1]): ln.split()[7:13] for ln in open(out) if ln.startswith("R ")}
        nb = 8 * H.ESZ[kind]
        same = len(segr) == 4 and all(all(H.same(a_, b_, nb) for a_, b_ in zip(segr[i], r2[i][1])) for i in range(4))
        log.check(same, "H1 smoke %s seg: checkpoint 0 + 2 whole steps equals checkpoint 2's bytes for all 4 objects" % kind)
        tg2 = "%s/%s_seg_e_targets.txt" % (smoke, kind)
        e = ts + 2 * 15.0 + 7.5
        with open(tg2, "w", newline="\n") as f:
            for i in range(4):
                f.write("%d 2 E %s\n" % (i, float.hex(e)))
        out2 = "%s/%s_seg_e.txt" % (smoke, kind)
        run(log, [M1H, "seg", "--kind", kind, "--table", "in/frame_h0.bin", "--init", "%s:%s" % (f2, H.sha256(f2)), "--targets", tg2, "--out", out2, "--lanes", 4])
        se = [ln.split() for ln in open(out2) if ln.startswith("R ")]
        log.check(len(se) == 4 and all(float.fromhex(r[4]) == e and all(abs(H.f64(x)) < float("inf") for x in r[13:19]) for r in se),
                  "H1 smoke %s seg to t_2 + 7.5 s: 4 finite states at the epoch" % kind)
    c = cpu.close("h_build log %03d" % log.n)
    if c is not None:
        log.w("# CPU: %.2f s by cycles / 2.5e9 (this script and every process it started)" % c)
    return log.close()


if __name__ == "__main__":
    sys.exit(main())
