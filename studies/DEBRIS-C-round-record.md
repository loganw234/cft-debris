# Round DEBRIS-C: the record

The lead's record of round DEBRIS-C in cft-debris, 2026-11-12.
- **The plan of record:** `DEBRIS-C-plan.md`. Logan approved draft 3 in chat ("Approve and start"), with all seven decisions at their defaults (SHA-256 `2d55ec47581a396e6c048aeab3a9402ff7dcc936b92e481b70b83790c8be29ed`).
  - It was corrected twice, each change recorded in the ledger first: in Phase 0, the Java invocation (SHA-256 `807e66c6c2218e063f3b766a566d06502812b9c16e71694353f1ea69b4987538`); at 18:56, the CPU counter (`69941aa3849cf18e2f2a31a015df3aa2b44ce7996b5bb6b0313cb0f84fe5b61b`).
- **The ledger:** `C:\Users\logan\source\repos\cft-debris-ledger\` (`lead.md`, `DEBRIS-C.md` and `verifier-C.md`). It is outside this repository.

## What ran

| agent | model | job | wall time | CPU | output |
|---|---|---|---|---|---|
| plan-verifier-C | Sonnet 5.5 | check the plan, then re-check draft 2 | 6 min, then 1 min | small | its findings, in the plan's "What changed" tables |
| DEBRIS-C | Opus 5.5 | the study: M0 to M4 | 57 min, 17:56 to 18:53 | 7.2 min, by cycles | `DEBRIS-C-measurements.md`, `debris-c\`, `DEBRIS-C-report.md` |
| verifier-C | Sonnet 5.5 | disconfirm DEBRIS-C | 12 min, 18:58 to 19:10 | 4.2 min, by cycles | `DEBRIS-C-verifier-C-report.md` |
| merge-check-C | Haiku 5.5 | check the lead's narrowing | 1.5 min | none | its verdict, in `lead.md` (19:15) |

- Every prompt arrived identical to its filed copy, every agent ran on the model Logan chose, and both round agents reached the lead by message within a minute.
- Each agent's time was booked in the TimeSheet as a `notice` (B0013, B0021) and released when it finished.

## Phase 0, before dispatch

- **Lasser et al.'s benchmark has moved.** The article's FTP path answers "550 ITSG: No such file or directory". The dataset is at `https://ftp.tugraz.at/pub/ITSG/COST-G/softwareComparison/`, with HTML listings.
- **Its README settled most of M1's conventions:** degrees 2 to 180, GPS time, DE421 point masses. It also carries its own `EIGEN6-C4.gfc`, so ICGEM's full field was not needed.
- **Downloads:** 19 files, each approved by Logan by name: Orekit 13.1.9 and seven Hipparchus jars, DE421 and its test file, and eight benchmark files.
  - Each sits in its own read-only directory.
  - The jars match their Maven SHA-1, and every file's SHA-256 is in the ledger.
  - Two of them were checked on download, a hash cross-check and a CR test, by checks that could not fail at first. Both were redone with controls (the lead's slips, below).
- **The smoke test:** on this host's Java 8 runtime, 21 of 22 classes loaded, and the planted missing class failed.
  - `jjs -cp` cannot take a multi-jar classpath here. Nashorn runs as `java -cp ... jdk.nashorn.tools.Shell`, and the plan was corrected to say so.

## What it found

The study as narrowed at the merge. verifier-C re-ran it from clean, and every figure it re-ran reproduced.
1. **M0, the gate.** Orekit ran every path the study uses without orekit-data, once one input was normalised.
   - The benchmark's own `EIGEN6-C4.gfc` lists its degree-0 coefficient twice, and Orekit refuses the duplicate. The lead's ruling of 18:07 allowed a copy with that one line removed, derived by an asserting script.
2. **M1, force models held to published authorities.**
   - **Gravity:** the custom C kernel and Orekit both meet Lasser et al.'s accelerations, at 2.3e-15 and 2.2e-15 m/s², against a 1e-11 criterion. The planted truncation is reported at 9.8e-10.
   - **Third bodies:** both meet theirs, the Sun at 1.5e-17, the Moon at 4.4e-16 and the planets at 4.7e-22 m/s².
   - **JPL's `testpo.421`:**
     - The custom reader failed its own 1e-13 criterion at 13 libration angles, by 1 to 3 ulps. Its basis overlooked angles that large.
     - Orekit failed as run. verifier-C traced the miss to the query dates: built with `createJDDate(..., TDB)`, they round-trip 11.9 to 14.5 µs off. With each date shifted by its round-trip error, Orekit's reader passes (1.51e-14 AU).
3. **M2, the density model sets the LEO cost.**
   - NRLMSISE00 costs 7.3 to 7.5 µs a call and JB2008 29.9 to 31.6 µs, in Java (minima; the medians are 8 to 30% higher).
   - At degree 20 the LEO catalogue then costs 431 to 441 CPU-hours a year with NRLMSISE00, and 1,493 to 1,573 with JB2008, against 87 with an exponential atmosphere.
4. **M3, reproducibility.**
   - Orekit reproduced itself to the bit across six JVM compilation modes, on one JVM and one machine.
   - The custom C kernel's bits change when the compiler uses fused multiply-adds.
5. **M4, the hindcast, designed.**
   - Truth exists: EDC lists laser data for ENVISAT to 2024-08-08.
   - Both ILRS data centres need an account.
   - The pass and fail criteria are stated, and a pilot needs about 2 CPU-minutes a month.
6. **No recommendation** among build, adopt and hybrid: the evidence does not decide it.

## Rulings and events

- **No send-back.** verifier-C found one defect, a wrong attribution, not a wrong measurement.
  - Eight passages were narrowed at the merge, each marked and listed in the study.
  - The study as reported is kept in the ledger's `filed\`.
  - The lead re-ran verifier-C's round-trip test before narrowing, and got 11.9 to 14.5 µs. It first recorded "12.0", a misreading corrected in the ledger.
  - **merge-check-C** found six of the eight narrowed passages sound. Its other points, a too-broad "Verified", a rounded range and four smaller ones, were fixed in its terms.
- **The CPU counter.** Windows' `GetProcessTimes` charges a busy thread only 0.23 to 0.57 of its time on this host under load. From 18:31 the round counted CPU by cycles, and the plan says so.
- **The public repository,** on Logan's word: https://github.com/loganw234/cft-debris.
  - Its privacy scan was clean.
  - `.gitattributes` is `* -text`, because 95 records end their lines with CRLF and the manifests are over exact bytes.
  - A fresh clone, with and without `autocrlf`, passes every manifest.
- **The MIT licence,** after a check found no third-party code or data in the repository.

## What the plan got wrong

1. Lasser et al.'s FTP path, taken from the article, is stale.
2. `jjs -cp` and `CLASSPATH`, as the way to run Orekit.
3. M0's stop rules had no branch for an approved input that Orekit refuses.
4. `GetProcessTimes` as the JVM's CPU counter.
5. "The precision `testpo.421` prints" as a tolerance basis: it ignores the large libration angles.
6. The suggested route to Orekit's test reference values: GitHub's HTML view truncates them.
7. "Is the EUROLAS data centre open?": it needs an account.
8. In draft 2: JPL's README as the source of the test tolerance (caught by plan-verifier-C).

## The lead's slips

1. A path check that extracted nothing, while still printing its controls as passing. The harness collapsed the regex's doubled backslashes.
2. JPL's README named as a source without being opened.
3. "Python's `hashlib` agrees with `sha256sum`" written into the ledger before the check's output was read. The output said 11 of 11 disagreed, because of a parsing fault in the check.
4. A CR test that could not fail: Git Bash's `grep` strips the CR at each line end. With it, the first commit used `eol=lf`, which would have broken every manifest. Git's warnings caught it before the push.
5. Two checks in the licence and clone work that tested nothing at first: a "first value" search that picked up a header word, and a clone control that could not fail. Both were redone with controls that bite.
6. A first run of the lead's CPU-counter check failed on its own `ctypes` types, before giving any figure.
7. The lead's re-run of verifier-C's round-trip test was recorded as "12.0 to 14.5 µs"; it was 11.9. The merge first rounded the range to "12 to 15 µs". merge-check-C caught the second, and the lead found the first.

## Cost

Tokens processed (input, cache writes, cache reads and output), read from the transcripts by the ledger's `dispatch\cost.py`.

**Known-answer check:** each agent's last-call context matches the harness's own figure:
- exactly for plan-verifier-C (154,873) and verifier-C (215,255);
- within 1,199 tokens for DEBRIS-C (621,001, against 622,200).

| | model | calls | output tokens | tokens processed |
|---|---|---|---|---|
| the lead, 17:14 to 19:15 (drafting, Phase 0, dispatch, rulings, the merge, and the repository) | Opus 5.5 | 115 | 267,947 | 78,461,778 |
| plan-verifier-C | Sonnet 5.5 | 17 | 35,818 | 1,918,701 |
| DEBRIS-C | Opus 5.5 | 138 | 298,139 | 53,363,500 |
| verifier-C | Sonnet 5.5 | 50 | 42,320 | 7,878,760 |
| merge-check-C | Haiku 5.5 | 4 | 19,044 | 302,144 |
| **the round** | | | | **141,924,883** |

**The lead's share is 55% of the round.** By this round each of its calls re-read about 0.86 M tokens of its own context. A fresh session for the next round would cut that share most.

## Where things are

**`studies\`:**
- `DEBRIS-C-plan.md`;
- `DEBRIS-C-measurements.md` (narrowed) and `debris-c\` (136 files, under `MANIFEST.sha256`);
- `DEBRIS-C-report.md` and `DEBRIS-C-verifier-C-report.md`;
- this record.

**The ledger:**
- `lead.md`, `DEBRIS-C.md` and `verifier-C.md`;
- `dispatch\`: the prompts, briefs and scripts;
- `relayed\`;
- `filed\`: the studies as reported.

**The downloads:** `C:\Users\logan\source\repos\cft-debris-downloads\`, not redistributed.

## Open, for Logan

- **The decision:** build, adopt or hybrid.
- **The hindcast** (M4) needs accounts that would be Logan's: an EDC API key or an Earthdata Login, and Space-Track.
- **Orekit's `createJDDate(..., TDB)` round trip:** whether it is an Orekit defect or a misuse of the API. A question to Orekit's maintainers would settle it.
- **Still unmeasured:**
  - whether JB2008 is correct as timed;
  - what a C density model would cost;
  - reproducibility across JVM versions, threads and machines.
