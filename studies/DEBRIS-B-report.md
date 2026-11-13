# DEBRIS-B's report (round DEBRIS-B)

The agent's final message, which is its report, filed verbatim by cft-debris's lead at 2026-11-12 16:50 -0700 with `cft-debris-ledger\dispatch\file_report.py`. Model claude-opus-5-5; final message timestamped 2026-11-12T23:48:01.425Z (UTC). Harness usage: <subagent_tokens>545797</subagent_tokens><tool_uses>181</tool_uses><duration_ms>3297212</duration_ms>. The text below is identical in the agent's own transcript and in the completion notice the lead received; a one-character change was shown to break that comparison. Body SHA-256 `c3cae972386c06dce9d646fe7a97d89f655069356aee599269661699706cdb22`.

---

I've written the DEBRIS-B study. One-line answer: a custom debris model would rest on mostly free authorities and cost tens to hundreds of CPU-hours per catalogue-year at binary64. Wider arithmetic buys only accuracy checks (rulers), and binary128 is enough for those. The evidence lays out the three product shapes but doesn't decide between building, adopting existing tools, or a hybrid.

**Q1 – authorities (READ, mostly through WebFetch summaries)**
- **Covered:** SOFA for time and frames, IERS C04 and Bulletin C for Earth orientation, JPL DE440 with its test file `testpo.440` (838.1K), and Vallado's SGP4 package (`AIAA-2006-6753.zip`, 1,248,284 bytes).
- **Strongest find:** Lasser et al. 2020, a published benchmark of accelerations along a one-day GRACE orbit. It covers gravity to degree 180, third bodies, tides, relativity and the celestial–terrestrial rotation, and was made to check exactly this kind of software.
- **Gaps:** no test vectors found for drag, radiation pressure with shadow, orbit determination or the breakup model. ESA's DISCOS is closed to individuals; GCAT (CC-BY) is the open alternative.
- **Foreign oracle:** Orekit 13.1.9 targets Java 1.8, so it should run on this host's Java 8 after about three downloads. Agreement with it catches coding errors, not model error.

**Q2 – cost of a real force evaluation (binary64, host load 13–69%)**

| kernel | time per call |
|---|---|
| gravity, degree 8 / 20 / 36 / 70 | 183 / 864 / 2,618 / 10,039 ns |
| Earth-fixed transform, interpolated as Orekit does (6 points, 1 h) | 512 ns (full series: 147 µs) |
| Sun and Moon | 129 ns |
| exponential drag | 80 ns |
| radiation pressure with shadow | 35–75 ns |

- **Controls:** both negative controls pass. Every run with the force call compiled out was at least 14.9× faster, and 40 asserted independent checks agree. Two first-run check failures are kept in the records and explained.
- **Evaluations per day:** a degree-20 to 70 field raises IAS15 to 16,463–20,159 evaluations per LEO object-day, with no change in step count.
- **Budget (COMPUTED):** 46–634 CPU-hours a year for the 28,149 catalogued LEO objects, under 0.3 for MEO plus GEO. Object counts are from ESA DISCOS, updated 2 November 2026.
- **Open term:** I found no absolute cost for NRLMSISE-00 or JB2008. Any density model above 1.85 µs per call would more than double the degree-20 LEO cost.

**Q3 – arithmetic beyond binary64**
- **Binary64 is never the limit.** Its error is at most 1.2e-5 m after a week and 0.9 m after 30 years on the pessimistic transfer (COMPUTED). A 20% density error moves a 400 km object 5 km in a day; a 20% area-to-mass error moves MEO and GEO objects 5–7 km in a year (MEASURED).
- **Logan's hypothesis, tested:**
  - Each halving of the step cut binary256's round trip by 2^15.0: 8.9e-22, then 2.72e-26, then 8.31e-31 m. Both points are inside the predicted band (MEASURED).
  - Binary128 stops at 2–3e-26 m, its own floor.
  - So binary128 and binary256 tied at 100 s because of IAS15's fixed 15th-order step error, not the arithmetic.
  - Reaching binary256's floor this way would take about 600 times the steps. Taylor methods double the order instead (READ, heyoka paper).
- **Price of a wider format:** binary128 is enough for rulers, ill-conditioned orbit determination and covariance work. Binary128 gravity through libquadmath costs 177–214× binary64 (MEASURED). No tile rate exists for any force beyond point-mass gravity. On the measured point-mass rates, a year of the LEO catalogue at binary256 is about 0.9 tile-years.

**Q4 – product**
- **Bit-reproducible predictions with provenance:** possible at binary64 (the port matched REBOUND bit for bit). It needs a fixed operation order, and whether Orekit is already reproducible across machines is unmeasured.
- **Uncertainty with refusal:** proving it needs covariance-realism hindcasts, and truth data for debris is mostly TLEs.
- **GPU or tile ensembles:** no card rate exists with a real force, and at binary64 the CPU suffices.
- **Judgements:** all BELIEVED. The study makes no recommendation and names the measurements that would decide.

**The overlap figure:** 12,410 force evaluations and 559 steps for one LEO day (my J2 expression, my counter). Across mean anomalies and starting steps the count runs 12,397–12,459. With J2 in DEBRIS-A's operation order it is 12,452: the last bits of the expression move the count by 0.3%.

**Unsettled:**
- the NRLMSISE-00 and JB2008 cost;
- sizes of several test-vector sets: Lasser (FTP), NRLMSIS (server reset), JB2008 (403), NGA (unreachable);
- licences not stated for JPL, IERS, Vallado, GFZ and GMAT;
- whether Orekit is bit-reproducible across machines.

**Not done:**
- No Orekit, GMAT, heyoka or density-model runs.
- No downloads requested, and the approved [S21] PDF was not read.
- One unapproved file save: WebFetch saved JPL's README to disk. I reported it at 16:29, and Logan later approved reading it.
- The study runs to about 7,300 words, over the 6–10 page aim, mostly the Q1 table and sources.
- Used about 55 minutes of wall time and 8.2 CPU-minutes. The studies checks pass: 32 checksums OK, 29 DEBRIS-A files, no `__pycache__`.

**Where the brief was wrong:**
1. The binary128 floor is 2–3e-26 m for a round trip. The brief's 1e-27 m is the one-way difference at the turn.
2. "An arithmetic floor must not fall with dt" was judged on single binary64 runs, which fell 8× between 50 s and 25 s. As a 32-member ensemble the floor is flat within 2×, so the control holds only as a distribution. Both points are in my ledger.
3. The tile is "format-blind" per beat only, not per element (both leads).
4. The exponential atmosphere needed no batching (108× at one object per call).
5. The sweep cost 5.5 CPU-minutes, not about 13.
6. Real gravity fields have zero degree-1 and S_n0 terms by definition, so I started at degree 2.

Files are in C:\Users\logan\source\repos\cft-debris\studies:
- DEBRIS-B-custom-model.md
- debris-b\MANIFEST.sha256 (lists all 54 scripts, logs and records)
