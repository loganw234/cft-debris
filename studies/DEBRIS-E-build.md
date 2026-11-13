# DEBRIS-E: the build report for M1, the CPU reference propagator

Written by DEBRIS-E (claude-opus-5-5) on 2026-11-13 for round DEBRIS-E, under the plan of record `studies\DEBRIS-E-plan.md` (draft 3, SHA-256 `9c5d0b9b…db760`). **Nothing here has been verified:** verifier-E has not yet run. Labels as in the plan: MEASURED (a run, its command and log named), READ, COMPUTED (arithmetic from labelled inputs), ESTIMATE (basis and range named), BELIEVED.

At the merge the lead made five narrowings and one addition, and wrote this note, following verifier-E's report (`studies\DEBRIS-E-verifier-E-report.md`). verifier-E ran after DEBRIS-E wrote the sentence above. The changes touch seventeen places, each marked "narrowed at the merge" or "added at the merge", and the last section lists them. The text as DEBRIS-E reported it (SHA-256 `636ed5cdbfbafa5c9dd664b86a99f1bc9de4360a1934718076973a331f7f4aeb`) is kept in the project's ledger, as `filed\DEBRIS-E-build.as-reported.md`.

## 1. In short

**What was built.** M1 is in `src\` and its gates are in `tests\`.
- **One force-model source,** `src\m1_physics.h`, is compiled once for each of six number kinds: native32 (C `float`), native64 (C `double`), and libcft's software backend at binary32, binary64, binary128 and binary256 (cft32 to cft256).
- **Every operation is lane-batched.** No branch depends on a lane's data.
- **The force model:**
  - the central term;
  - EIGEN-6C4 to degree 180, in a uniformly turning Earth;
  - the Sun and the Moon, read from DE421 by a C reader of the binary;
  - drag through the 28-band exponential atmosphere, co-rotating;
  - radiation pressure with a conical shadow.
- **The integrator** is rk4 at a fixed step, over all lanes on one time grid. A lane's state is kept at every step, so a run can be cut into segments and restarted from any boundary.

**The gates.** Each gate's criteria are written in its script before the data. The script asserts them, and every log begins with them.

| gate | result | the evidence that carries it | log (on the final build unless noted) |
|---|---|---|---|
| E1 native against cft, kernel by kernel | PASS | 166,103 constants and table entries, and 10,000 lanes per kernel (64 at degree 180), native equal to cft bit for bit at binary64 and binary32; the transcendental kernels equal too once they are routed to libcft; the negative control broke only cos C, and the gate said where | `e1_gate.002.log` |
| E2 native against cft, whole runs | PASS | 8 lanes, 100 steps of 60 s, every force: native64 equals cft64 and native32 equals cft32, bit for bit at every step | `e2_gate.003.log` |
| E2's control as first specified | **FAILED** | the one ulp planted in lane 3's x was rounded away in the first step; its replacement (the ulp in z) passed | `e2_gate.001.log`, `.002`, `.003` |
| E3 the precision ladder | PASS | cft128 against cft256: at most 7.59e-26 m, against a stated bound of 6.25e-20 m; the control broke the bound by 6.3e9 times | `e3_gate.002.log` |
| E4 Lasser et al. | PASS | gravity, degrees 2 to 180: 2.28e-15 m/s² at most (native64 and cft64, all 2,880 epochs) and 1.49e-15 m/s² (cft128 and cft256, every tenth epoch); the Sun 1.3e-17 and the Moon 4.3e-16 m/s²; tolerance 1e-11; the truncation control was reported at 98 and 89 times the tolerance | `e4_gate.001.log` (build 2) |
| E5 JPL's `testpo.421` | PASS | 109 points of the Earth, Moon, Sun, SSB and EMB: within 4.9e-16 AU at cft64 and 4.2e-16 AU at cft128 and cft256; tolerance 1e-13 AU | `e5_gate.002.log` |
| E5's control as first specified | **FAILED** | the coefficient was planted in a coordinate the test point did not test; the corrected plant was reported | `e5_gate.001.log`, `.002` |
| E6 Orekit, force by force | PASS | 1,000 states: gravity within 7.3e-17 m/s² (tolerance 1e-14); drag within 6.8e-14 relative (1e-9); radiation sunlit within 1.3e-15 relative (1e-9), umbra exactly 0; three 1% plants each broke their tolerance | `e6_gate.003.log` |
| E6's gravity criterion, first run | **FAILED** | 7.5e-11 m/s²: I had turned Orekit's frame on TAI seconds while ours turns on TDB seconds; once matched, it passed with the criterion unchanged | `e6_gate.001.log` |
| E7 REBOUND as referee | PASS, with a limit | our rk4 at 5 s against IAS15 at ε 1e-9: 0.114 m (tolerance 0.5 m); the J2 plant gave 1,110 m. But IAS15 itself moves 0.21 m between ε 1e-9 and 1e-10 on this model, and 3.8e-5 m with radiation pressure off; that the shadow's edges are the cause is inferred, not isolated (narrowed at the merge) | `e7_rebound.003.log`, `e7_diag.003.log` |
| E8 reproducibility | PASS | all six kinds: two runs identical, `-O0` equal to `-O2`; five restarted segments equal to the continuous run at native64, cft64 and cft128, the kinds R4 ran (narrowed at the merge); the contracted build differed, as required | `e8_gate.002.log` |
| E9 cost | measured, in window B0030 | a lane's force evaluation at degree 20 takes 2.0 to 5.5 µs at native64 (0.05 to 0.14 s an object-day with rk4 at 15 s), 2.2 to 3.3 ms at cft64 (55 to 97 s) and 9.5 to 13.5 ms at cft256 (222 to 340 s). At binary64 the six correctly rounded transcendentals are about 30 to 35% of a cft64 evaluation; at binary128 and binary256 their share was not measured (narrowed at the merge; §8) | `e9_time.001.log` |

**How the native kinds and the cft kinds compare** (MEASURED, E1 and E2).
- Wherever only addition, multiplication, FMA, division and square root are involved, the native kinds equal the cft kinds bit for bit at binary64 and at binary32, on every input tried.
- With the C library's `exp`, `sin`, `cos`, `asin` and `acos`, almost every kernel output still equalled the cft kind's, bit for bit (narrowed at the merge). The figures below are differences in the kernels' outputs, not the functions' own errors. Against mpmath on 20,000 arguments, verifier-E found the functions within 0.79 ulps (`asin`), 0.84 (`acos`), 1.60 (`sin`), 1.49 (`cos`) and 0.50 (`exp`), so all but `exp` are not correctly rounded there (MEASURED by verifier-E):
  - the rotation kernel's outputs differed by 1 to 2 ulps in 5 of 10,000 lanes at binary64, on seed 0xE1. The figure depends on the lanes: on verifier-E's seed, 0x5EED77, the x output differed by up to 32 ulps, in 2 of 5,000 lanes (narrowed at the merge);
  - the radiation-pressure kernel's outputs (the acceleration and ν) differed in 12 of 10,000 lanes at binary64, by up to 1.2e10 ulps, while `asin` and `acos` themselves are within 0.84 ulps on verifier-E's arguments. That the penumbra's arithmetic amplifies their last-bit differences is BELIEVED (§6, item 3; narrowed at the merge). All 12 are penumbra lanes, out of 49, and their ν differs by 4.5e-13 to 1.4e-6 relative (`e1_penumbra.001.log`; §6);
  - nothing else differed: no drag lane at either width, and no rotation or radiation lane at binary32.
- No E2 trajectory differed at any step with the C library's transcendentals.

## 2. What was built

### The files

**In `src\`, every file headed cft-debris, MIT:**
- `m1.h`, the interface: the kinds, the model, the context, and each kind's table of entry points (`m1_vt`).
- **The number layer:** `m1_ops_native.h` and `m1_ops_cft.h`.
- `m1_physics.h`: the force model and rk4, written once.
- `m1_kind.h`, which assembles one kind. Each `kind_<name>.c` sets the kind's macros and includes it.
- `m1_consts.h`: every constant as its decimal string, with its source.
- `gfc.c`: the `.gfc` loader. It keeps each coefficient's decimal string.
- `de421.c`: the DE421 binary reader. It reads the header, the records and the choice of record and sub-interval; the Chebyshev sums are the kinds' own.
- `m1_common.c`: the arena of temporaries, the error exit and the table of kinds.

**In `tests\`, every file headed cft-debris, MIT:**
- `build.sh`: the build, with the object checks.
- `m1run.c`: the gates' driver. It writes every result as the hexadecimal of its encoding.
- `m1x.c`: the native64 model as a DLL, for E7.
- `fmacheck.c`: E1's `fma` finding.
- The gate scripts: `e1_gate.py`, `e1_fma.py`, `e2_gate.py`, `e3_gate.py`, `e4_gate.py`, `e5_gate.py`, `e6_gate.py` with `e6_orekit.js` and `e6_gfc_copy.py`, `e7_rebound.py`, `e7_diag.py`, `e8_gate.py` and `e9_time.py`.
- `gatelib.py`, which the gate scripts share.
- `cpurun.py`, DEBRIS-D's CPU wrapper, reused unchanged in its code.

Reused with a note in each file: DEBRIS-C's `m1a_grav.c` (gravity), DEBRIS-B's `q2bench.c` (the atmosphere and the shadow), DEBRIS-C's `m1b_check.py` (the body sums), DEBRIS-D's `q4prop.c` (rotation and rk4), DEBRIS-C's `m0_gate.js` (the Orekit setup) and `derive_gfc_copy.py`, and DEBRIS-D's `cpurun.py`. No third-party source is in the repository. libcft is linked from my scratch build and reached by an include path. REBOUND is imported as installed. Orekit is called through Nashorn.

### The number layer (B1)

**C11, with one header included once per kind, rather than C++ templates** (the reason is also in `m1_kind.h`):
- The cft kinds' elements are opaque bytes, reached only through libcft's C API.
- The native kinds need intrinsics, and exact control of how each expression rounds.
- The build checks each kind's object file on its own.

One plain C translation unit per kind keeps all three visible.

**Every operation acts on n lanes.** An operand can be marked scalar, one element applied to every lane.
- **In the cft kinds,** a scalar is `cft_elem_args`'s `scalar_mask` on `cft_run_ex`. The operations used:
  - `CFT_ADD`, `CFT_SUB`, `CFT_MUL`, `CFT_FMA`, `CFT_NEG`, `CFT_CMPLT`, `CFT_CMPLE` and `CFT_SELECT`, through `cft_run_ex`;
  - `cft_div` and `cft_sqrt`, with any scalar expanded first;
  - `cft_exp`, `cft_sin`, `cft_cos`, `cft_asin` and `cft_acos`;
  - `cft_convert`, `cft_from_decimal_char` and `cft_cvt_from_i64` for conversions.
- **In the native kinds:**
  - each operation is one loop;
  - every fused multiply-add is `_mm_fmadd_sd` or `_mm_fmadd_ss`, and every square root `_mm_sqrt_sd` or `_mm_sqrt_ss`;
  - `-ffp-contract=off`, no `-ffast-math`, and `-mfma`;
  - `FLT_EVAL_METHOD == 0` is checked at compile time with `#error`, and the CPU's FMA3 at start with `__builtin_cpu_supports("fma")`.
- **Three compound operations,** `a·b + e·f`, `a·b − e·f` and the 3-term dot product, are one C expression a lane in the native kinds. With contraction off they round exactly as the cft kinds' separate calls do, and a contracted build can fuse them, which is what lets E8's control fail.
- **Branches on data are selects:** the atmosphere's band choice, the four shadow cases and the clamps.

**Constants enter each kind once,** each from its decimal string: `strtod` or `strtof` in the native kinds, `cft_from_decimal_char` in the cft kinds. Their sources are in `m1_consts.h`.
- The field's GM, reference radius and coefficients are the `.gfc` file's own strings.
- DE421's EMRAT and AU are the binary's binary64 values. They convert exactly into the wider kinds, and are rounded into binary32.

**Derived tables are computed in each kind,** never converted from binary64: the recursion's An and Bn, Dg and Sd, F1, FA, FB and FZ.
- Each entry is sqrt(N/D), where N and D are exact integers formed on the host. In each kind it takes one conversion of each integer, one division and one square root, in a fixed order.
- E1 holds native64's tables equal to cft64's, and native32's equal to cft32's, entry for entry.

**Batches:**
- E4 sizes its batches so that V and W stay within 192 MB. At degree 180 that is 512 lanes (the cap) at binary32 and binary64, 360 at binary128 and 180 at binary256 (MEASURED from its outputs' headers).
- The arena of temporaries is 640 elements a lane.
- Working memory therefore stays under 1 GB at every kind. COMPUTED for the largest batch, cft256 at degree 180 with 180 lanes: about 220 MB in all (V and W 192 MB, the tables about 8 MB, DE421 14 MB, the arena 5 MB). The peak working set was not measured.

### The force model (B2)

- **Gravity:** DEBRIS-C's normalised Cunningham recursion in the Earth-fixed frame, degrees nmin to nmax (≤ 180), operation for operation. The central term is a separate kernel.
- **The Sun and the Moon,** as point masses: a = GM (d/|d|³ − s/|s|³), with GROOPS's GM values from Lasser et al.'s README.
  - The reader: the host chooses each lane's record and sub-interval and gathers its coefficients. The kind computes τ = (dt + dt)/len − 1 and then a Clenshaw sum, b = fma(2τ, b₁, cᵢ) − b₂.
  - Earth = EMB − Moon/(1 + EMRAT); the geocentric Sun = Sun − Earth.
- **Drag:** a = −bc ρ |v_rel| v_rel, with v_rel = v − ω × r (by FMA) and bc = Cd A/(2m).
  - ρ comes from the highest band whose base lies at or below h = |r| − R_EARTH: 28 bands (DEBRIS-B's table), or 1 band for E6.
- **Radiation pressure:** a = ν P_SUN (AU/|d|)² (Cr A/m) d/|d|, with d = r − r_sun.
  - ν is DEBRIS-B's conical shadow. Its four cases (sunlit, umbra, annular, penumbra) are all computed and selected in that order of precedence.
- **The frame:** θ = fma(ω, t, θ₀), with ω = 7.292115e-5 rad/s and θ₀ = 0.3 rad. It is a uniform rotation about z (decision 6), stated as a limit (§7).
- **The total:** a = (((((central + harmonics) + Sun) + Moon) + drag) + radiation). The Sun, the Moon and the frame are evaluated once a stage for the batch.

### The integrator (B3)

- **rk4 at a fixed step** (`ph_rk4`). The stages use fma(h/2, k, y) and fma(h, k₃, y), and the step's end is y ← fma(h/6, (k₁ + 2k₂ + 2k₃) + k₄, y).
- **Step j's time** is (step0 + j)·h, on the host, exactly.
- **Segments:** every lane's state goes to a callback after every step. `m1run traj --step0 s --from file` restarts a segment from a boundary state written in hex.
  - E8 R4 shows five restarted segments equal to the continuous run, bit for bit, at native64, cft64 and cft128. R4 did not run native32, cft32 or cft256 (narrowed at the merge).
  - No certificate is written.

## 3. How to build it

**The tools** (all MEASURED on this host): gcc 16.1.0 (Rev5, Built by MSYS2 project) from `C:\msys64\mingw64\bin`, GNU objdump (binutils) 2.46, GNU Make 4.4.1, Git Bash's bash 5.2.26, Python 3.12.15 (Miniconda3), REBOUND 5.1.1, and Java 1.8.0_411 with Orekit 13.1.9 and Hipparchus 4.0.3 from the downloads.

**1. libcft,** from the archive, in the scratch:
```
sha256sum cft-debris-ledger/tools/cft-fp256-0aa997a3.tar      # e01003cc...b8 (matched)
mkdir -p cft-debris-scratch/DEBRIS-E/cft-fp256
tar -xf cft-debris-ledger/tools/cft-fp256-0aa997a3.tar -C cft-debris-scratch/DEBRIS-E/cft-fp256
export PATH="/c/msys64/mingw64/bin:$PATH"; gcc -dumpmachine     # x86_64-w64-mingw32
cd cft-debris-scratch/DEBRIS-E/cft-fp256 && make -C host CC=gcc OS=Windows_NT TMP=/tmp TEMP=/tmp libcft.a
```
- The log is `records\build_libcft.001.log`; the build id is `unknown`.
- My build's `libcft.a` has SHA-256 `f0eec4f25f53521006526ba3376dd616997b90c7223145c66f6ddbc6aaca67a5`.

**2. M1,** every variant, with the object checks: `bash tests/build.sh <cft-fp256>/host <build dir>`.
- **The variants and their flags:**
  - O2: `-std=c11 -O2 -ffp-contract=off`, and `-mfma` for the native kinds;
  - O0: the same at `-O0`;
  - fast: the native kinds at `-O2 -ffp-contract=fast -mfma`;
  - negctl: O2 plus `-DM1_NEGCTL_REORDER` for the native kinds;
  - nofma and fma: `fmacheck.c` without and with `-mfma`.
- **It links** `m1run_<variant>.exe`, `m1x.dll`, `fmacheck_nofma.exe` and `fmacheck_fma.exe`, each against `libcft.a -lm`.
- **Its five criteria are asserted:**
  - the target triple;
  - every native object of O2, O0, fast and negctl holds at least one `vfmadd`, and has no undefined `fma`, `fmaf`, `sqrt` or `sqrtf` (`nm -u`);
  - `FLT_EVAL_METHOD` is 0;
  - `fmacheck_nofma.o` calls the library's `fma`, and `fmacheck_fma.o` holds a `vfmadd`;
  - every link succeeds.
- **What the checks found** (MEASURED, `logs\build.003.log`): 12 `vfmadd` per native object at O2 and negctl, 1 at O0, and 23 in the fast build, where the contracted compound operations add 11. No undefined `fma`, `fmaf`, `sqrt` or `sqrtf`.
- **The three builds of this round:**
  - build 1 (`build.001.log`) ran E1 log 001 and `e1_fma.001.log`;
  - build 2 (`build.002.log`) ran E2 logs 001 and 002, E3 log 001, E4, E5 log 001, E6 logs 001 and 002, E7 logs 001 and 002, `e7_diag` log 001 and E8 log 001;
  - build 3 (`build.003.log`) is the final build. It lists the SHA-256 of every source, and every other log ran on it.
  - Between the builds only `tests\m1run.c` and `tests\m1x.c` changed: new options for the controls and the diagnosis.
  - Every `src\` file was last modified at 06:05:38 or earlier, before build 1 at 06:16. That is file modification times (MEASURED); builds 1 and 2 did not print source hashes.
  - Executables are not byte-reproducible from build to build, since a PE header carries a timestamp. Gates therefore compare outputs, and every log names the SHA-256 of the binaries it ran.

**3. The gates:** `python -I -B tests/<gate>.py`, with the build directory in `M1_BUILD` (default: my scratch's `build\main`). E9 takes the TimeSheet booking's ID: `tests/e9_time.py B0030 2`, where 2 is the minimum seconds per measurement. B0030 is the window the lead moved earlier from B0029.
- **Orekit's gravity needs the de-duplicated coefficient file.** `tests/e6_gfc_copy.py` derives it into the scratch, under the lead's ruling of 2026-11-12 18:07. Its SHA-256, `bf296183…`, equals DEBRIS-C's copy (`logs\e6_gfc_copy.002.log`).
- **To charge CPU:** `python -I -B tests/cpurun.py <label> studies/debris-e/records/cpu.tsv -- <command>`.

## 4. The gates

### E1: native against cft, kernel by kernel (PASS; `e1_gate.002.log`; build 1's `e1_gate.001.log` gave the same verdicts)

**What varies between lanes.** Each lane is an independent draw from splitmix64, seed 0xE1:
- positions with directions uniform on the sphere, at radii set per kernel (gravity 6,600 to 8,000 km; the central term to 43,000 km; drag 100 to 1,100 km up, so bands 9 to 27);
- velocities, 7.0 to 8.0 km/s in a uniform direction;
- the Sun 1.47e11 to 1.52e11 m away and the Moon 3.56e8 to 4.07e8 m;
- epochs uniform over DE421's coverage, in multiples of 1/1024 s;
- rotation times over ten days;
- bc 0.002 to 0.05 m²/kg and cram 0.005 to 0.05 m²/kg.

**C1: constants and derived tables at degree 180.** Native64 equals cft64, and native32 equals cft32, on all 166,103 entries. Every C-library conversion (`strtod`, `strtof`) therefore gave libcft's correctly rounded bits for every constant and coefficient. Two hand values hold: π at binary64 is `0x400921fb54442d18`, and Dg[1] = √3 is `0x3ffbb67ae8584caa`.

**C2: the exact kernels,** bit for bit on every lane and output at both widths:
- gravity at degree 2 and at degree 20 (10,000 lanes each), and at degree 180 (64 lanes);
- the central term;
- the third body;
- the Chebyshev reader, with its body sums (15 outputs a lane);
- the shadow geometry.

**C3: the transcendental kernels.** With the C library, the differences are those in §1. In the control configuration, where the native kinds route `exp`, `sin`, `cos`, `asin` and `acos` to libcft, all three kernels are bit-identical at both widths. The control is a run-time switch, `--cr`, in the same binary, rather than a separate build. The switch can show a difference only where the C library and libcft differ on the lanes tried: in the rotation and radiation kernels at binary64. For `exp`, and for every kernel at binary32, the two gave the same bits, so there the control could not fail (verifier-E; added at the merge).

**C4: no NaN** in any kernel's output.

**C5: the hand check.** At degree 2, against an independent gradient of the closed-form degree-2 potential in exact rationals from the same decimal coefficients:
- native64 and cft64: at most 1.38e-15 |a|, against 1e-13;
- native32 and cft32: 7.65e-7 |a|, against 1e-5.

**C6: the negative control.** The negctl build divides cos C = (r·d/|r|)/|d| instead of r·d/(|r||d|), in the native kinds only.
- It broke bit-identity in the shadow geometry, in column 3 (cos C) only: 3,264 lanes at binary64 and 3,246 at binary32. The gate named the kernel, the column, the first lane and the count.
- Gravity at degree 20, the central term, the third body, the reader, drag and the rotation stayed identical.

**The finding on `fma`** (`e1_fma.001.log` on build 1, `e1_fma.002.log` on build 3, with the same results; not a gate):
- The cases are the lead's generator's 20,000. Its source in the ledger was compiled in my scratch, and its cases, and each build's `fma()` results, equal those of `tests/fmacheck.c`.
- **The reference:** libcft's `CFT_FMA` is correctly rounded on all 20,000, against exact rational arithmetic.
- **My control:** the unfused a·b + c was reported wrong on 5,094 of them, so the exact checker can fail.
- **The finding:**
  - the C library's `fma`, in a build without `-mfma`, is not correctly rounded on 6,559 of 20,000, and differs from `CFT_FMA` on the same 6,559;
  - the instruction is wrong on 0 of 20,000.

### E2: native against cft, whole runs (PASS; `e2_gate.003.log`)

**The run:** 8 lanes of near-circular LEO orbits, 350 to 700 km up, with inclinations of 0.1° to 98.6° and periods of 5,492 to 5,926 s. Every force is on, at degree 20. rk4 takes 100 steps of 60 s, 6,000 s in all, with the epoch at 2008-07-03 00:00 TDB.

**G1, the gate:** in the control configuration, native64 equals cft64, and native32 equals cft32, at all 101 steps × 8 lanes × 6 components.

**M1, the measurement:** with the C library's transcendentals, no difference appeared at any step, at either width. So the run gives no growth to report.

**The control.**
- **As first specified it FAILED** (`e2_gate.001.log`). The ulp planted in lane 3's x was gone after the first step, at both widths. In that step x grows from 9.04e5 m past 2^20 m, the result's ulp doubles, and rounding absorbed the half-ulp. The accelerations did not move.
- **Its replacement C1b,** stated before its data in version 2, plants the ulp in lane 3's z, which stays inside its binade. It broke bit-identity in lane 3 alone, from the start and at every step, at both widths. Lane 3's |dr| reached 2.7e-8 m (binary64) and 13.7 m (binary32) by step 100.
- The x plant is still re-run, and reported as failing.

### E3: the precision ladder (PASS; `e3_gate.002.log`)

**The arcs at the wide formats,** as the brief asks: every cft128 and cft256 trajectory this round is E2's arc, 6,000 s in 100 steps of 60 s on 8 lanes. That covers E3's runs and its control, and E8's runs, whose R4 cuts the same arc into five segments.

**The bound, stated before the data:** B = N_ops × u₁₂₈ × R × G = 3.046e6 × 2⁻¹¹³ × 7.1e6 m × 30 = 6.25e-20 m.
- N_ops is the run's own count of lane-operations a lane, within 10% of the planned 3.05e6, and the same at cft64, cft128 and cft256.
- G = 30 is linearised Kepler growth over one orbit.
- This is an ESTIMATE-based bound, believed generous; it is not rigorous.

**Results:**
- **L2:** cft128 is at most 7.59e-26 m from cft256 over every lane and boundary, 1.2e-6 of B.
- **L3, the control:** cft128 with the central term's factor −GM/r³ rounded to binary64 at every evaluation reached 3.92e-10 m, 6.3e9 B.

**Each kind against cft256** (max over the 8 lanes, MEASURED):

| t (s) | cft128 \|dr\| | cft64 \|dr\| | cft32 \|dr\| |
|---|---|---|---|
| 0 | 3.6e-28 m | 3.7e-10 m | 0.21 m |
| 1,200 | 2.8e-27 m | 3.1e-7 m | 1.36 m |
| 2,400 | 1.2e-26 m | 1.5e-6 m | 4.45 m |
| 3,600 | 3.2e-26 m | 3.1e-6 m | 10.4 m |
| 4,800 | 6.0e-26 m | 3.8e-6 m | 12.5 m |
| 6,000 | 7.6e-26 m | 3.6e-6 m | 21.8 m |

At t = 0 the differences are the decimal starting states' rounding into each format.

**Binary64 against binary128** (cft64 against cft128, the same run), max over 8 lanes: 3.7e-10 m at t = 0, 3.1e-7 m at 1,200 s, 1.5e-6 m at 2,400 s, and 3.6e-6 m at 6,000 s.
- This is not DEBRIS-D's figure, and the definitions differ. DEBRIS-D's 1.2e-6 to 1.3e-5 m is |fp64 − long double| for one object's final position after one object-day, with the two runs starting from the same binary64 values, at degree 20 with drag only.
- Ours is 8 lanes over one orbit with every force on, and includes the rounding of the decimal inputs.
- **One lane carries ours** (MEASURED, `e3_lanes.001.log`).
  - Lane 1 starts at 350 km, exactly on a band edge of the 28-band atmosphere. It reaches 1.3e-8 m at the first step and 3.6e-6 m at 6,000 s.
  - The other seven stay between 2.0e-8 and 1.0e-7 m at 6,000 s.
  - That lane 1's jump comes from the table's density step at its edge (§6) is BELIEVED.

### E4: Lasser et al. (PASS; `e4_gate.001.log`, on build 2)

The tolerance is 1e-11 m/s² on the largest vector difference over the epochs, DEBRIS-C's.

**Gravity, degrees 2 to 180, Earth-fixed:**
- native64 and cft64, all 2,880 epochs: 2.281e-15 m/s². DEBRIS-C's binary64 kernel gave 2.278e-15; our derived tables round differently. Native64 equals cft64 bit for bit at every epoch, for gravity and for the tides alike;
- cft128 and cft256, every tenth epoch: 1.488e-15 m/s². That what is left is the benchmark's own rounding is BELIEVED.

**The tides, with DEBRIS-C's TT and TDB convention:**
- the Sun: 1.26e-17 (binary64) and 1.05e-17 m/s² (the wide kinds);
- the Moon: 4.34e-16 and 3.91e-16 m/s².

**cft32, reported only:** gravity 6.7e-8 m/s², the Sun 2.1e-9 and the Moon 1.4e-11 m/s².

**The control:** the field truncated at degree 173 was reported at 9.77e-10 m/s² (native64, 97.7 times the tolerance) and 8.88e-10 m/s² (cft64, every tenth epoch, 88.8 times).

**Cost:** E4 used 477.8 CPU-s by cycles, against its approval of 15 CPU-minutes.

### E5: JPL's `testpo.421` (PASS; `e5_gate.002.log`)

**The points:** 109 positions, coordinates 1 to 3, in all 20 ordered pairs of the Earth, the Moon, the Sun, the SSB and the EMB, inside the binary's coverage; 3 points fall outside it.

**Results, against a tolerance of 1e-13 AU:**
- cft64: 4.89e-16 AU at most;
- cft128 and cft256: 4.16e-16 AU, testpo's 17 printed digits;
- native64 (reported): 4.89e-16 AU.

**The control.**
- **As first specified it FAILED** (`e5_gate.001.log`). The first point involving the Moon tests z, and the plant was in x, so no point moved.
- **Its replacement P2b** plants in the coordinate that point tests. Exactly that point (line 25, record 12) was reported, at 6.60e-12 AU.

### E6: Orekit, force by force (PASS; `e6_gate.003.log`)

**The states:** 1,000 LEO states, seed 0xE6:
- 300 to 800 km up, epochs over 20 days;
- area, mass, Cd and Cr drawn at random.

**Every input matched,** each listed in the Orekit script's header in the log:
- **The frame:** Orekit's body frame is a TransformProvider turning uniformly at our ω and θ₀, on TDB seconds since T₀ = 2008-07-03 00:00 TDB.
- **The dates:** each is built in TDB from components.
- **The Sun:** Orekit's own reader of the same DE421 file. It agrees with ours to 7.7e-5 m (5.1e-16 AU).
- **Gravity:** the same coefficients (the de-duplicated copy), degree and order 20.
- **Drag:** `SimpleExponentialAtmosphere` on a sphere (flattening 0) of radius 6,378,136.3 m, against our one band (3.725e-12 kg/m³ at 400 km, H 58,515 m). Each state's A, m and Cd go to `IsotropicDrag`.
- **Radiation:** `ConicallyShadowedLightFluxModel(kRef = P_SUN·AU², R_SUN, Sun, R_EARTH)` with `IsotropicRadiationSingleCoefficient(A, Cr)`.

**Results, the same at cft64 and native64:**

| | worst difference | tolerance |
|---|---|---|
| D1 gravity | 7.35e-17 m/s² | 1e-14 |
| D2 drag | 6.8e-14 relative | 1e-9 |
| D3 radiation, sunlit (673 states) | 1.33e-15 relative | 1e-9 |
| D3 radiation, umbra (324 states) | exactly 0 | 1e-20 m/s² |

**The penumbra,** reported only: 3 states, where our ν and Orekit's lighting ratio differ by 3e-11 to 8e-11 and the accelerations by 8e-19 to 5e-18 m/s². No state was classified differently by the two models.

**D4, the three plants:** Cd, Cr and C̄20, each 1% off on our side, broke their tolerances at 1,000, 673 and 1,000 states.

**The first run's gravity failure** (`e6_gate.001.log`, up to 7.5e-11 m/s², growing with the epoch) was a defect in my matching. Orekit's frame turned on TAI seconds (`durationFrom`), while ours turns on TDB seconds. Over 20 days the two drift apart by up to 5.7e-4 s, which is 4.2e-8 rad. Version 2 of `e6_orekit.js` turns on TDB seconds; the criteria are unchanged. Both script versions are kept.

**As figures only:**
- native64 equals cft64 bit for bit at 998 of the 1,000 states. That the other 2 differ through the C library's transcendentals is BELIEVED; native64 ran with them here.
- NRLMSISE00 (F10.7 150, Ap 15) over the one-band exponential density, at the 1,000 states: 0.45 to 6.8, median 1.06.

### E7: REBOUND as an integrator referee (PASS, with a limit; `e7_rebound.003.log`, and the diagnosis in `e7_diag.003.log`, versions 1 and 2 in logs 001 and 002)

**The run:** one object-day from E2's lane 0, with every force on, at native64 with the C library's transcendentals. IAS15 (REBOUND 5.1.1, ε = 1e-9, gravity "none", `force_is_velocity_dependent` = 1) took 560 steps and 16,464 evaluations.

**The gate:**
- **I1:** our rk4 at 5 s, a step chosen beforehand, is 0.114 m from IAS15. The tolerance is 0.5 m. Its basis is DEBRIS-D's 0.148 m at 7.5 s, scaled by h⁴ to 0.029 m, with a margin of 17 for the forces DEBRIS-D lacked.
- **C1:** J2 planted 1e-3 off in IAS15 alone gave 1,110 m.

**The limit,** from the diagnosis (`e7_diag.003.log`, MEASURED):
- **rk4 converges** on the full model: 5 s against 2.5 s is 2.1e-2 m, 2.5 s against 1.25 s is 2.5e-3 m, and 1.25 s against 0.625 s is 4.0e-6 m. The last drop is far more than h⁴'s factor of 16. Against the smooth model's 8.1e-5 m below, it looks like errors cancelling by chance (BELIEVED).
- **IAS15 moves:** ε 1e-9 against 1e-10 is 0.206 m, and every rk4 run sits 0.09 to 0.12 m from either IAS15 run.
- **The cause, taking the model apart:**

  | the model | IAS15, ε 1e-9 against 1e-10 |
  |---|---|
  | radiation pressure off | 3.8e-5 m |
  | one band of atmosphere | 0.206 m, unchanged |
  | both smooth | 1.1e-6 m |

  So IAS15's movement comes with radiation pressure, and the band edges cost it about 4e-5 m. That the conical shadow's edges are what it does not resolve is inferred, not isolated: no run took the shadow off and left radiation pressure on (narrowed at the merge).
- **What is left, on the smooth model** (version 3 of the diagnosis):
  - rk4 converges at about h⁴: 1.25 s against 0.625 s is 8.1e-5 m.
  - rk4 at 0.625 s is still 2.3e-5 m from IAS15 at ε 1e-9.
  - That is more than rk4's own error at 0.625 s, about 5e-6 m (COMPUTED by the h⁴ law: 8.1e-5 / 15), and more than IAS15's movement with ε (1.1e-6 m). So about 2e-5 m is not explained. It is not settled.
- **What it means for E7:** it passed against a referee that, on this model, is good to about 0.1 to 0.2 m, not to DEBRIS-D's 4e-7 m.

### E8: reproducibility (PASS; `e8_gate.002.log`)

- **R1:** each of the eight configurations reproduces bit for bit across two runs. They are native64 and native32, each in both transcendental configurations, and cft32, cft64, cft128 and cft256.
- **R2:** `-O0` equals `-O2` in all eight.
- **R3, the control:** the contracted build differs from O2 at native64 in 647 of 808 lane-steps, and at native32 in 706, with all 8 lanes differing at the final step.
- **R4:** five segments of 20 steps, each restarted from the previous boundary's hex state, equal the continuous run at every step, at native64, cft64 and cft128.

## 5. Native against cft: the findings in ulps

- **Exact kernels,** at binary64 and binary32: 0 ulps everywhere. That covers 166,103 constants and table entries, 7 kernels on 10,000 lanes (64 at degree 180), 808 lane-steps of the whole model, and 2,880 Lasser epochs.
- **The C library's transcendentals, at binary64:**
  - `sin` and `cos`, through the rotation kernel: 5 of 10,000 lanes differ, by 1 ulp (x, 4 lanes) and up to 2 ulps (y, 3 lanes), in the kernel's outputs on seed 0xE1. On verifier-E's seed the x output differed by up to 32 ulps, in 2 of 5,000 lanes (narrowed at the merge);
  - `asin` and `acos`, through radiation pressure: 12 of 10,000 lanes, all in penumbra, with every output of the kernel differing by up to 1.2e10 ulps (ν by 4.5e-13 to 1.4e-6 relative). The functions themselves are within 0.84 ulps (verifier-E; narrowed at the merge);
  - `exp`, through drag: 0 of 10,000.
- **The same at binary32:** 0 of 10,000 in each kernel.
- **Whole runs with the C library:** 0 differing steps (E2); in E6, 2 of 1,000 states.
- **The C library's `fma`,** in a build without `-mfma`: 6,559 of 20,000 hard cases not correctly rounded, against 0 for `vfmadd` and for `CFT_FMA`.

## 6. Findings beyond the gates

1. **The 28-band atmosphere steps in density at its band edges** (COMPUTED from DEBRIS-B's table, `e3_lanes.001.log`).
   - The steps are small: between 7e-7 and 1e-4 relative at every edge, but 1.4e-3 at 25 km. At 350 km the band below gives 9.51793e-12 kg/m³ against the band's own 9.518e-12, +7.7e-6.
   - Even so, a rounding-level change in h at an edge becomes a change in force. E3's lane 1 starts at 350 km, exactly on an edge, and carries the largest binary64-against-binary128 difference. It jumps to 1.3e-8 m in the first step and reaches 3.6e-6 m in one orbit; the other lanes stay at 2.0e-8 to 1.0e-7 m (MEASURED).
   - The jump's size fits that step, acting in the first stage: 7.7e-6 × lane 1's drag of about 2.9e-6 m/s² = 2.2e-11 m/s², times about 600 s² ≈ 1.3e-8 m (COMPUTED, rough). So the attribution is BELIEVED; no run isolated it.
   - Lanes 0 and 2 also start on edges (400 and 500 km) and did not jump, presumably because both formats put them on the same side.
   - The table also costs IAS15 about 4e-5 m an object-day (E7's diagnosis).
2. **IAS15 at ε 1e-9 is not converged on this model:** 0.21 m between ε 1e-9 and 1e-10, and 3.8e-5 m with radiation pressure off (MEASURED, E7). That the conical shadow is the cause is inferred, not isolated (narrowed at the merge). For this model, rk4 at 1.25 s or less is the better reference.
3. **The penumbra amplifies last-bit differences** (MEASURED, `e1_penumbra.001.log`).
   - Every one of E1's 12 lanes that differ under the C library's `asin` and `acos` is a penumbra lane, out of 49 penumbra lanes in 10,000.
   - In those lanes ν moves by up to 1.4e-6 relative, from inputs that differ in their last bits.
   - Why is BELIEVED: near ca, cb → ±1, acos turns an input ulp into a large relative change in the overlap's area, and x = (C² + A² − B²)/(2C) cancels.
   - A better-conditioned formulation is a later round's question.
4. **The C library's `fma` on this host** (E1, above) agrees with plan-verifier-E's and the lead's findings, on the same 20,000 cases as the lead's.

## 7. Limits

- **The frame is a uniform rotation** (decision 6). It has no precession, nutation, polar motion or UT1, so absolute positions are a model's, not the real Earth's.
- **The atmosphere is exponential** (decision 5), with the density steps above. NRLMSISE00 and JB2008 are referees only.
- **The ephemeris reader serves positions only;** E5 tests no velocities, and no librations or nutations.
- **The bit-identity claims hold on the inputs tried:** E1's random lanes (seed 0xE1), E2's eight lanes, E4's 2,880 epochs and E6's 1,000 states, on this host's CPU and C library. They are evidence, not a proof for all inputs. The C library's results in particular are the library's own, and may differ on another host.
- **E3's bound is an ESTIMATE-based bound,** not a rigorous error bound.
- **E7's referee is limited** to about 0.1 to 0.2 m on this model (§4).
- **E4 ran on build 2,** not the final build 3. That only the driver changed between them rests on file times, not hashes: builds 1 and 2 recorded no source hashes, and every `src\` file's modification time precedes build 2. The driver, `tests\m1run.c`, holds E4's own modes and changed after E4, and `tests\m1x.c`, E7's DLL, changed too (§3). verifier-E re-ran E4 on build 3 at every 30th epoch (96 epochs), at native64 and cft64: gravity within 1.15e-15, the Sun 8.6e-18 and the Moon 3.2e-16 m/s², native64 equal to cft64 bit for bit, and the degree-173 control at 52.9 times the tolerance (narrowed at the merge).
- **The native kinds need an x86-64 with FMA3.** The cft kinds are portable C over libcft.
- **No certificate is written.** The runs are designed for one: segment restarts reproduce the continuous run bit for bit, at native64, cft64 and cft128, the kinds E8's R4 ran (narrowed at the merge).

## 8. Cost (E9)

**The run** (MEASURED, `e9_time.001.log`) took place in the lead's `sensitive` window B0030, from 06:50:00 to 06:52:09 -0700, with nothing else of mine running. It used 101 CPU-s by cycles.
- **The load:** Windows CPU % over 0.5 s before and after each measurement, 5 to 35%, given per row in the log. With 12 logical processors, one busy thread is about 8%.
- **Each cell below** is the wall time of one lane's force evaluation (the whole model at degree 20, with the Sun, the Moon and the frame once a batch), then the wall time of one lane's object-day: rk4 at 15 s, 5,760 steps and 23,040 evaluations. The object-day is COMPUTED from the measured time of a step.
- **"C library"** means the C library's `exp`, `sin`, `cos`, `asin` and `acos`; **"libcft"** means libcft's correctly rounded host functions instead.
- **Each cell is a single run.** The cft256 cell at 64 lanes rests on 4 evaluations, and its object-day on 2 rk4 steps (`e9_time.001.log`; narrowed at the merge).

| kind | 1 lane | 8 lanes | 64 lanes |
|---|---|---|---|
| native32, C library | 5.3 µs; 0.14 s | 2.8 µs; 0.065 s | 2.2 µs; 0.054 s |
| native32, libcft's | 650 µs; 17.9 s | 395 µs; 10.6 s | 356 µs; 10.1 s |
| native64, C library | 5.5 µs; 0.135 s | 2.3 µs; 0.067 s | 2.0 µs; 0.050 s |
| native64, libcft's | 1,169 µs; 35.0 s | 739 µs; 18.2 s | 677 µs; 19.0 s |
| cft32 | 2,339 µs; 60.1 s | 1,957 µs; 48.1 s | 1,618 µs; 41.0 s |
| cft64 | 3,287 µs; 97.0 s | 2,342 µs; 56.0 s | 2,240 µs; 55.1 s |
| cft128 | 5,173 µs; 141 s | 4,410 µs; 106 s | 3,975 µs; 87.6 s |
| cft256 | 13,491 µs; 340 s | 9,585 µs; 222 s | 9,456 µs; 223 s |

**Beside DEBRIS-D's Q3 prices,** MEASURED then (`studies\debris-d\logs\q3_host.001.log`), at binary64, binary128 and binary256:

| operation | binary64 | binary128 | binary256 |
|---|---|---|---|
| add | 251 ns | 249 ns | 361 ns |
| multiply | 153 ns | 179 ns | 244 ns |
| FMA | 195 ns | 235 ns | 313 ns |
| divide | 3.6 µs | 5.6 µs | 9.2 µs |
| square root | 4.4 µs | 6.4 µs | 11.0 µs |
| `exp` | 0.14 ms | 0.33 ms | 1.12 ms |
| `sin` | 0.23 ms | 0.55 ms | 1.89 ms |
| `cos` | 0.22 ms | 0.63 ms | 1.93 ms |

**What the figures say:**
- **The ESTIMATE in the log.** About 7,600 lane-operations an evaluation (the run's own count) times DEBRIS-D's FMA price gives 1.5, 1.8 and 2.4 ms a lane-evaluation at binary64, binary128 and binary256. The measured costs are 2.2 to 3.3, 4.0 to 5.2 and 9.5 to 13.5 ms.
- **At binary64, most of the rest is the six correctly rounded transcendentals each lane needs:** drag's `exp`, and radiation pressure's two `asin` and three `acos`. Measured directly, routing them to libcft turns native64's 2.0 to 5.5 µs into 0.68 to 1.17 ms (MEASURED). That is 30 to 35% of a cft64 evaluation, and 65 to 91% of its excess over the ESTIMATE (COMPUTED from the table above: at 64 lanes, 0.675 of 2.24 ms, and of the 0.74 ms excess). At binary128 and binary256 the split was not measured (narrowed at the merge). That is about 0.11 to 0.15 ms a call (COMPUTED: six calls a lane, plus `sin` and `cos` once a batch), of the order of DEBRIS-D's `exp`, `sin` and `cos` prices.
- **A slip in the log:** `e9_time.py`'s criteria text says DEBRIS-D did not time add and multiply. It did, as the table above shows (MEASURED then), and the log cannot be corrected.
- **What one core carries in real time** at degree 20 with rk4 at 15 s, 64 lanes (COMPUTED as 86,400 s over the time an object-day takes): about 1.7 million objects at native64 with the C library, 4,500 at native64 with libcft's transcendentals, 1,570 at cft64, 990 at cft128 and 390 at cft256. These are on this host, under the load stated, before any change to the model (for instance a cheaper shadow formulation).
- **Batching** lowers the cost a lane by 1.7 to 2.8 times from 1 lane to 64 in the native kinds, and by 1.3 to 1.5 times in the cft kinds, as the per-call overhead spreads.

## 9. Records and budget

- **`studies\debris-e\`** holds:
  - `logs\`: every gate log, numbered and never overwritten;
  - `scripts\`: every version of every script that wrote a log, named by the first 12 hex digits of its hash;
  - `records\`: the libcft build log and `cpu.tsv`;
  - `MANIFEST.sha256` over all of them: 60 files, every one checking OK when run from `studies\debris-e\`.
- **This report is not in the manifest,** and neither are `src\` and `tests\`. `build.003.log` lists the SHA-256 of every C source and header that build compiled.
- **CPU, counted by cycles at 2.5e9 a second** (the rate is BELIEVED):
  - 38 charged runs took 1,896 s, which is 31.6 CPU-minutes (MEASURED; `GetProcessTimes` gives 9.5 minutes for the same runs). They are listed in `records\cpu.tsv`, apart from my two trial builds and seven probes, which are in my scratch's `work\cpu_try.tsv` and inside the total.
  - Within it, E4 took 477.8 s, against its approval of 15 minutes, and E9 101 s, against 10 minutes.
  - Not charged: smoke runs, a 300-lane dry run of E1, the Orekit and REBOUND API probes and two short readings. They add about 1 CPU-minute (ESTIMATE, range 0.5 to 1.5, from their sizes against the charged runs).
- **Wall time:** from 05:42 to about 07:05 -0700.
- **Earlier records,** checked before the report: 32 OK, 29 files, 54, 136 and 73 OK, and no `__pycache__`.

## 10. What was not done, and what the brief got wrong

**Not done:**
- velocities in E5;
- a rigorous E3 bound;
- an explanation of the about 2e-5 m between rk4 at 0.625 s and IAS15 on the smooth model (E7's diagnosis);
- a re-run of E4 on the final build;
- naming `m1x.dll`'s hash in `e7_diag`'s logs. They ran on build 2's DLL (log 001) and build 3's (logs 002 and 003), whose hashes are in `build.002.log` and `build.003.log`;
- E1's "control build" as a separate binary: it is a run-time switch;
- any accuracy tweak, by design.

**What the brief got wrong:**
1. E2's control, "one ulp planted in one lane's starting state must break bit-identity in that lane alone, from the first step", is not guaranteed: rounding can absorb a one-ulp plant within a step (E2 log 001).
2. E7's premise that IAS15 at ε 1e-9 referees rk4 to DEBRIS-D's 4e-7 m does not hold on this model (0.21 m between ε 1e-9 and 1e-10). That the conical shadow is the cause is inferred, not isolated (narrowed at the merge).
3. E1's C-library differences are rare here (5 and 12 lanes in 10,000 at binary64, none at binary32), so "how the difference grows" in E2 has nothing to measure on its eight lanes.

## Narrowed at the merge, from verifier-E's report

verifier-E's report (`studies\DEBRIS-E-verifier-E-report.md`) found every re-run passing and no defect that sends work back. It re-ran, at the sizes it states:
- the build from clean, with the same `libcft.a`, `vfmadd` in every native object, and no call to `fma` or `fmaf`;
- E1 on a new seed, 0x5EED77, with 5,000 lanes and degree-180 batches of 64;
- E2 and E3 in full;
- E4 on build 3 at every 30th epoch, at native64 and cft64;
- E5, E6, E7 and E8;
- E9's figures, recomputed from the log without re-timing;
- the records, with the manifest at 60 OK.

The lead checked the narrowings against the scripts and logs before ruling (READ):
- `tests\e1_gate.py` counts ulps between the kernels' output columns;
- `e8_gate.002.log` states R4 at native64, cft64 and cft128 alone;
- `tests\e7_diag.py` takes off radiation pressure, the bands, or both, and never the shadow alone;
- `e9_time.001.log` gives the cft256 cell at 64 lanes 4 evaluations.

There was no send-back. No figure is false, and each narrowing states what the evidence does not cover.

**Narrowed**, each marked in the text:
1. **The ulp figures (§1 and §5):** they are differences in the kernels' outputs, not the functions' own errors.
   - The C library's `asin`, `acos`, `sin` and `cos` are not correctly rounded on verifier-E's 20,000 arguments, at 0.79 to 1.60 ulps at worst.
   - The rotation's "1 to 2 ulps in 5 of 10,000 lanes" is seed 0xE1's. verifier-E's seed gave up to 32 ulps in 2 of 5,000.
2. **E4 on build 2 (§7):** "only the driver changed" rests on file times, since builds 1 and 2 recorded no source hashes, and the driver holds E4's own modes. verifier-E's re-run on build 3, at every 30th epoch, passed.
3. **The IAS15 finding (§1, §4's E7, §6 and §10):** IAS15's 0.21 m comes with radiation pressure. That the conical shadow's edges are the cause is inferred, not isolated.
4. **E8's restarted segments (§1, §2 and §7):** R4 ran at native64, cft64 and cft128 only.
5. **E9 (§1 and §8):**
   - at binary64 the six transcendentals are 30 to 35% of a cft64 evaluation, not most of it;
   - at binary128 and binary256 their share was not measured;
   - each cell is a single run, and the cft256 cell at 64 lanes rests on 4 evaluations.
6. **Added (§4's E1, C3):** the `--cr` control could not fail for `exp`, nor for any kernel at binary32, where the C library and libcft gave the same bits.

**DEBRIS-E's own report** (`studies\DEBRIS-E-report.md`) is filed verbatim and stays as written. Its sentences on the same points, at its lines 15, 21, 28, 29, 39, 44, 50 and 57, are narrowed by this section.

**Notes** from verifier-E, not narrowed:
- **E2's control:** the replacement z plant was chosen after the x plant failed.
  - Its criterion is in the script's version 2, `2e5400caad14`.
  - File times cannot show that the criterion was written before log 002's data.
  - The x plant's failure stays reported.
- **E3's bound** has about 1e6 of headroom.
  - L2 was 7.59e-26 m against B = 6.25e-20 m, so an error in cft128 of up to about 6e-20 m would pass the gate.
  - verifier-E's report gives the range the gate would miss as 6e-20 m to 4e-10 m. That inverts it: the gate fails anything above B (`tests\e3_gate.py`, L2), as it failed the control's 3.9e-10 m.
- **IAS15 as a referee "good to about 0.1 to 0.2 m"** (§4's E7, §7, and DEBRIS-E's report, line 7) is not narrowed.
  - It rests on measurements, not on the inferred cause.
  - IAS15 moved 0.21 m between ε 1e-9 and 1e-10.
  - Every rk4 run, from 5 s to 0.625 s, sat 0.09 to 0.12 m from either IAS15 run, while successive rk4 runs agreed within 2.1e-2 m.
- **What verifier-E did not do:** re-time E9; re-run E1's C5 hand check; run E3 on other lanes; or run E4 at cft128 and cft256. It ran E4 at every 30th epoch.
- **E9's PASS lines** mean only that a run completed.
- **`m1x.dll`** lives only in DEBRIS-E's scratch, `cft-debris-scratch\DEBRIS-E\build\main`, outside the repository.
- **Beyond the gates:** gravity and the central term stayed bit-identical over 3,000 lanes at each width, with radii from 0.1 m to 1e13 m, including 1,345 binary32 lanes with NaN or overflow. This was run on verifier-E's copy of `m1run.c`, in its scratch.
- **The brief's errors,** as verifier-E reports them:
  - item 6 asked for source hashes that builds 1 and 2 never recorded;
  - item 2's "would fail" holds only for the binary64 rotation and radiation kernels.
- **verifier-E's report** runs to 1,475 words in its body, past its 1,200. It gives its wall time as about 40 minutes, where the harness gives 878 s.

**merge-check-E** (Haiku) checked this narrowing against verifier-E's report, DEBRIS-E's report and the text as reported. It confirmed the hashes, the seventeen marks and every figure. Its points were then fixed, and the fixes were not checked again:
- a mechanism stated as fact, now labelled BELIEVED;
- `tests\m1x.c`, added to what changed between builds;
- an unclear antecedent in §1's E9 row;
- the inverted E3 range;
- verifier-E's "not done" list;
- DEBRIS-E's report's line 21.
