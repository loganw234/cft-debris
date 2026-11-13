# DEBRIS-C's report (round DEBRIS-C)

The agent's final message, which is its report, filed verbatim by cft-debris's lead at 2026-11-12 18:54 -0700 with `cft-debris-ledger\dispatch\file_report.py`. Model claude-opus-5-5; final message timestamped 2026-11-13T01:54:06.268Z (UTC). Harness usage: <subagent_tokens>622200</subagent_tokens><tool_uses>185</tool_uses><duration_ms>3444664</duration_ms>. The text below is identical in the agent's own transcript and in the completion notice the lead received; a one-character change was shown to break that comparison. Body SHA-256 `38c80b983927614b51ed6b1cf858ffd586ac93e0f95e94d4024416db6a8aedce`.

---

DEBRIS-C is done. The study is at `C:\Users\logan\source\repos\cft-debris\studies\DEBRIS-C-measurements.md` (SHA-256 `f6f93859...`), and its scripts, logs and records are in `studies\debris-c\`, with a `MANIFEST.sha256` (136 files, all check OK). It has not been verified yet. It runs to about 7,700 words, over the brief's 6 to 10 pages.

**Short answer.**
- **Verifiable:** gravity and third-body forces can be checked against the published benchmarks, by a custom kernel and by Orekit alike.
- **Density sets the cost:** the density model, not gravity, dominates a LEO catalogue's budget.
- **Reproducible:** Orekit gave identical bits across six runs in different JVM compilation modes, on this one JVM and machine. The custom C kernel's bits change when the compiler uses fused multiply-adds (FMA).
- **Hindcast:** feasible with public laser-ranging truth, but it needs Logan's accounts.
- **No recommendation:** the evidence does not decide among build, adopt and hybrid.

**M0, the gate: PASS on the second run.**
- **Run 001 FAILED, 6 of 9 calls.** Orekit refuses the benchmark's own `EIGEN6-C4.gfc`, which has its degree-0 line twice, so the propagator step never ran.
- **Run 002 PASSED, 10 of 10.** Under your 18:07 ruling it read a de-duplicated copy: one line removed, no value changed. The copy's derivation is asserted, and two planted second changes fail it.
- **Without orekit-data:** UTC, the rotating frame, the Sun from DE421, both density models, gravity and one propagator step all ran, with no linkage error. No leg was stopped.

**M1a, gravity (EIGEN-6C4, degrees 2–180, 2,880 epochs): PASS.**
- **Criterion:** 1e-11 m/s² on the maximum vector difference over the day.
- **Results:** my normalised C kernel misses Lasser et al.'s values by 2.28e-15 at most, and Orekit by 2.21e-15. The two differ from each other by 3.2e-16.
- **Control PASS:** truncation at degree 173 was chosen by computation before any comparison (expected 10.9× the tolerance). It was reported at 9.8e-10 by both kernels.
- **What the criterion catches:** removing degree 180 alone is reported. One changed degree-180 coefficient gives 9.6e-12 and is not.

**M1b, Sun and Moon: third bodies PASS, both testpo criteria FAILED.**
- **Third bodies PASS:** Sun 1.5e-17, Moon 4.4e-16, planets 4.7e-22 m/s², with both readers. Both planted errors were reported.
- **My DE421 reader FAILED** my 1e-13 tolerance at 13 libration points, by 1–3 ulps of angles up to 4,107 rad. My stated basis overlooked those angles. The criterion was not loosened.
- **Orekit's reader FAILED:** up to 6.8e-12 AU (1.0 m) at 697 of 1,594 points, about 1.3 m in the full position vector. It behaves as a 6–15 µs time offset at TDB-dated queries; the cause is not determined, and it does not appear at GPS-dated queries.
- **Control PASS:** the shifted-time reader fails all 1,801 points, as it must.

**M2, density cost (Java from Nashorn, two runs at 11–96% load).**

| model | cost per call | against the 1.85 µs break-even |
|---|---|---|
| NRLMSISE00 | 7.3–7.5 µs | 4.0–4.1× |
| JB2008 | 29.9–31.6 µs | 16–17× |

- **Control 1 PASS:** every model loop is at least 67× the trivial call (7.3–8.1 ns, a lower bound).
- **Control 2 PASS:** NRLMSISE00's nine densities match a published C run to 2.7e-16 relative. No reference check was run for JB2008.
- **Budget (computed):** the LEO catalogue at degree 20 rises from 87 to 431–441 CPU-hours a year with NRLMSISE00, and to 1,493–1,573 with JB2008.
- **Gravity:** Orekit's costs 1.5–3.5× DEBRIS-B's C kernel, language and algorithm together.

**M3, reproducibility: PASS.**
- **Orekit:** the default JIT ×3, `-Xint`, C1 only and C2 only gave bit-identical results at all 358 steps and in the final state.
- **Control PASS:** one ulp in the initial x changes the hash from step 0 and moves the end of the day by 5.6e-6 m.
- **C kernel:** the native FMA build contains 29 FMA instructions against none for `-O2`. Their outputs differ at 2,547 of 2,880 epochs, by at most 5.2e-17 m/s².
- **C control PASS:** a planted one-ulp change alters the hash.

**M4, the hindcast (designed).**
- **Truth:** the EUROLAS Data Center lists laser data for ENVISAT to 2024-08-08 and TOPEX/Poseidon to 2025-02-20.
- **Access:** CDDIS needs an Earthdata Login for HTTPS, and EUROLAS needs registration and an API key.
- **Criteria are numeric now:** a binomial band on the fraction with |z| ≤ 2 and a χ² band on mean z², plus a tested refusal rule.
- **Pilot:** about 2 CPU-minutes a month (computed). The real costs are credentials and modelling ENVISAT's 2.5 m spin signature.

**Controls that failed:** none of those that ran. Three control scripts crashed before finishing: `m1b_check` at the last ephemeris record, `m2_reference` on a Nashorn argument type, and the M3 one-ulp run on a missing `Math.nextUp`. Each was fixed in a second version, and both logs are kept. M2 timing run 001 is set aside because its calibration ran cold.

**Environment facts, both in my ledger:**
- **CPU counter:** GetProcessTimes reports about a quarter of the real CPU on this host today, so CPU is counted by cycles, per your 18:31 ruling.
- **Orekit:** the time offset in M1b above.

**Could not settle:**
- the cause of Orekit's time offset;
- why GROOPS sits 2e-15 from both of our gravity kernels;
- whether JB2008 is correct as timed;
- what a C density model would cost;
- reproducibility across JVM versions and machines;
- current pass rates, and whether TOPEX tracking ended in 2005 (ILRS) or 2025 (EUROLAS).

**Did not do:** download anything, use orekit-data, run the hindcast or any orbit determination, count Orekit's force evaluations, or touch DEBRIS-A or DEBRIS-B.

**Budget and checks:** 57 minutes of wall time to the last measurement and 7.2 CPU-minutes. DEBRIS-A and DEBRIS-B records still check (32 OK, 29 files, 54 OK, no `__pycache__`). No process of mine is running.

**What the brief got wrong:**
1. M0's stop rules had no branch for an approved input that Orekit refuses.
2. GetProcessTimes as the JVM's CPU counter.
3. "The precision testpo prints" fails as a tolerance basis for large libration angles.
4. GitHub's HTML view cuts off `NRLMSISE00Test.java` before its reference values, and orekit.org blocks fetches, so I used pynrlmsise00's documentation.
5. The EUROLAS Data Center is not open without an account.

Files are in `C:\Users\logan\source\repos\cft-debris\`:
- `studies\DEBRIS-C-measurements.md`
- `studies\debris-c\` (with `MANIFEST.sha256`)
- `..\cft-debris-ledger\DEBRIS-C.md`
