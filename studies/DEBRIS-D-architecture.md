# DEBRIS-D: a real-time, wide-precision debris propagator as cft programs, priced

Study parcel DEBRIS-D for cft-debris, 2026-11-12, under the plan of record `studies\DEBRIS-D-plan.md` (draft 5, SHA-256 `57709adb2b3bf75dc8c20cba6e407caeda23d6361c25a4f84f231bf7b6778da0`). A study: it builds no part of the propagator, commits nothing, writes and audits no certificate, and ran nothing on a GPU. My scripts, systems, logs and records are in `studies\debris-d\` (this repository's, MIT), listed in its `MANIFEST.sha256`. cft-fp256's sources, my libcft build, every compiled image and bank, and the copy of cft-rebound's `ias15_cft.c` stay in my scratch, `cft-debris-scratch\DEBRIS-D\`; `debris-d\images.tsv` records each image's SHA-256, its manifest's counts and the command that rebuilds it. The generated field sources (degrees 6 to 20) carry 300 to 1,750 values derived from EIGEN-6C4, so they stay in my scratch too. `q2\gen_field.py` regenerates them byte for byte from the approved download; their hashes are in `debris-d\field_sources.sha256`, and the regeneration was checked against them (all five OK).

At the merge the lead made six narrowings and one addition, and wrote this note, following verifier-D's report (`studies\DEBRIS-D-verifier-D-report.md`). They touch fourteen places, each marked "narrowed at the merge" or "added at the merge", and the last section lists them. The text as DEBRIS-D reported it (SHA-256 `210604d4340f0075d34477346f6c81d3c5f35800da24894ecc33f9d264bea9da`) is kept in the project's ledger, as `filed\DEBRIS-D-architecture.as-reported.md`.

**Labels.** MEASURED: run here, with its command and log (every log names the SHA-256 of the script that wrote it). COMPUTED: arithmetic from labelled inputs, in a named script. READ: opened the source; "READ (via WebFetch)" is a model's summary of an HTML page and supports "consistent with" only. ESTIMATE: a judgement with its basis and range. BELIEVED: taken on trust or my judgement.

**Host and load.** i5-12400F (12 threads), Windows 11, gcc 16.1.0 (x86_64-w64-mingw32), Python 3.12.15 with mpmath 1.3.0, REBOUND 5.1.1. libcft and its tools were built from the lead's archive of cft-fp256 at 0aa997a3 (`tools\cft-fp256-0aa997a3.tar`, SHA-256 `e01003cc...9b8`, checked at extraction; 2,643 files). As expected, the build names its build id `unknown`, and so does `cftc --compiler-id`; the archive's SHA-256 ties it to 0aa997a3. Host timings ran inside the lead's sensitive window B0024 (21:15:05 to 21:21:18 -0700), with Windows' CPU load sampled at 0 to 11% before each block; `timesheet.py list desktop` showed only B0023 and B0024. My CPU, counted by `QueryProcessCycleTime` at 2.5e9 cycles a second (BELIEVED rate) through my wrapper `tools\cpurun.py`: 16.1 CPU-minutes (`debris-d\records\cpu.tsv`), against `GetProcessTimes`' 6.0 (the under-report this host is known for), plus about 0.3 for small runs outside the wrapper (ESTIMATE).

## Short answer

1. **The workload is gravity, and on a GPU it is the routines** (MEASURED, counting builds). One evaluation of DEBRIS-C's normalised degree-20 field is 8,160 FMA-class operations, 3 divisions and 1 square root; the Sun and Moon, the interpolated frame, exponential drag and radiation pressure add 799 FMA-class operations, 29 divisions, 9 roots, 20 transcendental calls and 2 fmod, with the object in sunlight. In penumbra they add 821 and 33 divisions (narrowed at the merge). In a compiled image, though, a division is 186 to 190 instructions and a sine 389 to 406, so the routines are 88% of the instructions of a J2-and-drag step and still 48% at degree 7 (MEASURED, cftc's manifests).
2. **v1 carries a LEO propagator's core today, bit for bit** (MEASURED). Two systems, J2 alone and J2 with C22/S22, drag and the Earth's rotation through `sin` and `cos` of ω t, compiled at binary64, binary128 and binary256. On the software executor they equal the reference interpreter bit for bit, states and per-lane flags, over 96 steps on 8 lanes. They agree with a 120-digit mpmath rk4 to at most 1.9% of a tolerance stated beforehand. A source with μ planted one ulp off fails, as it must.
3. **What v1 does not carry, by name** (MEASURED refusals, READ limits): `pow` (`transcendental`), an undeclared `t` (`time-dependence`), drag under Störmer-Verlet (`verlet-not-separable`), and IAS15, since v1 has no adaptive step. Tables chosen by time cannot be indexed inside a run, so the Sun, Moon, Earth orientation and space weather ride as one block's params, with a run per block. Gravity coefficients as params hit the 512-slot bank, and the field's spills hit sw's 256 slots. **Degree 7 is the largest field this study's generator fits within both at every format**, so it is what `hip:N` can carry today in that form. The generator is `q2\gen_field.py`, with its sums unrolled and every coefficient product a param; a rolled or `map` form, or sums in another order, were not tried (narrowed at the merge). Degree 8 is refused `scratch-capacity` (273 slots) at binary64 and binary128 and `bank-capacity` (516) at binary256, and degree 20 is refused `bank-capacity` (1,762 params).
4. **On this CPU, libcft's arithmetic is correctly rounded and slow** (MEASURED in B0024, every result checked bit for bit against mpmath). An FMA costs 195, 235 and 313 ns at the three formats, a divide 3.6, 5.6 and 9.2 µs. A host `cft_exp` costs 0.14, 0.33 and 1.12 ms, and `cft_pow` 0.34, 0.93 and 3.4 ms. The sequencer runs our images at 50 to 125 ns a lane-instruction, so a routine inside a program (exp, 180 to 201 instructions) costs a tenth to a fortieth of the host call.
5. **The integrator v1 offers is rk4, and it buys accuracy with steps** (MEASURED, real EIGEN-6C4 degree 20 with drag, one LEO object-day, against a Romberg reference good to 2e-8 m). rk4's error is 2,310 m at 60 s, 83 m at 30 s, 3.3 m at 15 s and 0.15 m at 7.5 s. IAS15 at ε = 1e-9 makes 4.0e-7 m in 559 steps and 16,449 evaluations. At binary64, rk4 never reaches IAS15's accuracy: its own rounding (1.2e-6 to 1.3e-5 m a day) is larger. Störmer-Verlet is 1,018 km off at 60 s, and refuses drag.
6. **On these estimates, real time is not the constraint on one consumer card; correctness and capacity are** (COMPUTED from GPU-A's measured program rates, and resting on the ESTIMATE of degree 20's instruction count). At a third of the rates, the low end of the ESTIMATE factor below, real time is the constraint: the RX 7600 at binary256 runs MASTER-8's 68,450 at 0.70 to 1.0 of real time (Q5 (i); narrowed at the merge). At degree 20 (an ESTIMATE of 30,000 to 40,000 instructions a step, since v1 cannot compile it) and rk4 at 15 s, one card runs 0.14 to 1.2 million objects at one simulated day a day, generic tier, binary256 to binary64. That is 2.1 to 18 times faster than real time for MASTER-8's 68,450, against 0.04 to 0.09 of real time on one CPU core. These rest on kernel-only, resident rates measured on routine programs at 1M lanes, so they carry an ESTIMATE factor of up to about 3 for our instruction mix and for catalogues far below 1M lanes.
7. **For exp, the replay budget is small on the arguments a propagator makes; for sin and cos it is not determined** (MEASURED): 0 marks in 196,608 lane-evaluations at each format. The 95% bound, 1.5e-5 an evaluation, holds for exp, whose arguments depend on each lane's orbit. sin and cos took w·t, which every lane shared from t = 0, so they saw 193 distinct arguments in 147,456 calls; nothing made them mark; and a marked time would mark every lane at once (verifier-D; narrowed at the merge). The edge windows mark heavily: exp at c·2^-p marks 5, 510 and 532 of 1,024 lanes. A design keeps routine arguments out of them.
8. **Certificates** (READ): the design keeps runs dense, streams fixed per run, every boundary state, and polynomial invariants (h_z) for `drift`. What certificates cannot yet state for this propagator: forcing that changes between segments, lane masks, a bound, values through a root, `hip:N` identity, depth and audit, and replays in C. Dense runs and one forcing block per run avoid the first two; the rest are requests.
9. **For the build** (BELIEVED): a CPU reference in v1 at degree 7 with rk4 can be built now. The GPU route at degree 20 needs a larger bank or index tables, a deeper scratch on `hip:N`, and pow as a routine (Q8's requests). The evidence does not decide the density model or the 24/7 host, and I make no recommendation on either.

## Q1. The workload, by operation class

**Method** (MEASURED). `q1\count_ops.cpp` defines a counting number type, `cnum`, whose every operator and math function increments its class's counter: the brief's counting macros, as C++ operators. `q1\make_count_build.py` copies this repository's own kernels into the counting build whole, by function name, with `double` turned into `cnum`, so nothing is retyped:
- DEBRIS-C's normalised gravity (`debris-c\m1a\m1a_grav.c`);
- DEBRIS-B's Chebyshev reader, interpolated frame, exponential atmosphere and conical-shadow radiation pressure (`debris-b\q2\q2bench.c`).
The Sun's and Moon's point masses are mine, written for the count.

**Controls** (`logs\q1_counts.001.log`, both PASS):
- **C1, the hand count.** Degree 2 must equal a count made by hand from `grav()`'s text: 104 multiplications, 37 additions, 3 divisions and 1 root, written into the script's docstring piece by piece. It matched exactly.
- **C2, a planted term.** A copy of `az -= FZ*C0*V` planted once a degree must add exactly 2 multiplications and 1 addition a degree summed, and change nothing else. At degrees 2, 8, 20, 36 and 70 it added 2, 14, 38, 70 and 138 multiplications and 1, 7, 19, 35 and 69 additions, and every other kernel's line stayed the same.
- **A limit:** the build was first run once by hand while its compile errors were fixed, before `q1_counts.py`, which re-ran it, was written. The hand count was derived before that run.

**One force evaluation** (MEASURED; FMA-class means additions, subtractions and multiplications, which a fused kernel would partly merge):

| part | FMA-class | div | sqrt | transcendentals |
|---|---|---|---|---|
| gravity, degree 2 / 8 / 20 / 36 / 70 | 141 / 1,482 / 8,160 / 25,352 / 93,335 | 3 | 1 | - |
| Sun and Moon positions (Chebyshev; Moon 13, Sun 11, EMB 13 coefficients) | 355 | 7 | - | - |
| Sun and Moon point masses | 54 | 4 | 4 | - |
| frame, interpolated (X, Y, s nodes; EOP; ERA) | 339 (+18 negations) | 12 | 1 | 7 sin, 7 cos, 1 atan, 1 atan2, 2 fmod |
| drag, exponential atmosphere (28 bands) | 23 | 1 | 2 | 1 exp |
| radiation pressure, conical shadow: sunlit / umbra / penumbra | 28 / 29 / 50 | 5 / 5 / 9 | 2 / 2 / 3 | 2 asin + 1 / 1 / 3 acos |

DEBRIS-B's figures for its own unnormalised kernel, 1,415, 7,859, 24,515 and 90,509 flops at degrees 8 to 70, keep DEBRIS-B's definition. The normalised kernel counts 3 to 5% more.

**The density models**, counted from source through GitHub's HTML view (READ via WebFetch), each with where its count stops:
- **NRLMSISE-00, not counted.** Orekit's `NRLMSISE00.java` shows lines 1 to 1,000 of 4,219, the data arrays only, and no method body. Brodowski's C (`magnific0/nrlmsise-00`, `nrlmsise-00.c`) shows 1,000 of 1,459 lines and stops inside `gtd7`, before `gts7`. What is visible:
  - `densu` makes 2 exp (3 below za); `ccor` 2 exp; `ccor2` 3 exp; `dnet` 1 log, 1 exp and 1 pow; `scalh` 1 pow;
  - `globe7` makes about 12 or more sin and cos;
  - pow appears with exponents 2, 1/a, 1 + α + γ, 3, 4, 8, 12 and 19.
  - ESTIMATE per call (basis: that structure, repeated for about 8 species, and BELIEVED): 40 to 60 exp, about 10 log, 20 to 30 pow, 20 to 40 sin and cos, and 1,000 to 2,000 FMA-class operations. These counts rest on WebFetch summaries. Asked again about the same page, they gave different counts for the same functions (verifier-D), so the figures are not determined (narrowed at the merge).
- **JB2008:** Orekit's `AbstractJacchiaBowmanModel.java` shows 1,000 of 1,259 lines, including the binary64 `computeDensity`. At 400 km, the summary counts about 12 exp, 12 log or log10, about 225 pow (`localTemp`, inside the quadrature from 90 km up: 79 intervals, about 316 points), 0 sqrt and 6 sin or cos. `JB2008.java` (442 lines, all shown) adds 2 sinCos and 1 pow. The FMA-class count is an ESTIMATE: 3,000 to 6,000, from the quadrature's 316 points.

**The integrators' own work, a step:**
- **rk4** (READ, LANGUAGE.md:1185-1197): 7 FMA-class operations a state component, so 42 for a 6-component state, and 4 evaluations.
- **Störmer-Verlet:** 9 for 3 degrees of freedom, and 1 evaluation.
- **IAS15** (READ, cft-rebound's `ias15_cft.c` at de376d8: `predict_positions` 1690-1723, `correct` 1751-1777, `predict_velocities` 2691-2705, `step_attempt` from 2884), in REBOUND's division form, a coordinate an iteration of 7 substeps:
  - the position predictor: 28 FMA-class operations and 8 divisions a substep;
  - the velocity predictor, run only for a velocity-dependent force: 25 and 7;
  - the corrector: 6n + 7 FMA-class operations and n divisions at substep n.
  - In all, 413 FMA-class operations and 84 divisions (positions only), or 588 and 133 with drag.
  - The port's FMA form turns the divisions by constants into multiplications.

**An object-day** (COMPUTED, `q1\q1_objectday.py`, `logs\q1_objectday.001.log`; evaluation counts MEASURED in Q4, with their domain: real EIGEN-6C4 degree 20 with drag, one LEO orbit):

| integrator | evaluations | FMA-class | div | sqrt | transcendentals |
|---|---|---|---|---|---|
| IAS15, ε 1e-9 (each object its own step) | 16,449 | 1.51e8 (4.0e6 of them IAS15's own) | 1.43e6 (9.1e5 IAS15's own) | 1.6e5 | 1.6e4 exp; 1.2e5 each of sin and cos; 6.6e4 others |
| rk4 at 15 s, a lockstep batch (Sun, Moon and frame shared by all its lanes) | 23,040 | 1.91e8 | 3.0e5 | 2.1e5 | 2.3e4 exp, 6.9e4 asin and acos |
| rk4 at 30 s, the same | 11,520 | 9.5e7 | 1.5e5 | 1.0e5 | 1.2e4 exp, 3.5e4 asin and acos |

A lockstep batch puts every object on one time grid, so the Sun, Moon and frame are evaluated once a stage for the batch, not once per object. IAS15's per-object steps cannot share them. With NRLMSISE-00 or JB2008, add their per-call counts above times the evaluations: for JB2008's pow alone, about 5 million a day.

## Q2. The route: cft programs, designed for certificates

**Part by part, against v1 at the pin** (READ `docs\LANGUAGE.md`; MEASURED where a compile is named):

| part | in v1? | how, or what stops it |
|---|---|---|
| central term, J2, tesserals | yes (MEASURED) | `j2-rk4.cftl`, `j2dragrot-rk4.cftl`, `field6/7/8` |
| gravity coefficients | as params, to degree 7 at every format with sw's 256 slots (MEASURED) | the bank holds 512 slots on every device, `bank-capacity`; the field's spills are `scratch-capacity` at sw's 256. As lane params the language allows 32,768 values a lane (LANGUAGE.md:291-293), but degree 20 needs a deeper scratch than `hip:N`'s fixed 256, and its compile did not finish in 290 s |
| time | yes, in the state (MEASURED) | `state t`, `d/dt t = 1`; at h = 60 s rk4's stage times are exact integers. An undeclared `t` is refused `time-dependence` (MEASURED) |
| the Earth's rotation | yes, `sin(w*t)`, `cos(w*t)` (MEASURED) | routines (LANGUAGE.md "Forcing", from 1476) |
| Sun and Moon positions; Earth orientation; space weather | not by table | an index is integer arithmetic on literals and the statement's index variable (LANGUAGE.md:302-304), so no table can be chosen by time inside a run. Each rides as **one block's params, with a run per block**: a Moon Chebyshev sub-interval (DE421's are 4 days), a day of EOP nodes or an interpolating polynomial in t, a day's F10.7 and Ap, with `select` on t for 3-hourly ap. **Runs are therefore at most a block long: hours to a day.** The IAU series themselves (thousands of sin and cos terms) stay on the host |
| each object's constants | yes, lane params (MEASURED: `bc`) | a param's sensitivity needs it in the state (`d/dt bc = 0`), since v1 has no tangents with respect to params (LANGUAGE.md:3281) |
| exponential drag | yes (MEASURED) | `exp` routine |
| NRLMSISE-00, JB2008 | not as written | `pow` is refused `transcendental` (MEASURED); `pow(x,y)` must be rewritten `exp(y*log(x))`, and integer powers as products. JB2008's quadrature is a fixed loop, so it can be unrolled |
| integrators | rk4, euler, stormer-verlet, map (LANGUAGE.md:217, 3325-3326) | IAS15 is not among them, and v1 has no adaptive steps (LANGUAGE.md:3321). Störmer-Verlet with drag is refused `verlet-not-separable` (MEASURED). A `map` can write any explicit fixed step out by hand, such as a fixed-iteration Gauss-Radau (BELIEVED) |

**Against `hip:N`, compared by hand** (READ, HOSTAPI.md:2280-2295: `seq_features` 0x75f1f, the software handle's 0x7ff1f less INDEXED 0x2000 and AUGADD 0x8000, and a depth fixed at 256 slots; feature values from `cft.h`). Every image I compiled uses some of WIDE_CONST, REGS32, BANK_PTR, KX9, SCRATCH, SCRATCH_IO, SCRATCH_STRICT and FLAG_CONTROL, all inside 0x75f1f, and none uses INDEXED or AUGADD.
- Q2's six images and the degree-6 and degree-7 fields declare 256 slots and use 20 to 222. So they would load on `hip:N` (BELIEVED from the published words; nothing ran on a GPU).
- The degree-8 field needs `sw:512`, which `hip:N` cannot open.

**The first test** (MEASURED; `q2\q2_first_test.py`, `logs\q2_first_test_j2-rk4.002.log` and `logs\q2_first_test_j2dragrot-rk4.001.log`, 0 failures):
- **The runs:** rk4, h = 60 s, 96 steps in 4 segments of 24, on 8 lanes. The lanes are near-circular orbits at 380 to 415 km, inclined 5 to 135°, with lane parameter `bc` = 0.005 to 0.019 m²/kg. Each image ran on libcft's software executor through my driver `tools\seqrun.c`, segment by segment.
- **The criteria, stated before the data:**
  - (a) every lane's state after each segment equals `lang.run`'s bit for bit, and its lane byte's five flags equal the definition's (the marked-lane rule);
  - (b) |image − mpmath| ≤ 64·N·2^-p·S, where N is the steps so far and S is 7e6 m or 8e3 m/s;
  - (c) `lang.run` of the source with μ planted one ulp of the format above must differ from the image somewhere;
  - (d) the plant is one encoding up.

| system, format | instructions a step | bank / scratch | (a) | (b): largest difference at 96 steps, pos / vel (share of tolerance) | (c): values that differ |
|---|---|---|---|---|---|
| J2, binary64 | 1,518 | 50 / 20 | PASS | 6.7e-8 m / 9.5e-11 m/s (0.014 / 0.017) | 181 of 192 |
| J2, binary128 | 1,538 | 50 / 20 | PASS | 5.7e-26 / 5.2e-29 (0.014 / 0.011) | 171 of 192 |
| J2, binary256 | 1,558 | 50 / 20 | PASS | 3.2e-63 / 4.2e-66 (0.016 / 0.019) | 175 of 192 |
| J2, drag, rotation, binary64 | 4,541 | 182 / 35 | PASS | 6.4e-8 / 8.2e-11 (0.013 / 0.015) | 179 of 224 |
| J2, drag, rotation, binary128 | 4,505 | 185 / 32 | PASS | 4.2e-26 / 4.6e-29 (0.010 / 0.010) | 178 of 224 |
| J2, drag, rotation, binary256 | 4,605 | 206 / 31 | PASS | 1.4e-63 / 1.8e-66 (0.007 / 0.008) | 180 of 224 |

- **Instruction counts by class** (MEASURED, the manifests; all in `debris-d\images.tsv`).
  - The drag system's step at binary64 holds 374 graph nodes: 136 fma, 148 mul, 6 add, 12 sub, 48 neg, 4 div, 8 sqrt, 4 exp, 4 sin and 4 cos.
  - They compile to 4,541 instructions. 4,020 of them are routines: per call, div 186, sqrt 165, exp 180, sin 406 and cos 402; at binary256, 190, 171, 201, 389 and 385.
  - The compiler shared one sine and one cosine between rk4's equal-time stages 2 and 3, so a step calls 3 of each, not 4.
- **Marks:** no lane was marked in any segment, at any format: 0 in 3,072 lane-evaluations a format. The larger count is in Q3.
- **Capacities and refusals** (MEASURED, `logs\q2_degree_sweep.001.log` and `.002.log`; `logs\q2_refusals.001.log`):

| field | binary64 | binary128 | binary256 |
|---|---|---|---|
| degree 6 | 7,281 instructions, bank 364, scratch 174 | 7,270, 367, 174 | 7,375, 388, 174 |
| degree 7 | 8,302, bank 424, scratch 222 | 8,291, 427, 222 | 8,396, 448, 222 |
| degree 8 | `scratch-capacity`: 273 slots (7 state, 1 lane param, 265 spills) against 256 | the same | `bank-capacity`: 322 params, 6 constants and 188 routine words, 516 against 512 |
| degree 8 on `sw:512` | 9,415 instructions, bank 492 | 9,404, bank 495 | refused `bank-capacity` |
| degree 20 | `bank-capacity`: 1,762 params and 6 constants | - | - |
| degree 20, coefficients as lane params, `sw:4096` | not finished in 290 s (283 CPU-s), stopped by the timeout I set under the stop rule | - | - |

  - The sweep's first log shows three FAILs. They are a fault in my script, which could not parse a Windows path's drive colon, and not in cftc; version 2 names each refusal.
  - `pow` is refused `transcendental` ("pow is not computed by a program in v1"), `^` `power`, and drag under Störmer-Verlet `verlet-not-separable`.

**Designed for certificates** (READ, `docs\CERTIFICATES.md` at 0aa997a3):
- **Runs of fixed streams, cut into segments, every boundary state kept.** "A run is dense and its streams are fixed" (lines 3424-3426), so a run is one forcing block with its bank fixed, and a day is many certificates. An image's one REPEAT count is a segment; cft-segrun runs consecutive segments (from line 1398).
- **Accuracy entries** (from line 687), each an estimate or a measurement, none a bound:
  - `step-halving` (cftc wrote a `.half.bank` for every image, MEASURED);
  - `wider-source` at binary64 and binary128, since it is refused at binary256 (line 3923);
  - `drift` of h_z = x·v_y − y·v_x, a polynomial, which J2 conserves and C22 and drag do not.
- **The audit** (lines 928-952) is handed the certificate, each run's image and bank, the states and the streams, and chooses all, named or k sampled segments. Handed only each run's initial state, a full audit "is the most independent audit there is".
- **Independence:** for a run made on libcft's software backend, "only the golden auditor is an implementation independent of it there" (lines 56-96).
- **A day's GPU runs, audited on the CPU,** once support arrives: `cft-audit` re-runs sampled segments on `sw`. No certificate written on `hip:N` has been audited yet (relayed).

**What certificates cannot yet state for this propagator**, by name (READ, "What version 1 does not do", from line 3414, and "What version 2 does not do", from line 4647; relayed where marked):

| item | design avoids it? | otherwise |
|---|---|---|
| forcing tables that change between segments ("streams that change from segment to segment") | yes: one block per run, so a run per forcing block | - |
| objects entering or leaving (lane masks) | yes: dense runs, with lanes repacked only between runs | - |
| a bound on the error ("No version-1 method has a rigorous remainder") | no | a request |
| values through a square root or a division by a state, such as a distance (line 3421) | partly: state differences of r² and h_z, which are polynomials | a rounded or enclosed method, a request |
| runs on `hip:N`: identity, scratch depth, audit in C (relayed; `cert_write.h:422-427` writing the device lines `unknown` was READ by the lead) | no | requested already (lead.md 20:30) |
| sources and replays audited in C ("Audit sources or replays in C") | partly: keep routine arguments out of the marking windows, so few segments carry a replay | the golden auditor (Python) for those segments, or a request |

## Q3. The price of each operation class, by format

**This CPU, one thread, libcft's software backend** (MEASURED in B0024; `q3\q3_host.py`, `logs\q3_host.001.log`, 0 failures). Every function's 1,000 results equal mpmath's correctly rounded values bit for bit, at each format (C1). Every timed loop is at least 61 times its fold-only control loop (C2, criterion ≥ 10). Beside them are cft-fp256's tables of 2026-09-01, MEASURED then (BENCHMARKS.md:224-231 and 244-294):

| ns an element | binary64 | binary128 | binary256 | 2026-09-01, binary64 / 128 / 256 |
|---|---|---|---|---|
| fma (cft-bench, my build) | 217.7 | 236.6 | 338.5 | 234.7 / 285.5 / 400.7 |
| mul (cft-bench) | 173.0 | 200.4 | 324.2 | 197.4 / 240.6 / 355.3 |
| add (cft-bench) | 234.3 | 294.1 | 448.8 | 259.0 / 477.4 / 469.6 |
| fma / mul / add (my driver, 1,000 a call) | 195 / 153 / 252 | 235 / 179 / 249 | 313 / 244 / 361 | - |
| div | 3,574 | 5,599 | 9,234 | 4,468 / 6,678 / 11,563 |
| sqrt | 4,400 | 6,419 | 11,037 | 5,638 / 8,018 / 12,704 |
| exp | 136,363 | 334,077 | 1,121,110 | none recorded (relayed) |
| log | 168,198 | 481,415 | 1,769,966 | - |
| pow | 342,443 | 931,901 | 3,360,582 | - |
| sin / cos | 225,890 / 218,207 | 552,460 / 634,610 | 1,888,168 / 1,926,897 | - |
| atan2 | 132,133 | 309,643 | 1,033,016 | - |

So a divide is 18 to 30 FMAs on the host, and a transcendental 700 to 11,000.

**The sequencer on our images** (MEASURED, `tools\seqrun.c --time`, 32 lanes, 3 runs of 24 steps, with the fold-only control and a check that the timed run equals Q2's first segment):

| image | ns a lane-instruction, binary64 / 128 / 256 | lane-steps a second |
|---|---|---|
| J2 | 50.0 / 49.2 / 69.8 | 13,177 / 13,220 / 9,194 |
| J2, drag, rotation | 72.4 / 86.7 / 124.6 | 3,042 / 2,561 / 1,743 |
| degree-8 field (`sw:512`, 8 lanes) | 85.9 / 97.0 / refused | 1,236 / 1,097 / - |

A routine in a program is far cheaper than the host's entry point. An exp is 180 to 201 instructions, about 13 to 25 µs on this executor, against 136 to 1,121 µs for `cft_exp` (COMPUTED).

**The consumer cards** (COMPUTED from GPU-A's MEASURED lane-programs a second, GPU-A-hip.md:845-855, times each routine's instruction count, LANGUAGE.md:466-467 and :504; kernel only, resident, 1M lanes; `q5\q5_ladder.py`, `logs\q5_ladder.002.log`). Lane-instructions a second, low to high of the sin and atan programs:

| | RTX 5060 Ti | RTX 4070 | RX 7600 |
|---|---|---|---|
| binary64, generic | 2.34-2.42e9 | 1.80-2.15e9 | 1.01-1.08e9 |
| binary128, generic (ESTIMATE: the binary64 rate over the card's measured binary64/128 elementwise FMA ratio, 1.85, 1.68 and 1.45, GPU-A-hip.md:507-511) | 1.27-1.31e9 | 1.07-1.28e9 | 0.70-0.75e9 |
| binary256, generic | 0.49-0.54e9 | 0.70-0.83e9 | 0.38-0.41e9 |
| binary256, the fixed path (GPU-A's study code, not in the backend `hip:N` runs) | 4.85-4.98e9 | 1.48-1.58e9 | 1.36-1.40e9 |

These reproduce GPU-A's own 1.0-2.5e9, 0.39-0.84e9 and 1.4-5.2e9 (lines 861-866).
- **The mix.** GPU-A's rate programs were one routine each, mostly integer, select and compare instructions. Ours are 88% routine for the drag system, 48% at degree 7 and about 10 to 13% at degree 20 (COMPUTED from the manifests; degree 20 an ESTIMATE), the rest floating-point instructions, each a softfloat call on the generic tier. On this CPU the executor's cost a lane-instruction rose from 72 to 86 ns between those mixes (MEASURED). So I carry an ESTIMATE factor of 1 to 3 below GPU-A's rates for our images (basis: the CPU's 1.2, and softfloat's unmeasured cost in a GPU thread).
- **Cross-check:** GPU-A's elementwise generic binary256 FMA, 77 to 175 M a second kernel-only (lines 483-485), is 3 to 6 times below the program rates. A generic FMA is a whole softfloat call, and a program's average instruction is cheaper.
- **Divides and roots** are priced inside the images, at 186 to 190 and 165 to 171 instructions a call (MEASURED), not from divfull and sqrtfull.
- **Not timed by GPU-A** (ESTIMATE):
  - binary128 throughout (above);
  - log, cos, tan and atan2 routines, taken at their instruction counts, 176 to 518 a call (LANGUAGE.md:466-505), at the same lane-instruction rates;
  - the MI300X, at 6.5 to 15.5 times the RX 7600. The basis is GPU-A's ESTIMATE of 0.5 to 1.2e9 generic binary256 FMAs a second for the MI300X (GPU-E-mi300x-ring.md:310-311), over the RX 7600's measured 77.4e6 (GPU-A-hip.md:485).

**The replay budget** (MEASURED; `q3\q3_marks.py`, `logs\q3_marks.002.log`, 0 failures):
- **On the propagator's own arguments:** the drag system's images on 512 random LEO lanes, perigee and apogee at 200 to 1,000 km, every inclination, ran 4 segments of 24 steps. They marked **0 lanes in 196,608 lane-evaluations at each format**, each lane-evaluation calling exp, sin and cos once. The 95% bound, 3/N = 1.5e-5 an evaluation, holds for exp, whose arguments depend on each lane's orbit. It does not hold for sin and cos. Every lane started at t = 0, so their argument w·t was the same in every lane: 193 distinct values in all. The compiler also shares one sine and one cosine between stages 2 and 3, so they made 147,456 calls, not 196,608 (verifier-D, COMPUTED from the script and the system). Their marking rate is not determined (narrowed at the merge).
- **At the edges,** one-call maps on 1,024 lanes an argument class:
  - none marked for exp on U[−20, 2], on ±[2^-40, 2^-20], or on U[−745, −708], binary64's underflow, which an HEO's density reaches above about 41,000 km;
  - none marked for sin and cos on U[−10, 10], tiny arguments, or U[1e5, 1e6]. So no class here made sin or cos mark, and they have no positive control (narrowed at the merge);
  - **exp at x = c·2^-p,** where 1 + x sits next to a rounding midpoint, marked 5, 510 and 532 lanes at the three formats. Every guess was right, and every unmarked lane equalled mpmath bit for bit.
- **The positive control's first version failed as stated** (log 001). It expected the tiny class to mark, and it marked none: those arguments are not next to an exact case. Version 2's control, the c·2^-p class, passed.
- **Price** (COMPUTED):
  - a marked lane-segment replayed by `lang.run` costs about 0.12 s on this CPU (MEASURED in Q2: 3.7 to 3.9 s for 32 lane-segments of the drag system, at every format);
  - for exp, at the 95% bound and rk4 at 15 s, that is at most 0.35 marked evaluations an object-day, so at most 0.04 s of host CPU an object-day. For 68,450 objects, at most 2,900 CPU-s a day, 3.4% of one core.
  - **For sin and cos the bound does not apply** (narrowed at the merge). A marked time marks every lane at once. At about 0.12 s a lane-segment, one such time costs about 8,200 CPU-s for 68,450 lanes (verifier-D, COMPUTED). How often that happens is not determined.
  - **The cautioned edge case is an ESTIMATE:** a workload living in a marking window, as fp32 atan2 did on cft-fp256's card night (relayed), marks up to half its lanes. Half of 68,450 lanes marked in every 24-step segment would cost about 4,100 CPU-s a segment, about 11 CPU-days a day, so it must be designed out, not budgeted.

## Q4. The integrator

**Measured on the CPU at binary64** (`q4\q4_integrators.py`, `logs\q4_integrators.002.log`; `q4\q4prop.c`, built at binary64 and at x87 extended precision). The setup:
- DEBRIS-C's normalised kernel, copied whole by `make_q4_kernel.py` with `double` turned into `REAL`;
- EIGEN-6C4 degrees 2 to 20 in an Earth turning uniformly, the central term, and Q2's exponential drag;
- one object-day of DEBRIS-B's LEO orbit (a = 6,778 km, e = 0.001, i = 51.6°).
- **The reference** (stated before the data): rk4 in long double, with two Romberg eliminations, from 1.875, 0.9375 and 0.46875 s. Its own check: |R2(1.875) − R2(3.75)| ≤ 1e-7 m. It passed at 2.0e-8 m with drag and 7.3e-10 m without.
- **Version 1's reference failed as stated:** one elimination gave 6.0e-5 m (log 001). rk4's error ratios per halving here are 27.7, 25.2, 22.4, 20.0 and 18.7, not 16, so an h^5 term was left.

| method, binary64 | step | evaluations | error an object-day (m) | binary64's own rounding (\|fp64 − long double\|, m) |
|---|---|---|---|---|
| rk4 | 60 s | 5,760 | 2,310 | 1.2e-6 |
| rk4 | 30 s | 11,520 | 83.5 | 1.2e-6 |
| rk4 | 15 s | 23,040 | 3.31 | 1.3e-6 |
| rk4 | 7.5 s | 46,080 | 0.148 | 4.5e-6 |
| rk4 | 3.75 s | 92,160 | 7.4e-3 | 1.2e-5 |
| rk4 | 1.875 s | 184,320 | 3.9e-4 | 9.9e-6 |
| rk4 | 0.9375 s | 368,640 | 1.0e-5 (long double 2.3e-5) | 1.3e-5 |
| Störmer-Verlet, no drag | 60 s / 1.875 s | 1,440 / 46,080 | 1.02e6 / 998 | 3e-7 / 1e-6 |
| IAS15, ε 1e-9, drag | 559 steps | 16,449 (29.4 a step) | 4.0e-7 | - |
| IAS15, no drag | 559 steps | 16,351 | 3.5e-7 | - |

- **At IAS15's accuracy:** rk4 at binary64 cannot get there, because its own rounding, 1.2e-6 to 1.3e-5 m a day, exceeds IAS15's 4e-7 m. In a wider format, rk4 reaches 4e-7 m at about 0.34 s (COMPUTED from the h^4 law at its smallest steps): 254,000 steps and 1.0 million evaluations, 62 times IAS15's.
- **Where a wide format's arithmetic would show:** where rk4's truncation meets binary64's rounding, near 1 to 1.9 s: 46,000 to 92,000 steps, or 184,000 to 369,000 evaluations an object-day.
- **For a loop held to TLEs, whose errors are of order a kilometre** (BELIEVED), 15 to 30 s steps, 3.3 to 83 m a day, are below that noise. They need 11,520 to 23,040 evaluations, about IAS15's own count.

**The wide format's place** (COMPUTED):
- At binary64's own steps, a wider format changes the result by 1e-6 to 1e-5 m a day against a truncation of 3 to 83 m. **It is a ruler on binary64's arithmetic, not a better orbit.**
- DEBRIS-B found binary256's round trip falling 2^15 a halving of IAS15's step, and put its floor at about 600 times smaller steps.
- rk4 falls 2^4 a halving. From 2.3e-5 m at 0.94 s, reaching binary128's floor of about 2e-26 m (DEBRIS-B's, for IAS15's round trip) takes 17.4 halvings, about 2e5 times smaller steps. Reaching binary256's BELIEVED floor of about 1e-63 m takes about 48.5 halvings, about 4e14 times smaller.
- So with the integrators v1 offers, the wide formats can never show their own floor on an orbit. They show as rulers, as reproducible bits, and in conditioning, as DEBRIS-B found.

**On the device** (READ and BELIEVED):
- IAS15 one wave a system (GPU-E's design) is not a v1 program. It needs a kernel of its own with an in-kernel divide (in no round's plan, GPU-E §6), or cft-rebound's program engine with index tables (round 2).
- **Divergence:** IAS15's iteration count varies by object (3 to 4 passes here; DEBRIS-B saw 12.8 to 18 at binary256) and its steps differ in size, so lanes in lockstep idle. A fixed-step rk4 batch has none: every lane runs the same instructions, and only the arguments differ.
- **Occupancy:** a lockstep batch needs no masks and keeps every lane live, measure (ii) of GPU-E.
- **Step counts:** rk4 at 15 s makes 1.4 times IAS15's evaluations here, but without IAS15's 4.0e6 FMA-class operations and 9.1e5 divisions a day of its own work, and with the Sun, Moon and frame shared across the batch.

**The licence** (READ: the plan, this repository's README, cft-fp256's `LICENSE` at the pin; BELIEVED where judgement; no legal conclusion, which is Logan's):
- **An IAS15 written for cft-debris from the published method** (Rein and Spiegel 2015), never from REBOUND's source, would be MIT here if it is in fact independent. Reading `ias15_cft.c` to count it, as Q1 did, makes "independent" harder to show.
- **cft-rebound's port** derives from REBOUND (GPL-3.0-or-later) and stays GPL in cft-rebound; cft-debris could run it as a separate program, not copy it.
- **v1's rk4, euler and Störmer-Verlet** are cft-fp256's templates (Apache-2.0). An image carries cft-fp256's routines, so images stay out of this repository; our sources are ours.

## Q5. The ladder

COMPUTED by `q5\q5_ladder.py` (`logs\q5_ladder.002.log`); no figure here is MEASURED.
- **The main line** is the v1 route: rk4 at 15 s (3.3 m a day) and at 30 s (83 m a day), in a lockstep batch.
- **The models:**
  - degree 7, the largest this study's generator fits on `hip:N` today (Q2; narrowed at the merge): 8,291 to 8,396 instructions a step, MEASURED;
  - degree 20, which needs Q8's requests: an ESTIMATE of 30,000 to 40,000 a step. Its basis is a quadratic fit to degrees 6, 7 and 8 (29,900), and Q1's count ratio on the degree-8 image's gravity share (32,400), with up to a quarter more for spills.
- **IAS15 beside them**, labelled as a route v1 cannot run: 16,449 evaluations at a quarter of an rk4 step each, plus an ESTIMATE of 7,000 instructions a step of its own.

**Device time an object-day, and objects at one simulated day a day,** rk4 at 15 s, generic tier unless marked:

| device, format | degree 7: s an object-day / objects | degree 20 (ESTIMATE): s / objects | IAS15 at degree 20 (not v1) |
|---|---|---|---|
| RTX 5060 Ti, binary64 | 0.020 / 4.2-4.4M | 0.071-0.098 / 0.88-1.2M | 1.2-1.7M |
| RTX 5060 Ti, binary128 (ESTIMATE) | 0.036-0.038 / 2.3-2.4M | 0.13-0.18 / 0.48-0.66M | 0.65-0.89M |
| RTX 5060 Ti, binary256 | 0.090-0.100 / 0.87-0.96M | 0.32-0.47 / 0.18-0.27M | 0.25-0.37M |
| RTX 5060 Ti, binary256 fixed path | 0.010 / 8.7-8.9M | 0.035-0.048 / 1.8-2.5M | 2.5-3.4M |
| RTX 4070, binary64 | 0.022-0.027 / 3.2-3.9M | 0.080-0.13 / 0.67-1.1M | 0.92-1.5M |
| RTX 4070, binary256 | 0.058-0.069 / 1.3-1.5M | 0.21-0.33 / 0.26-0.42M | 0.36-0.57M |
| RX 7600, binary64 | 0.044-0.047 / 1.8-2.0M | 0.16-0.23 / 0.38-0.54M | 0.52-0.74M |
| RX 7600, binary128 (ESTIMATE) | 0.064-0.068 / 1.3-1.4M | 0.23-0.33 / 0.26-0.37M | 0.36-0.51M |
| RX 7600, binary256 | 0.117-0.127 / 0.68-0.74M | 0.42-0.60 / 0.14-0.21M | 0.20-0.28M |
| MI300X, binary64 (ESTIMATE, from GPU-E's and GPU-A's estimates) | 0.003-0.007 / 12-30M | 0.010-0.035 / 2.5-8.4M | 3.4-11M |
| MI300X, binary256 (ESTIMATE) | 0.008-0.020 / 4.4-12M | 0.027-0.094 / 0.9-3.2M | 1.3-4.4M |
| this CPU, one core, binary64 / binary256 (MEASURED rates) | 4.1 / 21k; 6.0 / 14k | 15-20 / 4.4-5.8k; 22-29 / 3.0-4.0k | 6.0-7.9k; 4.1-5.4k |
| six cores (BELIEVED linear), binary64 / binary256 | 126k / 86k | 26-35k / 18-24k | 36-47k / 25-33k |

At rk4 30 s every figure doubles.

**GPU-E's method, and what I take from it:**
- **(i) Lanes resident.** GPU-A's rates are at 1M resident lanes. A 28,149 or 68,450-object batch may not fill a card, and no program rate below 1M lanes is measured.
  - GPU-A's elementwise FMA series moves by up to 1.8 between 0.5M and 4M lanes (GPU-A-hip.md:495-497).
  - So I carry the factor of 1 to 3 from Q3 for small batches as well (ESTIMATE).
  - At a third of the rates, MASTER-8's 68,450 at degree 20 and binary256 still runs in real time on the RTX 4070 (1.3 to 2.0), but falls to 0.89 to 1.3 on the RTX 5060 Ti and 0.70 to 1.0 on the RX 7600. At binary64, every card stays at 1.8 or more (COMPUTED).
- **(ii) Live lanes.** A lockstep batch keeps every lane live, with no masks and no divergence. IAS15 would not.
- **(iii) Memory.** A lane's scratch at `hip:N` is 256 slots, 2 KB at binary64 and 8 KB at binary256, so 1.5 million objects need 3 to 12 GB of scratch alone. The 8 GB RX 7600 holds them only at binary64 or binary128, and 230 million fit on no device (COMPUTED; card memories BELIEVED).

**The speed-up at ESA's sizes,** degree 20 at rk4 15 s, in simulated days a wall day (COMPUTED; no occupancy loss applied, so see (i)):

| objects | RX 7600 binary64 / binary256 | RTX 5060 Ti binary64 / binary256 | MI300X binary64 / binary256 (ESTIMATE) | one core / six cores, binary64 |
|---|---|---|---|---|
| 28,149 (LEO, catalogued) | 13-19 / 5.1-7.4 | 31-43 / 6.5-9.6 | 87-300 / 33-114 | 0.16-0.21 / 0.93-1.2 |
| 47,393 (catalogued) | 8.0-11 / 3.0-4.4 | 19-26 / 3.9-5.7 | 52-177 / 20-68 | 0.09-0.12 / 0.55-0.74 |
| 68,450 (MASTER-8, > 10 cm) | 5.5-7.9 / 2.1-3.0 | 13-18 / 2.7-3.9 | 36-123 / 14-47 | 0.06-0.09 / 0.38-0.51 |
| 1.5 million (1 to 10 cm) | 0.25-0.36 / 0.10-0.14 | 0.59-0.81 / 0.12-0.18 | 1.6-5.6 / 0.6-2.1 | 0.003-0.004 / 0.017-0.023 |
| 230 million (1 mm to 1 cm) | 0.0017-0.0024 / 0.0006-0.0009 | 0.004-0.005 / 0.0008-0.0012 | 0.011-0.037 / 0.004-0.014 | 1.9e-5 to 2.5e-5 / 1.1e-4 to 1.5e-4 |

The replay budget's 95% bound for exp, 3.4% of one CPU core for 68,450 objects, is host work, and does not change these device figures. The budget for sin and cos is not determined (Q3; narrowed at the merge).

**The candidate hosts for a 24/7 run, and what else uses them** (READ, the TimeSheet's `resources.json`; relayed where marked):
- the desktop's RTX 5060 Ti, "used from WSL cft-gpu";
- the desktop's RTX 4070, which "drives the displays", so any use is Logan's call;
- the RX 7600 in nvidia-box. Relayed: another session's server (lemond) shares that machine.
- Our agents touch no WSL distro, so the host is Logan's decision (Q8).

## Q6. The density model

| | NRLMSISE-00 | JB2008 | the simpler model: an exponential atmosphere (Q2's, or DEBRIS-B's 28 bands) |
|---|---|---|---|
| why it is here | the open standard; Orekit carries it | the operational choice for drag; Orekit carries it | it is what v1 compiles today, and the real-time path's floor |
| accuracy as published | BELIEVED of order 15% (1σ) in total density in quiet conditions, worse in storms; the paper's page was not reachable (AGU 403; ADS 405) | BELIEVED of order 10% (1σ), better than earlier Jacchia models in storms; SET's page returns 403 | BELIEVED tens of percent: no solar or geomagnetic input |
| operations a call (Q1) | not counted: the HTML views stop before the methods; ESTIMATE 40-60 exp, ~10 log, 20-30 pow, 20-40 sin/cos, not determined (Q1; narrowed at the merge) | READ (via WebFetch), at 400 km: ~12 exp, ~12 log, ~225 pow, 6 sin/cos, ~316 quadrature points | MEASURED: 1 exp, 2 sqrt, 23 FMA-class |
| host cost, binary64 / 128 / 256 (COMPUTED: the counts above × Q3's host prices) | 18-29 / 49-77 / 170-260 ms a call | about 83 / 225 / 810 ms a call, nearly all pow | about 0.15 / 0.36 / 1.2 ms, nearly all the exp |
| measured cost elsewhere (MEASURED there) | 7.3-7.5 µs in Java at binary64 (DEBRIS-C) | 29.9-31.6 µs (DEBRIS-C) | 79.5 ns in C (DEBRIS-B) |
| in v1 | no, as written: `pow` refused. Rewrite: pow → exp(y·log x), integer powers as products | no, as written: pow refused; the quadrature is a fixed loop, so it can be unrolled | yes (MEASURED) |
| cost of the rewrite in a program (ESTIMATE, at Q2's routine sizes) | ~25 pow × ~400 instructions + 50 exp × 190 + 30 sin/cos × 400, about 3e4 instructions a call | ~225 × ~400, about 1e5 instructions a call | 180-201 instructions |
| licence | Orekit's Java is Apache-2.0 (its header, READ via WebFetch), and credits Picone et al.'s Fortran, Brodowski's C and Parraud's Java. NRL's Fortran is under an "Open Source Academic Research License" (DEBRIS-B, search excerpt). Brodowski's C shows no licence in its first 1,000 lines | Orekit's Java is Apache-2.0 and credits Bowman's 2008 Fortran. SET's Fortran is "under a license agreement" (DEBRIS-B), and its page returns 403 | ours (MIT) |

**pow through exp(y·log x) loses correct rounding** (BELIEVED, standard numerical analysis): log x is rounded once and the product with y again, so exp's argument carries about 2u relative error scaled by |y·log x|. For |y·log x| near 10 that is about 20 ulps of the result. The result stays deterministic and the same on every device, but it is no longer the correctly rounded pow, and a certificate's definition would be the rewritten expression. Integer exponents (most of NRLMSISE-00's: 2, 3, 4, 8, 12, 19) can be written as products instead.

**What an MIT repository may do** (BELIEVED, not legal advice; Logan decides):
- **Call** Orekit's Apache-2.0 models, as DEBRIS-C did.
- **Port** Orekit's Java under Apache-2.0's notice terms for that file.
- **NRL's and SET's terms:** whether NRL's academic licence reaches a port of Orekit's translation turns on the translation's provenance, which Orekit's header does not settle (READ). SET's agreement for its own JB2008 code is unseen.
- **The exponential model** is free of both.

**The precision question** (COMPUTED from Q3, BELIEVED where judged):
- **The density at binary64, the dynamics wide:** the density is a factor known to 10 to 15% (BELIEVED), so its binary64 rounding is invisible. On the host it costs microseconds a call in C or Java (DEBRIS-C), against 18 to 810 ms through libcft's correctly rounded host functions at the wide formats. Inside the program it would be a second image, or params handed per run.
- **Everything wide:** about 3e4 to 1e5 instructions a call, one to three times the degree-20 field again.
- **For cft-fp256's use case,** the wide-format dynamics stay the use case, and the density's inputs set the noise floor.
- **For a certificate,** a density computed outside the program is an input. Held fixed for a run, one block of space weather, it can be stated; recomputed per step on the host, it is a stream that changes between segments, which certificates cannot state.

## Q7. The 24/7 self-validation loop (designed; nothing run)

**The data:**

| data | source and cadence | terms |
|---|---|---|
| GP elements | CelesTrak checks for new data every 2 hours, and the 18 SDS data behind it update 2 to 3 times a day. Users should not download more than once every 2 hours (READ via WebFetch by the lead, the plan's sources) | "a limit on HTTP errors (301, 403, or 404) of 50 in a 2-hour period", then the firewall. A refused repeat download is a 403 |
| space weather | CelesTrak `SW-All.csv` / `SW-Last5Years.csv`. Kp/ap from GFZ Potsdam; F10.7 from Natural Resources Canada; NOAA SWPC's 3-hourly Kp and 45-day forecasts; NASA's monthly predictions. It carries Ap, 3-hourly ap, F10.7 observed and its centred 81-day mean, enough for NRLMSISE-00, but not JB2008's S10, M10, Y10 or DSTDTC (READ via WebFetch) | none stated on the page |
| Earth orientation | USNO's `finals2000A.daily`, released each day between 17:30 and 18:00 UTC, the last 90 days and 90 of predictions (READ via WebFetch, maia.usno.navy.mil/products/daily); CelesTrak's `EOP-All.csv` | "Approved for public release: distribution unlimited" |
| needs an account | Space-Track (TLE histories); laser ranging, where CDDIS needs Earthdata and EDC registration (DEBRIS-C) | Logan's credentials |
| elements to states | `sgp4` (Brandon Rhodes) compiles Vallado's C++ from "Revisiting Spacetrack Report #3", the 2023 May 09 release. It passes the reference tests, and its fallback agrees to 0.1 mm. `SatrecArray` takes a batch. Version 2.27 (READ via WebFetch, pypi.org/project/sgp4) | MIT |

**Polling that cannot reach the error limit** (designed): one process owns all fetching. It fetches each GP group at most once in any 2 hours, on a fixed schedule, keeping each response's `Last-Modified` or ETag; it never retries a 403 or 404 in the same 2-hour window; and it stops every fetch at 10 non-200 responses in a rolling 2 hours, a fifth of the limit, until a person looks.

**The statistic** (designed): DEBRIS-C's M4 bands, with truth from later TLEs.
- **Truth:** each earlier fit propagated to a new element set's epoch, against that set through SGP4 at zero age.
- **The TLE error model:** a covariance from TLE-to-TLE differences, by Flohrer et al.'s or Geul, Mooij and Noomen's method, with Bamann's non-Gaussian caution (DEBRIS-C's READ excerpts), fitted on a calibration month and frozen.
- **The test:** z = Δ along a direction ⁄ sqrt(hᵀ(P_pred + P_TLE)h). PASS for a horizon bin (1, 2, 3, 5, 7 days) with N ≥ 50 iff the count with |z| ≤ 2 lies in the two-sided 99% binomial interval and the mean of z² lies in χ²(N)'s 0.5 to 99.5% band over N (for N = 86: 76 to 86, and 0.651 to 1.436). Otherwise FAIL; below 50, not determined.
- **Covariance in the language** (READ, LANGUAGE.md "The variational equations", from 1981, and :3277-3279): tangent vectors are declared one by one (`tangent v1, ..., v6`), and "nothing builds an n by n matrix". So six declared vectors carry the state transition matrix, and P = ΦP₀Φᵀ is formed on the host.
  - A ballistic coefficient's sensitivity needs it in the state, since v1 has no tangents with respect to params.
  - Each vector adds about one step's arithmetic again (BELIEVED).

**Divergence, each criterion stated now** (designed; the thresholds are BELIEVED):
- **Flag** an object when its z² mean over the last 20 comparisons leaves the N = 20 band of χ²(20)/20 at 0.5 to 99.5% (0.372 to 2.000, COMPUTED with mpmath's regularised incomplete gamma; not in a log).
- **Refit** when an object's new element set's along-track miss exceeds 5σ of its predicted covariance, or its fit is older than 3 days.
- **Refuse** a prediction when its predicted along-track 1σ exceeds 10 km (DEBRIS-C's rule, fixed before the data).
- **Refuse a whole run** when any lane's flags carry invalid or a mark the replay cannot decide (`replay-undecided`).

**Certificates, once support reaches the GPU backend, and replay** (READ, designed):
- **Cut:** runs of one forcing block and one dense batch, in 24-step segments (6 minutes at 15 s), every boundary state kept: about 240 segments a run-day.
- **A sampled audit** of k of S segments misses one bad segment with probability (S − k)/S, and f bad ones with C(S−f, k)/C(S, k) (CERTIFICATES.md:66-73). For S = 240, k = 24 misses one with probability 0.90 and k = 120 with 0.50 (COMPUTED), each run sampled on its own.
- **Entries:** `drift` of h_z and `step-halving` at every format, `wider-source` at binary64 and binary128. Keyed or open is Logan's choice, per certificate.
- **Outside what a certificate covers:** GP parsing, SGP4 (outside libcft), the elements' noise, the space-weather and EOP inputs' correctness, and Q2's list.
- **Replay:** GPU-A P2.1 ran libcft's programs bit for bit on three cards and the CPU, lane bytes included (READ), and the host's definition replays marked lanes. So any segment of a day's GPU run can be re-run on this CPU from its boundary state and compared bit for bit, and a disputed object-day can be replayed alone.

**What it costs around the clock** (COMPUTED from Q5, degree 20 at rk4 15 s): for 68,450 objects, 2.1 to 7.9 days a wall day at binary256 to binary64 on the RX 7600, so 13 to 48% of the card at the estimated rates. At a third of them, Q5's ESTIMATE factor, binary256 needs about 143% of the card. The figure prices one object-day per object a day. It leaves out the loop's own work: comparing each new element set with propagations from earlier fits, out to 7 days (narrowed at the merge). SGP4 for the truth sets is negligible (BELIEVED). The fetches are a few megabytes a day (BELIEVED).

## Q8. The first build, laid out for Logan

Each milestone with its gates, owner and dependencies. Costs are ESTIMATEs of agent wall time and CPU, and all are BELIEVED.

| milestone | owner | gates | depends on | cost |
|---|---|---|---|---|
| **M1. A CPU reference at libcft's formats, in v1:** degree 7 (8 on `sw:512`), rk4, objects as lane params, Sun, Moon and EOP as per-run blocks, exponential air, run on the software executor | cft-debris (MIT): systems, generator, drivers | Q2's three checks at every format; DEBRIS-C's authorities (Lasser et al.'s gravity to 1e-11 m/s², their third bodies, `testpo.421` through the per-block route); dense runs, fixed streams, boundary states | nothing new | 2 to 3 study days; CPU in minutes |
| **M2. The GPU route, replay-checked against M1** | cft-debris for the systems; cft-fp256 for `hip:N` and its tools | every lane bit for bit with M1 at segment boundaries, marked lanes replayed by the definition | a GPU parcel booked by cft-fp256's lead; Logan's host; for degree 20, requests 1 to 3 | a GPU parcel of hours |
| **M3. The 24/7 loop on a local host** | cft-debris | Q7's polling ledger, statistic and criteria on a calibration month, then a held-out month | Logan's host (5060 Ti under WSL cft-gpu, 4070, or the RX 7600 shared with lemond); Space-Track credentials for TLE histories | days to build; the card's 13 to 48% at degree 20 |
| **M4. MI300X runs** | cft-debris, with cft-fp256 | M2's gates on gfx942 | Logan's word and the price first | paid |

**Requests for cft-fp256**, for the lead to put to cft-fp256's lead, with the evidence:
1. **A larger bank, or index tables on `hip:N`**, for gravity coefficients: degree 8 is refused `bank-capacity` at binary256 (516 > 512) and degree 20 at every format (1,762 params). INDEXED is absent from 0x75f1f.
2. **A scratch depth above 256 on `hip:N`** (round 2's 2,048): degree 8 needs 273 slots (`scratch-capacity`).
3. **cftc's handling of very large systems:** degree 20 as lane params did not compile in 290 s (283 CPU-s).
4. **pow as a routine, or powr/pown:** NRLMSISE-00 and JB2008 need it; `transcendental` refuses it, and JB2008 makes about 225 calls a call.
5. **A `hip` target in cftc,** so these by-hand comparisons become refusals by name.
6. **binary128 program rates on the cards,** and program rates below 1M lanes (Q5's factor of 1 to 3).
7. **The specialised tier for programs** (round 3): the fixed path is 2.1 to 9.7 times the generic at binary256 (GPU-A P2.1).
8. **An in-kernel divide and root** (GPU-E's question 2, line 474) only if an IAS15 wave kernel is wanted; the v1 route does not need it.
9. **Certificates for forcing that changes between segments,** if one run a day is wanted instead of one a block; and a rounded or enclosed accuracy method for distances.
10. **Already requested** (lead.md 20:30): certificates of `hip:N` runs, with identity, depth, and an audit in C.

**What cft-debris would give back** (relayed request): the drag system, `j2dragrot-rk4.cftl`, compiled at binary128 and binary256 with 24-step segments, with its software-backend states and lane bytes, as a case beside the golden corpus in the gate for GPU certificates. Its sources and rebuild commands are in `debris-d\`.

The evidence does not decide the density model, the 24/7 host, or IAS15 against rk4 for the GPU. I make no recommendation on them.

## Measurements and their commands

All runs go through `python -I -B studies/debris-d/tools/cpurun.py <label> <ledger> -- <command>`, from `cft-debris-scratch/DEBRIS-D`, with mingw64 first on PATH. Logs are in `studies/debris-d/logs/`.

| what | command | log |
|---|---|---|
| libcft and tools | `make -C host CC=gcc OS=Windows_NT TMP=/tmp TEMP=/tmp libcft.a cft-bench.exe cft-segrun.exe cft-audit.exe positive-run.exe cft-asm.exe` in the extracted archive | scratch `logs/build.001.log` (0 warnings; build id `unknown`) |
| drivers | `gcc -std=c99 -O2 -I <archive>/host/include tools/seqrun.c <archive>/host/libcft.a`; the same for `tools/opbench.c` | - |
| Q1 counts | `python q1/make_count_build.py <scratch>/q1/count_kernels.inc [--plant]`; `g++ -std=c++17 -O1 -I <dir> q1/count_ops.cpp`; `python q1/q1_counts.py`; `python q1/q1_objectday.py` | `q1_counts.001`, `q1_objectday.001` |
| Q2 first test | `python q2/q2_first_test.py j2-rk4 fp64 fp128 fp256`, and the same for `j2dragrot-rk4` | `q2_first_test_j2-rk4.002`, `q2_first_test_j2dragrot-rk4.001` |
| Q2 capacities | `python q2/gen_field.py N <scratch>/systems/fieldN-rk4.cftl [--lane]`; `python q2/q2_degree_sweep.py 6 7 8`; cftc on `field8` with `--target sw:512`; `python q2/q2_refusals.py` | `q2_degree_sweep.001`/`.002`, `q2_refusals.001`; scratch `logs/cftc-*.log` |
| Q3 host | `python q3/q3_host.py`, inside B0024 | `q3_host.001` (a quick functional run outside the window is `q3_host_quick.001`, not a result) |
| Q3 marks | `python q3/q3_marks.py` | `q3_marks.001` (control failed), `.002` |
| Q4 | `python q4/make_q4_kernel.py`; `gcc -O2 -DREAL=double` / `-DREAL="long double"` / `-shared -DQ4_DLL q4/q4prop.c`; `python q4/q4_integrators.py` | `q4_integrators.001` (reference failed), `.002` |
| Q5 | `python q5/q5_ladder.py` | `q5_ladder.002` (001: the same figures, with citations corrected after) |

## What this study could not settle

- **Degree 20 as a program:** it is refused by the bank, and its lane-param form did not compile within the stop rule. Its instruction count, and so Q5's degree-20 rows, are an ESTIMATE.
- **Rates on the cards for our images:** no GPU ran. The mix, batch-size and binary128 factors are ESTIMATEs, and nothing here is measured on a GPU.
- **NRLMSISE-00's operation counts:** the HTML views stop before the code, and fetching the raw file is a download nobody approved.
- **The density models' published accuracies:** the papers' pages refused the fetch, so the figures are BELIEVED.
- **The replay budget's true rate:** for exp, 0 marks bounds it; it does not measure it. For sin and cos, nothing bounds it: every lane shared their argument (narrowed at the merge).
- **Whether the accidental WSL command** (below) touched anything: I did not look inside WSL. Relayed (lead.md, 21:24): cft-fp256's lead reads the default distro as cft2204, its own, with nothing of its running then, and needs no action.

## What the brief got wrong, and what I did not do

- **The Rules lacked a trap.** From Python, Windows' CreateProcess searches System32 before PATH. My wrapper's bare `bash -c` at 21:22:04 started `C:\Windows\System32\bash.exe`, the WSL launcher, for 0.24 s. A `gcc` there failed on its path and wrote nothing, as far as the Windows side shows. This breaks "No GPU, WSL, card or box", by accident; it is reported in my ledger at 21:22:34. Since then I start every program by its full path (the lead's ruling).
- **A second System32 name** (added at the merge): a bare `timeout` at 20:58 resolved to `C:\Windows\System32\TIMEOUT.EXE` and failed harmlessly. DEBRIS-D's ledger records it, but the study as reported omitted it (verifier-D).
- **The brief's drag-and-rotation system names no force that needs sin and cos of ω t,** since co-rotating air needs no trigonometry. I used the degree-2 tesserals in the Earth-fixed frame, so that the routines carry physics.
- **"Störmer-Verlet at fixed steps" with drag cannot be run in v1:** it is refused `verlet-not-separable`. I measured it without drag only.
- **The stop rule bit on compile time,** not on the interpreter: degree 20 was stopped by my own 290 s timeout.
- **Not done:**
  - no certificate written or audited (Logan's word);
  - nothing on a GPU;
  - no `cft-segrun` or `cft-audit` run, though both were built;
  - no download;
  - no JB2008 reference check;
  - no instrumented build of `ias15_cft.c` (its count is READ);
  - no run of the reference interpreter past the first test's sizes.

## Sources

- **cft-fp256 at 0aa997a3, from the lead's archive (READ):** `docs/LANGUAGE.md`, `docs/CERTIFICATES.md`, `docs/HOSTAPI.md:2239-2295`, `docs/BENCHMARKS.md`, `docs/studies/GPU-A-hip.md`, `docs/studies/GPU-E-mi300x-ring.md`, `host/include/cft.h`, `host/tools/positive-run.c`, `python/cftc/`, `programs/systems/kepler-sv-fp64.cftl`.
- **cft-rebound (READ by `git show` at de376d8):** `src/ias15_cft.c`, copied to my scratch.
- **The relayed answers** in the ledger's `relayed\`, and `lead.md`.
- **This repository:** DEBRIS-B and DEBRIS-C, and their `q2bench.c` and `m1a_grav.c`.
- **READ via WebFetch:**
  - https://github.com/CS-SI/Orekit/blob/develop/src/main/java/org/orekit/models/earth/atmosphere/NRLMSISE00.java, `JB2008.java` and `AbstractJacchiaBowmanModel.java`;
  - https://github.com/magnific0/nrlmsise-00/blob/master/nrlmsise-00.c;
  - https://pypi.org/project/sgp4/;
  - https://celestrak.org/SpaceData/ and https://celestrak.org/SpaceData/SpaceWx-format.php;
  - https://maia.usno.navy.mil/products/daily;
  - https://www.iers.org/IERS/EN/DataProducts/EarthOrientationData/eop.html (no products listed).
- **Refused:** https://sol.spacenvironment.net/jb2008/ (403), https://agupubs.onlinelibrary.wiley.com/doi/10.1029/2002JA009430 (403) and https://ui.adsabs.harvard.edu/abs/2002JGRA..107.1468P/abstract (405).
- **The downloads** (SHA-256 in `lead.md`): `EIGEN6-C4.gfc`.

## Narrowed at the merge, from verifier-D's report

verifier-D's report (`studies\DEBRIS-D-verifier-D-report.md`) found one defect, two claims that run past their evidence, and notes. It re-ran most of the study and confirmed it:
- the build and the first test;
- the degree sweep;
- Q1's counts;
- Q3's host prices, within 10% at a load of at most 11%, in window B0026;
- Q4's integrators;
- Q5's and Q7's arithmetic;
- Q2's claims, against the archive;
- the records.

The lead checked the defect against the script and the system before narrowing. `q3_marks.cf73c3231f5d.py` starts every lane with t = 0.0, and `j2dragrot-rk4.cftl` takes `th = w * t`. There was no send-back: the counts stand, and each narrowing states what the evidence does not cover.

**Narrowed**, each marked in the text:
1. **Short answer 7, Q3's replay budget and its price, Q5's note, and "could not settle":** the 95% bound of 1.5e-5 an evaluation, and the 3.4% of a core it prices, hold for exp only.
   - sin and cos took w·t, which every lane shared from t = 0: 193 distinct arguments in 147,456 calls, with no positive control.
   - Their marking rate is not determined. A marked time would mark every lane at once, at a cost of about 8,200 CPU-s for 68,450 lanes.
2. **Short answer 3 and Q5's models:** degree 7 is the largest field in the form this study's generator writes (`gen_field.py`: sums unrolled, every coefficient product a param). Other forms were not tried.
3. **Short answer 6:** the claim rests on the ESTIMATE of degree 20's instruction count. At a third of the rates, the RX 7600 at binary256 runs 68,450 objects at only 0.70 to 1.0 of real time.
4. **Q7's cost:** 13 to 48% is at the estimated rates, and about 143% at a third of them. It also leaves out the loop's own work of comparing new element sets with earlier fits, out to 7 days.
5. **Short answer 1:** the 799 FMA-class operations are for an object in sunlight; in penumbra, they are 821, with 33 divisions.
6. **Q1 and Q6, NRLMSISE-00:** the per-call ESTIMATE rests on WebFetch summaries that gave different counts when asked again, so it is not determined.
7. **Added:** the bare `timeout` at 20:58, which resolved to System32's `TIMEOUT.EXE` and which the study as reported omitted.

**Notes** from verifier-D, not narrowed:
- **Q2's check (b):** its tolerance is about 50 times the observed agreement, so a defect of tens of ulps would pass (b). Check (a), bit for bit against `lang.run`, is the binding one.
- **Q1's hand count:** the docstring holding control C1's hand count was written after the first build run, as DEBRIS-D says.
- **The stop rule:**
  - DEBRIS-D's message (21:11:22) came during the degree-20 lane-param compile, which began at 21:09:35 under its own 290 s timeout.
  - The timeout kept the compile under 5 CPU-minutes (282.9 CPU-s), and the lead's 21:12 ruling stands.
- **The sequencer range:** verifier-D measured 44.9 to 122 ns a lane-instruction, against the study's 50 to 125, within its ±30% tolerance.
- **The reports' lengths:**
  - verifier-D counts 1,150 words in the filed DEBRIS-D report. The lead finds that this count includes the filing header; the body is 1,085 words, as `file_report.py` printed.
  - Both counts run past the brief's 1,000-word limit.
  - verifier-D's own report runs to 1,799 words in its body, as `file_report.py` printed, past its 1,200. The whole file counts 1,866 with its header (merge-check-D).
- **verifier-D's slip:** it typed a ledger heading as "22:02" from memory, when `date` read 22:01. It appended a correction.
