# Round DEBRIS-I: the record

The lead's record of round DEBRIS-I in cft-debris, 2026-11-23.
- **The week's plan** (ledger `plans\week-2026-11-23.md`), approved by Logan at 06:31 ("Approve the plan", with its six defaults), put DEBRIS-I first: M1's force model as a cft program on the CPU, then DEBRIS-J on a GPU.
- **The plan of record:** `DEBRIS-I-plan.md`, draft 3 (SHA-256 `9463559925630a2c5b45f53e04e9c07f0d974f81013d183c74ce61d50bf31fab`). Logan approved it at 08:04: "Approved for DEBRIS-I with the recommendations", that is, with its 11 defaults.
  - plan-verifier-I (Sonnet) checked draft 1 and re-checked draft 2.
  - The lead's checker, `check_plan_i.py`, passed draft 3 at 244 checks (logs 001 to 007, in the ledger).
- **Logan's words that shaped it** (2026-11-12): "*Yes if possible utilize cft programs, as well as generating certificates when able", and "*Certificate support can be built for but not implemented in order to still have gpu capability at the moment".
- **The ledger:** `C:\Users\logan\source\repos\cft-debris-ledger\` (`lead.md`, `DEBRIS-I.md` and `verifier-I.md`). It is outside this repository.
- **DEBRIS-K,** a study Logan asked for at 07:51, ran beside it on the desktop. Its record is its own.

## What ran

| agent | model | job | wall time | CPU | output |
|---|---|---|---|---|---|
| plan-verifier-I | Sonnet 5.5 | check the plan's draft 1, then re-check draft 2 | 15.8 min, then 1.5 min | small | its findings, in the plan's "What changed" sections; both reports in the ledger's `filed\` |
| DEBRIS-I | Opus 5.5 | phase 1: the generator, the driver, M1's side, the harness, the desktop's gates and part B, and the box's staging; phase 2: the box's records and the build report | 77.9 min (08:07 to 09:25), then 6.1 min (11:56 to 12:02) | 56.5 min by cycles, plus about 0.5; then about 0.3 | `tests\i_*`, `m1i.c`, `build_i.sh`, `i3_server.py`; `DEBRIS-I-build.md`; `debris-i\`; its report |
| the lead's box runs | - | box-build, box-i0, box-i3 and box-i5, from DEBRIS-I's hand-off | 09:26 to 11:54 | the box's | `debris-i\box\logs\`; `out\` in the ledger |
| verifier-I | Sonnet 5.5 | disconfirm the build, its gates and the box's records | 20.7 min, 12:07 to 12:28 | about 13.0 min by cycles | `DEBRIS-I-verifier-I-report.md` |
| merge-check-I | Haiku 5.5 | check the lead's narrowing | 1.7 min, 12:30 to 12:32 | runs of seconds, not measured | its report, in the ledger's `filed\` |

- **Delivery:** every prompt arrived identical to its filed copy (`check_prompts.py`, whose one-character control differed each time), and every agent ran on the model the plan named. DEBRIS-I's and verifier-I's test escalations reached the lead at once.
- **TimeSheet:**
  - each agent's desktop time was booked as a `notice`: B0253, B0255, B0273 and B0276;
  - the box runs went in B0262 (`shared`, I3) and B0263 (`sensitive`, I5), with box-build and box-i0 as short work;
  - each booking was released when its holder finished.

## What it found, after verification and narrowing

The build report is `DEBRIS-I-build.md`, changed at the merge in four places: one passage narrowed, two added and one corrected, each marked and listed in its section 9. Its results:
1. **M1's force model runs as a cft program** on libcft's software executor (MEASURED; reproduced by verifier-I). The model is M1's forces without radiation pressure: degree 7, Sun, Moon and drag with M1's 28 bands, rk4 at 15 s.
   - The program equals cftc's reference interpreter bit for bit at binary32, 64, 128 and 256, with 0 marks.
   - Its parts equal M1's kernels bit for bit at binary64, 128 and 256. The frame meets its bounds at every stage time sampled.
2. **On the box, the program tracks M1 within the plan's tolerances** over a day of 64 objects at three pairs of formats, with t exact at every boundary and 0 marks.
3. **The model gap** is a difference between two models, not an error: the program's forces against M1's full model give 343 m median and 2,312 m largest at 24 h. Degree 7 against 20 carries almost all of it. Radiation pressure carries 4 m.
4. **The rates,** on the box's 36 threads (MEASURED in the sensitive window):
   - At the same forces, the program at binary256 runs 2.6 to 2.9 times M1 at cft256.
   - Against M1's full model it runs 13.8 to 15.5 times, but most of that is the lighter model.
   - At degree 7 and binary256, real time on 36 workers holds about 59,700 objects, an extrapolation past the 2,304 run.
5. **Degree 8 also fits `sw:512`,** against the plan's expectation. **I6,** the degree-20 compile at `sw:2048`, is not determined.
6. **C13 failed as specified.** A frame form carrying its own centre extrapolates well, so its plant could not fail I3. The frame's test is I2(e).
7. **Part B,** the service's fixes for DEBRIS-H's B2 and B3 findings, passes on the desktop.

## Rulings and events

- **07:22 to 07:50:** drafts 1 to 3.
  - plan-verifier-I found no blocker and six defects in draft 1, all upheld.
  - Its re-check of draft 2 found one defect and four notes.
- **08:04:** Logan's approval. **08:07:** DEBRIS-I dispatched on Opus.
- **08:53:** DEBRIS-I's budget question. I6 was capped at 20 CPU-minutes, and its box route withdrawn, since cftc refuses exp without mpmath (the lead's slip).
- **09:16:** at 55.1 of 60 CPU-minutes, the lead allowed up to 3 more, to keep I4's tides.
- **09:25 to 09:27:** the phase-1 hand-off, filed; the box staged, with 304 files checked there.
- **The box runs:**
  - box-build: 8 checks, 0 failed;
  - box-i0: 43 checks, 0 failed;
  - box-i3: 2 checks, 0 failed, 104 runs, 09:32 to 10:07;
  - box-i5: 22 checks, 0 failed, 11:00 to 11:53, every run valid at the first try.
- **10:40 to 10:45:** cft-fp256's lead warned that its box gate would run into I5's window. The lead first asked it to finish, then took its plan to pause the gate. The gate ended by itself at 10:45 with a pass.
- **11:54:** the box's 792 files copied back and verified against the box's own hashes. One log's two home paths were rewritten to `<root>` in the repository's copy.
- **11:56:** DEBRIS-I resumed for phase 2. No box run marked a lane, so no redo was needed.
- **12:07 to 12:28:** verifier-I found no defect in ten attacks. It was allowed one run over the 5 CPU-minute line, with a 10-minute stop.
- **12:30: the merge.** Nothing was sent back. The frame's bound was narrowed beside verifier-I's sample. I3's frame sensitivity and the full-model ratios were added.
- **12:32: merge-check-I** confirmed the merge, with two points.
  - Two of the passages were additions, not narrowings.
  - One sentence of DEBRIS-I's stated C13's result backwards.

  Both were fixed in its terms, and the fixes were not checked again.

## What the plan got wrong

- **I6's box route:** cftc refuses a source holding exp without mpmath, and the box has none.
- **Degree 8** fits `sw:512`, against plan-verifier-I's arithmetic, which the plan took.
- **C13's plant was too small** for a frame form that carries its own centre.
- **The interpreter costs about 0.055 CPU-s a lane-step,** about 5 times the plan's figure.
- **plan-verifier-I's re-check** gave 2026-11-20 00:00 TDB as 34 days from the epoch; it is 35.

## The lead's slips

- **In drafting,** each listed in the plan's "The lead's slips so far":
  - the checker's first version, edited before it was kept;
  - draft 1's rate ESTIMATE, which did not follow from its basis;
  - the 24-step segments;
  - a patch that lost its backslashes.
- **I6's box route,** withdrawn at 08:53.
- **box-i0's launch:** `test ... && setsid ... &` made bash background the whole list, so the ssh call hung. The run was unharmed, and later launches test first.
- **B0263's extension** was announced to cft-fp256's lead before it was booked. It was refused, and a correction followed.
- **To Logan at 12:28,** the lead gave the full-model ratio, 14 to 15 times, without saying that most of it is the lighter model. The like-for-like figure is 2.6 to 2.9.
- **The merge's first version** called two added passages "narrowed". merge-check-I caught it.
- **verifier-I's brief:** its notes name three gaps. Attack 2 did not say that part (c) has six outputs, attack 3 did not give the lanes' order, and the staged folder holds no image manifests.

## Cost

Tokens processed per agent, from the harness's transcripts, by `dispatch\cost.py` (MEASURED, 12:33):

| agent | model | calls | tokens processed |
|---|---|---|---|
| plan-verifier-I | Sonnet 5.5 | 70 | 12,783,705 |
| DEBRIS-I | Opus 5.5 | 243 | 138,072,051 |
| verifier-I | Sonnet 5.5 | 103 | 15,875,638 |
| merge-check-I | Haiku 5.5 | 9 | 747,999 |
| the agents' total | | | 167,479,393 |
| the lead, from 07:00 | Opus 5.5 | 449 | 238,092,403 |

- **The lead's figure** runs from 07:00, when round I's planning began after the box clean-up, to 12:33.
  - It includes DEBRIS-K's lead work from 07:51, which DEBRIS-K's record counted from then, so the two records' lead figures overlap and must not be added.
  - It stops before this record was written.
- **The known-answer check,** the last call's context against the harness's own `subagent_tokens`:
  - exact for plan-verifier-I (282,351, its re-check), DEBRIS-I (886,462, its phase 2) and merge-check-I (101,457);
  - verifier-I within 0.5% (226,055 against 227,140), the cause not determined.
- Nearly all of every agent's tokens are cache reads.

## Where things are

**In this repository:**
- `studies\DEBRIS-I-plan.md` (draft 3, approved);
- `studies\DEBRIS-I-build.md` (the build report, narrowed at the merge);
- `studies\debris-i\`, 119 files under its `MANIFEST.sha256`, the box's five logs among them;
- `studies\DEBRIS-I-report.md` and `studies\DEBRIS-I-verifier-I-report.md`, filed verbatim;
- `tests\i_*`, `tests\m1i.c`, `tests\build_i.sh` and `tests\i3_server.py`;
- this record.

**In the ledger:**
- `lead.md`, `DEBRIS-I.md` and `verifier-I.md`;
- `filed\`: the build report as reported; the hand-off; DEBRIS-I's, verifier-I's, plan-verifier-I's two and merge-check-I's reports;
- `dispatch\`: the prompts, their makers, and the plan checker with its logs;
- `debris-i\`: the desktop's work, the staged folder, the box's records with the box's own hashes, phase 2's per-object tables, and `held\`;
- `tools\`: both cft-fp256 archives, and `scan-i\`, the lead's scan.

**Kept out of the repository:** every image and bank, which carry cft-fp256's routines; libcft's and M1's builds; per-object states and tables; Earth orientation values; the box's address.

## Open, for Logan

- **DEBRIS-J,** the week's GPU round, which inherits the images, the driver's loop and I3's boundary states. Its plan comes next.
- **I6,** the degree-20 compile, is not determined. It needs a longer desktop window, or mpmath on the box, which is an install.
- **Degree 8 fits,** so a degree-8 program is open, at about the same cost.
- **Pushing this round to the public repository.**
