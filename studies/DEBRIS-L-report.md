# DEBRIS-L's report

The agent's final message, which is its report, filed verbatim by cft-debris's lead at 2026-11-23 13:51:57 -0700 with `cft-debris-ledger\dispatch\file_report.py`. Model claude-sonnet-5-5; final message timestamped 2026-11-23T20:51:32.872Z (UTC). Harness usage: <subagent_tokens>233559</subagent_tokens><tool_uses>67</tool_uses><duration_ms>873582</duration_ms>. The text below is identical in the agent's own transcript and in the completion notice the lead received (as sent); a one-character change was shown to break that comparison. Body SHA-256 `d77351b0da1de65e16719f1bc09c54585b9359c96c5546dc3f7c5c47e1d98421`.

**This repository's copy** differs from the text as filed only where the text names a folder on the desktop by its full path: the folder that holds the repositories is written `<root>`, in 3 places (the lead, at the merge, 2026-11-23). The text as filed, SHA-256 `d89f5d5c67a8167d3d405ac783ab173d38f13395d6d9c9863433a3c08a833e29`, is in `cft-debris-ledger\filed\DEBRIS-L-report.md`.

---

DEBRIS-L is finished. The gates V0 to V4 all pass, including their controls, and nothing is committed. CPU by cycles / 2.5e9 was about 190 s of the 20 CPU-minutes. No processes of mine are still running.

**What I made**
- **M1 build:** `tests\k_build.py` built M1 from the 0aa997a3 archive in my scratch. Every build check passed.
- **Code:** all in `tests\`:
  - `l_png.py`, a PNG writer and reader with CRC checks
  - `l_font.py`, a 5×7 bitmap font
  - `l_draw.py`, projection and drawing
  - `l_lib.py`, the log and CPU pieces
  - `l_prop.py`, the `m1f prop` driver, reusing `m1f_prop`
  - `l_media.py`, the frames, video and live display
  - `l_panel.py`, the charts and their source table
  - `l_gates.py`, the gates and the manifest
- **Propagation:** 2,688 objects × 181 frames at Δ = 60 s. The state at k = 0 equals the seed bit for bit.
- **Media** in the ledger's `debris-l\`, each with a `.sidecar.json`:
  - `video.mp4`: 181 frames, h264, 1280×720, 30 a second.
  - `live_display.html`: 3.9 MB, data inline, no network pattern. I checked it by running its script in node with a stubbed canvas. The rectangles it drew at frame 0 matched my count of objects not hidden by the Earth, top and edge-on.
  - Four screenshots in `screenshots\`: both views at k = 0 and k = 180, top view at k = 0 and edge-on at k = 0.
- **Results panel** in `studies\debris-l\panel\`: `chart_g.png`, `chart_i.png`, `chart_h.png`, `chart_k.png`, and `panel_table.tsv` with 29 numbers, each traced to a source file and line. `MANIFEST.sha256` covers `studies\debris-l\` (36 lines, all verified).
- **Logs:** aggregates in `studies\debris-l\logs\`, per-object detail in the ledger's `debris-l\logs\`. Every script version that wrote a log is kept in `studies\debris-l\scripts\`.
- **My ledger file** `DEBRIS-L.md` has the summary entry. The test escalation went out and you replied "received".

**Gates** (second runs, 002, except V4, which has one final run)

| gate | checks | what it showed |
|---|---|---|
| V0 | 5 | The PNG round-trips and ffmpeg reads it. A flipped byte in the image data or in IHDR raises a CRC error. |
| V1 | 4 | 20 objects drawn alone light exactly the pixels the seed state projects to, in their group's colour. After a swap, a pair of objects lands on each other's pixels. |
| V2 | 8 | The k = 0 state, frame times and hashes check out. For 20 objects × 5 frames, the recorded pixel and the display's decoded position match `prop`'s output. One object with x moved one ulp changes at every frame k ≥ 1, and four others are bit-for-bit unchanged. |
| V3 | 12 | All 29 numbers equal their source lines. A planted wrong number is caught. Every bar sits on its exact row, and a doubled value is caught on each chart. |
| V4 | 31 | The scan is clean: 22 patterns, each hitting its plant, and no catalogue number. |

The first V4 trial failed on the scanner's own plant strings, because `l_gates.py` is inside the scan's scope. I rewrote the patterns in pieces and moved that trial log to `debris-l\superseded\` with its script. Each gate also has a first run (001) made before the last media rerun, kept beside its second.

**What I did not do**
- I did not play the video or open the live display in a real browser. The built-in browser refused the `file://` page.
- The node stub test of the display is not in any gate or log.
- The video's sidecar names frame 0's hash, not all 181 frames'.
- The manifest check has no numbered log, only stdout.
- Frames show about 1,780 objects in the top view and 2,170 edge-on. The rest are behind the Earth's disc or, for a few, outside ±8,000 km. The largest coordinate is 9,325 km.
- I did not run V1 with the video's own renderer layout for the single-view screenshots.
- No timing is reported as a measurement. The wall times in the logs are incidental.

**What the brief got wrong**
- It pointed to `tests\i_lib.py` for the CPU count. I used `k_lib.CpuAccount`, which is the cycles-and-`GetProcessTimes` counter `k_build` already uses.
- `m1f prop` took about 50 s for all 181 frames, so the "factor of 1 to 5" slower than DEBRIS-G's rate was too cautious.
- Its V4 scope puts the scanner inside its own scan. A scanner kept in `tests\l_*.py` has to write its plants in pieces.
- It does not say which frame the screenshots show. I chose k = 0 and k = 180.

Files are in `<root>\cft-debris-ledger\debris-l\`, `<root>\cft-debris\studies\debris-l\` and `<root>\cft-debris\tests\l_*.py`.
