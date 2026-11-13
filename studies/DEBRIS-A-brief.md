You are study parcel **DEBRIS-A**, dispatched by the lead of cft-rebound on 2026-11-12. It is a small study, not an implementation: nothing is built, nothing is committed, and no repository changes.

## The question (Logan's words)

> "determine if rebound (and if so which integrator) would work best for long term high density space debris prediction, ideally capable of running in either direction to prove itself against historical data and cycle at a divergence from real data. No work needs to be done yet, this is just a study"

Read it as four questions, each answered with a verdict and its evidence:
1. **Fit.** Is REBOUND, or this repository's port of its IAS15 (cft-rebound), a sound core for long-term propagation of many debris objects? What it brings, what it lacks, and what the lack would cost.
2. **Which integrator.** Among REBOUND's at the pin (third_party/rebound at bdfda4bd): IAS15, WHFast/WHFast512, JANUS, TRACE, MERCURIUS, SABA, EOS, BS, LEAPFROG, and any others there. Answer by orbit regime: LEO, where drag and solar radiation pressure are non-conservative and velocity-dependent; MEO, GEO and graveyard orbits, which are nearly conservative. Weigh accuracy, cost per object, support for velocity-dependent forces, variational equations, and reversibility.
3. **Running in either direction.** Separate three kinds of reversibility:
   - physical: drag is dissipative, so what does "backward" mean, and what limits it;
   - numerical: the round-trip error of a forward-then-backward run;
   - bitwise: JANUS's integer reversibility.
   Say what a backward run could and could not prove against historical data. Name what the comparison data are: TLEs are SGP4 mean elements, not osculating states, so comparing a numerical propagator with a TLE history needs SGP4 or a fit. Name what else is needed.
4. **"Cycle at a divergence from real data."** Re-initialising when a prediction leaves the observations is orbit determination or data assimilation: least squares or a filter. What does REBOUND offer toward it: variational equations and state transition matrices, and which integrators support them? What does this port offer and refuse? Its drop-in refuses variational particles. It does have ensembles, test particles (`active n`), per-system adaptive steps, recorded and replayed schedules (`--dt-out`, `--attempts-out`, `--dt-file`), tools/compare_run.py, and binary128/binary256 formats.

## Context worth knowing (verify before relying on it)

- cft-rebound is REBOUND's IAS15 on libcft, a multi-precision arithmetic library: binary64 bit-identical to REBOUND, and binary128 and binary256 besides. Read README.md, ROUND4.md and CLAUDE.md, in `C:\Users\logan\source\repos\cft-rebound` (main, read only).
- Round 4 has just built, for a GPU run, a ring of 10^6 test particles in 64-body waves about an oblate Saturn: J2 and J4 in src/ias15_zonal.inc, the generator tools/make_ring.py, and the replay and compare tools. A debris catalogue about an oblate Earth, with the Moon and Sun, has the same shape: massless particles in a field. Say how far that design carries over, and where it does not (drag, SRP, tesseral harmonics, frames and time scales).
- REBOUNDx (extra forces, including gravitational harmonics and radiation forces) is not pinned here. Do not download or install it; read about it on the web if you need to.
- **The alternatives a fair answer must weigh,** each a READ claim with its source. Do not install them:
  - heyoka (Taylor integrator; ESA's Advanced Concepts Team used it for conjunction screening of the catalogue);
  - Orekit (numerical, DSST and orbit determination);
  - THALASSA (regularised formulations for Earth orbits);
  - SGP4/SDP4;
  - the operational practice of the US Space Force's special-perturbations catalogue (Gauss-Jackson);
  - and anything better that you find.

## How to work

- **Reading:**
  - the pinned REBOUND source (`C:\Users\logan\source\repos\cft-rebound\third_party\rebound`, read only);
  - this repository's docs;
  - the web, for the literature and the tools' documentation (WebSearch and WebFetch). Cite each URL.
  No downloads, no installs, no package managers.
- **Small measurements are welcome, and must stay small.** A full test suite is running on this host, so keep your total under about 10 CPU-minutes.
  - **Instruments:**
    - the rebound 5.1.1 Python wheel already in `C:\Users\logan\AppData\Local\Programs\Miniconda3\python.exe`;
    - the built `C:\Users\logan\source\repos\cft-rebound-seam\build\ias15_cft.exe`, which has the zonal term. Run it with `export PATH="/c/msys64/mingw64/bin:$PATH"` first, and write every output into your own scratch folder, never inside that worktree.
  - **Suggestions:**
    - a LEO orbit (Earth point mass plus J2 as a Python additional force), run forward for a day and then backward, with the round-trip error and the time per run, for IAS15, WHFast, JANUS (what it supports), BS and LEAPFROG;
    - the same round trip at binary64, binary128 and binary256 with ias15_cft, if its command line takes a negative dt. Find out; if it does not, say so.
- **Label every claim:** MEASURED (you ran it, with its command), COMPUTED (arithmetic from stated inputs), READ (a source, cited), or BELIEVED (your judgement).
- **Rules:**
  - Write nothing in any repository, worktree, or `C:\Users\logan\source\repos\cft-fp256` (another session's). No GPU, no WSL, no card.
  - Never run bare `git stash`.
  - Make no speed claims beyond what you measured, labelled with the host's state.

## Output

1. **The study:** write `C:\Users\logan\AppData\Local\Temp\claude\443d8e8619fd4f31\fa64df2f-560a-4117-8348-b3ce1b89172a\scratchpad\studies\DEBRIS-A-rebound-for-debris.md`. Lead with a short answer and a recommendation, then the four questions in order, then the measurements with their commands, then sources. Aim for 4 to 8 pages. It is a decision document for Logan: say plainly where REBOUND is the wrong tool, if it is.
2. **Your final message:** the short answer, the recommendation, the three most load-bearing pieces of evidence with their labels, and anything you could not settle. Keep it under 600 words.
