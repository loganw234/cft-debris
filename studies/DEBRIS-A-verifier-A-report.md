# verifier-A's report on DEBRIS-A (round DEBRIS-B)

The agent's final message, which is its report, filed verbatim by cft-debris's lead at 2026-11-12 16:50 -0700 with `cft-debris-ledger\dispatch\file_report.py`. Model claude-sonnet-5-5; final message timestamped 2026-11-12T23:05:57.525Z (UTC). Harness usage: <subagent_tokens>157105</subagent_tokens><tool_uses>42</tool_uses><duration_ms>741217</duration_ms>. The text below is identical in the agent's own transcript and in the completion notice the lead received; a one-character change was shown to break that comparison. Body SHA-256 `a5f618f11cb2e845e7e08dc07157ee7540bb0ff9938c46b13c76d80c81e1536a`.

---

**verifier-A report (DEBRIS-A).** DEBRIS-A's numbers reproduce. Its summary wording and several of its READ claims do not hold.

All times are wall time. Host load was heavier than the study's, at about 40% at the start of my runs. I used about 7.5 CPU-minutes of wall time as the stand-in, inside the 10-minute budget. At the end, `sha256sum -c SHA256SUMS` showed 32 OK, `debris-a` held 29 files, and there was no `__pycache__` under `studies\`.

**1. Re-run of §7, in §7's order — confirmed.**
- I ran the five `.py` files from a clean copy at `C:\Users\logan\source\repos\cft-debris-scratch\verifier-A\run\`, with `python -I -B`.
- My `port_roundtrip.py` copy points EXE at `cft-debris-ledger\tools\ias15_cft.exe`, which has SHA-256 `9d5cb048…` (measured).
- `leo_roundtrip`, `check_ref`, `var_check` and `meo_geo` match the archived logs to every printed digit.
- `port_roundtrip` matches too. At 216 steps the round trips are 3.827e-8, 8.909e-22 and 8.909e-22 m. At 864 steps they are 5.834e-8 and 1.254e-20 m. Bit-identity with REBOUND 5.1.1 at binary64 holds, and the turn-around differences (1.808e-8, 1.162e-27, 1.175e-8 m) match.
- The `.rec` and `turn` records match the archived ones in every non-header line, and `leo_j2.txt` is byte-identical.
- Timings differ with load. The port ran 124x slower than REBOUND on my run, against the study's 145x. Binary128 ran at 0.28-0.31 of binary64's rate and binary256 at 0.083, against the study's 0.33 and 0.10.
- **IAS15 at eps 1e-9 takes 12,452 force evaluations per LEO object-day** (559 steps, J2 only). With drag it takes 12,459, and with the Moon 12,382.

**2. State transition matrix check (`var_check.py`) — confirmed, with a narrower domain.**
- 0.44 (4.39e-1) and 8.0e-10 reproduce.
- The point-mass case is a real control for the variational setup and the finite-difference machinery. A broken setup would show about 1e-1 there, not 1.4e-9.
- The J2 finite difference is itself cross-checked: it matches the Jacobian-supplied variational column to 8e-10.
- The evidence is one column, one day, LEO, one conservative force (J2). The short answer's "every force a user adds" reaches past it. Drag was not tested.
- The code READ for "REBOUND linearises only its own gravity" is verified at `simulation.c:676-691`.

**3. References — defect in what the references prove.**
- Reference for the LEO tables: IAS15 at a fixed 20 s step. It agrees with the port's binary128 run (itself IAS15 at a fixed 100 s) to 4.4e-9 m.
- That reference shares the algorithm, the J2 expression and the constants with the thing it measures. It cannot show an error common to IAS15 or to the force model.
- The only independent integrators agree to about 1.5e-6 m (SABA) and 6e-6 m (JANUS). BS at 1e-13 is 5.5e-5 m off, so it is no check on a 1e-7 m claim.
- The drag and Moon references were never compared with the binary128 run, because the port has no drag. Only the IAS15 variants agreeing with one another supports them.
- The MEO/GEO reference (IAS15 at 300 s, binary64, one year) is unchecked, as §8 concedes. The 1.0e-3 m MEO figure is an upper bound on IAS15's error.
- Control I added (`verifier-A\saba_control.py`): SABA's MEO/GEO round trip with the force frozen at t=0 is 1.5e-3 to 9e-3 m. With the time dependence it is 9 to 73 km. So the time-dependence attribution holds (measured).

**4. READ claims.** All fetches were via WebFetch, so "consistent with" or "not found" is the strongest verdict. Local source lines are READ directly.
- **Verified in the local REBOUND source:** the `integrator_ias15.c`, `simulation.c`, SABA, EOS, JANUS, WHFast and leapfrog line numbers all match.
- **Consistent with:**
  - REBOUNDx main (`gravitational_harmonics.c`): `costheta2`, `f1`, the spin-axis rotation, J4's z factor and the zero-J4 skip.
  - REBOUNDx effects list: J2 and J4 only, no Earth drag, radiation with beta and PR, no shadow mentioned.
  - Orekit: every feature listed, Apache-2.0.
  - THALASSA: comparable on GTO, ten times faster on HEO "for the same accuracy". The abstract adds that it was slower on LEO, and the study omits this.
  - Levit and Marshall: 100 m/day and tenfold over SGP4.
  - Daquin: "strongly chaotic" and "unpredictable on decadal timescales". The abstract says "navigation satellites", not disposal orbits.
  - Vallado FAQ: the TEME frame relation was never officially released.
  - Cascade: 64.27 s for 30 days on 32 threads, and 4.35 h projected for 20 years. The page does not state the population size, and "LEO" and the BSTAR-to-drag wiring are only implied.
- **Not found (the cited source does not say it):**
  - ASSIST's "verified term by term against JPL": the abstract says variational equations are included for all terms, and nothing about verification.
  - The Levit-Marshall claim that TLE bias dominates below a day: not in the abstract.
  - The Vallado main page: "line 2 is mean elements" is not on it.
  - [S17] for MASTER, DELTA and LEGEND: the MIT page names DELTA and MOCAT-MC only. The MOCAT-MC arXiv text names none of them.
  - [S20]: the arXiv 2408.16805 abstract has no 15-20% figure and no "larger in storms" statement (the JB2008 paper was not opened).
- **Not determined:** [S21]. arXiv 1809.09196 is "Directed Energy Interception of Satellites". Its abstract gives no TLE figures, and its PDF came back as undecodable binary. WebFetch saved that PDF under `.claude\projects\…\tool-results\`; I did not open it. I did not check S11 beyond its abstract, S14, S19, or WHFast512's 9-particle limit.
- **54,000 objects above 10 cm:** a WebSearch summary says ESA's statistics page gave 54,000 for the 08/2024 population. ESA's 2025 report text says "over 50,000". The DISCOS page now shows 68,450 (MASTER-8, 02/2026). The study's budget is therefore stale against its own cited page, by a factor of about 1.27.

**5. Summary against the tables — two defects, one note.**
- **"Every round trip comes home to within 1.1e-6 m" — defect, the lead's suspicion is confirmed.**
  - IAS15 at MEO misses by 3.7e-5 m and at GEO by 3.7e-4 m (§2 table).
  - Other integrators miss by up to 73 km (SABA, MEO/GEO) or 8.2 m (JANUS with drag, LEO).
  - Even for IAS15 in LEO the maximum is 1.128e-6 m, which exceeds 1.1e-6 m.
  - Failure scenario: DEBRIS-B reads the sentence as covering MEO and GEO, or any integrator, and carries 1.1e-6 m into a GEO claim that is 300 times too tight.
  - It holds only as "IAS15, LEO, one day": 6.8e-8 to 1.13e-6 m.
- **"Within 1.4e-7 m of a binary128 reference" — defect, minor.**
  - `check_ref.log` gives 1.439e-07 m against binary128, which exceeds 1.4e-7.
  - The table's 1.396e-7 m is against the dt20 reference, not binary128. The sentence mixes the two.
- **The 1e-7 m sentence for drag and the Moon** holds only for eps 1e-9 (7.4e-8 and 9.2e-8 m). The eps 1e-6 rows are 2.0e-7 and 5.0e-7 m.
- **All other figures I checked match their tables:** SABA 1.5 µm to 1.6 m; JANUS bit-exact to 8.2 m; the 9 to 73 km misses; the 240x BS ratio (238); the 4e11 ratio (4.2e11); 572/39 ≈ 15; and the wall-time ranges, against the archived log.

**6. COMPUTED figures — confirmed.**
- The e-folding times redo to 25.2 years, 121.2 days and 16.3 days. These use the study's recalled Vallado densities at circular speed. The divergence is a volume rate, not a worst-direction error rate.
- The catalogue floor is 14.8 CPU-hours a year.
- 12,452 evaluations × 54,000 objects × 365 days = 2.454e11, which gives 28.4 days at 10 µs and 284 days at 100 µs.
- The JANUS lattice is 6.778e19, against 2^63 = 9.22e18.
- The pole drift is 20.01″/yr, or 9.70e-5 rad a year.
- The ring's 420 pairs are in `ROUND4.md`, and 61×3+3 = 186 holds.

**7. The lead's claims — confirmed.**
- The plan's SHA-256 matches `e2e07b05…`, the prompts match `lead.md`, and the port copy's SHA-256 matches.
- The `port_quarterday.log` figures the plan quotes (1.162e-27 and 8.909e-22 m) are right.
- `HARDWARE.md` is 647 lines, last changed at 9e9879f, and cft-fp256 has no such file.
- The lead's slip 1 is half right. 1.439e-7 m is indeed measured against binary128, but it is not "within 1.4e-7".
- I did not check `HORIZON.md` lines 111 and 218, or the tile answer.

**8. Not asked.**
- DEBRIS-A's two accuracy claims, "no measurable cost in accuracy" and "IAS15 in every regime", rest on references built from IAS15 itself. This is not a defect in the numbers.
- The SABA forward error is non-monotonic in step size in MEO (563 m at 1800 s, 245 m at 3600 s). The study does not remark on it.
- `meo_geo.py` has no main guard, so importing it runs the whole job.

**Not done:** no ledger reading beyond `lead.md`, no REBOUNDx 5406ae5 fetch, no re-derivation of the Vallado densities.
