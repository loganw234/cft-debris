# Provenance of `studies/`

Studies this project received rather than wrote. Each entry says where a
study came from, how it was copied, and what it has and has not been
checked against.

## DEBRIS-A: REBOUND for long-term debris prediction (received 2026-11-12)

**What it is.** A study written for cft-rebound's lead on 2026-11-12. It
answers Logan's question of whether REBOUND, and which of its
integrators, suits long-term, high-density debris prediction. It is a
study only; nothing was built. **It has had no verifier.** Its
MEASURED / COMPUTED / READ / BELIEVED labels are its author's own, so it
is a starting point, not evidence.

| file | what |
|---|---|
| `DEBRIS-A-rebound-for-debris.md` | the study (418 lines) |
| `DEBRIS-A-brief.md` | the brief it answered |
| `DEBRIS-A-handoff-message.md` | the sender's saved draft of the handoff message |
| `debris-a/` | its 29 scripts, logs and records |

**Where it came from.** cft-rebound's lead session sent the handoff by
message on 2026-11-12 and asked for the files to be copied on arrival.
They were in that session's temporary scratch directory,
`%TEMP%\claude\443d8e8619fd4f31\fa64df2f-560a-4117-8348-b3ce1b89172a\scratchpad\studies\`,
which is purged after about a week.

**The copy.** Made with `cp -p` at 2026-11-12 11:35 -0700. The source
layout is kept, so the study's relative references (`studies/debris-a/`)
still resolve. 32 files; `debris-a/` holds 85,719 bytes (146 KiB on
disk, the figure the handoff quotes). Compared with the source straight
after the copy:
- the paths and SHA-256 of all 32 files are identical;
- every modification time is identical.

Each comparison was shown to fail on a planted difference. `SHA256SUMS`
holds the hashes; to re-check, run `sha256sum -c SHA256SUMS` from this
directory.

**How the record differs from what was received.**
`DEBRIS-A-handoff-message.md` is the sender's saved draft. The message as
received differs from it only in its Files list, which gave full paths
and "29 files, 146 KB" where the draft abbreviates.

**Before anything here is published.** The study, its brief and its
scripts carry absolute paths into the owner's home and temporary
directories, so they must pass the privacy scan first.

**Rerunning it.**
- The scripts need the rebound 5.1.1 wheel in the owner's Miniconda Python.
- `port_roundtrip.py` points at an `ias15_cft` built in a cft-rebound
  worktree that is removed when cft-rebound's round 4 closes. To rerun
  it, rebuild from cft-rebound's main.

cft-rebound and cft-fp256 are read-only to this project. Ask their leads:
- cft-rebound's lead for the study and the port;
- cft-fp256's lead for GPU slots and libcft.
