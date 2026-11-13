# DEBRIS-C: the measurements that would decide build, adopt or hybrid

Study parcel DEBRIS-C for cft-debris, 2026-11-12, under the plan of record `studies\DEBRIS-C-plan.md` (draft 3 as corrected in Phase 0, SHA-256 `807e66c6c2218e063f3b766a566d06502812b9c16e71694353f1ea69b4987538`). A study only: nothing was built and no repository changed. Scripts, logs and records are in `studies\debris-c\`; its `MANIFEST.sha256` lists them. `binaries.sha256` hashes the executables and the de-duplicated gravity file, which stay in my scratch; its paths are relative to `cft-debris-scratch\DEBRIS-C\`. Not yet verified: verifier-C checks this study.

> "Im considering how challenging making a custom simulation model might be, considering how specialized of a focus this is and effects REBOUND isnt particularly good at or even supports" (Logan, before DEBRIS-B). After DEBRIS-B he chose "Draft DEBRIS-C".

Labels, as in DEBRIS-B:
- **MEASURED**: I ran it on this host. The command is in "Measurements and their commands", and every log names the SHA-256 of the script that wrote it.
- **COMPUTED**: arithmetic from labelled inputs; the script is named.
- **READ**: I opened the source. "READ (via WebFetch)" is a model's summary of an HTML page, so it supports "consistent with", never "confirmed". "READ (search excerpt)" is a search engine's summary only. Local files are READ directly.
- **BELIEVED**: my judgement, or a figure I did not fetch.

**Host and load.** i5-12400F, 12 threads, Windows 11, Java 1.8.0_411 (HotSpot 25.411-b09), gcc 16.1.0 (x86_64-w64-mingw32). Other sessions held the desktop `shared` through these hours: cft-fp256's WSL replay and cft-REBOUND's `make check`. The load during my runs was 8 to 100% (GetSystemTimes, all 12 logical CPUs), and it is stated beside each timing. Every timing run first passed the TimeSheet's `check desktop --short` (FREE), and its output is in the log.

## Short answer

1. **M0, the gate: Orekit runs here without orekit-data, after one input was normalised** (MEASURED).
   - The first run failed: Orekit's ICGEM reader refuses the benchmark's own `EIGEN6-C4.gfc`, which carries its degree-0 line twice. That left 6 of 9 calls passing, and the propagator step was skipped.
   - The re-run reads a copy with that one line removed and no value changed (the lead's ruling, lead.md 18:07). All 10 calls returned finite values: a script-built UTC (TAI-UTC 33 s), a script-built rotating frame, the Sun from DE421, the ellipsoid, NRLMSISE00, JB2008, the gravity field and one propagator step.
   - No linkage error occurred, so no leg was stopped.
2. **M1, force kernels held to published authorities: gravity and third bodies meet the stated tolerance with both kernels; two of my JPL-test criteria failed** (MEASURED).
   - **Gravity** (EIGEN-6C4, degrees 2 to 180, 2,880 epochs):
     - my normalised C kernel and Orekit's Holmes-Featherstone reproduce Lasser et al.'s accelerations to 2.28e-15 and 2.21e-15 m/s² at most, 4,400 times under the 1e-11 m/s² threshold;
     - the two agree with each other to 3.2e-16;
     - both report the planted truncation at degree 173, at 9.8e-10 m/s² (98 times the tolerance).
   - **Third bodies** on Lasser et al.'s CRF orbit: Sun 1.5e-17, Moon 4.4e-16 and planets 4.7e-22 m/s², from either reader; both planted errors were reported.
   - **JPL's `testpo.421`:** two of my criteria failed as stated.
     - My reader is within 1.4e-14 AU on bodies. It misses my 1e-13 tolerance at 13 libration points, by 1 to 3 ulps of angles up to 4,107 rad; my tolerance's basis overlooked those angles.
     - Orekit's reader is off by up to 6.8e-12 AU (1.0 m) in testpo's coordinates, at 697 of 1,594 points, and by up to 1.3 m in the full position vector. The miss is a time offset of 6 to 15 µs at TDB-dated queries, cause not determined.
     - The planted sub-interval shift fails all 1,801 points, as it must.
3. **M2, the density models' cost is over DEBRIS-B's break-even** (MEASURED: Java driven from Nashorn, binary64, two runs at 11 to 96% load).
   - **Per call:** NRLMSISE00 costs 7.3 to 7.5 µs, 4.0 to 4.1 times DEBRIS-B's 1.85 µs break-even. JB2008 costs 29.9 to 31.6 µs, 16 to 17 times it.
   - **Both controls pass:**
     - every model loop is at least 67 times slower than the trivial call (7.3 to 8.1 ns, a lower bound on Nashorn's overhead);
     - NRLMSISE00's nine densities match a published run of the C code to 2.7e-16 relative.
     - No reference check was run for JB2008 (a limit).
   - **The budget** (COMPUTED): with DEBRIS-B's other terms, the LEO catalogue at degree 20 costs 431 to 441 CPU-hours a year with NRLMSISE00 and 1,493 to 1,573 with JB2008, against 87 with DEBRIS-B's exponential atmosphere.
   - **Gravity:** Orekit's costs 1.5 to 3.5 times DEBRIS-B's C kernel, from degree 70 down to degree 8. That ratio is language and algorithm together.
4. **M3, reproducibility** (MEASURED):
   - **Orekit** reproduced itself to the bit across six runs: the default JIT three times, `-Xint`, C1 only and C2 only. Every one of 358 steps matched, and so did the final state. One ulp in the initial x changes the hash at the first step (9.3e-10 m) and moves the end of the day by 5.6e-6 m.
   - **The custom C kernel's bits depend on fused multiply-adds.** The `-march=native -ffp-contract=fast` build holds 29 FMA instructions in its own code, against none for `-O2`. 2,547 of its 2,880 outputs differ from the `-O2` build's, by at most 5.2e-17 m/s², and each build reproduces itself.
   - **The scope:** one JVM on one machine, so the cross-JVM question stays open.
5. **M4, the hindcast, designed:**
   - **Truth exists** for defunct objects: the EUROLAS Data Center lists laser data for ENVISAT to 2024-08-08 and for TOPEX/Poseidon to 2025-02-20 (READ via WebFetch).
   - **Both ILRS data centres need an account:** CDDIS needs an Earthdata Login for HTTPS, and EDC needs registration and an API key (READ via WebFetch).
   - **The pilot:** one object-month of ENVISAT needs minutes of CPU (COMPUTED). Its real costs are Logan's credentials, about 0.15 MB of normal points (COMPUTED, from BELIEVED record sizes), and modelling the metre-level spin signature in debris ranges.
6. **For build, adopt and hybrid** (BELIEVED). M1 shows that layers 3 and 4 can be verified against authorities, and that Orekit can serve as their oracle at the 1e-11 level. M2 shows that the density model, not gravity, sets a LEO catalogue's cost. M3 weakens the bit-reproducibility differentiator on one JVM, and shows that a C model keeps it across builds only if its floating-point contraction is pinned. The evidence does not decide among the three, and I make no recommendation.

---

## M0. The gate: can Orekit run here without orekit-data?

`m0/m0_gate.js` builds every Orekit object M1 to M3 use and calls each once.
- **Criterion** (in the script, asserted): every call returns finite values.
- **Data registered:** a `DirectoryCrawler` on the DE421 binary's own download directory, and one on the gravity file's own directory, and nowhere else. Each directory is asserted to hold its one file only.
- **No `orekit.data.path`** was set (MEASURED: null).

| call | run 001 (the download) | run 002 (the de-duplicated copy) |
|---|---|---|
| UTC from the script's loader (`addUTCTAIOffsetsLoader`, TAI-UTC 33 s from 2006-01-01) | PASS: UTC-TAI = -33 s; the loader was called once | PASS, the same |
| body frame: a script `TransformProvider`, uniform about GCRF z at 7.292115e-5 rad/s | PASS | PASS |
| `GravityFieldFactory.getNormalizedProvider(180, 180)` | **FAIL**: `OrekitException: duplicated gravity field coefficient ... (0, 0)` | PASS: mu 3.986004415e14, ae 6378136.46, tide-free |
| `HolmesFeatherstoneAttractionModel(body, 180).gradient(...)` | not reached | PASS |
| `getNormalizedProvider(20, 20)` | **FAIL**, the same exception | PASS |
| Sun from DE421 (`CelestialBodyFactory.getSun()`) | PASS: \|r\| = 1.521e11 m | PASS |
| `OneAxisEllipsoid` on the body frame | PASS: altitude 460.8 km | PASS |
| `NRLMSISE00(inputs, Sun, ellipsoid, script UTC)` | PASS: 1.07e-12 kg/m³ | PASS |
| `JB2008(inputs, Sun, ellipsoid, script UTC)` | PASS: 8.03e-13 kg/m³ | PASS |
| `NumericalPropagator` (DP853, degree 20 and NRLMSISE00 drag), 30 s | skipped | PASS |
| **criterion** | **FAIL, 6 of 9** | **PASS, 10 of 10** |

(MEASURED: `logs/m0_gate.001.log` and `.002.log`.)
- **The UTC value** is READ (via WebFetch) from the IERS EOP Centre's TAI-UTC table: "2006 Jan. 1 - 2009 Jan. 1 33s". The search excerpt of Bulletin C 30 is consistent with it.
- **The check:** T0, 2008-07-03 00:00:00 GPS, printed as 23:59:46 UTC on 2 July. That is UTC = GPS - 14 s, as the dataset's README states for that day (READ).
- **Neither stop rule fitted run 001.** It was not a linkage error, and no data file was asked for. I escalated (ledger, 18:06:19), and the lead ruled the same minute (lead.md 18:07).
- **The copy.** `m0/derive_gfc_copy.py` removes line 16 only, the second `gfc 0 0` line: `0.10000000000E+01` against line 15's `1.00000000000E+00`. It asserts three things:
  - the copy is the original minus exactly that line;
  - each of the 16,469 (L, M) keys then appears once;
  - no value changed and no key was lost.
  
  Two planted second changes, a changed digit at (180,180) and the (2,0) line removed as well, each fail that check (MEASURED, `logs/m0_derive_gfc_copy.001.log`).
  - The copy lives in my scratch, `gfc_dedup\EIGEN6-C4.gfc`, SHA-256 `bf296183bf9c9180e58c64a2fca22ece0124d6c7f82448508b8599a944010852`. The download stays untouched (`b5d58320...`).
  - Every Orekit gravity path in M1a, M2 and M3 reads the copy.
  - **The C kernel reads the download.** It accepts a duplicate only if both lines hold equal values (asserted). Its output from the copy is bit-identical to its output from the download (MEASURED, `logs/m1a_run_c.001.log`).
- **What M0 closes:** the smoke test could not catch a call to an API newer than Java 8. Every path that M1 to M3 use has now run on this Java 8 (MEASURED). Paths not run here, such as orbit determination, remain untested.

## M1. Force kernels held to published authorities

### M1a. The gravity field (layer 3)

**Conventions, established before any comparison** and written into `m1a/m1a_compare.py`'s header:

| convention | value | source |
|---|---|---|
| coefficient file | the benchmark's `models/EIGEN6-C4.gfc`, header `EIGEN-6C4_180`, icgem2.0, max degree 180, fully normalised | README "02 gravity field"; the file (READ) |
| GM, reference radius | 0.3986004415E+15 m³/s², 0.6378136460E+07 m, the file's, used by all three | header (READ) |
| tide system | tide-free, used as written by all three | header (READ) |
| degree 0, degree 1 | the benchmark sums degree and order 2 to 180, so the central term is excluded; degree 1 is absent from the file (2 missing terms), so zero | README (READ); m1a_grav's count (MEASURED) |
| time-variable terms | none: every data key is `gfc` (no `gfct`, `trnd`, `acos`, `asin`), so the field is static and evaluates the same on 3 July 2008 | MEASURED |
| Orekit's central term | `gradient()` returns "the gradient of the non-central part", and its sums start at `n = FastMath.max(2, m)`, so it covers 2 to N and nothing is added or subtracted | READ (via WebFetch), `HolmesFeatherstoneAttractionModel.java` at tag 13.1.9 [C4] |
| frame | Lasser et al.'s TRF accelerations at the TRF positions of `00orbit_itrf.txt`; all evaluate Earth-fixed, so no rotation enters | README (READ) |

No convention was found wrong after the data.

**The custom kernel** is `m1a/m1a_grav.c`, derived from a copy of DEBRIS-B's `q2/grav_body.inc`. It is the Cunningham V, W recursion in Earth-fixed Cartesian coordinates, made **fully normalised**: V̄ = N_nm V with N_nm² = (2-δ_m0)(2n+1)(n-m)!/(n+m)!, built by the forward column recursion.
- **What changed from DEBRIS-B's kernel:**
  1. normalised recursion coefficients: the column terms sqrt((2n-1)(2n+1)/((n-m)(n+m))) and sqrt((2n+1)(n+m-1)(n-m-1)/((2n-3)(n+m)(n-m))), the sub-diagonal sqrt(2m+3), and the diagonal sqrt(3), then sqrt((2m+1)/(2m));
  2. in every acceleration term, the ratio of the normalisations it mixes (the factors `F1`, `FA`, `FB`, `FZ` in the source);
  3. the real coefficients, with GM and R from the file;
  4. arrays to degree 181, in metres;
  5. degrees 2 to N only.
  
  DEBRIS-B's loop order is kept.
- **Why:** unnormalised V_mm grows like (2m-1)!!, which overflows binary64 long before degree 180 (BELIEVED, standard).

**Tolerance, stated before the run:** 1e-11 m/s² on the maximum over the day of |Δa|, the Euclidean norm of the vector difference at each epoch. That is the threshold the COST-G packages met for each force (READ via WebFetch, Lasser et al. 2020, through the plan; I did not re-fetch it). Applying it to the norm is stricter than applying it per component.

**Negative control, COMPUTED first** (`m1a/m1a_control_degree.py`, logged before any comparison ran).
- **The model:** a degree's RMS signal over a sphere of radius r is (GM/r²)(R/r)^n sqrt((n+1)(2n+1)) σ_n, with σ_n² = Σ_m (C̄²+S̄²) taken from the file.
- **The choice:** truncation at D = 173 omits an RMS 1.09e-10 m/s² at the orbit's largest radius over the day (6,861.3 km), which is 10.9 times the tolerance. At the mean radius it omits 1.73e-10. Kaula's rule, at the mean radius, gives 1.49e-10 at D = 172 and 1.04e-10 at D = 175 (COMPUTED, same log).

| comparison (2,880 epochs) | max \|Δa\| (m/s²) | RMS | criterion | result |
|---|---|---|---|---|
| custom C, degrees 2-180, against Lasser et al. | 2.278e-15 | 4.37e-16 | < 1e-11 | **PASS** |
| Orekit Holmes-Featherstone, 2-180, against Lasser et al. | 2.210e-15 | 4.29e-16 | < 1e-11 | **PASS** |
| custom C against Orekit (two of ours) | 3.24e-16 | 8.3e-17 | < 1e-11 | PASS |
| control: custom truncated at 173 | 9.772e-10 | 1.80e-10 | reported (> 1e-11) | **PASS**, 98 × tolerance |
| control: Orekit truncated at 173 | 9.772e-10 | 1.80e-10 | reported | **PASS** |

(MEASURED, `logs/m1a_compare.001.log`; the largest |a| over the day is 2.41e-2 m/s².) The measured RMS of the truncation, 1.80e-10, is consistent with the COMPUTED 1.73e-10 at the mean radius.

**Which degrees the comparison tests** (COMPUTED, then MEASURED in `m1a/m1a_domain.py`, written after the comparison and changing none of its criteria):
- **Every whole degree.** Each degree's own RMS signal at the orbit's largest radius exceeds the tolerance. The smallest is degree 180's, at 3.25e-11 m/s² (COMPUTED, `m1a/m1a_degree_min.py`, `logs/m1a_degree_min.001.log`). Removing degree 180 alone is reported at a maximum of 1.79e-10 (MEASURED). So the 1e-11 criterion tests every degree from 2 to 180 as a whole.
- **Not a single high-degree coefficient.** Changing C̄(180,90) by 3.09e-10, Kaula's size at that degree, gives a maximum of 9.56e-12 and an RMS of 2.15e-12 (MEASURED). That is under the tolerance, so the criterion does not report it, although it is 4,200 times the unplanted residual.
- **So:** the pass rests on 1e-11. The measured residual of 2.3e-15 would expose far smaller errors, but nothing asserts that.

**What the agreement proves, and what it does not.** Lasser et al.'s values come from GROOPS, and were published so that other software can be held to them. So the custom kernel and Orekit each meeting them is agreement with an authority. The two agreeing with each other is two of ours agreeing.
- All three read the same coefficients, so nothing here tests the coefficients themselves.
- Mine and Orekit's agree with each other 7 times more closely (3.2e-16) than either agrees with GROOPS (2.2e-15). The cause is not determined: BELIEVED, a different recursion or summation order in GROOPS, at about 1e-13 of |a|.
- The FMA build of M3 differs from the `-O2` build by at most 5.2e-17, so it too is within 2.33e-15 of Lasser et al. (COMPUTED, triangle inequality).

### M1b. The Sun and Moon (layer 4)

**The readers:**
- **My own,** in `m1b/m1b_check.py`, written from the binary layout.
  - `header.421` gives NCOEFF = 1018 and the pointers, and the binary's first record must hold the same pointers (asserted).
  - The binary covers JED 2414992.5 to 2469808.5, in 1,713 records of 32 days, with AU = 149597870.6996262 km and EMRAT = 81.3005690699153 (MEASURED).
  - Each series is summed from its highest coefficient down. Earth = EMB - Moon/(1+EMRAT), and the geocentric Moon is used directly for the pairs (10,3) and (3,10).
- **Orekit's,** driven from `m1b/m1b_orekit.js`: target minus centre in ICRF axes, at dates built with `AbsoluteDate.createJDDate(jd, s, TDB)`. Orekit exposes no nutations or librations, so its 1,594 points are bodies 1 to 13 only.

**Criteria, stated before the run:**
1. My reader within 1e-13 of `testpo.421`, in the file's own units, at every point inside the binary's coverage. The 50 points outside it are skipped and counted.
   - **The basis I stated:** testpo prints 17 significant digits, and one ulp of 50 AU is 7.1e-15 AU, so 1e-13 leaves at least 14 ulps.
   - That JPL's own `testeph` uses 1e-13 is BELIEVED only: its source is a `.f` file, outside the HTML-only rule.
2. Orekit, the same tolerance.
3. A negative control that must fail criterion 1: the Chebyshev series of the next sub-interval, evaluated at the same normalised time.

| check | points | failures | max \|d\| | result |
|---|---|---|---|---|
| 1. custom reader | 1,801 | 13 | positions 1.42e-14 AU, velocities 1.4e-17 AU/day, nutations 1.4e-20 rad, **librations 9.09e-13 rad** | **FAIL** |
| 2. Orekit's reader | 1,594 | 697 | positions **6.77e-12 AU** (1.0 m), velocities 4.6e-13 AU/day | **FAIL** |
| 3. control, shifted by one sub-interval | 1,801 | 1,801 | 0.73 AU | **PASS** (reported) |

(MEASURED, `logs/m1b_check.002.log`.)
- **Run 001 of the same check** gave identical results for criteria 1 and 2, then crashed in the control at the last record, which has no next sub-interval. Version 2 uses the previous sub-interval there; criteria 1 and 2 are unchanged between the versions.

**Why criterion 1 failed** (MEASURED, `logs/m1b_diag.001.log`, written after the data).
- All 13 failures are the libration angle ψ, whose values reach 520 to 4,107 rad at the failing points and 6,666 rad in the file. There one ulp is 1.1e-13 to 9.1e-13 rad, and the misses are 1 to 3 ulps.
- So my stated basis was wrong: it took the largest coordinate to be about 50 AU and overlooked the libration angles.
- The criterion stays failed. I did not loosen it.
- Outside the librations, my reader meets it everywhere.

**Why criterion 2 failed** (MEASURED, `logs/m1b_diag2.001.log`, written after the data).
- Orekit's full position vectors differ from my reader's (which matches testpo to 1.4e-14 AU) by up to 1.29 m.
- Within 1.5%, the difference lies along the relative velocity: it is a time offset of 6e-6 to 1.46e-5 s, of either sign, and it is independent of where the date falls in the Chebyshev sub-interval.
- **The cause is not determined.** BELIEVED: the size matches the 14 µs amplitude of the sin 2g term in the usual TDB-TT series, which suggests that the date conversion and the ephemeris reader use different TDB conventions.
- It does not appear at GPS-dated queries: on Lasser et al.'s day, Orekit's and my reader's third-body accelerations agree to 8e-18 m/s² (below).

**Third-body accelerations on Lasser et al.'s CRF orbit**, as direct tides of point masses (the README's convention): a = GM (d/|d|³ - s/|s|³), with s the geocentric body and d = s - r.
- **GM values:** GROOPS's, from the README.
- **Ephemeris time:** TT = GPS + 51.184 s, and TDB = TT + 0.001657 sin g + 0.000014 sin 2g. Choosing TT instead moves the Moon's term by about 2e-16 m/s² on this day (COMPUTED: TDB-TT = 4.9e-5 s).
- **Tolerances, stated before:**
  - Sun and Moon: 1e-11 m/s².
  - Planets (Mercury, Venus and the Mars, Jupiter and Saturn barycentres, summed): 1e-16. Their whole signal is 5.5e-12, so 1e-11 could not fail.
- **Controls:** each planted error's effect was COMPUTED from my own model first and asserted to be at least 10 times the tolerance.

| comparison | max \|Δa\| (m/s²) | tolerance | result |
|---|---|---|---|
| custom Sun against Lasser et al. (signal 4.0e-7) | 1.50e-17 | 1e-11 | **PASS** |
| custom Moon (signal 1.16e-6) | 4.35e-16 | 1e-11 | **PASS** |
| custom planets (signal 5.5e-12) | 4.68e-22 | 1e-16 | **PASS** |
| Orekit's positions: Sun, Moon, planets | 1.36e-17, 4.36e-16, 4.75e-22 | as above | **PASS** |
| custom against Orekit: Sun, Moon, planets | 7.8e-18, 2.0e-19, 4.3e-22 | as above | PASS |
| control: Moon's time +600 s (expected 4.05e-9, 405 × tolerance) | 4.05e-9 | reported | **PASS** |
| control: Saturn left out (expected 9.5e-14, 948 × tolerance) | 9.5e-14 | reported | **PASS** |

(MEASURED, `logs/m1b_check.002.log`.)

## M2. The density models' cost

**What was timed** (`m2/m2_time.js`):
- Orekit's `getDensity(date, position, frame)` and `HolmesFeatherstoneAttractionModel.gradient(date, position, mu)`, called from Nashorn at binary64.
- **Points:** 64 LEO points, Lasser et al.'s ICRF positions at every 45th epoch (454.9 to 500.5 km), each with its own date; call k uses point k mod 64.
- **Synthetic, constant inputs**, implemented in the script:
  - NRLMSISE00: F10.7 = 150, F10.7A = 150, Ap = 15 in all seven slots;
  - JB2008: F10, F10B, S10, S10B, XM10, XM10B, Y10, Y10B = 150, DSTDTC = 50 K.
- **Two variants:** (A) the ellipsoid on GCRF itself, so the model's own cost; (B) the ellipsoid on M0's script-built body frame, as M3 runs.
- **Each figure:** the minimum (and median) over 7 repetitions of about 0.25 s, after 3 warm-up repetitions.
- **Controls, stated before and asserted:**
  - Control 1: every model loop must be at least 10 times slower per call than a loop whose call is a trivial Java call (`Vector3D.getX()`, folded into the checksum like every output). The trivial call's time is Nashorn's per-call overhead, a lower bound because the JIT may fold it.
  - Control 2, in `m2/m2_reference.js`: NRLMSISE00 against published reference values.

| per call (ns, min / median) | run 002 (load 11-96%) | run 003 (load 12-49%) | × trivial call (run 003) |
|---|---|---|---|
| trivial Java call (overhead, lower bound) | 7.3 / 10.5 | 8.1 / 11.9 | - |
| empty loop | 1.2 / 1.3 | 1.2 / 1.3 | - |
| Holmes-Featherstone gradient, degree 8 | 573 / 609 | 541 / 717 | 67 |
| degree 20 | 2,162 / 2,801 | 1,746 / 1,983 | 216 |
| degree 36 | 5,617 / 6,337 | 4,478 / 4,634 | 555 |
| degree 70 | 16,011 / 17,984 | 14,919 / 17,358 | 1,849 |
| **NRLMSISE00**, A | **7,529** / 7,928 | **7,317** / 9,710 | 907 |
| NRLMSISE00, B (script frame) | 9,537 / 9,905 | 7,668 / 8,400 | 951 |
| **JB2008**, A | **31,623** / 33,740 | **29,914** / 31,419 | 3,708 |
| JB2008, B | 31,869 / 35,042 | 30,785 / 33,736 | 3,816 |

(MEASURED, `logs/m2_time.002.log` and `.003.log`; control 1 PASS in both.)
- **Callbacks.** Each NRLMSISE00 call makes 5 Java-to-script callbacks into the input parameters, and each JB2008 call makes 14. Variant B adds 3 and 2 frame transforms.
  - One callback costs 15.5 to 23.7 ns: a sort of 200,000 Integers with a script comparator, timed against Java's own comparator (MEASURED).
  - So the callbacks and the overhead together are under 0.4 µs of each density figure (COMPUTED). They are not subtracted in the table below.
- **Run 001 is set aside, and reported:** its calibration ran cold, so its density repetitions lasted only 19 to 90 ms. It gave 12.6 µs for NRLMSISE00 and 32.0 µs for JB2008 (`logs/m2_time.001.log`). Version 2 changed only the calibration and dropped a thread-CPU column (see "CPU" below).

**Control 2 (MEASURED, `logs/m2_reference.002.log`): PASS.**
- **The reference:** pynrlmsise00's documented run of the C model, `gtd7(2009, 172, 29000, 400, 60, -70, 16, 150, 150, 4)` (READ via WebFetch [C6]).
- **The check:** Orekit's model core (`NRLMSISE00$Output.gtd7`, reached by reflection as Orekit's own legacy test reaches it [C7]) gives all nine densities within 2.7e-16 relative, against a stated 1e-10. The two temperatures match to every printed digit.
- Run 001 of this control crashed on a Nashorn argument type before checking the second density, and is kept.
- **Limit:** this checks the model core, not the public `getDensity` path that was timed, which adds the geodetic conversion, the Sun and the local solar time.
- **Limit: no JB2008 check.** Orekit's JB2008 legacy reference values were located (12 cases, relative tolerance 2e-5; READ via WebFetch [C8]). Their inputs pass through a test helper (`RAP`, longitude to right ascension) whose formula the summary did not give, and the dates' fractional days came only as approximations. So the JB2008 timing has no fast-wrong-answer control.

**DEBRIS-B's C gravity kernel, timed again in the same hours** (MEASURED, `logs/m2_c_grav.001.log`, load 8-39%): 165, 831, 2,555 and 9,683 ns at degrees 8, 20, 36 and 70. DEBRIS-B had 183, 864, 2,618 and 10,039 ns. Against them, Orekit's gradient is 3.3-3.5 times slower at degree 8, 2.1-2.6 at 20, 1.8-2.2 at 36 and 1.5-1.7 at 70. That ratio is **language and algorithm together**: Holmes-Featherstone with normalised coefficients against unnormalised Cunningham.

**DEBRIS-B's LEO catalogue-year table again** (COMPUTED, `m2/m2_table.py`, `logs/m2_table.001.log`).
- **Definitions are DEBRIS-B's** (the script reproduces its four rows to the ns):
  - the integrator's 233 ns share (BELIEVED split), plus gravity, frame 512, Sun and Moon 129, radiation pressure 35 and exponential air 80 ns;
  - a density model "adds X to each LEO evaluation";
  - IAS15's evaluations per object-day;
  - 28,149 LEO objects;
  - CPU-hours a year = ms per object-day × objects × 365 / 3600.
- **Ranges** are run 003 to run 002.

| degree | DEBRIS-B (C gravity, exponential air): ns / CPU-h a year | + NRLMSISE00 (Java) | + JB2008 (Java) | Orekit gravity + NRLMSISE00 (both Java) |
|---|---|---|---|---|
| 8 | 1,171 / 46 | 8,488-8,700 / 336-344 | 31,085-32,794 / 1,229-1,296 | 8,846-9,090 / 350-359 |
| 20 | 1,852 / 87 | 9,169-9,381 / 431-441 | 31,766-33,475 / 1,493-1,573 | 10,051-10,679 / 472-502 |
| 36 | 3,606 / 184 | 10,923-11,135 / 558-569 | 33,520-35,229 / 1,714-1,801 | 12,782-14,134 / 653-723 |
| 70 | 11,027 / 634 | 18,343-18,556 / 1,055-1,068 | 40,941-42,650 / 2,355-2,454 | 23,224-24,528 / 1,336-1,411 |

- **Which figures are Java:** the density costs in the last three columns, and the gravity in the last. Everything else is DEBRIS-B's C or its BELIEVED integrator split.
- **What it shows:**
  - at degree 20, NRLMSISE00 multiplies DEBRIS-B's budget by 5.0 to 5.1, and JB2008 by 17 to 18;
  - at degree 20 the density model is 80% of an evaluation with NRLMSISE00 and 94% with JB2008; across degrees 8 to 70 the share runs from 40% (NRLMSISE00, degree 70) to 96% (JB2008, degree 8) (COMPUTED).
- **Not measured:** a C implementation of either density model. So whether a build would pay less for density is open.

**CPU, an environment fact** (MEASURED, `logs/m2_cyclecal.001.log` and `logs/m2_cpu_check.002.log`).
- On this host today, GetThreadTimes and GetProcessTimes, which are tick-sampled, charge a fully busy thread about a quarter of its time:
  - a native busy loop ran 2.42e9 to 2.44e9 cycles a wall second (QueryThreadCycleTime) and was charged 0.23 to 0.29 of its wall time;
  - a single-threaded JVM ran 14.35 s and was charged 3.55 s, while QueryProcessCycleTime gave 14.8 s at a 2.5 GHz reference.
- So the wall-clock timings above stand. The thread-CPU column of run 001 was meaningless, and I count CPU by cycles (runner version 2).
- The 2.5 GHz rate is BELIEVED; the native loop's 2.43e9 a second is consistent with it.

## M3. Is Orekit bit-reproducible?

**The run** (`m3/m3_prop.js`): one LEO object for one day, 2008-07-03, from Lasser et al.'s ICRF state at 00:00:00 GPS.
- **Integrator:** Hipparchus `DormandPrince853Integrator`, minimum step 1e-3 s, maximum 300 s, with tolerances from `NumericalPropagator.tolerances(1e-3 m, orbit, CARTESIAN)`: absolute 1e-3 m and 1.1e-6 m/s, relative 1.46e-10. Orbit type Cartesian.
- **Forces:**
  - EIGEN-6C4 to degree and order 20 (the copy), on M0's body frame;
  - the central term from the provider's mu;
  - NRLMSISE00 drag with M2's constant inputs: isotropic, 1 m², Cd 2.2, 100 kg.
- **Records:** at every step end, the offset from the start and the GCRF position and velocity, as raw bits. They go into a per-step file and a running SHA-256, and the final state is printed as hexadecimal doubles.
- **Why the frame needs no EOP, and why that is enough for this question:** the frame is a uniform rotation computed in the script. The question is whether the same inputs give the same bits. EOP would add more input data and more pure-Java interpolation and series code, not a different kind of arithmetic (BELIEVED). So a frame without EOP tests the same mechanism, though not that code.
- **Criterion, before the data** (`m3/m3_compare.py`): every run bit-identical, or the first step at which any differs, with its size.
  - jit1's first log predates the script.
  - All the version-2 runs below were made after it.

| run | JVM options | steps | step hash | final state |
|---|---|---|---|---|
| jit1, jit2, jit3 | default (tiered C1 + C2) | 358 | `b9c1c882bf57593b...` | identical |
| xint | `-Xint` | 358 | `b9c1c882bf57593b...` | identical |
| c1 | `-XX:TieredStopAtLevel=1` | 358 | `b9c1c882bf57593b...` | identical |
| c2 (added: it would catch a difference that only C2's optimisations make) | `-XX:-TieredCompilation` | 358 | `b9c1c882bf57593b...` | identical |
| control: initial x + 1 ulp | default | 358 | `c1700746f6ab571d...` | differs |

(MEASURED, `logs/m3_prop_*.002.log` and `logs/m3_compare.001.log`.)
- **Criterion PASS:** the six runs are bit-identical at every step. The final position is x = -0x1.5a504bc4aa17dp20, y = -0x1.6c5b8a8f1cc82p20, z = 0x1.8db0640e14989p22 m.
- **Control PASS:** one ulp in x changes the hash from the first step, at 0.076 s (9.3e-10 m, one ulp of 4.37e6 m), and moves the end of the day by 5.6e-6 m.
- **Run 001 of the control crashed:** JavaScript has no `Math.nextUp`. Version 2 calls `java.lang.Math.nextUp`, and every run was repeated with version 2. The version-1 runs had the same hash.
- **Wall time:** 1.7 to 3.0 s a run, 7.8 s under `-Xint` (the version-2 runs; load 13-67%).

**The custom side** (`m1a/build.sh`, `m1a/run_c.sh`; MEASURED).
- **The CPU has fused multiply-adds:** `gcc -O2 -march=native` resolves to `alderlake` and defines `__FMA__` and `__FP_FAST_FMA`, and plain `-O2` defines neither. The FMA build ran.
- **The FMA build really contains them** (`objdump -d`, the mnemonics vfmadd, vfmsub, vfnmadd and vfnmsub): 0 in `main`, where `grav()` is inlined, for `-O2`, and 29 for `-O2 -march=native -ffp-contract=fast`, among them `vfmadd132pd` on ymm registers. That is asserted. Neither binary has any elsewhere.
- **Hashes over Lasser et al.'s day:**
  - `-O2`: `e87242fb...`, the same on a rerun;
  - FMA build: `fe534418...`, the same on a rerun;
  - the two differ at 2,547 of 2,880 epochs, by at most 5.2e-17 m/s².
- **Control PASS:** one ulp planted at epoch 1000 changes the hash, and that epoch is the only one that differs.

**What M3 shows:** one JVM (8u411) on one machine reproduces itself to the bit across its compilation modes, for this pure-Java, single-threaded path. The C kernel's bits depend on whether the compiler contracts to FMA.
- **What it does not show:** reproducibility across JVM versions, threads or architectures; no second machine was named.
- **Why a pass settles little:** such a run is expected to reproduce itself (BELIEVED, plan-verifier-C). So the pass weakens the "bit-reproducible predictions" differentiator without settling it.

## M4. The covariance-realism hindcast, designed

**Objects with independent truth** (READ via WebFetch, EDC's satellite list [C11]):

| object | ILRS ID / NORAD | end of mission | laser data at EDC |
|---|---|---|---|
| ENVISAT | 0200901 / 27386 | contact lost April 2012 (READ, search excerpt [C14]) | 2002-04-11 to 2024-08-08 |
| TOPEX/Poseidon | 9205201 / 22076 | BELIEVED early 2006 | 1992-08-10 to 2025-02-20 |
| Jason-1 | 0105501 / 26997 | BELIEVED 2013 | 2001-12-19 to 2023-04-04 |
| Jason-2 | 0803201 / 33105 | BELIEVED 2019 | 2008-06-24 to 2025-03-06 |
| ERS-2 | 9502101 / 23560 | BELIEVED 2011 | 1995-05-01 to 2020-07-06 |

- **Sources disagree on TOPEX.** The ILRS past-missions table ends its tracking at 2005-12-15, while EDC lists data to 2025 (both READ via WebFetch [C10, C11]).
- **The normal-point bin is 15 s** for ENVISAT (READ via WebFetch, ILRS mission page).
- **How often:** in May to October 2013, 19 stations ranged to ENVISAT, about 2.87 station-passes a day (READ, search excerpt of an ILRS poster [C15]). One three-day subset held 10 passes and 115 normal points (READ, search excerpt [C16]).
- **The spin:** ENVISAT spins, and its reflector sits 2.52 m from the spin axis. That puts metre-scale oscillations in its ranges (READ, search excerpt [C14]).
- **Not found:** current pass rates, and TOPEX's.

**Truth data:**
- **ILRS normal points** are in CRD, version 2.01 since 1 August 2022 (READ via WebFetch [C13]).
- **CDDIS:** HTTPS needs an Earthdata Login account, and anonymous FTP ended in October 2020. FTP-SSL examples log in as "anonymous" with an email address as the password (READ via WebFetch [C12]).
- **EDC:** an API key is required, "obtained free of charge after registering". The data browser requires a login, and FTP and SFTP are being retired (READ via WebFetch [C11]). So EDC is not open without an account.
- **Volume** (COMPUTED from the READ excerpt and BELIEVED record sizes):
  - 2.87 passes a day is about 86 passes a month, and 11.5 normal points a pass is about 990 points;
  - at about 80 bytes a record and 10 header records a pass, that is about 0.15 MB an object-month.
- Nothing was downloaded.

**Predictions to test, and where each covariance comes from:**
- **TLE plus SGP4.** A TLE carries no covariance.
  - It is estimated from TLE-to-TLE differences, by Flohrer et al.'s method or by Geul, Mooij and Noomen's robust weighted differencing (READ, search excerpts [C17]).
  - Such differences are non-Gaussian and biased, and grow polynomially (READ, search excerpt, Bamann 2018 [C17]). So the test must be able to fail them.
- **Orbit determination with Orekit** (batch least squares or its Kalman filters, range measurements; READ via WebFetch by DEBRIS-B [B20]). The covariance comes from the fit's normal matrix, or the filter's state, propagated through the state transition matrix to each prediction time.

**The test, with its pass and fail criteria stated now.** The bands are COMPUTED exactly in `m4/m4_criteria.py`.
- **The statistic.** For each pass, use the one normal point nearest the pass midpoint, so the values are close to independent (BELIEVED):
  - z = (ρ_obs - ρ_pred) / sqrt(hᵀPh + σ_obs² + σ_spin²);
  - h is the line-of-sight unit vector, and P the predicted position covariance;
  - σ_spin is a stated allowance for the reflector's spin offset, 1.8 m for ENVISAT (BELIEVED: 2.52/√2 for a sinusoid).
  - Under a realistic covariance, z ~ N(0,1). Laser ranging gives range only, so this is the 1-D form of the χ² test: P(|z| ≤ 1, 2, 3) = 0.6827, 0.9545, 0.9973. The 3-D form would be 0.1987, 0.7385, 0.9707.
- **PASS,** for one method and one horizon bin (1, 2, 3, 5 and 7 days after the arc) with N ≥ 50 passes, iff both:
  - (a) the count with |z| ≤ 2 lies inside the two-sided 99% binomial interval;
  - (b) the mean of z² lies inside χ²(N)'s 0.5% to 99.5% band divided by N.
- **Otherwise FAIL;** with N < 50, "not determined". The bands:

  | N | (a) count with \|z\| ≤ 2 | (b) mean z² |
  |---|---|---|
  | 50 | 43 to 50 | 0.560 to 1.590 |
  | 86 | 76 to 86 | 0.651 to 1.436 |
  | 200 | 183 to 198 | 0.761 to 1.276 |

  At small N, (a) cannot fail on the high side. An over-cautious covariance is caught by (b) instead.
- **The refusal rule, and its own test.** A prediction is refused when its predicted along-track 1-σ exceeds 10 km, a threshold BELIEVED to mark where a Cartesian Gaussian stops describing LEO uncertainty. The threshold is fixed before the data.
  - The rule PASSES iff, on the hindcast, the refused predictions' realised z fail (a) or (b), the accepted ones pass both, and the rule refuses at most half of all predictions.
  - Otherwise it FAILS: it refused good predictions, or it kept bad ones, or it refused too much to be useful.

**What it would take here:**
- **Downloads** (each named and approved first):
  - ENVISAT CRD normal points for the pilot month, and a second month for calibration;
  - that object's TLE history, which is on Space-Track (an account, BELIEVED);
  - ILRS station coordinates and eccentricities, IERS EOP C04 and leap seconds;
  - space weather (CelesTrak `SW-All.csv`, DEBRIS-B [B5]).
- **Credentials, all Logan's:** an EDC registration and API key, or an Earthdata Login; and a Space-Track account.
- **CPU** (COMPUTED):
  - Orekit's DP853 took 358 steps an object-day in M3 (MEASURED). At 12 evaluations a step (BELIEVED) and 10.7 µs an evaluation (degree 20 plus NRLMSISE00, the table above), that is 46 ms an object-day.
  - With the 6×6 state transition matrix, BELIEVED 5 to 10 times that, it is 0.23 to 0.46 s.
  - Ten 3-day fits of 10 iterations (69 to 138 s), plus ten 7-day predictions with covariance (16 to 32 s), come to 1.4 to 2.8 CPU-minutes a month. SGP4 is negligible (BELIEVED).
- **The smallest pilot that would show the protocol works:**
  - one object (ENVISAT), one month of normal points and TLEs, and a second month held back, on which the fixed refusal rule is tested out of sample;
  - rolling 3-day fits;
  - the test above at 1 to 7 days for both methods.
  - Its first deliverable is whether either method passes (a) and (b) at any horizon with N ≥ 50.

## What M1 to M4 mean for build, adopt and hybrid (BELIEVED, from the measurements)

- **Build.**
  - The route exists, layer by layer, for layers 3 and 4: a normalised kernel written in this study from DEBRIS-B's recursion meets GROOPS at 2.3e-15 m/s², and my DE421 reader meets JPL to 1.4e-14 AU on bodies (MEASURED).
  - The cost argument is weaker than it looked. Gravity is 1.5 to 3.5 times cheaper in C than in Orekit (MEASURED), but at degree 20 a LEO evaluation is 80% (NRLMSISE00) to 94% (JB2008) density model (COMPUTED). A build would have to port NRLMSISE00 or JB2008, under the licence questions DEBRIS-B found, or call Orekit's.
  - M3 adds a discipline cost. Each C build reproduces its own bits, but two builds of the same source agree only with pinned contraction (`-ffp-contract=off` or an explicit `fma`) and a fixed operation order (DEBRIS-B's J2 finding).
- **Adopt.**
  - Orekit ran every path used here on Java 8 without orekit-data, met GROOPS at 2.2e-15 m/s², met the third-body accelerations to 4e-16, and reproduced itself to the bit across JIT modes (MEASURED).
  - Against it, also MEASURED: its reader refused the benchmark's own gravity file, a strictness a pipeline must handle. And its DE421 positions sit 6 to 15 µs off at TDB-dated queries, irrelevant at debris accuracy but a mark against it as a testpo-level oracle.
- **Hybrid.**
  - Orekit is a usable oracle for gravity and third-body forces at the 1e-11 level and well below (MEASURED). It is not one at 1e-13 AU in ephemeris positions, unless the time-offset question is resolved.
  - The custom part would carry its own density model or call Orekit's, and M2 prices that.
- **Candidate 1, bit-reproducible predictions:** weakened on one JVM and one machine, and unsettled across JVMs, threads and architectures.
- **Candidate 2, uncertainty with a refusal:** testable with public truth for a handful of defunct objects, at minutes of CPU. It needs Logan's accounts and a debris-specific measurement model for the spin.
- **No recommendation:** these results do not decide among the three.

## Measurements and their commands

All runs are from `studies\debris-c\`, through `python -I -B run.py --label L [--timing] --script S [--script S2] -- <command>`.
- **The runner:** it keeps every script version under `scripts\<name>.<12 hex>.<ext>`, writes `logs\L.NNN.log` without overwriting, records the script's SHA-256, and, with `--timing`, the TimeSheet check. From version 2 it also records the child's cycles.
- **`JJS`** expands to `C:/Program Files/Java/jre-1.8/bin/java.exe [options] -cp <the eight jars> jdk.nashorn.tools.Shell`.
- **"bash"** is `C:/Program Files/Git/usr/bin/bash.exe`, and **"python"** is Miniconda's, run with `-I -B`.

| measurement | command (after `--`) | log(s) |
|---|---|---|
| M0 gate, the download / the copy | `JJS m0/m0_gate.js` / `JJS m0/m0_gate.js -- <scratch>/gfc_dedup` | `m0_gate.001` (FAIL), `.002` (PASS) |
| the de-duplicated copy | `python m0/derive_gfc_copy.py` | `m0_derive_gfc_copy.001` |
| M1a control degree, COMPUTED first | `python m1a/m1a_control_degree.py` | `m1a_control_degree.001` |
| M1a builds and FMA counts | `bash m1a/build.sh` | `m1a_build.001` |
| M1a custom kernel runs (also M3's) | `bash m1a/run_c.sh` | `m1a_run_c.001` |
| M1a Orekit | `JJS m1a/m1a_orekit.js -- <copy dir> <00orbit_itrf.txt> 180 m1a/out/orekit_2_180.txt` (and 173) | `m1a_orekit_180.001`, `m1a_orekit_173.001` |
| M1a comparison | `python m1a/m1a_compare.py` | `m1a_compare.001` |
| M1a domain | `bash m1a/m1a_domain.sh`; `python m1a/m1a_domain.py`; `python m1a/m1a_degree_min.py` | `m1a_domain_runs.001`, `m1a_domain.001`, `m1a_degree_min.001` |
| M1b Orekit positions | `JJS m1b/m1b_orekit.js -- <testpo.421> <00orbit_icrf.txt> m1b/out/orekit_testpo.txt m1b/out/orekit_bodies.txt` | `m1b_orekit.001` |
| M1b checks | `python m1b/m1b_check.py` | `m1b_check.001` (crashed in the control), `.002` |
| M1b diagnoses (after the data) | `python m1b/m1b_diag.py`; `python m1b/m1b_diag2.py` | `m1b_diag.001`, `m1b_diag2.001` |
| M2 timings | `--timing ... JJS m2/m2_time.js` | `m2_time.001` (set aside), `.002`, `.003` |
| M2 control 2 | `JJS m2/m2_reference.js` | `m2_reference.001` (crashed), `.002` |
| C kernel again | `--timing ... bash m2/run_c_grav.sh` | `m2_c_grav.001` |
| CPU counters | `--timing ... <scratch>/bin/cyclecal.exe`; `--timing ... JJS m2/m2_cpu_check.js` | `m2_cyclecal.001`, `m2_cpu_check.001`, `.002` |
| M2 table | `python m2/m2_table.py` | `m2_table.001` |
| M3 Orekit runs | `bash m3/run_m3.sh` (each: `JJS [options] m3/m3_prop.js -- m3/out/v2/steps_<run>.txt [ulp]`) | `m3_prop_<run>.001` (version 1), `.002` |
| M3 comparison | `python m3/m3_compare.py` | `m3_compare.001` |
| M4 bands | `python m4/m4_criteria.py` | `m4_criteria.001` |
| the downloads against lead.md | `python check_downloads.py` | `check_downloads.001` |
| CPU total | `python cpu_total.py` | `cpu_total.001`, `.002` (the final count) |

- **Inputs:** all 19 downloaded files match lead.md's byte counts and SHA-256 (MEASURED, `python check_downloads.py`, `logs/check_downloads.001.log`, with a control: one altered hash is reported). I first compared them by eye with `sha256sum` at 17:59, before any use. The comparison scripts print the hashes of what they read.
- **Outputs:** the C, Orekit and step records are in `m1a\out`, `m1b\out` and `m3\out`.
- **CPU used:** 7.2 CPU-minutes in all (COMPUTED by `cpu_total.py`, `logs/cpu_total.002.log`, over 45 logs), against a budget of 30:
  - by cycles at 2.5e9 a second, for logs from runner version 2, as the lead's ruling of 18:31 requires;
  - by the larger of 4 × GetProcessTimes and the wall time, for version-1 logs. The lead measured the under-count at 1.7 times in its own run, so this is an upper estimate;
  - by wall time for bash-wrapped runs;
  - plus about 10 s of exploration outside the runner (BELIEVED).
- **Wall time:** 57 minutes from dispatch to the last measurement (17:56 to 18:53 by `date`), against a budget of 4 hours.

## What this study could not settle

- **Why Orekit's DE421 positions sit 6 to 15 µs off** at TDB-dated queries. The figure is MEASURED, the cause is not.
- **Why GROOPS sits 2e-15 m/s² from both of ours** in gravity, 7 times further than they sit from each other.
- **JB2008's correctness** as timed: there was no reference check (above).
- **A C density model's cost,** which would price the build option's density term.
- **Orekit's reproducibility across JVMs, threads and architectures.**
- **Current pass rates** for ENVISAT and TOPEX, and whether TOPEX's tracking ended in 2005 (ILRS) or continued to 2025 (EDC).
- **What I did not do:**
  - download anything, or use orekit-data;
  - run the hindcast, any orbit determination, or a second machine;
  - count Orekit's force evaluations per step;
  - check CRD record sizes;
  - re-check DEBRIS-B's GetProcessTimes-based sweep CPU figure;
  - fix anything in DEBRIS-A or DEBRIS-B.

## What the brief got wrong

1. **M0's stop rules** had no branch for an approved input that Orekit refuses: the duplicated degree-0 line. The lead's ruling supplied one.
2. **The Rules name GetProcessTimes** as the JVM's CPU counter. On this host today it reads about a quarter of the real CPU (MEASURED). The lead has since replaced it with the cycle counter (lead.md 18:31).
3. **M1b's example basis**, "the precision testpo.421 prints", fails for the libration angles, which reach 6,666 rad, where one ulp is 9.1e-13. A basis must scale with the value. I made the same mistake in my own stated basis.
4. **M2's suggested route to reference values** fails: GitHub's HTML view truncates `NRLMSISE00Test.java` before its reference values, and orekit.org's cross-reference pages are behind bot protection. I used pynrlmsise00's documentation instead.
5. **M4's question "is the EUROLAS data centre open?"** has the answer no: it needs registration and an API key.

## Sources

READ via WebFetch unless marked; fetched 2026-11-12.
- [C1] Lasser et al. 2020, Adv. Geosci. 55, 1-11: https://adgeo.copernicus.org/articles/55/1/2020/. Its 1e-11 m/s² threshold is as the plan READ it; I did not re-fetch the page.
- [C2] The dataset's `00README_simulation.txt`, and its `EIGEN6-C4.gfc`, orbit and acceleration files: local downloads (READ), from https://ftp.tugraz.at/pub/ITSG/COST-G/softwareComparison/, with SHA-256 in lead.md.
- [C3] JPL DE421 `lnxp1900p2053.421`, `header.421` and `testpo.421`: local downloads (READ), SHA-256 in lead.md.
- [C4] Orekit `HolmesFeatherstoneAttractionModel.java` at 13.1.9: https://github.com/CS-SI/Orekit/blob/13.1.9/src/main/java/org/orekit/forces/gravity/HolmesFeatherstoneAttractionModel.java
- [C5] IERS EOP Centre, TAI-UTC table: https://hpiers.obspm.fr/eop-pc/index.php?index=TAI-UTC_tab&lang=en. Bulletin C 30, as a search excerpt: https://mm.icann.org/pipermail/tz/2005-July/038153.html
- [C6] pynrlmsise00's README, "C model interface": https://pynrlmsise00.readthedocs.io/en/stable/README.html
- [C7] Orekit `NRLMSISE00Test.java` at 13.1.9, whose page truncates before the reference values: https://github.com/CS-SI/Orekit/blob/13.1.9/src/test/java/org/orekit/models/earth/atmosphere/NRLMSISE00Test.java. Its cross-reference page, https://www.orekit.org/site-orekit-13.0/xref-test/org/orekit/models/earth/atmosphere/NRLMSISE00Test.html, returned "Access Denied".
- [C8] Orekit `JB2008Test.java` at 13.1.9: https://github.com/CS-SI/Orekit/blob/13.1.9/src/test/java/org/orekit/models/earth/atmosphere/JB2008Test.java
- [C10] ILRS past missions: https://ilrs.gsfc.nasa.gov/missions/satellite_missions/past_missions/index.html; ENVISAT: https://ilrs.gsfc.nasa.gov/missions/satellite_missions/past_missions/env1_general.html; current missions: https://ilrs.gsfc.nasa.gov/missions/satellite_missions/current_missions/index.html
- [C11] EDC: https://edc.dgfi.tum.de/en/data/, https://edc.dgfi.tum.de/en/satellites/, https://edc.dgfi.tum.de/en/data/browser/; the EDC API: https://edc-api.readthedocs.io/ and https://edc-api.readthedocs.io/en/latest/authentication.html
- [C12] CDDIS archive access: https://www.earthdata.nasa.gov/centers/cddis-daac/archive-access
- [C13] ILRS CRD format: https://ilrs.gsfc.nasa.gov/data_and_products/formats/crd.html
- [C14] Kucharski et al. 2014, ENVISAT's attitude and spin from laser ranging (search excerpt): https://boris-portal.unibe.ch/handle/20.500.12422/154494
- [C15] The ILRS Laser Workshop 18 poster, Weigel et al. (search excerpt; a PDF, not fetched): https://ilrs.cddis.eosdis.nasa.gov/lw18/docs/papers/Posters/13-Po40-Weigel.pdf
- [C16] Wirnsberger et al., Laser Workshop 19 (search excerpt; a PDF, not fetched): https://ilrs.gsfc.nasa.gov/lw19/docs/2014/Papers/3017_Wirnsberger_paper.pdf
- [C17] TLE covariance (search excerpts):
  - Geul, Mooij and Noomen: https://research.tudelft.nl/en/publications/tle-uncertainty-estimation-using-robust-weighted-differencing/
  - Flohrer et al., SDC5 paper 111: https://conference.sdo.esoc.esa.int/proceedings/sdc5/paper/111/SDC5-paper111.pdf
  - Bamann, 2018: https://ilrs.cddis.eosdis.nasa.gov/lw21/docs/2018/presentations/SessionSD2_Bamann_presentation.pdf
  - the 3-D χ² practice: https://ntrs.nasa.gov/api/citations/20170003685/downloads/20170003685.pdf
- **From DEBRIS-B:** [B5] CelesTrak; [B20] Orekit's capabilities (READ via WebFetch by DEBRIS-B).
- **Local, READ:** DEBRIS-B's study, records and verifier-B's report; the ledger's `lead.md`.
