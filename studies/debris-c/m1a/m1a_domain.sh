#!/bin/bash
# DEBRIS-C, M1a: the comparison's domain, measured (written after m1a_compare.001.log passed).
# Builds m1a_grav.c version 2 (adds an optional coefficient plant; otherwise unchanged) as a new
# executable, and runs it: (1) unplanted, which must reproduce version 1's output bit for bit;
# (2) degree 180 removed (2..179); (3) one degree-180 coefficient, C-bar(180,90), changed by
# 3.09e-10 (Kaula's 1e-5/n^2 at n = 180). m1a_domain.py states and asserts what each must show.
set -e
export PATH="/c/msys64/mingw64/bin:$PATH"
test "$(gcc -dumpmachine)" = "x86_64-w64-mingw32"
S=C:/Users/logan/source/repos/cft-debris-scratch/DEBRIS-C/bin
SRC=C:/Users/logan/source/repos/cft-debris/studies/debris-c/m1a/m1a_grav.c
D=C:/Users/logan/source/repos/cft-debris-downloads
GFC=$D/EIGEN6-C4.gfc/EIGEN6-C4.gfc
ORB=$D/00orbit_itrf.txt/00orbit_itrf.txt
O=C:/Users/logan/source/repos/cft-debris/studies/debris-c/m1a/out
gcc -O2 -o $S/m1a_grav_O2_v2.exe $SRC -lm
sha256sum $SRC $S/m1a_grav_O2_v2.exe
$S/m1a_grav_O2_v2.exe $GFC $ORB 2 180 $O/c_v2_2_180.txt
$S/m1a_grav_O2_v2.exe $GFC $ORB 2 179 $O/c_v2_2_179.txt
$S/m1a_grav_O2_v2.exe $GFC $ORB 2 180 $O/c_v2_2_180_coef180_90.txt -1 180,90,3.09e-10
cd $O && sha256sum c_O2_2_180.txt c_v2_2_180.txt c_v2_2_179.txt c_v2_2_180_coef180_90.txt
