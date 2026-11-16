# verifier-F's report on DEBRIS-F

The agent's final message, which is its report, filed verbatim by cft-debris's lead at 2026-11-16 10:24 -0700 with `cft-debris-ledger\dispatch\file_report.py`. Model claude-sonnet-5-5; final message timestamped 2026-11-16T17:23:16.041Z (UTC). Harness usage: <subagent_tokens>220126</subagent_tokens><tool_uses>78</tool_uses><duration_ms>890768</duration_ms>. The text below is identical in the agent's own transcript and in the completion notice the lead received (as sent); a one-character change was shown to break that comparison. Body SHA-256 `58b71f53e284b01051c6bf3dc1a29a4b730e19b96dd00dab0fbd40746b8a8213`.

---

**verifier-F's report.** I found no wrong answer in the F1 to F9 gates. There are no blocking defects, and several claims should be narrowed at the merge. I used about 12 CPU-minutes by cycles and about 15 minutes of wall time. I wrote only in my scratch and my ledger file.

**Setup.** I copied `src\` and `tests\` into my scratch and repointed `f_lib.py` (`SCRATCH`, `LEDGER_F`) and `gatelib.py` (`BUILD`, `WORK`). `LOGS`, `SCRIPTS` and `CPU_TSV` follow `REPO`, which is now my copy. The diff against the originals is those paths, plus the seed lines I changed in `f1`/`f2`/`f3`/`f4_gate.py`, `f6_swcheck.py`'s span and `f5_gate.py`'s synthetic state. My logs carry my copies' hashes, not DEBRIS-F's.

1. **Build from clean: confirmed.**
   - The archive hashes to `e01003cc…29b8`, and libcft to `f0eec4f2…`.
   - `build_f.sh` passes criteria 1 to 5 on my build.
   - The four build logs' hash lists differ only in `tests\m1f.c`. Today's files and my build match build 4's list. I asserted that each list held 21 lines.
   - **F3, F5 and F8 never ran on build 4's `m1f.c`.** I re-ran all three on build 4, so that gap is closed.
   - Frame table:
     - My whole file hashes to `0d77db98…`, not `1d997961…`. My file is 29 bytes shorter, which I take to be the header's input paths. I did not diff the headers.
     - The payload matches (`5eb68492…`), which is the comparison the brief allows.
2. **F1, seed 0xBEEF1, 10,000 lanes: confirmed.**
   - G1 and G2 pass at both widths.
   - Negative control: the reordered M00 broke 5,164 lanes (binary64) and 5,166 (binary32), M00 was named first, and the other 11 values stayed identical.
   - With the C library's `exp`, 4 lanes differ at binary64 and none at binary32. "1 in 10,000" holds for DEBRIS-F's seed only.
3. **F2 and F3, new seeds: confirmed.**
   - F2 gives the same worst TDB − TT, 25.35 µs. F3(a) gives 0.012 µas. F3(b) gives 15.4 µas against 1 mas, and the dX control gives 1.0000 mas.
   - **T3's basis:** 40.50 µs is printed in log 001, before any T3 figure, and the script hash is identical across logs 001 to 003 (only `f_lib.py` changed). Whether the 50 µs was set before any development comparison is not determined, because that scratch is closed.
   - F3(a) is stated in the build report as 0h UTC rows only.
   - F3(b)'s disclosure of the 12 µas development check is adequate.
   - **F3(c):** 2.13 × 9.331e-10 = 1.987e-9 rad, which re-derives. The measured maximum is 2.5e-14, about 8e4 below the bound. Its dominant term, the EOP slope breaks at 0h UTC, was probably not in any of the 200 random midpoints. The gate cannot fail below roughly 400 µas.
4. **F4 and F8: confirmed.**
   - F4, seed 0xBEE4: D1 and D2 pass. The tilt control came out at 30.8 times the tolerance (stated: 10). The bc control was at 1.0e-2. native64 and cft64 agreed on all 1,000 states, so "1 in 1,000" is seed-specific too.
   - F8 version 2 ran to completion and passed R1 to R3, C1, G1, G2 and C2.
   - The baseline sources match DEBRIS-E's `build.003.log`: 18 hashes.
   - Version 2 is not in `scripts\` or the manifest, because no log of its own is kept.
   - My first run of F8 stopped early because I had not copied `studies\debris-e\logs\build.003.log` into my copy. That was my omission.
5. **F5: confirmed.**
   - (c) with my own state and bc recovered to 2e-7 m.
   - (d) reran bit for bit: 94 converged, median 519.1 m, 90th 576.0 m, maximum 613.4 m, and a table byte-identical to the ledger's.
   - The B4 disclosure is adequate. "94 converged" depends on thresholds tuned on the ISS, one of the 100 objects.
   - **The 22 of F6's 200 fits that stopped on the iteration limit are inside every (A) statistic.** The build report states 22 (line 193), but the DEBRIS-F report does not. Their median miss is 0.644 km against 1.196 km for the converged fits. Excluding them would move (A)'s median from 1.122 to 1.196 km and its 90th from 2.825 to 2.919 km.
   - I did not re-run F6's (A) fits.
6. **Comparator (C): confirmed.**
   - `f6_swcopy.py --stage3` gives `47acbcc2…`.
   - The two-fill check over 2026-11-12 to 11-18 gives K1 identical at all 145 epochs, and K2 changes 24 epochs.
   - Matched forces, by `f6_orekit_fit.js`:
     - EIGEN-6C4 at 20×20 and the Sun and Moon from DE421 are present.
     - Conical shadow is present, and `cram` is 0.01, through a 1 kg mass.
     - Only density, integrator and the meaning of Cd differ.
7. **F7: confirmed at small size.**
   - I ran 1 object for 6 × 10-minute targets. cft128 against cft256 differs by at most 7.7e-27 m. The round64 control gives 7.5e-11 m, and my own bound is about 6e-22 m.
   - `read_prop` decodes each kind's own encoding.
   - B = 45,906,584 × 2⁻¹¹³ × 7.1e6 × 120 = 3.77e-18 m, which re-derives.
   - **The headline "10 objects … cft128 within 3.1e-25 m of cft256" covers 3 objects.** The ledger table has 3 cft128 rows. The build report says 3. The DEBRIS-F report and the build report's table row do not.
8. **Logs 002/003 and 001/002 (F1, F2, F4): confirmed.** After removing header lines and lines containing "sha256", the diffs are empty. The F1 verdict lines are also identical.
9. **F9: confirmed.**
   - The reported figures match `f9_time.001.log`.
   - The ratio range of 0.56 to 1.16 times E9 is right.
   - **"Run-to-run spread" has no measurement behind it.** The runs are single, and the 64-lane cft256 and cft128 cells rest on 2 steps.
10. **F6's statistics: confirmed.**
    - Medians and 90th percentiles, the nine cells and 14 pairs under 500 km, 9 of 200, 19 of 50 and the 1.169/1.156 medians all recompute from the ledger table.
    - The draw to 200 reproduces exactly from the CSVs: 8, 145, 7 and 40, with the same keys.
    - (C)'s 50 are `Random(0xF6C).sample` of the 200, not of the 704.
    - The CRITERIA text hashes to `37a814fce680…bdbf5`, and `tests\f6_hindcast.py` is byte-identical to the kept version.
11. **Reports against logs.**
    - "(A) and (C) miss alike" is labelled an inference in the build report, correctly.
    - The bc and Cd ranges for F6 are **not determined**, since the ledger table lacks them. F5(d)'s 100 fits give bc −0.89 to 1.02, with 23 negative.
    - The tilt "30 times" cause, "the tilt also moves the position within the field", is stated without a run that isolates it.
    - The §8 arithmetic checks: 524 to 850 s, 24.25/35.25/85.0 s per arc, the 1.34/1.38/1.27 ratios and 1.53 min = 92 s.
12. **Records.**
    - `MANIFEST.sha256` gives 56 OK, with none unlisted.
    - No new source file lacks the cft-debris/MIT header.
    - No binary, no `__pycache__`, and no third-party source or data in the repository.
    - **The ISS log:** `f5_gate.001.log` (lines 15 and 43) prints the ISS key and the derived figures 42.686 m and 0.292 m. That is the only per-object GP-derived content in the repository; no table was found. The ruling is the lead's.
    - **CR bytes:** 13 logs and records hold them. Eight are whole-file CRLF logs (the `f6_swcopy` and `f6_swcheck` logs and the other short logs), and five are partial. The kept scripts hold none. The origin (text-mode write or captured output) is not determined, and no byte-sensitive file is affected.
13. **Criteria before data: confirmed.** Every logged script hash has a kept version, apart from DEBRIS-E's unchanged `gatelib.py`. Every tests-folder script matches a kept version except `f8_gate.py`. F2's log 001, B4's thresholds and the tilt control are reported as what they were. F7's dry run is reported, but its logs are in the closed scratch, so that is **not determined**.
14. **§10:** items 1, 2, 3, 4, 6 and 8 are consistent with the plan and logs. Item 1 slightly mislabels the plan, whose line 78 says "about 1 µs" against the two-term series and line 427 against eq. 2.6. Item 4 says the plan was wrong, but the plan already offered angle addition as the way down. Item 7's cause is inferred.
15. **Lead entries: confirmed.**
    - 704 pairs (8, 526, 25, 145) recompute.
    - The 09:50 correction's arithmetic and F9 line numbers check.
    - The space-weather rulings are consistent with the copy script and the check.

**Not done:**
- No `sensitive` window, so nothing was re-timed.
- No re-fit of F6's (A) fits, and no run of F6's (C) fits.
- No full-size F7; I ran a 1-object, 1-hour mini version.
- `tools\swprobe-f` and `tools\gpcheck-f` were not re-run.
- F9 was not re-timed.

**What the brief got wrong:**
- It does not mention that F8 version 2 reads `studies\debris-e\logs\build.003.log` and `e4_gate.001.log`, which a copy of only `src\` and `tests\` lacks.
- It lists `f6_pairs.001.tsv` as a source for the bc and Cd ranges, but that table does not carry them.
