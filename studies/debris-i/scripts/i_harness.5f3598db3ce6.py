"""i_harness.py - cft-debris DEBRIS-I: the gates' harness. It compiles the program and its part systems, fills their
values, runs the driver, holds the executor to the reference interpreter (I1) and the program to M1 (I2, I3), and
writes the logs. Standard library only where it runs on the box (modes box-*); the desktop's modes use the archive's
cft_golden (the reference interpreter and the golden softfloat) and mpmath.

cft-debris, MIT licence (see LICENSE at the repository root). Written by DEBRIS-I, 2026-11-23. DEBRIS-D's
studies/debris-d/q2/q2_first_test.py (cft-debris's own, MIT) is the model of I1's comparison and its marked-lane rule.

usage: python -I -B i_harness.py <mode> --cfg CFG.json [options]
  CFG.json names every path: repo, scratch, fp256 (the extracted archive), downloads, frame_table, test_seed, seed,
  bin (the folder of m1i and i_run), py (the desktop's Python). No path is written in this script.
modes (desktop): compile, i1, ...
"""
import argparse
import json
import os
import struct
import subprocess
import sys
import time
from fractions import Fraction

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import i_lib  # noqa: E402
import i_vals as V  # noqa: E402

SCRIPT = os.path.abspath(__file__)
MODULES = [os.path.join(HERE, m) for m in ("i_vals.py", "i_gen.py", "i_lib.py")]
WIDTH = V.ESZ
STEPS_SEG = 40
DEPTH = 512
TARGET = "sw:512"
N_PROG = 7


def cfg_load(path):
    c = json.load(open(path, "rb"))
    for k in ("repo", "scratch", "fp256", "downloads", "frame_table", "test_seed", "seed", "bin", "py"):
        if k not in c:
            raise SystemExit("cfg: %s missing" % k)
    c["logs"] = os.path.join(c["repo"], "studies", "debris-i", "logs")
    c["kept"] = os.path.join(c["repo"], "studies", "debris-i", "scripts")
    c["systems"] = os.path.join(c["repo"], "studies", "debris-i", "systems")
    c["work"] = os.path.join(c["scratch"], "work")
    c["img"] = os.path.join(c["scratch"], "images")
    for k in ("work", "img", "systems"):
        os.makedirs(c[k], exist_ok=True)
    return c


def exe(cfg, name):
    p = os.path.join(cfg["bin"], name)
    return p + ".exe" if sys.platform == "win32" else p


def m1env(cfg):
    e = dict(os.environ)
    d = cfg["downloads"].replace("\\", "/")
    e["M1_DOWNLOADS"] = d if d.endswith("/") else d + "/"
    return e


# ------------------------------------------------------------------ systems and compiles

def gen_system(cfg, kind, fmt, name=None, **kw):
    """Write a generated source into studies/debris-i/systems/ (data-free) and return (path, info)."""
    import i_gen
    if kind == "program":
        text, info = i_gen.program(kw.get("degree", N_PROG), fmt, kw.get("bands", 28), V.DM, V.DO,
                                   kw.get("layout", "bank:grav,bands,scal;lane:de,frame"))
        stem = name or "program-d%d-%s" % (kw.get("degree", N_PROG), fmt)
    elif kind == "program20":
        text, info = i_gen.program20(fmt)
        stem = name or "program20-lane-%s" % fmt
    else:
        text, info = i_gen.part(kind, kw.get("degree", N_PROG), fmt, kw.get("bands", 28), V.DM, V.DO)
        stem = name or "part-%s-%s" % (kind, fmt)
    path = os.path.join(cfg["systems"], stem + ".cftl")
    data = text.encode("ascii")
    if os.path.exists(path) and open(path, "rb").read() != data:
        raise SystemExit("%s exists with other bytes: a source is never overwritten" % path)
    if not os.path.exists(path):
        with open(path, "wb") as f:
            f.write(data)
        with open(path + ".json", "wb") as f:
            f.write((json.dumps(info, indent=1, sort_keys=True) + "\n").encode("ascii"))
    return path, info, stem


COMPILES = "compiles.tsv"
COMPILE_COLS = ["time_local", "stem", "format", "target", "steps", "source", "source_sha256", "result", "cftp_sha256",
                "bank_sha256", "manifest_sha256", "instructions", "per_step", "alu", "loads", "stores",
                "routine_calls", "bank_slots", "bank_params", "bank_consts", "bank_words", "scratch_slots",
                "scratch_state_lane", "spill_slots", "scratch_declared", "features", "order", "wall_s", "command"]


def compile_sys(cfg, src, fmt, target, stem, steps=STEPS_SEG, timeout=None, log=None):
    """cftc at the pin on one source; one row in studies/debris-i/compiles.tsv whatever the result."""
    out = cfg["img"]
    cftc = os.path.join(cfg["fp256"], "python", "cftc")
    cmd = [cfg["py"], "-I", "-B", cftc, src, "--steps", str(steps), "--target", target, "--format", fmt, "--out", out,
           "--stem", stem]
    t0 = time.time()
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        rc, err = r.returncode, r.stderr.strip()
    except subprocess.TimeoutExpired:
        rc, err = None, "stopped by the timeout of %s s" % timeout
    wall = time.time() - t0
    rel = os.path.relpath(src, cfg["repo"]).replace("\\", "/")
    row = {"time_local": time.strftime("%Y-%m-%d %H:%M:%S %z"), "stem": stem, "format": fmt, "target": target,
           "steps": steps, "source": rel, "source_sha256": i_lib.sha256_file(src), "wall_s": "%.1f" % wall,
           "command": "python -I -B <archive 9e8ff270>/python/cftc %s --steps %d --target %s --format %s --out <dir> "
                      "--stem %s" % (rel, steps, target, fmt, stem)}
    man = None
    if rc == 0:
        mp = os.path.join(out, stem + ".manifest.json")
        man = json.load(open(mp, "rb"))
        kinds = {}
        for b in man["bank"]:
            kinds[b["kind"]] = kinds.get(b["kind"], 0) + 1
        nlane = sum(1 for e in man["scratch"]["layout"] if e["kind"] != "state")
        nst = sum(1 for e in man["scratch"]["layout"] if e["kind"] == "state")
        rt = man.get("routines", {})
        row.update({"result": "compiled", "cftp_sha256": i_lib.sha256_file(os.path.join(out, stem + ".cftp")),
                    "bank_sha256": i_lib.sha256_file(os.path.join(out, stem + ".bank")),
                    "manifest_sha256": i_lib.sha256_file(mp), "instructions": man["uses"]["instructions"],
                    "per_step": man["per_step"]["instructions"], "alu": man["per_step"]["alu"],
                    "loads": man["per_step"]["loads"], "stores": man["per_step"]["stores"],
                    "routine_calls": json.dumps(rt.get("calls", {}), sort_keys=True).replace(" ", ""),
                    "bank_slots": man["uses"]["bank_slots"], "bank_params": kinds.get("param", 0),
                    "bank_consts": kinds.get("const", 0) + kinds.get("flip", 0), "bank_words": kinds.get("word", 0),
                    "scratch_slots": man["uses"]["scratch_slots"], "scratch_state_lane": "%d+%d" % (nst, nlane),
                    "spill_slots": man["scratch"]["spill_slots"], "scratch_declared": man["uses"]["scratch_declared"],
                    "features": ",".join(man["uses"]["features"]), "order": man["lowering"]["order"]})
    else:
        name = err.split("refused ", 1)[1].split(":", 1)[0] if "refused " in err else ("timeout" if rc is None else "exit %s" % rc)
        row.update({"result": "refused %s: %s" % (name, err.replace("\t", " ").replace("\n", " | ")[:400])})
    tsv = os.path.join(cfg["repo"], "studies", "debris-i", COMPILES)
    new = not os.path.exists(tsv)
    with open(tsv, "a", encoding="ascii", newline="\n") as f:
        if new:
            f.write("\t".join(COMPILE_COLS) + "\n")
        f.write("\t".join(str(row.get(c, "")) for c in COMPILE_COLS) + "\n")
    if log:
        log.w("compile %s: %s; %s instructions, bank %s, scratch %s (spills %s), %.1f s; source %s, image %s"
              % (stem, row["result"][:200], row.get("instructions", "-"), row.get("bank_slots", "-"),
                 row.get("scratch_slots", "-"), row.get("spill_slots", "-"), wall, row["source_sha256"],
                 row.get("cftp_sha256", "-")))
    return rc, man, row


def need_image(cfg, src, fmt, stem, log, target=TARGET):
    """The image of src at fmt, compiled once: reuse an image whose manifest names this source's SHA-256."""
    mp = os.path.join(cfg["img"], stem + ".manifest.json")
    if os.path.exists(mp):
        man = json.load(open(mp, "rb"))
        if man["source"]["sha256"] == i_lib.sha256_file(src) and man["format"] == fmt and \
                man["target"]["name"] == target:
            log.w("image %s: reused (manifest names source %s)" % (stem, man["source"]["sha256"]))
            return man
    rc, man, row = compile_sys(cfg, src, fmt, target, stem, log=log)
    if rc != 0:
        raise SystemExit("compile of %s refused: %s" % (stem, row["result"]))
    return man


# ------------------------------------------------------------------ the frame (M1's) and a run's values

def stage_times(T0, T1):
    return [T0 + Fraction(15, 2) * j for j in range(int((T1 - T0) / Fraction(15, 2)) + 1)]


def m1_frames(cfg, times, tag):
    """M1's frame_at at cft256 at each time (m1i frames): {t: [12 Fractions]}."""
    tp = os.path.join(cfg["work"], "%s.times.txt" % tag)
    op = os.path.join(cfg["work"], "%s.frames.txt" % tag)
    with open(tp, "w", newline="\n") as f:
        for t in times:
            f.write(float(t).hex() + "\n")
            if Fraction(float(t)) != t:
                raise SystemExit("a time not exact in binary64")
    r = subprocess.run([exe(cfg, "m1i"), "frames", "cft256", "--table", cfg["frame_table"], "--times", tp, "--out", op],
                       capture_output=True, text=True, env=m1env(cfg))
    if r.returncode:
        raise SystemExit("m1i frames: %s" % r.stderr)
    return V.read_frames(op)


class Program:
    """A compiled system with its slots and its static values at one format."""

    def __init__(self, cfg, src, info, man, fmt, stem):
        self.cfg, self.src, self.info, self.man, self.fmt, self.stem = cfg, src, info, man, fmt, stem
        _m, self.bank_slot, self.scr_slot, self.nscr, self.nstate = V.manifest_slots(
            os.path.join(cfg["img"], stem + ".manifest.json"))
        self.esz = WIDTH[fmt]
        self.base_bank = open(os.path.join(cfg["img"], stem + ".bank"), "rb").read()
        self.nconst = len(self.base_bank) // self.esz
        self.lane_names = [e["name"] for e in man["scratch"]["layout"] if e["kind"] != "state"]
        self.state_names = [e["name"] for e in man["scratch"]["layout"] if e["kind"] == "state"]
        self.vals = V.Vals(os.path.join(cfg["fp256"], "python"), fmt, cfg["downloads"],
                           os.path.join(cfg["repo"], "src", "m1_consts.h"), max(info.get("degree", 2), 2))
        self._graph = None

    def graph(self):
        if self._graph is None:
            sys.path.insert(0, os.path.join(self.cfg["fp256"], "python"))
            from cft_golden import lang
            self.lang = lang
            self._graph = lang.compile_text(open(self.src, "rb").read(), os.path.basename(self.src), self.fmt).graph
            if [p[0] for p in self._graph.param] != self.info["params"] or \
                    [x[0] for x in self._graph.lane] != self.info["lanes"]:
                raise SystemExit("the graph's params are not the generator's")
        return self._graph

    def run_values(self, T0, fit):
        """Every value of a run starting at T0: the static ones, DE421's block at T0 and the frame's fit."""
        v = dict(self.vals.v)
        de, where = self.vals.de_block(T0)
        v.update(de)
        if fit is not None:
            v.update(self.vals.frame_block(fit))
        return v, where

    def bank_params(self, v):
        return {name: v[name] for name in self.bank_slot}

    def bank(self, v):
        return V.bank_bytes(self.base_bank, self.esz, self.bank_slot, v)


def enc(prog, x):
    return prog.vals.q(Fraction(x))


# ------------------------------------------------------------------ I1

I1_CRIT = """I1: the program against its definition (cftc's reference interpreter, lang.run, at cft-fp256 9e8ff270).
Runs: 16 lanes, the test seed's indices 0..15 at its T_s (2026-11-17 00:00 TDB), 160 steps of 15 s in two runs of 80,
each run two segments of 40; each run's values (DE421's sub-interval at the run's start, the frame's fit over the run's
own 161 stage times) filled by the driver; the state carried across the run boundary, every lane param rewritten.
(a) after every segment, every unmarked lane's state equals lang.run's from the same boundary state with the same
    values, bit for bit (the NaN rule: NaN results agree as NaNs), and its lane byte has [7:5] clear and [4:0] equal to
    lang.run's five flags for that lane and segment; a marked lane (bit 7) is replayed by lang.run, its guess counted and
    compared, never required, and the replay's state carried on;
(b) t at every boundary equals the run's start + 600 s x the segment, exactly;
(c) every mark is counted, by run and segment.
C3 (control): lang.run on lanes 0 and 1 for the first segment with GM's encoding one up (as the run's value) must differ
    from the executor's unplanted state in at least one value; identical = control FAILED.
C4 (control, binary64 only): the executor's run 1, segment 1 given the Moon's coefficients of the following sub-interval
    must change every lane's state; any lane unchanged = control FAILED."""


def is_nan(fm, bits, sf):
    return sf.is_nan(fm, bits)


def same(prog, a, b):
    """The NaN rule: equal bits, or both NaN."""
    sf = prog.vals.sf
    return all((x == y) or (sf.is_nan(prog.vals.fm, x) and sf.is_nan(prog.vals.fm, y)) for x, y in zip(a, b))


def lanes_init(prog, rows, T0, extra=None):
    """INIT: each lane's state (t, then the seed's x..vz) and lane params (bc from the seed; shared ones 0)."""
    out = []
    for k, row in enumerate(rows):
        st = [enc(prog, T0)] + [enc(prog, Fraction(x)) for x in row[2]]
        lp = []
        for nm in prog.lane_names:
            if nm == "bc":
                lp.append(enc(prog, Fraction(row[3])))
            elif extra and nm in extra[k]:
                lp.append(extra[k][nm])
            else:
                lp.append(0)
        out.append(st + lp)
    return out


def run_driver(prog, tag, runs_spec, init, n):
    """Write RUNS and INIT, run i_run, read the segments and marks."""
    cfg = prog.cfg
    shared = [prog.scr_slot[nm] for nm in prog.lane_names if nm in runs_spec[0]["shared"]]
    shared_names = [nm for nm in prog.lane_names if nm in runs_spec[0]["shared"]]
    runs = []
    tslot = prog.scr_slot.get("t")
    for r in runs_spec:
        runs.append((r["nseg"], tslot if r.get("t_enc") is not None else None, r.get("t_enc") or 0, r["bank"],
                     [r["shared"][nm] for nm in shared_names]))
    rp = os.path.join(cfg["work"], tag + ".runs.bin")
    ip = os.path.join(cfg["work"], tag + ".init.bin")
    V.write_runs(rp, prog.esz, prog.nconst, prog.nscr, prog.nstate, shared, runs)
    V.write_init(ip, prog.esz, init)
    pre = os.path.join(cfg["work"], tag)
    r = subprocess.run([exe(cfg, "i_run"), "run", "--image", os.path.join(cfg["img"], prog.stem + ".cftp"), "--runs", rp,
                        "--init", ip, "--lanes", str(n), "--depth", str(DEPTH), "--out", pre],
                       capture_output=True, text=True)
    if r.returncode:
        raise SystemExit("i_run %s: exit %d: %s" % (tag, r.returncode, r.stderr))
    segs = V.read_segs(pre + ".seg.bin", n, prog.nstate, prog.esz)
    marks = V.read_marks(pre + ".marks.bin", prog.nscr, prog.nstate, prog.esz)
    return segs, marks, r.stdout, {"runs": i_lib.sha256_file(rp), "init": i_lib.sha256_file(ip),
                                   "segs": i_lib.sha256_file(pre + ".seg.bin")}


def program_runs_spec(prog, T_starts, nseg, log=None):
    """Each run's bank, shared lane params and t: values at T0, the frame fitted over the run's stage times."""
    spec = []
    for T0 in T_starts:
        T1 = T0 + STEPS_SEG * 15 * nseg
        times = stage_times(T0, T1)
        fr = m1_frames(prog.cfg, times, "%s-frame-%d" % (prog.stem, int(T0)))
        fit = V.frame_fit(T0, T1, fr)
        v, where = prog.run_values(T0, fit)
        shared = {nm: v[nm] for nm in prog.lane_names if nm != "bc"}
        spec.append({"T0": T0, "nseg": nseg, "bank": prog.bank(v), "shared": shared, "values": v,
                     "t_enc": enc(prog, T0), "where": where, "fit": fit})
        if log:
            log.w("run at t = %s s: DE421 %s; frame fit over %d stage times, tc %s"
                  % (T0, " ".join("%s rec %d sub %d" % (k, w[0], w[1]) for k, w in where.items()), len(times), fit["tc"]))
    return spec


def interp_lane(prog, state, lane_vals, bankv, steps):
    """lang.run of one lane: (state, flags)."""
    g = prog.graph()
    rr = prog.lang.run(g, [state], steps, lane_params=[lane_vals], param_bits=bankv)
    return rr.states[0], int(rr.flags)


def lane_vector(prog, spec_run, init_lane):
    """The lane params as the driver writes them at a run's start: the shared ones, the lane's own from INIT."""
    out = []
    for j, nm in enumerate(prog.lane_names):
        out.append(spec_run["shared"][nm] if nm in spec_run["shared"] else init_lane[prog.nstate + j])
    return out


def mode_i1(cfg, a):
    fmts = a.formats.split(",")
    smoke = a.nlanes != 16 or a.nruns != 2
    log = i_lib.Log(cfg["logs"] if not smoke else cfg["work"], ("i1_%s" if not smoke else "i1smoke_%s") % a.system,
                    SCRIPT, [I1_CRIT], keep_dir=cfg["kept"] if not smoke else None, modules=MODULES)
    rows = V.read_seed(cfg["test_seed"])
    log.w("test seed %s sha256 %s: %d objects, T_s %s" % (os.path.basename(cfg["test_seed"]),
                                                         i_lib.sha256_file(cfg["test_seed"]), len(rows), rows[0][1]))
    lanes = [(r[0], r[1], r[2], r[3]) for r in rows[:a.nlanes]]
    T_s = Fraction(rows[0][1])
    for fmt in fmts:
        log.w("")
        log.w("== I1 %s at %s ==" % (a.system, fmt))
        if a.system.startswith("program"):
            deg = int(a.system[len("program"):] or N_PROG)
            src, info, stem = gen_system(cfg, "program", fmt, degree=deg)
        else:
            raise SystemExit("i1: system %s is in mode i1parts" % a.system)
        man = need_image(cfg, src, fmt, stem, log)
        prog = Program(cfg, src, info, man, fmt, stem)
        log.w("source %s sha256 %s; image %s.cftp sha256 %s; depth %d" % (
            os.path.relpath(src, cfg["repo"]).replace("\\", "/"), i_lib.sha256_file(src), stem,
            i_lib.sha256_file(os.path.join(cfg["img"], stem + ".cftp")), DEPTH))
        spec = program_runs_spec(prog, [T_s, T_s + 1200][:a.nruns], 2 if a.nruns == 2 else 1, log)
        init = lanes_init(prog, lanes, T_s)
        segs, marks, out, hashes = run_driver(prog, "i1-%s" % stem, spec, init, len(lanes))
        log.w("driver: runs %s init %s segments %s" % (hashes["runs"], hashes["init"], hashes["segs"]))
        for ln in out.splitlines():
            if ln.startswith("seg ") or ln.startswith("REPORT"):
                log.w("  " + ln)
        # (a), (b), (c)
        t0 = time.process_time()
        ok_a, ok_b, nmark, wrong = True, True, 0, 0
        cur = [list(init[k][:prog.nstate]) for k in range(len(lanes))]
        si = 0
        for ri, run in enumerate(spec):
            bankv = prog.bank_params(run["values"])
            for s in range(1, run["nseg"] + 1):
                r_, s_, st, lb = segs[si]
                si += 1
                if (r_, s_) != (ri, s):
                    raise SystemExit("segment order")
                t_expect = enc(prog, run["T0"] + 600 * s)
                for k in range(len(lanes)):
                    lv = lane_vector(prog, run, init[k])
                    ref, fl = interp_lane(prog, cur[k], lv, bankv, STEPS_SEG)
                    byte = lb[k]
                    if byte & 0x80:
                        nmark += 1
                        if not same(prog, st[k], ref):
                            wrong += 1
                        log.w("  mark: run %d segment %d lane %d (seed index %d); guess %s" % (
                            ri + 1, s, k, lanes[k][0], "equal" if same(prog, st[k], ref) else "WRONG"))
                        cur[k] = ref
                        continue
                    if not same(prog, st[k], ref):
                        ok_a = False
                        log.w("  (a) run %d segment %d lane %d: the state differs from lang.run's" % (ri + 1, s, k))
                    if (byte & 0xE0) or (byte & 0x1F) != (fl & 0x1F):
                        ok_a = False
                        log.w("  (a) run %d segment %d lane %d: lane byte 0x%02x, lang.run flags 0x%02x" % (ri + 1, s, k, byte, fl))
                    if st[k][0] != t_expect:
                        ok_b = False
                    cur[k] = st[k]
        log.w("lang.run: %d lane-segments of %d steps in %.1f CPU-s (process time)" % (
            len(lanes) * si, STEPS_SEG, time.process_time() - t0))
        log.check(ok_a, "I1 %s %s (a) every lane equals lang.run bit for bit, states and lane flags, 4 segments x %d lanes"
                  % (a.system, fmt, len(lanes)))
        log.check(ok_b, "I1 %s %s (b) t exact at every boundary" % (a.system, fmt))
        log.w("I1 %s %s (c) marks: %d in %d lane-segments (driver's file: %d); wrong guesses %d" % (
            a.system, fmt, nmark, len(lanes) * si, len(marks), wrong))
        log.check(nmark == len(marks), "I1 %s %s (c) every mark the lane bytes show is in the driver's marks file" % (a.system, fmt))
        # C3: GM one up, lanes 0 and 1, the first segment
        bankv = prog.bank_params(spec[0]["values"])
        gm_bits = bankv.get("gm", None)
        if gm_bits is not None:
            planted = dict(bankv)
            planted["gm"] = gm_bits + 1
            nd = 0
            for k in (0, 1):
                ref, _fl = interp_lane(prog, list(init[k][:prog.nstate]), lane_vector(prog, spec[0], init[k]), planted, STEPS_SEG)
                nd += sum(1 for x, y in zip(ref, segs[0][2][k]) if x != y)
            log.w("C3: GM's encoding 0x%x -> 0x%x; %d of %d values differ from the executor's" % (gm_bits, gm_bits + 1, nd, 2 * prog.nstate))
            log.check(nd > 0, "I1 %s %s C3 (control) the planted interpreter differs from the executor" % (a.system, fmt))
        # C4: the Moon's next sub-interval, binary64
        if fmt == "fp64":
            r0 = dict(spec[0])
            where = r0["where"]["mo"]
            nxt = prog.vals.de.coeffs(V.SER["mo"], *(prog.vals.de.locate(V.SER["mo"], where[3])[:2]))
            sh = dict(r0["shared"])
            for c in range(3):
                for i, x in enumerate(nxt[c]):
                    sh["mo%d_%d" % (c, i)] = prog.vals.b64(x)
            r0["shared"] = sh
            r0["nseg"] = 1
            segs4, _m4, _o4, _h4 = run_driver(prog, "i1-%s-c4" % stem, [r0], init, len(lanes))
            changed = sum(1 for k in range(len(lanes)) if segs4[0][2][k] != segs[0][2][k])
            log.w("C4: the Moon's coefficients of the sub-interval from %s s; %d of %d lanes changed" % (where[3], changed, len(lanes)))
            log.check(changed == len(lanes), "I1 %s %s C4 (control) every lane's state changed" % (a.system, fmt))
    sys.exit(1 if log.close() else 0)


I6_CRIT = """I6: degree 20 with the gravity tables as lane params (a measurement, no pass condition).
cftc at the pin on the generator's degree-20 program (layout bank:bands,scal;lane:grav,de,frame; binary64; 40 steps a
segment) for sw:2048, and for sw:4096 only if sw:2048 refuses it; the whole stops at 1,800 s of wall time, which bounds
its CPU time by 30 minutes (one process, one thread). Recorded: compiled or not, its time, its instructions and slots,
or its refusal by name. If it compiles within 2,048 slots: I1's criterion (a) on 4 lanes of the test seed for one
segment of 40 steps at binary64."""


def mode_i6(cfg, a):
    log = i_lib.Log(cfg["logs"], "i6", SCRIPT, [I6_CRIT], keep_dir=cfg["kept"], modules=MODULES)
    src, info, stem = gen_system(cfg, "program20", "fp64")
    log.w("source %s sha256 %s: %d params, %d lane params" % (os.path.relpath(src, cfg["repo"]).replace("\\", "/"),
                                                             i_lib.sha256_file(src), len(info["params"]), len(info["lanes"])))
    t_start = time.time()
    budget = float(a.budget)
    res = {}
    for target in ("sw:2048", "sw:4096"):
        left = budget - (time.time() - t_start)
        if left < 60:
            log.w("%s: not tried, %.0f s left of the %.0f" % (target, left, budget))
            break
        rc, man, row = compile_sys(cfg, src, "fp64", target, "%s-%s" % (stem, target.replace(":", "")), timeout=left,
                                   log=log)
        res[target] = (rc, man, row)
        log.w("%s: %s after %s s wall" % (target, row["result"][:300], row["wall_s"]))
        if rc == 0 or rc is None:
            break
    log.w("I6 result: " + "; ".join("%s %s" % (t, r[2]["result"][:120]) for t, r in res.items()))
    sys.exit(1 if log.close() else 0)


# ------------------------------------------------------------------ the part systems: inputs and values

B_MOON = Fraction(3024000)      # 2026-11-20 00:00 TDB, a Moon sub-interval boundary of DE421 (s from JD 2461329.5)
I2_SEED = 0x44454252495332      # the PRNG's seed for I2's inputs, fixed before any data


class Rng:
    """DEBRIS-E's splitmix64 and its draws (tests/m1run.c), in Python."""

    def __init__(self, seed):
        self.s = seed & 0xFFFFFFFFFFFFFFFF

    def u64(self):
        self.s = (self.s + 0x9E3779B97F4A7C15) & 0xFFFFFFFFFFFFFFFF
        z = self.s
        z = ((z ^ (z >> 30)) * 0xBF58476D1CE4E5B9) & 0xFFFFFFFFFFFFFFFF
        z = ((z ^ (z >> 27)) * 0x94D049BB133111EB) & 0xFFFFFFFFFFFFFFFF
        return z ^ (z >> 31)

    def u(self):
        return (self.u64() >> 11) * 2.0 ** -53

    def rng(self, a, b):
        return a + (b - a) * self.u()

    def dir(self, rad):
        import math
        zz = 2.0 * self.u() - 1.0
        ph = 6.283185307179586 * self.u()
        sq = math.sqrt(1.0 - zz * zz)
        return [rad * sq * math.cos(ph), rad * sq * math.sin(ph), rad * zz]


def i2_inputs(cfg, n_rand=936):
    """I2's inputs (binary64), fixed before the data: for each part, n_rand lanes by DEBRIS-E's E1 recipes and the test
    seed's 64; (d) 1,000 stage times about the Moon's boundary; (e) I3's desktop stage times and 100 blocks x 10."""
    rows = V.read_seed(cfg["test_seed"])
    T_s = Fraction(rows[0][1])
    R = Rng(I2_SEED)
    out = {}
    # (a), (b): |r| 6,600 to 8,000 km, direction uniform (E1's grav); then the seed's r
    out["central"] = [{"x": a[0], "y": a[1], "z": a[2]} for a in (R.dir(R.rng(6.6e6, 8.0e6)) for _ in range(n_rand))]
    out["central"] += [{"x": r[2][0], "y": r[2][1], "z": r[2][2]} for r in rows]
    out["grav"] = [{"rbx": a[0], "rby": a[1], "rbz": a[2]} for a in (R.dir(R.rng(6.6e6, 8.0e6)) for _ in range(n_rand))]
    out["grav"] += [{"rbx": r[2][0], "rby": r[2][1], "rbz": r[2][2]} for r in rows]
    # (c): r as (b); the Sun 1.47e11 to 1.52e11 m and the Moon 3.56e8 to 4.07e8 m away, directions uniform (E1's third);
    # the seed's 64 lanes with their own r and M1's Sun and Moon at T_s (filled by the caller from m1i kern bodies)
    td = []
    for _ in range(n_rand):
        a, sn, mn = R.dir(R.rng(6.6e6, 8.0e6)), R.dir(R.rng(1.47e11, 1.52e11)), R.dir(R.rng(3.56e8, 4.07e8))
        td.append({"x": a[0], "y": a[1], "z": a[2], "is0": sn[0], "is1": sn[1], "is2": sn[2],
                   "im0": mn[0], "im1": mn[1], "im2": mn[2]})
    out["tides"] = td
    out["tides_seed_r"] = [r[2][:3] for r in rows]
    # (f): 100 to 1,100 km up, v 7.0 to 8.0 km/s, directions uniform, bc 0.002 to 0.05 m2/kg (E1's drag)
    dr = []
    for _ in range(n_rand):
        a, v, bc = R.dir(6378136.3 + R.rng(1.0e5, 1.1e6)), R.dir(R.rng(7.0e3, 8.0e3)), R.rng(0.002, 0.05)
        dr.append({"x": a[0], "y": a[1], "z": a[2], "vx": v[0], "vy": v[1], "vz": v[2], "bc": bc})
    dr += [{"x": r[2][0], "y": r[2][1], "z": r[2][2], "vx": r[2][3], "vy": r[2][4], "vz": r[2][5], "bc": r[3]} for r in rows]
    out["drag"] = dr
    # (d): 500 stage times in [B - 2 d, B), 499 in (B, B + 2 d], and B itself; multiples of 7.5 s
    ts = []
    for _ in range(500):
        ts.append(B_MOON - Fraction(15, 2) * (1 + int(R.u() * 23039)))
    for _ in range(499):
        ts.append(B_MOON + Fraction(15, 2) * (1 + int(R.u() * 23039)))
    ts.append(B_MOON)
    out["bodies"] = [{"t": t} for t in ts]
    # (e): every stage time of I3's desktop runs (2 hours from DEBRIS-H's T_s, each run its own block), then 100 hour
    # blocks across the frame table's window, 10 stage times in each
    srows_t = Fraction(V.read_seed(cfg["seed"])[0][1])
    fe = []
    for b in range(2):
        T0 = srows_t + 3600 * b
        for t in stage_times(T0, T0 + 3600):
            fe.append({"t": t, "block": (T0, T0 + 3600)})
    ft = V.read_ftab(cfg["frame_table"])
    lo = int((Fraction(ft["t0"]) + 3 * Fraction(ft["h"])) / 3600) + 1
    hi = int((Fraction(ft["t0"]) + (ft["nk"] - 4) * Fraction(ft["h"])) / 3600) - 2
    for _ in range(100):
        T0 = Fraction(3600 * (lo + int(R.u() * (hi - lo))))
        for _k in range(10):
            fe.append({"t": T0 + Fraction(15, 2) * int(R.u() * 481), "block": (T0, T0 + 3600)})
    out["frame"] = fe
    out["_T_s"] = T_s
    return out


def part_values(prog, part, inp, fits=None, de_cache=None):
    """A part lane's lane params (name -> encoding): its inputs and its data."""
    vv = prog.vals
    d = {}
    for k, x in inp.items():
        if k != "block":
            d[k] = enc(prog, Fraction(x))
    if part in ("central", "tides", "grav", "drag"):
        for nm in prog.lane_names:
            if nm not in d:
                d[nm] = vv.v[nm]
    elif part == "bodies":
        key = inp["t"]
        if de_cache is not None and key in de_cache:
            de = de_cache[key]
        else:
            de, _w = vv.de_block(inp["t"])
            if de_cache is not None:
                de_cache[key] = de
        d.update(de)
        d["fem"], d["km"] = vv.v["fem"], vv.v["km"]
    elif part == "frame":
        d.update(vv.frame_block(fits[inp["block"]]))
    missing = [nm for nm in prog.lane_names if nm not in d]
    if missing:
        raise SystemExit("part %s: no value for %s" % (part, missing[:5]))
    return d


def part_program(cfg, part, fmt, log):
    src, info, stem = gen_system(cfg, part, fmt)
    man = need_image(cfg, src, fmt, stem, log)
    prog = Program(cfg, src, info, man, fmt, stem)
    log.w("part %s %s: source %s sha256 %s; image sha256 %s; %d lane params, %d outputs" % (
        part, fmt, os.path.relpath(src, cfg["repo"]).replace("\\", "/"), i_lib.sha256_file(src),
        i_lib.sha256_file(os.path.join(cfg["img"], stem + ".cftp")), len(prog.lane_names), len(info["state"])))
    return prog


def frame_fits(cfg, blocks, tag):
    """The frame's fit for each block (T0, T1): M1's frame at the block's stage times, fitted exactly."""
    times = sorted(set(t for (T0, T1) in blocks for t in stage_times(T0, T1)))
    fr = m1_frames(cfg, times, tag)
    return {b: V.frame_fit(b[0], b[1], fr) for b in blocks}, fr


def part_init(prog, lane_vals):
    return [[0] * prog.nstate + [lv[nm] for nm in prog.lane_names] for lv in lane_vals]


def part_run(prog, tag, lane_vals, nruns=1, nseg=1):
    init = part_init(prog, lane_vals)
    spec = [{"nseg": nseg, "bank": prog.base_bank, "shared": {}, "t_enc": None} for _ in range(nruns)]
    return run_driver(prog, tag, spec, init, len(lane_vals)) + (init,)


def m1_bodies_at(cfg, kind, times, tag):
    """M1's geocentric Sun and Moon (kern bodies) at the times, as binary64 floats when the kind is native64."""
    ip = os.path.join(cfg["work"], tag + ".in")
    op = os.path.join(cfg["work"], tag + ".out")
    with open(ip, "w", newline="\n") as f:
        for i, t in enumerate(times):
            f.write("%d %016x\n" % (i, struct.unpack("<Q", struct.pack("<d", float(t)))[0]))
    r = subprocess.run([exe(cfg, "m1i"), "kern", "bodies", kind, "--table", cfg["frame_table"], "--in", ip, "--out", op],
                       capture_output=True, text=True, env=m1env(cfg))
    if r.returncode:
        raise SystemExit("m1i kern bodies: %s" % r.stderr)
    out = []
    for raw in open(op, "rb"):
        line = raw.decode("ascii")
        if line.startswith("#"):
            continue
        w = line.split()
        out.append([struct.unpack("<d", struct.pack("<Q", int(x, 16)))[0] for x in w[1:7]])
    return out


def seed_tides(cfg, inp):
    """The seed's 64 tide lanes: their r, and M1's Sun and Moon at T_s (native64's binary64 values)."""
    sm = m1_bodies_at(cfg, "native64", [inp["_T_s"]], "i2-bodies-Ts")[0]
    for r in inp["tides_seed_r"]:
        inp["tides"].append({"x": r[0], "y": r[1], "z": r[2], "is0": sm[0], "is1": sm[1], "is2": sm[2],
                             "im0": sm[3], "im1": sm[4], "im2": sm[5]})
    del inp["tides_seed_r"]


I1P_CRIT = """I1 (part systems): each part system of the program (degree 7: central, grav, tides, bodies, frame, drag; maps
whose inputs and data are lane params) against lang.run, at binary32, binary64, binary128 and binary256: 16 lanes of I2's
inputs (the test seed's first 16 for central, grav, tides and drag; the first 16 stage times for bodies and frame), two
runs of two segments of 40 steps, every lane param rewritten by the driver at each run's start; criterion (a) of I1
(states bit for bit by the NaN rule, lane bytes [7:5] clear and [4:0] the definition's flags; a marked lane replayed,
its guess counted)."""


def mode_i1parts(cfg, a):
    fmts = a.formats.split(",")
    parts = a.parts.split(",")
    log = i_lib.Log(cfg["logs"], "i1_parts", SCRIPT, [I1P_CRIT], keep_dir=cfg["kept"], modules=MODULES)
    inp = i2_inputs(cfg)
    seed_tides(cfg, inp)
    fits = None
    for part in parts:
        lanes = inp[part][-64:][:16] if part not in ("bodies", "frame") else inp[part][:16]
        if part == "frame":
            fits, _fr = frame_fits(cfg, sorted(set(x["block"] for x in lanes)), "i1p-frame")
        for fmt in fmts:
            prog = part_program(cfg, part, fmt, log)
            lv = [part_values(prog, part, x, fits) for x in lanes]
            segs, marks, out, hashes, init = part_run(prog, "i1p-%s" % prog.stem, lv, nruns=2, nseg=2)
            log.w("driver: runs %s init %s segments %s" % (hashes["runs"], hashes["init"], hashes["segs"]))
            ok, nmark, wrong = True, 0, 0
            cur = [list(r[:prog.nstate]) for r in init]
            for (r_, s_, st, lb) in segs:
                for k in range(len(lanes)):
                    ref, fl = interp_lane(prog, cur[k], init[k][prog.nstate:], {}, STEPS_SEG)
                    if lb[k] & 0x80:
                        nmark += 1
                        wrong += 0 if same(prog, st[k], ref) else 1
                        cur[k] = ref
                        continue
                    if not same(prog, st[k], ref) or (lb[k] & 0xE0) or (lb[k] & 0x1F) != (fl & 0x1F):
                        ok = False
                        log.w("  run %d segment %d lane %d: differs (byte 0x%02x, flags 0x%02x)" % (r_ + 1, s_, k, lb[k], fl))
                    cur[k] = st[k]
            log.check(ok and nmark == len(marks), "I1 part %s %s (a): %d lane-segments equal lang.run, marks %d (file %d), "
                      "wrong guesses %d" % (part, fmt, len(segs) * len(lanes), nmark, len(marks), wrong))
    sys.exit(1 if log.close() else 0)


M1_IN = {"central": ["x", "y", "z"], "grav": ["rbx", "rby", "rbz"],
         "tides": ["x", "y", "z", "is0", "is1", "is2", "im0", "im1", "im2"], "bodies": ["t"], "frame": ["t"],
         "drag": ["x", "y", "z", "vx", "vy", "vz", "bc"]}
PART_LETTER = {"central": "a", "grav": "b", "tides": "c", "bodies": "d", "frame": "e", "drag": "f"}


def hex64(x):
    return "%016x" % struct.unpack("<Q", struct.pack("<d", float(x)))[0]


def m1_kern(cfg, part, kind, lanes, tag, om=None):
    """M1's kernel (m1i kern) at the lanes' inputs: per lane, its outputs' encodings in the kind; and the files' hashes."""
    ip = os.path.join(cfg["work"], tag + ".in")
    op = os.path.join(cfg["work"], tag + ".out")
    with open(ip, "w", newline="\n") as f:
        for i, ln in enumerate(lanes):
            f.write("%d %s\n" % (i, " ".join(hex64(ln[k]) for k in M1_IN[part])))
    cmd = [exe(cfg, "m1i"), "kern", part, kind, "--table", cfg["frame_table"], "--in", ip, "--out", op,
           "--nmax", str(N_PROG)]
    if om is not None:
        cmd += ["--om"] + [hex64(x) for x in om]
    r = subprocess.run(cmd, capture_output=True, text=True, env=m1env(cfg))
    if r.returncode:
        raise SystemExit("m1i kern %s %s: %s" % (part, kind, r.stderr))
    out, model = [], ""
    for raw in open(op, "rb"):
        line = raw.decode("ascii")
        if line.startswith("# model"):
            model = line[2:].strip()
        if line.startswith("#"):
            continue
        out.append([int(x, 16) for x in line.split()[1:]])
    return out, i_lib.sha256_file(ip), i_lib.sha256_file(op), model


class Cmp:
    """The comparison of one part: program (format fmt) against M1 (the matching kind), component by component."""

    def __init__(self, prog, m1fmt):
        self.prog = prog
        sf, C, F = V.golden(os.path.join(prog.cfg["fp256"], "python"))
        self.C, self.sf, self.fp, self.fm = C, sf, F[prog.fmt], F[m1fmt]

    def vals(self, fm, bits):
        return None if self.sf.is_nan(fm, bits) else self.C.value_of(fm, bits)

    def diffs(self, P, M):
        """[(lane, component, |p - m| or None for a NaN pair, |m|)]; a NaN on one side alone is an infinite difference."""
        out = []
        for i, (pl, ml) in enumerate(zip(P, M)):
            for c, (pb, mb) in enumerate(zip(pl, ml)):
                pv, mv = self.vals(self.fp, pb), self.vals(self.fm, mb)
                if pv is None and mv is None:
                    out.append((i, c, None, Fraction(0)))
                elif pv is None or mv is None:
                    out.append((i, c, float("inf"), Fraction(0) if mv is None else abs(mv)))
                else:
                    out.append((i, c, abs(pv - mv), abs(mv)))
        return out


def rel_check(dl, ncomp, k):
    """|p - m| <= 2^-k x the component's largest |m| over the inputs: (ok, worst share, count over)."""
    big = [Fraction(0)] * ncomp
    for (_i, c, _d, a) in dl:
        big[c] = max(big[c], a)
    worst, over = 0.0, 0
    for (_i, c, d, _a) in dl:
        if d is None:
            continue
        tol = big[c] / Fraction(2) ** k
        if d == float("inf") or d > tol:
            over += 1
        if tol > 0 and d != float("inf"):
            worst = max(worst, float(d / tol))
        elif d == float("inf"):
            worst = float("inf")
    return over == 0, worst, over


def abs_check(dl, tol_of_c):
    worst, over = 0.0, 0
    for (_i, c, d, _a) in dl:
        if d is None:
            continue
        t = tol_of_c(c)
        if d == float("inf") or d > t:
            over += 1
        worst = max(worst, float("inf") if d == float("inf") else float(d / t))
    return over == 0, worst, over


def ulps64(prog, P, M):
    """binary64 differences in ulps of M1's value: (median, largest, count nonzero)."""
    import math
    us = []
    for pl, ml in zip(P, M):
        for pb, mb in zip(pl, ml):
            p = struct.unpack("<d", struct.pack("<Q", pb))[0]
            m = struct.unpack("<d", struct.pack("<Q", mb))[0]
            if math.isnan(p) and math.isnan(m):
                us.append(0.0)
                continue
            if m == 0:
                us.append(0.0 if p == 0 else float("inf"))
                continue
            e = math.frexp(abs(m))[1]
            us.append(abs(p - m) / 2.0 ** (e - 53))
    us.sort()
    return (us[len(us) // 2] if us else 0.0), (us[-1] if us else 0.0), sum(1 for u in us if u)


I2_CRIT = """I2: part by part, against M1's kernels (src/ at commit 1646c96, m1i kern; M1's model switches: central, degrees
2..7, the Sun, the Moon, drag through 28 bands, frame = 1 with DEBRIS-H's table; no radiation pressure).
Inputs (fixed in this script, PRNG seed I2_SEED): 936 lanes by DEBRIS-E's E1 recipes and the test seed's 64, for (a),
(b), (c) and (f); (d) 1,000 stage times: 500 in [B - 2 d, B), 499 in (B, B + 2 d], and B = 2026-11-20 00:00 TDB itself,
where the Moon's sub-interval changes and M1 takes the later one; (e) every stage time of I3's desktop runs (2 one-hour
blocks from DEBRIS-H's T_s) and 100 one-hour blocks drawn across the frame table's window, 10 stage times each, each
block its own run's fit. Each part by its part system on the executor (the images I1 holds, one segment) at binary64,
binary128 and binary256, and by M1's kernel at cft64, cft128 and cft256, with native64 beside.
Criteria, (a) to (d) and (f): at binary256, |program - M1| <= 2^-200 x the component's largest |M1| over the inputs; at
binary128 the same with 2^-80. At binary64: a measurement in ulps of M1's value (median and largest), against cft64 and
against native64.
Criterion (e) at binary256: every element of M within 1e-12 of M1's frame_at, and Omega within 1e-14 rad/s, at every
stage time listed. (At binary64 and binary128 the same differences are reported.)
Controls, each at binary256 unless named, each on the stated lanes, each of which must FAIL the criterion of its part:
 C5 c2_2 (C22) scaled by (1 + 2^-100) fails (b) (first 100 lanes);
 C6 gm scaled by (1 + 2^-100) fails (a) (first 100 lanes);
 C7 gmm (the Moon's GM) scaled by (1 + 2^-100) fails (c) (first 100 lanes);
 C8 each lane's largest Moon coefficient scaled by (1 + 2^-100) fails (d) (first 100 lanes);
 C9 rho0 of the band holding the most (f) inputs (at least 10, asserted) scaled by (1 + 2^-100) fails (f) on that
    band's inputs;
 C10 every C and S taken through binary64 (and P1, PZ0 from them) fails (b) at binary256 and at binary128 (first 100);
 C11 the frame's block of the hour after fails (e) (the lanes of the 100 drawn blocks).
 Before the data, each plant's movement is estimated from the inputs' ranges and the constants, and the script asserts
 that it exceeds its tolerance by at least 2^20."""


def scaled(prog, bits, k=100):
    v = prog.vals.value(bits)
    return prog.vals.q(v * (1 + Fraction(1, 2 ** k)))


def mode_i2(cfg, a):
    log = i_lib.Log(cfg["logs"], "i2", SCRIPT, [I2_CRIT], keep_dir=cfg["kept"], modules=MODULES)
    inp = i2_inputs(cfg)
    seed_tides(cfg, inp)
    blocks = sorted(set(x["block"] for x in inp["frame"]))
    fits, _fr = frame_fits(cfg, blocks + [(b[0] + 3600, b[1] + 3600) for b in blocks], "i2-frame")
    T_s = inp["_T_s"]
    frT = m1_frames(cfg, [T_s], "i2-om")
    om = [float(frT[T_s][9 + e]) for e in range(3)]
    for ln in inp["drag"]:
        ln["io0"], ln["io1"], ln["io2"] = om
    h_in = i_lib.sha256_bytes(json.dumps({k: [{kk: str(vv) for kk, vv in x.items()} for x in v]
                                          for k, v in inp.items() if not k.startswith("_")}, sort_keys=True).encode())
    log.w("inputs: SHA-256 %s (all parts' lanes, as text); Omega for (f) M1's at T_s %s (binary64): %s" % (
        h_in, T_s, " ".join(hex64(x) for x in om)))
    # --- the margins, before the data (estimates from the inputs' ranges and the constants)
    GM, GMM, RE = 3.986004415e14, 4.9028e12, 6.3781363e6
    est = {"C5": (2 ** -100 * 3 * GM / 8e6 ** 2 * (RE / 8e6) ** 2 * 2.4e-6, 2 ** -200 * 1.5 * 1.0826e-3 * GM / 6.6e6 ** 2),
           "C6": (2 ** -100 * GM / 8e6 ** 2, 2 ** -200 * GM / 6.6e6 ** 2),
           "C7": (2 ** -100 * GMM * 6.6e6 / 4.07e8 ** 3, 2 ** -200 * 2 * GMM * 8e6 / 3.56e8 ** 3),
           "C8": (2 ** -100 * 1e7, 2 ** -200 * 1.52e11),
           "C9": (2 ** -100 * 0.002 * 3e-15 * 7e3 ** 2, 2 ** -200 * 0.05 * 1.3 * 9e3 ** 2),
           "C10b256": (2 ** -60 * 1.0826e-3 * GM / 8e6 ** 2 * 1e-3, 2 ** -200 * 1.5 * 1.0826e-3 * GM / 6.6e6 ** 2),
           "C10b128": (2 ** -60 * 1.0826e-3 * GM / 8e6 ** 2 * 1e-3, 2 ** -80 * 1.5 * 1.0826e-3 * GM / 6.6e6 ** 2),
           "C11": (1e-3, 1e-12)}
    for k, (mv, tol) in sorted(est.items()):
        log.check(mv > 2 ** 20 * tol, "margin %s: estimated movement %.3e against tolerance %.3e (ratio %.2e)" % (k, mv, tol, mv / tol))
    results = {}
    pmeta = {}
    for part in ("central", "grav", "tides", "bodies", "frame", "drag"):
        lanes = inp[part]
        for fmt, kind in (("fp64", "cft64"), ("fp128", "cft128"), ("fp256", "cft256")):
            prog = part_program(cfg, part, fmt, log)
            dec = {}
            lv = [part_values(prog, part, x, fits, dec) for x in lanes]
            segs, _marks, out, hashes, _init = part_run(prog, "i2-%s" % prog.stem, lv)
            P = segs[0][2]
            nmk = sum(1 for b in segs[0][3] if b & 0x80)
            M, hi, ho, model = m1_kern(cfg, part, kind, lanes, "i2-m1-%s-%s" % (part, kind), om if part == "drag" else None)
            pmeta[(part, fmt)] = (prog, lv)
            results[(part, fmt)] = (P, M)
            log.w("(%s) %s: program %s image %s depth %d, %d lanes, marks %d; M1 %s (%s), inputs %s, outputs %s" % (
                PART_LETTER[part], part, fmt, i_lib.sha256_file(os.path.join(cfg["img"], prog.stem + ".cftp")), DEPTH,
                len(lanes), nmk, kind, model, hi, ho))
            cm = Cmp(prog, fmt)
            dl = cm.diffs(P, M)
            ncomp = len(P[0])
            if part == "frame":
                ok, worst, over = abs_check(dl, lambda c: Fraction(1, 10 ** 12) if c < 9 else Fraction(1, 10 ** 14))
                mx = max((d for (_i, c, d, _a) in dl if d is not None and c < 9), default=0)
                mo = max((d for (_i, c, d, _a) in dl if d is not None and c >= 9), default=0)
                log.w("  (e) %s: largest |M - M1| %.3e, |Omega - M1| %.3e rad/s; share of the bound %.3f; over %d" % (
                    fmt, float(mx), float(mo), worst, over))
                if fmt == "fp256":
                    log.check(ok, "I2 (e) binary256: M within 1e-12 and Omega within 1e-14 rad/s of M1's frame_at at "
                              "all %d stage times" % len(lanes))
            elif fmt in ("fp256", "fp128"):
                k = 200 if fmt == "fp256" else 80
                ok, worst, over = rel_check(dl, ncomp, k)
                nz = sum(1 for (_i, _c, d, _a) in dl if d)
                log.check(ok, "I2 (%s) %s %s: |program - M1| <= 2^-%d of each component's largest |M1|; largest share "
                          "%.3g, values differing %d of %d" % (PART_LETTER[part], part, fmt, k, worst, nz, len(dl)))
            else:
                med, big, nz = ulps64(prog, P, M)
                Mn, _hi2, _ho2, _m2 = m1_kern(cfg, part, "native64", lanes, "i2-m1-%s-native64" % part,
                                             om if part == "drag" else None)
                med2, big2, nz2 = ulps64(prog, P, Mn)
                log.w("  (%s) %s binary64: against cft64, ulps median %.3g largest %.3g (%d of %d differ); against "
                      "native64, median %.3g largest %.3g (%d differ)" % (PART_LETTER[part], part, med, big, nz,
                                                                         len(P) * ncomp, med2, big2, nz2))
    # --- the controls
    def ctl(name, part, fmt, lanes_idx, plant, check):
        prog, lv = pmeta[(part, fmt)]
        P0, M0 = results[(part, fmt)]
        lv2 = [dict(lv[i]) for i in lanes_idx]
        for d in lv2:
            plant(prog, d)
        segs, _m, _o, _h, _i = part_run(prog, "i2-%s-%s" % (name, prog.stem), lv2)
        P = segs[0][2]
        M = [M0[i] for i in lanes_idx]
        dl = Cmp(prog, fmt).diffs(P, M)
        ok = check(dl, len(P[0]))
        log.check(not ok, "%s (control) %s %s on %d lanes: the criterion FAILS, as it must" % (name, part, fmt, len(lanes_idx)))

    first = list(range(100))
    relchk = lambda k: (lambda dl, nc: rel_check(dl, nc, k)[0])

    def p_c22(prog, d):
        d["c2_2"] = scaled(prog, d["c2_2"])
    ctl("C5", "grav", "fp256", first, p_c22, relchk(200))

    def p_gm(prog, d):
        d["gm"] = scaled(prog, d["gm"])
    ctl("C6", "central", "fp256", first, p_gm, relchk(200))

    def p_gmm(prog, d):
        d["gmm"] = scaled(prog, d["gmm"])
    ctl("C7", "tides", "fp256", first, p_gmm, relchk(200))

    def p_moon(prog, d):
        names = ["mo%d_%d" % (c, i) for c in range(3) for i in range(prog.vals.de.ipt[V.SER["mo"]][1])]
        big = max(names, key=lambda nm: abs(prog.vals.value(d[nm])))
        d[big] = scaled(prog, d[big])
    ctl("C8", "bodies", "fp256", first, p_moon, relchk(200))

    prog_f, lv_f = pmeta[("drag", "fp256")]
    rr = [Fraction(math_hyp(x)) - prog_f.vals.value(prog_f.vals.v["rearth"]) for x in inp["drag"]]
    bh = [prog_f.vals.value(prog_f.vals.v["bh%d" % b]) for b in range(28)]
    band = [max(b for b in range(28) if bh[b] <= h) if h >= 0 else 0 for h in rr]
    counts = {}
    for b in band:
        counts[b] = counts.get(b, 0) + 1
    bstar = max(sorted(counts), key=lambda b: counts[b])
    log.w("C9: band %d holds the most (f) inputs, %d (by the inputs' heights above rearth)" % (bstar, counts[bstar]))
    log.check(counts[bstar] >= 10, "C9's band holds at least 10 inputs")

    def p_band(prog, d):
        d["br%d" % bstar] = scaled(prog, d["br%d" % bstar])
    ctl("C9", "drag", "fp256", [i for i, b in enumerate(band) if b == bstar], p_band, relchk(200))

    for fmt, k in (("fp256", 200), ("fp128", 80)):
        prog_g, _lv = pmeta[("grav", fmt)]
        via64 = prog_g.vals.grav(prog_g.vals.Cs, prog_g.vals.Ss,
                                 conv=lambda s_: prog_g.vals.q(Fraction(float(V.dec(s_)))))

        def p_64(prog, d, via64=via64):
            for nm, x in via64.items():
                if nm[0] in "cs" and nm[1].isdigit() or nm.startswith("p1_") or nm.startswith("pz_"):
                    d[nm] = x
        ctl("C10-%s" % fmt, "grav", fmt, first, p_64, relchk(k))

    s0 = Fraction(V.read_seed(cfg["seed"])[0][1])
    i3blocks = {(s0, s0 + 3600), (s0 + 3600, s0 + 7200)}
    nxt = {b: fits[(b[0] + 3600, b[1] + 3600)] for b in blocks}
    idx11 = [i for i, x in enumerate(inp["frame"]) if x["block"] not in i3blocks]
    prog_e, lv_e = pmeta[("frame", "fp256")]
    lv11 = []
    for i in idx11:
        d = dict(lv_e[i])
        d.update(prog_e.vals.frame_block(nxt[inp["frame"][i]["block"]]))
        lv11.append(d)
    segs, _m, _o, _h, _i = part_run(prog_e, "i2-C11-%s" % prog_e.stem, lv11)
    dl = Cmp(prog_e, "fp256").diffs(segs[0][2], [results[("frame", "fp256")][1][i] for i in idx11])
    ok, _w, _o2 = abs_check(dl, lambda c: Fraction(1, 10 ** 12) if c < 9 else Fraction(1, 10 ** 14))
    log.check(not ok, "C11 (control) frame fp256 on %d lanes, the next hour's block: the criterion FAILS, as it must" % len(idx11))
    sys.exit(1 if log.close() else 0)


def math_hyp(x):
    import math
    return math.sqrt(x["x"] * x["x"] + x["y"] * x["y"] + x["z"] * x["z"])


# ------------------------------------------------------------------ I3

I3_DRAW_SEED = 20261123          # the draw's seed, fixed before the data
BANDS_KM = ((None, 400), (400, 600), (600, 800), (800, None))
I3_EXCLUDE = {1595: "E0003: M1 (DEBRIS-H's A256) decayed it at step 1396, 5.8 h after T_s; a lane that re-enters "
                    "leaves the model's domain, and I3's tolerance bounds rounding and the frame, not a re-entry"}


def perigee_km(state):
    """The osculating two-body perigee height above 6,378.137 km, from a binary64 state (GM of EIGEN-6C4)."""
    import math
    mu = 3.986004415e14
    r, v = state[:3], state[3:]
    rn = math.sqrt(sum(x * x for x in r))
    v2 = sum(x * x for x in v)
    h = [r[1] * v[2] - r[2] * v[1], r[2] * v[0] - r[0] * v[2], r[0] * v[1] - r[1] * v[0]]
    vxh = [v[1] * h[2] - v[2] * h[1], v[2] * h[0] - v[0] * h[2], v[0] * h[1] - v[1] * h[0]]
    e = [vxh[i] / mu - r[i] / rn for i in range(3)]
    en = math.sqrt(sum(x * x for x in e))
    a = 1.0 / (2.0 / rn - v2 / mu)
    return (a * (1.0 - en) - 6378137.0) / 1000.0


def band_of(hp):
    for b, (lo, hi) in enumerate(BANDS_KM):
        if (lo is None or hp >= lo) and (hi is None or hp < hi):
            return b
    raise SystemExit("no band")


def i3_sample(cfg, log=None):
    """Decision 6: 64 of DEBRIS-H's seed, 16 a perigee band (under 400, 400 to 600, 600 to 800, 800 km and over), drawn
    by random.Random(I3_DRAW_SEED) from each band's eligible objects in index order; a band short of 16 gives all it has
    and the rest come from the nearest band with objects to spare (the lower band on a tie). Before the draw: the
    objects of I3_EXCLUDE, and every object whose state and bc equal a lower index's bit for bit (docked vehicles share
    element sets, DEBRIS-F's narrowing 11), are set aside."""
    import random
    rows = V.read_seed(cfg["seed"])
    seen, dup = {}, set()
    for r in rows:
        key = (tuple(r[2]), r[3])
        if key in seen:
            dup.add(r[0])
        else:
            seen[key] = r[0]
    elig = [[] for _ in BANDS_KM]
    for r in rows:
        if r[0] in I3_EXCLUDE or r[0] in dup:
            continue
        elig[band_of(perigee_km(r[2]))].append(r[0])
    R = random.Random(I3_DRAW_SEED)
    take = [min(16, len(e)) for e in elig]
    short = 64 - sum(take)
    while short > 0:
        for b in range(len(BANDS_KM)):
            if take[b] < 16:
                for dist in range(1, len(BANDS_KM)):
                    cands = [x for x in (b - dist, b + dist) if 0 <= x < len(BANDS_KM) and len(elig[x]) > take[x]]
                    if cands:
                        take[cands[0]] += 1
                        short -= 1
                        break
                break
        else:
            break
    picks = [sorted(R.sample(elig[b], take[b])) for b in range(len(BANDS_KM))]
    if log:
        log.w("I3 sample: seed %s sha256 %s, %d objects; set aside: %d duplicates of a lower index, and %s" % (
            os.path.basename(cfg["seed"]), i_lib.sha256_file(cfg["seed"]), len(rows), len(dup),
            "; ".join("index %d (%s)" % kv for kv in sorted(I3_EXCLUDE.items()))))
        log.w("I3 sample: eligible by band %s; drawn %s (random.Random(%d))" % (
            [len(e) for e in elig], take, I3_DRAW_SEED))
    return picks, rows


def build_program_runs(prog, T0, nruns, nseg, rows_sel, tag, frame_shift=None):
    """The runs file (hour blocks from T0, each its own DE421 sub-interval and frame fit) and the INIT file of the
    selected seed rows. frame_shift: {run index: block offset} gives that run another block's fit (C13)."""
    T_starts = [T0 + 3600 * k for k in range(nruns)]
    spec = program_runs_spec(prog, T_starts, nseg)
    if frame_shift:
        for ri, off in frame_shift.items():
            src = spec[ri + off]
            v = dict(spec[ri]["values"])
            v.update(prog.vals.frame_block(src["fit"]))
            spec[ri]["shared"] = {nm: v[nm] for nm in prog.lane_names if nm != "bc"}
            spec[ri]["bank"] = prog.bank(v)
    init = lanes_init(prog, [(r[0], r[1], r[2], r[3]) for r in rows_sel], T0)
    cfg = prog.cfg
    shared_names = [nm for nm in prog.lane_names if nm in spec[0]["shared"]]
    shared = [prog.scr_slot[nm] for nm in shared_names]
    runs = [(r["nseg"], prog.scr_slot["t"], r["t_enc"], r["bank"], [r["shared"][nm] for nm in shared_names]) for r in spec]
    rp = os.path.join(cfg["work"], tag + ".runs.bin")
    ip = os.path.join(cfg["work"], tag + ".init.bin")
    V.write_runs(rp, prog.esz, prog.nconst, prog.nscr, prog.nstate, shared, runs)
    V.write_init(ip, prog.esz, init)
    return rp, ip, spec, init


def drive(cfg, prog, rp, ip, n, prefix):
    r = subprocess.run([exe(cfg, "i_run"), "run", "--image", os.path.join(cfg["img"], prog.stem + ".cftp"), "--runs", rp,
                        "--init", ip, "--lanes", str(n), "--depth", str(DEPTH), "--out", prefix],
                       capture_output=True, text=True)
    if r.returncode:
        raise SystemExit("i_run: exit %d: %s" % (r.returncode, r.stderr))
    return r.stdout


def m1_traj(cfg, kind, idx, nsteps, out, extra=()):
    cmd = [exe(cfg, "m1i"), "traj", kind, "--table", cfg["frame_table"], "--seed",
           "%s:%s" % (cfg["seed"], i_lib.sha256_file(cfg["seed"])), "--idx", ",".join(str(i) for i in idx),
           "--nsteps", str(nsteps), "--every", "40", "--out", out] + list(extra)
    r = subprocess.run(cmd, capture_output=True, text=True, env=m1env(cfg))
    if r.returncode:
        raise SystemExit("m1i traj %s: %s" % (kind, r.stderr))


I3D_CRIT = """I3 on the desktop (a functional test; the full run is the box's): 8 of I3's 64 (the first 2 drawn in each band),
2 hours from DEBRIS-H's T_s (480 steps, two one-hour runs of 6 segments); the program (degree 7, 28 bands) at binary64,
binary128 and binary256 against M1 with the program's forces (m1i --model prog: central, degrees 2..7, Sun, Moon,
28-band drag, frame = 1, srp 0) at native64, cft64, cft128 and cft256, from the seed's binary64 states at T_s.
Criterion (i_analyze.py's): |program at p - M1 at the matching kind| <= 64 n 2^-p S + T_frame at every boundary and
object, S = 7e6 m and T_frame = 1e-3 m for positions, S = 8e3 m/s and T_frame = 1e-6 m/s for velocities; binary64 /
native64 reported beside; t equals M1's host stage time at every boundary, exactly. Every mark is replayed by lang.run
before its state is used; a criterion is evaluated only on unmarked or replayed-equal states.
C12 (control): M1 at cft256 with degree 6 against the program at binary256 must FAIL the criterion somewhere.
C13 (control): the program at binary256 with its second run given the frame's block of the hour before must FAIL.
Measurements: the share of each tolerance used (median and largest); binary64 against binary256, position, at 1 and
2 hours (the box's run gives 1, 6 and 24); the model gap (M1 at native64 and cft64: prog against full, and one force
at a time: degree 7 against 20 with srp off, srp off against on at degree 7), position differences at 1 and 2 hours."""


def mode_i3d(cfg, a):
    import i_analyze as A
    log = i_lib.Log(cfg["logs"], "i3_desktop", SCRIPT, [I3D_CRIT], keep_dir=cfg["kept"],
                    modules=MODULES + [os.path.join(HERE, "i_analyze.py")])
    picks, rows = i3_sample(cfg, log)
    sel = [p[0] for p in picks] + [p[1] for p in picks]
    sel = sorted(sel)
    log.w("desktop objects: 8 (2 a band), seed indices %s" % sel)
    rows_sel = [rows[i] for i in sel]
    T0 = Fraction(rows[0][1])
    nsteps = 480
    steps = list(range(40, nsteps + 1, 40))
    progs = {}
    precs = {}
    for fmt in ("fp64", "fp128", "fp256"):
        src, info, stem = gen_system(cfg, "program", fmt)
        man = need_image(cfg, src, fmt, stem, log)
        prog = Program(cfg, src, info, man, fmt, stem)
        progs[fmt] = prog
        rp, ip, spec, init = build_program_runs(prog, T0, 2, 6, rows_sel, "i3d-%s" % stem)
        pre = os.path.join(cfg["work"], "i3d-%s" % stem)
        out = drive(cfg, prog, rp, ip, len(sel), pre)
        rec, lb = A.read_prog_segs(pre + ".seg.bin", sel, prog.nstate, prog.esz)
        marks = V.read_marks(pre + ".marks.bin", prog.nscr, prog.nstate, prog.esz)
        log.w("program %s: image %s, runs %s, init %s, segments %s; marks %d" % (
            fmt, i_lib.sha256_file(os.path.join(cfg["img"], stem + ".cftp")), i_lib.sha256_file(rp),
            i_lib.sha256_file(ip), i_lib.sha256_file(pre + ".seg.bin"), len(marks)))
        for (r_, s_, l_, pre_s, post_s) in marks:
            g = prog.graph()
            run = spec[r_]
            ref, _fl = interp_lane(prog, pre_s[:prog.nstate], pre_s[prog.nstate:], prog.bank_params(run["values"]), 40)
            eq = same(prog, ref, post_s)
            log.w("  mark run %d seg %d lane %d (index %d): replayed, %s" % (r_ + 1, s_, l_, sel[l_], "equal" if eq else "DIFFERS"))
            if not eq:
                raise SystemExit("a replay differs: the lane's later states are void; the redo is not built for the desktop test")
        precs[fmt] = rec
    m1recs = {}
    for kind in ("native64", "cft64", "cft128", "cft256"):
        op = os.path.join(cfg["work"], "i3d-m1-%s.txt" % kind)
        m1_traj(cfg, kind, sel, nsteps, op, ["--model", "prog"])
        m1recs[kind], _k = A.read_m1_traj(op)
        log.w("M1 %s --model prog: output sha256 %s" % (kind, i_lib.sha256_file(op)))
    for fmt in ("fp64", "fp128", "fp256"):
        for kind in ([A.KIND_OF[fmt]] + (["native64"] if fmt == "fp64" else [])):
            fails, shares, tbad, nanp = A.i3_compare(precs[fmt], fmt, m1recs[kind], A.FMT_OF_KIND[kind], steps, sel, A.P_OF[fmt])
            med, big, n = A.stats(shares)
            text = "I3 desktop %s against %s: %d values at %d boundaries x %d objects; share of the tolerance median %.3g, largest %.3g; t mismatches %d; NaN pairs %d; over %d" % (
                fmt, kind, n, len(steps), len(sel), med, big, len(tbad), nanp, len(fails))
            if kind == A.KIND_OF[fmt]:
                log.check(not fails and not tbad, text)
            else:
                log.w("(beside) " + text)
    # binary64 against binary256
    for n in (240, 480):
        d = [A.pos_diff(precs["fp64"][(i, n)][1:4], "fp64", precs["fp256"][(i, n)][1:4], "fp256") for i in sel]
        med, big, _n = A.stats(d)
        log.w("binary64 against binary256 at %d h: position difference median %.3e m, largest %.3e m (8 objects)" % (n // 240, med, big))
    # C12
    op = os.path.join(cfg["work"], "i3d-m1-cft256-n6.txt")
    m1_traj(cfg, "cft256", sel, nsteps, op, ["--model", "prog", "--nmax", "6"])
    m6, _k = A.read_m1_traj(op)
    fails, _s, _t, _n = A.i3_compare(precs["fp256"], "fp256", m6, "fp256", steps, sel, 237)
    log.check(len(fails) > 0, "C12 (control): M1 at degree 6 against the program at degree 7, binary256: %d values over the tolerance (must be > 0)" % len(fails))
    # C13
    prog = progs["fp256"]
    rp, ip, _spec, _init = build_program_runs(prog, T0, 2, 6, rows_sel, "i3d-c13-%s" % prog.stem, frame_shift={1: -1})
    pre = os.path.join(cfg["work"], "i3d-c13-%s" % prog.stem)
    drive(cfg, prog, rp, ip, len(sel), pre)
    rec13, _lb = A.read_prog_segs(pre + ".seg.bin", sel, prog.nstate, prog.esz)
    fails, _s, _t, _n = A.i3_compare(rec13, "fp256", m1recs["cft256"], "fp256", steps, sel, 237)
    log.check(len(fails) > 0, "C13 (control): the second run given the hour before's frame block, binary256: %d values over the tolerance (must be > 0)" % len(fails))
    # the model gap, desktop size
    variants = {"prog": ["--model", "prog"], "full": ["--model", "full"], "deg20": ["--model", "prog", "--nmax", "20"],
                "srp": ["--model", "prog", "--srp", "1"]}
    for kind in ("native64", "cft64"):
        vr = {}
        for vn, ex in variants.items():
            op = os.path.join(cfg["work"], "i3d-gap-%s-%s.txt" % (kind, vn))
            if vn == "prog":
                vr[vn] = m1recs[kind]
                continue
            m1_traj(cfg, kind, sel, nsteps, op, ex)
            vr[vn], _k = A.read_m1_traj(op)
        fk = A.FMT_OF_KIND[kind]
        for (x, y, what) in (("prog", "full", "program's forces against the full model"),
                             ("prog", "deg20", "degree 7 against 20 (srp off)"), ("prog", "srp", "srp off against on (degree 7)")):
            for n in (240, 480):
                d = [A.pos_diff(vr[x][(i, n)][1][:3], fk, vr[y][(i, n)][1][:3], fk) for i in sel]
                med, big, _n = A.stats(d)
                log.w("gap %s %s at %d h: median %.4g m, largest %.4g m" % (kind, what, n // 240, med, big))
    sys.exit(1 if log.close() else 0)


# ------------------------------------------------------------------ I0

ARCHIVES = {"9e8ff270": "7814576d5d4d23fa4c1797553a32cd19b4e1d4c8f2d67fb7faecc9cfecb1c4bb",
            "0aa997a3": "e01003cc0b984864b065ce3395f56fa189451fcb0cd98cce5b11b3c17a9c29b8"}   # lead.md's
I0_KINDS = [("native32", []), ("native64", []), ("native32", ["--cr"]), ("native64", ["--cr"]), ("cft32", []),
            ("cft64", []), ("cft128", []), ("cft256", [])]

I0_CRIT = """I0: the pin and the builds (the desktop's half; the box's is the lead's, mode box-i0).
 P1 each archive's SHA-256 equals lead.md's (9e8ff270 7814576d...; 0aa997a3 e01003cc...);
 P2 every member of each archive equals its file in the extracted tree, byte for byte (so libcft, cftc and the
    interpreter come from the archive); files beyond the members are the build's outputs, counted;
 P3 src/ is byte-identical to commit 1646c96 (tests/build_i.sh check against studies/debris-i/src_1646c96.sha256), every
    source's SHA-256 printed; the builds' logs (tests/build_i.sh, one per libcft) are kept, and the binaries in use carry
    the SHA-256 their build printed;
 P4 M1 on 9e8ff270's libcft equals M1 on 0aa997a3's, bit for bit (every state line of m1i traj): the test seed's
    objects 0..15, 240 steps, from the same binary64 states, M1's full model (degree 20, 28 bands, Sun, Moon, radiation
    pressure, frame = 1 with DEBRIS-H's table), at native32, native64, native32 --cr, native64 --cr, cft32, cft64,
    cft128 and cft256 (the six kinds; the native ones with and without libcft's transcendentals);
 C1 (control) a copy of src/ with one byte of one file changed must FAIL P3's check;
 C2 (control) the 9e8ff270 run at cft64 with object 3's x one binary64 ulp up must FAIL P4's equality, in object 3's
    lines and in no other object's."""


def tar_check(tar_path, tree):
    """Every regular member of the tar equals the file under tree (git archive's layout, no top folder)."""
    import tarfile
    n, bad = 0, []
    with tarfile.open(tar_path) as t:
        for m in t:
            if not m.isfile():
                continue
            n += 1
            data = t.extractfile(m).read()
            p = os.path.join(tree, m.name)
            if not os.path.isfile(p) or open(p, "rb").read() != data:
                bad.append(m.name)
    nfiles = sum(len(f) for _d, _s, f in os.walk(tree))
    return n, nfiles, bad


def traj_lines(path):
    return [ln for ln in open(path, "rb").read().decode("ascii").splitlines() if ln.startswith("S ")]


def mode_i0(cfg, a):
    log = i_lib.Log(cfg["logs"], "i0_desktop", SCRIPT, [I0_CRIT], keep_dir=cfg["kept"], modules=MODULES)
    tools = cfg["tools"]
    trees = {"9e8ff270": cfg["fp256"], "0aa997a3": cfg["fp256_old"]}
    bins = {"9e8ff270": cfg["bin"], "0aa997a3": cfg["bin_old"]}
    for c, sha in ARCHIVES.items():
        tp = os.path.join(tools, "cft-fp256-%s.tar" % c)
        h = i_lib.sha256_file(tp)
        log.check(h == sha, "P1 archive %s SHA-256 %s equals lead.md's" % (c, h))
        n, nf, bad = tar_check(tp, trees[c])
        log.check(not bad and n > 2000, "P2 tree %s: %d archive members, each equal to its extracted file (%d differ or are "
                  "missing); the tree holds %d files, the rest the build's outputs" % (c, n, len(bad), nf))
        lib = os.path.join(trees[c], "host", "libcft.a")
        log.w("libcft.a from %s: SHA-256 %s" % (c, i_lib.sha256_file(lib)))
    bsh = os.path.join(HERE, "build_i.sh")
    bash = cfg.get("bash", "bash")
    exp = os.path.join(cfg["repo"], "studies", "debris-i", "src_1646c96.sha256")
    r = subprocess.run([bash, bsh, "check", os.path.join(cfg["repo"], "src"), exp], capture_output=True, text=True)
    for ln in r.stdout.splitlines():
        log.w("  " + ln)
    log.check(r.returncode == 0, "P3 src/ equals commit 1646c96 (build_i.sh check; build_i.sh SHA-256 %s)" % i_lib.sha256_file(bsh))
    for c in ARCHIVES:
        bl = cfg["build_logs"][c]
        txt = open(bl, "rb").read().decode("ascii", "replace")
        log.w("build log for %s: %s SHA-256 %s; its criteria: %s" % (c, os.path.basename(bl), i_lib.sha256_file(bl),
                                                                       ", ".join(x for x in txt.splitlines() if x.startswith("CRITERION") or x.startswith("BUILD"))))
        for exe_name in ("m1i", "i_run"):
            got = i_lib.sha256_file(os.path.join(bins[c], exe_name + (".exe" if sys.platform == "win32" else "")))
            log.check(got in txt, "P3 %s of the %s build: SHA-256 %s is the one its build printed" % (exe_name, c, got))
    # C1
    import shutil
    tmp = os.path.join(cfg["work"], "c1-src")
    if os.path.exists(tmp):
        raise SystemExit("%s exists: C1 never overwrites" % tmp)
    shutil.copytree(os.path.join(cfg["repo"], "src"), tmp)
    p = os.path.join(tmp, "m1_consts.h")
    b = bytearray(open(p, "rb").read())
    b[100] ^= 0x01
    open(p, "wb").write(bytes(b))
    r = subprocess.run([bash, bsh, "check", tmp, exp], capture_output=True, text=True)
    log.check(r.returncode != 0 and "DIFFERS" in r.stdout, "C1 (control) one byte of m1_consts.h changed: the source check FAILS")
    # P4
    seed = cfg["test_seed"]
    ss = "%s:%s" % (seed, i_lib.sha256_file(seed))
    idx = ",".join(str(i) for i in range(16))
    outs = {}
    for kind, extra in I0_KINDS:
        name = kind + ("-cr" if extra else "")
        for c in ARCHIVES:
            op = os.path.join(cfg["work"], "i0-%s-%s.txt" % (c, name))
            cmd = [os.path.join(bins[c], "m1i"), "traj", kind, "--table", cfg["frame_table"], "--seed", ss, "--idx", idx,
                   "--nsteps", "240", "--every", "40", "--out", op, "--model", "full"] + extra
            r = subprocess.run(cmd, capture_output=True, text=True, env=m1env(cfg))
            if r.returncode:
                raise SystemExit("m1i %s %s: %s" % (c, name, r.stderr))
            outs[(c, name)] = op
        la, lb = traj_lines(outs[("9e8ff270", name)]), traj_lines(outs[("0aa997a3", name)])
        log.check(la == lb and len(la) == 16 * 7, "P4 %s: M1 on 9e8ff270's libcft equals 0aa997a3's, %d state lines, "
                  "SHA-256 of the lines %s" % (name, len(la), i_lib.sha256_bytes("\n".join(la).encode())))
    # C2
    op = os.path.join(cfg["work"], "i0-9e8ff270-cft64-plant3.txt")
    cmd = [os.path.join(bins["9e8ff270"], "m1i"), "traj", "cft64", "--table", cfg["frame_table"], "--seed", ss, "--idx",
           idx, "--nsteps", "240", "--every", "40", "--out", op, "--model", "full", "--plant-x", "3"]
    r = subprocess.run(cmd, capture_output=True, text=True, env=m1env(cfg))
    la, lb = traj_lines(op), traj_lines(outs[("0aa997a3", "cft64")])
    diff_obj = sorted(set(x.split()[1] for x, y in zip(la, lb) if x != y))
    log.check(diff_obj == ["3"], "C2 (control) object 3's x one ulp up: the equality FAILS in object 3 alone (objects differing: %s)" % diff_obj)
    sys.exit(1 if log.close() else 0)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode")
    ap.add_argument("--cfg", required=True)
    ap.add_argument("--system", default="program7")
    ap.add_argument("--formats", default="fp64")
    ap.add_argument("--nlanes", type=int, default=16)
    ap.add_argument("--nruns", type=int, default=2)
    ap.add_argument("--budget", default="1800")
    ap.add_argument("--parts", default="central,grav,tides,bodies,frame,drag")
    a = ap.parse_args()
    cfg = cfg_load(a.cfg)
    cpu = i_lib.Cpu("harness-%s-%s" % (a.mode, a.system if a.mode == "i1" else ""), cfg.get("cpu_ledger"))
    try:
        if a.mode == "i1":
            mode_i1(cfg, a)
        elif a.mode == "i6":
            mode_i6(cfg, a)
        elif a.mode == "i1parts":
            mode_i1parts(cfg, a)
        elif a.mode == "i2":
            mode_i2(cfg, a)
        elif a.mode == "i3d":
            mode_i3d(cfg, a)
        elif a.mode == "i0":
            mode_i0(cfg, a)
        else:
            raise SystemExit("no mode %s" % a.mode)
    finally:
        cpu.close()


if __name__ == "__main__":
    main()
