# DEBRIS-F's report

The agent's final message, which is its report, filed verbatim by cft-debris's lead at 2026-11-16 09:58 -0700 with `cft-debris-ledger\dispatch\file_report.py`. Model claude-opus-5-5; final message timestamped 2026-11-16T16:57:56.890Z (UTC). Harness usage: <subagent_tokens>146958</subagent_tokens><tool_uses>367</tool_uses><duration_ms>12093411</duration_ms>. The text below is identical in the agent's own transcript and in the completion notice the lead received (as sent); a one-character change was shown to break that comparison. Body SHA-256 `cd8d63db1ad21983c5ad377543b9b8a783f380d1d7e2600b09c675338c8835fd`.

---

**DEBRIS-F: the report.** Nothing is committed, and nothing is verified: verifier-F has not run. The build report is `studies\DEBRIS-F-build.md` (SHA-256 `bb2f891d…`). Its records are in `studies\debris-f\` (56 files, and every line of `MANIFEST.sha256` checks OK). The three per-object tables are in `cft-debris-ledger\debris-f\`. No process of mine is running. I took your 09:50 correction into §8 and into a new item 8 in §10, with a ledger entry at 09:53:52.

**What was built** (in `src\` and `tests\`, each file headed cft-debris, MIT):
- **B1:** UTC, TAI, TT, TDB (Circular 179's eq. 2.6) and UT1, put onto M1's TDB grid. Each object runs from its own exact origin and ends on one exact short step.
- **B2:** the IERS 2010 CIO-based frame (the full IAU 2006/2000A series; Bulletin B, else A). It is computed once per window at binary256 through libcft into a node table. Every kind receives the table correctly rounded and interpolates it with additions, multiplications and FMAs only. Drag co-rotates, and the uniform rotation stays as a mode.
- **B3:** CelesTrak's CSV, decoded by Orekit's SGP4 into GCRF.
- **B4:** a native64 Gauss-Newton fit of state and bc to SGP4's positions, with its partials run as lanes.

**The gates** (all MEASURED; logs in `studies\debris-f\logs\`):
- **F1 PASS:** over 10,000 lanes, interpolation and frame application are bit for bit, native against cft, at binary64 and binary32. Control: the reordered build broke M00 alone, and the gate named it.
- **F2 PASS:** over 1,000 epochs:
  - TAI − UTC and TT − TAI are exact;
  - TDB − TT is within 25.35 µs (tolerance 50);
  - UT1 − UTC is within 5.6e-17 s.
  - Control: the cut leap table failed.
- **F3 PASS:**
  - (a) within 0.012 µas of Orekit at 161 file dates (50 µas);
  - (b) the table at native64, within 15.8 µas (1 mas);
  - (c) the table against the routine, within 1.6e-14 rad.
  - Control: the dX plant failed at 1.0000 mas.
- **F4 PASS:** over 1,000 states, gravity at degree 20 is within 1.06e-14 m/s² (3.1e-12), and drag within 2.3e-10 relative (1e-7). Controls: the bc and pole-tilt plants failed.
- **F5 PASS:**
  - 2,696 rows, every getter equal;
  - the mean-motion plant moved SGP4 42.686 m, against 42.704 computed;
  - a synthetic truth was recovered to 4e-7 m;
  - 94 of 100 real fits converged, with a post-fit RMS median of 519 m.
- **F7 PASS:** 10 objects over 6 h. cft128 is within 3.1e-25 m of cft256, against B = 3.77e-18 m (an ESTIMATE-based bound). native64 and cft64 are within 7.3e-7 m. Control: round64 reached 1.6e8 B.
- **F8 PASS:** the real frame is bit for bit across two runs, `-O0` against `-O2`, and restarts ending on a short step. The uniform mode reproduces DEBRIS-E's E2 and E4 byte for byte. Control: a one-ulp plant moved lane 3 alone.
- **F9, measured under load:** no sensitive window could be booked, so these are upper bounds. A lane's force evaluation at 1 / 64 lanes:
  - native64 5.78 / 2.13 µs;
  - cft64 3.23 / 2.42 ms;
  - cft128 4.85 / 4.02 ms;
  - cft256 10.4 / 9.30 ms.
  - The clean re-run is yours.
- **F6, a measurement; its controls PASS:** T1 the time tag, T2 the 1,647 equal sets (each exactly 0), and T3 the swapped identities.

**F6** (200 of 704 pairs; horizons 1.5 to 70.6 h; perigees 273 to 857 km; the miss at e1 against SGP4 from S1):

| method | median | 90th |
|---|---|---|
| (A) M1 fitted to S0 | 1.122 km | 2.825 km |
| (B) SGP4 from S0 | 0.075 km | 0.357 km |
| (C) Orekit fitted, NRLMSISE-00 (50 pairs) | 1.156 km | 2.895 km |

- (A) misses less than (B) in 9 of 200, and less than (C) in 19 of 50. On those 50 pairs the medians are 1.17 and 1.16 km. The pairs cluster, so these are not independent trials.
- (B) shares the reference's theory, so the comparison favours it by construction (inferred).
- Both fits' drag parameters are poorly determined: (A)'s bc is negative in 98 of 200, and (C)'s Cd in 26 of 50.

**What failed, and what I did.** Every gate's negative control failed as it must. Along the way:
- F2's log 001 crashed in my leap-second parser. I fixed it and re-ran as log 002, with the criteria unchanged.
- B4's first thresholds (1e-9) never converged, because the fit reaches a noise floor. I set new ones from a development fit of the ISS, before F5's data, and disclosed it.
- F7's dry run showed 0 differences between kinds, because it compared binary64 roundings. `read_prop` now decodes each kind's own encoding.
- Orekit 13.1.9 cannot read CelesTrak's `SW-Last5Years.txt` as served: there are three incompatibilities. I stopped and asked.
  - Under your rulings, (C) reads a copy normalised in three ways, and its two-fill check passed.
  - Your separate copy is byte-identical (`47acbcc2…`), an independent agreement.
  - Nothing goes upstream without Logan's word.
- F8's version 1 imported a DEBRIS-E module whose `makedirs` pointed at DEBRIS-E's existing scratch folder. Nothing was written, and the folder's modification time is unchanged. I reported it. Version 2 copies the functions instead and has not run.
- I made two ledger slips; each is corrected in the ledger.

**Budget.** About 56.4 of 95 CPU-minutes: 47.38 in `cpu.tsv`, 6.49 in dry runs, 0.51 for (C)'s probe, and about 2 uncharged (ESTIMATE). Wall time ran from 06:36 to 09:54.
- **F7 used 16.42 CPU-minutes against its 15, and I did not message you before it ran over, as the brief requires.** You accepted it after the fact (`lead.md` 09:47, corrected 09:50). The line closes at 16.42, the 95 stay binding, and no further F7 run goes without a message.
- **Per arc, against the plan's 1-lane prices** (COMPUTED):
  - cft64: 27.0 s against 24.25 (1.11);
  - cft128: 41.7 s against 35.25 (1.18);
  - cft256: 85.2 s against 85.0 (1.00).
- **What makes up the 16.42:**
  - the plan's upper end, 14.17;
  - the round64 control, 0.63. The plan's price left it out, though the brief requires a control for every gate; that omission is yours, in the plan;
  - cft64's and cft128's excess, 1.53;
  - cft256's excess, 0.01;
  - native64 and the start run, 0.08;
  - less the 0.83 margin, which leaves 1.42 over the line.
- **The cause is not isolated:**
  - F7's arcs ran 1.34, 1.38 and 1.27 times F9's 1-lane figures, and F9's cycles are 0.99 of its wall times.
  - F9's real-frame object-day times are 0.79 to 0.86 of E9's, so the real frame is not the cause.
  - Two candidates, both BELIEVED and untested: the four concurrent runs sharing cores, and the other bookings' load.

**Not settled:**
- Orekit's pole interpolation, which differs from 4-point Lagrange by up to 16 µas.
- The noise floor's cause (BELIEVED: the density table's steps and the shadow's edges).
- Why M1's post-fit RMS (median 534 m) is higher than Orekit's (307 m).
- Whether the free drag parameter absorbs SGP4's theory (BELIEVED).
- F7's excess.

**Not done:**
- F9 in a quiet window.
- F3, F5 and F8 re-run on build 4. `src\` is unchanged across the builds, and F1, F2 and F4 re-ran with identical results.
- F8's version 2.
- A second SGP4 decoder.
- Our own NRLMSISE-00, certificates, the 24/7 loop, and any GPU work.

**What the brief got wrong** (§10 of the build report):
1. Orekit's TDB is "about 1 µs" from eq. 2.6: it is up to 25.35 µs away.
2. Orekit "accepts" `SW-Last5Years.txt`: its loader refuses the content.
3. F4's "5 to 8 frames" of a week: the window needed 34 days.
4. "About 10 transcendentals" per fine node: none are needed.
5. B4's stop rule ignores the noise floor.
6. F7's batching from a common epoch: no two objects share one.
7. F4's tilt control at about 10 times the tolerance: it came out at 30 times.
8. F7's price left out its negative control: your omission, in the plan.
