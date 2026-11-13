# DEBRIS-B: what a custom debris model would stand on, cost, and buy

Study parcel DEBRIS-B for cft-debris, 2026-11-12, under the plan of record `studies\DEBRIS-B-plan.md` (draft 3). A study only: nothing was built and no repository changed. Scripts, logs and records are in `studies\debris-b\` (its `MANIFEST.sha256` lists them).

**Verified, 2026-11-12.** verifier-B re-ran the study's measurements from clean (`studies\DEBRIS-B-verifier-B-report.md`). Every figure it re-ran reproduced exactly, except Q2's timings, which reproduced within 12%. At the merge the lead narrowed eight passages that claimed more than their evidence. Each is marked "(narrowed at the merge)" and listed in the last section. The text as DEBRIS-B reported it (SHA-256 `014d75ff8d19ad5a9f4e914db096d4579b9b42b079618d3047f7aa1dd027fb8f`) is kept at `cft-debris-ledger\filed\DEBRIS-B-custom-model.as-reported.md`.

> "Im considering how challenging making a custom simulation model might be, considering how specialized of a focus this is and effects REBOUND isnt particularly good at or even supports" ... "I'm also curious if fp256 can buy us anything with our own model, as IAS15 showed no noticeable improvement past fp128 simply as it was designed for fp64 to begin with" (Logan)

Labels, as in DEBRIS-A:
- **MEASURED**: I ran it on this host; the command is in "Measurements".
- **COMPUTED**: arithmetic from labelled inputs. `q3\tables.py` does the tables; the few one-line figures elsewhere show their inputs where they appear.
- **READ**: I fetched or opened the source. "READ (WebFetch)" means a model's summary of the page, which supports "consistent with", never "confirmed". "READ (search excerpt)" means a search engine's summary only. Local files (HORIZON.md and the rest) are READ directly.
- **BELIEVED**: my judgement, or a figure I did not fetch.

DEBRIS-A's figures are used only where verifier-A reproduced them (lead.md, 16:08); each such use says so.

## Short answer

1. **The authorities exist for the core layers, and most are free and need no registration** (READ). SOFA covers time and frames, the IERS covers Earth orientation and leap seconds, and JPL's DE440 comes with its test file `testpo.440` (838.1K). Vallado's SGP4 comes with its verification set. The strongest single find is **Lasser et al. 2020**: published per-model accelerations along a one-day GRACE orbit. It covers gravity to degree and order 180, third bodies, tides, relativity and the celestial-terrestrial rotation, and it was made to verify exactly this kind of software.
   - **Gaps:** I found no published test vectors for drag, radiation pressure with shadow, or orbit determination. The density models' own test files exist, but NRL's server reset every connection, SET's returned 403, and their licences restrict commercial use. ESA's DISCOS is closed to individuals. For debris, independent truth is mostly TLE histories.
2. **In LEO a real force evaluation costs 1.2 to 11 µs here at binary64, and in MEO and GEO 1.1 µs** (MEASURED, kernels only, no full density model; narrowed at the merge). That covers gravity to degree 8 through 70, an interpolated frame, Sun and Moon, an exponential atmosphere, radiation pressure and the integrator's own share.
   - IAS15 needs 12,410 evaluations per LEO object-day with J2, and 16,463 to 20,159 with a degree-20 to degree-70 field (MEASURED).
   - So the 28,149 catalogued LEO objects cost **46 to 634 CPU-hours a year**, and MEO and GEO together about 0.3: 0.23 + 0.08 = 0.31 (COMPUTED; narrowed at the merge from "under 0.3").
   - The open term is the density model. I found no absolute cost for NRLMSISE-00 or JB2008. At 10 µs a call, one would multiply the degree-20 LEO budget by 6.4, to 557 CPU-hours.
3. **Binary64 is not the limit in any regime tabulated here**, which are near-circular LEO, MEO and GEO, with no GTO or HEO row (COMPUTED from measured coefficients; narrowed at the merge). Its arithmetic error is 2e-8 to 1.2e-5 m after a week, and at most 0.9 m after 30 years even on the pessimistic transfer. In GNSS disposal orbits, chaos amplifies the arithmetic along with everything else (BELIEVED, since the cited source speaks of navigation satellites; Q3.1, "What does not transfer").
   - Against the physics it is 10^7 or more below at a week and 10^6 or more below at a year. A 20% density error moves a 400 km object 5.0 km in a day; a 20% area-to-mass error moves MEO or GEO objects 0.2 to 0.3 km in a week and 5 to 7 km in a year (MEASURED).
   - Only a centimetre-level initial state comes near it: binary64 is 10^3 below that at a week, and 2 to 100 times below at a year. After 30 years the pessimistic law's 0.08 to 0.9 m exceeds a centimetre. That the centimetre has itself grown far past that by then is BELIEVED (narrowed at the merge).
4. **Logan's hypothesis, tested.** Halving the step cut binary256's round trip by 2^15.0 twice: 8.9e-22, then 2.7e-26, then 8.3e-31 m. Both points fall inside the predicted band (MEASURED). Binary128 stops at 2 to 3e-26 m, its own floor.
   - So "no improvement past fp128" at dt = 100 s was IAS15's fixed 15th-order discretization, not the arithmetic.
   - "Designed for fp64" is right about the step control and the fixed order. Reaching binary256's floor this way would take about 600 times smaller steps. Taylor methods instead double the order when the format's precision doubles (READ, the heyoka paper).
5. **A wider format buys rulers and conditioning, and binary128 is enough for every use found.** That rests on one measured floor, binary128's round trip at about 2e-26 m, and on BELIEVED judgements for orbit determination and covariance (narrowed at the merge). Binary256 is needed only to rule binary128 itself.
   - Price: binary128 gravity in C through libquadmath costs **177 to 214 times binary64** (MEASURED).
   - On the tile, no rate exists for any force beyond point-mass gravity (READ, both leads' answers). On the Kepler floor, a year of the LEO catalogue at binary256 is 0.9 tile-years, against 46 to 634 CPU-hours at binary64 (COMPUTED).
6. **Product.** The evidence lays out three shapes and does not choose among build, adopt or hybrid. Section Q4 names the measurement that would make each candidate advantage real.

---

## Q1. Authorities, layer by layer

At most two candidates per layer, in the order product (a) needs them. "On host": nothing in this list is installed (the lead's check, 2026-11-12: no erfa, astropy, sgp4, skyfield, jplephem, spiceypy, pymsis, orekit). Sizes are the server's own listing as WebFetch reported it.

| # | layer | standard or model | reference implementation (licence) | published test vectors: where, file, size, licence | registration |
|---|---|---|---|---|---|
| 1 | time scales, GCRF, ITRF | IAU 2006/2000A, CIO-based (IERS Conventions 2010, ch. 5) [B1]. Series term counts, READ from the tables' headers: X (5.2a) 1306/253/36/4/1 = 1,600; Y (5.2b) 962/277/30/5/1 = 1,275; s+XY/2 (5.2d) 33/3/25/4/1 = 66 | IAU SOFA, issue 2023-10-11 [B2]. The SOFA licence: free of charge; variations "must be explicitly marked"; routine names must not include "iau" or "sofa". ERFA (BSD-3) [B3] is SOFA's derivative, so ERFA agreeing with SOFA is a port agreeing with its original | (i) SOFA's distribution, `sofa_c-20231011tar.gz`, 3,055,571 bytes, which (BELIEVED, not on the page) carries SOFA's own test program. (ii) Lasser et al. 2020 [B9]: TRF-CRF rotations as quaternions and matrices at 30 s along a GRACE day, `ftp://ftp.tugraz.at/outgoing/ITSG/COST-G/softwareComparison/`. Its size was not reached: it is an FTP tree, and HTML pages only may be fetched. Article CC BY 4.0; no separate data licence; "freely accessible" | none found (READ) |
| 1 | TEME | Vallado et al. 2006 [B13] | inside Vallado's SGP4 package (row 7) | not separately located | none |
| 2 | Earth orientation, leap seconds | IERS EOP C04; IERS Bulletin C | the IERS series are themselves the authority | `eopc04.1962-now` 4.9M, updated 2026-11-12 15:21 [B4]; `Leap_Second.dat` 1.3K, 2026-07-06 [B4]. A reader is checked by reproducing tabulated epochs. CelesTrak's `EOP-All.csv` (2,385,176 bytes) re-serves EOP but names no source or terms [B5]. No licence statement was found on the pages read | none |
| 3 | gravity field | EGM2008 (NGA); EIGEN-6C4 (GFZ, degree 2190, via ICGEM) [B7] | NGA's synthesis code: not reached, earth-info.nga.mil failed twice. ICGEM offers a calculation service on user points and grids [B7] | Lasser et al. 2020 [B9]: EIGEN-6C4 accelerations to degree and order 180, in CRF and TRF, along the GRACE orbit (466 km). Size and licence as row 1 | ICGEM shows no registration for downloads [B7] |
| 4 | Sun and Moon | JPL DE440/DE441 (Park et al. 2021): Chebyshev polynomials "typically in 32-day intervals" (READ, JPL's README, the file WebFetch saved, read with Logan's approval) | JPL's Fortran readers ("require some tailoring") and NAIF SPICE, "the recommended means" [B8] | `testpo.440`, 838.1K, 2020-12-22, in `https://ssd.jpl.nasa.gov/ftp/eph/planets/ascii/de440/` [B8]. That it checks a reader through JPL's `testeph` is BELIEVED: none of the three pages read says so. No terms of use were found. Also Lasser et al.: third-body accelerations from DE421 | none; "anonymous ftp" (README) |
| 5 | atmosphere and space weather | NRLMSIS 2.1 (and NRLMSISE-00); JB2008 | NRL's Fortran, under an "Open Source Academic Research License" (READ, search excerpt). The pymsis README says "the MSIS2 code is not available for commercial use without contacting NRL" [B10]. JB2008: SET's Fortran, "under a license agreement" (READ, search excerpt); the code page returned 403 [B11] | NRLMSIS 2.1: `msis2.1_test_in.txt` and `msis2.1_test_ref_dp.txt` (READ, search excerpt); NRL's directory gave ECONNRESET twice, so no size. JB2008: "validation test cases and reference output data" on SET's site (search excerpt; 403). Drivers: CelesTrak `SW-All.csv`, 2,894,068 bytes [B5]; GFZ's Kp/ap/Ap/F10.7 files, nowcast with no forecast, licence not on the page, DOI 10.5880/Kp.0001 [B6] | NRL none known; SET agreement (BELIEVED); CCMC runs need registration [B11] |
| 6 | radiation pressure, shadow, area-to-mass | no standard; cannonball with a conical shadow (Montenbruck and Gill, section 3.4; BELIEVED) | none authoritative. The spherical-Earth conical model was 11.07% off accelerometer-derived shadow functions in one study, against -0.79% for a perspective-projection model (READ, search excerpt [B27]) | **not found.** Route: WebSearch for published conical-shadow test cases returned model descriptions and one validation study, but no table. Lasser et al.'s page does not mention radiation pressure or drag, so their exclusion is inferred (READ [B9]; narrowed at the merge) | n/a |
| 7 | SGP4/SDP4 and TLEs | Vallado et al. 2006, AIAA 2006-6753 [B13] | `AIAA-2006-6753.zip`, 1,248,284 bytes, in C++, C#, Fortran, Java, MATLAB and Pascal. The page states no licence ("non-proprietary version") [B13]. Python `sgp4` (MIT) compiles Vallado's C++ [B13]: a port of the original | the verification set inside the zip (`SGP4-VER.TLE` and its output). That it is inside is BELIEVED: the page does not list it. TLEs: CelesTrak GP, "Brouwer mean elements" fit to SSN observations, no accounts [B14]; Space-Track needs an account (BELIEVED) | none for CelesTrak |
| 8 | orbit determination | no algorithmic standard; CCSDS TDM and ODM formats | Orekit (Apache-2.0): batch least squares and extended and unscented Kalman filters, range, range-rate, angles and GNSS measurements [B20]; GMAT | **not found.** Route: WebSearch "orbit determination benchmark test case published reference solution..." The summary found "no single canonical ... benchmark"; Papers with Code lists 0 datasets (search excerpt). The working substitute is real tracking with independent precise orbits (row 9) | n/a |
| 9 | truth for hindcasts | ILRS laser ranging (CRD normal points, full rate); IGS GNSS orbits | n/a | At CDDIS, HTTPS needs an Earthdata Login and plain anonymous FTP ended in October 2020; its FTP-SSL examples log in as "anonymous" (READ [B24]). EUROLAS (DGFI) is the other ILRS centre; its access was not reached. IGS final orbits are about 3 cm (search excerpt only [B25]). For debris objects themselves I located no public independent truth: SLR to defunct satellites is BELIEVED, not READ | CDDIS HTTPS: yes |
| 10 | object properties | ESA DISCOS; GCAT (McDowell) | n/a | DISCOSweb accounts are only for "research institutes, government bodies, or industrial companies in ESA Member States", not individuals (READ, SDUP page [B16]). GCAT is CC-BY-4.0, release 1.8.9 (2026-11-06), with no registration; that it carries mass and dimensions is BELIEVED, not on the page [B17] | DISCOS yes and restricted; GCAT none |
| 11 | conjunction screening, collision probability | CCSDS 508.0-B-1, the CDM (2013, Technical Corrigendum 2 2021, ISO 19389) (search excerpt [B18]) | NASA CARA Analysis Tools, MATLAB, NASA Open Source Agreement, with unit tests and a DataFiles folder [B18]. Orekit has Chan, Alfriend, Alfano, Patera and Laas Pc, and CDM I/O [B20] | CARA's unit tests and DataFiles are located; their sizes are not listed (Git LFS). Alfano's test cases are not confirmed on the page | none (GitHub) |
| 12 | fragmentation, long-term environment | NASA Standard Breakup Model (Johnson et al. 2001); ESA MASTER-8 | `esa/NASA-breakup-model-cpp`, GPL-3.0, C++17, GoogleTest; "validated implementation", with its details in a TU Munich thesis [B19]. MASTER: through an SDUP licence application; "a full MASTER installation gives access also to the historic and future population" [B16] | **not found** as files. The model's published distributions are its definition | MASTER: licence application |

**The trap, applied.** Vallado's verification output is the authority for SGP4. Orekit's SGP4 agreeing with it, or python-sgp4 agreeing with it, is a port agreeing with its original. Likewise ERFA with SOFA, and any NRLMSISE-00 port with NRL's code. Lasser et al.'s accelerations are a different kind of authority: GROOPS produced them, and the paper was written so that other software can be held to them.

**Whole-propagator foreign oracles.**
- **Orekit 13.1.9** (tagged 2026-10-03) compiles with Java source and target 1.8 and Hipparchus 4.0.3, under Apache-2.0 (READ, its pom at that tag [B20]). So it should run on this host's Java 8 (BELIEVED; not run).
  - Its `develop` branch, 14.0-SNAPSHOT, needs Java 21 (READ).
  - Running it here takes about three named downloads: the Orekit jar, the Hipparchus jars, and orekit-data (EOP, leap seconds, ephemerides, gravity fields). orekit.org's bot protection refused WebFetch, so their sizes were not reached.
  - Orekit interpolates CIRF with 6 points at 1-hour spacing (`Constants.JULIAN_DAY / 24`, READ, `AbstractFrames.java` [B20]). That is the interval timed in Q2.
- **GMAT R2025a:** `gmat-win-R2025a.zip`, about 428.7 MB (search excerpt [B21]). Its licence was not confirmed.
- **What agreement would prove:** a custom implementation reproduces an independent implementation of the same published models, with the same data files, to a stated tolerance. That catches coding errors in frames, gravity, third bodies and integration.
- **What it would not prove:**
  - that the models match the sky (that needs row 9);
  - anything about the shared inputs (EOP, DE440, the gravity coefficients), whose errors cancel;
  - anything about a model Orekit has ported from the same source: SGP4, NRLMSISE-00, JB2008.
- The published vectors above are the stronger authority: `testpo.440`, Vallado's output, SOFA's tests, Lasser et al. and NRLMSIS's reference output.

## Q2. The cost of a real force evaluation

Small self-written C (`q2\q2bench.c`, `gcc -O2`, x86_64-w64-mingw32 16.1.0), binary64. Synthetic coefficients are in each model's magnitude range, from a fixed seed, with no zeros and no subnormals. Gravity uses Kaula-rule magnitudes, 1e-5/n² per normalised coefficient, with C̄20 at its real value. Degree 1 and S_n0 are zero by definition, so they are not used, not drawn.

Each figure is the minimum of 5 repetitions of about 0.25 s. The host load during each repetition was 13 to 69% (GetSystemTimes, all 12 logical CPUs); every repetition's load is in `q2_time.log`. QueryThreadCycleTime, read at a 2.5 GHz TSC (BELIEVED, the part's base clock), puts the thread on a CPU for 97 to 98% of each repetition's wall time. GetThreadTimes' CPU figures are too coarse at this length to use.

| kernel (timed unit) | operations a call (COMPUTED from the loops) | ns a call (MEASURED) | control 1: force/no-force | control 2: independent check (asserted) |
|---|---|---|---|---|
| gravity, degree and order 8 | 1,415 flops (1 sqrt) | 183 | 365x | 7.4e-16 rel., degrees 2-8 vs mpmath |
| gravity, 20 | 7,859 | 864 | 1,721x | 9.1e-16 |
| gravity, 36 | 24,515 | 2,618 | 5,225x | 1.9e-15 |
| gravity, 70 | 90,509 | 10,039 | 19,957x | 2.1e-15; degrees 36-70 alone 9.0e-15 |
| Sun and Moon, Chebyshev (DE-like: Moon 13 coefficients over 4 days, Sun 11 and EMB 13 over 16 days; BELIEVED layout) | 359 flops | 129 | 14.9x | 4.0e-15 of Σ\|c\| vs cos(k arccos τ) |
| GCRS to ITRS, full: the X, Y and s series term by term (2,941 terms, the IERS counts above), ERA, polar motion, matrix, applied to r | 94,278 flops + 2,941 sin/cos pairs + 19 transcendental calls | 146,936 | 10,495x | with the kernel's own binary64 arguments, 1.3e-16 of Σ\|amp\|; with exact arguments, 1.9e-12, 8% of the argument-formation error bound; matrix 2.2e-16 |
| the same, interpolated as Orekit does: X, Y, s by 6-point Lagrange on 3,600 s nodes; ERA exact; xp, yp and dUT1 linear in a daily table | 349 flops + 19 transcendental calls | 512 | 37.0x | Lagrange 2.2e-16 vs mpmath; matrix 4.4e-16. The interpolated-minus-full error for this synthetic series is 9.8e-14 rad (reported, not asserted) |
| exponential atmosphere (28 bands) and drag, one object a call | 25 flops + 2 sqrt + exp + 5 compares | 79.5 | 108x at one object | 1.7e-14 rel. |
| radiation pressure, conical shadow: 1,024 points round a LEO orbit | about 33 flops + 2 sqrt + 2 asin + acos + 4 div | 34.6 | 69x | 4.3e-16 of the unshadowed force |
| the same, points across the penumbral band only | the above + 12 flops + sqrt + 2 acos + 3 div | 74.9 | 149x | shadow fraction 7.2e-10 abs. against a quadrature of the discs' overlap |
| gravity at binary128 (libquadmath), 8 / 20 / 36 / 70 | as binary64 | 32,398 / 184,821 / 539,250 / 1,954,159 | 61,128x and up | 6.4e-33 / 7.2e-33 rel. (8 and 20 checked) |

**Negative controls, both results.**
- **Control 1, "the compiler can discard work whose result is never used."**
  - Every timed loop folds every output component into a printed checksum. The checksums were identical across repetitions.
  - The no-force build compiles every kernel call out (`-DNO_FORCE`). Every ratio is 10x or more (`q2_time.py` asserts it).
  - The exponential atmosphere passed at one object a call (108x). The batching the brief allowed for was not needed.
  - The closest margin is the Chebyshev kernel, 14.9x: the loop's own `fmod` for the time argument (8.7 ns) stays in both builds.
- **Control 2, "a fast wrong answer is still wrong."** `q2_check.py` re-evaluates each kernel independently and asserts.
  - Gravity: the potential in spherical coordinates with Legendre functions in mpmath at 60 digits, themselves checked against `mpmath.legenp`, differentiated numerically. This shares nothing with Cunningham's Cartesian recursion in the kernel.
  - Chebyshev: cos(k arccos τ).
  - Radiation pressure: a quadrature of the overlap area.
  - Final run: 40 assertions, all pass (`q2_check.log`).
- **It failed twice first**, and both failures are kept (`q2_check_v1_srp1_FAILED.log`, `q2_check_v2_frame_FAILED.log`):
  - **Deep penumbra.** The force was 2.7e-8 off in relative terms where the shadow fraction ν is 0.024. The closed-form lens, evaluated in mpmath, agrees with the quadrature to 8.8e-25. So the formula is right, and the binary64 closed form loses about 7e-10 of ν near the umbra's edge. The assertion was restated as error ÷ unshadowed force (7.2e-10). The per-point relative figure is still printed.
  - **The full series.** It missed my first tolerance, 1e-12 of Σ|amp|, at 1.3e-12. The cause is binary64 rounding in forming arguments of up to about 1e4 rad; my synthetic series pairs large amplitudes with fast arguments, which the real series does not. The check now asserts the kernel's own arguments to 1e-14, and the exact arguments against a computed error bound.

**IAS15's evaluations per object-day.** My own setup and counter (MEASURED, `ias15_evals.py`). The counter is a list of simulation times appended at every force call.
- The setup is DEBRIS-A §2's: REBOUND 5.1.1, a point-mass Earth, J2 as a Python force, ε = 1e-9, one day. Ω, ω and M are the values in DEBRIS-A's `leo_roundtrip.py`, read there, not run.
- **LEO 400 km, one day: 12,410 force evaluations, 559 steps.**
  - Over mean anomalies 0, 90, 180 and 270° and starting steps of 10 and 300 s: 12,397 to 12,459.
  - J2 written in REBOUNDx's 2020 operation order instead of the textbook order: 12,452 (`ias15_evals_order.log`). So the count moves 0.3% with the J2 expression's last bits: they change how many predictor-corrector passes converge, not the steps.
- **Ten-day averages** (J2): 12,372 a day at 400 km, 11,340 at 800 km, 1,601 MEO, 801 GEO, 793 graveyard. IAS15 takes 36 steps an orbit in every near-circular regime: 559, 72.2 and 36.3 steps a day.
- **A richer field costs passes, not steps.** With the Earth-fixed synthetic field turning at Earth's rate, LEO evaluations a day rise from 12,403 at degree 2 to 13,852 (8), 16,463 (20), 17,912 (36) and 20,159 (70), all at 559 steps. Drag adds nothing (16,470 at degree 20). MEO and GEO are unchanged at degree 8 (1,599 and 802 a day).

**NRLMSISE-00 and JB2008: cost not found** (READ, routes below). Neither model's absolute cost was found.
- The only figure: SatelliteToolbox.jl's author put Jacchia-Roberts 1971 at "10x less than NRLMSISE-00 and something like 70x less than JB2008" (2018, READ (WebFetch) [B12]). That is an estimate, not a benchmark.
- Routes that returned nothing usable:
  - pymsis README: no figures;
  - Orekit forum search: no per-call cost;
  - the arsa-2025-0007 article page: its abstract only;
  - Brodowski's C code: no licence stated;
  - NRL's server: ECONNRESET.
- No download was requested, because neither a size nor an open licence could be established.

**The catalogue-year budget** (COMPUTED, `q3\tables.log`).
- **Inputs:** per evaluation, the sum of the measured kernels plus the integrator's own 233 ns. That last figure is REBOUND's C IAS15 at 2.887 ms per point-mass LEO object-day (MEASURED), spread over 12,410 evaluations (a BELIEVED split).
- **Objects:** ESA DISCOS's statistics page, last updated 2 November 2026 (READ (WebFetch) [B16]): catalogued LEO 28,149, MEO 1,290, GEO 939, all regimes 47,393. MASTER-8 (02/2026) estimates 68,450 objects above 10 cm.

| regime and model | ns an evaluation | evaluations a day | ms per object-day | objects | CPU-hours a year |
|---|---|---|---|---|---|
| LEO, degree 8, exponential air | 1,171 | 13,852 | 16.2 | 28,149 | 46 |
| LEO, degree 20, exponential air | 1,852 | 16,463 | 30.5 | 28,149 | 87 |
| LEO, degree 36, exponential air | 3,606 | 17,912 | 64.6 | 28,149 | 184 |
| LEO, degree 70, exponential air | 11,027 | 20,159 | 222.3 | 28,149 | 634 |
| MEO, degree 8 | 1,091 | 1,599 | 1.75 | 1,290 | 0.23 |
| GEO, degree 8 | 1,091 | 802 | 0.88 | 939 | 0.08 |

- **The other 17,015 catalogued objects** (GTO, HEO and the rest), priced at LEO degree 20 as an upper bound, add at most 53 CPU-hours.
- **Scaling to MASTER-8's 68,450** multiplies by 1.44, assuming the same regime mix (BELIEVED).
- **The density model is the open term.** A model costing X ns a call adds X to every LEO evaluation:
  - X = 1 µs gives 134 CPU-hours a year at degree 20;
  - X = 10 µs gives 557;
  - X = 100 µs gives 4,786.
  - The break-even, where the density model doubles degree 20's cost, is X = 1.85 µs.
- **The full precession-nutation series** costs 287 times the interpolated transform. Evaluated hourly it is 1.3 CPU-seconds a year for a whole catalogue, because every object shares it.
- **Against DEBRIS-A's BELIEVED 10-100 µs an evaluation:** without a full density model, the measured range is 1.2 to 11 µs.

## Q3. Arithmetic beyond binary64

### 3.1 Binary64's error against the physics

**Binary64's arithmetic error** (COMPUTED), as along-track metres, from two measured coefficients:
- **Low:** DEBRIS-A's LEO binary64-versus-binary128 difference after one day on the same 100 s steps, 1.175e-8 m (`port_fullday.log`; reproduced by verifier-A), grown as t^1.5 (Brouwer). It is a single draw, and the ensemble's draws span about 50x, so "low" is an estimate, not a lower bound (narrowed at the merge).
- **High:** HORIZON.md's p90 law for its e = 1/2 Kepler ensemble, phase = 2.11e-16 × orbits^1.525.
- The high law overstates LEO by about 50x at one day (5.9e-7 against 1.2e-8 m). A near-circular orbit accumulates less phase roundoff than e = 1/2 (HORIZON: "the eccentricity is the orbit's amplifier").
- **The physical columns** are MEASURED with my own models (`q3_physics.log`), except where marked.

| regime | horizon | binary64, low to high | TLE-level initial state | precise-orbit initial state | density ±20% | area-to-mass ±20% |
|---|---|---|---|---|---|---|
| LEO 400 km, drag | a week | 2.2e-7 to 1.2e-5 m | grows ~1 km/day (inferred from [B15]; the error at epoch is not READ) | cm-level for GNSS-tracked satellites (BELIEVED); none for debris | 5.0 km after a day, 252 km after a week | the same as density: drag depends on ρB only |
| LEO 400 km | a year, decades | 8.2e-5 to 4.8e-3 m in a year | | | grown as t², 5.0 km × (t/day)² passes the whole orbit (40,000 km) at about 90 days; the object re-enters in about 160 days anyway (COMPUTED: H/\|da/dt\| with H = 58.5 km and \|da/dt\| = 0.37 km/day, scale height held constant) | |
| LEO 800 km, drag | week / year / 30 yr | 2.0e-7–1.1e-5 / 7.6e-5–4.4e-3 / 0.013–0.79 m | as above | as above | 16 m a day, 766 m a week, 14 km in 30 days | as density |
| MEO, GNSS disposal | week / year / 30 yr | 4.0e-8–2.0e-6 / 1.5e-5–8.2e-4 / 2.4e-3–0.15 m | as above | about 3 cm for active GNSS (IGS final; search excerpt only); none for disposed objects | n/a | 0.20 km a week, 5.3-7.1 km in a year |
| GEO and graveyard | week / year / 30 yr | 2.2e-8–1.1e-6 / 8.3e-6–4.5e-4 / 1.4e-3–0.081 m | as above | none public for debris (BELIEVED) | n/a | 0.34 km a week, 5.3-6.5 km in a year |

**Read across:**
- **Against TLE, density and area-to-mass errors:** binary64 is 10^7 or more below at a week (1.2e-5 m at most, against 0.2 km and up), 10^6 or more below at a year, and 10^4 or more below at 30 years (COMPUTED from the table).
- **Against a centimetre-level initial state:** 10^3 below at a week, and 2 to 100 times below at a year.
- **After 30 years** the pessimistic law reaches 0.08 to 0.9 m. By then a centimetre initial uncertainty has itself grown far past that, since any velocity error drifts along-track linearly (BELIEVED).

**What transfers:**
- IAS15's 36 steps an orbit in every regime (MEASURED), which is close to HORIZON's 51;
- the t^1.5 walk;
- ORBITS.md's finding that roundoff is worth an O(1) number of the format's own ulps of initial condition. As an equivalent da/a, the high law gives 4e-16 to 8e-14, against 1.5e-9 relative for a centimetre in LEO.

**What does not transfer:**
- **Dissipation.** With drag, any force error grows as t² along-track. The arithmetic's share is a relative 2^-53 in the drag term, worth 4e-7 m in a year at 400 km (COMPUTED). Model error is what grows.
- **Chaos.** In GNSS disposal orbits, any initial difference grows exponentially past the Lyapunov time ("strongly chaotic", DEBRIS-A [S18]; verifier-A found the source speaks of navigation satellites, so applying it to disposal orbits is BELIEVED). The arithmetic is amplified with everything else. Its ratio to a centimetre-level initial uncertainty is about 1e-7 at the start and grows only as the square root of time, to about 1e-4 after 30 years (COMPUTED from the equivalent da/a: 2.7e-14 × 26,560 km = 7e-7 m in MEO).
- **The real force model's roundoff.** It is not measured. 2,000 more operations an evaluation at relative 1e-16 is BELIEVED to stay within the high law's factor.

### 3.2 Logan's hypothesis: the dt sweep

On the preserved port (SHA-256 `9d5cb048...a048`, checked before every leg). Quarter day, LEO with J2, fixed steps, forward then back from the exact turn-around state. Unchanged copies of DEBRIS-A's scripts were used: `run_port_copy.py` checks their SHA-256 against `SHA256SUMS` and only redirects the executable.

| dt | steps | binary64 round trip | binary128 round trip | binary256 round trip | binary128 vs binary256 at the turn | binary64, 32 members: median / p90 |
|---|---|---|---|---|---|---|
| 100 s (DEBRIS-A) | 216 | 3.827e-8 m | 8.909e-22 | 8.909e-22 | 1.162e-27 | 3.0e-8 / 5.5e-8 |
| 50 s | 432 | 5.211e-8 | 3.644e-26 | **2.722e-26** | 3.935e-27 | 2.1e-8 / 5.2e-8 |
| 25 s | 864 | 6.318e-9 | 1.969e-26 | **8.309e-31** | 1.314e-27 | 1.5e-8 / 3.7e-8 |
| 12.5 s | 1,728 | (REBOUND, same steps: 1.451e-8) | 2.924e-26 | not run | | 1.9e-8 / 4.0e-8 |

(MEASURED. Port rates, wall-based: binary64 59 to 64 steps/s, binary128 17 to 27, binary256 4.9 to 6.6. The predictor-corrector passes a step fell with dt: binary256 went 18.0, 15.0, 12.8.)

- **Binary256 fell by 2^15.0 per halving, twice** (32,730 and 32,760). Both points sit inside the predicted band: 6.8e-27 to 1.1e-25 m at 50 s, and 5.2e-32 to 1.3e-29 m at 25 s. The central predictions were 2.1e-26 and 4.9e-31.
  - So 8.9e-22 m at 100 s was the method's discretization: IAS15's time asymmetry, a 15th-order error.
  - Two halvings bought 2^30.
- **Binary128 followed to 50 s, then stopped at 2.0 to 2.9e-26 m** and rose a little at 12.5 s, as predicted in shape. Its floor is 20 times the brief's "about 1e-27 m".
  - That figure is the one-way binary128-versus-binary256 difference at the turn (1.2 to 3.9e-27 m, MEASURED here too).
  - A round trip crosses twice as many steps, and its turn-around error is propagated back. So the round-trip floor is the larger quantity.
- **The positive control.** The single binary64 legs fell 8x from 50 s to 25 s, which the brief says an arithmetic floor must not do. So I measured the floor as a distribution:
  - 32 initial states, x shifted by 0 to 31 ulps, on REBOUND's IAS15. Member 0 reproduces the port's binary64 at 100, 50 and 25 s, an assertion in `fp64_ensemble.py`.
  - The median moves by a factor of 1.97 across an 8x change in dt: 2.999e-8, 2.124e-8, 1.521e-8 and 1.901e-8 m (`sweep\fp64_ensemble.log`). Over the first two halvings alone, binary256's truncation fell 2^30.
  - That 2x criterion was set after the single-leg control failed, and nothing asserts it. verifier-B's bootstrap puts the ratio of the 100 s and 25 s medians at 1.2 to 3.0 (95%), so a fall of 2 to 3x is not excluded. (Narrowed at the merge from "flat within 2x".)
  - The 25 s draw was a low one: the members range from 1.0e-9 to 4.8e-8.
  - So the control does what it is for: the binary64 floor does not fall like the method's 2^15 a halving. That it is flat is not shown, and a single draw cannot carry either reading, as HORIZON.md says.
- **Verdict on the hypothesis.** "No noticeable improvement past fp128" was true at dt = 100 s and is not a property of the formats.
  - Binary256 improves on binary128 as soon as the step makes the method's error smaller than binary128's floor: about 2e-26 m on this quarter day, crossed between 50 and 25 s.
  - "Designed for fp64" is right in a narrower sense. IAS15's order is fixed at 15, and its step control and convergence test are tuned for binary64. At 2^15 per halving, reaching binary256's own floor from 8.9e-22 m takes about 9.3 more halvings, roughly 600 times the steps (COMPUTED). The floor, about 1e-63 m, is BELIEVED by analogy: binary128's round-trip floor is about 20 ulps of position.
- **What an integrator built for wide formats does instead** (READ (WebFetch), the heyoka paper on ar5iv [B23]):
  - It chooses the Taylor order as p = ⌈−½ log ε + 1⌉ (Eq. 12). So "switching from double to quadruple precision requires doubling the Taylor order": p = 20 becomes p = 40, at about 4 times the work a step.
  - "A fixed-order method would instead need the timestep reduced by roughly 13×." My measured 2^15 a halving gives about 16x for the same 18 decades (COMPUTED), consistent with that.
  - The same paper reports quadruple precision "about two orders of magnitude slower", and on its outer-solar-system test 13 s at double against about 10,500 s at quadruple.
  - Read against the slope: a fixed 15th-order method pays steps for every decade; a variable-order method pays order, and the order grows only linearly in the number of digits.

### 3.3 What a wider format could still buy a custom model

| use | binary128 enough? | when binary256 | software price | tile price |
|---|---|---|---|---|
| **A ruler for the production propagator's numerical error.** Rerun sampled objects on the same steps (arithmetic) or at a tighter tolerance (truncation), and difference | yes. Its floor is about 19 decades under binary64's (sweep: 1e-27 m one-way against 1e-8 m) | only to rule binary128 itself | C with libquadmath: 177-214x a gravity evaluation (MEASURED). The port: binary128 at 0.28-0.33 of its binary64 rate, but its binary64 is 124-145x REBOUND's (DEBRIS-A, verifier-A, this sweep: 0.29-0.33). Sampling 1 object in 1,000 adds 0.2x to a catalogue | n/a |
| **Ensembles that measure the dynamics, in chaotic regimes** | yes. Debris ensembles perturb by physical amounts (km at TLE level, cm when precise), which are 10^6 to 10^12 times binary64's ulp of position (1.5e-9 m in LEO, 9e-9 m at GEO), so binary64 members already measure the dynamics (BELIEVED, from HORIZON's ulp-ensemble result) | only for ulp-scale Lyapunov work, which debris does not need | as above | the measured Kepler point-mass floor (rows below) |
| **Ill-conditioned orbit determination** (short arcs, drag and radiation-pressure parameters, normal equations squaring the condition number) | yes, or binary64 with QR or square-root information filters (BELIEVED, standard practice, not measured here) | not found | as above, for the solve only | n/a |
| **Covariance propagation** (along-track variance grows as t² while radial stays bounded, so the condition number grows) | yes, or binary64 Cholesky/UD forms (BELIEVED) | not found | as above | n/a |

**The tile.**
- **Both leads answered:** no IAS15 rate exists on the card for any force beyond point-mass gravity. "Format-blind" holds per beat, not per element (relayed answers, 16:04 and 16:09).
- **The measured Kepler ensembles**, which I READ myself in cft-rebound `docs\VALIDATION.md` at 9e9879f:
  - entry 45: binary256 at E = 512 ran 20 steps in 50.10 s on one tile, 204 system-steps a second, up from 88 at E = 64, and no wider binary256 run exists (cft-rebound's lead); binary128 ran 576 a second (COMPUTED);
  - entry 37: 562 a second at binary128 and 1,406 a second at binary64, at E = 4,096.
- **On that floor, the LEO catalogue for a year** (559 steps an object-day) is (COMPUTED):
  - 0.89 tile-years at binary256;
  - 0.32 at binary128;
  - 0.13 at binary64;
  - 2.9 core-years on the software backend's binary256 (62 a second at E = 1,024, HARDWARE.md).
  - Against that, 46-634 CPU-hours at binary64 on this CPU.
- A real force raises the tile's cost further. cft-rebound's lead BELIEVES cost tracks correctly rounded calls: J2 makes 11 an evaluation against gravity's 2.

## Q4. The product question, laid out for Logan

| | (a) single object, OD, hindcasts | (b) catalogue and conjunction screening | (c) population over decades |
|---|---|---|---|
| layers (Q1) | 1-10 | 1-7, 10, 11 | 12, with mean-element or semi-analytical propagation, forecast solar activity and launch traffic |
| cost (Q2) | tens of ms per object-day; an OD fit is many propagations (COMPUTED order) | 46-634 CPU-hours a year plus the density model and screening | deterministic, LEO at degree 20 for 30 years is about 2,600 CPU-hours a run (COMPUTED: 30.5 ms × 28,149 × 10,958), and Monte Carlo multiplies it |
| what validates it | SLR (ILRS) and GNSS-derived orbits, for tracked active and geodetic satellites; for debris, TLE histories (mean elements, ~1 km/day). Lasser et al. for the force layers | Space-Track CDMs (registration, BELIEVED); TLE histories; no public truth for most objects | none for the future; hindcasts of past decades against catalogue history |
| what exists | Orekit: numerical, DSST, SGP4; NRLMSISE-00 and JB2008; eclipses; batch least squares and Kalman filters; covariance by STM; Pc methods and CDMs (READ [B20]). GMAT | cascade: the SSN LEO population (count not stated; at least 3,685), J2, C22/S22 and exponential drag from BSTAR. 30 days ran in 64.27 s on 32 threads, projected 20 years in 4.35 h. No validation against observations is shown (READ [B22]). CARA tools; Orekit Pc | MASTER-8, which has historic and future populations behind a licence application (READ [B16]). The NASA SBM in open C++ (GPL-3.0). MOCAT-MC and DELTA (DEBRIS-A [S17]; verifier-A found only DELTA and MOCAT-MC named) |
| could a custom model do something they don't? | see the three candidates below | the same | not shown by anything I read |

**The three candidates, tested rather than assumed** (judgements BELIEVED).
1. **Bit-reproducible predictions that carry their own provenance**, from libcft's determinism, binary64 included.
   - **What exists:** the port at binary64 is bit-identical to REBOUND 5.1.1 with the same Python J2, at dt = 50 and 25 s (MEASURED). So binary64 determinism is achievable.
   - **What it demands:** the J2 expression's operation order alone moved the evaluation count from 12,410 to 12,452 (MEASURED). Reproducibility needs a fixed operation order across implementations, not just IEEE arithmetic.
   - **What would show it real:** the same prediction rerun on a second OS, compiler and machine (and on the card) gives identical bits, and a hash chain over inputs (EOP, ephemeris, gravity and density data, steps) reproduces.
   - **Whether it is novel:** a control would have to show that Orekit is *not* already reproducible across JVMs for the same version and data. I BELIEVE it may be, since Java arithmetic is IEEE and Hipparchus's FastMath is pure Java; this is unmeasured.
   - **Who needs it:** whoever must defend a prediction after the fact, such as screening providers, operators in a dispute and regulators. Not accuracy, which is limited at the kilometre level.
2. **Uncertainty carried with every prediction, with a refusal past the point where it can be bounded.**
   - **What would show it real:** covariance realism on hindcasts. Across many objects and horizons, the fraction of truth points inside the predicted k-sigma region matches χ². The refusals are right more often than the predictions they replace.
   - **What exists:** Orekit propagates covariance, and CDMs carry it (READ). A refusal policy was not found in anything I read.
   - **Who needs it:** collision probability is only as good as its covariance, so screening (BELIEVED).
   - **What it hinges on:** truth data, which for debris is mostly TLEs, whose own errors are about 1 km.
3. **GPU-scale or tile-scale ensembles.**
   - **What would show it real:** ensemble throughput with a real force model on the card, measured. No one has measured it (both leads).
   - **What the CPU already does:** at binary64 a 1,000-member Monte Carlo of one LEO object-day is about 30 CPU-seconds (COMPUTED from 30.5 ms).
   - **What the tile offers:** its advantage is binary256 width, which Q3 finds debris does not need. At binary64 the tile is slower than one CPU core (READ, HARDWARE.md).
   - **Who needs it:** Monte Carlo collision probability, breakup ensembles and environment Monte Carlo (BELIEVED).

**No recommendation** among build, adopt and hybrid: the evidence does not decide it. These would:
- an Orekit run held to Lasser et al.'s vectors and to a custom kernel on the same data, which is the hybrid's oracle;
- the cross-JVM reproducibility control above;
- a covariance-realism hindcast on SLR-tracked objects.

## Measurements and their commands

**Host:** i5-12400F, 12 threads; Windows 11; Git Bash. The host load was sampled at 2-99% through the session from other sessions' work, and is stated beside each timing.

**CPU used:** about 8 CPU-minutes in all, by child-process CPU time where measured (the sweep: 330.8 s, from GetProcessTimes), and otherwise wall time as the stand-in.

**Instruments:**
- Python 3.12 (Miniconda, `-I -B`), REBOUND 5.1.1, numpy 2.2.6, mpmath 1.3.0;
- gcc 16.1.0 x86_64-w64-mingw32 with libquadmath;
- the port at `cft-debris-ledger\tools\ias15_cft.exe`.

Every run's working copy is in `cft-debris-scratch\DEBRIS-B\`.
- The scripts, logs and port records are copied into `studies\debris-b\`. `MANIFEST.sha256` holds their hashes: run `sha256sum -c MANIFEST.sha256` there.
- `binaries.sha256` holds the hashes of the executables used, which are not copied: `q2bench.exe`, `q2bench_noforce.exe`, `gravdll.dll` and the port.
- The sweep's five DEBRIS-A script copies are not copied either; `run_port_copy.py` checked them against `SHA256SUMS` before every leg.

| measurement | command | output |
|---|---|---|
| Q3 dt sweep (50, 25 s: three formats; 12.5 s: binary128) | `bash sweep/run_sweep.sh` (each leg: `python -I -B run_port_copy.py <dir> --dt D --steps N --formats F`) | `sweep/dt*/sweep_dt*.log`, `.rec`, turn files |
| binary64 floor as a distribution | `python -I -B sweep/fp64_ensemble.py` | `fp64_ensemble.log` |
| Q2 kernels: build | `gcc -O2 -o q2bench.exe q2bench.c -lquadmath`; the same with `-DNO_FORCE` | |
| Q2 control 2 | `python -I -B q2/q2_check.py` | `q2_check.log` (40 pass). Two earlier failures are kept: `q2_check_v1_srp1_FAILED.log` (from `q2_check_v1.py`), and `q2_check_v2_frame_FAILED.log` (from `q2_check.py` before its frame-series edit, a version not kept separately) |
| Q2 timings and control 1 | `python -I -B q2/q2_time.py` | `q2_time.log` |
| operation counts | `q2bench.exe count <kernel> <param>` | in the table above |
| evaluations per object-day (J2) | `python -I -B q2/ias15_evals.py`; `ias15_evals_order.py` | `ias15_evals.log`, `ias15_evals_order.log` |
| evaluations with the SH field; MEO, GEO; the C floor | `gcc -O2 -shared -o gravdll.dll gravdll.c`; `python -I -B q2/shcount/ias15_evals_sh.py`; `ias15_evals_sh_meogeo.py` | `ias15_evals_sh*.log` |
| physical uncertainties | `python -I -B q3/q3_physics.py` | `q3_physics.log` |
| every COMPUTED table | `python -I -B q3/tables.py` | `tables.log` |

## What this study could not settle

- **The cost of NRLMSISE-00 and JB2008.** It is unread and unmeasured. Since it can dominate LEO, it is left as a parameter with a break-even of 1.85 µs.
- **The sizes of several test-vector sets:**
  - Lasser et al. (FTP);
  - NRLMSIS 2.1 (server reset);
  - JB2008 (403);
  - NGA's EGM2008 files (unreachable);
  - CARA DataFiles (Git LFS);
  - Orekit's jars and data (bot protection).
- **Licences not stated on the pages read:** JPL ephemerides, IERS EOP, Vallado's code, GFZ's indices and GMAT's.
- **No published test vectors were found** for drag, radiation pressure with shadow, orbit determination, or the breakup model.
- **The real force model's roundoff** (as opposed to J2's), and how IAS15's pass count responds to a real gravity field rather than a Kaula-rule synthetic one (BELIEVED similar).
- **Any tile rate beyond point mass** (none exists).
- **Whether Orekit is bit-reproducible across platforms.**
- **What I did not do:**
  - run Orekit, GMAT, heyoka or any density model;
  - read [S21]'s PDF (approved, but my work does not rest on it);
  - ask for any download.

## Sources

READ via WebFetch unless marked; fetched 2026-11-12.
- [B1] IERS Conventions (2010), chapter 5: https://iers-conventions.obspm.fr/chapter5.php; Tables 5.2a, 5.2b and 5.2d headers: https://iers-conventions.obspm.fr/content/chapter5/additional_info/tab5.2a.txt (likewise 5.2b, 5.2d).
- [B2] SOFA: https://www.iausofa.org/, https://www.iausofa.org/2023-10-11c, https://www.iausofa.org/terms-and-conditions
- [B3] ERFA: https://github.com/liberfa/erfa
- [B4] IERS EOP C04 listing: https://hpiers.obspm.fr/iers/eop/eopc04/; Bulletin C: https://hpiers.obspm.fr/iers/bul/bulc/
- [B5] CelesTrak space data: https://celestrak.org/SpaceData/
- [B6] GFZ Kp: https://kp.gfz.de/en/data
- [B7] ICGEM: https://icgem.gfz.de/tom_longtime
- [B8] JPL: https://ssd.jpl.nasa.gov/ftp/eph/planets/ascii/de440/; https://ssd.jpl.nasa.gov/planets/eph_export.html; README.txt, the file WebFetch saved (read with Logan's approval, lead.md 16:38).
- [B9] Lasser et al. 2020, Adv. Geosci. 55, 1-11: https://adgeo.copernicus.org/articles/55/1/2020/; data: ftp://ftp.tugraz.at/outgoing/ITSG/COST-G/softwareComparison/ (not fetched).
- [B10] NRLMSIS 2.1 (search excerpts; https://map.nrl.navy.mil/map/pub/nrl/NRLMSIS/NRLMSIS2.1/ gave ECONNRESET); pymsis: https://github.com/SWxTREC/pymsis
- [B11] JB2008: https://ccmc.gsfc.nasa.gov/models/JB2008~2008; https://sol.spacenvironment.net/jb2008/code.html (403; search excerpt).
- [B12] https://discourse.julialang.org/t/jacchia-roberts-1971-atmospheric-model-is-now-available-in-satellitetoolbox-jl/16758
- [B13] Vallado et al. 2006: https://celestrak.org/publications/AIAA/2006-6753/; python-sgp4: https://pypi.org/project/sgp4/
- [B14] CelesTrak GP formats: https://celestrak.org/NORAD/documentation/gp-data-formats.php
- [B15] Levit and Marshall 2011, abstract: https://arxiv.org/abs/1002.2277 ("100 meters per day", "approximately a 10-fold improvement" over SGP4; ~1 km/day for SGP4 is my inference).
- [B16] DISCOS statistics: https://sdup.esoc.esa.int/discosweb/statistics/; SDUP: https://sdup.esoc.esa.int/
- [B17] GCAT: https://planet4589.org/space/gcat/
- [B18] NASA CARA: https://github.com/nasa/CARA_Analysis_Tools; CCSDS 508.0-B-1 (search excerpt): https://ccsds.org/publications/bluebooks/entry/3064/
- [B19] https://github.com/esa/NASA-breakup-model-cpp
- [B20] Orekit: https://raw.githubusercontent.com/CS-SI/Orekit/develop/src/site/markdown/index.md; https://raw.githubusercontent.com/CS-SI/Orekit/develop/src/main/java/org/orekit/frames/AbstractFrames.java; https://github.com/CS-SI/Orekit/tags; https://raw.githubusercontent.com/CS-SI/Orekit/13.1.9/pom.xml; https://raw.githubusercontent.com/CS-SI/Orekit/develop/pom.xml
- [B21] GMAT R2025a (search excerpt): https://www.sourceforge.net/projects/gmat/files/GMAT/GMAT-R2025a
- [B22] cascade example: https://esa.github.io/cascade/examples/20yearsofLEO_coll.html
- [B23] heyoka: https://ar5iv.labs.arxiv.org/html/2105.00800 (sections 2.2, 2.3, 3.2, 4.9); https://bluescarni.github.io/heyoka/tut_adaptive.html; https://bluescarni.github.io/heyoka.py/notebooks/arbitrary_precision.html
- [B24] CDDIS access: https://www.earthdata.nasa.gov/centers/cddis-daac/archive-access
- [B25] IGS products (search excerpt; the page truncated): https://www.igs.org/products
- [B26] Density-model accuracy, Bruinsma et al. (search excerpt; the page returned 403): https://www.swsc-journal.org/articles/swsc/abs/2017/01/swsc160034/swsc160034.html. NRLMSISE-00 "bias of about 20%", JB2008 and DTM2013 "10–15%" amplitude differences, against GOCE.
- [B27] Shadow-model validation, Li et al., UCL (search excerpt only): https://discovery-pp.ucl.ac.uk/10059978/
- **Local, READ:**
  - cft-rebound `docs\HORIZON.md`, `docs\HARDWARE.md` lines 177-230 and 364-368, and `docs\VALIDATION.md` entries 37 and 45 (at 9e9879f);
  - cft-fp256 `docs\ORBITS.md`, "The fp64-versus-fp256 result";
  - DEBRIS-A and its records;
  - the relayed answers in `cft-debris-ledger\relayed\`.

## Narrowed at the merge, and notes (the lead, 2026-11-12)

verifier-B re-ran from clean: the sweep's 50 s and 25 s legs, the binary64 ensemble at four step sizes, Q2's timings and both controls, the evaluation counts, the tables and the physics. Every figure it re-ran reproduced exactly, except Q2's timings, which reproduced within 12% (`studies\DEBRIS-B-verifier-B-report.md`). It found no wrong answer that would send the study back. Under Logan's rule, sentences that claimed too much were narrowed at the merge instead. The text as reported has SHA-256 `014d75ff8d19ad5a9f4e914db096d4579b9b42b079618d3047f7aa1dd027fb8f` and is kept at `cft-debris-ledger\filed\DEBRIS-B-custom-model.as-reported.md`.

**Narrowed**, each marked in the text:
1. **Short answer 2:** the 1.2 to 11 µs range is LEO's. MEO and GEO cost 1.1 µs.
2. **Short answer 2:** MEO plus GEO is 0.31 CPU-hours a year, not "under 0.3" (`q3\tables.log`: 0.23 + 0.08).
3. **Short answer 3:** "not the limit anywhere in debris prediction" became "in any regime tabulated here", and those regimes are near-circular only. The caveat on chaos now stands in the short answer.
4. **Short answer 3:** after 30 years the pessimistic arithmetic exceeds a centimetre initial state. That the centimetre has itself grown past it by then is BELIEVED.
5. **Short answer 5:** "binary128 is enough" rests on one measured floor and on BELIEVED judgements.
6. **§3.2:** the positive control was "flat within 2x". That criterion was set after the single-leg control failed, and nothing asserts it. It now reads that the median moves by 1.97, and so does not fall like 2^15 a halving.
7. **§3.1:** the "low" arithmetic-error column comes from a single draw, so it is not a lower bound.
8. **Q1, row 6:** Lasser et al.'s page not mentioning drag and radiation pressure is not the same as excluding them.

**The narrowing was checked** by merge-check (on Haiku). Six passages held. It found two problems, and both were fixed in its own terms:
- the chaos sentence in short answer 3 had dropped the BELIEVED label it carries in §3.1;
- "every figure it re-ran reproduced" overstated Q2's timings, which reproduced within 12%.

The two fixes were not checked again.

**Notes** from verifier-B; these sentences were not narrowed:
- **Deep penumbra:** an mpmath check (8.8e-25) justifies the assertion's change of denominator. The change still loosens the tolerance, to 1e-8 against a measured 7.2e-10.
- **The frame series:** its "kernel's own arguments" assertion reuses the kernel's Horner order. The "exact arguments" check is the independent one.
- **No-force ratios:** for most gravity rows the no-force loop is empty, so the 10x ratio can hardly fail there. The force build's own time shows the work was done.
- **The integrator's 233 ns share** divides by the J2 run's evaluations, because the point-mass run's count was never measured. It is labelled BELIEVED.
- **The IERS term counts** could not be re-read under the HTML-only ruling. They are internally consistent: the check asserts 2,941.
- **heyoka's "13 s against 10,500 s"** was not re-checked.
- **DEBRIS-B's report** (`DEBRIS-B-report.md`) is filed verbatim, so it keeps its "under 0.3".
- **A slip in verifier-B's report:** it gives the medians' max/min as 1.999. From `sweep\fp64_ensemble.log` it is 1.97 (2.999e-8 over 1.521e-8).
