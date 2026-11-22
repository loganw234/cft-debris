# DEBRIS-H build report: M1 as a 72-hour service on amd-arc-box, checked against CelesTrak every 3 hours

cft-debris, MIT licence. Written by DEBRIS-H, 2026-11-21 (phase 2). Labels: MEASURED (a run's own output, with its log), COMPUTED (arithmetic from labelled inputs), READ (from a named record; for the box, chiefly the lead's ledger entries in `lead.md`, which record the lead's runs), INFERRED (a reading no run isolates), BELIEVED, ESTIMATE. Every box run was the lead's; this agent never connected to the box. Desktop runs are functional tests, and no desktop time is reported as a measurement. Objects are named by seed index; catalogue numbers, designators, single objects' groups and every state are in the ledger only. **Every check's reference is the catalogue's new element set through SGP4, not the truth: a miss is a distance from that reference.**

**Narrowed at the merge.** After verifier-H's report, the lead made one narrowing and three additions. Each is marked in the text and listed in §10.

## 1. What was built

| file | what | SHA-256 |
|---|---|---|
| `tests/m1h.c` | the driver, linked to M1's `src/` (commit 1646c96) and libcft. `run` steps one worker's slice of the seed step-major at the wall clock (step k due at `unix_ref` + 15 k s; at most 60 s early, plus a stagger of i x 15/W s), logs every step (`S k start finish due lag compute_s`), writes a checkpoint every 40 steps by rename without overwrite, marks an object decayed below 6,498.137 km, and checks a pause file every 5 s. `seg` re-propagates objects from a checkpoint to given instants (whole steps, then one short step). | b37aae29b6a9ce91c77aa4aab7e8481730247f19ad679f2fb04e17239e3de2f7 |
| `tests/h_service.py` | the supervisor: `init`, `start`, `stop`. One per run folder (flock); workers at nice 19; every checkpoint hashed into `manifest.tsv`; a restart's rewrites compared object by object; a track restarted from its latest complete checkpoint, at most 6 times an hour; every minute the foreign load (`/proc/stat` busy time less its own tree's CPU), free space, pause files and `status.json`; at each slot the fetcher, then the check; the kinds' divergence at every checkpoint. | 8b1e203fc2978aa9fdfa7d903e3de95ef372d547a0ebe0761f9835dc9c8899c6 |
| `tests/h_fetch.py` | the fetcher: the four group files once per slot from CelesTrak's fixed URL, with a fixed User-Agent and gzip accepted, each body archived with its SHA-256. It stops (writes `fetch/STOP`) at the first response that is not 200, at a body that fails its check, or at the second slot in a row without a response. | 98597766b7a59d8ab20eac2da8e51087d683c791a5b3645f6f4280b6e23e4db0 |
| `tests/h_check.py` | the check, DEBRIS-F's F6 at each slot: for each eligible new set, (A256), (A64) and (A64f) by `seg` from the track's latest checkpoint at or before the set's epoch e, (B) SGP4 from the seed's set at e, the reference SGP4 from the new set at e, the miss and its RIC parts, T1 and T3. | 3a9d41ed8a08739e334b03ccff46f77a8f3d46ec94d4bab5d5c27451bba88688 |
| `tests/h_seed.py` | the seed: DEBRIS-F's fit (`m1f`) of each object to its own set, then the catch-up to T_s; seed 1 with bc estimated, seed 2 with bc fixed at 0.01 m^2/kg; `combine`. Since the fix phase it gives every `m1f` `M1_DOWNLOADS`. | d43000d54299f28773b6db57bb923eb4b7caad29ff81a075e3345f7a52acc22d |
| `tests/h_lib.py` | the scripts' library (standard library only): numbered logs that never overwrite and name their script's SHA-256, process pools, CPU accounting by cycles, the time scales and clock map, the GP reader, the statistics, the seed and checkpoint readers. | 7bd11067b93f8f2ac7975034894e2d9c15c8ba0b163cb039f95f924fc096e4bb |
| `tests/h_build.py`, `tests/h_stage.py` | H1 (sources by hash, `src/` against 1646c96, the builds, smoke runs, C1); the stage for the box (`in/`, `EXPECTED.sha256`). | ec39f7c79e3b608872a4e59eb299165e03b67d4d29d551110b6011cd46313b00, 1aa2022238682d55ecd12ff33b4d58fc2ea0a8435fe28548d05407b89e3a6ab1 |
| `tests/h0_gate.py` | H0 on the new frame table `frame_h0.bin` (in the ledger, `debris-h/`). | afb630669cafcd1b43d94c75aca156b98ad8abeba2d968749fb5faf495f3cf36 |
| `tests/h2_gate.py` | H2: restarts, a changed worker count and a pause, with C2 to C4. | 396d2a755716084edb5f45e53dd9fc9ddb441127d9a0a21b20d02d7c22c3e6af |
| `tests/h3_gate.py`, `tests/h3_server.py` | H3: the fetcher against a local server with planted responses, C6 to C11. | 5883fe8055030c848599ff7416937c1424aa0b4445799c543873e3ea03eaf4ba, 65eb863673f73f6b00a7bfe44ed4c6454316e5f16d15676386c0a31b57ce6f84 |
| `tests/h4_gate.py` | H4: S0's sets decoded at three instants each, compared across machines; C12. | db829b60e87b3b70ba86a5d642523fc0ee704a3ce8b813c568acf6b71950c2fa |
| `tests/h5_gate.py` | H5: the seed's counts and states, C13 to C15, and the F5(d) regression. | d53d5604e73f25bcbdb3a2bb2061cf8d18c60eaf6854757418c9904567a54f1e |
| `tests/h6_gate.py` | H6: F6's 200 pairs through the service's fit, driver, `seg` and check; C16. | 739c9b0c4f7edbdc86d1bddd3048ad25a3955d57aeb5cc3aaf30cad1ccebaede |
| `tests/h_paced.py`, `tests/h_itest.py`, `tests/h_env_gate.py` | the paced dry run (P1, P2, C5); the integration test (the supervisor runs a slot's fetch from a local server, then its check); C17 (the downloads path). | 5cdb2c66db787ae16c8dae1037196b30147e9df9800f51a57f2bb3782b326dc8, a5317b360feb3d012771097a4ee59f152854c9c8ff38da9fe3829f0c6c9bfcca, 9cad7f9a5c2eb1d2cf70caef655a3b201fef6d6ebf60cbd6963d302141d25884 |
| `tests/h_audit.py` | H7(d): (d1) every checkpoint against the manifest, (d2) 10 sampled segments per track re-propagated by `seg` (seed 0xA0D17, 64 objects each). | 8025573f87710594754f83202975b469b33ade90a3cc3794f69c1d5076427435 |
| `tests/h_analyze.py` | phase 2: H7(a) to (f) and the measurements, from the run's records. | b1136838b2338581781c742e97fde774f5f8f67731d0920a5707433f6990a9e8 |
| `tests/h_fitdiag.c`, `tests/h_crlibm.c`, `tests/h_fitdiag_cmp.py` | the fix phase's diagnostics: `m1f`'s fit iteration with every C-library call logged; libcft's correctly rounded `exp`, `asin` and `acos` linked in their place; the comparison. | 9dce9e2ce44b2e521811c8c3817fb3a93a89d535c408bea3304bea94298fb81c, 399578d4cabef68a5c0660016676171c0d5fc938853044b92bf8c1dbf04fc42b, 3edd1e05a71a96720c12af70ee25ac2405df7b6738f0e6c0146a8b3bf9faf8e4 |

M1's `src/` is unchanged: H1's B1 asserted its 18 files equal commit 1646c96 on both machines (MEASURED, `h_build` logs). Every script version that wrote a kept log is in `studies/debris-h/scripts/` under the first 12 hex digits of its SHA-256.

## 2. How to build and run

- **Stage** (desktop): `python -I -B tests/h_stage.py <repo> <ledger> <downloads> <dest>`. The fix phase's stage holds 71 files, `EXPECTED.sha256` `0f74d208f6b07b89913bbcf6a81a96056c92cbdee8a128c5d1188e87ed30ca23` (MEASURED); the lead staged the run folder `r2` from it (READ, `lead.md` 2026-11-18 11:59). Copy `<dest>/in` to the run folder and run everything from there.
- **Build and gates** (box): `python3 -I -B in/tests/h_build.py .`, then `h2_gate.py . --size box`, `h_paced.py .`, `h4_gate.py . --java java --compare in/desktop/h4_decode.txt`, `h6_gate.py . --java java --procs 36 --compare in/desktop/h6_pairs.tsv` (and again with `--fits-from in/desktop`), as in the phase 1 hand-off (`filed/DEBRIS-H-handoff-1.md` in the ledger).
- **The seed:** `h_seed.py fit --seed 1 ...`, `--seed 2`, then `h_seed.py combine`; then `h5_gate.py`.
- **The service:** `h_service.py init . svc --track A256:cft256:seed/seed1.txt:18 --track A64:native64:seed/seed1.txt:1 --track A64f:native64:seed/seed2.txt:1 --divergence A256,A64 --fetch live --sh0-unix U ...`, then `setsid python3 -I -B in/tests/h_service.py start . svc </dev/null >svc.out 2>&1 &`. `touch svc/PAUSE` pauses every worker; `h_service.py stop . svc` stops; the same `start` resumes from the latest complete checkpoints.
- **After the run:** `python3 -I -B in/tests/h_audit.py . svc` on the box; then, on the desktop, `python -I -B tests/h_analyze.py --box studies/debris-h/box --r2 <ledger>/debris-h/box/r2 --leaps <stage>/in/orekit/tai-utc.dat --out <ledger>/debris-h/phase2 --cpu studies/debris-h/records/cpu.tsv`. It reads only, holds every input to its recorded SHA-256 first, writes one numbered log, and puts per-object tables in the ledger.

## 3. The gates

| gate | criterion | desktop (MEASURED, `studies/debris-h/logs/`) | box (the lead's runs; READ from `lead.md` unless a log is named) |
|---|---|---|---|
| H0 | F3's checks on the new table at the window's dates; C1 | PASS (`h0_gate.001`): (a) 73 dates, largest angle 0.011 µas against 50 µas; C1 failed as specified (1.0000 mas); (b) 1,000 times, largest 15.757 µas against 1 mas; (c) 7.6523e-14 rad against 1.9874e-9, \|dOmega\| 9.077e-16 rad/s against 1.297e-13 | not a box gate |
| H1 | sources by hash, `src/` equal to 1646c96, builds and smoke runs; C1 | PASS (`h_build.001`, `h_build.002` for the fix phase's stage) | PASS in `r1` (08:54) and `r2` (`box/logs/h_build.001.log`) |
| H2 | checkpoints bit-identical across a restart, a changed worker count and a pause; C2 to C4 | PASS at desktop size, 4 objects and 12 steps (`h2_gate_desktop.001`), a functional test | PASS: 16 objects, 120 steps, both kinds; C2 to C4 as specified (09:09) |
| H3 | the fetcher's rules; C6 to C11 from planted responses | PASS (`h3_gate.001`, 24 lines) | desktop only |
| H4 | the decode bit-identical across machines; C12 | the desktop half: 8,088 states, C12 as specified (`h4_gate.001`) | PASS: all 8,088 GCRF states bit-identical (11:30) |
| H5 | the seed's counts, finite states above 120 km, checkpoint 0 equal at both kinds, seed 2's bc exactly 0.01, TDB - UTC within 1 ms of Orekit's; C13 to C15; the F5(d) regression | `h5_gate.001` FAILED the regression (1 of 5 fits at the printed digits: the decoder's history, section 7); `h5_gate.002` PASS with F5(d)'s decode order replayed (TDB - UTC 2.211e-05 s) | PASS on S_H0 (`box/logs/h5_gate.001.log`): 2,688 objects; seed 1 2,335 converged and 353 on the iteration limit, seed 2 2,687 and 1; TDB - UTC 2.174e-05 s (15:31) |
| H6 | F6's 200 pairs within 1 mm; T1 to T3; C16 | PASS (`h6_gate.001`, 0 of 200 differ). It used 18.8 CPU-minutes, past the lead's 15-minute line, unstopped: a failure of process, accepted after the fact (08:34) | **FAILED**: 10 of 200 pairs differ, by up to 0.0230 m from F6 (`box/logs/h6_gate.001.log`); recorded as failed on Logan's word (14:46). With the desktop's fits it passes, 0.000000 m from the desktop (`box/logs/h6_gate.002.log`), so the difference is made in the fit (section 7) |
| C17 | every `m1f` reads `in/dl/` whatever its caller's environment | PASS (`h_env_gate.001`) | PASS (`box/logs/h_env_gate.001.log`) |
| paced | P1 no step more than 60 s early; P2 no late step in minutes of foreign load under 5%; C5 the catch-up at T = D/(r - 1) within 10% | functional tests at 4 objects: C5 failed in `h_paced.001` (at a 60 s offset, too few late steps for the formula) and for native64 in `.002` (at 600 s the run caught up exactly at a checkpoint step, whose write took about as long as the late phase); `h_paced.003`, with no checkpoint inside C5, PASS (ratios 1.015 and 1.018). P2 cannot be measured on Windows | PASS: P2 31 of 31 minutes, no late step; C5 ratios 1.0040 (P256) and 1.0270 (P64) (11:30) |
| integration | the supervisor runs a slot's fetch and its check | PASS (`h_itest.001`) | not run |

## 4. The long run's timeline

Times are the box's local time (-0700). MEASURED from the service log (`box/svc/logs/service.001.log`) and the step logs, by `h_analyze.001.log`, unless marked.

- **2026-11-18 15:23:47** the supervisor started 20 workers: A256 (cft256, seed 1, 18 workers of 149 or 150 objects), A64 (native64, seed 1, 1 worker) and A64f (native64, seed 2, 1 worker), 2,688 objects each.
- **15:48:50.817 T_s** (2,933,400 s TDB on M1's axis); the first step was due at 15:49:05.8, step 17280 at 2026-11-21 15:48:50.8.
- **Pauses: none.** No `p` or `P` line in any step log, no pause-file line in the service log.
- **Restarts: none.** 7,361 rewrite comparisons, none with a difference.
- **The fetcher** (slot j due at U + 3j h, U = 15:00:07 on 11-18, READ `lead.md` 15:03):
  - slots 1 to 11: four requests each, all answered 200;
  - slot 12 (11-20 03:00): no response for cosmos-2251-debris, the slot's last file; the first slot in a row, so the fetcher went on;
  - slots 13 and 14: all 200;
  - slot 15 (12:00): no response for fengyun-1c-debris, the slot's second request; the slot ended there;
  - **slot 16 (15:00): no response for cosmos-2251-debris, the second slot in a row: `STOP` written at 15:01:52.** Slot 17 made no request;
  - **the resume, on Logan's word (19:09, READ `lead.md` 19:11):** the lead renamed `STOP` to `STOP.slot16` at 21:01:26 (READ, 21:03), and slot 18 fetched at once, all 200;
  - slot 19 (11-21 00:00): no response for fengyun-1c-debris; the slot ended there;
  - **slot 20 (03:00): HTTP 500 for fengyun-1c-debris: `STOP` written at 03:00:20.** Logan's word at 09:49 left it stopped (READ, 09:50). Slots 21 to 24 made no request.
  - In all, 70 requests: 65 answered 200, 4 without a response, 1 answered 500. 22 bodies equalled the previous slot's (logged as findings).
- **The checks** ran after slots 1 to 15, 18 and 19, not after 16 and 20 (the fetcher stopped in those slots). Sets were eligible at slots 3 (116), 4 (649), 5 (747), 7 (906), 9 (343), 10 (254), 11 (583), 13 (1,216) and 18 (1,655): 6,469 checks. Slot 5's, 11's and 18's checks exited 1 on a T3 hit. Slot 16's three files held 191 sets later than the last checked and after T_s; none was checked, since the fetcher stopped in that slot (`h_analyze.001.log`; narrowed at the merge).
- **Decays in M1:** idx 1595 below 6,498.137 km at step 1396 (due 11-18 21:37:50) and idx 1178 at step 15328 (11-21 07:40:50), both in A256 and A64. A64f, from seed 2, has neither.
- **Departures from the catalogue's files:** idx 1595 from slot 7, idx 2513 from slot 16, idx 836 from slot 18 (absent from their group's fetched file).
- **The end:** A64 and A64f finished step 17280 at 15:47:50 on 11-21, 59.9 s early; A256 at 15:56:24, 454.0 s late; `END` at 15:56:25. The audit ran from 15:57:02 to 16:00:40 (READ, `lead.md` 16:09).

## 5. H7's results

All from `studies/debris-h/logs/h_analyze.001.log` (script `b1136838b233`), MEASURED from the records after each input matched its recorded SHA-256: the repository's 91 copies (`SHA256SUMS.box`), the 106 ledger files read (`MANIFEST.copy-003.sha256`), and all 8,660 checkpoint copies (the run's `manifest.tsv`).

| criterion | result | figures |
|---|---|---|
| **(a)** the fetches | **PASS** | 19 slots attempted, every request logged and inside its slot, in time order; 70 (slot, file) pairs, none requested twice; 65 bodies archived with the logged size and SHA-256; the 500 at slot 20 stopped the fetcher at once with no later request; the second slot without a response (16) stopped it until the resume on Logan's word at slot 18 |
| **(b)** the checks | **FAIL by its letter** (T3) | eligibility recomputed from the archived files, the seed's epochs and the earlier tables: 6,469 eligible sets, equal to the tables' rows, every one checked (0 listed, 0 decayed); the counts equal each check log's. Slot 16's 191 later sets after T_s are not eligible by (b)'s definition, since the fetcher stopped in that slot, and were neither checked nor listed (narrowed at the merge). T1: 25,876 check-methods, 0 outside 1% of \|v\|. **T3: 6,469 compared, 3 within 100 km, at slots 5, 11 and 18** (recomputed, equal to each check log). Logan kept (b) as written (READ, `lead.md` 2026-11-19 15:10) |
| **(c)** the sanity bound | **PASS** | (A256)'s median miss at horizons under 24 h, every check, flagged fits in: n 1,494, median 1.240 km (bound 5 km). Without the flagged fits: n 1,333, 1.411 km |
| **(d)** the checkpoints | **PASS** | (d1) re-checked on the desktop's copies: 433 checkpoints per track, every file present, the object ranges tiling the 2,688 objects, all 8,660 files equal to the manifest in size and SHA-256. (d2), the box's `audit.001.log` (READ; its script equals `tests/h_audit.py`, `8025573f8771`): 10 of 10 segments equal on each track. verifier-H's own sample, seed 0x7A11C5, run by the lead from 16:48 to 16:51 on 11-21, also gave (d1) and (d2) PASS on every track (READ, `lead.md` 2026-11-21 16:52; added at the merge) |
| **(e)** the pacing | **FAIL by its letter** | 73 clock hours had steps due; 20 qualify (foreign load under 5% of 36 CPUs, no pause): 19 full and the partial first hour (15:00 on 11-18, 880 steps due). Late steps in 2 of them: **08:00 on 11-19 (274, largest lag 915.6 s) and 08:00 on 11-20 (732, largest lag 1,304.0 s)**. Logan kept (e) as written (READ, 2026-11-19 05:08). The lead counted 19 qualifying hours, the full ones (READ, 2026-11-21 09:29); either count is over 6. The plan does not say whether a partial hour counts, and `h_analyze.py`'s reading was fixed after the data, since the script was written in phase 2, after the run; either reading gives the same verdict (added at the merge) |
| **(f)** the kinds | **PASS** at T_s | DIV at k 0: n 2,688, all 2,688 distances zero; recomputed from the checkpoint copies at k 0 and at k 17280, each equal to the service's DIV line |

**H7(e)'s split** (defined after the data, no pass condition; Logan's ruling of 2026-11-19 05:08). Of the 20 qualifying hours, 18 began on time and hold no late step. Two began behind: 08:00 on 11-19, with 4 workers behind at its first second and the largest backlog 1,419.2 s, and 08:00 on 11-20, with 5 workers and 1,989.2 s. Their 1,006 late steps are the catch-up from the night before.

**H7(b)'s split** (defined after the data, no pass condition; Logan's ruling of 2026-11-19 15:10). Catalogue numbers, groups and designators are in the ledger, `debris-h/phase2/h_analyze.001/t3_hits.tsv`.

| slot | (B) of | against the reference of | T3 distance | the references apart | (B)'s own misses | argp + M of the new sets | inclination, RAAN (second - first) |
|---|---|---|---|---|---|---|---|
| 5 | idx 2610 | idx 2612 | 38,435.6 m | 38,455.0 m | 366.6 m; 71,770.9 m | 359.6858 deg; 359.7137 deg | 0.0066 deg; 0.3077 deg |
| 11 | idx 2684 | idx 2686 | 46,241.1 m | 42,537.3 m | 21,621.1 m; 133,558.9 m | 0.1457 deg; 0.1540 deg | -0.0101 deg; -0.0461 deg |
| 18 | idx 2276 | idx 2278 | 65,079.3 m | 65,161.3 m | 405.3 m; 2,045.7 m | 359.6586 deg; 0.0259 deg | 0.3409 deg; -0.2970 deg |

Over every checked set, the share whose argp + M lies within 5 and within 1 degree of the ascending node: cosmos-2251-debris 538 and 447 of 1,475 (36.5%, 30.3%); fengyun-1c-debris 1,694 and 1,204 of 4,685 (36.2%, 25.7%); iridium-33-debris 108 and 103 of 285 (37.9%, 36.1%); stations 24 and 24 of 24. INFERRED from these: in each hit both new sets have their epochs within 0.35 degree of the ascending node, on planes within 0.35 degree of each other, so the two references lie near the same node point, tens of kilometres apart, though they belong to different objects at different instants. T3's premise, that another object's reference lies over 100 km away, fails for such pairs; nothing points to swapped identities. Slot 5's and slot 18's figures and the four groups' shares equal the lead's visit 4 and visit 8 computations to their printed digits (READ, `lead.md` and `tools/visits-h/visit8d.out`).

## 6. The measurements

MEASURED (`h_analyze.001.log`, 578 lines, which holds every cell for every method, with and without the flagged fits, and every slot). Medians and 90th percentiles (the ceil(0.9n)-th smallest) of the miss, in km. (A64) equals (A256) in every cell at the printed metre, as the kinds' divergence (below) implies.

**Over the run, all 6,469 checks:** (A256) median 4.888, 90th 21.277; (A64f) 3.422 and 28.114; (B) 0.306 and 2.250. Without the 735 checks of flagged fits: (A256) 5.261 and 21.886; (A64f) 3.621 and 31.070; (B) 0.318 and 2.488. (A256)'s parts: \|R\| 0.120 and 0.302, \|A\| 4.880 and 21.270, \|C\| 0.095 and 0.212.

| cell | n | (A256) | (A64f) | (B) |
|---|---|---|---|---|
| horizon e - e0 under 6 h | 0 | | | |
| 6 to 24 h | 1,494 | 1.240 / 4.267 | 1.244 / 5.067 | 0.123 / 0.423 |
| 1 to 2 d | 2,505 | 4.700 / 11.561 | 3.297 / 17.049 | 0.262 / 1.195 |
| 2 to 3 d | 1,625 | 10.474 / 22.832 | 6.168 / 37.102 | 0.553 / 2.791 |
| 3 to 7 d | 783 | 18.307 / 56.735 | 13.835 / 87.199 | 1.258 / 8.229 |
| 7 d and over | 62 | 68.758 / 230.790 | 74.026 / 338.931 | 6.982 / 71.771 |
| run's age e - T_s under 6 h | 1,144 | 1.610 / 6.961 | 1.151 / 9.337 | 0.150 / 1.207 |
| 6 to 24 h | 2,530 | 4.149 / 12.880 | 2.981 / 19.656 | 0.256 / 1.602 |
| 1 to 2 d | 2,642 | 9.627 / 27.585 | 5.802 / 41.875 | 0.474 / 3.444 |
| 2 to 3 d | 153 | 9.103 / 27.006 | 4.559 / 40.365 | 0.433 / 3.398 |
| perigee under 500 km | 195 | 10.927 / 70.880 | 49.273 / 624.713 | 3.740 / 61.105 |
| 500 to 800 km | 4,750 | 5.299 / 21.372 | 4.410 / 29.764 | 0.340 / 2.411 |
| 800 km and over | 1,524 | 3.269 / 16.565 | 1.762 / 5.670 | 0.190 / 0.711 |
| seed set's age at T_s up to 1 d | 4,632 | 3.667 / 14.011 | 2.622 / 16.395 | 0.228 / 1.184 |
| 1 to 3 d | 1,505 | 8.982 / 27.025 | 6.572 / 40.481 | 0.635 / 4.221 |
| 3 to 7 d | 290 | 31.374 / 81.631 | 24.485 / 141.078 | 1.811 / 9.713 |
| over 7 d | 42 | 69.621 / 297.858 | 94.078 / 338.931 | 9.663 / 82.558 |
| seed 1's fitted bc > 0 | 4,109 | 3.857 / 20.779 | 5.003 / 42.959 | 0.345 / 3.562 |
| bc < 0 | 2,360 | 7.440 / 21.984 | 1.792 / 8.902 | 0.256 / 1.063 |

Every cell holds at least 20 checks, except the empty one. The bc cells split by seed 1's fitted bc for every method; (A64f)'s own bc is fixed at 0.01 m^2/kg.

**Per slot,** (A256) and (B) medians: slot 3 0.845 and 0.091 (n 116); 4 1.479 and 0.146 (649); 5 2.441 and 0.198 (747); 7 3.003 and 0.212 (906); 9 5.593 and 0.262 (343); 10 6.689 and 0.311 (254); 11 6.688 and 0.325 (583); 13 7.323 and 0.364 (1,216); 18 11.785 and 0.579 (1,655).

**(A256) misses less than (B)** in 334 of 6,469 checks (5.2%), and 313 of 5,734 without the flagged fits (5.5%). Checks cluster by object and by update, so these are not shares of independent trials.

**Objects:** 2,076 of 2,688 checked; checks per object from 1 to 9, median 3 (1: 511 objects, 2: 377, 3: 366, 4: 310, 5: 287, 6: 156, 7: 58, 8: 10, 9: 1).

**The kinds' divergence,** \|A256 - A64\| over the objects in binary64, at all 433 checkpoints (the service's DIV lines; recomputed at k 0 and k 17280):

| k (run age) | n | median | largest |
|---|---|---|---|
| 0 (0 h) | 2,688 | 0 (all zero) | 0 |
| 1440 (6 h) | 2,687 | 3.468e-07 m | 1.997e-06 m |
| 5760 (24 h) | 2,687 | 2.737e-06 m | 1.430e-05 m |
| 11520 (48 h) | 2,687 | 7.925e-06 m | 3.703e-05 m |
| 17280 (72 h) | 2,686 | 1.412e-05 m | 7.195e-05 m |

The largest distance over the run is 7.200e-05 m (k 17080).

**The pacing, outside H7(e)'s criterion:** A256 had 183,045 of 311,040 steps late (58.8%), the largest lag 2,728.5 s (step 7877, due 11-20 00:38:05); A64 and A64f had none of 17,280 each. In the 53 hours that do not qualify, 182,039 of 253,520 steps were late (71.8%); every one of those hours, with foreign shares from 5.77% to 30.29%, had late steps. A256's late stretches (the union over its workers of every late step's [due, finish]): 47, of which 42 under a minute (107 late steps, the largest lag 17.0 s), and five longer:

| from | to | to be on time again | late steps | largest lag |
|---|---|---|---|---|
| 11-18 18:44:05 | 11-19 08:42:01 | 837.9 min | 49,656 | 2,214.8 s |
| 11-19 13:15:35 | 13:18:16 | 2.7 min | 52 | 31.7 s |
| 11-19 14:52:35 | 15:23:03 | 30.5 min | 1,143 | 266.8 s |
| 11-19 18:44:20 | 11-20 08:59:05 | 854.7 min | 51,904 | 2,728.5 s |
| 11-20 18:46:35 | 11-21 15:56:24 (the end) | 1,269.8 min | 80,183 | 2,440.3 s |

The last stretch had not closed when the run ended.

## 7. Findings

1. **The decoder's output depends on what its JVM decoded before** (phase 1, MEASURED on the desktop: the same set at the same 721 instants differs by up to 1.7e-5 m in position when decoded after another object; the same batch repeats bit for bit; ledger 2026-11-18 08:21). H5's regression failed until F5(d)'s decode order was replayed. BELIEVED cause, which no run isolated: Orekit's interpolating frame-transform caches, whose sample grid depends on the first dates requested. Every decode of the service, the seed's and each check's, logs its batches' composition and order. H4 found the box's decode of one file in one JVM bit-identical to the desktop's.
2. **The two machines' C libraries round differently, and the fit amplifies it** (fix phase, MEASURED). In one fit iteration of one object, the desktop's `asin`, `acos` and `exp` are not correctly rounded in 37,361 of 1,105,920 calls, the box's in 480; the first differing call changes one lane's observations, so J and the step differ. The desktop with libcft's correctly rounded functions reproduces the box's first iteration bit for bit (for two of the 10 objects). No change to the fit could make the box's fits equal the desktop's while the desktop's stay equal to F6's, so H6's box half failed on 10 of 200 pairs (largest 0.023 m) and was recorded as failed on Logan's word.
3. **T3 fired three times on co-planar sets at their nodes** (section 5's split).
4. **A256 kept real time only while the box was otherwise idle** (MEASURED, the hour table in `h_analyze.001.log`): every hour with a foreign share of 5.77% or more had late A256 steps, and every qualifying hour that began on time had none. The long stretches began at 18:44 to 18:46 each evening and closed at 08:42 and 08:59 the next mornings; the third had not closed at the end. INFERRED: the evening load was cft-fp256's nightly runs, about 9 CPUs by the lead's visits (READ); the one-worker native64 tracks never fell behind. DEBRIS-G's figure that 18 workers keep cft256 in real time was measured with the box booked `sensitive` (READ, `DEBRIS-G-build.md`); this run shows no such margin beside a 9-CPU load.
5. **(A256) misses less than (B) in only 334 of 6,469 checks (5.2%),** and its miss is mostly along track (over the run \|A\|'s median is 4.880 km of the miss's 4.888 km), growing with the run's age. The reference and (B) are both SGP4 from the same catalogue's sets, so (B) shares the reference's model; (A) is M1's physics fitted to SGP4 pseudo-observations of one set. These figures say how far each method lies from the next catalogue set, not which is nearer the object. INFERRED, not tested: the along-track growth points at the fitted drag.
6. **A log line misnames a skipped slot** (READ, `tests/h_service.py` lines 582 to 595): "SLOTS missed while the service was down: [17]". The service was up. The scheduler does nothing while the stop file exists (line 582); at its first tick after the rename it logged every unattempted slot since the last attempted one with that text (lines 593 to 595).

## 8. Limits

- Every miss is a distance from the catalogue's next set through SGP4, not from the object.
- Checks cluster: 2,076 objects with 1 to 9 checks each, and the sets of one update share their orbit determination.
- No check could have a horizon under 6 h: the youngest seed set was 7.00 h old at T_s (MEASURED, `seed_meta.tsv`'s ages), and every checked epoch is after T_s. The plan foresaw few such checks.
- Run ages of 2 to 3 days rest on slot 18's 153 checks: the fetcher stopped at slots 16 and 20 under its rules and fetched again only at 18.
- (d2) is the box's measurement, read here; `h_analyze.py` re-hashed the checkpoint copies but re-propagated nothing.
- (d2)'s comparison has no planted-difference control: it can fail, but no run has shown it failing. Neither audit's sample covers the two segments in which M1 decayed an object, 1360 to 1400 and 15320 to 15360 (added at the merge).
- H7(e)'s foreign load is the service's per-minute `/proc/stat` busy time less its own processes' CPU: everything else on the box, not only cft-fp256.
- The decays are M1's, from its states falling under 120 km; whether an object re-entered is the catalogue's matter (the lead's `events/events.tsv`).
- The box gates' figures are the lead's runs, read from `lead.md`.

## 9. Records

- `studies/debris-h/logs/`: the desktop logs and `h_analyze.001.log`; `studies/debris-h/scripts/`: every script version that wrote a kept log; `studies/debris-h/records/cpu.tsv`: CPU by cycles; `studies/debris-h/box/`: the run's aggregate records (91 files, `SHA256SUMS.box`); `studies/debris-h/MANIFEST.sha256` over all of these.
- The ledger (per object): `debris-h/box/r2/` (the run's seed, checkpoints, step logs, fetches and check tables; `MANIFEST.copy-003.sha256`), and `debris-h/phase2/h_analyze.001/` (`t3_hits.tsv`, `objects.tsv`, `departures_decays.tsv`).
- Phase 2's CPU (MEASURED by cycles): 4.9 s for a trial with outputs in scratch, 13.7 s for the run of record.

## 10. Narrowed at the merge

The lead made these changes after verifier-H's report (`studies/DEBRIS-H-verifier-H-report.md`): one narrowing and three additions, each marked in the text. Everything else is as DEBRIS-H wrote it.
- DEBRIS-H's own report stays verbatim in `studies/DEBRIS-H-report.md`.
- This report as DEBRIS-H left it is kept in the ledger, as `filed\DEBRIS-H-build.as-reported.md`.

**Narrowed:**
1. **§4 and §5, H7(b):** "every one checked (0 listed)" now names slot 16's 191 later sets after T_s. They are not eligible by (b)'s definition, since the fetcher stopped in that slot, and they were neither checked nor listed.
   - The source is verifier-H's defect. The lead checked it against `h_analyze.001.log`, whose slot 16 line counts the 191.
   - The verdict does not change.

**Added:**
2. **§5, H7(d):** verifier-H's own sample, seed 0x7A11C5, passed (d1) and (d2) on every track in the lead's box run.
3. **§5, H7(e):** the plan does not say whether a partial hour counts, and `h_analyze.py`'s reading, that it does, was fixed after the data (verifier-H, item 6). The script was written in phase 2, after the run. Either reading gives the same verdict.
4. **§8:** (d2)'s comparison has no planted control, and neither audit's sample covers the two decay segments (verifier-H, item 5). The lead checked both audit logs: 60 sampled segments, none of them 1360 or 15320.

**In DEBRIS-H's own report,** narrowing 1 covers line 40, "and all of them were checked".

**Notes from verifier-H's report, not narrowed:**
- **The service's own checks as foreign load** (item 6): not borne out by the data.
  - The one check that ran in a quiet hour, slot 7's (12:00:40 to 12:07:20 on 11-19), left that hour at 0.05% foreign. The service's own CPU rose to 725.8 CPU-seconds a minute, against about 690 in hours 9 to 11 (the hour table in the ledger's `tools\visits-h\visit6.out`).
  - The hours near 3.8% on 11-20, 10 and 15, held cft-fp256's box gates B0226 and B0233, not checks (READ, `lead.md` 2026-11-20 18:51).
- **The node shares** (item 11): the report's "26% to 36%" (line 57) speaks of each debris group, so it rightly leaves out stations' 24 of 24.
- **The fetcher's stop rule** (item 4): stopping only at the second slot in a row without a response goes beyond the policy's wording. That is the plan's choice (decision 7, "The fetcher"), stated there.
- **Not determined by verifier-H:** the Orekit decode of the reference (item 3), which it did not re-implement.
- **What verifier-H did not do:**
  - re-run H3 to H6, the paced run or C17;
  - re-check H6's pairs beyond the 20 it sampled;
  - run the `sha256sum -c` checks on `debris-b` to `debris-g` (the lead's scan ran them);
  - read `lead.md` and the visit scripts in full.
- **The lead's brief** said the stage takes `src/` from commit 1021414. `h_stage.py` takes it from 1646c96, and `src/` is identical at both.
