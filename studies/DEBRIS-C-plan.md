# DEBRIS-C: the measurements that would decide build, adopt or hybrid (plan of record, draft 3)

Drafted 2026-11-12 by cft-debris's lead for Logan's approval. Nothing has been dispatched, and nothing has been downloaded.
- **Draft 1** went past a plan verifier, plan-verifier-C (Sonnet, ParcelRound METHOD §7). It found no blocker, five defects and six notes.
- **Draft 2** answered them.
- **The same verifier's scoped re-check of draft 2:**
  - eight answered, two partly, one not;
  - two new defects and three new notes.
- **This draft** applies them in the verifier's own terms, and has not been checked a third time. The last sections list what changed, and the lead's slips.

## The question, in Logan's words

- **Before DEBRIS-B** (2026-11-12): "Im considering how challenging making a custom simulation model might be, considering how specialized of a focus this is and effects REBOUND isnt particularly good at or even supports"
- **After DEBRIS-B** (2026-11-12): asked "Should I draft DEBRIS-C around the three measurements that would decide it?", Logan answered "Draft DEBRIS-C".

## What DEBRIS-C is for

DEBRIS-B (verified by verifier-B, narrowed at the merge: `studies\DEBRIS-B-custom-model.md`) made no recommendation among building a custom model, adopting Orekit and cascade, or a hybrid in which those tools are the custom model's foreign oracles. It named three measurements that would decide it. DEBRIS-C runs the first two, adds the cost DEBRIS-B left open, and designs the third:

| measurement | what it decides | if it comes out one way | if the other |
|---|---|---|---|
| **M1. Force kernels held to published authorities.** A custom binary64 kernel and Orekit, each against Lasser et al. 2020's gravity accelerations and JPL's DE421 test points | whether a custom model can be verified layer by layer against authorities that exist, and whether Orekit can serve as the hybrid's oracle | both meet the stated tolerance: building is verifiable, and Orekit is a usable oracle | either misses: say where, and what that costs the option it belongs to |
| **M2. The density models' cost.** Orekit's NRLMSISE-00 and JB2008, timed per call | the LEO catalogue budget, which DEBRIS-B left as a parameter (break-even 1.85 µs) | under the break-even: DEBRIS-B's budget roughly holds | over it: the budget multiplies, and the density model dominates any build |
| **M3. Bit-reproducibility, on both sides.** One Orekit propagation rerun across JVM modes, and the custom C kernel built with and without fused multiply-adds | whether "bit-reproducible predictions that carry their provenance" could set a custom model apart | Orekit reproduces itself across modes on this JVM: the differentiator is weakened but not settled, because other JVM versions, threads and architectures are untested | it does not: a candidate advantage, with its measured size |
| **M4. A covariance-realism hindcast, designed, not run** | whether candidate 2, "uncertainty with a refusal", can be tested with public truth data, and at what cost | feasible with public data: a later round runs it | not feasible: the candidate cannot be shown real with what exists |

The decision stays Logan's. Where the evidence does not decide, DEBRIS-C makes no recommendation.

## What DEBRIS-C starts from (labels as in DEBRIS-B)

- **Lasser et al. 2020** (Adv. Geosci. 55, 1-11; READ (via WebFetch), https://adgeo.copernicus.org/articles/55/1/2020/):
  - one day, 3 July 2008, of a GRACE orbit at 30 s, at a mean altitude of 466 km, in GPS time;
  - accelerations for the gravity field (EIGEN-6C4, degree and order 2 to 180) and for third bodies from DE421, among others, in the CRF, with the gravity field also given in the TRF;
  - the orbit in the TRF (ITRF2014) and the CRF (ICRF2), and the rotation as quaternions and matrices;
  - data "freely accessible" at `ftp://ftp.tugraz.at/outgoing/ITSG/COST-G/softwareComparison/`, with `00README_simulation.txt`; the article is CC BY 4.0. The page names no other file, and does not mention drag, radiation pressure or albedo.
  - 1e-11 m/s² is the threshold the COST-G packages met for each force (READ (via WebFetch), the article), not a measured agreement. The EGU 2020 abstract puts their agreement "below 1e-11 m/s²", with one exception in the solid Earth tides (READ, search excerpt, https://boris.unibe.ch/144918/1/EGU-GA-2020-las.pdf).
  - **Not on the article's page:** whether degree 0 (the central term) is in the gravity accelerations; the tide system; whether EIGEN-6C4's coefficients carry time-variable terms. The README and the coefficient file's header must settle these before any comparison.
- **JPL's planets README:** `C:\Users\logan\.claude\projects\C--Users-logan-source-repos-cft-debris\f2d8df67-8151-496f-a30a-eb8aa40b27db\tool-results\webfetch-1794526145347-n7y0el.bin`. WebFetch saved it in round DEBRIS-B, and Logan approved it for reading.
  - It describes the ephemerides.
  - It does not mention `testpo` or `testeph`, or give a test tolerance (MEASURED with `grep`, by plan-verifier-C and the lead).
- **Orekit 13.1.9** (READ (via WebFetch), its pom at the tag, https://github.com/CS-SI/Orekit/blob/13.1.9/pom.xml): Java source and target 1.8; Apache-2.0; runtime dependencies are seven Hipparchus 4.0.3 modules and nothing else.
- **This host's Java** (MEASURED by the lead, 2026-11-12): a Java 8 runtime only, `C:\Program Files\Java\jre-1.8` (1.8.0_411). No `javac`. Nashorn's `jjs.exe` is in its `bin\`, and ran a one-line script.
- **DEBRIS-B** (verified): binary64 force kernels cost 1.2 to 11 µs per evaluation in LEO without a density model; the density model doubles the degree-20 LEO cost above 1.85 µs a call; Orekit's density models' cost was not found.

## The shape

| agent | job | model | when |
|---|---|---|---|
| the lead (this session) | Phase 0 below; writes the briefs and keeps the ledger; answers escalations; files each final message; narrows at the merge; writes the round's record with its cost | Opus | throughout |
| DEBRIS-C | the study: M1 to M4 in its brief below | Opus | after Phase 0 |
| verifier-C | disconfirm DEBRIS-C | Sonnet | when DEBRIS-C reports |
| merge-check | check any narrowing the lead makes at the merge | Haiku | after verifier-C, if the lead narrows anything |

The models follow Logan's rule of 2026-10-12 for challenging work (carried from cft-fp256 through the lead's memory), and the round DEBRIS-B precedent for a very small fix.

## Phase 0: the lead, before dispatch

1. **Metadata, saving nothing** (decision 2): list Lasser et al.'s FTP directory with its sizes; print `00README_simulation.txt` to the terminal to read its file names and conventions; ask ICGEM's server for the sizes of EIGEN-6C4's `.zip` and `.gfc` (an HTTP HEAD request). Record the listings in `lead.md`.
2. **Ask Logan, by name and size, for the files the listing shows M1 needs** (decision 3), and for EIGEN-6C4 if Lasser's dataset does not carry it.
3. **Download each approved file** into its own new, empty directory under `C:\Users\logan\source\repos\cft-debris-downloads\`.
   - Check its byte count against the server's listing.
   - For a Maven jar, check its SHA-1 against the `.sha1` published beside it.
   - Record every file's SHA-256 in `lead.md`, and mark the file read-only.
   - Extract a `.zip` with Python's `zipfile` into a new directory of its own, refusing any member with an absolute path or `..`.
   - Run nothing from inside those directories: a jar goes on a classpath by its absolute path.
4. **Smoke test:** a Nashorn script, run as the Rules' Java line describes, loads the Orekit and Hipparchus classes M1 to M3 name, and prints Orekit's version.
   - **What it catches:** class files built for a newer Java, which fail as they load. It does not catch a call to an API newer than Java 8, which fails only when it runs: Orekit and Hipparchus compile with source and target 1.8 but no `release` flag (plan-verifier-C, READ). DEBRIS-C's M0 is the gate for that.
   - **What it executes:** loading those classes runs their static initialisers, which is downloaded code running on Logan's desktop. Approving rows 1 to 8 approves that.
5. **Book the agents' time in the TimeSheet** as `notice` windows (`--who cft-debris/<name>`), and book any run of 10 minutes or more an agent asks for, in the mode it needs.
6. **Dispatch** as in "Dispatch" below.

## The downloads

Sizes are the servers' own listings, READ (via WebFetch) on 2026-11-12, so "consistent with" until the download checks them.

| # | file | from (HTTPS unless marked) | size | integrity | licence | for |
|---|---|---|---|---|---|---|
| 1 | `orekit-13.1.9.jar`, with its `.sha1` | `https://repo1.maven.org/maven2/org/orekit/orekit/13.1.9/` | 8,538,135 bytes (`.sha1` 40) | SHA-1 from Maven Central | Apache-2.0 (READ, pom) | M1-M3 |
| 2 | `hipparchus-core-4.0.3.jar`, with its `.sha1` | `https://repo1.maven.org/maven2/org/hipparchus/hipparchus-core/4.0.3/` | 1,959,795 | the same | Apache-2.0 (BELIEVED) | M1-M3 |
| 3 | `hipparchus-geometry-4.0.3.jar`, with its `.sha1` | the same tree, `hipparchus-geometry/4.0.3/` | 276,264 | the same | the same | M1-M3 |
| 4 | `hipparchus-ode-4.0.3.jar`, with its `.sha1` | `hipparchus-ode/4.0.3/` | 282,008 | the same | the same | M1-M3 |
| 5 | `hipparchus-fitting-4.0.3.jar`, with its `.sha1` | `hipparchus-fitting/4.0.3/` | 31,076 | the same | the same | M1-M3 |
| 6 | `hipparchus-optim-4.0.3.jar`, with its `.sha1` | `hipparchus-optim/4.0.3/` | 228,802 | the same | the same | M1-M3 |
| 7 | `hipparchus-filtering-4.0.3.jar`, with its `.sha1` | `hipparchus-filtering/4.0.3/` | 31,650 | the same | the same | M1-M3 |
| 8 | `hipparchus-stat-4.0.3.jar`, with its `.sha1` | `hipparchus-stat/4.0.3/` | 222,980 | the same | the same | M1-M3 |
| 9 | `lnxp1900p2053.421` (DE421, binary) | `https://ssd.jpl.nasa.gov/ftp/eph/planets/Linux/de421/` | 13.3M | none published that the lead found; SHA-256 recorded | no terms found (DEBRIS-B, Q1) | M1b |
| 10 | `header.421` | the same | 8.2K | the same | the same | M1b |
| 11 | `testpo.421`, JPL's test points for DE421 | the same | 117.6K | the same | the same | M1b |
| 12 | Lasser et al.'s README and the files M1 needs: the TRF and CRF orbits, the TRF gravity accelerations, the third-body accelerations, and the gravity field file if the dataset carries one | `ftp://ftp.tugraz.at/outgoing/ITSG/COST-G/softwareComparison/` (FTP) | not reached: an FTP tree; listed in Phase 0 | none published; SHA-256 recorded | "freely accessible"; the article CC BY 4.0 | M1 |
| 13 | EIGEN-6C4, `.zip` or `.gfc`, only if row 12 lacks it | `https://icgem.gfz.de/getmodel/zip/7fd8fe44aa1518cd79ca84300aef4b41ddb2364aef9e82b7cdaabdb60a9053f1/EIGEN-6C4.zip` | not on the page; asked of the server in Phase 0 | none published; SHA-256 recorded | not on the page; DOI 10.5880/ICGEM.2015.1 | M1, M3 |
| 14 | a leap-second file in a format Orekit reads, only if M0's script-built UTC fails. Orekit's loaders take `UTC-TAI.history` or USNO's `tai-utc.dat`, not IERS's `Leap_Second.dat` (plan-verifier-C, READ (via WebFetch), Orekit's `UTCTAIHistoryFilesLoader` and `TimeScalesFactory`) | named when asked for | named when asked for | SHA-256 recorded | named when asked for | M0, M2 |

Rows 1 to 8 total 11,570,710 bytes, and rows 9 to 11 about 13.4 MB (COMPUTED from the listings). EIGEN-6C4 is complete to degree 2190 and ICGEM offers no truncated file (READ (via WebFetch)), so row 13 may be large; M1 needs only its first 180 degrees.

**What the integrity checks show:**
- A Maven jar's `.sha1` comes from the same server as the jar. So it shows the transfer is intact, not that the publisher signed the file.
- Maven Central also lists PGP signatures (`.asc`). Checking them needs the signers' public keys, which would be another download. Not done: a stated limit.

**Not requested:** orekit-data, whose GitLab page refused WebFetch behind bot protection, so its size and contents are unknown.
- The measurements are designed to run without it, but that is unproven until M0 runs. Plan-verifier-C found two places Orekit may reach for data on its own:
  - JB2008's UTC;
  - any Earth-fixed frame.
- M0 is the gate. A measurement that turns out to need orekit-data, or any other file, is a download request, never a workaround.

## Dispatch

Each agent's prompt is a dispatch note, its brief, and then, verbatim, this plan's sections "Dispatch", "The ledger", "Rules every brief carries" and "READY", written by a script from this file and checked after dispatch against the harness's transcript (as in round DEBRIS-B).

Each agent sends one test escalation as it starts:
- it writes `test escalation from <name>` in its own ledger file;
- it sends the same words to the lead (SendMessage to `main`);
- the lead replies "received" and records the round trip in `lead.md`.

The route worked for all three agents of round DEBRIS-B. If the lead has no test escalation from an agent within ten minutes of dispatching it, the lead reads that agent's ledger file, arms a watch on the ledger directory, and says so in `lead.md`.

## The ledger

The ledger is `C:\Users\logan\source\repos\cft-debris-ledger\`, as in round DEBRIS-B.

- **One file per author, append only:** `lead.md` continues; this round adds `DEBRIS-C.md` and `verifier-C.md`, which the lead creates with a header only. Correct an entry by appending beneath it, never by editing it.
- **Times:** every heading's time comes from `date`, never from memory.
- **Read it at three moments:** before starting; before resting anything on another study's number; before the final report.
- **Verifiers read `lead.md` only**, and the files it points them to. This keeps their independence from the work they check.
- **Escalation:** write the entry first, then message the lead (SendMessage to `main`). Wait for the answer to a question while working on what does not depend on it; never end your turn to wait.
- **When to write:** when an entry would change another agent's work or the lead's: an environment fact, a brief that turned out wrong, or a finding about a shared input, never progress. Every entry marks which claims were measured and which are believed.
- **When a pause is announced**, record where you are before you stop. On resuming, do a full read, check your outputs before trusting your memory of them, and say where you stopped.
- **Scratch:** each agent creates its own directory when it starts, `C:\Users\logan\source\repos\cft-debris-scratch\<name>\`. Read no other agent's scratch. Keep no secrets anywhere an agent is given.
- **The downloads:** `C:\Users\logan\source\repos\cft-debris-downloads\`, one directory per file, each file's SHA-256 in `lead.md`. Read-only for every agent.
- **What the lead writes in `lead.md`, every verifier reads.** It relays upstream facts there, and never writes a judgement of DEBRIS-C's work there before verifier-C has reported.
- **`tools\ias15_cft.exe`** is the port binary DEBRIS-A used (SHA-256 `9d5cb048ee63e609bad448237476443c651623a96d7fe5f0340fd8cd5d8aa048`). This round does not need it.

## Rules every brief carries

From Logan's standing rules (carried from cft-fp256 and cft-rebound, 2026-09 to 2026-11), canonical ParcelRound, and the rulings of round DEBRIS-B:

- **Read-only, except your own outputs and scratch.** cft-rebound, cft-fp256 and the TimeSheet are other sessions' live repositories. Read their files, and use `git -C <repo> log` or `show`. Never write in them, never run `git status` there, and never run a bare `git stash`. In the TimeSheet you may run `timesheet.py check` and `list`, which only read.
- **No downloads, installs or package managers.** This round's files are in the downloads folder above, with their SHA-256 in `lead.md`. Read them in place, or copy what you need into your scratch; never write, move or extract anything in the downloads folder. If another file would settle a question, ask the lead for it, giving its name, source URL, size, licence and purpose. Each file needs Logan's approval.
- **Reading the web: HTML pages only.**
  - WebFetch returns a model's summary of a page, not its bytes. A figure or quote taken through it is labelled "READ (via WebFetch)". It supports "consistent with", never "confirmed".
  - WebFetch saves any response that is not HTML to disk. So a URL ending in `.txt`, `.pdf`, `.csv`, `.zip`, `.bin`, `.jar` or `.gfc`, or in an FTP tree, is a download request, whatever it seems to hold.
  - Test-vector files are located and identified (URL, file, size, licence), never transcribed from a summary.
- **No GPU, WSL, card or box.** Take small measurements only, at the machine's natural load, and state the load beside every timing. Before every timing run, `C:\Users\logan\AppData\Local\Programs\Miniconda3\python.exe -I -B C:\Users\logan\source\repos\TimeSheet\timesheet.py check desktop --short` must print FREE; keep its output with the timing. The lead has booked your time as a `notice`. A run of 10 minutes or more goes to the lead first, who books it.
- **CPU budget** means the CPU time of the processes you start. For a single-threaded native run at natural load, its wall time is an acceptable stand-in, if you say that is what you used. A JVM is not single-threaded: its JIT and garbage collector add CPU beyond wall time.
  - So for a JVM, and wherever wall time is not a fair stand-in, report CPU from the process's cycle counter: `QueryProcessCycleTime` through Python's `ctypes`, divided by 2.5e9 cycles a second (BELIEVED, the part's base clock). Give `GetProcessTimes` beside it.
  - On this host `GetProcessTimes` under-reports a busy thread under load, by a factor of about 1.7 to 4 (MEASURED in round DEBRIS-C; `lead.md`, 18:31).
- **Long jobs:** run them through the Bash tool, in the foreground with a timeout of at most 600000 ms or with run_in_background. Never use nohup, and never end your turn while one of your jobs is running.
- **C:** put `C:\msys64\mingw64\bin` first on PATH before any compile, and check that `gcc -dumpmachine` prints `x86_64-w64-mingw32`. In this Git Bash a bare `gcc` is the 32-bit i686 compiler.
- **Java:** the host has a Java 8 runtime only, `C:\Program Files\Java\jre-1.8\bin\`, with `java.exe` and Nashorn's `jjs.exe`, and no `javac`.
  - Run Nashorn scripts through `java` itself:
    `"C:/Program Files/Java/jre-1.8/bin/java.exe" -cp "<the jars, ;-separated, absolute paths in the downloads folder>" jdk.nashorn.tools.Shell <script.js>`.
  - `jjs -cp` and `CLASSPATH` both fail here (MEASURED by the lead in Phase 0, `lead.md`).
  - Pass JVM options straight to `java`, for example `-Xint` or `-XX:TieredStopAtLevel=1`.
  - Nashorn here is ES5. Use `var` and `function`: `let` is a syntax error and an arrow function crashes the compiler (plan-verifier-C, MEASURED).
  - `new (Java.extend(SomeInterface))({...})` implements a Java interface, and `java.lang.Double.doubleToRawLongBits` gives a double's bits (the same, MEASURED).
- **Python:** `C:\Users\logan\AppData\Local\Programs\Miniconda3\python.exe -I -B`.
- **Processes and files:** kill only processes you started, and only by PID. Delete only what you made, and never through a computed path.
- **Earlier studies' records are read-only.** Copy what you run (DEBRIS-A's scripts, DEBRIS-B's `q2\q2bench.c` and the rest) into your scratch or your own output folder. Before your report, check: `sha256sum -c SHA256SUMS` run from `studies\` shows 32 OK; `find studies/debris-a -type f | wc -l` gives 29; `sha256sum -c MANIFEST.sha256` run from `studies\debris-b\` shows 54 OK; and there is no `__pycache__` anywhere under `studies\`.
- **Host traps:**
  - MSYS `.exe` transparency: writing a file `X` beside an existing `X.exe` writes to `X.exe`.
  - Passing a script to bash from Python with `text=True` turns every newline into CR+LF.
  - In the Bash tool, a doubled backslash reaches the shell as one, inside a heredoc too. Write any script that contains backslashes with the Write tool, not through the shell, and write Windows paths in commands with forward slashes.
  - Never start a process under `pythonw`, or detached.
- **No helper agents.**
- **Your final message is your report.** Its word limit is in your brief. If the harness refuses the write of a document your brief names, your final message is that document followed by the report, and the word limit then applies to the report alone.
- **Before you report**, stop any background work you started. End with what you did not do, and with anything your brief got wrong.

## READY, stated before the first pass

READY applies to DEBRIS-C and to every verifier's verdict. Every load-bearing claim must rest on one of:
- a measurement, with its command and output;
- a fetched source, cited by URL;
- arithmetic from labelled inputs.

Otherwise it is stated as a limit, in terms of the behaviour it concedes. A claim's domain and quantifier are claims, and so is a figure's definition. A number carried over from an earlier study keeps its definition, or it is re-measured.

**From round DEBRIS-B:**
- **Every control states its pass and fail criteria before the data, and the code asserts them.** A control that fails as specified is reported as failed, whatever replaces it.
- **Every agreement claim states its tolerance before the data.** Two counts or two vectors "agree" only within a stated tolerance, or to the bit.
- **Every log names the SHA-256 of the script that wrote it**, and the criterion that script asserted. Then whoever checks the log can show which criterion was in force when the data was taken.
  - Keep every version of a script that wrote a log, under a name carrying the first 12 hex digits of its hash.
  - Never overwrite a log: number each run's log.
  - The manifest lists every version, so a criterion changed after its data leaves both versions on the record.

A verifier may reuse a run instead of re-running it only when all three of these hold:
- someone other than the author of the work made the run;
- its inputs are identical, file hashes included;
- the verifier re-runs from clean whatever it doubts.

Only a wrong answer sends work back: a false claim, or a measurement or check that cannot fail. Everything else is a note the lead records, and a sentence that claims too much is narrowed at the merge.
- **Loop cap (Logan, 2026-10-15, carried through the lead's memory):** after three NOT READYs for narrowing reasons, the next pass blocks only on wrong answers.
- **Threat model (Logan, 2026-10-02):** each verifier's brief states one, and findings outside it do not reopen the loop.

## Logan's decisions (each default stands unless changed)

1. **Models:** Opus for DEBRIS-C, Sonnet for verifier-C, Haiku for a merge-check of any narrowing.
2. **Metadata requests by the lead, saving nothing:** list Lasser et al.'s FTP directory, print its `00README_simulation.txt` to the terminal, and ask ICGEM's server for EIGEN-6C4's file sizes. Default: yes.
3. **Downloads:**
   - Rows 1 to 11 of "The downloads" now.
   - Rows 12 and 13 asked for by name and size after Phase 0's listing.
   - Row 14 only if M0 needs it.
   - Approving rows 1 to 8 approves running that code, in the smoke test and in M0 to M3.
   - Default: approve rows 1 to 11.
4. **A second machine for M3:** none, so M3 compares JVM modes on this desktop only. The alternative is a machine Logan names, with how it is reached and whether it has Java. Default: none.
5. **Budgets:** DEBRIS-C 4 hours of wall time and 30 CPU-minutes; verifier-C 2 hours and 15 CPU-minutes; merge-check 20 minutes.
6. **Java:** the host's Java 8 runtime and `jjs` only.
   - A compiler (an ECJ jar that runs on Java 8) is the alternative for scripting, but it cannot help if Orekit needs a newer runtime.
   - If M0 shows that it does, the Orekit legs of M1 to M3 stop. The custom legs and M4 go on, and the lead asks Logan about a named, sized newer runtime as a separate download.
   - Default: no compiler, and no newer runtime unless M0 shows the need.
7. **Outputs** go in `cft-debris\studies\`.

## Not in this round

- Building the propagator, or any repository change.
- orekit-data, and every run that needs it.
- The rotation layer against Lasser et al.'s quaternions. It needs the IERS series tables and EOP as files: a later round.
- Tides, relativity and dealiasing. At debris accuracy they are below every uncertainty DEBRIS-B measured (BELIEVED).
- Running the hindcast. M4 designs it.
- GMAT, heyoka and cascade; any GPU or tile run.
- Any source that needs an account: Earthdata (CDDIS), Space-Track, DISCOSweb.
- The decision itself, which is Logan's.

---

## Brief: DEBRIS-C

You are study parcel **DEBRIS-C** in cft-debris, a project for space-debris tracking and simulation. Its folder, `C:\Users\logan\source\repos\cft-debris`, is not a git repository. This is a study: nothing is built and no repository changes.

**Budget:** 4 hours of wall time and 30 CPU-minutes. Message the lead before you pass either.

**Start here:**
1. This plan, `C:\Users\logan\source\repos\cft-debris\studies\DEBRIS-C-plan.md`: the question in Logan's words, what each measurement decides, and the downloads.
2. DEBRIS-B, `studies\DEBRIS-B-custom-model.md` (verified, narrowed at the merge), with its records in `studies\debris-b\`, and verifier-B's report, `studies\DEBRIS-B-verifier-B-report.md`.
3. `lead.md` in the ledger: Phase 0's listings, the files' SHA-256, and the smoke test.

**Your job.** Run the gate M0, then answer M1 to M4 below for Logan's decision.
- **Where it goes:** the study in `studies\DEBRIS-C-measurements.md`; your scripts, logs and records in `studies\debris-c\`, with a `MANIFEST.sha256` over them.
- **Order:** a short answer, then M1 to M4, then what they mean for build, adopt and hybrid, then the measurements with their commands, then the sources. Aim for 6 to 10 pages.
- **Labels:** MEASURED, COMPUTED, READ or BELIEVED on every claim, as DEBRIS-B does.
- **Criteria first:** for every comparison and every control, write its tolerance or its pass and fail criteria into your script before you run it, and assert them in code. Every log names the SHA-256 of the script that wrote it. Report a control that fails as failed, whatever you do next.

**M0. The gate: can Orekit run here without orekit-data?** Before M1 to M3, build every Orekit object they need in one `jjs` script, and call each once:
- the EIGEN-6C4 gravity provider, read from the downloads folder, and `HolmesFeatherstoneAttractionModel` on the body frame below;
- the body frame: a frame turning uniformly about GCRF's z axis at 7.292115e-5 rad/s, built in the script as a `TransformProvider`;
- **UTC,** built in the script through `TimeScalesFactory.addUTCTAIOffsetsLoader`, with a loader implemented in the script that returns TAI-UTC = 33 s from 2006-01-01. READ that value from IERS Bulletin C's HTML pages.
  - Then build `JB2008` through its constructor that takes the caller's UTC.
  - Every epoch in M0 to M3 is on 2008-07-03, Lasser et al.'s day, inside that offset's validity.
- `NRLMSISE00` with script-implemented inputs, a `OneAxisEllipsoid` on the body frame, and the Sun from DE421 through Orekit's JPL loader.
  - Register Orekit's `DirectoryCrawler` on the DE421 binary's own download directory, which holds that file only, and likewise on the EIGEN-6C4 file's.
  - Never register it on the downloads root, where Orekit's loaders would try every file;
- one `NumericalPropagator` step with that gravity and drag.

**Criterion:** every call returns finite values.

**Stop rules:**
- **A linkage error** (`NoSuchMethodError`, `UnsupportedClassVersionError` or another) means this Java 8 runtime cannot run that path. Stop the Orekit legs that need it, write it in your ledger file, and message the lead (decision 6).
- **An error that asks for a data file** means a download. Stop that leg, and ask the lead for the named file (row 14, for leap seconds).
- Either way, the custom legs of M1 and M3, and M4, go on.

**M1. Force kernels held to published authorities.**

*M1a, the gravity field (layer 3).*

**Conventions first.** Before any comparison, establish these from Lasser et al.'s README and the coefficient file's header, and write them into your script:
- the coefficient file;
- GM and the reference radius;
- the tide system;
- whether the accelerations include degree 0 (the central term) and degree 1;
- whether EIGEN-6C4 carries time-variable terms, and how they evaluate on 3 July 2008.

For Orekit, establish from its documentation whether `HolmesFeatherstoneAttractionModel` includes the central term, then add or subtract it so that all three compare like with like. A convention found wrong after the data is a failed first comparison. Report it as failed, with the corrected re-run beside it, and never loosen the tolerance instead.

Then compute the gravity acceleration at every epoch of the TRF orbit with:
- **a custom binary64 kernel in C**, derived from a copy of DEBRIS-B's `q2\q2bench.c` gravity recursion and reading the real EIGEN-6C4 coefficients. At degree 180 an unnormalised recursion overflows or loses accuracy: use a normalised one, say which, and say what you changed from DEBRIS-B's kernel;
- **Orekit's `HolmesFeatherstoneAttractionModel`**, driven from `jjs`, on the same coefficient file.

Compare each with Lasser et al.'s TRF gravity accelerations, and the two with each other: the maximum and RMS of |Δa| over the day.
- **Tolerance:** state it before the run, with its basis. 1e-11 m/s² is the threshold the COST-G packages met for each force (READ); if you choose another figure, say why.
- **Negative control:** a planted error whose expected effect, COMPUTED first, is at least 10 times the tolerance, with an assertion that the comparison reports it.
  - Truncating at degree 179 is too close. The degree-180 signal at 466 km is about 3e-11 m/s² by the Kaula rule (plan-verifier-C, COMPUTED), only three times a 1e-11 tolerance.
  - One changed coefficient of degree 180 gives about 1.5e-12, which is below the tolerance.
  - So plant a truncation at a degree D chosen so that the omitted degrees' signal is at least 10 times the tolerance (COMPUTED first). That exercises the recursion's high degrees. A change in C̄20 would test degree 2 only.
- **The claim's domain:** a tolerance near the top degrees' own signal cannot resolve those degrees. Say which degrees the comparison actually tests.
- **What agreement proves, and what it does not:** Lasser et al.'s values come from GROOPS and were published to hold software to (the authority). The custom kernel agreeing with Orekit is two of ours agreeing, not an authority (HonestFramework METHOD §1). All three share the coefficient file, so no comparison here tests the coefficients themselves.

*M1b, the Sun and Moon (layer 4).*
- Read DE421 (rows 9 and 10) with a small custom reader of your own, and with Orekit's JPL ephemeris reader. Hold both to JPL's `testpo.421`.
  - **The tolerance:** JPL's own test keeps its tolerance in its Fortran program and `.txt` files. Those are outside the HTML-only rule, and the approved README does not give it.
  - So state a tolerance before the run, with its basis, for example the precision `testpo.421` prints, unless an HTML page gives JPL's figure.
- If Lasser et al.'s listing has third-body accelerations, compute them on their CRF orbit and compare, with the tolerance stated first.
- Negative control: a planted error in the reader, for example the Chebyshev time argument shifted by one sub-interval, must fail the `testpo` check.

**M2. The density models' cost.** DEBRIS-B left it as a parameter, with a break-even of 1.85 µs a call at degree 20.
- Time Orekit's `NRLMSISE00` and `JB2008` per call at binary64 on this host, from `jjs`, at LEO points, with synthetic, constant space-weather inputs (implement the input interfaces in the script). State the inputs.
- Time Orekit's `HolmesFeatherstoneAttractionModel` per call at degrees 8, 20, 36 and 70. Hold it against DEBRIS-B's C kernel at the same degrees, and label the ratio as language and algorithm together.
- **Control 1, the overhead:** measure Nashorn's per-call overhead with a trivial Java call in the same loop, and report it beside every figure.
  - The trivial call's result goes into the checksum too. Even so, the JIT may fold it, so report the overhead as a lower bound.
  - Every timed loop folds every output into a printed checksum.
  - A loop with the model call removed must time at least 10 times faster.
- **Control 2, a fast wrong answer:** NRLMSISE00's density at a few inputs against published reference values, asserted to a stated tolerance. READ the values, for example from Orekit's own test sources through GitHub's HTML view, and cite them. If none are found for JB2008, state that as a limit.
- **Then COMPUTE** DEBRIS-B's LEO catalogue-year table again, with the measured density cost added, and say which figures come from Java.

**M3. Is Orekit bit-reproducible?**
- Propagate one LEO object for one day with Orekit's `NumericalPropagator` (state the integrator and its tolerances), EIGEN-6C4 gravity to degree 20 and NRLMSISE00 drag with constant inputs, on M0's body frame. That frame needs no EOP data; say why that is enough for this question.
- Record the final state's bits, as hexadecimal doubles, and a SHA-256 over every step's state.
- **Runs:** the default JIT three times; `-Xint` once; `-XX:TieredStopAtLevel=1` once. Add others if you can say what each would catch.
- **Criterion, before the data:** bit-identical across every run, or the first step at which any run differs, with its size.
- **Negative control:** the same run with one input changed by one ulp must change the hash. Say at which step it first differs.
- **The custom side:** build the M1a C kernel twice, with `-O2` and with `-O2 -march=native -ffp-contract=fast`, and hash its outputs over Lasser et al.'s day. Fused multiply-adds are the usual source of C-side differences.
  - Say whether this CPU has them (MEASURED, from the compiler's predefined macros).
  - Show that the second build really contains them: count the FMA instructions in `objdump -d` of each build (`objdump` is in `C:\msys64\mingw64\bin`).
  - **Control:** a planted one-ulp change in the kernel's output must change the hash.
- **A second machine** only if Logan's decision 4 names one.
- **What it shows:** whether one JVM on one machine reproduces itself across compilation modes, and whether the C kernel's bits depend on fused multiply-adds.
- **What it does not show:** reproducibility across JVM versions, threads or architectures, unless decision 4 adds a machine.
- **Why a pass settles little:** a single-threaded, pure-Java run is expected to reproduce itself (BELIEVED, plan-verifier-C). So a pass here weakens the differentiator without settling it.

**M4. The covariance-realism hindcast, designed.** Candidate 2 of DEBRIS-B, uncertainty carried with every prediction with a refusal past the point where it can be bounded, needs truth for debris-like objects.
- **Objects:** which defunct objects have independent truth, for example ILRS laser ranging to ENVISAT or TOPEX/Poseidon. READ which are tracked, since when and how often.
- **Truth data:** where ILRS normal points are served, whether an account is needed (CDDIS needs Earthdata; is the EUROLAS data centre open?), the format, and the volume per object-month. Locate and identify; download nothing.
- **Predictions to test:** a TLE-based one (SGP4) and an orbit-determination one (Orekit's batch least squares or Kalman filter), each with its covariance. Say where each covariance comes from.
- **The test:** the fraction of truth points inside the predicted k-sigma region against its chi-squared expectation, and a refusal rule that is itself tested. State the pass and fail criteria now.
- **What it would take here:** the downloads, the credentials and whose they are, the CPU (COMPUTED from DEBRIS-B's and M2's costs), and the smallest pilot that would show the protocol works.

**Then lay out what M1 to M4 mean** for build, adopt and hybrid. Label judgement BELIEVED. Where the evidence does not decide, make no recommendation.

**Instruments on this host** (the lead checked them on 2026-11-12):
- **Java:** see Rules. Orekit and Hipparchus as downloaded in Phase 0.
- **Python** (see Rules): rebound 5.1.1, numpy 2.2.6, mpmath 1.3.0 and gmpy2 2.2.1.
- **C** (see Rules): gcc 16.1.0 (MSYS2 mingw64), with libquadmath.
- **The web:** WebSearch and WebFetch, HTML pages only.

**Do not:**
- write outside `studies\DEBRIS-C-measurements.md`, `studies\debris-c\` and your scratch;
- weaken a claim's label, or a criterion, to make it pass;
- fix anything in DEBRIS-A or DEBRIS-B. Report it instead.

**Report:** your final message, under 900 words:
- the short answer;
- M0's result, and every leg it stopped;
- M1 to M4, each with its most load-bearing evidence, its criterion and whether it passed;
- every control that failed, and what you did next;
- anything you could not settle;
- what you did not do;
- anything this brief got wrong.

---

## Brief: verifier-C (completed when DEBRIS-C reports)

You are **verifier-C**: a verifier, not an author. Try to disconfirm study DEBRIS-C, and report. Fix nothing. Budget: 2 hours of wall time and 15 CPU-minutes. The lead books your time as a `notice` in the TimeSheet.

**Threat model.**
- **In scope:** numbers that do not reproduce from DEBRIS-C's scripts; a summary, table or report that misquotes its records; READ claims the cited source does not support; a measurement or control that could not fail, or whose criterion was set after the data; an agreement claimed without its tolerance; a claim whose domain or quantifier reaches past its evidence; a figure carried over from DEBRIS-A or DEBRIS-B whose definition changed without saying so.
- **Out of scope:** re-deciding build, adopt or hybrid, which is Logan's decision, and physics outside the study's stated models.

The attack list is finished from DEBRIS-C's own content, and starts with:
1. Re-run M1's comparisons from clean, with the downloaded files checked against their SHA-256 in `lead.md`, including both planted-error controls.
2. Re-run M2's timings and both controls, at the load you state.
3. Re-run M3 in at least two JVM modes, and its one-ulp control.
4. Fetch every load-bearing READ claim (HTML pages only), recording the route and the response for every "not found".
   - **Positive control:** first fetch one cited page you expect to hold its claim, to show that your route reaches content.
5. Redo every COMPUTED figure.
6. Hold the summary and the report against the tables, domain and quantifier included.
7. Check that every criterion was written before its data. Each log names the SHA-256 of the script that wrote it: check that hash against the script, and that the criterion is in that version.
   - **Negative control:** a copy of one script with its criterion changed must fail your check.
8. Check the lead's rulings in `lead.md`, and this plan's premises.
9. Anything else.

**Report:** your final message, under 1,200 words.
- For each item: the commands you ran, what you observed, and a verdict (confirmed, defect, or not determined).
- Every defect needs a concrete failure scenario. "Found nothing" is an acceptable answer.
- End with what you did not do, and anything this brief got wrong.

---

## What round DEBRIS-B taught, applied here

| lesson (round DEBRIS-B) | here |
|---|---|
| A positive control redefined after it failed was reported as passing | Criteria before the data, asserted in code; a failed control is reported as failed (READY) |
| The overlap's "one is false" assumed counts are properties of the setup | Every agreement states its tolerance before the data (READY) |
| WebFetch saved two files without approval | HTML pages only (Rules); every file is named, sized, approved and checksummed in Phase 0, before dispatch |
| The tile question went to one lead when the records were another's | M1's authorities are named with their owners; questions about Orekit go to its published sources, not to a peer |
| A verifier's two hours of short runs had no way to show their load | The TimeSheet's `notice` mode, booked by the lead for each agent |
| Sentences that claimed too much reached the merge | They are narrowed at the merge, and the narrowing goes past merge-check |

## What changed from draft 1 (plan-verifier-C's findings, answered)

| finding | answer |
|---|---|
| **Defect 1.** The smoke test only loads classes, but Orekit compiled with source and target 1.8 and no `release` flag can still call a newer API and fail only when that call runs; and there was no branch for a failure | The smoke test says what it catches and what it cannot. M0 is a gate that runs every Orekit path M1 to M3 use, with stop rules. Decision 6 gives the branch: the Orekit legs stop, the custom legs and M4 go on, and a newer runtime is a separate named download |
| **Defect 2.** "orekit-data not needed" was unproven: JB2008 takes its UTC from the default data context, leap seconds need a file, and gravity and drag need a rotating body frame that was not named | M0 builds UTC in the script and uses JB2008's constructor that takes the caller's UTC. It names the body frame: a uniform rotation built as a `TransformProvider`. Row 14 adds IERS `Leap_Second.dat` if M0 needs it. A need for any file is a download request |
| **Defect 3.** M1a's second planted error, one changed degree-180 coefficient, gives about 1.5e-12 m/s², below the tolerance, so it would pass silently | Every planted error's effect is COMPUTED first and must be at least 10 times the tolerance. The brief says which examples are too small, and requires the study to say which degrees the comparison actually tests |
| **Defect 4.** 1e-11 m/s² is a threshold the packages met, not a measured agreement; whether the central term is included, the tide system and any time-variable terms were not settled | The basis is restated. The conventions are established and written into the script before the comparison. A convention found wrong after the data is a failed comparison, reported as failed, never a looser tolerance |
| **Defect 5.** verifier-C's checks had no controls of their own, and its report spec omitted two of Logan's must-haves | A positive control for its fetch route and a negative control for its criteria check: every log names its script's SHA-256 (READY). The report ends with what was not done and what the brief got wrong |
| **Note 1.** M3 overreached: a single-threaded, pure-Java run is expected to reproduce itself, and the C side was untested | The decision table and M3 are narrowed. The C kernel is now built with and without fused multiply-adds |
| **Note 2.** The JIT can fold the trivial call that measures Nashorn's overhead | Its result goes into the checksum, and the overhead is reported as a lower bound |
| **Note 3.** Nashorn on 8u411 is ES5 only | It is in the Rules, with what does work |
| **Note 4.** A `.sha1` from the same server shows integrity, not authorship; the smoke test runs downloaded code | Both are stated, in "The downloads" and in decision 3 |
| **Note 5.** A JVM's CPU exceeds its wall time | The Rules require process counters for a JVM |
| **Note 6.** JPL's test tolerance sits in a `.txt` or Fortran file, which the HTML-only rule forbids | The approved JPL README is named as a source; otherwise the tolerance is stated before the run |

## What changed from draft 2 (the scoped re-check's findings)

| finding | answer |
|---|---|
| **Note 6, not answered:** the approved JPL README does not give `testeph`'s tolerance; `grep` finds no `testpo`, `testeph` or tolerance in it | The claim is withdrawn, and the lead confirmed the `grep`. M1b states its tolerance before the run, with its basis, unless an HTML page gives JPL's figure. The lead's slip 2 below |
| **Defect 2, partly answered; new defect 1:** row 14's IERS `Leap_Second.dat` is a format Orekit's loaders do not read; M0's UTC route named no mechanism; "through 2008" breaks for any other epoch | Row 14 is now a file in a format Orekit reads, named only if it is needed. M0 builds UTC through `TimeScalesFactory.addUTCTAIOffsetsLoader`, with a loader written in the script. Every epoch is pinned to 2008-07-03 |
| **New defect 2:** a criterion edited in place, with its log overwritten, would carry the new hash and pass the check | Every script version that wrote a log is kept under its hash, logs are numbered and never overwritten, and the manifest lists every version |
| **New note 3:** M3's custom leg had no control on its hash, and nothing showed that the second build used fused multiply-adds | A planted one-ulp change must change the hash, and `objdump -d` counts the FMA instructions in each build |
| **New note 4:** Orekit's JPL loader needs a directory, and would try every file it finds there | `DirectoryCrawler` goes on the file's own download directory, which holds that file alone, never on the downloads root |
| **New note 5:** a change in C̄20 tests degree 2 only, not the high-degree recursion | The control is a truncation chosen to clear the 10x margin, which exercises the high degrees |

## The lead's slips so far

Round DEBRIS-B's are in `studies\DEBRIS-B-round-record.md`.

1. **A path check that checked nothing.** Draft 1's first mechanical check extracted no paths, yet still printed its controls as passing.
   - The harness collapsed the regex's doubled backslashes inside a heredoc.
   - The check had no control on its own extraction.
   - It was rewritten as a file, with a control that the extraction finds at least ten paths, a known one among them. That control was shown to fire on a planted copy.
   - Round DEBRIS-B's slip 2 was the same failure.
2. **A source named without opening it.** Draft 2 named JPL's README as the route to the test tolerance. It does not contain one: plan-verifier-C's `grep` found none, and the lead's confirmed it. The lead had read about the file, not the file.
