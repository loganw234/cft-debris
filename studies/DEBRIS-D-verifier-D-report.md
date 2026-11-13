# verifier-D's report on DEBRIS-D

The agent's final message, which is its report, filed verbatim by cft-debris's lead at 2026-11-12 22:19 -0700 with `cft-debris-ledger\dispatch\file_report.py`. Model claude-sonnet-5-5; final message timestamped 2026-11-13T05:18:38.484Z (UTC). Harness usage: <subagent_tokens>251392</subagent_tokens><tool_uses>83</tool_uses><duration_ms>1319528</duration_ms>. The text below is identical in the agent's own transcript and in the completion notice the lead received (as sent); a one-character change was shown to break that comparison. Body SHA-256 `1912b920ea7cfe4da903c6deecd4c4abbeda6ea8a56cf24767dcf815a5b0b652`.

---

# verifier-D report, round DEBRIS-D

I found one defect (item 5, sin/cos marking), two claims that run past their evidence (items 2/11 and 7), and three smaller notes. Everything I re-ran reproduced.

Scratch is `C:\Users\logan\source\repos\cft-debris-scratch\verifier-D\`. My copies of DEBRIS-D's scripts are there, with only `dd.py`'s two path constants, and `q3_host.py`'s window times, changed.

**Budget.** About 5.2 CPU-minutes by cycles at 2.5e9 per second (BELIEVED rate), plus about 1.3 for the later marks re-run. `GetProcessTimes` gave 2.0 for the first 5.2. Wall time was about 25 minutes. I used DEBRIS-D's `cpurun.py` as the meter; I did not audit it. Every program started by full path or through the Bash tool; I touched no WSL.

**1. Build and first test: confirmed.**
- The archive SHA-256 is `e01003cc...`. libcft built with mingw64 gcc, using the Rules' make line.
- `q2_first_test.py` ran both systems at fp64, fp128 and fp256, with 0 failures:
  - (a) bit for bit against `lang.run`;
  - (b) at most 1.9% of the stated tolerance against mpmath;
  - (c) the planted μ fails (a).
- 12 of 12 image and bank hashes match `images.tsv` for Q2's six images. The two degree-8 `sw:512` images (fp64 and fp128) also match.
- Tolerance (b) is about 50 times looser than the observed agreement. A bug of tens of ulps would pass (b); (a) is the real test.

**2. Degree sweep: confirmed, with one over-wide claim.**
- Degrees 6 and 7 compile at 7,281/7,270/7,375 and 8,302/8,291/8,396 instructions, with bank 424/427/448 and scratch 222 for degree 7.
- Degree 8 is refused `scratch-capacity` (273) at fp64 and fp128, and `bank-capacity` (516) at fp256.
- Degree 20 is refused `bank-capacity` (1,762 params and 6 constants) in 1.2 s. I did not compile degree 20 with lane params.
- All five generated field sources match `field_sources.sha256`.
- **Quantifier note.** "Degree 7 is the largest field that fits... what `hip:N` can carry today" is shown only for gen_field.py's single formulation: unrolled lets, every coefficient product a param. A rolled or `map` form, or differently ordered sums, was not tried. The claim should read "this generator's degree 7".

**3. Q1: confirmed.**
- My rebuild of `count_ops` matches, including the 8,160 FMA-class, 3 divides and 1 root at degree 20.
- C1 matches the hand count (104 mul, 37 add, 3 div, 1 sqrt). C2 (the planted term) passes at degrees 2, 8, 20, 36 and 70.
- **Note.** The 799 (also 29 divisions, 9 roots, 20 transcendentals) uses the sunlit radiation-pressure case. Penumbra gives 821 and 33 divisions. The study does not say "sunlit".

**4. Q3 host prices: confirmed.**
- Window B0026 ran 22:10:00 to 22:16:20, with 0 failures. The Windows CPU load sample was at most 11%, and only my notice B0025 was on the desktop. The lead released B0026 early.
- Tolerance stated beforehand: ±30%. Results against DEBRIS-D:

| quantity | mine | DEBRIS-D | gap |
|---|---|---|---|
| FMA, my driver (ns) | 193 / 218 / 308 | 195 / 235 / 313 | within 7% |
| FMA, `cft-bench` (ns) | 197.7 / 234.2 / 326.6 | 217.7 / 236.6 / 338.5 | 9% worst |
| divide (µs) | 3.73 / 5.82 / 8.98 | 3.6 / 5.6 / 9.2 | within 4% |
| exp (ms) | 0.127 / 0.323 / 1.167 | 0.136 / 0.334 / 1.121 | within 7% |
| pow (ms) | 0.354 / 0.921 / 3.310 | 0.342 / 0.932 / 3.361 | within 4% |
| sequencer (ns per lane-instruction) | 44.9 to 122 | 50 to 125 | 10% worst (J2 fp64) |

- Every function matches mpmath bit for bit at 1,000 arguments. The minimum timed-to-fold ratio is 64 (they report 61), and the ratio control is trivially satisfied (typical ratios of 1e5).

**5. Marks: one defect.**
- The 0/0/0 in 196,608 and the exp edge counts of 5, 510 and 532 of 1,024 reproduce (`q3_marks.py` re-run).
- Script hashes: version 1 (`db776d4587ea`) ran its log, failed C3 as stated, and was reported as a failure. Version 2 (`cf73c3231f5d`) keeps the same threshold (at least 1 lane) and changes only the argument class. Its criterion was written before its data, and it could fail.
- **Defect.** Part A starts every lane at t = 0.0 (`kepler_states`). The sin/cos argument is w·t, a function of time only, so all 512 lanes see identical arguments. I computed 193 distinct arguments over 96 steps × 4 stages. The compiler shares one sine and cosine between stages 2 and 3, so there are 147,456 sin/cos calls, not 196,608. Only exp has 196,608 independent LEO-dependent evaluations.
- **Failure scenario.** The "95% bound 3/N = 1.5e-5" and the replay price (3.4% of a core for 68,450 objects) assume independent trials. One unlucky time t would mark all lanes at once. At about 0.12 s per marked lane-segment, 68,450 lanes cost about 8,200 s, not a fraction of a second. The positive control covers exp only; sin and cos have no control that could mark.

**6. Q4: confirmed.**
- rk4 errors reproduce: 2,310 / 83.5 / 3.31 / 0.148 m at 60 / 30 / 15 / 7.5 s. IAS15 at ε 1e-9 gives 3.97e-7 m, 559 steps and 16,449 evaluations.
- The reference check is 2.0e-8 m at version 2. Version 2 kept the 1e-7 m threshold and changed only the method (a second Romberg elimination), after version 1 failed at 6.0e-5 m. The study reports the failure.
- The rounding claim holds. The |fp64 − long double| difference is 1.2e-6 to 1.3e-5 m a day, larger than IAS15's 4e-7. The 0.34 s figure recomputes from the h^4 law.

**7. Q5/Q7 recomputed: arithmetic right; two wording defects.**
- Inputs, with labels:
  - instructions per step: degree 7 is MEASURED (8,291 to 8,396); degree 20 is an ESTIMATE (30,000 to 40,000);
  - steps per object-day: MEASURED (5,760 at 15 s);
  - GPU lane-programs per second: READ from `GPU-A-hip.md:845-866`, times routine instruction counts (`LANGUAGE.md:466-467`, `:504`);
  - fp128 is an ESTIMATE.
- Results:
  - 5060 Ti, fp64: 0.071 to 0.098 s per object-day, giving 0.88 to 1.2M objects.
  - RX 7600, fp256: 0.42 to 0.60 s per object-day, giving 0.14 to 0.21M objects.
  - So 0.14 to 1.2M and "2.1 to 18 times real time" recompute.
  - Degree 7's row recomputes (4.2 to 4.4M on the 5060 Ti at fp64).
  - So does "13 to 48% of the RX 7600" (1/7.9 to 1/2.1).
- **Defect, short answer 6.** "Real time is not the constraint on one consumer card" and the headline range are COMPUTED but rest on the degree-20 instruction ESTIMATE. The short answer carries the "up to 3" factor, but not as part of the claim. Q5's own text shows that at a third of the rates the RX 7600 at binary256 reaches 0.70 to 1.0 of real time.
- **Defect, Q7.** "13 to 48%" applies no factor. At the factor of 3, that card at binary256 is at about 143%. The figure also prices one object-day per object per day, not the loop's own work: horizon bins out to 7 days from earlier fits to each new element set.
- Check on the routine shares: 88% is 4,020/4,541 and 48% is about 4,020/8,302.

**8. Q6.**
- JB2008 "about 225 pow": my WebFetch of the GitHub HTML view gave about 226 (224 in `localTemp` above 125 km, 2 in `tSubL`) and about 317 `localTemp` calls. This is consistent with the study; it is a model summary, not a bytes-level count.
- Positive control for the NRLMSISE-00 route: GitHub's view stops at line 1,000 of 1,459, and `gts7` has no definition in the displayed text. That supports "not counted".
- Count stability: asked again, the same page gave `ccor` 4 exp, `ccor2` 5 exp and `densu` 3 exp with 6 pow. The study lists 2, 3, and 2 to 3 exp and no pow in `densu`. Static counts per summary are unstable, so the 20 to 30 pow estimate for NRLMSISE is not determined.
- Licences: laid out as claimed, no legal conclusion. I checked nothing further.

**9. Q2's v1 claims: confirmed against the archive.**
- `transcendental` (`LANGUAGE.md:878`), `time-dependence` (`:880`) and `verlet-not-separable` (`:1266`, `:2834`).
- The `rk4` template (`:1185-1197`) gives 7 FMA-class operations a state component.
- The lane-capacity (`:291-293`), index-arithmetic (`:302-304`) and `HOSTAPI.md` `seq_features` 0x75f1f lines say what the study says.
- The `CERTIFICATES.md` citations I opened (66-73, 928-935, 3414-3426, 3921-3924) are accurate.

**10. Records: confirmed.**
- 32 OK, 29 files, 54 OK, 136 OK, and `debris-d` 73 OK (74 files). There is no `__pycache__`.
- No image, bank, `.gfc` or Apache/GPL header in `studies\`. `j2-sv.cftl` shares no code with cft-fp256's `kepler-sv-fp64.cftl`.
- Every log's header script hash has a kept script of that name, and the manifest lists them.

**11. Summary and report against the tables.** Points 1 to 5 and 7 are consistent with the tables, apart from the items above. Point 7 (0 marks) rests on the item 5 defect, and point 6 needs the narrowing above. The report says 1,085 words; the filed file counts 1,150.

**12. Criteria before data: confirmed.** The three versioned failures (Q4 reference, Q3 marks control, sweep parser) are each reported as a failure with the replacement named. The sweep's first log shows three FAILs with "REFUSED ?", from a regex that broke on the drive colon.

**13. Lead's rulings.**
- Degree 20 with lane params started at 21:09:35 under a 290 s timeout, which capped it below 5 CPU-minutes (282.9 CPU-s by cycles). The stop-rule message is timestamped 21:11:22, mid-run, not before. The 21:12 ruling matches.
- `cpu.tsv` sums to 16.07 CPU-minutes, as reported.
- DEBRIS-D's account of the WSL breach and `lead.md`'s agree.
- DEBRIS-D's ledger also records a bare `timeout` at 20:58 that resolved to System32's `TIMEOUT.EXE` and failed harmlessly. The study omits it.

**Did not do**
- The 290 s degree-20 lane-param compile, per the stop rule.
- `ias15_cft.exe` and cft-rebound's source.
- A GPU, the cft-bench tables or WSL.
- NRLMSISE-00's raw source (that would be a download).
- The `q2_refusals.py` and `q1_objectday.py` re-runs. I recomputed the object-day IAS15 own work (4.1e6 against their 4.0e6) by hand.
- I verified my own claim in item 5 by direct computation of the distinct arguments (193), not by running a second marks experiment.

**What the brief got wrong.**
- Item 4 asks for "the sequencer at 50 to 125 ns". The measured range with these lane counts is 44.9 to 122, which fits the stated tolerance but not the quoted lower edge.
- The brief did not ask for an independent hand count for C1 of item 3. I accepted the script's docstring, which was written after the first build run (DEBRIS-D discloses this).
- My ledger heading "22:02" was typed from memory, and `date` read 22:01. I appended a correction.
