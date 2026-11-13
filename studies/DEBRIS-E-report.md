# DEBRIS-E's report

The agent's final message, which is its report, filed verbatim by cft-debris's lead at 2026-11-13 06:54 -0700 with `cft-debris-ledger\dispatch\file_report.py`. Model claude-opus-5-5; final message timestamped 2026-11-13T13:54:42.287Z (UTC). Harness usage: <subagent_tokens>771479</subagent_tokens><tool_uses>311</tool_uses><duration_ms>4338934</duration_ms>. The text below is identical in the agent's own transcript and in the completion notice the lead received (as sent); a one-character change was shown to break that comparison. Body SHA-256 `9d9889021534248276cafa1435331ca510530d5976be4af5f917cba6064de887`.

---

I built M1 and ran gates E1 to E9: every gate passes as finally specified, but two controls and one first gate run failed as first written. E7 passes against a referee that turns out to be good only to about 0.2 m on this model. Nothing is committed and nothing is verified yet.

**Built** (in `src\`, `tests\`, `studies\debris-e\` and `studies\DEBRIS-E-build.md`; every source carries a cft-debris / MIT header):
- **One physics source.** `src\m1_physics.h` is compiled once for each of six kinds: native32, native64, and cft32 to cft256 (libcft's software backend). I used C11 with a header included once per kind, rather than templates, because each kind's object file then stays visible on its own (reasons in `m1_kind.h`).
- **The native kinds** are built with `-ffp-contract=off -mfma`. Every FMA goes through `_mm_fmadd_sd`/`_ss` and every square root through the intrinsic. `FLT_EVAL_METHOD` and FMA3 are checked.
- **The number layer** works on batches of lanes, and branches on data are selects.
- **Constants** enter each kind once from their decimal strings, with sources in `m1_consts.h`. Derived tables are computed in each kind from exact integers.
- **New code:** a DE421 binary reader in C (the host picks each lane's record; the sum runs in the kind), and a `.gfc` loader that keeps the decimal strings.
- **The force model:** central term, EIGEN-6C4 to degree 180, Sun and Moon, 28-band co-rotating drag, conical-shadow radiation pressure, uniform rotation. rk4 runs on one shared time grid, and a run restarted from any boundary state is bit-identical.

**Gates** (all MEASURED; logs in `studies\debris-e\logs`; final build 3 unless noted):

| gate | result |
|---|---|
| **E1** | PASS: native equals cft bit for bit at binary64 and binary32 on 166,103 constant and table entries and on 7 exact kernels × 10,000 lanes (degree 180: 64 lanes). The transcendental kernels also match once routed to libcft (a run-time switch, not a separate binary). Degree-2 hand check: 1.4e-15 relative. The negative control broke only cos C (3,264 and 3,246 lanes), and the gate named where. |
| **E2** | PASS: 8 lanes × 100 steps of 60 s, all forces: native64 = cft64 and native32 = cft32 at every step. |
| **E3** | PASS: cft128 is at most 7.6e-26 m from cft256, against a bound of 6.2e-20 m stated beforehand (an estimate-based bound, not rigorous). The control broke it by 6.3e9 times. |
| **E4** (build 2) | PASS against Lasser et al. (tolerance 1e-11 m/s²): gravity, degrees 2–180, within 2.28e-15 m/s² (native64 and cft64, all 2,880 epochs; native64 = cft64 bit for bit) and 1.49e-15 (cft128/256, every tenth epoch). Sun 1.3e-17, Moon 4.3e-16. The degree-173 control was reported at 98× the tolerance. 478 CPU-s, within the approved 15 minutes. |
| **E5** | PASS: 109 testpo points (Earth, Moon, Sun, SSB, EMB) within 4.9e-16 AU at cft64 and 4.2e-16 at cft128/256, against 1e-13. |
| **E6** | PASS against Orekit on 1,000 states with matched inputs: gravity 7.3e-17 m/s² (tolerance 1e-14), drag 6.8e-14 relative (1e-9), radiation 1.3e-15 relative in sunlight and exactly 0 in umbra. Penumbra (3 states) is reported only. The three 1% plants all broke their tolerances. |
| **E7** | PASS: rk4 at 5 s is 0.114 m from IAS15 at ε 1e-9 (tolerance 0.5 m). The J2 plant gave 1,110 m. |
| **E8** | PASS: all six kinds reproduce across two runs; `-O0` equals `-O2`; the contracted build differs (647 and 706 of 808 lane-steps); five restarted segments equal the continuous run. |
| **E9** | Measured in window B0030 at 5–35% host load. Per lane-evaluation (object-day at rk4 15 s): native64 2.0–5.5 µs (0.05–0.14 s), cft64 2.2–3.3 ms (55–97 s), cft256 9.5–13.5 ms (222–340 s). Most of the cft cost is the six correctly rounded transcendentals each lane needs. |

**Controls and first runs that failed, and what I did next:**
- **E2's control as worded** (one ulp in lane 3's x) failed: rounding absorbed the ulp in the first step, as x crossed 2^20 m. I added a replacement stated before its data, the ulp in z, which passes. The x plant stays reported as failing.
- **E5's control** failed: I planted the coefficient in x, but the test point checks z. Planted in the right coordinate, exactly that point was reported (6.6e-12 AU).
- **E6's gravity check failed on its first run** at 7.5e-11 m/s². My matching was wrong: Orekit's frame turned on TAI seconds (`durationFrom`) while ours turns on TDB. After matching, it passed with the criterion unchanged.
- **E7's first run crashed** on REBOUND 5's API for setting ε. Fixed and re-run.

**Native against cft, in ulps:**
- Exact kernels: 0 ulps everywhere.
- With the C library's functions at binary64: sin/cos differ in 5 of 10,000 lanes by 1–2 ulps. asin/acos differ in 12 of 10,000 lanes, all of them penumbra lanes, by up to 1.2e10 ulps (ν moves by up to 1.4e-6 relative). exp: 0 lanes. At binary32: 0 in every kernel.
- Whole runs with the C library: no step differed.
- The C library's `fma`, built without `-mfma`: 6,559 of the lead's 20,000 cases are not correctly rounded; `vfmadd` and `CFT_FMA` get 0 wrong. My checker's own control (unfused a·b + c) was caught on 5,094 cases.

**Not settled:**
- **IAS15 is not a fine referee here.** It moves 0.21 m between ε 1e-9 and 1e-10 on this model because it does not resolve the shadow's edges: 3.8e-5 m with radiation pressure off, 1.1e-6 m with the model fully smooth. On the smooth model about 2e-5 m between rk4 at 0.625 s and IAS15 is still unexplained.
- **Binary64 against binary128 over one orbit is 3.6e-6 m,** almost all from one lane that starts exactly on a band edge of the atmosphere table. That this comes from the table's small density step there (7.7e-6 relative) is my belief: the size fits, but no run isolated it.
- **E3's bound** is an estimate, not a rigorous bound.

**Not done:**
- velocities in E5;
- E4 re-run on the final build (only the driver changed between builds; the physics sources predate both);
- measuring peak memory (computed at about 220 MB for the largest batch);
- naming `m1x.dll`'s hash in the E7 diagnosis logs;
- any certificate.

**What the brief got wrong:**
1. A one-ulp plant is not guaranteed to survive a step, so E2's control as worded can fail on a correct build.
2. IAS15 at ε 1e-9 does not referee a shadowed model to DEBRIS-D's 4e-7 m.
3. E2's "how the difference grows" had nothing to measure: the C library agreed on every call in that run.

I also slipped in E9's criteria text, which says DEBRIS-D never timed add and multiply; it did. The log can't be edited, so the correction is in the build report.

**Budget:** 1 h 13 min of wall time and 31.6 CPU-minutes counted by cycles, plus about 1 uncharged minute (estimate). The earlier studies' records all check (32, 29, 54, 136, 73 OK, no `__pycache__`), and `studies\debris-e\MANIFEST.sha256` gives 60 OK. Nothing of mine is still running.

The build report is `C:\Users\logan\source\repos\cft-debris\studies\DEBRIS-E-build.md` (SHA-256 `636ed5cd…`).
