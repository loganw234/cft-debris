# verifier-H's report

The agent's final message, which is its report, filed verbatim by cft-debris's lead at 2026-11-21 16:54:04 -0700 with `cft-debris-ledger\dispatch\file_report.py`. Model claude-sonnet-5-5; final message timestamped 2026-11-21T23:53:30.018Z (UTC). Harness usage: <subagent_tokens>214046</subagent_tokens><tool_uses>88</tool_uses><duration_ms>749460</duration_ms>. The text below is identical in the agent's own transcript and in the completion notice the lead received (as sent); a one-character change was shown to break that comparison. Body SHA-256 `db80bbdd585e63207e55a968c28a0ad26af269ef9a5fc4808332dda06c2319fa`.

---

**verifier-H report.** I found one narrow defect and no wrong answers. Every other item I checked came out confirmed, and the rest are marked not determined or not done below.

My logs carry my own run root's hashes, not DEBRIS-H's. The stage's `EXPECTED.sha256` is 0f74d208…, equal to the build report's. Everything I wrote is in `cft-debris-scratch\verifier-H\` and my ledger file. I used about 72 desktop CPU-seconds by cycles, in `cpu.tsv`. The lead's box run cost an estimated 29 box CPU-minutes.

**Defect (narrow).**
- **What:** `studies\DEBRIS-H-report.md` and `DEBRIS-H-build.md` §5 say H7(b)'s 6,469 eligible sets were "all checked (0 listed)". Slot 16 fetched three files. Its check never ran, because the stop file was written in that slot.
- **Evidence:** `h_analyze.001.log` line 176 counts 191 sets "later than the last checked and after T_s" that were never checked. I found exactly 191 independently. Neither document mentions them.
- **Fix:** both should say "6,469 checked at slots with a check; 191 sets from slot 16 were neither checked nor listed, because the fetcher stopped in that slot". Check both documents for the word "all".
- **Effect:** (b) already fails by T3, so the verdict does not change. The claim is stronger than its evidence.

**Items.**
1. **H2's controls bite: confirmed.**
   - I ran `h_build.py` on my stage: PASS, and C1 fails as specified.
   - I ran `h2_gate.py --size desktop` (4 objects, 12 steps). C2 refuses the altered checkpoint by hash and restarts from checkpoint 4. C3 differs for 4 of 4 objects at both kinds. C4's pause shows as 35.1 s (H2c) and 30.0 s (H2n).
2. **H6: confirmed.**
   - Pairs: for 20 pairs, my miss and its radial/along-track/cross-track parts, recomputed from the printed A, B and reference states, equal the gate table exactly.
   - F6: they sit within 0.0005 m of F6's file.
   - Not re-run: the gate itself, which cost 18.8 CPU-minutes.
3. **The check's frame and time: confirmed.**
   - For 20 checks across slots 3, 5, 9, 11 and 18, my miss and parts equal the table to the printed digit.
   - `e_q` equals T_s plus the new epoch within 1.2 ms for every row of those five slots (TDB − TT).
   - The reference radius and speed fit the new set's own elements (vis-viva).
   - Not determined: the Orekit decode of the reference, which I did not re-implement. I judged the frame consistent from B and A64f both landing within kilometres of the reference.
4. **Fetch log against the policy: confirmed.**
   - There were 70 requests: 65 answered 200, 4 got no response, 1 got HTTP 500. Spacing within a slot is at least 10.0 s and slots are 10,800 s apart.
   - The first no-response slots (12, 15, 19) were followed by the next 3-hour slot. Slot 16, the second in a row, wrote the stop file. The next request was slot 18's, at 21:01:26 local, 80 s after slot 18's due time.
   - After slot 20's HTTP 500 there was no further request.
   - All 65 bodies match their logged size and SHA-256. `h_fetch.py` follows no redirect and sends `Accept-Encoding: gzip`.
   - The log line "SLOTS missed while the service was down: [17]" is indeed wrong, as DEBRIS-H says.
   - Note: the plan's own choice, a stop only on a second slot in a row without a response, goes beyond the policy's wording. It is disclosed.
5. **H7(d) with my own seed 0x7A11C5: confirmed.**
   - Log: `debris-h\box\r2\verifier-h\logs\audit.001.log`. All three tracks pass (d1), and 30 of 30 sampled segments (64 objects each) equal the next checkpoint's bytes. The sampled segments are not DEBRIS-H's.
   - On the desktop, 3 A256 segments of 6 objects each (k 0, 8000 and 17240) also equal the box's next checkpoints.
   - Note: `h_audit.py` has no planted-difference control. Its comparison can fail, but it was never shown to.
   - Note: neither audit's sample covers the two decay segments.
6. **Lag accounting: confirmed.**
   - From the 20 step logs and the service log's LOAD lines, I get 20 qualifying hours, 19 of them full. The partial hour 15:00 on 11-18 has 880 steps due and none late.
   - The late steps are 274 in hour 08 on 11-19 (largest lag 915.6 s) and 732 in hour 08 on 11-20 (1,304.0 s). Those two hours began behind, with backlogs of 1,419.2 s and 1,989.2 s.
   - The other 18 qualifying hours hold no late step. The 53 non-qualifying hours (5.77% to 30.29% foreign load) all have late steps.
   - A256 was late in 58.8% of its steps (183,045 of 311,040), with the largest lag 2,728.5 s. A64 and A64f were never late.
   - There were no pauses or restarts.
   - On the partial hour: "every clock hour" does not say whether it counts. The reading was fixed in `h_analyze.py` after the data, but it is disclosed and the verdict is the same either way.
   - Note: the service's own check jobs appear to count as foreign load. Hours with a check show 3.8%, which is conservative.
7. **Aggregates: confirmed.**
   - Over 6,469 checks and 2,076 objects, A256 has median 4.888 km and 90th percentile 21.277 km. A64 equals A256 at the printed metre. A64f is 3.422 / 28.114 km, and B is 0.306 / 2.250 km.
   - H7(c) is n 1,494, median 1.240 km.
   - A256 misses less than B in 334 checks (5.2%).
8. **Seed rules: confirmed.**
   - Rebuilt from S_H0's files: 2,699 rows, 11 dropped as sharing a set, no screen exclusions, 2,688 objects.
   - The catalogue numbers and epochs equal `seed_meta.tsv` exactly, in ascending order.
9. **Divergence: confirmed.**
   - My median, maximum and n equal the service log's DIV lines at k 1400, 8000, 15360 and 17280. At k 17280, n is 2,686, median 1.412168e-5 m and maximum 7.194537e-5 m.
10. **Repository: confirmed.**
    - I searched every new file for all 2,701 catalogue numbers from the seed and the fetched files, for object names, and for state-like hex floats.
    - The only hits are two coincidental byte counts (34026) and the shared T_s constant.
    - The T3 objects are named by seed index only. The username appears in paths, as it does in earlier rounds.
    - `src\` equals commit 1021414 (empty diff).
    - All 23 new files carry the MIT header.
11. **Splits: confirmed.**
    - T3 hits at slots 5, 11 and 18 match the lead's figures. Both epochs lie within 0.35° of the node, and the plane differences are at most 0.35°.
    - My per-group shares equal the log's, for example fengyun 25.7% within 1° (4,685 checked sets). The report's "26% to 36%" leaves out stations (24 of 24 sets).
    - Both splits are labelled as defined after the data.
12. **Departures and decays: confirmed.**
    - Absent objects per slot match: 1595 from slot 7, 2513 at slot 16, and 836 at slot 18.
    - DIV's n drops 2688, 2687 and 2686 at k 1400 and k 15360. The step logs' `D` lines agree.
    - Workers 7 and 10 are the only ones with the invalid flag (`cft_flags` 0x11), and they are the ones holding the decayed objects.
13. **Lead's part: confirmed in part.**
    - `MANIFEST.copy-003.sha256`: 9,210 of 9,210 OK. `SHA256SUMS.box`: 91 of 91 OK. `MANIFEST.sha256`: 149 of 149 OK. `SHA256SUMS`: 32 OK.
    - The phase 2 message hash is 492c0ad6…, as stated. The script hashes in the logs equal the repository's.
    - The 16:09 end entry's figures match (454.0 s, A64 at −59.9 s, zero restarts). The "back on time" times of 08:42:22 and 08:59:23 match my late-stretch recomputation.
    - Not read in full: the visit entries of 11-18 to 11-20, and `visit4c.py` to `visit8d.py`.

**What I did not do.**
- Re-run H6, H3, H4, H5, the paced run or C17.
- Read `lead.md` in full or the visit scripts.
- Re-implement the SGP4 decode.
- Re-check the attack-2 pairs beyond the 20 sampled.
- Run the `sha256sum -c` checks on `studies\debris-b` to `debris-g`.

**What the brief got wrong.** It says `h_stage.py` stages from "commit 1021414", but the script uses 1646c96. `src\` is identical at both, so this has no effect.
