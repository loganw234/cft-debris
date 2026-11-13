From cft-rebound's lead: study DEBRIS-A, on REBOUND for long-term debris prediction, handed to your project. It covers what it found, what it did not settle, and where its files are.

**What it is.** DEBRIS-A is a study parcel that Logan asked cft-rebound's lead for on 2026-11-12. It is a study only: nothing was built, and no repository changed. Every claim carries a label:
- MEASURED: run, with the command in its §7;
- COMPUTED: arithmetic from stated inputs;
- READ: cited, sources [S1]-[S17];
- BELIEVED: judgement.

**It has had no verifier.** Its labels are its own author's. Treat it as the starting point, not as evidence: your first parcel should re-measure the numbers below before anything rests on them.

**The question, in Logan's words:** "determine if rebound (and if so which integrator) would work best for long term high density space debris prediction, ideally capable of running in either direction to prove itself against historical data and cycle at a divergence from real data."

**Short answer**
- **REBOUND is a sound integrator and the wrong platform.**
  - IAS15 handles drag, a moving Moon, and backward runs (MEASURED). After a day of LEO with J2 it lands within 1.4e-7 m of a binary128 reference, and every round trip comes home within 1.1e-6 m.
  - REBOUND has no atmosphere, no gravity field past REBOUNDx's J2 and J4, no frames, Earth orientation or time scales, no TLE handling, and no orbit determination (READ).
  - Its state transition matrix leaves out every force a user adds. One column was 44% wrong after a day with J2 added as a Python force (MEASURED). With J2's Jacobian supplied by hand it agrees to 8e-10.
- **Which integrator: IAS15 in every regime.** The symplectic family's advantage does not survive a debris force model as REBOUND implements it (MEASURED):
  - drag takes SABA(10,6,4) from 1.5 µm a day to 1.6 m, and JANUS from a bit-exact round trip to an 8 m miss;
  - a time-dependent Moon breaks JANUS's exact return;
  - SABA's one-year MEO/GEO round trip misses by 9 to 73 km, because SABA, EOS and JANUS evaluate every stage's force at the step's start time (READ, in REBOUND's source).
- **cft-rebound, a multi-precision port of REBOUND's IAS15, is the wrong tool here.** The force model limits debris prediction, not the arithmetic (MEASURED):
  - a 20% density error moves a 400 km object 5.0 km in one day, while binary64 and binary128 differ by 1.2e-8 m: a factor of 4e11;
  - the port ran 145 times slower than REBOUND on the same steps (12.5 s against 0.086 s for a day), with bit-identical results;
  - it refuses variational particles.
- **"Either direction"** runs everywhere, but a round trip proves only that an integrator inverts itself. Proof against history is a hindcast: fit to past data, propagate, and compare with independent truth. TLEs are SGP4 mean elements, so they need SGP4 or a fit first.
- **"Cycle at a divergence"** is orbit determination: batch least squares or a filter.

**Recommendation (BELIEVED)**
- **Populations and conjunctions:** ESA's cascade, built on heyoka. READ: its example propagates the US-tracked LEO catalogue with J2, C22/S22 and drag, 30 days in 64 s on 32 threads.
- **Single objects, hindcasts and the re-fit cycle:** Orekit, which has SGP4, TLE fitting, atmospheres, Earth orientation, least squares and Kalman filters.
- **Decades to centuries, statistically:** MASTER, DELTA, LEGEND or MOCAT-MC, or the semi-analytical DSST, STELA and THALASSA.
- **If REBOUND anyway:** IAS15 with forces in C and a hand-written Jacobian for each, as ASSIST does.

**Not settled**
- **The real force model's cost** was not measured, and it decides the budget. For 54,000 objects a year it ranges from 15 CPU-hours at point-mass cost to 28-280 CPU-days at a BELIEVED 10-100 µs per force evaluation.
- **cascade, heyoka and Orekit** were read about, not run.
- **TLE accuracy and density-model error** figures come from secondary sources.
- **The MEO/GEO reference** was not checked at binary128.

**Files.** These are in cft-rebound's lead session's temporary scratchpad, so copy them into your repository on arrival:
- the study: `C:\Users\logan\AppData\Local\Temp\claude\443d8e8619fd4f31\fa64df2f-560a-4117-8348-b3ce1b89172a\scratchpad\studies\DEBRIS-A-rebound-for-debris.md` (418 lines);
- its scripts, logs and records: `...\scratchpad\studies\debris-a\` (146 KB);
- its brief: `...\scratchpad\studies\DEBRIS-A-brief.md`.

The scripts use the rebound 5.1.1 wheel in `C:\Users\logan\AppData\Local\Programs\Miniconda3\python.exe`. `port_roundtrip.py` points at a build of cft-rebound's `ias15_cft` in a worktree that is removed when cft-rebound's round 4 closes; rebuild from cft-rebound's main if you rerun it.

**Who to ask**
- **cft-rebound's lead** (session cft-REBOUND): the study, REBOUND at its pin, and the port.
- **cft-fp256's lead:** GPU slots and libcft. GPU work is coordinated through cft-fp256 first.
- **Both repositories** are read-only to you.
