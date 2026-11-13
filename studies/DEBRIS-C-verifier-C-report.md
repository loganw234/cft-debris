# verifier-C's report on DEBRIS-C (round DEBRIS-C)

The agent's final message, which is its report, filed verbatim by cft-debris's lead at 2026-11-12 19:11 -0700 with `cft-debris-ledger\dispatch\file_report.py`. Model claude-sonnet-5-5; final message timestamped 2026-11-13T02:10:34.978Z (UTC). Harness usage: <subagent_tokens>215255</subagent_tokens><tool_uses>58</tool_uses><duration_ms>714028</duration_ms>. The text below is identical in the agent's own transcript and in the completion notice the lead received; a one-character change was shown to break that comparison. Body SHA-256 `b1f6d3a7ecf2045c223399c08814a19931e723b7eb5c8f62ec0ac1b29247deac`.

---

**verifier-C report: DEBRIS-C.** One defect found, in how the study attributes the Orekit testpo failure. Everything else reproduced. All timings ran at 10–71% host load, and `check desktop --short` printed FREE before each timing run. My CPU was about 4.2 minutes by cycles at 2.5e9 per second (BELIEVED), 3.5 times under budget. Wall time was about 13 minutes.

**Defect: the 6–15 µs "Orekit offset" comes from the driver's date construction (item 2).**
- `m1b_orekit.js` builds its dates with `AbsoluteDate.createJDDate(jd, s, TDB)`. I round-tripped those dates through `getComponents(TDB)` (`vc_rt.js`). They come back 14.497, 12.564, −11.932 and −12.492 µs off. These are exactly the `dt` values `m1b_diag2` implies for the same JEDs.
- Orekit's TDB−TT agrees with the two-term formula to 0.9 µs, and the offset correlates with cos g at r = 0.99995. So the cause is not the TDB series.
- I shifted each query date by its round-trip error (`vc_orekit_fix.js`) and re-ran. Orekit's DE421 reader then passes criterion 2: 0 failures of 1,594, maximum 1.51e-14 AU (`vc_check_fix.py`). The largest full-vector miss falls from 1.3 m to 3 mm.
- Criterion 2, as run, did fail, and DEBRIS-C reported that correctly. What overreaches is the attribution in three places:
  - "Orekit's reader FAILED" (report);
  - "a mark against it as a testpo-level oracle" and "not [an oracle] at 1e-13 AU in ephemeris positions" (study, Adopt and Hybrid);
  - the BELIEVED guess that the date conversion and the reader use different TDB conventions.
- The failure scenario: anyone who reads the study as saying "Orekit's DE421 positions are 6–15 µs off" would wrongly rule Orekit out as an ephemeris oracle. The date-construction path (`createJDDate` with a TDB scale) is what is off.
- The study's own evidence points the same way. Orekit and the custom reader agree to 8e-18 m/s² on GPS-dated queries.
- Not determined: whether the round-trip error is a bug in Orekit or a misuse of the API.
- Written to my ledger at 19:10.

**Item by item**
1. **M0 and M1a: confirmed.**
   - All 19 downloads match lead.md.
   - My copy of `derive_gfc_copy.py` produced a gfc copy with SHA-256 `bf296183…0852`, the expected value. Both planted changes fail.
   - The M0 gate passes 10 of 10 on that copy.
   - `build.sh` gives 0 against 29 FMA instructions. A separate `grep -ci 'vfm|vfnm'` on `objdump -d` gave 0 and 29.
   - The C and Orekit legs and `m1a_compare.py` reproduce:

     | Quantity | Value |
     |---|---|
     | C against Lasser et al. | 2.278e-15 |
     | Orekit against Lasser et al. | 2.210e-15 |
     | C against Orekit | 3.238e-16 |
     | both truncated at 173 | 9.772e-10 |
     | degree 180 removed | 1.791e-10 |
     | C̄(180,90) changed | 9.560e-12 |
     | per-degree minimum, degree 180 | 3.248e-11 |

   - Brief error: the SHA-256 `bf296183…` is the copy's hash. The script's hash is `1d7a28bd…`.
   - Both planted changes fail on assertion 1 alone, so assertions 2 and 3 are never exercised by the controls (a note).
2. **M1b: confirmed, apart from the defect above.**
   - Counts and maxima: 13 failures at the librations; 697 for Orekit with a maximum of 6.77e-12 AU; 1,801 for the control; the third-body table and its two controls.
   - The two kept versions of `m1b_check` differ only in the control's shift branch. TOL, criteria 1 and 2 are untouched, and the logs 001 and 002 give identical lines for them.
   - Neither testpo criterion was loosened.
3. **M2 and M3.**
   - **M2 timing: confirmed within load.** At 31% load, NRLMSISE00 measured 7.2 µs, JB2008 variant A 34.7 µs and variant B 32.7 µs. JB2008 variant A is 10–16% above the study's 29.9–31.6 µs, which is within load noise. Control 1 passes with large margins (58× or more), so it could hardly fail.
   - The study's headline costs are minima. The medians are 8–30% higher; the over-break-even conclusion holds either way.
   - **Control 2: confirmed.** All nine densities reproduce, and the nine reference values match the pynrlmsise00 page (via WebFetch).
   - **Run 001 set aside: sound.** Version 2 changed only the calibration and dropped the thread-CPU column. Run 001's 12.6 µs came from repetitions of 19–90 ms. Setting it aside was decided after seeing the data, but the choice is reported and my re-run supports version 2.
   - **M3: confirmed.** Step hash `b9c1c882bf57593b` for jit1, jit2, jit3, `-Xint`, C1 and C2, with step files byte-identical. The one-ulp control gives `c1700746f6ab571d`, differing from step 0. On the C side, 2,547 of 2,880 epochs differ by at most 5.17e-17, and the plant at epoch 1000 differs there alone.
4. **READ claims.**
   - **Positive control:** the pynrlmsise00 page returned the example with all nine values.
   - **Confirmed (via WebFetch), no "not found":**
     - Orekit 13.1.9, `n = FastMath.max(2, m)`. The Javadoc body says "negative gradient"; the summary omits "negative".
     - IERS TAI-UTC, 33 s.
     - EDC list, ENVISAT to 2024-08-08 and TOPEX to 2025-02-20. EDC calls the row "topex", not "TOPEX/Poseidon".
     - EDC API key.
     - CDDIS Earthdata Login, and anonymous FTP ended October 2020.
     - ILRS TOPEX/Poseidon ends 2005-12-15.
     - CRD 2.01 supersedes v1.01 on 2022-08-01. The page words this as "superseded", not "effective".
5. **COMPUTED figures: confirmed.**
   - `m2_table.py` reproduces DEBRIS-B's four rows to the ns (1,171, 1,852, 3,606, 11,027).
   - Ratios: 4,390 (the study says 4,400), 97.7, and 5.0–5.07 times DEBRIS-B's budget.
   - M4's bands reproduce, and 0.15 MB and 1.4–2.8 CPU-minutes recompute.
6. **Summary against tables.**
   - Every figure I held against its table matched.
   - "Orekit is a usable oracle … at 1e-11 and well below" is MEASURED on one day, one LEO arc at 455–500 km, a static field and point-mass bodies. It is narrower than the sentence reads.
   - "Every whole degree": the pass rests on each degree's RMS signal, which is COMPUTED. Removing a single degree is measured only for degree 180. The study says as much.
   - The six-run scope (one JVM, one machine) is stated correctly.
7. **Criteria before data: confirmed, with two caveats.**
   - All 97 script and runner hashes in the logs match kept versions. A copy of `m1b_check` with TOL changed to 1e-11 fails my check.
   - `m1a_control_degree.001` (18:10:02) precedes `m1a_compare.001` (18:11:57).
   - `m3_compare.py` was written at 18:34:44.16, together with `m3_prop.js` version 2 and `run_m3.sh`, before the first version-2 run, which is logged at 18:34:44. The order holds only to within about a second. The version-1 runs, which showed the same hash, had already been seen.
   - `m1a_compare.py` was written after the kernel outputs existed (18:11:55, against outputs at 18:10:49 and 18:11:22), but before anyone compared them.
8. **Rulings.**
   - The 18:07 conditions are met.
   - The M2 and M3 logs do not name the gravity file. The scripts hard-code the copy's directory, and the unmodified download throws in Orekit, so the copy must have been read.
   - The 7.2-minute CPU total re-adds to 433 s. Its version-1 logs use a conservative 4× rule.
9. **Other.**
   - The callbacks-plus-overhead "under 0.4 µs" (study) was measured at 15.5–23.7 ns per callback. In my run it was 29.7 ns, so JB2008 variant B gives about 0.49 µs, which is 1.5% of its cost and immaterial.
   - Records: 136 OK, 32 OK, 29 files, 54 OK, and no `__pycache__`.

**Not done:**
- The "GitHub truncates NRLMSISE00Test" claim.
- The EDC data-browser and FTP claims.
- The search-excerpt sources.
- JB2008 correctness.
- I did not read `DEBRIS-C.md`, per the brief.
- The five-points item (lead.md, 18:55) was not checked independently.
- The brief pointed to lead.md at 18:55 for these points, but no such entry exists. The last two entries are at 18:56 and 18:57; the five points are in DEBRIS-C's report.
- I read lead.md once, at the start. It was edited afterwards and I did not re-read it.

**The brief got wrong:** the `bf296183…` hash (above), and the 18:55 lead.md pointer.

My scratch is `C:\Users\logan\source\repos\cft-debris-scratch\verifier-C\`. The key files are `m1b\vc_rt.js`, `m1b\vc_orekit_fix.js` and `m1b\vc_check_fix.py`.
