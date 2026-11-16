# DEBRIS-F: M1 meets real data: the real Earth, open orbit data, and a first hindcast (plan of record, draft 3)

Drafted 2026-11-16 by cft-debris's lead for Logan's approval.
- This is a **build round**. It takes M1, the CPU reference propagator built in round DEBRIS-E, from a model's Earth to the real one. It then compares M1 with the open data that Logan's 24/7 loop is to check itself against.
- **Draft 1** passed the lead's checker (`check_plan_f.py`, log 002: 118 checks, 0 failed; its log 001 failed two, on figures the lead had carried from memory).
- **plan-verifier-F** (Sonnet) then found two blockers, nine defects and notes. Its report is filed verbatim in the ledger's `filed\`. Draft 2 answers each finding in "What changed from draft 1", and the lead checked both blockers before answering.
- **plan-verifier-F's scoped re-check of draft 2** found no blocker, two defects and notes, also filed. Draft 3 answers them in "What changed from draft 2". Draft 3 has had the lead's check only.
- Nothing has been dispatched, and nothing has been downloaded.

## The question, in Logan's words

- **This round** (2026-11-16): "Good morning, its Monday morning, so time to begin work again, whats the plan for today?" The lead recommended DEBRIS-F as the real-data round, before any GPU port, and Logan answered: "Yes, draft it".
- **The goal** (2026-11-12): "a simulation capable of realtime (or slightly faster) simulation on a consumer card, so a 24x7 sim could run on a local box here for long run tests, validating itself with the open datasets update intervals, scaling tracked objects as the main scaling parameter presumably. High performance cards like the MI300X could then be used for higher density or faster/concurrent runs."
- **The route** (2026-11-13): "What route would you recommend? Considering building a custom solution simply so the existing tools can be utilized as reference models, while ours can be tweaked as needed to improve the accuracy of the simulation"
- **Carried from earlier rounds:**
  - the kinds (2026-11-13): "utilize native and cft for binary64 (and 32 if needed) so the library utilizes the entire precision range offered by cft, and the results can be compared for correctness";
  - the precision (2026-11-12): "Id also prefer to continue to utilize the higher precisions, simply to be a usecase for cft-fp256 as well";
  - the route through cft programs (2026-11-12): "*Yes if possible utilize cft programs, as well as generating certificates when able";
  - certificates (2026-11-12): "*Certificate support can be built for but not implemented in order to still have gpu capability at the moment".

## What DEBRIS-F is for

M1 matches its referees, but it cannot yet be compared with the real sky. DEBRIS-E's build report states both reasons as limits (§7):
- **"The frame is a uniform rotation"**: no precession, nutation, polar motion or UT1.
- **"The atmosphere is exponential"**: at E6's 1,000 states, NRLMSISE00 differed from the one-band exponential density by a factor of 0.45 to 6.8, median 1.06 (MEASURED, DEBRIS-E E6).

Logan's goal has the simulation "validating itself with the open datasets update intervals". DEBRIS-F takes the first step there, on the CPU. It does not wait on cft-fp256, and any validation needs the real Earth and real data, whatever hardware runs it.

| part | what it settles | the evidence it rests on |
|---|---|---|
| **B1. Time scales** | UTC, TAI, TT, TDB and UT1, from published tables, onto M1's time grid | gate F2 against Orekit |
| **B2. The Earth's orientation** | the IERS 2010 frame (CIO-based IAU 2006/2000A, with IERS's Earth orientation data), as a node table every kind interpolates | gates F1, F3 and F4 |
| **B3. Open orbit data** | CelesTrak's GP data in CSV, decoded by SGP4 into GCRF positions | gate F5 |
| **B4. The fit** | M1's state, and its drag parameter where drag matters, fitted to those positions | gate F5 |
| **F6. The first hindcast** | how far M1, fitted to one GP update, lands from the next update, beside SGP4's own prediction | a measurement, with its statistics fixed before the data |
| **F7 to F9** | the precision ladder on real objects, reproducibility, and cost | as in DEBRIS-E |

What this round does not do: build our own NRLMSISE-00, run the 24/7 loop itself, use precise orbits as truth, or touch a GPU ("Not in this round").

## What DEBRIS-F starts from (labels as in DEBRIS-C)

### M1, round DEBRIS-E's build (MIT, in `src\` and `tests\`, commit 183c7049)

- **Time:** `src\m1.h` line 97, `double jd_epoch; /* TDB JED of t = 0, a multiple of 1/2 day */` (READ). Step j's time is (step0 + j)·h, on the host, exactly (`DEBRIS-E-build.md` §2, B3, READ).
- **The frame:** `src\m1_physics.h` from line 596, "theta = fma(omega, t, theta0); cos and sin of it" (READ). Drag's co-rotation uses the same ω, at lines 661 and 662 (READ).
- **One time grid for all lanes,** so the Sun, the Moon and the frame are evaluated once a stage for the batch (DEBRIS-E's plan, B3, READ).
- **Measured in DEBRIS-E** (reproduced by verifier-E, after the merge's narrowing):
  - native equals cft, bit for bit, at binary64 and binary32, wherever only addition, multiplication, FMA, division and square root are involved;
  - restarted segments equal the continuous run at native64, cft64 and cft128;
  - over one orbit, cft64 reaches 3.6e-6 m from cft256;
  - one core carries about 1.7 million objects in real time at native64 with the C library's functions, 1,570 at cft64, 990 at cft128 and 390 at cft256, at degree 20 with rk4 at 15 s (COMPUTED from MEASURED single runs, in window B0030);
  - the C library's `sin`, `cos`, `asin` and `acos` are not correctly rounded on verifier-E's 20,000 arguments (MEASURED by verifier-E).

### Measured in earlier rounds

- **DEBRIS-C:** NRLMSISE00 costs 7.3 to 7.5 µs and JB2008 29.9 to 31.6 µs a call, through Orekit (MEASURED). Orekit's dates built with `createJDDate(..., TDB)` round-trip 11.9 to 14.5 µs off (MEASURED).
- **DEBRIS-D's prices** for libcft's host functions at binary64, binary128 and binary256 (MEASURED, reproduced by verifier-D within 10%):
  - an FMA, 195, 235 and 313 ns;
  - `sin`, 0.23, 0.55 and 1.89 ms;
  - `cos`, 0.22, 0.63 and 1.93 ms.

### The tools on this host (MEASURED by the lead, 2026-11-16)

- **Python** (Miniconda3) has numpy 2.2.6, mpmath 1.3.0 and rebound 5.1.1. It has no pyerfa, astropy, sgp4, skyfield or scipy.
- **Orekit 13.1.9,** already downloaded, holds:
  - `TLEPropagator` and `TLE` (SGP4), and CCSDS `Omm`;
  - `NRLMSISE00`, `JB2008` and `CssiSpaceWeatherData`;
  - `BatchLSEstimator`;
  - frame getters `getGCRF`, `getCIRF`, `getTIRF`, `getITRF` and `getTEME`.
- **Orekit's file-name patterns,** printed through Nashorn:
  - Earth orientation data: `^finals2000A\.[^.]*$`;
  - space weather: `^S(?:pace)?W(?:eather)?-(?:All)?.*\.txt$`.
- **Orekit's jar carries its own copies of the IERS 2010 tables,** among them `tab5.2a.txt`, `tab5.2b.txt` and `tab5.2d.txt`, under `assets/org/orekit/IERS-conventions/2010/` (READ, the jar's list). M1 reads the IERS's own copies instead (Phase 0), so a table that one side transcribed wrongly cannot hide behind the other.
- **The series' size** (MEASURED from Orekit's copies by plan-verifier-F, and again by the lead): 1,600 terms for X, 1,275 for Y and 66 for s + XY/2, 2,941 in all. Each term multiplies at most 6 of the 14 fundamental arguments, by integers of at most 21 (MEASURED by the lead).
- **plan-verifier-F's probes,** through Nashorn (MEASURED):
  - Orekit's `TLE` constructor accepts a 6-digit satellite number (100123), and `TLEPropagator.selectExtrapolator` returns an SGP4 propagator. The constructor takes the radian and radian-per-second units that its Javadoc gives;
  - a USNO-format `tai-utc.dat` loads through a `DirectoryCrawler`, giving TAI−UTC = 37 s in 2026;
  - Orekit's `TDBScale` is a short series. It differs by about 1 µs from the two-term formula 0.001657 sin g + 0.000014 sin 2g, over eight dates of 2026;
  - **Orekit fails silently without Earth orientation data.** With only `tai-utc.dat` in the crawled directory, `getITRF(IERS_2010, true)` and `getTEME()` still return frames: zero EOP, a rotation rate of 7.29212e-5 rad/s about z, and no polar motion or UT1.
- **Orekit's online Javadoc is behind bot protection.** plan-verifier-F's fetch was refused, and the lead's browser met a challenge page, which it did not try to pass. So Orekit's signatures are read by reflection in Nashorn (`getMethods`, `getConstructors`), never online.

### The data sources

Each was READ on 2026-11-16 through the built-in browser, which returns the page's own text, not a model's summary.

CelesTrak's pages are paraphrased here, not quoted.
- **CelesTrak's GP data.**
  - The query is `https://celestrak.org/NORAD/elements/gp.php?{QUERY}=VALUE[&FORMAT=VALUE]`, with `GROUP=` among the queries. CSV has been the default format since 2026-05-09.
  - The 5-digit catalogue numbers ran out on 2026-07-11. Objects catalogued since then have 6-digit numbers, which the TLE format cannot carry, so their GP data come only in the other formats. This round reads CSV, never TLE.
  - The groups named here are `stations`, `fengyun-1c-debris`, `iridium-33-debris` and `cosmos-2251-debris`, each linked as `gp.php?GROUP=<group>&FORMAT=csv` from CelesTrak's "Current GP Element Sets" page.
- **CelesTrak's usage policy,** dated 2026-11-16:
  - GP data are updated every 2 hours, and each update is to be downloaded at most once;
  - CSV is asked for, being about a third of JSON's size, and compressed transfer is asked for too;
  - automated clients are to stop at the first response that is not HTTP 200, and report it to a person;
  - after a 500 or 503 response, all requests are to stop for at least 15 minutes.
- **CelesTrak's space weather:** `SW-Last5Years.txt`, 313,862 bytes, in the legacy format, which Orekit's pattern accepts. It is updated every 3 hours, and the policy asks for the 5-year file rather than the full history.
- **The IERS Rapid Service/Prediction Center (USNO),** under "Distribution Statement A. Approved for public release: distribution unlimited":
  - `finals2000A.daily`: "Polar motion, UT1-UTC, and length of day values for last 90 days with dX & dY using IAU2000A Nutation/Precession Theory (with 90 days of predictions)";
  - its format note, `readme.finals2000A`, and `checksums.sha512`;
  - `tai-utc.dat`, the table of leap seconds;
  - daily files are "scheduled for release daily between 17:30 and 18:00 UTC";
  - "NO leap second will be introduced at the end of December 2026. The last leap second was positive and WAS introduced in UTC at the end of December 2016."
- **The IERS Conventions Centre,** chapter 5 of the IERS Conventions (2010): `icc5.pdf` (410K), and the series tables `tab5.2a.txt` (167K), `tab5.2b.txt` (134K) and `tab5.2d.txt` (8.5K).
- **USNO Circular 179** (Kaplan, 2005), on the IAU's resolutions on reference systems, time scales and Earth rotation models: a free PDF of 1.6M, `https://aa.usno.navy.mil/downloads/Circular_179.pdf`. It is the named source for B1's TDB−TT formula.
- **ESA's STEP site** lists Sentinel-1 precise orbits (`auxdata/orbits/Sentinel-1/POEORB/`, folders S1A, S1C and S1D) in a public index. That is for a later round ("Not in this round").

### libcft

- **The pin stays at 0aa997a3:** the archive `cft-debris-ledger\tools\cft-fp256-0aa997a3.tar`, SHA-256 `e01003cc0b984864b065ce3395f56fa189451fcb0cd98cce5b11b3c17a9c29b8`.
- **cft-fp256's main** has 14 commits since the pin (READ, `git log`): the GPU backend's gates (G1C), study GPU-F (WebGPU), roadmap notes, and Logan's answers on the GPU studies. That none of them changes the host arithmetic M1 uses is BELIEVED, from their subjects.

### The licences

- **CelesTrak's data** and the downloads stay outside the repository.
- **The IERS's tables** are read at run time from the downloads, as EIGEN-6C4 is, and never copied into the repository.
- **Orekit** stays Apache-2.0, called and never copied.
- **USNO's files** are released for public distribution, but they too stay in the downloads.

## The frame's design, and why

The IAU 2006/2000A series hold 2,941 terms (MEASURED, above).
- **The naive cost:** if every term took its own sine and cosine at binary256, at DEBRIS-D's 1.89 and 1.93 ms, one evaluation would cost about 11 s (COMPUTED by plan-verifier-F).
- **The cost by angle addition:**
  - the sine and cosine of only the 14 fundamental arguments are taken;
  - their powers up to 21 come from repeated complex multiplication;
  - each term is a product of at most 6 of them, then two fused multiply-adds.
  
  That is about 65,000 FMA-class operations and 28 transcendentals a point, or about 0.07 s a point at binary256 (ESTIMATE from DEBRIS-D's prices; the operation count is the lead's, from the table's shape, and F9 measures the real cost).
- **How often it would be paid:** an object-day at rk4 15 s has 11,520 distinct stage times (COMPUTED: two new times a step), and B4's fit repeats every stage time in each of its iterations.
- So even at 0.07 s the series cannot be paid per stage time. It belongs where it is paid once per node, and the nodes once per day of data.

**The default (decision 3) is a frame node table:**
1. **The slowly varying quantities** (X, Y and s, the pole offsets dX and dY, polar motion and UT1−UTC) are computed at nodes, by one routine at cft256 through libcft, with the series evaluated by angle addition.
2. **The full rotation matrix,** GCRS to ITRS, is assembled at finer nodes from them, with the Earth rotation angle's sine and cosine at cft256.
3. **Each kind receives the node values correctly rounded,** and interpolates each matrix element by a fixed scheme of additions, multiplications and FMAs.

**What that buys:**
- native equals cft, bit for bit, through the frame;
- the frame costs each kind only an interpolation per stage time;
- the table is computed once per day of data, and shared by every run and every object;
- it is pure FMA, with no transcendental on the device, so it suits the GPU route later.

The interpolation's error is a stated, computed model limit, like the gravity field's truncation at degree N.

## The shape

| agent | job | model | when |
|---|---|---|---|
| the lead (this session) | <ul><li>Phase 0, the downloads among it</li><li>the GP snapshots S0 and S1</li><li>the briefs and the ledger</li><li>escalations and TimeSheet bookings</li><li>filing each final message</li><li>the merge and its narrowing</li><li>the commit</li><li>the round's record</li></ul> | Opus | throughout |
| DEBRIS-F | the build: B1 to B4 and gates F1 to F9, in its brief below | Opus | after Phase 0 |
| verifier-F | disconfirm DEBRIS-F's build, its gates and its hindcast | Sonnet | when DEBRIS-F reports |
| merge-check-F | check any narrowing the lead makes at the merge | Haiku | after verifier-F, if the lead narrows anything |

## Phase 0: the lead, before dispatch

1. **The archive:** the one in the ledger's `tools\` (decision 7). Its SHA-256 is checked again before dispatch.
2. **Downloads,** each approved by Logan by name (decision 6). Each goes into `cft-debris-downloads\<file>\`, with its SHA-256 recorded in `lead.md`. The USNO files are held to `checksums.sha512` where it lists them.
3. **The GP snapshot S0:** one request per group (decision 5), in CSV, compressed. Any response other than HTTP 200 stops the snapshot, and the lead reports it to Logan. Each file's SHA-256, size and response date go in `lead.md`. The lead's script is `dispatch\fetch_f.py`: it follows no redirect, retries nothing and overwrites nothing.
4. **The Earth orientation file in Orekit:** the lead loads `finals2000A.daily` through a `DirectoryCrawler`, and records in `lead.md`:
   - that the load took, shown by UT1−UTC at one of the file's dates equalling the file's value, not zero;
   - how Orekit treats rows whose dX and dY are blank, such as prediction rows.
   F3's epochs then avoid such rows, or match Orekit's treatment, as `lead.md` states before dispatch.
5. **TimeSheet:** each agent's time is booked as a `notice`. F9's timings run in a `sensitive` window on `desktop`, booked when DEBRIS-F asks.
6. **Ledger files:** `DEBRIS-F.md` and `verifier-F.md`, with headers only, and the folder `debris-f\` for the data that stay out of the repository (decision 11).
7. **Dispatch,** as in "Dispatch" below.

**During the round, the snapshot S1:**
- **When:** DEBRIS-F asks for it when F6 is next, and no earlier than 3 hours after S0. That is CelesTrak's 2-hour update, with margin.
- **What:** the same requests, made the same way.
- **An S2,** under decision 5, only if S1 yields too few pairs.

No agent requests CelesTrak, or any other source, itself.

## Dispatch

Each agent's prompt is a dispatch note and its brief, followed verbatim by four sections of this plan: "Dispatch", "The ledger", "Rules every brief carries" and "READY". A script writes the prompt from this file. After dispatch, the prompt is checked against the harness's transcript.

Each agent sends one test escalation as it starts:
- it writes `test escalation from <name>` in its own ledger file;
- it sends the same words to the lead (SendMessage to `main`);
- the lead replies "received" and records the round trip in `lead.md`.

If no test escalation arrives from an agent within ten minutes of its dispatch, the lead reads that agent's ledger file, arms a watch on the ledger directory, and says so in `lead.md`.

## The ledger

The ledger is `C:\Users\logan\source\repos\cft-debris-ledger\`, as in rounds DEBRIS-B to DEBRIS-E.

- **One file per author, append only:** `lead.md` continues; this round adds `DEBRIS-F.md` and `verifier-F.md`, which the lead creates with a header only. Correct an entry by appending beneath it, never by editing it.
- **Times:** every heading's time comes from `date`, never from memory.
- **Read it at three moments:** before starting; before resting anything on another study's number; before the final report.
- **Verifiers read `lead.md` only**, and the files it points them to.
- **Escalation:** write the entry first, then message the lead (SendMessage to `main`). Wait for the answer to a question while working on what does not depend on it; never end your turn to wait.
- **Questions for cft-fp256's lead go through this round's lead.** No agent messages another session.
- **When to write:** when an entry would change another agent's work or the lead's: an environment fact, a brief that turned out wrong, or a finding about a shared input, never progress. Every entry marks which claims were measured and which are believed.
- **When a pause is announced**, record where you are before you stop. On resuming, do a full read, check your outputs before trusting your memory of them, and say where you stopped.
- **Scratch:** each agent creates its own directory when it starts, `C:\Users\logan\source\repos\cft-debris-scratch\<name>\`. Read no other agent's scratch. Keep no secrets anywhere an agent is given.
- **The downloads:** `C:\Users\logan\source\repos\cft-debris-downloads\`, one directory per file, each file's SHA-256 in `lead.md`. Read-only for every agent. This round adds the Earth orientation, leap-second, IERS and space-weather files, and the GP snapshots, each named in `lead.md`.
- **The tools:** `cft-debris-ledger\tools\`, holding the archive `cft-fp256-0aa997a3.tar`, with its SHA-256 in `lead.md`. Read-only for every agent.
- **Data kept out of the repository:** `cft-debris-ledger\debris-f\`, for the hindcast's per-object table and anything else derived object by object from GP data (decision 11). DEBRIS-F writes there; verifiers read it.
- **What the lead writes in `lead.md`, every verifier reads.** The lead relays upstream facts there. It never writes a judgement of DEBRIS-F's work there before verifier-F has reported.

## Rules every brief carries

These come from three places: Logan's standing rules (carried from cft-fp256 and cft-rebound, 2026-09 to 2026-11), canonical ParcelRound, and the rulings of rounds DEBRIS-B to DEBRIS-E.

- **Read-only, except your own outputs and scratch.**
  - cft-rebound, cft-fp256 and the TimeSheet are other sessions' live repositories. Read their files; in git, use only `git -C <repo> log` and `git -C <repo> show`. Never write in them, never run `git status` there, and never run a bare `git stash`.
  - In the TimeSheet you may run `timesheet.py check` and `list`, which only read.
  - cft-fp256 is Apache-2.0. Extract and build its archive only in your scratch.
  - In cft-debris, write only where your brief says. Commit nothing: the lead commits after verification.
- **The repository is public and MIT.**
  - Every source file you write carries a header naming cft-debris and the MIT licence.
  - Copy no third-party source into the repository, whether cft-fp256's, REBOUND's, cft-rebound's or Orekit's. libcft is linked from a build outside the repository and is never vendored; its header is reached by an include path.
  - Copy no third-party data into the repository either: no GP data, no IERS table, no Earth orientation or space-weather file. Code reads them from the downloads at run time.
  - Data derived object by object from GP data, such as the hindcast's per-object table, go to `cft-debris-ledger\debris-f\`, not the repository (decision 11). The repository gets aggregate statistics only.
  - Reading a source to understand an interface is fine; quoting more than a short passage is not.
  - This project's own earlier code (DEBRIS-B's to DEBRIS-E's) is MIT, and may be reused with a note of where it came from.
- **No downloads, installs or package managers, and no requests to any data service.**
  - The approved files are in the downloads folder, with their SHA-256 in `lead.md`. Read them in place, or copy what you need into your scratch.
  - **CelesTrak in particular:** only the lead requests it, once per update, under CelesTrak's usage policy. Ask the lead for a snapshot; never query CelesTrak yourself, not even for a page that looks like HTML.
  - If another file would settle a question, ask the lead for it. Give its name, source URL, size, licence and purpose. Each file needs Logan's approval.
- **Reading the web: HTML pages only, and never CelesTrak's.**
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
  - DEBRIS-E's `tests\cpurun.py` does both, and may be reused.
- **Long jobs:** run them through the Bash tool, in the foreground with a timeout of at most 600000 ms or with run_in_background. Never use nohup, and never end your turn while one of your jobs is running.
- **C:**
  - Before any compile, put `C:\msys64\mingw64\bin` first on PATH and check that `gcc -dumpmachine` prints `x86_64-w64-mingw32`. In this Git Bash, a bare `gcc` is the 32-bit i686 compiler.
  - libcft's Windows build line is `make -C host CC=gcc OS=Windows_NT TMP=/tmp TEMP=/tmp <targets>` (cft-fp256's `bindings/wasm/verify_demos.mjs:51-58`). On Windows the targets end in `.exe`.
  - M1's own build is `bash tests/build.sh <cft-fp256>/host <build dir>` (DEBRIS-E's build report, §3). Every native fused multiply-add goes through `_mm_fmadd_sd` or `_mm_fmadd_ss`: on this host the C library's `fma` is not correctly rounded, and at `-O0` a plain `fma()` still calls it (MEASURED, round DEBRIS-E).
- **Java:** a Java 8 runtime only, `C:\Program Files\Java\jre-1.8\bin\`, and no `javac`.
  - Run Nashorn scripts as `"C:/Program Files/Java/jre-1.8/bin/java.exe" -cp "<the jars, ;-separated, absolute paths in the downloads folder>" jdk.nashorn.tools.Shell <script.js>`.
  - `jjs -cp` and `CLASSPATH` both fail here.
  - Nashorn here is ES5: use `var` and `function`.
  - Build Orekit's dates without `createJDDate(..., TDB)` round trips, which DEBRIS-C found 11.9 to 14.5 µs off.
  - **Orekit's data:** point Orekit at a directory in your scratch holding copies of the approved Earth orientation, leap-second and space-weather files, through a `DirectoryCrawler`. Never fetch orekit-data.
  - **Assert that the Earth orientation data loaded,** in every Orekit run that uses a frame: UT1−UTC at a date the file covers must equal the file's value. Without the file, Orekit builds its frames silently with zero EOP (MEASURED by plan-verifier-F).
  - **Orekit's API:** its online Javadoc is behind bot protection. Read signatures by reflection in Nashorn (`getMethods`, `getConstructors`), and never try to pass a challenge page.
- **Python:** `C:\Users\logan\AppData\Local\Programs\Miniconda3\python.exe -I -B`. It has numpy, mpmath and rebound 5.1.1, and no scipy, pyerfa or sgp4.
- **Processes and files:** kill only processes you started, and only by PID. Delete only what you made, and never through a computed path.
- **Earlier studies' records are read-only.** Copy what you run into your scratch or your own output folder. Before your report, check all six:
  - `sha256sum -c SHA256SUMS` run from `studies\` shows 32 OK;
  - `find studies/debris-a -type f | wc -l` gives 29;
  - `sha256sum -c MANIFEST.sha256` shows 54 OK from `studies\debris-b\`, 136 OK from `studies\debris-c\`, 73 OK from `studies\debris-d\` and 60 OK from `studies\debris-e\`;
  - there is no `__pycache__` anywhere under `studies\`.
- **Host traps:**
  - **System32 before PATH.** From Python, or anything else that calls CreateProcess, Windows searches System32 before PATH. So a bare `bash` is `C:\Windows\System32\bash.exe`, the WSL launcher, and a bare `timeout` is `TIMEOUT.EXE`; System32 also holds `wsl`, `tar` and `curl`. Start every program from Python by its full path, such as `C:/msys64/usr/bin/bash.exe` and `C:/msys64/mingw64/bin/gcc.exe`, or run it through the Bash tool directly (round DEBRIS-D, `lead.md`, 2026-11-12 21:23).
  - MSYS `.exe` transparency: writing a file `X` beside an existing `X.exe` writes to `X.exe`.
  - Passing a script to bash from Python with `text=True` turns every newline into CR+LF. So does any text-mode write from Python on Windows, `Path.write_text` included. Write bytes, or open with `newline="\n"`, wherever a file's bytes matter.
  - In the Bash tool, a doubled backslash reaches the shell as one, inside a heredoc too. Write any script that contains backslashes with the Write tool, and write Windows paths in commands with forward slashes. A check run from such a heredoc matched nothing and printed no verdict in round DEBRIS-E; every check asserts that it found something to check.
  - A Bash `cd` into a subfolder can move the session's working directory for every later call. Use absolute paths, or `git -C`.
  - Git Bash's `grep` strips the CR at each line end unless given `-U`. Count CRLF with Python.
  - A harness task's `%TEMP%` output file is empty while the agent runs; a transcript is read from the session's `subagents\` folder.
  - Never start a process under `pythonw`, or detached.
- **No helper agents.**
- **Your final message is your report.** Its word limit is in your brief. If the harness refuses the write of a document your brief names, your final message is that document followed by the report, and the word limit then applies to the report alone.
- **Before you report**, stop any background work you started. End with what you did not do, and with anything your brief got wrong.

## READY, stated before the first pass

READY applies to DEBRIS-F and to every verifier's verdict. Every load-bearing claim must rest on one of:
- a measurement, with its command and output;
- a fetched source, cited by URL;
- arithmetic from labelled inputs.

Otherwise it is stated as a limit, in terms of the behaviour it concedes. A claim's domain and quantifier are claims, and so is a figure's definition. A number carried over from an earlier study keeps its definition, or it is re-measured.

**From rounds DEBRIS-B to DEBRIS-E:**
- **Every control states its pass and fail criteria before the data, and the code asserts them.** A control that fails as specified is reported as failed, whatever replaces it.
- **Every agreement claim states its tolerance before the data,** with its basis.
- **A measurement with no pass condition states its statistics, its bins and its sample before the data.** F6 is one.
- **Every log names the SHA-256 of the script that wrote it**, and the criterion that script asserted.
  - Keep every version of a script that wrote a log, under a name carrying the first 12 hex digits of its hash.
  - Never overwrite a log: number each run's log.
  - The manifest lists every version.
- **Every build prints the SHA-256 of every source it compiles** (round DEBRIS-E's builds 1 and 2 did not, and its E4 claim rested on file times).
- **An ESTIMATE names its basis and its range**, and is never added to a MEASURED figure without saying so.
- **A bound over many trials holds only when the trials are independent.** Say what varies from trial to trial (round DEBRIS-D, its marks test).
- **A cause is claimed only when a run isolates it.** Otherwise it is inferred, and labelled so (round DEBRIS-E, its IAS15 finding).

A verifier may reuse a run instead of re-running it only when all three of these hold:
- someone other than the author of the work made the run;
- its inputs are identical, file hashes included;
- the verifier re-runs from clean whatever it doubts.

Only a wrong answer sends work back: a false claim, a measurement or check that cannot fail, or code that does not build or does not do what its gate says it does. Everything else is a note the lead records, and a sentence that claims too much is narrowed at the merge.
- **Loop cap (Logan, 2026-10-15, carried through the lead's memory):** after three NOT READYs for narrowing reasons, the next pass blocks only on wrong answers.
- **Threat model (Logan, 2026-10-02):** each verifier's brief states one, and findings outside it do not reopen the loop.

## Logan's decisions (each default stands unless changed)

1. **Models:** Opus for DEBRIS-F, Sonnet for verifier-F, Haiku for a merge-check.
2. **The precession-nutation model:**
   - (a) IAU 2006/2000A, the full series from the IERS Conventions (2010), so that M1 can be held to Orekit at the microarcsecond level;
   - (b) IAU 2000B, about 80 terms, simpler and good to about a milliarcsecond (BELIEVED, from its published description), which is far below a debris orbit's needs. The gate against Orekit would then be about a hundred times looser.
   - Default: (a). It is the convention Orekit implements, so the gate can be tight; the node table makes its cost small.
3. **Where the frame is computed:**
   - (a) the node table above: one routine at cft256 computes the nodes, every kind receives them correctly rounded, and each interpolates with exact operations;
   - (b) each kind evaluates the series itself, at its own precision, at nodes, with the native kinds using the C library's `sin` and `cos` and the difference measured, as in DEBRIS-E's E1.
   - Default: (a). Native equals cft through the frame, the cost is an interpolation per stage time, and it suits the GPU route.
4. **The density model in the hindcast:**
   - (a) M1's exponential table, with the drag parameter fitted. Orekit, fitted on its own with NRLMSISE00 and CelesTrak's space weather, and with every other force matched, is a comparator on 50 pairs, to show what the table costs;
   - (b) M1 only, with no comparator and no space-weather file.
   - Default: (a). Our own NRLMSISE-00 is a later round's, after its licence is settled (decision 5 of round DEBRIS-E).
5. **The GP data:**
   - (a) four groups in CSV: `stations`, `fengyun-1c-debris`, `iridium-33-debris` and `cosmos-2251-debris`. S0 is taken in Phase 0, and S1 no earlier than 3 hours later, when DEBRIS-F asks. One more snapshot, S2, no earlier than 2 hours after S1, is pre-approved if S1 yields fewer than 50 pairs;
   - (b) add the `active` group, which is much larger, and on which CelesTrak says it is starting to enforce its limits;
   - (c) fewer groups.
   - Default: (a). Their sizes are unknown until S0. No account is needed.
6. **The downloads,** each by name. **Every request goes to its host once, made by the lead:**

   | # | file | source | size | why |
   |---|---|---|---|---|
   | 1 | `finals2000A.daily` | `https://maia.usno.navy.mil/ser7/finals2000A.daily` | not listed | Earth orientation data, M1's and Orekit's |
   | 2 | `readme.finals2000A` | `https://maia.usno.navy.mil/ser7/readme.finals2000A` | not listed | its format |
   | 3 | `checksums.sha512` | `https://maia.usno.navy.mil/ser7/checksums.sha512` | not listed | USNO's own hashes, for rows 1 and 4 where it lists them |
   | 4 | `tai-utc.dat` | `https://maia.usno.navy.mil/ser7/tai-utc.dat` | not listed | the leap seconds |
   | 5 | `icc5.pdf` | `https://iers-conventions.obspm.fr/content/chapter5/icc5.pdf` | 410K | the IERS Conventions' chapter 5: the frame's equations |
   | 6 | `tab5.2a.txt` | `https://iers-conventions.obspm.fr/content/chapter5/additional_info/tab5.2a.txt` | 167K | the X series |
   | 7 | `tab5.2b.txt` | `.../additional_info/tab5.2b.txt` | 134K | the Y series |
   | 8 | `tab5.2d.txt` | `.../additional_info/tab5.2d.txt` | 8.5K | the s + XY/2 series |
   | 9 | `SW-Last5Years.txt` | `https://celestrak.org/SpaceData/SW-Last5Years.txt` | 313,862 bytes | space weather for Orekit's NRLMSISE00; only under decision 4(a) |
   | 10 | `Circular_179.pdf` | `https://aa.usno.navy.mil/downloads/Circular_179.pdf` | 1.6M | the named source of B1's TDB−TT formula |
   | 11 to 14 | the four groups' CSV, at S0 | `https://celestrak.org/NORAD/elements/gp.php?GROUP=<group>&FORMAT=csv` | unknown | the orbit data |
   | 15 to 18 | the same four, at S1 | as above | unknown | the next update |
   | 19 to 22 | the same four, at S2 | as above | unknown | only if S1 yields fewer than 50 pairs, under decision 5(a) |

   - The sizes marked "not listed" are not on the pages read. The lead records each one at download.
   - **Row 10's cost** is 1.6M for one formula. Without it, B1 would take TDB−TT from Orekit's `TDBScale`, whose source the lead cannot read, and F2 would then compare Orekit with itself. So row 10 stays in the default list, and Logan may strike it.
   - No second SGP4 is downloaded. Orekit's `TLEPropagator` is the decoder, and its agreement with the published SGP4 verification cases is BELIEVED, not re-checked here. python-sgp4 (MIT, PyPI) would be a second decoder, and is offered as an extra, not a default.
7. **libcft:**
   - (a) the archive in the ledger, at 0aa997a3, as in DEBRIS-E;
   - (b) a newer pin, cft-fp256's main at 9abd37ab, with a new archive made in Phase 0.
   - Default: (a).
8. **Layout:**
   - (a) the build extends `src/` and `tests/`. Logs and records go in `studies/debris-f/`, and the build report is `studies/DEBRIS-F-build.md`. The uniform rotation stays available as a mode, so that DEBRIS-E's gates still reproduce;
   - (b) another layout Logan names.
   - Default: (a).
9. **Scope and budgets:**
   - (a) One round:
     - DEBRIS-F gets 6 hours of wall time and 95 CPU-minutes, and messages the lead before any single run expected to pass 5 CPU-minutes, and before any line below runs over;
     - the CPU-minutes by line:

       | line | CPU-minutes | approved in advance |
       |---|---|---|
       | the fits and the hindcast (B4, F5, F6), Orekit's comparator (C) taking at most 10 of them | 40 | yes |
       | F7's 6-hour arcs at the wide kinds | 15 | yes |
       | F9's timings | 10 | yes |
       | the node tables, and F3's direct evaluations | 5 | yes |
       | F8 at E8's arcs | 5 | yes |
       | development, builds, and F1 to F4 | 20 | no: the 5-minute message rule applies |

     - **The fits** are ESTIMATEd at 17 to 40 CPU-minutes (plan-verifier-F's re-check):
       - M1's fits cost about 2 to 11 s each;
       - F6 reuses an F5(d) fit wherever an object and its S0 set are the same;
       - Orekit's (C) stops at 50 pairs or 10 CPU-minutes, whichever comes first.

     - F7 is COMPUTED at 9 to 14 CPU-minutes:
       - 10 objects, 6-hour arcs at cft64 and cft128;
       - 3 objects at cft256;
       - at E9's object-day prices, from 64 lanes to 1 lane: 55 to 97 s at cft64, 88 to 141 s at cft128, and 222 to 340 s at cft256.
       - The upper end is one lane a batch. Batching the objects from a common start epoch brings it down.
     - verifier-F gets 3 hours and 30 CPU-minutes;
     - a merge-check gets 25 minutes.
     - If time runs short, DEBRIS-F cuts in this order: F9, then F7's cft256 leg, then F6's NRLMSISE00 comparator, then the binary32 rung of the new kernels. B1 to B4, F1 to F5, F6's core and F8 are kept.
   - (b) Two rounds: the time scales and the frame (B1, B2, F1 to F4 and F8) first; the orbit data, the fit and the hindcast (B3, B4, F5 to F7 and F9) in a second round.
   - Default: (a). For scale, DEBRIS-E used 72 minutes of wall time and 31.6 CPU-minutes for its build.
10. **Outputs and the push:** the lead commits the build after verification and the merge. Pushing to the public repository waits for Logan's word.
11. **Data derived from GP data, object by object** (new in draft 2):
    - (a) the hindcast's per-object table, with each object's catalogue number, epochs and misses, stays in the ledger's `debris-f\`, outside the repository. The repository gets the aggregate statistics only: counts, medians, 90th percentiles and shares;
    - (b) the per-object table is published in `studies\debris-f\` too.
    - Default: (a). CelesTrak's terms for derived data were not read, so the plan does not assume they allow it.

## Not in this round

- **Our own NRLMSISE-00 or JB2008.** Their licences are unsettled (DEBRIS-B, DEBRIS-D), so they stay referees, through Orekit.
- **The 24/7 loop itself:** scheduled snapshots, a service, and the statistic over weeks. F6 is its first measurement, made by hand.
- **Precise orbits as truth,** such as ESA's Sentinel-1 orbits. They would hold M1 to metres, where GP data hold it to the GP sets' own error.
- **Sub-daily tides and libration in the Earth's orientation.** They are left out on both sides, as in Orekit's "simple EOP", and their size is stated as a limit.
- **The GPU route.** It waits for cft-fp256's second GPU round: index tables, the 2,048-slot depth, and the device divide and square root, which Logan approved for that round on 2026-11-13 (READ, cft-fp256's `docs/studies/GPU-E-mi300x-ring.md`, its dated note).
- **Writing or auditing a certificate.** The node table is a fixed data stream, which a certificate could later cover. None is written.
- **Any account, any GPU, WSL, card or box,** and any download not listed in decision 6.

---

## Brief: DEBRIS-F

You are build parcel **DEBRIS-F** in cft-debris, a project for space-debris tracking and simulation. Its folder, `C:\Users\logan\source\repos\cft-debris`, is a public git repository under the MIT licence. You take M1, the CPU reference propagator from round DEBRIS-E, to the real Earth and to open orbit data, and you build the gates that hold it. You commit nothing: the lead commits after verification.

**Budget:** 6 hours of wall time and 95 CPU-minutes. Message the lead before you pass either, before any line below runs over, and before any single run you expect to pass 5 CPU-minutes outside the approved lines. Five lines are approved here and need no message:
- the fits and the hindcast (B4, F5 and F6): up to 40 CPU-minutes in all. Orekit's comparator (C) takes at most 10 of them, and stops at 50 pairs or 10 minutes, whichever comes first. F6 reuses an F5(d) fit wherever the object and its S0 set are the same;
- F7's 6-hour arcs at the wide kinds: up to 15;
- F9's timings: up to 10;
- the node tables and F3's direct evaluations: up to 5;
- F8, at E8's arcs: up to 5.

The other 20 CPU-minutes are for development, builds and F1 to F4. Log each line's use. Runs at cft128 and cft256 are slow: 4.0 to 5.2 and 9.5 to 13.5 ms a lane-evaluation at degree 20 (MEASURED, DEBRIS-E E9, single runs). So hold their arcs short, and say how long each is.

**Start here:**
1. This plan, `C:\Users\logan\source\repos\cft-debris\studies\DEBRIS-F-plan.md`: Logan's words, what each part settles, and what the round starts from.
2. M1 itself: `src\`, `tests\`, `studies\DEBRIS-E-build.md` (narrowed at the merge; its last section lists the narrowings) and `studies\debris-e\`.
3. `lead.md` in the ledger: Phase 0, the downloads' SHA-256, and the snapshot S0.
4. Chapter 5 of the IERS Conventions (2010), `icc5.pdf` in the downloads, for the frame's equations; `readme.finals2000A` for the Earth orientation file's format; and USNO Circular 179, `Circular_179.pdf`, for TDB−TT.
5. Orekit's API, read by reflection in Nashorn (`getMethods`, `getConstructors`) for `TLE`, `TLEPropagator`, `FramesFactory`, `IERSConventions`, `TDBScale`, `NRLMSISE00` and `BatchLSEstimator`. Its online Javadoc is behind bot protection: do not try it.

**Where it goes:**
- `src/` and `tests/`: the library and the gates, extended;
- `studies\debris-f\`: the logs and records, with a `MANIFEST.sha256` over them;
- `studies\DEBRIS-F-build.md`: the build report. It covers what was built, how to build it, each gate's criteria and result, the hindcast's aggregate tables, and the limits.
- `cft-debris-ledger\debris-f\`: the hindcast's per-object table and anything else derived object by object from GP data (decision 11), with its SHA-256 named in the build report.
- **In your scratch only:** cft-fp256's sources, libcft's build, every executable, the node tables, and every third-party file, the GP snapshots included.

**B1. Time scales,** on the host, exact to 1 ns or better as arithmetic:
- UTC to TAI from `tai-utc.dat`; TAI to TT by 32.184 s; UT1 from UTC and the interpolated UT1−UTC.
- **TT to TDB** by a formula from USNO Circular 179, cited by its equation number. Its stated accuracy is the model's limit. Orekit's `TDBScale` is a different short series, about 1 µs away (MEASURED by plan-verifier-F), and F2's tolerance allows for that.
- **M1's time stays TDB seconds** from `jd_epoch`. Every GP epoch, Earth orientation date and pseudo-observation is converted onto it.
- **Each object's run has its own origin,** the start of its fit span, held exactly as TDB seconds from `jd_epoch`. State how.
  - The fit's pseudo-observations, every 2 minutes, fall on the 15 s grid: every 8th step.
  - A prediction runs whole steps to the last grid time before e1, then one short step that lands on e1 exactly. State how that step's length is formed, in every kind.

**The force model** for B4, F5, F6 and F7: M1's full model at degree 20, with the Sun, the Moon, drag through the 28-band table and radiation pressure, and rk4 at 15 s. DEBRIS-D measured rk4's error at 15 s as 3.3 m an object-day, for one LEO object at degree 20 with drag.

**B2. The Earth's orientation, IERS Conventions (2010), CIO-based** (decisions 2 and 3):
- **[GCRS] = Q(t) R(t) W(t) [ITRS]:**
  - Q from X and Y (`tab5.2a.txt`, `tab5.2b.txt`), from s (`tab5.2d.txt`), and from the pole offsets dX and dY;
  - R from the Earth rotation angle, from UT1;
  - W from polar motion and s′.
- **Earth orientation data** from `finals2000A.daily`, interpolated by a scheme you name, with sub-daily tides and libration left out. Their size, READ from the conventions, is stated as a limit.
- **The node table:**
  - the slow quantities at nodes, then the matrix at finer nodes, each by one routine at cft256 through libcft;
  - **the series by angle addition:** the sines and cosines of the 14 fundamental arguments only, their integer multiples by complex multiplication, and each term as a product of at most 6 of them. No term takes its own transcendental;
  - every kind receives the nodes correctly rounded, and interpolates the matrix elements with additions, multiplications and FMAs only, in a fixed order;
  - state the node spacings and the scheme, and bound the interpolation error by computation;
  - **the window:** the days of data the round uses, from one day before the earliest fit span to one day after the latest S1 epoch. State it;
  - a table's build stays under 2 CPU-minutes. If it would not, message the lead before running it;
  - **choose the fine spacing with that cost in view.** A fine node needs about 10 transcendentals at cft256 (ERA's and the polar motion's), about 20 ms (ESTIMATE, plan-verifier-F's re-check). At 60 s spacing a week is about 10,000 nodes and 200 s, past the cap; at 300 s it is about 2,000 nodes and 40 s (COMPUTED from that ESTIMATE). Advancing ERA by angle addition is the other way down;
  - the table is built once per window and kept, with its SHA-256, in your scratch.
- **Drag's co-rotation** uses the Earth's angular velocity from the same model. Say how it enters.
- **The uniform rotation stays,** as a mode, so that DEBRIS-E's gates still reproduce (F8).

**B3. Open orbit data:**
- **A parser for CelesTrak's CSV.** Name its columns from S0's own header, and handle 6-digit catalogue numbers.
- **The decoder:** Orekit's `TLEPropagator` (SGP4), through Nashorn, with each `TLE` built from the CSV's mean elements in the units Orekit's javadoc gives. It yields GCRF positions and velocities at requested UTC instants, through the same Earth orientation file.
- **The sample,** stated in a script before S0's values are read:
  - ephemeris type 0 only;
  - any object Orekit cannot build is excluded and counted;
  - F5(d) takes 100 objects: every object of the `stations` group, and the rest by a seeded random draw across the other groups, in proportion to their sizes. State the seed beforehand.

**B4. The fit,** at native64:
- **Pseudo-observations:** GCRF positions from SGP4 at the S0 set, every 2 minutes over the day before that set's epoch, e0.
- **The parameters:**
  - the state at the span's start;
  - the drag parameter `bc` too, for objects with perigee under 1,000 km;
  - `cram` fixed at a value you state.
- **The method:** Gauss-Newton, with partials by finite differences run as extra lanes of the same batch (one nominal lane and up to seven perturbed), with step sizes you state.
- **Stop** when every parameter's relative change falls below a threshold you state, or after 10 iterations, and count the fits that stop on the iteration limit.

**The gates,** in `tests/`. For each gate: write its criteria into its script before its data, assert them in code, and give it a negative control that must fail as specified. Each gate's size is fixed below, so that the budget holds.

- **The NaN rule,** as in DEBRIS-E: non-NaN results agree bit for bit; NaN results agree as NaNs.
- **F1. Native against cft, the new kernels,** at binary64 and binary32:
  - the node table's interpolation and the frame's application, at 10,000 random stage times and states;
  - bit for bit, wherever only addition, multiplication, FMA, division and square root are involved;
  - **negative control:** one operation reordered in the native build alone must break bit-identity, and the gate must say where.
- **F2. Time scales against Orekit:**
  - at 1,000 epochs spread over the Earth orientation file's span: TAI−UTC, TT−TAI, TDB−TT and UT1−UTC, each within a tolerance stated beforehand with its basis. TDB−TT's tolerance covers the two models' difference;
  - **the leap seconds themselves:** TAI−UTC at epochs just before and after 2015-06-30 24:00 and 2016-12-31 24:00 UTC, against Orekit's UTC, which loads the same `tai-utc.dat` through its own parser. These need no Earth orientation data. The file's 2026 span holds no leap second;
  - **negative control:** the leap-second table cut before 2017 must fail.
- **F3. The Earth's orientation against Orekit** (IERS 2010, simple EOP):
  - (a) **the model:** at every one of the Earth orientation file's own dates across its span (about 180), the node routine itself, at cft256 and with no table, against Orekit. The angle between the two GCRS-to-ITRS rotations must be within a tolerance no looser than 50 µas. At about 0.07 s a date, that is seconds (ESTIMATE);
  - (b) **the table as M1 uses it:** at 1,000 epochs inside the window, within a tolerance no looser than 1 mas, whose basis is the two interpolation schemes;
  - (c) the node table's interpolation, against direct evaluation at cft256 at 200 midpoints between nodes, within the computed bound;
  - every epoch respects the Phase 0 ruling on rows with blank dX and dY;
  - **negative control:** a plant chosen beforehand, at least ten times the tolerance in (a), with its expected size computed, must fail (a).
- **F4. Forces in the real frame against Orekit,** at 1,000 sampled LEO states at native64 and cft64, with Orekit's ITRF (IERS 2010, simple EOP) as the body frame:
  - **the epochs:** the Earth orientation file's own dates inside the window, about 5 to 8 frames, with the states spread across them. F4 tests the forces given a frame; F3(a) tests the frame across the file's span;
  - **gravity at degree 20,** within a tolerance derived beforehand from F3(a)'s. A frame error δθ turns the non-central acceleration by δθ. J2's is about 1.25e-2 m/s² in LEO, so 50 µas, 2.4e-10 rad, gives about 3e-12 m/s² (COMPUTED). Add DEBRIS-E E6's agreement to that;
  - **drag,** with one band, against Orekit's `SimpleExponentialAtmosphere` co-rotating with that frame;
  - **negative controls:**
    - one drag parameter planted 1% off must break drag's tolerance;
    - a pole tilt of ten times F3(a)'s tolerance, in our frame alone, must break gravity's.
- **F5. The decoder and the fit:**
  - (a) every S0 row's parsed numbers, converted to Orekit's units, equal the values Orekit's `TLE` getters return for the object built from them;
  - (b) **sensitivity control:** a mean motion planted 1e-6 rev/day off moves SGP4's position by an amount computed beforehand;
  - (c) **synthetic truth:** pseudo-observations made by M1 itself, from a state and `bc` you choose, are fitted back. Hold the recovered state and `bc` to tolerances stated beforehand;
  - (d) on S0's sample: the post-fit RMS of the position residuals, and the counts of fits that converged and that did not. This is a measurement.
- **F6. The first hindcast,** a measurement, with its sample, statistics and bins fixed in a script before S1 is read:
  - **The pairs:** objects whose S1 set has a later epoch e1 than their S0 set's e0, by no more than 3 days. If there are more than 200, take every `stations` pair and a seeded random draw of the rest, in proportion to the groups, to 200 in all. State the seed beforehand.
  - **The methods:**
    - (A) M1, fitted as in B4, propagated from its fit to e1;
    - (B) SGP4 from the S0 set to e1;
    - (C, decision 4(a)) Orekit, fitted on its own:
      - its `BatchLSEstimator`, on the same pseudo-observations, estimates the state and the drag coefficient;
      - its force model is NRLMSISE00 with CelesTrak's space weather, Holmes-Featherstone gravity at degree 20 from the same EIGEN-6C4, the Sun and the Moon from the same DE421, and radiation pressure with the conical shadow and the same `cram`;
      - it then propagates to e1 with the same forces;
      - it runs on a subset of 50 pairs, by a seeded draw stated beforehand, and stops early if it reaches 10 CPU-minutes.
      
      (A) and (C) then differ in density model and in code. F4 holds the codes together where the models match, so any difference between (A)'s and (C)'s misses is attributed to the density models as an inference, not an isolated cause.
  - **The miss:** each method's position at e1 against SGP4 from the S1 set at e1, as a distance and in radial, along-track and cross-track parts.
  - **The statistics:**
    - each method's median and 90th percentile, in three perigee bands (under 500 km, 500 to 800, 800 and over) and three horizons (under 6 h, 6 to 24 h, 24 h and over);
    - a cell with fewer than 20 pairs gives its count and median only. The band under 500 km is expected to hold the `stations` pairs alone (BELIEVED: the debris groups orbit higher);
    - the share of pairs in which (A) misses less than (B). The pairs cluster by breakup and by how recently they were updated, so the share is not a sample of independent trials. Say so;
    - the ten largest misses, by object, in the ledger's `debris-f\` (decision 11).
  - **Controls,** each asserted for every pair:
    - **the time tag:** SGP4 from the S1 set evaluated at e1 + 1 s, with the method's position kept at e1, must change the miss vector by the reference's velocity times 1 s, within 1% of that velocity's size. Compare the Cartesian GCRF miss vectors, not radial, along-track and cross-track parts, which rotate;
    - **equal sets:** an object whose S1 set equals its S0 set must give (B) a miss of exactly 0. This catches a mismatch of identities or times, not much else;
    - **swapped identities:** one object's (B) position against another object's S1 reference must miss by more than 100 km.
  - What F6 says holds for this sample on this day, and the S1 set's own error is part of every miss. Say so.
- **F7. The precision ladder on real objects:**
  - 10 of F6's objects, the lowest perigees first, with (A)'s fitted states propagated over a fixed 6-hour arc from e0 at native64, cft64 and cft128, and 3 of them at cft256;
  - **every kind starts from the same state at e0:** one native64 run from the fit carries each object to e0, and its binary64 state goes to every kind, exactly, since binary64 converts exactly into the wider formats;
  - batch them from a common start epoch where you can;
  - each kind's difference from the widest run, against a bound for cft128 stated beforehand, as in DEBRIS-E's E3.
- **F8. Reproducibility,** on E8's arc (8 lanes, 100 steps of 60 s) in the real frame, with one run ending on a short step:
  - two runs agree; `-O0` equals `-O2`; restarted segments equal the continuous run, at native64, cft64 and cft128;
  - **the regression:** in the uniform-rotation mode, the new build reproduces DEBRIS-E's E2 trajectories and E4's outputs at a sample of epochs, bit for bit, against DEBRIS-E's logs.
- **F9. Cost,** in a `sensitive` window the lead books. Run nothing else during the window. Give:
  - each kind's time per force evaluation with the real frame, beside DEBRIS-E's E9;
  - the node table's build time per day of data;
  - a fit's time per object at native64.

**Instruments on this host:**
- C, with gcc 16.1.0 from mingw64;
- Python with numpy, mpmath and rebound 5.1.1;
- Java 8, with Orekit 13.1.9 and Hipparchus 4.0.3 from the downloads;
- the archive of cft-fp256;
- the web, HTML pages only, and never CelesTrak.

**Do not:**
- write outside `src/`, `tests/`, `studies\debris-f\`, `studies\DEBRIS-F-build.md`, the ledger's `debris-f\` and your scratch;
- put any per-object table derived from GP data in the repository;
- request any data service, CelesTrak above all;
- run anything on a GPU;
- message any session but the lead;
- weaken a gate's criterion, or a claim's label, to make it pass.

**Report:** your final message, under 1,200 words:
- what was built;
- each gate's result, with its most load-bearing evidence and its label;
- F6's table, in brief;
- every control that failed, and what you did next;
- anything you could not settle;
- what you did not do;
- anything this brief got wrong.

---

## Brief: verifier-F (completed when DEBRIS-F reports)

You are **verifier-F**: a verifier, not an author. Try to disconfirm DEBRIS-F's build, its gates and its hindcast, and report. Fix nothing. Budget: 3 hours of wall time and 30 CPU-minutes, counted by cycles. The lead books your time as a `notice`, and books any timing window you ask for. Re-run each gate at its stated size or smaller, and say which.

**Threat model.**
- **In scope:**
  - code that does not build from clean with the build report's commands;
  - a gate that does not test what it says, or could not fail;
  - a criterion, a statistic or a sample rule set after its data;
  - a bit-identity claim that does not hold on inputs the gate did not try;
  - a referee comparison whose inputs were not matched;
  - a claim whose domain, quantifier or cause reaches past its evidence;
  - third-party source or data in the repository.
- **Out of scope:**
  - the choice of route, which is Logan's;
  - the physics of the models themselves, beyond whether the code computes what the build report says it does.

The attack list is finished from DEBRIS-F's own content, and starts with:
1. Build libcft from the archive and the library from clean, in your scratch, with the build report's commands.
2. Re-run F1, and F2 and F3 at epochs of your own, with their controls.
3. Check the node table's error bound, and re-derive it.
4. Re-run F4 and F8, the regression against DEBRIS-E included.
5. Re-run F5(c) with a state of your own, and a sample of F6's fits.
6. Recompute F6's statistics from its per-object table in the ledger's `debris-f\`, and check its controls and its sample's draw.
7. Hold the build report against the logs, and every header and file against the licence and data rules.
8. Check criteria before data by the logs' script hashes, with a negative control.
9. Anything else.

**Report:** your final message, under 1,200 words.
- For each item: the commands you ran, what you observed, and a verdict (confirmed, defect, or not determined).
- Every defect needs a concrete failure scenario. "Found nothing" is an acceptable answer.
- End with what you did not do, and anything this brief got wrong.

---

## What changed from draft 1 (plan-verifier-F's findings, answered)

plan-verifier-F's report is filed verbatim as `cft-debris-ledger\filed\DEBRIS-F-plan-verifier-F-report.md`. The lead re-counted blocker 1's terms itself before answering it (`lead.md`).

| plan-verifier-F found | draft 2 |
|---|---|
| **Blocker 1.** The series has 2,941 terms; evaluated term by term at cft256 a point costs about 11 s, so F3(c), the node routine and F3 at 1,000 epochs overrun the budget | Confirmed by the lead. B2 requires angle addition, with no transcendental per term: about 0.07 s a point (ESTIMATE). F3 uses the node table; F3(c) is sized at 200 midpoints; a table's build stays under 2 CPU-minutes; the table covers a stated window, not the file's whole span |
| **Blocker 2.** F7 "over their horizons" costs 36 to 53 CPU-minutes per day of horizon, far past its 25 | F7 runs a fixed 6-hour arc from e0: COMPUTED at 9 to 14 CPU-minutes, now its own 15-minute line |
| F6's 1 s control was ambiguous, with no tolerance | Only the reference moves, to e1 + 1 s. The miss vector must change by its velocity times 1 s, within 1%, for every pair |
| No sample rule, and no minimum cell size | F5(d): 100 objects, every `stations` object and a seeded draw. F6: up to 200 pairs, the same way. Fewer than 20 pairs in a cell give the count and median only |
| Stage times at an arbitrary start, and the end at e1 | B1: each run's own exact origin, pseudo-observations on every 8th step, and one short final step landing on e1. F8 covers a run ending on it |
| F2 could not exercise a leap second | F2 adds TAI−UTC either side of 2015-06-30 and 2016-12-31, from `tai-utc.dat` |
| Comparator (C) under-specified, and fed a `bc` fitted to another density model | (C) is Orekit's own fit, by `BatchLSEstimator`, with every force matched but density, on 50 pairs. The A-to-C difference is labelled an inference |
| F4's control could not test the frame | F4's states sit at F3(a)'s epochs. Its gravity tolerance comes from F3(a)'s, and a pole tilt of ten times F3(a)'s tolerance must break it |
| The per-object table, derived from GP data, would enter the public repository | Decision 11 (new): it stays in the ledger's `debris-f\`, and the repository gets aggregates |
| The downloads table lacked S2, and row 9 was conditional | Rows 19 to 22 for S2, with their condition; row 9 marked "only under decision 4(a)"; row 10, USNO Circular 179, added for TDB |
| Orekit builds frames silently with zero Earth orientation data | The Rules require every Orekit run to assert that the file loaded. Phase 0 records how Orekit treats rows with blank dX and dY, before dispatch |
| **Probes:** 6-digit `TLE` works; `tai-utc.dat` loads; `TDBScale` sits about 1 µs from the two-term formula; no planned download named TDB's source | In "What DEBRIS-F starts from". B1 takes TDB−TT from USNO Circular 179, and F2's tolerance covers the models' difference |
| **Notes:** the equal-sets control is near-tautological; the pairs cluster; F8 at cft128 had no budget line; F5(a) could pass by keeping strings; the budget did not add up | A swapped-identity control is added and the equal-sets control's reach stated. The clustering is stated beside the share. F8 runs on E8's arc with its own line. F5(a) compares with Orekit's getters. The budget is 90 CPU-minutes in six lines |
| **Also found by the lead:** Orekit's online Javadoc is behind bot protection | The brief reads Orekit's API by reflection, and forbids trying the challenge page |

## What changed from draft 2 (plan-verifier-F's re-check, answered)

The re-check is filed verbatim as `cft-debris-ledger\filed\DEBRIS-F-plan-verifier-F-recheck-report.md`. It confirmed that both blockers are fixed, with its own arithmetic for each.

| the re-check found | draft 3 |
|---|---|
| F3(a) at 1,000 epochs could not run: the window holds only about 5 to 8 of the file's dates, and F4 inherited that | F3(a) tests the model at every file date across the file's span, by the node routine with no table. F3(b) tests the table at 1,000 epochs in the window. F4 spreads its 1,000 states over the window's 5 to 8 frames, and says it tests the forces given a frame |
| 30 CPU-minutes may not cover 300 M1 fits and 50 Orekit fits: 17 to 40 minutes (ESTIMATE) | The fits line is 40 CPU-minutes. (C) stops at 50 pairs or 10 minutes. F6 reuses F5(d)'s fits. The total is 95 CPU-minutes, with development at 20 |
| **Notes:** the table cap is tight at fine spacing; F7's state at e0 was undefined; F2's leap epochs and Orekit; the time tag in Cartesian vectors; row 10's cost | B2 states the fine-node cost, 300 s against 60 s, and ERA by angle addition as an option. F7 starts every kind from one native64 state at e0. F2 compares the leap epochs with Orekit's UTC. F6 compares Cartesian GCRF vectors. Decision 6 states row 10's cost and its alternative |

## What earlier rounds taught, applied here

| lesson | here |
|---|---|
| Criteria set after the data, and a redefined control reported as passing | Criteria before the data, asserted in code, and each script version kept under its hash (READY) |
| A claim rested on file times, because builds printed no source hashes (DEBRIS-E's E4) | READY: every build prints every source's SHA-256 |
| A cause stated as fact when no run isolated it (DEBRIS-E's IAS15 finding) | READY: a cause is claimed only when a run isolates it |
| A figure measured on a kernel's output reported as the function's (DEBRIS-E's ulps) | F1 names what it measures; the frame's transcendentals run once, at cft256 |
| A check that could not fail for some of its cases (DEBRIS-E's transcendental control) | F3's and F5's controls are sized beforehand against their tolerances |
| A bare `bash` from Python reached WSL (DEBRIS-D) | The Rules' first host trap |
| A figure taken from an interim message instead of the report (DEBRIS-D's merge) | The lead quotes only filed reports at the merge |
| Orekit's dates built with `createJDDate(..., TDB)` (DEBRIS-C) | The Rules' Java line |
| Data services can block a client that ignores their terms | Only the lead requests CelesTrak, under its usage policy |

## The lead's slips so far

Rounds DEBRIS-B's to DEBRIS-E's are in their records. In drafting DEBRIS-F:
- **Draft 1 carried DEBRIS-C's atmosphere costs from the lead's memory notes,** as 7.3 µs and 30 µs a call. The study gives ranges: 7.3 to 7.5 µs and 29.9 to 31.6 µs. The plan checker caught it (log 001), and the figures now come from the study.
- **A `cd` into `studies\` moved the session's working directory again,** the trap the Rules name. It was restored at once.
- **Draft 1 priced the series naively and never committed the routine to a cheaper method,** so the round could not fit its budget (plan-verifier-F's blocker 1).
- **Draft 1 left F7's arcs as long as the hindcast's horizons,** past their budget by two to six times (blocker 2).
- **Draft 1 sent DEBRIS-F to Orekit's online Javadoc,** which is behind bot protection.
- **Draft 1 left the per-object table's place, the sample's rule, the comparator's forces and TDB's source unstated.** plan-verifier-F found each one.
- **Draft 2 put F3(a) at 1,000 epochs inside a window that holds only about 5 to 8 of the file's dates,** and set the fits line at 30 CPU-minutes without pricing the fits. The re-check found both.
- **The checker's own slips:**
  - **Log 005:** a control written too broadly failed on the historical record of draft 2.
  - **Log 006:** the edit narrowing that control went through a Bash heredoc. Its doubled backslash collapsed, as the Rules warn, and the checker crashed. The crashed version is kept, and the fix went in with the Edit tool.
