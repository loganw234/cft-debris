# DEBRIS-I's report (phase 2's final message)

The agent's final message, which is its report, filed verbatim by cft-debris's lead at 2026-11-23 12:02 -0700 with `cft-debris-ledger\dispatch\file_report.py`. Model claude-opus-5-5; final message timestamped 2026-11-23T19:02:31.949Z (UTC). Harness usage: <subagent_tokens>886462</subagent_tokens><tool_uses>24</tool_uses><duration_ms>366919</duration_ms>. The text below is identical in the agent's own transcript and in the completion notice the lead received (as sent); a one-character change was shown to break that comparison. Body SHA-256 `514135dd96f9d41700288ba8a01af7be99caddb8a39d178b10cdfd31aaa943dc`.

---

Phase 2 is done: about 0.3 CPU-minutes (8.3 s by cycles, plus small commands) and about 6 minutes of wall time, with nothing of mine still running.

**DEBRIS-I report**

Every gate passes except C13, which failed as specified, and I6, which was not determined. The program, M1's force model without radiation pressure as a cft program at degree 7 with M1's 28 bands, matches cftc's reference interpreter bit for bit and matches M1 within every tolerance the plan fixed. The build report is `studies\DEBRIS-I-build.md`; `studies\debris-i\MANIFEST.sha256` (119 rows, SHA-256 `a28515e6…`) checks 119 OK. Figures are MEASURED by the logs named in the build report unless labelled.

**What I built** (all new files in `tests\`; nothing committed; `src\` unchanged)
- `i_gen.py` writes the program and six part systems. Every data value is a param or lane param with default 0; the 34 generated sources hold no number but 0, 1 and h = 15.
- `i_vals.py` fills each value by M1's own rounding route and fits the frame exactly.
- `i_run.c` drives libcft's executor. `m1i.c` is M1's side. `build_i.sh`, `i_harness.py` (desktop and box modes), `i_lib.py` and `i_analyze.py` (phase 2) complete the build. Part B is `i_service.py`, `i_fetch.py`, `i3_server.py` and `i_partb.py`.
- **The frame's form:** each of M's nine elements a degree-7 polynomial in s = t − tc, and Omega's three of degree 3. Each is an exact least-squares fit of M1's `frame_at` over the run's one-hour block.
- **Layout at sw:512:** gravity, bands and scalars in the bank (312 params); DE421, the frame and bc as 203 lane params.
- **Binary256 image:** 19,758 instructions, bank 425/512, scratch 378/512. **Degree 8 also compiles at sw:512** (bank 485, scratch 400), against the plan's expected refusal.

**Gates**
- **I0:** passes, after one fix.
  - libcft.a from the two archives is byte-identical.
  - M1 on 9e8ff270 equals M1 on 0aa997a3 bit for bit in all eight kind-modes, on the desktop and on the box. The line hashes are also equal across the two machines.
  - C1 and C2 bite. R1: the box's executor equals the desktop's on all 32 I1 cases.
  - P3 first failed because my harness passed a backslashed path to `sha256sum`. After the fix it passes, with a stricter C1; the failed log is kept.
- **I1:** passes. Both programs and all six part systems equal the interpreter bit for bit at all four formats, states and lane flags, with 0 marks. C3 and C4 bite.
- **I2:** passes.
  - Parts (a) to (d) and (f) equal M1's kernels bit for bit at binary64, 128 and 256 (0 of 3,000–6,000 values differ).
  - The frame (e) is at 25% and 32% of its bounds at 1,962 stage times (2.49e-13; 3.22e-15 rad/s).
  - C5 to C11 bite. One pre-data margin check (C10 at binary128) failed through my wrong estimate formula; the corrected margins all pass.
- **I3 on the box:** passes. 64 objects × 144 boundaries at each pair, t exact, 0 marks.

| pair | share of tolerance, median | largest |
|---|---|---|
| binary64 / cft64 | 2.8e-4 | 0.017 |
| binary128 / cft128 | 4.5e-6 | 1.8e-4 |
| binary256 / cft256 | 4.5e-6 | 1.8e-4 |

  - C12 bites.
  - **C13 failed as specified.** A diagnostic added after the data shows the hour-before block is read but moves positions only 3.4e-5 m in the hour, under T_frame's 1e-3 m. INFERRED cause: the block's polynomial carries its own tc, so it extrapolates well.
- **I4:** passes. testpo within 3.2e-16 AU (bound 1e-13). Lasser et al.'s tides within 1.2e-17 m/s² (Sun) and 3.9e-16 (Moon), bound 1e-11. Both controls bite.
- **I6:** not determined. The lead's cap stopped it by PID at 20 CPU-minutes, still in its sw:2048 compile.
- **Part B:** B2 and B3 pass, and their controls bite; everything ran on 127.0.0.1.

**Measurements**
- **The program's binary64 against its binary256** (position, median / largest): 2.0e-8 / 9.7e-8 m at 1 h; 3.6e-7 / 1.5e-6 m at 6 h; 2.4e-6 / 1.5e-5 m at 24 h.
- **The model gap** (M1 alone, a difference between two models; native64 = cft64):
  - the program's forces against the full model: 48 / 174 m at 1 h; 147 / 719 m at 6 h; 343 / 2,312 m at 24 h (median / largest), mostly along-track;
  - degree 7 against 20 carries almost all of it (347 m median at 24 h);
  - radiation pressure off against on: 4.0 / 18.6 m at 24 h.
- **I5:** all 21 runs valid at the first try, foreign load 0.045–0.080%, rates in object-seconds per second.

| configuration | W = 1 | W = 18 | W = 36 |
|---|---|---|---|
| program, binary256 | 4,632 | 64,332 | 59,732 |
| program, binary64 | 7,278 | 101,958 | 92,573 |

  - Against M1 at the same forces: binary256/cft256 is 2.88 at W = 1, binary128/cft128 1.61, binary64/cft64 1.14.
  - Against M1's full model (DEBRIS-G's G4): binary256/cft256 is 15.5 / 15.4 / 13.8, inside the plan's ESTIMATE of 10–30.
  - Real-time capacity at W = 36 is about 59,700 objects at binary256. That extrapolates well past the 2,304 objects actually run.

**Records and CPU**
- Per-object data are only in the ledger's `debris-i\`: the sample's list, the desktop's work files, the staged folder and the phase-2 tables.
- `i2.001.log` printed Omega's three encodings, an Earth-orientation value. It is held in the ledger, and the repository has a redacted copy.
- The earlier studies' ten checks pass. A scan of the 133 new repository files finds no catalogue number and no home path.
- CPU: phase 1 used 56.5 of the allowed 63 CPU-minutes by cycles, plus about 0.5 uncounted; phase 2 about 0.3.

**Not done**
- No redo was needed (0 marks).
- I6 is not determined.
- No GPU, no certificate, no one-band variant (28 bands fit).
- The I3 sample sets aside index 1595 (re-enters at 5.8 h; rule stated before the draw), so I3 says nothing about re-entry.

**What the brief got wrong**
- I6's box route cannot work: cftc refuses exp without mpmath.
- Degree 8 fits sw:512.
- C13's plant is too small for a frame form that carries its own tc.
- The interpreter costs about 0.055 CPU-s a lane-step, about 5 times the plan's figure.
- plan-verifier-I's re-check gives 2026-11-20 00:00 TDB as 34 days from the epoch; it is 35 days (3,024,000 s).
- My own slips, each recorded with its log kept:
  - the backslashed-path P3;
  - the C10 margin formula;
  - the Omega line in `i2.001.log`;
  - the missing worker environment, caught on the desktop before staging;
  - make's home path in `box_build.001.log`, which the lead redacted.
