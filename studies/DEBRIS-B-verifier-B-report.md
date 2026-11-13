# verifier-B's report on DEBRIS-B (round DEBRIS-B)

The agent's final message, which is its report, filed verbatim by cft-debris's lead at 2026-11-12 17:07 -0700 with `cft-debris-ledger\dispatch\file_report.py`. Model claude-sonnet-5-5; final message timestamped 2026-11-13T00:05:55.087Z (UTC). Harness usage: <subagent_tokens>160424</subagent_tokens><tool_uses>50</tool_uses><duration_ms>701947</duration_ms>. The text below is identical in the agent's own transcript and in the completion notice the lead received; a one-character change was shown to break that comparison. Body SHA-256 `fadd6721b14a92ebb81d144512d5756930523ca8cd4918501fb88d74f40c7b04`.

---

**verifier-B report.** I found two small defects and two wording or quantifier problems. Nothing I re-ran contradicts a headline figure. I did not re-decide Q4.

**Environment.** Test escalation: written to my ledger file and sent to `main`, and "received" came back. I used `C:\msys64\mingw64\bin` first on PATH, and `gcc -dumpmachine` printed `x86_64-w64-mingw32`. Host load was 13–34% at the start of the runs. My CPU was about 6 minutes, with wall time as the stand-in for the single-threaded runs.

**1. Q3 sweep: confirmed.**
- The port's SHA-256 matches `lead.md`.
- I ran `run_port_copy.py` on fresh copies of the five DEBRIS-A scripts, in an empty directory per dt, at dt = 50 s and 25 s. Every round trip matches §3.2's table to every printed digit. The 25 s fp64 and fp128 legs were also fully re-run.

| leg | round trip |
|---|---|
| 50 s, binary64 | 5.211e-8 m |
| 50 s, binary128 | 3.644e-26 m |
| 50 s, binary256 | 2.722e-26 m |
| 25 s, binary64 | 6.318e-9 m |
| 25 s, binary128 | 1.969e-26 m |
| 25 s, binary256 | 8.309e-31 m |

- The binary256 falls are 32,730 and 32,760, so 2^15.0 per halving, inside the plan's band. The band is in the plan at lines 239–240 and was stated before the data. A flat floor would have failed it.
- Plan line 245 says the sweep is not measuring what it claims if the binary64 floor falls with dt, so I checked the control next.

**2. Positive control: defect in wording (does not change the conclusion).**
- I re-ran `fp64_ensemble.py` from a clean copy at all four step sizes. Every figure reproduces exactly, and member 0's assertion holds at 100, 50 and 25 s.
- The criterion "flat within 2x" was set after the single-leg control failed. `fp64_ensemble.py` asserts only member 0. Nothing asserts flatness, and no failing result was stated beforehand.
- The medians run 3.0, 2.1, 1.5, 1.9e-8 m, so max/min is 1.999. This is borderline, not clearly flat.
- I bootstrapped the 32 members, 2,000 resamples. The dt = 100 s median is 3.0e-8 m (95% CI 2.5–3.5e-8). The dt = 25 s median is 1.5e-8 m (95% CI 1.1–2.2e-8). The ratio of the two medians has a 95% CI of 1.2 to 3.0.
- So a real 2–3x fall over a 4x change in dt is not excluded. Member spread is about 50x.
- Failure scenario: a reader takes "flat" as measured when it is "not shown to fall like 2^15". The conclusion that the floor is far from 2^15 per halving stands, and binary256's 2^30 dwarfs the 2x.

**3. Q2 timings and controls: confirmed, with two notes.**
- I rebuilt `q2bench.exe` and the `-DNO_FORCE` twin and re-ran `q2_time.py` at host load 13%. Every time is within 12% of the filed log. For example, gravity at degree 8 is 170 ns against 183, degree 70 is 10.3 µs against 10.0, and the full frame series is 151 µs against 147. The no-force ratios run from 15.5x (Chebyshev) up, so every one clears 10x. The atmosphere was 98x at one object per call.
- `q2_check.py` gives "ALL 40 ASSERTIONS PASSED", and its log diffs clean against the filed one.
- The checks are independent of the kernels for gravity (mpmath potential and Legendre functions), Chebyshev (cos k·arccos τ), the SRP quadrature, and the rotations (numpy). The frame series has a partial overlap: the "kernel's own arguments" assertion reuses the kernel's Horner order for argument formation. The independent "exact arguments" check is the one that stands.
- Restatement after the deep-penumbra failure: it changed the denominator from the force itself to the unshadowed force. The closed form in mpmath agrees with the quadrature to 8.8e-25, so the metric change is justified. It is still a loosening: the tolerance is 1e-8 against a measured 7e-10.
- Restatement after the full-series failure: it replaced a fixed 1e-12 tolerance with an analytic error bound (the kernel sits at 8% of it). That corrected the check.
- For most gravity rows the no-force loop is empty (0.5 ns), so those ratios could hardly fail. That is acceptable, because the force build's own time proves work was done.

**4. Evaluation counts: confirmed.**
- `ias15_evals.py` gives 12,410 evaluations in 559 steps, and `ias15_evals_order.py` gives 12,452. Both match the logs.
- I built `gravdll.dll`; the degree-20 point gives 16,463 evaluations in 559 steps. The rest of the shcount output matches: 12,403, 13,852, 17,912 and 20,159.
- DEBRIS-A's own J2 is the 2020 operation order, which accounts for the 12,452 against 12,410.

**5. Computed figures: reproduce, with two notes.**
- `tables.py` reproduces its log exactly.
- 0.89, 0.32 and 0.13 tile-years and 2.9 core-years all reproduce. 559 ÷ 204.4 × 28,149 gives 0.889 tile-years.
- 9.3 halvings is 41.95 decades ÷ 4.5155 decades per halving, and 2^9.29 is about 625, so "roughly 600" holds.
- Integrator share, 233 ns: it is 2.887 ms divided by the J2 run's 12,410 evaluations. The point-mass run's own evaluation count was never measured. The study labels it BELIEVED, and that is accurate. If the point-mass run needed 15 evaluations per step instead of the J2 run's 22, the share would be about 1.5x higher.
- "Low" arithmetic-error column: it is scaled from a single draw (1.175e-8 m). The ensemble's draws span roughly 50x. So "low" is not a lower bound, and the bracket is a pair of estimates.

**6. Physical columns: confirmed.** `q3_physics.py` gives 4,991 m after a day (density ×1.2), and 5,293 and 5,326 m after a year, with maxima 7,063 and 6,518 m (area-to-mass ×1.2, MEO and GEO). The table states "5.3-7.1 km" for MEO and "5.3-6.5" for GEO, so they match.

**7. READ claims** (WebFetch, HTML pages only, so "consistent with" at most).
- Lasser et al.:
  - Consistent with degree and order 180, DE421 third bodies, tides, relativity, the rotation, and CC BY 4.0.
  - The page does not say drag and radiation pressure are excluded. It only never mentions them, and Table 1 is an image. The study's "exclude" is an inference.
- `testpo.440`: 838.1K, dated 2020-12-22, consistent with.
- `AIAA-2006-6753.zip`: 1,248,284 bytes, languages as stated, no licence stated, verification files not mentioned. Consistent with.
- Orekit 13.1.9 pom: Java 1.8 and Hipparchus 4.0.3, consistent with.
- DISCOS: the SDUP page says accounts are for research institutes, government bodies or industrial companies of an ESA Member State, "not as an individual". The statistics page gives LEO 28,149, a table total of 47,393, and an update date of 2 November 2026. All consistent with.
- heyoka: Eq. 12, the doubling of the Taylor order for quadruple precision, the 10^(18/16) ≈ 13 timestep factor, and "≳2 orders of magnitude slower" are all consistent with. I read only the first 100,000 of 114,221 characters. The "10,500 s against 13 s" figure is not checked.
- IERS term counts: not found. The chapter-5 page states no counts, and the `.txt` tables fall under the HTML-only ruling. The arithmetic 1,306+253+36+4+1 = 1,600 and the 2,941 total are internally consistent (the check asserts 2,941).

**8. Summary against tables.**
- **Defect:** "MEO and GEO together under 0.3" appears in both the report and the Short answer. The tables give 0.23 + 0.08 = 0.31 CPU-hours a year (unrounded 0.3116). Failure scenario: anyone who quotes "under 0.3" and checks it fails.
- "1.2 to 11 µs": the LEO rows reproduce (1.171 to 11.03 µs), but the MEO and GEO rows are 1.09 µs. The range is for LEO only, with the exponential atmosphere included.
- "Binary64 is not the limit anywhere in debris prediction": the quantifier reaches past the evidence.
  - The regimes tabulated are near-circular only. No GTO or HEO row exists, though the high law is an e = 1/2 Kepler law.
  - The body's own "What does not transfer" caveat on chaos is absent from the Short answer and the report.
  - At 30 years the arithmetic (0.08–0.9 m) exceeds a 1 cm initial state, and the rescue ("the centimetre has itself grown") is BELIEVED.
  - The Short answer's own "2 to 100 times below" claim holds only at a year.
- "Binary128 is enough for every use found": the table rests on BELIEVED judgements. The one measured floor is 2e-26 m, and enough-ness for OD and covariance is not measured.

**9. Carried figures.**
- `port_fullday.log`'s 1.175e-8 m is the fp64-versus-fp128 forward difference at the turn, after 864 steps of 100 s. That is how the study uses it, so its definition is kept. The same log's round trip is 5.8e-8 m, 5x larger, so the difference is not the round-trip floor.
- The 54,000 above 10 cm is not reused. DEBRIS-B uses DISCOS catalogued objects (28,149 in LEO) and states the 68,450 MASTER-8 figure separately. Definitions are kept.
- Rate ratios: in my sweep, binary128 ran 0.30 and binary256 0.088 of binary64's rate (16.9 and 5.0 against 57 steps/s), inside the stated ranges.

**10. Premises: confirmed.**
- Binary128 floor: the round trip is 2.0–3.6e-26 m, so the brief's "about 1e-27 m" was the one-way figure.
- Overlap: DEBRIS-A's own J2 uses the 2020 operation order, which reproduces 12,452. Step counts are identical, and the 42-evaluation gap is the expression's.
- The plan's overlap premise is wrong as the lead says.

**11. Other.** Not run:
- I did not fetch any of the other [B] sources.
- I ran no tile or other hardware measurements.
- I did not re-run the heyoka or Orekit claims beyond the pom.

**Checks before reporting.** `MANIFEST.sha256` shows 54 OK. `SHA256SUMS` shows 32 OK, `debris-a` has 29 files, and there is no `__pycache__`. No process of mine is running.

**What the brief got wrong:** nothing material.
