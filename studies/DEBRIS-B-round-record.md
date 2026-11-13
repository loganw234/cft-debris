# Round DEBRIS-B: the record

The lead's record of round DEBRIS-B in cft-debris, 2026-11-12, written when the round closed.
- **The plan of record:** `DEBRIS-B-plan.md`, draft 3, SHA-256 `e2e07b0543b2624eca5aa0f6173cf1dc7cdaf4f02af569356348ef35dee700d3`. Logan approved it in chat, with all five decisions at their defaults, and it did not change during the round.
- **The ledger:** `C:\Users\logan\source\repos\cft-debris-ledger\`, with every heading stamped by `date`. `lead.md` is the lead's file, and every agent has its own.
- **The prompts and the lead's scripts:** in the ledger's `dispatch\`.

## What ran

| agent | model | job | wall time | CPU (its own figure) | output |
|---|---|---|---|---|---|
| verifier-A | Sonnet 5.5 | disconfirm DEBRIS-A | 12 min, 15:53 to 16:06 | about 7.5 min | `DEBRIS-A-verifier-A-report.md` |
| DEBRIS-B | Opus 5.5 | the study, Q1 to Q4 | 55 min, 15:53 to 16:48 | about 8 min | `DEBRIS-B-custom-model.md`, `debris-b\`, `DEBRIS-B-report.md` |
| verifier-B | Sonnet 5.5 | disconfirm DEBRIS-B | 12 min, 16:53 to 17:05 | about 6 min | `DEBRIS-B-verifier-B-report.md` |
| merge-check | Haiku 5.5 | check the lead's narrowing of the study | 1.5 min | none | its verdict is in `lead.md`, 17:12 |

- **Budgets:** DEBRIS-B had 4 hours and 25 CPU-minutes; verifier-A 2 hours and 10; verifier-B 2 hours and 15. Every agent finished inside its budget.
- **Prompts:** every one arrived identical to its filed copy (`dispatch\check_prompts.py`, against the harness's transcripts).
- **Models:** each transcript's replies came from the model Logan chose.
- **Messages:** all three round agents reached the lead with SendMessage to `main`, within a minute of starting.

## What it found

**DEBRIS-A** (verifier-A):
- Its numbers reproduce from its own scripts, to every printed digit.
- Its wording does not always hold. "Every round trip within 1.1e-6 m" is true only for IAS15 in LEO over one day. "Within 1.4e-7 m of a binary128 reference" is 1.439e-7 m against binary128.
- Its LEO references share IAS15's algorithm and force model, so they cannot show an error common to either.
- Several READ claims are not in their cited sources.
- Its 54,000 objects is stale: DISCOS now shows 68,450.
- The study is untouched. Its errata are in verifier-A's report, and they have been sent to cft-rebound's lead.

**DEBRIS-B** (verified by verifier-B, and narrowed at the merge). Its short answer:
1. **The authorities exist for the core layers, and most are free:** SOFA, the IERS, DE440 with `testpo.440`, Vallado's SGP4, and the Lasser et al. 2020 benchmark.
   - There are no published vectors for drag, radiation pressure with shadow, or orbit determination.
   - DISCOS is closed to individuals.
2. **A real force evaluation costs 1.2 to 11 µs in LEO and 1.1 µs in MEO and GEO,** at binary64 and without a full density model.
   - The LEO catalogue costs 46 to 634 CPU-hours a year.
   - The density model is the open term: at more than 1.85 µs a call it doubles the cost.
3. **Binary64 is not the limit in any regime tabulated,** which are near-circular orbits only.
4. **Logan's fp256 hypothesis, tested.**
   - Halving the step cut binary256's round trip by 2^15 each time, twice, and both results fell inside the band predicted before the run.
   - So the binary128-binary256 tie at 100 s was IAS15's fixed 15th-order step error, not the arithmetic.
   - Binary128 levels off at about 2e-26 m.
5. **Binary128 is enough for every use found,** partly on BELIEVED judgements.
   - It costs 177 to 214 times binary64 in C.
   - No tile rate exists for any force beyond point-mass gravity.
6. **No recommendation among build, adopt and hybrid.** Three named measurements would decide it.

**The figure measured twice:** IAS15's force evaluations per LEO object-day.
- verifier-A got 12,452 from DEBRIS-A's script.
- DEBRIS-B got 12,410 with its own J2 expression, and 12,452 with DEBRIS-A's operation order. verifier-B reproduced both.
- Both runs took 559 steps. The count depends on the force expression's last bits.

**The tile:** cft-rebound's and cft-fp256's leads both answered from their records.
- No IAS15 rate on the tile has been measured for any force beyond point-mass gravity.
- The 1,300 binary256 system-steps a second per tile is a projection.
- "Format-blind" holds per beat, not per element.
- cft-rebound's lead will raise HORIZON.md's lines 111 and 218 with Logan.
- Both answers are filed in the ledger's `relayed\`.

## Rulings and events

- **No send-back.**
  - verifier-B found two wording defects ("under 0.3" for 0.31, and a control criterion set after the fact) and two quantifiers that reached past the evidence.
  - None is a wrong answer in READY's sense, so under Logan's rule eight passages were narrowed at the merge.
  - Each is marked in the study and listed in its last section. merge-check found two problems in the narrowing, and both were fixed.
  - The study as reported is kept in the ledger's `filed\`.
- **The positive control.** As specified, the binary64 control failed: single runs fell 8x.
  - DEBRIS-B re-measured it as a 32-member distribution. That shows the floor does not fall like 2^15 a halving, but its "flat within 2x" was a criterion chosen after the data.
  - The study now says so.
- **Unapproved downloads, by the harness.** WebFetch saves any response that is not HTML. A PDF (arXiv 1809.09196) and JPL's ephemeris README (served as binary) were saved that way.
  - Ruling: fetch HTML pages only.
  - Logan left both files in place and approved reading them.
- **The TimeSheet** arrived mid-round from cft-fp256's lead.
  - Nothing after it needed a booking: verifier-B's runs were each under 10 minutes, and the desktop had no sensitive window.
  - Logan approved cft-debris booking there.
- **Process checks.** After DEBRIS-B reported, one `ias15_cft.exe` was running. It was cft-rebound's own, from its `cft-rebound-r4\build\`, so it was left alone. After verifier-B reported, nothing of the round's was running.

## What the plan got wrong

1. **The overlap's premise,** "if they disagree, one of the two claimed measured figures is false". The count also depends on the force expression's last bits.
2. **The binary128 floor,** "about 1e-27 m". That figure is the one-way difference; the round-trip floor is about 2e-26 m.
3. **The binary64 positive control,** judged on single runs. One draw cannot carry it: it needs a distribution, and a criterion stated before the data.
4. **The tile priced as "format-blind",** quoting HORIZON.md. That holds per beat only.
5. **The tile question routed to cft-fp256's lead alone.** The IAS15 records were cft-rebound's.
6. **The sweep's cost:** 5.5 CPU-minutes, not about 13. Also, the exponential atmosphere needed no batching.

## The lead's slips

These continue the plan's list, which records slips 1 to 4 from drafting.

5. **The watch on the ledger files** was armed after the agents had started, so its "expect 0" reading said 1.
6. **Two ledger entries were garbled** by backslash escapes in a `printf` format string. The second came after a memory note about the first. The cause, measured: this harness hands the shell a doubled backslash as a single one.
7. **Two entry times were typed from memory,** and both were wrong.
8. **The retraction about DEBRIS-A's "1.4e-7 m",** sent to Logan and to cft-rebound's lead, was half right. cft-rebound's lead now has the correction.
9. **The first version of the cost script** had a control that compared a count with itself, so it could not fail. Before use it was replaced by a known-answer check against the harness's own figures.

## Cost

**Tokens processed** per agent: input, cache writes, cache reads and output, summed over its API calls. They were read from the transcripts by the ledger's `dispatch\cost.py`, which counts each call once by its message id.

**Known-answer check:** each agent's last-call context matches the harness's own figure:
- exactly for verifier-A (157,105), verifier-B (160,424) and merge-check (95,756);
- within 243 tokens for DEBRIS-B (545,554, against 545,797).

| | model | calls | output tokens | tokens processed |
|---|---|---|---|---|
| the lead, from dispatch (15:52) to 17:13 | Opus 5.5 | 95 | 206,942 | 29,198,029 |
| DEBRIS-B | Opus 5.5 | 103 | 294,831 | 32,536,742 |
| verifier-A | Sonnet 5.5 | 27 | 33,943 | 3,105,674 |
| verifier-B | Sonnet 5.5 | 43 | 26,915 | 5,116,850 |
| merge-check | Haiku 5.5 | 5 | 17,580 | 393,242 |
| **the round** | | | | **70,350,537** |
| drafting: the lead before dispatch | Opus 5.5 | 62 | 279,302 | 20,742,977 |
| drafting: the plan verifier | Sonnet 5.5 | 37 | 68,128 | 5,772,501 |

Cache reads are 97% of the round's tokens processed (68,320,571 of 70,350,537).

## Where things are

**`studies\`:**
- `DEBRIS-B-plan.md`;
- `DEBRIS-B-custom-model.md` (narrowed) and `debris-b\` (54 files, under `MANIFEST.sha256`);
- `DEBRIS-B-report.md`;
- `DEBRIS-A-verifier-A-report.md` and `DEBRIS-B-verifier-B-report.md`;
- this record.

The DEBRIS-A files are untouched: 32 checksums OK, 29 files, no `__pycache__`.

**The ledger:**
- `lead.md`, `DEBRIS-B.md`, `verifier-A.md` and `verifier-B.md`;
- `dispatch\`: the prompts, the briefs and the lead's scripts;
- `relayed\`: the two tile answers;
- `filed\`: the study as reported;
- `tools\`: the preserved port.

## Open, for Logan

- **The decision:** build, adopt or hybrid. DEBRIS-B makes no recommendation.
- **The measurements that would decide it:**
  - an Orekit run held to Lasser et al.'s vectors, which needs three named downloads;
  - whether Orekit is bit-reproducible across machines;
  - a covariance-realism hindcast on objects tracked by satellite laser ranging.
- **The density model's cost** (NRLMSISE-00, JB2008). Settling it needs a download, and their licences restrict commercial use.
- **HORIZON.md's two lines** are with cft-rebound's lead.
