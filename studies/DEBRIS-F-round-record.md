# Round DEBRIS-F: the record

The lead's record of round DEBRIS-F in cft-debris, 2026-11-16.
- **The plan of record** is `DEBRIS-F-plan.md`, draft 3 (SHA-256 `3dd4064ddcd779dbf4a3564f1e984bf96d70edf746eb43764f372fdde2f9b9af`).
  - Logan approved it in chat with "Approve and start", which approved all eleven decisions at their defaults and the listed downloads by name.
  - plan-verifier-F (Sonnet) checked draft 1 and re-checked draft 2. Both of draft 1's blockers were confirmed and answered: the series' cost at cft256, and F7's arcs. Draft 3 had only the lead's checker, `check_plan_f.py`.
- **Logan set the round's direction** on Monday morning. He asked "whats the plan for today?"; the lead recommended M1 on real data, on the CPU, before any GPU port; and Logan answered "Yes, draft it".
- **The ledger** is `C:\Users\logan\source\repos\cft-debris-ledger\`: `lead.md`, `DEBRIS-F.md` and `verifier-F.md`. It is outside this repository.

## What ran

| agent | model | job | wall time | output |
|---|---|---|---|---|
| plan-verifier-F | Sonnet | checked draft 1; re-checked draft 2 | 06:07 to 06:28 -0700 | its two reports, filed verbatim in the ledger's `filed\` |
| DEBRIS-F | Opus | built B1 to B4; ran F1 to F9 | 06:35 to 09:54; the harness gives 12,093 s and 367 tool calls; about 56.4 CPU-minutes by its count | `src\`, `tests\`, `DEBRIS-F-build.md`, `debris-f\` and `DEBRIS-F-report.md`; three per-object tables in the ledger's `debris-f\` |
| verifier-F | Sonnet | rebuilt from clean, and re-ran samples of every gate | 10:08 to 10:23; the harness gives 890 s and 78 tool calls; about 12 CPU-minutes by its count | `DEBRIS-F-verifier-F-report.md` |
| merge-check-F | Haiku | checked the lead's narrowing | 10:31 to 10:36; the harness gives 276 s and 13 tool calls | its report, filed verbatim in the ledger's `filed\` |
| merge-check-F2 | Haiku | checked the lead's last narrowing and addition | 14:49 to 14:55; the harness gives 350 s and 28 tool calls | its report, filed verbatim in the ledger's `filed\` |
| the lead | Opus | Phase 0, the snapshots, the rulings, filing, the merge, F9's quiet re-run on amd-arc-box, the commit | throughout | `lead.md`, the ledger's tools for this round, and `tests\f9_box.py` with its shim |

## Phase 0, before dispatch

- **The downloads,** rows 1 to 10 of decision 6, came through `fetch_f.py static` between 13:31:09 and 13:31:16 UTC, one request each, every one HTTP 200.
  - Their SHA-256 are in `lead.md` at 06:34. `finals2000A.daily` matches USNO's `checksums.sha512`.
  - The IERS's three tables are byte for byte the copies inside Orekit's jar.
- **S0** was taken from 13:31:48 to 13:31:50 UTC (06:31 -0700): 2,696 objects in four groups, all of ephemeris type 0, with set epochs from 2026-10-18 to 2026-11-16.
- **Orekit's Earth orientation:** Orekit takes blank dX and dY as zero and interpolates across the gap. So F3 and F4 were ruled to epochs at MJD 61430 or earlier.
- **Dispatch:** DEBRIS-F went out at 06:35 on Opus, under the notice B0051. Its prompt arrived identical to the filed copy, and its test escalation came back within a minute.

## What it built and found, after verification and narrowing

**What was built:**
- **B1, the time scales:** the time scales from the published tables onto M1's TDB grid, each object on its own exact origin and ending on one exact short step.
- **B2, the frame:** the IERS 2010 CIO-based frame, computed once per window at binary256 through libcft into a node table. Every number kind receives the table correctly rounded, and interpolates it with additions, multiplications and FMAs only.
- **B3, the data:** CelesTrak's CSV, decoded by Orekit's SGP4.
- **B4, the fit:** a native64 Gauss-Newton fit of state and drag parameter to SGP4's positions.

`DEBRIS-F-build.md` gives the details, with eleven narrowings and three additions at the merge, in thirty-eight marked places.

**The gates** (MEASURED; re-run in samples by verifier-F):
- **F1:** native against cft, bit for bit, at binary64 and binary32.
- **F2:** the time scales against Orekit. TDB − TT is within 25.35 µs of Orekit's shorter series.
- **F3:** the frame against Orekit, within 0.012 µas at the file's dates, and 15.8 µas through the table.
- **F4:** the forces in the real frame against Orekit.
- **F5:** the decoder and the fit.
- **F7:** the precision ladder. cft128 is within 3.1e-25 m of cft256 over 6 hours, on the 3 objects run at cft256. Its 10 objects are 6 distinct orbits.
- **F8:** reproducibility, and the uniform mode's regression against DEBRIS-E, byte for byte.

Every one of these passes. Every negative control failed as it must.

**The first hindcast, F6** (a measurement, with its controls passing). 200 of the 704 pairs, which are 196 distinct orbits, at horizons from 1.5 to 70.6 hours. The median miss at the later set's epoch, against SGP4 from that set:

| method | over the 200 pairs | over the 196 distinct orbits |
|---|---|---|
| (A) M1 fitted to the earlier set | 1.122 km (1.196 km without its 22 fits stopped on the iteration limit) | 1.143 km |
| (B) SGP4 from the earlier set | 0.075 km | 0.075 km |
| (C) Orekit fitted, with NRLMSISE-00 (50 pairs) | 1.156 km | 1.156 km: its 50 pairs are 50 orbits |

- (B) shares the reference's theory, so the comparison favours it by construction (inferred).
- (A) and (C) miss alike in the median, on their 50 common pairs.
- Both fits' drag parameters are poorly determined, and many come out negative. A free drag parameter fitted to one day of SGP4 positions is not a physical drag coefficient here.

**F9, cost:**
- DEBRIS-F's run was under load, single runs, as upper bounds.
- **The lead's quiet re-run** on amd-arc-box ran from 14:30:27 to 14:32:00, inside the box's `sensitive` booking B0083. The box's load was 0.0 to 0.2%.
- **Quiet, the box took 1.14 to 1.49 times the desktop's wall time under load** per lane-evaluation at 1 lane, and 1.23 to 1.37 times at 64 lanes. A lane-evaluation took 7.11 µs at native64 against the desktop's 5.78, and 13.0 ms at cft256 against 10.4. The desktop's walls under load are upper bounds on its CPU time, so per thread the box is at least that much slower.
- **So these are the box's own figures,** not the desktop's clean cost, which is still unmeasured. The machine, the compiler and the C library all differ, and which of them makes the difference is not determined.

**Findings beyond the gates:**
1. **Orekit 13.1.9 cannot read CelesTrak's current `SW-Last5Years.txt` as served,** in three ways:
   - the blank flux qualifier on the daily predictions;
   - the blank fields of the monthly predictions;
   - the monthly section's marker, which Orekit's loader does not know.

   Comparator (C) read a copy normalised in three asserted, mechanical ways, under the lead's rulings. A two-fill check showed that the placeholders do not reach the model's inputs at (C)'s dates. The lead's own copy, made separately, is byte-identical to DEBRIS-F's.
2. **CelesTrak served the same element sets with different digits three hours apart** (the lead's, MEASURED):
   - 151 epochs moved by 864 µs, one unit in a TLE epoch's last place;
   - in 318 sets, BSTAR and the eccentricity carried more digits at S0 than a TLE holds.

   The cause is BELIEVED: S1's copies passed through a TLE's fields. Neither F6's pairs nor its controls are affected.
3. **Orekit's EOP loader takes Bulletin B where a row has it,** else Bulletin A. Its pole interpolation between rows differs from 4-point Lagrange by up to about 16 µas.
4. **The fit reaches an iteration noise floor.** Its stopping thresholds sit above that floor, and were set after one sample object, the ISS. This is disclosed.
5. **The samples count docked vehicles as separate orbits** (the lead's, found at the merge; narrowing 11). In S0, 13 objects of the `stations` group share 3 element sets:
   - the ISS's, with Poisk, Nauka and five docked vehicles;
   - Tianhe's, with China's two station modules;
   - Tianzhou-10's, with Shenzhou-23.

   So F5(d)'s 100 fits are 90 orbits, F6's 200 pairs are 196, and F7's 10 objects are 6. The ISS's set, on which the fit's thresholds were set, is 8 of F5(d)'s 100. No verdict turns on it, and the figures over distinct orbits move little, except the `stations` group's own: its median (A) miss goes from 0.82 to 1.25 km over its 4 orbits.

## Rulings and events

- **07:48, 08:07 and 08:12, the space weather for (C):**
  - a derived copy, normalised in three stages, through Orekit's own loader, after the lead's probe found the third cause;
  - a stop rule: no fourth stage, and on failure (C) is cut;
  - DEBRIS-F's own reader was not taken.
- **08:07, F9:** its `sensitive` window was refused, because the desktop was held `shared` by other sessions. So F9 ran under load, as upper bounds, and its clean re-run was ruled to come before the merge.
- **09:32 and 09:37, S1:**
  - S1 was taken three hours after S0, every request HTTP 200;
  - it gave 704 pairs, so there was no S2;
  - the lead's counts and DEBRIS-F's agree.
- **09:47, corrected at 09:50, F7's budget:**
  - F7's line ran over, 16.42 CPU-minutes against 15, with no message first. It was accepted after the fact, and the total stayed binding;
  - the lead's first ruling misread the plan's prices. DEBRIS-F caught it, and the ruling was corrected.
- **10:08:**
  - DEBRIS-F's report was filed verbatim;
  - the lead's factual scan of its outputs was clean: licences, data and secrets;
  - verifier-F was dispatched, with a brief that had it copy the scripts and repoint their hard-coded paths before any re-run.
- **10:29:** no send-back, and the build report was narrowed at the merge. The ISS's figures in one F5 log stay, as one control's evidence for one public object (decision 11).
- **10:40:** merge-check-F's points were fixed, and the commit waited for F9's window.
- **11:56, F9's machine:**
  - **Logan's word, in chat:** "You also have permission to run the tests on the 'amd-arc-box', which has many more cpu cores, its information should be in TimeSheet".
  - **Why the box:** the desktop's `shared` bookings ran to 18:41. So F9's re-run went to the box, run by the lead, in its own `sensitive` booking B0083 from 14:30.
  - **The harness:** F9's driver could not run there unchanged, so the lead wrote a Linux harness that keeps every M1 source byte-identical. It built on the box at 12:00, and its smoke runs passed.
- **12:28 to 12:38, the box and the TimeSheet, on Logan's word:**
  - the throughput run waits for the next round;
  - the box's CPUs and its Intel Arc A750 are open to cft-debris, and the U50 is withheld;
  - the lead added the card to the TimeSheet as `arc-a750`, with a notes file of three suggestions;
  - TimeSheet's local commit `1acd777`, amended to name the session as Logan asked, holds it. TimeSheet has no remote.
- **14:30 to 14:32, F9 on the box:** the run took 14:30:27 to 14:32:00 under B0083, which the lead released at 14:32:37. Every row passed, at 0.0 to 0.2% load, so no re-run was needed.
- **14:43, the samples:** on the box, T3's fits came out bit-identical for different objects, because those objects share their element sets in S0. No figure is false and no verdict turns on it, so there was no send-back. It became narrowing 11 at the merge, with the figures over distinct orbits.
- **14:56 to 15:01, merge-check-F2's report:**
  - It confirmed narrowing 11's figures, recomputed with its own code, and the addition's table and conditions.
  - Its defect, ratios called "per thread", was upheld in part. Every ratio is of wall times, so the text now gives them as lower bounds per thread.
  - Its alternative, which rested on GetProcessTimes, was not taken: the harness documents that measure as under-reporting on this host.
  - DEBRIS-F's report line 92 was added to the list, and F7's shared e0q was measured.
  - The lead also removed three catalogue numbers and two perigees from §4's F7.
  - A script showed that the six edits are all that changed since the check.

## Failures, recorded as failures

- **F2's log 001** crashed in DEBRIS-F's leap-second parser before any comparison. The criteria were unchanged.
- **B4's first stopping thresholds** never converged, because the fit reaches a noise floor.
- **F7's dry run** showed no difference between number kinds, because it compared binary64 roundings. The decoding was fixed before the run of record.
- **Orekit's loader refused the space-weather file** twice before the third normalisation.
- **F8's version 1** imported a DEBRIS-E module that pointed at DEBRIS-E's scratch folder. Nothing was written there.
- **F7's line ran over** without the message the brief requires.
- **F4's tilt control** came out at 30 times its tolerance against an expected 10. It still failed as it must.
- **verifier-F's first F8 run stopped early,** because its copy lacked DEBRIS-E's logs. The brief had not said that F8 needs them.

## What the plan got wrong

- **The eight items of the build report's §10,** as narrowed at the merge. Among them:
  - Orekit's TDB differs from Circular 179's eq. (2.6) by up to 25 µs, not about 1 µs;
  - Orekit's loader refuses CelesTrak's space-weather file;
  - F4's window spans 34 days, not a week;
  - a fine node needs no transcendentals.
- **F7's price** left out its negative control.
- **F9:** the plan expected a `sensitive` window on the desktop within the round.
  - None opened there: the `shared` bookings listed at 11:56 ran to 18:41.
  - The re-run went to amd-arc-box on Logan's word, so the desktop's clean figures are still unmeasured.
  - F9's driver was written for Windows alone, so the box needed a harness of its own.
- **The sample rule** took every object of CelesTrak's `stations` group. Its docked vehicles carry their station's element set, so 13 of S0's objects share 3 sets, and every sample counted some orbits more than once. The plan should have drawn one object per element set.

## The lead's slips

1. **Drafting:** two of DEBRIS-C's costs were carried from memory notes. `check_plan_f.py` caught them.
2. **A `cd` into `studies\`** moved the session's working directory, three times: once while drafting, and twice into `studies\debris-f\`, after the box's build and after the box's run. Each time it was restored at once.
3. **`fetch_f.py`** lacked row 10 until just before Phase 0. This was caught before any request.
4. **The space-weather probe's copy script, version 1,** planted its control's change into the source. So the control could not fail. That version is kept, and version 2 fixed it.
5. **The F7 ruling at 09:47** read the plan's per-object-day prices as totals per kind. DEBRIS-F caught it, and the ruling was corrected at 09:50.
6. **The plan** priced F7 without its control.
7. **Times typed without `date`** went into `lead.md`:
   - **09:47:** a time in the entry, corrected at 09:48.
   - **12:37:** a heading's minute, which should read 12:36, corrected by the next entry.
   - **12:02 and 12:28:** two more headings, typed the same way as the expected append time. The session transcript's timestamps put those appends at 12:02:05 and 12:28:12, so they stand.
8. **verifier-F's brief** omitted F8's dependency on DEBRIS-E's logs, and named a table for figures it does not carry.
9. **At the merge,** there was an unmarked change, and a narrowing stated verifier-F's guess as fact. merge-check-F caught both. The lead's comparison of the two frame tables then showed the guess was wrong.
10. **A `grep` count of CR bytes** counted the letter r. Python's count was 0, and the error was caught before it reached a record.
11. **The F9 shim's first version** returned without setting the timer's value when the clock failed.
    - gcc warned of it in the box's first build, r1, before any measurement.
    - Now a failed clock aborts the program, and r2 was built from clean.
12. **The duplicate check's first version** kept the first object of each shared set, and so dropped (C)'s one pair on a shared set. One cell lost its only (C) pair, which showed the error before any figure reached a record. Now an orbit keeps (C)'s miss from any of its objects.
13. **The prompt check's first regex** found no path-and-hash pairs, because the Bash tool had turned a doubled backslash into one. So it checked nothing. Its count of zero showed this, and the second version found both pairs and ran its control.
14. **F9's addition called its ratios "per thread"** when they are ratios of wall times, and on the desktop's side those walls were taken under load. merge-check-F2 caught it. The lead's message to Logan while the check ran said "slower per thread" too, and the next message corrects it.
15. **Narrowing 11 first gave three catalogue numbers and two perigees** that it did not need. The lead removed them after merge-check-F2's check.

## Cost

Tokens processed per agent, from the harness's transcripts since round DEBRIS-E closed (2026-11-13 09:33 -0700), by `dispatch\cost.py` at 15:01 (MEASURED):

| agent | model | calls | tokens processed |
|---|---|---|---|
| the lead | Opus 5.5 | 492 | 165,995,929 |
| plan-verifier-F | Sonnet 5.5 | 20 | 2,117,875 |
| DEBRIS-F | Opus 5.5 | 301 | 194,335,171 |
| verifier-F | Sonnet 5.5 | 77 | 11,814,901 |
| merge-check-F | Haiku 5.5 | 10 | 1,035,106 |
| merge-check-F2 | Haiku 5.5 | 28 | 2,922,473 |
| total | | | 378,221,455 |

- **Cache reads** are 98.5% of the total (COMPUTED). DEBRIS-F is 51.4% of it and the lead 43.9%. F9's move to the box, its harness and narrowing 11 added to the lead's share. The lead's line ends at 15:01, before the commit.
- **The known-answer check:** each agent's last call's context, held against the harness's own `subagent_tokens`.
  - plan-verifier-F, merge-check-F and merge-check-F2 are exact.
  - DEBRIS-F is 1.94% short and verifier-F 0.21% short. The causes are not determined, as in rounds DEBRIS-D and DEBRIS-E.

## Where things are

- **This repository:**
  - `src\`: `m1_nodes.c`, `m1_nodes.h` and `m1_ftab.c` are new, and `m1.h`, `m1_kind.h` and `m1_physics.h` are extended;
  - `tests\`: `build_f.sh`, `m1f.c`, `m1nodes.c`, `f_lib.py`, `f_fit.py`, and the gate scripts F1 to F9; and the lead's `f9_box.py` with its shim, `f9_box_windows.h`;
  - `studies\`: `DEBRIS-F-plan.md`, `DEBRIS-F-build.md` (narrowed), `DEBRIS-F-report.md`, `DEBRIS-F-verifier-F-report.md`, this record, and `debris-f\`, which holds 61 files under its `MANIFEST.sha256`.
- **The ledger:**
  - `lead.md`, `DEBRIS-F.md` and `verifier-F.md`;
  - in `filed\`: plan-verifier-F's two reports, the build report as reported and as at the first merge, and merge-check-F's and merge-check-F2's reports;
  - in `debris-f\`: the three per-object tables;
  - in `tools\`: the lead's tools `swprobe-f\`, `gpcheck-f\`, `scan-f\`, `f9box\`, `dupcheck\` and `eop_probe_f.js`;
  - in `dispatch\`: the prompts and briefs, and `fetch_f.py` with its logs.
- **The downloads,** rows 1 to 10 and the snapshots S0 and S1, are in `cft-debris-downloads\`.
- **Each agent's scratch** is in `cft-debris-scratch\`, outside the repository. The lead's staging for the box is there too, in `lead-f9box\`.
- **On amd-arc-box,** in the home folder's `cft-debris-f9\`:
  - `r1`, the first build, unused;
  - `r2`, the build and the run of record, with every output.

## Open, for Logan

1. **The push** waits for Logan's word (decision 10).
2. **An upstream report** to Orekit's project about CelesTrak's space-weather file, on Logan's word only.
3. **CelesTrak serves the same GP sets with different digits** between requests. Whether to tell CelesTrak is Logan's call.
4. **The box's run folders,** `r1` and `r2`: keep them, or the lead removes them on Logan's word.
5. **F9 on the desktop itself,** in a quiet window, whenever one opens. The box's figures are another machine's.
6. **The next round.** Its samples should take one object per element set.
