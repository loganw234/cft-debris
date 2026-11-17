# verifier-G's report (second pass)

The agent's final message, which is its report, filed verbatim by cft-debris's lead at 2026-11-17 12:17:04 -0700 with `cft-debris-ledger\dispatch\file_report.py`. Model claude-haiku-5-5; final message timestamped 2026-11-17T19:16:03.922Z (UTC). Harness usage: <subagent_tokens>199975</subagent_tokens><tool_uses>57</tool_uses><duration_ms>1868054</duration_ms>. The text below is identical in the agent's own transcript and in the completion notice the lead received (as sent); a one-character change was shown to break that comparison. Body SHA-256 `09599180af146dd84af720bead2a8cda8fc6593d409848f45d793ba5d0e5c3af`.

---

verifier-G, second pass. The desktop CPU budget is spent: `cpu.tsv` totals about 1,510 CPU-seconds (about 25 minutes), against the 20-minute limit. The G2 run alone took 1,473 of those seconds. I stopped desktop runs there, so G3's desktop half is not run and is "not determined". The record is in `cft-debris-ledger\verifier-G.md`, appended beneath the earlier entries.

**Overlap breach.** At 11:59 two of my G2 runs overlapped, with five `m1g.exe` processes at once. I stopped both trees by PID (15288 and 30984), cleared `g2\out`, and reran G2 as a single process with at most 4 workers. The stopped runs are not in `cpu.tsv`, so the budget total above is an undercount by whatever they used.

**Run root.** Staged at `C:\Users\logan\source\repos\cft-debris-scratch\verifier-G\r1\`. `EXPECTED.sha256` hashes to `77d07f81…`, matching the hand-off.

**Verdicts.**

1. **Build from clean: confirmed.** Harness `build` on the desktop gives PASS for B1 to B6, and C1 fails as specified. The desktop `libcft.a` is `f0eec4f2…` (mingw); the box's was `14f95b22…` (gcc on Linux). The B5 vfmadd counts (21) match the box's.

2. **G2: confirmed for seven of eight kind-modes.** My runner is `g2\g2_own.py`, at most 4 processes at once, 40 steps, 64 objects. For native32, native64, native64-cr, cft32, cft64, cft128 and cft256, every partition (Q2 to Q5, plus my own four-worker partition with stride 4 and 3 lanes) equals Q1 bit for bit. The planted control (object 23's x moved one ulp) differs in exactly object 23, every kind. native32-cr was not run.

3. **G3 desktop half: not determined.** Not run, because the budget is spent. The box's outputs in `debris-g\box\out\g3_001\` remain uncompared.

4. **G4 and G5 from the logs: confirmed, with two notes.**
   - I recomputed the G4 table from the 59 runs in the three `runs.json` files, with my own script. Every figure in build report §3 reproduces.
   - G5's worst lag is -5.584 s, from `g_paced.001.log`'s per-worker maxima, and the medians match the report's -5.67 to -5.81 range.
   - Per-worker busy shares are not in the log (only mean 0.613, min 0.506, max 0.622): not determined.
   - The report says "1/0.613 = 1.63 matches 1.613". That is 1.1% apart, so "matches" overstates it.
   - `g_analyze.py`'s A1 checks compare the runs' figures against the log lines, and A7 is a control that changes one X by 0.1%; A5 is a threshold check on lags. I read the code but did not run the script.

5. **Load and clock accounting: confirmed by code reading, with one note.** The timed region in `m1g.c` starts at the release byte and ends at the last step; loading is outside it. The foreign-share computation clamps negative values to zero (`max(0, …)` in `g_harness.py`, line 504), which would hide a negative accounting residual. I found no case where this changes a verdict.

6. **Criteria before data: not confirmed for F9 (item 8); confirmed for the G5 rule.** The G5 fallback rule is in plan draft 3 (hash `4d683…`, verified), so cft256 is the choice by the plan's own text.

7. **Population: confirmed.** My independent recount from the four S0 CSVs gives 2,696 rows, 2,686 distinct keys, 0 excluded at 200 km (minimum perigee 270.1 km), and 10,744 replica lines. The per-object rule: a scan of the 54 new files found only five five-digit numbers that match an S0 catalogue number. Each is a numeric aggregate (a resident size, an `objsec` value, or a SHA fragment), not an object identifier.

8. **§4's F9 ratio: defect (criterion not in code, no pre-data record).** The criterion appears only as prose in `tests\g_f9data.py`'s header, and the script never evaluates it. The header was last written at 11:31:39; the log at 11:33:18. The ledger has no pre-data entry for the criterion, and the "earlier unlogged console run" has no time. So "fixed before any data was seen" is not supported. The numbers match the log (native64-cr 1.094 and 1.124; cft64 1.083 and 1.257; cft256 1.147 and 1.122). The conclusion "the states do cost more" overstates two kinds on a desktop two-repeat test. cft64 fails the stated criterion, and cft32 and cft128 were not measured in this test. The report's "consistent for cft32, cft64 and cft128" should be narrowed.

9. **Mean clock: confirmed against the code.** The sampler (`g_harness.py` lines 441 to 463 and 507 to 509) starts before the release and averages readings over time and CPUs, including idle readings. The report's account of this matches.

10. **Copy-back: confirmed against the manifest.** All 1,953 entries in `back2_manifest.box.txt` match the repository's 13 box logs and the ledger's 1,940 `out\` files, with no extra files. This verifies the copies against the manifest, not against the box.

**What I did not do:** G3's desktop half (item 3); per-worker busy shares for G5; a run of `g_analyze.py` with its checks forced to fail; native32-cr in G2; and a re-run of the F9 test to separate the criterion from the data.
