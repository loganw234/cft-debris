#!/bin/bash
# build_i.sh - cft-debris DEBRIS-I: build M1 (src/, unchanged) with tests/m1i.c, and the program's driver tests/i_run.c,
# against one libcft build, on the desktop (mingw64) or the box (gcc, Linux). Modelled on DEBRIS-F's tests/build_f.sh
# (cft-debris's own, MIT), whose O2 flags it uses; build_f.sh stays as it was.
# cft-debris, MIT licence (see LICENSE at the repository root). Written by DEBRIS-I, 2026-11-23.
#
# usage: bash build_i.sh build <cft-fp256 host dir, libcft.a built> <output dir> <src dir> <tests dir> <expected src sha256>
#        bash build_i.sh check <src dir> <expected src sha256>       (the source check alone: I0's control C1 runs it)
#
# CRITERIA (written before any build; asserted - the script stops at the first failure):
#   S1 every file of <src dir> is in <expected> with that SHA-256, and every file there is present: src/ as commit
#      1646c96 holds it (the expected list is made from `git show 1646c96:src/<file>`); every hash printed;
#   B1 gcc -dumpmachine prints x86_64-w64-mingw32 (desktop) or x86_64-linux-gnu (box);
#   B2 the SHA-256 of every source and header compiled, and of libcft.a, is printed before the first compile;
#   B3 every native object holds at least one vfmadd and has no undefined fma, fmaf, sqrt or sqrtf (nm -u);
#   B4 every compile and link succeeds.
set -euo pipefail
case "$(uname -s)" in
  MINGW*|MSYS*) export PATH="/c/msys64/mingw64/bin:/usr/bin:$PATH"; EXE=.exe; WANT=x86_64-w64-mingw32 ;;
  *) EXE=; WANT=x86_64-linux-gnu ;;
esac

check_src() {
  local src="$1" exp="$2" bad=0 n=0
  # every expected file present with its hash
  while read -r h f; do
    f="${f#\*}"
    n=$((n + 1))
    if [ ! -f "$src/$f" ]; then echo "S1: $f missing"; bad=1; continue; fi
    g=$(sha256sum < "$src/$f" | cut -c1-64)   # from stdin: a backslash in the path cannot reach sha256sum's line
    echo "S1: $g $f (expected $h)"
    if [ "$g" != "$h" ]; then echo "S1: $f DIFFERS"; bad=1; fi
  done < "$exp"
  # no file beyond the list
  for p in "$src"/*; do
    b=$(basename "$p")
    if ! grep -q " [*]*$b\$" "$exp"; then echo "S1: $b is not in the list"; bad=1; fi
  done
  if [ "$n" -lt 1 ]; then echo "S1: the expected list is empty"; bad=1; fi
  if [ "$bad" -ne 0 ]; then echo "CRITERION S1 FAILED"; return 1; fi
  echo "CRITERION S1 PASS ($n files)"
}

if [ "${1:-}" = "check" ]; then
  check_src "$2" "$3"
  exit $?
fi
if [ "${1:-}" != "build" ]; then echo "usage: build_i.sh build|check ..."; exit 64; fi
CFTH="$2"; OUT="$3"; SRC="$4"; TST="$5"; EXP="$6"
check_src "$SRC" "$EXP"
M=$(gcc -dumpmachine)
echo "gcc -dumpmachine: $M"
test "$M" = "$WANT" || { echo "CRITERION B1 FAILED"; exit 1; }
echo "CRITERION B1 PASS"
gcc --version | head -1
CI="$CFTH/include"
LIB="$CFTH/libcft.a"
echo "libcft.a: $(sha256sum < "$LIB" | cut -c1-64)"
echo "cft.h: $(sha256sum < "$CI/cft.h" | cut -c1-64)"
mkdir -p "$OUT/obj"
echo "sources built (sha256):"
sha256sum "$SRC"/*.c "$SRC"/*.h "$TST/m1i.c" "$TST/i_run.c" | sed "s#$SRC/#src/#; s#$TST/#tests/#"
echo "CRITERION B2 PASS (the hashes above)"
O2="-std=c11 -O2 -ffp-contract=off -Wall -Wextra"
for k in native32 native64; do
  gcc $O2 -mfma -I"$CI" -c "$SRC/kind_$k.c" -o "$OUT/obj/kind_$k.o"
done
for k in cft32 cft64 cft128 cft256; do
  gcc $O2 -I"$CI" -c "$SRC/kind_$k.c" -o "$OUT/obj/kind_$k.o"
done
for f in m1_common gfc de421 m1_ftab m1_nodes; do
  gcc $O2 -I"$CI" -c "$SRC/$f.c" -o "$OUT/obj/$f.o"
done
gcc $O2 -I"$CI" -I"$SRC" -c "$TST/m1i.c" -o "$OUT/obj/m1i.o"
gcc -o "$OUT/m1i$EXE" "$OUT/obj/m1i.o" "$OUT"/obj/kind_*.o "$OUT/obj/m1_common.o" "$OUT/obj/gfc.o" "$OUT/obj/de421.o" \
    "$OUT/obj/m1_ftab.o" "$OUT/obj/m1_nodes.o" "$LIB" -lm
echo "linked m1i$EXE"
gcc $O2 -I"$CI" -o "$OUT/i_run$EXE" "$TST/i_run.c" "$LIB" -lm
echo "linked i_run$EXE"
for k in native32 native64; do
  o="$OUT/obj/kind_$k.o"
  nf=$(objdump -d "$o" | grep -c vfmadd || true)
  bad=$(nm -u "$o" | grep -wE "fma|fmaf|sqrt|sqrtf" || true)
  echo "$k: vfmadd instructions $nf; undefined fma/fmaf/sqrt/sqrtf: '${bad}'"
  if [ "$nf" -lt 1 ] || [ -n "$bad" ]; then echo "CRITERION B3 FAILED for $k"; exit 1; fi
done
echo "CRITERION B3 PASS"
echo "CRITERION B4 PASS (every compile and link)"
sha256sum "$OUT/m1i$EXE" "$OUT/i_run$EXE" | sed "s#$OUT/##"
echo "BUILD PASS"
