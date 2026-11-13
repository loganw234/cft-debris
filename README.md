# cft-debris

Space-debris tracking and simulation, held to the methods of [HonestFramework](https://github.com/loganw234/HonestFramework) and [ParcelRound](https://github.com/loganw234/ParcelRound). So far the repository holds studies only. Nothing has been built.

## The studies

| study | question | status, 2026-11-12 | files in `studies/` |
|---|---|---|---|
| DEBRIS-A | Does REBOUND, and which of its integrators, suit long-term debris prediction? Received from cft-rebound's lead. | verified by verifier-A; its numbers reproduce, and the report lists its errata | `DEBRIS-A-rebound-for-debris.md`, `debris-a/`, `DEBRIS-A-verifier-A-report.md`, `PROVENANCE.md` |
| DEBRIS-B | What would a custom debris model stand on, cost and buy? It includes whether binary256 arithmetic buys anything. | verified by verifier-B; eight passages narrowed at the merge, each marked | `DEBRIS-B-plan.md`, `DEBRIS-B-custom-model.md`, `debris-b/`, `DEBRIS-B-report.md`, `DEBRIS-B-verifier-B-report.md`, `DEBRIS-B-round-record.md` |
| DEBRIS-C | The measurements that would decide between building, adopting existing tools, and a hybrid | checked by verifier-C; one defect, an attribution, and eight passages narrowed at the merge, each marked | `DEBRIS-C-plan.md`, `DEBRIS-C-measurements.md`, `debris-c/`, `DEBRIS-C-report.md`, `DEBRIS-C-verifier-C-report.md`, `DEBRIS-C-round-record.md` |

Every claim in a study carries one of four labels: MEASURED, COMPUTED, READ or BELIEVED.

## Checking the records

Each study's records come with SHA-256 manifests:
- DEBRIS-A: run `sha256sum -c SHA256SUMS` from `studies/`;
- DEBRIS-B and DEBRIS-C: run `sha256sum -c MANIFEST.sha256` from `studies/debris-b/` and `studies/debris-c/`.

`.gitattributes` turns off line-ending conversion, so every file is checked out with its exact bytes. Many records end their lines with CRLF, and the checksums hold on any platform.

## Licence

MIT (`LICENSE`). It covers this repository's own work: the studies, their scripts and their records. The software and data the studies used are not included, and they keep their own licences:
- **Called through their interfaces, never copied in:** REBOUND (GPL-3.0), and Orekit and Hipparchus (Apache-2.0).
- **Named with their sources, never redistributed:** JPL's DE421, EIGEN-6C4 and Lasser et al.'s benchmark data.

## What is not here

- **Machine-specific paths:** the paths inside the records are those of the machine where the runs were made.
- **Third-party inputs** are not redistributed: Orekit and Hipparchus, JPL's DE421, and the files of Lasser et al.'s 2020 benchmark. Each study names where they came from.
- **The project's ledger** is not part of this repository. It holds the hashes recorded at download, and the lead's rulings during each round.
