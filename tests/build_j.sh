#!/bin/bash
# build_j.sh - cft-debris DEBRIS-J: build libcft from cft-fp256's archive at 9e8ff270 and link tests/j_run.c against it:
#   gpu      in cft-gpu (Linux, the lead's run): libcft with the GPU backend on HIP 7.2.4's NVIDIA layer, and j_run
#            linked with the Makefile's NVIDIA libraries;
#   desktop  on the desktop (mingw64): libcft's software build, with j_run and DEBRIS-I's i_run (for j_run's desktop
#            gate, which holds j_run to i_run's bytes).
# Modelled on DEBRIS-I's tests/build_i.sh (cft-debris's own, MIT), which stays as it was.
# cft-debris, MIT licence (see LICENSE at the repository root). Written by DEBRIS-J, 2026-11-23.
#
# usage: HIP=1 HIP_PLATFORM=nvidia HIP_ROOT=<dir> HIP_ARCH=<arch> HIP_CUDA=<dir> \
#          bash build_j.sh gpu <work dir> <archive .tar> <tests dir>
#        bash build_j.sh desktop <work dir> <archive .tar> <tests dir>
# The work dir is the build's own folder; the archive is extracted into <work dir>/cft-fp256-9e8ff270 (and, if that
# folder exists already, compared with the archive by tar's --diff and reused).
#
# CRITERIA (written before any build; asserted - the script stops at the first failure):
#   G0 (gpu only) HIP is 1, HIP_PLATFORM is nvidia, and HIP_ROOT, HIP_ARCH and HIP_CUDA are given (no default is
#      taken for any of them); all five are printed; HIP_ROOT/bin/hipcc and HIP_CUDA/lib64 exist;
#   A1 the archive's SHA-256 is 7814576d5d4d23fa4c1797553a32cd19b4e1d4c8f2d67fb7faecc9cfecb1c4bb (9e8ff270's, lead.md's);
#      no member is absolute or climbs out with ..; the extracted tree equals the archive (tar --diff);
#   B1 the C compiler's -dumpmachine is x86_64-linux-gnu (gpu) or x86_64-w64-mingw32 (desktop);
#   B2 libcft.a builds: gpu, make -C host HIP=1 HIP_PLATFORM=nvidia HIP_ROOT HIP_ARCH HIP_CUDA libcft.a, and its
#      hip-symcheck line ("... none in both") is printed (the Makefile holds libcft.a to it); desktop, make -C host
#      CC=gcc OS=Windows_NT TMP=/tmp TEMP=/tmp libcft.a;
#   B3 the SHA-256 of every source compiled (j_run.c, i_run.c, cft.h) and of libcft.a is printed before the link;
#   B4 j_run links (gpu: with -L$HIP_CUDA/lib64 -Wl,-rpath,$HIP_CUDA/lib64 -lcudart -lstdc++ -lpthread -ldl -lrt, the
#      Makefile's HIPLIBS for nvidia, host/Makefile lines 153-154 at 9e8ff270); the binaries' SHA-256 are printed;
#      gpu: ldd names libcudart from HIP_CUDA.
set -euo pipefail
MODE="${1:-}"
case "$MODE" in gpu|desktop) ;; *) echo "usage: build_j.sh gpu|desktop <work dir> <archive .tar> <tests dir>"; exit 64 ;; esac
WORK="$2"; TAR="$3"; TST="$4"
ARCHIVE_SHA=7814576d5d4d23fa4c1797553a32cd19b4e1d4c8f2d67fb7faecc9cfecb1c4bb
TREE="$WORK/cft-fp256-9e8ff270"

if [ "$MODE" = gpu ]; then
  bad=0
  for v in HIP HIP_PLATFORM HIP_ROOT HIP_ARCH HIP_CUDA; do
    if [ -z "${!v:-}" ]; then echo "G0: $v is not given"; bad=1; else echo "G0: $v=${!v}"; fi
  done
  if [ "$bad" -ne 0 ]; then echo "CRITERION G0 FAILED: every one of HIP, HIP_PLATFORM, HIP_ROOT, HIP_ARCH and HIP_CUDA must be given"; exit 1; fi
  if [ "$HIP" != 1 ] || [ "$HIP_PLATFORM" != nvidia ]; then echo "CRITERION G0 FAILED: HIP must be 1 and HIP_PLATFORM nvidia"; exit 1; fi
  if [ ! -x "$HIP_ROOT/bin/hipcc" ] || [ ! -d "$HIP_CUDA/lib64" ]; then echo "CRITERION G0 FAILED: no $HIP_ROOT/bin/hipcc or no $HIP_CUDA/lib64"; exit 1; fi
  echo "CRITERION G0 PASS"
  CC_=cc; EXE=; WANT=x86_64-linux-gnu
else
  export PATH="/c/msys64/mingw64/bin:/usr/bin:$PATH"
  CC_=gcc; EXE=.exe; WANT=x86_64-w64-mingw32
fi

# A1: the archive
got=$(sha256sum < "$TAR" | cut -c1-64)
echo "A1: archive SHA-256 $got"
if [ "$got" != "$ARCHIVE_SHA" ]; then echo "CRITERION A1 FAILED: the archive is not 9e8ff270's"; exit 1; fi
if tar --force-local -tf "$TAR" | grep -qE '^/|(^|/)\.\.(/|$)'; then echo "CRITERION A1 FAILED: a member is absolute or climbs out"; exit 1; fi
mkdir -p "$WORK"
if [ ! -d "$TREE" ]; then
  mkdir "$TREE"
  tar --force-local -xf "$TAR" -C "$TREE"
  echo "A1: extracted into the work dir's cft-fp256-9e8ff270"
else
  echo "A1: the work dir's cft-fp256-9e8ff270 exists: compared with the archive and reused"
fi
# tar --diff also reports a member's mode, owner and time, which extraction need not keep: only its contents, size,
# type and presence are held here (a line naming any of those, or any line of another kind, fails)
tar --force-local --diff -f "$TAR" -C "$TREE" > "$WORK/tar-diff.txt" 2>&1 || true
if grep -vE ': (Mode|Uid|Gid|Mod time) differs$' "$WORK/tar-diff.txt" > "$WORK/tar-diff-content.txt"; then
  echo "CRITERION A1 FAILED: the extracted tree differs from the archive:"; head -20 "$WORK/tar-diff-content.txt"; exit 1
fi
echo "A1: tar --diff: $(wc -l < "$WORK/tar-diff.txt") lines, every one a mode, owner or time; none of contents, size, type or presence"
echo "CRITERION A1 PASS ($(tar --force-local -tf "$TAR" | wc -l) members, the tree's contents equal to them)"

# B1: the compiler
M=$($CC_ -dumpmachine)
echo "B1: $CC_ -dumpmachine: $M"
$CC_ --version | head -1
if [ "$M" != "$WANT" ]; then echo "CRITERION B1 FAILED"; exit 1; fi
echo "CRITERION B1 PASS"

# B2: libcft.a
if [ "$MODE" = gpu ]; then
  echo "B2: make -C <tree>/host HIP=1 HIP_PLATFORM=$HIP_PLATFORM HIP_ROOT=$HIP_ROOT HIP_ARCH=$HIP_ARCH HIP_CUDA=$HIP_CUDA libcft.a"
  make -C "$TREE/host" HIP=1 HIP_PLATFORM="$HIP_PLATFORM" HIP_ROOT="$HIP_ROOT" HIP_ARCH="$HIP_ARCH" HIP_CUDA="$HIP_CUDA" \
       libcft.a > "$WORK/make-libcft.txt" 2>&1 || { echo "CRITERION B2 FAILED: make:"; tail -30 "$WORK/make-libcft.txt"; exit 1; }
  sed "s#$TREE#<tree>#g; s#$WORK#<work>#g" "$WORK/make-libcft.txt" | tail -12
  # gen/hip/symcheck.ok is never made as a file, so every make of libcft.a with HIP=1 runs the check and prints its line
  if ! grep -q "^hip-symcheck: .* none in both" "$WORK/make-libcft.txt"; then
    echo "CRITERION B2 FAILED: no passing hip-symcheck line"; exit 1
  fi
else
  echo "B2: make -C <tree>/host CC=gcc OS=Windows_NT TMP=/tmp TEMP=/tmp libcft.a"
  make -C "$TREE/host" CC=gcc OS=Windows_NT TMP=/tmp TEMP=/tmp libcft.a > "$WORK/make-libcft.txt" 2>&1 \
       || { echo "CRITERION B2 FAILED: make:"; tail -30 "$WORK/make-libcft.txt"; exit 1; }
  sed "s#$TREE#<tree>#g; s#$WORK#<work>#g" "$WORK/make-libcft.txt" | tail -3
fi
LIB="$TREE/host/libcft.a"
test -f "$LIB" || { echo "CRITERION B2 FAILED: no libcft.a"; exit 1; }
echo "CRITERION B2 PASS"

# B3: the sources
echo "B3: libcft.a $(sha256sum < "$LIB" | cut -c1-64)"
echo "B3: include/cft.h $(sha256sum < "$TREE/host/include/cft.h" | cut -c1-64)"
echo "B3: tests/j_run.c $(sha256sum < "$TST/j_run.c" | cut -c1-64)"
if [ "$MODE" = desktop ]; then echo "B3: tests/i_run.c $(sha256sum < "$TST/i_run.c" | cut -c1-64)"; fi
echo "CRITERION B3 PASS (the hashes above)"

# B4: the links
O2="-std=c11 -O2 -ffp-contract=off -Wall -Wextra"
if [ "$MODE" = gpu ]; then
  HIPLIBS="-L$HIP_CUDA/lib64 -Wl,-rpath,$HIP_CUDA/lib64 -lcudart -lstdc++ -lpthread -ldl -lrt"
  echo "B4: $CC_ $O2 -I<tree>/host/include -o <work>/j_run tests/j_run.c <tree>/host/libcft.a $HIPLIBS -lm"
  $CC_ $O2 -I"$TREE/host/include" -o "$WORK/j_run" "$TST/j_run.c" "$LIB" $HIPLIBS -lm
  # the CUDA runtime the loader takes must be HIP_CUDA's (its real folder, whatever symbolic links lie between)
  CUDART=$(ldd "$WORK/j_run" | awk '/libcudart/ {print $3; exit}')
  if [ -z "$CUDART" ] || [ "$(dirname "$(readlink -f "$CUDART")")" != "$(readlink -f "$HIP_CUDA/lib64")" ]; then
    echo "CRITERION B4 FAILED: ldd does not name libcudart from HIP_CUDA's lib64:"; ldd "$WORK/j_run"; exit 1
  fi
  echo "B4: ldd: $(ldd "$WORK/j_run" | grep cudart | sed 's/ (0x[0-9a-f]*)//'), in HIP_CUDA's lib64"
  echo "B4: j_run $(sha256sum < "$WORK/j_run" | cut -c1-64)"
else
  $CC_ $O2 -I"$TREE/host/include" -o "$WORK/j_run$EXE" "$TST/j_run.c" "$LIB" -lm
  $CC_ $O2 -I"$TREE/host/include" -o "$WORK/i_run$EXE" "$TST/i_run.c" "$LIB" -lm
  echo "B4: j_run$EXE $(sha256sum < "$WORK/j_run$EXE" | cut -c1-64)"
  echo "B4: i_run$EXE $(sha256sum < "$WORK/i_run$EXE" | cut -c1-64)"
fi
echo "CRITERION B4 PASS"
echo "BUILD PASS ($MODE)"
