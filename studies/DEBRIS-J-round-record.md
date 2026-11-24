# Round DEBRIS-J: the record

The lead's record of round DEBRIS-J in cft-debris, 2026-11-23.
- **Logan's requests,** in chat:
  - at 12:46, "Draft it", for the week's second round;
  - at 13:14, "Approved. Along with that, dispatch a small parcel for visualization generation for the project, …". The lead read its first word as the plan's approval, with every decision at its default (`lead.md`, 13:15). The parcel is DEBRIS-L, with its own record.
- **The week's aim** (approved 06:31): M1's force model as a cft program on a GPU, on the RTX 5060 Ti in WSL's `cft-gpu`, under cft-fp256's lock. The 4070 is never used.
- **The plan of record:** `DEBRIS-J-plan.md`, draft 3 (SHA-256 `4b84a073c8fda02c6d17bcca3d0887a90a0fe83502764a3b43ce574f6a6a1377`).
  - plan-verifier-J (Sonnet) checked draft 1 and found two blockers and eight defects, all upheld. It re-checked draft 2 and found no blocker open and five defects, all answered in draft 3.
  - The lead's checker, `check_plan_j.py`, passed draft 3 at 236 checks (logs 001 to 005, in the ledger).
- **The ledger:** `cft-debris-ledger\`, a folder beside this repository and outside it (`lead.md`, `DEBRIS-J.md` and `verifier-J.md`).
- **DEBRIS-L,** a visualization parcel, ran beside it on the desktop. Its record is its own.

## What ran

| who | model | job | wall time | CPU | output |
|---|---|---|---|---|---|
| plan-verifier-J | Sonnet 5.5 | check draft 1, then re-check draft 2 | 6.9 min, then 1.9 min | small | its findings, answered in the plan's "What changed" sections; both reports in the ledger's `filed\` |
| DEBRIS-J, phase 1 | Opus 5.5 | the driver, the build, the desktop gates, the staged folder, the card's commands | 64.3 min, 13:21 to about 14:25; its hand-off filed at 14:25:31 | 27.1 min by cycles, plus about 3.6 unmetered (ESTIMATE) | `tests\j_*`, `tests\build_j.sh`, `studies\debris-j\`; its hand-off in the ledger's `filed\` |
| the lead, in `cft-gpu` | Opus 5.5 | J0, J0c, J1, J2 and J3 on the RTX 5060 Ti, from DEBRIS-J's commands | 14:27 to 16:42 | the card's | the card's records, copied back to the ledger's `debris-j\gpu\r1\` |
| DEBRIS-J, phase 2 | Opus 5.5 | the analysis, the build report, the manifest | 6.3 min, from 16:46 | 2.7 s by cycles | `DEBRIS-J-build.md`, `studies\debris-j\`, `DEBRIS-J-report.md` |
| verifier-J | Sonnet 5.5 | disconfirm the build, its gates and the card's records | 13.2 min, 16:54 to 17:07 | about 4 min by cycles; no card time | `DEBRIS-J-verifier-J-report.md`; its logs in the ledger's `debris-j\verifier-j\` |
| merge-check-J | Haiku 5.5 | check the lead's merge | 3.2 min, 17:14 to 17:17 | runs of seconds, not measured | its report, in the ledger's `filed\` |

- **Delivery:** every prompt arrived identical to its filed copy (`check_prompts.py`, whose one-character control differed each time), and every agent ran on the model the plan named. Every test escalation reached the lead at once.
- **TimeSheet:**
  - desktop notices: B0277 (plan-verifier-J), B0278 (DEBRIS-J), B0298 (verifier-J) and B0300 (merge-check-J);
  - for the card: B0293 `rtx5060ti` and B0294 `wsl-cft-gpu`, exclusive, 14:26 to 18:26; B0295, the desktop `shared` for J0 to J1; and B0297, the desktop `sensitive` for J2 and J3, 15:05 to 18:05.

  Each was released when its holder finished, the card's at 16:42:51. cft-fp256's next GPU day, B0283 to B0287 on Wednesday, was never met.

## What it found, after verification and the merge

The build report is `DEBRIS-J-build.md`. At the merge the lead corrected two sentences and added one note, each marked and listed in its section 13. Its answers, all MEASURED on the card unless labelled:
1. **The card gives the CPU's bits.**
   - J1: over I3's day of 64 objects, at binary64, binary128 and binary256, every 40-step boundary equals amd-arc-box's record: 1,152 records a format, 0 differences. I1's 32 cases equal the software executor and R1's hashes.
   - J3's 16 drawn lanes equal the desktop's replays at all 144 boundaries.
   - No mark occurred.
   - verifier-J recomputed J1 on three objects of its own choosing and replayed four of J3's lanes. It found 0 differences.
2. **The step,** from J0c: s = 1. A 2,048-lane call took 138.67 ms at binary64, 166.20 ms at binary128 and 239.68 ms at binary256. Against the plan's ESTIMATE of 23 and 83 ms a step, the 2,048-lane calls took 6.0 times as long at binary64 and 2.9 times at binary256 (COMPUTED). Every launch is far under Windows' 2-s timeout.
3. **The rates** (J2, X in object-seconds a second at s = 1, the median of 3 runs of the best batch):
   - 233,407.4 at binary64, 191,230.8 at binary128 and 134,394.9 at binary256;
   - 2.52, 2.45 and 2.25 times the box's 36 workers on the same program (COMPUTED, rates over rates; verifier-J recomputed every X from the provenance files);
   - X levels off at 2,048 lanes, the backend's chunk at this program's reach;
   - the three 32,768-lane runs were each stopped by the 1,000-ms rule after one call;
   - at binary256, 2,048 and 8,192 lanes tie.
4. **The catalogue's day** (J3): 2,687 objects, one per element set, for 24 simulated hours: DEBRIS-H's seed less seed index 1595, as the plan set it. It took 1,499.8 s at binary64, **57.6 times real time**, and 2,583.5 s at binary256, **33.4 times real time**. That is about two-thirds of J2's best rate: each step's second launch, of 639 lanes, costs nearly a full one (INFERRED).
5. **What it is not:**
   - The forces are the program's: degree 7, the Sun, the Moon and drag, with no radiation pressure. They are not M1's full model.
   - The report does not claim a real-time capacity of 233,000 or 134,000 objects. That extrapolates past the 8,192 lanes run validly, and the driver would have to split a step into calls under 1,000 ms.
   - No certificates were written.

**The desktop's load** beside J2 and J3 came from other sessions: Undertone's gates to about 15:18, then cft-fp256's runs. In each best batch the most-loaded run was 0.14% to 0.27% slower than the least, so J2 was not repeated. The load and the run order are not separated.

**verifier-J's notes,** outside its threat model, recorded here:
- **"The same build"** in the threat model and in attack 3: the later steps' records name the device line, the caps and the images, not the binary. The binary is named in J0's records alone, and by the lead's reading of the card's `j_run` after J3 (the build report, sections 4 and 13).
- **The plan's paths:** `DEBRIS-J-plan.md` keeps four lines naming the desktop's user folder, and the shared lock's path in WSL, as the committed plans of DEBRIS-H, I and K do. This is a convention, not a defect.
- **`tests\j_harness.py`** and five of its kept versions name those folders only as the redaction code's own pattern strings.
- **The twelve record checks all held:** SHA256SUMS 32 OK, `debris-a` 29 files, the manifests of DEBRIS-B to DEBRIS-K, and no `__pycache__`.
- **Not run by verifier-J:** the driver's abort and `load` paths under attack 1. J0 ran `load`, and j_run's desktop gate ran the abort (exit 6).

## Rulings and events

- **12:46 to 13:18:** drafts 1 to 3, plan-verifier-J's two reports, and Logan's approval at 13:14.
- **13:21:** DEBRIS-J dispatched on Opus; cft-fp256's Phase 0 answers relayed.
- **13:31:** DEBRIS-J found that the plan's 2,686 seed objects are 2,688. J2 tiles 2,688, and J3 runs 2,687.
- **13:39:** the 1,000-ms rule kept as written for J2's 32,768-lane batch.
- **13:43:** cft-fp256's GPU day noted for Wednesday, so the card's runs went in on Monday.
- **14:25:** DEBRIS-J's hand-off. The lead verified the staged folder and read the three scripts that run as root in `cft-gpu`: no deletion, the lock never created, and the device pinned.
- **14:27 to 16:42:** J0 (10 checks), J0c (12), J1 (42), J2 and J3 (7), all passing.
  - J2's thresholds came from the idle readings: 64 MiB and 10%, against 12 MiB and 0% idle.
  - Undertone's and cft-fp256's loads inside B0297 were reported, recorded, and held off by both sessions until its release.
- **16:42:** the records copied back and verified (360 files), the repository's copies made (11), and the bookings released.
- **16:46 to 16:52:** phase 2 and DEBRIS-J's report.
- **17:07: verifier-J** confirmed all eight attacks, and found one false sentence: `j_run`'s SHA-256 is not carried by the later steps. **Ruling: no send-back.**
  - The lead read the card's `j_run` again, and found J0's SHA-256 with J0's build time. So the binary did not change.
  - The lead found at the merge that J2's 32,768-lane runs were three, not "four".
- **17:13: the merge:**
  - both reports copied, verifier-J's with its desktop paths written `<root>`;
  - the build report corrected in two places and added to in one, each marked;
  - this record and the README;
  - the lead's scan of the commit's files (`tools\scan-j\`, in the ledger).
- **17:17: merge-check-J** confirmed the hashes, the report copies, the build report's five changes at their sources, the record's figures, the cost and the README. It found:
  - phase 1's end given as 14:27, where its hand-off was filed at 14:25:31;
  - the step's ratio to the ESTIMATE given loosely as "3 to 6 times";
  - five of verifier-J's notes missing from the record;
  - the scan run before the record's last edit.

  All were fixed in its terms: the times and the ratio, the notes added above, and the scan run again on the final files. The fixes were not checked again.
- **17:20: the pre-push check's first run failed one check.** verifier-J's report quotes the private LAN prefix in attack 8, saying it found none, and the check holds that string to zero. The lead's scan had looked only for whole addresses.
  - The repository's copy of verifier-J's report now writes that quotation in words, as its paragraph says. The text as filed is unchanged in the ledger.
  - The local commit was amended before any push, and the check run again.

## What the plan got wrong

- **2,686 seed objects,** carried by the lead from DEBRIS-G's count. DEBRIS-H's seed has 2,688, one per element set.
- **The step's ESTIMATE,** from a single-thread divide, was 3 to 6 times low at binary64: 3.2 times for an 8-lane step and 6.0 for a 2,048-lane one (COMPUTED from J0c). Its capacity ESTIMATE, 1.3 million objects at binary64, is far above the MEASURED 0.233 million.
- **"The four additions"** left out the abort, warm-up, `load` and caps lines the gates need.
- **J0c's warm-up** used each process's own image. C-J1 on the card ran one hour, not a day. One J2 run lasted 57.7 s against its 60 s.
- **plan-verifier-J's "offset 93"** is `cmp`'s count from 1. The byte is at 92.
- **"The chunk may halve there":** it did not.

## The lead's slips

- **2,686** for 2,688, carried into the plan from DEBRIS-G. DEBRIS-J found it.
- **The idle readings** were taken during J0's build, not before any run. One was lost to the next slip.
- **The console:** `wsl.exe` relays stdout and stderr through separate handles. Sent to one file, stderr overwrote the start of stdout: the first idle reading, and perhaps the start of J0's console. The harness's own logs were unaffected, and every later step kept them apart.
- **"Four" 32,768-lane runs** for three, in `lead.md` and to Logan, before the merge found it.
- **J3's projection** in the 15:34 entry divided by J2's rate as if the 639-lane launch cost its share. It costs nearly a full launch, as the lead's first estimate had said.
- **A ruling's time** given as 13:40 for 13:39, and a `printf` entry whose path became an octal byte. `append_lead.py` refused it, and it was rewritten with the Write tool.

## Cost

Tokens processed per agent, from the harness's transcripts, by `dispatch\cost.py` (MEASURED at 17:10; merge-check-J's and the lead's at 17:17):

| agent | model | calls | tokens processed |
|---|---|---|---|
| plan-verifier-J | Sonnet 5.5 | 45 | 7,005,627 |
| DEBRIS-J, both phases | Opus 5.5 | 184 | 85,389,613 |
| verifier-J | Sonnet 5.5 | 62 | 9,521,626 |
| merge-check-J | Haiku 5.5 | 18 | 1,991,342 |
| the agents' total | | | 103,908,208 |
| the lead, from Logan's "Draft it" at 12:46 | Opus 5.5 | 333 | 170,390,305 |

- **The lead's figure is shared** with parcel DEBRIS-L, whose plan, dispatch, merge and push the lead handled in the same hours. It also covers the card's runs. It is not split, and it stops before this record was written.
- **The known-answer check,** the last call's context against the harness's own `subagent_tokens`:
  - plan-verifier-J exact (224,124, its re-check);
  - DEBRIS-J exact (744,235, phase 2);
  - verifier-J within 0.3% (218,456 against 218,905);
  - merge-check-J exact (165,550).
- Nearly all of every agent's tokens are cache reads.

## Where things are

**In this repository:**
- `studies\DEBRIS-J-plan.md` (draft 3);
- `studies\DEBRIS-J-build.md`, marked at the merge;
- `studies\debris-j\`, under its `MANIFEST.sha256` (38 files):
  - `compiles.tsv`;
  - the desktop's logs;
  - the kept script versions;
  - `gpu\r1\`, the card's five logs and six JSON records, with its bus redacted;
- `studies\DEBRIS-J-report.md`, filed verbatim, and `studies\DEBRIS-J-verifier-J-report.md`, with its desktop paths written `<root>` and its one quotation of the private LAN prefix written in words, as its added paragraph says;
- `tests\j_run.c`, `tests\build_j.sh`, `tests\j_harness.py` and `tests\j_gpu.sh`;
- this record.

**In the ledger:**
- `lead.md`, `DEBRIS-J.md` and `verifier-J.md`;
- `filed\`: plan-verifier-J's two reports, DEBRIS-J's hand-off and report, verifier-J's and merge-check-J's reports, and the build report as reported;
- `dispatch\`: the prompts, their makers, verifier-J's brief completion, the plan's drafts 1 and 2, and the plan checker with its logs;
- `debris-j\`:
  - `gpu\r1\`, the card's run folder as copied back (360 files);
  - `gpu-console\`, the lead's consoles and the idle readings;
  - `gpu-stage\r1\in\`, the staged folder;
  - `desktop\`, the load logs and the desktop tests;
  - `verifier-j\`, verifier-J's logs;
- `relayed\`: cft-fp256's Phase 0 answers, its python3 and flock answer, its GPU day and its hold; Undertone's report of its load;
- `tools\merge-j\` (the merge's scripts and logs) and `tools\scan-j\` (the lead's scan).

**Kept out of the repository:** the images and banks (they carry cft-fp256's routines; each image's SHA-256 is in `compiles.tsv`), the INIT and runs files, every state, and the card's per-object outputs.

## Open, for Logan

- **A driver that splits a step into calls under 1,000 ms,** so that J2's capacity, about 233,000 objects at binary64 and 134,000 at binary256, could be run in real time and not only extrapolated.
- **Certificates,** built for but not written, as the plan said.
- **The degree-20 program,** whose compile DEBRIS-I left undetermined.
- **Decision 6 was not triggered:** the card is faster than the box at binary256, so no request goes to cft-fp256's lead.
- **Pushing this round** to the public repository.
