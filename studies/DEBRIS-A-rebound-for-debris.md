# DEBRIS-A: REBOUND for long-term, high-density space-debris prediction

Study parcel DEBRIS-A, for cft-rebound's lead, 2026-11-12. This is a study only. Nothing was built or committed, and no repository was changed. Scripts, logs and records are in `studies/debris-a/` beside this file.

> "determine if rebound (and if so which integrator) would work best for long term high density space debris prediction, ideally capable of running in either direction to prove itself against historical data and cycle at a divergence from real data." (Logan)

Every claim carries a label:
- **MEASURED**: I ran it; the command is in section 7.
- **COMPUTED**: arithmetic from stated inputs.
- **READ**: a cited source. [S1] is the pinned REBOUND at bdfda4bd; [S2] is this repository.
- **BELIEVED**: my judgement.

## Short answer

- **REBOUND is a sound integrator and the wrong platform.**
  - Its IAS15 handles the forces debris physics brings, drag and a moving Moon, and runs in either direction, at no measurable cost in accuracy (MEASURED).
    - With J2 it lands within 1.4e-7 m of a binary128 reference after a day.
    - With drag or the Moon added, it lands within 1e-7 m of its reference.
    - Every round trip comes home to within 1.1e-6 m.
  - But the integrator is the small part of a debris predictor. REBOUND has no atmosphere, no gravity field past REBOUNDx's J2 and J4, no frames, Earth orientation or time scales, no TLE handling and no orbit determination (READ [S1][S3]).
  - Its state transition matrix silently leaves out every force a user adds: one column was 44% wrong after one day of LEO with J2 (MEASURED).
- **Which integrator: IAS15, in every regime.** The symplectic family's advantages do not survive a debris force model as REBOUND implements them.
  - Drag takes SABA(10,6,4) from 1.5 µm a day to 1.6 m. It takes JANUS from a bit-exact return to an 8 m one (MEASURED).
  - SABA, EOS and JANUS evaluate every stage's force at the step's start time (READ [S1]). With a time-dependent Moon and Sun, SABA's one-year round trip misses by 9 to 73 km (MEASURED).
- **cft-rebound is the wrong tool here.** What it offers is precision past binary64 and exact reproducibility. Debris prediction is limited by the force model, not by arithmetic.
  - A 20% density error moves a 400 km object 5.0 km in one day. Binary64 and binary128 differ by 1.2e-8 m over the same day. That is a factor of 4e11 (MEASURED).
  - It refuses variational particles (READ [S2]). Its standalone forces are a point mass plus J2 and J4. At binary64 it ran 145 times slower than REBOUND on the same steps (MEASURED).
- **"Either direction" is easy, and proves less than it sounds.** Every integrator here runs backward. A round trip shows that an integrator inverts itself, not that its model matches the sky. Proof against history is a hindcast: fit to past observations, propagate, and compare with independent truth.
- **"Cycle at a divergence" is orbit determination.** REBOUND supplies only the derivative engine, and only for its own gravity. The port supplies neither, though its ensembles suit a filter that needs no derivatives.

## Recommendation (BELIEVED, from the evidence below)

1. **Do not build debris prediction on cft-rebound, or on REBOUND as the platform.**
2. **For the long-term, high-density question as asked, start from ESA's `cascade`** (Biscani and Izzo, MPL-2.0, built on heyoka) [S9].
   - It was made for this: propagate a debris population and detect every conjunction and collision, by Taylor expansions.
   - Its published example propagates the US-tracked LEO population with J2, C22/S22 and drag from each object's BSTAR. 30 days took 64 s on 32 threads, which projects 20 years to 4.3 h (READ).
3. **For individual objects, proof against history and the re-fit cycle, use Orekit** (Apache-2.0) [S10].
   - Propagators: numerical, DSST and SGP4/SDP4.
   - Forces: NRLMSISE-00, DTM2000, JB2008 and Harris-Priester atmospheres; radiation pressure with eclipses; third bodies; solid tides.
   - Frames and time: TEME and every ITRF, with Earth orientation parameters.
   - Estimation: batch least squares, unscented and semi-analytical Kalman filters, TLE generation by fixed point or least squares, Jacobians and covariance propagation (READ).
   - It is the only candidate here that answers questions 3 and 4 off the shelf.
4. **For statistical evolution over decades to centuries,** use the environment models or semi-analytical propagation, not a deterministic integrator per object.
   - Environment models: ESA's MASTER and DELTA, NASA's LEGEND, MIT's MOCAT-MC [S17].
   - Semi-analytical: DSST or STELA. THALASSA's regularised formulations for GTO and HEO matched STELA's speed on GTO and were ten times faster on HEO [S11].
5. **If a REBOUND component is wanted anyway,** use IAS15 with C force callbacks and hand-written Jacobians.
   - ASSIST shows that path working for heliocentric small bodies (READ [S15]).
   - For a debris-flavoured version of the GPU ring, the GEO graveyard is the regime the ring's design fits (section 5).

## 1. Fit

### What REBOUND brings

- **IAS15** (READ [S1] `integrator_ias15.c:55-69`):
  - adaptive and 15th order;
  - "can handle arbitrary forces (including those who are velocity dependent)";
  - "in most cases accurate down to machine precision";
  - it integrates variational equations.
- **Where user forces enter** (READ [S1]):
  - `additional_forces` runs after gravity at every force evaluation (`simulation.c:689-691`).
  - Velocities are predicted at the nodes for a velocity-dependent force (`integrator_ias15.c:434`).
- **Test particles** through `N_active`.
- **Backward integration is native.** `integrate(tmax)` turns the step's sign toward `tmax` (`simulation.c:378-381`).
- **Variational equations** at first and second order [S6], Simulationarchive, and Python.
- **Cost in C, with no Python callback** (point-mass LEO, 30 days, host load 6-20%, MEASURED):

  | integrator | ms per object-day |
  |---|---|
  | BS at 1e-12 | 0.8 |
  | LEAPFROG o2 at 10 s | 1.6 |
  | IAS15 at 1e-9 | 2.7 |
  | WHFast at 10 s | 4.0 |
  | JANUS o6 at 10 s | 5.6 |

### What it lacks, and what the lack costs

| a debris predictor needs | REBOUND at the pin [S1] | REBOUNDx, not pinned [S3] | the lack |
|---|---|---|---|
| gravity past J2 | nothing | J2 and J4 only, any spin axis | Tesserals must be written, with Earth rotation. C22/S22 drives GEO longitude drift. Earth's J3 (-2.5e-6) exceeds its J4 (-1.6e-6) (BELIEVED values). |
| atmospheric drag | nothing | nothing (its "gas" effects model disks) | An empirical atmosphere, its solar and geomagnetic drivers, geodetic altitude, the Sun's position |
| radiation pressure | nothing | pressure and Poynting-Robertson drag from a source body, a β per particle; no shadow is documented | A shadow model, and an area-to-mass ratio per object |
| Sun and Moon | as integrated bodies | none | An ephemeris binding such as DE440, or N-body bodies |
| frames, Earth orientation, time scales | an arbitrary inertial frame and a scalar `t` | none | GCRF, ITRF and TEME; UTC, TT and UT1 |
| TLEs | nothing | nothing | SGP4, and TEME conversions |
| orbit determination | variational equations only | none documented | Measurement models, an estimator, covariance |
| a step per object | one step for the whole simulation | none | Next table |

**A GEO object pays LEO's step count** (MEASURED, IAS15 over one day):

| test particle | steps a day alone | steps a day sharing one simulation with the other three |
|---|---|---|
| LEO | 559 | 572 |
| MEO | 74 | 572 |
| GTO | 172 | 572 |
| GEO | 39 | 572 |

**The state transition matrix** (MEASURED, `var_check.py`). The test is one column (d final position / d initial x), after one day of LEO, from REBOUND's own variational particle and from a central finite difference:

| case | relative mismatch |
|---|---|
| point mass only (the control) | 1.4e-9 |
| with the J2 callback as written | 0.44 |
| with J2's Jacobian added to the variational particle inside the callback | 8.0e-10 |

- REBOUND linearises its own gravity (`reb_gravity_basic_calculate_acceleration_var`) and nothing else (READ [S1] `simulation.c:676-691`).
- A force of relative size 1e-3, left out of the linearisation, made the column 44% wrong. Leaving the force out does not give an error of 0.1%.
  - BELIEVED mechanism: Kepler's along-track drift is a degenerate (Jordan) mode, and perturbing it splits it as the square root of the perturbation.
- So every force needs its own Jacobian, written by hand.
  - ASSIST did that for every one of its terms and verified them term by term against JPL's integrator (READ [S15]).
  - heyoka derives variational equations automatically at any order (READ [S8]).
  - Orekit computes Jacobians and propagates covariance (READ [S10]).

### The port, cft-rebound

- **Precision is not the binding constraint** (MEASURED, 400 km, B = 0.022 m²/kg, exponential atmosphere):
  - drag on against drag off: 24.9 km in one day;
  - a 20% denser atmosphere: 5.0 km in one day;
  - binary64 against binary128 on identical steps: 1.2e-8 m.
  - Thermospheric models have long carried 15-20% one-sigma density errors (READ, search excerpt of the JB2008 paper [S20]), and errors grow much larger in storms [S20].
- **Cost** (MEASURED, one day, 864 fixed steps):
  - REBOUND 5.1.1 with a Python J2 callback: 0.086 s.
  - The port at binary64: 12.5 s, 145 times slower.
  - Binary128 runs at a third of binary64's rate, and binary256 at a tenth.
- **Refusals** (READ [S2] README):
  - It refuses variational particles, so it has no matrix for orbit determination.
  - The standalone program's forces are a point mass plus P1's zonal term.
  - The drop-in accepts `additional_forces`, evaluated at binary64 even in a binary256 run.
- **What it does have suits a catalogue in shape (BELIEVED):** test particles, ensembles with a step per system, recorded and replayed schedules, and `compare_run.py`.

**Verdict on fit:** REBOUND is a sound core integrator inside someone else's astrodynamics layer, and a poor platform on its own. cft-rebound is the wrong tool for debris.

## 2. Which integrator, by regime

**The LEO tests** (MEASURED, `leo_roundtrip.py`):
- The orbit: 400 km, e = 0.001, i = 51.6°, about a point-mass Earth with J2 as a Python force, for one day.
- The forward error is against IAS15 at a fixed 20 s step, which agrees with the port's binary128 run to 4.4e-9 m.
- The round trip is one day forward, then back to t = 0.
- "Force evaluations" is a cost measure that does not depend on the host.

| integrator | J2: error a day | J2: round trip | J2+drag: error | J2+drag: round trip | force evaluations a day |
|---|---|---|---|---|---|
| IAS15, ε 1e-9 | 1.4e-7 m | 2.4e-7 m | 7.4e-8 m | 7.1e-7 m | 12,452 (559 steps) |
| IAS15, ε 1e-6 | 3.0e-7 m | 6.8e-8 m | 2.0e-7 m | 9.3e-7 m | 7,686 (210 steps) |
| BS, 1e-12 | 3.3e-5 m | 5.4e-5 m | 3.8e-5 m | 3.8e-5 m | 13,692 |
| BS, 1e-8 (default) | 0.57 m | 1.09 m | 1.3 m | 0.61 m | 8,121 |
| SABA(10,6,4), 30 s | 1.5e-6 m | 1.3e-5 m | **1.6 m** | **10.5 m** | 23,040 |
| JANUS o6, 10 s | 6.2e-6 m | **0, bit-exact** | **4.6 m** | **8.2 m, not bit-exact** | 77,760 |
| LEAPFROG o6, 10 s | 1.7e-5 m | 3.0e-5 m | 6.4 m | 11.4 m | 77,760 |
| WHFast, 10 s | 4.1 m | 6.7e-6 m | 4.1 m | 4.9e-3 m | 8,640 |
| WHFast, corrector 11, 30 s | 1.1 m | 7.3e-6 m | 1.8 m | 1.4e-2 m | 118,080 |
| TRACE or MERCURIUS, 30 s (identical) | 70 m | 1.5e-6 m | 70 m | 7.4e-3 m | 5,760 |
| LEAPFROG o2, 10 s | 28 km | 1.5e-5 m | 28 km | 3.8 m | 8,640 |
| EOS LF/LF n = 2, 30 s | 16 km | 7.7e-6 m | 16 km | 1.5e-2 m | 2,880 |

**Wall time per forward day, with the Python callback** (MEASURED, host load 6-20%):
- 0.02 to 0.24 s for every row except three;
- 0.49 to 0.58 s for JANUS o6 and LEAPFROG o6, both at 10 s;
- 0.78 to 0.85 s for WHFast with corrector 11.

The force evaluations are the cost to carry to a real force model.

**With an analytic, time-dependent Moon** (MEASURED):
- IAS15: 9.2e-8 m error, and a 1.1e-6 m round trip.
- JANUS o6 at 10 s: 8.6e-4 m error, and a round trip of 8.5e-4 m that is **not bit-exact**.
- LEAPFROG o2 still returns to 1.2e-6 m.

**MEO and GEO** (MEASURED, `meo_geo.py`):
- One year with J2, an analytic circular Moon and Sun, and cannonball radiation pressure with no shadow.
- The reference is IAS15 at a fixed 300 s step, in binary64 only.

| integrator | MEO: error a year | MEO: round trip | GEO: error a year | GEO: round trip | force evaluations, MEO / GEO |
|---|---|---|---|---|---|
| IAS15, ε 1e-9 | 1.0e-3 m | 3.7e-5 m | 1.2e-4 m | 3.7e-4 m | 581,683 / 289,401 |
| LEAPFROG o6, 600 s | 415 m | 5.0e-3 m | 5.0 m | 1.4e-2 m | 473,364 |
| SABA(10,6,4), 1800 s | 563 m | **9.1 km** | 131 m | **36.7 km** | 140,256 |
| SABA(10,6,4), 3600 s | 245 m | **18.3 km** | 1.8 km | **73.4 km** | 70,128 |
| WHFast, 600 s | 11.2 km | 6.5e-3 m | 1.6 km | 4.5e-3 m | 52,596 |
| WHFast, 1800 s | 102 km | 3.6e-4 m | 14.5 km | 6.9e-4 m | 17,532 |

**Why SABA fails a round trip** (READ [S1]):
- SABA, EOS and JANUS advance `r->t` once, at the end of the step (`integrator_saba.c:351`, `integrator_eos.c:631`, `integrator_janus.c:270`). Every stage therefore sees the start time.
- That is first order in any explicit time dependence, and it is not symmetric: a forward step reads t0, and the step back from t0+dt reads t0+dt.
- WHFast kicks at mid-step (`integrator_whfast.c:1187,1266`), and LEAPFROG advances time in each drift (`integrator_leapfrog.c:81`). Both come home.

**The verdicts.**
- **LEO** (drag and radiation pressure; non-conservative and velocity-dependent): **IAS15.** BS at a tight tolerance is the alternative, at similar force-evaluation cost and about 240 times less accuracy (3.3e-5 m against 1.4e-7 m). Every splitting method loses its order or its symmetry with drag (table). The Kepler splits also carry metres to kilometres of J2 error a day.
- **MEO, GEO and graveyard** (nearly conservative but time-dependent): **IAS15** again.
  - SABA's order, which was the reason to want it, does not survive REBOUND's handling of time.
  - WHFast costs a tenth as many force evaluations for kilometres of error a year. That is acceptable only where radiation-pressure parameters are worse than that (BELIEVED).
  - GNSS disposal orbits are "strongly chaotic" and "unpredictable on decadal timescales" (READ, excerpt [S18]). There, deterministic prediction ends whatever the integrator, and binary64 ensembles are the tool (READ [S2] docs/HORIZON.md).
- **The rest:**
  - WHFast512 takes at most 9 particles [S1].
  - SEI is for the shearing sheet [S1].
  - MERCURIUS and TRACE switch integrators for close encounters between massive bodies, and an Earth catalogue has none. They behaved as one integrator here (table).
  - JANUS's default lattice overflows its `int64` at LEO in km: 6,778 / 1e-16 = 6.8e19 > 2^63 (COMPUTED). I set `scale_pos` to 1e-14 and `scale_vel` to 1e-17.
- **Variational support at the pin** (READ [S1]):

  | integrator | variational particles |
  |---|---|
  | IAS15 | first and second order |
  | BS | first and second order |
  | WHFast | first order |
  | SABA, WHFast512 | refused with an error |
  | EOS ("no longer supported since REBOUND version 5"), MERCURIUS, TRACE | warning only |
  | JANUS, LEAPFROG | silently never advanced |

## 3. Running in either direction

### Physical reversibility

Drag dissipates energy, but the equations of motion remain a smooth, deterministic ODE with a unique inverse flow.

**What "backward" means.** Integrate the same equations with t decreasing. The object climbs and gains energy. Nothing in the mathematics forbids it: IAS15 with drag came home to 7.1e-7 m (MEASURED).

**What limits it:**
- **Model error grows in both directions.** A density or ballistic-coefficient error grows along-track roughly as t² (MEASURED above: 5 km a day for 20% density).
- **Events the model lacks cannot be integrated through:** manoeuvres, fragmentations, attitude changes.
- **Conditioning near re-entry.** The phase-space contraction rate is div = -2ρB|v| (COMPUTED, inputs from Vallado's exponential table as recalled, BELIEVED):

  | altitude | e-folding time of the contraction |
  |---|---|
  | 400 km | 25 years |
  | 200 km | 121 days |
  | 150 km | 16 days |

  So a backward run started near re-entry amplifies its errors. Elsewhere in LEO it is well conditioned.
- **Historical space weather is measured; forecast space weather is not.** A backward hindcast can use measured F10.7 and Ap, while a forecast must predict them. Hindcasts therefore overstate forecast skill (BELIEVED).

### Numerical reversibility

**REBOUND, LEO** (MEASURED): round trips of 6.8e-8 to 1.1e-6 m for IAS15, with or without drag or a moving Moon, and millimetres for WHFast with drag (section 2).

**The port, LEO with J2, 100 s fixed steps** (MEASURED, `port_roundtrip.py`):

| format | quarter day: round trip | one day: round trip | rate (steps a second) |
|---|---|---|---|
| binary64 | 3.8e-8 m | 5.8e-8 m | 57-69 |
| binary128 | 8.9e-22 m | 1.3e-20 m | 18-22 |
| binary256 | 8.9e-22 m | not run | 5.5 |

- Binary128 and binary256 agree to the digit. That figure is IAS15's own time asymmetry: its Radau nodes include the start of a step and not the end (READ [S2] docs/HORIZON.md).
- The port at binary64 is **bit-identical to REBOUND 5.1.1's IAS15 with the same J2 written in Python**, at the turn and on return, over both spans.
- The port's command line takes a negative `--dt`. `tools/reversal.py` relies on that, and so did this run.

### Bitwise reversibility (JANUS)

- JANUS's integer lattice returned bit for bit with J2 at 10 s and at 30 s (MEASURED).
- It lost that with drag (an 8.2 m return) and with a time-dependent Moon (8.5e-4 m) (MEASURED).
  - A velocity-dependent kick, or a force evaluated at the step's start time, breaks the exact inverse.
  - Its paper claims exact time symmetry for Hamiltonian systems (READ [S7]).
- Neither force set is optional for debris, so bitwise reversibility is unavailable exactly where it would be wanted. It would not be needed even if it were available: data errors are kilometres (BELIEVED).

### What a backward run can and cannot prove

**It can:**
- Show that propagator and force model reproduce an object's observed past over a span, as a residual history against independent truth.
- Date a breakup and find its parent, by propagating fragments back until their orbits converge in inclination and node or in mutual distance. That is an established use. Its accuracy rests on each fragment's ballistic coefficient (READ, excerpts [S19]).

**It cannot:**
- Show that forecasts are good, because forecast drivers are predicted.
- Beat the accuracy of its comparison data.
- Validate anything through its own round trip. A return to 1e-7 m says that the integrator inverts itself, and nothing about the model. It is this repository's "bit-identity is not validity" in another form.

### The comparison data, and what else is needed

**TLEs are SGP4 mean elements, not osculating states.**
- Line 2 "consists primarily of mean elements calculated using the SGP4/SDP4 orbital model" (READ [S12]).
- SGP4's output is in TEME, whose relation to standard frames was never officially released (READ [S12]).
- Comparing a numerical propagator with a TLE history therefore takes one of two routes:
  - evaluate SGP4 at each TLE's epoch and compare states in a common frame; or
  - fit a numerical orbit to TLE-derived pseudo-observations. Levit and Marshall did this and reached about 100 m a day of predicted range error, about ten times better than SGP4. Below about a day their errors were dominated by the TLEs' own bias (READ [S13]).
- TLE error is commonly put at about 1 km at epoch, growing 1-3 km a day in LEO (READ, secondary [S21]).

**Better truth:**
- laser ranging (ILRS) for the objects it tracks [S13];
- operators' own ephemerides;
- GNSS-tracked satellites;
- radar. The SP catalogue itself is not public.

**Also needed:**
- Earth orientation parameters and leap seconds;
- historical F10.7 and Ap;
- an atmosphere model;
- object masses and areas (ESA DISCOS);
- an Earth gravity model;
- DE440 for the Sun and Moon.

## 4. "Cycle at a divergence from real data"

**What the cycle is.** Propagate. Test each new observation against the prediction, against its covariance rather than a fixed distance. On failure, re-fit on recent data and restart.
- That is orbit determination: a batch least-squares differential correction, or a filter with an innovation test.
- **Operational practice (READ [S14]):**
  - The US special-perturbations catalogue has used an eighth-order Gauss-Jackson integrator since the 1960s.
  - The NRC's 2012 review lists J70 plus HASDM for the atmosphere, and weighted batch least squares with drag and radiation-pressure segmentation (search excerpt).
  - HASDM's dynamic calibration is itself data assimilation: one weighted differential correction of the density model across all its calibration satellites.

**What REBOUND offers.**
- Variational equations for IAS15 and BS (first and second order) and WHFast (first order), which make a state transition matrix possible.
- But only for its own gravity. Every added force needs a hand-written Jacobian (MEASURED, section 1).
- None of the rest: measurement models, an estimator, process noise, parameter estimation for drag or radiation-pressure coefficients, data ingestion.

**What the port offers and refuses.**
- **Refuses** variational particles (READ [S2]), so no matrix exists, and Gauss-Newton fitting would mean finite differences.
- **Ensembles: the useful piece** (BELIEVED). E independent systems, each on its own adaptive step and gated bit for bit against its members, are the shape of an unscented filter's 13 sigma points or of an ensemble Kalman filter. The update step would live outside, in Python, between calls.
- **Test particles** (`active n`) make each object one massless body.
- **`--dt-out`, `--attempts-out` and `--dt-file`** make any cycle exactly replayable.
- **`compare_run.py` holds engine against engine, not model against data.** It reruns a record's sampled members and reports bit-identity (READ [S2]). That makes it the tool for holding a GPU run to the CPU. It is not a residual against observations.
- **`divergence.py` measures members against member 0** (READ [S2]). That is ensemble spread, the uncertainty-growth half of a filter, with nothing to compare it to observations.
- **binary128 and binary256 add nothing to this error budget** (MEASURED, section 1).

## 5. How far the ring design carries over

**What carries over.**
- **Massless objects in a field:** `active n` with Earth, Moon and Sun active.
  - A 64-body wave would hold 61 objects and 186 pairs a force evaluation, against the ring's 420 (COMPUTED: 61×3 + 3).
- **Waves sorted so a wave shares one step need,** by perigee and period instead of radius.
  - This matters: shared steps cost a GEO object 15 times its own (MEASURED, section 1).
- **J2 and J4 about z,** with the inclined-orbit trap ROUND4 names.
- **P3's replay of one object out of its wave,** and **P4's sampled comparison.** Both carry over as they are, for holding a GPU run to the CPU.

**What does not carry over.**

| missing piece | why it matters |
|---|---|
| **Drag** | Velocity-dependent. The standalone program has no velocity-dependent path, and a wide drag term would need the node velocity predictor plus `exp`. It needs a ballistic coefficient per object, and the problem format has no per-body parameter. Without drag there is no LEO, which is where the debris are. |
| **Radiation pressure** | Needs the Sun's direction, a shadow (a discontinuity) and an area-to-mass ratio per object. |
| **Tesseral harmonics** | An Earth-fixed field, so Earth rotation and UT1. `zonal` is axisymmetric by construction. |
| **J3** | Absent from the zonal line, and larger than J4 for Earth (BELIEVED values: J3 = -2.53e-6, J4 = -1.62e-6). |
| **Frames and time** | A fixed z axis is wrong by the pole's motion: 50.3″/yr × sin 23.44° = 20″/yr, 9.7e-5 rad a year (COMPUTED). That is fine for days and not for decades. TLE epochs are UTC and their frame is TEME. |

**A debris-flavoured ring (BELIEVED).**
- The GEO graveyard is the regime the ring's design fits: near-circular, near-equatorial and nearly conservative, with Earth's J2 and J4 and the Moon and Sun as massive bodies.
- It needs radiation pressure (with a β per particle and no shadow, it is conservative) to be credible.
- It needs C22/S22 for objects near GEO itself.

## 6. Found in passing, for the lead

1. **REBOUNDx's harmonics are not in the order `src/ias15_zonal.inc` says it recalls** (READ [S4]).
   - The port's stated order is REBOUNDx's as of 5406ae5 (2020-04-13): `costheta2 = dz*dz/r2`, `prefac = 3.*J2*R*R/r2/r2/r/2.`, `G*M` first, and J4's z factor `(fac+12.-28.*costheta2)`.
   - The file was rewritten on 2024-10-20 (8402022, "Adding 'j2' with a general spin axis"). Main now does all of the following:
     - forms `costheta2` from `dw/r` squared;
     - computes `f1 = 3.0/2.0*G*m*J2*R*R/r2/r2/r`;
     - rotates into a spin-axis frame, which is exact for the default z axis;
     - orders J4's z factor as `f2 - 28.0*costheta2 + 12.0`;
     - and skips a zero J4.
   - So decision 4's "op-for-op against what REBOUND's users run" would compare with the old order only. I ran nothing against REBOUNDx: I BELIEVE any REBOUNDx a REBOUND 5.1.1 user installs would differ in bits from the port.
   - MEASURED: the port at binary64 is bit-identical to REBOUND 5.1.1 plus a Python J2 in the 2020 order.
2. **`tools/state_to_problem.py` carries neither the `active` nor the `zonal` line.** That holds on main and on round4-int5 (READ). So `tools/reversal.py`, run on a zonal or `active` problem, would integrate back on a different problem (BELIEVED consequence; not run). `port_roundtrip.py` here carries every line.
3. **REBOUND's SABA, EOS and JANUS take a whole step at the start time** (section 2). docs/INTEGRATORS.md ranks SABA second for a wide port. That ranking stands for autonomous forces only, which is all the ring has.

## 7. Measurements and their commands

**Host and budget:**
- i5-12400F, 12 threads.
- CPU load 6-20% when sampled at 09:04 and 09:22 local. Bash-tool children run at BelowNormal priority.
- Timings are this host's on this day. No other speed claim is made.
- Total about 5 CPU-minutes.

**Instruments and setup:**
- Python: `C:\Users\logan\AppData\Local\Programs\Miniconda3\python.exe` (3.12.15, rebound 5.1.1).
- The port: `C:\Users\logan\source\repos\cft-rebound-seam\build\ias15_cft.exe`, round4-int5, `libcft-0.18`, software backend, run with `C:\msys64\mingw64\bin` first on PATH.
  - The binary's mtime is 07:24:03, before that branch's tip (d9c8c8c, 08:13), so it is an earlier build of that worktree. Every record's `# identity` line names libcft 922c2ad, clean.
  - The worktree's sources and docs changed during this study (`src/ias15_cft.c` at 09:20), but the binary was not rebuilt, and every port run ended by 09:11. So one build made every port number here.
- Every file was written in `scratchpad\studies\debris-a\`.

| measurement | command | output |
|---|---|---|
| LEO tables; density scale; cost floor; global step | `python leo_roundtrip.py` | `leo_roundtrip.log`, `.json` |
| port round trip, quarter day, three formats | `python port_roundtrip.py --dt 100 --steps 216 --formats fp64,fp128,fp256` | `port_quarterday.log` |
| port round trip, one day | `python port_roundtrip.py --dt 100 --steps 864 --formats fp64,fp128` | `port_fullday.log` |
| references against the port's binary128 day | `python check_ref.py` | `check_ref.log` |
| state transition matrix | `python var_check.py` | `var_check.log` |
| MEO and GEO, one year | `python meo_geo.py` | `meo_geo.log` |

**Details of the measurements:**
- The port's forward and backward runs were each `ias15_cft.exe --format F --problem leo_j2.txt --dt ±100 --epsilon 0 --steps N --sample N --max-iter 12|24|60 --quiet`. The backward run started from a turn-around file holding the exact recorded state and every header line.
- The J2 force is written in the 2020 REBOUNDx order:
  - GM = 398600.4418 km³/s²;
  - R = 6378.137 km;
  - J2 = 1.08262668e-3;
  - J4 = 0 in the port's line.
- Drag uses an exponential atmosphere with ρ = 3.725e-12 kg/m³ at 400 km and a 58.515 km scale height, B = 0.022 m²/kg, and a co-rotating atmosphere.
- The Moon and Sun are analytic circular orbits.

## 8. What this study could not settle

- **The cost of a real force evaluation** (gravity field, atmosphere, ephemeris) was not measured. It decides the catalogue's cost, since IAS15 needs about 12,500 evaluations per object-day in LEO.
  - At the C point-mass floor, 54,000 objects above 10 cm (READ [S16]) cost 15 CPU-hours a year (COMPUTED).
  - At a BELIEVED 10-100 µs a force evaluation, they cost 28 to 280 CPU-days a year (COMPUTED: 12,452 evaluations × 54,000 objects × 365 days).
- **heyoka, cascade and Orekit were read about, not run.** I have no measured comparison with IAS15 on this problem. The cascade example does not state its population's size.
- **Two accuracy figures rest on excerpts or secondary sources:** TLE growth rates, and the density-model error figure.
- **The current SP catalogue's algorithms** are known here only from a 2012 review's excerpt and older papers.
- **The MEO and GEO reference** is binary64 IAS15 at 300 s, not checked at binary128.
- **Whether REBOUNDx 5.x's J2 differs in bits from the port** at binary64 is read from code, not run.

## Sources

- [S1] REBOUND at bdfda4bd, `C:\Users\logan\source\repos\cft-rebound\third_party\rebound\src` (file:line given in the text).
- [S2] cft-rebound main 291c99c: README.md, ROUND4.md, docs/HORIZON.md, docs/INTEGRATORS.md, tools/; and the round4-int5 worktree `cft-rebound-seam`: src/ias15_zonal.inc, tools/state_to_problem.py, tools/compare_run.py.
- [S3] REBOUNDx effects: https://reboundx.readthedocs.io/en/stable/_sources/effects.rst.txt
- [S4] REBOUNDx `gravitational_harmonics.c`, main: https://raw.githubusercontent.com/dtamayo/reboundx/main/src/gravitational_harmonics.c. At 5406ae5: https://raw.githubusercontent.com/dtamayo/reboundx/5406ae5/src/gravitational_harmonics.c. History: https://github.com/dtamayo/reboundx/commits/main/src/gravitational_harmonics.c
- [S5] Rein & Spiegel 2015, IAS15: https://ui.adsabs.harvard.edu/abs/2015MNRAS.446.1424R/abstract
- [S6] Rein & Tamayo 2016, second-order variational equations: https://arxiv.org/abs/1603.03424
- [S7] Rein & Tamayo 2018, JANUS: https://arxiv.org/abs/1704.07715
- [S8] Biscani & Izzo 2021, heyoka: https://arxiv.org/abs/2105.00800. Variational ODEs: https://bluescarni.github.io/heyoka.py/notebooks/var_ode_sys.html. Batch mode, with a time and step per element: https://bluescarni.github.io/heyoka.py/notebooks/Batch%20mode%20overview.html
- [S9] cascade: https://github.com/esa/cascade, https://esa.github.io/cascade. The example: https://esa.github.io/cascade/examples/20yearsofLEO_coll.html. Its heyoka dependency: https://raw.githubusercontent.com/esa/cascade/main/CMakeLists.txt
- [S10] Orekit features: https://raw.githubusercontent.com/CS-SI/Orekit/develop/src/site/markdown/index.md. Estimation (search excerpt): https://www.orekit.org/static/architecture/estimation.html
- [S11] Amato et al. 2019, THALASSA's formulations: https://ui.adsabs.harvard.edu/abs/2019CeMDA.131...21A and https://export.arxiv.org/abs/1810.11418
- [S12] Vallado et al. 2006, AIAA 2006-6753: https://celestrak.org/publications/AIAA/2006-6753/. Its FAQ: https://celestrak.org/publications/AIAA/2006-6753/faq.php. Kelso, TLE FAQ: https://celestrak.org/columns/v04n03/
- [S13] Levit & Marshall 2011: https://arxiv.org/abs/1002.2277
- [S14] Berry & Healy 2004, Gauss-Jackson: https://drum.lib.umd.edu/items/e989dac8-3ddb-4377-a549-b041ef77f39b/full. NRC 2012, *Continuing Kepler's Quest* (excerpt): https://www.nationalacademies.org/read/13456/chapter/19. HASDM: https://spacewx.com/wp-content/uploads/2024/02/High_accuracy_satellite_drag_model_HASDM.pdf
- [S15] Holman et al. 2023, ASSIST: https://arxiv.org/abs/2303.16246v1 and https://assist.readthedocs.io/
- [S16] ESA Space Environment Report 2025: https://www.esa.int/Space_Safety/Space_Debris/ESA_Space_Environment_Report_2025. DISCOS statistics: https://sdup.esoc.esa.int/discosweb/statistics/
- [S17] MOCAT-MC: https://arxiv.org/html/2407.21000v1 and https://aeroastro.mit.edu/?p=10162
- [S18] Daquin et al. 2016 (excerpt): https://arxiv.org/abs/1507.06170. Rosengren et al. 2015: https://arxiv.org/abs/1503.02581
- [S19] Breakup epoch by back-propagation (excerpts): https://re.public.polimi.it/retrieve/275e0392-4164-45f2-acb5-4d8032efdf88/OTTOF01-24.pdf and https://ccd.aiub.unibe.ch/publist/data/2021/artproc/TS_ECSD2021b.pdf
- [S20] Bowman et al. 2008, JB2008 (search excerpt only; not opened). Storm-time model errors: https://arxiv.org/abs/2408.16805
- [S21] 1-3 km/day TLE growth, secondary: https://arxiv.org/pdf/1809.09196
