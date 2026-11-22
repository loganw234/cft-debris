# DEBRIS-H: M1 as a 24/7 service on amd-arc-box: the first long run, checked against CelesTrak's updates (plan of record, draft 3)

Drafted 2026-11-18 by cft-debris's lead for Logan's approval.
- This is a **build round with a long run.** It takes M1 as rounds DEBRIS-F and DEBRIS-G left it (commit 1021414; `src\` unchanged since commit 1646c96) and runs it as a service on amd-arc-box for 72 hours (decision 5):
  - it holds four CelesTrak groups' objects at the wall clock, at binary256, with two native64 tracks beside it;
  - every 3 hours it fetches CelesTrak's new element sets, and checks its own states against each new set at that set's epoch;
  - it keeps checkpoints, so that a restart continues bit for bit.
- **Draft 1** passed the lead's checker (`dispatch\check_plan_h.py`, log 004: 211 checks, 0 failed).
- **plan-verifier-H** (Sonnet) then found one blocker, eleven defects and notes. Its report is filed verbatim in the ledger's `filed\`. The lead checked each finding's evidence before answering it. Draft 2 answers every finding in "What changed from draft 1".
- **plan-verifier-H's scoped re-check of draft 2** found no blocker, three lines still in draft 1's form, and four small concerns. Its report is filed too. Draft 3 answers them in "What changed from draft 2".
- Draft 3 has had the lead's check only (`lead.md` names its log). Nothing has been dispatched, downloaded or requested.

## The question, in Logan's words

- **This round** (2026-11-18, asked "Draft the next round, the 24/7 run on the box?"): "Yes, draft it. I'll have the cft lead update you on gpu compatibility progress".
- **The goal** (2026-11-12): "a simulation capable of realtime (or slightly faster) simulation on a consumer card, so a 24x7 sim could run on a local box here for long run tests, validating itself with the open datasets update intervals, scaling tracked objects as the main scaling parameter presumably. High performance cards like the MI300X could then be used for higher density or faster/concurrent runs."
- **The box** (2026-11-16): "You also have permission to run the tests on the 'amd-arc-box', which has many more cpu cores, its information should be in TimeSheet"; and "Next round, though you have permission to utilize the box for the cpu or Intel arc card, the U50 is the only withheld resource on that machine."
- **Carried from earlier rounds:**
  - the kinds (2026-11-13): "utilize native and cft for binary64 (and 32 if needed) so the library utilizes the entire precision range offered by cft, and the results can be compared for correctness";
  - the precision (2026-11-12): "Id also prefer to continue to utilize the higher precisions, simply to be a usecase for cft-fp256 as well";
  - the route through cft programs (2026-11-12): "*Yes if possible utilize cft programs, as well as generating certificates when able";
  - certificates (2026-11-12): "*Certificate support can be built for but not implemented in order to still have gpu capability at the moment".

## What DEBRIS-H is for

DEBRIS-G measured how many objects the box's CPUs carry in real time, and held 2,686 objects at real time at binary256 for 20 minutes. The goal's 24/7 loop needs three things no round has tried:
1. **Days on a shared machine.** The box's CPUs are cft-fp256's at night and at weekends, in `shared` windows whose text says "others may share, at low priority" (TimeSheet S003; S004 for weekends). A long run must live beside that work, and record when it falls behind.
2. **Real states, checked against the open data.** DEBRIS-G's population was shaped like the sky but placed at one epoch, not where the objects are. This round starts each object from DEBRIS-F's fit to its own element set, and checks every new set CelesTrak publishes during the run, as F6 did once.
3. **Survival.** A process that dies, or a pause for someone else's window, must not change the results. A restart from a checkpoint must continue bit for bit.

| part | what it settles | the evidence it rests on |
|---|---|---|
| **H0. The frame table** | M1's Earth frame over the run's dates, from DEBRIS-F's Earth orientation file (decision 8) | DEBRIS-F's F3 checks, re-run on the new table |
| **H-a. The seed** | each object's state at the run's start, from its own element set by DEBRIS-F's fit | gate H5: its counts and controls, and DEBRIS-F's fits reproduced |
| **H-b, H-c. The driver and the supervisor** | stepping at the wall clock, checkpoints, restarts, pauses | gate H2: restarts, a changed worker count and a pause, all bit-identical |
| **H-d. The fetcher** | CelesTrak's updates, fetched by its usage policy | gate H3: each rule forced by a planted response from a local server |
| **H-e. The check** | M1 against each new set, beside SGP4's own prediction | gate H4 (the box's decoder equals the desktop's), gate H6 (F6's misses reproduced), and T1 to T3 on every check |
| **H7. The long run** | 72 hours on the box | its criteria and statistics, fixed in this plan |

What this round does not do: change M1's library or physics, use any GPU, add objects during the run, re-fit objects from new sets, install anything that restarts the run by itself, or run past 72 hours without Logan's word ("Not in this round").

## What DEBRIS-H starts from (labels as in DEBRIS-C)

### M1 (MIT, commit 1021414, on origin/main)

- **`src\`,** M1's library, byte-identical to commit 1646c96 (DEBRIS-G's builds asserted it, READ from `studies\DEBRIS-G-build.md`). Its force model: degree-20 gravity from EIGEN-6C4, the Sun and the Moon from DE421, an exponential atmosphere with drag co-rotating with the frame table's Omega, and radiation pressure with a conical shadow. It integrates with classical rk4 at a fixed step, and a final short step lands on a given time (READ, `src\m1_physics.h`). The atmosphere is static: M1 reads no space weather.
- **`tests\m1f.c`:** the real frame, the fit (`m1f fit`, native64) and predictions (`m1f prop`: whole steps, then one short step) (READ, its usage lines).
- **`tests\f_fit.py`:** the fit's orchestration. Each object's origin O is its set's epoch e0, rounded to 2^-20 s, less one day. Its 721 pseudo-observations, every 120 s from O to e0, come from SGP4. M1's fit estimates the state and the drag parameter `bc` (fixed at 0.01 m²/kg where perigee is 1,000 km or higher), with `cram` fixed at 0.01 m²/kg (READ, its header).
- **`tests\f5_sgp4.js`:** the decoder: Orekit 13.1.9's `TLEPropagator` through Nashorn, giving GCRF states at requested instants through the same Earth orientation file (READ, its header). On the desktop it runs on Java 8, `C:\Program Files\Java\jre-1.8` (READ, `tests\f_lib.py`).
- **`tests\f6_hindcast.py`:** F6's method, which this round's check repeats. The reference is SGP4 from the new set at its own epoch. The miss is the GCRF distance, with its radial, along-track and cross-track parts. Its controls are T1 (the time tag), T2 (equal sets) and T3 (swapped identities) (READ, its criteria block).
- **`tests\m1g.c` and `tests\g_harness.py`:** DEBRIS-G's batch driver and harness: processes, 64-lane batches, a paced mode, and the foreign load from `/proc/stat` (READ).
- **`tests\m1nodes.c`:** DEBRIS-F's builder of the frame table (READ, `studies\DEBRIS-F-build.md` §2).

### What DEBRIS-F and DEBRIS-G measured (MEASURED, as narrowed at their merges)

- **F6, the first hindcast** (`studies\DEBRIS-F-build.md` §5): 200 pairs over horizons of 1.5 to 70.6 h (196 distinct orbits). The median miss against SGP4 from the next set:
  - (A) M1 fitted, at native64: **1.122 km**, 90th percentile 2.825 km, with 22 fits stopped on the iteration limit included (1.196 and 2.919 km without them);
  - (B) SGP4 from the earlier set: **0.075 km**, 90th percentile 0.357 km;
  - (A)'s cell medians under 6 h run from 0.370 to 1.402 km over the 196 distinct orbits. Its miss is mostly along-track (median parts: radial 0.094, along-track 1.115, cross-track 0.095 km).
  - The ledger's `debris-f\f6_pairs.001.tsv` holds each pair's misses and their parts in metres, printed to the millimetre, and `f5d_fits.001.tsv` each F5(d) fit's summary: its iterations, convergence, `bc` to six figures, and its residuals to the millimetre. Neither holds a fitted state (READ).
  - DEBRIS-F's fit and predictions run native64 with the C library's functions, not libcft's (READ, `tests\f_fit.py` lines 75 and 94). So a fit made on the box may differ from one made on the desktop in its last bits. G3 found no such difference on its sample.
- **The fitted drag parameter is poorly determined** (`studies\DEBRIS-F-build.md` §5 and §6, narrowed at its merge). Over F6's 200 fits, `bc` ran from −0.73 to 1.32 m²/kg, negative in 98: figures DEBRIS-F gave and nobody verified. In F5(d)'s 100 fits it is negative in 23: verifier-F's re-run, and the lead's count of the ledger's table today. DEBRIS-F's words: "A free drag parameter fitted over one day of SGP4 positions is not a physical drag coefficient here." Over 72 hours, a negative `bc` raises an orbit where drag would lower it.
- **The fit's cost on the box** (F9's T3): 1.81 s an object at 3 iterations.
- **Throughput** (`studies\DEBRIS-G-build.md` §4, 64 lanes), in object-seconds a second:
  - cft256: 299 on 1 worker, 4,176 on 18, 4,332 on 36;
  - cft128: 684, 9,587 and 9,564;
  - native64: 1,291,561 on 1 worker.
  
  These are throughputs. Above the 2,304 objects the runs carried, a capacity is an extrapolation.
- **G5:** 2,686 objects at cft256 on 36 workers held real time for 20 minutes. Every step finished at least 5.584 s early, and the workers were busy 61.3% of the time on average.
- **G2 and G3:** an object's result does not depend on its batch, lane or worker. On G3's 16 objects and 240 steps, every kind-mode agreed bit for bit between the desktop and the box, the C library's native kinds included. That equality extends no further (READ, `studies\DEBRIS-G-build.md`).
- **Restarts are the same run by design:** M1's rk4 computes each step's time from its index, t0 + (step0 + j) h, never by accumulating, and its comment states that a segment restarted from a boundary state with its step index is the same run (READ, `src\m1_physics.h`, `ph_rk4`). No round has tested it; H2 does.

### The box (MEASURED by the lead's read-only survey, 2026-11-18 05:47, `ledger\tools\survey-h\box_survey.001.txt`)

- **Its night's load,** inside S003: 8 `clause5-soak` processes, one thread each, at nice 10, with `cft-audit` and one `python3` at nice 10. All 36 CPUs were 25.3% busy over 2 s.
- **Java is absent.** Python 3.12.3 has numpy, and no `sgp4`. There is no `ensurepip`, so no venv.
- **Tools:** wget present, curl absent; tmux and screen absent; `setsid`, `flock`, `chrt`, `ionice`, `taskset`, `systemd-run` and `crontab` present.
- **The clock** is NTP-synchronised, by systemd-timesyncd; chrony is inactive.
- **logind's Linger is off.** cft-fp256 leaves detached runs on the box (its home holds many `*.nohup` files, READ), so a process started with `setsid` is BELIEVED to outlive its ssh session; H2 checks it.
- **The disk:** 15 GB free of 233 GB (94% used). cft-debris's old run folders hold 304 MB and 187 MB.
- **Memory:** 48,060 MiB, 45,042 available.
- From DEBRIS-G's survey: a Xeon E5-2697 v4, 18 cores and 36 threads; CPU c and c + 18 share a core; gcc 13.3.0; Ubuntu 24.04.

### The box's time, in the TimeSheet (READ 2026-11-18, `timesheet.py list` and `data\bookings.json`)

- **S003:** `box`, `shared`, Monday to Thursday, 18:00 to 07:45: "the nightly card's oracle work (MPFR) on the box's CPUs; others may share, at low priority".
- **S004:** `box`, `shared`, Friday 18:00 to Monday 07:45: "the weekend card window's oracle work on the box's CPUs".
- **S001 and S002** are the U50's `sensitive` windows, on `u50` alone. The U50 is withheld from cft-debris.
- **By day,** cft-fp256 books the box as it needs it. Today it holds the box `shared` from 07:50 to 10:30 (B0130, B0123).
- **A correction to the lead's own memory:** it carried a rule that every box run ends by 17:50. S001's text says that cft-fp256's preflight ends by 17:50, and S003's allows others at low priority. This plan rests on the TimeSheet's text, and Phase 0 confirms it with cft-fp256's lead.

### CelesTrak (READ through the built-in browser: by the lead on 2026-11-16, as `studies\DEBRIS-F-plan.md` records it, and again on 2026-11-18, `lead.md` 06:16)

- The query is `https://celestrak.org/NORAD/elements/gp.php?GROUP=<group>&FORMAT=csv`. DEBRIS-F's four groups are `stations`, `fengyun-1c-debris`, `iridium-33-debris` and `cosmos-2251-debris`. Its S0 held 2,696 objects in 2,686 distinct element sets.
- **The usage policy,** last updated 2026-11-16, paraphrased:
  - GP data are updated every 2 hours. Download only what you need, when you will use it, and each update at most once;
  - ask for CSV, and for compressed transfer (gzip and brotli are supported);
  - machine-to-machine software is to stop querying at the first response that is not HTTP 200, and report it to a person. Ignoring such responses gets the address firewalled;
  - after a 500 or 503, all requests stop for at least 15 minutes;
  - each data set has a directory query (`jsonDir.php`) showing when its data last changed, to be queried no more than once an hour;
  - limits are beginning to be enforced on the larger sets, such as `active`.
- **A block would reach every machine behind Logan's router.** CelesTrak cannot tell apart users behind one address (the policy's own point about NATs; the lead's reading for this household).
- **Sets are published hours after their epochs** (MEASURED from DEBRIS-F's snapshots): the newest epoch was 5.62 h before S0's request and 4.00 h before S1's. Of their 2,696 sets, 1,731 and 1,774 had epochs within a day of the request.
- **One script got both encodings:** S0 came back uncompressed and S1 gzip-compressed (READ, `dispatch\fetch_f.002.log` and `fetch_f.003.log`).
- The lead reads the policy again before the launch.

### The frame table and the Earth orientation file

- DEBRIS-F's `frame_main.bin` covers TDB 2026-10-16 00:00 to 2026-11-19 00:00 (READ, `studies\DEBRIS-F-build.md` §2). It ends before this round's run, so H0 builds a new table.
- **DEBRIS-F's `finals2000A.daily` reaches further:** its 181 rows run from MJD 61270 to 61450 (2026-08-18 to 2027-02-14), with UT1 predicted from MJD 61360 (2026-11-16) on (MEASURED from its rows' flags). So H0 can build the new table from it with no download (decision 8). The run's dates then rest on predictions made from data to 2026-11-15. A fresh file would carry measured values to about the day of its download.
- **Its dX and dY run to MJD 61437,** and are blank from 61438 (MEASURED). Orekit takes a blank as zero, so DEBRIS-F held F3's and F4's epochs to MJD 61430 or earlier (READ, `lead.md`, 2026-11-16). H0's window ends at MJD 61402, before both.
- DEBRIS-F's build of the 34-day table took 26.8 CPU-s, about 0.8 CPU-s a day of data.

### The GPU route (cft-fp256's lead, 2026-11-18; the sender's labels, filed in the ledger's `relayed\`)

- cft-fp256's GPU backend, `hip:N`, runs and is verified on the RTX 5060 Ti and the RX 7600. Its build carries code for the RTX 4070, which is never run, because it drives the display.
- **The Intel Arc A750 is not a `hip:N` device:** HIP has no Intel target, and its two study routes are not libcft devices.
- Index tables, and scratch depths to 2,048, now run on the device. The constant bank stays at 512 slots, so M1's degree-20 field (1,762 constants) is still refused for capacity. Index tables are the route for it.
- A divide and square root callable from the device ("S1") is measured, not built, and is Logan's call.

So porting M1 to a GPU is a later round's. This round's service is built so that a GPU backend could replace its workers: a worker's whole job is "advance these objects from checkpoint k to checkpoint k + 1".

## The design, and why

**Time.**
- M1's host time stays TDB seconds from `jd_epoch` 2461329.5 (DEBRIS-F). The run's grid is t_k = T_s + 15k s, with T_s a multiple of 600 s.
- **Step k is due** when the box's UTC clock reaches the UTC instant of t_k, by DEBRIS-F's B1 scales.
- **The clock map** is a pair (unix_ref, t_ref): step k is due at unix_ref + (t_k − t_ref). The supervisor computes the long run's map once, at the start, from UTC, and records it. Across 72 hours, the periodic part of TDB − TT moves by under 0.1 ms (COMPUTED: at most 1.66 ms × 2π / 365.25 days, about 0.03 ms a day), far below a step. Tests may shift the map, to run a seed of another date at the real clock's pace.
- **A step may be computed up to 4 steps (one minute) before it is due,** and no earlier: "real time (or slightly faster)". With the workers' stagger (below), worker i starts each step i × 15/18 s later than that, so between 60 and about 46 s before it is due. A step that finishes after it is due is **late**, and its **lag** is its finish time less its due time.

**The seed** (decision 3):
- **S_H0** is a new snapshot of DEBRIS-F's four groups, taken by the lead when the service is ready to start.
- One object per element set (DEBRIS-F's lesson: docked vehicles share a set). Perigee at least 200 km, as in DEBRIS-G. The set's epoch no more than 30 days before T_s.
- Each object gets DEBRIS-F's fit, unchanged. Then `m1f prop` at native64 carries the fitted state from its origin O to T_s.
- **Every kind starts from that one binary64 state at T_s.** So the run's wide precision is the propagation's, and the seed is binary64: a stated limit.
- Why native64 for the catch-up to T_s: at cft256 an object-day costs 289 s on one worker (86,400 / 299, COMPUTED from G4), so catching 2,700 objects up by days would take CPU-days. At native64 it costs 0.067 s an object-day.
- A fit stopped on the iteration limit keeps its last iterate and is flagged. Statistics are given with and without the flagged objects, as F6's narrowing did.
- **The fitted `bc` is kept as fitted,** negative or not, and its sign is flagged; statistics are split by it.
- **A second seed** (decision 4(b)): the same fit with `bc` held at 0.01 m²/kg for every object, as DEBRIS-F's fit already holds it where perigee is 1,000 km or higher (`fitbc` = 0 in `tests\f_fit.py`'s terms). It seeds one more native64 track, (A64f). Set beside (A64), it tests whether the free drag parameter helps or hurts beyond a day, for about 0.2% of a worker and a second round of fits.
- **The second seed's path is new on real objects.** All of F5(d)'s 100 fits estimated `bc` (READ, `f5d_fits.001.tsv`), and so did F6's 200, whose perigees ran from 273 to 857 km. So H5 runs the held-`bc` fits on the test seed's 64 objects in phase 1, before the box (plan-verifier-H's D5).
- **An object that falls below 120 km during its catch-up,** in either seed, is left out of every track and counted.
- **The fits' cost:** about 2.4 CPU-s an object on the box (F9's T3: 0.60 s an iteration; F5(d)'s fits averaged 4.04 iterations, MEASURED from its table), so about 110 CPU-minutes for each seed of 2,700, a few minutes on 36 processes (COMPUTED; plan-verifier-H's D6).

**Workers** (decision 6):
- One process per worker, with 64-lane batches, as in DEBRIS-G. There are 18 cft256 workers and one worker for each native64 track, each cft256 worker owning a fixed slice of the population. They are unpinned, at nice 19.
- G2 showed that results do not depend on the partition, so a restart may use a different number of workers.
- **The load:** about 2,700 objects / 232 object-seconds a second per worker (G4's 18-worker rate, 4,176 / 18) = **11.6 workers' worth** at cft256 (COMPUTED). That is about 12 of the 36 logical CPUs on average, and two thirds of the 18 cores.
- **The workers are staggered.** Each cft256 worker owns about 150 objects, and a step costs it about 9.7 s of every 15 s (150 × 15 / 232, COMPUTED). Workers that woke together would run in bursts, all 18 at once about 65% of the time (plan-verifier-H). So worker i starts each step i × 15/18 s after worker 0, and about 12 are busy at any moment.
- **Beside cft-fp256's nights** (about 9 single-thread processes, survey): staggered, about 21 busy threads share 18 cores, so at least 3 cores carry two; in bursts it would be up to 27. Where one of ours shares a core with one of theirs, both slow down. G4's X(36) / X(18) of 0.939 to 1.106 means two threads on a core do about as much as one alone, so each runs at about half speed (INFERRED from G4). So, staggered, up to a third of cft-fp256's night threads could run at about half speed at any moment; in bursts, about two thirds (ESTIMATE). Nice 19 does not prevent this: it orders threads on one logical CPU, not on a core's two. Phase 0 tells cft-fp256's lead, who may ask for decision 6(b) or for a pause.
- **The native64 worker** is DEBRIS-G's `native64`: the C library's functions, not libcft's.

**Checkpoints:**
- Every 40 steps (10 minutes of run time), each worker writes its slice: each state in the kind's own bytes and rounded to binary64, with the step index. It writes to a temporary name, flushes, and renames.
- The supervisor records each checkpoint file's SHA-256 in an append-only manifest.
- **A restarted worker never overwrites a checkpoint.** When it reaches one that already exists, it writes its own under a new name, and the supervisor compares the two. If they differ, it stops the track and logs it. Every restart thus checks itself (plan-verifier-H's note).
- **All checkpoints are kept for the run.** No file is deleted while it runs. ESTIMATE: about 240 bytes an object at cft256 (6 × 32 bytes, and 6 × 8 rounded) and 48 at native64, so about 0.65 MB and 0.13 MB per checkpoint for 2,700 objects, and about 0.39 GB for 432 checkpoints of the three tracks, twice that if written in hex.

**Restarts:**
- If a worker exits, the supervisor restarts every worker of that kind from the latest checkpoint whose files are all present and match the manifest.
- At most 6 restarts of a kind in an hour. Past that, it stops the kind and logs it.
- A restarted kind runs flat out until it is due again. Its late steps are recorded.

**Pauses:**
- While a file named `PAUSE` exists in the run folder, each worker finishes its current step and waits, checking every 5 s.
- A pause takes hold within a step and a poll: about 15 s at most for the step (a cft256 step costs a worker about 9.7 s, COMPUTED), plus a 5 s poll. When a shared core halves a worker's speed, its step takes about 19 s, and the pause about 24 s (plan-verifier-H's re-check).
- The lead creates it at the request of a session that needs the box to itself (decision 9). The booking's text tells other sessions how to ask, and how to pause it themselves.
- The pause's interval is logged, and the lag it causes is recorded.

**The fetcher** (decision 7):
- **S_H0 is slot 0.** Slot j comes 3j hours after S_H0's request, for j = 1 to 24 while the run lasts. Each makes one request for each of the four groups' CSV, 10 s apart: 32 requests a day, and 96 after S_H0's own 4.
- **DEBRIS-F's fetch rules and CelesTrak's policy:** compressed transfer asked for; no redirect followed; one request per file per slot, never retried; a generic client name and no personal details in the User-Agent.
- **A body is checked before it is kept:** CSV with the header's 17 columns, and at least one row. A body that fails is treated as a response that is not 200.
  - Rows of another ephemeris type are kept and counted, never checked. Every row of S0 and S1 was type 0 (MEASURED).
  - A body with fewer than half the rows of that group's previous body is kept, and logged as a finding for the lead. It does not stop the fetcher: a small group can shrink for real, and `stations` held 17 rows in S0 (MEASURED; plan-verifier-H's re-check).
- **At the first response that is not HTTP 200, or a body that fails its check,** the fetcher stops for the rest of the run and writes a stop file. The supervisor schedules no more fetches, and the propagation goes on. The lead tells Logan at its next turn, since the policy asks for a person. Fetching resumes only on Logan's word.
- **A request with no response** (no answer within 60 s, or a DNS or connection error) ends that slot, and nothing is retried in it. The next slot, 3 hours later, tries again. A second such slot in a row stops the fetcher as above. The policy names responses, not lost connections (plan-verifier-H's D9); decision 7(b) would stop at the first.
- Each body is kept with its SHA-256. A body equal to the previous slot's is counted, as a finding about the update interval.
- **Why every 3 hours:** each 2-hourly update is to be downloaded at most once. Slots 3 hours apart, counted from S_H0, never fetch one update twice, unless an update interval exceeds 3 hours. DEBRIS-F took S1 three hours after S0, by the same reasoning.

**The check,** after each fetch. It covers every object whose new set has an epoch e later than the epoch of the last set checked for it, and no earlier than T_s:
- **the reference:** SGP4 from the new set at e, in GCRF (F6's);
- **(A256), (A64) and (A64f):** M1's state at e from each track (cft256, native64, and native64 from the second seed), re-propagated from the track's latest checkpoint at or before e: whole steps, then one short step landing on e. e is rounded to 2^-20 s, as in DEBRIS-F (at most 0.48 µs);
- **(B):** SGP4 from the seed set at e: F6's (B), how well SGP4 itself predicts the new set;
- **the miss:** F6's: the GCRF distance, and its radial, along-track and cross-track parts in the reference's frame;
- **the controls:** T1 and T3 on every check, as F6 defines them. F6's T2, for a new set equal to the old, cannot fire in the run: such a set has e = e0, before T_s, so it is counted, not checked. T2 runs in H6.
- Sets with e before T_s are counted, not checked. Since sets are published hours after their epochs, slot 1 checks few objects, and the checks under a 6-hour horizon will be few (plan-verifier-H's D4).
- **Why from checkpoints:** the live workers do no side work, and a check costs at most 41 steps: at most 2.1 CPU-s at cft256 (15 × 41 / 299, COMPUTED from G4).
- **The reference is the catalogue, not the truth.** SGP4 from the new set carries that set's own error. Every miss includes it.

**The kinds compared:** at every checkpoint, the binary64 roundings of the cft256 and native64 positions are compared: the median and the largest distance over the objects, against time since T_s. At T_s the difference is 0, by construction.

**Where SGP4 runs** (decision 2):
- The check needs SGP4 and the IERS frame after every fetch. Orekit through Nashorn is the decoder DEBRIS-F verified. Java 8 on the box would run it unchanged, and H4 tests that the box's decode equals the desktop's.
- The alternatives: python-sgp4, with one wheel downloaded and a new conversion from TEME to GCRF to verify; or checks run later on the desktop, from the box's records.

**What a long run can lose, and how it is recorded:**
- **the supervisor's death, or a reboot,** stops the run until the lead restarts it from the latest checkpoint. The gap is recorded as lag. No cron entry or systemd unit is installed ("Not in this round");
- **a full disk:** the supervisor pauses the run when free space falls under 5 GB, and resumes it when free space is back above 6 GB;
- **the fetcher's stop:** checks stop, and the propagation goes on.

## The shape

| agent | job | model | when |
|---|---|---|---|
| the lead (this session) | <ul><li>Phase 0, the downloads and S_H0</li><li>the briefs and the ledger</li><li>every run on the box, its staging and its bookings</li><li>the long run's launch, pauses, visits and end</li><li>escalations, and filing each final message</li><li>the merge and its narrowing, the commit, and the round's record</li></ul> | Opus | throughout |
| DEBRIS-H | <ul><li>**phase 1:** H0, the seed, the driver, the supervisor, the fetcher, the check and the gates' code, tested on the desktop; its hand-off</li><li>**phase 2:** the long run's analysis, and the build report</li></ul> | Opus (decision 1) | after Phase 0; phase 2 when the run has ended |
| verifier-H | disconfirm the build, its gates and the long run's records | Sonnet (decision 1) | when DEBRIS-H reports |
| merge-check-H | check any narrowing the lead makes at the merge | Haiku | after verifier-H, if the lead narrows anything |

**The schedule (ESTIMATE):**
- **Day 1,** the day of approval: Phase 0, and DEBRIS-H's phase 1.
- **Day 2:** the lead's box work in the day (H1, H4, H6 and H2 on the box, and a paced dry run); S_H0 and the seed; the launch.
- **Days 2 to 5:** the long run, 72 hours. It ends by itself.
- **Day 5 or 6:** phase 2, verifier-H, the merge and the commit. The push waits for Logan's word.

## Phase 0: the lead, before dispatch

1. **Logan's decisions,** recorded verbatim. Under decision 2(a), Logan installs Java 8 on the box himself. The lead then records `java -version` there, as short work.
2. **The downloads** (decision 8), through `dispatch\fetch_h.py`, written from `fetch_f.py`'s rules: none in Phase 0 under 8(a). Under 8(b), USNO's three files, each in a new folder named with `-H` (`finals2000A.daily-H\` and so on), since DEBRIS-F's folders keep their names; each SHA-256 goes in `lead.md`. S_H0 is taken later, when the service is ready, into `gp-<group>-SH0\`.
3. **CelesTrak's usage policy** was read again on 2026-11-18 (`lead.md` 06:16). The lead reads it once more before the launch. If anything the fetcher relies on has changed, the launch waits for Logan.
4. **The archive:** libcft at 0aa997a3 in the ledger's `tools\` (decision 14). Its SHA-256 is checked again.
5. **TimeSheet:** DEBRIS-H's desktop time as a `notice`. The box's gates run as short work, or are booked when longer; the long run is booked `shared` (decision 9).
6. **cft-fp256's lead is told,** by a cross-session message: the run's window, its nice 19, its worker counts and their stagger, the `PAUSE` file, and that the run's `shared` booking will refuse their `exclusive` or `sensitive` bookings on `box` for 3 days, so they ask, and the lead pauses the run for them. It asks only whether S003's and S004's work needs other terms, and whether "every box run ends by 17:50" still holds for other sessions. The answer is filed with `dispatch\relay.py`, and anything that changes this plan goes to Logan first.
7. **Ledger files:** `DEBRIS-H.md` and `verifier-H.md`, with headers only, and the folder `debris-h\` for every per-object file (decision 13).
8. **Dispatch,** as below.

## Dispatch

- **The prompt:** a dispatch note and the agent's brief, followed verbatim by four sections of this plan: "Dispatch", "The ledger", "Rules every brief carries" and "READY". A script writes the prompt from this file. After dispatch, `dispatch\check_prompts.py` checks the prompt against the harness's transcript.
- **The test escalation:** each agent sends one as it starts:
  - it writes `test escalation from <name>` in its own ledger file;
  - it sends the same words to the lead (SendMessage to `main`);
  - the lead replies "received" and records the round trip in `lead.md`.
- If no test escalation arrives within ten minutes of a dispatch, the lead reads that agent's ledger file, arms a watch on the ledger folder, and says so in `lead.md`.
- **DEBRIS-H runs in two phases:**
  - Phase 1's final message is its **hand-off.**
  - The lead files it and runs the box's work in this order: H1 (the build, with its control first); H4 and H6's box half; H2; the paced dry run; then S_H0, H5's seed, and the launch of H7.
  - If a box run fails, the lead resumes DEBRIS-H with the failing log. DEBRIS-H fixes it and hands off again.
  - When the run has ended and its records are in place, the lead resumes DEBRIS-H for phase 2. Phase 2's final message is DEBRIS-H's report.

## The ledger

The ledger is `C:\Users\logan\source\repos\cft-debris-ledger\`, as in rounds DEBRIS-B to DEBRIS-G.

- **One file per author, append only:**
  - `lead.md` continues;
  - this round adds `DEBRIS-H.md` and `verifier-H.md`, which the lead creates with a header only;
  - correct an entry by appending beneath it, never by editing it.
- **Times:** every heading's time comes from `date`, never from memory.
- **Read it at three moments:** before starting; before resting anything on another study's number; before the final report.
- **Verifiers read `lead.md` only,** and the files it points them to.
- **Escalation:** write the entry first, then message the lead (SendMessage to `main`). Wait for the answer to a question while working on what does not depend on it. Never end your turn to wait, except at the end of a phase.
- **No agent messages another session.** Questions for cft-fp256's lead go through this round's lead.
- **When to write:** when an entry would change another agent's work or the lead's: an environment fact, a brief that turned out wrong, or a finding about a shared input, never progress. Every entry marks which claims were measured and which are believed.
- **When a pause is announced,** record where you are before you stop. On resuming, do a full read, check your outputs before trusting your memory of them, and say where you stopped.
- **Scratch:** each agent creates its own folder when it starts, `C:\Users\logan\source\repos\cft-debris-scratch\<name>\`. Read no other agent's scratch. Keep no secrets anywhere an agent is given.
- **The downloads:** `C:\Users\logan\source\repos\cft-debris-downloads\`, one folder per file, each file's SHA-256 in `lead.md`. Read-only for every agent. This round adds S_H0's four, in `gp-<group>-SH0\` folders, and, only under decision 8(b), USNO's three, in folders named with `-H`.
- **The tools:** `cft-debris-ledger\tools\`, read-only for every agent. It holds the archive `cft-fp256-0aa997a3.tar`, DEBRIS-F's `frame-f\frame_main.bin`, and `survey-h\`, the lead's survey of the box.
- **Data kept out of the repository:** `cft-debris-ledger\debris-h\` (decision 13): the seed file, every checkpoint, every fetched GP file, and every output that names an object or holds its state. DEBRIS-H writes there from the desktop, the lead copies the box's files there, and verifiers read it.
- **What the lead writes in `lead.md`, every verifier reads.** The lead records there every box run, with its booking and its log's SHA-256, and every visit to the long run. It never writes a judgement of DEBRIS-H's work there before verifier-H has reported.

## Rules every brief carries

These come from three places: Logan's standing rules (carried from cft-fp256 and cft-rebound, 2026-09 to 2026-11), canonical ParcelRound, and the rulings of rounds DEBRIS-B to DEBRIS-G.

- **Read-only, except your own outputs and scratch.**
  - cft-rebound, cft-fp256 and the TimeSheet are other sessions' live repositories. Read their files; in git, use only `git -C <repo> log` and `git -C <repo> show`. Never write in them, never run `git status` there, and never run a bare `git stash`.
  - In the TimeSheet you may run `timesheet.py check` and `list`, which only read.
  - cft-fp256 is Apache-2.0. Extract and build its archive only in your scratch.
  - In cft-debris, write only where your brief says. Commit nothing: the lead commits after verification.
- **The repository is public and MIT.**
  - Every source file you write carries a header naming cft-debris and the MIT licence.
  - Copy no third-party source into the repository, whether cft-fp256's, REBOUND's, cft-rebound's or Orekit's. libcft is linked from a build outside the repository and never vendored. Orekit is called through Nashorn, never copied.
  - Copy no third-party data into the repository either: no GP data, no IERS table, no frame table.
  - **Per-object data stay out of the repository** (decision 13). Logs in the repository name objects only by their index in the seed file, never by catalogue number. They carry hashes, counts and aggregates, never a state.
  - Reading a source to understand an interface is fine; quoting more than a short passage is not.
  - This project's own earlier code (DEBRIS-B's to DEBRIS-G's, and the lead's scripts in the ledger) is MIT, and may be reused with a note of where it came from.
- **No downloads, installs or package managers, and no requests to any data service.**
  - This round's files are in the downloads and the ledger's `tools\`.
  - **CelesTrak in particular: no agent requests it,** not even a page that looks like HTML. The fetcher is tested against a local server on 127.0.0.1 only. Its live runs are the lead's, on the box.
  - If another file would settle a question, ask the lead for it. Give its name, source URL, size, licence and purpose. Each file needs Logan's approval.
- **Reading the web: HTML pages only, and never CelesTrak's.**
  - WebFetch returns a model's summary of a page, not its bytes. A figure or quote taken through it is labelled "READ (via WebFetch)". It supports "consistent with", never "confirmed".
  - WebFetch saves any response that is not HTML to disk. So a URL ending in `.txt`, `.pdf`, `.csv`, `.zip`, `.bin`, `.jar` or `.gfc`, or one in an FTP tree, is a download request, whatever it seems to hold.
- **No GPU, WSL, card or box.**
  - **amd-arc-box is the lead's.** No agent connects to it. Every run there is the lead's, in its bookings, from commands you hand it.
  - Code meant for the box keeps its Linux-only parts guarded, so that its other parts run on the desktop for testing.
- **Keys:** this round uses no keys and signs nothing. Never look in `~/.ssh`.
- **Timings: none on the desktop.**
  - The desktop is shared. Desktop runs are functional tests: no time from them is reported as a measurement.
  - The round's timings are the box's, from the lead's runs.
- **At most 4 processes at once on the desktop,** counting every child process you start: workers, JVMs and test servers alike.
- **CPU budget** means the CPU time of the processes you start on the desktop, counted by cycles:
  - read `QueryProcessCycleTime` through Python's `ctypes`, and divide by 2.5e9 cycles a second;
  - the divisor is the part's base clock (READ, cft-fp256's `docs/BENCHMARKS.md`), and taking it as the counter's rate is BELIEVED;
  - give `GetProcessTimes` beside it. On this host it under-reports a busy thread under load: by a factor of about 1.7 to 4 in round DEBRIS-C, and in DEBRIS-F it gave 2.00 s for a run whose cycles showed 3.97 s (MEASURED);
  - DEBRIS-E's `tests\cpurun.py` does both, and may be reused.
- **Long jobs:** run them through the Bash tool, in the foreground with a timeout of at most 600000 ms or with run_in_background. Never use nohup, and never end your turn while one of your jobs is running. The service's detached start on the box is the lead's, by its brief.
- **C on the desktop:**
  - Before any compile, put `C:\msys64\mingw64\bin` first on PATH and check that `gcc -dumpmachine` prints `x86_64-w64-mingw32`. In this Git Bash, a bare `gcc` is the 32-bit i686 compiler.
  - libcft's Windows build line is `make -C host CC=gcc OS=Windows_NT TMP=/tmp TEMP=/tmp <targets>` (cft-fp256's `bindings/wasm/verify_demos.mjs:51-58`). On Windows the targets end in `.exe`.
  - M1's build is as `studies\DEBRIS-F-build.md` gives it, through `tests\build_f.sh`. Every native fused multiply-add goes through `_mm_fmadd_sd` or `_mm_fmadd_ss`. On this host the C library's `fma` is not correctly rounded, and at `-O0` a plain `fma()` still calls it (MEASURED, round DEBRIS-E).
- **C on the box (the lead's runs):** gcc 13.3.0, `x86_64-linux-gnu`. libcft is built by `make -C cft-fp256/host CC=gcc libcft.a`, and M1 at `build_f.sh`'s O2 flags, as `tests\g_harness.py` does it.
- **Java:** on the desktop, Java 8 at `C:\Program Files\Java\jre-1.8\bin\java.exe`, with DEBRIS-F's Orekit and Hipparchus jars as `tests\f_lib.py` lists them. On the box, Java 8 only under decision 2(a), installed by Logan.
- **Python:**
  - On the desktop: `C:\Users\logan\AppData\Local\Programs\Miniconda3\python.exe -I -B`, with numpy and mpmath.
  - Scripts that run on the box use Python 3.12's standard library only.
- **Processes and files:** kill only processes you started, and only by PID. Delete only what you made, and never through a computed path. The service deletes nothing.
- **Earlier studies' records are read-only.** Copy what you run into your scratch or your own output folder. Before your report, check all nine:
  - `sha256sum -c SHA256SUMS` run from `studies\` shows 32 OK;
  - `find studies/debris-a -type f | wc -l` gives 29;
  - `sha256sum -c MANIFEST.sha256` shows 54 OK from `studies\debris-b\`, 136 OK from `studies\debris-c\`, 73 OK from `studies\debris-d\`, 60 OK from `studies\debris-e\`, 61 OK from `studies\debris-f\` and 43 OK from `studies\debris-g\`;
  - there is no `__pycache__` anywhere under `studies\`.
- **Host traps:**
  - **System32 before PATH.** From Python, or anything else that calls CreateProcess, Windows searches System32 before PATH. So a bare `bash` is `C:\Windows\System32\bash.exe`, the WSL launcher, and a bare `timeout` is `TIMEOUT.EXE`. System32 also holds `wsl`, `tar` and `curl`. Start every program from Python by its full path, such as `C:/msys64/usr/bin/bash.exe` and `C:/msys64/mingw64/bin/gcc.exe`, or run it through the Bash tool directly (round DEBRIS-D, `lead.md`, 2026-11-12 21:23).
  - **MSYS `.exe` transparency:** writing a file `X` beside an existing `X.exe` writes to `X.exe`.
  - **CRLF:** passing a script to bash from Python with `text=True` turns every newline into CR+LF. So does any text-mode write from Python on Windows, `Path.write_text` included. Write bytes, or open with `newline="\n"`, wherever a file's bytes matter. The box's shell will not run a script with CR bytes, and hashes are taken over bytes.
  - **Backslashes:** in the Bash tool, a doubled backslash reaches the shell as one, inside a heredoc too. Write any script that contains backslashes with the Write tool, and write Windows paths in commands with forward slashes. Every check asserts that it found something to check.
  - **`cd`:** a Bash `cd` into a subfolder can move the session's working directory for every later call. Use absolute paths, or `git -C`.
  - **`grep` and CR:** Git Bash's `grep` strips the CR at each line end unless given `-U`. Count CRLF with Python.
  - **Transcripts:** a harness task's `%TEMP%` output file is empty while the agent runs. A transcript is read from the session's `subagents\` folder.
  - **Never start a process under `pythonw`,** or detached, on the desktop.
- **No helper agents.**
- **Your final message is your report,** or, for DEBRIS-H's phase 1, its hand-off. Its word limit is in your brief. If the harness refuses the write of a document your brief names, your final message is that document followed by the report, and the word limit then applies to the report alone.
- **Before you report,** stop any background work you started. End with what you did not do, and with anything your brief got wrong.

## READY, stated before the first pass

READY applies to DEBRIS-H and to every verifier's verdict. Every load-bearing claim must rest on one of:
- a measurement, with its command and output;
- a fetched source, cited by URL;
- arithmetic from labelled inputs.

Otherwise it is stated as a limit, in terms of the behaviour it concedes. A claim's domain and quantifier are claims, and so is a figure's definition. A number carried over from an earlier study keeps its definition, or it is re-measured.

**From rounds DEBRIS-B to DEBRIS-G:**
- **Every control states its pass and fail criteria before the data, and the code asserts them.** A control that fails as specified is reported as failed, whatever replaces it.
- **Every agreement claim states its tolerance before the data,** with its basis.
- **A measurement with no pass condition states its statistics, its configurations and its sample before the data.** H7's misses, lags and the kinds' divergence are such measurements.
- **Every log names the SHA-256 of the script that wrote it,** and the criterion that script asserted.
  - Keep every version of a script that wrote a log, under a name carrying the first 12 hex digits of its hash, before you change it.
  - Never overwrite a log: number each run's log.
  - The manifest lists every version.
- **Every build prints the SHA-256 of every source it compiles.**
- **An ESTIMATE names its basis and its range,** and is never added to a MEASURED figure without saying so.
- **A bound over many trials holds only when the trials are independent.** Say what varies from trial to trial.
- **A cause is claimed only when a run isolates it.** Otherwise it is inferred, and labelled so.
- **Every throughput or lag figure names its configuration** (the kind, the workers, the lanes and the priority) and the foreign load of its interval.
- **Every ratio of times says what it divides:** wall times or CPU times.

**New in this round:**
- **Every miss statistic names its method, its cell, its count, and whether the flagged fits are in it.**
- **Every check's reference is the catalogue,** not the truth. No sentence calls a miss an error of M1 against the sky.
- **A pause, a restart and a fetcher's stop are each recorded where they happen,** with their times, and no statistic silently spans one.

A verifier may reuse a run instead of re-running it only when all three of these hold:
- someone other than the author of the work made the run;
- its inputs are identical, file hashes included;
- the verifier re-runs from clean whatever it doubts.

The box's runs are the lead's, from DEBRIS-H's code. So their logs count as made by someone other than DEBRIS-H, but not as independent of DEBRIS-H's code.

Only a wrong answer sends work back: a false claim, a measurement or check that cannot fail, or code that does not build or does not do what its gate says it does. Everything else is a note the lead records, and a sentence that claims too much is narrowed at the merge.
- **Loop cap (Logan, 2026-10-15, carried through the lead's memory):** after three NOT READYs for narrowing reasons, the next pass blocks only on wrong answers.
- **Threat model (Logan, 2026-10-02):** each verifier's brief states one, and findings outside it do not reopen the loop.

## Logan's decisions (each default stands unless changed)

1. **Models:**
   - (a) **Opus for DEBRIS-H, Sonnet for verifier-H,** and Haiku for a merge-check. This is Logan's pairing for challenging work (2026-10-12): the round builds a service with clocks, restarts and a decoder on a second machine;
   - (b) Sonnet for DEBRIS-H and Haiku for verifier-H, as in DEBRIS-G. DEBRIS-G's Haiku verifier stopped early once and ran over its budget.
   - Default: (a).
2. **Where SGP4 runs for the seed and the checks:**
   - (a) **on the box, through Orekit as in DEBRIS-F.** Logan installs Java 8 there himself (Ubuntu's `openjdk-8-jre-headless`, which is BELIEVED to carry Nashorn, as Java 8 does). The lead copies DEBRIS-F's Orekit and Hipparchus jars and the Earth orientation files to the run folder. H4 then holds the box's decode to the desktop's;
   - (b) on the box, through python-sgp4 (MIT): one wheel downloaded on Logan's approval, unpacked in the run folder and never installed. DEBRIS-H then writes and verifies its own conversion from TEME to GCRF, held to Orekit's on the desktop;
   - (c) on the desktop: the box runs the service and archives every fetched set, and the lead runs the checks from those records when it visits and at the end. The run still checks itself, but not as it goes.
   - Default: (a). The lead never runs `sudo`. If Java is not on the box when DEBRIS-H hands off, the lead runs the seed on the desktop and the checks as in (c), and tells Logan.
3. **The population:**
   - (a) **S_H0,** a new snapshot of DEBRIS-F's four groups taken when the service is ready: one object per element set, perigee at least 200 km, the set no more than 30 days old at T_s. DEBRIS-F's S0 had 2,686 distinct sets in these groups;
   - (b) DEBRIS-F's S0, already downloaded: no new seed request, but its sets are two days old already, and older by the launch;
   - (c) a larger group, such as `active`, at a cheaper kind.
   - Default: (a).
4. **The tracks:**
   - (a) **cft256 and native64** for every object, from one seed;
   - (b) **as (a), and a third track:** native64 from a second seed whose fit holds `bc` at 0.01 m²/kg for every object (see "The seed");
   - (c) as (a), with cft128 on a fixed sample of 256 objects as well, to bound cft256's own rounding by a second wide kind;
   - (d) cft128 as the main kind, for more headroom at night.
   - Default: (b). cft256 is the widest kind, as Logan's preference asks. Each native64 track costs about 0.2% of one worker (COMPUTED from G4), and the second seed about 110 CPU-minutes of fits on the box (see "The seed"), a few minutes on 36 processes. DEBRIS-F's finding on `bc` makes the third track the cheapest test of the seed's drag.
5. **The run's length:**
   - (a) **72 hours,** then it stops by itself. Whether a service runs on after this round is decided at the round's end;
   - (b) 24 hours;
   - (c) open-ended: the round reports at 72 hours, and the run goes on until Logan stops it.
   - Default: (a).
6. **Workers and priority:**
   - (a) **18 cft256 workers and one worker for each native64 track, at nice 19, unpinned, day and night,** beside cft-fp256's windows as their text allows;
   - (b) as (a) by day, and 9 cft256 workers in S003 and S004, switched by a restart from the latest checkpoint at each window's edge. Nine workers carry about 2,090 objects at real time (9 × 299 × 0.776, from G4's efficiency at 9 workers of 0.76 to 0.78, COMPUTED), so the run falls behind in those windows: by about 3 hours by 07:45, caught up by early afternoon, and by about 14 hours over a weekend (ESTIMATE, at 2,700 objects and 18 workers' 4,176 by day);
   - Default: (a). Phase 0 tells cft-fp256's lead, who may ask for (b) or a pause.
7. **CelesTrak's requests:**
   - (a) **the fetcher on the box,** run by the service: the four groups' CSV every 3 hours counted from S_H0, which is slot 0. That is 32 requests a day, and 96 after S_H0's own 4. It stops for the rest of the run at the first response that is not HTTP 200 or a body that fails its check. A request with no response ends its slot, and a second such slot in a row stops it;
   - (b) as (a), but the first request with no response stops it too;
   - (c) the GP directory query (`jsonDir.php`) once an hour, and the four groups fetched once after each update: every update once, about 48 data requests and 24 directory queries a day. The policy allows directory queries hourly; the query's output has not been examined;
   - (d) the lead fetches by hand when it visits.
   - Default: (a). S_H0's four requests are the lead's.
8. **Downloads** (each file needs Logan's approval; all are free and need no account):

   | row | file | URL | size | purpose |
   |---|---|---|---|---|
   | 1 | `finals2000A.daily` | `https://maia.usno.navy.mil/ser7/finals2000A.daily` | not listed | fresh Earth orientation data for H0's table and for Orekit; only under (b) |
   | 2 | `tai-utc.dat` | `https://maia.usno.navy.mil/ser7/tai-utc.dat` | not listed | the leap seconds, checked against DEBRIS-F's copy; only under (b) |
   | 3 | `checksums.sha512` | `https://maia.usno.navy.mil/ser7/checksums.sha512` | not listed | USNO's own hashes for rows 1 and 2, where it lists them; only under (b) |
   | 4 to 7 | the four groups' CSV, at S_H0 | `https://celestrak.org/NORAD/elements/gp.php?GROUP=<group>&FORMAT=csv` | about 0.4 MB in all (MEASURED for S0: 413,811 bytes uncompressed) | the seed |
   | 8 on | the same four, every 3 hours during the run | as rows 4 to 7 | as above | the checks (decision 7) |

   - (a) **rows 4 on.** H0's table and Orekit use DEBRIS-F's `finals2000A.daily`, already in the downloads, whose predictions cover the run (see "The frame table and the Earth orientation file");
   - (b) all rows, with a fresh Earth orientation file.
   - Default: (a). Over the run's days, the difference between predictions made from data to 2026-11-15 and a fresh file is far below the misses this round measures: USNO's UT1 predictions a week out are good to about a millisecond (BELIEVED, not checked), and a millisecond of Earth rotation moves a point 7,000 km from the axis by about 0.5 m (COMPUTED). The lead records each size at download.
9. **Bookings and pauses:**
   - (a) **a `shared` booking on `box` for the run's window:** the TimeSheet's mode for "a long CPU job at low priority" (READ, its README). It overlaps cft-fp256's `shared` windows, and it refuses others' `exclusive` and `sensitive` bookings on `box`, so a session that needs the box to itself asks, and the lead pauses the run for it (or Logan decides). Its text says how to ask, and how to pause the run in need: create `PAUSE` in the run folder, and remove it to resume. The box's gate runs are short work, run when `check box --short` answers FREE, or booked when longer;
   - (b) a `notice` for the window. It blocks no one, so another session's `exclusive` or `sensitive` window could open over the running service unless someone pauses it; the README names `notice` for "a series of short runs".
   - Default: (a) (plan-verifier-H's D10).
10. **Who runs the box's work:**
    - (a) the lead, as the standing rule has it;
    - (b) DEBRIS-H itself, over ssh, inside the lead's bookings.
    - Default: (a).
11. **Scope and budgets:**
    - (a) **One round:**
      - DEBRIS-H's phase 1: 7 hours of wall time and 50 CPU-minutes on the desktop, enough for H6 twice (plan-verifier-H's D6). Its fixes after a failed box run: 2 hours and 15 CPU-minutes in all. Its phase 2: 2.5 hours and 15 CPU-minutes. It messages the lead before passing any of these, and before any single desktop run it expects to pass 5 CPU-minutes, H6 included;
      - the box: the gates as short work; the paced dry run (30 minutes) and the seed under a `notice`; the long run under decision 9;
      - verifier-H: 3 hours and 25 CPU-minutes on the desktop, and up to 30 CPU-minutes on the box, run by the lead at its request;
      - a merge-check: 25 minutes.
      - **If time runs short,** the lead cuts in this order:
        1. the run's length, to 48 hours;
        2. H2's changed worker count and its pause (R2 and R3);
        3. H7(d)'s audit sample, from 10 segments per kind to 5;
        4. H5's reproduction of DEBRIS-F's fits.
        
        H0, H1, H2's restart and controls, H3, H4, H6, the seed and H7's criteria are kept.
    - (b) **Two rounds:** the build and the gates first; the long run in a second round.
    - Default: (a). For scale, DEBRIS-F used about 56 of its 95 CPU-minutes.
12. **Outputs and the push:** the lead commits after verification and the merge. Pushing to the public repository waits for Logan's word.
13. **Per-object data:**
    - (a) the seed file, the checkpoints, the fetched GP files and every output that names an object or holds its state stay in the ledger's `debris-h\`. The repository gets the rules, the counts, the files' SHA-256 and aggregates;
    - (b) published as well, but only after the lead reads CelesTrak's terms on derived data and finds that they allow it, and Logan agrees.
    - Default: (a), as in DEBRIS-F and DEBRIS-G.
14. **libcft:**
    - (a) the archive in the ledger, at 0aa997a3, as in DEBRIS-E to DEBRIS-G;
    - (b) cft-fp256's main at d4964c3c, with its GPU work of round 2, in a new archive made in Phase 0.
    - Default: (a). This round uses no GPU, and the run's numbers stay comparable with DEBRIS-G's.

## Not in this round

- **A GPU port** of M1 through cft-fp256's `hip:N`, the Arc A750, the MI300X, and certificates. The service's workers are where a GPU backend would go.
- **Re-fitting objects from new sets during the run,** or adding new objects: the population is fixed at T_s, and its arrivals and decays are counted.
- **Anything that restarts the service by itself:** no cron entry, no systemd unit, no change to logind's Linger. A reboot ends the run until the lead restarts it.
- **Any change to M1's library,** its physics or its accuracy. `src\` stays byte for byte as at commit 1646c96.
- **Space weather.** M1's atmosphere is static, and this round adds no drag model.
- **Any download or request beyond decision 8,** any account, and any GPU, WSL or card.
- **Removing the box's old run folders** (`cft-debris-f9\r1`, `r2`, `cft-debris-g\r1`), which waits for Logan's word.

---

## Brief: DEBRIS-H

You are build parcel **DEBRIS-H** in cft-debris, a project for space-debris tracking and simulation. Its folder, `C:\Users\logan\source\repos\cft-debris`, is a public git repository under the MIT licence. You build what the lead needs to run M1 as a service on amd-arc-box for 72 hours:
- H0, a new frame table;
- the seed: each object's state at the run's start;
- a driver and a supervisor that step at the wall clock, keep checkpoints, restart and pause;
- a fetcher of CelesTrak's updates;
- the check of M1 against each new element set.

Then, after the lead's long run, you analyse its records and write the build report. You never connect to the box, and you never request CelesTrak: the lead runs everything on the box, and you test the fetcher against a local server only. You commit nothing: the lead commits after verification.

**Two phases.**
- **Phase 1:** 7 hours of wall time and 50 CPU-minutes on the desktop. It covers H0, H-a to H-e, the gates' scripts, their desktop runs, and H6's desktop half. It ends with your hand-off, your final message, under 700 words:
  - the files the lead stages to the box, with their SHA-256, and the run folder's layout;
  - the exact commands in order, each with its expected wall time (ESTIMATE) and what it must print;
  - what is per-object and must come back to the ledger, not the repository.
- **Fixes:** if a box run fails, the lead resumes you with its log. Fix, re-test on the desktop, and hand off again: up to 2 hours and 15 CPU-minutes in all.
- **Phase 2:** 2.5 hours and 15 CPU-minutes. The lead resumes you when the run has ended, its aggregate logs are in `studies\debris-h\box\` and its per-object files in the ledger's `debris-h\box\`. You evaluate H7, run the analysis and write the build report. Your final message then is your report.
- Message the lead before passing any budget, and before any single desktop run you expect to pass 5 CPU-minutes. cft256 costs about 0.05 CPU-s an object-step on one box worker (15 / 299, COMPUTED from G4), and more on the desktop under load. So hold desktop tests to a few objects and steps.

**Start here:**
1. This plan, `C:\Users\logan\source\repos\cft-debris\studies\DEBRIS-H-plan.md`: Logan's words, the design and its reasons, and what the round starts from.
2. M1 and the pipelines you build on:
   - `src\`;
   - `tests\m1f.c`, `tests\build_f.sh`, `tests\f_lib.py`, `tests\f_fit.py`, `tests\f5_sgp4.js`, `tests\f6_hindcast.py`, `tests\m1nodes.c` and `tests\f3_gate.py`;
   - `tests\m1g.c`, `tests\g_harness.py` and `tests\g_stage.py`;
   - `studies\DEBRIS-F-build.md` and `studies\DEBRIS-G-build.md`, each narrowed at its merge, with its narrowings listed in its last section.
3. `lead.md` in the ledger: Phase 0, the downloads and their SHA-256, and the archive.

**Where it goes:**
- `tests\`: the new code. `src\` stays byte for byte as at commit 1646c96, and your builds assert it. Reuse earlier code by copying it into new files with a note of where it came from; earlier files stay unchanged.
- `studies\debris-h\`: the logs and records, with a `MANIFEST.sha256` over them. The lead puts the box's logs in `studies\debris-h\box\`.
- `studies\DEBRIS-H-build.md`: the build report.
- `cft-debris-ledger\debris-h\`: the seed file, the table's working copy, and every output that names an object or holds its state.
- **In your scratch only:** cft-fp256's sources, libcft's build and every executable.
- **Paths:** every script takes its paths from its arguments or its run folder. None hard-codes a home folder; DEBRIS-F's `tests\f_lib.py` did, and its verifier had to repoint it.

**H0. The frame table.** Build it with `tests\m1nodes.c`, unchanged, from DEBRIS-F's `finals2000A.daily` (decision 8(a); under 8(b), Phase 0's fresh copy) and DEBRIS-F's IERS series, over TDB 2026-10-17 00:00 to 2026-12-28 00:00. If the Earth orientation file does not reach that end, stop at its last row of predictions less a day, and say so. Then re-run DEBRIS-F's F3 checks (`tests\f3_gate.py`, copied and repointed) on the new table at its own dates: the node routine against Orekit, with F3's tolerances. The table goes in the ledger's `debris-h\`, and its SHA-256 in the build report.

**H-a. The seed:** one script, `tests\h_seed.py`. It fixes every rule below in its text before it reads S_H0's values.
- **Rows:** S_H0's four CSV files; ephemeris type 0 only.
- **One object per element set,** by DEBRIS-G's key (`tests\g_pop.py`): keep the smallest catalogue number in each set.
- **The screens:** perigee at least 200 km (DEBRIS-G's formula, GM = 3.986004415e14 m³/s²); the set's epoch no more than 30 days before T_s. Count each exclusion.
- **T_s** comes from the lead's command line: a multiple of 600 s on M1's TDB axis, set at least 20 minutes after the seed starts.
- **The fit:** DEBRIS-F's B4, unchanged in its rules: the origin, the 721 pseudo-observations from Orekit's SGP4, `m1f fit` at native64 with its iteration limit, `bc` estimated below 1,000 km of perigee and fixed above, and `cram` fixed. A fit that stops on the iteration limit keeps its last iterate and is flagged.
- **The second seed** (decision 4(b)): the same rules, with `bc` held at 0.01 m²/kg for every object (`fitbc` = 0 in `tests\f_fit.py`'s terms).
- **The catch-up:** `m1f prop` at native64 from O to T_s: whole steps, then one short step landing on T_s. An object below 120 km at T_s in either seed, or whose catch-up stops early, is left out of every track and counted.
- **The Earth orientation file** is DEBRIS-F's for every fit, under decision 8(a).
- **The file:** one line an object, with its index, catalogue number, flags, T_s, its binary64 state, `bc` and `cram`, every value in `%a` hex. It goes in the ledger's `debris-h\`.
- **Where it runs:** on the box, by the lead, with up to 36 processes, under decision 2(a). On the desktop it runs for tests only, on at most 5 objects, unless decision 2(c) applies.

**H-b. The driver:** a new C program in `tests\`, built from `tests\m1g.c` and `tests\m1f.c`, with an MIT header.
- **Mode `run`,** a live worker. Its inputs: the kind-mode, the frame table, a seed or checkpoint file, its slice, the lanes (64), the start step k0, the end step, the clock map, the allowance (4 steps), the checkpoint interval (40) and the run folder.
- **The loop is step-major,** as in DEBRIS-G. Before step k:
  - while `PAUSE` exists, wait, checking every 5 s, and log the pause's start and end;
  - if step k is due more than 60 s ahead, sleep until its due time less 60 s, plus this worker's stagger: i × 15/W s for worker i of W.
- **After step k:** record k, its finish time, its due time and its lag. At every multiple of 40, write the checkpoint: each state in the kind's own bytes and in binary64, with k, to a temporary name, flushed, then renamed. If that checkpoint exists already, after a restart, write yours under a new name and never overwrite.
- **On SIGTERM:** finish the current step, then exit. The supervisor restarts from the latest checkpoint.
- **The end checks, at every checkpoint:** every state finite, and every object's distance from the centre above 6,498.137 km. An object below it is marked decayed at that checkpoint, and is not checked after it. A non-finite state stops the worker with its object's index.
- **Mode `seg`:** from a checkpoint file at step k, for given objects, either to given epochs (whole steps to the last grid point at or before each epoch, then one short step landing on it) or to step k + n. Its output: each state in the kind's bytes and in binary64.
- **Clocks:** due times by `CLOCK_REALTIME`, durations by `CLOCK_MONOTONIC`; on Windows, their equivalents, for tests.

**H-c. The supervisor:** `tests\h_service.py`, standard library only.
- One instance per run folder, held by `flock`.
- It starts each track's workers at nice 19, unpinned, with decision 6's counts, and records the clock map. The map's TDB − UTC at T_s is checked against Orekit's (H5).
- It compares every checkpoint a restarted worker rewrote with the original, and stops the track if they differ.
- It restarts a track from its latest complete checkpoint when a worker exits, by the rule in "The design", and logs each restart with the checkpoint used.
- Every minute it samples `/proc/stat` and its own processes' CPU times, and logs the foreign load: everything but its own processes, as a share of 36 CPUs.
- At each slot (every 3 hours from S_H0's request, which is slot 0) it runs the fetcher, then the check, at nice 19. With checks off (decision 2(c)), it runs the fetcher alone, and needs no Java.
- When free space falls under 5 GB, it creates its own pause file and logs it. It removes the file when free space is back above 6 GB.
- Every minute it writes `status.json`: each kind's step, its latest lag, the latest checkpoint, the latest fetch and check, the restarts and the foreign load.
- At T_s + 72 hours the workers stop at the end step, a final checkpoint is written, and it writes a summary.
- It never deletes a file, and never overwrites a log.
- `setsid` starts it, and it outlives its ssh session. H2 checks that.

**H-d. The fetcher:** `tests\h_fetch.py`, standard library only, from the rules of the lead's `dispatch\fetch_f.py` in the ledger and CelesTrak's policy as Phase 0 reads it.
- A slot makes one request for each of the four groups' CSV, 10 s apart. Its URLs are fixed in the script. Slot j is due 3j hours after S_H0's request, for j = 1 to 24.
- It asks for compressed transfer, follows no redirect, and retries nothing. Its User-Agent is a fixed generic client name with no personal details. It accepts an uncompressed body and a gzip-compressed one.
- **Each body is checked before it is kept:** CSV with the header's 17 columns, and at least one row. Rows of another ephemeris type are kept, counted and never checked. A body with fewer than half the rows of that group's previous body is kept, and logged as a finding for the lead.
- **At the first response that is not HTTP 200, or a body that fails its check,** it writes the stop file and makes no further request, in that slot or any later one.
- **A request with no response** (none within 60 s, or a DNS or connection error) ends its slot; the next slot tries again. A second such slot in a row writes the stop file. Under decision 7(b), the first does.
- Each body is stored decompressed, under a name of its own, never overwriting, with both sizes and its SHA-256 in an append-only request log, beside the response's Date and Last-Modified headers.
- **Test mode** takes a base URL on 127.0.0.1 and refuses any other host. **Live mode** refuses any host but `celestrak.org`, and makes no request in a slot whose time has not come.

**H-e. The check:** `tests\h_check.py`, with the decoder `tests\f5_sgp4.js` unchanged if it serves, or a copy with a note of what changed.
- It does what "The design" says: the reference, (A256), (A64), (A64f) and (B), the miss and its parts, and T1 to T3, all as `tests\f6_hindcast.py` defines them.
- Its inputs: the seed file, the run's checkpoints and manifest, and the new GP files. Its outputs: a per-object table for each slot (to the ledger), and an aggregate line for each slot (to the log).
- It never reads a checkpoint whose SHA-256 does not match the manifest.

**The gates.** For each gate: write its criteria into its script before its data, assert them in code, and give it a negative control that must fail as specified. The NaN rule holds throughout, as in DEBRIS-E: non-NaN results agree bit for bit, and NaN results agree as NaNs.

- **H0. The table** (desktop): F3's checks pass on the new table, with F3's tolerances, at the new window's dates. Its control is F3's own.
- **H1. The build** (desktop yours; box the lead's): every source's SHA-256 printed; `src\` byte-identical to commit 1646c96; a smoke run of `run` and `seg` at cft256 and native64, 4 lanes and 2 steps. Control C1: a copy of one source changed by one byte must fail the source check.
- **The test seed:** `h_seed.py` run on the desktop on 64 of DEBRIS-F's S0 objects, with T_s = 2026-11-17 00:00 TDB and H0's table, both seeds, each in a run of its own: about 2.5 CPU-minutes each, 5 in all (ESTIMATE: 64 fits at 2.25 to 2.4 CPU-s, from F6's record and F9's T3). H2 takes the first seed's first 16 objects, and the paced dry run all 64. It is per-object, so it goes to the ledger.
- **H2. The service's determinism** (box; on the desktop as a functional test, with 4 objects, 12 steps and checkpoints every 4). Sixteen objects of the test seed, at cft256 and native64, run 120 steps from T_s, with checkpoints every 40. The clock map is set in the past, so every step is due at once and the runs go flat out:
  - R0: unbroken, one worker;
  - R1: its worker killed by SIGKILL after a step between 41 and 79 that the script fixes, and restarted by the supervisor from checkpoint 40;
  - R2: restarted from checkpoint 80 with 4 workers instead of 1 (2 on the desktop, so that the gate, the supervisor and its workers stay within 4 processes);
  - R3: paused for 30 s after step 50, then resumed.
  
  **Criterion:** checkpoints 40, 80 and 120 are bit-identical across R0 to R3, at each kind. **Controls:**
  - C2: a checkpoint with one byte changed is refused by its hash, and nothing starts from it;
  - C3: a restart planted one step off, from checkpoint 40's states with k0 = 41, must give checkpoint 120's bytes different from R0's;
  - C4: R3's 30 s pause must appear in its step log as a pause, and as lag.
  
  On the box, H2 also starts the supervisor with `setsid` from an ssh session, ends that session, and checks from a new one that the supervisor is alive.
- **The paced dry run** (box, the lead's, under a `notice`): the test seed's 64 objects at cft256 on 1 worker, and at native64 on 1, for 30 minutes at the real clock's pace, with the clock map shifted so that T_s falls a minute after the launch, and the fetcher off. **Criteria:** no step starts more than 60 s before it is due; in minutes with foreign load under 5%, no step is late. **Control C5:** the same run with its clock map set 600 s in the past must log late steps from its start, then catch up. Let r be its simulated seconds per wall second while late (15 s × the late steps, over their wall time). The lag then shrinks by r − 1 a second, so the first step that is not late must come T = 600 / (r − 1) s after the start, and the measured time must lie within 10% of T.
- **H3. The fetcher** (desktop only, against a local `http.server` the gate script starts on 127.0.0.1 and stops by its PID). **Criteria:** one request per file per slot, `Accept-Encoding: gzip` sent, the fixed User-Agent sent, a gzip-compressed body and an uncompressed one each stored decompressed with both sizes and its SHA-256, and no file overwritten. **Controls,** each from a planted response:
  - C6: a 301 stops the fetcher, and the server's log shows no request after it;
  - C7: a 503 does the same;
  - C8: a 200 whose body is an HTML page does the same. A CSV with a tenth of the previous body's rows must be kept and logged, and must not stop the fetcher;
  - C9: a response delayed past the timeout ends its slot only, and a second such slot in a row stops the fetcher;
  - C10: a slot after a stop makes no request;
  - C11: test mode refuses a URL on any host but 127.0.0.1, and live mode refuses any host but `celestrak.org`, both without making a request.
- **H4. The decode on the box** (box, the lead's, under decision 2(a)). All of DEBRIS-F's S0 sets, decoded by `f5_sgp4.js` at three instants each, on the box and on the desktop, with the same jars and Earth orientation file. **Criterion:** bit-identical GCRF states. If they are not, the gate still passes when every position agrees within 1 mm and every velocity within 1 µm/s, and the differences are reported as a finding. The basis: 1 mm is a twenty-thousandth of the smallest cell median F6 reported, (B)'s 20 m (800 km and over, under 6 h, n 15). **Control C12:** one set with its mean motion moved by one ulp must change its states.
- **H5. The seed** (box, the lead's, at the start; and in phase 1 on the desktop, on the test seed's 64 objects, both seeds). **Criteria,** for each seed: every object fitted, converged or flagged, and counted; every object left out for its catch-up counted; every seed state finite and above 120 km; the cft256 and native64 tracks of the first seed start identical in binary64; in the second seed every `bc` is exactly 0.01 m²/kg. Also, the clock map's TDB − UTC at T_s equals Orekit's within 1 ms. **Controls:**
  - C13: one pseudo-observation of one object moved by 1 km must change that object's fitted state;
  - C14: a copy of the second seed with one `bc` changed must fail its `bc` criterion;
  - C15: a copy of the first seed's native64 track with one state moved by one ulp must fail the identity criterion.
  
  **The regression, on the desktop:** `h_seed.py`'s fits of five of F5(d)'s objects from S0, with DEBRIS-F's table and Earth orientation file, reproduce `f5d_fits.001.tsv`: the same iterations and convergence, and `bc` and the residuals equal at the printed digits.
- **H6. The check against F6** (desktop; then the box, under decision 2(a)). For each of F6's 200 pairs:
  - fit the object from its S0 set with `h_seed.py`'s fit, DEBRIS-F's table and DEBRIS-F's Earth orientation file;
  - run it alone from its origin O with the service's driver, at native64, with checkpoints every 40 steps and the clock map in the past;
  - then `seg` to e1, and the check, with S1's set as the new one.
  
  **Criterion:** (A)'s and (B)'s misses, and their three parts, equal `f6_pairs.001.tsv`'s within 1 mm, since the file prints them to the millimetre. T1 to T3 pass on every pair. On the box, every miss equals the desktop's within 1 mm, and any difference is reported: the fit's native64 uses each machine's C library. **Control C16:** one pair's e1 moved by 1 s must fail the criterion for that pair. Its cost on the desktop is about 9 to 10 CPU-minutes (ESTIMATE from F6's own record, `studies\debris-f\records\cpu.tsv`: 420 CPU-s of fits for 187 objects, about 2.25 s each, and 57 s of predictions; plan-verifier-H's D6).
- **H7. The long run** (box, the lead's, 72 hours). Criteria, fixed now:
  - **(a) the fetches:** every slot's requests logged; at most one request per file per slot; every 200's body archived with its SHA-256; any other response stopped the fetcher at once, with no later request;
  - **(b) the checks:** every eligible new set checked, or listed with its reason. Eligible means a later epoch than the last set checked for that object, an epoch no earlier than T_s, the object not decayed, and the fetcher not stopped. T1 and T3 pass on every check. T2 cannot fire here (see "The check");
  - **(c) the sanity bound:** over the run, (A256)'s median miss at horizons under 24 hours is at most 5 km, over at least 20 checks. With fewer, (c) is reported as not determined, never as passed. The basis: F6's cell medians under 24 h were 0.37 to 1.40 km; a 1 s time-tag error at these speeds moves a position by about 7.5 km, and TEME taken for GCRF moves it by up to about 44 km at 400 km altitude (COMPUTED from 26.9 years of precession at 50.29" a year). Under 6 h the checks will be few, since sets are published hours after their epochs (plan-verifier-H's D4);
  - **(d) the checkpoints:** every 40 steps of each track, all files present, each hash matching the manifest. A sample of 10 segments per track, drawn by a seed fixed in the script before the run, and always including every segment that follows a restart, re-propagated by `seg` from checkpoint k to k + 1 for 64 objects, equals checkpoint k + 1's bytes;
  - **(e) the pacing:** in every clock hour with foreign load under 5% of 36 CPUs and no pause, no step of any track is late, over at least 6 such hours. With fewer, (e) is reported as not determined. Elsewhere it is a measurement: the share of late steps, the largest lag, and how long the run took to catch up after each late stretch;
  - **(f) the kinds:** at T_s the cft256 and native64 positions of the first seed are equal. After that, a measurement.
  
  **The measurements,** with their statistics fixed now, for (A256), (A64), (A64f) and (B), per slot and over the run:
  - the miss distance's median and 90th percentile (the ceil(0.9n)-th smallest), and the same for the sizes of its radial, along-track and cross-track parts;
  - by horizon e − e0 (under 6 h, 6 to 24 h, 1 to 2 days, 2 to 3 days, 3 to 7 days, 7 days and over), by the run's age e − T_s (under 6 h, 6 to 24 h, 1 to 2 days, 2 to 3 days), by perigee band (under 500, 500 to 800, 800 km and over), by the seed set's age at T_s (up to 1 day, 1 to 3, 3 to 7, over 7), and by the sign of the fitted `bc`;
  - with and without the flagged fits. A cell of fewer than 20 checks gives its count and median only;
  - the share of checks in which (A256) misses less than (B). Checks cluster by object and by update, so this is not a share of independent trials;
  - the distinct objects checked, and the checks per object;
  - the kinds' divergence at every checkpoint: the median and the largest distance over the objects.

**Phase 2's analysis:** `tests\h_analyze.py` evaluates H7's criteria from the run's records and computes the measurements. Its log holds the aggregates; per-object tables stay in the ledger.

**The build report,** `studies\DEBRIS-H-build.md`: what was built, how to build and run it, each gate's criteria and result, the long run's timeline (its pauses, restarts and fetcher's state), H7's results and measurements, and the limits.

**Your report** (phase 2's final message, under 900 words): what you built, each gate's result, H7's results, what you did not do, and anything this brief got wrong. Label every figure.

## Brief: verifier-H (completed when DEBRIS-H reports)

You are **verifier-H** in cft-debris. Your job is to disconfirm DEBRIS-H's build, its gates and the long run's records, never to fix them. Edit no file outside your scratch. You never connect to the box: any box run you need, the lead runs from your script.

**Threat model.** A wrong answer in DEBRIS-H's work: a check that cannot fail; a restart or a pause that changes a state; a miss computed in the wrong frame, at the wrong time, or against the wrong set; a fetch that broke CelesTrak's policy; a statistic not as defined; a lag or foreign load not as defined; per-object data in the repository. Findings outside this model are notes and do not reopen the loop.

**Attack these, in this order:**
1. H2's controls bite: re-run C2 to C4 on the desktop.
2. H6: recompute 20 of F6's pairs' misses with code of your own, from the states the gate printed, and compare with F6's ledger values.
3. The check's frame and time: recompute 20 checks of the long run from the per-object tables' states, with code of your own.
4. The fetch log against the policy: the requests per slot, and what followed any response that was not 200.
5. H7(d): write a sampler with a seed of your own; the lead runs it on the box as short work. The bytes must equal the checkpoints.
6. The lag accounting: recompute the late shares from the step logs and the foreign-load samples.
7. The aggregates: recompute the medians and 90th percentiles from the per-object tables.
8. The seed's rules: one object per set, the screens, and the counts.
9. The kinds' divergence: recompute it from two checkpoints.
10. The repository: no catalogue number, state or personal string in any file under `studies\` or `tests\`.

**Budget:** 3 hours of wall time and 25 CPU-minutes on the desktop, and up to 30 CPU-minutes on the box. Message the lead before passing either. Your booking is the lead's notice: it already covers your desktop runs.

**Report:** your final message, under 1,200 words. Give each attack's verdict (confirmed, defect, or not determined) with its evidence. For every defect, the exact passage and what it should say.

## What changed from draft 1 (plan-verifier-H's findings, answered)

The lead checked each finding's evidence before answering it: the old Earth orientation file's span and flags, F5(d)'s iterations and `fitbc` values, S0's and S1's encodings and epochs, F6's cycles in `studies\debris-f\records\cpu.tsv`, and the TimeSheet's README. Every finding was upheld.

- **B1, the fetch schedule.** Slot 0 came 25 to 60 minutes after S_H0, inside the same 2-hourly update. S_H0 is now slot 0, and slot j comes 3j hours after it ("The fetcher", decision 7).
- **D1, the load.** Workers that wake together run in bursts of 18, up to 27 threads at night beside cft-fp256's 9. The workers are now staggered, worker i starting i × 15/18 s after worker 0, and the ESTIMATE gives both cases ("Workers").
- **D2, the Earth orientation file.** H5's regression and H6 now name DEBRIS-F's file. Its predictions cover the run (MJD 61270 to 61450, MEASURED), so decision 8's default is now no new download, with the fresh file as (b).
- **D3, the folders.** New copies would go in folders named with `-H`, and S_H0 goes in `gp-<group>-SH0\` (Phase 0). `dispatch\fetch_h.py` is written that way, and has been run dry only.
- **D4, criteria that could pass empty.** H7(c) now covers horizons under 24 hours, over at least 20 checks, and H7(e) needs at least 6 qualifying hours; with fewer, each is "not determined". The sets' publication lag is now a stated fact, and the measurements add the run's age.
- **D5, the seed's gaps.** Controls C14 and C15 cover the second seed's `bc` and the tracks' identity, and the controls now run C1 to C16 without a gap. The held-`bc` path runs on the test seed's 64 objects in phase 1. An object that falls below 120 km in its catch-up is left out of every track and counted.
- **D6, the costs.** H6 is now about 9 to 10 CPU-minutes and each seed about 110 CPU-minutes on the box. Phase 1's budget is 50 CPU-minutes, enough for H6 twice.
- **D7, the desktop's R2:** 2 workers there.
- **D8, H4's basis** (the lead's slip 5): the smallest cell median is (B)'s 20 m, so 1 mm is a twenty-thousandth of it.
- **D9, the fetcher.** A body is checked before it is kept. H3 serves both encodings, and plants an HTML body and a short CSV. A request with no response ends its slot, and only a second in a row stops the fetcher; decision 7(b) is the stricter choice. Decision 7 also gains the directory query as (c).
- **D10, the booking.** Decision 9's default is now `shared`, the TimeSheet's mode for a long CPU job at low priority, so others' `exclusive` and `sensitive` bookings are refused and they ask. A pause takes hold in under 20 s, and the disk pause ends above 6 GB free.
- **D11, C5's condition:** T = 600 / (r − 1), within 10%.
- **Notes taken:** "all nine" checks; T2 stated as unable to fire in the run, and kept in H6; a restarted worker's rewritten checkpoints compared with the originals; the clock map's TDB − UTC held to Orekit's within 1 ms (H5); a supervisor mode without checks, for decision 2(c).
- **Also new in draft 2:** the lead's second reading of CelesTrak's policy (`lead.md` 06:16): brotli, the directory queries, enforcement on larger sets, and the shared address's risk.

## What changed from draft 2 (plan-verifier-H's re-check, answered)

The re-check found no blocker, and confirmed draft 2's answers in every place it looked. Its three defects were lines left in draft 1's form, and each is fixed:
1. the part table's H0 named fresh Earth orientation data. It now names DEBRIS-F's file (decision 8);
2. "The ledger" said that this round adds Phase 0's three files. It now says S_H0's four, in `gp-<group>-SH0\`, and USNO's three only under decision 8(b);
3. the test seed's cost said about 2 CPU-minutes, for one seed. Draft 2 runs both, so each now runs on its own, at about 2.5 CPU-minutes, and neither passes the 5-minute line unannounced.

Its four small concerns:
- **The pause's latency** now reads about 20 s, or about 24 s when a shared core halves a worker's speed.
- **The body check:** draft 2 stopped the fetcher for a row of another ephemeris type, or a group halved since the last slot. Draft 3 stops it only for a body that is not the CSV, and keeps and logs the rest, since `stations` held 17 rows and could shrink for real.
- **The stagger and the allowance:** "Time" now says that worker i starts each step between 60 and about 46 s before it is due.
- **The predicted Earth orientation:** "The frame table and the Earth orientation file" now gives the file's dX and dY to MJD 61437, and DEBRIS-F's rule that kept its epochs to 61430. H0's window ends at 61402.

## What earlier rounds taught, applied here

- **One object per element set** (DEBRIS-F's narrowing 11): the seed's rule.
- **Hard-coded paths** (DEBRIS-F's `f_lib.py`): every new script takes its paths from its arguments.
- **A criterion its script never evaluated** (DEBRIS-G's F9 test): every criterion here is asserted in code.
- **Too many processes on the shared desktop** (DEBRIS-G's build and its verifier): the limit of 4 now counts every child process, and the briefs say so.
- **Script versions overwritten before they were kept** (DEBRIS-G): keep each version before changing it.
- **A Haiku verifier** stopped early and overspent (DEBRIS-G): this round's verifier is Sonnet, with sizes stated.
- **The build report edited before its as-reported copy was kept** (the lead, DEBRIS-G): the lead copies every report before any edit.
- **The TimeSheet's output:** read a booking's id from its `BOOKED` line, never from the last line (the lead, DEBRIS-G).
- **Estimates of serial work** (DEBRIS-G's G2): this plan's box times are ESTIMATEs, and the lead records the real ones.

## The lead's slips so far

1. **The 05:57 entry of `lead.md`** stated where the "ends by 17:50" rule came from as if READ. It is the lead's reading of S001's text, BELIEVED.
2. **The same entry** named chrony as the box's clock service. The survey's line reads `active inactive` for `systemd-timesyncd chrony`, in that order, so it is systemd-timesyncd. Draft 1 repeated the slip, and the lead's own check of the survey caught it before the checker ran. The 06:09 entry corrects both.
3. **The checker's first two versions,** which wrote its logs 001 and 002, were edited before they were kept. Each log names its script's SHA-256 on its first line. The version that wrote log 003 and later is kept as `check_plan_h.6b56f942b714.py`.
4. **One of the checker's first controls could not fail** (an `or True` in its condition). The lead found it before the first run, and replaced it with the same predicate applied to a perturbed copy of the table.
5. **Draft 1's H4 basis** called (B)'s overall median, 75 m, the smallest median F6 reported. The smallest cell median is 20 m (plan-verifier-H's D8).
6. **Draft 1's fetch schedule** would have fetched S_H0's update twice (plan-verifier-H's B1), and its load account averaged away the workers' bursts (D1). Both were the lead's design errors.
7. **Draft 2 left three lines in draft 1's form** (plan-verifier-H's re-check). The lead's edits followed the findings' sections, and missed the same facts stated elsewhere.
