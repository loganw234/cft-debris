# Study DEBRIS-K: the record

The lead's record of study DEBRIS-K in cft-debris, 2026-11-23.
- **Logan's request,** in chat at 07:51, while DEBRIS-I's plan waited for his answer: "While the others work, dispatch a study in the feasibility of this being utilized to track a small subset of objects to provide more thorough and comprehensive forecast predictions, the first set could be LEO objects which are likely to decay within the prediction windows, we could utilize the various predictions to refine the models accuracy over time depending on the findings." His word to dispatch was the study's approval, with every decision at its default.
- **The plan of record:** `DEBRIS-K-plan.md`, draft 3 (SHA-256 `b05a736e392dd94d95ca8f2b1d70b2042d0f2d16f1e7dd624840f97c1717066a`).
  - plan-verifier-K (Sonnet) checked draft 1 and re-checked draft 2. The lead's checker, `check_plan_k.py`, passed draft 3 at 134 checks (logs 001 to 005, in the ledger).
  - The repository's copy differs from draft 3 only on the two lines that gave one per-object value, removed at the merge (SHA-256 `581e1bc0a9c6c79a61b9c6144ef65e842f36baef8bc10cf5840706f0e21f2683`). Draft 3 as approved is held in the ledger's `debris-k\held\`.
- **The ledger:** `C:\Users\logan\source\repos\cft-debris-ledger\` (`lead.md`, `DEBRIS-K.md` and `verifier-K.md`). It is outside this repository.
- **DEBRIS-I,** a build round, ran beside it, on the desktop and then on the box. Its record is its own.

## What ran

| agent | model | job | wall time | CPU | output |
|---|---|---|---|---|---|
| plan-verifier-K | Sonnet 5.5 | check the plan's draft 1, then re-check draft 2 | 5.3 min, then 1.1 min | small | its findings, in the plan's "What changed" sections; both reports in the ledger's `filed\` |
| DEBRIS-K | Opus 5.5 | the study, Q1 to Q7, with the pilot hindcast | 58 min, 08:20 to 09:18 | 15.7 min by cycles | `DEBRIS-K-study.md`, `debris-k\`, `DEBRIS-K-report.md`; per-object outputs in the ledger's `debris-k\` |
| verifier-K | Sonnet 5.5 | disconfirm DEBRIS-K | 7.4 min, 09:23 to 09:30 | about 50 s by cycles | `DEBRIS-K-verifier-K-report.md` |
| merge-check-K | Haiku 5.5 | check the lead's merge | 6.0 min, 09:54 to 10:00 | runs of seconds, not measured | its report, in the ledger's `filed\` |

- **Delivery:** every prompt arrived identical to its filed copy (`check_prompts.py`, whose one-character control differed each time), and every agent ran on the model the plan named. DEBRIS-K's and verifier-K's test escalations reached the lead at once.
- **TimeSheet:** each agent's time was booked as a desktop `notice`: B0254, B0258, B0261 and B0265. Nothing was timed, so no `sensitive` window was booked. Each notice was released when its holder finished.

## What it found, after verification and narrowing

The study is `DEBRIS-K-study.md`, narrowed at the merge in 24 passages, each marked and listed in its last section. Its answer: **feasible on the CPU as a measurement campaign of tens of objects, not yet as a forecast that beats the catalogue's own.**
1. **Compute is not the limit** (COMPUTED from DEBRIS-G's rates; reproduced by verifier-K). At native64, 100 objects × 100 ensemble members, re-forecast at every new set over a 30-day window, need about 0.36 of one box worker. At M1's cft256, 10 objects with one member each need about 7.3. Both assume 1.5 new sets a day an object; counting each orbit determination once, the pilot's rate is 1.3, and the costs about 13% lower.
2. **On the pilot's 16 low-perigee objects, nothing beat (B'),** SGP4 from the same latest set (MEASURED; every statistic recomputed by verifier-K). Over 130 checks, the median misses are (B') 4.33 km, (R) 6.53, (H) 6.65 on its 60, and (C) 8.27. Counted once per orbit determination (the lead's recount, checked by merge-check-K), they are 4.82, 6.86, 7.33 on 56, and 9.19, over 112 checks. From 1 to 2 days (R) and (H) are level with (B') in their medians only.
3. **No learning curve** in (H), by sets or by determinations.
4. **M1's decay times are reproducible, but have nothing to be scored against.** Seed index 1595's reconstruction decays 4.63 h after SATCAT's date; index 1178 has no record.
5. **Q1's rule** finds about five objects in DEBRIS-H's four groups likely to decay within 30 days, so a watch of tens of objects needs the whole catalogue.
6. **The recommendation,** labelled as one: a decay watch at native64 with an ensemble, scored against SATCAT's dates and Space-Track's TIP windows, with cft256 as a one-member audit. It needs four of Logan's decisions on data. Without SATCAT's dates the study recommends against building it.
7. **A finding about CelesTrak's files,** made by DEBRIS-K, counted run-wide by the lead, and corrected by the lead after verifier-K. In DEBRIS-H's 72 hours, 3,074 rows on 808 objects carry an epoch earlier than a row already fetched. Every one is exactly one 1e-8-day unit earlier, with BSTAR and eccentricity differing in their low digits. They are most likely one orbit determination written two ways (INFERRED), not older sets.

## Rulings and events

- **07:55:** the study named DEBRIS-K, to be dispatched without asking again, after a plan-verifier.
- **08:02 to 08:18:** drafts 1 to 3. plan-verifier-K found two blockers and eleven defects in draft 1, all upheld, and three defects in draft 2, all answered.
- **08:20:** DEBRIS-K dispatched on Opus.
- **08:47 and 08:56:** DEBRIS-K's notices before (H)'s fits and before (C). Its control K2 failed as specified.
- **09:02 and 09:04:** DEBRIS-K's finding that CelesTrak's files "sometimes carry an older set", and the lead's run-wide count. The lead read the rows as older sets, and told Logan so.
- **09:21 and 09:23:** DEBRIS-K's report filed; verifier-K dispatched on Sonnet.
- **09:32:** verifier-K found one defect, per-object orbit values by seed index in three logs, and confirmed its seven other attacks.
- **09:33:** the lead's correction: every such row is one 1e-8-day unit earlier.
- **09:53: the merge.** No answer was false, so nothing was sent back.
  - The defect was fixed: the three logs' originals are held in the ledger, and their per-object lines rewritten in the repository.
  - The lead found that six of the pilot's kept sets repeat a determination. It recounted the headline figures and narrowed the study in 24 places.
- **10:01: merge-check-K** confirmed the hashes, the diffs, the re-runs, the six pairs, the recount and the marks. It found five points:
  - 1178's perigee left as "near 400 km";
  - (C)'s two medians under a day given as one;
  - "13% high" where the rows are 15% high;
  - the header's account of the plan's two lines;
  - four of verifier-K's "did not do" items missing from the notes.

  All were fixed in its terms, and the fixes were not checked again.

## What the plan got wrong

- **Its rule for the sets,** "A set whose epoch is no later than the object's previous set's is skipped and counted", kept a determination's later form as a new set six times. The two forms were not known when the lead wrote it.
- **It did not say how forecasts that repeat each other count.** DEBRIS-K fixed its own rule before the data: one distinct (object, set used, reference).
- **Its control K2 assumed DEBRIS-H's check tables used the newest set fetched.** At slot 18 DEBRIS-H checked the other form of 191 sets.
- **It carried one per-object value,** seed index 1178's fitted `bc`, in two places. Both were removed at the merge.
- **Its estimate for (H),** 6 to 38 CPU-minutes, was high: (H) took 4.0.

## The lead's slips

- **The step-backs read as older sets,** at 09:04, and told to Logan. verifier-K's note on K2's 0.9 ms led the lead to measure them. The correction is in `lead.md` at 09:33, and the lead tells Logan.
- **verifier-K's brief** called K2's unmatched rows "older sets". It also used "conflict" for Space-Track's two statements, which the page leaves unreconciled.
- **verifier-K's prompt, first generation:** the maker ran in the same command as the booking, so the prompt held placeholders for the booking. It is kept as `verifier-K-prompt.placeholder-slip.md`, and was never sent.
- **The merge's first narrowing** left 1178's perigee as "near 400 km" and wrote "13% high" for 15%. The lead's 09:53 entry said the study held no other per-object value. merge-check-K found both.
- **The backslash trap,** twice in this study and four times today in all. A heredoc patch put a CR and an FF into a path in draft 3, which a byte check caught before dispatch. A one-line Python check at the merge failed at once. Scripts holding backslashes are written with the Write tool.
- **The cost's lower ends** in draft 3 were written 7 and 17; they are 6 and 16. The checker caught the total.
- **The recount's first version** failed on DEBRIS-H's own rows, whose reference is an epoch, not a set. Its versions are kept by hash.

## Cost

Tokens processed per agent, from the harness's transcripts, by `dispatch\cost.py` (MEASURED, 10:03):

| agent | model | calls | tokens processed |
|---|---|---|---|
| plan-verifier-K | Sonnet 5.5 | 26 | 2,985,991 |
| DEBRIS-K | Opus 5.5 | 174 | 81,270,552 |
| verifier-K | Sonnet 5.5 | 55 | 7,965,790 |
| merge-check-K | Haiku 5.5 | 37 | 5,771,648 |
| the agents' total | | | 97,993,981 |
| the lead, from Logan's request at 07:51 | Opus 5.5 | 238 | 138,975,155 |

- **The lead's figure is shared** with round DEBRIS-I, whose plan, dispatch and box runs the lead ran in the same hours. It is not split between them, and it stops before this record was written.
- **The known-answer check,** the last call's context against the harness's own `subagent_tokens`:
  - exact for plan-verifier-K (158,940, its re-check) and merge-check-K (236,054);
  - verifier-K within 0.2% (215,860 against 216,185);
  - DEBRIS-K within 0.3% (712,940 against 714,762).

  The causes of the two gaps are not determined.
- Nearly all of every agent's tokens are cache reads.

## Where things are

**In this repository:**
- `studies\DEBRIS-K-plan.md` (draft 3, one per-object value removed);
- `studies\DEBRIS-K-study.md` (the study, narrowed at the merge);
- `studies\debris-k\`, 37 files under its `MANIFEST.sha256`;
- `studies\DEBRIS-K-report.md`, filed verbatim;
- `studies\DEBRIS-K-verifier-K-report.md`, whose two quotations of per-object values are replaced, as its added paragraph says;
- `tests\k_*`, DEBRIS-K's code;
- this record.

**In the ledger:**
- `lead.md`, `DEBRIS-K.md` and `verifier-K.md`;
- `filed\`: the study as reported; DEBRIS-K's, verifier-K's, plan-verifier-K's two and merge-check-K's reports;
- `dispatch\`: the prompts, their makers, and the plan checker with its logs;
- `debris-k\`: the per-object outputs, and `held\`, the originals of the three logs and of draft 3;
- `tools\scan-k\` (the lead's scan of DEBRIS-K's files), `tools\scan-h\` (the run-wide count and the one-unit measurement) and `tools\merge-k\` (the merge's scripts and logs).

**Kept out of the repository:** catalogue numbers, element sets, states and per-object orbit values; the downloads; the JVM jars and Orekit; libcft's build.

## Open, for Logan

- **The study's four decisions on data** (its Q7, W0):
  - (a) SATCAT decay dates for the watch's objects;
  - (b) observed space weather;
  - (c) a Space-Track account for TIP and decay messages, with his reading of its redistribution terms;
  - (d) the source of the whole catalogue's candidate list.
- **Whether to build the decay watch** (W1 to W3), as the study recommends.
- **The week's decision 4,** a SATCAT request for seed index 1178, still not made.
- **The service's follow-up:** count sets one 1e-8-day unit apart as one orbit determination, and log the alternation. It bears on DEBRIS-H's counts too.
- **The Aerospace Corporation's list,** which refused WebFetch: it needs a person with a browser.
- **Pushing this study to the public repository.**
