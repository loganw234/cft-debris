#!/bin/bash
# DEBRIS-C, M1a and M3: build the custom gravity kernel twice, and show whether
# the second build really contains fused multiply-adds.
# Criteria (asserted): gcc targets x86_64-w64-mingw32; the -O2 build has no FMA
# instruction in its own code (main, where grav() is inlined); the native build has
# at least one there.
set -e
export PATH="/c/msys64/mingw64/bin:$PATH"
S=C:/Users/logan/source/repos/cft-debris-scratch/DEBRIS-C/bin
SRC=C:/Users/logan/source/repos/cft-debris/studies/debris-c/m1a/m1a_grav.c
mkdir -p $S
M=$(gcc -dumpmachine)
echo "gcc -dumpmachine: $M"
test "$M" = "x86_64-w64-mingw32"
gcc --version | head -1
objdump --version | head -1
echo "build 1: gcc -O2 -o m1a_grav_O2.exe m1a_grav.c -lm"
gcc -O2 -o $S/m1a_grav_O2.exe $SRC -lm
echo "build 2: gcc -O2 -march=native -ffp-contract=fast -o m1a_grav_native.exe m1a_grav.c -lm"
gcc -O2 -march=native -ffp-contract=fast -o $S/m1a_grav_native.exe $SRC -lm
echo "predefined macros, gcc -O2 (FMA-related):"
echo | gcc -O2 -dM -E - | grep -E "__FMA__|__FP_FAST_FMA |__AVX2__" || echo "  (none)"
echo "predefined macros, gcc -O2 -march=native (FMA-related):"
echo | gcc -O2 -march=native -dM -E - | grep -E "__FMA__|__FP_FAST_FMA |__AVX2__"
echo "-march=native resolves to: $(gcc -march=native -Q --help=target | grep -E '^\s+-march=' | awk '{print $2}')"
RE='\bvfn?m(add|sub)(add|sub)?[0-9]{3}[ps][sd]\b'
for b in O2 native; do
  all=$(objdump -d $S/m1a_grav_$b.exe | grep -cE "$RE" || true)
  own=$(objdump -d --disassemble=main $S/m1a_grav_$b.exe | grep -cE "$RE" || true)
  tables=$(objdump -d --disassemble=tables $S/m1a_grav_$b.exe | grep -cE "$RE" || true)
  echo "FMA instructions in m1a_grav_$b.exe: whole binary $all; in main (grav inlined) $own; in tables() $tables"
  eval "OWN_$b=$own"
done
echo "objdump -d --disassemble=main | grep -E vfmadd... (first 5 lines of the native build):"
objdump -d --disassemble=main $S/m1a_grav_native.exe | grep -E "$RE" | head -5
test "$OWN_O2" -eq 0
test "$OWN_native" -ge 1
echo "ASSERT PASS: -O2 build has no FMA in main; native build has $OWN_native"
sha256sum $S/m1a_grav_O2.exe $S/m1a_grav_native.exe
