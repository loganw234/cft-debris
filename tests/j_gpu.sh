#!/bin/bash
# j_gpu.sh - cft-debris DEBRIS-J: the lead's wrapper for one GPU step in WSL's cft-gpu. It checks the tools, copies the
# staged run folder into the run folder (once: a run folder's in/ is never refreshed; a new staging takes a new run
# folder), and runs tests/j_harness.py's gpu-<mode> there, which verifies every staged file's SHA-256 before anything
# runs and takes the lock around its GPU work. Mode "back" copies the run folder's logs/ and out/ to a folder the lead
# names (on /mnt/c), with a SHA-256 list of every file copied; it touches no GPU and takes no lock.
# cft-debris, MIT licence (see LICENSE at the repository root). Written by DEBRIS-J, 2026-11-23.
#
# usage (the lead, from Windows):
#   MSYS_NO_PATHCONV=1 wsl -d cft-gpu -- bash <staged in/ on /mnt/c>/tests/j_gpu.sh <j0|j0c|j1|j2|j3> \
#       <staged in/ folder on /mnt/c> <run folder in cft-gpu> <lock file> [j_harness.py options]
#   MSYS_NO_PATHCONV=1 wsl -d cft-gpu -- bash <staged in/ on /mnt/c>/tests/j_gpu.sh back \
#       <staged in/ folder on /mnt/c> <run folder in cft-gpu> <destination folder on /mnt/c, new>
# Every path, the lock and the toolchain are the lead's parameters; nothing here names another session's path. In an
# option's value a '+' stands for a space (--expect-device NVIDIA+GeForce+RTX+5060+Ti), so that no quoting has to
# survive the trip through wsl.exe.
set -euo pipefail
if [ "$#" -lt 4 ]; then
  echo "usage: j_gpu.sh <j0|j0c|j1|j2|j3|back> <staged in/ folder> <run folder> <lock file | destination> [options]"; exit 64
fi
MODE="$1"; STAGE="$2"; ROOT="$3"; FOURTH="$4"; shift 4
case "$MODE" in j0|j0c|j1|j2|j3|back) ;; *) echo "j_gpu.sh: unknown mode $MODE"; exit 64 ;; esac
echo "j_gpu.sh $MODE: started $(date '+%Y-%m-%d %H:%M:%S %z')"
if [ "$MODE" = back ]; then
  DEST="$FOURTH"
  [ -d "$ROOT/logs" ] && [ -d "$ROOT/out" ] || { echo "j_gpu.sh back: no logs/ and out/ in the run folder"; exit 1; }
  [ ! -e "$DEST" ] || { echo "j_gpu.sh back: the destination exists: refused (a copy goes to a new folder)"; exit 1; }
  mkdir -p "$DEST"
  cp -r "$ROOT/logs" "$ROOT/out" "$DEST/"
  # of work/, the derived runs files only (small; the replay of a mark needs its run's bank); the derived INIT files
  # are not copied: each one's SHA-256 is in the logs, and each is remade from the staged base
  mkdir -p "$DEST/work"
  find "$ROOT/work" -maxdepth 1 -type f -name '*runs*.bin' -exec cp {} "$DEST/work/" \;
  (cd "$ROOT" && { find logs out -type f; find work -maxdepth 1 -type f -name '*runs*.bin'; } | LC_ALL=C sort | xargs sha256sum) \
    > "$DEST/COPIED.sha256"
  (cd "$DEST" && sha256sum -c --quiet COPIED.sha256) && echo "j_gpu.sh back: $(wc -l < "$DEST/COPIED.sha256") files copied and verified"
  echo "j_gpu.sh back: ended $(date '+%Y-%m-%d %H:%M:%S %z')"
  exit 0
fi
LOCK="$FOURTH"
for t in python3 flock nvidia-smi make tar sha256sum; do
  p=$(command -v "$t") || { echo "j_gpu.sh: MISSING $t"; exit 1; }
  echo "tool $t: $p"
done
python3 --version
[ -f "$LOCK" ] || { echo "j_gpu.sh: no lock file at the path given: refused (this script never creates it)"; exit 1; }
if [ ! -d "$ROOT/in" ]; then
  [ -f "$STAGE/EXPECTED.sha256" ] || { echo "j_gpu.sh: the staged folder has no EXPECTED.sha256"; exit 1; }
  mkdir -p "$ROOT"
  cp -r "$STAGE" "$ROOT/in"
  echo "j_gpu.sh: copied the staged folder into <run>/in ($(find "$ROOT/in" -type f | wc -l) files)"
else
  echo "j_gpu.sh: <run>/in exists: not copied again"
fi
rc=0
python3 -I -B "$ROOT/in/tests/j_harness.py" "gpu-$MODE" --root "$ROOT" --lock "$LOCK" "$@" || rc=$?
echo "j_gpu.sh $MODE: ended $(date '+%Y-%m-%d %H:%M:%S %z'), exit $rc"
exit $rc
