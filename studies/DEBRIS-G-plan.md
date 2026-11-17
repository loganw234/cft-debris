# DEBRIS-G: M1 at scale on amd-arc-box: how many objects in real time, at each number kind (plan of record, draft 3)

Drafted 2026-11-17 by cft-debris's lead for Logan's approval.
- This is a **measurement round** with a small build. It takes M1 as round DEBRIS-F left it (commit 1646c96, `src\` unchanged) and measures three things on amd-arc-box:
  - how many objects its 36 threads carry in real time, at each number kind;
  - whether each object's result stays bit for bit the same however the work is split, and on another machine;
  - whether a population paced to the wall clock keeps up for 20 minutes.
- **Draft 1** passed the lead's checker (`check_plan_g.py`, log 001: 139 checks, 0 failed).
- **plan-verifier-G** (Sonnet) then found three blockers, nine defects and notes. Its report is filed verbatim in the ledger's `filed\`. Draft 2 answers each finding in "What changed from draft 1". The lead checked the blockers and the first defect before answering, and surveyed the box's topology again for the first defect.
- **plan-verifier-G's scoped re-check of draft 2** confirmed the three blockers fixed, in its own reasoning. It found one new blocker, three defects and notes, also filed. Draft 3 answers them in "What changed from draft 2". Draft 3 has had the lead's check only.
- Nothing has been dispatched. Nothing is to be downloaded or requested in this round.

## The question, in Logan's words

- **This round:**
  - (2026-11-16, for F9's re-run) "You also have permission to run the tests on the 'amd-arc-box', which has many more cpu cores, its information should be in TimeSheet";
  - (2026-11-16, asked whether a 36-thread throughput run should go in F9's window or wait for this round) "Next round, though you have permission to utilize the box for the cpu or Intel arc card, the U50 is the only withheld resource on that machine.";
  - (2026-11-17, asked "Draft the next round's plan, starting with the 36-thread run on the box?") "Yes, draft it".
- **The goal** (2026-11-12): "a simulation capable of realtime (or slightly faster) simulation on a consumer card, so a 24x7 sim could run on a local box here for long run tests, validating itself with the open datasets update intervals, scaling tracked objects as the main scaling parameter presumably. High performance cards like the MI300X could then be used for higher density or faster/concurrent runs."
- **Carried from earlier rounds:**
  - the kinds (2026-11-13): "utilize native and cft for binary64 (and 32 if needed) so the library utilizes the entire precision range offered by cft, and the results can be compared for correctness";
  - the precision (2026-11-12): "Id also prefer to continue to utilize the higher precisions, simply to be a usecase for cft-fp256 as well";
  - the route through cft programs (2026-11-12): "*Yes if possible utilize cft programs, as well as generating certificates when able";
  - certificates (2026-11-12): "*Certificate support can be built for but not implemented in order to still have gpu capability at the moment".

## What DEBRIS-G is for

Logan's goal is a 24/7 simulation "on a local box here", scaled by the number of tracked objects. amd-arc-box is such a box, and its CPUs are open to cft-debris. So far M1 has only been priced one thread at a time:
- **DEBRIS-E** COMPUTED one desktop core's real-time load from single runs, in its uniform-rotation frame and at 64 lanes: about 1.7 million objects at native64 with the C library's functions, 1,570 at cft64, 990 at cft128 and 390 at cft256, at degree 20 with rk4 at 15 s (DEBRIS-F's plan, READ; the frame and the lanes READ from `studies\DEBRIS-E-build.md`).
- **DEBRIS-F's F9** measured the box's single thread, quiet (below).

No run has used more than one thread, and none has carried a population. Three things a 24/7 loop needs are untested:
1. **Throughput at scale.** With all 36 threads busy, the clock falls below one thread's turbo, and pairs of threads share a core.
2. **Determinism at scale.** An object's result must not depend on how the objects are batched into lanes or spread over workers. For the kinds built on libcft, it should not depend on the machine, the compiler or the C library either. DEBRIS-F's F8 tested reproducibility on one machine, for fixed batches.
3. **A loop paced to the clock.** A population held to real time for a sustained period must keep up.

| part | what it settles | the evidence it rests on |
|---|---|---|
| **P1. The population** | real orbit shapes at one epoch, one object per element set, scalable by replicas | its rule, written into its script before S0's values are read, and its counts |
| **P2 and P3. The driver and the harness** | M1's batches, run by many workers at once, timed and checked | gate G1 |
| **G2. Determinism across partitions** | each object's result is independent of its batch, its lane and its worker | bit-identity on the box |
| **G3. Determinism across machines** | the libcft kinds give the same bits on the desktop and on the box | bit-identity, with the C library's differences measured |
| **G4. Throughput** | object-seconds per second at each kind, by workers and lanes; the real-time capacity | a measurement, its statistics fixed before the data |
| **G5. A paced run** | the population at binary256 in real time for 20 minutes | its lag criteria, fixed before the data |

What this round does not do: change M1's library or physics, claim anything about accuracy, use the Arc card, request any data, or run the 24/7 loop itself ("Not in this round").

## What DEBRIS-G starts from (labels as in DEBRIS-C)

### M1, as round DEBRIS-F left it (MIT, commit 1646c96, on origin/main)

- **Six kinds:** native32, native64, cft32, cft64, cft128 and cft256. The native kinds can take libcft's correctly rounded transcendentals in place of the C library's: m1f's `--cr` sets `cr_transc` (READ, `tests\m1f.c`, `kopen`).
  - This plan calls the eight variants **kind-modes:** the six kinds, and native32 and native64 with libcft's transcendentals.
  - F9 timed seven of them, all but native32 with libcft's transcendentals. Its name for native64 with them is "native64, libcft's".
- **The driver, `tests\m1f.c`** (READ):
  - its `prop` mode runs one object at a time, at 1 lane, each from its own origin;
  - its `time` mode runs n lanes from 8 fixed states;
  - neither runs a population in batches, or more than one thread;
  - it keeps its inputs in process-wide variables (`G`, `DE` and `FT`), loaded once by `load_inputs`.
- **A batch shares one time grid:** the Sun, the Moon and the frame are evaluated once a stage for all its lanes (DEBRIS-E's plan, B3, READ). With rk4 at a fixed step, no lane's arithmetic reads another lane's. That is BELIEVED from the design; G2 tests it.
- **The frame table** is DEBRIS-F's `frame_main.bin`.
  - It covers TDB 2026-10-16 00:00 to 2026-11-19 00:00, 34 days (READ, `studies\DEBRIS-F-build.md`).
  - Its size is 4,410,718 bytes (MEASURED by the lead at DEBRIS-F's merge).
  - Its SHA-256 is in `studies\debris-f\logs\f9_time.001.log`'s header (READ). Copies are in DEBRIS-F's scratch and on the box, in `r2/in/`.
  - It is derived from the IERS's data, so it never enters the repository.
- **Measured in DEBRIS-F,** after verification:
  - F1: native equals cft bit for bit, at binary64 and binary32, in the real frame's new kernels, wherever only addition, multiplication, FMA, division and square root are involved;
  - F8: two runs agree, `-O0` equals `-O2`, and restarted segments equal the continuous run, at native64, cft64 and cft128, on one machine.
- **The C library's** `sin`, `cos`, `asin` and `acos` are not correctly rounded (DEBRIS-E, MEASURED by verifier-E). The box's C library (glibc) is not the desktop's (mingw-w64's). So native results with the C library's functions are expected to differ between the two machines. With libcft's transcendentals they are expected to agree. Both expectations are BELIEVED; G3 measures them.

### F9 on the box

These are MEASURED, DEBRIS-F, `studies\debris-f\logs\f9_box.001.log`, on 2026-11-16 at 14:30, at a load of 0.0 to 0.2%. They are one thread's seconds per object-day of rk4 at 15 s, each from a single short run:

| kind-mode | 1 lane | 64 lanes | one worker's real-time load at 64 lanes (COMPUTED: 86,400 s ÷ the 64-lane figure) |
|---|---|---|---|
| native32, C library | 0.158 | 0.066 | about 1.31 million |
| native64, C library | 0.159 | 0.067 | about 1.29 million |
| native64, libcft's transcendentals | 22.319 | 21.406 | 4,036 |
| cft32 | 89.560 | 54.363 | 1,589 |
| cft64 | 114.765 | 71.893 | 1,202 |
| cft128 | 166.906 | 120.139 | 719 |
| cft256 | 324.800 | 266.713 | 324 |

**What 36 workers might carry** (ESTIMATE): about 13.0 to 18.9 times one worker's figure.
- 18 cores (MEASURED, below);
- an all-core clock of 2.6 to 2.8 GHz, against one busy core's 3.6 GHz (the ceiling READ from the box; the all-core figure BELIEVED, not measured; G4 samples the clock);
- the second thread of each core adding 0 to 35% (BELIEVED; G4 measures it).
- So 18 × 2.6/3.6 × 1.00 = 13.0, and 18 × 2.8/3.6 × 1.35 = 18.9 (COMPUTED).

The resulting ranges, rounded:

| kind-mode | ESTIMATE at 36 workers |
|---|---|
| native32, C library | 17 to 25 million |
| native64, C library | 17 to 24 million |
| native64, libcft's transcendentals | 52,000 to 76,000 |
| cft32 | 21,000 to 30,000 |
| cft64 | 16,000 to 23,000 |
| cft128 | 9,300 to 13,600 |
| cft256 | 4,200 to 6,100 |

S0's 2,686 distinct element sets (below) would load cft256 at 44 to 64% of that range (COMPUTED).

### The box

MEASURED by the lead's read-only survey, 2026-11-17 05:55, `tools\survey-g\box_survey.001.txt` in the ledger:
- **The CPU:**
  - one Intel Xeon E5-2697 v4: 18 cores, 36 threads, one NUMA node;
  - logical CPUs 0 to 17 are distinct cores, and 18 to 35 their hyperthreads: for every c from 0 to 17, cpu c and cpu c + 18 are the two threads of one core, and the 18 cores are distinct. This was MEASURED for all 36 CPUs at 06:20, in `tools\survey-g\box_survey.002.txt`; the first survey sampled six;
  - 45 MiB of L3; `avx2` and `fma`, no `avx512f`;
  - the intel_cpufreq driver with the schedutil governor, 1.2 to 3.6 GHz, turbo on.
- **Memory:** 46 GiB, 44 available.
- **Software:** kernel 6.8.0-139, gcc 13.3.0, Python 3.12.3, `taskset`, `numactl` and `perf`, with `perf_event_paranoid` at 4.
- **Its nights are cft-fp256's** (READ, the TimeSheet):
  - the standing S003 holds the box's CPUs `shared` from 18:00 to 07:45, for cft-fp256's oracle work. The load average at 05:55 was 9.20;
  - the U50's S001 is `sensitive` over the same hours;
  - cft-fp256's rule ends every other box run by 17:50 on a nightly day (READ, from cft-fp256's memory, as the lead carries it).
- **The Arc A750** (DG2, 8086:56a1) runs the i915 driver, and its render nodes are open to the account. It has no compute runtime:
  - no Intel OpenCL runtime: the only OpenCL vendor file is Xilinx's, for the U50, though the OpenCL loader and headers are installed;
  - no Level Zero, and no oneAPI;
  - Mesa's Vulkan drivers and the Vulkan loader are installed, but no Vulkan development files and no shader compiler.
- **DEBRIS-F's run folders** `r1` and `r2` are still in `~/cft-debris-f9/`, an open item for Logan.

### The population's source

- **S0** is DEBRIS-F's GP snapshot of 2026-11-16: the CSV files of four CelesTrak groups, `stations`, `fengyun-1c-debris`, `iridium-33-debris` and `cosmos-2251-debris`. They are in the downloads, each with its SHA-256 in `lead.md`.
- **Its distinct sets:** the 2,696 objects that Orekit built hold 2,686 distinct element sets. 13 `stations` objects share 3 sets (MEASURED, the lead's `tools\dupcheck\dup_f.py`, output 003).
- **Per-object data derived from GP data** stay out of the repository (DEBRIS-F's decision 11).

### libcft

The pin stays at 0aa997a3: the archive `cft-debris-ledger\tools\cft-fp256-0aa997a3.tar`, whose SHA-256 is in `lead.md` and in DEBRIS-F's plan.

## The design, and why

**Workers are processes** (decision 3).
- Each worker is one process running M1 on its share of the population, pinned to one logical CPU:
  - workers 0 to 17 go to CPUs 0 to 17, one to a core;
  - workers 18 to 35 go to CPUs 18 to 35, the hyperthreads.
- So 18 workers fill the cores, and 36 fill the threads.
- With processes, no review is needed of whether M1's library and libcft are safe to share between threads.
- Each worker loads its inputs, then waits at a start barrier. Its timed region begins when the harness releases all workers together. It excludes the loading.
- Each worker reports when it was released, which CPU it ran on, and its CPU time at each stage. So the harness can show that the workers ran together, each on its own CPU, and computed only in their timed regions (G4's validity criteria, and G1's controls).

**The population is at one epoch** (decision 2). A batch's lanes share one time grid, so the population starts at one epoch E inside the frame table's window. Its orbit shapes come from S0's element sets. Its positions at E are not the sky's.

**Real-time capacity, defined.**
- **X** is the object-seconds simulated per second of wall time, summed over the workers. Its wall time runs from the first worker's release to the last worker's end.
- An object at real time needs one object-second a second. So X is the number of objects the configuration would carry at real time, if its cost per object held: **its real-time capacity**. At a speed-up s, it is X/s.
- **It is a throughput figure, not a carriage.** G4's runs carry at most 9,216 objects, and G5 carries the population's base. Above the population a run carried, memory and cache behaviour is not measured. So a capacity beyond it is an extrapolation of the run's cost per object, and is labelled so. The native kinds' capacities, in the millions, are all of that kind.

**Why a paced run.** X is measured with every worker flat out. A 24/7 loop instead holds itself to the wall clock, sleeping when ahead. G5 runs one such loop below capacity for 20 minutes, and records how far behind the clock each step finishes.

## The shape

| agent | job | model | when |
|---|---|---|---|
| the lead (this session) | <ul><li>Phase 0</li><li>the briefs and the ledger</li><li>every run on the box, its staging and its bookings</li><li>escalations</li><li>filing each final message</li><li>the merge and its narrowing</li><li>the commit</li><li>the round's record</li></ul> | Opus | throughout |
| DEBRIS-G | <ul><li>**phase 1:** P1 to P3 and the gates' code, tested on the desktop, and G3's desktop half</li><li>**phase 2:** the analysis of the box's logs, and the build report</li></ul> | Sonnet (decision 1) | after Phase 0; phase 2 when the lead resumes it with the box's logs |
| verifier-G | disconfirm DEBRIS-G's build, its gates and its figures | Haiku (decision 1) | when DEBRIS-G reports |
| merge-check-G | check any narrowing the lead makes at the merge | Haiku | after verifier-G, if the lead narrows anything |

## Phase 0: the lead, before dispatch

1. **The archive:** the one in the ledger's `tools\`. Its SHA-256 is checked again before dispatch.
2. **No downloads and no requests.** P1 reads S0 from the downloads, where it already is.
3. **The frame table:** the lead copies DEBRIS-F's `frame_main.bin` into the ledger's `tools\frame-f\`. Its SHA-256 is held to `f9_time.001.log`'s header, and it is read-only for every agent.
4. **TimeSheet:** DEBRIS-G's desktop time is booked as a `notice`. The box's windows are booked by the lead when each run is ready (decision 5). Nothing is booked on `arc-a750`.
5. **Ledger files:** `DEBRIS-G.md` and `verifier-G.md`, with headers only, and the folder `debris-g\` for the population and every per-object output (decision 10).
6. **Dispatch,** as in "Dispatch" below.

## Dispatch

- **The prompt:** a dispatch note and the agent's brief, followed verbatim by four sections of this plan: "Dispatch", "The ledger", "Rules every brief carries" and "READY". A script writes the prompt from this file. After dispatch, the prompt is checked against the harness's transcript.
- **The test escalation:** each agent sends one as it starts:
  - it writes `test escalation from <name>` in its own ledger file;
  - it sends the same words to the lead (SendMessage to `main`);
  - the lead replies "received" and records the round trip in `lead.md`.
- If no test escalation arrives from an agent within ten minutes of its dispatch, the lead reads that agent's ledger file, arms a watch on the ledger directory, and says so in `lead.md`.
- **DEBRIS-G runs in two phases:**
  - Phase 1's final message is its **hand-off**.
  - The lead files the hand-off and runs the box's work in this order: G1, whose controls must fail as specified first; then G2 and G3; then G4 and G5, in a `sensitive` window booked only after G1 has passed. It resumes DEBRIS-G with SendMessage, with the logs in place.
  - If a box run fails, the lead resumes DEBRIS-G with the failing log. DEBRIS-G fixes it and hands off again.
  - Phase 2's final message is DEBRIS-G's report.

## The ledger

The ledger is `C:\Users\logan\source\repos\cft-debris-ledger\`, as in rounds DEBRIS-B to DEBRIS-F.

- **One file per author, append only:**
  - `lead.md` continues;
  - this round adds `DEBRIS-G.md` and `verifier-G.md`, which the lead creates with a header only;
  - correct an entry by appending beneath it, never by editing it.
- **Times:** every heading's time comes from `date`, never from memory.
- **Read it at three moments:** before starting; before resting anything on another study's number; before the final report.
- **Verifiers read `lead.md` only,** and the files it points them to.
- **Escalation:** write the entry first, then message the lead (SendMessage to `main`). Wait for the answer to a question while working on what does not depend on it. Never end your turn to wait, except at the end of a phase.
- **No agent messages another session.** Questions for cft-fp256's lead go through this round's lead.
- **When to write:** when an entry would change another agent's work or the lead's: an environment fact, a brief that turned out wrong, or a finding about a shared input, never progress. Every entry marks which claims were measured and which are believed.
- **When a pause is announced,** record where you are before you stop. On resuming, do a full read, check your outputs before trusting your memory of them, and say where you stopped.
- **Scratch:** each agent creates its own directory when it starts, `C:\Users\logan\source\repos\cft-debris-scratch\<name>\`. Read no other agent's scratch. Keep no secrets anywhere an agent is given.
- **The downloads:** `C:\Users\logan\source\repos\cft-debris-downloads\`, one directory per file, each file's SHA-256 in `lead.md`. Read-only for every agent. This round adds nothing to them.
- **The tools:** `cft-debris-ledger\tools\`, read-only for every agent. It holds:
  - the archive `cft-fp256-0aa997a3.tar`;
  - `frame-f\frame_main.bin`, the frame table;
  - `survey-g\`, the lead's survey of the box.
- **Data kept out of the repository:** `cft-debris-ledger\debris-g\` (decision 10). It holds:
  - the population file;
  - every output that names or holds an object's state, from the desktop and from the box.
  
  DEBRIS-G writes there, the lead copies the box's per-object outputs there, and verifiers read it.
- **What the lead writes in `lead.md`, every verifier reads.** The lead records there every box run it makes, with its booking and its log's SHA-256. It never writes a judgement of DEBRIS-G's work there before verifier-G has reported.

## Rules every brief carries

These come from three places: Logan's standing rules (carried from cft-fp256 and cft-rebound, 2026-09 to 2026-11), canonical ParcelRound, and the rulings of rounds DEBRIS-B to DEBRIS-F.

- **Read-only, except your own outputs and scratch.**
  - cft-rebound, cft-fp256 and the TimeSheet are other sessions' live repositories. Read their files; in git, use only `git -C <repo> log` and `git -C <repo> show`. Never write in them, never run `git status` there, and never run a bare `git stash`.
  - In the TimeSheet you may run `timesheet.py check` and `list`, which only read.
  - cft-fp256 is Apache-2.0. Extract and build its archive only in your scratch.
  - In cft-debris, write only where your brief says. Commit nothing: the lead commits after verification.
- **The repository is public and MIT.**
  - Every source file you write carries a header naming cft-debris and the MIT licence.
  - Copy no third-party source into the repository, whether cft-fp256's, REBOUND's, cft-rebound's or Orekit's. libcft is linked from a build outside the repository and is never vendored; its header is reached by an include path.
  - Copy no third-party data into the repository either: no GP data, no IERS table, no frame table.
  - **Per-object data stay out of the repository** (decision 10). The population file, and every output that holds an object's state, go to `cft-debris-ledger\debris-g\`. Logs in the repository name objects only by their index in the population file, never by catalogue number. They carry hashes, counts and aggregates, never a state.
  - Reading a source to understand an interface is fine; quoting more than a short passage is not.
  - This project's own earlier code (DEBRIS-B's to DEBRIS-F's, and the lead's `tests\f9_box.py`) is MIT, and may be reused with a note of where it came from.
- **No downloads, installs or package managers, and no requests to any data service.**
  - This round needs no file beyond what is in the downloads and the ledger's `tools\`.
  - CelesTrak in particular: no agent requests it, not even for a page that looks like HTML.
  - If another file would settle a question, ask the lead for it. Give its name, source URL, size, licence and purpose. Each file needs Logan's approval.
- **Reading the web: HTML pages only, and never CelesTrak's.**
  - WebFetch returns a model's summary of a page, not its bytes. A figure or quote taken through it is labelled "READ (via WebFetch)". It supports "consistent with", never "confirmed".
  - WebFetch saves any response that is not HTML to disk. So a URL ending in `.txt`, `.pdf`, `.csv`, `.zip`, `.bin`, `.jar` or `.gfc`, or one in an FTP tree, is a download request, whatever it seems to hold.
- **No GPU, WSL, card or box.**
  - **amd-arc-box is the lead's.** No agent connects to it. Every run there is the lead's, in its bookings, from commands you hand it.
  - Code meant for the box keeps its Linux-only parts guarded, so that its other parts run on the desktop for testing.
- **Keys:** this round uses no keys and signs nothing. Never look in `~/.ssh`.
- **Timings: none on the desktop.**
  - The desktop is shared. Desktop runs are functional tests: no time from them is reported as a measurement.
  - The round's timings are the lead's runs of your harness on the box.
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
- **C on the box (the lead's runs):** gcc 13.3.0, `x86_64-linux-gnu`. libcft is built by `make -C cft-fp256/host CC=gcc libcft.a`, and M1 at `build_f.sh`'s O2 flags, as `tests\f9_box.py` does it.
- **Python:**
  - On the desktop: `C:\Users\logan\AppData\Local\Programs\Miniconda3\python.exe -I -B`, with numpy and mpmath.
  - Scripts that run on the box use Python 3.12's standard library only.
- **Processes and files:** kill only processes you started, and only by PID. Delete only what you made, and never through a computed path.
- **Earlier studies' records are read-only.** Copy what you run into your scratch or your own output folder. Before your report, check all seven:
  - `sha256sum -c SHA256SUMS` run from `studies\` shows 32 OK;
  - `find studies/debris-a -type f | wc -l` gives 29;
  - `sha256sum -c MANIFEST.sha256` shows 54 OK from `studies\debris-b\`, 136 OK from `studies\debris-c\`, 73 OK from `studies\debris-d\`, 60 OK from `studies\debris-e\` and 61 OK from `studies\debris-f\`;
  - there is no `__pycache__` anywhere under `studies\`.
- **Host traps:**
  - **System32 before PATH.** From Python, or anything else that calls CreateProcess, Windows searches System32 before PATH. So a bare `bash` is `C:\Windows\System32\bash.exe`, the WSL launcher, and a bare `timeout` is `TIMEOUT.EXE`. System32 also holds `wsl`, `tar` and `curl`. Start every program from Python by its full path, such as `C:/msys64/usr/bin/bash.exe` and `C:/msys64/mingw64/bin/gcc.exe`, or run it through the Bash tool directly (round DEBRIS-D, `lead.md`, 2026-11-12 21:23).
  - **MSYS `.exe` transparency:** writing a file `X` beside an existing `X.exe` writes to `X.exe`.
  - **CRLF:** passing a script to bash from Python with `text=True` turns every newline into CR+LF. So does any text-mode write from Python on Windows, `Path.write_text` included. Write bytes, or open with `newline="\n"`, wherever a file's bytes matter. This matters twice here: the box's shell will not run a script with CR bytes, and hashes are taken over bytes.
  - **Backslashes:** in the Bash tool, a doubled backslash reaches the shell as one, inside a heredoc too. Write any script that contains backslashes with the Write tool, and write Windows paths in commands with forward slashes. Checks run from such heredocs have matched nothing and printed no verdict (rounds DEBRIS-E and DEBRIS-F). Every check asserts that it found something to check.
  - **`cd`:** a Bash `cd` into a subfolder can move the session's working directory for every later call. Use absolute paths, or `git -C`.
  - **`grep` and CR:** Git Bash's `grep` strips the CR at each line end unless given `-U`. Count CRLF with Python.
  - **Transcripts:** a harness task's `%TEMP%` output file is empty while the agent runs. A transcript is read from the session's `subagents\` folder.
  - **Never start a process under `pythonw`,** or detached.
- **No helper agents.**
- **Your final message is your report,** or, for DEBRIS-G's phase 1, its hand-off. Its word limit is in your brief. If the harness refuses the write of a document your brief names, your final message is that document followed by the report, and the word limit then applies to the report alone.
- **Before you report,** stop any background work you started. End with what you did not do, and with anything your brief got wrong.

## READY, stated before the first pass

READY applies to DEBRIS-G and to every verifier's verdict. Every load-bearing claim must rest on one of:
- a measurement, with its command and output;
- a fetched source, cited by URL;
- arithmetic from labelled inputs.

Otherwise it is stated as a limit, in terms of the behaviour it concedes. A claim's domain and quantifier are claims, and so is a figure's definition. A number carried over from an earlier study keeps its definition, or it is re-measured.

**From rounds DEBRIS-B to DEBRIS-F:**
- **Every control states its pass and fail criteria before the data, and the code asserts them.** A control that fails as specified is reported as failed, whatever replaces it.
- **Every agreement claim states its tolerance before the data,** with its basis. In this round, every agreement is bit for bit.
- **A measurement with no pass condition states its statistics, its configurations and its sample before the data.** G4 is one.
- **Every log names the SHA-256 of the script that wrote it,** and the criterion that script asserted.
  - Keep every version of a script that wrote a log, under a name carrying the first 12 hex digits of its hash.
  - Never overwrite a log: number each run's log.
  - The manifest lists every version.
- **Every build prints the SHA-256 of every source it compiles.**
- **An ESTIMATE names its basis and its range,** and is never added to a MEASURED figure without saying so.
- **A bound over many trials holds only when the trials are independent.** Say what varies from trial to trial.
- **A cause is claimed only when a run isolates it.** Otherwise it is inferred, and labelled so.

**New in this round:**
- **Every throughput figure names its configuration:** the kind-mode, the workers, the lanes, the pinning and the steps. It also gives its run's foreign load and mean clock.
- **Every ratio of times says what it divides:** wall times or CPU times. Round DEBRIS-F called a ratio of wall times "per thread".

A verifier may reuse a run instead of re-running it only when all three of these hold:
- someone other than the author of the work made the run;
- its inputs are identical, file hashes included;
- the verifier re-runs from clean whatever it doubts.

The box's runs are the lead's, from DEBRIS-G's harness. So their logs count as made by someone other than DEBRIS-G, but not as independent of DEBRIS-G's code.

Only a wrong answer sends work back: a false claim, a measurement or check that cannot fail, or code that does not build or does not do what its gate says it does. Everything else is a note the lead records, and a sentence that claims too much is narrowed at the merge.
- **Loop cap (Logan, 2026-10-15, carried through the lead's memory):** after three NOT READYs for narrowing reasons, the next pass blocks only on wrong answers.
- **Threat model (Logan, 2026-10-02):** each verifier's brief states one, and findings outside it do not reopen the loop.

## Logan's decisions (each default stands unless changed)

1. **Models:**
   - (a) Sonnet for DEBRIS-G; Haiku for verifier-G and for a merge-check. This is Logan's pairing for simpler work (2026-10-12): the round adds a driver and a harness, not physics;
   - (b) Opus for DEBRIS-G and Sonnet for verifier-G, as in rounds DEBRIS-D to DEBRIS-F.
   - Default: (a).
2. **The population:**
   - (a) S0's element sets, one object per set, placed at one epoch E (P1), with replicas for larger runs. No request is made;
   - (b) a new snapshot that adds a larger group, such as `active`: a CelesTrak request, with Logan's approval by file;
   - (c) random synthetic orbits.
   - Default: (a). Its orbit shapes are real, and it needs nothing new.
3. **Workers:**
   - (a) processes, one a logical CPU, pinned as in "The design";
   - (b) threads in one process, after a review of whether M1's library and libcft are safe to share between threads.
   - Default: (a).
4. **The paced run (G5):**
   - (a) **cft256,** carrying the population's base objects (no replicas) on 36 workers, at real time, for 20 minutes. The fallback rule is fixed now: if G4's capacity at cft256 (36 workers, 64 lanes) is under 1.25 times the base count, G5 runs at cft128; if cft128's is under too, at cft64;
   - (b) native64 with libcft's transcendentals, at 80% of its capacity;
   - (c) no paced run.
   - Default: (a). It is the widest kind, as Logan's preference for the higher precisions asks, and the ESTIMATE puts the load at 44 to 64%.
5. **Box time:**
   - (a) at most 2 hours of `sensitive` windows on `box` for G4 and G5, booked by the lead, in the day, each ending by 17:50:
     - plan-verifier-G ESTIMATEs G4 at 49 to 65 minutes of timed runs plus 59 launches, and G5 at about 22 minutes: 1.3 to 1.7 hours in all;
     - G1 to G3's box work is short work: each gate under 10 minutes of wall time, its runs overlapping, run in the day when the TimeSheet answers FREE, and never in cft-fp256's nights;
     - verifier-G's box time, up to 30 minutes, comes on top of the 2 hours;
     - if no `sensitive` window opens in the round, G4 and G5 wait, and the lead tells Logan. Conflicts are never forced;
   - (b) other limits Logan names.
   - Default: (a).
6. **Who runs the box's work:**
   - (a) the lead, as the standing rule has it;
   - (b) DEBRIS-G itself, over ssh, inside the lead's bookings. Under (b), the box lines of the Rules and of DEBRIS-G's brief change before dispatch, and the lead's checker runs again.
   - Default: (a).
7. **The Arc A750:**
   - (a) not in this round;
   - (b) Logan installs Intel's OpenCL runtime for the card himself (Ubuntu's `intel-opencl-icd` package, and `clinfo`). The lead then records `clinfo`'s report on the card, as short work: its limits, and whether it lists binary64 (`cl_khr_fp64`). No kernel runs, and no gate rests on it.
   - Default: (a). The card needs a runtime first, and installing one is Logan's to do. The lead never runs `sudo`.
8. **Scope and budgets:**
   - (a) **One round:**
     - DEBRIS-G's phase 1: 4 hours of wall time and 30 CPU-minutes on the desktop. Its fixes after a failed box run: 1.5 hours and 12 CPU-minutes in all. Its phase 2: 1.5 hours and 10 CPU-minutes. It messages the lead before passing any of these, and before any single desktop run it expects to pass 5 CPU-minutes;
     - the box, under decision 5;
     - verifier-G: 2.5 hours and 20 CPU-minutes on the desktop, and up to 30 minutes of box time, run by the lead at its request;
     - a merge-check: 25 minutes.
     - **If time runs short,** the lead cuts in this order:
       1. G4's extra worker counts for cft64;
       2. G4's 8- and 256-lane runs;
       3. G5's length, to 10 minutes;
       4. G4's repeats, down to one. A capacity then rests on one run and says so, and there is no spread.
       
       G1 to G3, G4's core sweep and G5 are kept.
   - (b) **Two rounds:** G1 to G3 first; G4 and G5 in a second.
   - Default: (a). For scale, DEBRIS-F used about 56 of its 95 CPU-minutes.
9. **Outputs and the push:** the lead commits after verification and the merge. Pushing to the public repository waits for Logan's word.
10. **Per-object data:**
    - (a) the population file and every output holding an object's state stay in the ledger's `debris-g\`. The repository gets the rule, the counts, the files' SHA-256, and aggregates;
    - (b) the population is published in `studies\debris-g\` too, but only after the lead reads CelesTrak's terms on derived data and finds that they allow it, and Logan agrees.
    - Default: (a), as DEBRIS-F's decision 11. CelesTrak's terms for derived data were not read, so the plan does not assume they allow it.
11. **F9 on the desktop:**
    - (a) it stays open: the desktop has had no quiet window, and this round measures the box;
    - (b) the lead re-runs F9 on the desktop if a `sensitive` window opens there during the round.
    - Default: (a).
12. **libcft:**
    - (a) the archive in the ledger, at 0aa997a3, as in DEBRIS-E and DEBRIS-F;
    - (b) a newer pin, with a new archive made in Phase 0.
    - Default: (a). G3 then compares builds of one libcft source on two machines.

## Not in this round

- **The 24/7 loop itself:** ingesting GP updates, scheduled snapshots, validating against them, and running as a service. G5 is its first paced step.
- **The Arc A750,** unless decision 7(b).
- **Threads within a process** (decision 3(b)).
- **Any change to M1's library,** its physics or its accuracy. `src\` stays byte for byte as at commit 1646c96. This round claims nothing about accuracy.
- **A faster correctly rounded binary64 library.** At 64 lanes, F9's native64 with libcft's transcendentals took about 320 times as long as with the C library's (21.406 s against 0.067 s an object-day, COMPUTED from MEASURED). A correctly rounded library built for binary64 speed could close much of that gap, with results that would not depend on the machine. Its licence and its agreement with libcft would come first. That is a later round's, if Logan wants it.
- **The MI300X,** the GPU route through cft-fp256, and certificates.
- **Any download or request,** any account, and any GPU, WSL or card.

---

## Brief: DEBRIS-G

You are build parcel **DEBRIS-G** in cft-debris, a project for space-debris tracking and simulation. Its folder, `C:\Users\logan\source\repos\cft-debris`, is a public git repository under the MIT licence. You build what the lead needs to measure, on amd-arc-box, how many objects M1 carries in real time at each kind:
- a population;
- a batch driver;
- a harness.

Then, in a second phase, you analyse the box's logs and write the build report. You never connect to the box: the lead runs everything there. You commit nothing: the lead commits after verification.

**Two phases.**
- **Phase 1:** 4 hours of wall time and 30 CPU-minutes on the desktop. It covers P1 to P3, the gates' scripts, their tests on the desktop, and G3's desktop half. It ends with your hand-off, your final message, under 600 words:
  - the files the lead stages to the box, with their SHA-256;
  - the exact commands in order, each with its expected wall time (ESTIMATE) and what it must print;
  - what is per-object and must come back to the ledger, not the repository.
- **Fixes:** if a box run fails, the lead resumes you with its log. Fix, re-test on the desktop, and hand off again: up to 1.5 hours and 12 CPU-minutes in all. That covers one more run of G3's desktop half, about 5 to 5.5 CPU-minutes (plan-verifier-G's ESTIMATE).
- **Phase 2:** 1.5 hours and 10 CPU-minutes. The lead resumes you when the box's logs are in `studies\debris-g\box\` and its per-object outputs in the ledger's `debris-g\box\`. You run the analysis and G3's comparison, and write the build report. Your final message then is your report.
- Message the lead before passing any budget, and before any single desktop run you expect to pass 5 CPU-minutes. cft-kind runs are slow: at 64 lanes, F9 measured 54 to 267 s an object-day on one thread (above). So hold desktop tests to a few steps.

**Start here:**
1. This plan, `C:\Users\logan\source\repos\cft-debris\studies\DEBRIS-G-plan.md`: Logan's words, what each part settles, and what the round starts from.
2. M1:
   - `src\`;
   - `tests\m1f.c` and `tests\build_f.sh`;
   - `tests\f9_box.py` and its shim `tests\f9_box_windows.h`. These are the lead's Linux harness for F9. Its build criteria B1 to B5, its source-hash list and its load measurement are the model for yours;
   - `studies\DEBRIS-F-build.md` (narrowed at the merge; its last section lists the narrowings). Its §4, at F9, has the box's figures;
   - `studies\debris-f\`.
3. `lead.md` in the ledger: Phase 0, S0's files and their SHA-256 (2026-11-16), and the frame table's copy.

**Where it goes:**
- `tests\`: the new driver and scripts. `src\` stays byte for byte as at commit 1646c96, and your builds assert it;
- `studies\debris-g\`: the logs and records, with a `MANIFEST.sha256` over them. The lead puts the box's logs in `studies\debris-g\box\`;
- `studies\DEBRIS-G-build.md`: the build report. It covers what was built, how to build and run it, each gate's criteria and result, G4's tables, G5's lag, and the limits;
- `cft-debris-ledger\debris-g\`: the population file and every output holding an object's state (decision 10);
- **in your scratch only:** cft-fp256's sources, libcft's build, every executable, and the frame table's working copy.

**P1. The population.** One script makes it. The script fixes every rule below before it reads S0's values.
- **Rows:** S0's four CSV files, in the downloads; ephemeris type 0 only.
- **One object per element set:** rows whose `EPOCH`, `MEAN_MOTION`, `ECCENTRICITY`, `INCLINATION`, `RA_OF_ASC_NODE`, `ARG_OF_PERICENTER`, `MEAN_ANOMALY`, `BSTAR`, `MEAN_MOTION_DOT` and `MEAN_MOTION_DDOT` are equal as parsed binary64 values form one set. Keep the smallest catalogue number in each. The lead's count over the objects Orekit built is 2,686 sets; give yours, and say why it differs if it does.
- **The screen:** exclude any set whose perigee is under 200 km. Take the perigee as a(1 − e) − 6,378.137 km, with a from the mean motion by Kepler's third law and GM = 3.986004415e14 m³/s² (EIGEN-6C4's). Count the exclusions.
- **The epoch E:** a time on M1's grid inside the frame table's window, at least 2 days from either end. State it, with `jd_epoch` and `t0`, before reading S0's values.
- **The state at E:**
  - take the mean elements as osculating Keplerian elements;
  - advance the mean anomaly two-body from the set's epoch to E; keep the other elements;
  - convert to position and velocity in M1's inertial frame, taking TEME's axes as GCRS's.

  So the positions are not the sky's, and the frames' difference is ignored. State both as limits.
- **The drag and radiation parameters:** `bc` = 0.01 m²/kg and `cram` = 0.01 m²/kg for every object: DEBRIS-F's starting `bc` and its fixed `cram` (`studies\DEBRIS-F-build.md`, B4).
- **The order:**
  - the base objects in a seeded random permutation, with the seed stated beforehand;
  - then replicas k = 1, 2 and 3 of every base object, in the same order. Replica k has its position and velocity rotated about the z axis by k × 137.50776405 degrees.
  
  That is four copies in all, and about 10,700 objects.
- **The file:** one line an object, with its index, its replica number, its catalogue number, `t0`, the state, `bc` and `cram`, every value binary64 in `%a` hex. It goes in the ledger's `debris-g\`, and its SHA-256 goes in the build report.

**P2. The driver:** a new C program in `tests\`, with an MIT header, built with M1's library and libcft.
- **Inputs:** a kind-mode, the frame table, the population file, a slice (first index and count), lanes L, steps S, and passes.
- **The inputs' checks:** every object in the slice has the same `t0`, since the model's `t0` belongs to the context. The driver prints the SHA-256 of every binary64 value it parsed, in order.
- **The loop is step-major.** Each step advances every batch of the worker by one rk4 step of 15 s, batch after batch.
- **Steps and passes:** S is the run's total step count. The run makes ⌈S/5,760⌉ passes, each from the initial states: every pass takes 5,760 steps (one day) but the last, which takes the rest. X counts every pass's object-seconds. The final states are the last pass's.
- **The timed region** runs from the barrier's release to the end of the last step:
  - on Linux, by `CLOCK_MONOTONIC`, which all processes share, and the process's CPU time by `CLOCK_PROCESS_CPUTIME_ID`;
  - on Windows, for desktop tests, by `QueryPerformanceCounter` and `QueryProcessCycleTime`.
- **The barrier:** after loading, the driver prints `READY`, flushes it, and blocks on reading one byte, `G`, from standard input in binary mode. (On Windows, a byte 0x1A reads as end of file in text mode.)
- **What each worker reports:**
  - the time it read the release byte, and the time its last step ended;
  - its CPU time at `READY`, at the release and at the end;
  - the CPU it ran on at its start and at its end (`sched_getcpu`, Linux only), and its affinity;
  - its own peak resident memory: `getrusage`'s `ru_maxrss` on Linux, `GetProcessMemoryInfo` on Windows.
- **A planted fault, for G1's control C4 only:** `--plant-early-clock` starts the timed region before the loading.
- **The paced mode:** after each step, if the step's deadline lies ahead, the driver sleeps until it. The deadline is the release time plus 15 s × the steps done, divided by the speed: 1 in G5, 1,000 in G1's control C5. It records each step's lag, its finish time less its deadline.
- **The end checks,** at the end of every pass: every state finite, and every object's distance from the centre above 6,498.137 km (120 km above 6,378.137 km).
- **The outputs:**
  - per object: each final state in the kind's own bytes, in hex, and in binary64. These are per-object;
  - per run: the timings and the reports above, the step count, every lag in the paced mode, and the SHA-256 of all final states in index order.

**P3. The harness:** a Python script in `tests\`, standard library only. Its modes are `build`, `smoke`, `g2`, `g3`, `sweep` and `paced`.
- **Before it pins anything** (Linux): it asserts that its own affinity is CPUs 0 to 35, and reads every CPU's `thread_siblings_list`, asserting the pairing that "The box" gives.
- **Workers:** it starts them, pins them with `os.sched_setaffinity` on Linux (unpinned on Windows), waits for every `READY`, notes its release time, then releases them together.
- **The box's foreign load,** for each run:
  - read `/proc/stat` at the release and when the last worker reports its timed region done;
  - the foreign load is the CPU time of everything but the workers (`/proc/stat`'s busy time less the workers' own CPU times), as a share of 36 × the wall time;
  - also read `/proc/loadavg` before the run.
- **The clock:** each pinned CPU's `scaling_cur_freq`, sampled once a second during the run, and its mean over the run. This is the kernel's reading. Under `intel_cpufreq` it may be the governor's request rather than the achieved clock (plan-verifier-G, from its recall of the kernel; not checked here). G1's calibration says which.
- **Memory:** each worker's own report of its peak.
- **Its logs** name its own SHA-256 and the driver's, its criteria, and every configuration. It never overwrites a log. It works from its run folder with relative paths, so no home path reaches a log. Per-object outputs go to a folder of their own, for the lead to bring back to the ledger.
- **On the desktop,** the Linux-only parts are skipped, and say so in the log.

**The gates.** For each gate: write its criteria into its script before its data, assert them in code, and give it a negative control that must fail as specified. The NaN rule holds throughout, as in DEBRIS-E: non-NaN results agree bit for bit, and NaN results agree as NaNs.

- **G1. The build and the harness,** on the desktop (yours) and on the box (the lead's):
  - **the build:** on the desktop, `build_f.sh`'s criteria; on the box, `f9_box.py`'s B1 to B5. On both, every file of `src\` byte-identical to commit 1646c96, each SHA-256 printed;
  - **a smoke run** of every kind-mode: 4 lanes, 2 steps;
  - **the clock's calibration** (box): a fixed-work loop of dependent integer additions, on 1 worker and then on 36 at once.
    - Its rate is COMPUTED at one addition a cycle (BELIEVED for such a chain on this part), beside the kernel's frequency reading at the same time. If the two differ by more than 5%, the report gives the clock as the kernel's reading only.
    - The optimiser must not remove the loop: its accumulator is stored through a `volatile` each iteration, its count is read at run time, and the build log keeps the loop's disassembly.
    - It checks the kernel's reading at 1 and at 36 busy workers. It does not show the clock under M1's own load;
  - **negative controls.** Each must fail as specified, and the harness asserts it:
    - C1, the build: a copy of one source changed by one byte must fail the source check;
    - C2, foreign load (box): a throughput run at W = 9, with a busy loop the harness starts pinned to CPU 35 for the whole run, must come out void on foreign load. One busy CPU is 2.8% of 36;
    - C3, pinning (box): a run at W = 2, with both workers pinned to CPU 0, must come out void on its CPU share;
    - C4, the timed region: a run with the driver's planted early clock must come out void on its start time;
    - C5, the lag: a paced run of native64 with libcft's transcendentals, 1 worker, 64 lanes, at 1,000 times real time, must fail the lag criterion within 2 minutes.
    
    C1, C4 and C5 run on the desktop too, as functional tests. The harness stops its busy loop by its PID.
- **G2. Determinism across partitions,** on the box, at all eight kind-modes. The population's first 64 objects run 40 steps under five partitions:
  - Q1: one worker, one batch of 64 lanes;
  - Q2: 8 workers of 8 lanes, object i in worker i mod 8;
  - Q3: 36 workers, the objects dealt round-robin, 1 or 2 lanes each;
  - Q4: one worker, 64 batches of one lane;
  - Q5: one worker, one batch of 64 lanes in reverse order.
  
  **Pass:** every object's final state is equal bit for bit across Q1 to Q5.
  
  **Negative control:** Q1 again, with one object's initial x moved by one ulp of the kind's input format. For the 32-bit kinds, x is rounded to binary32, moved to the next binary32 above, and written back exactly as binary64. For the others, it is the next binary64 above x. Exactly that object's final state must differ, and no other. A coupling between lanes would spread the change.
  
  G2 is not a timing, so its runs overlap, and the gate takes a few minutes of wall time. Run one after another, its runs would take about 18 minutes (plan-verifier-G's ESTIMATE). The lead runs it as short work.
- **G3. Determinism across machines.** The population's first 16 objects run 240 steps (one hour) at all eight kind-modes, in one worker, one batch of 16 lanes. You run it on the desktop in phase 1, and the lead runs it on the box.
  - **The inputs first:** the two machines' input files (the population, the frame table, the gravity field and DE421) must have the same SHA-256, and so must each driver's hash of the values it parsed.
  - **Pass:** cft32, cft64, cft128 and cft256, and native32 and native64 with libcft's transcendentals, give every final state bit for bit equal on the two machines.
  - **And, on each machine:** native64 with libcft's transcendentals equals cft64, and native32 with them equals cft32, bit for bit. This is BELIEVED from DEBRIS-E's and DEBRIS-F's F1. If it fails, find the first step and the first operation that differ, and report it as a finding.
  - **No pass condition** for the native kinds with the C library's functions: give how many objects differ between the machines, and the largest difference in position after 240 steps.
  - **Negative control:** the comparison, run on a copy of the box's output with one bit flipped in one object's state, must flag exactly that object.
- **G4. Throughput:** a measurement, on the box, in a `sensitive` window. Its configurations, its statistics and its validity criteria are fixed in its script before the data.
  - **The configurations,** at each of the seven kind-modes that F9 timed:
    - workers W = 1, 9, 18 and 36, at L = 64 lanes;
    - L = 8 and 256, at W = 36;
    - for cft64 only, W = 2, 4 and 27, at L = 64;
    - W = 36 at L = 64 two more times, three in all.
  - **Each run** takes the population's first W × L objects. Worker w takes objects w·L to w·L + L − 1. Workers are pinned as in "The design".
  - **Its steps:** S is fixed for each kind-mode and L. It is the smallest whole number of steps that one worker would take 30 s over, by F9's figure for that kind-mode (the 1-lane figure for L = 1, the 64-lane one otherwise), and at least 2. Log S before the run.
    - For the native kinds with the C library's functions, S spans several passes (P2): about 40,300 steps at 64 lanes.
    - F9's 64-lane figures for the cft kinds rest on 2 to 4 steps each. They size the runs here, and predict nothing: cft256's S is 11 steps.
  - **A run is valid only if:**
    - every worker exits 0, and the end checks pass;
    - **the workers ran together:** every worker read its release byte within 50 ms of the harness's release, and no worker's timed region began before the release;
    - **they computed only when timed:** each worker used under 10 ms of CPU between `READY` and its release, and CPU for at least 95% of its timed region's wall time;
    - **each ran on its own CPU:** its affinity was that CPU alone, and it was on that CPU at its start and at its end;
    - the foreign load is at most 2%;
    - the wall time is at least 20 s.
    
    A run that fails the load criterion is repeated once. If it fails again, it is recorded as void, and not used. G1's controls C2 to C4 show that these criteria can fail. The control runs are exempt from the repeat: each is expected to come out void on its first run.
  - **A check in every run:** worker 0's slice is the same 64 objects in every run at L = 64 for a kind-mode, with the same S. So its final states' SHA-256 must be the same across all those runs: every W, and every repeat.
  - **The figures:**
    - X for each run;
    - for each kind-mode at L = 64: X(W) ÷ (W × X(1)), the parallel efficiency, and X(36) ÷ X(18), what the hyperthreads add;
    - X at L = 8, 64 and 256, at W = 36;
    - the spread of the three repeats, as their largest ÷ their smallest. They run one after another, so the spread says nothing of how a later window would differ;
    - each run's mean frequency reading, read as G1's calibration allows, and each worker's peak memory.
  - **The real-time capacity** of each kind-mode is X at W = 36 and L = 64, the median of the three repeats. No other configuration is put in its place, even a faster one. A faster one is reported beside it.
- **G5. The paced run,** on the box, in a `sensitive` window, under decision 4:
  - the kind-mode by decision 4's rule, which the script asserts from G4's figures;
  - the population's base objects, no replicas;
  - 36 workers, with ⌈N/36⌉ lanes each and the remainder on the last;
  - real time, for 20 minutes of wall time.
  
  **Pass, fixed before the data:** every worker's lag is at most 15 s (one step) at every step. Also, every worker exits 0, the end checks pass, and G4's validity criteria hold, all but the CPU share. A paced worker sleeps when it is ahead, so its CPU share is its load, which G5 reports. A worker starved of its CPU would fall behind, and the lag criterion catches that. G1's control C5 shows the lag criterion can fail.
  
  **Report:** each worker's lag (its median, 99th percentile and largest), the share of the wall time the workers were busy, the mean clock, the kind-mode and N.

**Instruments:**
- on the desktop: C, with gcc 16.1.0 from mingw64, and Python with numpy and mpmath;
- the archive of cft-fp256;
- the box, through the lead;
- the web, HTML pages only, and never CelesTrak.

**Do not:**
- write outside `tests\`, `studies\debris-g\`, `studies\DEBRIS-G-build.md`, the ledger's `debris-g\` and your scratch;
- change anything in `src\`;
- put any per-object output, catalogue number or state in the repository;
- connect to the box, or run anything on a GPU;
- request any data service;
- message any session but the lead;
- report a desktop time as a measurement;
- weaken a gate's criterion, or a claim's label, to make it pass.

**Report:** your final message in phase 2, under 1,200 words:
- what was built;
- each gate's result, with its most load-bearing evidence and its label;
- G4's capacities, and its efficiency and hyperthreading figures, in brief;
- G5's result;
- every control that failed, and what you did next;
- anything you could not settle;
- what you did not do;
- anything this brief got wrong.

---

## Brief: verifier-G (completed when DEBRIS-G reports)

You are **verifier-G**: a verifier, not an author. Try to disconfirm DEBRIS-G's build, its gates and its figures, and report. Fix nothing.
- **Budget:** 2.5 hours of wall time and 20 CPU-minutes on the desktop, counted by cycles. The lead books your time as a `notice`.
- **Box time:** up to 30 minutes, run by the lead at your request. Give the exact commands. The lead runs them and returns the logs. You never connect to the box.

**Threat model.**
- **In scope:**
  - code that does not build from clean with the build report's commands;
  - a timed region that includes the loading, or leaves out work;
  - workers that did not run at the same time;
  - foreign load the harness could not see;
  - a capacity, efficiency or ratio that does not follow from the logs;
  - a determinism claim on partitions, kind-modes or machines the gate did not test;
  - a criterion, a configuration or a rule set after its data;
  - the population's rule, and its counts;
  - per-object data, or third-party source or data, in the repository.
- **Out of scope:**
  - the choice of route, which is Logan's;
  - the box's hardware;
  - M1's physics and accuracy.

The attack list is finished from DEBRIS-G's own content, and starts with:
1. Build libcft from the archive, and M1 and the driver from clean, in your scratch, with the build report's commands.
2. Re-run G2's partitions on the desktop on a few objects for a few steps, with a partition of your own.
3. Re-run G3's desktop half, and compare it with the box's per-object outputs in the ledger.
4. Recompute G4's figures and capacities, and G5's lags, from the logs.
5. Read the harness's load and clock accounting, and test it: ask the lead to re-run three G4 configurations of your choice.
6. Check criteria before data, by the logs' script hashes, with a negative control.
7. Re-derive the population's counts from S0, and check the per-object rule.
8. Anything else.

**Report:** your final message, under 1,200 words.
- For each item: the commands you ran, what you observed, and a verdict: confirmed, defect, or not determined.
- Every defect needs a concrete failure scenario. "Found nothing" is an acceptable answer.
- End with what you did not do, and anything this brief got wrong.

---

## What changed from draft 1 (plan-verifier-G's findings, answered)

plan-verifier-G's report is filed verbatim as `cft-debris-ledger\filed\DEBRIS-G-plan-verifier-G-report.md`. The lead checked the three blockers against the plan and the code before answering, and surveyed the box's topology again for the first defect.

| plan-verifier-G found | draft 2 |
|---|---|
| **Blocker 1.** G3 names native32 with libcft's transcendentals, a variant outside the seven kind-modes | Confirmed by the lead. There are now eight kind-modes: the six kinds, and native32 and native64 with libcft's transcendentals. G2 and G3 run all eight; G4 runs the seven that F9 timed |
| **Blocker 2.** G2's control moves x by one binary64 ulp, which the 32-bit kinds round away, so the control fails at two modes by construction | Confirmed by the lead: the population is binary64, and the 32-bit kinds convert it by rounding. The control now moves x by one ulp of the kind's input format |
| **Blocker 3.** G4 and G5 have no negative controls, and G4's validity criteria cannot catch staggered workers, a worker off its CPU, or loading inside the timed region | Confirmed. Each worker now reports its release, its CPU, and its CPU time at each stage. G4's validity requires that the workers ran together, each on its own CPU, computing only when timed. G1 adds controls on the box: an injected busy loop (C2), a planted pinning fault (C3), a planted early clock (C4), and a paced run at 1,000 times real time (C5). The lead runs G1 first, and books G4's window only after G1 passes |
| The sibling pairing was called MEASURED from 6 of 36 CPUs | Confirmed. The lead surveyed all 36 at 06:20 (`box_survey.002.txt`): cpu c and cpu c + 18 share a core for every c from 0 to 17, over 18 distinct cores. The harness asserts the pairing before it pins |
| How S maps to passes was undefined for the native kinds | P2 defines S as the run's total step count, in ⌈S/5,760⌉ passes, the last taking the rest |
| The mean clock may be the governor's request, not the achieved clock | The plan calls it the kernel's reading. G1 calibrates it with a fixed-work loop, and the report reads it only as far as the calibration allows |
| G1 named f9_box.py's Linux criteria for the desktop too | The desktop's build uses `build_f.sh`'s criteria, and the box's uses B1 to B5 |
| The fix allowance could not cover one more run of G3's desktop half | It is now 1.5 hours and 12 CPU-minutes |
| Decisions 6(b), 7(b) and 10(b) had no matching content | 6(b) says what changes before dispatch. 7(b) is the lead's record of `clinfo`'s report, with no kernel and no gate. 10(b) waits on CelesTrak's terms and on Logan |
| Box time: whether the verifier's 30 minutes sit inside the 2 hours, and what "under 10 minutes each" covers | The verifier's time comes on top of the 2 hours. Each of G1 to G3 takes under 10 minutes of wall time, its runs overlapping, in the day, and never in cft-fp256's nights |
| "Carries N objects at real time" extrapolates from at most 9,216 objects; DEBRIS-E's loads were in its uniform frame at 64 lanes | Capacity is defined as a throughput figure, and any capacity beyond a run's population is labelled an extrapolation. DEBRIS-E's frame and lane count are stated |
| The cut order took G4's repeats to one, where the capacity is a median of three | The repeats are cut last. A capacity on one run says so, with no spread |
| **Notes:** cft256's S rests on 2-step figures; `READY` unflushed, and a 0x1A byte on Windows; the race in reading `VmHWM`; one `t0` per context; the harness's own affinity; G3's inputs; adjacent repeats | P2 flushes `READY`, reads the byte `G` in binary mode, reports its own peak memory, and asserts one `t0`. P3 asserts its affinity and the pairing. G3 compares the inputs' hashes and the parsed values' hash. G4 says what F9's cft figures can do, and that the repeats are adjacent |

## What changed from draft 2 (plan-verifier-G's re-check, answered)

The re-check is filed verbatim as `cft-debris-ledger\filed\DEBRIS-G-plan-verifier-G-recheck-report.md`. It confirmed draft 1's three blockers fixed, each by its own reasoning, and that G1's controls C2 to C5 can each fail.

| the re-check found | draft 3 |
|---|---|
| **Blocker.** G5 could never pass: it inherited G4's rule that a worker computes for at least 95% of its timed wall time, and a paced worker sleeps when ahead, at an ESTIMATEd 44 to 64% load | Confirmed by the lead. G5 keeps G4's validity criteria, all but the CPU share, and reports the share as its load. A worker starved of its CPU falls behind, and the lag criterion catches it |
| C2's deliberate failure would trigger the rule that repeats a run failing on load | The control runs are exempt, and each is expected to come out void on its first run |
| The end checks covered only the last pass, which can be one step long; whether X counts every pass was unstated | The end checks run at the end of every pass, and X counts every pass's object-seconds |
| The calibration loop could be optimised away, and the 5% rule says nothing of the clock under M1's load | The loop's accumulator is stored through a `volatile` each iteration, its count is read at run time, and its disassembly is logged. The plan says the calibration checks the kernel's reading at 1 and at 36 busy workers only |

## What earlier rounds taught, applied here

| lesson | here |
|---|---|
| DEBRIS-F's samples counted docked vehicles as separate objects, because they share their station's element set | P1 takes one object per element set |
| F9's driver was written for Windows alone, so the box needed a harness of its own | the driver and the harness are written for both machines from the start |
| F9's ratios of wall times were called "per thread" | READY: every ratio of times says what it divides |
| DEBRIS-F's plan expected a `sensitive` desktop window that never opened | decision 5 says what happens without a window, and the box's nights are named |
| F7 was priced without its control | G2's and G3's controls are counted in their runs |
| Two of DEBRIS-C's figures were carried from memory notes into DEBRIS-F's draft 1 | the lead's checker holds every figure here to its source |
| Criteria set after the data; logs without script hashes; builds without source hashes | READY, as in DEBRIS-F |
| A bare `bash` from Python reached WSL (DEBRIS-D) | the Rules' first host trap |

## The lead's slips so far

Rounds DEBRIS-B's to DEBRIS-F's are in their records. In drafting DEBRIS-G:
- **The survey's first package query** went through three layers of quoting, matched nothing, and printed "none". A plain `dpkg -l` on the next call listed the packages, and the recorded survey uses it. The zero count is what exposed the slip.
- **Draft 1 called the sibling pairing of all 36 CPUs MEASURED** when the survey had sampled six. plan-verifier-G caught it, and the second survey measured all 36.
- **Draft 1 named a native32 mode outside its own seven kind-modes, gave G2 a control that could not bite at binary32, and left G4 and G5 without negative controls.** These were plan-verifier-G's three blockers.
- **Draft 2 made G5 inherit G4's CPU-share rule,** which a paced worker cannot meet. This was the re-check's blocker.
