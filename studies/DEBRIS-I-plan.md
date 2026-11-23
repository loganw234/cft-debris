# DEBRIS-I: M1's force model as a cft program on libcft's software executor, held to its definition and to M1 (plan of record, draft 3)

Drafted 2026-11-23 by cft-debris's lead for Logan's approval.
- This is a **build round, with no long run.** It writes the part of M1's force model that cft's language carries today as a cft program. That program is compiled by cftc and run on libcft's software executor:
  - the program is held bit for bit to cftc's reference interpreter, which defines it;
  - it is held to M1, the C propagator, set to the same forces, within tolerances fixed in this plan;
  - its rate is measured on amd-arc-box's 36 threads, beside M1's.
- The same images are what a GPU runs through `hip:N`. That is DEBRIS-J, the next round, so nothing here touches a GPU.
- **Draft 1** passed the lead's checker (`dispatch\check_plan_i.py`, log 003: 207 checks, 0 failed).
- **plan-verifier-I** (Sonnet) then found no blocker, six defects and notes. Its probes compiled with cftc and ran the reference interpreter at 9e8ff270. Its report is filed verbatim in the ledger's `filed\`. The lead checked each finding's evidence before answering it. Draft 2 answers every finding in "What changed from draft 1".
- **plan-verifier-I's scoped re-check of draft 2** found no blocker, one defect and four notes. Its report is filed too. Draft 3 answers them in "What changed from draft 2".
- Draft 3 has had the lead's check only (`lead.md` names its log). Nothing has been dispatched, downloaded or requested.

**Names.** "M1" is the C propagator of rounds DEBRIS-E to DEBRIS-H. DEBRIS-D's study called its own first milestone "M1" too: a CPU reference in cft's language. This plan calls that **the program**, to keep the two apart.

## The question, in Logan's words

- **This week** (2026-11-23 05:07:34): "Push it, then begin working on the plan of work for the week, working roughly from 6am-6pm, with longer runs allowed to continue out of schedule as usual".
- **The week's plan** (ledger `plans\week-2026-11-23.md`) names this round "DEBRIS-I: M1's force model as a cft program, on the CPU". Logan approved it at 06:31:29, answering "Approve the week's plan with its six defaults?": "Approve the plan". Its first decision says each round's own plan still comes to him before dispatch. This is that plan.
- **The goal** (2026-11-12): "a simulation capable of realtime (or slightly faster) simulation on a consumer card, so a 24x7 sim could run on a local box here for long run tests, validating itself with the open datasets update intervals, scaling tracked objects as the main scaling parameter presumably. High performance cards like the MI300X could then be used for higher density or faster/concurrent runs".
- **Carried from earlier rounds:**
  - the route through cft programs (2026-11-12): "*Yes if possible utilize cft programs, as well as generating certificates when able";
  - certificates (2026-11-12): "*Certificate support can be built for but not implemented in order to still have gpu capability at the moment";
  - the precision (2026-11-12): "Id also prefer to continue to utilize the higher precisions, simply to be a usecase for cft-fp256 as well";
  - the kinds (2026-11-13): "utilize native and cft for binary64 (and 32 if needed) so the library utilizes the entire precision range offered by cft, and the results can be compared for correctness";
  - the box (2026-11-16): "you have permission to utilize the box for the cpu or Intel arc card, the U50 is the only withheld resource on that machine".

## What DEBRIS-I is for

DEBRIS-D designed the route to a card. A propagator is written as a cft program, compiled once by cftc, and run by libcft on any device: the CPU's software executor or the GPU backend `hip:N`, with the same bits on each.

It built only small systems: J2 alone, and J2 with C22/S22, drag and the Earth's rotation. It also swept the field's degree for capacity. No round has written M1's model as a program, run it for a day of real objects, or held it to M1. Three things follow:
1. **The model as a program.** Which of M1's forces v1 carries, and at what degree, within the bank's 512 slots and a lane's scratch.
2. **Two holds.**
   - To the program's definition: the interpreter, bit for bit, as DEBRIS-D's first test did.
   - To M1: independent code, already held to Lasser et al., to `testpo.421`, to Orekit force by force, and to CelesTrak's sets over 72 hours.
3. **Its price on the box's CPUs, beside M1's.** The executor runs a routine as instructions inside the image, where M1's wide kinds call libcft's host functions. DEBRIS-D measured a routine inside a program at a tenth to a fortieth of the host call.

| part | what it settles | the evidence it rests on |
|---|---|---|
| **I0. The pin and the builds** | cft-fp256 at one commit for the program and for M1's libcft | gate I0: every source hashed; M1 unchanged; M1 on the new libcft equal to M1 on the old, bit for bit |
| **I-a. The generator** | the program's cft source, with every data value a parameter | the compiles' manifests (instructions, bank, scratch) |
| **I-b. The run's blocks** | the Earth's orientation and DE421's series as parameters of each run | gate I2's frame bound and its ephemeris parts |
| **I-c. The driver** | images run on the executor, run by run and segment by segment, every boundary state kept | gates I1 and I3 |
| **I1. Against the definition** | the executor equals the interpreter, bit for bit | states and lane flags, at four formats |
| **I2. Part by part, against M1's kernels** | each force, the frame and the ephemeris | rounding-scale tolerances at binary256, fixed here |
| **I3. A day, against M1** | the whole program, on 64 real objects | tolerances fixed here, at binary64, binary128 and binary256 |
| **I4. The authorities, through the program** | DE421's series and the tides by the program's own route | `testpo.421`; Lasser et al.'s tides |
| **I5. The rate on the box** | object-seconds a second, beside M1's | a measurement in a `sensitive` window, configurations fixed here |
| **I6. Degree 20 as lane params** | whether cftc compiles it, and in what depth | a time-boxed measurement |
| **Part B. Two of DEBRIS-H's follow-ups** | the skipped slot's log line, and each request's time to its first byte | local tests (decision 7) |

What this round does not do: use any GPU, write a certificate, change M1's library, carry radiation pressure in the program, download anything, or request any data service ("Not in this round").

## What DEBRIS-I starts from (labels as in DEBRIS-C)

### M1 (MIT, commit 094444c, on origin/main)

- **`src\`** is byte-identical between commits 1646c96 and 094444c (MEASURED, `git diff --stat 1646c96 094444c -- src` prints nothing). Its force model (READ, `src\m1_physics.h`) is:
  - the central term and the harmonics from EIGEN-6C4, in the Earth-fixed frame;
  - the Sun and the Moon as point masses, from DE421's Chebyshev series by Clenshaw's sum;
  - an exponential atmosphere of 28 bands, chosen by selects on the height |r| − R, with drag co-rotating;
  - radiation pressure with a conical shadow.
  - They are summed as (((((central + harmonics) + Sun) + Moon) + drag) + radiation pressure). Classical rk4 integrates at a fixed step, from host stage times t0 + (step0 + j) h.
- **Its switches** (READ, `src\m1.h`, `m1_model`):
  - `central`, `nmin`, `nmax`, `sun`, `moon`, `drag` and `srp`, each on or off;
  - `nbands`, 28 or 1, with the one band's h0, ρ0 and scale height as decimal strings;
  - `frame`: 0 is DEBRIS-E's uniform rotation, and 1 is the IERS 2010 frame from a node table.
  - In the context, `cr_transc` routes the native kinds' exp, sin, cos, asin and acos to libcft.
- **The frame, `frame` = 1** (READ, `src\m1_physics.h`, `ph_frame_at` and `ph_frame_apply`; `studies\DEBRIS-F-build.md` §2):
  - M (GCRS ← ITRS, 9 elements) and Ω (3, rad/s) are interpolated at each stage time by 6-point Lagrange, from fine nodes every 256 s;
  - DEBRIS-H's table `frame_h0.bin` (ledger `debris-h\`) covers TDB 2026-10-17 00:00 to 2026-12-28 00:00, nodes every 256 s (READ, its header's note and its `t0_dec` and `tlast_dec`, 85,376 s and 6,308,224 s from JD 2461329.5).
  - M1's own interpolation differs from the node routine by up to 7.65e-14 rad in M, and 9.08e-16 rad/s in Ω, on that table (MEASURED, DEBRIS-H's H0 (c), `studies\DEBRIS-H-build.md`).
- **The number kinds:** native32, native64, cft32, cft64, cft128 and cft256 (READ, `src\m1.h`). cft64, cft128 and cft256 run every operation through libcft's software backend, as host calls.
- **Its kernels are callable one by one** through `m1_vt`: `grav`, `central`, `third`, `series`, `bodies`, `pleph`, `frame_at`, `frame_apply`, `drag` and `drag_om` (READ, `src\m1.h`). `tests\m1run.c` already drives them for the gates of DEBRIS-E: modes `e1` (per kernel), `traj`, `lasser`, `lasser3` and `testpo` (READ, its usage lines).
- **Its record:**
  - E4: Lasser et al.'s gravity to degree 180 within 2.28e-15 m/s², and their Sun and Moon tides within 1.3e-17 and 4.3e-16 m/s², against a tolerance of 1e-11;
  - E5: `testpo.421` within 4.9e-16 AU, against 1e-13;
  - E6: Orekit, force by force;
  - all MEASURED in `studies\DEBRIS-E-build.md`.
- **Throughput on the box** (MEASURED, `studies\DEBRIS-G-build.md` §4, 64 lanes, in a `sensitive` window), in object-seconds a second:
  - cft256: 299 on 1 worker, 4,176 on 18 and 4,332 on 36;
  - cft128: 684, 9,587 and 9,564;
  - native64: 1,291,561 on 1 worker.
- **DEBRIS-H's seed** (ledger `debris-h\box\r2\seed\seed1.txt`, READ): 2,688 objects at T_s = 2026-11-18 22:50:00 TDB, each with its binary64 state, `bc` and `cram` in C99 hex. It is per-object data, and stays in the ledger. The test seed's 64 objects are in `debris-h\testseed\`.

### cft-fp256 at the pin (READ by `git show` and `git diff --stat` in its checkout, which this round never writes)

- **The commits:**
  - `0aa997a3` is the archive M1 has linked since DEBRIS-E (ledger `tools\cft-fp256-0aa997a3.tar`).
  - `9e8ff270` is the commit cft-fp256's lead offered on 2026-11-18: "For a pin of yours: 9e8ff270 has everything in this morning's message" (relayed: GPU round 2 closed).
  - `5ac396d3` is cft-fp256's main of 2026-11-20 15:11.
- **From 0aa997a3 to 9e8ff270,** `docs\LANGUAGE.md` and `python\cftc\` are unchanged: `git diff --stat` prints nothing for them. The host library did change, in `host\include\cft.h`, `host\src\augmented.c`, `backend.h`, `device.c` and `softfloat.h`, `host\Makefile`, and the GPU backend. So I0 holds M1 on 9e8ff270's libcft against M1 on 0aa997a3's.
- **From 9e8ff270 to 5ac396d3,** of `docs\LANGUAGE.md`, `python\cftc\`, `host\include\` and `host\src\`, only `host\src\backend_hip.cpp` and two new headers of the GPU's fixed tier changed (READ, `git diff --stat`). So on the CPU the two are the same code.
- **The language** (READ, `docs\LANGUAGE.md` at 9e8ff270, 3,330 lines):
  - **Statements:** `state`, `const`, `param`, `lane param`, `let`, `d/dt`, `next` and `step`.
  - **Integrators:** rk4, euler, stormer-verlet and map.
  - **Arrays** are one-dimensional and unrolled into the step graph. An index is integer arithmetic on literals and the statement's index variable.
  - **A `param`** is a bank slot of the run, and a run may give it another value, so one image serves every value. **A `lane param`** is one value per lane, held after the state in the lane's scratch. A lane holds at most 32,768 values.
  - **Routines:** exp, expm1, exp2, log, log1p, log2, sin, cos, tan, atan, asin, acos and atan2. `pow` is refused `transcendental`.
  - **Built-ins and comparisons:** `select`, `min`, `max`, `abs`, `copysign`, `fma` and `sqrt`; `<`, `<=` and `==`.
  - **Time:** there is no built-in `t`. A system carries time in its state (`d/dt t = 1`).
  - **The language has no tables.** The index tables cft-fp256 added to `hip:N` are a host-interface feature (`docs\HOSTAPI.md`, "Index tables (round 2, G2B)"), and no statement of the language's grammar names one. cftc emits indexed loads and stores of its own (`python\cftc\regalloc.py` counts LDX and STX), but no source can place data in a table. So the week's plan's "a probe of degree 20 through index tables if cftc can express it" is answered: it cannot. I6 tries the lane-param route instead.
- **The GPU, relayed** (2026-11-17 and 2026-11-18, the sender's labels):
  - `hip:N` opens at any power of two up to 2,048 slots. Measured lanes a launch: 2,048 at depths 256 and 512, 1,008 at 1,024 and 504 at 2,048.
  - Its features are 0x7ff1f, the software handle's own.
  - The bank stays at 512 by Logan's word.
  - `docs\HOSTAPI.md` gives the bound behind those figures (READ): a launch carries at most pool / (reach × 260) lanes. Reach is the whole depth for a program that indexes, and its highest static slot + 1 otherwise.

### What DEBRIS-D measured (MEASURED there, as narrowed at its merge; `studies\DEBRIS-D-architecture.md`)

- **Its first test passed.** J2 alone, and J2 with drag and rotation, at binary64, binary128 and binary256: on the software executor they equal the interpreter bit for bit, states and lane flags, over 96 steps on 8 lanes, with no lane marked.
- **Capacity:**

| field | binary64 | binary128 | binary256 |
|---|---|---|---|
| degree 7 | 8,302 instructions, bank 424, scratch 222 | 8,291, 427, 222 | 8,396, 448, 222 |
| degree 8 | refused `scratch-capacity`: 273 slots against 256 | the same | refused `bank-capacity`: 516 against 512 |
| degree 8 on `sw:512` | 9,415, bank 492 | 9,404, bank 495 | refused `bank-capacity` |
| degree 20 | refused `bank-capacity`: 1,762 params | - | - |
| degree 20, coefficients as lane params, `sw:4096` | not finished in 290 s, stopped by its own timeout | - | - |

  - Its generator, `studies\debris-d\q2\gen_field.py`, unrolls the sums and makes every coefficient product a param. A rolled or `map` form was not tried.
- **Routines in an image:** a division costs 186 to 190 instructions, a root 165 to 171, exp 180 to 201, sin 389 to 406 and cos 385 to 402.
- **The executor's cost on the desktop's CPU:** 50 to 125 ns a lane-instruction, in its sensitive window B0024.
- **Marks:** 0 lanes marked in 196,608 lane-evaluations of exp on LEO lanes at each format. sin and cos of an argument every lane shared were not determined: a marked time would mark every lane at once.
- **Its tools, MIT and reusable with a note:** `studies\debris-d\q2\gen_field.py`, `studies\debris-d\tools\seqrun.c` (the executor's driver, segment by segment, with `--depth`), `studies\debris-d\q2\q2_first_test.py` and `studies\debris-d\tools\cpurun.py`.

### The box and its time (READ, the TimeSheet, 2026-11-23)

- **Free of standing windows** on weekdays from 07:45 to 18:00. S003 holds it `shared` on the nights of Monday to Thursday, and S004 from Friday 18:00 to Monday 07:45: "others may share, at low priority".
- **DEBRIS-G timed in a `sensitive` window,** B0107, and I5 does the same.
- **The disk:** 13.14 GB free on the root filesystem since the lead's removal this morning (MEASURED by statvfs, `lead.md` 07:00).

## The design, and why

**1. The model the program carries.** Everything M1 computes except radiation pressure:
- the central term and the harmonics of degrees 2 to N in the Earth-fixed frame;
- the Sun and the Moon as point masses, at DE421's geocentric positions;
- drag, co-rotating with the frame's Ω.

They are summed in M1's order where the parcel can keep it.
- **Radiation pressure is left out.** Its shadow needs asin and acos per lane and many parameters, and the bank is the constraint (below). The model-gap measurement in I3 prices its absence.
- **The step** is rk4 at 15 s, the service's.

**2. Every data value is a parameter.** Each run's bank and lanes carry the data: the gravity coefficients, DE421's coefficients for the run's sub-interval, the frame's block and the atmosphere's bands.
- **In the source,** each is a `param` or `lane param` whose default is 0 or another value the source can state without data, filled by the driver for each run.
- So **the generated sources carry no third-party data** and can live in the repository, as M1's sources do.
- **The images stay out of it:** an image carries cft-fp256's routines, which are Apache-2.0 (DEBRIS-D's licence note).

**3. Capacity decides the degree, and the parcel measures it.**
- The bank holds 512 slots on every device. A lane's scratch holds the state, its lane params and the spills. The software executor opens at a chosen depth.
- **DEBRIS-D's field alone** took 424 to 448 bank slots at degree 7. Adding DE421's three series (13, 11 and 13 coefficients for the Moon, the Sun and the Earth-Moon barycentre, so 111 values) would pass 512 at degree 7 if all were params, before the frame's values and the bands are even counted (COMPUTED: 448 + 111 = 559 at binary256).
- **plan-verifier-I's probe** compiled a crude whole program at degree 7 and binary256 on `sw:512` (MEASURED by its compile, a probe and not a build). It carried:
  - M1's 28 bands by `select`, drag with Ω, and the Sun's and the Moon's tides by Clenshaw over DE421's 111 coefficients;
  - the frame as degree-10 polynomials (108 values).
  - With all 304 of those values as lane params, cftc refused it: `scratch-capacity`, 567 slots against 512.
  - With 60 of them in the bank, it compiled to 15,755 instructions (the probe image's count), with scratch 503 of 512 and 442 bank slots. A probe with 40 in the bank was refused, and 50 was not tried.
- So the parcel chooses the layout: which values ride in the bank and which as lane params (the same value in every lane). It reports each variant's manifest.
- **The depth stays at most 512** (decision 3), since `hip:N` runs 2,048 lanes a launch at depths 256 and 512, and half that at 1,024 (relayed).
- **The degree is 7.** Degree 8 does not fit at depth 512 by plan-verifier-I's arithmetic, so the parcel compiles it once and reports its refusal by name.
- **If the whole model does not fit at degree 7,** the parcel gives way in this order:
  1. M1's 28 bands are replaced by one band;
  2. it stops and asks the lead, who asks Logan, before any lower degree.

**4. Runs and blocks.**
- A run is one block. Its frame's form and its DE421 sub-interval are fixed for it, so its streams are fixed, as certificates need.
- **The block's length is 1 hour:** 240 steps, run in 6 segments of 40 (decision 4).
- **A segment is 40 steps, 600 s,** DEBRIS-H's checkpoint interval. cftc fixes an image's steps a segment when it compiles (`--steps S`, "the image's one REPEAT count", READ `python\cftc\__main__.py`).
- **A block never crosses a DE421 sub-interval** of any of the three series. The driver ends a block early at one.
- **Every run starts on the 600 s grid of TDB:** DEBRIS-H's T_s is 22:50:00 TDB, and the test seed's is 00:00. Every DE421 sub-interval starts at 00:00 TDB, since its records start at JED 2414864.5 and run for whole days. So a block that ends early at a boundary still ends on a whole segment.
- **24-step segments would not.** From 22:50, the next midnight is 70 minutes away, 11 segments and 16 steps (plan-verifier-I's D5).
- **I3's day crosses no sub-interval boundary** (COMPUTED from `header.421`'s 32-day records): the Moon's 4-day sub-interval runs from 2026-11-16 to 2026-11-20, and the Sun's and the Earth-Moon barycentre's 16-day sub-interval from 2026-11-16 to 2026-12-02. So I2(d) exercises the driver's choice of sub-interval instead, with inputs on both sides of 2026-11-20 00:00 TDB and one exactly on it.
- **A limit at a boundary.** A block that ends at a boundary lands its last stage on the boundary itself. The program evaluates that stage on the earlier sub-interval's series. M1 takes the later one there (READ, `src\de421.c`, `m1_de_locate`, with dt = 0). So the two differ by DE421's own discontinuity at that point, for one stage, which is BELIEVED far within T_frame. I3's day crosses no boundary, so this round does not test it.
- The state at every segment boundary is kept.

**5. The frame's form per run** is the parcel's design, held to a bound fixed now (I2(e)).
- **The bound:** at every stage time of I3's runs, every element of the program's M within 1e-12 of M1's `ph_frame_at` (frame = 1, DEBRIS-H's table), and Ω within 1e-14 rad/s.
- **Its basis** (COMPUTED by the checker):
  - an angle of 1e-12 at 7,000 km is 7 µm;
  - tilting J2's field by 1e-12 changes an acceleration of about 1.2e-2 m/s² by about 1.2e-14 m/s². Held constant for a day, that moves a position by under 5e-5 m (½ a t²), a crude upper bound;
  - Ω's 1e-14 rad/s moves v_rel by under 1e-7 m/s at 7,000 km, a part in 1e11 of LEO's 7.5 km/s;
  - both bounds are at least ten times M1's own interpolation's differences from the node routine (7.65e-14 rad and 9.08e-16 rad/s, above), so a form fitted to the node routine can meet them.
- **Shared arguments.** M1's Ω and M come from host time, the same for every lane, and so would a program's angle of the Earth's rotation. A routine of an argument that every lane shares marks every lane at once when it marks (DEBRIS-D). So a form whose routines cannot mark, such as polynomials in t, is preferred where it meets the bound. Any routine of a shared argument that remains is named in the build report with its mark count.

**6. The ephemeris inside the program.** DE421's own series for the run's sub-interval, evaluated as M1's `ph_series` and `ph_bodies` evaluate them:
- τ = (dt + dt)/len − 1, from t;
- Clenshaw's sum from the highest coefficient down;
- the Earth as EMB − Moon/(1 + EMRAT), and the Sun less it.

So I2 holds it to M1's own bodies at rounding scale, and I4 holds it to `testpo.421`.

**7. Drag.**
- M1's exponential atmosphere, with v_rel = v − Ω × r, M1's `ph_drag_g` with Ω given.
- **The bands:** M1's 28 by selects if capacity allows. Otherwise one band (M1's `nbands` = 1), with values the parcel states before the data.
- `bc` is a lane param.

**8. Time.** t is in the state.
- At 15 s, every stage time is a multiple of 7.5 s, exact in binary (COMPUTED).
- **plan-verifier-I's probe** found t exact under the language's rk4 at 15 s. Started from 6,308,224, it ended exactly 3,600 later at binary64 and binary256 (MEASURED in the interpreter, 240 steps).
- Each run starts its t at the block's start, and the stage times must equal M1's host stage times exactly. I3 checks t at every boundary.

**9. Holding the program to M1** (I2 and I3).
- **M1 is set to the program's forces:**
  - central, degrees 2 to N, the Sun, the Moon and drag on, with the same band or bands;
  - `srp` off;
  - `frame` = 1 with DEBRIS-H's table;
  - rk4 at 15 s from the same t0.
- **The program then differs from M1 in three things only:** the frame's form (bounded by I2(e)), operation order, and the formats' rounding. So the tolerances are those three, stated now.
- **At binary256,** rounding is far below the frame's term, so I3 there tests the frame's term and everything else. A wrong coefficient, sign or unit moves a position by metres to kilometres in a day.
- **At binary64,** rounding dominates. So I3 there is DEBRIS-D's rounding tolerance, and binary256 carries the model's check.

**10. Formats.**
- binary64 and binary256 in every gate, as the week's plan says.
- binary128 too, since it costs little and Logan asked for "the entire precision range".
- binary32 is compiled and run in I1 only. An orbit cannot be propagated usefully at binary32, but its bits can still be held to the definition.

**11. What a GPU needs from this round,** kept for DEBRIS-J:
- each image and bank, with its manifest, depth and features;
- the driver's run and segment loop;
- every boundary state of I3's runs at each format, and the marks.

DEBRIS-J then holds the card to these, lane for lane.

**12. Certificates:** built for, and not implemented.
- Runs are dense, with fixed streams and one block a run, and every boundary state is kept. cftc's step-halving `.half.bank` is kept.
- No certificate is written or audited (Logan, 2026-11-12).

**13. The rate** (I5), on the box, in a `sensitive` window: the program's executor and M1, at the same model and configurations, so that the ratio divides like by like.
- **ESTIMATE, before the data:** the program at binary256 runs 10 to 30 times M1's cft256 at its full model.
- **Its basis:**
  - 15,755 instructions, the image's count in plan-verifier-I's probe at degree 7. For DEBRIS-D's degree-7 image, the image's count and its count a step differed by 16;
  - DEBRIS-D's 69.8 to 124.6 ns a lane-instruction at binary256 on the desktop (MEASURED there, its table of the sequencer on its images);
  - a box thread 1.5 to 2.5 times slower than the desktop's (BELIEVED);
  - G4's 299 object-seconds a second, so 3,050 to 9,090 for the program (COMPUTED from the above).
- The ratio against M1 at the program's own model is measured, not estimated.

**14. Degree 20** (I6). Its 1,762 coefficients cannot be params (the bank) or a table (the language), so the only v1 route is lane params, in a scratch of more than 1,762 slots a lane.
- DEBRIS-D stopped that compile at 290 s.
- I6 gives it more time and records what it takes. A depth of 2,048 is `hip:N`'s largest.

## The shape

| agent | job | model | when |
|---|---|---|---|
| the lead (this session) | <ul><li>Phase 0</li><li>the briefs and the ledger</li><li>every box run, its staging and its bookings</li><li>escalations, and filing each final message</li><li>the merge and its narrowing, the commit and the round's record</li></ul> | Opus | throughout |
| DEBRIS-I | <ul><li>**phase 1:** the generator, the driver, M1's side, the harness, I0 to I4 and I6 at the desktop's sizes, part B; its hand-off</li><li>**phase 2:** the box's records, and the build report</li></ul> | Opus (decision 1) | after Phase 0; phase 2 after the lead's box runs |
| verifier-I | disconfirm the build, its gates and the box's records | Sonnet (decision 1) | when DEBRIS-I reports |
| merge-check-I | check any narrowing the lead makes at the merge | Haiku | after verifier-I, if the lead narrows anything |

**The schedule (ESTIMATE):**
- **Day 1,** the day of approval: Phase 0, and DEBRIS-I's phase 1, continuing into day 2 if it must.
- **Day 2:** the hand-off. Then the lead's box work in the day: I0's box build; I3's full run; I5 in a `sensitive` window; and I6's longer compile if the desktop's did not finish. Then phase 2.
- **Day 3:** verifier-I, the merge and the commit. The push waits for Logan's word. DEBRIS-J's plan follows.

## Phase 0: the lead, before dispatch

1. **Logan's decisions,** recorded verbatim.
2. **The archive** (decision 2): `git -C cft-fp256 archive 9e8ff270` into the ledger's `tools\cft-fp256-9e8ff270.tar`. git writes only to that file, and cft-fp256's checkout is not touched. Its SHA-256 and its file count go in `lead.md`. This is the lead's act. The agents' rule, `log` and `show` only, stands.
3. **TimeSheet:** DEBRIS-I's desktop time as a `notice`. The box's runs are short work, or booked when longer; I5's window is booked `sensitive`, in the day, after the hand-off.
4. **Ledger files:** `DEBRIS-I.md` and `verifier-I.md`, with headers only, and the folder `debris-i\` for every per-object file.
5. **cft-fp256's lead is not asked anything.** This round reads its archive and runs nothing of theirs on any device of theirs. DEBRIS-J's plan will ask about the card.
6. **Dispatch,** as below.

## Dispatch

- **The prompt:** a dispatch note and the agent's brief, followed verbatim by four sections of this plan: "Dispatch", "The ledger", "Rules every brief carries" and "READY". A script writes the prompt from this file. After dispatch, `dispatch\check_prompts.py` checks the prompt against the harness's transcript.
- **The test escalation:** each agent sends one as it starts:
  - it writes `test escalation from <name>` in its own ledger file;
  - it sends the same words to the lead (SendMessage to `main`);
  - the lead replies "received" and records the round trip in `lead.md`.
- If no test escalation arrives within ten minutes of a dispatch, the lead reads that agent's ledger file, arms a watch on the ledger folder, and says so in `lead.md`.
- **DEBRIS-I runs in two phases:**
  - Phase 1's final message is its **hand-off.**
  - The lead files it and runs the box's work in this order: I0's box build, with its control first; I3's full run; I5 in its window; I6 on the box if needed.
  - If a box run fails, the lead resumes DEBRIS-I with the failing log. DEBRIS-I fixes it and hands off again.
  - When the box's records are in place, the lead resumes DEBRIS-I for phase 2. It replays on the desktop every mark the box logged, then evaluates. Phase 2's final message is DEBRIS-I's report.
- **Ending its turn ends an agent's run,** and its final message becomes its report or hand-off. A later message from the lead resumes it.

## The ledger

The ledger is `C:\Users\logan\source\repos\cft-debris-ledger\`, as in rounds DEBRIS-B to DEBRIS-H.

- **One file per author, append only:**
  - `lead.md` continues;
  - this round adds `DEBRIS-I.md` and `verifier-I.md`, which the lead creates with a header only;
  - correct an entry by appending beneath it, never by editing it.
- **Times:** every heading's time comes from `date`, never from memory.
- **Read it at three moments:** before starting; before resting anything on another study's number; before the final report.
- **Verifiers read `lead.md` only,** and the files it points them to.
- **Escalation:** write the entry first, then message the lead (SendMessage to `main`). Wait for the answer to a question while working on what does not depend on it. Never end your turn to wait, except at the end of a phase.
- **No agent messages another session.** Questions for cft-fp256's lead go through this round's lead.
- **When to write:** when an entry would change another agent's work or the lead's: an environment fact, a brief that turned out wrong, or a finding about a shared input, never progress. Every entry marks which claims were measured and which are believed.
- **When a pause is announced,** record where you are before you stop. On resuming, do a full read, check your outputs before trusting your memory of them, and say where you stopped.
- **Scratch:** each agent creates its own folder when it starts, `C:\Users\logan\source\repos\cft-debris-scratch\<name>\`. Read no other agent's scratch. Keep no secrets anywhere an agent is given.
- **The downloads:** `C:\Users\logan\source\repos\cft-debris-downloads\`, one folder per file, each file's SHA-256 in `lead.md`. Read-only for every agent. This round adds none. It reads `EIGEN6-C4.gfc`, DE421 (`lnxp1900p2053.421` and `header.421`), `testpo.421`, and Lasser et al.'s files (`00README_simulation.txt`, `00orbit_icrf.txt`, `00orbit_itrf.txt`, `02gravityfield_itrf.txt`, `03directTideMoon_icrf.txt`, `03directTideSun_icrf.txt`). M1's frame reads DEBRIS-H's table from the ledger.
- **The tools:** `cft-debris-ledger\tools\`, read-only for every agent. It holds the archives `cft-fp256-0aa997a3.tar` and, after Phase 0, `cft-fp256-9e8ff270.tar`.
- **Data kept out of the repository:** `cft-debris-ledger\debris-i\`, for every output that names an object or holds its state. DEBRIS-I writes there from the desktop, the lead copies the box's files there, and verifiers read it. DEBRIS-H's seed, test seed and frame table are read from `debris-h\`, never changed.
- **What the lead writes in `lead.md`, every verifier reads.** The lead records there every box run, with its booking and its log's SHA-256. It never writes a judgement of DEBRIS-I's work there before verifier-I has reported.

## Rules every brief carries

These come from three places: Logan's standing rules (carried from cft-fp256 and cft-rebound, 2026-09 to 2026-11), canonical ParcelRound, and the rulings of rounds DEBRIS-B to DEBRIS-H.

- **Read-only, except your own outputs and scratch.**
  - cft-rebound, cft-fp256 and the TimeSheet are other sessions' live repositories. Read their files; in git, use only `git -C <repo> log` and `git -C <repo> show`. Never write in them, never run `git status` there, and never run a bare `git stash`.
  - In the TimeSheet you may run `timesheet.py check` and `list`, which only read.
  - cft-fp256 is Apache-2.0. Extract and build its archive only in your scratch.
  - In cft-debris, write only where your brief says. Commit nothing: the lead commits after verification.
- **The repository is public and MIT.**
  - Every source file you write carries a header naming cft-debris and the MIT licence.
  - Copy no third-party source into the repository, whether cft-fp256's, REBOUND's, cft-rebound's or Orekit's. libcft is linked from a build outside the repository and never vendored.
  - **No image or bank goes in the repository:** an image carries cft-fp256's routines. Record each image's SHA-256, its manifest's counts and the command that rebuilds it, as DEBRIS-D did.
  - Copy no third-party data into the repository either: no gravity coefficients, no DE421 coefficients, no Earth orientation values, no frame table, no GP data. The generated sources carry every such value as a parameter with a default the source states without data.
  - **Per-object data stay out of the repository.** Logs in the repository name objects only by their index in DEBRIS-H's seed, never by catalogue number. They carry hashes, counts and aggregates, never a state.
  - Reading a source to understand an interface is fine; quoting more than a short passage is not.
  - This project's own earlier code (DEBRIS-B's to DEBRIS-H's, and the lead's scripts in the ledger) is MIT, and may be reused with a note of where it came from.
- **No downloads, installs or package managers, and no requests to any data service.**
  - This round's files are in the downloads, the ledger's `tools\` and `debris-h\`.
  - **CelesTrak in particular: no agent requests it,** not even a page that looks like HTML.
  - If another file would settle a question, ask the lead for it. Give its name, source URL, size, licence and purpose. Each file needs Logan's approval.
- **Reading the web: HTML pages only, and never CelesTrak's.**
  - WebFetch returns a model's summary of a page, not its bytes. A figure or quote taken through it is labelled "READ (via WebFetch)". It supports "consistent with", never "confirmed".
  - WebFetch saves any response that is not HTML to disk. So a URL ending in `.txt`, `.pdf`, `.csv`, `.zip`, `.bin`, `.jar` or `.gfc`, or one in an FTP tree, is a download request, whatever it seems to hold.
- **No GPU, WSL, card or box.**
  - **amd-arc-box is the lead's.** No agent connects to it. Every run there is the lead's, in its bookings, from commands you hand it.
  - Code meant for the box builds and runs on the desktop too, for testing. Scripts that run on the box use Python 3.12's standard library only.
  - No WSL distro, and no `hip:N` device, is opened by anyone in this round.
- **Keys:** this round uses no keys and signs nothing. Never look in `~/.ssh`.
- **Timings: none on the desktop.**
  - The desktop is shared. Desktop runs are functional tests: no time from them is reported as a measurement.
  - The round's timings are the box's, from the lead's runs in I5's window.
- **At most 4 processes at once on the desktop,** counting every child process you start: compilers, interpreters, drivers and workers alike.
- **CPU budget** means the CPU time of the processes you start on the desktop, counted by cycles:
  - read `QueryProcessCycleTime` through Python's `ctypes`, and divide by 2.5e9 cycles a second;
  - the divisor is the part's base clock (READ, cft-fp256's `docs/BENCHMARKS.md`), and taking it as the counter's rate is BELIEVED;
  - give `GetProcessTimes` beside it. On this host it under-reports a busy thread under load: by a factor of about 1.7 to 4 in round DEBRIS-C, and in DEBRIS-F it gave 2.00 s for a run whose cycles showed 3.97 s (MEASURED);
  - DEBRIS-E's `tests\cpurun.py` does both, and may be reused.
- **Long jobs:** run them through the Bash tool, in the foreground with a timeout of at most 600000 ms or with run_in_background. Never use nohup, and never end your turn while one of your jobs is running.
- **C on the desktop:**
  - Before any compile, put `C:\msys64\mingw64\bin` first on PATH and check that `gcc -dumpmachine` prints `x86_64-w64-mingw32`. In this Git Bash, a bare `gcc` is the 32-bit i686 compiler.
  - libcft's Windows build line is `make -C host CC=gcc OS=Windows_NT TMP=/tmp TEMP=/tmp <targets>` (cft-fp256's `bindings/wasm/verify_demos.mjs:51-58`). On Windows the targets end in `.exe`.
  - M1's build is as `studies\DEBRIS-F-build.md` gives it, through `tests\build_f.sh`. Every native fused multiply-add goes through `_mm_fmadd_sd` or `_mm_fmadd_ss`. On this host the C library's `fma` is not correctly rounded, and at `-O0` a plain `fma()` still calls it (MEASURED, round DEBRIS-E).
- **C on the box (the lead's runs):** gcc 13.3.0, `x86_64-linux-gnu`. libcft is built by `make -C cft-fp256/host CC=gcc libcft.a`, and M1 at `build_f.sh`'s O2 flags, as `tests\g_harness.py` does it.
- **Python:**
  - On the desktop: `C:\Users\logan\AppData\Local\Programs\Miniconda3\python.exe -I -B`, with numpy and mpmath. cftc and the interpreter run from the archive's `python\` folder in your scratch.
  - Scripts that run on the box use Python 3.12's standard library only.
- **Processes and files:** kill only processes you started, and only by PID. Delete only what you made, and never through a computed path.
- **Earlier studies' records are read-only.** Copy what you run into your scratch or your own output folder. Before your report, check all ten:
  - `sha256sum -c SHA256SUMS` run from `studies\` shows 32 OK;
  - `find studies/debris-a -type f | wc -l` gives 29;
  - `sha256sum -c MANIFEST.sha256` shows 54 OK from `studies\debris-b\`, 136 OK from `studies\debris-c\`, 73 OK from `studies\debris-d\`, 60 OK from `studies\debris-e\`, 61 OK from `studies\debris-f\`, 43 OK from `studies\debris-g\` and 149 OK from `studies\debris-h\`;
  - there is no `__pycache__` anywhere under `studies\`.
- **Host traps:**
  - **System32 before PATH.** From Python, or anything else that calls CreateProcess, Windows searches System32 before PATH. So a bare `bash` is `C:\Windows\System32\bash.exe`, the WSL launcher, and a bare `timeout` is `TIMEOUT.EXE`. System32 also holds `wsl`, `tar` and `curl`. Start every program from Python by its full path, such as `C:/msys64/usr/bin/bash.exe` and `C:/msys64/mingw64/bin/gcc.exe`, or run it through the Bash tool directly (round DEBRIS-D, `lead.md`, 2026-11-12 21:23).
  - **MSYS `.exe` transparency:** writing a file `X` beside an existing `X.exe` writes to `X.exe`.
  - **CRLF:** passing a script to bash from Python with `text=True` turns every newline into CR+LF. So does any text-mode write from Python on Windows, `Path.write_text` included. Write bytes, or open with `newline="\n"`, wherever a file's bytes matter. The box's shell will not run a script with CR bytes, and hashes are taken over bytes.
  - **Backslashes:** in the Bash tool, a doubled backslash reaches the shell as one, inside a heredoc too. Write any script that contains backslashes with the Write tool, and write Windows paths in commands with forward slashes. Every check asserts that it found something to check.
  - **`cd`:** a Bash `cd` into a subfolder can move the session's working directory for every later call. Use absolute paths, or `git -C`.
  - **`grep` and CR:** Git Bash's `grep` strips the CR at each line end unless given `-U`. Count CRLF with Python.
  - **Windows paths in `sha256sum`:** given a backslashed path, it prefixes its line with `\`. Pass forward-slashed paths.
  - **Transcripts:** a harness task's `%TEMP%` output file is empty while the agent runs. A transcript is read from the session's `subagents\` folder.
  - **Never start a process under `pythonw`,** or detached, on the desktop.
- **No helper agents.**
- **Your final message is your report,** or, for DEBRIS-I's phase 1, its hand-off. Its word limit is in your brief. If the harness refuses the write of a document your brief names, your final message is that document followed by the report, and the word limit then applies to the report alone.
- **Before you report,** stop any background work you started. End with what you did not do, and with anything your brief got wrong.

## READY, stated before the first pass

READY applies to DEBRIS-I and to every verifier's verdict. Every load-bearing claim must rest on one of:
- a measurement, with its command and output;
- a fetched source, cited by URL;
- arithmetic from labelled inputs.

Otherwise it is stated as a limit, in terms of the behaviour it concedes. A claim's domain and quantifier are claims, and so is a figure's definition. A number carried over from an earlier study keeps its definition, or it is re-measured.

**From rounds DEBRIS-B to DEBRIS-H:**
- **Every control states its pass and fail criteria before the data, and the code asserts them.** A control that fails as specified is reported as failed, whatever replaces it.
- **Every agreement claim states its tolerance before the data,** with its basis.
- **A measurement with no pass condition states its statistics, its configurations and its sample before the data.** I3's model gap, I5's rates and I6's compile are such measurements.
- **Every log names the SHA-256 of the script that wrote it,** and the criterion that script asserted.
  - Keep every version of a script that wrote a log, under a name carrying the first 12 hex digits of its hash, before you change it.
  - Never overwrite a log: number each run's log.
  - The manifest lists every version.
- **Every build prints the SHA-256 of every source it compiles,** and every compile of a cft source prints the source's SHA-256 and the image's.
- **An ESTIMATE names its basis and its range,** and is never added to a MEASURED figure without saying so.
- **A bound over many trials holds only when the trials are independent.** Say what varies from trial to trial.
- **A cause is claimed only when a run isolates it.** Otherwise it is inferred, and labelled so.
- **Every throughput figure names its configuration** (the kind or format, the workers, the lanes, the model, the priority) and the foreign load of its interval.
- **Every ratio of times says what it divides:** wall times or CPU times.

**New in this round:**
- **Every comparison names both sides exactly:** the program's format, image SHA-256 and depth; M1's kind and switches; the inputs' hashes; and the stage times.
- **Every mark is counted where it happens,** by format, routine and run.
  - **On the desktop,** every marked lane is replayed by the interpreter before its state is used.
  - **On the box** the interpreter cannot run. It needs mpmath for any program that holds `exp` (READ, `python\cft_golden\lang\interp.py`, `need_mpmath`), and the box's scripts use the standard library only. So a box run carries the executor's state on, and logs each mark with its lane, segment and the boundary state before it.
  - The lead copies those back, and the interpreter replays each marked lane-segment on the desktop from its boundary state. If the replay equals the executor's state, the run stands. If not, that lane's later states are void, and its run is redone from the replayed state.
  - **The redo is DEBRIS-I's, on the desktop, in phase 2,** from the replayed state to the run's end, with any mark in the redone run replayed at once. Phase 2's 15 CPU-minutes cover it: a lane-day is 6 to 11 CPU-seconds of executor time (ESTIMATE, "The design" §13). Past 10 lanes to redo, DEBRIS-I asks the lead first.
  - A gate's criterion is evaluated only on states that are unmarked or replayed equal (plan-verifier-I's D2).
- **No figure from the model-gap measurement is called an error** of the program or of M1. It is a difference between two models.

A verifier may reuse a run instead of re-running it only when all three of these hold:
- someone other than the author of the work made the run;
- its inputs are identical, file hashes included;
- the verifier re-runs from clean whatever it doubts.

The box's runs are the lead's, from DEBRIS-I's code. So their logs count as made by someone other than DEBRIS-I, but not as independent of DEBRIS-I's code.

Only a wrong answer sends work back: a false claim, a measurement or check that cannot fail, or code that does not build or does not do what its gate says it does. Everything else is a note the lead records, and a sentence that claims too much is narrowed at the merge.
- **Loop cap (Logan, 2026-10-15, carried through the lead's memory):** after three NOT READYs for narrowing reasons, the next pass blocks only on wrong answers.
- **Threat model (Logan, 2026-10-02):** each verifier's brief states one, and findings outside it do not reopen the loop.

## Logan's decisions (each default stands unless changed)

1. **Models:**
   - (a) **Opus for DEBRIS-I, Sonnet for verifier-I,** and Haiku for a merge-check. This is Logan's pairing for challenging work (2026-10-12): the round writes a propagator in a new language and holds it to two references;
   - (b) Sonnet for DEBRIS-I and Haiku for verifier-I.
   - Default: (a).
2. **The pin:**
   - (a) **cft-fp256 at 9e8ff270,** from an archive the lead makes in Phase 0, for the program and for M1's libcft alike. I0 holds M1 on it to M1 on 0aa997a3. It is the commit cft-fp256's lead named for our pin, and the one DEBRIS-J needs for `hip:N`'s depths;
   - (b) 0aa997a3 for M1, as since DEBRIS-E, and 9e8ff270 for the program;
   - (c) 5ac396d3, cft-fp256's main of 2026-11-20. On the CPU it is 9e8ff270's code (READ), and it adds the GPU's fixed tier, which DEBRIS-J could want.
   - Default: (a). DEBRIS-J may move to (c) with a check that its CPU files equal 9e8ff270's.
3. **The depth and the degree:**
   - (a) **a software depth of at most 512, and degree 7,** with M1's 28 bands if they fit and one band otherwise. Degree 8 is compiled once and its refusal reported;
   - (b) depths to 1,024, to keep M1's 28 bands or to try degree 8, at half `hip:N`'s lanes a launch.
   - Default: (a). If degree 7 does not fit with one band, the parcel asks the lead, and the lead asks Logan.
4. **The block:**
   - (a) **1 hour,** 240 steps in 6 segments of 40 (600 s), ending early at any DE421 sub-interval's end, which lies on the same 600 s grid;
   - (b) 10 minutes, one segment a run.
   - Default: (a). A shorter block makes the frame's bound easier to meet, and costs more runs.
5. **Formats:**
   - (a) **binary64, binary128 and binary256 in I1, I2 and I3,** and binary32 in I1 only;
   - (b) binary64 and binary256 only, as the week's plan named them.
   - Default: (a).
6. **I3's sample:**
   - (a) **64 objects of DEBRIS-H's seed, one day from its T_s.** The objects are drawn by a seed fixed in the script before the data, 16 from each of four perigee bands (under 400, 400 to 600, 600 to 800, and 800 km and over). Where a band holds fewer than 16, the rest come from the nearest band with objects to spare. The full run is the lead's, on the box; the desktop runs 8 of them for 2 hours, as a functional test;
   - (b) 16 objects, on the desktop only.
   - Default: (a).
7. **Part B, DEBRIS-H's follow-ups:**
   - (a) **two of the three:** the skipped slot's log line, and each request's time to its first byte. Each is a copy of DEBRIS-H's file with the change, tested against DEBRIS-H's local server. The seed fit through libcft's correctly rounded functions is left for the next round that re-seeds the service. Its cost is the reason: libcft's host exp costs about 0.14 ms at binary64 (DEBRIS-D, MEASURED), so a fit's propagations would cost minutes an object where they now cost seconds (ESTIMATE);
   - (b) as (a), and the fit's option built and run on 2 of H6's pairs on each machine, with the box's cost a fit measured in I5's window;
   - (c) none in this round.
   - Default: (a).
8. **The box's time:**
   - (a) **I0's box build, I3's full run and I6's box compile as short work,** or under a `notice` or `shared` booking when longer, at nice 19. I5 in one `sensitive` window of at most 2 hours, booked by the lead in the day, after the hand-off;
   - (b) as (a), with I3 in the `sensitive` window too.
   - Default: (a). If no `sensitive` window can be had in the round's days, I5 waits, and the lead tells Logan. Conflicts are never forced.
9. **Scope and budgets:**
   - (a) **One round:**
     - DEBRIS-I's phase 1: 8 hours of wall time and 60 CPU-minutes on the desktop. Its fixes after a failed box run: 2 hours and 15 CPU-minutes in all. Its phase 2: 2 hours and 15 CPU-minutes;
     - it messages the lead before passing any of these, and before any single desktop run it expects to pass 5 CPU-minutes. I6's compile is the one exception: one process, up to 30 CPU-minutes inside phase 1's 60, announced when it starts;
     - verifier-I: 3 hours and 25 CPU-minutes on the desktop, and up to 30 CPU-minutes on the box, run by the lead at its request;
     - a merge-check: 25 minutes.
     - **If time runs short,** the lead cuts in this order:
       1. part B;
       2. I6;
       3. I4's tides;
       4. binary128 in I2 and I3;
       5. I3's sample, from 64 objects to 16.

       I0, I1, I2 and I3 at binary64 and binary256, the model gap and I5 are kept.
   - (b) **Two rounds:** the program and I1 to I4 first; I3's day, I5 and I6 in a second.
   - Default: (a). For scale, DEBRIS-H's phase 1 used about 38 of its 50 desktop CPU-minutes.
10. **Outputs and the push:** the lead commits after verification and the merge. Pushing to the public repository waits for Logan's word.
11. **Per-object data:** every boundary state of I3, every per-object table and the sample's list stay in the ledger's `debris-i\`. The repository gets the rules, the counts, the hashes and the aggregates, as in DEBRIS-F to DEBRIS-H.

## Not in this round

- **Any GPU,** WSL distro or card, and the Arc A750. DEBRIS-J takes the program to a card.
- **A certificate,** written or audited.
- **Radiation pressure in the program,** and M1's 28 bands if capacity refuses them. The model gap prices both.
- **Any change to M1's library.** `src\` stays byte for byte as at commit 1646c96. New code goes in `tests\`.
- **The service,** the fetcher's live runs, CelesTrak, and DEBRIS-H's seed fit (decision 7).
- **A new T3** for co-planar fragments, and the SATCAT request for seed index 1178 (the week's decision 4).
- **Any download** or account.

---

## Brief: DEBRIS-I

You are build parcel **DEBRIS-I** in cft-debris, a project for space-debris tracking and simulation. Its folder, `C:\Users\logan\source\repos\cft-debris`, is a public git repository under the MIT licence.

You write M1's force model as a cft program, without radiation pressure:
- compiled by cftc from cft-fp256's archive at 9e8ff270;
- run on libcft's software executor;
- held bit for bit to cftc's reference interpreter, and to M1, the C propagator, set to the same forces.

You also prepare the box's runs, which the lead makes: a day of 64 objects, and the rates. Then, after the lead's runs, you analyse their records and write the build report. You never connect to the box, and you touch no GPU. You commit nothing: the lead commits after verification.

**Two phases.**
- **Phase 1:** 8 hours of wall time and 60 CPU-minutes on the desktop. It ends with your hand-off, your final message, under 700 words:
  - the files the lead stages to the box, with their SHA-256, and the run folder's layout;
  - the exact commands in order, each with its expected wall time (ESTIMATE) and what it must print;
  - what is per-object and must come back to the ledger, not the repository.
- **Fixes:** if a box run fails, the lead resumes you with its log. Fix, re-test on the desktop, and hand off again: up to 2 hours and 15 CPU-minutes in all.
- **Phase 2:** 2 hours and 15 CPU-minutes. The lead resumes you when the box's aggregate logs are in `studies\debris-i\box\` and its per-object files are in the ledger's `debris-i\box\`. First replay every mark the box's runs logged, under "READY"'s rule, and redo any lane whose replay differs. Then evaluate I3 and I5 from the records, and write the build report. Your final message then is your report.
- Message the lead before passing any budget, and before any single desktop run you expect to pass 5 CPU-minutes. I6's compile is the exception: one process, up to 30 CPU-minutes inside the 60, announced when it starts. At DEBRIS-D's rates, a day of one object at binary256 is about 6 to 11 CPU-seconds of executor time on the desktop (ESTIMATE: 5,760 steps of plan-verifier-I's 15,755 instructions, at 69.8 to 124.6 ns). M1 at cft256 with the program's forces is about 30 to 70 CPU-seconds (ESTIMATE: its full model takes 86,400 / 299 = 289 s an object-day on a box worker, from G4, and without radiation pressure's inverse sines and cosine, and at degree 7, it takes a quarter to a tenth of that). So hold desktop runs to a few objects and hours.

**Start here:**
1. This plan, `C:\Users\logan\source\repos\cft-debris\studies\DEBRIS-I-plan.md`: Logan's words, the design and its reasons, and what the round starts from.
2. DEBRIS-D: `studies\DEBRIS-D-architecture.md` (Q2 to Q5 and Q8, with its narrowings); `studies\debris-d\q2\gen_field.py`, `studies\debris-d\q2\q2_first_test.py` and `studies\debris-d\tools\seqrun.c`.
3. M1:
   - `src\`;
   - `tests\m1run.c`, `tests\m1f.c`, `tests\build_f.sh`, `tests\e4_gate.py`, `tests\e5_gate.py` and `tests\f3_gate.py`;
   - `studies\DEBRIS-E-build.md` and `studies\DEBRIS-F-build.md`, each narrowed at its merge.
4. cft-fp256, extracted from `cft-debris-ledger\tools\cft-fp256-9e8ff270.tar` into your scratch: `docs\LANGUAGE.md`, `docs\HOSTAPI.md`, `python\cftc\`, the reference interpreter, and `host\`.
5. `lead.md` in the ledger: Phase 0 and the archive's SHA-256.

**Where it goes:**
- `tests\`: the new code. `src\` stays byte for byte as at commit 1646c96, and your builds assert it. Reuse earlier code by copying it into new files with a note of where it came from; earlier files stay unchanged.
- `studies\debris-i\`: the logs, the records and the generated sources (data-free), with a `MANIFEST.sha256` over them. The lead puts the box's aggregate logs in `studies\debris-i\box\`.
- `studies\DEBRIS-I-build.md`: the build report.
- `cft-debris-ledger\debris-i\`: every output that names an object or holds its state.
- **In your scratch only:** cft-fp256's sources, libcft's build, every image and bank, and every executable.
- **Paths:** every script takes its paths from its arguments or its run folder, and none hard-codes a home folder.

**I-a. The generator:** `tests\i_gen.py`.
- **It writes the program's cft source** for a degree N, a format, a drag variant (M1's 28 bands, or one band), the frame's form and the layout of the run's values (bank or lane params).
- **It also writes the part systems I2 needs:** one small `map` system per part, computing that part from given inputs, with the same expressions the program uses.
- **Every data value is a `param` or `lane param`,** with a default the source states without data, and the driver fills it per run from the downloads and the ledger. So the sources go in `studies\debris-i\systems\`.
  - **This covers every constant too:** EIGEN-6C4's GM and radius, M1's constants (`src\m1_consts.h`), the bands' values, and every coefficient. The source holds no number but the step, 15 s, and the small exact integers and rationals of its own formulas, such as 2 and 1/2 (plan-verifier-I's D6).
  - **Every value the driver fills is correctly rounded at the run's format,** from its decimal string or exactly from a binary value. Nothing goes through binary64, or through a literal of fewer than 80 significant digits. DEBRIS-D's `lit()` writes 40, about 2^-133 of the value, which I2 at 2^-200 would catch (plan-verifier-I's note).
- **Every compile is recorded:** the source's and image's SHA-256, cftc's command, and the manifest's counts (instructions by class, bank slots, scratch slots, depth and features), in a table in `studies\debris-i\`.
- **The model,** term by term as M1 computes it (READ `src\m1_physics.h`):
  - the central term (`ph_central`);
  - degrees 2 to N in the Earth-fixed frame (`ph_grav`'s model; your form and its operation order may differ, as DEBRIS-D's did);
  - the Sun and the Moon as point masses (`ph_third`);
  - their geocentric positions from DE421's series (`ph_series` and `ph_bodies`: τ from t, Clenshaw from the highest coefficient down, the Earth as EMB − Moon/(1 + EMRAT));
  - drag (`ph_drag_g`, with the frame's Ω).
  - M1's constants (`src\m1_consts.h`) and EIGEN-6C4's GM and radius as M1 reads them, and M1's sum order where you can keep it. No radiation pressure.
- **The degree:** design decision 3. Report each variant you compiled, with its manifest or its refusal by name.

**I-b. The run's blocks.** For each run the driver computes, on the host:
- **the frame's form.** It is your design, derived from M1's frame (`frame` = 1, DEBRIS-H's `frame_h0.bin`, by M1's own `frame_at`), and it must meet I2(e)'s bound. Prefer a form whose routines cannot mark, such as polynomials in t;
- **DE421's coefficients** for the run's sub-interval of each of the three series;
- **the atmosphere's values,** and each lane's `bc`;
- **t's start.**

A run never crosses a DE421 sub-interval. Its length is decision 4's block.

**I-c. The driver:** `tests\i_run.c`, from DEBRIS-D's `studies\debris-d\tools\seqrun.c`, with a note.
- It opens libcft's software executor at the image's depth, and loads the image and its bank.
- It fills the run's params and lane params, and runs the run segment by segment (40 steps).
- It writes every boundary state and each lane's flags, and lists marked lanes for the replay. Runs follow one another, carrying the state.
- **Lane params ride in the scratch, after the state,** so a carried scratch carries them too. The driver rewrites every lane param at each run's start, whether or not its value changed (plan-verifier-I's note).
- **On the box,** it logs each mark with its lane, its segment and the boundary state before it, for the desktop's replay ("READY").
- It builds on the desktop and on the box (gcc, Linux).
- **Workers for I5:** the driver runs a slice of the objects in 64-lane batches. A small standard-library harness starts W workers at nice 19, pinned as in DEBRIS-G's G4, and records each run's wall time, its object-seconds and the foreign load from `/proc/stat`, as `tests\g_harness.py` does.

**M1's side:** `tests\m1i.c`, from `tests\m1run.c`, with a note, linking M1's `src\` unchanged.
- Its kernels at given inputs (I2), and its trajectories with the switches set to the program's forces (I3), at every kind, from given states.
- For I3's model gap, also M1's full model (degree 20, 28 bands, radiation pressure, `frame` = 1), at native64 and cft64.

**The harness:** `tests\i_harness.py`, standard library only wherever it runs on the box. It orchestrates the gates and writes their logs.

**The gates.** For each gate: write its criteria into its script before its data, assert them in code, and give it a negative control that must fail as specified. The NaN rule holds throughout, as in DEBRIS-E: non-NaN results agree bit for bit where bits are the criterion, and NaN results agree as NaNs.

- **I0. The pin and the builds** (desktop yours; box the lead's).
  - Every source's SHA-256 is printed. `src\` is byte-identical to commit 1646c96.
  - The archive's SHA-256 equals `lead.md`'s.
  - libcft, cftc and the interpreter come from it.
  - **M1 on 9e8ff270's libcft equals M1 on 0aa997a3's,** bit for bit: 16 objects of the test seed, 240 steps, at each of the six kinds, from the same states, with M1's full model and `frame` = 1.
  - **On the box (the lead's):** the same builds from the same archive, M1's equality there, and I1's runs repeated on the box's executor, equal to the desktop's bit for bit, states and flags. DEBRIS-J holds a card to these.
  - **Controls:**
    - C1: a copy of one source changed by one byte must fail the source check;
    - C2: one state moved by one ulp in one of the two runs must fail the equality.
- **I1. The program against its definition** (desktop).
  - **The systems:** the program at degree 2 and at your N, and every part system, at binary32, binary64, binary128 and binary256.
  - **The runs:** 16 lanes from the test seed, 160 steps in two runs of 80 (so a run boundary is crossed), each run in two segments of 40. The run's values are from the test seed's T_s. plan-verifier-I's rough figure for the interpreter, about 0.01 CPU-seconds a lane-step at binary256, puts this at under a minute a format.
  - **Criterion:** after every segment, every lane's state equals the interpreter's bit for bit, and its lane byte's five flags equal the definition's (DEBRIS-D's marked-lane rule). Every mark is counted, and every marked lane replayed.
  - **Controls:**
    - C3: the interpreter given GM one ulp up, as the run's value, must differ from the executor's unplanted run somewhere (DEBRIS-D's (c), with GM now a parameter);
    - C4: one run given the Moon's series of the following sub-interval must change every lane's state at binary64. This shows that the run's values are read. A plant of one ulp in one coefficient would not bite: it moves a state by far less than its last bit (COMPUTED).
- **I2. Part by part, against M1's kernels** (desktop).
  - **The inputs:** 1,000 states (DEBRIS-E's E1 recipe for LEO states, plus the test seed's 64) and the run's values at given stage times. Among the stage times are some on each side of 2026-11-20 00:00 TDB, where the Moon's sub-interval changes, and one exactly on it, where M1 takes the later sub-interval (READ, `src\de421.c`, `m1_de_locate`). So (d) tests the driver's choice of sub-interval, which must be M1's.
  - **The parts:**
    - (a) the central term;
    - (b) degrees 2 to N;
    - (c) the Sun's and the Moon's tides;
    - (d) the geocentric Sun and Moon;
    - (e) the frame;
    - (f) drag, with Ω.
  - **Evaluation:** each by the program's part system on the executor at binary64, binary128 and binary256, and by M1's kernel (`m1_vt`) at the matching kind, cft64, cft128 and cft256, with native64 reported beside.
  - **Criterion for (a) to (d) and (f), at binary256:** |program − M1| ≤ 2^-200 × the part's largest magnitude over the inputs, component by component.
    - The basis: each part is at most about 2^20 operations, each rounded once at 2^-237, so different orders leave at most about 2^-217 (COMPUTED). Any wrong term, coefficient, sign or unit moves a part by far more.
    - At binary128 the same with 2^-80 in place of 2^-200, on the same basis at 2^-113 (2^-93).
    - Both catch a coefficient taken from binary64 instead of from its decimal string, which errs by about 1e-16 of its value.
    - At binary64 the differences are a measurement, in ulps: median and largest per part. Your forms' operation order may differ from M1's, and the program's binary64 is held by I1 and I3.
  - **Criterion for (e), at binary256,** at every stage time of I3's desktop runs and of 1,000 stage times drawn across the frame table's window: every element of the program's M within 1e-12 of M1's `frame_at`, and Ω within 1e-14 rad/s. The design gives the basis.
  - **Controls,** one a part (plan-verifier-I's D1), each at binary256 unless named:
    - C5: one gravity coefficient scaled by (1 + 2^-100) must fail (b);
    - C6: the central term's GM scaled by (1 + 2^-100) must fail (a);
    - C7: the Moon's GM scaled by (1 + 2^-100) must fail (c);
    - C8: the largest of the Moon's Chebyshev coefficients scaled by (1 + 2^-100) must fail (d);
    - C9: one band's ρ0 scaled by (1 + 2^-100) must fail (f) on the inputs in that band. The band is the one holding the most inputs, and the script asserts it holds at least 10;
    - C10: every gravity coefficient taken through binary64 instead of from its decimal string must fail (b) at binary256 and at binary128. This tests the claim made for the two tolerances above;
    - C11: the frame's block of the hour after must fail (e).
    - Each plant moves its part by about 2^-100 of the planted term or more, against tolerances of 2^-200 and 2^-80 of the part (COMPUTED for each in the script, which asserts the margin before the data).
- **I3. A day, against M1** (desktop as a functional test; the full run on the box, the lead's).
  - **The sample:** decision 6.
  - **Each object's start:** its seed state at T_s, propagated one day (5,760 steps) in runs of the block's length:
    - by the program at binary64, binary128 and binary256;
    - by M1 with the program's forces at native64, cft64, cft128 and cft256.
  - **Criterion:** at every segment boundary, for every object, |program at p − M1 at the matching kind| ≤ T_round(p, n) + T_frame. Positions use S = 7e6 m and T_frame = 1e-3 m; velocities use S = 8e3 m/s and T_frame = 1e-6 m/s.
    - T_round(p, n) = 64 · n · 2^-p · S: DEBRIS-D's form, with n the steps so far and p the precision (53, 113 or 237).
    - The pairs: binary64 against cft64, binary128 against cft128, binary256 against cft256. binary64 against native64 is reported beside.
  - **The basis:**
    - at binary64, T_round after a day is about 2.9e-4 m (COMPUTED). Binary64's own rounding over a day was 1.2e-6 to 1.3e-5 m in DEBRIS-D's Q4;
    - at binary256, T_round is about 1e-59 m, so T_frame carries the gate. It is 20 times the frame term's crude bound of 5e-5 m;
    - for velocities, T_frame is about the mean motion (1.1e-3 rad/s at 400 km, COMPUTED) times T_frame for positions, since an orbit links the two errors.
  - **t is held exactly:** at every boundary, the program's t equals M1's host stage time.
  - **Marks:** the box's run logs them, and the desktop replays them, under "READY"'s rule.
  - **Controls:**
    - C12: M1 with degree 6 against the program at degree 7 must fail at binary256;
    - C13: one run of the program given the frame's block of the hour before must fail.
  - **The measurements, fixed now:**
    - the share of each tolerance used, as median and largest over objects and boundaries;
    - the marks, by format and routine;
    - the program's binary64 against its binary256: the median and largest position difference at 1, 6 and 24 hours.
  - **The model gap, fixed now** (M1 alone, native64 and cft64; no criterion). M1 with the program's forces against M1's full model (degree 20, 28 bands, radiation pressure, `frame` = 1), on the same 64 objects:
    - the median and largest position difference at 1, 6 and 24 hours, and its radial, along-track and cross-track parts;
    - by perigee band;
    - with each difference also taken one force at a time: degree N against 20; one band against 28, if the program has one; radiation pressure off against on.
- **I4. The authorities, through the program's route** (desktop).
  - **(a) `testpo.421`:** the points whose pair the program's ephemeris part computes (the Moon from the Earth, the Sun from the Earth, and their reverses), at their epochs, by the part system at binary64 and binary256. They must lie within 1e-13 AU (E5's tolerance). Its control is E5's P2b: a plant in the coordinate a point tests.
  - **(b) Lasser et al.'s Sun and Moon tides** (`03directTideSun_icrf.txt`, `03directTideMoon_icrf.txt`), at every tenth epoch, by the program's tide part with its own ephemeris. They must lie within 1e-11 m/s² (E4's tolerance). Its control: the Moon's GM scaled by (1 + 1e-3) must fail. The Moon's tide on a LEO object is about 1.2e-6 m/s² (COMPUTED, 2 GM r / d³), so the plant moves it by about 1e-9, a hundred times the tolerance.
  - **Lasser et al.'s gravity is to degree 180,** so it cannot hold a field of degree N. I2(b) holds the program's field to M1's, which passed E4. The program's difference from Lasser's values is reported, as truncation, with no criterion.
- **I5. The rate on the box** (the lead's runs, in decision 8's `sensitive` window). A measurement. Its configurations, statistics and validity criteria are fixed in its script before the data, as DEBRIS-G's G4 did:
  - **the program** at binary64, binary128 and binary256, on 1, 18 and 36 workers, each worker carrying one 64-lane batch of DEBRIS-H's seed (64, 1,152 and 2,304 objects in all), as G4 did;
  - **M1 with the program's forces** at native64, cft64, cft128 and cft256, on the same configurations;
  - **the durations:** each run at least 60 s of wall time and at least one whole block a worker, chosen so that every run fits one window of 2 hours, and fixed in the script before the data. At native64 a block is about 0.18 s of work (plan-verifier-I, from G4's rate), so its 60 s is about 330 blocks, some 14 days of model time. M1 then crosses DE421's boundaries itself, and the frame table covers the time;
  - **a check that worker 0's final states hash equal** across 1, 18 and 36 workers, for each format and kind. Worker 0 carries the same first 64 objects of the seed in every configuration, as in G4's D checks;
  - **the foreign load** from `/proc/stat` over each run, with the run void above 2%;
  - **the statistics:** object-seconds a second for each run, and the ratios, rate against rate, with M1 at the program's forces and at its full model (G4's figures).
- **I6. Degree 20 as lane params** (desktop, then the box if needed; a measurement).
  - cftc on the generator's degree-20 program, with the gravity coefficients as lane params, for `sw:2048`, then `sw:4096` if 2,048 refuses it.
  - **The expectation** (plan-verifier-I's note): 1,762 lane params and at least 256 spills pass 2,048, so `sw:2048` is likely refused. No `hip:N` depth reaches 4,096, so a program that needs it is a CPU program only. Either answer is the finding.
  - It stops at 30 CPU-minutes on the desktop, inside phase 1's 60. If it has not finished, hand the lead its exact command, and the lead runs it on the box at nice 19 for up to 3 hours.
  - **Recorded:** whether it compiles, its time, its instructions and slots, or its refusal by name.
  - If it compiles within 2,048 slots, run it under I1's criterion on 4 lanes for one segment of 40 steps at binary64.
- **Part B** (decision 7; desktop). B1, the seed fit through libcft's functions, is decision 7's (b), and is not in the default.
  - **B2. The skipped slot's log line:** `tests\i_service.py`, a copy of `tests\h_service.py`.
    - **Why it is more than a line** (plan-verifier-I's D3, READ): the scheduler returns early while the stop file exists, before it computes the slot. At its first tick after a rename, it logs every unattempted slot since the last attempted one as "missed while the service was down". Nothing records which slots fell due under the stop.
    - **The change:** while the stop file exists, the scheduler still computes the slot, and logs each slot that falls due as skipped under the stop file, once. A slot that fell due while the service was not running keeps the old line.
    - Its test plants a stop, two slots falling due under it, a rename and the scheduler's next tick, and checks both texts.
    - Control: the unchanged copy must print the old text for the slots under the stop.
  - **B3. The time to first byte:** `tests\i_fetch.py`, a copy of `tests\h_fetch.py` that logs each request's time to its first byte and to its last.
    - **Its server** is `tests\i3_server.py`, a copy of DEBRIS-H's `tests\h3_server.py` with one option added: a delay after the response's first byte. DEBRIS-H's server sleeps only before it responds (READ, its `do_GET`; plan-verifier-I's D4). It runs on 127.0.0.1 only, and is stopped by its PID.
    - With a planted delay of 5 s before the first byte, the fetcher must log at least 5 s. A response with no delay must log under 1 s.
    - Control: with the delay moved after the first byte, the time to first byte must stay under 1 s and the time to the last must pass 5 s.
  - Neither copy is run live. DEBRIS-H's files stay unchanged.

**Phase 2's analysis:** `tests\i_analyze.py` evaluates I3's criteria from the box's records, and computes I3's measurements, the model gap and I5's statistics. Its log holds the aggregates; per-object tables stay in the ledger.

**The build report,** `studies\DEBRIS-I-build.md`, covers:
- what was built, and how to build and run it;
- the generator's variants, with their manifests and refusals;
- the frame's form and the layout;
- each gate's criteria and result;
- the model gap, the rates and the degree-20 probe;
- what DEBRIS-J inherits;
- the limits.

**Your report** (phase 2's final message, under 900 words): what you built, each gate's result, the measurements, what you did not do, and anything this brief got wrong. Label every figure.

## Brief: verifier-I (completed when DEBRIS-I reports)

You are **verifier-I** in cft-debris. Your job is to disconfirm DEBRIS-I's build, its gates and the box's records, never to fix them. Edit no file outside your scratch. You never connect to the box: any box run you need, the lead runs from your script.

**Threat model.** A wrong answer in DEBRIS-I's work:
- a check that cannot fail;
- a program that differs from its definition;
- a part or a trajectory compared at different inputs, times, frames or kinds;
- a tolerance not as stated, or fixed after the data;
- a model difference hidden by the comparison;
- a rate not as defined, or measured outside its window;
- third-party data, an image, or per-object data in the repository.

Findings outside this model are notes and do not reopen the loop.

**Attack these, in this order:**
1. **I1:** re-run the interpreter against the executor on 4 lanes of your own choosing, at binary64 and binary256, from DEBRIS-I's images and sources.
2. **I2:** recompute 20 values of parts (b) and (c) at binary256 with code of your own, in mpmath at 300 digits, independent of both M1 and the program. Compare with both.
3. **I3's configuration:** M1's switches against the program's model, term by term; the stage times; and the tolerances in the script against this plan.
4. **The controls bite:** re-run C3 to C13 on the desktop.
5. **The frame's bound:** recompute the program's M and Ω against M1's `frame_at` at 50 stage times of your own.
6. **The sources carry no data,** and no image or bank is in the repository.
7. **I5's records:** the window, the foreign loads, the validity checks and the ratios.
8. **The repository:** no catalogue number, state, data value or personal string in any file under `studies\` or `tests\`.

**Budget:** 3 hours of wall time and 25 CPU-minutes on the desktop, and up to 30 CPU-minutes on the box. Message the lead before passing either. Your booking is the lead's notice: it already covers your desktop runs.

**Report:** your final message, under 1,200 words. Give each attack's verdict (confirmed, defect, or not determined) with its evidence. For every defect, give the exact passage and what it should say.

## What changed from draft 1 (plan-verifier-I's findings, answered)

The lead checked each finding's evidence before answering it:
- `python\cft_golden\lang\interp.py`'s `need_mpmath` at 9e8ff270, and the box's survey;
- `tests\h_service.py`'s scheduler and `tests\h3_server.py`'s `do_GET`;
- cftc's `--steps` in `python\cftc\__main__.py`;
- `docs\HOSTAPI.md`'s lanes a launch;
- DEBRIS-D's table of the sequencer's cost.

Every defect was upheld.

- **D1, controls for every part of I2.** C6 to C10 are new: the central GM, the Moon's GM, a Chebyshev coefficient, a band's ρ0, and every coefficient through binary64. The last tests the claim made for the two tolerances. The frame's control is now C11, and I3's are C12 and C13.
- **D2, marks on the box.** The interpreter needs mpmath for `exp`, and the box's scripts are standard library only. "READY" now says how a box run's marks are logged, replayed on the desktop in phase 2, and how a lane whose replay differs is voided and redone. A gate is evaluated only on states that are unmarked or replayed equal.
- **D3, B2.** The scheduler returns before it computes the slot while the stop file exists, so the copy needs new state, not a new line. B2 now says so, and its test and control cover slots under the stop.
- **D4, B3's server.** DEBRIS-H's server sleeps only before responding. B3 now has its own copy, `tests\i3_server.py`, with a delay after the first byte.
- **D5, blocks that end early.** cftc fixes an image's steps a segment, and 24-step segments from 22:50 do not meet midnight. Segments are now 40 steps, 600 s, on the grid where every run starts and every DE421 sub-interval begins.
  - I3's day crosses no boundary, so I2(d) now tests the driver's choice of sub-interval on both sides of 2026-11-20 00:00 TDB.
  - I1's runs are now 80 steps, two segments each.
- **D6, constants.** Every constant is now a parameter, GM and the radius among them. Every value filled is correctly rounded from its decimal string, never through binary64 or a literal under 80 digits.

**Notes taken:**
- **Capacity.**
  - The probe's figures are in "The design" §3. Degree 8 does not fit at depth 512, so decision 3 now names degree 7, with the fallback of one band before anything else, and asks before any lower degree.
  - The 559 sentence now says it leaves the frame and the bands out.
  - The rate's ESTIMATE now rests on the probe's 15,755 instructions and DEBRIS-D's binary256 costs. It is 10 to 30 times, and the object-day 6 to 11 CPU-seconds.
- **Lane params** ride in the carried scratch, so the driver rewrites them at every run.
- **I6:** the likely refusal at `sw:2048` and its meaning are stated, and its 30 CPU-minutes are inside the 60.
- **I5:** the hash check names worker 0's batch, and the durations note native64's 14 model days.
- **The rest:**
  - B1 is named;
  - Phase 0's `git archive` is the lead's;
  - the time probe is cited in "The design" §8;
  - HOSTAPI's bound is quoted beside the relayed figures;
  - the re-check's message gives the command that reads a seed's two header lines and no row (its brief said "headers only", and its `head -c` printed about ten rows into its context, though it copied none).

## What changed from draft 2 (plan-verifier-I's re-check, answered)

The re-check found no blocker, and confirmed each of draft 2's answers, the ESTIMATEs' arithmetic and the controls' margins. Its one defect and four notes are answered:
- **The defect: where a voided lane is redone.** "READY" now says it is DEBRIS-I's, on the desktop, in phase 2. Any mark in the redone run is replayed at once. Phase 2's budget covers it, and past 10 lanes DEBRIS-I asks first.
- **The notes:**
  - I2(d) now has a stage time exactly at 2026-11-20 00:00 TDB, where M1 takes the later sub-interval. The lead read `src\de421.c`'s `m1_de_locate`, which confirms it.
    - That reading also showed a limit, now in "The design" §4. A block that ends at a boundary evaluates its last stage on the earlier sub-interval, where M1 takes the later. I3's day crosses no boundary.
  - The literal rule now names the step, 15 s, beside the formulas' small exact numbers.
  - 15,755 is the probe image's count, not a measured count a step, and the plan says so.
  - "At least 60 in the bank" is now "60", with the refused 40 and the untried 50 named.

## What earlier rounds taught, applied here

- **A criterion its script never evaluated** (DEBRIS-G's F9 test): every criterion here is asserted in code.
- **A positive control that cannot fire** (DEBRIS-D's tiny-argument class; DEBRIS-E's E5 plant in the wrong coordinate): every control here names the property that makes it bite.
- **Third-party data in generated sources** (DEBRIS-D kept its fields in scratch): here every data value is a parameter, so the sources carry none.
- **Too many processes on the shared desktop** (DEBRIS-G): the limit of 4 counts every child process.
- **Script versions overwritten before they were kept** (DEBRIS-G): keep each version before changing it.
- **A desktop run past its estimate** (DEBRIS-H's H6, 18.8 CPU-minutes against an ESTIMATE of 9 to 11): announce any run past 5 CPU-minutes before it starts, with its basis.
- **The build report edited before its as-reported copy was kept** (the lead, DEBRIS-G): the lead copies every report before any edit.
- **UTC read as local** (the lead, DEBRIS-H's 16:57 entry): every time in this round's logs names its scale.

## The lead's slips so far

1. **The week's closing message at 05:12** told Logan that the box's folders to be removed were "all of it already verified in the ledger". 94,369 of their 103,306 files were not; the lead copied them to the ledger first, then removed the folders (`lead.md` 07:00).
2. **The week's plan offered "a probe of degree 20 through index tables if cftc can express it".** The language has no tables (READ now), so I6 tries lane params instead. The lead had not read the language's definition before writing that line.
3. **The checker's first version,** which wrote its log 001, was edited before it was kept. The log's first line names its SHA-256. The versions behind logs 002 and later are kept.
4. **Draft 1's rate ESTIMATE, 3 to 30 times, did not follow from its own basis.** Taken at face value, that basis gives about 12 to 60. Draft 2 recomputes it from plan-verifier-I's measured instruction count and DEBRIS-D's binary256 costs.
5. **Draft 1's segments of 24 steps** could not end a block on a DE421 boundary (plan-verifier-I's D5). The lead had taken them from DEBRIS-D's design without checking them against the run's start.
