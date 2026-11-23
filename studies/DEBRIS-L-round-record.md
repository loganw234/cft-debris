# Parcel DEBRIS-L: the record

The lead's record of parcel DEBRIS-L in cft-debris, 2026-11-23.
- **Logan's request,** in chat at 13:14, with his approval of DEBRIS-J's plan: "Approved. Along with that, dispatch a small parcel for visualization generation for the project, using the data to create screenshots, videos or live displays if desired. Doesn't have to be anything fancy to start, just something to give the project a visual presentation surface". The lead read his word to dispatch as the parcel's approval, with every decision at its default (`lead.md`, 13:15).
- **The plan of record:** `DEBRIS-L-plan.md`, draft 2 (SHA-256 `63722769e87fc183be1d1fc1acd2ebedd4e54a8753bb5803d689974f4f68b539`).
  - plan-verifier-L (Sonnet) checked draft 1 and found no blocker. The lead upheld its three defects and its findings on the gates, except one group's count (it gave 581; the file has 582).
  - The lead's checker, `check_plan_l.py`, passed draft 2 at 67 checks (logs 001 to 003, in the ledger).
- **The ledger:** `cft-debris-ledger\`, a folder beside this repository and outside it (`lead.md`, `DEBRIS-L.md` and `verifier-L.md`).
- **DEBRIS-J,** a build round, ran beside it on the desktop. Its record is its own.

## What ran

| agent | model | job | wall time | CPU | output |
|---|---|---|---|---|---|
| plan-verifier-L | Sonnet 5.5 | check the plan's draft 1 | 3.0 min, from 13:24 | small | its findings, answered in the plan's "What changed from draft 1"; its report in the ledger's `filed\` |
| DEBRIS-L | Sonnet 5.5 | the code, the media, the gates and the report | 14.6 min, 13:37 to 13:51 | about 190 s by cycles, its own count | `tests\l_*.py`, `studies\debris-l\`, `DEBRIS-L-report.md`; the media in the ledger's `debris-l\` |
| verifier-L | Haiku 5.5 | disconfirm DEBRIS-L's media and gates | 3.3 min, 13:57 to 14:00 | not stated | `DEBRIS-L-verifier-L-report.md`; its logs in the ledger's `debris-l\verifier-l\` |
| merge-check-L | Haiku 5.5 | check the lead's merge | 3.5 min, 14:09 to 14:13 | runs of seconds, not measured | its report, in the ledger's `filed\` |

- **Delivery:** every prompt arrived identical to its filed copy (`check_prompts.py`, whose one-character control differed each time), and every agent ran on the model the plan named. DEBRIS-L's and verifier-L's test escalations reached the lead at once.
- **TimeSheet:** each agent's time was booked as a desktop `notice`: B0280, B0281, B0290 and B0291. Nothing was timed, so no `sensitive` window was booked. Each notice was released when its holder finished.

## What it made, after verification

**The media,** kept in the ledger (decision 2), each with a sidecar naming the SHA-256 of its data and of the scripts that drew it. One picture, both views at the start, is also the README's, with its sidecar, in `studies\debris-l\readme\`: decision 2 (b), on Logan's word at 15:42 (see the last section).
- **Screenshots,** 1,280 × 720: both views at the start, T_s (2026-11-18 22:50:00 TDB), and 3 hours later; the top view and the edge-on view at the start.
- **A video:** 181 frames, one a minute from T_s for 3 hours, at 30 frames a second, about 6 s; h264, 1,280 × 720.
- **A live display:** one HTML file of 3.9 MB, its data inline (positions rounded to 1 km, as 16-bit integers). verifier-L found no network reference in it.

**What they show:** the 2,688 objects of DEBRIS-H's four groups: 1,991 Fengyun-1C debris, 582 Cosmos 2251 debris, 109 Iridium 33 debris and 6 stations.
- The positions are M1's propagation of DEBRIS-H's seed at native64, by `m1f prop` with DEBRIS-H's frame table. They are not observations, and each picture says so.
- The views are inertial, from above the North Pole and edge-on, around the Earth's disc. No map is drawn.
- At the start, about 1,780 objects are visible from above the pole and 2,170 edge-on (MEASURED by DEBRIS-L; verifier-L counted 1,778 and 2,167). The rest are behind the Earth's disc or, for a few, outside the frame's ±8,000 km.
- The largest coordinate over all frames is 9,324.6 km, at frame 52 (COMPUTED by the lead from the states).

**The results panel,** in this repository's `studies\debris-l\panel\`: four charts drawn from this repository's committed records, and `panel_table.tsv`, which gives each of their 29 numbers with its source file, line and cell:
- DEBRIS-G's real-time capacity at 36 threads, by number kind;
- DEBRIS-I's program against M1 at the program's forces, by format;
- DEBRIS-H's median miss against CelesTrak, by horizon;
- DEBRIS-K's pilot median misses, by variant.

**The gates,** each with its control, all pass (MEASURED, DEBRIS-L's logs): V0, the PNG writer (5 checks); V1, the positions (4); V2, the propagation (8); V3, the numbers and the charts (12); V4, the repository scan (31). None of verifier-L's attacks succeeded:
- V1 re-run on five objects of its own choosing, written down before its run;
- V3 re-run on all 29 numbers;
- the pictures and the video's first and last frames, looked at against their captions;
- its own scan of the new files, and the manifest;
- each control read for whether it can fail.

**Limits, from the verification and the merge:**
1. **V2's control asserts** that the changed object's states differ in at least one frame. Its log records 180 of 180. It checks four other objects for no change, not all 2,687.
2. **V4's catalogue rule knows only the numbers in the seed and the downloads' snapshots.** verifier-L's own scan, with a five-digit rule, found none.
3. **A cosmetic defect:** in the two single-view screenshots, the view's label sits between the legend and the population, and the top of the ring of objects is drawn over it. verifier-L held that part of the legend is hard to read. The lead, reading `shot_top_k000.png`, found the legend clear.
4. **Two logs carry the number 001 for V4's trial run.** The first failed on the scanner's own plant strings, and is kept with its script in the ledger's `debris-l\superseded\`. The second is `studies\debris-l\logs\v4_scan_trial.001.log`. No log was overwritten.
5. **Not checked:**
   - the video and the live display, played in a browser. DEBRIS-L ran the display's script in node against a stub canvas, outside any gate;
   - the video's frames after the first, against their PNG files' hashes;
   - the charts' text, glyph by glyph;
   - the propagation, run again: verifier-L did not run `m1f`.

## Rulings and events

- **13:15:** the parcel named DEBRIS-L, to be dispatched after a plan-verifier.
- **13:24 to 13:31:** drafts 1 and 2, with plan-verifier-L's report between them.
- **13:37:** DEBRIS-L dispatched on Sonnet.
- **13:51:** DEBRIS-L's report.
- **13:55:** the lead's first look. M1's states and the groups were copied from DEBRIS-L's scratch to the ledger, so that verifier-L could read them there.
- **13:57:** verifier-L dispatched on Haiku, with its brief completed from DEBRIS-L's report.
- **14:03: the ruling.** No answer was false, so nothing was sent back.
- **14:08: the merge:**
  - the two reports copied into `studies\`, each with its desktop paths written `<root>`;
  - this record and the README;
  - the lead's scan of the commit's files (`tools\scan-l\`, in the ledger).
- **14:13: merge-check-L** confirmed the hashes, the copies' differences, the record's figures and times at their sources (with 9,324.6 km recomputed), the cost, the README's other lines and the scan's log. It found five points:
  - the parcel's approval given as Logan's words, where it is the lead's reading of them;
  - the reports' word counts given without their method;
  - limit 5 missing that `m1f` was not run again;
  - limit 3 missing verifier-L's view that part of the legend is hard to read;
  - the README's row giving the media's place as settled while decision 2 is open.

  All were fixed in its terms, and the fixes were not checked again.

## What the plan got wrong

- **It pointed to `tests\i_lib.py` for the CPU count.** DEBRIS-L used `k_lib`'s counter, as `k_build.py` does.
- **Its estimate for `prop`,** a factor of 1 to 5 slower than G4's rate, was cautious. DEBRIS-L's whole run used about 190 s of CPU.
- **V4's scope holds the scanner itself,** so its plant strings had to be written in pieces.
- **It did not name the screenshots' frames.** DEBRIS-L chose the start and frame 180.
- **Its V2 control,** "must change that object's states at k ≥ 1, and no other object's", fixed no count. The code asserts at least one changed frame and checks four other objects.

## The lead's slips

- **Draft 2 was written over draft 1** before a copy was kept. Draft 1 was recovered exactly from the lead's session transcript, its SHA-256 equal to the one recorded, and is kept read-only in the ledger.
- **The lead's first look called a chart's "see table" a defect.** It is not: the subtitle points to the source's tables, which hold the counts. It was withdrawn at 14:03.
- **The 14:03 entry in `lead.md` dates the first look 13:54.** Its heading is 13:55.
- **The backslash trap:** a shell search of the reports for paths failed on its own pattern, and was redone in a script written with the Write tool.

## The agents' slips

- **verifier-L typed two of its ledger headings' times,** against its file's rule that they come from `date`: 14:03 on an entry written at 13:57:43, and 14:25 on one written by about 14:00. The facts under them hold. Its transcript shows that it wrote down its five objects before it ran V1.
- **DEBRIS-L's report ran slightly long.** Counting only tokens that hold a letter or a digit, it has 707 words against its 700, and verifier-L's has 596 against its 600, within it (COMPUTED). `file_report.py`'s whitespace count, which also counts table rules and list marks, gives 775 and 618; the lead first gave those against the limits.
- **DEBRIS-L tried to open the live display** in the desktop app's browser pane, which refused the `file://` page. This was not outside its brief.

## Cost

Tokens processed per agent, from the harness's transcripts, by `dispatch\cost.py` (MEASURED, 14:14):

| agent | model | calls | tokens processed |
|---|---|---|---|
| plan-verifier-L | Sonnet 5.5 | 24 | 2,215,727 |
| DEBRIS-L | Sonnet 5.5 | 58 | 9,053,702 |
| verifier-L | Haiku 5.5 | 35 | 3,372,946 |
| merge-check-L | Haiku 5.5 | 19 | 2,024,538 |
| the agents' total | | | 16,666,913 |
| the lead, from Logan's request at 13:14 | Opus 5.5 | 144 | 63,218,316 |

- **The lead's figure is shared** with round DEBRIS-J, whose plan, dispatch and questions the lead handled in the same hours. It is not split between them, and it stops before this record was written.
- **The known-answer check,** the last call's context against the harness's own `subagent_tokens`:
  - plan-verifier-L within 0.2% (115,843 against 115,999);
  - DEBRIS-L within 0.5% (232,455 against 233,559);
  - verifier-L within 0.1% (135,686 against 135,721);
  - merge-check-L exact (152,312).
- Nearly all of every agent's tokens are cache reads.

## Where things are

**In this repository:**
- `studies\DEBRIS-L-plan.md` (draft 2);
- `studies\debris-l\`, under its `MANIFEST.sha256`:
  - `panel\`: the four charts, their sidecars and `panel_table.tsv`;
  - `readme\`: the README's picture and its sidecar, added by the lead on Logan's word;
  - `logs\`: the gates' aggregate logs;
  - `scripts\`: the script versions that wrote logs;
- `studies\DEBRIS-L-report.md` and `studies\DEBRIS-L-verifier-L-report.md`, each with its desktop paths written `<root>`, as its added paragraph says;
- `tests\l_*.py`, DEBRIS-L's code;
- this record.

**In the ledger:**
- `lead.md`, `DEBRIS-L.md` and `verifier-L.md`;
- `filed\`: DEBRIS-L's, verifier-L's, plan-verifier-L's and merge-check-L's reports;
- `dispatch\`: the prompts, their makers, verifier-L's brief completion, the plan's draft 1, and the plan checker with its logs;
- `debris-l\`:
  - the screenshots, the video and the live display, each with its sidecar;
  - the gates' per-object logs;
  - `data\`, M1's states for the 181 frames and the groups;
  - `verifier-l\`, verifier-L's logs;
  - `superseded\`;
- `tools\scan-l\` (the lead's scan) and `tools\merge-l\` (the merge's scripts and logs).

**Kept out of the repository:** the video, the live display and the population's other pictures, M1's states, and every per-object line of the gates' logs.

## Open, for Logan

- **The cosmetic label** in the two single-view screenshots, for a later pass if wanted.

## Decided after the first commit

Logan, in chat at 15:42, after he had seen the media: "Clear to push and picture is fine in the readme".
- **Decision 2 is (b).** The lead copied `shot_both_k000.png`, both views at the start, and its sidecar from the ledger to `studies\debris-l\readme\`. The picture's SHA-256 equals its sidecar's. `MANIFEST.sha256` now lists 38 files, its 36 old lines unchanged. The README shows the picture under its opening paragraph, with a caption saying the positions are M1's propagation of DEBRIS-H's seed, not observations.
- **The push:** this parcel's two commits, the first and the picture's, go to the public repository after the pre-push check.
