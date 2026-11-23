# DEBRIS-K study: thorough forecasts for a small set of objects, decaying LEO objects first

cft-debris, MIT licence. Written by DEBRIS-K, 2026-11-23, under its plan of record (`studies\DEBRIS-K-plan.md`, draft 3, SHA-256 `b05a736e…`). The repository's copy of the plan differs from draft 3 only on the two lines that gave one per-object value: each now says the value is held in the ledger, and one says it is positive and inside F6's range. Draft 3 as approved is held at `cft-debris-ledger\debris-k\held\DEBRIS-K-plan.draft-3.md` (narrowed at the merge).

Labels: MEASURED (a run's own output, with its log in `studies\debris-k\logs\`), COMPUTED (arithmetic from labelled inputs), READ (a named record), READ (via WebFetch) (a model's summary of a web page: "consistent with", never "confirmed"), INFERRED (a reading no run isolates), BELIEVED, ESTIMATE (with its basis and range).

Objects are named by their index in DEBRIS-H's seed; catalogue numbers, states, element sets and per-object tables are in the ledger's `debris-k\` only. **Every check's reference is the catalogue: a later element set through SGP4. A miss is a distance from that reference, not an error against the object in the sky.** No desktop time is reported as a measurement; CPU figures are the budget's accounting, by cycles.

**Checked by verifier-K, 2026-11-23** (`cft-debris-ledger\filed\DEBRIS-K-verifier-K-report.md`).
- It confirmed the sets used at each forecast time, all 646 misses recomputed from the stored states, every headline statistic, the controls re-run at small size, the decay predictions, Q6's and Q1's arithmetic, and Q5's quotations against the pages.
- It did not re-run the fits, the SGP4 decodes, the (C) route or the decay propagation, and it did not search the text past Q1 for per-object values.
- It found one defect: per-object orbit values by seed index in three of the logs. The repository's copies no longer carry them, and the originals are held in the ledger's `debris-k\held\`.

At the merge the lead narrowed 24 passages and wrote this note. Each is marked "(narrowed at the merge)" and listed in the last section. The text as DEBRIS-K reported it (SHA-256 `8ec59c6e6ee4417ac289ee5488414bf6257247cc8f045f7aa07a6dfb4509de22`) is kept at `cft-debris-ledger\filed\DEBRIS-K-study.as-reported.md`. **One finding is the lead's own, after verifier-K:** six of the pilot's 55 new sets are a determination already kept, written in its other form, so the pilot counts some checks twice. Q3 gives each figure it changes both ways.

## Short answer

**Feasible, on the CPU, as a measurement campaign of tens of objects. Not yet as a forecast that beats the catalogue's own.** The evidence:

- **The compute is not the constraint** (COMPUTED, Q6). At native64, 100 objects with 100 ensemble members each, re-forecast at every new set over a 30-day decay window, need about 0.36 of one box worker. Wide precision is the constraint: at M1's cft256, ten objects with one member each need about 7.3 box workers. Both assume 1.5 new sets a day an object. Counting each orbit determination once, the pilot's rate is 1.3, which lowers every cost by about 13% (narrowed at the merge).
- **On the pilot's 16 low-perigee objects, nothing beat SGP4 from the same latest set** (MEASURED, Q3). (B') is SGP4 from that set. Against the next catalogue sets, over all horizons:
  - (B') has a median miss of 4.33 km;
  - (R), M1 refitted at each new set, 6.53 km; it misses less than (B') in 30 of 130 checks;
  - (H), M1 fitted to every set so far, 6.65 km; less in 16 of 60;
  - (C), Orekit with NRLMSISE-00 and predicted space weather, 8.27 km; less in 34 of 130.
  - **Counted once per orbit determination** (the lead's recount, Q3; narrowed at the merge): 112 checks. (B') has 4.82 km; (R) 6.86 km, less in 29 of 112; (H) 7.33 km on 56 checks, less in 14; (C) 9.19 km, less in 32 of 112. The order is unchanged.
  - Only from 1 to 2 days are (R) and (H) level with (B'), and only in their medians: 11.12 and 10.37 km, against 11.51 and 10.65 km on the same checks. Check by check, (R) misses less in 11 of 51 and (H) in 8 of 25. Recounted, (R) has 12.63 against 12.62 km on 44 checks, still less in 11, and (H)'s cell does not change (narrowed at the merge). The reference shares SGP4's theory with (B'), so this comparison favours (B') by construction (INFERRED, as F6 inferred it).
- **Refitting brings no learning curve here** (MEASURED). (H)'s median miss at 12 to 36 h does not fall as sets are added: 35.3 km with 2 sets (n 4), 5.92 with 3 or 4 (n 22), 6.70 with 5 to 8 (n 11), against (B')'s 4.19, 1.85 and 2.03 on the same checks. The 2-set bin's 4 checks carry no conclusion of their own. Binned by orbit determinations rather than sets, the bins hold 10, 20 and 5 checks, at 6.01, 10.00 and 6.70 km against (B')'s 4.23, 2.33 and 2.03: still no fall (the lead's recount; narrowed at the merge).
- **M1's decay times are reproducible, but have no reference to score against.** Seed index 1595's reconstruction decays at 2026-11-19 04:37:51 UTC, 4.63 h after SATCAT's date. Index 1178's seed set gives 2026-11-21 14:40:41 UTC (MEASURED). Both lie within one 15-s step of the steps in which DEBRIS-H's service decayed them (E0003 and E0008, READ). One SATCAT date is one case, not a skill.
- **A first build is laid out in Q7:** a decay watch scored against SATCAT dates and Space-Track's re-entry messages. It needs four of Logan's decisions on data (Q5, Q7).

## Q1. The candidates

**The rule** (fixed in `tests\k_candidates.py` before it was applied; MEASURED by `k_candidates.001.log`). Its version 2 (`k_candidates.002.log`) only adds the pilot's objects beside the counts, which do not change. It uses each object's latest set at each look (S_H0's, then each slot's):
- **LEO:** apogee under 2,000 km.
- **The decay rate:** the larger of the TLE's ṅ (2 × `MEAN_MOTION_DOT`, the TLE's ṅ/2 by DEBRIS-F's belief) and the change of mean motion across the object's kept sets, where their epochs lie 12 h or more apart.
- **The estimate:** ȧ = −(2/3) a ṅ / n, and τ = (a e + H_s) / |ȧ|. H_s is the scale height of M1's 28-band table at perigee, read from `src\m1_consts.h`. This is an ESTIMATE of the time to re-entry, from one scale height and one rate. I take its range as a factor of 3 either way.
- **A candidate for window W** (1, 3, 7 or 30 days): τ ≤ W ("point"), and τ ≤ 3W ("wide").

**The counts** (MEASURED):

| look | LEO objects | no decay signal (ṅ ≤ 0) | 1 d point / wide | 3 d | 7 d | 30 d |
|---|---|---|---|---|---|---|
| S_H0 (T_s) | 2,689 | 18 (BSTAR ≤ 0: 12) | 0 / 1 | 1 / 1 | 1 / 3 | 5 / 16 |
| slot 20 | 2,691 | 11 (14) | 0 / 1 | 1 / 2 | 1 / 3 | 5 / 16 |
| union of the 20 looks | | | 0 / 1 | 1 / 2 | 1 / 4 | 5 / 17 |

- **Departures:** of the first look's wide candidates, one, at every window, was absent from the last fetch that held its group. That is seed index 1595.
- **The two validation points** (one case each, not a measure of skill):
  - **1595:** τ = 1.24 d from its set's epoch, a point candidate at 3 days. That puts its re-entry near 04:50 UTC on 2026-11-19 (COMPUTED, ±7 min for τ's rounding), the day after SATCAT's date (E0005, READ), about where M1 put it.
  - **1178:** τ = 18.63 d from its seed set, whose mean elements put its perigee above 400 km. M1's propagation of that set had lowered it under 300 km by T_s, and to M1's decay sphere on 11-21 (narrowed at the merge: the per-object values are held in the ledger's `debris-k\held\`).
- **The pilot's 17** are chosen by perigee in the seed's propagated state, not by this rule. Four are 30-day point candidates and nine wide candidates. Outside them, the first look has 1 point and 7 wide 30-day candidates (MEASURED, `k_candidates.002.log`).
- **So, by the rule's point estimate, the four groups hold about five objects that may decay within 30 days, and one within 3 days.** A watch of "tens of objects" needs the whole catalogue.

**The whole catalogue's candidates** need a source beyond DEBRIS-H's four groups:
- **CelesTrak's GP queries,** by group as DEBRIS-H used them, under the usage policy as DEBRIS-H's plan records it (2026-11-16 and 11-18; no agent read CelesTrak's pages). Data update every 2 hours, and each update is to be downloaded at most once. The first response that is not HTTP 200 stops all querying. Limits are beginning to be enforced on larger sets, such as `active`. So a catalogue-wide list costs at most one large request an update, each on Logan's yes. Whether one group holds the whole debris catalogue is not known here.
- **Space-Track's GP class** with a perigee query: "Once every hour for TLEs", with an account, since "Each individual user or entity is required to obtain a separate account" (READ (via WebFetch), `https://www.space-track.org/documentation`).

## Q2. "More thorough and comprehensive forecasts": the menu

Costs are on one box worker, COMPUTED by `k_compute.001.log` from DEBRIS-G's G4 rates (MEASURED there: native64 1,291,561 object-seconds a second; cft256 299).

| item | what it buys (evidence) | cost a forecast, one object | what it needs |
|---|---|---|---|
| a refit on every new set, (R) | MEASURED: 6.53 km against (B')'s 4.33; fewer misses in 30 of 130; level from 1 to 2 d (11.12 against 11.51) | 2.14 CPU-s native64 (32 lane-days); 9,250 at cft256 | nothing new |
| a fit over the history, (H) | MEASURED: 6.65 km against (B')'s 2.33 and (R)'s 4.19 on its 60 checks; no learning curve; 4 of 33 fits on the iteration limit, against (R)'s 1 of 47 | 5.62 CPU-s native64 at 2.4-day spans (84 lane-days) | nothing new |
| a space-weather atmosphere, (C) | MEASURED, predicted space weather only: 8.27 km; fewer misses than (B') in 34 of 130, than (R) in 37; better than (R) in its medians under 6 h (0.52 against 0.66 km) and from 6 to 24 h (2.65 against 2.96 km), on the 130 checks, though it misses less than (R) in only 2 of 8 and 15 of 47 of them (the lead's count; narrowed at the merge); worse from 1 to 2 d (18.39 against 11.12); fitted Cd 0.65 to 46.9 (median 2.41), none negative | NRLMSISE-00 7.3 to 7.5 µs a call in Java, about 5 times the force budget at degree 20; JB2008 30 µs (DEBRIS-C, MEASURED there) | observed space weather (Q5). JB2008 also needs S10, M10, Y10 and DSTDTC, which `SW-Last5Years.txt` lacks (DEBRIS-D's Q7, READ) |
| an ensemble over bc and the density's scale | a decay window with stated odds. Not run here | N × 2.01 CPU-s for 30-day members at native64; 8,670 each at cft256 | priors calibrated on scored decays (Q4) |
| the step and integrator near re-entry | not measured: M1 is rk4 at 15 s throughout | a step-halving control doubles the final days' cost only | a control in the first build |
| the decay criterion | M1's rule is a sphere 6,498.137 km from the centre: 120 km above the equator, 139.8 km above the ellipsoid at 74° and 141.4 km above the poles (COMPUTED, WGS84 radii). TIP's location is where an object "is predicted to reach 10 km altitude" (READ (via WebFetch), Space-Track) | none | a geodetic criterion at a stated height |
| the six kinds as a ruler | DEBRIS-H's \|A256 − A64\|: median 1.4e-5 m after 72 h, largest 7.2e-5 m; both kinds decayed 1595 and 1178 at the same steps (READ, DEBRIS-H's report, E0003, E0008). Against misses of kilometres, precision is not the limit; the ruler audits the arithmetic and the decay step | one cft256 member: 8,670 CPU-s a 30-day forecast; DEBRIS-I's program 285 to 850 (ESTIMATE) | the program (DEBRIS-I) or a card (DEBRIS-J) beyond a sample |
| radiation pressure | 0.3 to 2% of drag at bc = 0.01 m²/kg between 300 and 400 km, less below (COMPUTED: cram × 4.56e-6 N/m² against bc ρ v², M1's band densities, v = 7.5 km/s). The fitted bc spans a factor of 77 (0.0023 to 0.18 m²/kg), wide enough to take up an error of that size from the fixed cram (INFERRED) | none | nothing |

The pilot's figures in this table are as DEBRIS-K's counting rule gives them. Counted once per orbit determination (Q3's recount), (R) has 6.86 km against (B')'s 4.82, and is level in its median from 1 to 2 d (12.63 against 12.62). (H) has 7.33 km against (B')'s 2.61 and (R)'s 4.78 on its 56 checks. (C) has 9.19 km, with fewer misses than (B') in 32 of 112 and than (R) in 31. Its median beats (R)'s from 6 to 24 h only (3.02 against 3.10 km), not under 6 h (0.77 against 0.66, n 6) (narrowed at the merge).

## Q3. The pilot hindcast

### Method, as the plan fixes it

The rules below are written into `tests\k_pilot.py`'s criteria before any miss was computed; each stage wrote one log. Its three versions are kept:
- `3a8cd903…` wrote the first five stages and statistics log 001;
- `a8fcaf1c…` added the cfit stage before any miss of (C) existed, with K2's diagnosis and a count of the slot rows not kept (descriptions, no pass condition), in log 002;
- `21e05a47…` added (H) against (R), defined after the data, in log 003.
- Logs 002 and 003 repeat log 001's figures unchanged (MEASURED, a diff), adding (C)'s; T1's count rises from 320 to 450 with (C)'s 130.

- **The objects** (MEASURED, `k_pilot_prep.001.log`): 17 seed objects have an osculating perigee under 400 km at T_s, the plan's count. 1 is under 250 km, 5 under 300 and 8 under 350. Seed index 1595 is a reconstruction only, so 16 carry misses.
- **The sets:** S_H0, then slots 1 to 20, in order. A set is kept when its epoch is later than the object's previous kept set's.
  - The new sets per object are, by seed index: 278: 6, 720: 4, 1000: 2, 1178: 1, 1211: 0, 1427: 3, 1500: 0, 1538: 0, 1595: 0, 1597: 8, 2045: 3, 2178: 2, 2679: 7, 2683: 3, 2684: 6, 2685: 4, 2686: 6.
  - **Indices 1211, 1500 and 1538 have no new set.** Their (R) is the seed set's refit, and they have no reference.
  - The slot rows not kept are these: 185 copies, 18 with a kept epoch but other fields, and 15 at an epoch older than the newest already fetched, for 6 objects (MEASURED, `k_pilot_stats.002.log`). Each of the 15 is one 1e-8-day unit (0.864 ms) older: the lead's run-wide scan holds 15 such rows on the same 6 objects, the same count for each (`cft-debris-ledger\tools\merge-k\cross15.002.log`; narrowed at the merge).
  - **The lead's count over the whole run:** 3,074 slot rows on 808 of 2,701 objects carry an epoch earlier than one already fetched. Every one is exactly one 1e-8-day unit earlier, and differs from the later row in BSTAR, and in 2,795 also in eccentricity. They are most likely one orbit determination written two ways, not older sets (the lead's MEASURED counts, `lead.md` 2026-11-23 09:04 and 09:33, from the ledger's `tools\scan-h\epoch_regress.002.log` and `epoch_jitter.001.log`; the reading is INFERRED; narrowed at the merge).
  - **Six of the 55 new sets are a determination already kept, in its other form** (the lead's COMPUTED, post hoc, `cft-debris-ledger\tools\merge-k\same_od.003.log`; narrowed at the merge). Each lies one unit after its object's previous kept set, and differs from it in BSTAR and eccentricity, one also in the node. There is one each for indices 278, 720, 2679 and 2684, and two for 1597. The keep rule took each as a new set, so:
    - index 278's check from slot 1 compares a set with its own other form, at a horizon of 0.000864 s, in (B'), (R) and (C);
    - 17 more checks count one determination twice, as two references or as two sets used;
    - 13 of (H)'s forecasts fit a history that holds one determination twice.
    The recount after the tables below counts each determination once.
- **The forecast times:**
  - T_s, 2026-11-18 22:48:50 UTC;
  - slot 1, 2.20 h later; slot 5, 14.20 h; slot 9, 26.20 h; slot 13, 38.20 h;
  - each slot's time is its fetch's end, from `slots.tsv`.
  - (B'), (R) and (C) forecast at all five, (H) at slots 5, 9 and 13.
- **The references:** each later kept set, at its epoch rounded to 2^-20 s, through SGP4, as F6 and DEBRIS-H took it. The horizon is the reference's epoch less the epoch of the set the forecast used.
- **A check** is a distinct (object, set used, reference). Forecasts at two times from the same latest set are one check, counted once.
  - **This counting rule is mine, written before the data.** The plan does not say how forecasts that repeat each other count.
  - (B'), (R) and (C) have 188 rows and 130 distinct checks; (H) has 60 distinct checks. The per-row table is in the ledger (`debris-k\pilot\checks.003.tsv`). Counted once per orbit determination, they are 112 and 56 (narrowed at the merge).
- **(A) and (B)** are the 41 check-table rows of 12 pilot objects, read from DEBRIS-H's tables.

### The controls (each stated before the data and asserted)

| control | result | evidence |
|---|---|---|
| (R)'s regression on DEBRIS-H's test seed, against `testseed\repro\fit1.001.tsv` | **PASS:** all 1,088 printed values of the 64 objects equal; convergence and iterations equal in 64. The decode batch's input matched its recorded SHA-256 `c7b17fd9…` | `k_refit_fit.001.log` |
| T1, the time tag, every check and variant | **PASS:** 450 check-variants within 1% of \|v\| | `k_pilot_stats.003.log` |
| T2, equal sets | **PASS:** 35 latest sets repeated by a later slot give (B') a miss of exactly 0. The two JVMs' inputs were byte-identical, so T2 tests the rows' equality and the decoder's repeatability, as F6's did | `k_pilot_bprime.001.log` |
| T3, swapped identities, with the co-planar exception | **PASS:** 179 comparisons, none within 100 km; 9 exceptions, all index 2684 against 2686, planes 0.0375° and 0.0646° apart (DEBRIS-H's slot-11 pair) | `k_pilot_stats.003.log` |
| K1: `tests\k_fit.c` is a faithful copy | **PASS:** k_fit's FIT line equals m1f's, character for character, on (R)'s 721 observations of index 278 | `k_pilot_rfit.001.log` |
| K2: (B') at T_s and the references against DEBRIS-H's B_pos and ref_state, 1e-3 m | **FAIL, as specified:** 39 of 41 rows match (largest 1.95e-5 m, every e_q equal). Two rows (indices 720 and 1000, slot 18) have no kept set: at slot 18 DEBRIS-H checked the other form, one 1e-8-day unit earlier, of slot 16's sets, which it never checked (my ledger 09:01:31; the lead's count: 191 such checks, all at slot 18, each one unit earlier; narrowed at the merge) | `k_pilot_stats.002.log`, `.003.log` |
| the planted bc | **PASS:** index 2683 at T_s, a reference 32.03 h later. The pipeline's state with bc doubled equals m1f prop run directly, bit for bit, and moves the position by 571,278 m | `k_pilot_rfit.001.log` |
| the planted identity | **PASS:** (H) for index 2683 fitted to index 2684's sets misses by 11,463 km, against 10 × (H)'s median, 66.5 km. It rests on one reference, and its miss is 172 times the bound, so it shows a wholesale swap, not a subtle one (verifier-K's note; narrowed at the merge) | `k_pilot_stats.003.log` |
| the two-fill check for (C), DEBRIS-F's, over 2026-11-01 to 11-22 UTC | **PASS:** the 0 and 4 fills give identical inputs at 505 epochs, and the plant changes 24. (C)'s dates, 60 h of ap history included, lie inside (2026-11-01 17:24 to 11-20 21:45 UTC) | `k_swcheck.001.log`, `k_pilot_cfit.001.log` |
| (C)'s inputs | the gfc copy equals DEBRIS-E's `bf296183…`, and the 0-filled space-weather copy equals DEBRIS-F's `47acbcc2…` | `records\k_gfc_copy.console.001.txt`, `k_swcopy.001.log` |

**Measurements beside the controls** (MEASURED, no tolerance stated):
- **The 17 seed sets refitted on the desktop against the box's seed fits.** Convergence and iterations are equal in all 17. The state at O differs by a median of 0.00068 m; the largest is 0.182 m, for 1595's flagged fit. bc differs by at most 1.1e-8 m²/kg. At T_s the median difference is 0.0036 m; the largest is 3.29 m, for 1178 after a 14.7-day catch-up. That the cause is DEBRIS-H's finding 2, the two C libraries rounding differently with the fit amplifying it, is INFERRED; no run here isolates it.
- **(R) at T_s against (A64)** on their 39 common checks: the misses differ by a median of 0.012 m, and by at most 0.078 m.

### The tables (aggregates; flagged fits in)

The miss's median and 90th percentile (the ceil(0.9n)-th smallest), in km, by horizon cell; n is the count of distinct checks.

| cell | (A64) | (B) | (B') | (R) | (H) | (C) |
|---|---|---|---|---|---|---|
| all | n 41: 29.49 / 177.39 | n 41: 19.40 / 154.93 | n 130: 4.33 / 64.43 | n 130: 6.53 / 93.74 | n 60: 6.65 / 69.10 | n 130: 8.27 / 100.13 |
| under 6 h | n 0 | n 0 | n 8: 0.054 / 0.167 | n 8: 0.661 / 1.461 | n 1: 0.871 | n 8: 0.524 / 1.555 |
| 6 to 24 h | n 6: 4.85 / 7.15 | n 6: 1.81 / 13.47 | n 47: 1.36 / 11.44 | n 47: 2.96 / 8.12 | n 30: 3.47 / 29.98 | n 47: 2.65 / 9.81 |
| 1 to 2 d | n 17: 17.72 / 70.87 | n 17: 17.73 / 61.11 | n 51: 11.51 / 51.26 | n 51: 11.12 / 45.38 | n 25: 10.37 / 86.44 | n 51: 18.39 / 56.50 |
| 2 d and over | n 18: 101.81 / 238.37 | n 18: 85.85 / 207.23 | n 24: 64.02 / 207.22 | n 24: 86.44 / 238.36 | n 4: 91.37 | n 24: 81.84 / 202.78 |

- **(A256) equals (A64) in every cell** at the printed metre, as DEBRIS-H found.
- **Without the flagged fits,** (A), (B) and (R) do not change: no check rests on a flagged fit (the one flagged (R) fit is 1595's). (H) drops to n 57: 6.43 / 63.70 km overall, n 29: 3.45 from 6 to 24 h, n 23: 6.93 / 31.69 from 1 to 2 d, and n 4: 91.37 from 2 d.
- **The along-track part** carries nearly all of every miss. From 6 h on, its size's median is within 0.03 km of the miss's median in every cell of 5 checks or more; under 6 h it is up to 0.10 km below.
- **Overall, its signed median is negative for every method, and from 2 days it is −52 to −82 km:** (B') −1.01 km overall and −52.1 km from 2 d; (R) −3.36 and −57.4; (C) −7.19 and −81.8; (A64) −16.4 and −79.4. Every method lags the next set, as it would if the objects decayed faster than predicted (INFERRED).

**The main comparisons, on the same checks** (medians in km, and the count in which the variant misses less):

| cell | (R) against (B'), 130 checks | (H) against (B'), 60 | (C) against (B'), 130 |
|---|---|---|---|
| all | 6.53 / 4.33; 30 of 130 | 6.65 / 2.33; 16 of 60 | 8.27 / 4.33; 34 of 130 |
| under 6 h | 0.661 / 0.054; 0 of 8 | 0.871 / 0.167; 0 of 1 | 0.524 / 0.054; 0 of 8 |
| 6 to 24 h | 2.96 / 1.36; 8 of 47 | 3.47 / 1.31; 7 of 30 | 2.65 / 1.36; 10 of 47 |
| 1 to 2 d | 11.12 / 11.51; 11 of 51 | 10.37 / 10.65; 8 of 25 | 18.39 / 11.51; 15 of 51 |
| 2 d and over | 86.44 / 64.02; 11 of 24 | 91.37 / 68.62; 1 of 4 | 81.84 / 64.02; 9 of 24 |

- **(A64) against (B),** DEBRIS-H's own comparison restated on these objects: (A64) misses less in 12 of 41, against 334 of 6,469 over DEBRIS-H's whole run. M1's fit beats SGP4 from the seed more often on these low objects (INFERRED from two shares; the 41 cluster in 12 objects).
- **Defined after the data** (`k_pilot_stats.003.log`): (H) against (R) on (H)'s 60 checks, 6.65 against 4.19 km; (H) misses less in 26.
- **(C) against (R)** on 130 checks: 8.27 against 6.53 km; (C) misses less in 37.
- **These shares are not of independent trials.** Checks cluster by object, and 13 objects carry them: 278, 1597 and 2679 hold 67 of the 130, and 51 of the 112 recounted (narrowed at the merge).

**Per object** (all horizons, flagged fits in: n, median in km):

| idx | (B') | (R) | (H) | (C) |
|---|---|---|---|---|
| 278 | 20: 14.55 | 20: 17.07 | 9: 29.36 | 20: 44.09 |
| 720 | 7: 61.11 | 7: 70.87 | 3: 10.61 | 7: 29.38 |
| 1000 | 3: 17.73 | 3: 27.56 | 3: 27.56 | 3: 35.72 |
| 1178 | 1: 514.95 | 1: 456.14 | 1: 456.14 | 1: 202.78 |
| 1427 | 6: 42.85 | 6: 63.84 | 3: 100.81 | 6: 11.78 |
| 1597 | 23: 1.45 | 23: 3.24 | 8: 1.88 | 23: 4.09 |
| 2045 | 6: 1.76 | 6: 7.15 | 3: 5.41 | 6: 10.36 |
| 2178 | 3: 60.76 | 3: 63.70 | 3: 63.70 | 3: 6.68 |
| 2679 | 24: 0.51 | 24: 2.85 | 11: 1.81 | 24: 4.32 |
| 2683 | 6: 7.94 | 6: 6.44 | 1: 1.68 | 6: 8.12 |
| 2684 | 12: 7.53 | 12: 7.62 | 6: 3.22 | 12: 14.59 |
| 2685 | 7: 13.72 | 7: 14.13 | 3: 10.62 | 7: 9.64 |
| 2686 | 12: 29.33 | 12: 24.54 | 6: 24.53 | 12: 44.34 |

**Objects differ more than methods do** (MEASURED, the per-object table). For example, (C) has the smallest median for 1427, 2178 and 1178 and the largest for 278 and 2686. Thirteen objects cannot show whether that is the density model or chance.

**(H)'s learning curve** (horizons 12 to 36 h, flagged in; (B') on the same checks):

| sets in the fit | 1 | 2 | 3 or 4 | 5 to 8 | 9 or more |
|---|---|---|---|---|---|
| (H) | n 0 | n 4: 35.27 | n 22: 5.92 | n 11: 6.70 | n 0 |
| (B') | | 4.19 | 1.85 | 2.03 | |

**The headline figures recounted, each orbit determination once** (narrowed at the merge). This is the lead's COMPUTED, post hoc, after verifier-K, from the ledger's per-check table (`cft-debris-ledger\tools\merge-k\same_od.py`, log `same_od.003.log`). Before it recounts, its control reproduces the 31 printed figures it compares: 30 from `k_pilot_stats.003.log`, and Q3's count of 67. A planted change of one miss makes it fail. It drops index 278's one-determination check, and counts each (object, determination used, determination referred to) once, keeping the first row in the table's order. Medians in km, and the count in which the first variant misses less:

| cell | (R) against (B') | (H) against (B') | (C) against (B') | (C) against (R) |
|---|---|---|---|---|
| all | n 112: 6.858 / 4.816; 29 | n 56: 7.330 / 2.609; 14 | n 112: 9.192 / 4.816; 32 | 9.192 / 6.858; 31 |
| under 6 h | n 6: 0.661 / 0.104; 0 | n 1: 0.871 / 0.167; 0 | n 6: 0.765 / 0.104; 0 | 0.765 / 0.661; 1 |
| 6 to 24 h | n 39: 3.104 / 1.363; 8 | n 26: 4.361 / 1.337; 5 | n 39: 3.021 / 1.363; 10 | 3.021 / 3.104; 12 |
| 1 to 2 d | n 44: 12.625 / 12.615; 11 | n 25: 10.367 / 10.651; 8 | n 44: 20.196 / 12.615; 13 | 20.196 / 12.625; 9 |
| 2 d and over | n 23: 99.489 / 64.425; 10 | n 4: 91.366 / 68.621; 1 | n 23: 67.421 / 64.425; 9 | 67.421 / 99.489; 9 |

- **(H)'s learning curve, by determinations in the fit:** 2: n 10, 6.006 km against (B')'s 4.234; 3 or 4: n 20, 10.004 against 2.333; 5 to 8: n 5, 6.695 against 2.029. (H) against (R) on its 56 checks: 7.330 against 4.776 km, less in 23.
- **Keeping the last row of each pair instead** changes no figure above by more than 0.004 km (the log's last column).
- **Dropping only index 278's one-determination check** gives 129 checks: (B') 4.457 km, (R) 6.570, (H) 6.652 and (C) 8.276.
- **Not recounted:** the 90th percentiles, the per-object table, the along-track figures, the lines without flagged fits, and (A) and (B), which are DEBRIS-H's rows.
- (C)'s comparison with (R) cell by cell is the lead's; DEBRIS-K printed it overall only.

### The decay predictions

M1's rule (`tests\m1h.c`'s RMIN, carried in `tests\k_fit.c decay`), from each fit's origin, to 30 days after the forecast time (MEASURED, `k_pilot_stats.003.log`):

| seed index | variant, forecast times | sets used | predicted decay (UTC) |
|---|---|---|---|
| 1595 (reconstruction) | (R) and (H), its 1 set with an epoch before 2026-11-18 00:00 UTC | 1 | 2026-11-19 04:37:51, 4.63 h after SATCAT's date taken as the whole UTC day 2026-11-18. The service's crossing step ends at 04:37:50.8 (E0003); this run's grid starts at the fit's origin, so its steps do not coincide with the service's |
| 1178 | (R) at T_s, slots 1, 5 and 9; (H) at slots 5 and 9 | 1 (the seed set, 13.7 d before T_s) | 2026-11-21 14:40:41, inside E0008's step (14:40:35.8 to 14:40:50.8) |
| 1178 | (R) at slot 13 | 1: its newer set, first fetched after slot 9 | 2026-11-15 09:50:22: **123 h before the forecast time** |
| 1178 | (H) at slot 13, its fit stopped on the iteration limit | 2 | 2026-11-23 12:44:26 |
| 1427 | all 5 (R); all 3 (H), each fit flagged | 1 to 3 | no decay within 30 days |
| 2683 | all 8 | 1 to 4 | no decay within 30 days |
| 2686 | (R) at T_s and slot 1 | 1 | 2026-12-10 11:46:34 |
| 2686 | (R) at slots 5 and 9; slot 13 | 1 | 2026-12-07 16:50:30; 2026-12-09 08:51:49 |
| 2686 | (H) at slots 5 and 9; slot 13 | 3; 5 | 2026-12-08 04:19:04; 2026-12-07 12:14:19 |

- **Index 1178 has no reference** (decision 2(a)). Its newest set predicts a re-entry before the run began, yet CelesTrak listed it throughout. E0006 and E0007 fit a 30-day cutoff for stale sets, so a stale set could keep a re-entered object listed for weeks (INFERRED). A SATCAT request would say, on Logan's yes.
- **Index 2686's eight predictions span 71.5 h** (12-07 12:14 to 12-10 11:46) across forecasts 38 h apart; Q1's rule puts it about a week later (τ 28.4 d). That spread measures the forecast's instability, not its error.

### Limits

- **One window:** 2.2 days of fetches, 16 objects, 130 checks (112 when each orbit determination counts once; narrowed at the merge); slots 12, 15, 16, 19 and 20 lacked groups, and slot 17 was never fetched.
- **The reference is SGP4 of the next set,** which shares (B')'s theory and is itself a fit of a falling object's tracking. Nothing here scores a method against the sky.
- **(C)'s space weather is predicted throughout:** the file's observations end on 2026-11-15, and on predicted days Orekit gives every 3-hourly ap the day's Ap (DEBRIS-F, READ).
- **No ensemble ran and no decay time could be scored;** (H)'s learning curve is not determined beyond 8 sets.
- **The fits rest on SGP4 pseudo-observations, as F6's did.** M1's fitted bc are all positive here (47 (R) fits, MEASURED), unlike F6's higher objects; that alone does not make them physical.

## Q4. The refinement loop

**What can be learned from each new set and each decay** (designed; nothing run):
- **Each object's bc,** as a series over its refits; the pilot's 47 (R) fits give one each, all positive (MEASURED). The ensemble's bc prior is that series' spread over the last k sets.
- **A density scale by height band and space-weather state,** shared across objects: one multiplier per 50 km band and Ap class, fitted on the host to every object's along-track residuals. It turns many objects' misses into one model correction.
- **A decay-time bias,** the predicted decay time less the catalogued one, binned by days before decay, learned only from scored decays.
- **Per object and shared:** objects differ by more than methods do (the per-object table), so both kinds are needed, and the holdout must tell them apart.

**Validated without fooling itself** (designed, statistics fixed before the data in each future plan):
- **A holdout by time:** fit the parameters on weeks 1 to k, score on week k + 1, and never the reverse.
- **A holdout by object:** split by breakup group or by object, since checks cluster by object (as in this pilot, where 3 objects hold half the checks).
- **The reference:** the catalogue for positions, SATCAT dates and TIP windows for decays, never the truth.
- **A planted parameter** as in this pilot: a known bc or density factor injected into a copy of the data must be recovered.

**How much data:**
- **ESA's page:** on average "two small tracked debris objects reenter per day", and objects of 1 m or more "reenter about once a week" (READ (via WebFetch), `https://www.esa.int/Space_Safety/Space_Debris/Reentry_and_collision_avoidance`): about 60 tracked re-entries a month, 4 of them of 1 m or more (COMPUTED).
- **DEBRIS-H's four groups gave one SATCAT-dated decay in 72 hours** (E0005, READ) and one M1 decay without a record (E0008). So a calibration bin of 50 decays (DEBRIS-D's Q7 rule) needs the whole catalogue for about a month (ESTIMATE).
- **The lead's count** (MEASURED there): 808 of 2,701 objects were carried, in some slot, in a second form one 1e-8-day unit earlier than a form already fetched. That is most likely one orbit determination written two ways (INFERRED). A loop must count the two forms as one determination and log the alternation, or it counts one determination twice. The pilot's keep rule dropped the earlier form when it came second, but kept the later form as a new set when that came second, six times (Q3) (narrowed at the merge).

**DEBRIS-D's Q7 criteria, applied:**
- **"Refuse a prediction when its predicted along-track 1σ exceeds 10 km".** For these objects, (B')'s own median miss from 1 to 2 days is 11.5 km, and 64 km from 2 days. If a forecast's predicted 1σ matched those misses, about half the forecasts from 1 to 2 days and most beyond would be refused (INFERRED from the medians). For decaying objects, the forecast's product is the decay window, not the position, and its test is the window's coverage of the catalogued decay.
- **"Refit when … its fit is older than 3 days".** For these objects that becomes a refit at every new set, which is (R).
- **The z-score with a TLE covariance** carries over to positions, but its TLE error model must be fitted on low-perigee objects separately. On these objects, (B)'s medians are 15 and 68 times DEBRIS-H's run-wide (B) medians: 1.81 against 0.123 km from 6 to 24 h (n 6), and 17.7 against 0.262 km from 1 to 2 d (n 17) (COMPUTED from the two logs).

## Q5. The data and its terms

| source | what it holds | cadence | terms | what it needs from Logan |
|---|---|---|---|---|
| CelesTrak's SATCAT | `DECAY_DATE` per catalogue number, a date only (E0005's record, READ) | not read here | DEBRIS-H's plan's record of the usage policy (Q1). The events README: "A decay record from CelesTrak's SATCAT takes Logan's yes for each request" (READ) | a yes per request, or a standing yes for a set list (his rule) |
| a fresh `SW-Last5Years.txt` (CelesTrak) | observed Ap, Kp and F10.7, then 45 daily and 178 monthly predictions (the downloads' copy, READ) | the copy says updated 2026-11-16 12:35:04 UTC (READ). Its cadence is not read (CelesTrak) | DEBRIS-D's Q7: "none stated on the page" (READ (via WebFetch) there). Orekit needs DEBRIS-F's three normalisations | a download, on his yes |
| NOAA SWPC's 45-day Ap and F10.7 forecast | Ap and F10.7, 45 days | "updated daily at 0000 UTC"; days 8 to 45 "updated weekly, on every Sunday" | no reuse terms stated on the page (READ (via WebFetch), `https://www.spaceweather.gov/products/usaf-45-day-ap-and-f107cm-flux-forecast`; swpc.noaa.gov redirects there) | a download from `services.swpc.noaa.gov`, a data endpoint, on his yes |
| NOAA SWPC's 27-day outlook | F10.7, Ap and the largest daily K | issued Mondays "by 1500 UTC" | The Weekly's contents "have no copyright or other restrictions" (READ (via WebFetch), `https://www.spaceweather.gov/products/27-day-outlook-107-cm-radio-flux-and-geomagnetic-indices`) | a download, on his yes |
| Space-Track's `decay` class | "SATCAT - Historical", "Decay Entry - Historical" and "60day Decay" predictions | queries: "DECAY and SATCAT are once per day" | an account, one per user; "less than 30 requests per 1 minute(s) and 300 requests per 1 hour(s)". Redistribution: "express blanket approval" for basic SSA data, cited, beside the user agreement's "not to transfer any data … without prior express approval"; the page does not reconcile them (READ (via WebFetch), `https://www.space-track.org/documentation`) | his account, and his reading of the terms |
| Space-Track's TIP messages | "Projected satellite reentry predictions": a time with a "+/- XX Hours" window, and where the object reaches 10 km | queries: hourly; every 10 minutes within 12 h of re-entry | as above | as above |
| ESA's re-entry predictions (`https://reentry.esoc.esa.int/home`) | a portal with Register and Login; its guide is a PDF | not stated | not stated (READ (via WebFetch)) | an account, or the guide's download |
| The Aerospace Corporation's list | not read: three of its pages returned HTTP 403 to WebFetch (MEASURED, 2026-11-23) | | | a person with a browser |

A decay watch needs SATCAT dates and TIP windows to score against, observed space weather for (C), and the whole catalogue's candidates (Q1). Q7's W0 lists them as Logan's decisions.

## Q6. The compute

**One object, one box worker** (COMPUTED from G4's MEASURED rates; DEBRIS-I's program from its plan's ESTIMATE):

| | (R) fit, 32 lane-days | (H) fit, 84 lane-days | one 30-day member |
|---|---|---|---|
| native64 | 2.14 CPU-s | 5.62 | 2.01 |
| cft256 (M1) | 9,250 | 24,300 | 8,670 |
| binary256, DEBRIS-I's program (ESTIMATE, degree 7) | 304 to 906 | 798 to 2,380 | 285 to 850 |

**The workload** (ESTIMATE):
- **New sets:** 55 over 17 objects in 2.21 days, about 1.5 a day an object (MEASURED count). Slots were missed, so this is a lower bound. Each new set brings one cycle. Six of the 55 are a determination already kept, in its other form (Q3). That leaves 49 determinations, about 1.3 a day an object, so the rows below, at 1.5, are about 15% high: at 1.3, each cost is about 13% lower (COMPUTED; narrowed at the merge).
- **Each cycle:** one (R) fit, one (H) fit, and N members over a 30-day window.
- **Lane-days a day:** 1.5 × (116 + 30 N) an object.

**What sets of 10, 100 and 1,000 objects need** (COMPUTED, `k_compute.001.log`):

| objects × members | native64, box workers | cft256 (M1), box workers | DEBRIS-I's program, box workers (ESTIMATE) | RX 7600 binary256, cards (ESTIMATE) | RTX 5060 Ti binary64, cards (ESTIMATE) |
|---|---|---|---|---|---|
| 10 × 1 | 0.0017 | 7.3 | 0.24 to 0.72 | 0.011 to 0.046 | 0.0018 to 0.0075 |
| 10 × 100 | 0.036 | 156 | 5.1 to 15 | 0.23 to 0.97 | 0.038 to 0.16 |
| 10 × 1,000 | 0.35 | 1,510 | 50 to 148 | 2.2 to 9.4 | 0.37 to 1.5 |
| 100 × 1 | 0.017 | 73 | 2.4 to 7.2 | 0.11 to 0.46 | 0.018 to 0.075 |
| 100 × 100 | 0.36 | 1,560 | 51 to 153 | 2.3 to 9.7 | 0.38 to 1.6 |
| 100 × 1,000 | 3.5 | 15,100 | 497 to 1,480 | 22 to 94 | 3.7 to 15 |
| 1,000 × 1 | 0.17 | 732 | 24 to 72 | 1.1 to 4.6 | 0.18 to 0.75 |
| 1,000 × 100 | 3.6 | 15,600 | 514 to 1,530 | 23 to 97 | 3.8 to 16 |
| 1,000 × 1,000 | 35 | 151,000 | 4,970 to 14,800 | 220 to 941 | 37 to 154 |

- **Every row assumes 1.5 cycles a day.** At 8 a day (every 3-hour slot), multiply by 5.3; at a 7-day window, divide the member-dominated cells by about 4 (both in the log).
- **A box worker is one of 36 logical CPUs.** DEBRIS-H found that A256 kept real time only while the box was otherwise idle (READ, its finding 4).
- **The card rows are DEBRIS-D's ESTIMATEs at degree 20,** times 1 to 3 for small batches. They assume a degree-20 program on the card, which DEBRIS-I's I6 is testing: its 1,762 coefficients fit neither the constant bank nor a table today (READ, DEBRIS-I's plan). An ensemble is a lockstep batch, which suits a card.
- **So:** native64 carries 100 objects × 100 members on a third of one worker. Wide precision carries one member each for 10 objects through M1 (7 workers), or 100 through DEBRIS-I's program (2.4 to 7.2 workers, ESTIMATE). Wide ensembles need cards.

## Q7. The first build, laid out for Logan

**Feasible as a decay watch on the CPU.** It is a measurement campaign, and its first product is a scored record, not a public forecast.

**The milestones:**
- **W0, decisions (Logan's):**
  - **(a) SATCAT decay dates** for the watch's objects: one request a week for the list, or one per decay (his rule);
  - **(b) observed space weather:** a fresh `SW-Last5Years.txt` a day, or NOAA's products;
  - **(c) a Space-Track account** for TIP and decay messages, with his reading of the redistribution terms;
  - **(d) the candidate list's source** for the whole catalogue: CelesTrak's queries by group, or Space-Track's GP class.
  - Without (a) nothing can be scored, and the watch stops at Q3's kind of evidence.
- **W1, the list:** Q1's rule at each fetch, counting sets one 1e-8-day unit apart as one determination and logging the alternation (narrowed at the merge). Gate: a second script reproduces its counts.
- **W2, the forecasts:** at each new set, (R) and 100 native64 members over bc (prior from the refit series) and a density scale (prior 10 to 15% 1σ, DEBRIS-D's BELIEVED figure for NRLMSISE-00); a geodetic decay criterion; each window's 10, 50 and 90% times. Gates: this pilot's controls, a step-halving control on the final day, and one cft256 member per object as the audit.
- **W3, the scoring:** each window against SATCAT's day and TIP's window. The statistic, fixed before the data: the fraction of decays whose catalogued day the 90% window covers, with N ≥ 30 before a verdict, beside Q1's τ as a baseline; holdouts by time and object.
- **W4, the refinement:** bc priors and the density scale refitted from W3's record, adopted only if the holdout's coverage improves by a margin fixed beforehand.

**The costs:**
- **CPU** (COMPUTED, Q6): 100 objects at 100 members is 0.36 box workers at native64. A cft256 audit member for 10 objects is 7.3 workers. Both fit beside the box's other work only at low priority (DEBRIS-H's finding 4).
- **Data:** the requests of W0.
- **Agents:** one build round for W1 and W2, then a long run of about a month for W3, so that about 60 decays occur in the catalogue (Q4).

## Recommendation (a recommendation, apart from the evidence)

**I recommend building W0 to W3 as a decay watch: M1 at native64 with an ensemble, scored against SATCAT dates and TIP windows.** I recommend not presenting its positions as better forecasts than the catalogue's for these objects, since the pilot found none.
- **The wide kinds belong in it as an audit, not in every member,** until DEBRIS-I's program or DEBRIS-J's card carries them.
- **Space weather comes second:** with predicted space weather alone, (C)'s medians are lower than (R)'s in both cells under a day, under 6 h and from 6 to 24 h, and higher from 1 to 2 days. Under a day it misses less than (R) in only 17 of 55 checks, and recounted, its median is lower from 6 to 24 h only (narrowed at the merge). Observed space weather is W0(b)'s decision, and it should be tested before it is relied on.

**What would change it:**
- **If W0(a) is declined,** no decay can be scored. The watch then has nothing to learn from, and I would recommend against building it.
- **If the first month's scored windows cover the catalogued decays no better than Q1's τ does,** the ensemble is not earning its cost. A TLE-based list would then serve Logan's aim more cheaply.
- **If (C) with observed space weather beats (R) from 1 to 2 days** on a holdout, the atmosphere moves ahead of the ensemble in the build.
- **If DEBRIS-I's measured rate is far below its estimate,** the audit stays at a sample.

## What this study could not settle

- Whether M1's decay windows have skill: one SATCAT date, one decay without a record, no ensemble.
- Whether NRLMSISE-00 helps with observed space weather (decision 2(a) left only predictions).
- Whether (H) learns past 8 sets, and why it stops on its iteration limit more often than (R) (4 of 33 against 1 of 47; that longer spans stiffen the fit is BELIEVED).
- Why CelesTrak's files carry some sets in two forms one 1e-8-day unit apart, which the lead reads as one determination written two ways (INFERRED; narrowed at the merge); whether index 1178 re-entered, and when.
- The step's error near re-entry, and the time from M1's sphere to TIP's 10 km.
- Space-Track's redistribution terms, whose two passages the page does not reconcile (each read through a model's summary; narrowed at the merge from "conflict"); The Aerospace Corporation's list, which refused every fetch.

## Budget and records

- **CPU by cycles / 2.5e9: 943.2 s, 15.7 CPU-minutes,** of the 50 (MEASURED, `records\cpu.tsv`): the build 53.2 s, the regression 187.4, prep 0.8, bprime 11.7, rfit 128.2, hfit 242.4, decay 71.6, cfit 224.1, the two-fill check 6.4, three stats runs 1.6, Q1 15.7. GetProcessTimes gives 491.0 s for the same, about half.
- **Not in `cpu.tsv`:** the first build attempt, which failed at its tar call (a few seconds, BELIEVED), and `k_swcopy.py`, `k_gfc_copy.py` and `k_compute.py`, which start no process (under 5 s, BELIEVED).
- **Wall time:** about 1 h 10 min of the 5 h (08:20 to about 09:30). **Processes:** each stage ran its children one at a time; the build's compiles held idle parents (`make`, `bash`, the gcc driver) beside one compiler.
- **Records:** 17 logs in `studies\debris-k\logs\`; every script version that wrote one in `scripts\` under its hash; `records\` (`cpu.tsv`, the gfc copy's console record); `MANIFEST.sha256` over all of them.
- **Code,** in `tests\`: `k_lib.py`, `k_refit.py`, `k_fit.c`, `k_pilot.py`, `k_candidates.py`, `k_compute.py`, `k_build.py`, `k_swcopy.py`, `k_swcheck.py`, `k_gfc_copy.py`, `k_orekit_fit.js`. Each names what it copies and from where; no earlier file changed.
- **The ledger's `debris-k\`:** `regress\` (the regression's table and work); `pilot\` (the stages' JSON, `checks.001.tsv` to `.003.tsv`, and `work\` with every decode batch's input); `candidates\` (Q1's tables).

## Sources

- **READ:** `studies\DEBRIS-K-plan.md`; `lead.md` from 2026-11-23 07:55; `studies\DEBRIS-F-build.md` §§2 and 4 to 7; `studies\DEBRIS-H-build.md`; `studies\DEBRIS-H-plan.md` (CelesTrak's policy); `studies\DEBRIS-C-measurements.md` M2; `studies\DEBRIS-D-architecture.md` Q5 to Q7; `studies\DEBRIS-I-plan.md`; the ledger's `events\`.
- **READ (via WebFetch), 2026-11-23:** `https://www.space-track.org/documentation`; `https://www.esa.int/Space_Safety/Space_Debris/Reentry_and_collision_avoidance`; `https://reentry.esoc.esa.int/home`; `https://www.spaceweather.gov/products/usaf-45-day-ap-and-f107cm-flux-forecast`; `https://www.spaceweather.gov/products/27-day-outlook-107-cm-radio-flux-and-geomagnetic-indices`.
- **Refused (HTTP 403):** `https://aerospace.org/reentries`, `https://www.aerospace.org/reentries`, `https://aerospace.org/article/spacecraft-reentry-faqs`. No CelesTrak page was read.

## What I did not do, and what the brief got wrong

**Not done:**
- no ensemble run;
- no request or download;
- no box, GPU or WSL run;
- no count of DEBRIS-H's whole run, which the lead made;
- no step-halving test;
- no JB2008.

**The brief and the plan:**
- **The plan does not say how forecasts from the same set at different times count.** I count each distinct (object, set, reference) once, and fixed that before the data.
- **My own control K2 assumed that DEBRIS-H's check tables used the newest set fetched.** Two of its rows used the other form, one 1e-8-day unit earlier, of a set already fetched, and the lead's count finds 191 such checks (narrowed at the merge). (A) and (B) are read as DEBRIS-H recorded them, as the plan says, so their figures stand as DEBRIS-H's rule defined them.
- **The plan's estimate for (H)** (6 to 38 CPU-minutes) was high. It took 4.0 minutes at 33 distinct histories, since many forecasts share a history.
- **The brief's process rule** ("counting every child") and a compile's idle parents do not sit easily together. I ran one working process at a time.

## Narrowed at the merge, and notes (the lead, 2026-11-23)

verifier-K confirmed its attacks 1 to 7 and found one defect, per-object orbit values by seed index in three logs (`cft-debris-ledger\filed\DEBRIS-K-verifier-K-report.md`). That is not a wrong answer, so under Logan's rule nothing was sent back. The text as reported is kept at `cft-debris-ledger\filed\DEBRIS-K-study.as-reported.md`.

**The defect, fixed.** The three logs' per-object lines are rewritten in the repository's copies, and the originals are held whole in the ledger's `debris-k\held\logs\`; `debris-k\MANIFEST.sha256` lists the rewritten copies. The plan's one fitted `bc` by seed index, given twice, is held the same way. Both were done by the ledger's `tools\merge-k\hold_redact.py`, log `hold_redact.001.log`. In the study, Q1 gives index 1178's perigees by band. The lead's first narrowing still gave the first of them as "near 400 km"; merge-check-K found that, and it now reads "above 400 km".

**merge-check-K** (Haiku) checked this merge (`cft-debris-ledger\filed\DEBRIS-K-merge-check-K-report.md`). It confirmed the hashes, the diffs, the re-runs of `same_od.py` and `cross15.py` (byte for byte), the six pairs from `plan.json` with code of its own, every figure of the recount, and the 24 marks. It found:
- 1178's perigee "near 400 km", a point value by another name;
- (C)'s two medians under a day, given as if they were one;
- the rows "about 13% high", where they are 15% high and the costs at 1.3 are 13% lower;
- the header's account of the plan's two lines, which was loose;
- four of verifier-K's "did not do" items, missing from the notes below.

All were fixed in its terms, and the fixes were not checked again. Its note that `tests\k_candidates.py` and `tests\k_pilot.py` print the removed values is below. Two more items it left to the lead stay as they are. The desktop's and the box's fits differing by 0.182 m for 1595 and 3.29 m for 1178 (Q3) are differences between two machines' arithmetic, not orbit values. M1's decay times by seed index (Q3's table) are results, as DEBRIS-H's events E0003 and E0008 are.

**The lead's own finding, after verifier-K.** verifier-K noticed that K2's two unmatched rows lie about 0.9 ms from slot 16's sets. That led the lead to measure the step-backs, and every one is one 1e-8-day unit (`lead.md`, 09:33). The plan's rule, "A set whose epoch is no later than the object's previous set's is skipped and counted", therefore kept six later forms of determinations the pilot already held. DEBRIS-K's figures stand as its rule defines them. The recount sits beside them, and the conclusions it touches do not change: nothing beat (B'), (R) and (H) are level with it from 1 to 2 days only in their medians, and there is no learning curve. One reading does change: (C)'s lower median under a day holds, after the recount, from 6 to 24 h only.

**Narrowed**, each marked in the text:
1. **The header:** the repository's copy of the plan, and where draft 3 is held.
2. **Short answer, the compute:** the costs at 1.3 new determinations a day an object.
3. **Short answer, the pilot:** the recounted medians and counts, beside DEBRIS-K's.
4. **Short answer, 1 to 2 days:** level in the medians only (verifier-K's note), and the recount.
5. **Short answer, the learning curve:** the 2-set bin's 4 checks (verifier-K's note), and the bins by determination.
6. **Q1, index 1178:** its perigees given by band; the values are held in the ledger.
7. **Q2, (C)'s row:** better than (R) in its medians under 6 h and from 6 to 24 h, not check by check.
8. **Q2, after the table:** the recount of the pilot's figures.
9. **Q3, the slot rows not kept:** the 15 older rows are each one unit older.
10. **Q3, the lead's run-wide count:** one unit each, most likely one determination in two forms.
11. **Q3, the six pairs among the kept sets** (new).
12. **Q3, the distinct checks:** 112 and 56 when recounted.
13. **Q3, K2:** the other form of slot 16's sets.
14. **Q3, the planted identity:** one reference and an easy bound (verifier-K's note).
15. **Q3, the clustering:** 51 of the 112.
16. **Q3, the recount table** (new).
17. **Q3, the limits:** the check count.
18. **Q4, the lead's count:** what a loop must do with the two forms.
19. **Q6, the new sets:** 49 determinations, and the rows about 15% high.
20. **Q7, W1:** sets one unit apart count as one determination.
21. **The recommendation, space weather:** medians only, and the recount.
22. **What this study could not settle, CelesTrak's files:** two forms, not older sets.
23. **What this study could not settle, Space-Track's terms:** "does not reconcile", not "conflict" (verifier-K: the page's summary calls them "ambiguous rather than clearly contradictory").
24. **The brief and the plan, K2:** the other form, one unit earlier.

**Notes** from verifier-K, not narrowed:
- It did not re-run the JVM decode batch for (R)'s regression, the fits, the (C) route or the decay propagation, so the misses it recomputed check the arithmetic, not the propagator.
- **The brief's error, the lead's:** it called K2's unmatched rows "older sets". They are one unit older, the other form of the same determinations. The brief also used "conflict" for Space-Track's statements, where the study had "does not reconcile".
- **The lead's error, outside this study:** at 09:04 the lead's count read the step-backs as older sets, and the lead told Logan so. That is corrected in `lead.md` at 09:33, and here.
- **verifier-K did not:**
  - re-run the lead's scan of DEBRIS-K's files (`tools\scan-k\`, in the ledger);
  - check the study for personal strings beyond finding none. The lead's byte and privacy check at the merge covers the study, the plan, the three rewritten logs and the manifest (`lead.md`, 09:53);
  - re-check the 8 file counts in DEBRIS-K's own log beyond the manifests. Its own check of the ten studies' manifests passed, `debris-k`'s 37 among them;
  - search the study past Q1 for per-object values. The lead searched the rest at the merge, and merge-check-K searched it all.
- **verifier-K cited the prep log's lines 91 and 92;** only line 91 held perigees, and line 92 lists the sources (merge-check-K).
- **The code prints per-object values** (merge-check-K's note). `tests\k_candidates.py` (line 183) and `tests\k_pilot.py` (line 305) write the perigees, apogees and ndot that were removed from the logs. The code stays as it ran. A re-run's log belongs in the ledger, and only a copy without those lines belongs here.
