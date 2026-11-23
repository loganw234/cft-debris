# verifier-L's report

The agent's final message, which is its report, filed verbatim by cft-debris's lead at 2026-11-23 14:00:58 -0700 with `cft-debris-ledger\dispatch\file_report.py`. Model claude-haiku-5-5; final message timestamped 2026-11-23T21:00:31.162Z (UTC). Harness usage: <subagent_tokens>135721</subagent_tokens><tool_uses>45</tool_uses><duration_ms>196206</duration_ms>. The text below is identical in the agent's own transcript and in the completion notice the lead received (after unescaping the notice's HTML entities); a one-character change was shown to break that comparison. Body SHA-256 `a42391f085e86cc4639a93b4996d26adc8f2ac171ef6fddc5ad8cffb3ed322c6`.

**This repository's copy** differs from the text as filed only where the text names a folder on the desktop by its full path: the folder that holds the repositories is written `<root>`, in 2 places (the lead, at the merge, 2026-11-23). The text as filed, SHA-256 `8bfce395be86e12e1a7e79194740993df778f805964f0e7bcc11c90d215433ed`, is in `cft-debris-ledger\filed\DEBRIS-L-verifier-L-report.md`.

---

**verifier-L report, DEBRIS-L: no attack succeeded.** Nothing in cft-debris was changed and nothing was committed. The one defect I found is cosmetic.

**Test escalation:** sent to the lead, who replied "received".

**1. V1, five objects (holds).** I wrote the indices down before any result (ledger, 14:03): 2427 (group 0), 1596 (group 1), 2051 (group 2), 2679 (group 3), 2347 (group 0). Log: `ledger\debris-l\verifier-l\v1_check.1ca78d179e35.log`, script `scratch\verifier-L\v1_check.py`.
- Parsing `seed1.txt` with `float.fromhex` and comparing against `states.npy` frame 0: all five equal bit for bit.
- I projected each object with my own code, using the layout constants in `l_draw.py`. Then I drew each object alone with `l_draw.render` and read its pixel. Each non-hidden point matches, and each centre pixel is its group colour. The two objects my projection marks hidden (1596 edge, 2347 top) are not drawn.

**2. V3, every number (holds).** Log: `ledger\debris-l\verifier-l\v3_table.29cf9edc169f.log`. All 29 rows of `panel_table.tsv` equal their source cell at the cited line, after the part before ` / ` and the label before `: ` are removed. I looked at the four charts. Labels, bar order and heights agree with the table on the axis each chart states (log for g and h, linear for i and k).

**3. Pictures (holds, with one cosmetic defect).**
- Video first frame (extracted with ffmpeg `-threads 2`): frame 000, 2026-11-18 22:50, counts 1991/582/109/6, both views. Matches its caption.
- Video last frame: frame 180, 2026-11-19 01:50, +03:00. Matches.
- Four screenshots: all show the captioned frame, group and view. Defect: in `shot_top_k000` and `shot_edge_k000` the view label is drawn over the legend row, so part of the legend is hard to read.
- Recount at frame 0 with my code: 1778 visible in the top view and 2167 edge-on. The report says "about 1,780" and "2,170", which agrees.
- `live_display.html` (3.9 MB): zero matches for any URL, `fetch`, `XMLHttpRequest`, `WebSocket`, `import`, `src=`, `href=` or `sendBeacon`. Log: `ledger\debris-l\verifier-l\html_manifest.a769e4f9443c.log`.

**4. Repository scan (holds).** Log: `verifier-l\scan.4da62ccfcae4.log`, script `scratch\verifier-L\scan.py`. I scanned 45 files in `tests\l_*.py` and `studies\debris-l\`. The positive control caught every pattern kind. There were 183 hits, all benign: imports, CSS and JS numbers, ffmpeg output, chart ticks, and the check code that names the patterns. There are no user paths, URLs, personal addresses or catalogue numbers. The only PNGs outside `panel\` are none. The manifest is clean: 36 entries, 36 files, 0 problems (`html_manifest` log).

**5. Controls (all can fail as written).**
- V0.3 (`l_gates.py` ~184–202): one flipped byte in IDAT, and one in IHDR, must each raise a CRC error.
- V1.3 (~235–266): after a swap, each colour must light the other object's pixels.
- V2.3 (~326–341): a one-ulp change in one object's x.
- V3.1 (~428–431): one planted wrong number must give exactly one mismatch.
- V3.2 (~437–447): a doubled smallest bar must be found on its chart.
- V4.3 (~516–518): each pattern must match its plant.
- V4.4 (~522–527): a planted hash is exempt, and a planted catalogue number is found.

Two weak spots:
- V2.3 passes if A changes in one frame (`changedA >= 1`), so it is weaker than it reads.
- The V4 catalogue check only knows numbers in the seed and the downloads snapshots. A catalogue number outside those sets would not be caught.

**Not checked:** the largest coordinate of 9,325 km over all 181 frames; I checked only frames 0 and 180 (max 9,288 km at 180). Video frame hashes beyond frame 0 are not checked, because the sidecar hashes are of PNG frames and my decode is lossy. The chart text as glyphs is not checked. I did not play the video in a browser or run `m1f`. No background processes are running.

Ledger: `<root>\cft-debris-ledger\verifier-L.md`, with logs in `debris-l\verifier-l\`. Scratch: `<root>\cft-debris-scratch\verifier-L\`.
