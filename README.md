# cft-debris

Space-debris tracking and simulation, held to the methods of [HonestFramework](https://github.com/loganw234/HonestFramework) and [ParcelRound](https://github.com/loganw234/ParcelRound). It holds the rounds' studies and, since round DEBRIS-E, the first build: M1, a CPU reference propagator, in `src/`, with its gates in `tests/`. Round DEBRIS-F put M1 in the real Earth frame and ran it on CelesTrak's public orbit data. Round DEBRIS-G measured how many objects it carries in real time on the 36 threads of a second machine, amd-arc-box.

## The rounds

| round | question | status, 2026-11-17 | files in `studies/` |
|---|---|---|---|
| DEBRIS-A | Does REBOUND, and which of its integrators, suit long-term debris prediction? Received from cft-rebound's lead. | verified by verifier-A; its numbers reproduce, and the report lists its errata | `DEBRIS-A-rebound-for-debris.md`, `debris-a/`, `DEBRIS-A-verifier-A-report.md`, `PROVENANCE.md` |
| DEBRIS-B | What would a custom debris model stand on, cost and buy? It includes whether binary256 arithmetic buys anything. | verified by verifier-B; eight passages narrowed at the merge, each marked | `DEBRIS-B-plan.md`, `DEBRIS-B-custom-model.md`, `debris-b/`, `DEBRIS-B-report.md`, `DEBRIS-B-verifier-B-report.md`, `DEBRIS-B-round-record.md` |
| DEBRIS-C | The measurements that would decide between building, adopting existing tools, and a hybrid | checked by verifier-C; one defect, an attribution, and eight passages narrowed at the merge, each marked | `DEBRIS-C-plan.md`, `DEBRIS-C-measurements.md`, `debris-c/`, `DEBRIS-C-report.md`, `DEBRIS-C-verifier-C-report.md`, `DEBRIS-C-round-record.md` |
| DEBRIS-D | What a real-time, wide-precision propagator on a consumer GPU would cost, written in cft-fp256's language, and what it needs from cft-fp256 | checked by verifier-D; one defect, a marking bound that reached past its evidence; six narrowings and one addition at the merge, each marked | `DEBRIS-D-plan.md`, `DEBRIS-D-architecture.md`, `debris-d/`, `DEBRIS-D-report.md`, `DEBRIS-D-verifier-D-report.md`, `DEBRIS-D-round-record.md` |
| DEBRIS-E | Build M1 in six number kinds, native and libcft at binary32 and binary64 and libcft at binary128 and binary256, from one force-model source. Hold it to gates: native against libcft bit for bit, and against Lasser et al., JPL, Orekit and REBOUND | built, and checked by verifier-E; every gate passes as finally specified, and every re-run passed; five narrowings and one addition at the merge, each marked | `DEBRIS-E-plan.md`, `DEBRIS-E-build.md`, `debris-e/`, `DEBRIS-E-report.md`, `DEBRIS-E-verifier-E-report.md`, `DEBRIS-E-round-record.md`; the code is in `src/` and `tests/` |
| DEBRIS-F | Put M1 on real data: the IERS 2010 Earth frame from a binary256 node table, CelesTrak's GP data decoded by Orekit's SGP4, a native64 fit, and a first hindcast against later element sets | built, and checked by verifier-F; every gate passes, with no send-back; eleven narrowings and three additions at the merge, each marked, among them that the samples count docked vehicles, which share their station's element set, as separate objects; F9 re-run quiet on amd-arc-box, another machine, so the desktop's own clean timing is still to come | `DEBRIS-F-plan.md`, `DEBRIS-F-build.md`, `debris-f/`, `DEBRIS-F-report.md`, `DEBRIS-F-verifier-F-report.md`, `DEBRIS-F-round-record.md`; the code is in `src/` and `tests/` |
| DEBRIS-G | How many objects M1 carries in real time on amd-arc-box's 36 threads, at each number kind, and whether its results stay bit-identical across batch partitions and across machines | built, and checked by verifier-G; every gate passes, with no send-back; two narrowings and four additions at the merge, each marked. Real-time capacity at 36 threads runs from about 18.5 million objects at native32 to 4,332 at cft256: throughput, extrapolated beyond the 2,304 objects the runs carried. A 20-minute run held all 2,686 of S0's distinct element sets in real time at cft256 | `DEBRIS-G-plan.md`, `DEBRIS-G-build.md`, `debris-g/`, `DEBRIS-G-report.md`, `DEBRIS-G-verifier-G-report.md`, `DEBRIS-G-round-record.md`; the code is in `tests/` |

Every claim in a study carries a label: MEASURED, COMPUTED, READ, ESTIMATE or BELIEVED.

## Building M1

M1 needs an x86-64 CPU with FMA3, gcc, and libcft from cft-fp256 at commit 0aa997a3, built outside this repository. It was built and tested with mingw64's gcc 16.1.0 on Windows. `studies/DEBRIS-E-build.md` and `studies/DEBRIS-F-build.md`, each in its section 3, give every command and tool version.
- **The build,** with its object checks: `bash tests/build.sh <cft-fp256>/host <build dir>` for DEBRIS-E's gates, and `bash tests/build_f.sh <cft-fp256>/host <build dir>` for DEBRIS-F's, which adds the Earth frame and the fit.
- **The gates:** `python -I -B tests/<gate>.py`, with the build directory in `M1_BUILD` (DEBRIS-E) or `M1F_BUILD` (DEBRIS-F). They also need the inputs this repository does not redistribute (see below). `tests/gatelib.py` and `tests/f_lib.py` set the downloads, scratch and Python paths to this machine's.
- **On Linux:** F9's timing was also built and run on Ubuntu 24.04 with gcc 13.3.0, by `tests/f9_box.py`. It gives `tests/m1f.c`'s two Windows timers Linux clocks through a stand-in header, `tests/f9_box_windows.h`, and leaves every source unchanged.
- **At scale (DEBRIS-G):** `tests/g_stage.py` lays out a run folder, and `tests/g_harness.py` builds M1 with the batch driver `tests/m1g.c` and runs the gates from it, on Windows or Linux. `studies/DEBRIS-G-build.md`, section 1, gives the commands.

## Checking the records

Each study's records come with SHA-256 manifests:
- DEBRIS-A: run `sha256sum -c SHA256SUMS` from `studies/`;
- DEBRIS-B to DEBRIS-G: run `sha256sum -c MANIFEST.sha256` from `studies/debris-b/`, `studies/debris-c/`, `studies/debris-d/`, `studies/debris-e/`, `studies/debris-f/` and `studies/debris-g/`.

`.gitattributes` turns off line-ending conversion, so every file is checked out with its exact bytes. Many records end their lines with CRLF, and the checksums hold on any platform.

## Licence

MIT (`LICENSE`). It covers this repository's own work: the studies, their scripts and their records, and M1's code in `src/` and `tests/`. The software and data the studies and the build used are not included, and they keep their own licences:
- **Called through their interfaces, never copied in:** REBOUND (GPL-3.0), imported as an installed package; Orekit and Hipparchus (Apache-2.0); and cft-fp256's libcft and its compiler, cftc (Apache-2.0), built from a pinned commit outside this repository. M1 links libcft at build time; neither its sources nor its build are here. The systems in `studies/debris-d/systems/` are written in cft-fp256's language and are this repository's own. The images cftc compiles from them carry cft-fp256's routines, so they are not included; the records give each image's SHA-256 and the command that rebuilds it.
- **Named with their sources, never redistributed:** JPL's DE421, EIGEN-6C4, Lasser et al.'s benchmark data, the IERS Conventions' tables and the IERS Earth orientation data, USNO's table of TAI − UTC, and CelesTrak's orbit data and space weather.

## What is not here

- **Machine-specific paths:** the paths inside the records are those of the machine where the runs were made, and so are the defaults in `tests/gatelib.py`.
- **Executables:** M1's builds, `m1x.dll` and libcft's build stay outside the repository. Every gate log names the SHA-256 of the binaries it ran.
- **Third-party inputs** are not redistributed: Orekit and Hipparchus, JPL's DE421, the files of Lasser et al.'s 2020 benchmark, cft-fp256's sources, the gravity-field sources DEBRIS-D generated from EIGEN-6C4, the IERS and USNO tables, and CelesTrak's GP data and space-weather files. Each study names where they came from, and `studies/debris-d/q2/gen_field.py` regenerates the field sources byte for byte.
- **Per-object tables** derived from CelesTrak's GP data, such as DEBRIS-F's fits and hindcast pairs, and DEBRIS-G's population and final states, stay in the project's ledger. The repository holds their aggregates, and one control's figures for one public object, the ISS (`studies/DEBRIS-F-build.md`, section 9).
- **The project's ledger** is not part of this repository. It holds the hashes recorded at download, and the lead's rulings during each round.
