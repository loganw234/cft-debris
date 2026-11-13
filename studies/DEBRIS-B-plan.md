# DEBRIS-B: scoping a custom debris model (plan of record, draft 3)

Drafted 2026-11-12 by cft-debris's lead for Logan's approval. Nothing has been dispatched yet.
- Draft 1 went past a plan verifier (Sonnet), which found defects in nearly every section. Draft 2 answered them (ParcelRound METHOD §7, origin/main).
- The same verifier's scoped re-check of draft 2 confirmed those fixes and found seven smaller defects. This draft applies them in the verifier's own terms. It has not been re-checked a third time.
- The last three sections list what changed, and the lead's own slips.

## The question, in Logan's words

- **The question DEBRIS-A answered** (2026-11-12, put to cft-rebound's lead): "determine if rebound (and if so which integrator) would work best for long term high density space debris prediction, ideally capable of running in either direction to prove itself against historical data and cycle at a divergence from real data."
- **After DEBRIS-A** (2026-11-12): "Im considering how challenging making a custom simulation model might be, considering how specialized of a focus this is and effects REBOUND isnt particularly good at or even supports"
- **And** (2026-11-12): "Draft DEBRIS-B, I'm also curious if fp256 can buy us anything with our own model, as IAS15 showed no noticeable improvement past fp128 simply as it was designed for fp64 to begin with"

## What DEBRIS-B is for

DEBRIS-B is a study, like DEBRIS-A. Nothing is built and no repository changes. It gathers the evidence for Logan's next decision, which is one of:
- build a custom model;
- adopt existing tools (Orekit, cascade);
- a hybrid, in which those tools become the custom model's foreign oracles.

If the decision is to build, the evidence also says which product to build, held against which authorities, and at what cost.

It starts from DEBRIS-A, which has had no verifier. So a verifier re-measures DEBRIS-A in parallel, and DEBRIS-B treats every DEBRIS-A number as BELIEVED until that verifier reports.

## The shape

| agent | job | model | when |
|---|---|---|---|
| verifier-A | Disconfirm DEBRIS-A: re-run its scripts, fetch its load-bearing sources, hold its summary against its own tables | Sonnet | at dispatch |
| DEBRIS-B | The study: questions 1 to 4 in its brief below | Opus | at dispatch |
| verifier-B | Disconfirm DEBRIS-B the same way | Sonnet | when DEBRIS-B reports |
| the lead (this session) | Writes the briefs and keeps the ledger; relays verifier-A's findings to DEBRIS-B; answers escalations; files each final message; writes its own slips into the ledger and the round's record; writes the round's record with its cost (tokens processed per agent, read from the transcripts) | Opus | throughout |

The models follow Logan's rule of 2026-10-12 for challenging work: Opus authors, Sonnet verifiers. That rule is carried from cft-fp256 through the lead's memory; it was not re-read from cft-fp256's record.

**One figure measured twice.** HonestFramework METHOD §9 offers a way to check a judge without an answer key: give two agents the same measurement and compare. Here that measurement is IAS15's force evaluations per LEO object-day.
- DEBRIS-B measures it for its Q2 budget with its own setup and its own counter, never DEBRIS-A's `leo_roundtrip.py`. The physical setup is DEBRIS-A §2's: REBOUND 5.1.1, J2 as a Python force, eps 1e-9, one day.
- verifier-A re-measures DEBRIS-A's figure of 12,452 by re-running DEBRIS-A's script.
- The lead posts neither count anywhere until both final reports are in. Then it compares the two and records the result. If they disagree, one of the two claimed "measured" figures is false.
- Stated limit: both counts come from REBOUND's IAS15. Agreement shows that two setups and two counters agree on one integrator; it does not test the integrator.

## Dispatch

Each agent's prompt is its brief below, followed verbatim by this plan's sections "The ledger", "Rules every brief carries" and "READY".

Each agent sends one test escalation as it starts:
- it writes `test escalation from <name>` in its own ledger file;
- it sends the same words to the lead (SendMessage to `main`);
- the lead replies "received" and records the round trip in `lead.md`.

The route to `main` has not yet been tested from a dispatched agent.
- An agent whose send fails says so in its own ledger file and carries on.
- If the lead has no test escalation from an agent within ten minutes of dispatching it, the lead reads that agent's ledger file. It then arms a watch on the ledger directory (the file channel of METHOD §4) and says so in `lead.md`.

## The ledger

The ledger is `C:\Users\logan\source\repos\cft-debris-ledger\`, outside the project folder (ParcelRound METHOD §4, origin/main). It has existed since 2026-11-12, holding only `tools\`; entries begin at dispatch.

- **One file per author, append only:** `lead.md`, `DEBRIS-B.md`, `verifier-A.md`, `verifier-B.md`. Correct an entry by appending beneath it, never by editing it.
- **Times:** every heading's time comes from `date`, never from memory.
- **Read it at three moments:** before starting; before resting anything on a DEBRIS-A number; before the final report.
- **Verifiers read `lead.md` only, throughout.** This keeps their independence from the work they check.
- **Escalation:** write the entry first, then message the lead (SendMessage to `main`). Wait for the answer to a question; do not hold it for the report.
- **When to write:** when an entry would change another agent's work or the lead's. That means an environment fact, a brief that turned out wrong, or a finding about a shared input, never progress. Every entry marks which claims were measured and which are believed.
- **When a pause is announced**, record where you are before you stop: what is done, what is half done, what you were about to do. On resuming, do a full read, check your outputs before trusting your memory of them, and say where you stopped.
- **Scratch:** each agent creates its own directory when it starts, `C:\Users\logan\source\repos\cft-debris-scratch\<name>\`. Read no other agent's scratch. Keep no secrets anywhere an agent is given.
- **What the lead writes in `lead.md`, every verifier reads.**
  - So the lead relays upstream facts there, such as verifier-A's findings about DEBRIS-A.
  - It never writes a judgement of DEBRIS-B's work there before verifier-B has reported.
  - It never posts either overlap count there before both final reports are in.
- **`tools\ias15_cft.exe`** is the port binary DEBRIS-A used.
  - It was copied on 2026-11-12 from `cft-rebound-seam\build\`, which disappears when cft-rebound's round 4 closes.
  - SHA-256 `9d5cb048ee63e609bad448237476443c651623a96d7fe5f0340fd8cd5d8aa048`, identical to the original. A two-step run of each gave identical state output.
  - It needs `C:\msys64\mingw64\bin` first on PATH, for libwinpthread.
  - Use this copy, never the original.

## Rules every brief carries

From Logan's standing rules (carried from cft-fp256 and cft-rebound, 2026-09 to 2026-11) and canonical ParcelRound:

- **Read-only, except your own outputs and scratch.** cft-rebound and cft-fp256 are other sessions' live checkouts. Read their files, and use `git -C <repo> log` or `show`. Never write in them, never run `git status` there (it can rewrite the index), and never run a bare `git stash`.
- **No downloads, installs or package managers.** If a file would settle a question, ask the lead for it, giving its name, source URL, size, licence and purpose. Each file needs Logan's approval.
- **Reading the web.**
  - WebFetch returns a model's summary of a page, not the page's bytes.
  - A figure or quote taken through it is labelled "READ (via WebFetch)". It can support "consistent with", never "confirmed".
  - Test-vector files are located and identified (URL, file, size, licence), never transcribed.
  - A file you would need to open in order to describe it is a download request.
- **No GPU, WSL, card or box.** Take small measurements only, at the machine's natural load. The desktop is shared, and other sessions' suites run on it. State the load beside every timing, and never load the machine on purpose.
- **CPU budget** means the CPU time of the processes you start. For a single-threaded run at natural load, its wall time is an acceptable stand-in, if you say that is what you used.
- **Long jobs:** run them through the Bash tool, in the foreground with a timeout of at most 600000 ms or with run_in_background. Never use nohup, and never end your turn while one of your jobs is running. Ask the lead before anything longer than 10 minutes.
- **C:** put `C:\msys64\mingw64\bin` first on PATH before any compile, and check that `gcc -dumpmachine` prints `x86_64-w64-mingw32`. In this Git Bash a bare `gcc` is the 32-bit i686 compiler. The 64-bit one, called by its full path without that PATH, fails with rc=1 and no message.
- **Python:** `C:\Users\logan\AppData\Local\Programs\Miniconda3\python.exe -I -B`. The `-B` stops it writing `__pycache__`.
- **Processes and files:** kill only processes you started, and only by PID. Delete only what you made, and never through a computed path.
- **DEBRIS-A's records are read-only.** Its scripts write their outputs beside themselves (`HERE`), and they import one another.
  - Copy the five `.py` files, and nothing else, into an empty directory in your scratch, and run them there.
  - For the port sweep, use an empty directory per dt: `port_roundtrip.py` names its records by format and step count, not by dt.
  - Before your report, check all three: `sha256sum -c SHA256SUMS` run from `studies\` shows all 32 OK; `find studies/debris-a -type f | wc -l` gives 29; and there is no `__pycache__` anywhere under `studies\`.
- **Host traps:**
  - MSYS `.exe` transparency: writing a file `X` beside an existing `X.exe` writes to `X.exe`.
  - Passing a script to bash from Python with `text=True` turns every newline into CR+LF.
  - Never start a process under `pythonw`, or detached: each child opens a console window on Logan's desktop.
- **No helper agents.**
- **Your final message is your report.** Its word limit is in your brief. If the harness refuses the write of a document your brief names, your final message is that document followed by the report, and the word limit then applies to the report alone.
- **Before you report**, stop any background work you started. End with what you did not do, and with anything your brief got wrong.

## READY, stated before the first pass

READY applies to DEBRIS-B and to both verifiers' verdicts. Every load-bearing claim must rest on one of:
- a measurement, with its command and output;
- a fetched source, cited by URL;
- arithmetic from labelled inputs.

Otherwise it is stated as a limit, in terms of the behaviour it concedes. A claim's domain and quantifier are claims, and so is a figure's definition. A number carried over from DEBRIS-A keeps its definition, or it is re-measured.

A verifier may reuse a run instead of re-running it only when all three of these hold:
- someone other than the author of the work made the run;
- its inputs are identical, binary hashes included;
- the verifier re-runs from clean whatever it doubts.

Only a wrong answer sends work back: a false claim, or a measurement or check that cannot fail. Everything else is a note the lead records.
- **Loop cap (Logan, 2026-10-15, carried from QRO-Crate through the lead's memory):** after three NOT READYs for narrowing reasons, the next pass blocks only on wrong answers.
- **Threat model (Logan, 2026-10-02):** each verifier's brief states one, and findings outside it do not reopen the loop.

## Logan's decisions (each default stands unless changed)

1. **Models:** Opus for DEBRIS-B, Sonnet for both verifiers.
2. **Downloads:** none pre-approved. Each named file is asked for during the round.
3. **Raw page text:** may agents read a page's raw text with `curl` to stdout, saving nothing, where WebFetch's summary could paraphrase a figure? Default: no.
4. **Budgets:**
   - DEBRIS-B: 4 hours of wall time and 25 CPU-minutes. The Q3 sweep alone takes about 13 CPU-minutes.
   - verifier-A: 2 hours and 10 CPU-minutes.
   - verifier-B: 2 hours and 15 CPU-minutes.
5. **Outputs** go in `cft-debris\studies\`, beside DEBRIS-A.

## Not in this round

- Building anything.
- Running Orekit, cascade, heyoka or GMAT (each needs an install).
- Any GPU or tile run.
- The decision itself, which is Logan's.

---

## Brief: DEBRIS-B

You are study parcel **DEBRIS-B** in cft-debris, a new project for space-debris tracking and simulation. Its folder, `C:\Users\logan\source\repos\cft-debris`, is not a git repository. This is a study, not an implementation: nothing is built and no repository changes.

**Budget:** 4 hours of wall time and 25 CPU-minutes. Message the lead before you pass either.

**Start here:**
1. This plan, `C:\Users\logan\source\repos\cft-debris\studies\DEBRIS-B-plan.md`: the question in Logan's words and what the study is for.
2. DEBRIS-A: `studies\DEBRIS-A-rebound-for-debris.md`, with its scripts, logs and records in `studies\debris-a\`. Treat its numbers as BELIEVED. verifier-A is re-measuring them now, and its findings reach you through `lead.md`.
3. For question 3: `C:\Users\logan\source\repos\cft-rebound\docs\HORIZON.md` in full, and the section "The fp64-versus-fp256 result" in `C:\Users\logan\source\repos\cft-fp256\docs\ORBITS.md`.

**Your job.** Answer the four questions below for Logan's decision about a custom debris model.
- **Where it goes:** the study in `studies\DEBRIS-B-custom-model.md`; your scripts, logs and records in `studies\debris-b\`.
- **Order:** a short answer, then the four questions, then the measurements with their commands, then the sources. Aim for 6 to 10 pages.
- **Labels:** mark every claim MEASURED, COMPUTED, READ or BELIEVED, as DEBRIS-A does. READ means you fetched it. A "not found" records the route you took and the response you got.

**Q1. Authorities, layer by layer.** Work through the layers in this order, which is the order product (a) in Q4 needs them:
1. time scales and frames: UTC, TAI, TT, UT1, TDB; GCRF, ITRF, TEME;
2. Earth orientation data and leap seconds;
3. the gravity field;
4. the Sun and Moon;
5. atmosphere and space weather, historical and forecast;
6. radiation pressure, Earth's shadow, and object area-to-mass;
7. SGP4/SDP4 and TLEs;
8. orbit determination;
9. truth data for hindcasts;
10. object properties;
11. conjunction screening and collision probability;
12. fragmentation and long-term environment models.

For each layer, give:
- the standard or model;
- its reference implementation and licence;
- where its published test vectors are: the URL, the file or table, its size from the server's own listing, and its licence, located and identified but not transcribed;
- whether it can be obtained without registration;
- what is already on this host (see Instruments below).

Consider at most two candidate authorities per layer. When your time box nears, finish the table with "not reached" rows rather than dropping layers.

Then name at least one whole-propagator foreign oracle (Orekit, GMAT): what it would take to run here, and what its agreement would and would not prove.

**The trap:** two implementations of one source agreeing is not an external authority (HonestFramework METHOD §1). Orekit's SGP4 agreeing with Vallado's SGP4 is a port agreeing with its original. Vallado's published verification output is the authority.

**Q2. The cost of a real force evaluation.** This was DEBRIS-A's biggest open item, and it decides the catalogue budget.

**What to time.** Measure at binary64 on this host, using small self-written C (`gcc -O2`, see Rules) or numpy, with no downloads:
- spherical-harmonic gravity at degree and order 8, 20, 36 and 70;
- Chebyshev evaluation of the Sun's and Moon's positions at a DE-like degree;
- the GCRF-to-ITRF transformation as a propagator computes it: the IAU 2006/2000A precession-nutation series at the standard's own term count (READ that count), the Earth rotation angle, and polar motion. Time it once at full cost, and once as the per-step cost when a propagator interpolates it; state the interval;
- an exponential atmosphere, as the floor;
- radiation pressure with a conical shadow.

**How:**
- Draw synthetic coefficients in the real model's magnitude range, with no zeros and no subnormals.
- State each timed unit's operation count.
- For NRLMSISE-00 and JB2008, READ their cost, or measure it if Logan approves a named download.

**Negative controls,** named by the property that makes each one bite. Report both results.
1. **The compiler can discard work whose result is never used.**
   - Every timed loop folds every output component into a checksum it prints.
   - A run with the force call removed must time at least 10 times faster.
   - If a kernel is too cheap for that (the exponential atmosphere may be), time it over enough points per call that it passes, and say how many.
2. **A fast wrong answer is still wrong.** Compare each kernel's output on a few inputs with an independent evaluation in numpy or mpmath, to a stated tolerance, with an assertion that fails the run. A printed value does not count.

**The overlap:** measure IAS15's force evaluations per LEO object-day yourself, with your own setup and your own counter, never DEBRIS-A's `leo_roundtrip.py`, as "One figure measured twice" in the plan describes. Put the count in your report only, not in your ledger file.

**Then COMPUTE the catalogue-year budget for each regime:** your evaluations per object-day × the number of objects (cite where that count comes from) × 365, priced at the costs you measured.

**Q3. Arithmetic beyond binary64.** Start from what is already measured:
- HORIZON.md's criterion, its two growth laws, "Where binary64 is entirely sufficient" and "The niche";
- ORBITS.md's "What binary64's roundoff is worth as a perturbation";
- DEBRIS-A's port records.

**Apply that to debris.** For each regime (LEO with drag; MEO and GNSS disposal; GEO and graveyard) and each horizon (a week, a year, decades), set binary64's arithmetic error against:
- initial-condition uncertainty, at TLE level and at precise-orbit level;
- density uncertainty;
- area-to-mass uncertainty.

Compute binary64's arithmetic error from those laws (COMPUTED). Name the measured coefficient you transfer each figure from, and say what does not transfer.

**What a wider format could still buy a custom model:**
- a certificate, or ruler, for the production propagator's numerical error;
- ensembles that measure the dynamics, not the arithmetic, in chaotic regimes;
- ill-conditioned orbit determination;
- covariance propagation.

For each, say whether binary128 is enough, and when binary256 would be needed. Price it:
- on the software backend, from DEBRIS-A's records;
- on the tile, where HORIZON.md calls the rate format-blind. Ask the lead to put the question to cft-fp256's lead. Never run on the tile.

**Logan's hypothesis, tested:** "IAS15 showed no noticeable improvement past fp128 simply as it was designed for fp64".

- **What the records show** (`debris-a\port_quarterday.log`): at the quarter-day turn, binary128 and binary256 differ by 1.162e-27 m. Yet both formats' round trips miss home by the same 8.909e-22 m.
- **The prediction:** halving dt should cut the binary256 round trip by between 2^13 and 2^17.
  - At the central exponent of 15.4, that is about 2.1e-26 m at dt = 50 s and 4.9e-31 m at 25 s.
  - The band runs from 1.1e-25 to 6.8e-27 m at 50 s, and from 1.3e-29 to 5.2e-32 m at 25 s.
  - Binary128's should follow to about 50 s, then stop falling near its own roundoff (about 1e-27 m, the binary128-versus-binary256 difference at the quarter-day turn). It may rise with the step count.
- **The prediction's basis:** HORIZON.md's binary128 truncation coefficients, at 51 and 138 steps an orbit, are 1.71e-21 and 3.86e-28. Together they imply the method's error scales as about the 15.4th power of the step.
- **What to run:** quarter day each, on the preserved port (`tools\ias15_cft.exe` in the ledger), using copies of `port_roundtrip.py` and `leo_roundtrip.py`:
  - binary256 at dt = 50 s (432 steps) and 25 s (864 steps);
  - binary128 at 50, 25 and 12.5 s (1728 steps);
  - binary64 at 50 and 25 s, as the positive control. An arithmetic floor must not fall with dt; if it does, the sweep is not measuring what it claims.
- **Cost:** about 13 CPU-minutes in all. Run the long legs with run_in_background.
- **Also report:** the binary128-versus-binary256 forward difference at the turn, for each dt where both ran.
- **If binary256's floor does not fall within that band,** the floor is not the method's discretization, and Logan's reading needs another explanation. Say which.
- **What to READ:** what an integrator built for wide formats looks like. Variable-order Taylor methods raise the order rather than shrink the step (see heyoka's documentation on precision and order). Read it against the slope you measure.

**Q4. The product question, laid out for Logan to decide.** There are three shapes:
- (a) single-object prediction, with orbit determination and hindcasts against independent truth;
- (b) catalogue propagation and conjunction screening;
- (c) the population's evolution over decades.

For each shape, give:
- the layers it needs (Q1) and its cost (Q2);
- what validates it: which truth data exist, and for which objects;
- what Orekit, cascade, MASTER and the others already do;
- whether a custom model could do something they don't.

Test these candidates rather than assume them:
- bit-reproducible predictions that carry their own provenance, from libcft's determinism, binary64 included;
- uncertainty carried with every prediction, with a refusal past the point where it can be bounded;
- GPU-scale or tile-scale ensembles.

For each candidate, say what measurement would show it is real, and whether anyone needs it. Label judgement BELIEVED. Where the evidence does not decide, make no recommendation.

**Instruments on this host** (the lead checked them on 2026-11-12):
- **Python** (see Rules): rebound 5.1.1, numpy 2.2.6, mpmath 1.3.0 and gmpy2 2.2.1. Not installed: scipy, sgp4, astropy, erfa, skyfield, jplephem, spiceypy, pymsis, heyoka, orekit.
- **C** (see Rules): gcc 16.1.0 (MSYS2 mingw64). libquadmath is present, so `__float128` is available.
- **The port:** the preserved copy, `C:\Users\logan\source\repos\cft-debris-ledger\tools\ias15_cft.exe`. Its command line is in `debris-a\port_quarterday.log`. Write every output into your scratch.
- **Java:** `java` on PATH is Java 8 (1.8.0_411). Whether that is enough for Orekit is not known, and no Orekit run is planned.
- **The web:** WebSearch and WebFetch, under the reading rule.

**Do not:**
- write outside `studies\DEBRIS-B-custom-model.md`, `studies\debris-b\` and your scratch;
- weaken a claim's label to make it pass;
- fix anything in DEBRIS-A. Report it instead.

**Report:** your final message, under 800 words:
- the short answer;
- the four verdicts, each with its most load-bearing evidence and its label;
- your force-evaluation count for the overlap;
- anything you could not settle;
- what you did not do;
- anything this brief got wrong.

---

## Brief: verifier-A

You are **verifier-A**: a verifier, not an author. Try to disconfirm study DEBRIS-A (`C:\Users\logan\source\repos\cft-debris\studies\DEBRIS-A-rebound-for-debris.md`, with its records in `studies\debris-a\`), and report. Fix nothing.

**Budget:** 2 hours of wall time and 10 CPU-minutes. Message the lead before you pass either. In the ledger, read `lead.md` only.

DEBRIS-A was written by another session's study parcel. Its labels are its author's own, and no verifier has checked it. A later study, DEBRIS-B, is running now and will rest on its numbers. The question is whether those numbers, and the sentences built on them, hold.

**Threat model.**
- **In scope:**
  - numbers that do not reproduce from DEBRIS-A's own scripts;
  - a summary or table that misquotes its records;
  - READ claims the cited source does not support;
  - a measurement that could not fail, such as a reference that shares the error it is used to measure;
  - a claim whose domain or quantifier reaches past its evidence.
- **Out of scope:** re-deciding its recommendations, and physics outside its stated models.

**Attack these:**
1. **Re-run every command in DEBRIS-A §7, in §7's order.** Work from copies, as the Rules say: the five `.py` files only, in an empty directory. For the port, use the preserved copy, `C:\Users\logan\source\repos\cft-debris-ledger\tools\ias15_cft.exe`. Point your copy of `port_roundtrip.py` at it, and say so. Compare the new outputs with the archived logs, and with every number the study quotes from them. Report the force-evaluation count per LEO object-day you get for IAS15 at eps 1e-9.
2. **The state transition matrix check** (`var_check.py`). Is the point-mass case a real control, one that would show a wrong column? Do "0.44" and "8.0e-10" reproduce?
3. **The references.** For each error column, what was the reference? Does the reference share the error it is used to measure?
4. **The READ claims.** Fetch the source behind every READ claim in "Short answer", "Recommendation" and §8, and say whether it says that. Under the Rules' reading rule, a figure read through WebFetch can earn "consistent with" or "not found", never "confirmed". For each source you cannot reach, record the route and the response.
5. **The summary against the tables.** Hold every figure, and every quantifier, in "Short answer", "Recommendation" and §8 against the table or record it rests on.
   - The lead suspects that the short answer's "Every round trip comes home to within 1.1e-6 m" outruns §2's MEO/GEO table. Confirm or refute that, then look for others of the same kind.
   - Check the claim the lead got wrong once: "within 1.4e-7 m of a binary128 reference", against `debris-a\check_ref.log`.
6. **The COMPUTED figures.** Redo the arithmetic for the catalogue budgets, the e-folding times, the JANUS overflow and the pole drift.
7. **The lead's own claims.** Check the lead's grants and rulings in `lead.md` made after dispatch. Check this plan's statements about DEBRIS-A's records: the figures DEBRIS-B's brief quotes from `port_quarterday.log`, and the copy's SHA-256.
8. **Anything else.** The list above is what the lead suspects; report what the lead did not think to ask.

**Report:** your final message, under 1,200 words. For each item give:
- the commands you ran;
- what you observed;
- a verdict: confirmed, defect, or not determined.

Every defect needs a concrete failure scenario, not just a concern. Distinguish "DEBRIS-A is right" from "DEBRIS-A's check would have caught it if it weren't". "Found nothing" is an acceptable answer and will not be held against you; say plainly what you ran.

## Brief: verifier-B (completed when DEBRIS-B reports)

This is verifier-A's brief, applied to DEBRIS-B, with a budget of 2 hours of wall time and 15 CPU-minutes. DEBRIS-B authored its own runs, so verifier-B may not reuse them. The attack list is finished from DEBRIS-B's own content and starts with:
1. Re-run from clean at least the dt = 25 s legs and the binary64 control of the Q3 sweep, and Q2's timings with and without the force call, with their asserted comparisons.
2. Fetch every load-bearing READ claim, recording the route and the response for any "not found".
3. Redo every COMPUTED figure.
4. Hold the summary against the tables, domain and quantifier included.
5. Check that every figure carried over from DEBRIS-A keeps its definition, or was re-measured.
6. Check the Q3 sweep against its stated band.
7. Check the lead's rulings in `lead.md`, and this plan's premises.
8. Anything else.

---

## What changed from draft 1 (the plan verifier's findings, answered)

| finding | answer |
|---|---|
| A bare `gcc` in this Git Bash is i686, and the 64-bit one fails silently without its PATH | A C rule in "Rules every brief carries": PATH first, and `gcc -dumpmachine` must print `x86_64-w64-mingw32`. The lead reproduced both failure modes. |
| The port binary's identity rested on its mtime alone, and the binary could disappear | It is copied into the ledger's `tools\`; the SHA-256 is identical to the original; a two-step run of both gives identical state output. Every brief uses the copy. |
| DEBRIS-B's brief carried no budget; the dispatch text was unspecified; no stop line; no pause note; the test escalation was undefined | A budget in every brief; a "Dispatch" section; Q1's order, a two-candidate limit and "not reached" rows; a pause/resume rule; the test escalation's text and recipient. |
| Verifier lists lacked the reuse-of-runs conditions, the lead's rulings and the plan's premises; there was no list of the lead's slips | Reuse conditions in READY; items 7 and 8 for verifier-A and verifier-B; the lead's slips listed below and in the round's record. |
| Q1 asked for test vectors "fetched, not recalled" under a no-downloads rule, through a summarising fetch | The vectors are located and identified, never transcribed. Anything read through WebFetch is labelled as such. Raw-text `curl` is Logan's decision 3. |
| The 800-word report conflicted with the document-in-message fallback | The limit applies to the report alone. |
| Q2's controls allowed partial elimination and an undefined unit, compared nothing, and had no rule for cheap kernels; the "values don't matter" claim fails for subnormals | The checksum covers every component; a comparison against numpy or mpmath fails the run on a mismatch; operation counts are stated; the frame unit is defined; cheap kernels are batched; magnitudes are realistic. |
| The dt-sweep prediction had no stated basis, no band, a single point past binary128's crossover, and no positive control | Basis: HORIZON.md's 51- and 138-step coefficients (exponent about 15.4). A band of 2^13 to 2^17 per halving. Binary128 at 12.5 s added. Binary64 added as the positive control. The binary128-versus-binary256 difference reported at each dt. |
| The withheld control leaked through the plan's text and the ledger, its key was the lead's own judgement, and its limit was understated | **Dropped.** Of its two items, the second was the lead's misreading (slip 1 below), and one thin item is no measurement. It is replaced by "One figure measured twice". The remaining suspicion is named openly in verifier-A's item 5. Verifiers now read only `lead.md`, and scratch has moved out of the ledger tree. |
| Verifier-B's 10 CPU-minutes could not cover re-running the sweep | 15 CPU-minutes, with the dt = 25 s legs and the binary64 control re-run from clean. |
| The time boxes were tight; "CPU-minute" was undefined | DEBRIS-B 4 hours; each verifier 2 hours; CPU budget defined in the Rules. |
| `sha256sum -c` cannot see added files; the copy instructions were ambiguous; one script imports another | Python runs with `-B`; a file count of 29 and a `__pycache__` check before every report; the copies are the five `.py` files only, in an empty directory, one per dt for the sweep. |
| The owner rules dated 2026-10-12 and 2026-10-15 are in neither canonical METHOD nor ADOPTION | Each is cited as carried from cft-fp256 or QRO-Crate through the lead's memory, and not re-read. |

## What changed from draft 2 (the scoped re-check's findings)

| finding | answer |
|---|---|
| The plan said "six `.py` files" where there are five | Five, in all three places. |
| The reading rule forbade quoting the values that Q1, Q2 and verifier-A's item 4 need | A figure read through WebFetch is labelled as such and supports "consistent with", never "confirmed". Vector files are located, never transcribed. |
| The overlap ran the same code and counter, and whichever count was posted first could reach the other agent | DEBRIS-B uses its own setup and counter. The lead posts neither count until both reports are in. The limit is stated. |
| Who creates the scratch directories was unstated | Each agent creates its own. |
| Java's version was unstated | Java 8 (1.8.0_411), checked by the lead. |
| Whether a dispatched agent can reach `main` is untested | A ten-minute fallback: the lead arms a file watch and says so. |
| `lead.md` is every verifier's input, and the lead relays through it | Only upstream facts go there: no judgement of DEBRIS-B's work before verifier-B reports, and no overlap count early. |
| DEBRIS-B had about 7 CPU-minutes left after the sweep | DEBRIS-B's CPU budget is raised to 25 minutes (decision 4). |

## The lead's slips so far

1. **A misreading, passed on.** Draft 1 seeded a withheld control with two wording defects in DEBRIS-A. The second was the lead's misreading: DEBRIS-A's "within 1.4e-7 m of a binary128 reference" is measured directly against the port's binary128 run (`debris-a\check_ref.log`: 1.439e-07 m). The lead had read the §2 table's reference and never opened that log. It had passed the misreading on to Logan and to cft-rebound's lead; both were corrected on 2026-11-12.
2. **A broken path check.** Draft 1's first mechanical check selected zero paths. Its second marked every path missing because of a `sed` quoting error. Both were caught before the plan went out. The check that held was rewritten in Python with controls in both directions: a known file must read as existing, and a bogus path as missing.
3. **A moved working directory.** Twice, a `cd` in the lead's own shell moved the session's working directory. The lead now uses absolute paths.
4. **A count typed from memory.** Draft 2 said "six `.py` files" where there are five. The re-check caught it.
