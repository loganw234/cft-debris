# DEBRIS-K: thorough forecasts for a small set of objects, decaying LEO objects first, refined by the predictions over time: a study (plan of record, draft 3)

Drafted 2026-11-23 by cft-debris's lead, on Logan's word to dispatch a study.
- This is a **study, run beside DEBRIS-I.** It reads what the ledger and the downloads already hold. It runs a small hindcast on the desktop, and lays out what a forecast service for a few objects would take, what it would cost, and what data it would need.
- It builds no part of M1's library and no cft program, runs nothing on the box, a GPU or WSL, and requests and downloads nothing.
- **Logan's word to dispatch is its approval.** Every decision below stands at its default unless he changes it. As the method has every plan, it goes past the lead's checker and a plan-verifier before dispatch.
- **Draft 1** passed the lead's checker (`dispatch\check_plan_k.py`, log 002: 92 checks, 0 failed).
- **plan-verifier-K** (Sonnet) then found two blockers, eleven defects and notes. Its report is filed verbatim in the ledger's `filed\`. The lead checked each finding's evidence before answering it. Draft 2 answers every finding in "What changed from draft 1".
- **plan-verifier-K's scoped re-check of draft 2** found no blocker, three defects and notes. Its report is filed too. Draft 3 answers them in "What changed from draft 2".
- Draft 3 has had the lead's check only (`lead.md` names its log). Nothing has been dispatched, downloaded or requested.

## The question, in Logan's words

- **This study** (2026-11-23 07:51:20): "While the others work, dispatch a study in the feasibility of this being utilized to track a small subset of objects to provide more thorough and comprehensive forecast predictions, the first set could be LEO objects which are likely to decay within the prediction windows, we could utilize the various predictions to refine the models accuracy over time depending on the findings."
- **The goal** (2026-11-12): "a simulation capable of realtime (or slightly faster) simulation on a consumer card, so a 24x7 sim could run on a local box here for long run tests, validating itself with the open datasets update intervals, scaling tracked objects as the main scaling parameter presumably. High performance cards like the MI300X could then be used for higher density or faster/concurrent runs".
- **Carried from earlier rounds:**
  - the precision (2026-11-12): "Id also prefer to continue to utilize the higher precisions, simply to be a usecase for cft-fp256 as well";
  - the route through cft programs (2026-11-12): "*Yes if possible utilize cft programs, as well as generating certificates when able";
  - the kinds (2026-11-13): "utilize native and cft for binary64 (and 32 if needed) so the library utilizes the entire precision range offered by cft, and the results can be compared for correctness".

## What DEBRIS-K is for

DEBRIS-H ran M1 as a service for 72 hours: 2,688 objects at one fidelity, each checked against every new element set CelesTrak published. For an object about to re-enter, that service is at its weakest in three places:
- **its atmosphere** is static: 28 exponential bands, with no space weather;
- **its drag parameter** is fitted once, over one day of SGP4 positions before the seed set. DEBRIS-F found such a parameter "is not a physical drag coefficient here";
- **it never refits.** The seed stands for the whole run, however many new sets arrive.

Two records are consistent with that, though no run isolates the cause (INFERRED):
- **Over all of DEBRIS-H's 6,469 checks** (2,076 objects, flagged fits in), SGP4 from the seed's own set missed far less than the service's forecast from it. The medians were 0.306 km against 4.888 km, and the service missed less in only 334 checks, 5.2% (MEASURED there).
- **One decay:** M1 decayed seed index 1595 at 04:37 UTC on 2026-11-19, from a set 23.8 hours before the run's start. CelesTrak's SATCAT gives its decay date as 2026-11-18, so M1 was 4.6 to 28.6 hours late (E0003, E0005). That is one object.

A small set changes the arithmetic. With tens of objects, not thousands, each can have far more:
- a refit on every new set;
- a fit over its whole history of sets;
- a space-weather atmosphere (DEBRIS-F's route (C));
- an ensemble that gives a re-entry window with stated odds;
- smaller steps near the end.

And the stream of new sets is a stream of tests, which a model can learn from, as Logan asks. This study asks what that would take, what it would cost and what the data allow. It also measures a first answer on data already in the ledger.

| part | what it settles | the evidence it rests on |
|---|---|---|
| **K1. The candidates** | a rule for "LEO objects likely to decay within the prediction windows", from element sets alone | the rule applied to the ledger's sets; counts |
| **K2. The forecast's menu** | what "more thorough and comprehensive" can mean for M1, each item priced and rated | READ, COMPUTED, and K3's measurements |
| **K3. The pilot hindcast** | refits, history fits and the space-weather atmosphere against SGP4 from the same sets, beside the service's own forecasts, on the ledger's low-perigee objects | MEASURED, statistics fixed in this plan |
| **K4. The refinement loop** | what is learned from each new set and each decay, and how it is validated without fooling itself | a design, with its statistics |
| **K5. The data and its terms** | which sources give decays, re-entry predictions and space weather, and what each needs from Logan | READ, HTML pages only |
| **K6. The compute** | each variant's cost a forecast, and what a small set with ensembles needs | COMPUTED from G4 and DEBRIS-I's plan |
| **K7. The first build, laid out** | milestones, gates, data requests and costs, or a finding that it is not feasible | the above |

## What DEBRIS-K starts from (labels as in DEBRIS-C)

### M1 and its fits (READ)

- **`src\`** is unchanged since commit 1646c96. Its forces: degree-20 gravity, the Sun and the Moon from DE421, a static 28-band exponential atmosphere with drag co-rotating, and radiation pressure with a conical shadow. It integrates with rk4 at a fixed step.
- **The fit,** `tests\f_fit.py` with `tests\m1f.c fit`: 721 pseudo-observations from SGP4, every 120 s over the day before a set's epoch. It estimates the state and `bc`, with `bc` held at 0.01 m²/kg where perigee is 1,000 km or higher, and `cram` fixed at 0.01 m²/kg (READ, its header).
  - `m1f.c`'s fit takes its pseudo-observations on that one grid, `t0 + 120 k`, and weighs them equally (READ, its `Obj` and `lsq`).
  - `tests\f_lib.py` hard-codes DEBRIS-F's scratch for its build and data (READ, its line 22). DEBRIS-H's `tests\h_seed.py fit` takes every path from its arguments, and reads the downloads' `gp-<group>-<tag>` layout, not the ledger's slot folders (READ, its usage line).
  - M1's decay rule, the first state below 6,498,137.0 m from the centre, is in `tests\m1h.c` (`RMIN`, its line 64), not in `m1f.c`.
- **The fitted drag parameter is poorly determined.** Over F6's 200 fits, of objects with perigees from 273 to 857 km, it ran from −0.73 to 1.32 m²/kg, negative in 98 (DEBRIS-F's figures, carried in DEBRIS-H's plan). Below 400 km it is untested; seed index 1178's fitted `bc` is positive and inside that range (narrowed at the merge: its value is held in the ledger's `debris-k\held\`).
- **DEBRIS-F's route (C):** Orekit 13.1.9 fitted on its own to the same pseudo-observations, with NRLMSISE00 drag (`tests\f6_orekit_fit.js`). Its space weather is CelesTrak's `SW-Last5Years.txt`, through a normalised copy (`tests\f6_swcopy.py`).
  - In F6, (A), M1, and (C) had medians of 1.17 and 1.16 km on their 50 common pairs. That the density model makes no difference is an inference, not an isolated cause (MEASURED there, `studies\DEBRIS-F-build.md` §5).

### DEBRIS-H's run (MEASURED there; its records in the ledger)

- **The run:** 72 hours from T_s, 2026-11-18 22:50:00 TDB, with 2,688 objects on tracks A256, A64 and A64f.
- **Its slots:** the four groups' sets every 3 hours, slots 1 to 20 (MEASURED today, `svc\fetch\slots.tsv` and the slot folders).
  - Slots 1 to 11, 13, 14 and 18 fetched all four groups.
  - Slots 12, 15, 16 and 19 each ended at a request without a response, and slot 20 at an HTTP 500. They hold 3, 1, 3, 1 and 1 of the four groups' files.
  - Slot 17 was not attempted. The fetcher stopped after slot 16, its second slot in a row without a response, resumed at slot 18 on Logan's word, and stopped for the rest of the run at slot 20 (READ, `lead.md`).
- **The fetched files** are in the ledger's `debris-h\box\r2\svc\fetch\slotNN\`, one CSV a group.
- **Each slot's check table,** `debris-h\box\r2\svc\checks\slotNN.tsv`, gives a row per check. Each row carries the seed's and the new set's epochs, the horizon, the perigee and `bc`, and the misses of (A256), (A64), (A64f) and (B), with their radial, along-track and cross-track parts (READ, `tests\h_check.py`'s columns).
  - **Every forecast in them starts from the seed's set,** and the horizon is the new set's epoch less the seed set's. (B) is SGP4 from the seed's set, not from the set before the new one.
  - Tables exist for slots 1 to 15, 18 and 19, and none for 16, 17 and 20.
- **H7's measurements** (READ, `studies\DEBRIS-H-round-record.md`), over all 6,469 checks of 2,076 objects, flagged fits in:
  - (A256): median 4.888 km, 90th percentile 21.277 km;
  - (B): 0.306 km and 2.250 km;
  - (A256) missed less than (B) in 334 checks (5.2%).
- **Departures:** seed index 1595 is absent from its group's fetched files from slot 7 on (READ, `studies\DEBRIS-H-build.md`).
- **The event history,** `events\events.tsv`, E0001 to E0008:
  - E0003 and E0005: M1 decayed seed index 1595, as above;
  - E0008: M1 decayed seed index 1178 at 14:40 UTC on 2026-11-21, from a set 13.7 days before T_s, with a fitted `bc` (narrowed at the merge: its value is held in the ledger's `debris-k\held\`). It has no SATCAT record.
- **The seed's low perigees** (COMPUTED by the lead's checker from `seed1.txt`'s states at T_s): 1 object under 250 km, 5 under 300, 8 under 350 and 17 under 400. Indices 1595 and 1178 are among them.

### The downloads (READ, `lead.md`'s records of them)

- **`SW-Last5Years.txt`:** version 1.2, updated 2026-11-16 12:35:04 UTC. It holds 2,145 `OBSERVED` lines, the last for 2026-11-15, then 45 `DAILY_PREDICTED` lines (2026-11-16 to 2026-12-30) and 178 `MONTHLY_PREDICTED`. So DEBRIS-H's window has predicted space weather only.
- **DEBRIS-F's and DEBRIS-H's snapshots:** the `gp-*-S0`, `gp-*-S1` and `gp-*-SH0` folders.
- **Orekit 13.1.9 and Hipparchus 4.0.3,** as `tests\f_lib.py` lists them.

### Density and the loop, in earlier studies (READ)

- **DEBRIS-C** (`studies\DEBRIS-C-measurements.md`): NRLMSISE00 costs 7.3 to 7.5 µs a call and JB2008 29.9 to 31.6 µs, in Java at binary64. NRLMSISE00's nine densities matched a published run of the C code to 2.7e-16 relative. JB2008 had no reference check.
- **DEBRIS-D** (`studies\DEBRIS-D-architecture.md`, Q6 and Q7):
  - in a cft program, NRLMSISE-00 needs its `pow` rewritten, about 3e4 instructions a call (ESTIMATE), against 180 to 201 for the exponential atmosphere;
  - the 24/7 loop's statistic was designed there: a z-score with a TLE error covariance, and rules to flag, refit and refuse.

### Throughput (MEASURED in DEBRIS-G's G4, box workers, M1's full model)

- native64: 1,291,561 object-seconds a second on 1 worker;
- cft256: 299 on 1 worker, 4,332 on 36.
- DEBRIS-I's plan estimates its cft program at 10 to 30 times M1's cft256, at a smaller model (ESTIMATE there).

## The questions

**Q1. The candidates.**
- A rule that picks "LEO objects likely to decay within the prediction windows" from element sets alone: perigee and apogee, BSTAR, the mean motion's derivative, and the change of mean motion across an object's sets.
- The windows are 1, 3, 7 and 30 days.
- Apply it to the ledger's sets (S_H0 and DEBRIS-H's slots), and give the counts.
- Name the source that would give the whole catalogue's candidates, its terms, and what a request would cost under CelesTrak's usage policy (READ, `studies\DEBRIS-H-plan.md`'s record of it).

**Q2. "More thorough and comprehensive forecasts": the menu.**

Each item gets what it buys (with evidence, or as an ESTIMATE with its basis), what it costs a forecast, and what it needs:
- a refit on every new set;
- a fit over an object's history of sets;
- a space-weather atmosphere: NRLMSISE-00, or JB2008, through Orekit;
- an ensemble over `bc` and the density's scale, for a re-entry window with stated odds;
- the step size and the integrator near re-entry;
- the decay criterion: M1's 120 km, or another;
- the six kinds as a numerical ruler, from DEBRIS-H's measured divergence of A256 and A64;
- radiation pressure's share, for these objects.

**Q3. The pilot hindcast** (below). MEASURED.

**Q4. The refinement loop.**
- What is learned from each new set and each decay: each object's `bc`, and a density correction by height and space weather, or another parameter the study argues for.
- How it is validated without fooling itself: a holdout split by time, and another by object; statistics fixed before the data; the catalogue as the reference, never the truth.
- How much data it needs, and how many LEO decays a month there are (READ, with each source labelled).
- How DEBRIS-D's Q7 criteria apply, and what they would change.

**Q5. The data and its terms.**

For each source: what it holds, its cadence, its terms, and what it needs from Logan (a download, a request or an account):
- SATCAT decay records, from CelesTrak;
- a fresh space-weather file;
- Space-Track's decay and re-entry (TIP) messages;
- published re-entry predictions, such as The Aerospace Corporation's and ESA's pages.

Pages are read as HTML only, through WebFetch, and never CelesTrak's.

**Q6. The compute.**
- Each variant's cost a forecast for one object, from G4's box figures and the pilot's own operation counts. The desktop's timings are no measurement.
- What a set of 10, 100 and 1,000 objects needs at 1, 100 and 1,000 ensemble members, on the box's CPUs or on a card through DEBRIS-I's program (COMPUTED and ESTIMATE).

**Q7. The first build, laid out for Logan:** milestones, gates, data requests (each for his yes) and costs. Or a finding that it is not feasible, with its reason.

## The pilot hindcast (K3), fixed before the data

The lead read the seed's states to count these objects, the event history, and the check tables' headers. It read no miss of any of them before writing what follows.

- **The objects:** every object of DEBRIS-H's seed with perigee under 400 km at T_s, 17 by the lead's count.
  - The perigee comes from the seed's binary64 state at T_s: the semi-major axis and eccentricity of the osculating orbit, with GM = 3.986004415e14 m³/s² and R = 6,378,136.46 m.
  - Their indices and catalogue numbers go in the ledger's `debris-k\` only.
  - **Seed index 1595 is a reconstruction, not a forecast** (plan-verifier-K's D4). SATCAT dates its decay 2026-11-18, and it is absent from the fetched files from slot 7 on. Its decay most likely fell before T_s (BELIEVED, from the date), so every forecast time is after it.
    - **Its only output is a decay prediction,** from fits to sets with epochs before 2026-11-18 00:00 UTC, compared with SATCAT's date.
    - **No miss of it is computed.** Its later sets were published for an object that had most likely gone, and those before the decay are the very sets its fits are denied (the re-check's defect 2).
    - It is reported apart, and no forecast skill is claimed from it.
- **The sets:** each object's sets in S_H0 and in DEBRIS-H's slot folders 1 to 20, in epoch order, one a distinct epoch. A set whose epoch is no later than the object's previous set's is skipped and counted.
  - The count of new sets per object is reported first. For an object with none, (R) is its seed fit, and the study says so.
- **The forecast times:**
  - T_s, and the fetch times of slots 1, 5, 9 and 13, for (B'), (R) and (C);
  - slots 5, 9 and 13 for (H).
  - A forecast at a time uses only the sets fetched by then. Slot 18 is not a forecast time: after it only slots 19 and 20 fetched, one group each.
- **The horizon, for every variant,** is the reference set's epoch less the epoch of the latest set the forecast used (plan-verifier-K's B1). For (A) and (B) that set is the seed's, as DEBRIS-H recorded it. For (B'), (R), (H) and (C) it is the latest set at the forecast time.
- **The variants:**
  - **(A)** the service's own forecast, as DEBRIS-H recorded it: A64's misses, and A256's beside them, read from the check tables. Nothing is re-run;
  - **(B)** SGP4 from the seed's set, as DEBRIS-H recorded it;
  - **(B')** SGP4 from the latest set at the forecast time, to each reference. This is the like-for-like baseline for (R), (H) and (C), which start from the same set;
  - **(R)** M1 at native64, refitted from the latest set at each forecast time by DEBRIS-F's fit rule, as DEBRIS-H's `tests\h_seed.py fit` runs it. A copy, `tests\k_*.py`, reads the ledger's slot folders, with a note of what changed;
  - **(H)** M1 at native64, fitted at each forecast time to every set so far (plan-verifier-K's B2):
    - through `tests\k_fit.c`, a copy of `m1f.c`'s fit that takes its pseudo-observations from a file at any times. Its least squares are `m1f.c`'s, with equal weights;
    - **the rule:** over the span from one day before the oldest set's epoch to the last 120 s grid time at or before the latest set's epoch, each grid time takes its pseudo-observation from SGP4 of the earliest set whose epoch is at or after it. So each set speaks for the span since the set before it, and the oldest for the day before its own epoch. The fitted state is propagated from the span's origin, as in `m1f.c`;
  - **(C)** DEBRIS-F's route (C), with (R)'s fitting rule, if the budget allows (decision 3).
- **The reference:** each later set of the object, fetched through slot 20, at its own epoch, through SGP4, as F6 and DEBRIS-H's check took it.
- **The decay prediction** (plan-verifier-K's D1): for seed index 1178 and every object with perigee under 300 km, from each forecast time of (R) and (H), propagated up to 30 days.
  - It uses M1's rule in `tests\m1h.c`: the first step whose distance from the centre falls below 6,498,137.0 m. A copy, `tests\k_*.c`, carries the rule, with a note.
  - 1595's is set beside SATCAT's date.
  - The frame table runs to 2026-12-28 00:00 TDB, so it covers 30 days from every forecast time.
- **The statistics, fixed now:**
  - for each variant and each horizon cell (under 6 hours, 6 to 24 hours, 1 to 2 days, and 2 days and over), with n:
    - the miss's median and 90th percentile, the ceil(0.9n)-th smallest, as `tests\h_check.py` takes it;
    - the same for the along-track part's size, with its signed median beside;
    - a cell of fewer than 5 checks gives its count and median only;
  - **the main comparisons:** (R) against (B'), and (H) against (B'), cell by cell, since each pair starts from the same set. (A) against (B) restates DEBRIS-H's;
  - per object, the same over all horizons;
  - for (H), the learning curve: the median miss at horizons of 12 to 36 hours, by the number of sets in the fit (1, 2, 3 or 4, 5 to 8, and 9 or more);
  - the decay predictions above, each with its forecast time and the sets it used;
  - the share of checks in which (R), (H) and (C) each miss less than (B'). Checks cluster by object, so this is not a share of independent trials.
- **The controls, stated now and asserted in code:**
  - **T1 and T2 of F6, on every check** (`tests\f6_hindcast.py`);
  - **T3, on every check** except pairs of objects whose orbital planes lie within 0.1° of each other: the co-planar case DEBRIS-H met. The script states its plane test before the data, and lists each exception;
  - **(R)'s regression, on the same machine** (plan-verifier-K's D3):
    - (R)'s code is run on DEBRIS-H's test seed, which DEBRIS-H fitted on this desktop: `debris-h\testseed\`, 64 objects of S0, T_s 2026-11-17 00:00 TDB. So the (R) copy reads the downloads' S0 layout as well as the ledger's slot folders.
    - **Its target is `testseed\repro\fit1.001.tsv`,** SHA-256 `377dbf86205380ae202414dd438de5ec2ebb6c2184147d133d89aa80373c8505`, written by DEBRIS-H's run whose log is `studies\debris-h\logs\h_seed_fit1.002.log`. That log records its decode batch: one JVM (`--jprocs 1`), with the 64 objects in the order of `work_fit1_2/pv_in.00.txt`, whose SHA-256 it gives. `testseed\fit1.001.tsv` came from log 001, by an earlier version that recorded no batch, so it is not the target.
    - **It decodes in that batch.** The decoder's output depends on what its JVM decoded before (DEBRIS-H's finding 1), so another batch could fail the control for no fault of the code (the re-check's defect 1).
    - **The script's version:** log 002 ran `h_seed.py` version `008027ab…`. The current `tests\h_seed.py`, `d43000d5…`, differs from it only in handing `m1f` its downloads folder (`M1_DOWNLOADS`) and in logging `m1f`'s errors (READ, the diff of DEBRIS-H's kept versions in `studies\debris-h\scripts\`). So the fit's computation is the same, given `--downloads` at the desktop's downloads.
    - It must reproduce the target: the same convergence and iterations, and every printed value equal.
    - The test seed's objects all lie above 400 km: the lowest perigee is 470 km (COMPUTED by the lead from its states). So this tests the pipeline's plumbing, not its behaviour where drag is strong.
    - The 17 objects' seed fits were made on the box. They are refitted on the desktop too, and their differences reported as a measurement. DEBRIS-H's H6 found the two machines up to 0.023 m apart in a miss, so equality is not expected there;
  - **a planted `bc`** (plan-verifier-K's D10): take the lowest-perigee object, other than seed index 1595, that has a reference 12 to 36 hours after a forecast time and that M1 does not decay before that reference (the re-check's defect 3). Double its `bc` in (R)'s pipeline.
    - The pipeline must give, bit for bit, the state `tests\m1f.c prop` gives when run directly with the doubled `bc` and the same inputs. That shows that `bc` reaches the force model whole, not in part.
    - It must also move the predicted position at that reference by at least 100 m. That shows that it matters;
  - **a planted identity:** (H) given another object's sets must miss by more than ten times (H)'s own median, or be refused by its fit.
- **The cost (ESTIMATE, revised after plan-verifier-K's D8):** a one-day fit costs about 2.4 CPU-seconds on the box (DEBRIS-H's plan, from F9's T3), and 1.5 to 2.5 times that on the shared desktop (BELIEVED).
  - (R): 17 objects at 5 times, 85 one-day fits, about 5 to 9 CPU-minutes.
  - (H): 17 objects at 3 times, with spans of about 2 to 3 days, and 4 to 10 iterations, about 6 to 38 CPU-minutes (the re-check's note: an iteration over 2 to 3 days costs about 1.8 to 4.5 CPU-seconds on the desktop).
  - The SGP4 decodes through Orekit: about 5 to 10 CPU-minutes (BELIEVED: each decode starts a Java machine).
  - So the total before (C) is about 16 to 57 CPU-minutes. (C) runs only if the total after (R), (H) and the decodes is under 30 CPU-minutes. If the total passes 40, (H) at slot 13 is cut, by decision 4's order. The study measures its own CPU as it goes.

## The shape

| agent | job | model | when |
|---|---|---|---|
| the lead (this session) | the brief and the ledger; escalations, and filing the final message; the merge and its narrowing, the commit and the round's record | Opus | throughout |
| DEBRIS-K | the study: Q1 to Q7, and the pilot | Opus (decision 1) | after the plan-verifier |
| verifier-K | disconfirm the study and its pilot | Sonnet (decision 1) | when DEBRIS-K reports |
| merge-check-K | check any narrowing the lead makes at the merge | Haiku | after verifier-K, if the lead narrows anything |

**The schedule (ESTIMATE):** the study runs about 5 hours from dispatch, today. verifier-K follows, then the merge and the commit. The push waits for Logan's word.

## Dispatch

- **The prompt:** a dispatch note and the brief, followed verbatim by four sections of this plan: "Dispatch", "The ledger", "Rules every brief carries" and "READY". A script writes the prompt from this file. After dispatch, `dispatch\check_prompts.py` checks the prompt against the harness's transcript.
- **The test escalation:** DEBRIS-K sends one as it starts:
  - it writes `test escalation from DEBRIS-K` in its own ledger file;
  - it sends the same words to the lead (SendMessage to `main`);
  - the lead replies "received" and records the round trip in `lead.md`.
- If no test escalation arrives within ten minutes of a dispatch, the lead reads the agent's ledger file, arms a watch on the ledger folder, and says so in `lead.md`.
- **One phase.** DEBRIS-K's final message is its report. Ending its turn ends its run, and a later message from the lead resumes it.

## The ledger

The ledger is `C:\Users\logan\source\repos\cft-debris-ledger\`, as in rounds DEBRIS-B to DEBRIS-I.

- **One file per author, append only:**
  - `lead.md` continues;
  - this round adds `DEBRIS-K.md` and `verifier-K.md`, which the lead creates with a header only;
  - correct an entry by appending beneath it, never by editing it.
- **Times:** every heading's time comes from `date`, never from memory.
- **Read it at three moments:** before starting; before resting anything on another study's number; before the final report.
- **Verifiers read `lead.md` only,** and the files it points them to.
- **Escalation:** write the entry first, then message the lead (SendMessage to `main`). Wait for the answer to a question while working on what does not depend on it. Never end your turn to wait.
- **No agent messages another session.** Your messages go to the lead, `main`, only.
- **When to write:** when an entry would change another agent's work or the lead's: an environment fact, a brief that turned out wrong, or a finding about a shared input, never progress. Every entry marks which claims were measured and which are believed.
- **Scratch:** each agent creates its own folder when it starts, `C:\Users\logan\source\repos\cft-debris-scratch\<name>\`. Read no other agent's scratch. Keep no secrets anywhere an agent is given.
- **The downloads:** `C:\Users\logan\source\repos\cft-debris-downloads\`, one folder per file, each file's SHA-256 in `lead.md`. Read-only for every agent. This round adds none.
- **The tools:** `cft-debris-ledger\tools\`, read-only for every agent.
- **Data kept out of the repository:** `cft-debris-ledger\debris-k\`, for every output that names an object or holds its state or its elements. DEBRIS-K writes there. DEBRIS-H's and DEBRIS-F's records, and `events\`, are read there, never changed.
- **What the lead writes in `lead.md`, every verifier reads.** The lead never writes a judgement of DEBRIS-K's work there before verifier-K has reported.

## Rules every brief carries

These come from three places: Logan's standing rules (carried from cft-fp256 and cft-rebound, 2026-09 to 2026-11), canonical ParcelRound, and the rulings of rounds DEBRIS-B to DEBRIS-I.

- **Read-only, except your own outputs and scratch.**
  - cft-rebound, cft-fp256 and the TimeSheet are other sessions' live repositories. Read their files; in git, use only `git -C <repo> log` and `git -C <repo> show`. Never write in them, never run `git status` there, and never run a bare `git stash`.
  - In the TimeSheet you may run `timesheet.py check` and `list`, which only read.
  - In cft-debris, write only where your brief says. Commit nothing: the lead commits after verification.
  - **DEBRIS-I may be building in `tests\` and `studies\debris-i\` at the same time.** Touch none of its files.
- **The repository is public and MIT.**
  - Every source file you write carries a header naming cft-debris and the MIT licence.
  - Copy no third-party source into the repository, whether cft-fp256's, REBOUND's, cft-rebound's or Orekit's. Orekit is called through Nashorn, never copied.
  - Copy no third-party data into the repository either: no GP data, no SATCAT record, no space-weather values, no Earth orientation values.
  - **Per-object data stay out of the repository.** Logs in the repository name objects only by their index in DEBRIS-H's seed, never by catalogue number. They carry hashes, counts and aggregates, never a state or an element set.
  - Reading a source to understand an interface is fine; quoting more than a short passage is not.
  - This project's own earlier code (DEBRIS-B's to DEBRIS-H's, and the lead's scripts in the ledger) is MIT, and may be reused with a note of where it came from.
- **No downloads, installs or package managers, and no requests to any data service.**
  - This round's files are in the downloads and the ledger.
  - **CelesTrak in particular: no agent requests it,** not even a page that looks like HTML. **Space-Track** needs an account, and no agent uses one.
  - If another file would settle a question, ask the lead for it. Give its name, source URL, size, licence and purpose. Each file needs Logan's approval.
- **Reading the web: HTML pages only, and never CelesTrak's.**
  - **What may be read:** documentation and publication pages, such as The Aerospace Corporation's, ESA's, NOAA's or Space-Track's public pages (plan-verifier-K's D11).
  - **What may not:** a data endpoint, a page behind a login, or any page on celestrak.org. CelesTrak's terms are DEBRIS-H's plan's record of them, from 2026-11-16 and 2026-11-18, since no agent reads CelesTrak's pages.
  - WebFetch returns a model's summary of a page, not its bytes. A figure or quote taken through it is labelled "READ (via WebFetch)". It supports "consistent with", never "confirmed".
  - WebFetch saves any response that is not HTML to disk. So a URL ending in `.txt`, `.pdf`, `.csv`, `.zip`, `.bin`, `.jar` or `.gfc`, or one in an FTP tree, is a download request, whatever it seems to hold.
- **No GPU, WSL, card or box.** amd-arc-box is the lead's, and this study needs no run there.
- **Keys:** this round uses no keys and signs nothing. Never look in `~/.ssh`.
- **Timings: none.** The desktop is shared. Desktop runs are functional, and no time from them is reported as a measurement.
- **At most 2 processes at once on the desktop,** counting every child process you start: JVMs, fits and predictions alike. DEBRIS-I may hold up to 4 beside you.
- **CPU budget** means the CPU time of the processes you start on the desktop, counted by cycles:
  - read `QueryProcessCycleTime` through Python's `ctypes`, and divide by 2.5e9 cycles a second;
  - the divisor is the part's base clock (READ, cft-fp256's `docs/BENCHMARKS.md`), and taking it as the counter's rate is BELIEVED;
  - give `GetProcessTimes` beside it. On this host it under-reports a busy thread under load: by a factor of about 1.7 to 4 in round DEBRIS-C, and in DEBRIS-F it gave 2.00 s for a run whose cycles showed 3.97 s (MEASURED);
  - DEBRIS-E's `tests\cpurun.py` does both, and may be reused.
- **Long jobs:** run them through the Bash tool, in the foreground with a timeout of at most 600000 ms or with run_in_background. Never use nohup, and never end your turn while one of your jobs is running.
- **C on the desktop:**
  - Before any compile, put `C:\msys64\mingw64\bin` first on PATH and check that `gcc -dumpmachine` prints `x86_64-w64-mingw32`. In this Git Bash, a bare `gcc` is the 32-bit i686 compiler.
  - M1's build is as `studies\DEBRIS-F-build.md` gives it, through `tests\build_f.sh`, in your scratch. libcft comes from the ledger's archive `tools\cft-fp256-0aa997a3.tar`, extracted and built in your scratch, as DEBRIS-F did.
- **Java:** Java 8 at `C:\Program Files\Java\jre-1.8\bin\java.exe`, with DEBRIS-F's Orekit and Hipparchus jars as `tests\f_lib.py` lists them.
- **Python:** `C:\Users\logan\AppData\Local\Programs\Miniconda3\python.exe -I -B`, with numpy and mpmath.
- **Processes and files:** kill only processes you started, and only by PID. Delete only what you made, and never through a computed path.
- **Earlier studies' records are read-only.** Copy what you run into your scratch or your own output folder. Before your report, check all ten:
  - `sha256sum -c SHA256SUMS` run from `studies\` shows 32 OK;
  - `find studies/debris-a -type f | wc -l` gives 29;
  - `sha256sum -c MANIFEST.sha256` shows 54 OK from `studies\debris-b\`, 136 OK from `studies\debris-c\`, 73 OK from `studies\debris-d\`, 60 OK from `studies\debris-e\`, 61 OK from `studies\debris-f\`, 43 OK from `studies\debris-g\` and 149 OK from `studies\debris-h\`;
  - there is no `__pycache__` anywhere under `studies\`.
- **Host traps:**
  - **System32 before PATH.** From Python, or anything else that calls CreateProcess, Windows searches System32 before PATH. So a bare `bash` is `C:\Windows\System32\bash.exe`, the WSL launcher, and a bare `timeout` is `TIMEOUT.EXE`. System32 also holds `wsl`, `tar` and `curl`. Start every program from Python by its full path, such as `C:/msys64/usr/bin/bash.exe` and `C:/msys64/mingw64/bin/gcc.exe`, or run it through the Bash tool directly (round DEBRIS-D, `lead.md`, 2026-11-12 21:23).
  - **MSYS `.exe` transparency:** writing a file `X` beside an existing `X.exe` writes to `X.exe`.
  - **CRLF:** passing a script to bash from Python with `text=True` turns every newline into CR+LF. So does any text-mode write from Python on Windows, `Path.write_text` included. Write bytes, or open with `newline="\n"`, wherever a file's bytes matter.
  - **Backslashes:** in the Bash tool, a doubled backslash reaches the shell as one, inside a heredoc too. Write any script that contains backslashes with the Write tool, and write Windows paths in commands with forward slashes. Every check asserts that it found something to check.
  - **`cd`:** a Bash `cd` into a subfolder can move the session's working directory for every later call. Use absolute paths, or `git -C`.
  - **`grep` and CR:** Git Bash's `grep` strips the CR at each line end unless given `-U`. Count CRLF with Python.
  - **Windows paths in `sha256sum`:** given a backslashed path, it prefixes its line with `\`. Pass forward-slashed paths.
  - **Per-object files:** read a per-object file's header with `head -n 2`, never `head -c`, so that no row of it lands in your context unasked.
  - **Never start a process under `pythonw`,** or detached, on the desktop.
- **No helper agents.**
- **Your final message is your report.** Its word limit is in your brief. If the harness refuses the write of a document your brief names, your final message is that document followed by the report, and the word limit then applies to the report alone.
- **Before you report,** stop any background work you started. End with what you did not do, and with anything your brief got wrong.

## READY, stated before the first pass

READY applies to DEBRIS-K and to every verifier's verdict. Every load-bearing claim must rest on one of:
- a measurement, with its command and output;
- a fetched source, cited by URL;
- arithmetic from labelled inputs.

Otherwise it is stated as a limit, in terms of the behaviour it concedes. A claim's domain and quantifier are claims, and so is a figure's definition. A number carried over from an earlier study keeps its definition, or it is re-measured.

**From rounds DEBRIS-B to DEBRIS-I:**
- **Every control states its pass and fail criteria before the data, and the code asserts them.** A control that fails as specified is reported as failed, whatever replaces it.
- **Every agreement claim states its tolerance before the data,** with its basis.
- **A measurement with no pass condition states its statistics, its configurations and its sample before the data.** The pilot is such a measurement, and this plan fixes its statistics.
- **Every log names the SHA-256 of the script that wrote it,** and the criterion that script asserted.
  - Keep every version of a script that wrote a log, under a name carrying the first 12 hex digits of its hash, before you change it.
  - Never overwrite a log: number each run's log.
  - The manifest lists every version.
- **An ESTIMATE names its basis and its range,** and is never added to a MEASURED figure without saying so.
- **A bound over many trials holds only when the trials are independent.** Say what varies from trial to trial.
- **A cause is claimed only when a run isolates it.** Otherwise it is inferred, and labelled so.
- **Every miss statistic names its method, its cell, its count, and whether the flagged fits are in it.**
- **Every check's reference is the catalogue,** not the truth. No sentence calls a miss an error of M1 against the sky.

**New in this study:**
- **A decay prediction names its rule, its forecast time and the sets it used.** A SATCAT date is a date only, so a predicted time is compared with the whole day, as E0005 was.
- **A recommendation is labelled as one, apart from the evidence,** and says what evidence would change it.

A verifier may reuse a run instead of re-running it only when all three of these hold:
- someone other than the author of the work made the run;
- its inputs are identical, file hashes included;
- the verifier re-runs from clean whatever it doubts.

Only a wrong answer sends work back: a false claim, a measurement or check that cannot fail, or code that does not do what its claim says it does. Everything else is a note the lead records, and a sentence that claims too much is narrowed at the merge.
- **Loop cap (Logan, 2026-10-15, carried through the lead's memory):** after three NOT READYs for narrowing reasons, the next pass blocks only on wrong answers.
- **Threat model (Logan, 2026-10-02):** each verifier's brief states one, and findings outside it do not reopen the loop.

## Logan's decisions (each default stands unless changed)

1. **Models:**
   - (a) **Opus for DEBRIS-K, Sonnet for verifier-K,** and Haiku for a merge-check: Logan's pairing for challenging work (2026-10-12). The study reasons across the force model, the data's terms and a fitted hindcast;
   - (b) Sonnet for DEBRIS-K and Haiku for verifier-K.
   - Default: (a).
2. **The pilot's data:**
   - (a) **only what the ledger and the downloads hold,** with no request;
   - (b) also one SATCAT request for seed index 1178 (the week's decision 4, still not made) and a fresh space-weather file, each on Logan's yes and made by the lead.
   - Default: (a). Without (b), index 1178's decay has no reference, and DEBRIS-H's window has predicted space weather only.
3. **The pilot's variants:**
   - (a) **(A), (B), (B'), (R) and (H), and (C) if the budget allows;**
   - (b) (A), (B), (B') and (R) only.
   - Default: (a).
4. **Scope and budget:**
   - (a) **5 hours of wall time and 50 CPU-minutes on the desktop,** at most 2 processes at once. DEBRIS-K messages the lead before passing either, and before any single run it expects to pass 5 CPU-minutes. If time runs short, it cuts in this order: (C); (H) at slot 13; Q6's GPU rows. Q1, Q2, Q4, Q5, Q7 and the pilot's (A), (B), (B') and (R) are kept;
   - (b) 3 hours and 25 CPU-minutes, without (C) or (H).
   - Default: (a). The pilot's revised cost is about 16 to 57 CPU-minutes before (C) (ESTIMATE, "The pilot hindcast"), so the cut order may bite. (C) runs only under 30, and (H) at slot 13 goes past 40.
5. **Outputs and the push** (a statement, not a choice): the study's report goes in the repository after verification, and its per-object tables in the ledger. Pushing waits for Logan's word.

## Not in this round

- **Any change to M1's library,** and any build of a cft program or service.
- **Any run on the box,** a GPU, a WSL distro or a card.
- **Any download or request:** CelesTrak, SATCAT, Space-Track and the space-weather file. Q5 proposes them, for Logan.
- **A long run,** a live service, and certificates.
- **A model of the atmosphere of our own:** Q2 and Q4 may recommend one, priced.

---

## Brief: DEBRIS-K

You are study parcel **DEBRIS-K** in cft-debris, a project for space-debris tracking and simulation. Its folder, `C:\Users\logan\source\repos\cft-debris`, is a public git repository under the MIT licence.

Your question is Logan's: whether M1 (and later DEBRIS-I's cft program) could give a small set of objects more thorough forecasts, decaying LEO objects first, and refine its model over time from how its predictions fare. Answer Q1 to Q7 of the plan, and run its pilot hindcast as the plan fixes it. You build nothing for the service, change no earlier file, and request nothing. You commit nothing: the lead commits after verification.

**Budget:** decision 4: 5 hours of wall time and 50 CPU-minutes on the desktop, at most 2 processes at once. Message the lead before passing either, and before any single run you expect to pass 5 CPU-minutes. Your booking is the lead's notice on the desktop: it already covers your runs.

**Start here:**
1. This plan, `C:\Users\logan\source\repos\cft-debris\studies\DEBRIS-K-plan.md`: Logan's words, what the study starts from, the questions, and the pilot.
2. `lead.md` in the ledger, from its entry headed 2026-11-23 07:55 on, and its records of DEBRIS-H's run, read as you need them.
3. M1 and its pipelines:
   - `src\`;
   - `tests\m1f.c`, `tests\build_f.sh`, `tests\f_lib.py`, `tests\f_fit.py`, `tests\f5_sgp4.js`, `tests\f6_hindcast.py`, `tests\f6_orekit_fit.js` and `tests\f6_swcopy.py`;
   - `tests\h_seed.py` and `tests\h_lib.py`, DEBRIS-H's fit with its paths taken from arguments; and `tests\m1h.c`, whose `RMIN` is M1's decay rule;
   - `tests\h_check.py` and `tests\h_analyze.py`, DEBRIS-H's check and its analysis.
4. The studies:
   - `studies\DEBRIS-F-build.md` §5 and §6, and `studies\DEBRIS-H-build.md`, each narrowed at its merge;
   - `studies\DEBRIS-C-measurements.md`, on the density models;
   - `studies\DEBRIS-D-architecture.md`, Q6 and Q7.
5. The data:
   - the ledger's `events\events.tsv`;
   - DEBRIS-H's `debris-h\box\r2\seed\seed1.txt`, `svc\fetch\` and `svc\checks\`;
   - the downloads' snapshots and `SW-Last5Years.txt`.

**Where it goes:**
- `tests\`: new code only, named `k_*.py`, `k_*.js` or `k_*.c`, among them `tests\k_fit.c` for (H). Reuse earlier code by copying it into new files with a note of where it came from; earlier files stay unchanged.
- `studies\debris-k\`: your scripts' logs and records, with a `MANIFEST.sha256` over them.
- `studies\DEBRIS-K-study.md`: the study, under 7,000 words.
- `cft-debris-ledger\debris-k\`: every output that names an object or holds its state or elements.
- **In your scratch only:** cft-fp256's sources, libcft's and M1's builds, and every executable.
- **Paths:** every script takes its paths from its arguments, and none hard-codes a home folder.

**The study, `studies\DEBRIS-K-study.md`:**
- a short answer, then Q1 to Q7 in order, each with its evidence and labels;
- the pilot's method, its controls' results, its tables (aggregates only) and its limits;
- a recommendation, labelled as one, with what would change it;
- what the study could not settle, and its sources.

**Your report** is your final message, under 900 words: the short answer, the pilot's results, the recommendation, what you did not do, and anything this brief got wrong. Label every figure.

## Brief: verifier-K (completed when DEBRIS-K reports)

You are **verifier-K** in cft-debris. Your job is to disconfirm DEBRIS-K's study and its pilot, never to fix them. Edit no file outside your scratch.

**Threat model.** A wrong answer in DEBRIS-K's work:
- a pilot statistic not as this plan fixed it, or fixed after the data;
- a check that cannot fail;
- a miss computed at the wrong time, in the wrong frame or against the wrong set;
- a fit that used sets fetched after its forecast time;
- a claim about a data source or its terms that the source does not support;
- a cost not as defined;
- per-object or third-party data in the repository.

Findings outside this model are notes, and do not reopen the loop.

**Attack these, in this order** (completed when DEBRIS-K reports):
1. the pilot's sets by forecast time: no set fetched after a forecast's time is in its fit, and every horizon is measured from the set the plan names;
2. 20 of the pilot's misses, recomputed with code of your own;
3. the controls bite: re-run them;
4. the statistics against this plan's definitions;
5. Q5's claims about sources and terms, against the pages cited;
6. Q6's arithmetic;
7. the repository: no catalogue number, state, element set or personal string in any file under `studies\` or `tests\`.

**Budget:** 2 hours of wall time and 15 CPU-minutes on the desktop, at most 2 processes at once.

**Report:** your final message, under 1,000 words, with each attack's verdict (confirmed, defect, or not determined) and its evidence. For every defect, give the exact passage and what it should say.

## What changed from draft 1 (plan-verifier-K's findings, answered)

The lead checked each finding's evidence before answering it:
- `tests\h_check.py`'s columns;
- `tests\m1f.c`'s `Obj` and `lsq`;
- `tests\m1h.c`'s `RMIN`;
- `tests\f_lib.py`'s line 22 and `tests\h_seed.py`'s usage;
- `tests\h6_gate.py`'s tolerance;
- the round record's H7 and the build report's departures;
- the check tables present.

Every blocker and defect was upheld.

- **B1, unlike baselines.** Every horizon is now measured from the set the forecast used. (B'), SGP4 from the latest set, is the like-for-like baseline. The main comparisons are (R) and (H) against (B'), with (A) against (B) restating DEBRIS-H's.
- **B2, (H)'s fit.** It now runs `tests\k_fit.c`, a copy of `m1f.c`'s fit that takes pseudo-observations at any times, with equal weights. A grid time's observation comes from the earliest set at or after it.
- **The defects:**
  1. M1's decay rule is `tests\m1h.c`'s `RMIN`, carried in a copy.
  2. (R) runs DEBRIS-H's `tests\h_seed.py` rule through a copy that reads the slot folders. `tests\f_lib.py`'s hard-coded scratch is named.
  3. The regression now runs on DEBRIS-H's test seed, fitted on this same desktop, for exact equality. The box-made fits' differences are a measurement, since H6's 0.023 m was a miss, not a fitted state.
  4. Seed index 1595 is a reconstruction, reported apart, with fits and references held to before its decay date.
  5. H7's figures carry their domain, and (B)'s are beside them.
  6. The event history's case is labelled one case and inferred.
  7. The `bc` range names F6's perigees, 273 to 857 km.
  8. The cost is revised: (R) at 5 times, (H) at 3, about 16 to 34 CPU-minutes before (C), so the budget is 50, with (C) only if the total stays under 30.
  9. The 90th percentile is the ceil(0.9n)-th smallest, the along-track part is taken by size with its signed median beside, and the learning curve is binned. (B) is named as from the seed's set.
  10. The planted `bc` names its object, must equal `tests\m1f.c prop` run directly bit for bit, and must move the position 100 m. T3 has a pass rule with its co-planar exception.
  11. The web rule now names what may be read, and where CelesTrak's terms come from.
- **The notes:**
  - slot 18 is no longer a forecast time;
  - decision 5 is marked a statement;
  - the escalation rule names `main`.

## What changed from draft 2 (plan-verifier-K's re-check, answered)

The re-check found no blocker. It confirmed B1, B2, D3, D4, D8 and D10 in substance, and the budgets. The lead checked its evidence (the round record's finding 1, `tests\h_check.py`'s batch log, and the test seed's own log of its batch) and answered each point:
- **Defect 1, the regression's batch.** It now decodes in the batch the test seed's log records: one JVM, in the order of its `pv_in` file. The plan says the regression tests the plumbing only, and that the (R) copy reads S0's layout too.
  - The lead found that the test seed has two tables. Only `testseed\repro\fit1.001.tsv`'s run, log 002, recorded its batch, so it is the target.
  - The lead also found that its script's version differs from the current `tests\h_seed.py` only in its downloads' environment and its error logging, so the fit's computation is the same.
- **Defect 2, seed index 1595's references.** No miss of it is computed. Its only output is a decay prediction from sets before its decay date, set beside SATCAT's date.
- **Defect 3, the planted `bc`'s object.** It excludes 1595, and any object M1 decays before the reference.
- **The notes:**
  - (H)'s cost is now 6 to 38 CPU-minutes, at 4 to 10 iterations. The total before (C) is 16 to 57, with (H) at slot 13 cut past 40;
  - (H)'s grid ends on the last 120 s grid time at or before the latest epoch, and its state is propagated from the origin.

## The lead's slips so far

1. **Draft 1's account of the slots** said that slots 1 to 20 were fetched "except 16 and 17". The lead's own reading of `slots.tsv` corrected it before the checker's last run.
2. **The baselines** (plan-verifier-K's B1). Draft 1 compared refits from the latest set with DEBRIS-H's forecasts from the seed set by horizon, and never said where a horizon starts.
3. **(H) "with M1's fit unchanged"** (B2). The lead had not read `m1f.c`'s observation grid before writing that.
4. **The regression's basis** (D3) took H6's 0.023 m, a miss, for a difference in a fitted state.
