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
                    SCRIPT, [I1_CRIT], keep_dir=cfg["kept"] if not smoke else None)
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
    log = i_lib.Log(cfg["logs"], "i6", SCRIPT, [I6_CRIT], keep_dir=cfg["kept"])
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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode")
    ap.add_argument("--cfg", required=True)
    ap.add_argument("--system", default="program7")
    ap.add_argument("--formats", default="fp64")
    ap.add_argument("--nlanes", type=int, default=16)
    ap.add_argument("--nruns", type=int, default=2)
    ap.add_argument("--budget", default="1800")
    a = ap.parse_args()
    cfg = cfg_load(a.cfg)
    cpu = i_lib.Cpu("harness-%s-%s" % (a.mode, a.system if a.mode == "i1" else ""), cfg.get("cpu_ledger"))
    try:
        if a.mode == "i1":
            mode_i1(cfg, a)
        elif a.mode == "i6":
            mode_i6(cfg, a)
        else:
            raise SystemExit("no mode %s" % a.mode)
    finally:
        cpu.close()


if __name__ == "__main__":
    main()
