#!/bin/bash
# DEBRIS-B Q3 sweep: a quarter day per leg on the preserved port, through
# unchanged copies of DEBRIS-A's scripts (run_port_copy.py checks them).
# One empty directory per dt, as the plan's Rules require.
PY="C:/Users/logan/AppData/Local/Programs/Miniconda3/python.exe"
S="C:/Users/logan/source/repos/cft-debris-scratch/DEBRIS-B/sweep"
load() { powershell.exe -NoProfile -Command '$a=@(); 1..3 | % { $a += (Get-CimInstance Win32_Processor).LoadPercentage; Start-Sleep -Milliseconds 500 }; "host load % " + ($a -join " ")'; }
leg() { # dir dt steps formats
  echo "### $(date '+%Y-%m-%d %H:%M:%S %z') start dt=$2 steps=$3 formats=$4; $(load)"
  "$PY" -I -B "$S/run_port_copy.py" "$S/$1" --dt "$2" --steps "$3" --formats "$4"
  rc=$?
  echo "### $(date '+%Y-%m-%d %H:%M:%S %z') end dt=$2 rc=$rc; $(load)"
}
leg dt50 50 432 fp64,fp128,fp256 > "$S/dt50/sweep_dt50.log" 2>&1
leg dt25 25 864 fp64,fp128,fp256 > "$S/dt25/sweep_dt25.log" 2>&1
leg dt12p5 12.5 1728 fp128 > "$S/dt12p5/sweep_dt12p5.log" 2>&1
echo "sweep done $(date '+%Y-%m-%d %H:%M:%S %z')"
