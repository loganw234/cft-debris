#!/bin/bash
# build_f.sh - cft-debris M1 (DEBRIS-F): build the library and DEBRIS-F's programs in the variants its gates use,
# and check every native object. Modelled on DEBRIS-E's tests/build.sh (cft-debris's own, MIT), which stays as it
# was for DEBRIS-E's gates.
# cft-debris, MIT licence (see LICENSE at the repository root). Written by DEBRIS-F, 2026-11-16.
#
# usage: bash tests/build_f.sh <cft-fp256 host dir, with libcft.a built> <output dir>
#
# Variants:
#   O2      -std=c11 -O2 -ffp-contract=off; native kinds add -mfma          (the reference build)
#   O0      the same at -O0                                                  (F8)
#   negctl  O2 with -DM1_NEGCTL_FRAME for the native kinds only              (F1's negative control)
# Programs: m1f_<v>.exe (tests/m1f.c), m1run_<v>.exe (DEBRIS-E's tests/m1run.c, unchanged, against this src/),
# m1nodes.exe (tests/m1nodes.c, the frame node routine).
#
# CRITERIA (written before any build; asserted - the script stops at the first failure):
#   1. gcc -dumpmachine prints x86_64-w64-mingw32;
#   2. every native object of O2, O0 and negctl holds at least one vfmadd and has no undefined fma, fmaf, sqrt
#      or sqrtf (nm -u);
#   3. the native kinds compile (m1_ops_native.h refuses FLT_EVAL_METHOD != 0);
#   4. every compile and link succeeds;
#   5. the SHA-256 of every source and header compiled is printed before the first compile.
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
echo "libcft.a: $(sha256sum "$LIB" | cut -c1-64)"
mkdir -p "$OUT"
echo "sources built (sha256):"
( cd "$HERE/.." && sha256sum src/*.c src/*.h tests/m1f.c tests/m1run.c tests/m1nodes.c )
echo "CRITERION 5 PASS (the hashes above)"

KINDS_NATIVE="native32 native64"
KINDS_CFT="cft32 cft64 cft128 cft256"
COMMONSRC="m1_common gfc de421 m1_ftab m1_nodes"

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
    for p in m1f m1run; do
        gcc $cf -I"$CI" -I"$SRC" -c "$TST/$p.c" -o "$d/$p.o"
        gcc -o "$OUT/${p}_$v.exe" "$d/$p.o" "$d"/kind_*.o "$d"/m1_common.o "$d"/gfc.o "$d"/de421.o "$d"/m1_ftab.o "$d"/m1_nodes.o "$LIB" -lm
        echo "[$v] linked ${p}_$v.exe"
    done
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
build_variant negctl "$O2" "$O2 -mfma -DM1_NEGCTL_FRAME"
echo "CRITERION 2 PASS (O2, O0, negctl); CRITERION 3 PASS (the native kinds compiled)"
gcc $O2 -I"$CI" -I"$SRC" -o "$OUT/m1nodes.exe" "$TST/m1nodes.c" "$SRC/m1_nodes.c" "$LIB" -lm
echo "linked m1nodes.exe"
echo "CRITERION 4 PASS (every compile and link)"
sha256sum "$OUT"/*.exe | sed "s#$OUT/##"
echo "BUILD PASS"
