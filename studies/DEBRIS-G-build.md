# DEBRIS-G build report: M1 at scale on amd-arc-box

cft-debris, MIT licence. Written by DEBRIS-G, 2026-11-17 (phase 2). Labels: MEASURED (a run's own output, with its log), COMPUTED (arithmetic from labelled inputs), INFERRED (a reading no run isolates), BELIEVED, READ. Every box figure is the lead's run of the harness below, on amd-arc-box (Xeon E5-2697 v4, 18 cores, 36 threads, gcc 13.3.0, kernel 6.8), in B0107 (`sensitive`) for G4 and G5. No desktop time here is a measurement. Per-object data (the population, every final state) are in the ledger's `debris-g\`, not in this repository; the logs name objects by index only.

**Narrowed at the merge.** After verifier-G's report, the lead made two narrowings and four additions. Each is marked in the text and listed in §7.

## 1. What was built

| file | what | SHA-256 |
|---|---|---|
| `tests/g_pop.py` | P1: the population | 544d92489b48002606f8f6804c3ddc44a1825fa15cbb3a22faf4a93a7fd718ba |
| `tests/m1g.c` | P2: the batch driver, linked to M1's `src/` and libcft | f227dd5b5abb4db6eeba5c32f138a47d9ea27df20707a82bdba4a18cad641102 |
| `tests/g_calib.c` | G1's clock loop (8 dependent `add` per iteration in inline assembly, a volatile store, a run-time count) | 7b06abcbb3e0bd1b84c1d3a9cfebfe44a08bde4e01bb32aaea5145f000bccc0b |
| `tests/g_harness.py` | P3: modes build, smoke, g2, g3, g3cmp, calib, controls, sweep, paced (standard library only) | 52284f71e5093e9e296b77ca5e9fddba2506d4c9df17ceae37381bc159269a6d |
| `tests/g_stage.py` | lays out `in/` and `EXPECTED.sha256` (src/ taken from commit 1646c96 by `git show`) | 37b70c50a10a52f4858f079b34e68ca9b8521a2f3bd94dcc1659776ef5503efa |
| `tests/g_analyze.py` | phase 2: recomputes G4's and G5's figures from the box's logs | 50565699e275d8493fc3d8b8483046e7e67aa35ea99bba47e1d993b164b99b35 |
| `tests/g_f9data.py` | phase 2: tests whether the states move a step's cost (section 6) | 2321e3dfeb6d04d296e347a81965fef4a3b6d69964de5b817b9ceb7d457c38d0 |

`src/` is byte for byte as at commit 1646c96: `EXPECTED.sha256` (77d07f81f251e5d22cc49e8e91fe750fe2d0a1947edcad5c5d42150eeea35d1a) lists its 18 files, and the harness's B1 asserted them on both machines (MEASURED, `g_build` logs). Every script version that wrote a kept log is in `studies/debris-g/scripts/` under its hash; the box ran harness 52284f71e509 and driver build 57c98729034c.

**The driver** runs a slice of the population (first, count, stride, optional reverse) in batches of L lanes, step-major: each of the S steps advances every batch by one rk4 step of 15 s. It runs ceil(S/5,760) passes from the initial states, each of 5,760 steps but the last; X counts every pass; the end checks (finite, radius above 6,498.137 km) run at every pass. It prints `READY`, blocks on the byte `G`, and times from its read of that byte to the last step's end (Linux `CLOCK_MONOTONIC`, `CLOCK_PROCESS_CPUTIME_ID`; Windows `QueryPerformanceCounter`, `QueryProcessCycleTime`/2.5, desktop only). It reports its CPU at READY, at the release and at the end, its CPU (`sched_getcpu`) and affinity at start and end, and its peak resident memory. Paced mode records every step's lag.

**How to build and run** (from a run root holding `in/`, as the lead did): `python3 -I -B in/g_harness.py <mode> . [options]`, modes in the order build, smoke, calib, controls, g2, g3, sweep (`<booking> --kinds a,b`), paced (`<booking> --g4 <runs.json>[,...]`). The harness works with relative paths, never overwrites a log, and kills only processes it started.

## 2. P1, the population (MEASURED, `logs/g_pop.001.log`)

2,696 rows in S0's four files, all ephemeris type 0; 2,686 distinct element sets (the lead's count over the objects Orekit built: 2,686, equal); 0 excluded by the 200 km perigee screen (smallest perigee kept 270.1 km); 10,744 lines (4 x 2,686: base objects in a seeded permutation, then three replicas rotated about z by k x 137.50776405 degrees). Population SHA-256 016f380e74ad4c090add550ad59d52229f4b6b1214e403fb6ac77a7aea6f5428. E = 2026-11-02 00:00 on M1's TDB scale, jd_epoch 2461329.5, t0 = 1,468,800 s; seed 20261117; bc = cram = 0.01 m^2/kg; all fixed in the script and in `DEBRIS-G.md` before S0's values were used. Kepler's equation was solved to 1e-15, and radius and vis-viva held to 1e-9 (P-c, P-d, with a control that the test can fail).

## 3. Gates

**G1 (MEASURED, box: `box/g_build`, `g_smoke`, `g_calib`, `g_controls`; desktop: `logs/desktop-v52284f71e509/`).**
- B1 to B6 pass on both machines, and libcft.a on the box has the SHA-256 DEBRIS-F's box build had (14f95b22...). The disassembly of the clock loop is in `g_build.001.log`.
- Smoke: all eight kind-modes, 4 lanes, 2 steps.
- Controls, each failed as specified: C1 (changed source fails the check); C2 foreign load 2.84% against 2%; C3 void on CPU share; C4 void on its start time (the only failed criterion); C5 the lag passed 15 s at step 62, after 16.2 s (limit 120).
- **The clock.** At 1 worker the loop implies 3.557 GHz against the kernel's 3.461 GHz (+2.76%): AGREE. At 36 workers it implies 2.589 GHz (2.543 to 2.634) against the kernel's 2.794 GHz (-7.33%): DIFFER. By G1's rule every clock below is **the kernel's `scaling_cur_freq` reading only**. Why they differ is open: the loop's one addition a cycle is BELIEVED, two threads share each core at 36 workers, and the kernel's reading may be the governor's request (plan-verifier-G, from recall, not checked). No run here separates these. The calibration does not show the clock under M1's own load.

**G2 (MEASURED, `box/g_g2.001.log`).** At all eight kind-modes, Q2 to Q5 equal Q1 bit for bit for all 64 objects (40 steps; the NaN rule applied, no NaN occurred), and each control, with object 23's x moved one ulp of the input format, differs in exactly object 23: 40 of 40 partition and control lines pass. What this covers: batch composition, worker count and order do not change a final state, for these 64 objects and 40 steps. verifier-G re-ran G2 on the desktop at seven of the eight kind-modes (not native32-cr), on the same 64 objects and 40 steps, with a partition of its own, and found every partition equal to Q1 and the control differing only in object 23 (added at the merge).

**G3 (MEASURED, `box/g_g3.001.log`, `logs/earlier/g_g3.001.log`, `logs/box-compare/g_g3cmp.002.log`).** The 16 objects, 240 steps, one worker, one batch of 16.
- The inputs agree: the population, frame table, gfc, DE421 and its header have equal SHA-256 on the desktop and the box, and every kind-mode's driver hash of the parsed values is equal.
- cft32, cft64, cft128, cft256, native32-cr and native64-cr are bit for bit equal across the two machines (0 of 16 differ at each). On each machine native64-cr equals cft64 and native32-cr equals cft32 (0 of 16). So the first-step finding procedure was not needed.
- native32 and native64 with the C library's functions (no pass condition): 0 of 16 differ between the machines, largest position difference 0 m. That is the glibc of the box against mingw's, for this sample only.
- The control (one bit flipped in object 5's z of cft64, in a copy) flags exactly that object. The comparison is bit for bit; it says nothing for other compilers or other populations.
- At the merge, the lead re-ran G3's desktop half from a clean staging, in two groups of four kind-modes to keep the desktop at 4 workers. A comparison of the lead's own, with a control, found every object's output file byte-equal to the box's and to this report's desktop run, at all eight kind-modes, with the inputs and the drivers' hashes equal too (added at the merge).

**G4 (MEASURED; recomputed by `tests/g_analyze.py`, `logs/g_analyze.002.log`; its checks A1 to A7 pass).** 59 runs in three sweeps (A: native32, native64, native64-cr; B: cft32, cft64; C: cft128, cft256), 59 valid, none void, none repeated; the worst foreign load was 0.084% (criterion 2%); all 45 D checks pass (worker 0's final states at L=64 hash equal across every W and repeat of a kind-mode). X is object-seconds summed over workers / wall time from the first release to the last end, per run; each ratio below divides these rates, never CPU times. Pinning as in the plan (worker w on CPU w).

| kind-mode | **capacity: X, W=36, L=64, median of 3** | X, W=1 | X, W=18 | efficiency at W=18 | X(36)/X(18) | X(L=8)/X(L=64) | X(L=256)/X(L=64) | spread of 3 repeats | X(1) / F9's |
|---|---|---|---|---|---|---|---|---|---|
| native32 | 18,526,551 | 1,329,147 | 18,552,326 | 0.775 | 0.999 | 0.917 | 1.061 | 1.0004 | 1.015 |
| native64 | 18,259,424 | 1,291,561 | 17,613,716 | 0.758 | 1.037 | 0.922 | 1.049 | 1.0011 | 1.002 |
| native64-cr | 57,040 | 3,702 | 51,579 | 0.774 | 1.106 | 0.987 | 0.996 | 1.0006 | 0.917 |
| cft32 | 19,828 | 1,506 | 21,111 | 0.779 | 0.939 | 0.946 | 1.007 | 1.0004 | 0.947 |
| cft64 | 15,322 | 1,137 | 15,929 | 0.778 | 0.962 | 0.950 | 1.005 | 1.0024 | 0.946 |
| cft128 | 9,564 | 684 | 9,587 | 0.779 | 0.998 | 0.961 | 1.001 | 1.0005 | 0.951 |
| cft256 | 4,332 | 299 | 4,176 | 0.776 | 1.038 | 0.974 | 1.002 | 1.0003 | 0.923 |

- **Capacity** is the number of objects the configuration would carry at real time if its cost per object held. The runs carried at most 2,304 objects at L=64 (9,216 at L=256), so every capacity is an extrapolation of the cost per object; the native kinds' millions most of all. A faster configuration, reported beside, never in its place: cft32 X(18) = 21,111 (6% above its capacity), cft64 X(18) = 15,929 (4% above), cft128 9,587; the fastest run of native32, native64 and cft256 was W=36, L=256 (19,656,396; 19,154,210; 4,340).
- **Efficiency.** At W=9 and W=18 the efficiency is 0.76 to 0.78 for every kind. The kernel's mean clock was about 3,590 MHz at W=1 and 2,790 to 2,810 MHz at W=9 and above (ratio 0.78), and efficiency divided by the clock ratio is 0.99 to 1.01 for the cft kinds and the native64-cr, and 0.97 to 1.00 for native32 and native64 (COMPUTED, per kind in the log). So the loss from W=1 to W=18 is the clock falling as cores are loaded (INFERRED: it rests on the kernel's reading, and G1 showed it can differ by several percent). cft64's extra points: efficiency 0.958 at W=2 (3,514 MHz), 0.881 at W=4 (3,245 MHz).
- **Hyperthreads add almost nothing:** X(36)/X(18) is 0.94 to 1.04 for the cft kinds and the native kinds, and 1.106 for native64-cr. Efficiency at W=36 is 0.37 to 0.43 (the 18 cores explain the floor of about 0.5 less the clock). cft64 at W=27 gives X(27)/X(36) = 0.7512 against 27/36 = 0.7500, with wall times 85.58 s and 85.71 s: every worker does the same steps, so the run ends with its core-sharing workers (INFERRED).
- **Lanes:** L=8 costs 4 to 8% against L=64 for the native32/64 and the cft32 to cft128 kinds (2.6% for cft256, 1.3% for native64-cr); L=256 adds 5 to 6% for the native kinds and under 1% elsewhere (the per-batch overhead is the likely cause: INFERRED).
- **Memory:** every worker's own peak resident size was 23.6 to 32.0 MB over all 59 runs (L=256 included).
- **Spread:** the three repeats differ by at most 0.24% (largest / smallest). They ran one after another, so this says nothing of how a later window would differ.

**G5 (MEASURED, `box/g_paced.001.log`, B0107).** Decision 4's rule chose cft256 (capacity 4,332.4 >= 1.25 x 2,686 base objects) and the harness asserted it from G4's three runs.json files. 36 workers, 75 lanes each and 61 on the last, real time, 80 steps, wall time 1,200.00 s. **Pass:** every worker's lag is at most -5.584 s, so every step of every worker finished at least 5.584 s before its deadline (worst compute time of a step 9.42 s of 15 s); every worker exited 0, the end checks passed, V2, V4, V5, V6 held, the foreign load was 0.064%. Medians of worker lag, -5.67 to -5.81 s, except worker 35 (-7.40 s) and worker 17 (-6.52 s). Worker 35's step time against the others' is 0.820, and its lanes 61/75 = 0.813 (COMPUTED); worker 17 shares its core with CPU 35 (INFERRED: its sibling worked less). Busy share of wall time per worker: mean 0.613, from 0.506 to 0.622, and 1 / 0.613 = 1.63 is within 1.2% of capacity / N = 1.613, from independent runs (COMPUTED; narrowed at the merge). The headroom is therefore about 1.6 times at cft256. A step of 15 s is the unit; the criterion tests lateness, not a count of objects the machine could add.

**The mean clock, 2,455 MHz.** The harness's sampler (`g_harness.py`, lines 441 to 463 and 505 to 509) reads `scaling_cur_freq` of every pinned CPU once a second from just before the release until all workers have reported, whether or not the CPU is computing, and averages the readings over time and CPUs. A paced worker sleeps for 39% of each step, so the mean contains the readings taken while CPUs were idle or waking. If the busy 61% read as G4's 2,795 MHz, the rest would read about 1,917 MHz (COMPUTED from the two means; the split is INFERRED: the log holds only the means). It is not a measurement of the clock under load.

## 4. The F9 ratio (open in part)

G4's X at W=1, L=64 against F9's box figure (`F9_POD`): 1.002 to 1.015 for native32 and native64, 0.917 for native64-cr, 0.923 to 0.951 for the cft kinds. F9 filled its lanes from DEBRIS-E's eight hand-set states repeated (several with exact zeros), and timed cft kinds over 2 to 4 steps; G4 timed 30 s of the population's states. `g_f9data.py` ran the G4 driver on the desktop at W=1, 64 lanes, on the first 64 population objects and on LANES8 repeated eight times, alternating the order, twice (`logs/g_f9data.001.log`). Population over LANES8, per step: native64-cr 1.094 and 1.124; cft64 1.083 and 1.257; cft256 1.147 and 1.122. The script's header states a criterion: the states are read as moving the cost only if both repeats agree on the side of 1.0 and differ from 1.0 by more than they differ from each other. The script does not evaluate it, and no record shows it was fixed before the data: the header was last written at 11:31:39 and the log at 11:33:18, and an earlier console run was not logged. Read by hand, native64-cr and cft256 meet it, and cft64 does not (its repeats differ by 0.17); cft32 and cft128 were not in the test. **So, in one desktop functional test of two repeats, the population's states cost 9 to 15% more per step than LANES8's for native64-cr and cft256, about the size of their gaps (1/0.917 = 1.09 and 1/0.923 = 1.08). That the states cause the box's gaps is BELIEVED for those two kinds, and open for the others.** (Narrowed at the merge.) It is a desktop, ratio-only test, and no box run isolates it, so the box's gap is not proved to be this. The native C-library kinds were not tested; their ratio near 1 is not explained. The mean clock at W=1 (3,571 to 3,598 MHz) does not differ between kinds, so the kernel's reading does not explain the cft gap. The parts left open: whether F9's short cft runs also carried cold-start cost.

## 5. Limits

- The positions are not the sky's: TEME's axes are taken as GCRS's, mean elements as osculating, the set's UTC epoch and E's TDB label as one scale (about 69 s). The replicas are rotated copies, not independent orbits.
- One population epoch; passes restart from the initial states each day, so a step's cost at day 2 or later is not measured. Capacities come from at most 2,304 objects (G4, L=64) and 2,686 (G5), one machine, one window, one 20-minute paced run.
- The clock is the kernel's reading only.
- X's timed region includes the end checks of every pass but the last. The last pass's end checks run after the timer stops (`m1g.c` lines 437 and 459). So in runs of more than one pass, X counts that work beside the steps (added at the merge).
- The foreign share is clamped at zero (`g_harness.py` line 504), so a negative accounting residual would not show. verifier-G found no case where this changes a verdict (added at the merge).
- G2 and G3 cover 64 and 16 objects, 40 and 240 steps, and two compilers and two C libraries; their equality is bit for bit and extends no further.
- The desktop functional tests ran at W up to 48 before the lead's limit of 4 reached me; G2's and the sweep's desktop test logs are in `logs/earlier/` under script versions whose text I did not keep (listed in the manifest). `logs/g_analyze.001.log` was written by an earlier version of `g_analyze.py` (before two lines were added; its text was not kept) and is superseded by `g_analyze.002.log`. Every claim here rests on logs whose script version is kept. `m1g.c` carries the desktop downloads path as its default when `M1_DOWNLOADS` is unset, as DEBRIS-F's `m1f.c` does; the box ran with the variable set.

## 6. Not done, and what the brief got wrong

Not done: no replicas in G5, no population above 9,216 objects, no thread-based workers, no Arc card, no per-worker clock, no repeat of the box's G1 clock calibration under M1's load. The brief's "parallel efficiency" at W=36 mixes the hyperthreads and the clock (0.37 to 0.43 is below the 0.5 that 18 cores would give if hyperthreads added nothing); the brief's G4 rule makes a capacity at W=36 that is lower than X(18) for cft32, cft64 and cft128, and says so only through "beside it". The brief's G2 estimate (about 18 minutes serial) was beaten by running the partitions together (about 7 minutes on the box, 07:53:10 to 08:00:05).

## 7. Narrowed at the merge

The lead made these changes after verifier-G's report (`studies/DEBRIS-G-verifier-G-report.md`): two narrowings and four additions, each marked in the text. Everything else is as DEBRIS-G wrote it.
- DEBRIS-G's own report stays verbatim in `studies/DEBRIS-G-report.md`.
- This report as DEBRIS-G left it is kept in the ledger, as `filed\DEBRIS-G-build.as-reported.md`.

**Narrowed:**
1. **§4, the F9 ratio** (verifier-G, item 8; checked by the lead against the script and the files' times):
   - the unlogged console run no longer supports anything;
   - the criterion is described as what it is: prose in the script's header, which the script does not evaluate, with no record that it came before the data;
   - the conclusion now covers only native64-cr and cft256, labelled BELIEVED. cft64 fails the criterion, and cft32 and cft128 were not in the test.
2. **§3, G5:** "1 / 0.613 = 1.63 matches 1.613" became "is within 1.2% of": 1.14% from the printed figures (verifier-G, item 4; merge-check-G corrected the lead's first figure, 1.1%).

**Added:**
3. **§3, G2:** verifier-G's desktop re-run, at seven of the eight kind-modes, with a partition of its own.
4. **§3, G3:** the lead's re-run of the desktop half. verifier-G's budget was spent before G3, so the lead ran it; it confirms the cross-machine equality at all eight kind-modes.
5. **§5:** X's timed region includes the end checks of every pass but the last (merge-check-G corrected the lead's first wording, which said every pass).
6. **§5:** the foreign share is clamped at zero (verifier-G, item 5).

**In DEBRIS-G's own report,** narrowing 1 covers lines 60 to 62. "My pre-set criterion" (line 61) is not shown to have been set before the data, and "inferred as the cause" (line 62) now stands as BELIEVED, for native64-cr and cft256 only. Line 53 says "against", not "matches", so narrowing 2 does not touch it.

**Notes from verifier-G's report, not narrowed:**
- G5's per-worker busy shares are not in its log, only their mean, minimum and maximum, which is all §3 gives.
- verifier-G read `g_analyze.py`'s checks A1 to A7, but did not run them with a forced failure.
- native32-cr was not in verifier-G's G2 re-run. The box's G2 log covers it.
- No one re-ran the F9 test to separate its criterion from its data.
