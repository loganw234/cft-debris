#!/bin/bash
# DEBRIS-C, M3: the remaining Orekit runs, each through the runner (one numbered log each).
# Version 2: every run again with m3_prop.js version 2 (the plant used JavaScript Math.nextUp, which does
# not exist: m3_prop_ulp.001.log), into m3/out/v2/. The version-1 runs and their logs stay on the record.
set -e
cd C:/Users/logan/source/repos/cft-debris/studies/debris-c
PY=C:/Users/logan/AppData/Local/Programs/Miniconda3/python.exe
run() { label=$1; shift; "$PY" -I -B run.py --label m3_prop_$label --script m3/m3_prop.js -- JJS "$@" m3/m3_prop.js -- m3/out/v2/steps_$label.txt ${ULP:-} | grep -E "^(STEPHASH|FINAL|# steps|# wall|# child CPU cycles|# log)"; }
mkdir -p m3/out/v2
run jit1
run jit2
run jit3
run c1 -XX:TieredStopAtLevel=1
run c2 -XX:-TieredCompilation
ULP=ulp run ulp
run xint -Xint
