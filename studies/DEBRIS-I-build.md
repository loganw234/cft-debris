# DEBRIS-I: M1's force model as a cft program on libcft's software executor (build report)

Written by DEBRIS-I, 2026-11-23, for cft-debris (MIT). The plan of record is `studies\DEBRIS-I-plan.md`, draft 3 (SHA-256 `9463559925630a2c5b45f53e04e9c07f0d974f81013d183c74ce61d50bf31fab`).

**Labels.**
- MEASURED: a log in `studies\debris-i\logs\` or `studies\debris-i\box\logs\`, every log naming the SHA-256 of the script that wrote it and of the modules it imported (the versions are kept in `studies\debris-i\scripts\`).
- READ, COMPUTED, ESTIMATE, BELIEVED and INFERRED as in earlier rounds.
- The box's runs are the lead's, made from this parcel's code and staged inputs.

**The manifest.** `studies\debris-i\MANIFEST.sha256` lists every file under `studies\debris-i\`. Per-object data (states, the sample's list, per-object tables) are in the ledger's `debris-i\` only.

**Checked by verifier-I, 2026-11-23** (`studies\DEBRIS-I-verifier-I-report.md`).
- It found no defect in any of its ten attacks. It re-ran I1 on 4 lanes of its own at binary64 and binary256, and recomputed 20 values of parts (b) and (c) in mpmath at 300 digits. It re-ran C3 to C13, recomputed I3's shares for 3 objects, the frame at 600 stage times of its own, I5's ratios and the model gap, and scanned the repository.
- It did not re-run I0, I4, part B or I1's six part systems, and it did not recompute parts (d) and (f) in mpmath.

At the merge the lead narrowed one passage, added two and corrected one, and wrote this note. Each is marked in the text ("narrowed", "added" or "corrected at the merge") and listed in section 9. The text as DEBRIS-I reported it (SHA-256 `4bb10c9f3118be9e983e0e956f56338d1a0714136b5144f4dd549f04cc199006`) is kept at `cft-debris-ledger\filed\DEBRIS-I-build.as-reported.md`.

## 1. What was built, and how to build and run it

| file | what it is |
|---|---|
| `tests\i_gen.py` | the generator: the program's cft source for a degree, format, band count, frame degrees and layout, and the six part systems (`map` systems, one a part, the program's own expressions) |
| `tests\i_vals.py` | every value the driver fills, at each format, by M1's own rounding route; the frame's exact fit; DE421's blocks; the driver's files |
| `tests\i_run.c` | the driver, from DEBRIS-D's `seqrun.c`: libcft's software executor at a depth, run by run and segment by segment, every lane param rewritten at each run's start, t checked at each run's start, every boundary state, lane byte and mark kept; mode `rate` for I5 |
| `tests\m1i.c` | M1's side, linking `src\` unchanged: its kernels at given inputs, its trajectories with the switches set (`--model prog` or `full`, `--nmax`, `--srp`, `--bands`), the frame at given times, and a timed batch run |
| `tests\build_i.sh` | builds M1, `m1i` and `i_run` against one libcft, and asserts that `src\` is commit 1646c96's (S1) |
| `tests\i_harness.py` | the gates' harness: the desktop's modes (compile, i1, i1parts, i2, i3d, i0, i4, calib, stage, and the records' modes) and the box's (box-build, box-i0, box-i3, box-i5, standard library only) |
| `tests\i_lib.py` | the logs (numbered, never overwritten, each script and module kept by its hash) and the in-process CPU accounting |
| `tests\i_analyze.py` | I3's criterion, measurements and model gap, and I5's statistics, from the box's records (phase 2) |
| `tests\i_service.py`, `tests\i_fetch.py`, `tests\i3_server.py`, `tests\i_partb.py` | part B (section 4) |

**Build** (the desktop's: mingw64 gcc; the box's: gcc 13.3.0):
1. libcft from cft-fp256's archive at 9e8ff270 (`7814576d…`): `make -C host CC=gcc libcft.a` (with `OS=Windows_NT TMP=/tmp TEMP=/tmp` on the desktop).
2. `bash tests/build_i.sh build <host dir> <out> src tests studies/debris-i/src_1646c96.sha256`.

**Run:** `python -I -B tests/i_harness.py <mode> --cfg CFG.json` on the desktop. Its CFG names every path. On the box, `python3 -I -B in/tests/i_harness.py box-<mode> --root .` from a staged folder (`stage` writes it, with `EXPECTED.sha256`).

**The images and banks** stay out of the repository (they carry cft-fp256's routines). `studies\debris-i\compiles.tsv` gives each compile's source SHA-256, image SHA-256, manifest SHA-256, counts and cftc command. Images are rebuilt by `python -I -B <archive 9e8ff270>/python/cftc studies/debris-i/systems/<source> --steps 40 --target sw:512 --format <fmt> --out <dir> --stem <stem>`.

## 2. The program and its variants

**The model** (READ `src\m1_physics.h`; the generator's docstring states it):
- **The sum:** (((central + harmonics) + Sun) + Moon) + drag, in the inertial frame. No radiation pressure.
- **The integrator:** rk4 at h = 15 s, with t in the state (`d/dt t = 1`).
- **Order of operations:** each force is M1's operations in M1's order (`ph_central`, `ph_grav`, `ph_third`, `ph_series`, `ph_bodies`, `ph_frame_apply`, `ph_drag_g`). The exceptions are an operation on an exact zero (W(n, 0), Clenshaw's first step, the sums' starting 0), which is left out, and nhFA t1 + hFB t2, written hFB t2 - hFA t1, which is the same rounding of the same sum.
- **Values:** every data value and constant is a `param` or `lane param` with default 0. The 34 generated sources hold no number but 0, 1 and h = 15 (MEASURED by a scan).
- **Rounding of values:**
  - each value from a decimal string is rounded once at the run's format;
  - DE421's values are exact from binary64;
  - M1's derived tables are made by M1's own operations through the golden softfloat.

**The variants** (MEASURED, `compiles.tsv`; `sw:512`, 40 steps a segment):

| source | format | instructions | bank (params + consts + routine words) | scratch (state + lane params + spills) |
|---|---|---|---|---|
| degree 7, 28 bands (the program) | binary32 / 64 / 128 / 256 | 19,990 / 19,362 / 19,550 / 19,758 | 409 / 403 / 412 / 425 (312 + 6 + 91 / 85 / 94 / 107) | 378 (7 + 203 + 168) |
| degree 2, 28 bands | binary32 / 64 / 128 / 256 | 15,792 / 15,137 / 15,325 / 15,533 | 214 / 208 / 217 / 230 | 330 / 322 / 322 / 322 |
| degree 8, 28 bands (compiled once, decision 3) | binary256 | 21,134 | 485 (372 + 6 + 107) | 400 (7 + 203 + 190) |
| degree 20, gravity as lane params (I6) | binary64 | not determined: stopped at 20 CPU-minutes on `sw:2048` | - | - |
| the six part systems | four formats | 172 to 2,033 a step | 0 to 107 | 7 to 290 |

- **Routines a step of the program:** 39 divisions, 26 roots and 4 exp. Five divisions and two roots are shared between rk4's equal-time stages 2 and 3 (MEASURED, the manifest).
- **The features used:** WIDE_CONST, REGS32, BANK_PTR, KX9, SCRATCH, SCRATCH_IO, SCRATCH_STRICT and FLAG_CONTROL. The image does not use INDEXED or AUGADD.
- **M1's 28 bands fit at degree 7,** so decision 3's fallback to one band was not used.
- **Degree 8 also fits `sw:512`,** where the plan expected a refusal. The program stays at degree 7 (decision 3).
- **Two exploratory compiles** of an early generator, made before the harness existed, are not in `compiles.tsv`. One was refused `duplicate-name` (a let named like a band param, renamed); one compiled. Neither image was used.

**The images DEBRIS-J inherits** (degree 7; source / image SHA-256):
- binary64: `c71f5c68…` / `d0a6558b12bf62070b38cf5dee715c9978a4eb68258cc2b74e499f5acbcd53b3`
- binary128: `2c186ac1…` / `02245fbc6025031797005317dbab02d1dec8baa6e16377963aa6c83593bc5994`
- binary256: `a889d2d2…` / `974d6760c68399df1a4f1c93d5027c41e3f1d6eecb926ade0d0c52181c79f7d9`
- binary32: `f1413208…` / `cdfe93d03fee156e4e0651eaa28f771f0dda196f5fa4ef099b8510ae15fdfc43`

## 3. The frame's form and the layout

**The frame's form** (`tests\i_vals.py`, fixed before any fit was seen):
- **The variable:** for a run of stage times T0 to T1 (its own block), s = t - tc with tc = (T0 + T1)/2.
- **The polynomials:** each of M's nine elements is a polynomial of degree 7 in s, and each of Omega's three of degree 3. Each is the exact least-squares fit, in rational arithmetic, of M1's own `frame_at` (cft256, DEBRIS-H's `frame_h0.bin`) at every stage time of the block.
- **Rounding and evaluation:** each coefficient is rounded once at the run's format. The program evaluates them by Horner, one fma a step.
- **Marks:** no routine of the frame can mark.
- **Against M1** (MEASURED, I2(e) at 1,962 stage times): the largest |M - M1| is 2.49e-13 and |Omega - M1| 3.22e-15 rad/s, 25% and 32% of the bounds. An exploratory check, run before the design was fixed (scratch only, no log), gave 2.49e-13 at degree 7 and 2.43e-13 at degree 8 on three of I3's blocks. So the floor is BELIEVED to be the residual wiggle of M1's own 6-point interpolation of the 256-s nodes.

**The layout:**
- **The bank:** the gravity tables (222 values at degree 7), the 84 band values and 6 scalars, which make 312 params.
- **The lanes:** DE421's 111 coefficients with their three lengths and starts, the frame's 85 values and bc, which make 203 lane params.
- Every lane param is rewritten by the driver at each run's start (READ `i_run.c`).

**The run's blocks:**
- One hour (240 steps, 6 segments of 40) from DEBRIS-H's T_s on the 600-s grid.
- DE421's sub-interval is the one M1's floor rule takes at the run's start. I2(d) holds that choice, at stage times on both sides of 2026-11-20 00:00 TDB and exactly on it.
- The day of I3 crosses no DE421 boundary (COMPUTED): it ends at 2026-11-19 22:50 TDB, before the Moon's next boundary at 2026-11-20 00:00 TDB (3,024,000 s from JD 2461329.5), and the Sun's and the EMB's sub-interval runs to 2026-12-02.

## 4. The gates

**I0** (MEASURED, `i0_desktop.001.log`, `i0_src.001.log`, `box_build.001.log`, `box_i0.001.log`):
- Both archives' SHA-256 equal `lead.md`'s, and every member equals its extracted file.
- libcft.a built from the two archives is byte-identical on the desktop (`f0eec4f2…`).
- M1 on 9e8ff270's libcft equals M1 on 0aa997a3's, bit for bit, at native32, native64, native32 and native64 with libcft's transcendentals, cft32, cft64, cft128 and cft256: the test seed's objects 0 to 15, 240 steps, the full model, frame = 1. This holds on the desktop and on the box.
- The eight line-sets' SHA-256 are the same on the two machines (MEASURED, by comparing the two logs).
- C2 fails in object 3 alone, as it must.
- R1: the box's executor equals the desktop's on all 32 of I1's cases, states and lane bytes.
- **P3:** `src\` equals commit 1646c96. Its first run failed, because my harness passed a backslashed path to `build_i.sh`, and Git Bash's sha256sum then prefixes a backslash. That log is kept. After the fix (hash from stdin), P3 passes, and C1 fails naming `m1_consts.h` alone.

**I1** (MEASURED, `i1_program7.001.log`, `i1_program2.001.log`, `i1_parts.002.log` and `.003.log`):
- **Criterion:** the executor equals cftc's reference interpreter bit for bit, states and lane bytes' five flags.
- **Cases:** the program at degrees 7 and 2 and all six part systems, at binary32, 64, 128 and 256; 16 lanes of the test seed, 160 steps in two runs of 80, each run two segments of 40. Every case passes, with 0 marks.
- **Controls:** C3 (the interpreter with GM one encoding up differs, 2 to 6 of 14 values) and C4 (the Moon's next sub-interval changes all 16 lanes, binary64) bite.
- `i1_parts.001.log` stopped at the frame table's hex header before any check, and `.002` stopped at drag's missing Omega input; both are kept.

**I2** (MEASURED, `i2_redacted.001.log`, `i2_margins.001.log`; the original `i2.001.log` is held in the ledger's `debris-i\held\`, since it printed Omega's three binary64 encodings):
- **Inputs:** 1,000 per part, from DEBRIS-E's E1 recipes and the test seed's 64. Bodies take 1,000 stage times about 2026-11-20 00:00 TDB. The frame takes 1,962 stage times: I3's desktop hours, and 100 drawn hour blocks of 10.
- **(a) to (d) and (f):** the part systems equal M1's kernels bit for bit at binary64, binary128 and binary256, with 0 values differing, against cft64 and native64 alike.
- **(e):** as in section 3.
- **Controls:** C5 to C11 all make their criterion fail. C11 uses the next hour's block, on the first 10 of the 100 drawn blocks (110 lanes).
- **One margin assertion failed:** C10 at binary128, by a wrong estimate formula of mine (a stray factor of about 1e-4). Corrected, all eight margins pass (C10 at binary128: ratio 1.8e7, against 2^20).

**I3:**
- **The criterion,** at every boundary and object: |program - M1| <= 64 n 2^-p S + T_frame.
- **The sample:** 64 objects, 16 a perigee band, drawn by `random.Random(20261123)`.
  - Seed index 1595 was set aside before the draw: DEBRIS-H decayed it 5.8 h after T_s. The rule was stated in the script before the data.
  - No state duplicates another's. The list is the ledger's `debris-i\i3_sample.tsv`.
- **The box's day** (MEASURED, `box_i3.001.log` and `phase2.001.log`): every pair passes over 64 objects x 144 boundaries (55,296 values each), t exact at every boundary, 0 marks at every format.

| pair | share of the tolerance, median | largest |
|---|---|---|
| binary64 / cft64 (and native64, identical) | 2.8e-4 | 0.017 |
| binary128 / cft128 | 4.5e-6 | 1.8e-4 |
| binary256 / cft256 | 4.5e-6 | 1.8e-4 |

- **The program's binary64 against its binary256** (position, median / largest): 2.0e-8 / 9.7e-8 m at 1 h, 3.6e-7 / 1.5e-6 m at 6 h, and 2.4e-6 / 1.5e-5 m at 24 h.
- **The desktop's functional test** (8 objects, 2 h, `i3_desktop.001.log`): passes, and C12 (M1 at degree 6) bites.
- **C13 failed as specified:** with the hour before's frame block in hour 2, 0 values were over the tolerance, and the control needs more than 0 (corrected at the merge: the report said "no value passed the tolerance", the reverse of its log's line).
  - `c13_diag.001.log`, added after the data and labelled so, shows the block was read: hour 2 departs from the unplanted run at its first boundary.
  - The departure was only 3.4e-5 m in the hour, against T_frame's 1e-3 m. INFERRED: the block's polynomial, carrying its own tc, extrapolates the frame well for another hour.
- **What I3 says about the frame** (verifier-I's note; added at the merge): at binary128 and binary256 the tolerance is almost wholly T_frame, and the shares are equal at the two formats. So I3 bounds the frame's effect on positions only at T_frame's 1e-3 m, far more loosely than I2(e) bounds the frame itself. I2(e) is the frame's test.

**I4** (MEASURED, `i4.001.log`), through part (d) and part (c):
- **testpo.421:** the 16 points of the pairs (10, 3), (3, 10), (11, 3) and (3, 11) lie within 3.2e-16 AU at binary64 and 2.2e-16 at binary256, against 1e-13. P2b fails, as it must.
- **Lasser et al.'s tides,** at 288 epochs: the Sun within 1.2e-17 m/s² and the Moon within 3.9e-16, against 1e-11. The Moon's GM x (1 + 1e-3) gives 1.15e-9, which fails, as it must.
- **Truncation, reported:** degree 7 against their degree-180 field differs by up to 1.8e-4 m/s². The log's criteria text says this comparison adds the central term; the code compares degrees 2 to 7 alone, as its result line says.

**Part B** (MEASURED, `partb.001.log`):
- **B2:** `i_service.py` logs each slot falling due under the stop file once, as skipped. It keeps "missed while the service was down" only for a slot due while the service was not running. The control, the unchanged `h_service.py`, prints the old text for slots 1 and 2.
- **B3:** `i_fetch.py` logs each request's time to its first byte, from a wrapper of the connection's socket, and to its last. With 5 s before the response it logs 5.00 to 5.02 s; with no delay, 0.001 to 0.016 s. The control, the delay after the first byte, gives a first byte at 0.002 to 0.004 s and a last byte at 5.00 s.
- Everything ran on 127.0.0.1.

## 5. The model gap, the rates and the degree-20 probe

**The model gap** (MEASURED, `phase2.001.log`; M1 alone, a difference between two models, never an error of either; native64 and cft64 give the same figures):

| M1, 64 objects, position (median / largest) | 1 h | 6 h | 24 h |
|---|---|---|---|
| the program's forces against the full model | 48 / 174 m | 147 / 719 m | 343 / 2,312 m |
| degree 7 against 20 (radiation pressure off) | 48 / 174 m | 148 / 720 m | 347 / 2,312 m |
| radiation pressure off against on (degree 7) | 0.29 / 0.75 m | 1.1 / 3.9 m | 4.0 / 18.6 m |

- At 24 h the gap is mostly along-track: median 341 m, against 16 m radial and 41 m cross-track.
- By perigee band at 24 h the median is 672 m (under 400 km), 231 m, 229 m and 527 m (800 km and over).
- So degree 20's terms carry almost all of the gap.

**The rates** (MEASURED, `box_i5.001.log` and `phase2.001.log`):
- The box ran in the sensitive window B0263, and all 21 runs were valid at the first try.
- The foreign load was 0.045% to 0.080%, the runs took 67 to 357 s, and there were 0 marks.
- X is object-seconds summed over the workers, over the wall time from the first start to the last end: 64-lane batches, worker w on CPU w, nice 19. Every ratio divides rates.

| configuration | X, W = 1 | W = 18 | W = 36 |
|---|---|---|---|
| the program, binary64 | 7,278 | 101,958 | 92,573 |
| the program, binary128 | 6,078 | 85,013 | 78,198 |
| the program, binary256 | 4,632 | 64,332 | 59,732 |
| M1 at the program's forces, native64 | 6,389,227 | 89,625,190 | 93,947,184 |
| M1 at the program's forces, cft64 | 6,392 | 89,857 | 85,294 |
| M1 at the program's forces, cft128 | 3,786 | 53,063 | 52,375 |
| M1 at the program's forces, cft256 | 1,606 | 22,597 | 23,246 |

- **The program against M1 at the same forces,** at W = 1 / 18 / 36:
  - binary64 / cft64: 1.14 / 1.14 / 1.09;
  - binary128 / cft128: 1.61 / 1.60 / 1.49;
  - binary256 / cft256: 2.88 / 2.85 / 2.57;
  - native64 runs about 880 times the program at binary64.
- **The program against M1's full model** (DEBRIS-G's G4: cft256 299 / 4,176 / 4,332): 15.5 / 15.4 / 13.8 at binary256, inside the plan's ESTIMATE of 10 to 30. At binary128 it is 8.9 / 8.9 / 8.2, and at binary64 6.4 / 6.4 / 6.0.
  - These ratios compare two models (verifier-I's notes; added at the merge). Most of each is M1's own gain from the program's lighter forces, 5.4 to 5.6 for the cft kinds (next line). At the same forces the program's own gain at binary256 is 2.57 to 2.88.
  - G4's capacity at W = 36 is the median of three runs (`studies\DEBRIS-G-build.md`, G4's table), and the program's figures are one run each.
  - So 59,700 objects (below) is a degree-7 figure, and is not comparable with DEBRIS-G's 4,332 objects of M1's full model.
- **M1's own model** is faster at the program's forces than at its full model: 5.4 to 5.6 times for the cft kinds, and 4.9 to 5.1 for native64.
- **Scaling:** X(18) / (18 X(1)) is 0.77 to 0.78 everywhere. Hyperthreads take the program down a little, X(36) / X(18) 0.91 to 0.93, against 0.95 to 1.05 for M1.
- **Capacity at real time** (X at W = 36, an extrapolation past the 2,304 objects run): about 59,700 objects at binary256 and 92,600 at binary64.

**The degree-20 probe (I6):**
- cftc on the degree-20 program, with the gravity tables as 1,548 lane params (1,751 in all), for `sw:2048`, was stopped by PID at the lead's cap of 20 CPU-minutes. It ran 1,191.7 CPU-s; it had neither compiled nor refused, and had written nothing.
- **Not determined.** The box route was withdrawn: cftc refuses exp without mpmath, and the box has none.

## 6. What DEBRIS-J inherits

- **The images** of section 2. Their depth is 512 and their features are those listed in section 2. The bank stays inside 512.
- **The driver's run and segment loop** (`i_run.c`): the bank as per-run data, the lane params rewritten at each run's start, t checked at each run's start, and the carried scratch.
- **The values,** made by `i_vals.py` and the staged runs and INIT files (in the ledger's `debris-i\box-stage\`).
- **Every boundary state of I3's day,** at binary64, binary128 and binary256, for 64 objects, with their lane bytes and 0 marks. They are in the ledger's `debris-i\box\out\i3\`, to hold a card to lane for lane.
- **Degree 8 fits `sw:512`.** At sw:512, `hip:N` runs 2,048 lanes a launch (relayed).

## 7. Limits

- **The frame's form** meets I2(e) within its bounds at every stage time sampled. It reaches 25% (M) and 32% (Omega) at DEBRIS-I's 1,962 times, and 14% and 48% at verifier-I's 600, drawn from 60 blocks with a seed of its own (narrowed at the merge). Its floor, about 2.4e-13 in M, is BELIEVED to be M1's own interpolation's. With s = t - tc, a block's polynomial extrapolates well, so C13's plant cannot fail I3.
- **The program drops radiation pressure.** Its cost is the gap above: about 4 m a day, median, at degree 7.
- **A block ending exactly on a DE421 boundary** evaluates its last stage on the earlier sub-interval, where M1 takes the later. I3's day touches no boundary, so this is not tested.
- **The comparison with M1** holds at M1's own operation order. Both sides share M1's tables and frame table, so a fault common to both would not show here. E4, E5, I4 and DEBRIS-H's checks against CelesTrak bear on that.
- **I5's rates** are one window's, on 64-lane batches of DEBRIS-H's seed. Capacities past 2,304 objects are extrapolations.
- **I3's sample** sets aside one re-entering object, so the gate says nothing about a lane crossing the surface.
- **Desktop timings** are functional only. The calibration's rates fixed I5's durations and nothing else.
- **The interpreter costs about 0.055 CPU-s a lane-step** at degree 7 (COMPUTED from I1's 570 CPU-s by cycles), about 5 times plan-verifier-I's figure.

## 8. What the brief got wrong

- I6's box route cannot work (`routine-unavailable` without mpmath).
- Degree 8 fits `sw:512` with M1's form of the field.
- C13's plant is too small for a frame form that carries its own tc.
- The interpreter's cost was about 5 times the plan's.
- plan-verifier-I's re-check gives 2026-11-20 00:00 TDB as 34 days from the epoch. It is 35 days, 3,024,000 s (COMPUTED from JD 2461329.5 = 2026-10-16 00:00 TDB), and it is on the grid and on the Moon's boundary either way.

## 9. Narrowed at the merge, and notes (the lead, 2026-11-23)

verifier-I found no defect in any of its ten attacks (`studies\DEBRIS-I-verifier-I-report.md`), so nothing was sent back. Where a sentence claimed more than its evidence, or left out what verifier-I found, the lead narrowed it or added beside it. merge-check-I found one more sentence to correct. The text as reported is kept at `cft-debris-ledger\filed\DEBRIS-I-build.as-reported.md`.

**The note near the top** is new. It says what verifier-I checked and what it did not.

**Narrowed**, marked in the text:
1. **Section 7, the frame's form:** within its bounds at every time sampled. verifier-I's 14% and 48%, at 600 times of its own, stand beside DEBRIS-I's 25% and 32%.

**Added**, each marked in the text (verifier-I's notes):
1. **Section 4, I3:** what I3 says about the frame. At binary128 and binary256 the tolerance is T_frame, so the frame's test is I2(e), not I3.
2. **Section 5, the full-model ratios:** they compare two models.
   - Most of each ratio is M1's own gain from the lighter forces.
   - G4's capacity at W = 36 is a median of three runs, against one run each here.
   - 59,700 objects at degree 7 is not comparable with DEBRIS-G's 4,332 of the full model.

**Corrected**, marked in the text:
1. **Section 4, C13:** the report said "no value passed the tolerance". The log (`i3_desktop.001.log`, line 42) says 0 values were over it, where the control needs more than 0. merge-check-I found this; verifier-I's account matches the log.

**merge-check-I** (Haiku) checked this merge (`cft-debris-ledger\filed\DEBRIS-I-merge-check-I-report.md`). It confirmed:
- the hashes, and that every difference from the report as reported is the note, a marked passage or this section;
- every figure at its source, the marks, and that nothing of verifier-I's was dropped;
- the rewrite of `box_build.001.log`.

Its two points were fixed in its terms:
- the lead's first version called the two added passages "narrowed";
- C13's sentence was the reverse of its log.

The fixes were not checked again.

**The lead's own change before verifier-I:** `box\logs\box_build.001.log` quoted make's "Leaving directory" message twice, on lines 19 and 78, with the box's home path. The lead rewrote those two paths to `<root>` in the repository's copy. The original is in the ledger's `debris-i\box\logs\`, and verifier-I found the copy differs from it in exactly those two lines.

**Notes** from verifier-I, not narrowed:
- **C3's plant** moved 1 of 14 values at binary64 and 4 of 14 at binary256 on verifier-I's 4 lanes and one segment, against section 4's "2 to 6 of 14" on DEBRIS-I's cases. The control needs any difference, so it bites either way.
- **`i1` in its smoke mode** labels its checks "4 segments" when one ran.
- **`i2_redacted.001.log`** still ends "28 checks, 1 failed", for C10's margin at binary128. The corrected margins are in `i2_margins.001.log`, a separate run, and no log calls the fix a pass. Its Omega line is replaced by the SHA-256 of the three encodings joined by single spaces, which verifier-I recomputed.
- **The one catalogue-like token** verifier-I's scan found, `58515`, is a drag-table scale height from `src\m1_consts.h`.
- **verifier-I did not:**
  - run C5 to C11 at binary64 or binary32 beyond what `i2` does;
  - re-run I1 on the six part systems, I4, part B or I0;
  - replay any mark, since there were none;
  - recompute parts (d) and (f) in mpmath;
  - re-scan the lead's 65 hexadecimal hits one by one. It scanned for numbers and hashes in its own way instead.
- **Its notes on the lead's brief:**
  - attack 2 did not say that part (c) has six outputs;
  - attack 3's recompute needs the program's lane order, which follows the sorted object order of the M1 files;
  - the staged folder holds no image manifests, so a verifier's re-run recompiles each image (about 15 s each).
