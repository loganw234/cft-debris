# cft-debris

Space-debris tracking and simulation, held to the methods of [HonestFramework](https://github.com/loganw234/HonestFramework) and [ParcelRound](https://github.com/loganw234/ParcelRound). It holds the rounds' studies and, since round DEBRIS-E, the first build: M1, a CPU reference propagator, in `src/`, with its gates in `tests/`.

## The rounds

| round | question | status, 2026-11-13 | files in `studies/` |
|---|---|---|---|
| DEBRIS-A | Does REBOUND, and which of its integrators, suit long-term debris prediction? Received from cft-rebound's lead. | verified by verifier-A; its numbers reproduce, and the report lists its errata | `DEBRIS-A-rebound-for-debris.md`, `debris-a/`, `DEBRIS-A-verifier-A-report.md`, `PROVENANCE.md` |
| DEBRIS-B | What would a custom debris model stand on, cost and buy? It includes whether binary256 arithmetic buys anything. | verified by verifier-B; eight passages narrowed at the merge, each marked | `DEBRIS-B-plan.md`, `DEBRIS-B-custom-model.md`, `debris-b/`, `DEBRIS-B-report.md`, `DEBRIS-B-verifier-B-report.md`, `DEBRIS-B-round-record.md` |
| DEBRIS-C | The measurements that would decide between building, adopting existing tools, and a hybrid | checked by verifier-C; one defect, an attribution, and eight passages narrowed at the merge, each marked | `DEBRIS-C-plan.md`, `DEBRIS-C-measurements.md`, `debris-c/`, `DEBRIS-C-report.md`, `DEBRIS-C-verifier-C-report.md`, `DEBRIS-C-round-record.md` |
| DEBRIS-D | What a real-time, wide-precision propagator on a consumer GPU would cost, written in cft-fp256's language, and what it needs from cft-fp256 | checked by verifier-D; one defect, a marking bound that reached past its evidence; six narrowings and one addition at the merge, each marked | `DEBRIS-D-plan.md`, `DEBRIS-D-architecture.md`, `debris-d/`, `DEBRIS-D-report.md`, `DEBRIS-D-verifier-D-report.md`, `DEBRIS-D-round-record.md` |
| DEBRIS-E | Build M1 in six number kinds, native and libcft at binary32 and binary64 and libcft at binary128 and binary256, from one force-model source. Hold it to gates: native against libcft bit for bit, and against Lasser et al., JPL, Orekit and REBOUND | built, and checked by verifier-E; every gate passes as finally specified, and every re-run passed; five narrowings and one addition at the merge, each marked | `DEBRIS-E-plan.md`, `DEBRIS-E-build.md`, `debris-e/`, `DEBRIS-E-report.md`, `DEBRIS-E-verifier-E-report.md`, `DEBRIS-E-round-record.md`; the code is in `src/` and `tests/` |

Every claim in a study carries a label: MEASURED, COMPUTED, READ, ESTIMATE or BELIEVED.

## Building M1

M1 needs an x86-64 CPU with FMA3, gcc, and libcft from cft-fp256 at commit 0aa997a3, built outside this repository. It was built and tested with mingw64's gcc 16.1.0 on Windows. `studies/DEBRIS-E-build.md`, section 3, gives every command and tool version.
- **The build,** with its object checks: `bash tests/build.sh <cft-fp256>/host <build dir>`.
- **The gates:** `python -I -B tests/<gate>.py`, with the build directory in `M1_BUILD`. They also need the inputs this repository does not redistribute (see below). `tests/gatelib.py` sets the downloads folder and the Python path to this machine's.

## Checking the records

Each study's records come with SHA-256 manifests:
- DEBRIS-A: run `sha256sum -c SHA256SUMS` from `studies/`;
- DEBRIS-B to DEBRIS-E: run `sha256sum -c MANIFEST.sha256` from `studies/debris-b/`, `studies/debris-c/`, `studies/debris-d/` and `studies/debris-e/`.

`.gitattributes` turns off line-ending conversion, so every file is checked out with its exact bytes. Many records end their lines with CRLF, and the checksums hold on any platform.

## Licence

MIT (`LICENSE`). It covers this repository's own work: the studies, their scripts and their records, and M1's code in `src/` and `tests/`. The software and data the studies and the build used are not included, and they keep their own licences:
- **Called through their interfaces, never copied in:** REBOUND (GPL-3.0), imported as an installed package; Orekit and Hipparchus (Apache-2.0); and cft-fp256's libcft and its compiler, cftc (Apache-2.0), built from a pinned commit outside this repository. M1 links libcft at build time; neither its sources nor its build are here. The systems in `studies/debris-d/systems/` are written in cft-fp256's language and are this repository's own. The images cftc compiles from them carry cft-fp256's routines, so they are not included; the records give each image's SHA-256 and the command that rebuilds it.
- **Named with their sources, never redistributed:** JPL's DE421, EIGEN-6C4 and Lasser et al.'s benchmark data.

## What is not here

- **Machine-specific paths:** the paths inside the records are those of the machine where the runs were made, and so are the defaults in `tests/gatelib.py`.
- **Executables:** M1's builds, `m1x.dll` and libcft's build stay outside the repository. Every gate log names the SHA-256 of the binaries it ran.
- **Third-party inputs** are not redistributed: Orekit and Hipparchus, JPL's DE421, the files of Lasser et al.'s 2020 benchmark, cft-fp256's sources, and the gravity-field sources DEBRIS-D generated from EIGEN-6C4. Each study names where they came from, and `studies/debris-d/q2/gen_field.py` regenerates the field sources byte for byte.
- **The project's ledger** is not part of this repository. It holds the hashes recorded at download, and the lead's rulings during each round.
