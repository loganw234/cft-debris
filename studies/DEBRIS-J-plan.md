# DEBRIS-J: M1's force model as a cft program on a consumer GPU (the plan)

The plan of round DEBRIS-J in cft-debris, written by the project's lead. **Draft 3, 2026-11-23.** It answers plan-verifier-J's findings on draft 1 and its scoped re-check of draft 2; the sections "What changed from draft 1" and "What changed from draft 2" give each answer. Logan approved the plan at 13:14 ("Approved"), with its seven defaults, while the re-check ran. Draft 3's answers change no decision, scope, budget or use of the card.

Labels as in earlier rounds:
- **MEASURED:** a run's own output, with its log.
- **COMPUTED:** arithmetic from labelled inputs.
- **READ:** a named record, with its place.
- **READ (relayed):** a message from cft-fp256's lead, filed verbatim in the ledger's `relayed\`. It is the sender's word, and cft-debris has not checked it.
- **ESTIMATE**, with its basis and its range; **BELIEVED**; **INFERRED.**

## The question, in Logan's words

- **His goal** (2026-11-12): "a simulation capable of realtime (or slightly faster) simulation on a consumer card, so a 24x7 sim could run on a local box here for long run tests, validating itself with the open datasets update intervals, scaling tracked objects as the main scaling parameter presumably. High performance cards like the MI300X could then be used for higher density or faster/concurrent runs"
- **On precision:** "Id also prefer to continue to utilize the higher precisions, simply to be a usecase for cft-fp256 as well".
- **On cft programs and certificates:** "*Yes if possible utilize cft programs, as well as generating certificates when able", then "*Certificate support can be built for but not implemented in order to still have gpu capability at the moment".
- **The week's plan,** which Logan approved at 06:31 on 2026-11-23 ("Approve the plan"), names this round's question (ledger `plans\week-2026-11-23.md`, round 2): "on one card, does the program equal DEBRIS-I's executor runs bit for bit at segment boundaries, with marked lanes replayed? And how many objects does it carry in real time at binary64 and at binary256?"
- **Today, 12:46:** after round DEBRIS-I was pushed, the lead asked whether to start drafting this plan. Logan answered: "Draft it".

## What DEBRIS-J is for

DEBRIS-D laid out the GPU route as four milestones (`studies\DEBRIS-D-architecture.md`, Q8). DEBRIS-I built the first: M1's force model as a cft program, held bit for bit to cftc's reference interpreter and within fixed tolerances to M1, on libcft's software executor (`studies\DEBRIS-I-build.md`, verified). DEBRIS-J is the second, **M2: the same program on a GPU, replay-checked.** It answers two questions, and only these:
1. **Q-J1, correctness:** on the RTX 5060 Ti, through cft-fp256's `hip:N` device, does the program give the same bits as libcft's software executor, lane for lane at every boundary of 40 steps, with any marked lane replayed by the interpreter?
2. **Q-J2, capacity:** how many objects does the card carry in real time, at binary64 and at binary256 (and binary128, at little extra cost)?

It does not build the 24/7 loop (M3), use any other GPU, or change the program's source. A degree-20 program, certificates for GPU runs, and the MI300X wait for later rounds.

## What DEBRIS-J starts from

### DEBRIS-I's program (READ, `studies\DEBRIS-I-build.md`, at `a3beff9` on origin/main)

- **The model:** M1's forces without radiation pressure: gravity to degree 7, the Sun and the Moon from DE421, the Earth's orientation as a per-hour polynomial block, and exponential drag with M1's 28 bands. Integration is rk4 at h = 15 s, with t in the state.
- **The images** (section 2), compiled by cftc at cft-fp256's `9e8ff270` for `sw:512`, 40 steps a segment:

| format | instructions a step | bank (of 512) | scratch (of 512) | image SHA-256 |
|---|---|---|---|---|
| binary32 | 19,990 | 409 | 378 | `cdfe93d03fee156e4e0651eaa28f771f0dda196f5fa4ef099b8510ae15fdfc43` |
| binary64 | 19,362 | 403 | 378 | `d0a6558b12bf62070b38cf5dee715c9978a4eb68258cc2b74e499f5acbcd53b3` |
| binary128 | 19,550 | 412 | 378 | `02245fbc6025031797005317dbab02d1dec8baa6e16377963aa6c83593bc5994` |
| binary256 | 19,758 | 425 | 378 | `974d6760c68399df1a4f1c93d5027c41e3f1d6eecb926ade0d0c52181c79f7d9` |

  - The scratch is 7 state slots, 203 lane params and 168 spills. The features used are WIDE_CONST, REGS32, BANK_PTR, KX9, SCRATCH, SCRATCH_IO, SCRATCH_STRICT and FLAG_CONTROL; not INDEXED, and not AUGADD.
  - A step holds 39 divisions, 26 roots and 4 exp.
  - The six part systems step too: 172 to 2,033 instructions a step (section 2).
  - **A segment is one REPEAT loop around one step's instructions.** LANGUAGE.md at `9e8ff270` says "a segment is one REPEAT of 1 to 4,294,967,295 steps" (line 2947), and cft-fp256's own gate patches a reference's REPEAT to 1, 2, 5 and its own count, holding every lane to the interpreter at each (line 2960). DEBRIS-I's binary64 image holds 19,362 instructions against 19,360 a step (READ, `studies\debris-i\compiles.tsv`).
- **The driver,** `tests\i_run.c`: the run and segment loop, every lane param rewritten at each run's start, t checked at each run's start, and every boundary state, lane byte and mark kept. It opens its device with `cft_open_ex`, giving a depth and no artifact, and refuses an image whose bank or scratch differs from its runs file's (lines 261 to 263).
- **The records DEBRIS-J holds the card to** (section 6, "What DEBRIS-J inherits"):
  - **I3's day:** every boundary state of 64 objects × 144 boundaries of 40 steps, at binary64, binary128 and binary256, with lane bytes and 0 marks. The box's executor wrote them, in 8 batches of 8 lanes, and they are in the ledger's `debris-i\box\out\i3\`.
  - **I1's 32 cases:** the program at degrees 7 and 2 and the six part systems, at four formats, 16 lanes and 160 steps. The box's executor equalled the desktop's on every one, and the whole segment files' SHA-256 are recorded (R1, `studies\debris-i\box\logs\box_i0.001.log`).
- **The box's rates** (I5, MEASURED there, X in object-seconds a second at 1 / 18 / 36 workers):
  - the program at binary64: 7,278 / 101,958 / 92,573;
  - the program at binary256: 4,632 / 64,332 / 59,732.
  - Real time on the box's 36 workers is about 59,700 objects at binary256, an extrapolation past the 2,304 objects run.

### cft-fp256's `hip:N` at `9e8ff270`

READ in `docs\HOSTAPI.md` at `9e8ff270` (its section "The GPU backend: a HIP device as a libcft device", from line 2239) and in `host\src\backend_hip.cpp` at `9e8ff270`, and READ (relayed) in the ledger's `relayed\2026-11-18-cft-fp256-lead-gpu-backend-round-2.md` and `relayed\2026-11-18-cft-fp256-lead-gpu-round-2-closed.md`:
- **Opening it:** `hip:N` is one more spelling of `cft_open`'s artifact, in a build made with `make -C host HIP=1`. On NVIDIA it goes through HIP 7.2.4's NVIDIA layer: `HIP_PLATFORM=nvidia HIP_ROOT=/opt/rocm-7.2.4`, with `HIP_ARCH` default `89 120` (the RTX 4070 and the RTX 5060 Ti).
  - A number past the runtime's count is `CFT_ERR_NO_DEVICE`, naming the count.
  - A GPU whose architecture the build carries no code for is refused at open by name.
- **What runs on the GPU is libcft itself:** "a program lane is seq_exec.h's four per-lane functions around `seq_run_block`, one thread a lane". "The software handle is the definition the backend's tests hold it to, element by element and flag by flag."
- **What it publishes:** every format, the seven opcode groups, and the software executor's capacities with all its features, `seq_features` 0x7ff1f.
- **Depth:** `cft_open_ex` opens a GPU at a power of two up to 2,048 (`CFT_HIP_SCRATCH_MAX`). Deeper is `CFT_ERR_UNSUPPORTED`. The depth costs 260 bytes of device memory a slot a lane.
- **The chunk rule** (READ, `backend_hip.cpp`, lines 590 to 595, 615, 1744 to 1754 and 2039 to 2045): a program's lanes run in chunks, one launch a chunk.
  - A handle's chunk starts at 2,048 lanes (`PROG_CHUNK_START`), capped at `kmax`, and the handle keeps it from call to call.
  - After a launch over 250 ms (`LAUNCH_SLOW_MS`) the next chunk is halved, down to 8 lanes. After one under 62 ms (`LAUNCH_FAST_MS`) it is doubled, only while twice it is at most `kmax`.
  - `kmax` is the most lanes the stage and the pool hold, rounded down to a multiple of 8. The pool is at most 256 MiB (`POOL_MAX`), and a lane's share of it is its reach × 260 bytes. For a program that does not index, reach is its highest static slot + 1.
  - "That cliff - 504 lanes a launch at 2,048 - is a known limit for round 4's tuning".
- **One thread's latency** (READ, HOSTAPI): "a launch of one thread runs the whole divide in 0.25 ms on the 5060 Ti", at fp64, "212 interpreted instructions". The whole divide's rates there are 5.0e7 a second at fp64 and 1.4e7 at fp256.
- **Two of its measured costs on the RTX 5060 Ti** (READ (relayed)):
  - "every hip:N program without AUGADD pays 7 to 17%";
  - deep programs are far slower there: a 64-iteration STX/LDX program at fp64 ran 86,249 lanes a second at depth 256 and, at the same batch (8,192), 2,774 at depth 2,048, against 93,373 on the RX 7600 (relayed 2026-11-17, `relayed\2026-11-17-cft-fp256-lead-depth-rates-correction.md`). The cause is believed, by cft-fp256's lead, to be the clear of each lane's whole reach, and is not isolated.
- **Which GPU ran:** `cft_caps` says only `hip`. With `CFT_HIP_INFO=1` each open prints one line to stderr: the device's name and architecture, its PCI bus and memory, the HIP runtime and driver, the visible devices with `CUDA_VISIBLE_DEVICES`, and the build's `HIP_ARCH`. The line exists only on a GPU handle.
- **Failure:** an allocation refused before anything runs is `CFT_ERR_OUT_OF_MEMORY`, and the handle stays usable. Any other HIP failure once a launch may have started poisons the handle: "close it and open it again".
- **Linking:** on the NVIDIA platform the Makefile links the backend with `-L$(HIP_CUDA)/lib64 -Wl,-rpath,$(HIP_CUDA)/lib64 -lcudart -lstdc++ -lpthread -ldl -lrt` (READ, `host\Makefile` at `9e8ff270`, lines 153 to 154). `HIP_CUDA` defaults to `/usr/local/cuda`.
- **Certificates:** cft-segrun writes certificates on `hip:N`. Still missing, by cft-fp256's lead's account: the GPU's identity in a certificate, a stated depth beside a device, and cft-audit of a GPU-written certificate (READ (relayed), 2026-11-18).
- **Their own checks of the card** (READ, `docs\VALIDATION.md` at `9e8ff270`): "hip:0 in every run. On this desktop `CUDA_VISIBLE_DEVICES=1`, so the RTX 5060 Ti is the process's only device and the RTX 4070 is never touched; nvidia-smi ran before each run."

### The card, and the rules around it

- **The card** (the week's decision 2, approved with its default): "the RTX 5060 Ti, in the desktop's WSL distro `cft-gpu`. It is booked as `rtx5060ti`, `wsl-cft-gpu` and `desktop`, under cft-fp256's lock `/root/lead-gpu5060.lock`." The RX 7600 only if nvidia-box's other session agrees. "The RTX 4070 not at all, since it drives the displays." "Only the lead touches a GPU."
- **The TimeSheet** (READ, `timesheet.py resources`): `rtx5060ti` is "CUDA device 1 in PCI order (CUDA_DEVICE_ORDER=PCI_BUS_ID), used from WSL cft-gpu". `wsl-cft-gpu` is "the WSL distro cft-gpu (the GPU builds, CUDA and HIP): one user at a time". `rtx4070` is "CUDA device 0 in PCI order; it drives the displays". No standing window holds the 5060 Ti (`timesheet.py standing list`).
- **cft-fp256's lead** (READ (relayed), 2026-11-18): "in cft-gpu the 5060 Ti is device 1 in PCI order (CUDA_DEVICE_ORDER=PCI_BUS_ID with CUDA_VISIBLE_DEVICES=1). Device 0 is the 4070." Their runs "take flock locks: /root/lead-gpu5060.lock in cft-gpu ... If you take the same lock around your GPU runs, your runs and ours never overlap on a card."
- **The desktop's default WSL distro is `cft2204`,** cft-fp256's lead's (READ (relayed), 2026-11-12). Every WSL command in this round names its distro: `wsl.exe -d cft-gpu`.
- **Today** cft-fp256 holds `rtx5060ti` and `wsl-cft-gpu` exclusive until 15:00 (B0266, B0267: its GPU round 3's verifier).

### What the earlier estimates say

DEBRIS-D's ladder (`studies\DEBRIS-D-architecture.md`, Q5, COMPUTED there from GPU-A's measured rates at 1 million resident lanes, generic tier, no measurement of a program) gives degree 7 on the RTX 5060 Ti:
- binary64: 0.020 s of device time an object-day, so 4.2 to 4.4 million objects in real time;
- binary256: 0.090 to 0.100 s, so 0.87 to 0.96 million.

Those rest on DEBRIS-D's degree-7 image of 8,291 to 8,396 instructions a step. DEBRIS-I's program carries 19,362 at binary64 and 19,758 at binary256, 2.3 to 2.4 times as many. Scaled by that alone, the same method gives 1.8 to 1.9 million objects at binary64 and 0.37 to 0.41 million at binary256 (COMPUTED: each end of DEBRIS-D's range times its own instruction count over DEBRIS-I's). That assumes a million lanes resident, which the chunk rule above does not allow; "Rates" below gives this plan's ESTIMATE.

## The design, and why

**Two phases, as DEBRIS-I's were,** because no agent touches a GPU or WSL:
- **Phase 1, DEBRIS-J's:** the GPU driver, the build script, the harness and the analysis, built and tested on the desktop's software executor; the images at short segments, with gate E1; the staged inputs for every GPU run; and a hand-off naming each command the lead runs.
- **The lead's GPU work:** the build in `cft-gpu`, then J0, its calibration J0c, J1, J2 and J3, each run under its bookings and inside cft-fp256's lock.
- **Phase 2, DEBRIS-J's:** the replay of any marked lane on the desktop, the analysis of the GPU's records, and the build report.

**Short segments on the card, because one lane is one thread.** A launch lasts at least one lane's whole segment, whatever the chunk.
- **The ESTIMATE of one thread's step:** at binary64, 19,362 instructions × 0.25 ms / 212 = 23 ms, taking the whole divide's single-thread latency as the cost of an interpreted instruction (BELIEVED). At binary256, 19,758 instructions at 3.6 times that cost each, 83 ms, taking the whole divide's rates, 5.0e7 / 1.4e7, as the ratio of latencies too (BELIEVED). Its range is a third to three times (ESTIMATE).
- **So a 40-step segment would launch for about 0.9 s at binary64 and 3.3 s at binary256** (COMPUTED from that ESTIMATE). That is past the 250 ms that halves the chunk, down to 8 lanes. At binary256 it is past Windows' default 2-second timeout for a GPU's work, which would poison the handle. Whether that timeout reaches into WSL is not determined; it is BELIEVED to, since WSL's GPU goes through the Windows driver.
- **So the card runs images of s steps a segment,** s in 1, 2, 4 and 8 (each divides 40), compiled by cftc from DEBRIS-I's unchanged sources with `--steps s`. The calibration J0c picks one s for the round, by a rule fixed below.
- **Gate E1 holds the short images to DEBRIS-I's records on the desktop,** before any GPU run. An s-step image must differ from DEBRIS-I's 40-step image only in its REPEAT count, by a byte diff. The state after 40 / s segments of s steps must equal the state after one segment of 40, bit for bit. The lane bytes of a 40-step boundary must follow from the s-step ones by a relation DEBRIS-J states and asserts before the data (BELIEVED to be the OR of the flags, if each call's flags start clear).

**The driver is DEBRIS-I's, with four additions.** `tests\j_run.c` is a copy of `tests\i_run.c` (MIT, cft-debris's own) that adds:
1. an artifact for `cft_open_ex`, `--artifact hip:0` or none;
2. under `CFT_HIP_INFO=1`, the device line captured from its own stderr around the open, printed, and checked against `--expect-device`, stopping before any image loads if it differs;
3. a provenance record beside its outputs (below), and each call's wall time in its per-segment line;
4. `--keep-every N`: a segment record written only every N segments and at each run's end, with every mark still written. With s steps a segment, N = 40 / s keeps exactly the 40-step boundaries. J3's day at binary256 then writes 144 records of about 604 KB, 87 MB, where every segment's record would be about 3.5 GB (COMPUTED from plan-verifier-J's record size).

Its runs, INIT files, loop and outputs are i_run.c's. With no artifact and `--keep-every 1` it must give i_run.c's `.seg.bin` and `.marks.bin` bytes exactly; DEBRIS-J holds it to that on the desktop. The device-line path exists only on a GPU handle, so J0's control tests it on the card.

**The device's identity is checked before anything runs:**
- Every GPU process runs with `CUDA_DEVICE_ORDER=PCI_BUS_ID`, `CUDA_VISIBLE_DEVICES=1` and `CFT_HIP_INFO=1`, and opens `hip:0`, the one visible device.
- The driver stops before loading an image unless the device line names the RTX 5060 Ti. The line is kept in every log in the ledger. The repository's copies of the logs leave out its PCI bus.
- The RTX 4070 is never visible to a run, so it cannot be opened by mistake.

**The depth is 512,** the images' own. `cft_open_ex` takes it as a power of two within the GPU's 2,048. The program does not index, so its reach is 378 (READ, its scratch; plan-verifier-J read `seq_scratch_reach` as the largest of 378, 210 and 210). `kmax` is then 256 MiB / (378 × 260 bytes) = 2,731, rounded down to 2,728 (COMPUTED; the stage holds more). So a chunk starts at 2,048 lanes and cannot double (4,096 is past 2,728). If every launch stays under 250 ms, every chunk is 2,048 lanes.

**Bit for bit is the criterion for Q-J1, and the software executor is its reference,** as cft-fp256's own tests hold the GPU (HOSTAPI's "The software handle is the definition"). The chain to DEBRIS-I's records:
- the card's s-step outputs equal the software executor's s-step outputs (J1);
- the software executor's s-step outputs, reduced to 40-step boundaries, equal DEBRIS-I's 40-step records (E1, and J1's comparison with the box's I3 files).

M1's tolerance (I3's) then carries to the card through equality, and is not re-tested.

**Marks are replayed by the definition,** under DEBRIS-I's READY rule. A lane whose routine marked it carries the executor's result on, and its boundary state before the mark is kept. On the desktop, the interpreter (mpmath) replays the lane-segment from that state; if the replay equals the card's state, the run stands; if not, that lane's later states are void and it is redone from the replayed state. DEBRIS-I's box day logged 0 marks on the same inputs.

**Rates are measured on the card alone:**
- `rtx5060ti` and `wsl-cft-gpu` booked `exclusive`, and the desktop `sensitive` beside them in J2's and J3's windows;
- the card's memory in use and its utilisation, read by `nvidia-smi --query-gpu` before and after each run, within thresholds fixed in Phase 0 from its idle reading. Windows-side users of the card are invisible from WSL, so the bookings carry the rest;
- each run at least 60 s of wall time, with its number of segments fixed from J0c's call times before J2 begins.

**Certificates are built for, not implemented** (Logan's words above). Each GPU run writes a provenance record beside its outputs: the image's SHA-256, the runs and INIT files' SHA-256, `cft_build_id()`, the device line, the depth, s, and the SHA-256 of every output. That is what a certificate would bind. No certificate is written or audited, since cft-segrun's GPU certificates still lack the GPU's identity and a stated depth (above).

## The gates

Every criterion below is fixed before the data, and the code asserts it. A control that fails as specified is reported as failed.

**E1, the short segments, on the desktop** (DEBRIS-J's, phase 1, software executor only):
- **The images:** each s-step image's bytes differ from the 40-step image's of the same source and format only in the REPEAT instruction's count, at the offset DEBRIS-J reads from the image's format before any diff. plan-verifier-J's probe of one part system at fp64 found that the two images differ in one byte, at offset 93. Any other differing byte fails E1, and the `.bank` files must be identical.
- **I1's 32 cases at s = 1:** each case's output, reduced to its 40-step boundaries by the relation DEBRIS-J states, has the SHA-256 that R1 recorded for the 40-step run.
- **The program at degree 7, s = 2, 4 and 8,** at binary64, binary128 and binary256, on one of I3's batches (8 lanes) for 2 hours: reduced, each equals the 40-step image's output byte for byte.
- **j_run.c with no artifact** gives i_run.c's output bytes exactly on I1's 32 cases at s = 40.
- **Control:** an s = 1 output with one state byte flipped in its 40th segment must fail the reduced hash.

**J0, the build and the device** (the lead's, in `cft-gpu`, from DEBRIS-J's script):
- libcft from the `9e8ff270` archive (`7814576d…`), built in our own folder with `make -C host HIP=1 HIP_PLATFORM=nvidia HIP_ROOT=/opt/rocm-7.2.4 HIP_ARCH=120 HIP_CUDA=<as Phase 0 settles> libcft.a`, with `hip-symcheck` passing (the Makefile holds `libcft.a` to it).
- j_run.c linked against it with the Makefile's NVIDIA libraries. Every source's SHA-256 is printed, and the driver must equal the staged copy's.
- **The checks:**
  - the device line names the RTX 5060 Ti, and the build's `HIP_ARCH` is 120;
  - `cft_caps` gives backend `hip` and `seq_features` 0x7ff1f;
  - every image of the round loads on `hip:0` opened at 512 (`CFT_OK`);
  - **controls:** `hip:1` is refused with `CFT_ERR_NO_DEVICE` (one device visible); a depth of 4,096 is refused with `CFT_ERR_UNSUPPORTED`; and `--expect-device` given another card's name stops the driver before it loads an image.

**J0c, the calibration** (the lead's; a measurement, its rule fixed here):
- **The ladder:** the program at degree 7, at binary64, binary128 and binary256 in turn, at s = 1, 2, 4 and 8 in that order. At each step, one run of 2 segments at 8 lanes, then one at 2,048 lanes. The driver times each call.
- **The stop rule:** a format's ladder stops at the first s whose 2,048-lane call takes over 150 ms, and no larger s is started.
- **The warm-up:** each process's first call, 8 lanes and one segment at s = 1, carries the module's load and the pool's first allocation. It is logged and not judged.
- **The abort rule:** from each process's second call, any call over 1,000 ms stops the calibration. The driver stops itself, and the lead stops it by PID if it does not.
- **The choice:** the largest s whose 2,048-lane call stayed under 150 ms at every format, one s for the round. If s = 1 is over 150 ms at a format, s = 1 is still used, and the report says the chunk may halve there.
- **Its output:** each format's call time at 2,048 lanes for the chosen s, which fixes J2's run lengths and J3's projection.

**J1, bit for bit on the card** (the lead's GPU runs; DEBRIS-J's comparison):
- **(a) I1's 32 cases at s = 1:** each output file equals the desktop's software-executor output of the same image and runs, byte for byte. E1 chains them to R1's records.
- **(b) I3's day at the chosen s,** at binary64, binary128 and binary256: one run of 64 lanes, the 8 batches' INIT files joined, if their runs files are identical (DEBRIS-J checks; otherwise 8 runs of 8). At every 40th step, every lane's state and its lane byte (by E1's relation) equal its slice of the box's file in `debris-i\box\out\i3\`, byte for byte.
- **Marks:** each is counted by format, routine and run, and replayed on the desktop as above. A replay that differs voids its lane and is reported; past 10 such lanes DEBRIS-J asks the lead before redoing them.
- **Controls, each of which must fail:**
  - C-J1: one lane's INIT with its position one unit in the last place up, at binary256. Exactly that lane must differ, from the first 40-step boundary on.
  - C-J2: the program at degree 2, at s = 1 with its own runs and INIT files (I1's: 16 lanes, 160 steps), compared lane by lane at each 40-step boundary with the degree-7 case's states for the same lanes and boundaries. Every lane must differ at every boundary.
  - C-J3: the comparison run against a copy of one box file with one byte flipped. It must report that file and that boundary.

**J2, the rates** (a measurement, with no pass condition; its statistics fixed here):
- **Configurations:** the program at degree 7 and the chosen s, at binary64, binary128 and binary256; batches of 512, 2,048, 8,192 and 32,768 lanes. The lanes tile DEBRIS-H's 2,686 distinct seed sets in a fixed order; the harness tiles them inside `cft-gpu`, so nothing larger than one batch of 2,686 is staged.
- **A run:** as many whole hours from T_s as J0c's call time says will fill at least 60 s and at most 180 s. Where one hour would take more than 180 s, the run is the fewest whole segments that fill 60 s. Each configuration's length is fixed before J2 begins. The harness stages as many hourly blocks as the longest run needs (ESTIMATE: up to about 11 hours, for 512 lanes at binary64). The timed region runs from the first call after the warm-up to the last result read back.
- **The statistic:** X = object-seconds summed over the lanes / the wall time, as I5 defined it. Real-time capacity is X objects at one simulated second a second. Each format's batch with the largest X is run twice more, and its median and range are reported.
- **Validity:** the device line equals J0's; the card's memory in use and utilisation are within Phase 0's thresholds before and after; the desktop's CPU load is recorded. A run failing validity alone repeats once, and failing again is void. After the warm-up call, any call over 1,000 ms stops the run.
- **Beside the box:** X on the card against the box's I5 at 36 workers, the same program and format; a ratio of rates, from one sample on each side.

**J3, a catalogue day on the card** (a measurement, with one equality check at each format):
- **The lanes:** DEBRIS-H's 2,686 distinct seed sets, less seed index 1595, which DEBRIS-H decayed 5.8 hours after T_s and I3 set aside by the same rule: 2,685 lanes.
- **The span:** one simulated day from T_s at binary64 and binary256, at the chosen s, with `--keep-every 40/s`. A format runs the whole day only if its projection is at most 60 minutes of wall time; otherwise it runs 6 simulated hours. The projection is the span's calls (5,760 / s for a day) × 2 chunks (2,048 and 637 lanes, each a launch) × J0c's 2,048-lane call time at that format.
- **The measurement:** the wall time of the span, against its simulated time.
- **The check:** 16 lanes, drawn with `random.Random(20261124)` before the run, replayed on the desktop's software executor for the run's span at both formats. Each must equal the card's lane at every 40th step, bit for bit. (ESTIMATE of their cost: at the box's one-worker rates, 11.9 s a lane-day at binary64 and 18.7 s at binary256, 16 lane-days of each are 3.2 and 5.0 CPU-minutes; the desktop's rate is BELIEVED similar.)
- **Marks:** as in J1.
- J3 runs only if J1 passes.

## Rates: the ESTIMATE, and the card's time

- **The rate:** with s = 1 and 2,048 lanes a launch, binary64 gives 2,048 × 15 s / 23 ms, about 1.3 million object-seconds a second. binary256 gives 2,048 × 15 s / 83 ms, about 0.37 million (COMPUTED from the ESTIMATEs above). Staging each call's scratch and the launches themselves take some of that. The range is a third to three times (ESTIMATE).
- **Batches above 2,048 lanes** run as one chunk after another, so X is expected to level off there (INFERRED from the chunk rule). J2's 8,192 and 32,768 show whether it does.
- **Beside the box,** whose 36 workers give 92,573 at binary64 and 59,732 at binary256: if the ESTIMATE holds, the card carries about 14 and 6 times as many objects (COMPUTED). If the card at binary256 falls below the box, that is a finding for cft-fp256's round 4, sent as a request on Logan's word (decision 6).
- **The card's time,** at the ESTIMATE's rates and s = 1 (ESTIMATE, a third to three times):
  - J0 and J0c: 15 minutes;
  - J1: 25 minutes, mostly I3's three days of 5,760 steps at 64 lanes;
  - J2: 18 to 54 minutes, 18 runs of 60 to 180 s;
  - J3: 25 minutes, two days of 2,685 lanes in two chunks a call;
  - about 1.4 to 2 hours in all. At the top of the range it is about 3.7 hours, not three times as much: J2's runs are fixed at 60 to 180 s, and J3 is capped at 60 minutes a format (plan-verifier-J's arithmetic). The cut order (decision 5) keeps the card within its 4 hours either way.

## The shape

| who | job | model | when |
|---|---|---|---|
| the lead (this session) | Phase 0; the GPU builds and every GPU run, under the bookings and the lock; files each message; merges; the round's record | Opus | throughout |
| plan-verifier-J | check this plan before Logan sees it | Sonnet | now |
| DEBRIS-J | phase 1: j_run.c, the build script, the harness, the analysis, the short images and E1, the staged inputs and the hand-off; phase 2: the replay, the analysis and the build report | Opus (decision 1) | after Logan's approval |
| verifier-J | disconfirm the build, its gates and the GPU's records | Sonnet (decision 1) | when DEBRIS-J reports |
| merge-check-J | check any narrowing the lead makes at the merge | Haiku | after verifier-J, if the lead narrows anything |

- **Day 1 (Tuesday):** DEBRIS-J's phase 1, and the lead's Phase 0 questions to cft-fp256's lead.
- **Day 2 (Wednesday):** the GPU's work in agreed windows: J0, J0c, J1, J2, then J3. Then phase 2.
- **Day 3 (Thursday):** verifier-J, the merge and the commit. The push waits for Logan's word.

## Phase 0: the lead, before dispatch

1. **Ask cft-fp256's lead,** by cross-session message, and file the answer in `relayed\`:
   - (a) where in `cft-gpu` cft-debris may keep its own folder, and as which user;
   - (b) which CUDA toolkit to name as `HIP_CUDA` there, and whether `/opt/rocm-7.2.4` is the one to use;
   - (c) that cft-debris's GPU runs take `/root/lead-gpu5060.lock` with `flock`, as they offered;
   - (d) their GPU windows this week, so that the bookings never meet theirs;
   - (e) how `nvidia-smi` in `cft-gpu` names the 5060 Ti, and what it reads at idle.
2. **The archive:** the ledger's `tools\cft-fp256-9e8ff270.tar` (`7814576d…`) is DEBRIS-I's and is reused. Its SHA-256 is checked again before the build.
3. **Ledger files:** `DEBRIS-J.md` and `verifier-J.md`, with headers only, and the folder `debris-j\` for every per-object file.
4. **The TimeSheet:** a desktop `notice` for DEBRIS-J's phase 1. The GPU bookings (`rtx5060ti` and `wsl-cft-gpu` exclusive, with the desktop `shared` for J0, J0c and J1, and `sensitive` for J2 and J3) are made by the lead after the hand-off, in windows cft-fp256's lead has named free.
5. **The idle thresholds:** in the first booked window, before any run, the lead reads `nvidia-smi --query-gpu` on the 5060 Ti three times, and fixes J2's thresholds from those readings before J2 begins.

## Dispatch

- **The prompt:** a dispatch note and the agent's brief, followed verbatim by four sections of this plan: "Dispatch", "The ledger", "Rules every brief carries" and "READY". A script writes the prompt from this file. After dispatch, `dispatch\check_prompts.py` checks the prompt against the harness's transcript.
- **The test escalation:** each agent sends one as it starts:
  - it writes `test escalation from <name>` in its own ledger file;
  - it sends the same words to the lead (SendMessage to `main`);
  - the lead replies "received" and records the round trip in `lead.md`.
- If no test escalation arrives within ten minutes of a dispatch, the lead reads that agent's ledger file, arms a watch on the ledger folder, and says so in `lead.md`.
- **DEBRIS-J runs in two phases:**
  - Phase 1's final message is its **hand-off.**
  - The lead files it and runs the GPU's work in this order: J0's build and checks, with its controls first; J0c; J1; J2; J3 if J1 passes.
  - If a GPU run fails, the lead resumes DEBRIS-J with the failing log. DEBRIS-J fixes it on the desktop and hands off again.
  - When the GPU's records are in place, the lead resumes DEBRIS-J for phase 2. It replays on the desktop every mark the card logged, then evaluates. Phase 2's final message is DEBRIS-J's report.
- **Ending its turn ends an agent's run,** and its final message becomes its report or hand-off. A later message from the lead resumes it.

## The ledger

The ledger is `C:\Users\logan\source\repos\cft-debris-ledger\`, as in rounds DEBRIS-B to DEBRIS-I.

- **One file per author, append only:**
  - `lead.md` continues;
  - this round adds `DEBRIS-J.md` and `verifier-J.md`, which the lead creates with a header only;
  - correct an entry by appending beneath it, never by editing it.
- **Times:** every heading's time comes from `date`, never from memory.
- **Read it at three moments:** before starting; before resting anything on another study's number; before the final report.
- **Verifiers read `lead.md` only,** and the files it points them to.
- **Escalation:** write the entry first, then message the lead (SendMessage to `main`). Wait for the answer to a question while working on what does not depend on it. Never end your turn to wait, except at the end of a phase.
- **No agent messages another session.** Questions for cft-fp256's lead go through this round's lead.
- **When to write:** when an entry would change another agent's work or the lead's: an environment fact, a brief that turned out wrong, or a finding about a shared input, never progress. Every entry marks which claims were measured and which are believed.
- **When a pause is announced,** record where you are before you stop. On resuming, do a full read, check your outputs before trusting your memory of them, and say where you stopped.
- **Scratch:** each agent creates its own folder when it starts, `C:\Users\logan\source\repos\cft-debris-scratch\<name>\`. Read no other agent's scratch. Keep no secrets anywhere an agent is given.
- **The downloads:** `C:\Users\logan\source\repos\cft-debris-downloads\`, read-only for every agent. This round adds none, and reads only what DEBRIS-I's staging reads.
- **The tools:** `cft-debris-ledger\tools\`, read-only for every agent. It holds the archive `cft-fp256-9e8ff270.tar`.
- **Data kept out of the repository:** `cft-debris-ledger\debris-j\`, for every output that names an object or holds its state. DEBRIS-J writes there from the desktop, the lead copies the GPU's files there, and verifiers read it. DEBRIS-I's records are read from `debris-i\`, and DEBRIS-H's seed from `debris-h\`, never changed.
- **What the lead writes in `lead.md`, every verifier reads.** The lead records there every GPU run, with its bookings, the lock, the device line and its log's SHA-256. It never writes a judgement of DEBRIS-J's work there before verifier-J has reported.

## Rules every brief carries

These come from three places: Logan's standing rules (carried from cft-fp256 and cft-rebound, 2026-09 to 2026-11), canonical ParcelRound, and the rulings of rounds DEBRIS-B to DEBRIS-I.

- **Read-only, except your own outputs and scratch.**
  - cft-rebound, cft-fp256 and the TimeSheet are other sessions' live repositories. Read their files; in git, use only `git -C <repo> log` and `git -C <repo> show`. Never write in them, never run `git status` there, and never run a bare `git stash`.
  - In the TimeSheet you may run `timesheet.py check` and `list`, which only read.
  - cft-fp256 is Apache-2.0. Extract and build its archive only in your scratch.
  - In cft-debris, write only where your brief says. Commit nothing: the lead commits after verification.
- **The repository is public and MIT.**
  - Every source file you write carries a header naming cft-debris and the MIT licence.
  - Copy no third-party source into the repository, whether cft-fp256's, REBOUND's, cft-rebound's or Orekit's. libcft is linked from a build outside the repository and never vendored.
  - **No image or bank goes in the repository:** an image carries cft-fp256's routines. Record each image's SHA-256 and the command that rebuilds it, as DEBRIS-I did.
  - Copy no third-party data into the repository either: no gravity coefficients, no DE421 coefficients, no Earth orientation values, no frame table, no GP data.
  - **Per-object data stay out of the repository.** Logs in the repository name objects only by their index in DEBRIS-H's seed, never by catalogue number. They carry hashes, counts and aggregates, never a state.
  - **No machine's address, home path or GPU bus** goes in the repository: write a run's root as `<root>`, and keep any log that names one in the ledger, with a copy for the repository that does not.
  - **No other session's paths are fixed in `tests\`:** the lock file, the toolchain's paths and the run folder in `cft-gpu` are parameters, which the lead gives.
  - Reading a source to understand an interface is fine; quoting more than a short passage is not.
  - This project's own earlier code (DEBRIS-B's to DEBRIS-I's, and the lead's scripts in the ledger) is MIT, and may be reused with a note of where it came from.
- **No downloads, installs or package managers, and no requests to any data service.**
  - **CelesTrak in particular: no agent requests it.**
  - If another file would settle a question, ask the lead for it. Give its name, source URL, size, licence and purpose. Each file needs Logan's approval.
- **Reading the web: HTML pages only, and never CelesTrak's.** WebFetch returns a model's summary of a page, not its bytes: a figure or quote taken through it is labelled "READ (via WebFetch)", and supports "consistent with", never "confirmed". A URL ending in `.txt`, `.pdf`, `.csv`, `.zip`, `.bin`, `.jar` or `.gfc` is a download request.
- **No GPU, WSL, card or box.**
  - **The RTX 5060 Ti and `cft-gpu` are the lead's.** No agent opens a GPU, runs `wsl`, `nvidia-smi` or `hipcc`, or connects to any machine. Every GPU run is the lead's, in its bookings and inside cft-fp256's lock, from commands you hand it.
  - Code meant for `cft-gpu` builds and runs on the desktop too, against the software executor, for testing. Scripts that run in `cft-gpu` use Python 3's standard library only.
  - The RTX 4070 is never used by anyone in this round.
- **Keys:** this round uses no keys and signs nothing. Never look in `~/.ssh`.
- **Timings: none on the desktop.**
  - The desktop is shared. Desktop runs are functional tests: no time from them is reported as a measurement.
  - The round's timings are the card's, from the lead's runs in J0c's and J2's windows.
- **At most 4 processes at once on the desktop,** counting every child process you start: compilers, interpreters, drivers and workers alike.
- **CPU budget** means the CPU time of the processes you start on the desktop, counted by cycles:
  - read `QueryProcessCycleTime` through Python's `ctypes`, and divide by 2.5e9 cycles a second;
  - the divisor is the part's base clock (READ, cft-fp256's `docs/BENCHMARKS.md`), and taking it as the counter's rate is BELIEVED;
  - give `GetProcessTimes` beside it; on this host it under-reports a busy thread under load;
  - DEBRIS-I's `tests\i_lib.py` does both, and may be reused.
- **Long jobs:** run them through the Bash tool, in the foreground with a timeout of at most 600000 ms or with run_in_background. Never use nohup, and never end your turn while one of your jobs is running.
- **C on the desktop:**
  - Before any compile, put `C:\msys64\mingw64\bin` first on PATH and check that `gcc -dumpmachine` prints `x86_64-w64-mingw32`. In this Git Bash, a bare `gcc` is the 32-bit i686 compiler.
  - libcft's Windows build line is `make -C host CC=gcc OS=Windows_NT TMP=/tmp TEMP=/tmp <targets>`.
  - DEBRIS-I's `tests\build_i.sh` builds M1's side and its driver; reuse its pattern.
- **C in `cft-gpu` (the lead's runs):** libcft by `make -C host HIP=1 HIP_PLATFORM=nvidia HIP_ROOT=/opt/rocm-7.2.4 HIP_ARCH=120 HIP_CUDA=<as Phase 0 settles> libcft.a`; the driver linked with the Makefile's NVIDIA libraries. A build script must refuse to run without those settings, and print them.
- **Python:**
  - On the desktop: `C:\Users\logan\AppData\Local\Programs\Miniconda3\python.exe -I -B`, with numpy and mpmath. cftc and the interpreter run from the archive's `python\` folder in your scratch.
  - Scripts that run in `cft-gpu` use Python 3's standard library only.
- **Processes and files:** kill only processes you started, and only by PID. Delete only what you made, and never through a computed path.
- **Earlier studies' records are read-only.** Copy what you run into your scratch or your own output folder. Before your report, check all twelve:
  - `sha256sum -c SHA256SUMS` run from `studies\` shows 32 OK;
  - `find studies/debris-a -type f | wc -l` gives 29;
  - `sha256sum -c MANIFEST.sha256` shows 54 OK from `studies\debris-b\`, 136 OK from `studies\debris-c\`, 73 OK from `studies\debris-d\`, 60 OK from `studies\debris-e\`, 61 OK from `studies\debris-f\`, 43 OK from `studies\debris-g\`, 149 OK from `studies\debris-h\`, 119 OK from `studies\debris-i\` and 37 OK from `studies\debris-k\`;
  - there is no `__pycache__` anywhere under `studies\`.
- **Host traps:**
  - **System32 before PATH.** From Python, or anything else that calls CreateProcess, Windows searches System32 before PATH. So a bare `bash` is `C:\Windows\System32\bash.exe`, the WSL launcher into the default distro, and a bare `timeout` is `TIMEOUT.EXE`. Start every program from Python by its full path, such as `C:/msys64/usr/bin/bash.exe` and `C:/msys64/mingw64/bin/gcc.exe`, or run it through the Bash tool directly.
  - **MSYS `.exe` transparency:** writing a file `X` beside an existing `X.exe` writes to `X.exe`.
  - **CRLF:** any text-mode write from Python on Windows turns every newline into CR+LF, `Path.write_text` included. Write bytes, or open with `newline="\n"`, wherever a file's bytes matter. `cft-gpu`'s shell will not run a script with CR bytes, and hashes are taken over bytes.
  - **Backslashes:** in the Bash tool, a doubled backslash reaches the shell as one, inside a heredoc and in `printf` too. Write any script that contains backslashes with the Write tool, and write Windows paths in commands with forward slashes. Every check asserts that it found something to check.
  - **`cd`:** a Bash `cd` into a subfolder can move the session's working directory for every later call. Use absolute paths, or `git -C`.
  - **`grep` and CR:** Git Bash's `grep` strips the CR at each line end unless given `-U`. Count CRLF with Python.
  - **Windows paths in `sha256sum`:** given a backslashed path, it prefixes its line with `\`. Pass forward-slashed paths.
  - **Transcripts:** a harness task's `%TEMP%` output file is empty while the agent runs. A transcript is read from the session's `subagents\` folder.
  - **Never start a process under `pythonw`,** or detached, on the desktop.
- **No helper agents.**
- **Your final message is your report,** or, for DEBRIS-J's phase 1, its hand-off. Its word limit is in your brief.
- **Before you report,** stop any background work you started. End with what you did not do, and with anything your brief got wrong.

## READY, stated before the first pass

READY applies to DEBRIS-J and to every verifier's verdict. Every load-bearing claim must rest on one of:
- a measurement, with its command and output;
- a fetched source, cited by URL;
- arithmetic from labelled inputs.

Otherwise it is stated as a limit, in terms of the behaviour it concedes. A claim's domain and quantifier are claims, and so is a figure's definition. A number carried over from an earlier study keeps its definition, or it is re-measured.

**From rounds DEBRIS-B to DEBRIS-I:**
- **Every control states its pass and fail criteria before the data, and the code asserts them.** A control that fails as specified is reported as failed, whatever replaces it.
- **Every agreement claim states its tolerance before the data,** with its basis. In this round the tolerance is zero: bit for bit.
- **A measurement with no pass condition states its statistics, its configurations and its sample before the data.** J0c's calibration, J2's rates and J3's day are such measurements.
- **Every log names the SHA-256 of the script that wrote it,** and the criterion that script asserted.
  - Keep every version of a script that wrote a log, under a name carrying the first 12 hex digits of its hash, before you change it.
  - Never overwrite a log: number each run's log.
  - The manifest lists every version.
- **Every build prints the SHA-256 of every source it compiles,** and every load of an image prints the image's SHA-256.
- **An ESTIMATE names its basis and its range,** and is never added to a MEASURED figure without saying so.
- **A bound over many trials holds only when the trials are independent.** Say what varies from trial to trial.
- **A cause is claimed only when a run isolates it.** Otherwise it is inferred, and labelled so.
- **Every throughput figure names its configuration** (the format, the device and its line, the batch, the depth, s, the model) and the load beside it.
- **Every ratio of times says what it divides:** wall times or CPU times, rates or rates.

**New in this round:**
- **Every GPU run names its device by its line,** from `CFT_HIP_INFO=1`, and its build by `cft_build_id()`. A run whose line does not name the RTX 5060 Ti is void, whatever its bits.
- **Every comparison names both sides exactly:** the image's SHA-256, its s and depth, the device's line or the software executor, the runs and INIT files' SHA-256, and the boundaries compared.
- **Every mark is counted where it happens,** by format, routine and run, and replayed on the desktop by the interpreter before its lane is used. A gate's criterion is evaluated only on states that are unmarked or replayed equal.
- **A GPU failure is reported by its status and its sentence,** and a poisoned handle's run is void, not partly used.
- **No call on the card may run past 1,000 ms,** after its process's warm-up call. A run that does is stopped and reported, not continued.

A verifier may reuse a run instead of re-running it only when all three of these hold:
- someone other than the author of the work made the run;
- its inputs are identical, file hashes included;
- the verifier re-runs from clean whatever it doubts.

The GPU's runs are the lead's, from DEBRIS-J's code. So their logs count as made by someone other than DEBRIS-J, but not as independent of DEBRIS-J's code.

Only a wrong answer sends work back: a false claim, a measurement or check that cannot fail, or code that does not build or does not do what its gate says it does. Everything else is a note the lead records, and a sentence that claims too much is narrowed at the merge.
- **Loop cap (Logan, 2026-10-15, carried through the lead's memory):** after three NOT READYs for narrowing reasons, the next pass blocks only on wrong answers.
- **Threat model (Logan, 2026-10-02):** each verifier's brief states one, and findings outside it do not reopen the loop.

## Logan's decisions (each default stands unless changed)

1. **Models:**
   - (a) **Opus for DEBRIS-J, Sonnet for verifier-J,** and Haiku for a merge-check, as in DEBRIS-I;
   - (b) Sonnet for DEBRIS-J and Haiku for verifier-J.
   - Default: (a).
2. **The card:** the RTX 5060 Ti in `cft-gpu`, under cft-fp256's lock, as the week's decision 2 approved. Default: as approved, with no other GPU.
3. **The formats on the card:**
   - (a) J1 at binary64, binary128 and binary256 on I3's day, and at all four on I1's cases; J2 at binary64, binary128 and binary256;
   - (b) binary64 and binary256 only, as the week's plan asked.
   - Default: (a). binary128 adds 6 of J2's 18 runs, each 60 to 180 s, and one of J1's three I3 days, whose card time lies between binary64's and binary256's (ESTIMATE, from DEBRIS-D's ladder, which puts binary128 between them on this card).
4. **J3, the catalogue day:**
   - (a) run it, at binary64 and binary256, with its 16-lane checks;
   - (b) leave it out, and report J2's capacity only as X.
   - Default: (a).
5. **Scope and budgets:**
   - DEBRIS-J's phase 1: 6 hours of wall time and 40 CPU-minutes on the desktop. Its fixes after a failed GPU run: 2 hours and 15 CPU-minutes in all. Its phase 2: 2 hours and 15 CPU-minutes;
   - it messages the lead before passing any of these, and before any single desktop run it expects to pass 5 CPU-minutes;
   - **the card:** up to 4 hours of the lead's GPU time for J0 to J3, in windows cft-fp256's lead has named free;
   - verifier-J: 3 hours and 25 CPU-minutes on the desktop, and up to 30 minutes of card time beyond the 4 hours, run by the lead at its request;
   - a merge-check: 25 minutes.
   - **If time runs short,** the lead cuts in this order: J3; binary128; J2's batch of 32,768.
   - Default: these budgets, and this order of cuts.
6. **If the card is slower than the box:** if J2 finds the card at binary256 below the box's 59,700 objects, the lead sends cft-fp256's lead the measurement as a request for its round 4 (the chunk rule for long lanes), on Logan's word. Default: report it, and ask Logan before sending.
7. **If cft-fp256's lead cannot give windows this week,** or asks for another lock or another folder:
   - (a) wait for their windows, and tell Logan the new dates;
   - (b) ask Logan whether to book the card around them.
   - Default: (a). No window is forced.

## Not in this round

- The 24/7 loop on the card (milestone M3), and any long run.
- A degree-8 or degree-20 program, index tables, or any change to DEBRIS-I's program sources. Images at other `--steps` counts are compiled from those sources unchanged.
- The RX 7600, the RTX 4070, the Intel Arc A750 and the MI300X.
- Certificates written or audited (provenance records only).
- Any change to cft-fp256, its tools, its distro's toolchain, or its lock file.
- M1's own runs: J1 rests on DEBRIS-I's records, and M1's tolerance carries through equality.

## Brief: DEBRIS-J

You are **DEBRIS-J** in cft-debris. You build the code that runs DEBRIS-I's program on cft-fp256's `hip:N` device, test it on the desktop's software executor, stage the GPU's inputs, and hand off the commands the lead runs on the RTX 5060 Ti. Then, in phase 2, you analyse the GPU's records and write the build report, `studies\DEBRIS-J-build.md`. You never touch a GPU, WSL or any machine but the desktop.

**Phase 1** (6 hours and 40 CPU-minutes, at most 4 processes):
1. **`tests\j_run.c`,** a copy of `tests\i_run.c` with the design's four additions: `--artifact`, the device line under `CFT_HIP_INFO=1` checked against `--expect-device`, the provenance record with each call's wall time, and `--keep-every`.
2. **The short images:** cftc at `9e8ff270`, `--steps s` from DEBRIS-I's sources unchanged: I1's eight systems at four formats at s = 1, and the program at degree 7 at s = 2, 4 and 8 at binary64, binary128 and binary256. Record each compile as `compiles.tsv` does.
3. **Gate E1,** with its control, and j_run.c's own desktop gate. State the lane bytes' relation before you run E1.
4. **`tests\build_j.sh`:** the `cft-gpu` build. It refuses to run unless `HIP=1`, `HIP_PLATFORM=nvidia`, `HIP_ROOT`, `HIP_ARCH` and `HIP_CUDA` are given, prints them and every source's SHA-256, builds libcft from the archive in the folder it is given, and links j_run.c with the Makefile's NVIDIA libraries. It also builds the software j_run on the desktop, for your tests.
5. **`tests\j_harness.py`,** standard library only where it runs in `cft-gpu`:
   - **stage:** the GPU run folder, with `EXPECTED.sha256`: the images, I1's cases, I3's runs and INIT files, the base of 2,686 seed sets that J2 and J3 tile inside `cft-gpu`, J3's 16 lanes, and the controls' inputs;
   - **gpu-j0, gpu-j0c, gpu-j1, gpu-j2, gpu-j3:** the modes the lead runs, each a numbered log, each taking the lock's path and the run folder as parameters and running its GPU work inside `flock` on that lock, with the card's `nvidia-smi` reading before and after each J2 run, and J0c's stop and abort rules in its code;
   - **compare and analyze** (desktop, phase 2): J1's comparisons, the marks' replay, J2's statistics and J3's checks.
6. **The controls** C-J1 to C-J3 and E1's, each shown to fail on the desktop's software executor first, where it can be. J0's device controls run only on the card.
7. **The hand-off,** your final message of phase 1, under 900 words: what you built, E1's result, the staged folder with its `EXPECTED.sha256`, and every command the lead runs in `cft-gpu`, in order, with its ESTIMATE of card time and what it must print.

**Phase 2** (2 hours and 15 CPU-minutes): the lead resumes you when the GPU's records are in the ledger's `debris-j\gpu\`, with the repository's copies of the aggregate logs in `studies\debris-j\gpu\`. Replay every mark first, then evaluate J0 to J3 and write the build report. Your final message then is your report, under 900 words: what you built, each gate's result, the measurements, what you did not do, and anything this brief got wrong. Label every figure.

**Start here:**
- this plan, and `lead.md` from its heading dated 2026-11-23 12:40 to its end;
- `studies\DEBRIS-I-build.md`, all of it, and DEBRIS-I's code: `tests\i_run.c`, `tests\i_harness.py`, `tests\i_lib.py`, `tests\i_vals.py`, `tests\build_i.sh`;
- cft-fp256 at `9e8ff270`, from the ledger's archive: `docs\HOSTAPI.md`'s GPU section from line 2239, `host\src\backend_hip.cpp`'s chunk rule, and `host\Makefile`'s HIP lines.

## Brief: verifier-J (completed when DEBRIS-J reports)

You are **verifier-J** in cft-debris. Your job is to disconfirm DEBRIS-J's build, its gates and the GPU's records, never to fix them. Edit no file outside your scratch. You never touch a GPU or WSL: any card run you need, the lead runs from your script.

**Threat model.** A wrong answer in DEBRIS-J's work:
- a check that cannot fail;
- a GPU run that did not run on the RTX 5060 Ti, or ran on a poisoned handle;
- a comparison made at different inputs, images, s, depths or boundaries, or against the wrong reference;
- a driver that differs from i_run.c beyond its stated additions;
- a short image whose states at 40-step boundaries differ from DEBRIS-I's;
- a rate not as defined, or measured outside its window or beside another load on the card;
- a mark not replayed, or a voided lane used;
- third-party data, an image, a home path, a GPU bus, or per-object data in the repository.

Findings outside this model are notes and do not reopen the loop.

**Attack these, in this order:**
1. **The driver:** diff j_run.c against i_run.c, and re-run its desktop gate on 4 of I1's cases of your own choosing.
2. **E1:** re-run it for 2 of I1's cases and one format of the program at an s of your own choosing.
3. **The device:** every GPU log's device line names the RTX 5060 Ti and the same build; J0's controls bite; J0c's rules were followed.
4. **J1:** recompute the byte comparison for 3 objects of your own choosing at each format, from the GPU's files and the box's.
5. **The controls** C-J1 to C-J3: re-run them on the desktop where they can run.
6. **J2:** X from each run's own figures, the validity checks, and the ratio with the box's I5.
7. **J3:** the 16 lanes' checks, and each span's wall time against its simulated time.
8. **The repository:** no catalogue number, state, data value, home path, GPU bus or personal string in any file under `studies\` or `tests\`.

**Budget:** 3 hours of wall time and 25 CPU-minutes on the desktop, and up to 30 minutes of card time. Message the lead before passing either.

**Report:** your final message, under 1,200 words. Give each attack's verdict (confirmed, defect, or not determined) with its evidence. For every defect, give the exact passage and what it should say.

## What changed from draft 1 (plan-verifier-J's findings, answered)

plan-verifier-J's report is filed verbatim as `cft-debris-ledger\filed\DEBRIS-J-plan-verifier-J-report.md`. The lead checked each finding at its source before answering it, and upheld every one.

| finding | the lead's check | the answer in draft 2 |
|---|---|---|
| **B1:** the chunk starts at 2,048 and halves after any launch over 250 ms, down to 8; a 40-step lane probably runs for seconds, so the chunk collapses, J2 and J3 take hours, and a launch over about 2 s may meet Windows' GPU timeout | READ `backend_hip.cpp`, lines 590 to 595, 615 and 2039 to 2045. The lead's own ESTIMATE from HOSTAPI's single-thread divide gives 0.9 s and 3.3 s a 40-step launch | the card runs images of s steps (s in 1, 2, 4, 8), held to DEBRIS-I's records by the new gate E1; the new calibration J0c picks s with a stop rule at 150 ms and an abort at 1,000 ms; J3 runs a day only if J2 projects it within 60 minutes; the card's time is estimated |
| **B2:** C-J2 cannot run: i_run.c refuses an image whose bank differs from its runs file's (403 against 208 slots) | READ `tests\i_run.c`, lines 261 to 263 | C-J2 runs the degree-2 program with its own I1 runs and INIT files, compared with the degree-7 reference |
| **D1:** J2's "repeated until 60 s" is not what i_run does | READ, i_run.c's runs file and its t check | each run's length is fixed from J0c's call times, 60 to 180 s, before J2 begins |
| **D2:** "one change" is wrong, and the device-line path cannot be tested on the desktop | READ, HOSTAPI: the line exists only on a GPU handle | "three additions", named; the desktop gate covers the outputs; J0's control tests the device path on the card |
| **D3:** the `nvidia-smi` process check is probably vacuous in WSL | READ, VALIDATION.md: "nvidia-smi ran before each run" | memory and utilisation thresholds from Phase 0's idle readings, with the bookings for the rest |
| **D4:** J1(b)'s shape is not stated | READ, the box's I3 files: 8 batches of 8 lanes | one 64-lane run if the batches' runs files are identical, compared per lane slice; otherwise 8 runs |
| **D5:** J3 checks binary256 only, and the catalogue includes a lane that re-enters | READ, DEBRIS-I's I3 rule for seed index 1595 | 16-lane checks at both formats; 1595 set aside as I3 did; J1's marks rule applies |
| **D6:** J0's build line lacks `HIP_CUDA` | READ, the plan's own Phase 0(b) | added, as Phase 0 settles it |
| **D7:** the lock's path would be fixed in `tests\` | READ, the plan's harness | the lock, the toolchain's paths and the run folder are parameters; a rule says so |
| **D8:** the desktop's booking mode, verifier-J's card time, and a refused window are unstated | READ, the TimeSheet rule that timings book `sensitive` | the desktop `sensitive` for J2 and J3; verifier-J's 30 minutes beyond the 4 hours; decision 7 |
| **Note:** `kmax` is 2,728, not 2,731 | READ, `backend_hip.cpp` line 1747 | corrected |
| **Note:** the 6 to 11 CPU-seconds a lane-day came from a plan's ESTIMATE, not from DEBRIS-I's measurement | READ, `lead.md` | J3's replay cost now rests on the box's measured I5 rates |
| **Note:** staging J2's batches would take about 2 GB | COMPUTED from the batch sizes | the harness tiles them inside `cft-gpu` from one base of 2,686 |
| **Note:** J2 has one sample a cell | READ, the plan | each format's best batch runs three times |

## What changed from draft 2 (plan-verifier-J's re-check, answered)

plan-verifier-J's re-check is filed verbatim as `cft-debris-ledger\filed\DEBRIS-J-plan-verifier-J-recheck-report.md`. It found no blocker open: B1 and B2 are closed. Its probe confirmed E1's premise: a part system's 1-step and 40-step images at fp64 differ in one byte, the REPEAT count, and their banks are identical. The lead checked each new finding against the plan's own text and upheld every one. None changes a decision, the scope, a budget or the card's use, so Logan's approval stands.

| finding | the answer in draft 3 |
|---|---|
| **D1:** J2's rule of whole hours within 180 s cannot be met where one hour takes longer, such as binary256 at 32,768 lanes (about 318 s) | where one hour exceeds 180 s, a run is the fewest whole segments that fill 60 s; the hourly blocks staged cover the longest run |
| **D2:** the 1,000 ms abort does not exempt a process's first call, which carries the module's load and the pool's first allocation | each process's first call is a warm-up, logged and not judged; the abort counts from the second call, in J0c, J2 and READY |
| **D3:** E1's allowance for "any header field" could excuse an unexpected change | only the REPEAT count's bytes may differ, at the offset read from the image's format before the diff; the banks must be identical |
| **D4:** at s = 1 every segment's record makes J3's day about 3.5 GB at binary256 | j_run.c's fourth addition, `--keep-every 40/s`, keeps the 40-step boundaries: 87 MB |
| **D5:** J3's projection names no batch, and 2,685 lanes are two launches a call | the projection is the span's calls × 2 chunks × J0c's 2,048-lane call time |
| **B2's wording:** C-J2's comparison must be per lane over matching boundaries | it is now: 16 lanes, each 40-step boundary |
| **Note:** "up to about 6 hours" overstates the top | about 3.7 hours, with the reason |
| **Note:** phase 2's 15 CPU-minutes are tight, with J3's replays taking 8.2 | the budget stands as approved; `--keep-every` cuts the bytes compared, and DEBRIS-J messages the lead before passing it |
| **Note:** the estimate's basis includes a launch's overhead, so it likely overstates a step | left as written: J0c measures the step |
| **Not checked by it:** whether seed index 1595 is among the 2,686 distinct sets | DEBRIS-J's staging counts J3's lanes and reports the count. 1595 is in the `cosmos-2251-debris` group (READ, the ledger's `debris-k\pilot\plan.json`), so it is not one of the stations group's docked vehicles that share a set (INFERRED) |

## What earlier rounds taught, applied here

- **The box's runs worked because the lead ran them from a staged folder with `EXPECTED.sha256`** (DEBRIS-G, -H, -I). The GPU's runs do the same.
- **A launch line that backgrounds a list hangs its ssh** (DEBRIS-I's box-i0). The GPU's runs are run in the foreground of `wsl.exe -d cft-gpu`, each inside `flock`, with no backgrounded list.
- **A log can carry a home path from a tool's own output** (DEBRIS-I's `box_build.001.log`, make's "Leaving directory"). The rules now say how to keep such a log.
- **A control's plant can be too small to bite** (DEBRIS-I's C13). Each control here changes a lane's bits outright, so any difference shows.
- **Another session's long job can run into a sensitive window** (cft-fp256's gate, today). The GPU windows are agreed with cft-fp256's lead before they are booked.

## The lead's slips so far

1. **Draft 1's account of the chunk** read HOSTAPI's sentence on where a chunk starts as the chunk's size, and did not follow the halving rule to its end for a long lane. plan-verifier-J found it (B1), from the source code.
2. **Draft 1's C-J2** could not run against I3's runs file (B2).
3. **Draft 1 called j_run.c's changes "one change"** (D2).
4. **Draft 1 attributed the 6 to 11 CPU-seconds a lane-day to DEBRIS-I's measurements;** it was a plan's ESTIMATE.
5. **Draft 1's `kmax` was not rounded** to a multiple of 8.
6. **Draft 1's decision 5 named no default.** The lead's checker found it before plan-verifier-J saw the draft.
7. **Draft 2's J2 run rule could not be met at its largest batch, its abort rule caught the warm-up, its E1 allowance was loose, its volume at s = 1 was unstated, its J3 projection named no batch, and its "6 hours" overstated the top.** plan-verifier-J's re-check found each.
