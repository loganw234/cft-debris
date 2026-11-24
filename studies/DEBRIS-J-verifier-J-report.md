# verifier-J's report

The agent's final message, which is its report, filed verbatim by cft-debris's lead at 2026-11-23 17:07:23 -0700 with `cft-debris-ledger\dispatch\file_report.py`. Model claude-sonnet-5-5; final message timestamped 2026-11-24T00:06:47.046Z (UTC). Harness usage: <subagent_tokens>218905</subagent_tokens><tool_uses>63</tool_uses><duration_ms>790479</duration_ms>. The text below is identical in the agent's own transcript and in the completion notice the lead received (as sent); a one-character change was shown to break that comparison. Body SHA-256 `6c85fcb09605c8772d65d6cf1f3c9d9956a981659ac8e32e8e3897554c3e6f88`.

**This repository's copy** differs from the text as filed in two ways only (the lead, at the merge, 2026-11-23):
- where the text names a folder on the desktop by its full path, the folder that holds the repositories is written `<root>`, in 3 places;
- in attack 8, its quotation of the private LAN address prefix is written in words.

The text as filed, SHA-256 `98dbf5ced3f65f92bb1a55cb102e961aa2de84ad3156bf612bd8579fdd48351c`, is in `cft-debris-ledger\filed\DEBRIS-J-verifier-J-report.md`.

---

**verifier-J report (2026-11-23, 17:07)**

Attacks 1, 2 and 4 to 7 are confirmed by my own re-runs. Attack 3 is confirmed from the card's files, and attack 8 by a scan of the repository files. I found one defect, a false sentence in `studies\DEBRIS-J-build.md`.

**Defect (build report, section 4).** The passage reads: "The build is named instead by `j_run`'s SHA-256, which every later mode carries." That is false.
- Only J0's records carry `b3a75460…`: `gpu_j0.001.log`, `out\j0.001\build.txt`, `j0.json` and the lead's J0 console.
- A grep of the ledger's card copy finds it in none of the J0c, J1, J2 or J3 logs or provenance files.
- All 65 provenance files say `build_id unknown`, so the later steps have no per-run record of the binary. They name only the device line, caps and images.
- It should say: "`j_run`'s SHA-256 is in J0's log and `j0.json`; later steps record the device line, caps and image hashes, and ran from the build J0 made."
- This is outside the plan's threat model, so it is a note rather than a loop-reopener. It belongs in the threat model's "same build" item, though.

**Attack verdicts**

1. **Driver: confirmed.**
   - The `diff` of `j_run.c` against `i_run.c` shows only the four stated additions, plus the name strings and the `out_w` write checks.
   - I built `j_run` and `i_run` from the archive with `build_j.sh desktop` (`j_run.exe` ffc04d3a…, a relink of DEBRIS-J's).
   - On four of I1's cases I chose, `.seg.bin` and `.marks.bin` are identical between the two drivers, and each `.seg.bin` equals R1's hash:
     - part-bodies-fp256: 2b70fd2c…
     - program-d2-fp32: a132d8de…
     - part-central-fp128: 6a18edc6…
     - part-frame-fp64: 231e94e2…

2. **E1: confirmed.**
   - I recompiled three images with `cftc`. All three have SHA-256s equal to DEBRIS-J's staged ones, and each differs from DEBRIS-I's 40-step image in one byte, the REPEAT count.
   - My own reducer gives R1's hash for program-d2-fp256 at s=1 and part-grav-fp32 at s=1, and `--keep-every 40` equals the reduced output.
   - The program at fp256, s=4, on I3 batch 0 for 2 hours: the reduced output equals the box's first 12 records byte for byte, `--keep-every 10` is equal, and there are 0 marks.
   - A flipped-byte control changes the hash in both I1 cases.

3. **Device: confirmed, with one note.**
   - All 65 card provenance files carry one identical device line: RTX 5060 Ti, sm_120, "of 1 visible", `CUDA_VISIBLE_DEVICES=1`, and identical caps.
   - J0's controls: `hip:1` gives exit 2, depth 4096 gives exit 2, and the wrong device name gives exit 5 before any image loads.
   - J0c followed its stated rules: the ladder stops, the 150-ms rule and the s=1 choice.
   - The `build_id unknown` note is the defect above.

4. **J1: confirmed.** For global lanes 13, 38 and 50 at each of fp64, fp128 and fp256, I compared 432 records each, state and lane byte, and found 0 differences.
   - The card's INIT equals my own join of DEBRIS-I's eight batch files.
   - The card's runs file equals the box's runs with each run's segment count times 40.
   - Lane 13's fp256 state differs at all 144 boundaries, so the comparison is not trivially equal.

5. **Controls: confirmed**, using choices of my own.
   - C-J1: lane 44, word y, one ulp up, fp256, 1 hour. Exactly (44, boundaries 1 to 6) differs.
   - C-J2: degree 2 against degree 7 at the 40-step image differs at 64 of 64 lane-boundaries at fp32, fp64, fp128 and fp256.
   - C-J3: a flip at batch 6, record 101, lane 7 is reported as exactly that.

6. **J2: confirmed.**
   - X = lanes × timed calls × s × 15 / (`timed_end_ns` − `timed_start_ns`), taken from each of the 18 provenance files. Every value equals the log's.
   - The medians are 233,407.4, 191,230.8 and 134,394.9.
   - The ratios to I5 at W=36 are 2.521, 2.445 and 2.250.
   - The 57.67 s run, the four stopped 32,768-lane runs and the 0.075 to 0.131 VM-busy range match the report.
   - Note: at binary256, 2,048 lanes is the "best batch" by 6 object-seconds a second out of 134,250 against 8,192, which is a tie. The 8,192-lane run is one short run (57.7 s).

7. **J3: confirmed.**
   - The draw and seed indices equal the plan's.
   - My own join of the base minus seed 1595 reproduces J3's INIT hashes at both formats, and the base rows equal DEBRIS-I's INIT for the 64 I3 objects.
   - The card's 16 drawn lanes equal the staged desktop references (0 differences at 144 boundaries, both formats). Four of the 16 lanes sit in the second 639-lane chunk.
   - I replayed four lanes myself on the desktop (fp64 lanes 14, 1008 and 2328; fp256 lane 1905): 0 differences, 0 marks.
   - 86,400 / 1,499.75 = 57.6 and 86,400 / 2,583.5 = 33.4.

8. **Repository: confirmed.** Across 45 files I found no catalogue number, state, data value, GPU bus or private LAN address.
   - The repository copy of `j0.json` has its bus redacted, and the other ten card copies equal the ledger's.
   - Note: the plan (`studies\DEBRIS-J-plan.md`) has four `C:\Users\logan\…` lines and the `/root/lead-gpu5060.lock` path. Committed plans from H, I and K carry the same lines, so I treat that as convention, not a defect.
   - Note: `tests\j_harness.py` and five kept versions contain `/root` and `C:/Users` only as the redaction code's own patterns.
   - `MANIFEST.sha256` verifies 38 of 38 files.

**Records check.** All twelve come out as expected: 32 OK, debris-a has 29 files, B/C/D/E/F/G/H/I/K show 54/136/73/60/61/43/149/119/37 OK, and there is no `__pycache__`.

**Budget.** CPU was about 4 minutes by cycles (212 s metered, plus about 30 s before the counter file was reset), plus the unmetered desktop build. That is well under 25 minutes. I used no card time and made no requests to the lead. Under 20 minutes of wall time.

**Not done.** I did not check that the card's `j_run` binary is unchanged since J0, because I can't read it. I did not repeat J2. Under attack 1, I did not run the abort and `load` paths.

**Files.** My logs and scripts are in `<root>\cft-debris-ledger\debris-j\verifier-j\`. My ledger entry is `<root>\cft-debris-ledger\verifier-J.md`. My scratch is `<root>\cft-debris-scratch\verifier-J\`.
