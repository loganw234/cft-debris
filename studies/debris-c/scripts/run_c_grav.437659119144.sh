#!/bin/bash
# DEBRIS-C, M2: DEBRIS-B's C gravity kernel (q2/q2bench.c with grav_body.inc, Cunningham, unnormalised,
# synthetic Kaula-rule coefficients), timed again now, in the same hours as the Orekit timings, at
# degrees 8, 20, 36 and 70. Copies are taken into DEBRIS-C's scratch and checked against DEBRIS-B's
# MANIFEST.sha256 first; DEBRIS-B's records are not touched. Each figure: 5 repetitions of about 0.25 s;
# q2bench prints each repetition's wall ns a call, thread cycles a call and host load.
set -e
export PATH="/c/msys64/mingw64/bin:$PATH"
test "$(gcc -dumpmachine)" = "x86_64-w64-mingw32"
B=C:/Users/logan/source/repos/cft-debris/studies/debris-b
S=C:/Users/logan/source/repos/cft-debris-scratch/DEBRIS-C/q2copy
mkdir -p $S
cp $B/q2/q2bench.c $B/q2/grav_body.inc $S/
for f in q2bench.c grav_body.inc; do
  want=$(grep " \*q2/$f\$" $B/MANIFEST.sha256 | cut -d' ' -f1)
  got=$(sha256sum $S/$f | cut -d' ' -f1)
  echo "$f: copy $got, DEBRIS-B manifest $want"
  test -n "$want"
  test "$got" = "$want"
done
cd $S
gcc -O2 -o q2bench.exe q2bench.c -lquadmath
sha256sum q2bench.exe
for spec in "8 1400000" "20 300000" "36 100000" "70 25000"; do
  set -- $spec
  echo "== grav N=$1, ncall $2, 5 repetitions"
  ./q2bench.exe time grav $1 $2 5
done
