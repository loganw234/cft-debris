# DEBRIS-D: a real-time, wide-precision debris propagator on consumer GPUs, as cft programs, priced (plan of record, draft 5)

Drafted 2026-11-12 by cft-debris's lead for Logan's approval.
- **Draft 2** took in cft-fp256's lead's two answers of 2026-11-12. Both are filed verbatim in the ledger's `relayed\`, and every passage they cite was read at cft-fp256's commit 0aa997a3 (`lead.md`, 19:36).
- **Draft 3** takes in two things:
  - Logan's word on the route (`lead.md`, 19:59): cft programs, and certificates when able;
  - plan-verifier-D's report on draft 2 (Sonnet, filed verbatim in the ledger's `filed\`): no blockers, nine defects and ten notes, each answered in "What changed from draft 2" below.
- **Draft 4** answers plan-verifier-D's scoped re-check of draft 3, also filed verbatim in `filed\`: no blockers, three defects and five notes, each answered in "What changed from draft 3" below.
- **Draft 5** takes in Logan's word on certificates (`lead.md`, 20:30): design for them, and implement none yet, so that the GPU route is not held back. A feature request for certificates on the GPU backend went to cft-fp256's lead the same evening. Drafts 4 and 5 have had only the lead's check.
- **The lead's own check** ran before any verifier saw the plan: `cft-debris-ledger\dispatch\check_plan_d.py` (log 001), 185 checks with 0 failures, controls included. It covered every path, cited passage and carried figure, and the three web sources were fetched. Its corrections are listed in "The lead's slips so far". Draft 3's own re-check is recorded in `lead.md`.
- Nothing has been dispatched, and nothing has been downloaded.

## The question, in Logan's words

- **The goal** (2026-11-12): "One ideal goal would be a simulation capable of realtime (or slightly faster) simulation on a consumer card, so a 24x7 sim could run on a local box here for long run tests, validating itself with the open datasets update intervals, scaling tracked objects as the main scaling parameter presumably. High performance cards like the MI300X could then be used for higher density or faster/concurrent runs"
- **The precision** (2026-11-12): "Id also prefer to continue to utilize the higher precisions, simply to be a usecase for cft-fp256 as well"
- **The route** (2026-11-12, answering draft 2's route through cft-fp256's language): "*Yes if possible utilize cft programs, as well as generating certificates when able (they still dont cover all use cases)"
- **Certificates** (2026-11-12, answering draft 4): "*Certificate support can be built for but not implemented in order to still have gpu capability at the moment. You can send a feature request to cft-fp256 regarding the certificate update to bring support up to the gpu backend"
- **The lead** (2026-11-12): "You can carry on with the next round on this session as the lead. Context will compact and you can carry the lead role through development". And: "You may send a message to the cft-fp256 session if youd like to clarify future feature plans or make requests".

## What DEBRIS-D is for

DEBRIS-B and DEBRIS-C measured what a debris model stands on and what it costs. They made no recommendation. Logan's goal now names a product: a propagator that runs around the clock, in real time or faster, on a consumer card in this house. It is to:
- check itself against the open data as they update;
- scale with the number of tracked objects;
- run at libcft's wide formats, as a use case for cft-fp256;
- be written as cft programs, compiled by cftc and run by libcft's sequencer, wherever the language reaches;
- be designed for cft-fp256's certificates, so that its runs can be certified once certificates reach the GPU backend. None is implemented yet, so that the GPU route is not held back (Logan);
- use the MI300X for denser or concurrent runs.

DEBRIS-D turns that goal into an architecture and a first build, priced from measurements. It builds no part of the propagator. It ends with a development plan for Logan to approve or change.

| question | what it settles | the evidence it rests on |
|---|---|---|
| **Q1. The workload, by operation class** | what one force evaluation and one object-day cost: FMA-class operations, divides, square roots, and each transcendental | counting builds of DEBRIS-B's and DEBRIS-C's kernels; the density models counted in their source |
| **Q2. The route: cft programs, designed for certificates** | how much of the force model the language expresses as it stands; what the design keeps so that certificates can state its runs later; what neither covers, by name | cft-fp256's documents at the pinned commit; a first compiled system, run on this CPU |
| **Q3. The price of each operation class, by format** | binary64, binary128 and binary256, on this CPU through libcft and on the consumer cards | a libcft build timed here; the images' instruction counts; GPU-A's measured rates |
| **Q4. The integrator** | the fixed-step methods the language offers against IAS15: steps and error per object-day at matched accuracy, and under which licence | step counts and errors measured on the CPU; the licences READ |
| **Q5. The ladder** | how many objects each card runs in real time, at each format and tier, at ESA's population sizes | COMPUTED from Q1 to Q4, by GPU-E's method |
| **Q6. The density model** | which model, at what precision, under what licence, at what cost, and whether the language expresses it | Q1 to Q3; the licences READ |
| **Q7. The 24/7 loop** | which open data at what cadence, checked by what statistic; what divergence triggers; how a day is replayed, and how it would be certified | the sources READ; DEBRIS-C's M4 criteria; libcft's determinism; the certificates' documents |
| **Q8. The first build** | milestones, gates, owners, dependencies and costs, and the requests for cft-fp256, for Logan to decide | Q1 to Q7 |

**What the wide formats are for here.** DEBRIS-B found that "Binary64 is not the limit in any regime tabulated here": near-circular LEO, MEO and GEO, with no GTO or HEO row (COMPUTED there from measured coefficients). It also found binary128 "enough for every use found", and binary256 "needed only to rule binary128 itself". So binary128 and binary256 are used by choice, as cft-fp256's use case. The study prices them honestly, and claims for them only what they measurably buy:
- rulers on binary64's numerical error;
- reproducibility;
- conditioning in orbit determination;
- certainty at long horizons.

The decision stays Logan's. Where the evidence does not decide, DEBRIS-D makes no recommendation.

## What DEBRIS-D starts from (labels as in DEBRIS-C)

### This project's studies, and the open sources

- **DEBRIS-B and DEBRIS-C**, both verified and narrowed at the merge:
  - **IAS15's evaluations per LEO object-day** (MEASURED, DEBRIS-B, REBOUND at ε = 1e-9 with J2 as a Python force):
    - 12,410 in 559 steps with J2, at 400 km;
    - 16,463 to 20,159 with a field of degree 20 to 70, all at 559 steps. That field is an Earth-fixed synthetic one with Kaula-rule magnitudes, turning at Earth's rate. "A richer field costs passes, not steps", and drag adds nothing (16,470 at degree 20).
    - How the pass count responds to a real field is "BELIEVED similar" (DEBRIS-B's limits). The passes a step also change with the step size: at binary256 they fell from 18.0 to 15.0 to 12.8 as the step shrank (DEBRIS-B, the port's runs). DEBRIS-B gives no comparison of passes across formats.
  - **Kernel sizes** (COMPUTED, DEBRIS-B's table of kernels):
    - gravity at degree 8, 20, 36 and 70: 1,415, 7,859, 24,515 and 90,509 flops;
    - the Sun and Moon by Chebyshev: 359 flops;
    - the frame interpolated as Orekit does: 349 flops.
    - A figure carried over keeps DEBRIS-B's definition of a flop.
  - **Costs at binary64** (MEASURED):
    - gravity in C: 183, 864, 2,618 and 10,039 ns at those degrees (DEBRIS-B), and 165, 831, 2,555 and 9,683 ns when DEBRIS-C timed it again;
    - NRLMSISE00 in Orekit, in Java: 7.3 to 7.5 µs a call;
    - JB2008: 29.9 to 31.6 µs (DEBRIS-C).
  - **The LEO catalogue at degree 20, binary64, on a CPU** (COMPUTED in DEBRIS-C): 87 CPU-hours a year with an exponential atmosphere, 431 to 441 with NRLMSISE00, and 1,493 to 1,573 with JB2008. That is about 1%, 5% and 17 to 18% of one core.
  - **Wide formats on the CPU** (MEASURED, DEBRIS-B): binary128 gravity through libquadmath costs 177 to 214 times binary64.
- **ESA's populations** (READ via WebFetch, https://sdup.esoc.esa.int/discosweb/statistics/, last updated 2 November 2026):
  - catalogued objects: 28,149 in LEO and 47,393 in all;
  - MASTER-8's estimates (02/2026): 68,450 objects above 10 cm, 1.5 million from 1 to 10 cm, and 230 million from 1 mm to 1 cm.
- **The open data** (READ via WebFetch, https://celestrak.org/NORAD/documentation/gp-data-formats.php):
  - CelesTrak checks for new GP data every 2 hours, and the 18 SDS data behind it update 2 to 3 times a day;
  - it asks users not to download new data more than once every 2 hours, and refuses a repeat download until the data update;
  - it sets "a limit on HTTP errors (301, 403, or 404) of 50 in a 2-hour period", past which an address goes to its firewall. A refused repeat download is a 403, so it counts toward the 50 (plan-verifier-D).
- **The density models' licences:**
  - pymsis is MIT, and "the MSIS2 code is not available for commercial use without contacting NRL" (READ via WebFetch, https://github.com/SWxTREC/pymsis).
  - NRL's Fortran, for NRLMSIS 2.1 and NRLMSISE-00, is under an "Open Source Academic Research License" (DEBRIS-B, READ from a search excerpt). Q6 settles what that permits.
  - Orekit's Java NRLMSISE00 and JB2008 are Apache-2.0, as Orekit is (this repository's README, "Licence"). Whether terms inherited from NRL's code reach a port is Q6's question.
  - SET's Fortran for JB2008 is "under a license agreement", and its code page returned 403 (DEBRIS-B, READ from a search excerpt).
- **cft-rebound's IAS15 port** (`ias15_cft`) runs at libcft's formats on the CPU (DEBRIS-A, DEBRIS-B). Its copy is preserved as `cft-debris-ledger\tools\ias15_cft.exe`. GPU-E names cft-rebound's IAS15 as the reference a GPU run would be replayed against. Its source is GPL, as REBOUND's is.

### cft-fp256's library, language and GPU program, at 0aa997a3

READ at cft-fp256's commit 0aa997a3 unless marked "relayed". "Relayed" means stated by cft-fp256's lead in the filed answers and not yet read in a record.

**The terms used below:**
- **The generic tier** is libcft's own arithmetic compiled for the GPU. It is what `hip:N` runs on main.
- **The specialised tier** means GPU-A's specialised elementwise fp256 FMA kernel and, for programs, GPU-A's "fixed path": a fp256 variant on the runner's side. Both are in GPU-A's study code (`docs/studies/gpu-a/`, in the tree at the pin), not in the backend that `hip:N` runs. Round 3 is to bring specialised kernels into that backend.
- **binary128** has neither measured. GPU-A §10 names fp128 "next" among the specialised kernels.

- **What runs on `cft_open("hip:N")` today** (`docs/HOSTAPI.md:2239-2295`):
  - the GPU runs libcft's own arithmetic, compiled for it: elements, reductions, and sequencer programs, one thread a lane, at every format;
  - it publishes `seq_features` 0x75f1f, the software handle's 0x7ff1f without INDEXED and AUGADD;
  - it refuses index tables, augmentedAddition's control codes, `cft_get_image_id`, and "any non-zero scratch depth, explicit 256 included". The depth is fixed at the software executor's 256 slots.
  - "Augmented addition, the tables and the card's 2,048-slot depth are round 2's."
- **Divide and square root** (`docs/studies/GPU-E-mi300x-ring.md`, §6, from line 415):
  - Through the host API, `cft_div` and `cft_sqrt` on a `hip:N` handle are round trips orchestrated by the host. They cannot be called inside a kernel.
  - Inside a sequencer program, the whole-operation routines divfull and sqrtfull run on the device: at binary256, 216 and 195 instructions, of which 27 and 34 are FMA-class. Their cost on a GPU is not measured.
  - cftc's own inlined division and root are "155 to 191 instructions" (`docs/LANGUAGE.md:3306`). So a compiled system's divides are priced from its own manifest, not from divfull.
  - A divide and square root callable inside a kernel "is in no round's plan" (§6, item 6).
  - GPU-E's finding for its IAS15 ring: "divide and square root are 69 % of a substep-pass" at binary256 (line 40).
- **Transcendentals** (`host/src/transcend.c:43-61`; `docs/TRANSCENDENTALS.md:2250` and `:2301`):
  - libcft's 39 entry points, `cft_exp` and the rest, are host work on any handle.
  - On a device, a transcendental runs only as a routine compiled into a program. A routine either decides its last bit in the lane, or marks the lane for the host's definition to replay.
  - Routines exist for exp's and log's families and for sin, cos and tan. GPU-A's part 2 also ran atan programs.
  - Relayed: routines can mark many lanes. The fp32 atan2 routine at x = 1 and x = max marked every lane whose result underflows, 262,143 in one slice. So a propagator must budget for replay on the host.
- **The language** (`docs/LANGUAGE.md`), compiled by cftc (`python/cftc/`, Apache-2.0) to a sequencer image:
  - **Run-time operations:** division, square root, exp's and log's families, sin, cos, tan, atan, asin, acos and atan2. `sin` and `cos` of t are forcing, with t carried in the state ("Forcing", from line 1476).
  - **Refused in v1, by name** ("Refused in v1", from line 870):
    - pow, sinh "and the rest of the reserved transcendentals";
    - `^` and `**`;
    - `t`, unless time is carried in the state.
  - **Not in v1** ("What v1 does not do", from line 3271):
    - "A built-in time, adaptive steps and events" (line 3321);
    - "User-defined integrators, beyond rk4, euler, stormer-verlet and map" (line 3325).
    - So IAS15 cannot be written in v1.
  - **Arrays** ("Arrays and indices", from line 286):
    - they are one-dimensional, and an index is integer arithmetic on literals and the statement's index variable;
    - a lane holds at most 32,768 values of state, tangent vectors and lane params.
    - So a table chosen by the time at run time, such as a Chebyshev block or an Earth-orientation node, cannot be indexed inside a run.
  - **Its contents also name** the step's constants, params and lane params, and variational equations.
  - **cftc's targets** (`python/cftc/targets.py`) include the software handle (features 0x7ff1f) and the tiles, and no `hip` target. So an image compiled for the software handle may still need features or depth that `hip:N` refuses.
- **Measured rates on the consumer cards** (GPU-A, MEASURED there):
  - **Elementwise fp256 FMA, kernel only** (`docs/studies/GPU-A-hip.md:121-122`, and its table at lines 483-485): 0.8 to 1.8 × 10^8 a second at the generic tier, and 0.80 to 1.46 × 10^9 specialised.
  - **End to end:** 31 to 51 M/s, against 0.80 to 1.46 G/s kernel only. Hence "Residency, or the speed is lost" (GPU-A §10, lines 598-610).
  - **G1C's figures** (relayed; on main once G1C merges): fp256 FMA through `hip:N` runs at 23.76 to 27.88 M/s staged, and 146.4 to 217.5 M/s resident.
  - **Sequencer programs** (GPU-A P2.1, lines 660-700): kernel only, resident, at 1M lanes, in lane-programs a second:

    | program | RTX 5060 Ti | RTX 4070 | RX 7600 | libcft's sequencer, one core | MPFR, one core |
    |---|---|---|---|---|---|
    | exp, fp64 | 13.4 M | 9.9 to 10.5 M | 5.9 to 6.0 M | 45.5 K | 1.2 to 1.3 M |
    | exp, fp256, libcft's arithmetic | 2.64 M | 3.5 to 3.9 M | 2.11 M | 23.4 K | 0.59 to 0.60 M |
    | exp, fp256, the fixed path | 25.6 M | 8.0 to 8.6 M | 7.1 to 7.3 M | - | - |

  - **As lane-instructions a second** (GPU-A, lines 861-866):
    - fp64: 1.0 to 2.5 × 10^9;
    - fp256 with libcft's arithmetic: 0.39 to 0.84 × 10^9;
    - fp256 with the fixed path: 1.4 to 5.2 × 10^9;
    - one core of libcft: "120 to 215 ns a lane-instruction".
  - The programs ran bit for bit on all three cards and on the runner's CPU build (P2.1).
  - fp32 and fp128 rates were not run (P2.7, from line 948).
- **The roadmap:**
  - cft-fp256's GPU round plan, a record outside git, lines 28-31:
    - round 2, the sequencer's remaining classes;
    - round 3, specialised kernels by function;
    - round 4, tuning and the MI300X.
  - `docs/ROADMAP.md:7024` says "no dates".
  - Round 1, on main, is the generic tier only. So the generic tier is the basis, and specialised arithmetic is upside (relayed).
- **The IAS15 wave kernel** (GPU-E §6, item 2) is not planned and has no date.
  - GPU-E recommends that a port derived from REBOUND's IAS15 live in cft-rebound, under REBOUND's GPL. cft-fp256's permissive-only rule excludes it, and GPU-E calls the choice "Logan's to decide" ("Where the port lives").
  - Relayed: a debris force model would not ride on that kernel.
- **libcft on this desktop's CPU** (`docs/BENCHMARKS.md:244-294`; the provenance is at lines 31-63):
  - measured 2026-09-01 on the i5-12400F, one core, in a Linux container with gcc 13.3.0 at -O2;
  - nanoseconds per element, libcft's software backend:

    | | FMA | divide | square root |
    |---|---|---|---|
    | binary64 | 316.3 | 4,468.0 | 5,638.2 |
    | binary128 | 394.5 | 6,678.4 | 8,018.5 |
    | binary256 | 448.3 | 11,563.1 | 12,704.3 |

  - So on the CPU a divide costs 14.1 to 25.8 FMAs, and a square root 17.8 to 28.3 (COMPUTED).
  - libcft has changed since then, so these figures are MEASURED then, not now (relayed).
  - No record times the transcendentals on the host (relayed).
- **Tools in the tree:**
  - `host/Makefile` builds `cft-bench$(EXE)`, and `EXE` is `.exe` on Windows;
  - `host/tools/positive-run.c` runs a program from `--scratch-in` to `--scratch-out` and prints a hash, not a rate;
  - `host/tools/gen_build_id.sh` names a build `unknown` outside a git tree. So a build from the archive reports an unknown build id, and only the archive's SHA-256 in `lead.md` ties it to 0aa997a3.

### cft-fp256's certificates, at 0aa997a3 (READ, `docs/CERTIFICATES.md`)

This round designs for certificates and writes none (Logan, 2026-11-12). A feature request for certificates of runs on `hip:N` went to cft-fp256's lead the same day (`lead.md`, 20:30). Its answer is filed as `relayed\2026-11-12-cft-fp256-lead-gpu-certificates.md` and summarised under "Certificates on the GPU backend" below.

- **What a certificate is** (lines 1-96):
  - A certificate is a text file that says what a deterministic run was and how accurate it is: which program ran, on which inputs, cut into which segments, which state each segment began and ended on, what flags it raised, and what its accuracy is, of which kind.
  - An audit re-runs segments from their certified start states on an implementation the producer does not control, and checks their end states and flags.
  - **Independence:** for a certificate that libcft's software backend made, "only the golden auditor is an implementation independent of it there" (lines 56-96). `cft-audit` is libcft's own second check.
  - **What it holds:** a certificate records the program's digest (line 330) and each state's hash, not their bytes.
  - **What an auditor is handed** (lines 928-952): the images, banks and states, separately. It chooses all the segments, named ones, or a random sample.
  - **Keyed or open** (from line 96): every certificate is one or the other, and "The owner chooses, per certificate". Keyed hashes are HMACs under a 32-byte random salt that the owner keeps; an open certificate needs nothing secret.
- **The tools:**
  - `cft-segrun` writes certificates, version 2 by default (from line 1398);
  - `cft-audit` audits them in C, with `--choose all|sample:K|K,K,...` (line 2471);
  - the golden auditor is `python/cft_golden/cert.py`. It has no command-line tool: its `audit(...)` is a Python function (line 1746 of `cert.py`).
  - cft-segrun's usage text names `--device sw|<xclbin>|cft://host:port` (line 1421), and no `hip:` spelling. The text is incomplete: see the next item.
- **Certificates on the GPU backend:**
  - **cft-segrun writes on `hip:N`** (READ): it hands any `--device` but `sw` to `cft_open` (`host/tools/segrun.c:4340`).
  - **G1C's gate:** `certificates/corpus.py check --device` has cft-segrun remake each golden case on the device and holds it to the committed bytes, with the identity lines left out of both sides (READ, cft-fp256's `docs/VALIDATION.md` at G1C's merge 68151339; that merge is in cft-fp256's tree and due on main tomorrow).
    - Its counts are relayed: 324 checks with 0 failures, and 17 golden certificates remade on both GPUs, versions 1 and 2.
  - **Version 2's per-lane flags, marks and replay lines** come from the GPU's own executor (relayed).
  - **Not yet:**
    - **Identity:** no line states the GPU, and version 2's device lines are written `unknown` by any backend but software (`host/tools/cert_write.h:422-427`, READ). `hip:N` refuses `cft_get_image_id`.
    - **Depth:** a certificate written on `hip:N` states no scratch depth (G1C's known limits, READ at 68151339). So an audit on the software backend at its default of 256 matches "by coincidence, not by statement" (relayed).
    - **Audit:** no certificate written on `hip:N` has yet been audited by `cft-audit` (relayed).
    - **Round 2's refusals:** AUGADD programs and a depth of 2,048 (relayed).
  - **Planning:** none of this is in a round's plan. The request is logged for the GPU round's planning, and its order and dates are Logan's (relayed).
- **An audit refuses by name** (the table from line 1126). Among the names:
  - `body-hash`: the hash line is not the SHA-256 of the body;
  - `state-hash`: a state handed is not the one certified at its boundary;
  - `continuity`: a segment does not start where the one before it ended;
  - `segment-end`: a re-run segment does not end on its certified end state.
- **Accuracy entries** (from line 687):
  - `drift` is a measurement: Q(final) - Q(initial) for a polynomial Q in one lane's state;
  - `step-halving`, `wider` and `wider-source` are estimates: the largest absolute difference over the state's slots against a half-step run, or against a run one format wider;
  - "No version-1 method has a rigorous remainder", so no entry is a bound.
  - The wider-source run, the same source compiled one format wider, is refused at fp256, "the top of the ladder" (line 3923).
- **Version 2 adds** (from line 3518): per-lane flags; each lane a routine marked, with its replay by the definition; the source and the compiler; the wider-source run; provenance lines; and a detached Ed25519 signature.
- **What neither version does** ("What version 1 does not do", line 3414; "What version 2 does not do", line 4647):
  - carry a bound, or a value that is not an exact rational;
  - certify deposits, lane masks, index tables, or streams that change between segments;
  - audit sources or replays in C: those are the golden auditor's;
  - sign a time.

## The shape

| agent | job | model | when |
|---|---|---|---|
| the lead (this session) | <ul><li>Phase 0</li><li>writes the briefs and keeps the ledger</li><li>relays to cft-fp256's lead</li><li>answers escalations</li><li>books the TimeSheet</li><li>files each final message</li><li>narrows at the merge</li><li>writes the round's record with its cost</li></ul> | Opus | throughout |
| DEBRIS-D | the study: Q1 to Q8 in its brief below | Opus | after Phase 0 |
| verifier-D | disconfirm DEBRIS-D | Sonnet | when DEBRIS-D reports |
| merge-check-D | check any narrowing the lead makes at the merge | Haiku | after verifier-D, if the lead narrows anything |

## Phase 0: the lead, before dispatch

1. **cft-fp256's lead's answers:** received and filed (`relayed\2026-11-12-cft-fp256-lead-debris-d-answers.md` and `relayed\2026-11-12-cft-fp256-lead-debris-d-cpu-column.md`). Their citations were read at 0aa997a3 (`lead.md`, 19:36). Done.
2. **The archive** (decision 2):
   - The lead writes `git -C <cft-fp256> archive 0aa997a3` to `cft-debris-ledger\tools\cft-fp256-0aa997a3.tar`, records its SHA-256 in `lead.md`, and marks it read-only.
   - A build from it names its build id `unknown`, since the tree is not a git checkout. The archive's SHA-256 is what ties it to 0aa997a3.
   - **Control:**
     - its listing holds `host/Makefile`, `python/cftc/__init__.py`, `python/cftc/__main__.py`, `python/cft_golden/lang/` (the reference interpreter) and `LICENSE`;
     - a file extracted from it equals `git show 0aa997a3:<that file>` byte for byte;
     - a name that is not in the commit is absent.
3. **Q3's timings:** one `sensitive` window on `desktop`, which the lead books when DEBRIS-D asks for it. The TimeSheet's README names "a timing or rate measurement" as a sensitive run, and cft-fp256's lead advised the same. If the TimeSheet refuses the window, the lead says so; the Rules give the fallback.
4. **GPU time** (decision 3): none by default.
5. **Downloads:** none is expected. MPFR is not needed, since `cft-bench-peers` is not built.
6. **TimeSheet:** each agent's time is booked as a `notice`.
7. **Dispatch**, as in "Dispatch" below.

## Dispatch

Each agent's prompt is a dispatch note and its brief, followed verbatim by four sections of this plan: "Dispatch", "The ledger", "Rules every brief carries" and "READY". A script writes the prompt from this file. After dispatch, the prompt is checked against the harness's transcript.

Each agent sends one test escalation as it starts:
- it writes `test escalation from <name>` in its own ledger file;
- it sends the same words to the lead (SendMessage to `main`);
- the lead replies "received" and records the round trip in `lead.md`.

If no test escalation arrives from an agent within ten minutes of its dispatch, the lead reads that agent's ledger file, arms a watch on the ledger directory, and says so in `lead.md`.

## The ledger

The ledger is `C:\Users\logan\source\repos\cft-debris-ledger\`, as in rounds DEBRIS-B and DEBRIS-C.

- **One file per author, append only:** `lead.md` continues; this round adds `DEBRIS-D.md` and `verifier-D.md`, which the lead creates with a header only. Correct an entry by appending beneath it, never by editing it.
- **Times:** every heading's time comes from `date`, never from memory.
- **Read it at three moments:** before starting; before resting anything on another study's number; before the final report.
- **Verifiers read `lead.md` only**, and the files it points them to.
- **Escalation:** write the entry first, then message the lead (SendMessage to `main`). Wait for the answer to a question while working on what does not depend on it; never end your turn to wait.
- **Questions for cft-fp256's lead go through this round's lead.** No agent messages another session.
- **When to write:** when an entry would change another agent's work or the lead's: an environment fact, a brief that turned out wrong, or a finding about a shared input, never progress. Every entry marks which claims were measured and which are believed.
- **When a pause is announced**, record where you are before you stop. On resuming, do a full read, check your outputs before trusting your memory of them, and say where you stopped.
- **Scratch:** each agent creates its own directory when it starts, `C:\Users\logan\source\repos\cft-debris-scratch\<name>\`. Read no other agent's scratch. Keep no secrets anywhere an agent is given.
- **The downloads:** `C:\Users\logan\source\repos\cft-debris-downloads\`, one directory per file, each file's SHA-256 in `lead.md`. Read-only for every agent.
- **The tools:** `cft-debris-ledger\tools\`, holding the preserved port `ias15_cft.exe` and the archive `cft-fp256-0aa997a3.tar`, each with its SHA-256 in `lead.md`. Read-only for every agent.
- **What the lead writes in `lead.md`, every verifier reads.** The lead relays upstream facts there. It never writes a judgement of DEBRIS-D's work there before verifier-D has reported.

## Rules every brief carries

These come from three places: Logan's standing rules (carried from cft-fp256 and cft-rebound, 2026-09 to 2026-11), canonical ParcelRound, and the rulings of rounds DEBRIS-B and DEBRIS-C.

- **Read-only, except your own outputs and scratch.**
  - cft-rebound, cft-fp256 and the TimeSheet are other sessions' live repositories. Read their files; in git, use only `git -C <repo> log` and `git -C <repo> show`. Never write in them, never run `git status` there, and never run a bare `git stash`.
  - In the TimeSheet you may run `timesheet.py check` and `list`, which only read.
  - cft-fp256 is Apache-2.0. Extract and build its archive only in your scratch.
- **The repository is public and MIT.**
  - Copy no third-party source into `studies\`, whether cft-fp256's, REBOUND's, cft-rebound's or Orekit's. That includes what cftc compiles, since an image carries cft-fp256's routines.
  - Any copy or instrumented version of REBOUND's or cft-rebound's source stays in your scratch. Only the counts, and the scripts of your own that produced them, go in `studies\`.
  - Reading a source to count its operations is fine; quoting more than a short passage is not. Say where every counted figure comes from.
- **No downloads, installs or package managers.**
  - The approved files are in the downloads folder, with their SHA-256 in `lead.md`. Read them in place, or copy what you need into your scratch.
  - If another file would settle a question, ask the lead for it. Give its name, source URL, size, licence and purpose. Each file needs Logan's approval.
- **Reading the web: HTML pages only.**
  - WebFetch returns a model's summary of a page, not its bytes. A figure or quote taken through it is labelled "READ (via WebFetch)". It supports "consistent with", never "confirmed".
  - WebFetch saves any response that is not HTML to disk. So a URL ending in `.txt`, `.pdf`, `.csv`, `.zip`, `.bin`, `.jar` or `.gfc`, or one in an FTP tree, is a download request, whatever it seems to hold.
  - GitHub's HTML view of a source file is an HTML page. It may truncate a long file, so say where a count stops.
- **No GPU, WSL, card or box.**
- **Keys:** this round uses no keys and signs nothing. Never look in `~/.ssh`.
- **Timings:**
  - Take small measurements only, at the machine's natural load, and state the load beside every timing.
  - Host timings run inside a `sensitive` window on `desktop` that the lead books for you. Ask for it when you are ready, and keep its booking ID with the timings.
  - **Fallback, only if the lead tells you the window was refused:** wait for a quiet window, or time anyway, after `C:\Users\logan\AppData\Local\Programs\Miniconda3\python.exe -I -B C:\Users\logan\source\repos\TimeSheet\timesheet.py check desktop --short` prints FREE. Keep that output with the timing, and state the load as a limit. This is weaker than the window: `check --short` detects only another session's sensitive window, not load.
  - The lead books the rest of your time as a `notice`. A run of 10 minutes or more goes to the lead first, who books it.
- **CPU budget** means the CPU time of the processes you start, counted by cycles:
  - read `QueryProcessCycleTime` through Python's `ctypes`, and divide by 2.5e9 cycles a second;
  - the divisor is the part's base clock (READ, cft-fp256's `docs/BENCHMARKS.md`), and taking it as the counter's rate is BELIEVED;
  - give `GetProcessTimes` beside it. On this host it under-reports a busy thread under load, by a factor of about 1.7 to 4 (MEASURED in round DEBRIS-C).
- **Long jobs:** run them through the Bash tool, in the foreground with a timeout of at most 600000 ms or with run_in_background. Never use nohup, and never end your turn while one of your jobs is running.
- **C:**
  - Before any compile, put `C:\msys64\mingw64\bin` first on PATH and check that `gcc -dumpmachine` prints `x86_64-w64-mingw32`. In this Git Bash, a bare `gcc` is the 32-bit i686 compiler.
  - libcft's Windows build line is `make -C host CC=gcc OS=Windows_NT TMP=/tmp TEMP=/tmp <targets>` (cft-fp256's `bindings/wasm/verify_demos.mjs:51-58`). On Windows the targets end in `.exe`, as in `cft-bench.exe` and `cft-segrun.exe`.
- **Java:** a Java 8 runtime only, `C:\Program Files\Java\jre-1.8\bin\`, and no `javac`.
  - Run Nashorn scripts as `"C:/Program Files/Java/jre-1.8/bin/java.exe" -cp "<the jars, ;-separated, absolute paths in the downloads folder>" jdk.nashorn.tools.Shell <script.js>`.
  - `jjs -cp` and `CLASSPATH` both fail here.
  - Nashorn here is ES5: use `var` and `function`.
- **Python:** `C:\Users\logan\AppData\Local\Programs\Miniconda3\python.exe -I -B`.
  - `-I` keeps the current directory off `sys.path`, so `python -m cftc` run from the archive's `python\` fails.
  - Run the compiler as `python -I -B <the extracted archive>/python/cftc <arguments>`.
  - A script of yours that imports `cftc` or `cft_golden` puts `<the extracted archive>/python` on `sys.path` itself (plan-verifier-D, MEASURED with a stand-in package).
  - The reference interpreter is `lang.run`, in `python/cft_golden/lang/`. Import it the same way.
- **Processes and files:** kill only processes you started, and only by PID. Delete only what you made, and never through a computed path.
- **Earlier studies' records are read-only.** Copy what you run into your scratch or your own output folder. Before your report, check all four:
  - `sha256sum -c SHA256SUMS` run from `studies\` shows 32 OK;
  - `find studies/debris-a -type f | wc -l` gives 29;
  - `sha256sum -c MANIFEST.sha256` run from `studies\debris-b\` shows 54 OK, and from `studies\debris-c\` shows 136 OK;
  - there is no `__pycache__` anywhere under `studies\`.
- **Host traps:**
  - MSYS `.exe` transparency: writing a file `X` beside an existing `X.exe` writes to `X.exe`.
  - Passing a script to bash from Python with `text=True` turns every newline into CR+LF.
  - In the Bash tool, a doubled backslash reaches the shell as one, inside a heredoc too. Write any script that contains backslashes with the Write tool, and write Windows paths in commands with forward slashes.
  - Git Bash's `grep` strips the CR at each line end unless given `-U`. Count CRLF with Python.
  - Never start a process under `pythonw`, or detached.
- **No helper agents.**
- **Your final message is your report.** Its word limit is in your brief. If the harness refuses the write of a document your brief names, your final message is that document followed by the report, and the word limit then applies to the report alone.
- **Before you report**, stop any background work you started. End with what you did not do, and with anything your brief got wrong.

## READY, stated before the first pass

READY applies to DEBRIS-D and to every verifier's verdict. Every load-bearing claim must rest on one of:
- a measurement, with its command and output;
- a fetched source, cited by URL;
- arithmetic from labelled inputs.

Otherwise it is stated as a limit, in terms of the behaviour it concedes. A claim's domain and quantifier are claims, and so is a figure's definition. A number carried over from an earlier study, or from cft-fp256, keeps its definition, or it is re-measured.

**From rounds DEBRIS-B and DEBRIS-C:**
- **Every control states its pass and fail criteria before the data, and the code asserts them.** A control that fails as specified is reported as failed, whatever replaces it.
- **Every agreement claim states its tolerance before the data.**
- **Every log names the SHA-256 of the script that wrote it**, and the criterion that script asserted.
  - Keep every version of a script that wrote a log, under a name carrying the first 12 hex digits of its hash.
  - Never overwrite a log: number each run's log.
  - The manifest lists every version.
- **An ESTIMATE names its basis and its range**, and is never added to a MEASURED figure without saying so.

A verifier may reuse a run instead of re-running it only when all three of these hold:
- someone other than the author of the work made the run;
- its inputs are identical, file hashes included;
- the verifier re-runs from clean whatever it doubts.

Only a wrong answer sends work back: a false claim, or a measurement or check that cannot fail. Everything else is a note the lead records, and a sentence that claims too much is narrowed at the merge.
- **Loop cap (Logan, 2026-10-15, carried through the lead's memory):** after three NOT READYs for narrowing reasons, the next pass blocks only on wrong answers.
- **Threat model (Logan, 2026-10-02):** each verifier's brief states one, and findings outside it do not reopen the loop.

## Logan's decisions (each default stands unless changed)

1. **Models:** Opus for DEBRIS-D, Sonnet for verifier-D, Haiku for a merge-check.
2. **The host libcft for Q2 and Q3:**
   - (a) DEBRIS-D's own build, in its scratch, from the lead's archive of cft-fp256 at 0aa997a3. This is the route cft-fp256's lead prefers: "a build you make from a named commit is the record". It is also the only one that lets this round compile and run programs.
   - (b) none: Q3's CPU column READ from cft-fp256's 2026-09-01 tables, the transcendentals as ESTIMATEs, and Q2 reading only, with no program run.
   - Default: (a).
3. **GPU time in this round:**
   - (a) none: the cards' figures are COMPUTED or ESTIMATE from GPU-A's measured rates.
   - (b) after DEBRIS-D's first compiled systems exist, a request to cft-fp256's lead to run them on the RTX 5060 Ti and the RX 7600, as a small GPU parcel of its own booked by it in the TimeSheet. The rates would come back relayed. cft-segrun writes on `hip:N`, but its certificates there do not yet state the GPU or its depth, and none has been audited in C (relayed). This round writes no certificate anyway.
   - Default: (a). Either way the records keep the systems' sources, the commands that rebuild their images, and each image's SHA-256, so the images can be rebuilt and measured later.
4. **Budgets:**
   - DEBRIS-D: 4 hours of wall time and 30 CPU-minutes;
   - verifier-D: 2 hours and 15 CPU-minutes;
   - merge-check: 20 minutes.
   - For scale: DEBRIS-C used 57 minutes and 7.2 CPU-minutes, and verifier-C 12 minutes and 4.2.
   - **The stop rule:** within them, DEBRIS-D stops and messages the lead before it does either of these:
     - runs the reference interpreter past the first test's sizes (degree 2, 96 steps, 4 segments, 8 lanes);
     - compiles anything expected to pass 5 CPU-minutes.
     The reference interpreter is pure Python (plan-verifier-D).
5. **The density models to lay out:**
   - NRLMSISE-00, via Orekit's code;
   - JB2008, under SET's terms;
   - a simpler model for the real-time path.
   - Default: all three, with no recommendation.
6. **Outputs** go in `cft-debris\studies\`. Pushing to the public repository waits for Logan's word at the round's close.

## Not in this round

- Building the propagator, or any GPU kernel. Q8 lays out the build for Logan to decide.
- Any run of our agents on a GPU, and any run on the MI300X, which is paid and needs Logan's word with the price first.
- Any source that needs an account: Space-Track, Earthdata (CDDIS), EDC.
- MPFR, or any other download.
- Writing or auditing a certificate. The design is built for certificates, and they come once their support reaches the GPU backend (Logan). The choice between keyed and open, draft 4's decision 7, returns then as Logan's, per certificate.
- The decision itself, which is Logan's.

---

## Brief: DEBRIS-D

You are study parcel **DEBRIS-D** in cft-debris, a project for space-debris tracking and simulation. Its folder, `C:\Users\logan\source\repos\cft-debris`, is a public git repository under the MIT licence. This is a study: it builds no part of the propagator, and you commit nothing.

**Budget:** 4 hours of wall time and 30 CPU-minutes. Message the lead before you pass either. Also message the lead before you do either of these:
- run the reference interpreter past Q2's first-test sizes (degree 2, 96 steps, 4 segments, 8 lanes);
- compile anything you expect to pass 5 CPU-minutes.

**Start here:**
1. This plan, `C:\Users\logan\source\repos\cft-debris\studies\DEBRIS-D-plan.md`:
   - Logan's goal, his preference for the wide formats, and his word on the route and on certificates;
   - what each question settles;
   - what the round starts from, with each figure's source.
2. DEBRIS-B and DEBRIS-C (`studies\DEBRIS-B-custom-model.md` and `studies\DEBRIS-C-measurements.md`, both verified and narrowed), and both rounds' records.
3. In `lead.md`:
   - cft-fp256's lead's answers, filed in `cft-debris-ledger\relayed\`;
   - the archive's SHA-256.
4. cft-fp256's documents, at the pinned commit, in the archive:
   - `docs/LANGUAGE.md`, `docs/SEQUENCER.md`, `docs/PROGRAMS.md`, `docs/ORBITS.md` and `docs/CERTIFICATES.md`;
   - `docs/HOSTAPI.md`'s GPU section;
   - `docs/studies/GPU-A-hip.md` and `docs/studies/GPU-E-mi300x-ring.md`;
   - `docs/TRANSCENDENTALS.md` and `docs/BENCHMARKS.md`;
   - the golden certificates in `certificates/`, which include compiled systems such as `lorenz63-rk4-fp64` and `lorenz96-rk4-fp256`.

**Your job.** Answer Q1 to Q8 for Logan's goal.
- **Where it goes:**
  - the study, in `studies\DEBRIS-D-architecture.md`;
  - in `studies\debris-d\`, with a `MANIFEST.sha256` over them: your own scripts, drivers and systems written in the language, and your logs and records. These are this repository's (MIT).
  - **In your scratch only:** cft-fp256's sources, libcft's build, every image and bank cftc compiles (an image carries cft-fp256's routines), and any copy of REBOUND's or cft-rebound's source.
  - For each image, record in `studies\debris-d\` its SHA-256, its manifest's counts, and the command that rebuilds it from your source at the pinned commit.
- **Order:** a short answer, then Q1 to Q8, then the measurements with their commands, then the sources. Aim for 8 to 12 pages.
- **Labels:** MEASURED, COMPUTED, READ, ESTIMATE (with its basis) or BELIEVED, on every claim.
- **Criteria first:** for every comparison and every control, write its tolerance, or its pass and fail criteria, into your script before you run it, and assert them in code. Every log names the SHA-256 of the script that wrote it. Report a control that fails as failed.
- **The build id:** a build from the archive names its build id `unknown`, since the tree is not a git checkout, and so does `cftc --compiler-id`. That is expected, not a failure. The archive's SHA-256 is the record that ties the build to 0aa997a3.

**Q1. The workload, by operation class.** Count, for one force evaluation, and for one LEO object-day:
- FMA-class operations (additions, multiplications, FMAs);
- divides;
- square roots;
- each transcendental: exp, log, pow, sin, cos, atan2 and any other.

Count them for:
- gravity at degrees 8, 20, 36 and 70 (DEBRIS-C's normalised kernel);
- the Sun and Moon (a Chebyshev reader and point masses);
- the interpolated frame;
- drag with each density model laid out in Q6;
- radiation pressure with a conical shadow;
- the integrator's own work per step: IAS15, from cft-rebound's `ias15_cft.c` (read-only; any instrumented copy stays in your scratch), and the language's `rk4` and `stormer-verlet`.

For an object-day, count at IAS15's measured evaluation counts (with their domain: DEBRIS-B's synthetic field), and at the fixed-step counts Q4 measures.

**Method:**
- For our own kernels, build counting versions, with each operation class wrapped in a counting macro.
- For Orekit's density models, count from the source, read through GitHub's HTML view, and say where each count stops.

**Controls:**
- A counting build must match a hand count on a case small enough to count by hand. Degree 2 is J2.
- A planted extra term must change the count by exactly its own operations.

**Q2. The route: cft programs, designed for certificates.** Logan wants the propagator written as cft programs wherever the language reaches. He also wants it designed for cft-fp256's certificates without implementing them yet, so that the GPU route is not held back. Write and audit no certificate in this round.

- **READ, part by part.** Take each part of Q1's force model in turn, against v1 (cftc at the pinned commit). Say whether v1 expresses it, and if not, which refusal or limit stops it, by name. Cover at least:
  - pow, which v1 refuses;
  - time, which v1 needs carried in the state, with `sin` and `cos` of t as forcing;
  - the Sun's and Moon's positions, and the Earth's orientation, whose tables are chosen by time. v1 cannot index a table by time inside a run, so say how a run would carry them instead (for example one block's coefficients as params, with a run per block), and what that does to a run's length;
  - space weather, and each object's own constants as lane params;
  - the gravity field's coefficients, as constants or arrays, against the 32,768-value lane capacity;
  - which integrators v1 offers (rk4, euler, stormer-verlet and map), and that IAS15 is not among them.
- **For `hip:N`:** cftc has no `hip` target. So for each image, compare by hand the features and scratch depth its manifest says it uses against what `hip:N` publishes (`seq_features` 0x75f1f, 256 slots), and say whether it would load there.
- **The first test (MEASURED):**
  1. Build libcft and its tools (`cft-segrun.exe`, `cft-audit.exe`, `cft-bench.exe`) from the archive in your scratch (decision 2).
  2. Write two systems in v1. Step each by `rk4` at a fixed step of 60 s for 96 steps, a little over one orbit at 400 km, in 4 segments of 24 steps, on 8 lanes with different initial states. These sizes are the first test's; going past them comes under decision 4's stop rule.
     - **J2:** a LEO orbit under the central term and J2.
     - **J2, drag and rotation:** the same, plus drag through an exponential atmosphere, ρ0·exp(−(r − r0)/H), and the Earth's rotation as forcing, through sin and cos of ω·t. Its routines (exp, sin and cos) are the kind that can mark a lane. Divide and square root never do: a divide has "an exactly measurable residual", so it can "DECIDE its own last bit" (`host/src/transcend.c:43-61`).
  3. Compile both with cftc from the archive at binary64, binary128 and binary256.
  4. Run them on the software executor. Use `host/tools/positive-run.c`, cft-segrun on `--device sw`, or a driver of your own.
- **Hold each to:**
  - (a) the language's reference interpreter, bit for bit. That is cft-fp256's own definition of correct.
  - (b) an independent reference of your own: mpmath at 100 digits or more, with the same method and steps, within a tolerance you state before the run.
  - (c) a negative control: the reference interpreter run on a source with one coefficient planted one ulp off must fail (a).
- **Then:**
  - compile the degree-8 and degree-20 fields, if the capacities allow, and report the capacities each image uses, from its manifest, and any refusal by name;
  - record each image's instruction counts by class, for Q3 and Q5;
  - record which lanes the routines mark, and how often, from the software executor's lane bytes. The second system's arguments are the ones that matter here.
- **Designed for certificates** (READ; write no certificate). Say what the design must keep so that a certificate can state its runs once support reaches the GPU backend:
  - runs cut into segments whose streams stay fixed, with the states kept at every boundary;
  - the accuracy entries each run would carry. These are `step-halving`, if the compile writes a half bank; `wider-source` at binary64 and binary128, since it is refused at binary256; and a `drift` where a polynomial invariant exists, such as the z-component of the angular momentum, x·v_y − y·v_x, which J2 conserves and drag does not;
  - what an audit would be handed, which auditor would be independent of the run, and how a day's GPU runs would be audited on the CPU.
  - Check each against `docs/CERTIFICATES.md`'s own lines.
- **What certificates cannot yet state, by name.** Hold the propagator that Q1 and Q7 lay out against CERTIFICATES.md's lists of what versions 1 and 2 do not do. Cover at least:
  - forcing tables that change between segments;
  - objects entering or leaving a run (lane masks);
  - a bound on the error;
  - accuracy values through a square root, such as a distance;
  - runs on `hip:N`: their identity, their scratch depth and their audit in C, which cft-fp256's lead lists as not yet done. The request for them is with cft-fp256's lead (2026-11-12);
  - audits of sources and replays in C.
  - Say which of these a different design avoids, and which are requests for cft-fp256 (Q8).

**Q3. The price of each operation class, by format.** For binary64, binary128 and binary256, give the cost of an FMA-class operation, a divide, a square root and each transcendental Q1 names.
- **On this CPU** (MEASURED, inside the timing window; Rules):
  - FMA, multiply and add through `cft-bench.exe`, from your build;
  - divide, square root and the transcendentals through a driver of your own on the software backend, `cft_open(NULL, ...)`;
  - the software executor's lane-instructions a second, and steps a second, on Q2's images, through a timing driver of your own (`positive-run` prints a hash, not a rate);
  - beside them, cft-fp256's 2026-09-01 tables, as MEASURED then.
- **On the consumer cards** (RTX 4070, RTX 5060 Ti, RX 7600). Keep the generic and specialised tiers apart, as this plan defines them, and say which rate is kernel only and which is end to end.
  - **Program rates:** start from GPU-A's lane-instructions a second (lines 861-866, READ), times each image's instruction counts by class (MEASURED from its manifest). Say what the mix of instructions in GPU-A's rate programs was, and how far it carries to yours.
  - **The elementwise FMA rates** (GPU-A, lines 483-485) are a cross-check.
  - **Divides and roots:** price them from your images' manifests, not from standalone divfull and sqrtfull.
  - **What GPU-A did not time:** binary128 throughout; log, cos, tan and atan2 routines; anything on the MI300X. Give an ESTIMATE with its basis.
- **The replay budget:** a marked lane's cost, at the host rate you measured, times the marking rate from Q2's second system.
  - If it marks no lane, report 0 marks in N lane-evaluations, with the bound that implies (3/N at 95%).
  - Price the edge cases of cft-fp256's lead's caution (relayed) as an ESTIMATE.
- **Controls:**
  - in your own drivers, a timed loop folds every result into a printed checksum, and a loop with the operation removed must time at least 10 times faster. `cft-bench` is cft-fp256's tool, so this control does not apply to it;
  - the driver's results at 1,000 arguments a function equal mpmath's correctly rounded values, bit for bit, at each format.

**Q4. The integrator.**
- **Measure on the CPU at binary64,** with DEBRIS-C's degree-20 kernel with drag, for LEO:
  - IAS15 (REBOUND) at eps 1e-9: steps, evaluations and error per object-day;
  - RK4 and Störmer-Verlet at fixed steps, the methods v1 offers: steps and error at the same accuracy as IAS15, and at the accuracy at which a wide format's arithmetic would show;
  - each against a reference of your choice: higher precision at fixed small steps, with its tolerance stated before the run.
  - These step counts feed Q5.
- **The wide format's place,** with the cost of each configuration:
  - at binary64's own steps, a wider format gains only arithmetic: it is a ruler;
  - to show its precision, it needs smaller steps. DEBRIS-B measured binary256's round trip falling by 2^15.0 at each halving of IAS15's step, and from that put binary256's floor at "about 600 times smaller steps". Say what the same floor costs with RK4, whose error falls by 2^4 a halving.
- **On the device:**
  - IAS15 one wave per system (GPU-E's design) is not a v1 program. It would need a kernel of its own, which needs an in-kernel divide (not planned), or cft-rebound's program engine with index tables (round 2).
  - Lay it out against a fixed-step batch in v1, by divergence, occupancy and step counts.
- **The licence** (READ, and BELIEVED where it is judgement): REBOUND's IAS15 is GPL-3.0-or-later; cft-debris is MIT. Lay out:
  - an implementation written for cft-debris from the published method, never from REBOUND's source;
  - cft-rebound's port, which stays GPL in cft-rebound;
  - the fixed-step methods v1 offers, which are cft-fp256's (Apache-2.0).
  - Draw no legal conclusion; Logan decides.

**Q5. The ladder.** COMPUTE, from Q1 to Q4, the device time per object-day at degree 20 with each density model in Q6, for each card, format and tier.
- **The main line** is the v1 route: a fixed-step method at Q4's step counts, priced from Q3's program rates.
- **Beside it,** labelled as a route v1 cannot run: IAS15 at its measured evaluation counts.
- Use GPU-E's occupancy and live-lane method, and say what you take from it.
- From that, give the real-time capacity: the number of objects each card runs at one simulated day per day, resident, with the replay budget included.
- Give the speed-up at ESA's sizes: 28,149, 47,393, 68,450, 1.5 million and 230 million objects.
- Give the CPU's figures beside the cards': one core, and all of the i5-12400F's six cores.
- Give the MI300X's figures from GPU-E's estimates, labelled so.
- Every figure is COMPUTED or ESTIMATE, never MEASURED. Name the measured rates it rests on.
- **The candidate hosts for a 24/7 run, and what else uses them:**
  - READ from the TimeSheet's `resources.json`:
    - the desktop's RTX 5060 Ti, "used from WSL cft-gpu";
    - the desktop's RTX 4070, which "drives the displays", so any use is Logan's call;
    - the RX 7600, in the machine named nvidia-box.
  - Relayed: another session's server shares the RX 7600's machine.
  - Our agents touch no WSL distro (Rules), so a host for the 24/7 run is part of Q8's decision for Logan.

**Q6. The density model.** For NRLMSISE-00, JB2008 and one simpler model (say which, and why), give:
- its accuracy as published (READ, or BELIEVED);
- its Q1 operation counts, and its Q3 cost at each format;
- whether v1 can express it, and what a rewrite would cost. pow, for one, would become exp(y·log x): say what that does to correct rounding;
- its licence, and what an MIT repository may do with it: port it, call it, or neither. That includes whether NRL's terms reach a port of Orekit's code;
- **the precision question:** the dynamics at a wide format with the density at binary64, against everything at the wide format. Give each one's cost, and what it would mean for cft-fp256's use case and for a certificate.

**Q7. The 24/7 self-validation loop.** Design it, and run nothing.
- **The data:** CelesTrak's GP elements, polled within its stated limits; space weather; Earth orientation.
  - For each, give its cadence, source and terms (READ).
  - A refused repeat download is a 403, and counts toward CelesTrak's 50 errors in two hours. Design the polling so that cannot happen.
  - Name what would need an account: Space-Track, and laser ranging.
  - Name the SGP4 implementation that turns elements into states, with its licence (READ).
- **The statistic:** DEBRIS-C's M4 bands, adapted to truth derived from TLEs, with a TLE error model. Say where that model comes from. Say whether the language's variational equations could carry the covariance (READ, `docs/LANGUAGE.md`).
- **Divergence:** what triggers a refit, a flag or a refusal, with each criterion stated now.
- **Certificates, once support reaches the GPU backend, and replay:**
  - how a day's runs would be cut into runs and segments, so that each certificate's streams stay fixed;
  - what a sampled audit of a day's runs would prove, with CERTIFICATES.md's escape probability;
  - which accuracy entries each run would carry;
  - whether each would be keyed or open, which Logan chooses per certificate;
  - what a certificate and its audit cannot cover here: anything outside libcft, such as parsing the inputs, SGP4, and the elements' own noise, and the items Q2 names;
  - GPU-A P2.1 runs libcft's programs bit for bit across three cards and the CPU, and the host's definition replays marked lanes. Say what that lets a day's run replay.
- **What it costs** to run around the clock: COMPUTED from Q5.

**Q8. The first build, laid out for Logan.** Give milestones, each with its gates, owner, dependencies and cost:
- a CPU reference at libcft's formats, written as cft programs where v1 reaches, with DEBRIS-C's authority gates (Lasser et al.'s gravity and third bodies, and `testpo.421`), designed for certificates;
- the GPU route, replay-checked against that reference;
- the 24/7 loop on a local host, Logan's choice of host;
- MI300X runs.

**For each milestone:**
- Name which repository owns which part:
  - cft-debris (MIT): the systems and the loop, and later their certificates;
  - cft-fp256 (Apache-2.0): the language, cftc, the sequencer, the certificates' tools and the device library;
  - cft-rebound (GPL-3.0): any IAS15 derived from REBOUND.
- Name what it needs from cft-fp256 that does not exist yet, as a request the lead can put to cft-fp256's lead, with its evidence. For example:
  - pow as a routine;
  - a divide and square root inside a kernel (GPU-E's own question 2 to Logan, line 474, asks for them);
  - binary128 routine rates;
  - index tables;
  - the specialised tier for programs;
  - a `hip` target in cftc;
  - certificates for what Q2 found they cannot yet state, such as forcing that changes between segments. Certificates of runs on `hip:N` (their identity, their depth, and an audit in C) are already requested, on Logan's word of 2026-11-12.
- Name what cft-debris would give back: the test case cft-fp256's lead asked for when that work is planned (relayed). It is a small compiled system at binary128 and binary256, segmented as the days will be, with its software-backend digests, to stand beside the golden corpus in the gate for GPU certificates.

Label judgement BELIEVED. Where the evidence does not decide, make no recommendation.

**Instruments on this host:**
- C (gcc 16.1.0, mingw64) and Python with numpy, mpmath and rebound 5.1.1, as in the Rules. cftc needs only the standard library and mpmath (plan-verifier-D);
- Java 8, with Orekit 13.1.9 and Hipparchus 4.0.3 from the downloads;
- the preserved port, and the archive of cft-fp256;
- the web, HTML pages only.

**Do not:**
- write outside `studies\DEBRIS-D-architecture.md`, `studies\debris-d\` and your scratch;
- run anything on a GPU;
- message any session but the lead;
- weaken a claim's label, or a criterion, to make it pass.

**Report:** your final message, under 1,000 words:
- the short answer;
- Q1 to Q8, each with its most load-bearing evidence and its label;
- every control that failed, and what you did next;
- the requests for cft-fp256 that Q8 names;
- anything you could not settle;
- what you did not do;
- anything this brief got wrong.

---

## Brief: verifier-D (completed when DEBRIS-D reports)

You are **verifier-D**: a verifier, not an author. Try to disconfirm study DEBRIS-D, and report. Fix nothing. Budget: 2 hours of wall time and 15 CPU-minutes, counted by cycles. The lead books your time as a `notice`, and books any timing window you ask for.

**Threat model.**
- **In scope:**
  - counts, timings and compiled results that do not reproduce from DEBRIS-D's scripts, sources and rebuild commands;
  - a COMPUTED ladder figure whose inputs are misread, or whose arithmetic is wrong;
  - an ESTIMATE presented as a measurement;
  - READ claims the cited source does not support, cft-fp256's documents included;
  - a control that could not fail, or whose criterion was set after its data;
  - a claim whose domain or quantifier reaches past its evidence;
  - a figure carried over from an earlier study, or from cft-fp256, whose definition changed without saying so;
  - third-party source, or an image, in `studies\`.
- **Out of scope:**
  - re-deciding the build, which is Logan's;
  - the physics of the models themselves.

The attack list is finished from DEBRIS-D's own content, and starts with:
1. Rebuild libcft from the same archive (check its SHA-256 first). Rebuild Q2's images from their sources, and check each against its recorded SHA-256. Re-run the compiled systems and their three checks.
2. Re-run Q1's counting builds and their two controls.
3. Re-run Q3's host timings and their controls, in a window the lead books or under the Rules' fallback, and hold every card figure against the GPU-A lines it cites.
4. Re-run Q4's step counts and errors, at least once each.
5. Redo Q5's ladder from its stated inputs.
6. Fetch every load-bearing READ claim, HTML pages only, with a positive control on the fetch route, and record the route and the response for every "not found". Hold Q2's claims about v1 and about certificates against the lines of `docs/LANGUAGE.md` and `docs/CERTIFICATES.md`.
7. Hold the summary and the report against the tables, domain and quantifier included.
8. Check that criteria came before the data, by the logs' script hashes, with a negative control.
9. Check the lead's rulings in `lead.md`, and this plan's premises.
10. Anything else.

**Report:** your final message, under 1,200 words.
- For each item: the commands you ran, what you observed, and a verdict (confirmed, defect, or not determined).
- Every defect needs a concrete failure scenario. "Found nothing" is an acceptable answer.
- End with what you did not do, and anything this brief got wrong.

---

## What changed from draft 2 (plan-verifier-D's findings, answered)

plan-verifier-D's report is filed verbatim as `cft-debris-ledger\filed\DEBRIS-D-plan-verifier-D-report.md`. The lead checked each defect against its source before answering it (`lead.md`).

| plan-verifier-D found | draft 3 |
|---|---|
| 1. The ladder priced IAS15's counts for a route that runs only fixed-step methods (v1 has rk4, euler, stormer-verlet and map, and no adaptive steps); its integrator was unnamed, and the step counts came from a later question | The integrator is now Q4 and feeds the ladder, now Q5. Its main line is the v1 route at Q4's fixed-step counts; IAS15 sits beside it, labelled as a route v1 cannot run |
| 2. cftc has no `hip` target, and `hip:N` lacks INDEXED and AUGADD and fixes the depth at 256 | Q2 compares each image's features and depth against `hip:N`'s by hand; "a `hip` target in cftc" is among Q8's requests |
| 3. `python -m cftc` fails under `-I` | The Rules name the working form, and the `sys.path` step for scripts |
| 4. The hosts were cited to the wrong files, and the RX 7600's sharing is relayed | Q5 cites `resources.json` and marks the sharing as relayed; the 5060 Ti is "used from WSL cft-gpu", so the 24/7 host is Logan's decision in Q8 |
| 5. The evaluation counts lost their domain (a synthetic field), and their format dependence | "What DEBRIS-D starts from" carries both; Q1 counts with that domain |
| 6. A GPL-derived counting build had no named place | The Rules and the brief keep any copy of REBOUND's or cft-rebound's source in scratch |
| 7. A build from the archive reports an unknown build id | Phase 0 and the brief say so, and name the archive's SHA-256 as the record |
| 8. Decision 5 assumed a port is allowed | It now reads "via Orekit's code", and Q6 asks whether NRL's terms reach a port |
| 9. Q3 named no tool to run an image, nor GPU-A's lane-instruction rates | Q2 and Q3 name `positive-run`, cft-segrun and a timing driver; Q3 starts from GPU-A lines 861-866 |
| Notes: Windows targets end in `.exe`; cftc's own division and root are 155 to 191 instructions; the fixed path and the specialised tier were undefined; the scratch-depth wording was loose; the timing fallback was weaker than the window; the 10-times control cannot apply to `cft-bench`; the CPU budget was uncertain past degree 2; a repeat download counts toward CelesTrak's 50 errors | Each is answered in place: the Rules' C bullet; "What DEBRIS-D starts from"; the terms defined there; HOSTAPI's own words; the Rules' fallback marked as weaker; Q3's controls; decision 4's stop rule; Q7 |
| Notes it confirmed: cftc imports only the standard library and mpmath; `host/Makefile` has `cft-bench` and a Windows branch; the CelesTrak quotes hold; Q2's controls (a) and (c) can fail | Kept |

## What changed from draft 3 (plan-verifier-D's re-check, answered)

The re-check is filed verbatim as `cft-debris-ledger\filed\DEBRIS-D-plan-verifier-D-recheck-report.md`. The lead checked each defect against `docs/CERTIFICATES.md` before answering it (`lead.md`).

| the re-check found | draft 4 |
|---|---|
| 1. The flipped-bit control would be refused by a hash check before any segment is re-run, so it did not test the re-run; and whether the audit was full or sampled was unstated | Three controls, each refused by its own name: a self-consistent forgery, which a full audit must refuse `segment-end`; a flipped handed state, `state-hash`; and a changed body byte, `body-hash`. The re-check named the last `hash-line`, but CERTIFICATES.md's table gives `body-hash` for a body whose hash does not match. Every audit is full (`choose all`) |
| 2. The replay budget rested on a test that cannot mark, since divide and square root always decide their last bit | A second system adds exp, sin and cos: drag through an exponential atmosphere, and the Earth's rotation as forcing. If it marks no lane, the rate is reported as 0 in N with its bound, and the edge cases are priced as an ESTIMATE |
| 3. The stop rule never applied to the first test | The first test's sizes are fixed (96 steps, 4 segments, 8 lanes), and the stop rule applies past them |
| Notes: only the golden auditor is independent of libcft here; the golden auditor is a Python function, not a tool; "passes change with format" is not in DEBRIS-B; GPU-A's study code is in the tree, and what is missing is the backend; cft-segrun's keyed or open choice was unstated | The certificates subsection carries the independence caveat and what an auditor is handed; the Rules name `cert.audit(...)`; the passes line is narrowed to the step size; the terms say "not in the backend"; decision 7 puts keyed or open to Logan, as cft-fp256's rule has it |

## What changed from draft 4 (Logan's word on certificates, and cft-fp256's answer)

| the input | draft 5 |
|---|---|
| Logan: "*Certificate support can be built for but not implemented in order to still have gpu capability at the moment" | DEBRIS-D designs for certificates and writes none. Q2's certification, its audits and their three controls are gone; its reading of what a design needs stays. Draft 4's decision 7, keyed or open, leaves the round. The replay budget's marks now come from the software executor's lane bytes |
| Logan: "You can send a feature request to cft-fp256 regarding the certificate update to bring support up to the gpu backend" | Sent the same evening (`lead.md`, 20:30) |
| cft-fp256's lead's answer, filed in `relayed\` | cft-segrun already writes on `hip:N`, which draft 4 had read as impossible from its usage text. "Certificates on the GPU backend" now says what works, what does not yet, and what is READ and what relayed. Q8 adds the test case cft-fp256's lead asked for |

## What rounds DEBRIS-B and DEBRIS-C taught, applied here

| lesson | here |
|---|---|
| Criteria set after the data, and a redefined control reported as passing | Criteria before the data, asserted in code, and each script version kept under its hash (READY) |
| A cause blamed on a library that lay in the driver (DEBRIS-C, M1b) | Q2, Q3 and Q4 say what each measurement can and cannot attribute |
| A verifier's two hours of short runs, and the CPU counter that lied | `notice` bookings, a `sensitive` window for timings, and CPU counted by cycles (Rules) |
| The FTP path from a paper had moved | Sources are re-read at their current address, and a move is reported |
| An MIT repository with third-party models nearby | The Rules forbid copying third-party source, cft-fp256's and cft-rebound's included; Q4 and Q6 lay out each licence |
| The lead's own checks that could not fail | Every lead check in Phase 0 carries a control |
| A peer's answer is not a record | cft-fp256's lead's answers are filed verbatim, the passages they cite were read at the pinned commit, and what is only relayed is marked so |

## The lead's slips so far

Rounds DEBRIS-B's and DEBRIS-C's are in their records. In drafting DEBRIS-D, the lead's own check (`lead.md`) caught each of these before the plan verifier saw the plan:
- Draft 2 first carried three claims stronger than their source:
  - "binary64 is never the physical limit", where DEBRIS-B limits it to the regimes it tabulated;
  - "about 600 times" given as measured, where DEBRIS-B derived it from a measured order;
  - "no licence found" for NRLMSISE-00, where DEBRIS-B had READ one from a search excerpt.
- It cited Orekit's licence to DEBRIS-C, which never states it. This repository's README does.
- A doubled backslash in a Bash command broke a display of hashes; they were then taken in Python. This is the host trap the Rules name.

plan-verifier-D then found draft 2's nine defects, listed above. Two of them are the lead's slips of the same kind as the ones above:
- the hosts' citation (4) was written from memory, not from the files it cites;
- the counts' domain (5) was dropped, although the lead had read the line that states it.

The re-check of draft 3 found four more of the same kinds:
- a control that a hash check would refuse before the re-run it was meant to test;
- a marking rate to be measured on a test that cannot mark;
- a stop rule that its own first test never meets;
- passes said to change "with format", which DEBRIS-B does not show.

Draft 4 carried one more, which cft-fp256's lead's answer corrected. It read the absence of a `hip:` spelling in cft-segrun's usage text as "such runs could not yet be certified", without reading how the tool parses `--device`, which hands any device but `sw` to `cft_open` (`host/tools/segrun.c:4340`). The same sentence went into the evidence of the request to cft-fp256 (`lead.md`, 20:30 and 20:35).
