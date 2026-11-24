# DEBRIS-J: M1's force model as a cft program on a consumer GPU (build report)

Written by DEBRIS-J, 2026-11-23, for cft-debris (MIT). The plan of record is `studies\DEBRIS-J-plan.md`, draft 3 (SHA-256 `4b84a073c8fda02c6d17bcca3d0887a90a0fe83502764a3b43ce574f6a6a1377`).

**Labels.**
- **MEASURED:** a log in `studies\debris-j\logs\` (the desktop's), or in `studies\debris-j\gpu\r1\logs\` (the card's). Every log names the SHA-256 of the script that wrote it and of the module it imports. Every version of the script that wrote a log is kept in `studies\debris-j\scripts\`.
- **The card's runs are the lead's,** made in cft-gpu from this parcel's code and staged inputs. They count as made by someone other than DEBRIS-J, but not as independent of DEBRIS-J's code.
- READ, COMPUTED, ESTIMATE, BELIEVED and INFERRED as in earlier rounds.

**The manifest.** `studies\debris-j\MANIFEST.sha256` lists every file under `studies\debris-j\`. Per-object data (states, INIT files, runs files, the box's and the card's outputs) are in the ledger's `debris-j\` only.

**Checked by verifier-J** (Sonnet), with no wrong answer found. At the merge the lead corrected two sentences and added one note, each marked where it stands and listed in section 13.

## The answers

- **Q-J1, correctness: yes, on everything compared.** On the RTX 5060 Ti, through cft-fp256's `hip:0`, the program gives the bits of libcft's software executor. That holds for every state and lane byte compared:
  - I1's 32 cases at s = 1, at four formats;
  - I3's day for 64 objects at binary64, binary128 and binary256, at every 40-step boundary;
  - 16 drawn objects of the catalogue day at binary64 and binary256.

  No lane was marked anywhere on the card, so no replay was needed (MEASURED, section 6).
- **Q-J2, capacity:** X, in object-seconds a second at s = 1 (the median of 3 runs of each format's best batch, MEASURED):

  | format | X | the plan's real-time capacity |
  |---|---|---|
  | binary64 | 233,407.4 | about 233,000 objects |
  | binary128 | 191,230.8 | about 191,000 objects |
  | binary256 | 134,394.9 | about 134,000 objects |

  The capacities extrapolate past the 8,192 lanes run validly (section 7). The whole catalogue, 2,687 objects, ran a day in 25.0 minutes at binary64 and 43.1 at binary256: 57.6 and 33.4 times real time (MEASURED, J3).

## 1. What was built

| file | what it is |
|---|---|
| `tests\j_run.c` | the driver: DEBRIS-I's `tests\i_run.c` with the design's four additions (section 2) |
| `tests\build_j.sh` | the builds: `gpu` (cft-gpu: libcft with the GPU backend on HIP 7.2.4's NVIDIA layer, and `j_run` linked with the Makefile's NVIDIA libraries), and `desktop` (libcft's software build, with `j_run` and DEBRIS-I's `i_run`) |
| `tests\j_harness.py` | the harness, standard library only:<br>- the desktop's modes: `compile`, `e1`, `jgate`, `controls`, `j3ref`, `buildgate`, `stage`;<br>- the card's modes, run by the lead: `gpu-j0`, `gpu-j0c`, `gpu-j1`, `gpu-j2`, `gpu-j3`;<br>- phase 2's modes: `compare`, `replay`, `analyze`, `gpucopy`, `hostload` |
| `tests\j_gpu.sh` | the lead's wrapper for one GPU step in WSL's cft-gpu: checks its tools, copies the staged folder once, runs a mode; `back` copies the records out with a checked SHA-256 list |
| `tests\i_lib.py` | DEBRIS-I's logs and CPU accounting, imported unchanged |

**Building:**
- **The desktop:** `bash tests/build_j.sh desktop <work dir> <archive 9e8ff270> tests`.
- **cft-gpu:** `HIP=1 HIP_PLATFORM=nvidia HIP_ROOT=… HIP_ARCH=120 HIP_CUDA=… bash tests/build_j.sh gpu <work dir> <archive> <tests>`. It refuses to start without all five settings (MEASURED, `buildgate.002.log`, 4 refusals). On the card the lead ran it inside `gpu-j0`: BUILD PASS, with libcft (HIP) `0d4109e45fed…` and `j_run` `b3a75460c624…` (MEASURED, `gpu_j0.001.log`).

**The images** stay out of the repository. `studies\debris-j\compiles.tsv` gives 73 compiles (MEASURED, `compile.001.log`, 178 checks, 0 failed), all from DEBRIS-I's sources unchanged:
- I1's eight systems at four formats, at s = 40 and at s = 1;
- the program at degree 7 at s = 2, 4 and 8, at binary64, binary128 and binary256.

The 32 compiled at s = 40 have DEBRIS-I's image SHA-256: cftc reproduces DEBRIS-I's images. Each image is rebuilt by `python -I -B <archive 9e8ff270>/python/cftc studies/debris-i/systems/<stem>.cftl --steps <s> --target sw:512 --format <fmt> --out <dir> --stem <stem>`. The card ran s = 1: the program at degree 7 is `b7be3a3d…` (binary64), `3f2f1c5a…` (binary128) and `e0ea920a…` (binary256).

## 2. The driver

**`j_run.c` is `i_run.c` with these differences, listed in its header:**
1. `--artifact`.
2. The device's identity:
   - stderr is captured around `cft_open_ex` into `PREFIX.open.txt`;
   - the `CFT_HIP_INFO=1` line is printed as `device …`;
   - `--expect-device NAME` stops the driver, exit 5, before any image loads, unless the line names that device;
   - the caps are printed;
   - mode `load` loads each image given and runs nothing (J0).
3. The provenance and the call times:
   - `PREFIX.prov.txt` holds the build, the device line, the caps, the depth, s, and every input's and output's SHA-256 (outputs hashed as written);
   - `call_ns` is on each segment's line;
   - `--warmup-lanes W` makes one discarded call first;
   - `--abort-ms M` stops the driver, exit 6, after any call past M ms other than the process's first;
   - REPORT lines give the timed region;
   - a write error is refused.
4. `--keep-every N`: a record is written every N segments and at each run's end, its lane bytes the OR since the run's last record.

Beyond those, its messages say j_run, and its first stdout line names its options.

**Its desktop gate** (MEASURED, `jgate.002.log`, 72 checks, 0 failed):
- with no artifact, on I1's 32 cases, its `.seg.bin` and `.marks.bin` equal `i_run`'s, byte for byte, and have R1's SHA-256;
- the warm-up changes no byte written;
- `--expect-device` stops it before any image line (exit 5);
- the abort stops it after the second call (exit 6);
- `load` loads 41 of 41 images and refuses a corrupted one;
- every provenance file names the inputs' and outputs' SHA-256 as on disk.

## 3. The short segments: gate E1

**The relation, stated in E1's criteria before it ran** (BELIEVED then, from HOSTAPI's R23: each lane byte is "sticky within the run and starts it at zero"). With N = 40 / s:
- the 40-step boundary k of a run is the s-step boundary kN;
- its state equals the state after s-step segment kN;
- its lane byte is the bitwise OR of the N segments' lane bytes.

**E1 passes** (MEASURED, `e1.001.log`, 86 checks, 0 failed):
- **The images:** all 41 pairs differ in exactly one byte, the REPEAT count's low byte, at the offset read from the image's format (36 for the program, 60 to 132 for the part systems), and their banks are identical.
- **I1's 32 cases at s = 1** reduce to R1's 40-step SHA-256, and `--keep-every 40` gives the same reduction.
- **The program at s = 2, 4 and 8,** at three formats, on I3's batch 0 for 2 hours: each reduces to the box's first 12 records and to the desktop's own 40-step run, with 0 marks.
- **The control C-E1** (one state byte flipped at the first boundary) fails the hash, as it must.

## 4. J0: the build and the device (the card)

MEASURED, `gpu_j0.001.log`: 10 checks, 0 failed.
- **The tools and the build:** B0 (the 159 staged files match `EXPECTED.sha256`), B1 (the tools) and B2 (BUILD PASS) pass. `ldd` names `libcudart.so.12` in HIP_CUDA's lib64.
- **The controls,** run first:
  - `hip:1` is refused: "no such device (3)", and the runtime "sees 1";
  - depth 4,096 is refused with status 2;
  - `--expect-device "NVIDIA GeForce RTX 4070"` stops the driver with exit 5 before any image line.
- **The checks:**
  - K1: 41 of 41 images load at depth 512;
  - K2: the device line names "NVIDIA GeForce RTX 5060 Ti", sm_120, 1 visible device, `CUDA_VISIBLE_DEVICES=1`, platform nvidia and HIP_ARCH 120;
  - K3: the caps give backend hip, `seq_features` 0x7ff1f and `max_scratch` 512;
  - K4: nvidia-smi's index 1 names the 5060 Ti before and after.
- **The device line** is kept in `gpu\r1\out\j0.001\j0.json`, with its bus redacted. It also gives 36 multiprocessors, 16,283 MiB, runtime 12090 and driver 13040. The `seq` kernel uses 64 registers and 16,864 bytes of local memory a thread.
- `cft_build_id()` is "unknown", since the build is from an archive, not a git tree. The build is named instead by `j_run`'s SHA-256, in J0's log and `j0.json`. The later modes record the device line, the caps and the images' SHA-256, not the binary's. They ran from the build J0 made: the lead read its SHA-256 again in cft-gpu after J3, `b3a75460c6240473a892430e763729d9d2d7104743577dfb72d011e70f5a6475`, last modified at J0's build, 14:28:15 (MEASURED by the lead, 17:07:46). *(Corrected at the merge: it said the SHA-256 is one "which every later mode carries"; see section 13.)*

## 5. J0c: the calibration (the card)

MEASURED, `gpu_j0c.001.log`, 12 checks, 0 failed. A step's time is the larger of its two calls.

| format | s | 8 lanes (ms) | 2,048 lanes (ms) | warm-up (ms) |
|---|---|---|---|---|
| binary64 | 1 | 73.2, 72.9 | **138.67**, 131.61 | 100.3, 98.9 |
| binary64 | 2 | 142.9, 142.7 | 235.48, 226.12 | 168.7, 166.8 |
| binary128 | 1 | 87.7, 88.1 | **166.20**, 158.64 | 113.9, 110.5 |
| binary256 | 1 | 121.6, 121.3 | **239.68**, 235.44 | 150.2, 143.0 |

- **The stop rule** stopped binary64 at s = 2, and binary128 and binary256 at s = 1.
- **The choice is s = 1,** which the rule uses even where it is over 150 ms.
- **The chunk did not halve** at binary128 or binary256 (INFERRED). Every 2,048-lane launch was under the backend's 250-ms halving point (READ, `LAUNCH_SLOW_MS`). J2's 8,192-lane calls took four launches' time: 894.8 to 931.7 ms at binary256.

## 6. J1: bit for bit on the card

MEASURED, `gpu_j1.001.log`: 42 checks, 0 failed, "J1 PASS". Recomputed on the desktop from the copied records by `compare.001.log`: 44 checks, 0 failed.
- **(a) I1's 32 cases at s = 1** (16 lanes, 160 steps): each `.seg.bin` and `.marks.bin` equals the desktop's software-executor output of the same image, runs and INIT, and reduces to R1's hash.
- **(b) I3's day at s = 1:** one run of 64 lanes, 5,760 segments, `--keep-every 40`. At each format, 1,152 records of 8 lanes (144 boundaries × 8 batches) equal the box's records, state and lane byte, with 0 differences and 0 marks.

  | format | wall (s) | call max (ms) |
  |---|---|---|
  | binary64 | 478.7 | 96.3 |
  | binary128 | 586.4 | 109.8 |
  | binary256 | 819.2 | 151.9 |

- **The controls** each fail as they must:
  - C-J1 (lane 21's x one ulp up, binary256, one hour): exactly lane 21 differs, at all 6 boundaries;
  - C-J2 (degree 2 against degree 7): 64 of 64 lane-boundaries differ at each of four formats;
  - C-J3 (one byte flipped in a copy of batch 3's file): exactly (batch 3, record 77, lane 2) is reported.
- **The device:** none of the 65 stdout files of the card's runs (J0's controls aside) names a device line other than J0's (`compare.001.log`).
- **Marks:** 0 on the card in J0c, J1, J2 and J3. All 64 of the card's `.marks.bin` files are empty (MEASURED, the ledger's copies), and `replay.002.log` replayed 0. Its self-test, the interpreter against the executor on 3 lane-segments, passes.

## 7. J2: the rates (the card)

MEASURED, `gpu_j2.001.log`. X = B × 15 s × s × the timed calls / the timed wall time, the timed region running from the first call after the warm-up to the last call's end. The thresholds were `--mem-max-mib 64 --util-max 10`, from the lead's idle readings (12 MiB, 0%, P8).

**X by batch, s = 1** (object-seconds a second):

| format | 512 | 2,048 | 8,192 | 32,768 | best batch: median of 3 (range) |
|---|---|---|---|---|---|
| binary64 | 59,959.7 | 233,058.6 | 233,236.6 | stopped (one call: 227,147.0) | 8,192: 233,407.4 (233,236.6 to 233,704.4) |
| binary128 | 49,630.0 | 189,867.4 | 190,797.0 | stopped (one call: 192,375.9) | 8,192: 191,230.8 (190,797.0 to 191,312.7) |
| binary256 | 34,826.1 | 134,252.7 | 134,246.5 | stopped (one call: 134,028.7) | 2,048: 134,394.9 (134,252.7 to 134,434.1) |

- **The three 32,768-lane runs, one a format, were stopped by the 1,000-ms rule** *(corrected at the merge: it said "four"; see section 13)* after one timed call each, as the lead ruled at 13:39: 2,163.9, 2,555.0 and 3,667.3 ms (MEASURED). That is 16 chunks at 135 to 229 ms a chunk (COMPUTED).
- **X levels off at 2,048 lanes,** the chunk. A launch costs about the same at any lane count up to 2,048: a 512-lane call takes 0.96 to 0.97 of a 2,048-lane one (COMPUTED from the runs' timed calls and walls: 128.1 against 131.8 ms at binary64).
- **At binary256, 2,048 and 8,192 lanes tie.** Their single runs differ by 6 object-seconds a second in about 134,250 (0.005%), and the 8,192-lane run is the one of 57.7 s. So the choice of 2,048 as binary256's best batch rests on a tie, not a margin. *(Added at the merge, from verifier-J; see section 13.)*
- **Beside the box** (rates over rates; the card's medians of 3 against DEBRIS-I's single I5 runs at 36 workers, the same program and format; COMPUTED, `analyze.001.log`):

  | format | the card | the box | ratio |
  |---|---|---|---|
  | binary64 | 233,407.4 | 92,572.5 | 2.52 |
  | binary128 | 191,230.8 | 78,197.5 | 2.45 |
  | binary256 | 134,394.9 | 59,731.8 | 2.25 |

  The card is not below the box at binary256, so decision 6 does not arise.
- **Every run that finished is valid:** J0's device line, nvidia-smi within the thresholds before and after, exit 0. The WSL VM's own busy share was 0.075 to 0.131 a run.

## 8. J3: a catalogue day on the card

MEASURED, `gpu_j3.001.log`: 7 checks, 0 failed. The lanes are DEBRIS-H's 2,688 seed objects less seed index 1595: 2,687 lanes, each call two launches (2,048 and 639). The projection ((5,760 / s) calls × 2 chunks × J0c's call time) was 26.6 and 46.0 minutes, both within J3's 60, so both formats ran the whole day.

| format | timed wall | times real time | object-seconds a second over the day | marks | call max | the 16 drawn lanes against the desktop's replays |
|---|---|---|---|---|---|---|
| binary64 | 1,499.8 s | **57.6** | 154,796.6 | 0 | 275.6 ms | 0 differences at 144 boundaries |
| binary256 | 2,583.5 s | **33.4** | 89,862.1 | 0 | 465.7 ms | 0 differences at 144 boundaries |

- The day's rate is 66.3% and 66.9% of J2's best (COMPUTED). It fits 2,687 lanes paying for two full launches a call while filling 1.31 (COMPUTED: 2,687 / 2,048; INFERRED cause, from J2's 512-lane calls).
- The desktop's replays are `j3ref.001.log`, at s = 40 on the software executor, from the base that is checked against DEBRIS-I's 2,368 INIT rows.

## 9. The desktop's load beside J2 and J3

Each J2 run's window, set against `hostload-j2.tsv` (the desktop's busy share each second, from Windows' GetSystemTimes over 12 logical processors), gives the following (MEASURED, `analyze.001.log`):
- **The first runs, to about 22:20 UTC** (15:20 local), ran beside other sessions' load (relayed in `lead.md`): means of 0.21 to 0.40, and samples up to 0.76.
- **The repeats:** the first, from 22:20:08 UTC, ran at a mean of 0.261. The six from 22:22 UTC ran at means of 0.11 to 0.16.

| best batch | X at the lowest load (busy) | X at the highest load (busy) | change |
|---|---|---|---|
| binary64, 8,192 | 233,704.4 (0.108) | 233,236.6 (0.293) | -0.20% |
| binary128, 8,192 | 191,312.7 (0.159) | 190,797.0 (0.399) | -0.27% |
| binary256, 2,048 | 134,434.1 (0.110) | 134,252.7 (0.234) | -0.14% |

- **The sign is the same in all three.** In each, the highest-load run is also that configuration's first run, so load and run order are not separated (INFERRED: a small slowdown with load, or a first-run effect, or both).
- **The lead's inference stands in this form:** the load moved J2's figures by at most 0.27%.
- **J3:** means of 0.114 (binary64, highest 0.698) and 0.082 (binary256, highest 0.544).

## 10. Limits

- **The capacities extrapolate** past the 8,192 lanes J2 ran validly. A real-time service of about 233,000 objects at binary64 would make about 114 launches a step. Under the 1,000-ms rule, the driver would have to split a step into calls of at most about 7 chunks, which j_run does not do (COMPUTED from J0c's and J2's call times).
- **J2 has three samples** of each format's best batch and one of each other configuration, all in one window, beside other sessions' load (section 9).
- **The plan's ESTIMATE of a step was low.** An 8-lane step took 73 ms at binary64 and 121 ms at binary256, and a 2,048-lane step 139 and 240 ms, against the plan's 23 and 83 ms (MEASURED against ESTIMATE). The cause of the 2,048-lane slowdown is not isolated. The `seq` kernel's 16,864 bytes of local memory a thread are a candidate (INFERRED).
- **What J3 compares:** 16 of its 2,687 lanes. J1 compares all 64 lanes of I3's day.
- **Marks:** none occurred, so the replay was exercised only by its self-test.
- **Certificates:** none written or audited (the plan). The provenance records name what one would bind.
- **The desktop's figures** are functional tests only. Phase 1 used 27.1 CPU-minutes by cycles, plus about 3.6 unmetered (ESTIMATE). Phase 2 used under 1.

## 11. What the brief got wrong, and where I departed from it (accepted by the lead)

- **DEBRIS-H's seed has 2,688 objects, one per element set,** not 2,686 (the lead's carry-over from DEBRIS-G). So J3 has 2,687 lanes.
- **The plan's step ESTIMATE was 3 to 6 times low at binary64.** Its capacity ESTIMATE, 1.3 million objects (0.43 to 3.9 million), is above the MEASURED 0.233 million. At binary256 its 0.37 million (0.12 to 1.1) holds the MEASURED 0.134. My hand-off's card ESTIMATE for J3, about 20 minutes, rested on the same basis; J3 took 68.5.
- **"The four additions"** leave out the abort, warm-up, `load` and caps lines the gates need. I placed them under additions 2 and 3, and listed them.
- **J0c's warm-up** is one 8-lane segment of the process's own image, not one at s = 1. The GPU's code is the same for every image (READ, HOSTAPI).
- **C-J1 on the card** ran one hour (6 boundaries), not a day.
- **J2's runs were capped at the 24 staged hours.** No run needed more; the longest was 2 hours.
- **One J2 run fell short of 60 s:** binary256 at 8,192 lanes ran 57.7 s. Its length was projected at 60.4 s from J0c's larger call.
- **plan-verifier-J's "offset 93"** is `cmp`'s count from 1. The byte is at 92 counting from 0.
- **"The chunk may halve there":** it did not halve (INFERRED, section 5).
- **`build_j.sh` does not print its own SHA-256.** J0's B0 checks it against the staged hash.
- **A Windows relink changes `j_run.exe`'s SHA-256,** though its sources and `libcft.a` are unchanged (INFERRED: a link timestamp).
- **`buildgate.001.log` printed my scratch's path.** The original is held in the ledger, and the repository's copy differs in that line alone (ledger `DEBRIS-J.md`, 14:11).
- **`studies\grep.exe.stackdump`** (13:26:15, untracked) is an MSYS crash dump, possibly mine. The lead leaves it.
- **The idle readings were taken during J0's build,** not before any run, and one was lost. That was the lead's slip, recorded in `lead.md` 14:30.

## 12. Not done

Not done in this round: a degree-20 program; any GPU but the RTX 5060 Ti; certificates; a repeat of J2 in a quiet window (the lead's decision, section 9); a driver that splits calls for batches over about 7 chunks.

## 13. Corrected and added at the merge (the lead, 2026-11-23)

verifier-J (Sonnet) checked this build with eight attacks of its own, and found no wrong answer. Its report is `DEBRIS-J-verifier-J-report.md`. The lead corrected two sentences and added one note, each marked where it stands. The text as reported is kept in the ledger, `filed\DEBRIS-J-build.as-reported.md` (SHA-256 `5cf6bf45fa98ab9264ec2cb6a1511d3835b965c8a59769561a5a6bcb903c199f`).
1. **Section 4, corrected:**
   - The text said `j_run`'s SHA-256 is one "which every later mode carries". verifier-J found it only in J0's records: the 65 provenance files of the later runs say `build_id unknown`, and none names the binary.
   - The sentence now says where the SHA-256 is.
   - It adds the lead's own reading of the card's `j_run` after J3: the same SHA-256, last modified at J0's build. That settles the point verifier-J could not check, that the binary did not change after J0.
2. **Section 7, corrected:** the text said "four" 32,768-lane runs. J2 ran three, one at each format (MEASURED, the lead's console `j2.001.txt` and `gpu_j2.001.log`). The lead found this at the merge. DEBRIS-J's report and verifier-J's say "four" too, and are kept as filed. The lead had also repeated it in `lead.md`, which its entry of 17:09 corrects, and to Logan, whom the lead tells at the round's close.
3. **Section 7, added:** binary256's best batch is a tie between 2,048 and 8,192 lanes, as verifier-J noted.
