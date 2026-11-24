# DEBRIS-J's report (phase 2)

The agent's final message, which is its report, filed verbatim by cft-debris's lead at 2026-11-23 16:50:20 -0700 with `cft-debris-ledger\dispatch\file_report.py`. Model claude-opus-5-5; final message timestamped 2026-11-23T23:50:07.294Z (UTC). Harness usage: <subagent_tokens>744235</subagent_tokens><tool_uses>26</tool_uses><duration_ms>377728</duration_ms>. The text below is identical in the agent's own transcript and in the completion notice the lead received (as sent); a one-character change was shown to break that comparison. Body SHA-256 `116a3bb864e9f6ef42272e5650e460b933ff8116c9ed265c67d9027c2ced7a96`.

---

DEBRIS-J's phase 2 is done. The card gives the box's bits exactly on everything compared, and its rates are measured. The build report is `studies\DEBRIS-J-build.md`, and the manifest is `studies\debris-j\MANIFEST.sha256`: 38 files, all verify. Nothing is committed.

**What I built** (MIT headers, not committed):
- **`tests\j_run.c`:** `i_run.c` with the four additions:
  1. `--artifact`;
  2. the device line, checked against `--expect-device` (exit 5 before any image loads), the caps, and a `load` mode;
  3. a provenance record, each call's time, a warm-up call, and `--abort-ms` (exit 6);
  4. `--keep-every`, with the lane bytes OR'ed between records.
- **`tests\build_j.sh`**, **`tests\j_harness.py`** (desktop, card and phase-2 modes) and **`tests\j_gpu.sh`**.
- **73 images** compiled from DEBRIS-I's sources unchanged. The 32 at s = 40 have DEBRIS-I's SHA-256.

**Gates** (MEASURED from logs; the desktop's are in `studies\debris-j\logs\`, the card's in `studies\debris-j\gpu\r1\logs\`):
- **E1 passes** (86 checks, 0 failed):
  - all 41 image pairs differ in one byte, the REPEAT count's, and their banks are identical;
  - I1's 32 cases at s = 1 reduce to R1's hashes;
  - s = 2, 4 and 8 reduce to the box's records;
  - the control fails, as it must.
- **j_run's desktop gate passes** (72 checks): it writes i_run's bytes on all 32 cases.
- **The desktop controls** C-J1 to C-J3 fail as specified.
- **J0 passes** (10 checks): the build, three device controls, 41 of 41 images loaded. The device line names "NVIDIA GeForce RTX 5060 Ti", sm_120, 1 visible. The caps give backend hip and `seq_features` 0x7ff1f.
- **J0c** (12 checks) chose **s = 1**. The 2,048-lane calls took 138.67, 166.20 and 239.68 ms at binary64, 128 and 256.
- **J1 passes** (42 checks; my desktop recomputation from the copied records, 44 checks, 0 failed):
  - I1's 32 cases on the card equal the software executor byte for byte;
  - I3's day for 64 lanes equals the box's records at every 40-step boundary at all three formats: 1,152 records each, 0 differences;
  - C-J1 to C-J3 bite on the card.
- **Marks:** none anywhere. All 64 of the card's marks files are empty, so 0 were replayed; the replay self-test passes.
- **J3 passes** (7 checks): the 16 drawn lanes equal the desktop's replays at all 144 boundaries, at both formats.

**Measurements** (MEASURED unless labelled):
- **J2, X in object-seconds a second at s = 1,** the median of 3 runs of each format's best batch:

  | format | X (range) | the box's 36 workers | card over box |
  |---|---|---|---|
  | binary64 | 233,407.4 (233,236.6 to 233,704.4) | 92,572.5 | 2.52 |
  | binary128 | 191,230.8 (190,797.0 to 191,312.7) | 78,197.5 | 2.45 |
  | binary256 | 134,394.9 (134,252.7 to 134,434.1) | 59,731.8 | 2.25 |

  The ratios are COMPUTED, rates over rates. X stops rising at 2,048 lanes, one chunk: a 512-lane call costs 0.96 to 0.97 of a 2,048-lane one (COMPUTED). The four 32,768-lane runs were each stopped by the 1,000-ms rule after one call, of 2.2 to 3.7 s, as ruled.
- **J3, the catalogue day of 2,687 objects:**
  - binary64: 1,499.8 s, **57.6 times real time**;
  - binary256: 2,583.5 s, **33.4 times real time**.

  Over the day the rate is 66.3% and 66.9% of J2's best (COMPUTED). That fits each call's second, 639-lane launch costing nearly a full one (INFERRED).
- **The desktop's load, run by run, against J2** (`analyze.001.log`): in each best batch, the highest-load run was 0.14% to 0.27% slower than the lowest. Each of those runs was also its batch's first, so load and run order are not separated. The lead's inference holds as "at most 0.27%".
- **CPU:** phase 1 used 27.1 CPU-minutes by cycles plus about 3.6 unmetered (ESTIMATE); phase 2 used 2.7 s by cycles. The twelve record checks all pass.

**What I did not do:**
- I did not show that about 233,000 objects at binary64, or 134,000 at binary256, can run in real time. That extrapolates past the 8,192 lanes run validly, and j_run would have to split a step into calls under 1,000 ms, which it does not do.
- No certificates; no repeat of J2 in a quiet window; no degree-20 program and no other GPU.
- No mark was replayed, since none occurred.

**What the brief got wrong** (your departures list, accepted):
- **2,688 seed objects**, not 2,686, so J3 had 2,687 lanes.
- **The plan's ESTIMATE of a step was 3 to 6 times low at binary64** (MEASURED 73 ms for 8 lanes and 139 ms for 2,048, against 23 ms). Its capacity ESTIMATE of 1.3 million objects at binary64 is far above the MEASURED 0.233 million. My J3 card-time ESTIMATE, about 20 minutes, rested on the same basis; J3 took 68.5.
- **The "four additions"** leave out the abort, warm-up, `load` and caps lines the gates need.
- **J0c's warm-up** used each process's own image, not s = 1.
- **C-J1 on the card** ran one hour, not a day.
- **J2's 24-hour cap** was never reached.
- **One J2 run was 57.7 s,** short of its 60 s.
- **"Offset 93"** is 92 counting from 0.
- **The chunk did not halve** at binary128 or binary256 (INFERRED).
- **`build_j.sh` does not print its own SHA-256.**
- **A Windows relink changes `j_run.exe`'s SHA-256.**
- **`buildgate.001.log`'s scratch path** was redacted in the repository's copy, with the original held in the ledger.
- **`studies\grep.exe.stackdump`** is still there, possibly mine.
