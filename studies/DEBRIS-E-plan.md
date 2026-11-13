# DEBRIS-E: the CPU reference propagator at six number kinds, native and cft, held to its referees (plan of record, draft 3)

Drafted 2026-11-13 by cft-debris's lead for Logan's approval.
- This is a **build round**: it builds the first milestone of the route Logan asked for, M1, the CPU reference propagator.
- Draft 1 passed the lead's checker (`check_plan_e.py`, log 001: 86 checks, 0 failed). plan-verifier-E (Sonnet) then found two blockers, nine defects and notes. Its report is filed verbatim in the ledger's `filed\`, and draft 2 answers each finding in "What changed from draft 1".
- plan-verifier-E's scoped re-check of draft 2 found one blocker and three defects, also filed. Draft 3 answers them in "What changed from draft 2". Draft 3 has had the lead's check only.
- Nothing has been dispatched, and nothing has been downloaded.

## The question, in Logan's words

- **The route** (2026-11-13): "What route would you recommend? Considering building a custom solution simply so the existing tools can be utilized as reference models, while ours can be tweaked as needed to improve the accuracy of the simulation"
- **This round** (2026-11-13), answering the lead's recommendation: "Yes draft it, however utilize native and cft for binary64 (and 32 if needed) so the library utilizes the entire precision range offered by cft, and the results can be compared for correctness"
- **Carried from earlier rounds** (2026-11-12):
  - the goal: "a simulation capable of realtime (or slightly faster) simulation on a consumer card, so a 24x7 sim could run on a local box here for long run tests";
  - the precision: "Id also prefer to continue to utilize the higher precisions, simply to be a usecase for cft-fp256 as well";
  - the route: "*Yes if possible utilize cft programs, as well as generating certificates when able";
  - certificates: "*Certificate support can be built for but not implemented in order to still have gpu capability at the moment".

## What DEBRIS-E is for

The lead recommended, and Logan accepted, a hybrid:
- **The product:** our own propagator, MIT, which can be tweaked.
- **The referees:** existing tools and published authorities.
- **The judge of any accuracy tweak:** observations, in a later round's 24/7 loop.

DEBRIS-E builds the propagator's first milestone, M1: a reference propagator on this CPU, in portable C. One force-model source is compiled for six **number kinds**:

| kind | arithmetic | role |
|---|---|---|
| native32 | C `float` | the ladder's bottom rung, compared with cft32 (decision 2) |
| native64 | C `double` | the fast path, compared with cft64 |
| cft32 | libcft binary32, software backend | the ladder's bottom rung |
| cft64 | libcft binary64 | held bit for bit against native64 |
| cft128 | libcft binary128 | the ruler on binary64 |
| cft256 | libcft binary256 | the ruler on binary128 |

So the library uses the whole range of formats libcft offers.

Logan's correctness comparison is the round's centre. At binary64 and binary32 the native and cft kinds run the same operations in the same order. Basic operations are correctly rounded both in IEEE hardware and in libcft: addition, multiplication, fused multiply-add, division and square root. So the two kinds must agree **bit for bit** wherever only those operations are involved.

The comparison has already found one fault. On this host, the C library's own `fma` is not correctly rounded:
- Without the FMA instruction, gcc 16.1.0 from mingw64 compiles `fma` to a call into the library's routine, which was wrong on 6,559 of 20,000 hard cases (MEASURED by the lead; plan-verifier-E found 86,912 of 300,000).
- With `-mfma`, the same source compiles to the hardware instruction, which was right on all 20,000.

So the native kinds are built with the FMA instruction (decision 3). E1 keeps the library routine's error on record as a finding. Wherever native code calls the C library's transcendentals (exp, sin, cos, asin, acos), which are not correctly rounded in general, the difference is measured. A control build that routes those calls to libcft's correctly rounded functions must then agree bit for bit again. The referees then hold the physics to outside authorities:
- Lasser et al.'s gravity and third-body benchmark;
- JPL's `testpo.421`;
- Orekit's force models;
- REBOUND's IAS15, as an integrator.

| part | what it settles | the evidence it rests on |
|---|---|---|
| **B1. The number layer** | one source, six kinds, lane-batched; constants correctly rounded into each kind | the build, and gate E1's constant check |
| **B2. The force model** | gravity to degree 180, Sun and Moon, drag, radiation pressure, over the number layer | gates E1, E4, E5 and E6 |
| **B3. The integrator** | rk4 over the number layer, in segments designed for certificates | gates E2, E3, E7 and E8 |
| **E1 to E9. The gates** | native against cft bit for bit; the precision ladder; the referees; reproducibility; cost | each gate's criteria, written before its data |

What this round does not do: tweak anything for accuracy. M1 is the reference that later tweaks are measured against.

## What DEBRIS-E starts from (labels as in DEBRIS-C)

### This project's own code (MIT)

- **DEBRIS-B's kernels,** `studies\debris-b\q2\q2bench.c` and its include files:
  - gravity by the Cunningham V, W recursion (Montenbruck & Gill 2000, §3.2);
  - a DE-like Chebyshev reader;
  - the interpolated frame;
  - an exponential atmosphere;
  - radiation pressure with a conical shadow.
- **DEBRIS-C's normalised gravity kernel,** `studies\debris-c\m1a\m1a_grav.c`, derived from DEBRIS-B's.
  - It reproduced Lasser et al.'s accelerations, degrees 2 to 180, to 2.278e-15 m/s² at most, against a tolerance of 1e-11 (MEASURED, DEBRIS-C M1a).
  - Its control, the field truncated at degree 173, showed 9.772e-10 m/s², 98 times the tolerance (MEASURED).
- **DEBRIS-C's reader gate** (`studies\debris-c\m1b\`), written in Python (`m1b_check.py`): a Chebyshev reader within 1.4e-14 AU of `testpo.421` on bodies. It missed its 1e-13 tolerance at 13 points, each a libration angle, by 1 to 3 ulps of angles up to 4,107 rad (MEASURED, DEBRIS-C M1b).
- **What does not exist yet,** so the build writes it (plan-verifier-E, READ):
  - a DE421 binary reader in C;
  - a `.gfc` loader that keeps each coefficient's decimal string. `m1a_grav.c` converts with `strtod`.
  - DEBRIS-B's Chebyshev kernel runs on synthetic coefficients, and includes `windows.h` and `quadmath`.
- **DEBRIS-C's finding on FMA:** the C kernel's bits depend on fused multiply-adds. A `-march=native -ffp-contract=fast` build holds 29 FMA instructions against none at `-O2`. 2,547 of its 2,880 outputs differ from the `-O2` build's, by at most 5.2e-17 m/s², and each build reproduces itself (MEASURED, DEBRIS-C M3).
- **DEBRIS-D's drivers,** `studies\debris-d\tools\opbench.c` and `seqrun.c`, call libcft's host operations on the software backend: `cft_open(NULL, ...)`, `cft_run` with `CFT_ADD`, `CFT_MUL` and `CFT_FMA`, `cft_div`, `cft_sqrt`, `cft_exp`, `cft_sin` and `cft_cos` (READ).
- **DEBRIS-D's one-object propagator,** `studies\debris-d\q4\q4prop.c`: one LEO object for one day, under EIGEN-6C4 to degree N with exponential drag, stepped by rk4.

### What is measured

- **libcft on this CPU** (MEASURED, DEBRIS-D Q3, reproduced by verifier-D within 10%), at binary64, binary128 and binary256:
  - an FMA costs 195, 235 and 313 ns;
  - a divide, 3.6, 5.6 and 9.2 µs;
  - a host `cft_exp`, 0.14, 0.33 and 1.12 ms.
- **rk4** (MEASURED, DEBRIS-D Q4, reproduced). Over one LEO object-day, under EIGEN-6C4 to degree 20 with drag:
  - its error is 2,310, 83, 3.3 and 0.15 m at steps of 60, 30, 15 and 7.5 s, against a Romberg reference good to 2e-8 m;
  - at binary64 its own rounding is 1.2e-6 to 1.3e-5 m a day;
  - IAS15 at ε = 1e-9 makes 4.0e-7 m.
- **The precision question** (COMPUTED, DEBRIS-B): binary64 "is not the limit in any regime tabulated here", and binary128 is "enough for every use found".
- **The LEO catalogue at degree 20 on one CPU core, at binary64** (COMPUTED, DEBRIS-C): about 1% of a core with an exponential atmosphere, 5% with NRLMSISE00 and 17 to 18% with JB2008.

### libcft's host API, at cft-fp256's commit 0aa997a3

The header is `host/include/cft.h` (READ, through the archive):
- `cft_run` (line 1195) applies `CFT_ADD`, `CFT_MUL` and `CFT_FMA` to arrays, at a format and rounding;
- `cft_div` (1382) and `cft_sqrt` (1392);
- `cft_convert` (1460) between formats;
- `cft_exp` (1645) and `cft_sin` (2198), among the 39 correctly rounded functions;
- `cft_from_decimal_char` (1906) and `cft_to_decimal_char` (1933), and `cft_from_hex_char` (1943) and `cft_to_hex_char` (1959);
- `cft_asin` (1765) and `cft_acos` (1768);
- the opcode `CFT_SELECT` (353): "d = (c != 0) ? a : b; moves NaNs intact".

No earlier study called `cft_asin`, `cft_acos`, `CFT_SELECT`, the compare operations or `cft_from_decimal_char`, and DEBRIS-D did not price binary32 (plan-verifier-E, READ).

**NaNs differ.** A native invalid operation, such as `sqrtf(-1)` or `0/0`, gives a negative quiet NaN, `0xffc00000` (plan-verifier-E, MEASURED). libcft emits one canonical quiet NaN, with its sign bit clear (`host/src/softfloat.c`, `sf_qnan`, from line 50, READ). IEEE 754 leaves a generated NaN's sign and payload open, so the gates compare NaNs by class (rule in E1).

The archive is `cft-debris-ledger\tools\cft-fp256-0aa997a3.tar`, SHA-256 `e01003cc0b984864b065ce3395f56fa189451fcb0cd98cce5b11b3c17a9c29b8`. Every one of its 2,643 files matches the commit (`lead.md`, 2026-11-12 20:38).
- DEBRIS-D built libcft from it on this host with the Windows line.
- Such a build names its build id `unknown`; the archive's SHA-256 is the record.

### The referees, already downloaded

All of these are in `cft-debris-downloads\`, with their SHA-256 in `lead.md`:
- Lasser et al.'s benchmark files, and their `EIGEN6-C4.gfc`;
- DE421, with `header.421` and `testpo.421`;
- Orekit 13.1.9 and Hipparchus 4.0.3.

REBOUND 5.1.1 is installed in this host's Python.
- A Python `ctypes` callback can reach a C library from REBOUND's additional forces. For drag, `force_is_velocity_dependent` must be set (plan-verifier-E, READ).
- Orekit 13.1.9's jar holds `HolmesFeatherstoneAttractionModel`, `ICGEMFormatReader`, `DragForce`, `SimpleExponentialAtmosphere`, `NRLMSISE00` and `ConicallyShadowedLightFluxModel`. Its class files are version 52, which Java 8 loads (plan-verifier-E, READ from the jar's class list).

**The licences:**
- libcft and Orekit are Apache-2.0, and are used as built or called, never copied in.
- REBOUND is GPL-3.0. It is a referee called from Python, never a source.
- NRLMSISE-00's and JB2008's terms are unresolved for an MIT repository (DEBRIS-B and DEBRIS-D READ). So they appear only as referees through Orekit.

## The shape

| agent | job | model | when |
|---|---|---|---|
| the lead (this session) | <ul><li>Phase 0</li><li>the briefs and the ledger</li><li>escalations and TimeSheet bookings</li><li>filing each final message</li><li>the merge and its narrowing</li><li>the commit</li><li>the round's record</li></ul> | Opus | throughout |
| DEBRIS-E | the build: B1 to B3 and gates E1 to E9, in its brief below | Opus | after Phase 0 |
| verifier-E | disconfirm DEBRIS-E's build and its gates | Sonnet | when DEBRIS-E reports |
| merge-check-E | check any narrowing the lead makes at the merge | Haiku | after verifier-E, if the lead narrows anything |

## Phase 0: the lead, before dispatch

1. **The archive:** the one already in the ledger's `tools\` (decision 7). Its SHA-256 is checked again before dispatch.
2. **Downloads:** none. Every referee file is already in `cft-debris-downloads\`.
3. **TimeSheet:** each agent's time is booked as a `notice`. E9's timings run in a `sensitive` window on `desktop`, booked when DEBRIS-E asks.
4. **Ledger files:** `DEBRIS-E.md` and `verifier-E.md`, with headers only.
5. **Dispatch,** as in "Dispatch" below.

## Dispatch

Each agent's prompt is a dispatch note and its brief, followed verbatim by four sections of this plan: "Dispatch", "The ledger", "Rules every brief carries" and "READY". A script writes the prompt from this file. After dispatch, the prompt is checked against the harness's transcript.

Each agent sends one test escalation as it starts:
- it writes `test escalation from <name>` in its own ledger file;
- it sends the same words to the lead (SendMessage to `main`);
- the lead replies "received" and records the round trip in `lead.md`.

If no test escalation arrives from an agent within ten minutes of its dispatch, the lead reads that agent's ledger file, arms a watch on the ledger directory, and says so in `lead.md`.

## The ledger

The ledger is `C:\Users\logan\source\repos\cft-debris-ledger\`, as in rounds DEBRIS-B to DEBRIS-D.

- **One file per author, append only:** `lead.md` continues; this round adds `DEBRIS-E.md` and `verifier-E.md`, which the lead creates with a header only. Correct an entry by appending beneath it, never by editing it.
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
- **What the lead writes in `lead.md`, every verifier reads.** The lead relays upstream facts there. It never writes a judgement of DEBRIS-E's work there before verifier-E has reported.

## Rules every brief carries

These come from three places: Logan's standing rules (carried from cft-fp256 and cft-rebound, 2026-09 to 2026-11), canonical ParcelRound, and the rulings of rounds DEBRIS-B to DEBRIS-D.

- **Read-only, except your own outputs and scratch.**
  - cft-rebound, cft-fp256 and the TimeSheet are other sessions' live repositories. Read their files; in git, use only `git -C <repo> log` and `git -C <repo> show`. Never write in them, never run `git status` there, and never run a bare `git stash`.
  - In the TimeSheet you may run `timesheet.py check` and `list`, which only read.
  - cft-fp256 is Apache-2.0. Extract and build its archive only in your scratch.
  - In cft-debris, write only where your brief says. Commit nothing: the lead commits after verification.
- **The repository is public and MIT.**
  - Every source file you write carries a header naming cft-debris and the MIT licence.
  - Copy no third-party source into the repository, whether cft-fp256's, REBOUND's, cft-rebound's or Orekit's. libcft is linked from a build outside the repository and is never vendored; its header is reached by an include path.
  - Reading a source to understand an interface is fine; quoting more than a short passage is not.
  - This project's own earlier code (DEBRIS-B's to DEBRIS-D's) is MIT, and may be reused with a note of where it came from.
- **No downloads, installs or package managers.**
  - The approved files are in the downloads folder, with their SHA-256 in `lead.md`. Read them in place, or copy what you need into your scratch.
  - If another file would settle a question, ask the lead for it. Give its name, source URL, size, licence and purpose. Each file needs Logan's approval.
- **Reading the web: HTML pages only.**
  - WebFetch returns a model's summary of a page, not its bytes. A figure or quote taken through it is labelled "READ (via WebFetch)". It supports "consistent with", never "confirmed".
  - WebFetch saves any response that is not HTML to disk. So a URL ending in `.txt`, `.pdf`, `.csv`, `.zip`, `.bin`, `.jar` or `.gfc`, or one in an FTP tree, is a download request, whatever it seems to hold.
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
  - libcft's Windows build line is `make -C host CC=gcc OS=Windows_NT TMP=/tmp TEMP=/tmp <targets>` (cft-fp256's `bindings/wasm/verify_demos.mjs:51-58`). On Windows the targets end in `.exe`.
- **Java:** a Java 8 runtime only, `C:\Program Files\Java\jre-1.8\bin\`, and no `javac`.
  - Run Nashorn scripts as `"C:/Program Files/Java/jre-1.8/bin/java.exe" -cp "<the jars, ;-separated, absolute paths in the downloads folder>" jdk.nashorn.tools.Shell <script.js>`.
  - `jjs -cp` and `CLASSPATH` both fail here.
  - Nashorn here is ES5: use `var` and `function`.
  - Build Orekit's dates without `createJDDate(..., TDB)` round trips, which DEBRIS-C found 11.9 to 14.5 µs off.
- **Python:** `C:\Users\logan\AppData\Local\Programs\Miniconda3\python.exe -I -B`. It has numpy, mpmath and rebound 5.1.1.
- **Processes and files:** kill only processes you started, and only by PID. Delete only what you made, and never through a computed path.
- **Earlier studies' records are read-only.** Copy what you run into your scratch or your own output folder. Before your report, check all five:
  - `sha256sum -c SHA256SUMS` run from `studies\` shows 32 OK;
  - `find studies/debris-a -type f | wc -l` gives 29;
  - `sha256sum -c MANIFEST.sha256` shows 54 OK from `studies\debris-b\`, 136 OK from `studies\debris-c\` and 73 OK from `studies\debris-d\`;
  - there is no `__pycache__` anywhere under `studies\`.
- **Host traps:**
  - **System32 before PATH.** From Python, or anything else that calls CreateProcess, Windows searches System32 before PATH. So a bare `bash` is `C:\Windows\System32\bash.exe`, the WSL launcher, and a bare `timeout` is `TIMEOUT.EXE`; System32 also holds `wsl`, `tar` and `curl`. Start every program from Python by its full path, such as `C:/msys64/usr/bin/bash.exe` and `C:/msys64/mingw64/bin/gcc.exe`, or run it through the Bash tool directly (round DEBRIS-D, `lead.md`, 2026-11-12 21:23).
  - MSYS `.exe` transparency: writing a file `X` beside an existing `X.exe` writes to `X.exe`.
  - Passing a script to bash from Python with `text=True` turns every newline into CR+LF. So does any text-mode write from Python on Windows, `Path.write_text` included. Write bytes, or open with `newline="\n"`, wherever a file's bytes matter. The lead's own edit of this plan hit it in drafting.
  - In the Bash tool, a doubled backslash reaches the shell as one, inside a heredoc too. Write any script that contains backslashes with the Write tool, and write Windows paths in commands with forward slashes.
  - A Bash `cd` into a subfolder can move the session's working directory for every later call. Use absolute paths, or `git -C`.
  - Git Bash's `grep` strips the CR at each line end unless given `-U`. Count CRLF with Python.
  - Never start a process under `pythonw`, or detached.
- **No helper agents.**
- **Your final message is your report.** Its word limit is in your brief. If the harness refuses the write of a document your brief names, your final message is that document followed by the report, and the word limit then applies to the report alone.
- **Before you report**, stop any background work you started. End with what you did not do, and with anything your brief got wrong.

## READY, stated before the first pass

READY applies to DEBRIS-E and to every verifier's verdict. Every load-bearing claim must rest on one of:
- a measurement, with its command and output;
- a fetched source, cited by URL;
- arithmetic from labelled inputs.

Otherwise it is stated as a limit, in terms of the behaviour it concedes. A claim's domain and quantifier are claims, and so is a figure's definition. A number carried over from an earlier study keeps its definition, or it is re-measured.

**From rounds DEBRIS-B to DEBRIS-D:**
- **Every control states its pass and fail criteria before the data, and the code asserts them.** A control that fails as specified is reported as failed, whatever replaces it.
- **Every agreement claim states its tolerance before the data.**
- **Every log names the SHA-256 of the script that wrote it**, and the criterion that script asserted.
  - Keep every version of a script that wrote a log, under a name carrying the first 12 hex digits of its hash.
  - Never overwrite a log: number each run's log.
  - The manifest lists every version.
- **An ESTIMATE names its basis and its range**, and is never added to a MEASURED figure without saying so.
- **A bound over many trials holds only when the trials are independent.** Say what varies from trial to trial (round DEBRIS-D, its marks test).

A verifier may reuse a run instead of re-running it only when all three of these hold:
- someone other than the author of the work made the run;
- its inputs are identical, file hashes included;
- the verifier re-runs from clean whatever it doubts.

Only a wrong answer sends work back: a false claim, a measurement or check that cannot fail, or code that does not build or does not do what its gate says it does. Everything else is a note the lead records, and a sentence that claims too much is narrowed at the merge.
- **Loop cap (Logan, 2026-10-15, carried through the lead's memory):** after three NOT READYs for narrowing reasons, the next pass blocks only on wrong answers.
- **Threat model (Logan, 2026-10-02):** each verifier's brief states one, and findings outside it do not reopen the loop.

## Logan's decisions (each default stands unless changed)

1. **Models:** Opus for DEBRIS-E, Sonnet for verifier-E, Haiku for a merge-check.
2. **Binary32** ("and 32 if needed"):
   - (a) include native32 and cft32, as the ladder's bottom rung. They are held to E1 and E2 and measured in E3 and E9, but not held to E4's or E5's tolerances, which binary32 cannot meet;
   - (b) leave binary32 out.
   - Default: (a), so the library spans every format libcft offers.
3. **Native fused multiply-add** (new in draft 2). On this host the C library's `fma` is not correctly rounded; the hardware instruction is.
   - (a) The native kinds require the FMA instruction, reached through the intrinsics `_mm_fmadd_sd` and `_mm_fmadd_ss` with `-mfma`, on an x86-64 that has FMA3, as this i5-12400F does.
     - A plain `fma()` call is not enough: at `-O0` it still calls the library routine (MEASURED).
     - The build checks that every native object shows `vfmadd` and no call to `fma`, and the program checks the CPU at start.
     - The cft kinds stay portable.
   - (b) The force-model source uses no fused multiply-add at all, so every kind matches without the instruction. That costs some accuracy, and leaves libcft's FMA unused.
   - (c) A correctly rounded software `fma` of our own for the native kinds, slow, and itself to be proven.
   - Default: (a).
4. **The integrator in this round:**
   - (a) rk4 only. It is the integrator cft programs share, so the GPU route can later be replay-checked against it bit for bit. IAS15, written from the published method and never from REBOUND's source, comes in a later round;
   - (b) rk4, and IAS15 from the published method, both now.
   - Default: (a), to keep the round buildable and verifiable. REBOUND's IAS15 still serves as a referee in E7.
5. **The density model we own:**
   - (a) the exponential atmosphere. NRLMSISE00 and JB2008 appear only as referees, called through Orekit, until their licences are settled;
   - (b) also a published simple model, such as Harris-Priester or Jacchia, after a licence check.
   - Default: (a).
6. **The frame:**
   - (a) uniform Earth rotation in this round, stated as a limit. The IERS frame (precession, nutation, polar motion and UT1) comes in a later round, with its data downloads;
   - (b) the IERS frame now, with those downloads approved by name.
   - Default: (a).
7. **libcft:**
   - (a) the archive already in the ledger, cft-fp256 at 0aa997a3, built in DEBRIS-E's scratch, as in DEBRIS-D;
   - (b) a newer pin, cft-fp256's main after G1C's merge, with a new archive made in Phase 0.
   - Default: (a). The CPU arithmetic DEBRIS-E needs is unchanged by G1C, which is the GPU backend's gates (BELIEVED).
8. **Layout:**
   - (a) `src/` for the library, `tests/` for the gates, `studies/debris-e/` for the logs and records, and `studies/DEBRIS-E-build.md` for the build report. libcft is linked from outside the repository;
   - (b) another layout Logan names.
   - Default: (a).
9. **Scope and budgets:**
   - (a) One round:
     - DEBRIS-E gets 6 hours of wall time and 60 CPU-minutes, and messages the lead before any single run expected to pass 5 CPU-minutes. E4's degree-180 runs (up to 15 CPU-minutes) and E9's timings (up to 10) are approved in advance;
     - verifier-E gets 3 hours and 30 CPU-minutes;
     - a merge-check gets 20 minutes.
     - If time runs short, DEBRIS-E cuts in this order: E9, then E6's NRLMSISE00 figure, then E7, then the binary32 rung. E1 to E5, E6's core comparisons and E8 are kept.
     - plan-verifier-E estimates the whole at about 30 to 40 CPU-minutes, E4 being the largest at 9 to 15 (ESTIMATE).
   - (b) Two rounds: B1 to B3 with E1, E2, E3 and E8 first; the referees E4 to E7, and E9, in a second round.
   - Default: (a). For scale, DEBRIS-D used 70 minutes and 16.1 CPU-minutes for a study.
10. **Outputs and the push:** the lead commits the build after verification and the merge. Pushing to the public repository waits for Logan's word.

## Not in this round

- Any accuracy tweak. M1 is the reference that tweaks are later measured against.
- IAS15 of our own (decision 4), the IERS frame (decision 6), and ports of NRLMSISE00 or JB2008 (decision 5).
- The 24/7 loop: element ingestion, SGP4 and the validation statistic. That is a later round.
- The GPU route. It waits for cft-fp256's round 2: index tables and the 2,048-slot depth.
- Writing or auditing a certificate. The runs are designed for certificates, and none is written.
- Any download, any GPU, WSL, card or box, and any account.

---

## Brief: DEBRIS-E

You are build parcel **DEBRIS-E** in cft-debris, a project for space-debris tracking and simulation. Its folder, `C:\Users\logan\source\repos\cft-debris`, is a public git repository under the MIT licence. You build M1, the CPU reference propagator, and the gates that hold it. You commit nothing: the lead commits after verification.

**Budget:** 6 hours of wall time and 60 CPU-minutes. Message the lead before you pass either, and before any single run you expect to pass 5 CPU-minutes. Two pieces of planned work are approved here and need no message: E4's runs at degree 180, up to 15 CPU-minutes in all, and E9's timings, up to 10. Log each of them. Runs at cft128 and cft256 are slow: about 235 and 313 ns an FMA (DEBRIS-D). So hold their trajectories to short arcs, and say how long each is.

**Start here:**
1. This plan, `C:\Users\logan\source\repos\cft-debris\studies\DEBRIS-E-plan.md`: Logan's words, what each part settles, and what the round starts from.
2. This project's own code, which you may reuse with a note of where it came from:
   - `studies\debris-b\q2\q2bench.c` and its include files;
   - `studies\debris-c\m1a\m1a_grav.c`, with the Lasser gate in `studies\debris-c\m1a\`;
   - the reader gate in `studies\debris-c\m1b\`;
   - `studies\debris-d\tools\opbench.c`;
   - `studies\debris-d\q4\q4prop.c`.
3. DEBRIS-C's and DEBRIS-D's studies, for what each kernel and gate measured.
4. `lead.md` in the ledger: the archive's SHA-256, and Phase 0.
5. cft-fp256's `host/include/cft.h` and `docs/HOSTAPI.md`, in the archive: the host API.

**Where it goes:**
- `src/`: the library;
- `tests/`: the gates;
- `studies\debris-e\`: the logs and records, with a `MANIFEST.sha256` over them;
- `studies\DEBRIS-E-build.md`: the build report. It covers what was built, how to build it (exact commands and compiler versions), each gate's criteria and result, and the limits.
- **In your scratch only:** cft-fp256's sources, libcft's build, and anything third-party.
- Every file you write in `src/` and `tests/` carries a header naming cft-debris and the MIT licence.

**B1. The number layer.** One force-model source, compiled once per number kind:
- **The kinds:** native32 (C `float`) and native64 (C `double`); and cft32, cft64, cft128 and cft256, which are libcft's software backend (`cft_open(NULL, ...)`) through its host API.
- **No per-kind copy of any physics code.** Use C11 with a header included once per kind, or C++ templates if you judge them clearer, and say which and why.
- **Lane-batched:** every operation acts on a batch of lanes, one object a lane, as cft programs do. So libcft's per-call cost is paid once a batch, and the native kinds use the same batched calls.
- **Branches on data become selects,** so every lane runs the same operations.
- **Native arithmetic is exact IEEE:**
  - `-ffp-contract=off`, no `-ffast-math`, and explicit `fma` and `fmaf` wherever the source means a fused multiply-add;
  - `-mfma` for the native kinds (decision 3), with every native FMA written through the intrinsics `_mm_fmadd_sd` and `_mm_fmadd_ss`.
    - At `-O0`, a plain `fma()` call still compiles to the library routine. The intrinsics emit the instruction at every level of optimisation (MEASURED by plan-verifier-E and the lead).
    - The build checks every native object: `vfmadd` present, and no call to `fma` or `fmaf`.
    - The program checks at start that the CPU has FMA3;
  - check that `FLT_EVAL_METHOD` is 0.
- **Constants:** every constant enters each kind once, correctly rounded from its exact decimal value. In the cft kinds that is `cft_from_decimal_char`; in the native kinds, the C library's conversion, whose bits E1 holds to libcft's. Record each constant's source.
- **Derived tables,** such as the gravity recursion's coefficients, which are square roots of rational expressions: compute them in each kind, from exact integers, by correctly rounded operations in a fixed order. Never convert them from binary64, or cft128 and cft256 would carry binary64's error. E1 holds native64's tables equal to cft64's, bit for bit.
- **Batches:** size them so that working memory stays under 1 GB at every kind. At degree 180, one lane's V and W tables hold about 16,500 entries each.
- **The reader** chooses each lane's Chebyshev interval on the host, by gathering it. That has no counterpart on the GPU route until index tables arrive (cft-fp256's round 2). The propagation itself keeps one time grid for all lanes.

**B2. The force model,** over the number layer, from this project's kernels. You also write what does not exist yet: a DE421 binary reader in C, and a `.gfc` loader that keeps each coefficient's decimal string.
- **gravity:** the central term and normalised spherical harmonics to degree N ≤ 180, from EIGEN-6C4 (`EIGEN6-C4.gfc` in the downloads), in an Earth-fixed frame;
- **the Sun and Moon** as point masses, from DE421 through a Chebyshev reader;
- **drag** through an exponential atmosphere co-rotating with the Earth (decision 5);
- **radiation pressure** with a conical shadow;
- **the frame:** uniform Earth rotation (decision 6), stated as a limit.

**B3. The integrator:**
- rk4 at fixed steps (decision 4), over the number layer;
- runs cut into segments, with every lane's state kept at every boundary, designed for certificates (none written);
- the time grid shared by all lanes, so the Sun, Moon and frame are evaluated once a stage for the batch.

**The gates,** in `tests/`. For each gate: write its criteria into its script before its data, assert them in code, and give it a negative control that must fail as specified. Each gate's degree and size are fixed below, so that the budget holds; going past them comes under the stop rule.

- **The NaN rule,** for every bit-for-bit comparison: non-NaN results agree bit for bit; NaN results agree as NaNs. IEEE 754 leaves a generated NaN's sign and payload open, and native and libcft differ there. Choose lanes that avoid invalid operations, and report any lane that yields a NaN.
- **E1. Native against cft, kernel by kernel,** at binary64 and binary32, on 10,000 random lanes per kernel. Gravity is at degree 20, with degree 2 beside it for a hand check, and one batch of 64 lanes at degree 180, so that bit-identity is shown at the degree E4 uses. State what varies between lanes.
  - **Constants and derived tables:** every constant's native bits equal libcft's correctly rounded conversion, and every derived table matches across kinds.
  - **Kernels using only addition, multiplication, FMA, division and square root** must agree bit for bit, native against cft. These are the gravity recursion, the Chebyshev reader, and the shadow geometry before its inverse trigonometry.
  - **Kernels that call the C library's transcendentals** (exp, sin, cos, asin, acos): report each difference in ulps. Then build a control in which the native kinds route those calls to libcft's correctly rounded host functions. It must agree bit for bit.
  - **The library `fma`, on record:** the same 20,000 hard cases as the lead's check, on the library routine (a build without `-mfma`) and on the instruction, each held to libcft's `CFT_FMA`. This is a finding, not a gate.
  - **Negative control:** one operation reordered in the native build alone must break bit-identity, and the gate must say where.
- **E2. Native against cft, whole runs.** rk4 trajectories of 8 lanes over one orbit, at degree 20, with a 60 s step, at binary64 and binary32:
  - in the control build, bit for bit at every step. This is the gate;
  - with the C library's transcendentals, how the difference grows. This is a measurement, with no pass condition;
  - **negative control:** one ulp planted in one lane's starting state must break bit-identity in that lane alone, from the first step.
- **E3. The precision ladder.** The same runs at cft32, cft64, cft128 and cft256.
  - Report each kind's difference from cft256 at every segment boundary.
  - State beforehand a bound for cft128 against cft256, derived from binary128's unit roundoff and the operation count, and hold it.
  - **Negative control:** the cft128 run, with one intermediate of the force model rounded to binary64, must break that bound.
  - Report binary64's growth against cft128 beside DEBRIS-D's 1.2e-6 to 1.3e-5 m a day, keeping the definitions apart.
- **E4. Lasser et al.** Gravity, degrees 2 to 180, and the Sun and Moon, against the benchmark's accelerations within DEBRIS-C's 1e-11 m/s².
  - **At native64 and cft64:** every epoch.
  - **At cft128 and cft256:** every tenth epoch.
  - Report cft32 only as a figure, at every tenth epoch.
  - DEBRIS-C's planted control, the field truncated at degree 173, must fail.
- **E5. JPL's `testpo.421`.** The reader's Sun, Moon and Earth-Moon barycentre within 1e-13 AU, at cft64, cft128 and cft256, at every point inside DE421's coverage.
  - Librations are left out: the propagator does not use them, and DEBRIS-C's failures were there.
  - testpo prints 17 significant digits, so E5 tests the reader, not the formats' precision.
  - A planted coefficient error must fail.
- **E6. Orekit, force by force.** At 1,000 sampled LEO states, compare ours at cft64 and native64 with Orekit, within tolerances stated before the data, and report each tolerance's basis.
  - **Every input is matched,** and the gate's log lists each one:
    - Orekit's body frame is a uniform rotation at our ω, built as a frame of our own in Orekit, so that drag sees the same atmosphere velocity;
    - the Sun's position comes from the same DE421 file;
    - the solar flux constant and the Sun's and Earth's radii are set equal to ours.
  - **Each tolerance lies below the planted change it is to catch.** The drag tolerance is under 1% of the drag acceleration, so that the control below can fail.
  - **Drag,** with the inputs matched: our atmosphere configured with a single band, against Orekit's `SimpleExponentialAtmosphere` on a spherical body (flattening 0). Our own atmosphere is a 28-band table on spherical altitude (`q2bench.c`); Orekit's simple model has one band on geodetic height.
  - **Radiation pressure,** against Orekit's `ConicallyShadowedLightFluxModel`: in full sunlight and in full umbra within the tolerance. Penumbra is reported as a figure, unless the two shadow geometries are shown to be the same.
  - **Gravity:** Orekit's Holmes-Featherstone at degree 20.
  - **Beside these, as a figure only:** the same states with Orekit's NRLMSISE00, which our model does not include (decision 5).
  - **Negative control:** one force parameter planted 1% off, such as the drag coefficient, must break its tolerance.
- **E7. REBOUND as an integrator referee.** Our force model at native64, at degree 20, called from REBOUND's IAS15 at ε = 1e-9 through a `ctypes` callback, over one object-day.
  - Set `force_is_velocity_dependent`, since drag depends on velocity.
  - Compare against our rk4 at native64, at a step chosen beforehand. Hold the difference to a tolerance stated before the data; DEBRIS-D's rk4 table is a guide.
  - **Negative control:** J2 planted 1e-3 off, relatively (0.1%), on one side, must break that tolerance.
  - REBOUND stays outside the repository; only your harness script is ours.
- **E8. Reproducibility.** Each kind's E2 run reproduces bit for bit across two runs, and across `-O0` and `-O2`, with contraction off and the FMA instruction on. A build with contraction on (`-ffp-contract=fast`, with `-mfma`) must differ, as DEBRIS-C found.
- **E9. Cost,** in a `sensitive` window the lead books. Run nothing else during the window. For each kind, give the time per force evaluation at degree 20, and per object-day with rk4 at 15 s, beside DEBRIS-D's Q3 prices.

**Instruments on this host:**
- C, with gcc 16.1.0 from mingw64;
- Python with numpy, mpmath and rebound 5.1.1;
- Java 8, with Orekit 13.1.9 and Hipparchus 4.0.3 from the downloads;
- the archive of cft-fp256;
- the web, HTML pages only.

**Do not:**
- write outside `src/`, `tests/`, `studies\debris-e\`, `studies\DEBRIS-E-build.md` and your scratch;
- run anything on a GPU;
- message any session but the lead;
- weaken a gate's criterion, or a claim's label, to make it pass.

**Report:** your final message, under 1,200 words:
- what was built;
- each gate's result, with its most load-bearing evidence and its label;
- every control that failed, and what you did next;
- the native-against-cft findings, in ulps where they differ;
- anything you could not settle;
- what you did not do;
- anything this brief got wrong.

---

## Brief: verifier-E (completed when DEBRIS-E reports)

You are **verifier-E**: a verifier, not an author. Try to disconfirm DEBRIS-E's build and its gates, and report. Fix nothing. Budget: 3 hours of wall time and 30 CPU-minutes, counted by cycles. The lead books your time as a `notice`, and books any timing window you ask for. Re-run each gate at its stated size or smaller, and say which.

**Threat model.**
- **In scope:**
  - code that does not build from clean with the build report's commands;
  - a gate that does not test what it says, or could not fail;
  - a criterion set after its data;
  - a bit-identity claim that does not hold on inputs the gate did not try;
  - a referee comparison whose inputs were not matched;
  - a claim whose domain or quantifier reaches past its evidence;
  - third-party source in the repository.
- **Out of scope:**
  - the choice of route, which is Logan's;
  - the physics of the models themselves, beyond whether the code computes what the build report says it does.

The attack list is finished from DEBRIS-E's own content, and starts with:
1. Build libcft from the archive and the library from clean, in your scratch, with the build report's commands.
2. Re-run E1 and E2 with lanes of your own choosing, and with E1's negative control.
3. Re-run E4 and E5, and their planted controls.
4. Re-run E3 and E8.
5. Re-run E6 and E7 at least once each.
6. Hold the build report against the gates' logs, and every header and file against the licence rules.
7. Check criteria before data by the logs' script hashes, with a negative control.
8. Anything else.

**Report:** your final message, under 1,200 words.
- For each item: the commands you ran, what you observed, and a verdict (confirmed, defect, or not determined).
- Every defect needs a concrete failure scenario. "Found nothing" is an acceptable answer.
- End with what you did not do, and anything this brief got wrong.

---

## What changed from draft 1 (plan-verifier-E's findings, answered)

plan-verifier-E's report is filed verbatim as `cft-debris-ledger\filed\DEBRIS-E-plan-verifier-E-report.md`. The lead re-ran blocker 1 itself before answering it (`lead.md`, 05:05).

| plan-verifier-E found | draft 2 |
|---|---|
| **Blocker 1.** The C library's `fma` on this host is not correctly rounded: 86,912 wrong of 300,000. With `-mfma` it is right. So bit-identity could not hold as written | Confirmed by the lead: 6,559 wrong of 20,000 without `-mfma`, 0 with it. Decision 3 (new) makes the native kinds use the instruction, checked at build and at start. E1 keeps the library routine's error on record as a finding |
| **Blocker 2.** No degree was pinned for E1, E2, E3 or E8. At degree 180 the CPU budget and memory fail | Each gate's degree and size are fixed: degree 20 for E1, E2, E3, E7, E8 and E9; degree 180 for E4, at every epoch for the binary64 kinds and every tenth for the wide ones. Batches are held under 1 GB |
| NaN bits differ: native gives a negative quiet NaN, and libcft a positive one | The NaN rule: NaNs agree by class, the lanes avoid invalid operations, and any NaN lane is reported |
| E8's contraction control could not fail without the FMA instruction | With `-mfma` under decision 3, a contracted build can and must differ |
| E6's drag inputs were not matched | One band against Orekit's simple model on a spherical body; radiation pressure held only in full sunlight and full umbra |
| The premises overstated our code: DEBRIS-C's reader gate is Python, DEBRIS-B's Chebyshev kernel is synthetic, and no `.gfc` loader keeps decimal strings | "What DEBRIS-E starts from" says so, and B2 asks for the reader and the loader |
| How derived tables are built per kind was undefined | B1 computes them in each kind from exact integers, never from binary64, and E1 checks them |
| The shared time grid conflicts with the reader's per-lane epochs | B1: the reader gathers each lane's interval on the host, with no GPU counterpart until index tables |
| E2, E3, E6 and E7 had no controls, and E2's libm case no pass condition | Each now has a planted control. E2's libm case is a measurement, and its gate is the control build |
| verifier-E's budget was too small for its list | 3 hours and 30 CPU-minutes, with re-runs at stated sizes or smaller |
| Decisions were missing, and decision 8 had no alternative | Decision 3, native FMA, is new; decision 9 now offers two rounds instead of one, with a cut order |
| **Notes:** E5 tests the reader, not precision; asin, acos and `CFT_SELECT` exist but are unexercised; Orekit's classes are present; the TimeSheet window; the cut order | Each is answered in place: E5's text, "What DEBRIS-E starts from", E9's "run nothing else", and decision 9 |

## What changed from draft 2 (plan-verifier-E's re-check, answered)

The re-check is filed verbatim as `cft-debris-ledger\filed\DEBRIS-E-plan-verifier-E-recheck-report.md`. The lead re-ran its blocker before answering it (`lead.md`, 05:11).

| the re-check found | draft 3 |
|---|---|
| **Blocker.** At `-O0`, `-mfma` still leaves `fma()` a call to the library routine. B1's build check fails there, and E8's `-O0` leg would run the faulty routine | Confirmed by the lead. Every native FMA goes through the intrinsics `_mm_fmadd_sd` and `_mm_fmadd_ss`, which emit the instruction at `-O0` and `-O2` alike. The build checks every native object |
| E6 left the frame, the solar flux and the Sun's position unmatched | Orekit's body frame is a uniform rotation at our ω; the Sun comes from the same DE421; the flux constant and radii are set equal; the log lists each input |
| E6's and E7's controls were ill-defined | Each tolerance lies below the change it is to catch. J2's plant is 1e-3 relative |
| Bit-identity was shown only at degree 20 | E1 adds a batch of 64 lanes at degree 180 |
| E4 alone would pass the 5-minute message rule | E4's degree-180 runs (up to 15 CPU-minutes) and E9's timings (up to 10) are approved in advance, and logged |
| The cut order left E6 unplaced | E6's core comparisons are kept; its NRLMSISE00 figure is the second cut |

## What earlier rounds taught, applied here

| lesson | here |
|---|---|
| Criteria set after the data, and a redefined control reported as passing | Criteria before the data, asserted in code, and each script version kept under its hash (READY) |
| A bound over trials that were not independent (DEBRIS-D's marks) | READY: say what varies between trials; E1 states it |
| A bare `bash` from Python reached WSL (DEBRIS-D) | The Rules' first host trap |
| A study's stop rule never met its own first test (DEBRIS-D's plan) | The budget's stop rule is on any single run, with short arcs at the wide formats |
| A figure taken from an interim message instead of the report (DEBRIS-D's merge) | The lead quotes only filed reports at the merge |
| The C kernel's bits depend on FMA contraction (DEBRIS-C) | B1 turns contraction off, and E8 holds a contracted build to differ |
| Orekit's dates built with `createJDDate(..., TDB)` (DEBRIS-C) | The Rules' Java line |

## The lead's slips so far

Rounds DEBRIS-B's to DEBRIS-D's are in their records. In drafting DEBRIS-E:
- **Draft 1 called the native `fma` correctly rounded** without trying it on this toolchain. That is exactly what the round's gate exists to test, and plan-verifier-E found it false.
- **Draft 1 pinned no degree for most gates,** so the budget it stated could not hold.
- **Draft 1 overstated our existing code:** a Python reader gate, a synthetic Chebyshev kernel, and no decimal-keeping `.gfc` loader.
- **Draft 1 left out three rules and four controls:** a rule for derived tables, a NaN rule, and controls for E2, E3, E6 and E7.
- **The lead's line-targeted edit of draft 2, made through Python's `write_text`, turned the plan's line endings to CRLF.** It was caught by a byte check and reverted to LF. The same write had earlier turned this session's memory index to CRLF, now reverted too. The trap is now in the Rules.
- **Draft 2 answered blocker 1 with `-mfma` alone,** without trying `-O0`. The re-check found it insufficient there, and the lead confirmed that.
