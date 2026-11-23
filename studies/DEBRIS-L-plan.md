# DEBRIS-L: a first visual presentation of the project (the plan)

The plan of parcel DEBRIS-L in cft-debris, written by the project's lead. **Draft 2, 2026-11-23.** Logan's word to dispatch is its approval. The lead put draft 1 past plan-verifier-L, as the method has every plan; draft 2 answers its findings, in "What changed from draft 1". The parcel is dispatched with every decision at its default. Logan may change any of them.

Labels as in earlier rounds: MEASURED (a run's own output, with its log), COMPUTED, READ (a named record, with its place), ESTIMATE (with its basis and range), BELIEVED, INFERRED.

## The question, in Logan's words

- **Logan, 2026-11-23 at 13:14, in chat:** "Approved. Along with that, dispatch a small parcel for visualization generation for the project, using the data to create screenshots, videos or live displays if desired. Doesn't have to be anything fancy to start, just something to give the project a visual presentation surface"
- **His goal for the project** (2026-11-12): "a simulation capable of realtime (or slightly faster) simulation on a consumer card, so a 24x7 sim could run on a local box here for long run tests, validating itself with the open datasets update intervals, scaling tracked objects as the main scaling parameter presumably. High performance cards like the MI300X could then be used for higher density or faster/concurrent runs"

## What DEBRIS-L is for

A first presentation surface for the project: pictures, a short video and a page that show what the project simulates and what it has measured. It is small, and it builds nothing a later parcel must keep. It answers no physics question, and it changes no earlier record.

It makes four things:
1. **Screenshots of the tracked population** at DEBRIS-H's start time T_s: the 2,688 objects of DEBRIS-H's four groups around the Earth, in two views, coloured by group.
2. **A video** of the same population over the span of decision 3, propagated by M1 itself.
3. **A live display:** one self-contained HTML page that plays the same frames in a browser, with play, pause and a group filter, and no network access.
4. **A results panel:** charts of the project's measured figures, read from the committed records of rounds DEBRIS-G to DEBRIS-K.

## What DEBRIS-L starts from

- **The population** (READ, the ledger's `debris-h\box\r2\seed\`):
  - `seed1.txt` holds 2,688 objects at T_s (2026-11-18 22:50:00 TDB), each a state x, y, z, vx, vy, vz in metres and metres a second in M1's inertial frame, with bc and cram, as C99 hex floats;
  - `seed_meta.tsv` gives each object's group: 1,991 in `fengyun-1c-debris`, 582 in `cosmos-2251-debris`, 109 in `iridium-33-debris` and 6 in `stations` (COMPUTED by the lead from the file);
  - they are per-object data, derived from CelesTrak's GP data, and stay in the ledger.
- **M1** (`src\`, at `a3beff9`): `tests\m1f.c`'s mode `prop` reads `OBJ` and `T` lines, an object's state at an origin and its target times on the 15 s grid, and writes a `P` line with each object's state at each target (READ, `tests\m1f.c`, `read_objs` and `mode_prop`). At a target equal to the origin it writes the input state, converted (READ, the same; plan-verifier-L read it so).
- **Building M1:** DEBRIS-K's `tests\k_build.py` builds libcft and M1 through DEBRIS-F's `tests\build_f.sh` in a scratch it is given, with `--archive`, `--scratch`, `--logs`, `--keep` and `--cpu` required. Its archive is the ledger's `tools\cft-fp256-0aa997a3.tar`, whose SHA-256, `e01003cc0b984864b065ce3395f56fa189451fcb0cd98cce5b11b3c17a9c29b8`, it checks by default. It carries the `--force-local` fix for MSYS tar. DEBRIS-K's `tests\k_pilot.py`, `m1f_prop`, writes `prop`'s input and reads its output. Both may be reused.
- **The frame table** M1's `prop` takes: DEBRIS-H's `frame_h0.bin`, in the ledger's `debris-h\`, as DEBRIS-K ran it.
- **M1's speed** (MEASURED in DEBRIS-G's G4, `studies\DEBRIS-G-build.md`): 1,291,561 object-seconds a second at native64 on one box worker, with 64 lanes. So 2,688 objects for 3 hours, 29 million object-seconds, take about 23 s of one core (COMPUTED). `prop` runs one object at a time, so it is probably slower; at five times slower it takes about 2 CPU-minutes (ESTIMATE, a factor of 1 to 5).
- **The project's measured figures,** all in committed records: DEBRIS-G's capacities by kind (`studies\DEBRIS-G-build.md`, G4), DEBRIS-I's rates on the box (`studies\DEBRIS-I-build.md`, section 5), DEBRIS-H's checks against CelesTrak (`studies\DEBRIS-H-build.md`) and DEBRIS-K's pilot medians (`studies\DEBRIS-K-study.md`, Q3).
- **The desktop's tools** (MEASURED by the lead, 2026-11-23):
  - Python has numpy 2.2.6 and mpmath 1.3.0, but no matplotlib, Pillow, imageio or scipy. Installs are not allowed, so DEBRIS-L draws with numpy and writes PNG files itself, with `zlib` and `struct` from the standard library.
  - ffmpeg 9.0.2 is installed on the desktop by WinGet. Its path, a user path, is in the dispatch note, not in the repository. plan-verifier-L made an MP4 with its libx264 encoder from 30 frames written by a writer of `zlib` and `struct` (its probe, deleted after).

## The design, and why

**Everything is drawn from the project's own data, and nothing is invented.** Positions come from DEBRIS-H's seed and from M1's propagation of it; numbers on the charts come from committed records, each traced to its line.

**The views are inertial,** as M1's states are: one from above the North Pole, onto the equatorial plane, and one from the equatorial plane, edge-on. The Earth is drawn as a disc of radius 6,378.137 km. No coastline or map is drawn, since that would be third-party data.

**Text is drawn from a small bitmap font written in DEBRIS-L's own code:** digits, capital letters and a few marks, each glyph a few rows of bits. No font file is read or shipped. The HTML page uses the browser's own text. If time runs short, frames carry the time in digits alone.

**The video:**
- **Frames:** 181 frames, one every interval of decision 3 from T_s: at its default, one every 60 s for 3 hours, with k = 0 to 180. Each is 1,280 × 720 pixels.
- **States:** M1 at native64, through `m1f prop` with targets T_s + Δ k, Δ the interval, and DEBRIS-H's frame table, as DEBRIS-K ran it. `prop`'s output, about 150 MB of text, stays in DEBRIS-L's scratch.
- **Units:** M1's positions are in metres. Drawing and the display's data use kilometres. The display's data are rounded to 1 km and stored as 16-bit integers; every coordinate's size is under 10,000 km for this population, and the writer asserts it.
- **Assembly:** ffmpeg turns the frames into an MP4 at 30 frames a second, about 6 s long, with libx264 and `-threads 2`.
- **Labels:** the time on each frame, and a caption saying the positions are M1's propagation of DEBRIS-H's seed, not observations.

**The live display:**
- One HTML file, with its JavaScript and data inline and no network access.
- It holds the 181 frames' positions: 181 × 2,688 × 3 values of 2 bytes, about 2.9 MB, or 3.9 MB in base64 (COMPUTED).
- It draws them on a canvas, with play, pause, speed, a view switch and a toggle for each group.

**The results panel:** four PNG charts:
- **DEBRIS-G:** real-time capacity at 36 threads, by number kind.
- **DEBRIS-I:** the program's rate against M1's at the same forces, by format and workers.
- **DEBRIS-H:** the checks' median miss by horizon.
- **DEBRIS-K:** the pilot's median misses by variant.

Every plotted number is listed in a table beside the charts, with its source file and line. Numbers in the table keep their thousands commas, as their sources print them.

**Where things go** (decision 2):
- the code goes in `tests\l_*.py` (MIT);
- the results panel, its table and the gates' aggregate logs go in `studies\debris-l\` with a manifest, since they hold only aggregates of committed records and counts;
- the screenshots, the video, the live display, the gates' per-object detail and the display's data go in the ledger's `debris-l\`, since they hold positions derived from CelesTrak's data. The lead shows them to Logan, who decides where they may be published.

**What the repository's logs may say:** counts, SHA-256 values, and seed indices without any catalogue number, state, position or pixel of an object. Tool paths are written `<python>`, `<ffmpeg>`, `<msys>` and `<root>`. A log that names more goes to the ledger, with a copy for the repository that does not.

## The gates

Every criterion is fixed here, before the data, and the code asserts it.

- **V0, the PNG writer:**
  - A test image written by DEBRIS-L's writer and read back by a reader of its own gives the same pixels, and the CRC of every chunk checks.
  - ffmpeg reads it: `ffmpeg -i` exits 1 when no output is named, so the gate reads its stderr for the stream line naming `png` and the image's width and height.
  - **Control:** one byte flipped in the image data must fail the CRC check.
- **V1, the positions are the data's:**
  - For 20 objects drawn with `random.Random(20261123)`, each object drawn alone in a test image lands on the pixel its source state projects to, computed by a separate function written for this check.
  - **Control:** a pair of objects, checked before the swap to project to different pixels, swapped: each must land on the other's pixel.
- **V2, the propagation is M1's:**
  - (a) `m1f prop`'s state at its first target, T_s, equals `seed1.txt`'s state for every object, bit for bit; the frame times are T_s + Δ k exactly; the run's log names `m1f`'s SHA-256 and the frame table's.
  - (b) For 20 objects and 5 frames with k ≥ 1, drawn with `random.Random(20261124)`, the frame's drawn position and the display's decoded position equal the `P` line's, within the rounding stated (0.5 km for the display's data). Every value is finite.
  - **Control:** an input with one object's x changed by one unit in the last place must change that object's states at k ≥ 1, and no other object's.
- **V3, the numbers are the records', and the charts the numbers':**
  - (a) Every number in the panel's table equals its source line's, by a script that reads each source. **Control:** one planted wrong number must fail.
  - (b) Each chart's drawn bars or points match the table: a separate function computes each bar's extent in pixels from the table, and the gate compares it with the image. **Control:** a chart drawn from a table with one value doubled must fail.
- **V4, the repository stays clean:**
  - The scope is DEBRIS-L's own files: `tests\l_*.py` and `studies\debris-l\`.
  - The scan is DEBRIS-L's, adapted from the ledger's `tools\scan-k\scan_debris_k.py`:
    - its file rule is DEBRIS-L's own;
    - PNG files are allowed under `studies\debris-l\panel\` only;
    - its catalogue-number rule exempts digits inside hexadecimal tokens of 12 or more characters, as the lead's `tools\scan-i\scan_debris_i.py` does;
    - its patterns include the user paths and `AppData`.
  - It runs on a trial log before the real runs, and again at the end.
  - **Control:** its patterns must hit their plants.

## Logan's decisions (each default stands unless changed)

1. **Models:**
   - (a) **Sonnet for DEBRIS-L, Haiku for verifier-L,** as befits a small parcel;
   - (b) Opus for DEBRIS-L and Sonnet for verifier-L.
   - Default: (a).
2. **Where the pictures of the population go:**
   - (a) the ledger only, shown to Logan by the lead; the repository gets the code and the results panel;
   - (b) also the repository, as the README's picture;
   - (c) also a private claude.ai page for the live display, published by the lead.
   - Default: (a). Logan may choose (b) or (c) after he has seen them.
3. **The video's span:** 181 frames either way:
   - (a) 3 hours at a frame a minute (Δ = 60 s);
   - (b) 24 hours at a frame every 8 minutes (Δ = 480 s), about 8 times the CPU of (a).
   - Default: (a).
4. **Budget:**
   - 3 hours of wall time and 20 CPU-minutes on the desktop, at most 2 processes at once, beside DEBRIS-J's 4;
   - verifier-L: 1 hour and 5 CPU-minutes.
   - If time runs short, the lead cuts in this order: the live display, the edge-on view, then the fourth chart.
   - Default: these.

## Not in this parcel

- Any GPU run, WSL, the box, or the RTX 4070.
- Any third-party map, model or font file; any download or install.
- Any change to an earlier record, or to M1.
- Publishing anything outside the ledger and the repository's `studies\debris-l\` (decision 2 leaves that to Logan).

## The shape

| who | job | model | when |
|---|---|---|---|
| the lead (this session) | the plan, its checker and plan-verifier; files each message; merges; the record | Opus | throughout |
| plan-verifier-L | check this plan | Sonnet | done, on draft 1 |
| DEBRIS-L | the code, the media, the gates, the report | Sonnet (decision 1) | after draft 2 |
| verifier-L | disconfirm the media's provenance and the gates | Haiku (decision 1) | when DEBRIS-L reports |

## Dispatch

- **The prompt:** a dispatch note and the agent's brief, followed verbatim by three sections of this plan: "Dispatch", "Rules every brief carries" and "READY". After dispatch, `dispatch\check_prompts.py` checks the prompt against the harness's transcript.
- **The test escalation:** each agent writes `test escalation from <name>` in its own ledger file, `DEBRIS-L.md` or `verifier-L.md`, and sends the same words to the lead (SendMessage to `main`). The lead replies "received".
- **Ending its turn ends an agent's run,** and its final message becomes its report.

## Rules every brief carries

- **Read-only, except your own outputs and scratch,** `C:\Users\logan\source\repos\cft-debris-scratch\<name>\`. Read no other agent's scratch. In cft-debris, write only `tests\l_*.py` and `studies\debris-l\`. In the ledger, write only `debris-l\` and your own ledger file. Commit nothing: the lead commits after verification.
- **The repository is public and MIT.**
  - Every source file you write carries a header naming cft-debris and the MIT licence.
  - No third-party code, data, map or font goes in the repository.
  - **Per-object data stay out of the repository:** no catalogue number, state, position, pixel of an object, element set, or picture or video of the population. They go in the ledger's `debris-l\`.
  - No machine's address, home path or tool path goes in the repository: write `<python>`, `<ffmpeg>`, `<msys>` and `<root>`.
- **No downloads, installs or package managers,** and no requests to any data service. CelesTrak in particular is never requested.
- **No GPU, WSL, card or box.** At most 2 processes at once on the desktop, counting every child; ffmpeg runs with `-threads 2`. No timing is reported as a measurement.
- **CPU budget** is the CPU time of the processes you start, counted by cycles: `QueryProcessCycleTime` through `ctypes`, divided by 2.5e9, with `GetProcessTimes` beside it. DEBRIS-I's `tests\i_lib.py` does both, and may be reused.
- **Python:** `C:\Users\logan\AppData\Local\Programs\Miniconda3\python.exe -I -B`, with numpy. **C:** put `C:\msys64\mingw64\bin` first on PATH, and check that `gcc -dumpmachine` prints `x86_64-w64-mingw32`. **ffmpeg:** by its full path, as the dispatch note gives it.
- **Host traps:**
  - a bare `bash` or `timeout` from Python is System32's, so start programs by their full paths;
  - write files as bytes, or with `newline="\n"`, since text mode adds CR on Windows;
  - in the Bash tool a doubled backslash reaches the shell as one, inside a heredoc and in `printf` too, so write any script with backslashes with the Write tool;
  - a Bash `cd` can move your working directory for later calls, so use absolute paths.
- **Processes and files:** kill only processes you started, and only by PID. Delete only what you made.
- **No helper agents.** Message no one but the lead.
- **Your final message is your report.** Before it, stop any background work you started, and end with what you did not do and anything your brief got wrong.

## READY, stated before the first pass

Every load-bearing claim rests on a measurement with its command and output, a named record, or arithmetic from labelled inputs; otherwise it is stated as a limit. Every gate's criterion and every control are fixed before the data, and the code asserts them; a control that fails as specified is reported as failed. Every log names the SHA-256 of the script that wrote it; keep every version of a script that wrote a log, under a name carrying the first 12 hex digits of its hash; never overwrite a log. Every picture and video names, in a sidecar file, the SHA-256 of the data and the script that made it. Only a wrong answer sends work back; a sentence that claims too much is narrowed at the merge.

## Brief: DEBRIS-L

You are **DEBRIS-L** in cft-debris. You make the project's first visual presentation: screenshots, a short video, a live display and a results panel, as "The design" says. You never touch a GPU, WSL or any machine but the desktop.

**Your work** (3 hours, 20 CPU-minutes, at most 2 processes):
1. **M1:** build it in your own scratch with `tests\k_build.py`, giving `--archive` the ledger's `tools\cft-fp256-0aa997a3.tar` and `--scratch`, `--logs`, `--keep` and `--cpu` in your scratch. Read no other agent's scratch.
2. **The code,** in `tests\`:
   - a PNG writer and reader;
   - the small bitmap font;
   - the projection and drawing;
   - the `m1f prop` driver (reuse DEBRIS-K's `m1f_prop`), with DEBRIS-H's frame table;
   - the video's assembly;
   - the live display's writer;
   - the results panel's charts, with their source table.
3. **The media:**
   - the screenshots, the video, the live display and their sidecars to the ledger's `debris-l\`;
   - the results panel and its source table to `studies\debris-l\panel\`, with a `MANIFEST.sha256` over `studies\debris-l\`.
4. **The gates** V0 to V4, each with its control. Each writes a numbered log: its aggregate in `studies\debris-l\logs\`, and its per-object detail in the ledger's `debris-l\logs\`.
5. **Your report,** under 700 words: what you made and where, each gate's result, what you did not do, and anything this brief got wrong.

**Start here:**
- this plan;
- `tests\m1f.c` (`read_objs`, `mode_prop`), `tests\k_pilot.py` (`m1f_prop`) and `tests\k_build.py`;
- the seed's header in the ledger's `debris-h\box\r2\seed\seed1.txt`, and `seed_meta.tsv`;
- the four committed records the results panel reads;
- the ledger's `tools\scan-k\scan_debris_k.py` and `tools\scan-i\scan_debris_i.py`, for V4.

## Brief: verifier-L (completed when DEBRIS-L reports)

You are **verifier-L** in cft-debris. Disconfirm DEBRIS-L's media and gates; fix nothing.
- **Threat model:** a picture or video not drawn from the data it names; a number on the panel unlike its source; a gate or control that cannot fail; per-object data or a personal path in the repository.
- **Attack:**
  - re-run V1 for 5 objects of your own choosing, and V3 for every number;
  - look at each picture and at the video's first and last frames, and say whether they show what their captions say;
  - scan the repository's new files.
- **Report:** under 600 words, each attack's verdict with its evidence.

## What changed from draft 1 (plan-verifier-L's findings, answered)

plan-verifier-L's report is filed verbatim as `cft-debris-ledger\filed\DEBRIS-L-plan-verifier-L-report.md`. It found no blocker. The lead checked each finding against its source and upheld every one except its count of one group (it gave 581 for `cosmos-2251-debris`; the file has 582).

| finding | the answer in draft 2 |
|---|---|
| **D1:** V4 would fail on logs that name the tool paths; the K scan's file rule, its PNG and size rules and its catalogue-number rule do not fit this parcel | tool paths are logged as `<python>`, `<ffmpeg>`, `<msys>` and `<root>`; V4 is DEBRIS-L's own scan, scoped to its files, with PNG allowed in the panel, the hexadecimal exemption, and a trial run first; figures keep their commas |
| **D2:** V1's and V2's logs would put objects and pixels in the repository | the repository's logs carry counts and seed indices only; the per-object detail goes to the ledger |
| **D3:** the brief left out the build's inputs | `k_build.py`'s arguments, the 0aa997a3 archive with its SHA-256, a build in DEBRIS-L's own scratch, and the frame table are named |
| **Text needs a font, and none was planned** | a small bitmap font in DEBRIS-L's own code; time in digits alone if time runs short |
| **V3 did not check the drawn charts** | V3(b), with its control |
| **V2's control passed trivially at T_s** | the control now looks at k ≥ 1, for that object and no other |
| **No gate covered frames after T_s, the display's data, or the units** | V2(b); metres to kilometres stated; the writer asserts the range |
| **`ffmpeg -i` exits 1 on success; V1's control could hit two objects on one pixel** | V0 reads stderr; V1's pair is checked first |
| **Decision 3(b) was not carried into the text** | the frames and gates are written for Δ, 181 frames either way |
| **V4 should cover DEBRIS-L's own files only** | it does |
| **Notes:** `prop`'s output is about 150 MB; its speed is not G4's; ffmpeg's threads | it stays in scratch; the ESTIMATE says a factor of 1 to 5; `-threads 2` |

## The lead's slips so far

1. **Draft 1's V4 would have failed on the logs the plan itself required,** and its logs would have put per-object detail in the repository (plan-verifier-L's D1 and D2).
2. **Draft 1's brief named a build without its inputs** (D3).
3. **Draft 1 planned text without a font,** and left the drawn charts, the frames after T_s and the display's data unchecked.
4. **Draft 2 was written over draft 1 before a copy was kept.** Draft 1 was recovered exactly from the lead's session transcript, its SHA-256 equal to the one `lead.md` recorded, and is kept read-only as the ledger's `dispatch\DEBRIS-L-plan.draft-1.md`.
