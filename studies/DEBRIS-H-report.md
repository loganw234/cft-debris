# DEBRIS-H's report (phase 2)

The agent's final message, which is its report, filed verbatim by cft-debris's lead at 2026-11-21 16:34:39 -0700 with `cft-debris-ledger\dispatch\file_report.py`. Model claude-opus-5-5; final message timestamped 2026-11-21T23:34:05.470Z (UTC). Harness usage: <subagent_tokens>340033</subagent_tokens><tool_uses>98</tool_uses><duration_ms>1574081</duration_ms>. The text below is identical in the agent's own transcript and in the completion notice the lead received (as sent); a one-character change was shown to break that comparison. Body SHA-256 `e06ae8b0d39347909b4b9f7635341b16bb3dbf2d73b645d2328357f8e4cb6be5`.

---

DEBRIS-H, phase 2 report. Details are in my ledger file, `DEBRIS-H.md` (entries from 16:08 to 16:33).

H7 came out as follows: (a), (c), (d) and (f) pass. (b) and (e) fail by their letters, as Logan's rulings expected. Nothing is committed, and no process of mine is running.

**What I built** (untracked):
- **Phase 1 and the fix phase:**
  - the driver `tests/m1h.c` and the supervisor `h_service.py`;
  - the fetcher `h_fetch.py`, the check `h_check.py` and the seed `h_seed.py`, on the library `h_lib.py`;
  - the stage and build scripts, the gate scripts H0 to H6, the paced and integration tests, C17 and `h_audit.py`;
  - the fit diagnostics (`h_fitdiag.c`, `h_crlibm.c`).
- **Phase 2:**
  - `tests/h_analyze.py` (`b1136838b233`). Its log is `studies/debris-h/logs/h_analyze.001.log`, and its per-object tables are in the ledger at `debris-h/phase2/h_analyze.001/`.
  - The build report, `studies/DEBRIS-H-build.md` (4,604 words, `e308af9d…`).
  - `studies/debris-h/MANIFEST.sha256`, rewritten over all 149 files: 149 OK (MEASURED).

**The gates.** Desktop results are MEASURED; box results are READ from `lead.md`.
- **H0:** PASS. Largest angle 0.011 µas against 50 µas over 73 dates, and 15.757 µas against 1 mas over 1,000 times.
- **H1:** PASS on the desktop and on the box.
- **H2:** PASS at desktop size, 4 objects (a functional test). On the box: PASS with 16 objects and 120 steps at both kinds.
- **H3:** PASS (24 checks, C6 to C11).
- **H4:** PASS on the box: all 8,088 states bit-identical.
- **H5:** on the desktop, `.001` failed its regression because of the decoder's history, and `.002` passed. On the box: PASS on S_H0.
- **H6:**
  - On the desktop: PASS, 0 of 200 pairs differ. It used 18.8 CPU-minutes, past your line; you accepted that after the fact.
  - On the box: **FAILED**. 10 of 200 pairs differ, by up to 0.023 m, because the two C libraries round differently. Recorded as failed on Logan's word. With the desktop's fits it passes.
- **C17, the paced run and the integration test:** PASS.

**H7** (MEASURED by `h_analyze.001.log`). Before reading anything, it matched every input against its recorded SHA-256: the 91 repository copies, the 106 ledger files it reads, and all 8,660 checkpoint copies.
- **(a) PASS.**
  - 70 requests: 65 answered 200, 4 got no response, 1 got HTTP 500. No file was requested twice in a slot.
  - All 65 bodies are archived with the logged size and SHA-256.
  - The fetcher stopped at slot 16 (the second slot in a row without a response) and at slot 20 (the 500). No request followed either stop, apart from the resume at slot 18 on Logan's word.
- **(b) FAIL by its letter.**
  - I recomputed eligibility from the archived files: 6,469 sets were eligible, equal to the check tables' rows, and all of them were checked.
  - T1: 0 of 25,876 check-methods outside 1%.
  - **T3: 3 hits, at slots 5, 11 and 18.**
- **(c) PASS:** n 1,494, median 1.240 km, against the 5 km bound.
- **(d) PASS:**
  - all 8,660 checkpoint copies re-hashed on the desktop and equal to the manifest;
  - the box's audit sampled 10 segments per track and all 10 matched (READ).
- **(e) FAIL by its letter.**
  - 20 hours qualify: 19 full ones, plus the partial hour 15:00 on 11-18, with 880 steps due and none late.
  - Late steps fall in two of them: 08:00 on 11-19 (274, largest lag 915.6 s) and 08:00 on 11-20 (732, largest lag 1,304.0 s).
- **(f) PASS at T_s:** all 2,688 distances are zero. At k 17280 the median is 1.412e-5 m and the largest 7.195e-5 m; recomputed from the checkpoints, both equal the DIV line.

**The two splits** (MEASURED, defined after the data, no pass condition):
- **(e)'s split:** 18 qualifying hours began on time and hold no late step. The two 08:00 hours began behind, with backlogs of 1,419.2 s and 1,989.2 s.
- **(b)'s split:**
  - Slot 5 and slot 18 match your figures to the printed digit. Slot 11: seed indices 2684 and 2686, T3 distance 46,241.1 m, references 42,537.3 m apart.
  - In all three hits, both epochs lie within 0.35° of the ascending node, on planes within 0.35° of each other (MEASURED).
  - About 26% to 36% of checked sets in each debris group lie within 1° of the node (MEASURED). That makes the hits not swapped identities, but an assumption in T3 that fails for such pairs (INFERRED).

**Measurements** (MEASURED, all 6,469 checks, median and 90th percentile):

| method | median | 90th percentile |
|---|---|---|
| A256 | 4.888 km | 21.277 km |
| A64 | equal to A256 at the printed metre | |
| A64f | 3.422 km | 28.114 km |
| B | 0.306 km | 2.250 km |

- A256 misses less than B in only 334 checks (5.2%), and its miss is mostly along track.
- 2,076 of the 2,688 objects were checked.
- A256 was late in 58.8% of its steps, with the largest lag 2,728.5 s; A64 and A64f were never late.
- All 53 hours that do not qualify (foreign load 5.77% to 30.29%) had late steps.

**Budget** (MEASURED): wall 16:08 to 16:33; 18.6 CPU-seconds by cycles, all charged; one process at a time. B0243 was released at 16:32:49. The nine earlier records all check:
- A: 32 OK, and `debris-a` holds 29 files;
- the manifests: B 54 OK, C 136, D 73, E 60, F 61, G 43;
- no `__pycache__`.

**What I did not do:**
- Re-propagate (d2) on the desktop; the box's audit result is read, not repeated.
- Run or re-check the box gates.
- Test the INFERRED causes: that the evening load was cft-fp256's runs, and that the along-track growth comes from the fitted drag.
- Look into the large B misses of two T3 partners: idx 2612 at 71.8 km and idx 2686 at 133.6 km.
- Compare M1's decays with the catalogue.
- Commit anything, connect to the box, or request any data.

**What the brief or your message got wrong:**
- **Your message:** I found nothing wrong. All its figures agree with `h_analyze`: 70 requests, 6,469 checks, 3 hits, the decays, DIV's counts dropping at k 1400 and k 15360, the departures, the largest lag, and 19 full hours.
- **One reading differs.** H7(e) says "every clock hour", which also takes in the partial first hour, so 20 qualify. The plan does not say how partial hours count. The verdict is the same either way.
- **My own errors:**
  - Lines 50 and 80 of my ledger file contain stray control characters where I typed backslash paths through `printf`. I added a corrected entry rather than editing them.
  - The service's log line "SLOTS missed while the service was down: [17]" is my wording, and it is wrong: the service was up, and slot 17 was skipped because the fetcher had stopped.
