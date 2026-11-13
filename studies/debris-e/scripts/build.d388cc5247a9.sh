#!/bin/bash
# build.sh - cft-debris M1: build the library and the gates' programs in every
# variant the gates use, and check every native object.
# cft-debris, MIT licence (see LICENSE at the repository root). Written by
# DEBRIS-E, 2026-11-13.
#
# usage: bash tests/build.sh <cft-fp256 host dir, with libcft.a built> <output dir>
#   e.g. bash tests/build.sh C:/.../cft-fp256/host C:/.../build
#
# Variants (one object per kind each; see DEBRIS-E's build report):
#   O2      -std=c11 -O2 -ffp-contract=off; native kinds add -mfma   (the reference build)
#   O0      the same at -O0                                           (E8)
#   fast    native kinds -O2 -ffp-contract=fast -mfma                (E8's control: must differ)
#   negctl  native kinds -O2 ... -DM1_NEGCTL_REORDER                  (E1's negative control)
#   nofma   fmacheck.c without -mfma: fma() is the C library's routine (E1's finding)
#
# CRITERIA (written before any build; asserted - the script stops at the first failure):
#   1. gcc -dumpmachine prints x86_64-w64-mingw32;
#   2. every native object of O2, O0, negctl and fast holds at least one vfmadd, and none
#      has an undefined symbol fma, fmaf, sqrt or sqrtf (nm -u): the FMA and square-root
#      instructions, never the library routines;
#   3. FLT_EVAL_METHOD is 0 for the native kinds: m1_ops_native.h refuses to compile otherwise;
#   4. fmacheck_nofma.o has an undefined fma (the library routine is what it tests) and no
#      vfmadd; fmacheck_fma.o has a vfmadd and no undefined fma;
#   5. every compile and link succeeds.
set -euo pipefail
export PATH="/c/msys64/mingw64/bin:$PATH"
CFTH="$1"
OUT="$2"
HERE="$(cd "$(dirname "$0")" && pwd)"
SRC="$HERE/../src"
TST="$HERE"
CI="$CFTH/include"
LIB="$CFTH/libcft.a"
M=$(gcc -dumpmachine)
echo "gcc -dumpmachine: $M"
test "$M" = "x86_64-w64-mingw32" || { echo "CRITERION 1 FAILED"; exit 1; }
echo "CRITERION 1 PASS"
gcc --version | head -1
objdump --version | head -1
echo "libcft.a: $(sha256sum "$LIB" | cut -c1-64)"
echo "FLT_EVAL_METHOD with -mfma: $(echo '#include <float.h>
FLT_EVAL_METHOD' | gcc -std=c11 -mfma -E -P - | tail -1)"
mkdir -p "$OUT"

KINDS_NATIVE="native32 native64"
KINDS_CFT="cft32 cft64 cft128 cft256"
COMMONSRC="m1_common gfc de421"

build_variant() {
    local v="$1" cf="$2" nf="$3"
    local d="$OUT/$v"
    mkdir -p "$d"
    for k in $KINDS_NATIVE; do
        echo "[$v] gcc $nf -I$CI -c src/kind_$k.c"
        gcc $nf -I"$CI" -c "$SRC/kind_$k.c" -o "$d/kind_$k.o"
    done
    for k in $KINDS_CFT; do
        echo "[$v] gcc $cf -I$CI -c src/kind_$k.c"
        gcc $cf -I"$CI" -c "$SRC/kind_$k.c" -o "$d/kind_$k.o"
    done
    for f in $COMMONSRC; do
        gcc $cf -I"$CI" -c "$SRC/$f.c" -o "$d/$f.o"
    done
    gcc $cf -I"$CI" -I"$SRC" -c "$TST/m1run.c" -o "$d/m1run.o"
    echo "[$v] link m1run_$v.exe"
    gcc -o "$OUT/m1run_$v.exe" "$d/m1run.o" "$d"/kind_*.o "$d"/m1_common.o "$d"/gfc.o "$d"/de421.o "$LIB" -lm
    for k in $KINDS_NATIVE; do
        local o="$d/kind_$k.o"
        local nf_=$(objdump -d "$o" | grep -c vfmadd || true)
        local bad=$(nm -u "$o" | grep -wE "fma|fmaf|sqrt|sqrtf" || true)
        echo "[$v] $k: vfmadd instructions $nf_; undefined fma/fmaf/sqrt/sqrtf: '${bad}'"
        if [ "$nf_" -lt 1 ] || [ -n "$bad" ]; then echo "CRITERION 2 FAILED for $v $k"; exit 1; fi
    done
}

O2="-std=c11 -O2 -ffp-contract=off -Wall -Wextra"
O0="-std=c11 -O0 -ffp-contract=off -Wall -Wextra"
build_variant O2 "$O2" "$O2 -mfma"
build_variant O0 "$O0" "$O0 -mfma"
build_variant fast "$O2" "-std=c11 -O2 -ffp-contract=fast -mfma -Wall -Wextra"
build_variant negctl "$O2" "$O2 -mfma -DM1_NEGCTL_REORDER"
echo "CRITERION 2 PASS (O2, O0, fast, negctl); CRITERION 3 PASS (the native kinds compiled)"

# E7: the native64 force model and rk4 as a DLL for REBOUND's ctypes callback (O2 objects)
gcc $O2 -I"$CI" -I"$SRC" -c "$TST/m1x.c" -o "$OUT/O2/m1x.o"
gcc -shared -o "$OUT/m1x.dll" "$OUT/O2/m1x.o" "$OUT/O2"/kind_*.o "$OUT/O2"/m1_common.o "$OUT/O2"/gfc.o \
    "$OUT/O2"/de421.o "$LIB" -lm
echo "linked m1x.dll"

# E1's finding: the C library's fma against the instruction, each held to libcft's CFT_FMA
gcc -std=c11 -O2 -ffp-contract=off -I"$CI" -c "$TST/fmacheck.c" -o "$OUT/fmacheck_nofma.o"
gcc -std=c11 -O2 -ffp-contract=off -mfma -I"$CI" -c "$TST/fmacheck.c" -o "$OUT/fmacheck_fma.o"
nf0=$(objdump -d "$OUT/fmacheck_nofma.o" | grep -c vfmadd || true)
u0=$(nm -u "$OUT/fmacheck_nofma.o" | grep -wc fma || true)
nf1=$(objdump -d "$OUT/fmacheck_fma.o" | grep -c vfmadd || true)
u1=$(nm -u "$OUT/fmacheck_fma.o" | grep -wc fma || true)
echo "fmacheck_nofma.o: vfmadd $nf0, undefined fma $u0; fmacheck_fma.o: vfmadd $nf1, undefined fma $u1"
if [ "$nf0" -ne 0 ] || [ "$u0" -lt 1 ] || [ "$nf1" -lt 1 ] || [ "$u1" -ne 0 ]; then echo "CRITERION 4 FAILED"; exit 1; fi
echo "CRITERION 4 PASS"
gcc -o "$OUT/fmacheck_nofma.exe" "$OUT/fmacheck_nofma.o" "$LIB" -lm
gcc -o "$OUT/fmacheck_fma.exe" "$OUT/fmacheck_fma.o" "$LIB" -lm
echo "CRITERION 5 PASS (every compile and link)"
sha256sum "$OUT"/*.exe "$OUT"/*.dll | sed "s#$OUT/##"
echo "BUILD PASS"
