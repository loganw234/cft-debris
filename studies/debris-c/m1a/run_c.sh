#!/bin/bash
# DEBRIS-C, M1a and M3: run the custom kernel along Lasser et al.'s TRF orbit (2,880 epochs).
# Which coefficient file: the download itself (the file GROOPS read), except run "copy",
# which reads the de-duplicated copy Orekit reads, to show the two give the same bits.
set -e
S=C:/Users/logan/source/repos/cft-debris-scratch/DEBRIS-C/bin
D=C:/Users/logan/source/repos/cft-debris-downloads
GFC=$D/EIGEN6-C4.gfc/EIGEN6-C4.gfc
COPY=C:/Users/logan/source/repos/cft-debris-scratch/DEBRIS-C/gfc_dedup/EIGEN6-C4.gfc
ORB=$D/00orbit_itrf.txt/00orbit_itrf.txt
O=C:/Users/logan/source/repos/cft-debris/studies/debris-c/m1a/out
mkdir -p $O
sha256sum $S/m1a_grav_O2.exe $S/m1a_grav_native.exe $GFC $COPY $ORB
echo "== run O2 2..180 (download)"; $S/m1a_grav_O2.exe $GFC $ORB 2 180 $O/c_O2_2_180.txt
echo "== run O2 2..180 (copy)";     $S/m1a_grav_O2.exe $COPY $ORB 2 180 $O/c_O2_2_180_copy.txt
echo "== run O2 2..173 (control: truncation at D = 173)"; $S/m1a_grav_O2.exe $GFC $ORB 2 173 $O/c_O2_2_173.txt
echo "== run native 2..180 (download)"; $S/m1a_grav_native.exe $GFC $ORB 2 180 $O/c_native_2_180.txt
echo "== run native 2..180 again (same binary, same input: run-to-run check)"; $S/m1a_grav_native.exe $GFC $ORB 2 180 $O/c_native_2_180_rerun.txt
echo "== run O2 2..180 again (run-to-run check)"; $S/m1a_grav_O2.exe $GFC $ORB 2 180 $O/c_O2_2_180_rerun.txt
echo "== run O2 2..180 with a one-ulp plant at epoch 1000 (M3 control)"; $S/m1a_grav_O2.exe $GFC $ORB 2 180 $O/c_O2_2_180_plant1000.txt 1000
cd $O && sha256sum c_O2_2_180.txt c_O2_2_180_copy.txt c_O2_2_173.txt c_native_2_180.txt c_native_2_180_rerun.txt c_O2_2_180_rerun.txt c_O2_2_180_plant1000.txt
