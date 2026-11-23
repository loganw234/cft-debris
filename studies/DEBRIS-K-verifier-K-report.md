# verifier-K's report on study DEBRIS-K

The agent's final message, which is its report, filed verbatim by cft-debris's lead at 2026-11-23 09:32 -0700 with `cft-debris-ledger\dispatch\file_report.py`. Model claude-sonnet-5-5; final message timestamped 2026-11-23T16:30:22.705Z (UTC). Harness usage: <subagent_tokens>216185</subagent_tokens><tool_uses>59</tool_uses><duration_ms>446638</duration_ms>. The text below is identical in the agent's own transcript and in the completion notice the lead received (as sent); a one-character change was shown to break that comparison. Body SHA-256 `0171a9fdb2c51bfb60fc21583e8c0c1d4a848cac73533fc9d940463781770dc3`.

**This repository's copy** differs from the text as filed only in attack 8, where the two quotations of per-object values are replaced by "[a per-object value, held in the ledger]" (the lead, at the merge, 2026-11-23). The text as filed, SHA-256 `5ad986818642b488227cc2413b2429b6983644577a4355f902084ee83b3236c5`, is in `cft-debris-ledger\filed\DEBRIS-K-verifier-K-report.md`.

---

**verifier-K report.** I found one defect, which is per-object data in the repository (attack 8). The other seven attacks confirm DEBRIS-K's claims. The test escalation went out at 09:23 and the lead replied "received".

**1. Sets by forecast time: confirmed.** I used my own code on `plan.json` and `checks.003.tsv`.
- All 167 history entries behind the 5 forecast times have a fetch slot at or before the forecast.
- Each latest set is the latest by epoch among the sets fetched by then.
- Every reference was fetched after its forecast, and its epoch is later than the latest set's.
- All 646 (B′), (R), (H) and (C) rows have a horizon equal to the reference epoch minus the latest set's epoch, within the table's rounding (5e-5 h).
- (H)'s fit history equals the plan's history for its latest set.
- Seed index 1595 has no row in any table.

**2. 20 misses recomputed: confirmed.**
- I recomputed all 646 rows from the stored predicted and reference states, including the radial, along-track and cross-track parts. The largest difference from the tables is 5e-4 m.
- I looked at 20 rows chosen with seed 20261123, across variants and horizon cells.
- These states are K's own stored files, so this checks the miss arithmetic, not the propagator.

**3. Headline statistics: confirmed.**
- Every median, 90th percentile (ceil(0.9n)-th smallest), cell count and "misses less than (B′)" share matches. I also matched (H)'s learning curve (35.271, 5.920 and 6.695 km against (B′)'s 4.190, 1.848 and 2.029) and the 1 to 2 day cell.
- The counting rule is the same for every variant: 188 rows become 130 distinct checks for (B′), (R) and (C), and 82 rows become 60 for (H).
- The rule is in the first kept version of `k_pilot.py` (`3a8cd903…`), which wrote the prep log (08:43:24) and statistics log 001.
- Versions `a8fcaf1c` and `21e05a47` add only (C) and the post-hoc (H)-against-(R) block, which is labelled. Statistics log 001 matches log 003 for (B′), (R) and (H).

**4. Controls: confirmed.** I rebuilt libcft and M1 from the archive in my scratch (PASS, 46 s by cycles).
- **K1:** the `m1f` and `k_fit` FIT lines are equal, and the observations in `k1_kfit_in` equal `fit_in`'s.
- **Planted `bc`:**
  - the direct and pipeline inputs differ from the undoubled input only in `bc`;
  - my `m1f prop` output equals DEBRIS-K's line for line, bit for bit;
  - the undoubled and doubled runs differ by 571,278 m.
- **Planted identity:** one miss of 11,463 km against a bound of 66.5 km.
- **(R) regression:** I took 2 of the test seed's objects (`m1f fit` on `regress/work_fit1_1/fit_in.00.txt`). Convergence, iterations, `bc` and the state at O all equal `fit1.001.tsv`. I did not re-run the JVM decode batch.
- **K2:** it failed as specified. The 2 unmatched rows are seed indices 720 and 1000 at slot 18. Slot 16's set has an epoch about 0.9 ms later than the slot-18 set, so the slot-18 set was not kept.
- **T3:** I recomputed it independently. It gives 179 comparisons, 0 within 100 km, and 9 co-planar exceptions, all 2684 against 2686.

**5. Decay predictions: confirmed.**
- RMIN is 6,498,137.0 m, in both `m1h.c` and `k_fit.c`.
- 1595's decay time of 2026-11-19 04:37:51 UTC is 4.63 h after SATCAT's day. It uses the one set with an epoch before 11-18 00:00 UTC, fetched at S_H0 (slot 0).
- 2686's eight predictions span 71.54 h.
- 1427 and 2683 are LIVE through all 8 runs each.
- 1178's (R) prediction at slot 13 is 123 h before the forecast, and the study says so.

**6. Q6 and Q1: confirmed.**
- G4's rates are in the DEBRIS-G table: native64 1,291,561 and cft256 299 object-seconds a second on one worker.
- 100 objects × 100 members: 467,400 lane-days a day ÷ 1,291,561 gives 0.362 workers.
- 10 objects at cft256: 2,190 ÷ 299 gives 7.32 workers.
- From scratch on S_H0, Q1 gives the same counts as the study: 2,689 LEO objects, 18 with no decay signal, and point/wide counts of 0/1, 1/1, 1/3 and 5/16 at 1, 3, 7 and 30 days. τ is 1.24 d for 1595 and 18.63 d for 1178.

**7. Q5: confirmed, as READ via WebFetch.**
- `https://www.space-track.org/documentation` carries both redistribution statements: "express blanket approval" for basic SSA data, and "not to transfer any data". The fetch does not reconcile them.
- It also carries the limits of 30 requests a minute and 300 an hour, "separate account" for each user, SATCAT once a day after 17:00 UTC, TIP hourly (10 minutes near re-entry), and the 10 km wording.
- `https://aerospace.org/reentries` returned HTTP 403, as DEBRIS-K said. I tried only that URL, not its three.
- The fetch summary calls the two statements "ambiguous rather than clearly contradictory". The study's "the page does not reconcile them" fits that. The brief's word "conflict" is stronger.

**8. Repository: one defect.**
- I scanned 51 files for 4,376 catalogue numbers, all from the seed plus the pilot's. There are 0 hits outside SHA-256 hashes, so the lead's reading holds. I also found no element-set lines in the DEBRIS-K files.
- **Defect:** per-object orbit values by seed index are in the public repository.
  - `studies/debris-k/logs/k_candidates.001.log` lines 120-121, and `.002.log` lines 123-124, give for indices 1595 and 1178 the perigee and apogee ([a per-object value, held in the ledger]). Those two numbers fix an object's semi-major axis and eccentricity. The same lines give "ndot from the set" [a per-object value, held in the ledger], which is the set's `MEAN_MOTION_DOT` field.
  - `k_pilot_prep.001.log` lines 91-92 list the 17 pilot objects' perigees at T_s by index.
  - The rule says per-object logs carry "hashes, counts and aggregates, never a state or an element set". Those values should move to the ledger's `debris-k\`, with the logs keeping only the counts and τ.
  - DEBRIS-H's logs have no such per-index perigee lines (my grep found none). I did not read DEBRIS-K's study text beyond line 43 for the same values, so I did not clear the study of them.

**Notes outside the threat model:**
- "Level with (B′)" at 1 to 2 days is true of the medians only. (R) beats (B′) in 11 of 51 checks and (H) in 8 of 25.
- (H)'s 2-set learning-curve bin (n = 4) is too small to carry a conclusion.
- The planted-identity check has one reference, and its bound is easy to pass.

**What I did not do:**
- I did not re-run the fits, the SGP4 decodes (JVM), the (C) route or the decay propagation. They are recomputed only from stored states.
- I did not re-run the DEBRIS-K scan, and I did not check the study text against "logan" or personal strings, beyond finding none in the plan and study (the matches were the name as a decision-maker).
- I did not re-check the 8 file counts in DEBRIS-K's own log beyond the manifests. The ten earlier-study checks all pass: 32, 29, 54, 136, 73, 60, 61, 43, 149, and 37 for `debris-k`, with no `__pycache__`.

**Brief inaccuracy:**
- The brief says to compare the 2 unmatched rows with the slot-18 checks of "older sets". That is right, but the older epochs differ by only about 0.9 ms.

CPU: about 50 s by cycles, one process at a time. My work is in `C:\Users\logan\source\repos\cft-debris-scratch\verifier-K\`, and the ledger entry is `C:\Users\logan\source\repos\cft-debris-ledger\verifier-K.md`.
