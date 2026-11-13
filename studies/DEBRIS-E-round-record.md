# Round DEBRIS-E: the record

The lead's record of round DEBRIS-E in cft-debris, 2026-11-13.
- **The plan of record:** `DEBRIS-E-plan.md`, draft 3. Logan approved it in chat ("Approve and start"), with all ten decisions at their defaults (SHA-256 `9c5d0b9b15df343fc250a3dd55bdd79ee73e0849075191d1d1414ee9596db760`).
  - plan-verifier-E (Sonnet) checked draft 1 and re-checked draft 2. Draft 3 had only the lead's checker (`check_plan_e.py`, logs 001 to 005 in the ledger).
  - **Logan set the round's direction** while it was drafted. He asked: "What route would you recommend? Considering building a custom solution simply so the existing tools can be utilized as reference models, while ours can be tweaked as needed to improve the accuracy of the simulation".
  - The lead recommended our own propagator, with existing tools and published authorities as its referees. Logan answered: "Yes draft it, however utilize native and cft for binary64 (and 32 if needed) so the library utilizes the entire precision range offered by cft, and the results can be compared for correctness".
- **The ledger:** `C:\Users\logan\source\repos\cft-debris-ledger\` (`lead.md`, `DEBRIS-E.md` and `verifier-E.md`). It is outside this repository.

## What ran

| agent | model | job | wall time | CPU | output |
|---|---|---|---|---|---|
| plan-verifier-E | Sonnet 5.5 | check the plan's draft 1, then re-check draft 2 | 7.5 min, then 1.2 min | small | its findings, in the plan's "What changed" tables; both reports in the ledger's `filed\` |
| DEBRIS-E | Opus 5.5 | build M1 and run its gates, E1 to E9 | 72 min, 05:42 to 06:54 | 31.6 min by cycles, plus about 1 uncharged (ESTIMATE) | `src\`, `tests\`, `debris-e\`, `DEBRIS-E-build.md`, `DEBRIS-E-report.md` |
| verifier-E | Sonnet 5.5 | disconfirm DEBRIS-E | 15 min, 06:57 to 07:12 | about 8.0 min by cycles, plus about 1 unwrapped | `DEBRIS-E-verifier-E-report.md` |
| merge-check-E | Haiku 5.5 | check the lead's narrowing | 3.7 min | none | its report, in the ledger's `filed\` |

- **Delivery:** every prompt arrived identical to its filed copy, and every agent ran on the model Logan chose. Both round agents' test escalations reached the lead within about a minute.
- **TimeSheet:**
  - each agent of the round was booked as a `notice`: B0028 for DEBRIS-E, B0031 for verifier-E and B0032 for merge-check-E;
  - E9's timings ran in a `sensitive` window. B0029 was booked for 07:15 and released when DEBRIS-E asked to start earlier. B0030 was used from 06:50:00 to 06:52:09;
  - verifier-E did no timing and asked for no window;
  - every booking was released once its holder finished: B0028 at 06:54, B0030 at 06:52, B0031 at 07:12, and B0032 at 07:28, by the lead.

## Phase 0, before dispatch

- **The archive** re-hashed unchanged: cft-fp256 at 0aa997a3, SHA-256 `e01003cc0b984864b065ce3395f56fa189451fcb0cd98cce5b11b3c17a9c29b8`.
- **No downloads.**
- **This host's `fma`,** checked by the lead while drafting, after plan-verifier-E's blockers (MEASURED). The lead's `fmacheck.c`, `fmacheck.py` and `o0probe.c` are now in the ledger's `tools\fmacheck\`.
  - mingw64 gcc 16.1.0's library `fma()` was not correctly rounded on 6,559 of 20,000 hard cases. The `vfmadd` instruction was wrong on 0.
  - At `-O0`, even with `-mfma`, a plain `fma()` still calls the library. `_mm_fmadd_sd` and `_mm_fmadd_ss` emit `vfmadd` at every level.
  - So the native kinds reach FMA only through those intrinsics. The build checks every native object for `vfmadd`, and for no call to `fma` or `fmaf`.

## What it built and found, after verification and narrowing

M1 is in `src\`, and its gates are in `tests\`. The build report is `DEBRIS-E-build.md`, narrowed at the merge, with its narrowings listed in its last section. DEBRIS-E's own report is filed verbatim; where the two differ, the narrowed build report stands.

1. **One force-model source, six number kinds** (READ, the code). `src\m1_physics.h` is compiled once each for native32, native64, cft32, cft64, cft128 and cft256. The model has:
   - the central term;
   - EIGEN-6C4 to degree 180, in a uniformly turning Earth;
   - the Sun and the Moon from DE421;
   - drag through the 28-band exponential atmosphere;
   - radiation pressure with a conical shadow.

   rk4 at a fixed step carries every lane on one time grid, and a run can restart from any step's state.
2. **Native equals cft, bit for bit, wherever only addition, multiplication, FMA, division and square root are involved** (MEASURED; reproduced by verifier-E on a seed of its own). At binary64 and binary32 alike, that covers:
   - 166,103 constants and table entries;
   - 7 kernels on 10,000 lanes, 64 at degree 180;
   - whole runs of 8 lanes over 100 steps;
   - 2,880 Lasser epochs.
3. **The C library's transcendentals** (MEASURED; narrowed at the merge):
   - With them, a few kernel outputs differ from cft's. The rotation differs in 5 of 10,000 lanes: 1 to 2 ulps on seed 0xE1, and up to 32 ulps on verifier-E's seed. Radiation pressure differs in 12 of 10,000, all penumbra lanes, by up to 1.2e10 ulps.
   - The functions themselves are within 0.79 to 1.60 ulps on verifier-E's 20,000 arguments, so all but `exp` are not correctly rounded there.
   - No whole run in E2 differed.
   - With libcft's functions in their place, native equals cft in every kernel.
4. **The referees agree** (MEASURED; reproduced):
   - **Lasser et al.'s gravity, degrees 2 to 180:** within 2.28e-15 m/s² at binary64, and 1.49e-15 at binary128 and binary256, against a tolerance of 1e-11. This ran on build 2. verifier-E's sampled re-run on the final build passed.
   - **JPL's `testpo.421`:** 109 points within 4.9e-16 AU.
   - **Orekit, force by force on 1,000 states:** gravity within 7.3e-17 m/s², drag within 6.8e-14 relative, and radiation in sunlight within 1.3e-15 relative.
   - **REBOUND's IAS15:** our rk4 at 5 s is within 0.114 m over an object-day, against a tolerance of 0.5 m.
5. **The precision ladder** (MEASURED; reproduced). Over one orbit, cft128 stays within 7.59e-26 m of cft256, against an ESTIMATE-based bound of 6.25e-20 m. cft64 reaches 3.6e-6 m from cft256, and cft32 21.8 m.
6. **Reproducibility** (MEASURED; reproduced):
   - two runs agree, and `-O0` equals `-O2`, at all six kinds;
   - restarted segments equal the continuous run at native64, cft64 and cft128, the kinds that test ran.
7. **IAS15 is a coarse referee on this model** (MEASURED; the cause inferred).
   - It moves 0.21 m between ε 1e-9 and 1e-10, and only 3.8e-5 m with radiation pressure off.
   - That the shadow's edges are the cause is inferred, not isolated.
   - rk4 at 1.25 s or less is the better reference here.
8. **The cost on this CPU** (MEASURED in window B0030, at 5 to 35% load; each cell a single run). A lane's force evaluation at degree 20 takes:
   - 2.0 to 5.5 µs at native64 with the C library's functions;
   - 0.68 to 1.17 ms at native64 with libcft's;
   - 2.2 to 3.3 ms at cft64;
   - 9.5 to 13.5 ms at cft256.

   At binary64 the six correctly rounded transcendentals are 30 to 35% of a cft64 evaluation (COMPUTED). At degree 20, with rk4 at 15 s, one core carries this many objects in real time (COMPUTED):

   | kind | objects |
   |---|---|
   | native64, C library's functions | about 1.7 million |
   | native64, libcft's functions | 4,500 |
   | cft64 | 1,570 |
   | cft128 | 990 |
   | cft256 | 390 |
9. **Beyond the gates:**
   - The 28-band atmosphere steps in density at its band edges. The lane that starts on an edge carries the largest binary64-against-binary128 difference; the attribution is BELIEVED.
   - The C library's `fma`, in a build without `-mfma`, was wrong on 6,559 of 20,000 hard cases. This matches the lead's finding in drafting.

## Rulings and events

- **05:40:** Logan approved draft 3, with every default.
- **05:42:** Phase 0 done; DEBRIS-E dispatched.
- **06:09:** DEBRIS-E asked for the lead's 20,000 `fma` cases, which sat in the lead's scratch.
  - The lead placed its generator, checker and `-O0` probe in the ledger's `tools\fmacheck\`, read-only.
  - It noted that the checker's control was weak, so E1 needed one of its own.
- **06:30:** E9's `sensitive` window booked, B0029. DEBRIS-E also reported that E2's planted control, as worded, failed.
- **06:45:** E9's window moved earlier at DEBRIS-E's request, to B0030; B0029 released.
- **06:52:** E9 done; B0030 released early.
- **06:55:** DEBRIS-E reported. Before verifier-E, the lead checked its outputs as fact: the manifests, no binaries, every source's header, and no third-party traces.
- **06:57:** verifier-E dispatched, with a 13-item attack list finished from DEBRIS-E's content.
- **07:19: the ruling on verifier-E's report.**
  - Every re-run passed and no figure was false, so there was no send-back.
  - verifier-E found five claims that reach past their evidence, and a limit on one control.
  - The lead checked each against the scripts and logs before ruling.
  - It made five narrowings and one addition in seventeen marked places, and kept the text as reported in the ledger.
- **07:25 to 07:27: merge-check-E.**
  - It confirmed the narrowing's hashes, marks and figures, and found six points, all fixed.
  - One was the lead's slip: the E3 note's range, copied inverted from verifier-E's report.
  - The fixes were not checked again.

## Failures, recorded as failures

- **E2's control as first specified:** the ulp planted in x was rounded away in the first step. Its replacement, in z, was chosen after the failure.
- **E5's control as first specified:** it was planted in a coordinate the test point did not test.
- **E6's first gravity run:** Orekit's frame turned on TAI seconds, while ours turns on TDB seconds. Once they were matched, it passed with the criterion unchanged.
- **E7's first version** crashed on REBOUND's API before producing data. Its tolerance was in the script from version 1.

Each is in the build report and its logs, and verifier-E confirmed that each is reported as failed.

## What the plan got wrong

- **E2's control** assumed that a one-ulp plant must break bit-identity from the first step. Rounding can absorb it (E2 log 001).
- **E7's premise,** that IAS15 at ε 1e-9 referees rk4 to DEBRIS-D's 4e-7 m, does not hold on this model: 0.21 m between ε 1e-9 and 1e-10.
- **E2's measure of growth** had nothing to measure. E1's C-library differences are rare, and none reached E2's eight lanes.
- **verifier-E's brief,** the lead's, was wrong twice:
  - item 6 asked for the physics sources' hashes, which builds 1 and 2 never recorded;
  - item 2's "would fail if it did not" holds only for the binary64 rotation and radiation kernels.

## The lead's slips

**In drafting,** each listed in the plan's "The lead's slips so far":
- draft 1 called the native `fma` correctly rounded, without trying it on this toolchain;
- draft 1 pinned no degree for most gates;
- draft 1 overstated our existing code;
- draft 1 left out three rules and four controls;
- Python's `write_text` turned the plan's line endings, and earlier the memory index's, to CRLF;
- draft 2 answered the `fma` blocker with `-mfma` alone, without trying `-O0`.

The ledger adds two more: a heredoc's backslash crashed the plan check (log 002), and an `rglob` found a directory before the file (log 003).

**During the round:**
- **The E3 range:** the lead copied verifier-E's inverted range into the build report's notes without checking it against the gate. merge-check-E caught it.
- **A `lead.md` entry** said a prompt check was "on the line above" when it was not. An appended correction gives it.
- **A `cd` into `studies\debris-e`** moved the session's working directory again. It was restored at once.
- **The lead's first check of merge-check-E's prompt** ran from a Bash heredoc whose backslashes collapsed. Its pattern matched nothing, and it printed no verdict. It was rewritten as a script file that refuses an empty match.
- **The first prompt check against merge-check-E's transcript** pointed at the `%TEMP%` task file, which holds no user message while the agent runs, as the lead's notes say. The script refused, and the check against the durable transcript passed.

## Cost

Tokens processed per agent, from the harness's transcripts since round DEBRIS-D closed (2026-11-13 04:17 -0700), by `dispatch\cost.py` (MEASURED):

| agent | model | calls | tokens processed |
|---|---|---|---|
| the lead | Opus 5.5 | 150 | 90,047,724 |
| plan-verifier-E | Sonnet 5.5 | 42 | 5,128,678 |
| DEBRIS-E | Opus 5.5 | 277 | 157,828,049 |
| verifier-E | Sonnet 5.5 | 44 | 5,653,162 |
| merge-check-E | Haiku 5.5 | 8 | 789,188 |
| total | | | 259,446,801 |

- **The shares:** DEBRIS-E 61% of the total, and the lead 35%. Nearly all of every agent's tokens are cache reads.
- **The known-answer check,** the last call's context against the harness's own `subagent_tokens`:
  - exact for plan-verifier-E (182,019) and merge-check-E (141,252);
  - DEBRIS-E 0.38% short (768,523 against 771,479), and verifier-E 0.19% short (184,333 against 184,689). The causes are not determined.
- **The lead's figure** includes the round's drafting from 04:55, and runs to 07:27, before this record and the commit.

## Where things are

**In this repository:**
- `src\`, 15 files: M1, MIT;
- `tests\`, 21 files: its build script, driver and gates, MIT;
- `studies\DEBRIS-E-plan.md` (draft 3, approved);
- `studies\DEBRIS-E-build.md` (the build report, narrowed at the merge);
- `studies\debris-e\`, 60 files under its `MANIFEST.sha256`;
- `studies\DEBRIS-E-report.md` and `studies\DEBRIS-E-verifier-E-report.md`, each filed verbatim;
- this record.

**In the ledger:**
- `lead.md`, `DEBRIS-E.md` and `verifier-E.md`;
- `filed\`: the build report as reported, and the plan-verifier's and merge-check's reports;
- `dispatch\`: the prompts, their scripts, and the plan checker with its logs;
- `tools\`: the archive, and `fmacheck\` with the lead's `fma` generator, checker and probe.

**Kept out of the repository:**
- cft-fp256's sources and libcft's build;
- every executable, `m1x.dll` among them;
- the downloads: EIGEN-6C4, DE421, Lasser et al.'s files, Orekit and Hipparchus;
- REBOUND, imported as installed.

Each log names the SHA-256 of the binaries it ran, and `build.003.log` lists every source's.

## Open, for Logan

- **Pushing this round to the public repository.** The build is committed locally on `main`, under decision 10.
- **The certificate.** M1 writes none, under Logan's word that certificate support is built for but not implemented for now. It is built for one: restarted segments equal the continuous run at native64, cft64 and cft128. The request for GPU certificates is with cft-fp256, from round DEBRIS-D.
- **What the build report leaves open,** with no recommendation here:
  - a better-conditioned penumbra: the C library's last bits now move ν by up to 1.4e-6 relative;
  - the 28-band atmosphere's density steps at its edges;
  - the about 2e-5 m between rk4 and IAS15 on the smooth model;
  - velocities in E5, and a rigorous E3 bound;
  - a transcendental control for `exp` and for binary32 that can fail.
- **The next round's direction:** the GPU port, the 24/7 host, and accuracy tweaks judged against observations. Each is Logan's to order.
- **Still open from earlier rounds:**
  - the hindcast's accounts;
  - Orekit's date round trip;
  - JB2008's correctness;
  - reproducibility across JVMs and machines;
  - DEBRIS-D's nine requests to cft-fp256, logged there for planning.
