# DEBRIS-K's report

The agent's final message, which is its report, filed verbatim by cft-debris's lead at 2026-11-23 09:18 -0700 with `cft-debris-ledger\dispatch\file_report.py`. Model claude-opus-5-5; final message timestamped 2026-11-23T16:17:42.720Z (UTC). Harness usage: <subagent_tokens>714762</subagent_tokens><tool_uses>230</tool_uses><duration_ms>3461269</duration_ms>. The text below is identical in the agent's own transcript and in the completion notice the lead received (as sent); a one-character change was shown to break that comparison. Body SHA-256 `a51bc84482d03bc690be54765f542b380170d785cae315dfe1d72f0c09d8364b`.

---

I've finished the study, and it answers Logan's question: yes on the CPU as a measurement campaign of tens of objects, but not yet as a forecast that beats the catalogue's own. The study is `C:\Users\logan\source\repos\cft-debris\studies\DEBRIS-K-study.md`, 6,931 words by `wc -w`. One control, K2, failed as specified; every other control passed. Nothing is committed.

**Short answer**
- **Compute is not the limit at native64** (COMPUTED from DEBRIS-G's G4 rates). 100 objects with 100 ensemble members each, re-forecast at every new set over a 30-day window, need about 0.36 of one box worker. Wide precision is the limit: ten objects with one cft256 member each need about 7.3 box workers.
- **On the pilot's 16 low-perigee objects, nothing beat SGP4 from the same latest set**, called (B'). The figures below are MEASURED median misses against later catalogue sets over 130 distinct checks:
  - (B') 4.33 km;
  - (R), M1 refitted at each new set, 6.53 km; it missed less than (B') in 30 of 130 checks;
  - (H), M1 fitted to every set so far, 6.65 km on its 60 checks, where (B') has 2.33; it missed less in 16 of 60;
  - (C), Orekit with NRLMSISE-00 and predicted space weather only, 8.27 km; it missed less in 34 of 130.
- **Only from 1 to 2 days are (R) and (H) level with (B')**: 11.12 and 10.37 km against 11.51 and 10.65 km. The reference is SGP4 of the next set, so it favours (B') by construction (INFERRED, as DEBRIS-F inferred it).
- **(H) shows no learning curve** (MEASURED). At 12 to 36 h its median is 35.3 km with 2 sets (n 4), 5.92 km with 3 or 4 (n 22) and 6.70 km with 5 to 8 (n 11). (B') has 4.19, 1.85 and 2.03 km on the same checks.

**Pilot results**
- **The sample** (MEASURED): 17 objects, the plan's count; seed index 1595 is a reconstruction only, so 16 carry misses.
  - Objects 1211, 1500 and 1538 had no new set, so they have no reference.
  - The (A) and (B) baselines are 41 rows of DEBRIS-H's check tables for 12 of these objects.
- **The controls, each fixed before the data and asserted in code:**
  - **(R)'s regression on DEBRIS-H's test seed: PASS.** All 1,088 printed values equal the target, with its decode batch replayed.
  - **T1, T2 and T3: PASS.** T3 lists 9 co-planar exceptions, all the pair 2684 and 2686.
  - **K1, the new `k_fit.c` against `m1f.c`: PASS,** the same fit line character for character.
  - **Planted bc: PASS,** bit for bit; it moves the predicted position by 571 km.
  - **Planted identity: PASS,** a miss of 11,463 km.
  - **The two-fill space-weather check for (C): PASS.**
  - **K2: FAILED as specified.** 39 of 41 check-table rows match within 1.95e-5 m. The other 2 are sets DEBRIS-H checked at slot 18 that were older than sets fetched at slot 16, which was never checked.
- **That K2 failure is a finding about the fetched data.** CelesTrak's group files sometimes go back to an older set than an earlier fetch carried. Your whole-run count (3,074 rows on 808 objects; 191 of DEBRIS-H's checks) is cited in Q4 as your MEASURED count.
- **Desktop refits against the box's seed fits** (MEASURED): convergence and iteration counts equal in all 17, with states at T_s a median of 0.0036 m apart.
- **Decay predictions** (MEASURED):
  - 1595 reconstructs at 2026-11-19 04:37:51 UTC, 4.63 h after SATCAT's day.
  - 1178's seed set gives 2026-11-21 14:40:41 UTC, inside the step where the service decayed it (E0008). 1595's time is about a second after the service's crossing step, on a different step grid.
  - 1178's newer set puts its decay 123 h before the forecast time, yet CelesTrak kept listing it. Neither 1178 prediction can be scored, since no SATCAT record was requested.
  - 1427 and 2683 show no decay within 30 days. 2686's eight predictions span 71.5 h, between 7 and 10 December.
- **Q1's candidate rule** (MEASURED) picks out 5 objects likely to decay within 30 days and 1 within 3 days across DEBRIS-H's four groups. A watch of tens of objects therefore needs the whole catalogue.
- **CPU:** 943.2 s by cycles, 15.7 of the 50 CPU-minutes (MEASURED, `cpu.tsv`). Wall time is about 1 h 10 min of the 5 h.

**Recommendation** (labelled as one in the study): build a decay watch, M1 at native64 with an ensemble, scored against SATCAT decay dates and Space-Track's re-entry (TIP) windows. Run cft256 only as a one-member audit. Don't present its positions as better than the catalogue's for these objects. It needs four of Logan's decisions (Q7's W0):
1. SATCAT decay requests.
2. Observed space weather.
3. A Space-Track account. Its documentation page carries two redistribution statements that conflict (READ (via WebFetch)).
4. A source for the whole catalogue's candidates.

If SATCAT requests are declined, nothing can be scored, and I recommend against building it.

**What I did not do**
- No ensemble run, step-halving test or JB2008.
- No request, download, box, GPU or WSL run.
- The Aerospace Corporation's pages returned HTTP 403 to WebFetch, so they are unread.

**What the brief got wrong**
- **Repeat forecasts:** the plan doesn't say how forecasts from the same set at different times count. I counted each (object, set, reference) once and wrote that rule into the code before the data.
- **(H)'s cost:** the plan's estimate of 6 to 38 CPU-minutes was high. It took 4.0, because many forecasts share a history.
- **The process limit:** "counting every child" doesn't sit cleanly with compiles. During the build, `make`, `bash` and the gcc driver sat idle above one compiler; every other stage ran one child at a time.
- **K2's premise** was my own assumption, not the brief's: I assumed the check tables used the newest set fetched.

**Other notes**
- **Ledger, `DEBRIS-K.md`:** the 08:46:42 entry holds one stray carriage return, from a backslash that `printf` swallowed. The correction is appended at 08:47:00.
- **Privacy scan:** my repository files carry no catalogue numbers and no home paths. Its one flag is Logan's name, used as in every plan.

**Checks:** all ten checks of earlier records pass (32; 29; 54, 136, 73, 60, 61, 43 and 149 OK; no `__pycache__`), and DEBRIS-K's own manifest gives 37 OK. No background work is running.

Files are in:
- `C:\Users\logan\source\repos\cft-debris\studies\debris-k\` (17 logs, the kept script versions, records, `MANIFEST.sha256`)
- `C:\Users\logan\source\repos\cft-debris\tests\k_*`
- `C:\Users\logan\source\repos\cft-debris-ledger\debris-k\` (per-object outputs)
- `C:\Users\logan\source\repos\cft-debris-ledger\DEBRIS-K.md`
