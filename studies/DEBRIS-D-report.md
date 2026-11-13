# DEBRIS-D's report

The agent's final message, which is its report, filed verbatim by cft-debris's lead at 2026-11-12 21:53 -0700 with `cft-debris-ledger\dispatch\file_report.py`. Model claude-opus-5-5; final message timestamped 2026-11-13T04:51:33.716Z (UTC). Harness usage: <subagent_tokens>733636</subagent_tokens><tool_uses>263</tool_uses><duration_ms>4228371</duration_ms>. The text below is identical in the agent's own transcript and in the completion notice the lead received (as sent); a one-character change was shown to break that comparison. Body SHA-256 `7edbec21fda6e67e8ef9d2e9a0157f63802849a347304ae9657d455d8b440b22`.

---

DEBRIS-D is finished. Q1 to Q8 are answered in `C:\Users\logan\source\repos\cft-debris\studies\DEBRIS-D-architecture.md`, with scripts, logs and records in `C:\Users\logan\source\repos\cft-debris\studies\debris-d\` (73 files, `MANIFEST.sha256` all OK). The earlier records still check: 32 OK, 29 files, 54 OK, 136 OK, no `__pycache__`. CPU used: 16.1 CPU-minutes by cycles, plus about 0.3 outside my wrapper (ESTIMATE). Nothing of mine is running.

**Short answer**
- **v1 runs a LEO propagator's core today, bit for bit** (MEASURED). Two systems ran at fp64, fp128 and fp256 on the software executor: J2 alone, and J2 with C22/S22, drag and the Earth's rotation through sin/cos of ωt.
  - (a) Both equal `lang.run` bit for bit, states and lane flags.
  - (b) Both are within 1.9% of the tolerance I stated before the run, against 120-digit mpmath.
  - (c) The source with μ planted one ulp off fails, as it must.
- **On a GPU, real time is not the constraint; capacity is.** Degree 7 is the largest gravity field `hip:N` can carry today. At an estimated degree 20 with rk4 at 15 s, one consumer card runs 0.14 to 1.2 million objects in real time (COMPUTED). That figure carries an ESTIMATE factor of up to 3 below it.

**Q1 to Q8**
- **Q1, workload** (MEASURED, counting builds of our own kernels): the degree-20 field is 8,160 FMA-class operations, 3 divides and 1 root. Sun, Moon, frame, drag and radiation pressure add 799. Both controls passed: degree 2 equals my hand count (104 mul, 37 add, 3 div, 1 sqrt), and a planted term adds exactly its own operations. In compiled images the routines are 88% of a J2-and-drag step's instructions.
- **Q2, the route:**
  - Refusals (MEASURED): `pow` (`transcendental`), an undeclared `t` (`time-dependence`), and drag under Störmer-Verlet (`verlet-not-separable`).
  - Capacities (MEASURED): degree 8 is refused `scratch-capacity` (273 slots against 256) at fp64/fp128 and `bank-capacity` (516 against 512) at fp256. Degree 20 is refused `bank-capacity` (1,762 params).
  - Every image's features fall inside `hip:N`'s 0x75f1f; that they would load there is BELIEVED, since nothing ran on a GPU.
- **Q3, prices** (MEASURED in B0024, every result bit-exact against mpmath): FMA 195/235/313 ns, divide 3.6/5.6/9.2 µs, host exp 0.14/0.33/1.12 ms, host pow 0.34/0.93/3.4 ms. The sequencer runs our images at 50 to 125 ns a lane-instruction. Marks: 0 in 196,608 lane-evaluations per format.
- **Q4, the integrator** (MEASURED, real EIGEN-6C4 degree 20 with drag, one object-day):

  | method | error a day | evaluations |
  |---|---|---|
  | rk4, 60 s | 2,310 m | 5,760 |
  | rk4, 30 s | 83 m | 11,520 |
  | rk4, 15 s | 3.3 m | 23,040 |
  | IAS15, ε 1e-9 | 4.0e-7 m | 16,449 |

  At fp64, rk4 cannot reach IAS15's accuracy: its own rounding error (1e-6 to 1e-5 m a day) is larger.
- **Q5, the ladder** (COMPUTED): from GPU-A's rates times our instruction counts; a full table per card, format and tier is in the study.
- **Q6, density** (READ and ESTIMATE): JB2008 makes about 225 `pow` calls a call, which v1 refuses. NRLMSISE-00 could not be counted, because GitHub's HTML views stop at line 1,000, before its methods. The licences are laid out with no legal conclusion.
- **Q7, the 24/7 loop** (designed, nothing run): polling that stays clear of CelesTrak's 50-error limit, DEBRIS-C's M4 bands against TLE truth, and refit/flag/refuse criteria stated now. Around the clock, 68,450 objects take 13 to 48% of the RX 7600.
- **Q8, the build** (BELIEVED): four milestones, each with owner, gates and costs. No recommendation on the density model, the host, or IAS15 against rk4.

**Controls that failed as stated** (each kept in its log; each version 2 passed)
- **Q4's first reference:** one Romberg elimination gave 6.0e-5 m against the 1e-7 m criterion. Version 2 eliminated two error terms and passed at 2.0e-8 m.
- **Q3's first marking control:** the tiny-argument class marked no lanes. Version 2 used arguments next to exact cases, which marked 5, 510 and 532 of 1,024 lanes.
- **The degree sweep's first log:** three false FAILs from my parser, which choked on the drive colon in a Windows path. Version 2 names each refusal correctly.

**Requests for cft-fp256** (for you to put to its lead)
1. A larger constant bank, or index tables on `hip:N`.
2. A scratch depth above 256 slots on `hip:N`.
3. cftc that copes with very large systems: degree 20 did not compile in 290 s.
4. `pow` as a routine.
5. A `hip` target in cftc.
6. fp128 program rates on the cards, and rates below 1M lanes.
7. The specialised tier for programs.
8. An in-kernel divide and square root, only if an IAS15 kernel is wanted.
9. Certificates for forcing that changes between segments, and for values through a square root such as distances.

Certificates for `hip:N` runs are already requested. The test case to give back would be the drag-and-rotation system at fp128 and fp256.

**Not settled**
- Degree 20's instruction count is an ESTIMATE: it would not compile within the stop rule, and I did not compile it again.
- No rates for our images were measured on a card.
- NRLMSISE-00's operation counts.
- The density models' published accuracies: the paper pages refused the fetch (403/405), so those figures are BELIEVED.

**Not done**
- No certificate written or audited, and nothing run on a GPU.
- No cft-segrun or cft-audit runs, though both were built.
- No instrumented `ias15_cft.c`: its per-step count was read from the source.
- No downloads.

**What the brief got wrong, and a breach**
- **The Rules lacked a trap** (my ledger, 21:22:34). From Python, Windows searches System32 before PATH, so my wrapper's bare `bash -c` started `C:\Windows\System32\bash.exe`, the WSL launcher. It ran for 0.24 s, its gcc failed at once, and it wrote nothing. That broke "No GPU, WSL, card or box", by accident. Relayed through you: the default distro was cft2204, and nothing was disturbed. Since then I start every program by its full path.
- **The drag-and-rotation system named no force that needs sin and cos of ωt.** Co-rotating air needs no trigonometry, so I added C22/S22 in the Earth-fixed frame.
- **Störmer-Verlet with drag** is refused in v1, so I measured it without drag only.
- **The study runs to about 9,500 words,** past the 8 to 12 page aim; most of the length is tables.
- **I moved the generated field sources out of `studies` into scratch.** They carry values derived from EIGEN-6C4. `gen_field.py` regenerates them byte for byte, checked against `field_sources.sha256`.
