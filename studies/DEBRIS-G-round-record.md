# Round DEBRIS-G: the record

The lead's record of round DEBRIS-G in cft-debris, 2026-11-17.
- **The plan of record** is `DEBRIS-G-plan.md`, draft 3 (SHA-256 `4d6831fe7d23874a124736957534455dda6f7acf7baa01105badcede3a7a8780`).
  - Logan approved it in chat with "Approve and start", at 06:28:49, which approved all twelve decisions at their defaults.
  - plan-verifier-G (Sonnet) checked draft 1 and re-checked draft 2.
    - Draft 1's three blockers were confirmed and answered: an eighth kind-mode, G2's control at the 32-bit kinds, and no validity criteria for G4 and G5.
    - The re-check's blocker was confirmed and answered: G5 inherited G4's CPU-share rule, so it could never pass.
    - Draft 3 had only the lead's checker, `check_plan_g.py`: 156 checks, 0 failed.
- **Logan set the round's direction** on 2026-11-16: the next round opens with a 36-thread throughput run on amd-arc-box, planned with its criteria first. On 2026-11-17 at 05:45 he answered "Yes, draft it".
- **The ledger** is `C:\Users\logan\source\repos\cft-debris-ledger\`: `lead.md`, `DEBRIS-G.md` and `verifier-G.md`. It is outside this repository.

## What ran

| agent | model | job | wall time | output |
|---|---|---|---|---|
| plan-verifier-G | Sonnet | checked draft 1; re-checked draft 2 | 06:08 to 06:26 -0700 | its two reports, filed verbatim in the ledger's `filed\` |
| DEBRIS-G | Sonnet | phase 1: the population, the batch driver, the harness, desktop tests and G3's desktop half; phase 2: the analysis of the box's logs, and the build report | phase 1, 06:31 to 06:57 (1,544 s and 60 tool calls); phase 2, 11:29 to 11:35 (393 s and 17 tool calls); about 21.8 of its 40 desktop CPU-minutes by its count | `tests\`, `DEBRIS-G-build.md`, `debris-g\` and `DEBRIS-G-report.md`; its hand-off, filed in the ledger; the population and desktop outputs in the ledger's `debris-g\` |
| verifier-G | Haiku | rebuilt from clean; re-ran G2; recomputed G4 and G5 from the logs; read the timing and clock code; re-derived the population | 11:42 to 12:16; a first pass of 74 s and 14 tool calls, then a resumed pass, 1,868 s and 57 tool calls in all; about 25 CPU-minutes by its count, against 20 | `DEBRIS-G-verifier-G-report.md`; its first, partial report, filed in the ledger |
| merge-check-G | Haiku | checked the lead's narrowing | 12:26 to 12:29; the harness gives 167 s and 19 tool calls | its report, filed verbatim in the ledger's `filed\` |
| the lead | Opus | the box survey, Phase 0, every box run, filing, the ruling, G3's desktop re-run, the merge, the commit | throughout | `lead.md`, and the ledger's tools for this round |

## Phase 0, before dispatch

- **The archive:** `tools\cft-fp256-0aa997a3.tar` hashed to its recorded SHA-256 at 06:29.
- **No downloads and no requests.** The population is S0's, from round DEBRIS-F.
- **`dispatch\open_round_g.py`:** at 06:29 it wrote the two ledger files, made `debris-g\`, and copied DEBRIS-F's frame table, read-only, held to `f9_time.001.log`'s SHA-256.
- **Dispatch:** DEBRIS-G went out at 06:31 on Sonnet, under the desktop notice B0103. Its prompt arrived identical to the filed copy, and its test escalation came back within a minute.

## What it built and found, after verification and narrowing

**What was built:**
- **P1, the population:** S0's 2,696 objects give 2,686 distinct element sets, one object per set (round DEBRIS-F's narrowing 11), with none below a 200 km perigee. They are placed at one epoch E, inside DEBRIS-F's frame table, with three rotated replicas: 10,744 lines. The file is in the ledger.
- **P2, the batch driver** `tests\m1g.c`: M1's `src\`, unchanged since DEBRIS-F, run in batches of lanes, step by step, with a start barrier and its own timing and CPU reports.
- **P3, the harness** `tests\g_harness.py`, with `tests\g_calib.c` and `tests\g_stage.py`: it builds, runs the gates, pins one process to each CPU, and measures foreign load and the kernel's clock. It ran on the box without a fix.

`DEBRIS-G-build.md` gives the details, with two narrowings and four additions at the merge, each marked.

**The gates** (MEASURED; the box's runs are the lead's):
- **G1, the build:** B1 to B6 pass on both machines, and the controls C1 to C5 each failed as specified. At 36 workers the clock loop and the kernel's reading differ by 7.33%, so every clock in the round is the kernel's reading only.
- **G2, partitions:** at all eight kind-modes, five partitions of 64 objects over 40 steps gave bit-identical final states. verifier-G re-ran seven of the eight on the desktop, with a partition of its own.
- **G3, machines:** at all eight kind-modes, 16 objects over 240 steps came out bit-identical on the desktop and the box, the C library's native kinds included, for this sample. The lead's own re-run of the desktop half confirmed it.
- **G4, throughput:** 59 runs, all valid, with at most 0.084% foreign load. Real-time capacity is X at 36 workers and 64 lanes, the median of three: an extrapolation of the cost per object beyond the 2,304 objects the runs carried.

| kind-mode | capacity, objects at real time |
|---|---|
| native32 | 18,526,551 |
| native64 | 18,259,424 |
| native64-cr | 57,040 |
| cft32 | 19,828 |
| cft64 | 15,322 |
| cft128 | 9,564 |
| cft256 | 4,332 |

- **G5, real time:** cft256, chosen by decision 4's rule, ran all 2,686 base objects on 36 workers at real time for 20 minutes. Every step of every worker finished at least 5.584 s before its deadline. The workers were busy 61% of the time on average, so the headroom is about 1.6 times.

Every gate passes. Every negative control failed as it must.

**Findings beyond the gates:**
1. **From 1 to 18 workers,** efficiency falls to 0.76 to 0.78, and the kernel's clock falls in the same ratio. The loss is the clock (INFERRED, on the kernel's reading).
2. **Hyperthreads add almost nothing:** 36 workers against 18 give 0.94 to 1.04, and 1.106 for native64-cr. For cft32 and cft64, 18 workers beat 36.
3. **Against DEBRIS-F's one-thread figures,** the cft kinds and native64-cr reached 0.917 to 0.951 of F9's rates, and the plain native kinds 1.002 to 1.015. On one desktop test, the population's states cost 9 to 15% more per step than the eight hand-set states F9 used, for native64-cr and cft256. That this causes the gap is BELIEVED for those two kinds, and open for the rest (narrowed at the merge).
4. **G5's mean clock,** 2,455 MHz, includes the samples taken while paced workers slept. It is not the clock under load.

## Rulings and events

- **06:08 to 06:26, the plan:** plan-verifier-G's report and re-check, and drafts 2 and 3.
- **06:28:49:** Logan's "Approve and start".
- **06:32, DEBRIS-G's first ledger heading** was typed (06:33 against the file's 06:32:08). The lead told it, and it appended a correction.
- **06:57 to 06:59:** the hand-off was filed. The lead read the harness and the staging script before running anything, and staged and copied the run folder to the box.
- **07:45 to 08:00, the box, under the notice B0104:** G1, G3's box half and G2. At 07:45 another session's process held one CPU, so G3, not a timing, ran before the calibration and the controls. Those ran at 07:50, once the box was quiet.
- **08:00:** cft-fp256 booked the box `shared` until 10:00. The lead booked B0107, `sensitive`, from 10:00 to 11:55, inside decision 5's 2 hours.
- **09:43:** cft-fp256's lead reported that DEBRIS-D's requests 1 and 2, GPU index tables and a deeper scratch, are on its main. Filed in the ledger's `relayed\`; nothing in this round changed.
- **10:00 to 11:26, the box under B0107:** G4 in three groups, then G5. Nothing else touched the box. B0107 was released at 11:26, after 86 minutes.
- **11:27:** all 1,953 files came back, each with the SHA-256 the box gave: 13 logs to `studies\debris-g\box\`, and the per-object outputs to the ledger.
- **11:29:** DEBRIS-G was resumed for phase 2, with two questions: the F9 gap, and G5's mean clock.
- **11:43:** its report was filed; the lead's scan of its outputs was clean; verifier-G was dispatched.
- **11:45:** verifier-G's first pass ended after 74 seconds, with most of its list undone. It was filed, and verifier-G was resumed to finish.
- **11:59:** verifier-G briefly ran five workers at once on the desktop. It was reminded that 4 is a total, and it restarted as one run.
- **12:25, the ruling:** no send-back.
  - §4's F9 criterion was prose that the script never evaluated, with no record from before the data. §4 answers the lead's question and is not a gate, so it was narrowed.
  - G3's desktop half was left undetermined by verifier-G, so the lead re-ran it from clean, in two groups of four kind-modes, and compared it with a script of its own: every object equal to the box's.
- **12:30, merge-check-G:** it confirmed the diff, the markers and the figures, and found two defects in the lead's wording, "within 1.1%" and the end checks in the timed region. Both were fixed after the lead read the code, and a script showed the five edits are all that changed since its check.

## Failures, recorded as failures

- **verifier-G's first pass** stopped after 74 seconds, citing a booking it already had.
- **verifier-G ran over its budget,** about 25 CPU-minutes against 20, without the message its brief requires. Its two stopped runs are not counted. It re-ran G2 at full size, 64 objects and 40 steps, where its brief asked for a few objects and steps, and that run took 1,473 CPU-seconds.
- **verifier-G ran five workers at once** on the shared desktop, briefly, against a limit of 4.
- **DEBRIS-G ran up to 48 workers on the desktop** in phase 1, before the lead's limit of 4 reached it, and one sweep test cost 10 CPU-minutes without a message first.
- **DEBRIS-G's earliest script versions** were overwritten before it kept them. Their logs are in `logs\earlier\`, marked as functional tests only, and `g_analyze.001.log` is superseded.
- **The F9 test's criterion** was never evaluated by its script, and nothing shows it was fixed before the data.

## What the plan got wrong

- **Efficiency at 36 workers,** as the plan defines it, mixes the hyperthreads with the clock.
- **The capacity rule,** at 36 workers, gives a capacity below the 18-worker rate for cft32, cft64 and cft128. The plan reports the faster configuration only beside it.
- **G2's time:** the plan estimated about 18 minutes run serially. Run together, its partitions took about 7.
- **The plan's Haiku verifier** stopped early once and ran over its budget, and G3 was left to the lead.

## The lead's slips

1. **The survey's first package query** went through three layers of quoting and printed "none". The zero count exposed it.
2. **Draft 1** called the box's sibling pairing MEASURED from six CPUs. The second survey measured all 36.
3. **The 06:24 entry** called the filed file's hash the report's "body SHA-256". Corrected at 06:25.
4. **The first booking command** for B0107 used `+1h55m`, which the TimeSheet refused. Nothing was booked by it.
5. **The 11:27 entry** gave an estimated end time for the copy-back, and claimed more about a background process on the box than was seen. Both were corrected at 11:28.
6. **A `cd`** moved the session's working directory into `studies\debris-g\`, twice. Each time it was restored.
7. **The build report was edited before its as-reported copy was kept.** The copy was rebuilt from DEBRIS-G's transcript, and it has the SHA-256 the 11:43 entry recorded.
8. **verifier-G's brief,** finished by the lead, did not say that G3's mode starts all eight kind-modes at once, above the desktop's limit of 4. The lead's own re-run split it in two.
9. **merge-check-G's first prompt** named the wrong booking, read from a note line of the TimeSheet's output. It was removed, after a check of its hash, before dispatch, and written again.
10. **Two wordings at the merge** said too much: "within 1.1%" for a gap of 1.14%, and "the end checks inside the timed region", where the last pass's are not. merge-check-G caught both, and the 12:25 entry is corrected.

## Cost

Tokens processed per agent, from the harness's transcripts since round DEBRIS-F closed (2026-11-16 17:31 -0700), by `dispatch\cost.py` at 12:30 (MEASURED):

| agent | model | calls | tokens processed |
|---|---|---|---|
| the lead | Opus 5.5 | 1,493 | 620,846,270 |
| plan-verifier-G | Sonnet 5.5 | 40 | 6,012,193 |
| DEBRIS-G | Sonnet 5.5 | 74 | 16,601,852 |
| verifier-G | Haiku 5.5 | 77 | 11,728,279 |
| merge-check-G | Haiku 5.5 | 16 | 1,504,961 |
| total | | | 656,693,555 |

- **Cache reads** are 98.3% of the total (COMPUTED). The lead is 94.5% of it: it ran every box run, the G3 re-run and the merge itself, in one long session. The lead's line ends at 12:30, before the commit.
- **The known-answer check:** each agent's last call's context equals the harness's own `subagent_tokens`, exactly, for all four agents.

## Where things are

- **This repository:**
  - `tests\`: `g_pop.py`, `m1g.c`, `g_calib.c`, `g_harness.py`, `g_stage.py`, `g_analyze.py` and `g_f9data.py`;
  - `studies\`: `DEBRIS-G-plan.md`, `DEBRIS-G-build.md` (narrowed), `DEBRIS-G-report.md`, `DEBRIS-G-verifier-G-report.md`, this record, and `debris-g\`, which holds 43 files under its `MANIFEST.sha256`, the box's 13 logs among them.
- **The ledger:**
  - `lead.md`, `DEBRIS-G.md` and `verifier-G.md`;
  - in `filed\`: plan-verifier-G's two reports, DEBRIS-G's hand-off and report, verifier-G's first pass and report, the build report as reported, and merge-check-G's report;
  - in `debris-g\`: the population; DEBRIS-G's desktop G3 outputs; the box's whole `out\` folder (1,940 files); and the lead's desktop G3 re-run;
  - in `tools\`: the lead's `survey-g\`, `frame-f\`, `scan-g\` and `g3-lead\`;
  - in `dispatch\`: the prompts, the briefs and their makers, and `check_plan_g.py`;
  - in `relayed\`: cft-fp256's two messages of 09:41.
- **Each agent's scratch** is in `cft-debris-scratch\`, outside the repository. The lead's staging and console copies for the box are in `lead-g-box\`, and its G3 re-run in `lead-g-desk\`.
- **On amd-arc-box,** in the home folder's `cft-debris-g\r1\`: the staged inputs, the libcft and M1 builds, the logs and every output.

## Open, for Logan

1. **The push** waits for Logan's word.
2. **The 24/7 run.** On the box's CPUs, today's catalogue runs at cft256 in real time with about 1.6 times headroom, and 18 workers do as well as 36. The next round could start that long run, with its self-checks against each CelesTrak update.
3. **The Arc A750** has no compute runtime. Installing Intel's OpenCL runtime is Logan's to do (decision 7).
4. **The F9 gap's cause** is BELIEVED for two kinds and open for the rest. A box run could settle it.
5. **The box's run folders:** `cft-debris-f9\r1` and `r2`, and `cft-debris-g\r1`. Keep them, or the lead removes them on Logan's word.
6. **Carried from round DEBRIS-F:** an upstream report to Orekit's project about CelesTrak's space-weather file; whether to tell CelesTrak that it serves the same sets with different digits; and F9 on the desktop itself, in a quiet window.
7. **cft-fp256:** GPU index tables and depths to 2,048 are on its main. The 512-constant bank does not cover a degree-20 field, which cft-fp256 plans as its own item.
