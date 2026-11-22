# Round DEBRIS-H: the record

The lead's record of round DEBRIS-H in cft-debris, 2026-11-18 to 2026-11-21.
- **The plan of record** is `DEBRIS-H-plan.md`, draft 3 (SHA-256 `1fe450b289768ab25a6e27ec7f369406f4e9930304d4b0776e06d53b1b7eaa41`).
  - Logan approved it in chat at 07:24:54 on 2026-11-18: "Approved but I'm away for the day and won't be able to install Java for you until later". That approved its fourteen decisions at their defaults.
  - plan-verifier-H (Sonnet) checked draft 1 and re-checked draft 2. Every finding was upheld and answered. Draft 3 had only the lead's checker, `check_plan_h.py`.
- **Logan set the round's direction** on 2026-11-12: "a simulation capable of realtime (or slightly faster) simulation on a consumer card, so a 24x7 sim could run on a local box here for long run tests, validating itself with the open datasets update intervals". Round DEBRIS-G measured the box's capacity, and on 2026-11-18 Logan asked for this round's draft.
- **The ledger** is `C:\Users\logan\source\repos\cft-debris-ledger\`: `lead.md`, `DEBRIS-H.md` and `verifier-H.md`, and the round's per-object data in `debris-h\`. It is outside this repository.

## What ran

| agent | model | job | wall time | output |
|---|---|---|---|---|
| plan-verifier-H | Sonnet | checked draft 1; re-checked draft 2 | 11-18, 06:15 to 06:38 -0700 | its two reports, filed verbatim in the ledger's `filed\` |
| DEBRIS-H | Opus | **phase 1:** the driver, the supervisor, the fetcher, the check, the seed, the gates and their desktop runs. **The fix phase:** H6's box failure. **Phase 2:** `h_analyze.py` over the run's records, and the build report | phase 1, 11-18 07:30 to 08:53, about 38 of its 50 desktop CPU-minutes; the fix, 11:29 to 11:53, about 10.7 of 15; phase 2, 11-21 16:07 to 16:33 (1,574 s, 98 tool calls, 18.6 CPU-seconds) | `tests\`, `DEBRIS-H-build.md`, `debris-h\` and `DEBRIS-H-report.md`; its two hand-offs, filed in the ledger; its per-object tables in the ledger's `debris-h\` |
| verifier-H | Sonnet | **re-ran** the build and H2's controls. **Recomputed** H6's pairs, 20 checks, the fetch log, the lag accounting, the aggregates, the seed, the divergence, the splits and the departures. **An audit of its own sample** on the box, run by the lead | 11-21 16:41 to 16:53 (749 s, 88 tool calls); about 72 desktop CPU-seconds; about 29 box CPU-minutes (ESTIMATE) | `DEBRIS-H-verifier-H-report.md` |
| merge-check-H | Haiku | checked the lead's narrowing | 11-21 16:57 to 17:01 (230 s, 20 tool calls) | its report, filed verbatim in the ledger's `filed\` |
| the lead | Opus | Phase 0, every box run, the launch, eight visits and the end, filing, the ruling, the merge, the commit | throughout | `lead.md`, and the ledger's tools for this round |

## Phase 0, before dispatch

- **No downloads,** under decision 8(a). The run's first snapshot, S_H0, came at the launch.
- **`dispatch\open_round_h.py`** checked the archive and DEBRIS-F's frame table against their recorded SHA-256, and made the ledger files.
- **Dispatch:** DEBRIS-H went out at 07:30 on 2026-11-18 on Opus, under the desktop notice B0140. Its prompt arrived identical to the filed copy, and its test escalation came back.
- **cft-fp256's lead was told** of the run: its window, priority, workers, booking and pause. Its answer was that its night runs would carry our load beside theirs.

## The long run

- **Before the launch,** on 2026-11-18, the box ran:
  - H1, the build;
  - H2;
  - the paced dry run;
  - H4: all 8,088 decoded states bit-identical with the desktop's;
  - H6's box half and C17;
  - the two seed fits and H5.
- **H6's box half failed.** 10 of 200 fitted pairs differed by machine, by up to 0.023 m.
  - DEBRIS-H's fix phase measured the cause: the desktop's `asin`, `acos` and `exp` are not correctly rounded, and the fit amplifies the difference.
  - Logan's word at 14:39:42, "Yes, launch", recorded H6's box half as failed, with its criterion unchanged.
- **S_H0:** the lead's first run, at 14:43, stopped at its second request, which was answered with an HTTP 500. On Logan's word, "Yes, at 15:00", the three missing groups were fetched once each at 15:00.
- **The launch:** 15:23 on 2026-11-18, with T_s at 15:48:50.817 -0700, from the run folder `r2`, under B0176 (`shared`).
  - **The tracks:** A256, 18 cft256 workers; A64, one native64 worker on the same seed; A64f, one native64 worker on the second seed, with `bc` fixed at 0.01 m²/kg.
  - **The objects:** 2,688, one object per element set.
  - **The schedule:** a checkpoint every 40 steps of 15 s, and a CelesTrak fetch and a check every 3 hours.
- **Eight visits and the end,** from 2026-11-18 16:01 to 2026-11-21 16:09 in `lead.md`. Each ran read-only scripts on the box, sent by stdin. The scripts and their outputs are in the ledger's `tools\visits-h\`, with SHA-256 lists.
- **The nights.** cft-fp256's night runs loaded 9 to 12 of the box's 36 CPUs each night, from about 18:30 to 07:45. They were night 1118, then its standing windows S003 and S004.
  - A256's computing rose to about 15 s a step, and it fell behind by up to 2,214.8 s, 2,728.5 s and 2,440.3 s on the three nights.
  - It was on time again at 08:42:22 and 08:59:23 the next mornings. The third night ran to the end, which came 454.0 s late.
  - A64 and A64f were never late.
- **The fetcher** made 70 requests in 19 slots: 65 answered 200, 4 without a response (slots 12, 15, 16 and 19) and 1 answered HTTP 500 (slot 20).
  - It stopped at slot 16, the second slot in a row without a response, and again at slot 20, on the 500.
  - On Logan's word it resumed at slot 18: the lead renamed its stop file at 21:01:26 on 2026-11-20.
  - On Logan's word it stayed stopped after slot 20, so slots 21 to 24 made no request.
- **The end.** Step 17280 finished at 15:56:24 on 2026-11-21, and the service exited cleanly, with 0 restarts. `h_audit.py` passed (d1) and (d2).
  - The records were copied to this repository (91 files) and to the ledger (9,210 files), each equal to the box's SHA-256.

## What it built and found, after verification and narrowing

**What was built:**
- `tests\m1h.c`, the driver, on M1's unchanged `src\`;
- `tests\h_service.py`, the supervisor;
- `tests\h_fetch.py`, the fetcher;
- `tests\h_check.py`, the check;
- `tests\h_seed.py`, the seed;
- `tests\h_lib.py`, `tests\h_stage.py`, `tests\h_build.py` and `tests\h_audit.py`;
- the gates H0 and H2 to H6, with H3's local server;
- the paced and integration tests;
- `tests\h_analyze.py`.

`DEBRIS-H-build.md` gives the details, with one narrowing and three additions at the merge, each marked.

**H7, the long run** (MEASURED by `h_analyze.001.log`, and confirmed by verifier-H):

| criterion | result |
|---|---|
| (a) the fetches | PASS |
| (b) the checks | **FAIL by its letter.** 6,469 checks, and T1 passed on all 25,876 check-methods. T3 found 3 hits, at slots 5, 11 and 18, each on two distinct objects at their orbits' nodes. Slot 16's 191 later sets were not eligible, since the fetcher stopped in that slot (narrowed at the merge) |
| (c) the sanity bound | PASS: (A256)'s median miss at horizons under 24 hours is 1.240 km, n 1,494, against 5 km |
| (d) the checkpoints | PASS: 433 checkpoints per track, every file matching the manifest. 10 of 10 sampled segments equal on each track, and again on verifier-H's own sample |
| (e) the pacing | **FAIL by its letter.** 2 of 20 qualifying hours hold late steps: 08:00 on 2026-11-19 and 08:00 on 2026-11-20, each begun behind after a night's load |
| (f) the kinds | PASS at T_s. At step 17280 the median distance is 1.41e-5 m and the largest 7.19e-5 m |

**The measurements** (MEASURED, all 6,469 checks, flagged fits in; median and 90th percentile):
- (A256): 4.888 km and 21.277 km. (A64) equals (A256) at the printed metre.
- (A64f): 3.422 km and 28.114 km.
- (B): 0.306 km and 2.250 km.
- (A256) misses less than (B) in 334 checks (5.2%).
- 2,076 of the 2,688 objects were checked.

**Findings** (the build report's §7):
1. The decoder's output depends on what its JVM decoded before.
2. The two machines' C libraries round differently, and the fit amplifies it (H6's box half).
3. T3 fired three times on co-planar sets at their nodes.
4. A256 kept real time only while the box was otherwise idle.
5. (A256)'s miss is mostly along track, and it grows with the run's age.
6. A log line misnames a skipped slot: "missed while the service was down".

**Outside H7:** at Logan's request of 2026-11-19, the lead keeps an event history of the tracked objects in the ledger's `events\`: M1's decays, group changes and a SATCAT decay record, E0001 to E0008. It is not part of any criterion.

## Rulings and events

- **2026-11-18 07:24:54:** Logan approved the plan.
- **14:39:42:** "Yes, launch", with H6's box half recorded as failed.
- **14:52:21:** "Yes, at 15:00", for S_H0's three missing groups.
- **15:23:** the launch.
- **2026-11-19 05:08:04, H7(e):** "Keep it as written". The split, on time or behind at an hour's first second, is reported beside the verdict as a measurement defined after the data.
- **The visit planned for 09:15 on 2026-11-19 was missed:** no wake-up had been set. Visit 4 came at 12:23, and every later visit had a wake-up.
- **15:08:28, H7(b):** "Keep it as written". The T3 cause, objects at their nodes, is reported beside the verdict as a measurement defined after the data.
- **15:38:44:** Logan asked for the event history. **16:20:02:** "Yes, check SATCAT". One request confirmed that the object at seed index 1595, the first M1 decayed, came down on 2026-11-18.
- **2026-11-20 19:09:12:** "Resume at slot 18".
- **2026-11-21 09:49:50:** "Leave it stopped".
- **16:07:** DEBRIS-H was resumed for phase 2, and its report was filed at 16:39.
- **16:41:** verifier-H was dispatched. **16:52:** the lead ran its own-seed audit on the box.
- **16:57, the ruling:** no send-back.
  - verifier-H's one defect, "all checked (0 listed)" without slot 16's 191 sets, was narrowed at the merge.
  - Two of its notes, on foreign load and on the node shares, were not borne out by the data.
- **17:01, merge-check-H:** it confirmed the diff, the markers and the figures, and found three defects in the lead's wording: the foreign-load evidence, which read the service log's UTC times as local; verifier-H's one "not determined", left out of §10; and two of its "did not do" items, also left out. All three were fixed, and a script showed the four edits are all that changed since its check. The 16:57 entry is corrected at 17:03.

## Failures, recorded as failures

- **H6's box half failed:** the C libraries round differently by machine.
- **H7(b) and H7(e) fail by their letters,** each kept so on Logan's ruling.
- **The fetcher stopped twice,** and slots 17 and 21 to 24 fetched nothing.
- **DEBRIS-H's H6 desktop run** used 18.8 CPU-minutes, past the lead's stop line of 15. Its own ESTIMATE, when it asked, was 9 to 11. It was accepted after the fact.
- **Reports past their limits:** DEBRIS-H's report is 1,147 words against 900, and its second hand-off 750 against 700. verifier-H's report is 1,340 words against 1,200.
- **verifier-H did not release its booking,** B0244. The lead released it.
- **Ledger headings:** two lines of `DEBRIS-H.md` hold stray control characters, and one heading of `verifier-H.md` has an unexpanded date. Each is corrected beneath.

## What the plan got wrong

- **H7(e) is blind to the backlog** a loaded hour leaves. A quiet hour that begins behind fails it (the ruling of 05:08 on 2026-11-19).
- **T3's 100 km premise** fails for fragments of one breakup whose sets put them at their nodes (the ruling of 15:10).
- **"Every clock hour"** does not say whether a partial hour counts.
- **H7(b)'s eligibility,** "the fetcher not stopped", leaves the sets fetched in a slot that stopped the fetcher unmentioned.
- **The plan set no way to wake the lead** for its visits, so one was missed.
- **The verifier's 30 box CPU-minutes** were spent by one audit of its own sample.

## The lead's slips

1. Seven slips while drafting the plan, listed in the plan's last section.
2. **B0140's first booking** used a form the TimeSheet refuses (`+7h30m`), and a case-sensitive filter hid the refusal.
3. **The visit of 09:15 on 2026-11-19** was missed for want of a wake-up.
4. **The typed note for E0007** in the event history first said its set passed 30 days inside the window. The row's own ages showed otherwise, and the note was rewritten before the append.
5. **verifier-H's brief** said the stage takes `src\` from commit 1021414. `h_stage.py` takes it from 1646c96, and `src\` is identical at both.
6. **At the end,** a first process count by `pgrep` included the shell that ran it. A script sent by stdin counted 0.
7. **The draft of this record** said that DEBRIS-H's H6 overrun came before it asked, and gave the box folders' size from memory. Both were checked against `lead.md` and `du` and corrected before the commit.
8. **The ruling's evidence on foreign load** read the service log's UTC times as local: slot 4's check ran at 03:00, not 10:00. merge-check-H caught it. The conclusion stands on slot 7's check, and the 16:57 entry is corrected.
9. **This record's first version named two catalogue numbers** in its event-history lines, against the round's rule. The lead's rescan (`scan_debris_h.002.log`) caught them before the commit, and they are now seed indices (`scan_debris_h.003.log`).

## Cost

Tokens processed per agent, from the harness's transcripts since round DEBRIS-G closed (2026-11-17 12:32 -0700), by `dispatch\cost.py` at 17:04 (MEASURED):

| agent | model | calls | tokens processed |
|---|---|---|---|
| the lead | Opus 5.5 | 2,393 | 951,116,080 |
| plan-verifier-H | Sonnet 5.5 | 45 | 8,256,745 |
| DEBRIS-H | Opus 5.5 | 322 | 174,771,708 |
| verifier-H | Sonnet 5.5 | 87 | 12,976,249 |
| merge-check-H | Haiku 5.5 | 17 | 2,083,535 |
| total | | | 1,149,204,317 |

- **Cache reads** are 98.2% of the total, and the lead is 82.8% of it (COMPUTED).
  - The lead's line covers four days of visits in one long session, and ends at 17:04, before the commit.
  - Some of its records are the harness's own, marked `<synthetic>`.
- **The known-answer check:** for plan-verifier-H (267,817), DEBRIS-H (340,033) and merge-check-H (164,682), the last call's context equals the harness's count in the agent's last notice.
  - verifier-H's is 213,460 against the harness's 214,046, 586 apart. The gap is not explained.

## Where things are

- **This repository:**
  - `tests\`: the 23 files of this round;
  - `studies\`: `DEBRIS-H-plan.md`, `DEBRIS-H-build.md` (narrowed), `DEBRIS-H-report.md`, `DEBRIS-H-verifier-H-report.md` and this record;
  - `studies\debris-h\`: 149 files under its `MANIFEST.sha256`, the run's 91 aggregate copies in `box\` among them.
- **The ledger:**
  - `lead.md`, `DEBRIS-H.md` and `verifier-H.md`;
  - in `filed\`: plan-verifier-H's two reports, DEBRIS-H's two hand-offs and its report, verifier-H's report, the build report as reported, and merge-check-H's report;
  - in `debris-h\`: the test seed, the gates' box copies, the run's `r2\` (the seed, every checkpoint, the fetched files, the check tables, the step logs and both audits), and `phase2\h_analyze.001\`;
  - in `tools\`: `survey-h\`, `visits-h\` (every visit's scripts and outputs) and `scan-h\`;
  - in `events\`: the event history and its tools;
  - in `dispatch\`: the prompts, the briefs, their makers and the round's checks.
- **Each agent's scratch** is in `cft-debris-scratch\`, outside the repository.
- **On amd-arc-box,** in the home folder's `cft-debris-h\`: the run folders `r1` and `r2`, as the run left them, with the verifier's audit added.

## Open, for Logan

1. **The push** waits for Logan's word.
2. **The pacing.** On the box's CPUs, A256 at cft256 keeps real time only while the box is otherwise idle. Beside cft-fp256's nights it fell 37 to 45 minutes behind. A later round could carry fewer objects at cft256, serve native64 and check cft256 behind it, or hold the box.
3. **H6's box half.** The fit depends on the machine's C library. libcft's correctly rounded functions would remove that dependence (DEBRIS-H's finding).
4. **T3.** A swapped-identity control that holds for co-planar fragments is still to be written.
5. **CelesTrak:** timeouts at four slots, and HTTP 500s at S_H0 and slot 20. A later run could log each request's time to its first byte.
6. **The event history:** M1 decayed the object at seed index 1178 at 07:40 on 2026-11-21 (E0008). A SATCAT request would say whether the object itself has re-entered, and it needs Logan's yes.
7. **The box's run folders:** `cft-debris-h\r1` and `r2` hold about 4.0 GB (0.9 and 3.1 GB, MEASURED by `du` at 17:01 on 2026-11-21). Keep them, or the lead removes them on Logan's word.
