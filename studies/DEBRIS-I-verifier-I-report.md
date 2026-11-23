# verifier-I's report on round DEBRIS-I

The agent's final message, which is its report, filed verbatim by cft-debris's lead at 2026-11-23 12:28 -0700 with `cft-debris-ledger\dispatch\file_report.py`. Model claude-sonnet-5-5; final message timestamped 2026-11-23T19:27:59.245Z (UTC). Harness usage: <subagent_tokens>227140</subagent_tokens><tool_uses>107</tool_uses><duration_ms>1239478</duration_ms>. The text below is identical in the agent's own transcript and in the completion notice the lead received (after unescaping the notice's HTML entities); a one-character change was shown to break that comparison. Body SHA-256 `9ebabe789b45edd97e2c486ce395f683f5664e04448623755cebcb10110e5c34`.

---

**verifier-I report: no defect found in any of the ten attacks.** I never connected to the box and edited nothing outside my scratch. I used about 13.0 of 25 CPU-minutes (cycles/2.5e9), with at most 4 processes at once.

**Attack verdicts**

1. **I1 — confirmed.**
   - I rebuilt libcft from 9e8ff270, plus `m1i` and `i_run`.
   - I recompiled `program-d7` at fp64 and fp256 and got the image hashes in `compiles.tsv`: `d0a6558b…` and `974d6760…`.
   - On 4 test-seed objects I chose myself (rows 11, 29, 41, 58) and one 40-step segment, the executor equals `lang.run` bit for bit at both formats, with 0 marks.
   - C3 and C4 bite.
   - Note: C3's planted one-ulp GM change moves only 1 of 14 values at fp64 and 4 of 14 at fp256. It passes, because the control needs any difference.
2. **I2, parts (b) and (c) — confirmed.**
   - For 10 gravity and 10 tides lanes at binary256, the program equals M1's kernel exactly.
   - Both lie within 1e-67 to 1e-71 relative of my own mpmath reference at 300 digits. The bound is 2^-200, about 6.2e-61.
   - My reference reads the C and S values straight from the `.gfc` for degrees 2 to 7. For tides it uses the plain point-mass formula for the Sun and the Moon.
3. **I3's configuration — confirmed.**
   - M1's switches are `central 1, nmin 2, nmax 7, sun 1, moon 1, drag 1, srp 0, nbands 28, frame 1`. That matches the program's degree 7 with 28 bands.
   - The tolerances in `i_analyze.py` match the plan: S = 7e6 m and 8e3 m/s, T_frame = 1e-3 m and 1e-6 m/s, 64·n·2^-p·S with p = 53, 113 and 237, and 144 boundaries of 40 steps.
   - I recomputed the shares of tolerance for 3 objects of my own choosing (batches 1, 4 and 6), in exact arithmetic from `box\out\i3\`.
   - The largest shares are 0.0093, 0.017 and 0.0064 at fp64, and 1.1e-4 to 1.3e-4 at fp128 and fp256. The medians are 2.6e-4 to 5.3e-4 at fp64 and 4.2e-6 to 4.9e-6 at fp128 and fp256, consistent with the report's 2.8e-4, 4.5e-6 and 4.5e-6.
   - The program's t equals M1's host t at every boundary.
   - Every lane byte is 0x10, and every `marks.bin` is empty.
4. **The controls bite — confirmed.**
   - C3 and C4 bite (attack 1).
   - `i_harness.py i2` re-run: 28 checks, 0 failed, so C5 to C11 bite.
   - `i3d` re-run: C12 bites, and C13 FAILS as specified (0 values over the tolerance). I also saw the same 5 checks with 1 failed, as DEBRIS-I did.
5. **The frame's bound — confirmed.**
   - I took 600 stage times of my own, from 60 blocks drawn with a seed of my own. The largest |M − M1| is 1.4e-13, against a bound of 1e-12. The largest |Ω − M1| is 4.8e-15, against a bound of 1e-14.
   - That Ω figure is 48% of its bound, against the 32% the report gives for its 1,962 times.
6. **No data, image or bank in the repository — confirmed.**
   - All 34 `.cftl` sources have only zero param defaults, and the only numeric literal in the `let` lines I scanned is `1`.
   - There is no `.cftp`, bank or binary file under `studies\debris-i` or `tests\`, and none over 1 MB.
7. **I5's records — confirmed.**
   - All 21 runs are valid, with foreign share at most 8.0e-4, and X equals objsec/wall for every run.
   - The runs total 53.4 minutes, which fits the 11:00 to 11:53 window.
   - I recomputed the ratios: 2.884, 2.847 and 2.570 against M1 at the same forces. Against DEBRIS-G's cft256 rates they are 15.49, 15.41 and 13.79.
   - The wording "about 59,700 objects" is correctly labelled an extrapolation past the 2,304 objects run.
8. **The repository scan — confirmed.**
   - My scan of 134 files found only counts, instruction numbers and hashes. The one catalogue-like token, `58515`, is a drag-table scale height from `m1_consts.h`.
   - There is no `/home`, Windows user path or Omega hex.
   - **`box_build.001.log`:** it differs from the ledger original in exactly lines 19 and 78 (two paths rewritten to `<root>`).
   - **`i2_redacted.001.log`:** it equals `held\i2.001.log` apart from the Omega line. That line becomes the hash `cf7b9b0e…`, which is the SHA-256 of the three encodings joined by single spaces.
9. **The model gap — confirmed.**
   - From the `m1-prog` and `m1-full` native64 files, step 5760, I recomputed all 64 objects: median 343.14 m, largest 2312.31 m.
   - Ten values differ from the `gap_per_object` file only by its six-significant-figure rounding.
   - Both runs have the same seed-values hash, `t0`, table and `frame 1`. They differ only in `nmax` 7 against 20 and `srp` 0 against 1.
   - I also checked the one-force-at-a-time runs: degree 20 alone gives 346.8 m median and 2312.5 m largest. SRP alone gives 4.0 m and 18.6 m.
10. **The stated departures — confirmed, each says what it found.**
    - Degree 8's compile, I6's stop (1,200.9 CPU-s, "not determined") and C10's corrected margin all say what they found.
    - C10's corrected margin is arithmetic I checked: 3.386e-17 × 6.43e-3 = 2.18e-19.
    - **Note on `i2.001`:** DEBRIS-I's I2 comparison log, kept as `i2_redacted.001.log`, still ends "28 checks, 1 failed" (the C10 b128 margin). The corrected margins are in a separate run. No fix is called a pass in the log itself.

The CPU figures are cycles/2.5e9. The `GetProcessTimes` figures were lower, as expected on this host.

**Notes, not defects**
- At fp128 and fp256 the shares are identical, so the T_frame term decides I3 there. With T_frame at 1e-3 m, a wrong frame block moves positions only about 3e-5 m. C13 therefore cannot fail, and I3's frame sensitivity is far coarser than I2(e)'s.
- `i1` in smoke mode labels its checks "4 segments", though I ran 1.
- The 59,700 objects is the degree-7 program. It is not comparable with G's 4,332, which is M1's full model.
- The G4 ratio divides a single I5 run by the median of three G runs.

**What I did not do**
- I did not run C5 to C11 at fp64 or fp32 beyond what `i2` does.
- I did not re-run I1 on the six part systems, or I4, part B or I0.
- I did not re-run the box's marks replay. There were no marks.
- I did not independently re-scan the lead's 65 hex-token hits. I scanned for numbers and hashes myself instead.
- I did not recompute drag (f) or the Chebyshev bodies (d) in mpmath.
- Before reporting I ran the ten earlier-record checks: 32 OK in `SHA256SUMS`, 29 files in `debris-a`, B/C/D/E/F/G/H at 54/136/73/60/61/43/149 OK, and no `__pycache__`.

**What the brief got wrong**
- Attack 2 names parts (b) and (c) without saying (c) has six outputs, the Sun and then the Moon.
- Attack 3's "recompute for 3 objects from `i3\`" needs the program's lane order. It follows the sorted object order in the `m1-prog` files, and I confirmed it by exact t equality and small differences.
- `box-stage\r1\in` holds no image manifests, so a verifier re-run recompiles about 15 s per image, 30 s CPU in all.

My files are in `C:\Users\logan\source\repos\cft-debris-scratch\verifier-I\`, and my ledger entry is in `C:\Users\logan\source\repos\cft-debris-ledger\verifier-I.md`.
