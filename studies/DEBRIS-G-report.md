# DEBRIS-G's report (phase 2)

The agent's final message, which is its report, filed verbatim by cft-debris's lead at 2026-11-17 11:36:29 -0700 with `cft-debris-ledger\dispatch\file_report.py`. Model claude-sonnet-5-5; final message timestamped 2026-11-17T18:35:34.227Z (UTC). Harness usage: <subagent_tokens>349037</subagent_tokens><tool_uses>17</tool_uses><duration_ms>393256</duration_ms>. The text below is identical in the agent's own transcript and in the completion notice the lead received (as sent); a one-character change was shown to break that comparison. Body SHA-256 `e200b16556ab983a596d77fec666e6f3c6b2c8a6289286e84e4c4efff7419af1`.

---

**DEBRIS-G phase 2 report.** Every G1 to G5 criterion passed on the box, and G3's cross-machine comparison passed. I committed nothing. My phase 2 desktop use was 1.3 of 10 CPU-min by cycles, all at W=1. B0114 is released.

**Built.**
- **Population:** 2,686 sets, equal to the lead's count, and 0 excluded at 200 km. The file has 10,744 lines.
- **Driver and harness:** the driver `m1g.c`, the harness `g_harness.py`, `g_calib.c`, `g_stage.py` and `g_pop.py`. The harness ran on the box without a fix.
- **Analysis:** `g_analyze.py`, whose own checks A1 to A7 pass, and `g_f9data.py`.
- **Records:** `studies\DEBRIS-G-build.md`, and a manifest of 43 files, all OK.
- **Earlier-study checks:** the seven pass: 32, 29, 54, 136, 73, 60 and 61, with no `__pycache__`.

**Gates (MEASURED, box logs).**
- **G1:** B1 to B6 pass. C1 to C5 each failed as specified:
  - C2: 2.84% foreign load.
  - C3: void on CPU share.
  - C4: void on start time.
  - C5: the lag passed 15 s at step 62, after 16.2 s.
- **Clock:** the loop agrees with the kernel's reading at 1 worker (+2.76%) and differs at 36 (−7.33%). So every clock is the kernel's reading only. Why they differ is open: the loop's one add per cycle is believed, two threads share each core, and the kernel may be reporting the governor's request.
- **G2:** at all 8 kind-modes, Q2 to Q5 equal Q1 for all 64 objects. Each control differed in exactly object 23.
- **G3:**
  - The inputs' SHA-256 and the driver's parsed-value hashes are equal on both machines.
  - 0 of 16 objects differ at all 8 kind-modes, the C-library native kinds included (largest position difference 0 m).
  - On each machine native64-cr equals cft64 and native32-cr equals cft32.
  - The comparison control flagged exactly its object.
  - This covers 16 objects over 240 steps, for these two compilers and C libraries only.

**G4 (59 of 59 valid, worst foreign load 0.084%, all 45 D checks pass).** Capacities are X at W=36, L=64, median of 3. All are extrapolations, since the runs carried at most 2,304 objects.

| kind-mode | capacity (objects at real time) |
|---|---|
| native32 | 18,526,551 |
| native64 | 18,259,424 |
| native64-cr | 57,040 |
| cft32 | 19,828 |
| cft64 | 15,322 |
| cft128 | 9,564 |
| cft256 | 4,332 |

- **Efficiency:** it is 0.76 to 0.78 at W=9 and W=18, and the kernel's mean clock falls from about 3,590 to 2,800 MHz over the same range (ratio 0.78). Efficiency divided by that clock ratio is 0.97 to 1.01 for every kind, so the loss is the clock (inferred, on the kernel's reading).
- **Hyperthreads:** X(36)/X(18) is 0.94 to 1.04, and 1.106 for native64-cr. So the second thread adds almost nothing.
- **Faster configurations, beside the capacity:** for cft32 and cft64, X(18) is above the W=36 capacity (21,111 and 15,929).
- **cft64 at W=27:** X(27)/X(36) is 0.7512 against 27/36 = 0.7500, with wall times of 85.58 s and 85.71 s. The slowest core-sharing workers set the wall time (inferred).
- **Lanes:** L=8 costs 1 to 8% against L=64. L=256 adds 5 to 6% for the native kinds and under 1% elsewhere.
- **Spread:** the 3 repeats differ by at most 0.24%.
- **Memory:** every worker's own peak was 24 to 32 MB.

**G5 passes at cft256,** which decision 4's rule chose (4,332.4 ≥ 1.25 × 2,686). It ran 36 workers for 1,200.00 s.
- Every step finished at least 5.584 s before its deadline. The worst step's compute time was 9.42 s of 15 s.
- The busy-share mean is 0.613. 1/0.613 = 1.63 against capacity/N = 1.613, from independent runs.
- Worker 35 holds 61 lanes, and its step time is 0.820 of the others', against 61/75 = 0.813.

**The 2,455 MHz mean clock, from the code (`g_harness.py`, lines 441 to 463).** The sampler reads every pinned CPU's `scaling_cur_freq` once a second, from just before the release until all workers have reported, whether or not the CPU is computing. A paced worker sleeps 39% of each step, so the mean includes idle readings. If the busy 61% read as G4's 2,795 MHz, the rest would read about 1,917 MHz. That split is inferred, because the log holds only the means.

**The F9 ratio.** G4's X at W=1 over F9's figure is 1.002 to 1.015 for native32 and native64, 0.917 for native64-cr and 0.923 to 0.951 for the cft kinds.
- F9 filled its lanes from DEBRIS-E's 8 hand-set states, which include exact zeros. G4 used the population's states.
- On the desktop, at W=1 and in two back-to-back runs, the population cost 1.09 to 1.15 times LANES8 per step for native64-cr and cft256. That matches the gaps (1/0.917 and 1/0.923).
- For cft64 the repeats differed by 0.17, so my pre-set criterion does not read it.
- This is inferred as the cause. It is a desktop ratio only, not isolated on the box.
- It does not explain the native C-library kinds, which I did not test.

**Controls that failed:** none beyond the specified failures above.

**Could not settle:**
- why the loop and the kernel differ at 36 workers;
- the box-side cause of the F9 gap, and whether F9's short cft runs carried cold-start cost.

**Not done:**
- no replicas in G5;
- no population above 9,216 objects;
- no thread workers, and no Arc card;
- no calibration under M1's own load;
- G2 was not re-run on the desktop at W≤4.

**What the brief got wrong or underspecified:**
- **Efficiency at W=36:** 0.37 to 0.43 is below 0.5, the floor 18 cores give if hyperthreads add nothing.
- **Capacity at W=36:** it sits below X(18) for cft32 and cft64.
- **G2 time:** about 7 minutes on the box, against the plan's 18 minutes if run serially.
- **My own slips:**
  - 626 CPU-s on one sweep test before I had a W limit.
  - W up to 48 on the desktop before your limit reached me.
  - The text of my earliest script versions was overwritten before I saved it. `g_analyze.001.log` is superseded for that reason; the earlier desktop logs are in `logs\earlier\`.
  - `m1g.c` carries a desktop downloads path as its default when `M1_DOWNLOADS` is unset, as `m1f.c` does. The box ran with the variable set.

Files are in `C:\Users\logan\source\repos\cft-debris\`:
- studies\DEBRIS-G-build.md
- studies\debris-g\MANIFEST.sha256
- studies\debris-g\logs\g_analyze.002.log
- studies\debris-g\logs\g_f9data.001.log
- studies\debris-g\logs\box-compare\g_g3cmp.002.log
- tests\g_analyze.py
- tests\g_f9data.py
