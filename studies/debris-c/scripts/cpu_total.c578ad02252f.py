#!/usr/bin/env python3
"""DEBRIS-C: the CPU time of the processes this study started, COMPUTED from
its own logs (studies/debris-c/logs). For each log:
- runner version 2 logs carry QueryProcessCycleTime; CPU = cycles / 2.5e9
  (the 2.5 GHz reference rate is BELIEVED; logs/m2_cyclecal.001.log measured
  2.42e9 to 2.44e9 cycles a wall second for a busy native thread);
- runner version 1 logs carry only GetProcessTimes, which reads about a
  quarter of the real CPU on this host today (m2_cyclecal.001.log); for them
  CPU is taken as the larger of 4 x GetProcessTimes and the wall time;
- a log whose child is bash (builds and kernel runs) undercounts its own
  children either way, so its wall time is used as the stand-in.
Also adds the JVM exploration runs outside the runner (api dumps, about 2 s
of wall each, BELIEVED under 10 CPU-seconds in all).

  python -I -B cpu_total.py
"""
import os
import re

LOGS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")


def main():
    tot = 0.0
    rows = []
    for f in sorted(os.listdir(LOGS)):
        if not f.endswith(".log"):
            continue
        t = open(os.path.join(LOGS, f), encoding="utf-8").read()
        wall = float(re.search(r"^# wall: ([0-9.]+) s", t, re.M).group(1))
        gpt = float(re.search(r"= ([0-9.]+) s\n", t[t.find("# wall:"):]).group(1))
        cyc = re.search(r"QueryProcessCycleTime\): \d+ = ([0-9.]+) s", t)
        cmd = re.search(r"^# command: (.*)$", t, re.M).group(1)
        if "bash.exe" in cmd:
            cpu, how = wall, "wall (bash parent)"
        elif cyc:
            cpu, how = float(cyc.group(1)), "cycles"
        else:
            cpu, how = max(4 * gpt, wall), "max(4 x GetProcessTimes, wall)"
        tot += cpu
        rows.append((f, wall, gpt, cpu, how))
    for r in rows:
        print("%-32s wall %7.2f s  GetProcessTimes %7.2f s  counted %7.2f s  (%s)" % r)
    print("# total counted: %.1f CPU-seconds = %.2f CPU-minutes over %d logs; plus about 10 s outside the runner (BELIEVED)"
          % (tot, tot / 60, len(rows)))


if __name__ == "__main__":
    main()
