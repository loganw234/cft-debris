# Round DEBRIS-D: the record

The lead's record of round DEBRIS-D in cft-debris, 2026-11-12.
- **The plan of record:** `DEBRIS-D-plan.md`, draft 5. Logan approved it in chat ("Approve and start"), with all six decisions at their defaults (SHA-256 `57709adb2b3bf75dc8c20cba6e407caeda23d6361c25a4f84f231bf7b6778da0`).
  - plan-verifier-D (Sonnet) checked draft 2 and re-checked draft 3. Drafts 4 and 5 had only the lead's checker (`check_plan_d.py`, logs 001 to 006 in the ledger).
  - Logan shaped the round twice while it was drafted. First: "*Yes if possible utilize cft programs, as well as generating certificates when able (they still dont cover all use cases)". Then: "*Certificate support can be built for but not implemented in order to still have gpu capability at the moment".
- **The ledger:** `C:\Users\logan\source\repos\cft-debris-ledger\` (`lead.md`, `DEBRIS-D.md` and `verifier-D.md`). It is outside this repository.

## What ran

| agent | model | job | wall time | CPU | output |
|---|---|---|---|---|---|
| plan-verifier-D | Sonnet 5.5 | check the plan's draft 2, then re-check draft 3 | 6 min, then 2.5 min | small | its findings, in the plan's "What changed" tables; both reports in the ledger's `filed\` |
| DEBRIS-D | Opus 5.5 | the study: Q1 to Q8 | 70 min, 20:40 to 21:53 | 16.1 min by cycles, plus about 0.3 (ESTIMATE) | `DEBRIS-D-architecture.md`, `debris-d\`, `DEBRIS-D-report.md` |
| verifier-D | Sonnet 5.5 | disconfirm DEBRIS-D | 22 min, 21:57 to 22:19 | about 6.5 min by cycles | `DEBRIS-D-verifier-D-report.md` |
| merge-check-D | Haiku 5.5 | check the lead's narrowing | 2 min | none | its report, in the ledger's `filed\` |

- **Delivery:** every prompt arrived identical to its filed copy, and every agent ran on the model Logan chose. Both round agents' test escalations reached the lead within a minute.
- **TimeSheet:**
  - each agent's time was booked as a `notice`: B0023, B0025 and B0027;
  - each timing ran in a `sensitive` window the lead booked: B0024 for DEBRIS-D (used 21:15 to 21:21) and B0026 for verifier-D (used 22:10 to 22:16);
  - every booking was released as soon as its holder finished.

## Phase 0, before dispatch

- **cft-fp256's lead answered** four questions and one follow-up, and then the certificate request. Each answer is filed verbatim in the ledger's `relayed\`, and every passage they cite was read at cft-fp256's commit 0aa997a3.
- **The archive:** cft-fp256 at 0aa997a3, 62,515,200 bytes, SHA-256 `e01003cc0b984864b065ce3395f56fa189451fcb0cd98cce5b11b3c17a9c29b8`. All 2,643 files' git blob ids match the commit, and the plan's three controls passed.
- **No downloads.**
- **The certificate request,** sent on Logan's word: certificates for runs on `hip:N`.
  - cft-fp256's lead answered that cft-segrun already writes on `hip:N` (`host/tools/segrun.c:4340`, READ).
  - What is missing: GPU identity lines, a stated scratch depth, and an audit of a GPU-written certificate in C.
  - It is logged for the GPU round's planning; its order and dates are Logan's.

## What it found, after verification and narrowing

The study is `DEBRIS-D-architecture.md`, narrowed at the merge, with its narrowings listed in its last section. Its main results:
1. **The route works on the CPU** (MEASURED; reproduced by verifier-D).
   - Two systems in cft-fp256's language ran at binary64, binary128 and binary256: J2 alone, and J2 with C22/S22, drag and the Earth's rotation.
   - They equal the reference interpreter bit for bit, and agree with a 120-digit mpmath reference within the tolerance stated beforehand. A planted one-ulp error fails, as it must.
2. **Capacity is the GPU route's limit today** (MEASURED; reproduced).
   - In the form the study's generator writes, degree 7 is the largest gravity field that fits `hip:N`'s 512-slot bank and 256-slot scratch at every format.
   - Degree 8 is refused `scratch-capacity` (273) at binary64 and binary128, and `bank-capacity` (516) at binary256. Degree 20 is refused `bank-capacity` (1,762 params).
3. **Prices on this CPU** (MEASURED; reproduced within 10%):
   - an FMA is 195, 235 and 313 ns at binary64, binary128 and binary256, and a divide 3.6, 5.6 and 9.2 µs;
   - a host exp is 0.14, 0.33 and 1.12 ms, and a host pow 0.34, 0.93 and 3.4 ms;
   - the sequencer runs at 50 to 125 ns a lane-instruction.
4. **The integrators** (MEASURED; reproduced).
   - rk4's error is 2,310, 83, 3.3 and 0.15 m a day at 60, 30, 15 and 7.5 s; IAS15's is 4.0e-7 m.
   - At binary64, rk4's own rounding, 1e-6 to 1e-5 m a day, keeps it from IAS15's accuracy. v1 offers no IAS15.
5. **The ladder** (COMPUTED, on the ESTIMATE of degree 20's instruction count).
   - At degree 20 with rk4 at 15 s, one consumer card runs 0.14 to 1.2 million objects in real time.
   - At a third of the rates, the RX 7600 at binary256 runs the 68,450 objects of MASTER-8's "> 10 cm" class at only 0.70 to 1.0 of real time.
   - Degree 7's rows rest on measured instruction counts and GPU-A's measured rates.
6. **Replay on the host:**
   - exp marked 0 lanes in 196,608 evaluations, a 95% bound of 1.5e-5;
   - for sin and cos the rate is not determined: every lane shared their argument.
7. **Requests for cft-fp256** (Q8), nine of them:
   - a larger bank, or index tables, on `hip:N`;
   - a deeper scratch on `hip:N`;
   - a cftc that copes with very large systems;
   - pow as a routine;
   - a `hip` target in cftc;
   - fp128 program rates, and rates below 1M lanes;
   - the specialised tier for programs;
   - an in-kernel divide and square root, only if an IAS15 kernel is wanted;
   - certificates for forcing that changes between segments, and for values through a square root.

## Rulings and events

- **20:55:** DEBRIS-D's timing window, B0024, booked.
- **21:12:** DEBRIS-D's stop-rule message on degree 20.
  - The ruling: no second compile, and degree 20 is priced as an ESTIMATE from degree 8's manifest and Q1's counts.
  - It added one cheap probe, the largest degree within `hip:N`'s limits, which found degree 7.
- **21:22 to 21:24: a breach.** A bare `bash` from Python resolved to `C:\Windows\System32\bash.exe`, and one command ran in the default WSL distro for 0.24 s. Its gcc failed at once and wrote nothing.
  - The fix: every program from Python is started by its full path.
  - cft-fp256's lead, whose distro it was (cft2204), confirmed nothing of its was running there, and that no action was needed.
- **22:02:** verifier-D's timing window, B0026, booked.
- **22:22: the ruling on verifier-D's report.**
  - verifier-D found one defect: sin and cos shared their arguments across lanes, so the marking bound does not reach them. It also found two over-wide claims: degree 7's generality, and real time resting on an ESTIMATE.
  - No count was false, so there was no send-back. The lead made six narrowings and one addition at the merge, in fourteen marked places, and kept the text as reported in the ledger.
- **22:25:** merge-check-D confirmed the narrowing, except for one figure, "within 12%", which the lead had taken from verifier-D's interim message. It became the report's "within 10%". Two wording points were fixed too, and the fixes were not checked again.

## What the plan got wrong

- **Its Rules lacked the System32 trap,** a bare `bash` from Python being WSL. DEBRIS-D also met a bare `timeout`, which resolved to `TIMEOUT.EXE`. Every later brief names the trap.
- **The drag-and-rotation system named no force that needs sin and cos of ωt.** DEBRIS-D added the degree-2 tesserals in the Earth-fixed frame.
- **It asked for Störmer-Verlet with drag,** which v1 refuses (`verlet-not-separable`).
- **The marking test's design left every lane on one time,** so sin and cos could not be tested independently. The plan named "the second system's arguments" and did not ask for independent times.

## The lead's slips

**In drafting,** each listed in the plan's "The lead's slips so far":
- **Claims stronger than their source:**
  - "binary64 is never the physical limit";
  - "600 times" given as measured;
  - "no licence found" for NRLMSISE-00;
  - passes said to change "with format".
- **Citations:**
  - Orekit's licence cited to the wrong study;
  - the hosts' citation written from memory;
  - the evaluation counts' domain dropped.
- **Checks that could not do their job:**
  - a control that a hash check refuses before the re-run it was meant to test;
  - a marking rate set to be measured on a test that cannot mark;
  - a stop rule that its own first test never meets.
- **cft-segrun's usage text,** read as "GPU runs cannot be certified". cft-fp256's lead corrected it.
- **A doubled backslash** that broke a display of hashes.

**During the round:**
- **The "within 12%":** taken from an interim message into the study's last section. merge-check-D caught it.
- **A `cd` into `studies\debris-d`** moved the session's working directory, the trap the lead's own notes name. It was harmless, and restored at once.
- **A `lead.md` entry** said the study's final hash was "on the line above"; it was not there. An appended correction gives it.
- **verifier-D's brief was regenerated before dispatch,** after one sentence was changed so that cheap checks are not crowded out. The first generation was deleted by its literal path and never sent.

## Cost

Tokens processed per agent, from the harness's transcripts since round DEBRIS-C closed (2026-11-12 19:17 -0700), by `dispatch\cost.py` (MEASURED):

| agent | model | calls | tokens processed |
|---|---|---|---|
| the lead | Opus 5.5 | 218 | 108,751,933 |
| plan-verifier-D | Sonnet 5.5 | 54 | 7,783,707 |
| DEBRIS-D | Opus 5.5 | 205 | 89,394,590 |
| verifier-D | Sonnet 5.5 | 79 | 14,266,345 |
| merge-check-D | Haiku 5.5 | 7 | 598,072 |
| total | | | 220,794,647 |

- **The lead's share:** 49% of the total. Nearly all of every agent's tokens are cache reads.
- **The known-answer check,** the last call's context against the harness's own `subagent_tokens`:
  - exact for plan-verifier-D (211,428), verifier-D (251,392) and merge-check-D (104,888);
  - DEBRIS-D within 0.4%: 731,043 against 733,636. The cause is not determined.
- **The lead's figure** includes the round's drafting from 19:17. Its context reached about 0.71M tokens a call.

## Where things are

**In this repository's `studies\`:**
- `DEBRIS-D-plan.md` (draft 5, approved);
- `DEBRIS-D-architecture.md` (the study, narrowed at the merge);
- `debris-d\`, 73 files under its `MANIFEST.sha256`;
- `DEBRIS-D-report.md` and `DEBRIS-D-verifier-D-report.md`, each filed verbatim;
- this record.

**In the ledger:**
- `lead.md`, `DEBRIS-D.md` and `verifier-D.md`;
- `relayed\`: cft-fp256's lead's five answers;
- `filed\`: the study as reported, and the plan-verifier's and merge-check's reports;
- `dispatch\`: the prompts, their scripts, and the plan checker with its logs;
- `tools\`: the archive.

**Kept out of the repository** under its MIT licence:
- cft-fp256's sources;
- libcft's build;
- every compiled image and bank;
- the generated field sources. They stay in the agents' scratch, with hashes and rebuild commands recorded.

## Open, for Logan

- **The build's choices,** on which the study makes no recommendation: the density model, the 24/7 host, and IAS15 against rk4.
- **The nine requests for cft-fp256** (Q8), sent at 22:28. Logan allowed requests to cft-fp256's session, and their order and dates are his. cft-fp256's lead logged them for planning, and said where each would land (relayed; filed in the ledger's `relayed\`):
  - **index tables and the 2,048 depth** are round 2's;
  - **the 512-slot bank** is the software executor's own capacity, which `hip:N` publishes, so raising it changes the executor's contract and lies beyond the GPU round;
  - **cftc on large systems, and a `hip` target,** are the compiler's;
  - **pow, powr and pown** are the math library's;
  - **fp128 and small-batch program rates** would be a small measurement parcel;
  - **the specialised tier for programs** is round 3's;
  - **an in-kernel divide and square root** is in no round's plan;
  - **the certificate items** are joined to the GPU certificate item, now noted in cft-fp256's roadmap (its commit c0af3e44, relayed).
- **Pushing this round to the public repository.**
- **Still open from rounds DEBRIS-B and DEBRIS-C:** build, adopt or hybrid; the hindcast's accounts; Orekit's date round trip; JB2008's correctness; and reproducibility across JVMs and machines.
