# verifier-E's report on DEBRIS-E

The agent's final message, which is its report, filed verbatim by cft-debris's lead at 2026-11-13 07:12 -0700 with `cft-debris-ledger\dispatch\file_report.py`. Model claude-sonnet-5-5; final message timestamped 2026-11-13T14:12:07.989Z (UTC). Harness usage: <subagent_tokens>184689</subagent_tokens><tool_uses>47</tool_uses><duration_ms>878336</duration_ms>. The text below is identical in the agent's own transcript and in the completion notice the lead received (after unescaping the notice's HTML entities); a one-character change was shown to break that comparison. Body SHA-256 `5023876dead11d41ecedddc6b45e370018c555b5ec368a6fbc7d1226b09ff880`.

---

**verifier-E report.** Every re-run passed, and I found no defect that sends work back. I found 5 narrowing notes, listed under items 3, 4 and 6, 7, 9 and 10.

Scratch is `cft-debris-scratch\verifier-E\`. I used about 8.0 CPU-minutes by cycles (482 s), plus about 1 minute of builds that were not wrapped. Wall time was about 40 minutes, and I did no timing. The plan hash `9c5d0b9b…` and the build report hash `636ed5cd…` both match.

1. **Build from clean: confirmed.**
   - The archive hash is `e01003cc…`.
   - I ran `make -C host CC=gcc OS=Windows_NT TMP=/tmp TEMP=/tmp libcft.a`. My `libcft.a` has the same hash as DEBRIS-E's, `f0eec4f2…`.
   - `bash tests/build.sh <host> <out>` printed BUILD PASS with all 5 criteria.
   - `FLT_EVAL_METHOD` is 0. Every native object holds `vfmadd`: 12 at O2 and negctl, 1 at O0, 23 in fast. No native object has an undefined `fma`, `fmaf`, `sqrt` or `sqrtf`. The `nm -u` check is exact; my own `objdump` grep for calls was noisy and added nothing.
   - The commands work as written. The build has no warnings.

2. **E1 with my own lanes: confirmed, with a limit.**
   - I used a new seed, 0x5EED77, with 5,000 lanes and degree-180 batches of 64.
   - All 7 exact kernels are bit-identical, native against cft, at binary64 and binary32.
   - The `--cr` switch really reroutes the calls. The lanes it changes are exactly the lanes where libm differed from cft: 4 in `rot` and 9 in `srp`. The gate would fail if the switch did nothing.
   - **Limit:** the control cannot fail for `exp`, since libm and cft agreed on every lane. It also cannot fail for any binary32 kernel (0 differing lanes).
   - The negative control breaks only column 3 (cos C), in 1,613 lanes at binary64 and 1,602 at binary32. Gravity, central, third body and reader stay untouched.
   - The reordered operation sits in the negctl build's native objects alone.
   - **Beyond the gate:** I built a copy of `m1run.c` in scratch with radii log-uniform from 0.1 m to 1e13 m. Gravity and central were still bit-identical over 3,000 lanes at each width, including 1,345 binary32 lanes with NaN or overflow.

3. **E1's ulp figures: label defect, narrow.**
   - The 1.2e10 ulps is measured on the radiation-pressure kernel's outputs (acceleration and ν), after the penumbra cancellation. It is not the function's output. Neither the report nor the build report's §1 says so.
   - I compared the C library's functions against mpmath on 20,000 arguments, a quarter of them near 1. The worst errors were asin 0.79, acos 0.84, sin 1.60, cos 1.49 and exp 0.50 ulps.
   - **sin/cos figure:** "1 to 2 ulps in 5 of 10,000 lanes" is specific to seed 0xE1. With my seed the rotation kernel's x output differed by up to 32 ulps, in 2 lanes of 5,000. The rotation kernel's output is also post-cancellation.
   - Section 5 of the build report also says "almost every result was still correctly rounded". The C library's sin and cos are not correctly rounded. The statement holds only for kernel results.

4. **E2: confirmed.**
   - 8 lanes × 100 steps: native64 = cft64 and native32 = cft32 at every step, and the z-plant control passes.
   - The scripts are `d6d8fc1763dc` (log 001) and `2e5400caad14` (logs 002 and 003). The diff shows the replacement C1b stated "before its data" and the x plant kept as REPORTED. Log 001's two FAILs are named in the build report.
   - File times cannot prove the replacement was written before its data. They show only that the kept script and log 002 have the same timestamp. The z plant was chosen after the x failure.

5. **E3: confirmed, with a sensitivity note.**
   - I re-ran it in full. L2 gave 7.588e-26 m against B = 6.247e-20 m. The binary128-rounded-central-factor control gave 3.9e-10 m, which is 6.3e9 B.
   - I recomputed B from N_ops (3.05e6) × 2^-113 × 7.1e6 × 30 and got 6.2e-20. The script states it as estimate-based and states it before the data. N_ops was a trial count, not a result.
   - The gate has 1e6 of headroom. It would not see an error between 6e-20 m and 4e-10 m.

6. **E4: confirmed; the unchanged-physics claim is only partly supported.**
   - I ran build 3 with native64 and cft64 at every 30th epoch (96 epochs).
   - Gravity is 1.15e-15, Sun 8.6e-18 and Moon 3.2e-16 m/s², against the tolerance of 1e-11. native64 = cft64 bit for bit.
   - The degree-173 control gave 52.9× TOL (the gate's 98× is the max over all epochs). I added a degree-179 truncation: 16.8× TOL, so the gate resolves single degrees.
   - **"Only the driver changed":** this cannot be checked by hash. Builds 1 and 2 printed no source hashes. The only evidence is file times: every `src\` file was last modified at or before 06:05:38, before build 2 at 06:24. That is mtime evidence only.
   - `m1run.c` holds the lasser modes and did change after E4, so "the driver" includes E4's own front-end. My re-run on build 3 covers that.

7. **E5, E6 and E7: confirmed.**
   - **E5:** 109 points, worst 4.9e-16 AU at cft64. The corrected control P2b is asserted and passes.
   - **E6:** on 1,000 states, gravity is 7.3e-17 m/s², drag 6.8e-14 and radiation 1.3e-15. The three 1% plants broke their tolerances, and the 3 penumbra states are reported only.
   - The scripts `aa4493f7` and `863881d8` differ only by a comment. `e6_orekit.js` changed only the TDB-seconds time scale of the rotation angle. The D1 tolerance of 1e-14 is unchanged.
   - **E7:** the 0.5 m tolerance and its basis (0.029 m × 17) sit in the script from version 1. That first version crashed on REBOUND's API before producing any data. I measured 0.114 m, and the J2 plant gave 1,110 m.
   - The IAS15 diagnosis numbers match the log.
   - **Label defect:** the diagnosis switched radiation pressure on and off, but never turned the shadow off with radiation pressure left on. So "because it does not resolve the shadow's edges" is inferred, not isolated.

8. **E8: confirmed.**
   - Two runs agree, and -O0 equals -O2, for all six kinds.
   - The contracted build differs in 647 and 706 of 808 lane-steps.
   - The restarted segments match, but R4 was run for native64, cft64 and cft128 only. The report says "five restarted segments equal", which I read as unscoped.

9. **E9: matches the log; one claim is overstated.**
   - Every cell, the load range of 5 to 35%, and the capacities (1.73 million, 4,547, 1,568, 986 and 387 objects) recompute from the log.
   - "Most of the cft cost is the six transcendentals" is not supported at binary64. Routing the six calls to libcft costs 0.68 ms at 64 lanes, against 2.24 ms for the whole cft64 evaluation, so about 30%. The build report's narrower "most of the rest" (the excess over the FMA-price estimate) is arguable.
   - The cft256 64-lane cell rests on 4 evaluations. Each cell is a single run.

10. **Report against logs.**
   - "Every gate passes as finally specified" is true in the narrow sense, with E2 and E5 controls and E6's matching replaced.
   - The first-run failures are all reported (E2, E5, E6, E7). E9's "PASS" lines mean only that the run completed.
   - The IAS15 finding is accurate on numbers. Its cause is labelled as fact in the build report (§4 E7) and in §6 item 2 ("is not converged on a model with a conical shadow").
   - "3.6e-6 m, almost all from one lane" matches `e3_lanes`: lane 1 reaches 3.58e-6 m and the others stay at or below 1.0e-7 m. It is labelled a belief.

11. **Records: confirmed.**
    - `MANIFEST.sha256` gives 60 OK and the manifest equals the set of files, 61 in all with itself.
    - The earlier checks give 32, 29, 54, 136 and 73, with 0 `__pycache__`.
    - Every source has the MIT header. There are no binaries or third-party sources.
    - `m1x.dll` lives only in `cft-debris-scratch\DEBRIS-E\build\main`, outside the repository.

12. **Criteria before data: confirmed.** Every log's script hash is kept under `scripts\`, and every current `tests\` file equals a kept version. The controls that failed (E2, E5, E6 and the E7 crash) are reported as failed.

13. **`lead.md` and the premises:** nothing I could contradict.

**Not done:**
- I did not re-time E9 and asked for no window.
- I did not re-run E1's C5 hand check, E3 on other lanes, or E4 on cft128 and cft256.
- I ran E4 at stride 30, not the gate's full 2,880 epochs.

**What the brief got wrong:**
- Item 6 asks for "the physics sources' hashes", but builds 1 and 2 recorded none.
- Item 2's "would fail if it did not" holds only for the binary64 `rot` and `srp` kernels.

My ledger entry is appended to `verifier-E.md`. Nothing of mine is running.
