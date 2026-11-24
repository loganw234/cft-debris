"""j_harness.py - cft-debris DEBRIS-J: the harness of the GPU round. It compiles DEBRIS-I's program at short segments,
holds the short images to DEBRIS-I's 40-step records (gate E1), holds j_run to i_run on the desktop, stages the GPU's
run folder, runs the lead's GPU modes in cft-gpu, and compares and analyses the GPU's records.

cft-debris, MIT licence (see LICENSE at the repository root). Written by DEBRIS-J, 2026-11-23. Its logs, compiles
record and staging follow DEBRIS-I's tests/i_harness.py and tests/i_lib.py (cft-debris's own, MIT), which it imports
(i_lib) or copies in part (each copied piece says so); DEBRIS-G's validity rules (tests/g_harness.py, MIT) shape J2's.

Standard library only, everywhere: the GPU modes (gpu-*) run in cft-gpu under Python 3's standard library. The desktop
modes start cftc (the archive's python/cftc, which needs mpmath) and the drivers as child processes.

usage (desktop): python -I -B j_harness.py <mode> --cfg CFG.json [options]
  CFG.json names every path: repo, scratch, fp256 (the extracted archive), build (j_run and i_run), ledger, py.
  modes: compile, e1, jgate, controls, j3ref, stage, compare, analyze, replay, hostload
usage (cft-gpu, the lead's): python3 -I -B <root>/in/tests/j_harness.py gpu-<j0|j0c|j1|j2|j3> --root <run dir>
  --lock <lock file> [options]   (tests/j_gpu.sh is the wrapper the lead runs)
No other session's path is written in this script: the lock, the toolchain and the run folder are parameters.
"""
import argparse
import json
import math
import os
import random
import struct
import subprocess
import sys
import threading
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import i_lib  # noqa: E402  (DEBRIS-I's logs, hashes and CPU accounting, unchanged)

SCRIPT = os.path.abspath(__file__)
MODULES = [os.path.join(HERE, "i_lib.py")]
ESZ = {"fp32": 4, "fp64": 8, "fp128": 16, "fp256": 32}
PREC_FMT = {0: "fp32", 1: "fp64", 2: "fp128", 3: "fp256"}
FMT4 = ("fp32", "fp64", "fp128", "fp256")
FMT3 = ("fp64", "fp128", "fp256")
SHORT_S = (1, 2, 4, 8)
DEPTH = 512
TARGET = "sw:512"
H_STEP = 15                       # seconds a step
SEG40 = 40                        # DEBRIS-I's steps a segment
I1_SYSTEMS = ("program-d7", "program-d2", "part-central", "part-grav", "part-tides", "part-bodies", "part-frame",
              "part-drag")
CHUNK = 2048                      # hip:N's first chunk at this reach (backend_hip.cpp, PROG_CHUNK_START; kmax 2,728)
J3_DRAW_SEED = 20261124           # J3's 16 lanes (the plan), drawn at staging, before any run
J3_EXCLUDE = 1595                 # seed index set aside: DEBRIS-H decayed it 5.8 h after T_s (I3's rule)
CJ1_LANE, CJ1_WORD = 21, 1        # C-J1: lane 21 of the 64 (batch 2, lane 5), its x (state word 1), one ulp up
CJ3_BATCH, CJ3_REC, CJ3_BYTE = 3, 77, 8 + 2 * 7 * 8 + 1 * 8 + 3   # C-J3: fp64 batch 3, record 77, lane 2's x, byte 3
ABORT_MS = 1000.0                 # the plan's rule: no call on the card past 1,000 ms after the warm-up
STOP_MS = 150.0                   # J0c's stop rule
WARMUP_LANES = 8


# ------------------------------------------------------------------ paths

def cfg_load(path):
    c = json.load(open(path, "rb"))
    for k in ("repo", "scratch", "fp256", "build", "ledger", "py"):
        if k not in c:
            raise SystemExit("cfg: %s missing" % k)
    c["study"] = os.path.join(c["repo"], "studies", "debris-j")
    c["logs"] = c.get("logs") or os.path.join(c["study"], "logs")     # a CFG may send a functional test's logs elsewhere
    c["kept"] = c.get("kept") or os.path.join(c["study"], "scripts")
    c["systems"] = os.path.join(c["repo"], "studies", "debris-i", "systems")
    c["img"] = os.path.join(c["scratch"], "images")
    c["work"] = os.path.join(c["scratch"], "work")
    c["dj"] = os.path.join(c["ledger"], "debris-j")
    c["desk"] = os.path.join(c["dj"], "desktop")
    c["istage"] = os.path.join(c["ledger"], "debris-i", "box-stage", "r1", "in")
    c["ibox"] = os.path.join(c["ledger"], "debris-i", "box", "out", "i3")
    c["seed"] = os.path.join(c["ledger"], "debris-h", "box", "r2", "seed", "seed1.txt")
    c["tools"] = os.path.join(c["ledger"], "tools")
    for k in ("logs", "kept", "img", "work", "desk"):
        os.makedirs(c[k], exist_ok=True)
    return c


def redact(cfg, s):
    """A path or text with the desktop's roots written as tokens (no home path in a log)."""
    s = str(s)
    # the longest root first: the scratch's and the ledger's paths begin with the repository's
    for k, tok in sorted((("ledger", "<ledger>"), ("repo", "<repo>"), ("scratch", "<scratch>")), key=lambda x: -len(cfg[x[0]])):
        for form in (cfg[k], cfg[k].replace("\\", "/"), cfg[k].replace("/", "\\")):
            s = s.replace(form, tok)
    return s


def exe(path):
    return path + ".exe" if sys.platform == "win32" else path


# ------------------------------------------------------------------ images (SEQUENCER.md's header at 9e8ff270)

def image_parse(b):
    """A CFTP image: header words, the instruction section's offset, every REPEAT (instruction index, count, offset of
    its four count bytes). SEQUENCER.md: a 32-byte header (magic, version, n_insns, n_consts, max_deposits, precision,
    flags, scratch_io), then n_consts constants unless flags bit 0 (BANK_EXT), then n_insns 64-bit instructions; a
    control instruction has bit 31 set and its code in bits 7:0 (REPEAT is 1), and REPEAT's count is bits 63:32."""
    if len(b) < 32:
        raise ValueError("not an image: %d bytes" % len(b))
    magic, ver, ni, nc, md, prec, flags, sio = struct.unpack_from("<4s7I", b, 0)
    if magic != b"CFTP":
        raise ValueError("not an image: magic %r" % magic)
    fmt = PREC_FMT.get(prec)
    cb = 0 if flags & 1 else nc * ESZ[fmt]
    off = 32 + cb
    if len(b) != off + 8 * ni:
        raise ValueError("an image of %d bytes, its header says %d" % (len(b), off + 8 * ni))
    reps = []
    for k in range(ni):
        w = struct.unpack_from("<Q", b, off + 8 * k)[0]
        if (w >> 31) & 1 and (w & 0xFF) == 1:
            reps.append((k, w >> 32, off + 8 * k + 4))
    return {"version": ver, "n_insns": ni, "n_consts": nc, "max_deposits": md, "format": fmt, "flags": flags,
            "scratch_io": sio, "ins_off": off, "repeats": reps}


# ------------------------------------------------------------------ the driver's files (i_vals.py's layout)

def runs_parse(b):
    if len(b) < 32 or b[:4] != b"DBIR" or struct.unpack_from("<I", b, 4)[0] != 1:
        raise ValueError("not a DBIR version 1 runs file")
    esz, ncon, nscr, nst, nruns, nsh = struct.unpack_from("<6I", b, 8)
    off0 = 32 + 4 * nsh
    rec = 8 + esz + ncon * esz + nsh * esz
    if len(b) != off0 + nruns * rec:
        raise ValueError("a runs file whose length is not its header's")
    runs = [struct.unpack_from("<2I", b, off0 + r * rec) for r in range(nruns)]
    return {"esz": esz, "ncon": ncon, "nscr": nscr, "nst": nst, "nruns": nruns, "nsh": nsh, "off0": off0,
            "rec": rec, "nseg": [x[0] for x in runs], "tslot": [x[1] for x in runs]}


def runs_derive(b, mult=1, nruns=None, nseg_first=None):
    """A runs file from another: its first nruns runs (all by default), each run's nseg times mult, or (nseg_first) one
    run whose nseg is given. Every other byte is the source's."""
    p = runs_parse(b)
    nr = p["nruns"] if nruns is None else nruns
    if nr < 1 or nr > p["nruns"]:
        raise ValueError("runs_derive: %d runs of %d" % (nr, p["nruns"]))
    out = bytearray(b[:p["off0"]])
    struct.pack_into("<I", out, 24, nr)
    for r in range(nr):
        rec = bytearray(b[p["off0"] + r * p["rec"]:p["off0"] + (r + 1) * p["rec"]])
        nseg = struct.unpack_from("<I", rec, 0)[0]
        struct.pack_into("<I", rec, 0, nseg_first if nseg_first is not None else nseg * mult)
        out += rec
    return bytes(out)


def seg_records(b, n, nst, esz):
    """The records of a .seg.bin: [(run, seg, offset of the states, offset of the lane bytes)]."""
    rec = 8 + n * nst * esz + n
    if len(b) % rec:
        raise ValueError("not whole segment records (%d bytes, records of %d)" % (len(b), rec))
    out = []
    for o in range(0, len(b), rec):
        r, s = struct.unpack_from("<2I", b, o)
        out.append((r, s, o + 8, o + 8 + n * nst * esz))
    return out


def reduce40(b, n, nst, esz, N, nseg_runs, kept_every=1):
    """E1's relation: the 40-step file an s-step file makes (N = 40 / s). nseg_runs: each run's segments in the s-step
    file. A record kept at segment kN becomes (r, k) with the OR of the lane bytes of its N segments (with kept_every
    N those are already OR'ed by j_run). Raises unless the records are exactly the ones j_run writes."""
    recs = seg_records(b, n, nst, esz)
    out = bytearray()
    i = 0
    for r, nseg in enumerate(nseg_runs):
        if nseg % N:
            raise ValueError("run %d: %d segments, not a multiple of %d" % (r, nseg, N))
        want = list(range(kept_every, nseg + 1, kept_every))
        if nseg % kept_every:
            want.append(nseg)
        acc = bytearray(n)
        for s in want:
            rr, ss, so, lo = recs[i]
            i += 1
            if (rr, ss) != (r, s):
                raise ValueError("record %d is (%d, %d), expected (%d, %d)" % (i - 1, rr, ss, r, s))
            for k in range(n):
                acc[k] |= b[lo + k]
            if s % N == 0:
                out += struct.pack("<2I", r, s // N) + b[so:lo] + bytes(acc)
                acc = bytearray(n)
            elif s == nseg:
                raise ValueError("run %d ends inside a 40-step segment" % r)
    if i != len(recs):
        raise ValueError("%d records past the runs" % (len(recs) - i))
    return bytes(out)


def lane_slice(b, n, nst, esz, lanes):
    """The records of a 40-step file cut to the given lanes, in that order (header, states, lane bytes)."""
    out = bytearray()
    for r, s, so, lo in seg_records(b, n, nst, esz):
        out += struct.pack("<2I", r, s)
        for l in lanes:
            out += b[so + l * nst * esz:so + (l + 1) * nst * esz]
        out += bytes(b[lo + l] for l in lanes)
    return bytes(out)


def compare40(got, ref, n, nst, esz, label, nrec=None):
    """Two 40-step files of n lanes, record by record (nrec: only the first nrec of ref): [(record, run, seg, lane,
    'state' or 'byte')] of every difference, and the number of records compared."""
    a, b = seg_records(got, n, nst, esz), seg_records(ref, n, nst, esz)
    if nrec is not None:
        b = b[:nrec]
    diffs = []
    if len(a) < len(b):
        diffs.append((len(a), -1, -1, -1, "missing records: %d of %d" % (len(a), len(b))))
    for i in range(min(len(a), len(b))):
        (ra, sa, soa, loa), (rb, sb, sob, lob) = a[i], b[i]
        if (ra, sa) != (rb, sb):
            diffs.append((i, rb, sb, -1, "header (%d, %d)" % (ra, sa)))
            continue
        w = nst * esz
        for l in range(n):
            if got[soa + l * w:soa + (l + 1) * w] != ref[sob + l * w:sob + (l + 1) * w]:
                diffs.append((i, rb, sb, l, "state"))
            if got[loa + l] != ref[lob + l]:
                diffs.append((i, rb, sb, l, "byte 0x%02x / 0x%02x" % (got[loa + l], ref[lob + l])))
    return diffs, min(len(a), len(b))


def read(path):
    with open(path, "rb") as f:
        return f.read()


def write_new(path, data):
    """Write bytes to a new file (never over an existing one)."""
    with open(path, "xb") as f:
        f.write(data)


# ------------------------------------------------------------------ the seed and the lanes' INIT rows

def seed_rows(path):
    """DEBRIS-H's seed (i_vals.read_seed's reading, standard library): (idx, T_s, [x y z vx vy vz], bc) binary64."""
    out = []
    with open(path, "rb") as f:
        for raw in f:
            line = raw.decode("ascii")
            if line.startswith("#") or not line.strip():
                continue
            w = line.split()
            v = [float.fromhex(x) for x in w[3:12]]
            out.append((int(w[0]), v[0], v[1:7], v[7]))
    for k, row in enumerate(out):
        if row[0] != k:
            raise SystemExit("seed row %d has index %d" % (k, row[0]))
    return out


def widen(x, fmt):
    """The encoding of a binary64 value at fmt, exactly (widening is exact; binary32 is not used here)."""
    bits = struct.unpack("<Q", struct.pack("<d", x))[0]
    if fmt == "fp64":
        return bits
    ew, mw = {"fp128": (15, 112), "fp256": (19, 236)}[fmt]
    sign, e, m = bits >> 63, (bits >> 52) & 0x7FF, bits & ((1 << 52) - 1)
    if e == 0x7FF:
        raise ValueError("not finite")
    if e == 0:
        if m == 0:
            return sign << (ew + mw)
        k = m.bit_length() - 1                 # a subnormal binary64: normal at the wider format
        e2 = 1 - 1023 - 52 + k
        m2 = (m - (1 << k)) << (mw - k)
    else:
        e2 = e - 1023
        m2 = m << (mw - 52)
    return (sign << (ew + mw)) | ((e2 + (1 << (ew - 1)) - 1) << mw) | m2


def init_row(row, fmt, nscr, nst, bc_slot, T_s):
    """A lane's INIT (i_harness.lanes_init's layout): t, then x..vz, then the lane params: bc, the others 0."""
    if nst != 7:
        raise SystemExit("the state is not 7 words")
    words = [widen(T_s, fmt)] + [widen(x, fmt) for x in row[2]] + [0] * (nscr - nst)
    words[bc_slot] = widen(row[3], fmt)
    e = ESZ[fmt]
    return b"".join(w.to_bytes(e, "little") for w in words)


# ------------------------------------------------------------------ running a driver

class Ran:
    pass


def run_proc(argv, out_txt, cwd=None, env=None, watchdog_s=None, timeout_s=None):
    """Run one process, its stdout written to out_txt as it comes; a watchdog kills it by its PID (this harness
    started it) after watchdog_s seconds with no line, and timeout_s bounds it. Returns a Ran."""
    R = Ran()
    R.argv, R.lines, R.errs, R.killed = list(argv), [], [], None
    t0 = time.time()
    last = [time.time()]
    with open(out_txt, "xb") as fo:
        p = subprocess.Popen([str(x) for x in argv], cwd=cwd, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        R.pid = p.pid

        def rd():
            for raw in iter(p.stdout.readline, b""):
                fo.write(raw)
                fo.flush()
                R.lines.append(raw.decode("utf-8", "replace").rstrip("\r\n"))
                last[0] = time.time()

        def rde():
            for raw in iter(p.stderr.readline, b""):
                R.errs.append(raw.decode("utf-8", "replace").rstrip("\r\n"))

        t1, t2 = threading.Thread(target=rd, daemon=True), threading.Thread(target=rde, daemon=True)
        t1.start()
        t2.start()
        while p.poll() is None:
            time.sleep(0.2)
            now = time.time()
            if watchdog_s and now - last[0] > watchdog_s:
                R.killed = "no output for %.0f s" % (now - last[0])
            elif timeout_s and now - t0 > timeout_s:
                R.killed = "past %.0f s" % timeout_s
            if R.killed:
                p.kill()          # by its PID: this harness started it
                break
        p.wait()
        t1.join(10)
        t2.join(10)
    R.rc, R.wall = p.returncode, time.time() - t0
    R.rep = {}
    R.segs, R.device, R.caps, R.image, R.warmup, R.abort, R.loads = [], None, None, None, None, None, []
    for ln in R.lines:
        if ln.startswith("REPORT "):
            k, _, v = ln[7:].partition(" ")
            R.rep[k] = v
        elif ln.startswith("seg "):
            # j_run's line: seg <run> <seg> flags 0x.. bus 0x.. call_ns <ns> marked <k> [lanes ...]; i_run's has no call_ns
            w = ln.split()
            kv = {w[i]: w[i + 1] for i in range(3, len(w) - 1) if w[i] in ("flags", "bus", "call_ns", "marked")}
            lanes = [int(x) for x in w[w.index("lanes") + 1:]] if "lanes" in w else []
            R.segs.append({"run": int(w[1]), "seg": int(w[2]), "flags": int(kv.get("flags", "0"), 16),
                           "bus": int(kv.get("bus", "0"), 16), "call_ns": int(kv.get("call_ns", "-1")),
                           "marked": int(kv.get("marked", "0")), "lanes": lanes})
        elif ln.startswith("device "):
            R.device = ln[7:]
        elif ln.startswith("caps "):
            R.caps = ln[5:]
        elif ln.startswith("image "):
            R.image = ln[6:]
        elif ln.startswith("warmup "):
            R.warmup = ln
        elif ln.startswith("ABORT "):
            R.abort = ln[6:]
        elif ln.startswith("load "):
            R.loads.append(ln[5:])
    return R


def rep_int(R, k, default=None):
    try:
        return int(R.rep[k])
    except (KeyError, ValueError):
        return default


# ------------------------------------------------------------------ compiles (i_harness.compile_sys's record, copied)

COMPILES = "compiles.tsv"
COMPILE_COLS = ["time_local", "stem", "format", "target", "steps", "source", "source_sha256", "result", "cftp_sha256",
                "bank_sha256", "manifest_sha256", "instructions", "per_step", "alu", "loads", "stores",
                "routine_calls", "bank_slots", "bank_params", "bank_consts", "bank_words", "scratch_slots",
                "scratch_state_lane", "spill_slots", "scratch_declared", "features", "order", "wall_s", "command"]


def compile_row(cfg, src, fmt, stem, steps, outdir, rc, err, wall):
    """One row of studies/debris-j/compiles.tsv (i_harness.compile_sys's columns and reading of the manifest)."""
    rel = os.path.relpath(src, cfg["repo"]).replace("\\", "/")
    row = {"time_local": time.strftime("%Y-%m-%d %H:%M:%S %z"), "stem": stem, "format": fmt, "target": TARGET,
           "steps": steps, "source": rel, "source_sha256": i_lib.sha256_file(src), "wall_s": "%.1f" % wall,
           "command": "python -I -B <archive 9e8ff270>/python/cftc %s --steps %d --target %s --format %s --out <dir> "
                      "--stem %s" % (rel, steps, TARGET, fmt, stem)}
    if rc == 0:
        mp = os.path.join(outdir, stem + ".manifest.json")
        man = json.load(open(mp, "rb"))
        kinds = {}
        for b in man["bank"]:
            kinds[b["kind"]] = kinds.get(b["kind"], 0) + 1
        nlane = sum(1 for e in man["scratch"]["layout"] if e["kind"] != "state")
        nst = sum(1 for e in man["scratch"]["layout"] if e["kind"] == "state")
        rt = man.get("routines", {})
        row.update({"result": "compiled", "cftp_sha256": i_lib.sha256_file(os.path.join(outdir, stem + ".cftp")),
                    "bank_sha256": i_lib.sha256_file(os.path.join(outdir, stem + ".bank")),
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
    tsv = os.path.join(cfg["study"], COMPILES)
    new = not os.path.exists(tsv)
    with open(tsv, "a", encoding="ascii", newline="\n") as f:
        if new:
            f.write("\t".join(COMPILE_COLS) + "\n")
        f.write("\t".join(str(row.get(c, "")) for c in COMPILE_COLS) + "\n")
    return row


def img_dir(cfg, s):
    return os.path.join(cfg["img"], "s%d" % s)


def compile_list():
    """Every compile of the round: I1's eight systems at four formats at s = 40 (the references, for E1's byte diff and
    banks) and at s = 1; the program at degree 7 at s = 2, 4 and 8 at binary64, binary128 and binary256."""
    out = []
    for s in (40, 1):
        for sysn in I1_SYSTEMS:
            for fmt in FMT4:
                out.append(("%s-%s" % (sysn, fmt), fmt, s))
    for s in (2, 4, 8):
        for fmt in FMT3:
            out.append(("program-d7-%s" % fmt, fmt, s))
    return out


COMPILE_CRIT = """compile: cftc at cft-fp256 9e8ff270 (the archive 7814576d..., extracted in the scratch) on DEBRIS-I's sources
unchanged (studies/debris-i/systems/<stem>.cftl, each SHA-256 printed), for sw:512, one image a (source, format, s):
I1's eight systems (the program at degrees 7 and 2 and the six part systems) at binary32, 64, 128 and 256 at s = 40 and
at s = 1, and the program at degree 7 at s = 2, 4 and 8 at binary64, 128 and 256 (73 compiles; each s in its own
folder, the stem DEBRIS-I's). Each compile is one row of studies/debris-j/compiles.tsv (DEBRIS-I's columns).
Asserted: every compile succeeds; each source's SHA-256 is the one DEBRIS-I's compiles.tsv records for it; and each s =
40 image's SHA-256 equals DEBRIS-I's compiles.tsv's (cftc reproduces DEBRIS-I's images)."""


def debris_i_compiles(cfg):
    rows = {}
    for line in open(os.path.join(cfg["repo"], "studies", "debris-i", "compiles.tsv"), encoding="ascii"):
        w = line.rstrip("\n").split("\t")
        if w[0] == "time_local" or len(w) < 9 or w[7] != "compiled" or w[3] != TARGET:
            continue
        rows[w[1]] = {"source_sha256": w[6], "cftp_sha256": w[8], "steps": w[4]}
    return rows


def mode_compile(cfg, a):
    log = i_lib.Log(cfg["logs"], "compile", SCRIPT, [COMPILE_CRIT], keep_dir=cfg["kept"], modules=MODULES)
    cpu = i_lib.Cpu("compile", os.path.join(cfg["scratch"], "cpu.tsv"))
    ref = debris_i_compiles(cfg)
    cftc = os.path.join(cfg["fp256"], "python", "cftc")
    jobs = compile_list()
    if a.only:
        jobs = [j for j in jobs if "%s@%d" % (j[0], j[2]) in a.only.split(",")]
    todo, running, done = list(jobs), [], []
    width = int(a.width)
    while todo or running:
        while todo and len(running) < width:
            stem, fmt, s = todo.pop(0)
            out = img_dir(cfg, s)
            os.makedirs(out, exist_ok=True)
            if os.path.exists(os.path.join(out, stem + ".cftp")):
                raise SystemExit("%s at s = %d exists: an image is never overwritten" % (stem, s))
            src = os.path.join(cfg["systems"], stem + ".cftl")
            cmd = [cfg["py"], "-I", "-B", cftc, src, "--steps", str(s), "--target", TARGET, "--format", fmt, "--out", out,
                   "--stem", stem]
            p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            running.append((stem, fmt, s, src, out, p, time.time()))
        for item in list(running):
            stem, fmt, s, src, out, p, t0 = item
            if p.poll() is None:
                continue
            _o, e = p.communicate()
            running.remove(item)
            row = compile_row(cfg, src, fmt, stem, s, out, p.returncode, e.decode("utf-8", "replace").strip(), time.time() - t0)
            done.append(row)
            ok = row["result"] == "compiled"
            log.check(ok, "compile %s s=%d: %s; %s instructions, bank %s, scratch %s; source %s; image %s"
                      % (stem, s, row["result"][:120], row.get("instructions", "-"), row.get("bank_slots", "-"),
                         row.get("scratch_slots", "-"), row["source_sha256"], row.get("cftp_sha256", "-")))
            r = ref.get(stem)
            log.check(r is not None and r["source_sha256"] == row["source_sha256"],
                      "  %s: the source's SHA-256 is DEBRIS-I's compiles.tsv's" % stem)
            if s == 40 and ok:
                log.check(r is not None and r["cftp_sha256"] == row["cftp_sha256"],
                          "  %s at s = 40: the image's SHA-256 is DEBRIS-I's (%s)" % (stem, r["cftp_sha256"] if r else "-"))
        time.sleep(0.2)
    log.w("%d compiles, at most %d at once" % (len(done), width))
    cpu.close()
    sys.exit(1 if log.close() else 0)


# ------------------------------------------------------------------ E1 and j_run's desktop gate

def i1_cases(cfg):
    """I1's 32 staged cases: name, image stem, format, lanes, runs and INIT paths, R1's recorded SHA-256."""
    exp = {}
    for line in open(os.path.join(cfg["istage"], "i1", "EXPECTED-segs.sha256"), encoding="ascii"):
        h, case = line.split()
        exp[case] = h
    out = []
    for case in sorted(exp):
        meta = json.load(open(os.path.join(cfg["istage"], "i1", case + ".json"), "rb"))
        out.append({"case": case, "stem": meta["image"][:-len(".cftp")], "fmt": meta["format"], "lanes": meta["lanes"],
                    "runs": os.path.join(cfg["istage"], "i1", case + ".runs.bin"),
                    "init": os.path.join(cfg["istage"], "i1", case + ".init.bin"), "r1": exp[case]})
    if len(out) != 32:
        raise SystemExit("I1: %d staged cases, not 32" % len(out))
    return out


def jrun_desktop(cfg, argv_tail, prefix_dir, tag, extra=()):
    """j_run on the desktop's software executor; its stdout kept beside its outputs."""
    os.makedirs(prefix_dir, exist_ok=True)
    pre = os.path.join(prefix_dir, tag)
    R = run_proc([exe(os.path.join(cfg["build"], "j_run")), "run"] + list(argv_tail) + ["--depth", str(DEPTH), "--out", pre]
                 + list(extra), pre + ".stdout.txt", timeout_s=3600)
    R.pre = pre
    return R


def manifest_state(cfg, stem, s=40):
    man = json.load(open(os.path.join(img_dir(cfg, s), stem + ".manifest.json"), "rb"))
    lay = man["scratch"]["layout"]
    nst = sum(1 for e in lay if e["kind"] == "state")
    names = {e["name"]: e["slot"] for e in lay}
    return man, nst, man["scratch"]["in"], names


E1_CRIT = """E1: the short segments, on the desktop (libcft's software executor; j_run with no artifact, depth 512).
THE LANE BYTES' RELATION, stated before E1 runs (BELIEVED, from HOSTAPI's R23 at 9e8ff270, docs/HOSTAPI.md lines
3721-3737: a lane's byte is [4:0] the IEEE flags raised outside every quiet region, [5] deposit overflow, [6] strict
range, [7] the mark, and "Each byte is sticky within the run and starts it at zero"): with N = 40 / s, the 40-step
segment k of a run is the s-step segments (k-1)N+1 .. kN of the same run; its state equals the state after s-step
segment kN, bit for bit, and its lane byte equals the bitwise OR of those N segments' lane bytes, all eight bits. The
s-step runs file is the 40-step one with each run's nseg times N and no other byte changed. REDUCE(file, N) is the
40-step file this makes from an s-step file: each run's records at kN, renumbered (r, k), each with the OR of the lane
bytes of its N segments; a file j_run wrote with --keep-every N reduces by renumbering alone (its bytes are OR'ed).
(i) the images: for each (source, format), the s-step image and the 40-step image (both compiled here, same stem) are
    CFTP images with BANK_EXT, the same header words and length, and one REPEAT each (control code 1) at the same
    instruction, its count s and 40; the only bytes that differ are that REPEAT's four count bytes (offset + 4 .. + 7 of
    the instruction, read from the 40-step image's format before any diff); the two .bank files are identical. Any
    other differing byte fails E1.
(ii) I1's 32 cases at s = 1 (the staged INIT; the staged runs file with each run's nseg x 40): REDUCE(output, 40) has the
    SHA-256 R1 recorded for the 40-step run (ledger debris-i/box-stage/r1/in/i1/EXPECTED-segs.sha256); the marks file
    is empty (R1's cases had none); and the same run with --keep-every 40 reduces to the same bytes.
(iii) the program at degree 7, s = 2, 4 and 8, at binary64, binary128 and binary256, on I3's batch 0 (8 lanes) for 2
    hours (I3's day runs file cut to its first 2 runs, each run's nseg x N): REDUCE(output, N) equals, byte for byte,
    the first 12 records of the box's 40-step file (ledger debris-i/box/out/i3/prog-<fmt>-b0.seg.bin) and the desktop's
    own 40-step run of the same 2 hours; --keep-every N reduces to the same bytes; 0 marks.
C-E1 (control): I1's program at degree 7, binary64, s = 1 output with one state byte flipped in its 40th segment (the
    first 40-step boundary) must FAIL (ii)'s hash; the hash unchanged = control FAILED."""


def e1_images(cfg, log):
    ok_all = True
    pairs = []
    for s in (1,):
        for sysn in I1_SYSTEMS:
            for fmt in FMT4:
                pairs.append(("%s-%s" % (sysn, fmt), s))
    for s in (2, 4, 8):
        for fmt in FMT3:
            pairs.append(("program-d7-%s" % fmt, s))
    for stem, s in pairs:
        b40 = read(os.path.join(img_dir(cfg, 40), stem + ".cftp"))
        bs = read(os.path.join(img_dir(cfg, s), stem + ".cftp"))
        p40, ps = image_parse(b40), image_parse(bs)
        why = []
        if len(p40["repeats"]) != 1 or len(ps["repeats"]) != 1:
            why.append("REPEATs %d and %d" % (len(p40["repeats"]), len(ps["repeats"])))
        else:
            k40, c40, o40 = p40["repeats"][0]
            ks, cs, os_ = ps["repeats"][0]
            if (k40, o40) != (ks, os_):
                why.append("the REPEAT at instruction %d and %d" % (k40, ks))
            if c40 != SEG40 or cs != s:
                why.append("counts %d and %d" % (c40, cs))
            if not (p40["flags"] & 1 and ps["flags"] & 1):
                why.append("no BANK_EXT")
            if bs[:32] != b40[:32] or len(bs) != len(b40):
                why.append("the header or the length differs")
            allowed = set(range(o40, o40 + 4))
            diff = [i for i in range(min(len(b40), len(bs))) if b40[i] != bs[i]]
            if [i for i in diff if i not in allowed]:
                why.append("bytes outside the count differ: %s" % [i for i in diff if i not in allowed][:5])
            if read(os.path.join(img_dir(cfg, 40), stem + ".bank")) != read(os.path.join(img_dir(cfg, s), stem + ".bank")):
                why.append("the banks differ")
        ok = not why
        ok_all &= ok
        log.check(ok, "E1(i) %s s=%d: one REPEAT, instruction %d, count bytes at offset %d (count %d against 40); "
                  "differing bytes %s; banks identical; image %s against %s%s" % (
                      stem, s, ps["repeats"][0][0] if ps["repeats"] else -1, ps["repeats"][0][2] if ps["repeats"] else -1,
                      ps["repeats"][0][1] if ps["repeats"] else -1,
                      [i for i in range(min(len(b40), len(bs))) if b40[i] != bs[i]][:8],
                      i_lib.sha256_bytes(bs)[:16], i_lib.sha256_bytes(b40)[:16], ("; " + "; ".join(why)) if why else ""))
    return ok_all


def mode_e1(cfg, a):
    log = i_lib.Log(cfg["logs"], "e1", SCRIPT, [E1_CRIT], keep_dir=cfg["kept"], modules=MODULES)
    cpu = i_lib.Cpu("e1", os.path.join(cfg["scratch"], "cpu.tsv"))
    od = os.path.join(cfg["desk"], "e1")
    if os.path.exists(od):
        raise SystemExit("%s exists: E1 writes a new folder" % od)
    os.makedirs(od)
    log.w("outputs (per-object states): <ledger>/debris-j/desktop/e1/")
    # (i)
    log.w("")
    log.w("== E1(i): the images ==")
    e1_images(cfg, log)
    # (ii)
    log.w("")
    log.w("== E1(ii): I1's 32 cases at s = 1 ==")
    ref_out = {}
    for c in i1_cases(cfg):
        rb = read(c["runs"])
        rp = runs_parse(rb)
        r1 = runs_derive(rb, mult=40)
        rpath = os.path.join(od, c["case"] + ".s1.runs.bin")
        write_new(rpath, r1)
        img = os.path.join(img_dir(cfg, 1), c["stem"] + ".cftp")
        tail = ["--image", img, "--runs", rpath, "--init", c["init"], "--lanes", str(c["lanes"]), "--seg-steps", "1"]
        R = jrun_desktop(cfg, tail, od, c["case"] + ".s1")
        R40 = jrun_desktop(cfg, tail, od, c["case"] + ".s1k40", ["--keep-every", "40"])
        if R.rc or R40.rc:
            log.check(False, "E1(ii) %s: j_run exit %s / %s: %s" % (c["case"], R.rc, R40.rc, (R.errs + R40.errs)[-2:]))
            continue
        seg = read(R.pre + ".seg.bin")
        red = reduce40(seg, c["lanes"], rp["nst"], rp["esz"], 40, [x * 40 for x in rp["nseg"]])
        red40 = reduce40(read(R40.pre + ".seg.bin"), c["lanes"], rp["nst"], rp["esz"], 40, [x * 40 for x in rp["nseg"]],
                         kept_every=40)
        h = i_lib.sha256_bytes(red)
        marks = os.path.getsize(R.pre + ".marks.bin")
        ref_out[c["case"]] = {"seg": i_lib.sha256_file(R.pre + ".seg.bin"), "marks": i_lib.sha256_file(R.pre + ".marks.bin"),
                              "runs": i_lib.sha256_bytes(r1), "init": i_lib.sha256_file(c["init"]),
                              "image": i_lib.sha256_file(img), "reduced": h, "r1": c["r1"]}
        log.check(h == c["r1"] and red40 == red and marks == 0,
                  "E1(ii) %s s=1: %d segments; REDUCE %s, R1's %s; --keep-every 40 reduces to the same bytes: %s; marks "
                  "file %d bytes; image %s runs %s init %s; output %s" % (
                      c["case"], rep_int(R, "segments", -1), h, c["r1"], red40 == red, marks, ref_out[c["case"]]["image"][:16],
                      ref_out[c["case"]]["runs"][:16], ref_out[c["case"]]["init"][:16], ref_out[c["case"]]["seg"]))
    jp = os.path.join(od, "e1_s1_outputs.json")
    with open(jp, "x", encoding="ascii", newline="\n") as f:
        json.dump(ref_out, f, indent=1, sort_keys=True)
    log.w("the s = 1 outputs' SHA-256 (J1(a)'s references): <ledger>/debris-j/desktop/e1/e1_s1_outputs.json SHA-256 %s"
          % i_lib.sha256_file(jp))
    # C-E1
    c = [x for x in i1_cases(cfg) if x["case"] == "i1-program-d7-fp64"][0]
    seg = bytearray(read(os.path.join(od, c["case"] + ".s1.seg.bin")))
    rp = runs_parse(read(c["runs"]))
    recs = seg_records(bytes(seg), c["lanes"], rp["nst"], rp["esz"])
    r, s, so, lo = recs[39]
    seg[so + 3 * 8 + 5] ^= 0x01
    hp = i_lib.sha256_bytes(reduce40(bytes(seg), c["lanes"], rp["nst"], rp["esz"], 40, [x * 40 for x in rp["nseg"]]))
    log.check(hp != c["r1"], "C-E1 (control) one state byte flipped in segment (%d, %d), lane 0's z: the reduced hash %s "
              "against R1's %s: (ii) FAILS, as it must" % (r, s, hp[:16], c["r1"][:16]))
    # (iii)
    log.w("")
    log.w("== E1(iii): the program at degree 7, s = 2, 4, 8, I3's batch 0, 2 hours ==")
    plan = json.load(open(os.path.join(cfg["istage"], "i3", "plan.json"), "rb"))
    for fmt in FMT3:
        rb = read(os.path.join(cfg["istage"], "i3", plan["runs"][fmt]))
        two = runs_derive(rb, nruns=2)
        p2 = runs_parse(two)
        init = os.path.join(cfg["istage"], "i3", plan["batches"][0]["init"][fmt])
        box = read(os.path.join(cfg["ibox"], "prog-%s-b0.seg.bin" % fmt))
        nst, esz = p2["nst"], p2["esz"]
        box12 = b"".join(box[so - 8:lo + 8] for (_r, _s, so, lo) in seg_records(box, 8, nst, esz)[:12])
        r40p = os.path.join(od, "i3b0-%s.s40.runs.bin" % fmt)
        write_new(r40p, two)
        img40 = os.path.join(img_dir(cfg, 40), "program-d7-%s.cftp" % fmt)
        R = jrun_desktop(cfg, ["--image", img40, "--runs", r40p, "--init", init, "--lanes", "8", "--seg-steps", "40"], od,
                         "i3b0-%s.s40" % fmt)
        d40 = read(R.pre + ".seg.bin") if not R.rc else b""
        log.check(R.rc == 0 and d40 == box12, "E1(iii) %s: the desktop's 40-step run of 2 hours equals the box's first 12 "
                  "records (%s)" % (fmt, i_lib.sha256_bytes(d40)[:16]))
        for s in (2, 4, 8):
            N = SEG40 // s
            rs = runs_derive(two, mult=N)
            rsp = os.path.join(od, "i3b0-%s.s%d.runs.bin" % (fmt, s))
            write_new(rsp, rs)
            img = os.path.join(img_dir(cfg, s), "program-d7-%s.cftp" % fmt)
            tail = ["--image", img, "--runs", rsp, "--init", init, "--lanes", "8", "--seg-steps", str(s)]
            Ra = jrun_desktop(cfg, tail, od, "i3b0-%s.s%d" % (fmt, s))
            Rk = jrun_desktop(cfg, tail, od, "i3b0-%s.s%dk%d" % (fmt, s, N), ["--keep-every", str(N)])
            if Ra.rc or Rk.rc:
                log.check(False, "E1(iii) %s s=%d: j_run exit %s / %s: %s" % (fmt, s, Ra.rc, Rk.rc, (Ra.errs + Rk.errs)[-2:]))
                continue
            nsegs = [x * N for x in p2["nseg"]]
            red = reduce40(read(Ra.pre + ".seg.bin"), 8, nst, esz, N, nsegs)
            redk = reduce40(read(Rk.pre + ".seg.bin"), 8, nst, esz, N, nsegs, kept_every=N)
            mk = os.path.getsize(Ra.pre + ".marks.bin") + os.path.getsize(Rk.pre + ".marks.bin")
            log.check(red == box12 and red == d40 and redk == red and mk == 0,
                      "E1(iii) %s s=%d: %d segments; REDUCE equals the box's 12 records: %s, the desktop's 40-step run: %s; "
                      "--keep-every %d reduces to the same: %s; marks %d; image %s; reduced %s" % (
                          fmt, s, rep_int(Ra, "segments", -1), red == box12, red == d40, N, redk == red, mk,
                          i_lib.sha256_file(img)[:16], i_lib.sha256_bytes(red)[:16]))
    cpu.close()
    sys.exit(1 if log.close() else 0)


JGATE_CRIT = """j_run's desktop gate (libcft's software executor; j_run and DEBRIS-I's i_run built from one libcft.a by
tests/build_j.sh desktop; depth 512; no artifact):
(a) on I1's 32 cases at s = 40 (DEBRIS-I's staged 40-step images, runs and INIT files), j_run run with --keep-every 1
    writes .seg.bin and .marks.bin byte-identical to i_run's, and its .seg.bin has R1's SHA-256;
(b) with --warmup-lanes 8 and --abort-ms 60000 j_run writes the same bytes again (the warm-up's output is discarded), on
    four of the cases (the program at degree 7 at binary64; grav at binary256, tides at binary32, drag at binary128);
(c) the stop path: --expect-device with a name, on the software executor (whose open prints no device line), stops
    with exit 5 and a "device none" line, before any "image " line, with no output but PREFIX.open.txt;
(d) --abort-ms 0.000001 stops the driver after the process's second call, exit 6, with "ABORT" on stdout, the
    provenance's status ABORTED, and that call's segment line printed;
(e) mode load loads every image of the round (CFT_OK: the 32 of I1's systems at s = 1 and the program's 9 at s = 2, 4,
    8), and a copy of one with one header byte changed is refused, exit 3;
(f) each provenance file of (a) names the SHA-256 of the image, runs and INIT files, and of its outputs as they are
    on disk."""


def prov_read(path):
    d = {"lines": open(path, "rb").read().decode("utf-8", "replace").splitlines()}
    for ln in d["lines"]:
        k, _, v = ln.partition(" ")
        if k == "out":
            d.setdefault("out", []).append(v.split())
        else:
            d.setdefault(k, v)
    return d


def mode_jgate(cfg, a):
    log = i_lib.Log(cfg["logs"], "jgate", SCRIPT, [JGATE_CRIT], keep_dir=cfg["kept"], modules=MODULES)
    cpu = i_lib.Cpu("jgate", os.path.join(cfg["scratch"], "cpu.tsv"))
    od = os.path.join(cfg["desk"], "jgate")
    if os.path.exists(od):
        raise SystemExit("%s exists: the gate writes a new folder" % od)
    os.makedirs(od)
    jr, ir = exe(os.path.join(cfg["build"], "j_run")), exe(os.path.join(cfg["build"], "i_run"))
    log.w("j_run %s; i_run %s (build_j.sh desktop)" % (i_lib.sha256_file(jr), i_lib.sha256_file(ir)))
    ok_a = ok_b = ok_f = True
    for c in i1_cases(cfg):
        img = os.path.join(cfg["istage"], "img", c["stem"] + ".cftp")
        tail = ["--image", img, "--runs", c["runs"], "--init", c["init"], "--lanes", str(c["lanes"]), "--depth", str(DEPTH)]
        pi = os.path.join(od, c["case"] + ".i")
        Ri = run_proc([ir, "run"] + tail + ["--out", pi], pi + ".stdout.txt", timeout_s=1800)
        Rj = jrun_desktop(cfg, tail[:-2] + ["--seg-steps", "40"], od, c["case"] + ".j")
        same = Ri.rc == 0 and Rj.rc == 0 and read(pi + ".seg.bin") == read(Rj.pre + ".seg.bin") and \
            read(pi + ".marks.bin") == read(Rj.pre + ".marks.bin")
        h = i_lib.sha256_file(Rj.pre + ".seg.bin") if Rj.rc == 0 else "-"
        ok = log.check(same and h == c["r1"], "(a) %s: j_run's .seg.bin and .marks.bin equal i_run's: %s; .seg.bin %s, R1's %s"
                       % (c["case"], same, h, c["r1"]))
        ok_a &= ok
        if c["case"] in ("i1-program-d7-fp64", "i1p-part-grav-fp256", "i1p-part-tides-fp32", "i1p-part-drag-fp128"):
            Rw = jrun_desktop(cfg, tail[:-2] + ["--seg-steps", "40"], od, c["case"] + ".jw",
                              ["--warmup-lanes", "8", "--abort-ms", "60000"])
            samew = Rw.rc == 0 and read(Rw.pre + ".seg.bin") == read(Rj.pre + ".seg.bin") and \
                read(Rw.pre + ".marks.bin") == read(Rj.pre + ".marks.bin")
            ok_b &= log.check(samew and Rw.warmup is not None, "(b) %s: with the warm-up (%s) the same bytes: %s" % (
                c["case"], (Rw.warmup or "none")[:60], samew))
        pv = prov_read(Rj.pre + ".prov.txt")
        outs = {o[0]: o[2] for o in pv.get("out", [])}
        f_ok = pv.get("status") == "DONE" and \
            pv.get("image", "").split()[2] == i_lib.sha256_file(img) and \
            pv.get("runs", "").split()[2] == i_lib.sha256_file(c["runs"]) and \
            pv.get("init", "").split()[2] == i_lib.sha256_file(c["init"]) and \
            all(i_lib.sha256_file(p) == hh for p, hh in outs.items()) and len(outs) == 3
        ok_f &= log.check(f_ok, "(f) %s: the provenance names the inputs' and the %d outputs' SHA-256 as on disk" % (
            c["case"], len(outs)))
    # (c) the stop path
    c = i1_cases(cfg)[0]
    img = os.path.join(cfg["istage"], "img", c["stem"] + ".cftp")
    tail = ["--image", img, "--runs", c["runs"], "--init", c["init"], "--lanes", str(c["lanes"])]
    Rc = jrun_desktop(cfg, tail, od, "stop", ["--expect-device", "NVIDIA GeForce RTX 5060 Ti"])
    left = sorted(fn for fn in os.listdir(od) if fn.startswith("stop."))
    log.check(Rc.rc == 5 and Rc.device == "none" and Rc.image is None and left == ["stop.open.txt", "stop.stdout.txt"],
              "(c) --expect-device on the software executor: exit %s, device line %r, image line %s, files %s" % (
                  Rc.rc, Rc.device, Rc.image is not None, left))
    # (d) the abort
    Rd = jrun_desktop(cfg, tail, od, "abort", ["--abort-ms", "0.000001"])
    pv = prov_read(Rd.pre + ".prov.txt")
    log.check(Rd.rc == 6 and Rd.abort is not None and pv.get("status", "").startswith("ABORTED") and len(Rd.segs) == 2
              and rep_int(Rd, "calls") == 2, "(d) --abort-ms 0.000001: exit %s, %d segment lines, calls %s, ABORT %r, "
              "provenance %r" % (Rd.rc, len(Rd.segs), Rd.rep.get("calls"), Rd.abort, pv.get("status")))
    # (e) mode load
    imgs = [os.path.join(img_dir(cfg, 1), "%s-%s.cftp" % (sysn, fmt)) for sysn in I1_SYSTEMS for fmt in FMT4] + \
           [os.path.join(img_dir(cfg, s), "program-d7-%s.cftp" % fmt) for s in (2, 4, 8) for fmt in FMT3]
    argv = [exe(os.path.join(cfg["build"], "j_run")), "load", "--depth", str(DEPTH), "--out", os.path.join(od, "load")]
    for p in imgs:
        argv += ["--image", p]
    Re = run_proc(argv, os.path.join(od, "load.stdout.txt"), timeout_s=600)
    nok = sum(1 for x in Re.loads if " status CFT_OK " in x)
    log.check(Re.rc == 0 and nok == len(imgs) == 41, "(e) mode load: %d of %d images CFT_OK, exit %s" % (nok, len(imgs), Re.rc))
    bad = bytearray(read(imgs[0]))
    bad[0] ^= 0x01
    bp = os.path.join(od, "corrupt.cftp")
    write_new(bp, bytes(bad))
    Rb = run_proc([exe(os.path.join(cfg["build"], "j_run")), "load", "--depth", str(DEPTH), "--out",
                   os.path.join(od, "loadbad"), "--image", bp], os.path.join(od, "loadbad.stdout.txt"), timeout_s=600)
    log.check(Rb.rc == 3 and Rb.loads and " status CFT_OK " not in Rb.loads[0], "(e) a copy with one header byte changed: "
              "exit %s, %s" % (Rb.rc, Rb.loads[0][-90:] if Rb.loads else "-"))
    cpu.close()
    sys.exit(1 if log.close() else 0)


BUILDGATE_CRIT = """build_j.sh's refusals, on the desktop (its gpu mode cannot build here; this shows it will not start without
its settings): bash tests/build_j.sh gpu <work> <archive> <tests> must exit non-zero with "CRITERION G0 FAILED" and build
nothing (no work folder made) (1) with none of HIP, HIP_PLATFORM, HIP_ROOT, HIP_ARCH, HIP_CUDA given; (2) with all but
HIP_CUDA; (3) with HIP_PLATFORM=amd; (4) with all five given and a HIP_ROOT holding no bin/hipcc; and each of (1) to (3)
prints every setting it was given."""


def mode_buildgate(cfg, a):
    log = i_lib.Log(cfg["logs"], "buildgate", SCRIPT, [BUILDGATE_CRIT], keep_dir=cfg["kept"], modules=MODULES)
    bash = "C:/msys64/usr/bin/bash.exe"
    sh = os.path.join(HERE, "build_j.sh").replace("\\", "/")
    work = os.path.join(cfg["work"], "buildgate-never-made").replace("\\", "/")
    tar = os.path.join(cfg["tools"], "cft-fp256-9e8ff270.tar").replace("\\", "/")
    full = {"HIP": "1", "HIP_PLATFORM": "nvidia", "HIP_ROOT": "/nonexistent/hip-root", "HIP_ARCH": "120",
            "HIP_CUDA": "/nonexistent/cuda"}       # placeholders: no other session's path is written here
    cases = [("none given", {}), ("HIP_CUDA missing", {k: v for k, v in full.items() if k != "HIP_CUDA"}),
             ("HIP_PLATFORM amd", dict(full, HIP_PLATFORM="amd")),
             ("no hipcc under HIP_ROOT", dict(full, HIP_ROOT=os.path.join(cfg["work"], "no-such-rocm").replace("\\", "/")))]
    for name, env_add in cases:
        env = {k: v for k, v in os.environ.items() if k not in full}
        env.update(env_add)
        r = subprocess.run([bash, sh, "gpu", work, tar, os.path.join(HERE).replace("\\", "/")], capture_output=True,
                           text=True, env=env, timeout=120)
        out = redact(cfg, r.stdout + r.stderr)
        printed = all(("G0: %s=%s" % (k, v)) in out for k, v in env_add.items()) if name != "no hipcc under HIP_ROOT" else True
        log.check(r.returncode != 0 and "CRITERION G0 FAILED" in out and not os.path.exists(work) and printed,
                  "(%s) build_j.sh gpu: exit %d, %s; settings printed: %s; work folder made: %s" % (
                      name, r.returncode, [ln for ln in out.splitlines() if "G0" in ln][-1:], printed, os.path.exists(work)))
    sys.exit(1 if log.close() else 0)


# ------------------------------------------------------------------ the lanes: the base, I3's 64, C-J1, J3's 16

def bc_slot_of(cfg, fmt):
    _m, nst, nscr, names = manifest_state(cfg, "program-d7-%s" % fmt)
    if [n for n, s in sorted(names.items(), key=lambda x: x[1])][:7] != ["t", "x", "y", "z", "vx", "vy", "vz"]:
        raise SystemExit("the state is not t, x, y, z, vx, vy, vz")
    return names["bc"], nst, nscr


def build_base(cfg, fmt, log):
    """DEBRIS-H's 2,688 seed objects, in seed index order, as INIT rows at fmt (t = T_s, the state, bc; the shared lane
    params 0), checked byte for byte against DEBRIS-I's I3 batches and I5 workers, which hold 2,368 of them."""
    rows = seed_rows(cfg["seed"])
    T_s = rows[0][1]
    bc, nst, nscr = bc_slot_of(cfg, fmt)
    lane = nscr * ESZ[fmt]
    base = b"".join(init_row(r, fmt, nscr, nst, bc, T_s) for r in rows)
    plan = json.load(open(os.path.join(cfg["istage"], "i3", "plan.json"), "rb"))
    checked = bad = 0
    for bt in plan["batches"]:
        ib = read(os.path.join(cfg["istage"], "i3", bt["init"][fmt]))
        for k, idx in enumerate(bt["idx"]):
            checked += 1
            bad += ib[k * lane:(k + 1) * lane] != base[idx * lane:(idx + 1) * lane]
    for w in range(36):
        ib = read(os.path.join(cfg["istage"], "i5", "init-%s-w%02d.bin" % (fmt, w)))
        for k in range(64):
            checked += 1
            bad += ib[k * lane:(k + 1) * lane] != base[(64 * w + k) * lane:(64 * w + k + 1) * lane]
    log.check(bad == 0 and checked == 64 + 2304 and len(rows) == 2688,
              "the base at %s: %d seed objects (T_s %s), rows of %d bytes; %d of its rows checked against DEBRIS-I's I3 and "
              "I5 INIT files, %d differ; SHA-256 %s" % (fmt, len(rows), float(T_s).hex(), lane, checked, bad,
                                                         i_lib.sha256_bytes(base)))
    return base, rows, lane


def j3_lanes():
    """J3's lanes are the base less seed index 1595 (positions 0..2686); the 16 checked lanes, drawn before any run."""
    order = [i for i in range(2688) if i != J3_EXCLUDE]
    draw = sorted(random.Random(J3_DRAW_SEED).sample(range(len(order)), 16))
    return order, draw


def plant_up(word_bytes):
    """One unit in the last place up (toward +infinity) on an encoding: +1 if the sign is clear, -1 if set (non-zero)."""
    v = int.from_bytes(word_bytes, "little")
    top = 1 << (8 * len(word_bytes) - 1)
    v = v + 1 if not v & top else v - 1
    return v.to_bytes(len(word_bytes), "little")


def init64(cfg, fmt):
    plan = json.load(open(os.path.join(cfg["istage"], "i3", "plan.json"), "rb"))
    return b"".join(read(os.path.join(cfg["istage"], "i3", bt["init"][fmt])) for bt in plan["batches"]), plan


def cj1_init(cfg):
    b, plan = init64(cfg, "fp256")
    _bc, nst, nscr = bc_slot_of(cfg, "fp256")
    lane = nscr * 32
    o = CJ1_LANE * lane + CJ1_WORD * 32
    out = bytearray(b)
    out[o:o + 32] = plant_up(b[o:o + 32])
    return bytes(out)


def j1b_compare(got, n, nst, esz, N, nseg_runs, kept_every, boxes, nrec=None):
    """J1(b)'s comparison: the card's 64-lane file reduced to its 40-step boundaries, each batch's 8 lanes against the
    box's file for that batch. Returns [(batch, record, run, seg, lane in batch, kind)] and the records compared."""
    red = reduce40(got, n, nst, esz, N, nseg_runs, kept_every=kept_every)
    diffs, ncmp = [], 0
    for b, box in enumerate(boxes):
        sl = lane_slice(red, n, nst, esz, list(range(8 * b, 8 * b + 8)))
        d, k = compare40(sl, box, 8, nst, esz, "batch %d" % b, nrec=nrec)
        ncmp += k
        diffs += [(b,) + x for x in d]
    return diffs, ncmp


CONTROLS_CRIT = """The controls C-J1 to C-J3 on the desktop (libcft's software executor, j_run, depth 512), each stated before
its data and each required to FAIL its comparison as given; a control that does not fail as specified is reported
as failed.
C-J1: I3's 64 lanes at binary256 (DEBRIS-I's 8 batch INIT files joined in batch order), lane 21 (batch 2, lane 5) with
    its x (state word 1) one unit in the last place up (toward +infinity), for I3's first hour (6 segments of 40
    steps), compared at each 40-step boundary with the box's files (ledger debris-i/box/out/i3/prog-fp256-b*.seg.bin,
    their first 6 records): the lane-boundaries that differ must be exactly lane 21 at all 6 boundaries (its state),
    and every other lane equal, state and lane byte.
C-J2: I1's program at degree 2 against degree 7 (E1's s = 1 outputs, the same 16 lanes of the test seed, the same 4
    boundaries of 40 steps, REDUCE'd), at binary32, 64, 128 and 256: every lane's state must differ at every boundary.
C-J3: the J1(b) comparison of a 64-lane binary64 day made by joining the box's 8 batch files lane by lane (40-step
    records) against the box's files: 0 differences; then against the same files with one byte flipped in a copy of
    batch 3's file (record 77, lane 2's x, byte 3): it must report exactly batch 3, record 77, lane 2, and nothing
    else."""


def mode_controls(cfg, a):
    log = i_lib.Log(cfg["logs"], "controls", SCRIPT, [CONTROLS_CRIT], keep_dir=cfg["kept"], modules=MODULES)
    cpu = i_lib.Cpu("controls", os.path.join(cfg["scratch"], "cpu.tsv"))
    od = os.path.join(cfg["desk"], "controls")
    if os.path.exists(od):
        raise SystemExit("%s exists" % od)
    os.makedirs(od)
    # C-J1
    plan = json.load(open(os.path.join(cfg["istage"], "i3", "plan.json"), "rb"))
    rb = read(os.path.join(cfg["istage"], "i3", plan["runs"]["fp256"]))
    one = runs_derive(rb, nruns=1)
    p1 = runs_parse(one)
    rp = os.path.join(od, "cj1.runs.bin")
    write_new(rp, one)
    ip = os.path.join(od, "cj1.init.bin")
    write_new(ip, cj1_init(cfg))
    base64, _p = init64(cfg, "fp256")
    planted = read(ip)
    nd = sum(1 for i in range(len(base64)) if base64[i] != planted[i])
    log.w("C-J1's INIT: %d bytes differ from the joined batches (lane %d, word %d); INIT %s" % (
        nd, CJ1_LANE, CJ1_WORD, i_lib.sha256_file(ip)))
    R = jrun_desktop(cfg, ["--image", os.path.join(img_dir(cfg, 40), "program-d7-fp256.cftp"), "--runs", rp, "--init", ip,
                           "--lanes", "64", "--seg-steps", "40"], od, "cj1")
    boxes = [read(os.path.join(cfg["ibox"], "prog-fp256-b%d.seg.bin" % b)) for b in range(8)]
    diffs, ncmp = j1b_compare(read(R.pre + ".seg.bin"), 64, p1["nst"], 32, 1, p1["nseg"], 1, boxes, nrec=6)
    want = [(CJ1_LANE, k) for k in range(1, 7)]
    lanes_hit = sorted(set((8 * d[0] + d[4], d[3]) for d in diffs))
    kinds = sorted(set(d[5].split()[0] for d in diffs))
    log.check(R.rc == 0 and lanes_hit == want and kinds == ["state"],
              "C-J1 (control) one ulp in lane 21's x: the differing (lane, boundary) pairs are %s (wanted %s), kinds %s, "
              "over %d records compared: the comparison FAILS where it must, and only there" % (
                  lanes_hit[:8], want, kinds, ncmp))
    # C-J2
    e1 = os.path.join(cfg["desk"], "e1")
    for fmt in FMT4:
        c7 = [x for x in i1_cases(cfg) if x["case"] == "i1-program-d7-%s" % fmt][0]
        c2 = [x for x in i1_cases(cfg) if x["case"] == "i1-program-d2-%s" % fmt][0]
        p7, p2 = runs_parse(read(c7["runs"])), runs_parse(read(c2["runs"]))
        r7 = reduce40(read(os.path.join(e1, c7["case"] + ".s1.seg.bin")), 16, p7["nst"], p7["esz"], 40,
                      [x * 40 for x in p7["nseg"]])
        r2 = reduce40(read(os.path.join(e1, c2["case"] + ".s1.seg.bin")), 16, p2["nst"], p2["esz"], 40,
                      [x * 40 for x in p2["nseg"]])
        d, ncmp = compare40(r2, r7, 16, p7["nst"], p7["esz"], "d2/d7")
        st = set((x[0], x[3]) for x in d if x[4] == "state")
        log.check(len(st) == 16 * ncmp and ncmp == 4, "C-J2 (control) %s: degree 2 against degree 7, %d of %d lane-boundaries"
                  " differ in state (all must)" % (fmt, len(st), 16 * ncmp))
    # C-J3
    nst, esz = 7, 8
    boxes = [read(os.path.join(cfg["ibox"], "prog-fp64-b%d.seg.bin" % b)) for b in range(8)]
    recs = [seg_records(bx, 8, nst, esz) for bx in boxes]
    joined = bytearray()
    for i in range(len(recs[0])):
        r, s = struct.unpack_from("<2I", boxes[0], recs[0][i][2] - 8)
        joined += struct.pack("<2I", r, s)
        for b in range(8):
            joined += boxes[b][recs[b][i][2]:recs[b][i][3]]
        for b in range(8):
            joined += boxes[b][recs[b][i][3]:recs[b][i][3] + 8]
    nseg = [6] * 24
    d0, n0 = j1b_compare(bytes(joined), 64, nst, esz, 1, nseg, 1, boxes)
    log.check(not d0 and n0 == 8 * 144, "C-J3 (its base) the joined box day against the box's files: %d differences in %d "
              "records" % (len(d0), n0))
    flip = [bytearray(x) for x in boxes]
    o = recs[CJ3_BATCH][CJ3_REC][2] - 8 + CJ3_BYTE
    flip[CJ3_BATCH][o] ^= 0x01
    d1, n1 = j1b_compare(bytes(joined), 64, nst, esz, 1, nseg, 1, [bytes(x) for x in flip])
    r77, s77 = struct.unpack_from("<2I", boxes[CJ3_BATCH], recs[CJ3_BATCH][CJ3_REC][2] - 8)
    log.check([(x[0], x[1], x[4]) for x in d1] == [(CJ3_BATCH, CJ3_REC, 2)],
              "C-J3 (control) one byte flipped in a copy of batch 3's file (record %d = run %d, segment %d; lane 2's x): the "
              "comparison reports %s, and must report exactly that" % (CJ3_REC, r77, s77, [x[:5] for x in d1][:4]))
    cpu.close()
    sys.exit(1 if log.close() else 0)


J3REF_CRIT = """j3ref: the desktop's replays for J3's check, fixed before any card run: J3's lanes are DEBRIS-H's 2,688 seed
objects less seed index 1595 (2,687, in seed index order); 16 of them drawn by random.Random(20261124).sample(range(2687),
16), sorted; each replayed on libcft's software executor (j_run, no artifact, depth 512) for the whole day of I3's runs
(24 one-hour runs of 6 segments of 40 steps from DEBRIS-H's T_s) at binary64 and binary256, the 40-step image
(DEBRIS-I's program at degree 7, recompiled here, its SHA-256 DEBRIS-I's), keeping every boundary. Asserted: each INIT
row is the base's (itself checked against DEBRIS-I's INIT files); every run exits 0; outputs' SHA-256 logged; marks
counted. The outputs are per-object states: the ledger's debris-j/desktop/j3ref/."""


def mode_j3ref(cfg, a):
    log = i_lib.Log(cfg["logs"], "j3ref", SCRIPT, [J3REF_CRIT], keep_dir=cfg["kept"], modules=MODULES)
    cpu = i_lib.Cpu("j3ref", os.path.join(cfg["scratch"], "cpu.tsv"))
    od = os.path.join(cfg["desk"], "j3ref")
    if os.path.exists(od):
        raise SystemExit("%s exists" % od)
    os.makedirs(od)
    order, draw = j3_lanes()
    log.w("J3's lanes: %d (seed indices 0..2687 less %d); the 16 drawn positions %s = seed indices %s" % (
        len(order), J3_EXCLUDE, draw, [order[p] for p in draw]))
    plan = json.load(open(os.path.join(cfg["istage"], "i3", "plan.json"), "rb"))
    fmts = a.formats.split(",") if a.formats else ["fp64", "fp256"]
    for fmt in fmts:
        base, rows, lane = build_base(cfg, fmt, log)
        ib = b"".join(base[order[p] * lane:(order[p] + 1) * lane] for p in draw)
        ip = os.path.join(od, "j3ref-%s.init.bin" % fmt)
        write_new(ip, ib)
        rp = os.path.join(cfg["istage"], "i3", plan["runs"][fmt])
        R = jrun_desktop(cfg, ["--image", os.path.join(img_dir(cfg, 40), "program-d7-%s.cftp" % fmt), "--runs", rp, "--init",
                               ip, "--lanes", "16", "--seg-steps", "40"], od, "j3ref-%s" % fmt)
        log.check(R.rc == 0 and rep_int(R, "segments") == 144,
                  "j3ref %s: 16 lanes, %s segments, marks %s, INIT %s, runs %s, output %s" % (
                      fmt, R.rep.get("segments"), R.rep.get("marks"), i_lib.sha256_file(ip), i_lib.sha256_file(rp),
                      i_lib.sha256_file(R.pre + ".seg.bin") if R.rc == 0 else "-"))
    cpu.close()
    sys.exit(1 if log.close() else 0)


# ------------------------------------------------------------------ the GPU's run folder

STAGE_CRIT = """stage: the GPU's run folder in/ (written once: refused if it exists), every file listed in in/EXPECTED.sha256:
tests/ (j_harness.py, i_lib.py, j_run.c, build_j.sh, j_gpu.sh: LF only, no CR byte), the archive cft-fp256-9e8ff270.tar
(its SHA-256 7814576d...), img/ (the 41 short images of the round: I1's 32 systems at s = 1 and the program at degree 7
at s = 2, 4, 8 at three formats, each image's REPEAT count parsed and equal to its folder's s), i1/ (I1's 32 cases: the
s = 1 runs file, E1's, and DEBRIS-I's INIT), i3/ (I3's day runs file at each s, 24 one-hour runs of 6 x 40 / s
segments; the 8 batches' INIT files joined at each format; C-J1's planted INIT; the box's 24 I3 files, each SHA-256
the box's own MANIFEST's), base/ (the 2,688 seed objects at each format), j3/ (J3's 16 lanes' desktop replays), and
plan.json (each derived file's SHA-256 too). Asserted: every s-step runs file is the 40-step one with nseg x 40 / s and
no other byte changed; I3's 8 batches ran one runs file a format (the box's stdout names one SHA-256 for all 8); E1's
s = 1 outputs are the references of J1(a) (e1_s1_outputs.json)."""


def box_manifest(cfg):
    m = {}
    for line in open(os.path.join(cfg["ledger"], "debris-i", "box", "MANIFEST.box-001.sha256"), encoding="ascii"):
        h, rel = line.split(None, 1)
        m[rel.strip().lstrip("*")] = h
    return m


def mode_stage(cfg, a):
    import shutil
    root = os.path.join(cfg["dj"], "gpu-stage", a.run)
    ind = os.path.join(root, "in")
    if os.path.exists(root):
        raise SystemExit("%s exists: stage writes a new folder only" % root)
    log = i_lib.Log(cfg["logs"], "stage", SCRIPT, [STAGE_CRIT], keep_dir=cfg["kept"], modules=MODULES)
    cpu = i_lib.Cpu("stage", os.path.join(cfg["scratch"], "cpu.tsv"))
    for d in ("tests", "img/s1", "img/s2", "img/s4", "img/s8", "i1", "i3/box", "base", "j3"):
        os.makedirs(os.path.join(ind, d))
    plan = {"round": "DEBRIS-J", "run": a.run, "depth": DEPTH, "short_s": list(SHORT_S), "formats": list(FMT3),
            "seg40": SEG40, "h_step": H_STEP, "chunk": CHUNK, "abort_ms": ABORT_MS, "stop_ms": STOP_MS,
            "warmup_lanes": WARMUP_LANES}
    # tests
    for n in ("j_harness.py", "i_lib.py", "j_run.c", "build_j.sh", "j_gpu.sh"):
        b = read(os.path.join(HERE, n))
        if b"\r" in b:
            raise SystemExit("tests/%s holds a CR byte" % n)
        write_new(os.path.join(ind, "tests", n), b)
    log.w("tests: j_harness.py %s, i_lib.py %s, j_run.c %s, build_j.sh %s, j_gpu.sh %s (no CR byte in any)" % tuple(
        i_lib.sha256_file(os.path.join(ind, "tests", n))[:16]
        for n in ("j_harness.py", "i_lib.py", "j_run.c", "build_j.sh", "j_gpu.sh")))
    # the archive
    tp = os.path.join(cfg["tools"], "cft-fp256-9e8ff270.tar")
    if i_lib.sha256_file(tp) != "7814576d5d4d23fa4c1797553a32cd19b4e1d4c8f2d67fb7faecc9cfecb1c4bb":
        raise SystemExit("the archive is not lead.md's")
    shutil.copyfile(tp, os.path.join(ind, "cft-fp256-9e8ff270.tar"))
    # the images
    imgs, img_s, prog = [], {}, {f: {} for f in FMT3}
    for sysn in I1_SYSTEMS:
        for fmt in FMT4:
            imgs.append(("img/s1/%s-%s.cftp" % (sysn, fmt), img_dir(cfg, 1), "%s-%s" % (sysn, fmt), 1))
    for s in (2, 4, 8):
        for fmt in FMT3:
            imgs.append(("img/s%d/program-d7-%s.cftp" % (s, fmt), img_dir(cfg, s), "program-d7-%s" % fmt, s))
    for rel, d, stem, s in imgs:
        b = read(os.path.join(d, stem + ".cftp"))
        p = image_parse(b)
        if len(p["repeats"]) != 1 or p["repeats"][0][1] != s:
            raise SystemExit("%s: its REPEAT count is not %d" % (rel, s))
        write_new(os.path.join(ind, rel), b)
        img_s[rel] = s
        if stem.startswith("program-d7-") and p["format"] in FMT3:
            prog[p["format"]][str(s)] = rel
    plan["images"], plan["image_s"], plan["all_images"] = prog, img_s, [x[0] for x in imgs]
    log.check(len(imgs) == 41 and all(len(prog[f]) == 4 for f in FMT3), "img: %d images, the program at s = 1, 2, 4, 8 at "
              "each of %s" % (len(imgs), ", ".join(FMT3)))
    # I1's cases at s = 1
    e1 = os.path.join(cfg["desk"], "e1")
    e1out = json.load(open(os.path.join(e1, "e1_s1_outputs.json"), "rb"))
    cases = []
    for c in i1_cases(cfg):
        r1 = read(os.path.join(e1, c["case"] + ".s1.runs.bin"))
        if r1 != runs_derive(read(c["runs"]), mult=40):
            raise SystemExit("%s: E1's s = 1 runs file is not the 40-step one x 40" % c["case"])
        write_new(os.path.join(ind, "i1", c["case"] + ".s1.runs.bin"), r1)
        shutil.copyfile(c["init"], os.path.join(ind, "i1", c["case"] + ".init.bin"))
        o = e1out[c["case"]]
        if o["reduced"] != c["r1"]:
            raise SystemExit("%s: E1's reduced hash is not R1's" % c["case"])
        rp = runs_parse(r1)
        cases.append({"case": c["case"], "image": "img/s1/%s.cftp" % c["stem"], "fmt": c["fmt"], "lanes": c["lanes"],
                      "runs": "i1/%s.s1.runs.bin" % c["case"], "init": "i1/%s.init.bin" % c["case"], "nst": rp["nst"],
                      "esz": rp["esz"], "nseg": rp["nseg"], "seg_sha256": o["seg"], "marks_sha256": o["marks"],
                      "r1": c["r1"]})
    plan["i1"] = cases
    log.check(len(cases) == 32, "i1: %d cases, each with E1's s = 1 output SHA-256 as J1(a)'s reference" % len(cases))
    # I3
    ip = json.load(open(os.path.join(cfg["istage"], "i3", "plan.json"), "rb"))
    bm = box_manifest(cfg)
    i3 = {"runs": {}, "init64": {}, "box": {}, "nruns": 24, "seg_per_run": 6, "T_s": ip["T_s"], "batches": 8,
          "nst": 7, "nscr": {}, "esz": {f: ESZ[f] for f in FMT3}}
    for fmt in FMT3:
        shas = set()
        for b in range(8):
            for ln in open(os.path.join(cfg["ibox"], "prog-%s-b%d.stdout.txt" % (fmt, b)), "rb"):
                w = ln.decode("ascii", "replace").split()
                if w and w[0] == "runs":
                    shas.add(w[3])
        rb = read(os.path.join(cfg["istage"], "i3", ip["runs"][fmt]))
        log.check(shas == {i_lib.sha256_bytes(rb)}, "i3 %s: the box's 8 batches ran one runs file, %s" % (
            fmt, sorted(shas)[0][:16] if len(shas) == 1 else shas))
        i3["runs"][fmt] = {}
        for s in SHORT_S:
            d = runs_derive(rb, mult=SEG40 // s)
            rel = "i3/day-%s-s%d.runs.bin" % (fmt, s)
            write_new(os.path.join(ind, rel), d)
            i3["runs"][fmt][str(s)] = rel
        b64, _p = init64(cfg, fmt)
        rel = "i3/init64-%s.bin" % fmt
        write_new(os.path.join(ind, rel), b64)
        i3["init64"][fmt] = rel
        i3["nscr"][fmt] = runs_parse(rb)["nscr"]
        i3["box"][fmt] = []
        for b in range(8):
            fn = "prog-%s-b%d.seg.bin" % (fmt, b)
            src = os.path.join(cfg["ibox"], fn)
            if i_lib.sha256_file(src) != bm.get("out/i3/" + fn):
                raise SystemExit("%s is not the box's MANIFEST's" % fn)
            shutil.copyfile(src, os.path.join(ind, "i3", "box", fn))
            i3["box"][fmt].append("i3/box/" + fn)
    write_new(os.path.join(ind, "i3", "cj1-init64-fp256.bin"), cj1_init(cfg))
    i3["cj1"] = {"init": "i3/cj1-init64-fp256.bin", "lane": CJ1_LANE, "word": CJ1_WORD, "fmt": "fp256"}
    i3["cj3"] = {"fmt": "fp64", "batch": CJ3_BATCH, "record": CJ3_REC, "byte": CJ3_BYTE}
    plan["i3"] = i3
    # the base, J0c's slices, J3's lanes
    order, draw = j3_lanes()
    plan["base"], plan["j0c"], plan["j3"] = {}, {"init8": {}, "init2048": {}}, {
        "exclude": J3_EXCLUDE, "lanes": len(order), "draw_seed": J3_DRAW_SEED, "draw": draw,
        "seed_idx": [order[p] for p in draw], "ref": {}, "init_sha256": {}}
    for fmt in FMT3:
        base, rows, lane = build_base(cfg, fmt, log)
        rel = "base/base-%s.init.bin" % fmt
        write_new(os.path.join(ind, rel), base)
        plan["base"][fmt] = {"path": rel, "lanes": len(rows), "lane_bytes": lane, "sha256": i_lib.sha256_bytes(base)}
        plan["j0c"]["init8"][fmt] = i_lib.sha256_bytes(base[:8 * lane])
        plan["j0c"]["init2048"][fmt] = i_lib.sha256_bytes(base[:2048 * lane])
        plan["j3"]["init_sha256"][fmt] = i_lib.sha256_bytes(b"".join(base[i * lane:(i + 1) * lane] for i in order))
    jd = os.path.join(cfg["desk"], "j3ref")
    for fmt in ("fp64", "fp256"):
        for suf, key in ((".seg.bin", "seg"), (".init.bin", "init")):
            src = os.path.join(jd, "j3ref-%s%s" % (fmt, suf))
            rel = "j3/ref-%s%s" % (fmt, suf)
            shutil.copyfile(src, os.path.join(ind, rel))
            plan["j3"]["ref"].setdefault(fmt, {})[key] = rel
        base = read(os.path.join(ind, plan["base"][fmt]["path"]))
        lane = plan["base"][fmt]["lane_bytes"]
        want = b"".join(base[order[p] * lane:(order[p] + 1) * lane] for p in draw)
        log.check(read(os.path.join(ind, plan["j3"]["ref"][fmt]["init"])) == want,
                  "j3 %s: the desktop replay's INIT is the 16 drawn lanes of the base" % fmt)
    log.w("J3: %d lanes (the base less seed index %d); drawn positions %s (seed indices %s)" % (
        len(order), J3_EXCLUDE, draw, plan["j3"]["seed_idx"]))
    plan["j2"] = {"batches": [512, 2048, 8192, 32768], "min_s": 60.0, "max_s": 180.0}
    with open(os.path.join(ind, "plan.json"), "x", encoding="ascii", newline="\n") as f:
        json.dump(plan, f, indent=1, sort_keys=True)
    # EXPECTED
    lines = []
    for dp, _dn, fns in os.walk(ind):
        for fn in sorted(fns):
            pth = os.path.join(dp, fn)
            lines.append("%s  %s" % (i_lib.sha256_file(pth), os.path.relpath(pth, ind).replace("\\", "/")))
    lines.sort(key=lambda x: x.split("  ", 1)[1])
    with open(os.path.join(ind, "EXPECTED.sha256"), "x", encoding="ascii", newline="\n") as f:
        f.write("\n".join(lines) + "\n")
    tot = sum(os.path.getsize(os.path.join(dp, fn)) for dp, _dn, fns in os.walk(ind) for fn in fns)
    log.w("staged %d files, %d bytes, in <ledger>/debris-j/gpu-stage/%s/in; plan.json %s; EXPECTED.sha256 %s" % (
        len(lines), tot, a.run, i_lib.sha256_file(os.path.join(ind, "plan.json")),
        i_lib.sha256_file(os.path.join(ind, "EXPECTED.sha256"))))
    cpu.close()
    sys.exit(1 if log.close() else 0)


# ------------------------------------------------------------------ the GPU modes (cft-gpu; standard library only)

def attempt_dir(out, name):
    """A mode's own output folder, out/<name>.<NNN>, the next free number: a mode run again never overwrites one."""
    k = 1
    while os.path.exists(os.path.join(out, "%s.%03d" % (name, k))):
        k += 1
    d = os.path.join(out, "%s.%03d" % (name, k))
    os.makedirs(d)
    return d, os.path.basename(d)


def latest_dir(out, name, need):
    """The highest-numbered out/<name>.<NNN> that holds the file `need`."""
    ks = sorted(int(fn.rsplit(".", 1)[1]) for fn in os.listdir(out) if fn.startswith(name + ".") and
                fn.rsplit(".", 1)[1].isdigit() and os.path.isfile(os.path.join(out, fn, need)))
    if not ks:
        raise SystemExit("no out/%s.NNN holds %s: run that mode first" % (name, need))
    return os.path.join(out, "%s.%03d" % (name, ks[-1]))


def gp_paths(root):
    p = {"root": root, "in": os.path.join(root, "in"), "build": os.path.join(root, "build"),
         "logs": os.path.join(root, "logs"), "out": os.path.join(root, "out"), "work": os.path.join(root, "work")}
    for k in ("logs", "out", "work"):
        os.makedirs(p[k], exist_ok=True)
    return p


def gp_expected(p, log):
    """B0: every file in in/EXPECTED.sha256 carries its SHA-256 (asserted before anything runs)."""
    bad, n = [], 0
    for line in read(os.path.join(p["in"], "EXPECTED.sha256")).decode("ascii").splitlines():
        h, rel = line.split(None, 1)
        rel = rel.strip().lstrip("*")
        n += 1
        f = os.path.join(p["in"], rel)
        if not os.path.isfile(f) or i_lib.sha256_file(f) != h:
            bad.append(rel)
    return log.check(not bad and n > 0, "B0 the %d staged files carry the SHA-256 of in/EXPECTED.sha256 (%d differ or "
                     "are missing%s)" % (n, len(bad), (": " + ", ".join(bad[:5])) if bad else ""))


class Gpu:
    """The card's context for one mode: the lock, nvidia-smi, the process list and j_run's runs, all inside cft-gpu.
    With --desktop-test, the same code runs on the desktop's software executor: no lock, no nvidia-smi, no ps, no
    artifact and no expected device (a functional test of the harness, never a measurement)."""

    def __init__(self, a, p, log):
        self.a, self.p, self.log = a, p, log
        self.test = bool(a.desktop_test)
        self.jrun = a.jrun if a.jrun else os.path.join(p["build"], "j_run")
        self.env = dict(os.environ)
        if not self.test:
            for k, v in (("CUDA_DEVICE_ORDER", "PCI_BUS_ID"), ("CUDA_VISIBLE_DEVICES", a.cuda_visible), ("CFT_HIP_INFO", "1")):
                if v is None or v == "":
                    raise SystemExit("--cuda-visible is required")
                self.env[k] = v
        self.held = None
        self.abort = float(a.test_abort_ms) if a.test_abort_ms else ABORT_MS
        self.stop = float(a.test_stop_ms) if a.test_stop_ms else STOP_MS
        if self.test:
            log.w("DESKTOP TEST: the GPU mode's code on the desktop's software executor (no lock, no nvidia-smi, no "
                  "artifact); every time below is a functional test's, never a measurement (abort %g ms, stop %g ms)" % (
                      self.abort, self.stop))

    def rel(self, path):
        return os.path.relpath(path, self.p["root"]).replace("\\", "/")

    def lock_take(self, label):
        if self.test:
            self.log.w("lock (%s): skipped, desktop test" % label)
            return
        import fcntl
        if not os.path.isfile(self.a.lock):
            raise SystemExit("the lock file %s does not exist: refused (this harness never creates it)" % self.a.lock)
        fd = os.open(self.a.lock, os.O_RDONLY)
        t0 = time.time()
        while True:
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except OSError:
                if time.time() - t0 > float(self.a.lock_wait):
                    os.close(fd)
                    raise SystemExit("the lock is held by another process after %s s: refused" % self.a.lock_wait)
                time.sleep(1.0)
        self.held = fd
        self.log.w("lock taken (%s) at %s, after %.1f s" % (label, time.strftime("%H:%M:%S"), time.time() - t0))

    def lock_drop(self, label):
        if self.test or self.held is None:
            return
        import fcntl
        fcntl.flock(self.held, fcntl.LOCK_UN)
        os.close(self.held)
        self.held = None
        self.log.w("lock released (%s) at %s" % (label, time.strftime("%H:%M:%S")))

    def smi(self, tag, settle=0.0):
        """nvidia-smi --query-gpu on the given index: name, memory used (MiB), utilisation (%), temperature, SM clock."""
        if self.test:
            return {"name": "desktop-test", "mem": 0, "util": 0, "line": "skipped"}
        if settle:
            time.sleep(settle)
        q = "index,name,memory.used,memory.total,utilization.gpu,temperature.gpu,clocks.sm,pstate"
        r = subprocess.run(["nvidia-smi", "--query-gpu=" + q, "--format=csv,noheader,nounits", "-i", str(self.a.smi_index)],
                           capture_output=True, text=True, timeout=60)
        line = r.stdout.strip()
        w = [x.strip() for x in line.split(",")]
        d = {"line": line, "rc": r.returncode}
        try:
            d.update({"index": int(w[0]), "name": w[1], "mem": int(w[2]), "mem_total": int(w[3]), "util": int(w[4]),
                      "temp": w[5], "sm_mhz": w[6], "pstate": w[7]})
        except (IndexError, ValueError):
            d.update({"name": None, "mem": None, "util": None})
        self.log.w("nvidia-smi %s: %s" % (tag, line))
        return d

    def ps(self):
        """Every other process whose command looks like GPU work (j_run, i_run, device-test, hip-test, cft-segrun, nvcc and
        the like): the list, logged; this harness and its parents excluded."""
        if self.test:
            return []
        r = subprocess.run(["ps", "-eo", "pid,ppid,etimes,pcpu,comm", "--no-headers"], capture_output=True, text=True,
                           timeout=60)
        mine = {os.getpid(), os.getppid()}
        hits = []
        for ln in r.stdout.splitlines():
            w = ln.split(None, 4)
            if len(w) < 5:
                continue
            pid, comm = int(w[0]), w[4].strip()
            if pid in mine:
                continue
            if any(k in comm for k in ("j_run", "i_run", "device-test", "hip-test", "hip_test", "hip-corpus", "cft-",
                                       "seqrun", "nvcc", "cicc", "ptxas", "hipcc", "cudafe")):
                hits.append("%s %s cpu %s%% up %s s" % (pid, comm, w[3], w[2]))
        self.log.w("processes like GPU work, other than this harness: %s" % (hits if hits else "none"))
        return hits

    def jrun_argv(self, mode, out_rel, extra):
        argv = [self.jrun, mode, "--depth", str(DEPTH), "--out", out_rel]
        if not self.test:
            argv += ["--artifact", "hip:0", "--expect-device", self.a.expect_device]
        return argv + list(extra)

    def run(self, tag, image, runs, init, lanes, s, keep_every, sub="", warm=WARMUP_LANES, abort=None):
        abort = self.abort if abort is None else abort
        od = os.path.join(self.p["out"], sub)
        os.makedirs(od, exist_ok=True)
        out_rel = self.rel(os.path.join(od, tag))
        extra = ["--image", self.rel(image), "--runs", self.rel(runs), "--init", self.rel(init), "--lanes", str(lanes),
                 "--seg-steps", str(s), "--keep-every", str(keep_every), "--warmup-lanes", str(warm),
                 "--abort-ms", "%g" % abort]
        argv = self.jrun_argv("run", out_rel, extra)
        R = run_proc(argv, os.path.join(od, tag + ".stdout.txt"), cwd=self.p["root"], env=self.env, watchdog_s=180)
        R.pre = os.path.join(od, tag)
        R.tag = tag
        self.log.w("run %s: exit %s%s, wall %.1f s; device %s; segments %s, calls %s, timed %s, marks %s; warm-up %s; "
                   "call max %s ms%s" % (
                       tag, R.rc, (" KILLED " + R.killed) if R.killed else "", R.wall, "line" if R.device and R.device != "none"
                       else R.device, R.rep.get("segments"), R.rep.get("calls"), R.rep.get("timed_calls"), R.rep.get("marks"),
                       (R.warmup or "-")[:48], "%.1f" % (rep_int(R, "call_max_ns", 0) / 1e6),
                       (" ABORT " + R.abort) if R.abort else ""))
        if R.rc not in (0, 6):
            self.log.w("  stderr: %s" % " | ".join(R.errs[-4:]))
        return R


def j0_info(p):
    jp = os.path.join(latest_dir(p["out"], "j0", "j0.json"), "j0.json")
    d = json.load(open(jp, "rb"))
    if not d.get("pass"):
        raise SystemExit("J0 did not pass: nothing runs on the card")
    d["_dir"] = os.path.basename(os.path.dirname(jp))
    return d


def device_fields(line):
    """The device line's fields J0 checks (backend_hip.cpp's format at 9e8ff270)."""
    d = {"name": None}
    if not line or not line.startswith("cft hip: "):
        return d
    head, _, rest = line.partition(" = ")
    d["artifact"] = head[len("cft hip: "):]
    d["name"] = rest.split(" (", 1)[0]
    d["arch"] = rest.split(" (", 1)[1].split(",", 1)[0] if " (" in rest else None
    d["platform"] = rest.split("HIP platform ", 1)[1].split(",", 1)[0] if "HIP platform " in rest else None
    d["visible"] = rest.split("; of ", 1)[1].split(" visible", 1)[0] if "; of " in rest else None
    d["cvd"] = rest.split("CUDA_VISIBLE_DEVICES=", 1)[1].split(";", 1)[0].split(",", 1)[0] if "CUDA_VISIBLE_DEVICES=" in rest \
        else None
    d["hip_arch"] = rest.split("HIP_ARCH ", 1)[1].split(",", 1)[0] if "HIP_ARCH " in rest else None
    return d


GPU_J0_CRIT = """gpu-j0: J0, the build and the device (cft-gpu, the lead's run; DEBRIS-J's plan, J0):
 B0 every staged file carries its SHA-256 (in/EXPECTED.sha256);
 B1 python3, flock, nvidia-smi, make and tar present; every j_run starts with CUDA_DEVICE_ORDER=PCI_BUS_ID,
    CUDA_VISIBLE_DEVICES=<given> and CFT_HIP_INFO=1;
 B2 tests/build_j.sh gpu, with HIP=1 HIP_PLATFORM=nvidia HIP_ROOT, HIP_ARCH and HIP_CUDA as given, builds libcft.a from
    the staged archive in <root>/build (hip-symcheck passing) and links j_run with the Makefile's NVIDIA libraries:
    "BUILD PASS (gpu)"; the j_run.c it compiled is the staged one (B0);
 then inside the lock, nvidia-smi read before and after and the processes listed, the controls first:
 C0a (control) j_run load --artifact hip:1 at depth 512: refused at cft_open_ex with CFT_ERR_NO_DEVICE (3), the runtime
    seeing 1 device ("sees 1 (");
 C0b (control) j_run load --artifact hip:0 at depth 4096: refused at cft_open_ex with CFT_ERR_UNSUPPORTED (2);
 C0c (control) j_run run --artifact hip:0 --expect-device <another card's name>: exit 5 after a device line, with no
    image line (stopped before any image loads);
 K1 j_run load --artifact hip:0 at depth 512 with --expect-device <the given name> on every image of the round (41):
    exit 0, every load CFT_OK, each image's SHA-256 the staged one;
 K2 its device line: the name exactly the given one, "of 1 visible", CUDA_VISIBLE_DEVICES the given value, HIP platform
    nvidia, HIP_ARCH the given value;
 K3 cft_get_caps: backend hip, seq_features 0x7ff1f, max_scratch 512;
 K4 nvidia-smi's index <given> names the given device before and after.
 J0 passes when every check passes; out/j0/j0.json then holds the device line and j_run's SHA-256 for later modes."""


def gpu_j0(a):
    p = gp_paths(os.path.abspath(a.root))
    log = i_lib.Log(p["logs"], "gpu_j0", SCRIPT, [GPU_J0_CRIT], keep_dir=None, modules=MODULES)
    if not gp_expected(p, log):
        sys.exit(log.close() or 1)
    plan = json.load(open(os.path.join(p["in"], "plan.json"), "rb"))
    G = Gpu(a, p, log)
    od, sub = attempt_dir(p["out"], "j0")
    log.w("this attempt's outputs: out/%s" % sub)
    import shutil
    tools = {t: shutil.which(t) for t in ("python3", "flock", "nvidia-smi", "make", "tar")}
    log.check(G.test or all(tools.values()), "B1 tools: %s" % ", ".join("%s %s" % kv for kv in sorted(tools.items())))
    log.w("B1 python %s; environment for j_run: %s" % (sys.version.split()[0], "desktop test" if G.test else
          "CUDA_DEVICE_ORDER=PCI_BUS_ID CUDA_VISIBLE_DEVICES=%s CFT_HIP_INFO=1" % a.cuda_visible))
    if not G.test:
        env = dict(os.environ)
        env.update({"HIP": "1", "HIP_PLATFORM": "nvidia", "HIP_ROOT": a.hip_root, "HIP_ARCH": a.hip_arch,
                    "HIP_CUDA": a.hip_cuda})
        bl = os.path.join(od, "build.txt")
        R = run_proc(["bash", os.path.join(p["in"], "tests", "build_j.sh"), "gpu", p["build"],
                      os.path.join(p["in"], "cft-fp256-9e8ff270.tar"), os.path.join(p["in"], "tests")], bl, env=env,
                     timeout_s=7200)
        for ln in R.lines + R.errs:
            log.w("  " + ln.replace(p["root"], "<root>"))
        ok = log.check(R.rc == 0 and "BUILD PASS (gpu)" in R.lines and any(
            ln.startswith("B3: tests/j_run.c ") and ln.split()[2] == i_lib.sha256_file(os.path.join(p["in"], "tests", "j_run.c"))
            for ln in R.lines), "B2 build_j.sh gpu: exit %s, BUILD PASS, j_run.c the staged one" % R.rc)
        if not ok:
            sys.exit(log.close() or 1)
    jsha = i_lib.sha256_file(G.jrun if os.path.isfile(G.jrun) else G.jrun + ".exe")
    log.w("j_run: %s" % jsha)
    one = os.path.join(p["in"], plan["all_images"][0])
    G.lock_take("j0")
    try:
        b = G.smi("before")
        G.ps()
        if G.test:
            log.w("C0a, C0b, C0c: the card's controls, not run in a desktop test")
        else:
            argv = [G.jrun, "load", "--artifact", "hip:1", "--depth", str(DEPTH), "--out", G.rel(os.path.join(od, "c0a")),
                    "--image", G.rel(one)]
            R = run_proc(argv, os.path.join(od, "c0a.stdout.txt"), cwd=p["root"], env=G.env, watchdog_s=180)
            e = " | ".join(R.errs)
            log.check(R.rc == 2 and "cft_open_ex:" in e and "(3):" in e and "sees 1 (" in e,
                      "C0a (control) hip:1: exit %s, %s" % (R.rc, e[-200:]))
            argv = [G.jrun, "load", "--artifact", "hip:0", "--depth", "4096", "--out", G.rel(os.path.join(od, "c0b")),
                    "--image", G.rel(one)]
            R = run_proc(argv, os.path.join(od, "c0b.stdout.txt"), cwd=p["root"], env=G.env, watchdog_s=180)
            e = " | ".join(R.errs)
            log.check(R.rc == 2 and "cft_open_ex:" in e and "(2):" in e, "C0b (control) depth 4096: exit %s, %s" % (
                R.rc, e[-200:]))
            c = plan["i1"][0]
            argv = [G.jrun, "run", "--artifact", "hip:0", "--depth", str(DEPTH), "--expect-device", a.other_device,
                    "--out", G.rel(os.path.join(od, "c0c")), "--image", G.rel(os.path.join(p["in"], c["image"])), "--runs",
                    G.rel(os.path.join(p["in"], c["runs"])), "--init", G.rel(os.path.join(p["in"], c["init"])), "--lanes",
                    str(c["lanes"])]
            R = run_proc(argv, os.path.join(od, "c0c.stdout.txt"), cwd=p["root"], env=G.env, watchdog_s=180)
            log.check(R.rc == 5 and R.device and R.device.startswith("cft hip: hip:0 = ") and R.image is None,
                      "C0c (control) --expect-device \"%s\": exit %s, device line %s, image line %s" % (
                          a.other_device, R.rc, "present" if R.device else "absent", R.image is not None))
        argv = G.jrun_argv("load", G.rel(os.path.join(od, "k1")), [])
        for rel in plan["all_images"]:
            argv += ["--image", G.rel(os.path.join(p["in"], rel))]
        R = run_proc(argv, os.path.join(od, "k1.stdout.txt"), cwd=p["root"], env=G.env, watchdog_s=180)
        exp = {}
        for line in read(os.path.join(p["in"], "EXPECTED.sha256")).decode("ascii").splitlines():
            h, rel = line.split(None, 1)
            exp[rel.strip()] = h
        good = [x for x in R.loads if " status CFT_OK " in x and x.split()[2] == exp.get(x.split()[0][3:])]
        log.check(R.rc == 0 and len(good) == len(plan["all_images"]) == 41,
                  "K1 every image of the round loads at depth 512: %d of %d CFT_OK with the staged SHA-256, exit %s" % (
                      len(good), len(plan["all_images"]), R.rc))
        df = device_fields(R.device)
        if G.test:
            log.w("K2 device line: %s (desktop test: the software executor prints none)" % R.device)
        else:
            log.check(df["name"] == a.expect_device and df.get("visible") == "1" and df.get("cvd") == a.cuda_visible and
                      df.get("platform") == "nvidia" and df.get("hip_arch") == a.hip_arch,
                      "K2 device line: name %r, arch %s, %s visible, CUDA_VISIBLE_DEVICES %s, platform %s, HIP_ARCH %s" % (
                          df["name"], df.get("arch"), df.get("visible"), df.get("cvd"), df.get("platform"), df.get("hip_arch")))
        cw = (R.caps or "").split()
        want_backend = "software" if G.test else "hip"
        log.check(len(cw) >= 6 and cw[1] == want_backend and cw[3] == "0x7ff1f" and cw[5] == str(DEPTH),
                  "K3 caps: %s" % R.caps)
        aft = G.smi("after", settle=2.0)
        if not G.test:
            log.check(b.get("name") == a.expect_device and aft.get("name") == a.expect_device,
                      "K4 nvidia-smi index %s names %r before and %r after" % (a.smi_index, b.get("name"), aft.get("name")))
    finally:
        G.lock_drop("j0")
    passed = log.fails == 0
    with open(os.path.join(od, "j0.json"), "w", encoding="ascii", newline="\n") as f:
        json.dump({"pass": passed, "device": R.device, "j_run_sha256": jsha, "desktop_test": G.test,
                   "time": time.strftime("%Y-%m-%d %H:%M:%S %z")}, f, indent=1)
    log.w("J0 %s; out/%s/j0.json written" % ("PASS" if passed else "FAIL", sub))
    sys.exit(1 if log.close() else 0)


def slice_lanes(src, lane, lanes, dst):
    """An INIT of the given lanes (in that order) of another; written once, its SHA-256 returned."""
    b = read(src)
    out = b"".join(b[i * lane:(i + 1) * lane] for i in lanes)
    if os.path.exists(dst):
        if read(dst) != out:
            raise SystemExit("%s exists with other bytes" % dst)
    else:
        write_new(dst, out)
    return i_lib.sha256_bytes(out)


def derived_runs(p, plan, fmt, s, dst, **kw):
    out = runs_derive(read(os.path.join(p["in"], plan["i3"]["runs"][fmt][str(s)])), **kw)
    if os.path.exists(dst):
        if read(dst) != out:
            raise SystemExit("%s exists with other bytes" % dst)
    else:
        write_new(dst, out)
    return i_lib.sha256_bytes(out)


def same_device(G, R, j0):
    return G.test or (R.device == j0["device"])


GPU_J0C_CRIT = """gpu-j0c: J0c, the calibration (a measurement; its rules fixed in the plan before any data):
 the ladder: the program at degree 7 at binary64, binary128 and binary256 in turn, at s = 1, 2, 4 and 8 in that order;
    at each step one process of 8 lanes and one of 2,048 lanes (the base's first 8 and first 2,048 seed objects), each
    one run of 2 segments of s steps from DEBRIS-H's T_s (I3's first hour), every call timed by the driver;
 the warm-up: each process's first call is one segment of its own image on its first 8 lanes, logged and not judged
    (the plan says "at s = 1": the warm-up here uses the process's own s, since the code a GPU runs is libcft's, the
    same for every image; READ, HOSTAPI "What runs on the GPU is this library");
 a step's 2,048-lane call time is the larger of its two calls;
 the stop rule: a format's ladder stops at the first s whose 2,048-lane call takes over 150 ms; no larger s is started;
 the abort rule: from each process's second call, any call over 1,000 ms stops the calibration (j_run --abort-ms 1000
    stops itself, exit 6; the harness's watchdog kills a process by its PID after 180 s with no output);
 the choice: the largest s whose 2,048-lane call stayed under 150 ms at every format, one s for the round; if s = 1 is
    over 150 ms at a format, s = 1 is still used, and the report says the chunk may halve there;
 validity: every process's device line equals J0's; every process exits 0 (or 6, which stops the calibration);
 its output (out/j0c/j0c.json): every call's time, the choice, and each format's 2,048-lane call time at the chosen s."""


def gpu_j0c(a):
    p = gp_paths(os.path.abspath(a.root))
    log = i_lib.Log(p["logs"], "gpu_j0c", SCRIPT, [GPU_J0C_CRIT], keep_dir=None, modules=MODULES)
    if not gp_expected(p, log):
        sys.exit(log.close() or 1)
    j0 = j0_info(p)
    plan = json.load(open(os.path.join(p["in"], "plan.json"), "rb"))
    G = Gpu(a, p, log)
    od, sub = attempt_dir(p["out"], "j0c")
    log.w("this attempt's outputs: out/%s; J0's: %s" % (sub, j0["_dir"]))
    res = {"ladder": {}, "aborted": None, "desktop_test": G.test}
    stopped_all = False
    for fmt in FMT3:
        lane = plan["base"][fmt]["lane_bytes"]
        base = os.path.join(p["in"], plan["base"][fmt]["path"])
        LB = int(a.test_lanes) if a.test_lanes else 2048
        i8, i2048 = os.path.join(p["work"], "j0c-init8-%s.bin" % fmt), os.path.join(p["work"], "j0c-init%d-%s.bin" % (LB, fmt))
        h8 = slice_lanes(base, lane, range(8), i8)
        h2048 = slice_lanes(base, lane, range(LB), i2048)
        log.check(h8 == plan["j0c"]["init8"][fmt] and (h2048 == plan["j0c"]["init2048"][fmt] or LB != 2048),
                  "%s: the 8- and %d-lane INIT files are the staged plan's (%s, %s)" % (fmt, LB, h8[:16], h2048[:16]))
        res["ladder"][fmt] = []
        for s in SHORT_S:
            rp = os.path.join(p["work"], "j0c-runs-%s-s%d.bin" % (fmt, s))
            derived_runs(p, plan, fmt, s, rp, nruns=1, nseg_first=2)
            img = os.path.join(p["in"], plan["images"][fmt][str(s)])
            step = {"s": s}
            for L, ip in ((8, i8), (LB, i2048)):
                G.lock_take("j0c %s s=%d L=%d" % (fmt, s, L))
                try:
                    G.smi("before")
                    R = G.run("j0c-%s-s%d-L%d" % (fmt, s, L), img, rp, ip, L, s, 1, sub=sub)
                    G.smi("after", settle=2.0)
                finally:
                    G.lock_drop("j0c")
                calls = [x["call_ns"] / 1e6 for x in R.segs]
                step["L%d" % (L if L == 8 else 2048)] = {"lanes": L, "calls_ms": calls, "warmup_ms": (rep_int(R, "warmup_ns", -1) or -1) / 1e6, "rc": R.rc,
                                   "same_device": same_device(G, R, j0), "marks": rep_int(R, "marks")}
                kk = "L%d" % (L if L == 8 else 2048)
                log.check((R.rc == 0 and same_device(G, R, j0) and len(calls) == 2) or R.rc == 6,
                          "%s s=%d %d lanes: calls %s ms, warm-up %.1f ms, exit %s, device line J0's: %s" % (
                              fmt, s, L, ["%.2f" % c for c in calls], step[kk]["warmup_ms"], R.rc,
                              same_device(G, R, j0)))
                if R.rc != 0 or R.killed or not same_device(G, R, j0) or len(calls) != 2:
                    res["aborted"] = "%s s=%d L=%d: %s" % (fmt, s, L, R.abort or R.killed or (
                        "exit %s: %s" % (R.rc, " | ".join(R.errs[-2:])) if R.rc else "device line not J0's"))
                    stopped_all = True
                    break
            res["ladder"][fmt].append(step)
            if stopped_all:
                break
            c2048 = max(step["L2048"]["calls_ms"])
            step["c2048_ms"] = c2048
            if c2048 > G.stop:
                step["stopped"] = True
                log.w("%s: the stop rule at s = %d (%.2f ms over %.0f ms); no larger s" % (fmt, s, c2048, G.stop))
                break
        if stopped_all:
            break
    if stopped_all:
        log.check(False, "the calibration was stopped by the abort rule: %s" % res["aborted"])
    else:
        under = {}
        for fmt in FMT3:
            under[fmt] = [st["s"] for st in res["ladder"][fmt] if st["c2048_ms"] <= G.stop]
        common = [s for s in SHORT_S if all(s in under[f] for f in FMT3)]
        chosen = max(common) if common else 1
        res["chosen_s"] = chosen
        res["s1_over"] = [f for f in FMT3 if 1 not in under[f]]
        res["c2048_ms"] = {f: [st for st in res["ladder"][f] if st["s"] == chosen][0]["c2048_ms"] for f in FMT3}
        log.w("the choice: s = %d (each format's s under %.0f ms: %s)%s" % (chosen, G.stop, under,
              ("; s = 1 is over %.0f ms at %s, so the chunk may halve there" % (G.stop, res["s1_over"])) if res["s1_over"]
              else ""))
        for f in FMT3:
            log.w("FIG J0c %s: the 2,048-lane call at s = %d: %.2f ms (MEASURED; the larger of two calls)" % (
                f, chosen, res["c2048_ms"][f]))
    with open(os.path.join(od, "j0c.json"), "w", encoding="ascii", newline="\n") as f:
        json.dump(res, f, indent=1, sort_keys=True)
    log.w("out/%s/j0c.json SHA-256 %s" % (sub, i_lib.sha256_file(os.path.join(od, "j0c.json"))))
    sys.exit(1 if log.close() else 0)


def j0c_info(p):
    jp = os.path.join(latest_dir(p["out"], "j0c", "j0c.json"), "j0c.json")
    d = json.load(open(jp, "rb"))
    if "chosen_s" not in d:
        raise SystemExit("J0c made no choice (it was stopped): nothing more runs")
    d["_dir"] = os.path.basename(os.path.dirname(jp))
    return d


GPU_J1_CRIT = """gpu-j1: J1, bit for bit on the card (the lead's runs; DEBRIS-J's comparison, here and again on the desktop in
phase 2). Every run: hip:0 at depth 512, its device line J0's, warm-up 8 lanes, --abort-ms 1000.
(a) I1's 32 cases at s = 1 (the staged s = 1 image, runs and INIT; 16 lanes, 160 steps, every segment kept): each
    .seg.bin and .marks.bin has the SHA-256 of the desktop's software-executor output of the same image, runs and INIT
    (E1's; plan.json), byte for byte; and its REDUCE to 40-step boundaries has R1's SHA-256;
(b) I3's day at the chosen s, at binary64, binary128 and binary256: one run of 64 lanes (DEBRIS-I's 8 batch INIT files
    joined in batch order; the box ran all 8 batches with one runs file a format), 24 one-hour runs of 6 x 40 / s
    segments, --keep-every 40 / s: at every 40-step boundary, every lane's state and lane byte equal its slice of the
    box's file (ledger debris-i/box/out/i3/, staged in in/i3/box/), byte for byte;
marks: every mark is counted by format, run and segment (the routine is exp, the program's one routine that marks:
    READ, DEBRIS-I's box_i3.001.log); a mark is a lane byte the box's file does not have (the box logged 0 marks on these
    inputs), so it fails (b) at that lane until the desktop's replay (phase 2) says otherwise;
C-J1 (control) the planted INIT (lane 21's x one ulp up, binary256) for the first hour at the chosen s: exactly lane 21
    differs, at all 6 boundaries, and every other lane equals the box's;
C-J2 (control) (a)'s outputs at degree 2 against degree 7, at each format, at each 40-step boundary: every lane differs;
C-J3 (control) (b)'s binary64 comparison against the box's files with one byte flipped in a copy of batch 3's (record
    77, lane 2's x): it reports batch 3, record 77, lane 2 (beside any difference (b) itself found).
J1 PASSES when (a), (b) and the three controls hold with 0 marks; with any mark it is pending the desktop's replay."""


def gpu_j1(a):
    p = gp_paths(os.path.abspath(a.root))
    log = i_lib.Log(p["logs"], "gpu_j1", SCRIPT, [GPU_J1_CRIT], keep_dir=None, modules=MODULES)
    if not gp_expected(p, log):
        sys.exit(log.close() or 1)
    j0 = j0_info(p)
    j0c = j0c_info(p)
    s = int(a.s or j0c["chosen_s"])
    N = SEG40 // s
    plan = json.load(open(os.path.join(p["in"], "plan.json"), "rb"))
    G = Gpu(a, p, log)
    od, sub = attempt_dir(p["out"], "j1")
    log.w("this attempt's outputs: out/%s; J0's: %s; J0c's: %s" % (sub, j0["_dir"], j0c["_dir"]))
    hours = int(a.test_hours) if a.test_hours else 24
    log.w("the chosen s: %d (out/%s/j0c.json%s), N = %d; hours of I3's day run: %d%s" % (
        s, j0c["_dir"], ", overridden by --s in a desktop test" if a.s else "", N, hours,
        " (a desktop test's cut)" if hours != 24 else ""))
    marks = []
    ok_a = True
    outs_a = {}
    G.lock_take("j1 (a)")
    try:
        G.smi("before (a)")
        G.ps()
        for c in plan["i1"]:
            if a.only and c["case"] not in a.only.split(","):
                continue
            R = G.run("a-" + c["case"], os.path.join(p["in"], c["image"]), os.path.join(p["in"], c["runs"]),
                      os.path.join(p["in"], c["init"]), c["lanes"], 1, 1, sub=sub)
            hs = i_lib.sha256_file(R.pre + ".seg.bin") if os.path.isfile(R.pre + ".seg.bin") else "-"
            hm = i_lib.sha256_file(R.pre + ".marks.bin") if os.path.isfile(R.pre + ".marks.bin") else "-"
            red = "-"
            if R.rc == 0:
                red = i_lib.sha256_bytes(reduce40(read(R.pre + ".seg.bin"), c["lanes"], c["nst"], c["esz"], 40, c["nseg"]))
            nm = rep_int(R, "marks", -1)
            if nm:
                marks.append(("a", c["case"], nm))
            outs_a[c["case"]] = R.pre
            ok_a &= log.check(R.rc == 0 and same_device(G, R, j0) and hs == c["seg_sha256"] and hm == c["marks_sha256"] and
                              red == c["r1"], "(a) %s: .seg.bin %s (the desktop's %s), .marks.bin %s, REDUCE %s (R1's %s), "
                              "marks %s, device line J0's: %s" % (c["case"], hs[:16], c["seg_sha256"][:16],
                                                                   "equal" if hm == c["marks_sha256"] else "DIFFERS",
                                                                   red[:16], c["r1"][:16], nm, same_device(G, R, j0)))
        G.smi("after (a)", settle=2.0)
    finally:
        G.lock_drop("j1 (a)")
    # (b)
    ok_b = True
    i3 = plan["i3"]
    bout = {}
    for fmt in FMT3:
        rp = os.path.join(p["work"], "j1b-runs-%s-s%d-h%d.bin" % (fmt, s, hours))
        derived_runs(p, plan, fmt, s, rp, nruns=hours)
        G.lock_take("j1 (b) %s" % fmt)
        try:
            G.smi("before (b) %s" % fmt)
            G.ps()
            R = G.run("b-%s" % fmt, os.path.join(p["in"], plan["images"][fmt][str(s)]), rp,
                      os.path.join(p["in"], i3["init64"][fmt]), 64, s, N, sub=sub)
            G.smi("after (b) %s" % fmt, settle=2.0)
        finally:
            G.lock_drop("j1 (b)")
        bout[fmt] = R.pre
        nm = rep_int(R, "marks", -1)
        if nm:
            marks.append(("b", fmt, nm))
        if R.rc != 0:
            ok_b &= log.check(False, "(b) %s: exit %s %s" % (fmt, R.rc, R.abort or R.killed or ""))
            continue
        boxes = [read(os.path.join(p["in"], x)) for x in i3["box"][fmt]]
        d, ncmp = j1b_compare(read(R.pre + ".seg.bin"), 64, 7, ESZ[fmt], N, [6 * N] * hours, N, boxes, nrec=6 * hours)
        ok_b &= log.check(not d and ncmp == 8 * 6 * hours and same_device(G, R, j0),
                          "(b) %s at s = %d: %d records of 8 lanes compared with the box's (%d boundaries x 8 batches), %d "
                          "differences%s; marks %s; segments %s; device line J0's: %s; output %s" % (
                              fmt, s, ncmp, 6 * hours, len(d), (" " + str(d[:6])) if d else "", nm, R.rep.get("segments"),
                              same_device(G, R, j0), i_lib.sha256_file(R.pre + ".seg.bin")))
    # C-J1
    rp = os.path.join(p["work"], "cj1-runs-fp256-s%d.bin" % s)
    derived_runs(p, plan, "fp256", s, rp, nruns=1)
    G.lock_take("j1 C-J1")
    try:
        G.smi("before C-J1")
        R = G.run("cj1-fp256", os.path.join(p["in"], plan["images"]["fp256"][str(s)]), rp,
                  os.path.join(p["in"], i3["cj1"]["init"]), 64, s, N, sub=sub)
        G.smi("after C-J1", settle=2.0)
    finally:
        G.lock_drop("j1 C-J1")
    if R.rc == 0:
        boxes = [read(os.path.join(p["in"], x)) for x in i3["box"]["fp256"]]
        d, ncmp = j1b_compare(read(R.pre + ".seg.bin"), 64, 7, 32, N, [6 * N], N, boxes, nrec=6)
        hit = sorted(set((8 * x[0] + x[4], x[3]) for x in d))
        log.check(hit == [(CJ1_LANE, k) for k in range(1, 7)], "C-J1 (control) lane 21's x one ulp up: the differing (lane, "
                  "boundary) pairs %s: exactly lane 21 at all 6 boundaries" % hit[:8])
    else:
        log.check(False, "C-J1 (control): exit %s" % R.rc)
    # C-J2
    for fmt in FMT4:
        k7, k2 = "i1-program-d7-%s" % fmt, "i1-program-d2-%s" % fmt
        if k7 not in outs_a or k2 not in outs_a:
            continue
        c7 = [c for c in plan["i1"] if c["case"] == k7][0]
        r7 = reduce40(read(outs_a[k7] + ".seg.bin"), 16, 7, ESZ[fmt], 40, c7["nseg"])
        r2 = reduce40(read(outs_a[k2] + ".seg.bin"), 16, 7, ESZ[fmt], 40, c7["nseg"])
        d, ncmp = compare40(r2, r7, 16, 7, ESZ[fmt], "d2/d7")
        st = set((x[0], x[3]) for x in d if x[4] == "state")
        log.check(len(st) == 16 * ncmp and ncmp == 4, "C-J2 (control) %s: degree 2 against degree 7 on the card, %d of %d "
                  "lane-boundaries differ in state" % (fmt, len(st), 16 * ncmp))
    # C-J3
    if "fp64" in bout and os.path.isfile(bout["fp64"] + ".seg.bin"):
        boxes = [bytearray(read(os.path.join(p["in"], x))) for x in i3["box"]["fp64"]]
        rec = seg_records(bytes(boxes[CJ3_BATCH]), 8, 7, 8)[CJ3_REC]
        boxes[CJ3_BATCH][rec[2] - 8 + CJ3_BYTE] ^= 0x01
        d, ncmp = j1b_compare(read(bout["fp64"] + ".seg.bin"), 64, 7, 8, N, [6 * N] * hours, N,
                              [bytes(x) for x in boxes], nrec=6 * hours)
        hit = [(x[0], x[1], x[4]) for x in d]
        if CJ3_REC < 6 * hours:
            log.check((CJ3_BATCH, CJ3_REC, 2) in hit, "C-J3 (control) one byte flipped in a copy of batch 3's binary64 "
                      "file: the comparison reports %s" % hit[:4])
        else:
            log.w("C-J3: record 77 is past this desktop test's %d hours: not run" % hours)
    log.w("marks on the card: %s" % (marks if marks else "none"))
    if marks:
        verdict = "PENDING: %d runs with marks, for the desktop's replay; %d checks failed" % (len(marks), log.fails)
    else:
        verdict = "PASS" if (ok_a and ok_b and log.fails == 0) else "FAIL (%d checks)" % log.fails
    log.w("J1 %s" % verdict)
    with open(os.path.join(od, "j1.json"), "w", encoding="ascii", newline="\n") as f:
        json.dump({"verdict": verdict, "s": s, "hours": hours, "marks": marks, "desktop_test": G.test}, f, indent=1)
    sys.exit(1 if log.close() else 0)


GPU_J2_CRIT = """gpu-j2: J2, the rates (a measurement, no pass condition; fixed in the plan and here before any data).
 configurations: the program at degree 7 at the chosen s (out/j0c/j0c.json), at binary64, binary128 and binary256;
    batches of 512, 2,048, 8,192 and 32,768 lanes, tiling DEBRIS-H's 2,688 seed objects in seed index order (lane i is
    seed object i mod 2,688), made here from the staged base;
 a run's length, fixed for every configuration before the first run (out/j2/j2-plan.json): with c the format's
    2,048-lane call time at the chosen s (J0c's), a call of B lanes is projected at ceil(B / 2,048) x c and an hour at
    (240 / s) calls; a run is the fewest whole hours from T_s that fill 60 s if they take at most 180 s; where one hour
    would take more than 180 s, the fewest whole segments of the first hour that fill 60 s; at most the 24 staged hours
    (a run that 24 hours cannot fill to 60 s is run at 24 hours, and its wall time is reported as it is);
 a run: one process, hip:0 at depth 512, a warm-up call of 8 lanes, --abort-ms 1000, the states kept only at each run's
    end; the timed region from the first call after the warm-up to the last call's end (j_run's REPORT);
 the statistic: X = object-seconds summed over the lanes / the timed wall time = B x 15 s x s x timed calls / wall (I5's
    definition); each format's batch with the largest X is run twice more, and its median and range are reported;
 validity: the device line equals J0's; nvidia-smi before and after the run (after a 2-s settle): memory used at most
    --mem-max-mib and utilisation at most --util-max (Phase 0's thresholds, the lead's); exit 0. A run failing validity
    alone repeats once, and failing again is void. A run whose call passes 1,000 ms after the warm-up is stopped by the
    driver (exit 6), logged with that call's time, reported as stopped by the rule, and not repeated; the other runs go
    on. The VM's CPU load over each run (/proc/stat) is recorded; the desktop's own is the lead's to record beside."""


def stat_busy():
    try:
        with open("/proc/stat", encoding="ascii") as f:
            v = [int(x) for x in f.readline().split()[1:9]]
        return v[0] + v[1] + v[2] + v[5] + v[6] + v[7], sum(v), time.monotonic()
    except OSError:
        return None


def j2_plan(j0c, s, test_batches=None, test_segments=None):
    cfgs = []
    batches = test_batches or [512, 2048, 8192, 32768]
    for fmt in FMT3:
        c = j0c["c2048_ms"][fmt] / 1000.0
        for B in batches:
            call = math.ceil(B / float(CHUNK)) * c
            hour = (240 // s) * call
            if test_segments:
                nruns, nseg, rule = 1, int(test_segments), "desktop test: %d segments" % int(test_segments)
            elif hour * math.ceil(60.0 / hour) <= 180.0:
                H = int(math.ceil(60.0 / hour))
                rule = "%d whole hours (projected %.1f s)" % (H, H * hour)
                if H > 24:
                    rule = "24 hours, the staged day (projected %.1f s, short of 60 s)" % (24 * hour)
                    H = 24
                nruns, nseg = H, None
            else:
                S = int(math.ceil(60.0 / call))
                nruns, nseg, rule = 1, S, "%d segments of the first hour (projected %.1f s; an hour %.1f s)" % (S, S * call, hour)
            cfgs.append({"fmt": fmt, "B": B, "s": s, "nruns": nruns, "nseg": nseg, "rule": rule, "proj_call_s": call,
                         "proj_hour_s": hour})
    return cfgs


def gpu_j2(a):
    p = gp_paths(os.path.abspath(a.root))
    log = i_lib.Log(p["logs"], "gpu_j2", SCRIPT, [GPU_J2_CRIT], keep_dir=None, modules=MODULES)
    if not gp_expected(p, log):
        sys.exit(log.close() or 1)
    j0 = j0_info(p)
    j0c = j0c_info(p)
    s = int(j0c["chosen_s"])
    plan = json.load(open(os.path.join(p["in"], "plan.json"), "rb"))
    G = Gpu(a, p, log)
    if not G.test and (a.mem_max_mib is None or a.util_max is None):
        raise SystemExit("--mem-max-mib and --util-max (Phase 0's thresholds) are required")
    od, sub = attempt_dir(p["out"], "j2")
    log.w("this attempt's outputs: out/%s; J0's: %s; J0c's: %s" % (sub, j0["_dir"], j0c["_dir"]))
    tb = [int(x) for x in a.test_batches.split(",")] if a.test_batches else None
    cfgs = j2_plan(j0c, s, tb, a.test_segments)
    pp = os.path.join(od, "j2-plan.json")
    with open(pp, "w", encoding="ascii", newline="\n") as f:
        json.dump(cfgs, f, indent=1)
    log.w("the plan, fixed before the first run: out/%s/j2-plan.json SHA-256 %s" % (sub, i_lib.sha256_file(pp)))
    for c in cfgs:
        log.w("  %s B=%d: %s" % (c["fmt"], c["B"], c["rule"]))
    rows = []

    def one(c, attempt, rep):
        fmt, B = c["fmt"], c["B"]
        lane = plan["base"][fmt]["lane_bytes"]
        ip = os.path.join(p["work"], "j2-init-%s-%d.bin" % (fmt, B))
        hi = slice_lanes(os.path.join(p["in"], plan["base"][fmt]["path"]), lane, [i % 2688 for i in range(B)], ip)
        if c["nseg"] is None:
            rp = os.path.join(p["work"], "j2-runs-%s-s%d-h%d.bin" % (fmt, s, c["nruns"]))
            derived_runs(p, plan, fmt, s, rp, nruns=c["nruns"])
            keep = 240 // s
        else:
            rp = os.path.join(p["work"], "j2-runs-%s-s%d-seg%d.bin" % (fmt, s, c["nseg"]))
            derived_runs(p, plan, fmt, s, rp, nruns=1, nseg_first=c["nseg"])
            keep = c["nseg"]
        tag = "j2-%s-B%d-r%d-a%d" % (fmt, B, rep, attempt)
        G.lock_take(tag)
        try:
            sb = G.smi("before " + tag)
            G.ps()
            st0 = stat_busy()
            R = G.run(tag, os.path.join(p["in"], plan["images"][fmt][str(s)]), rp, ip, B, s, keep, sub=sub)
            st1 = stat_busy()
            sa = G.smi("after " + tag, settle=2.0)
        finally:
            G.lock_drop(tag)
        tc = rep_int(R, "timed_calls", 0)
        wall = (rep_int(R, "timed_end_ns", 0) - rep_int(R, "timed_start_ns", 0)) / 1e9
        X = B * H_STEP * s * tc / wall if wall > 0 and tc else None
        fails = []
        if not same_device(G, R, j0):
            fails.append("device")
        if not G.test:
            for tg, d in (("before", sb), ("after", sa)):
                if d.get("mem") is None or d["mem"] > float(a.mem_max_mib):
                    fails.append("memory_" + tg)
                if d.get("util") is None or d["util"] > float(a.util_max):
                    fails.append("util_" + tg)
        if R.rc not in (0, 6):
            fails.append("exit %s" % R.rc)
        vm = None
        if st0 and st1:
            vm = (st1[0] - st0[0]) / float(max(1, st1[1] - st0[1]))
        row = {"fmt": fmt, "B": B, "s": s, "rep": rep, "attempt": attempt, "tag": tag, "rc": R.rc, "stopped": R.rc == 6,
               "abort": R.abort, "timed_calls": tc, "wall_s": wall, "X": X, "segments": rep_int(R, "segments"),
               "marks": rep_int(R, "marks"), "call_max_ms": rep_int(R, "call_max_ns", 0) / 1e6,
               "call_min_ms": rep_int(R, "call_min_ns", 0) / 1e6, "warmup_ms": rep_int(R, "warmup_ns", 0) / 1e6,
               "smi_before": sb.get("line"), "smi_after": sa.get("line"), "vm_busy_share": vm, "failed": fails,
               "valid": not fails and R.rc == 0, "init_sha256": hi, "runs_sha256": i_lib.sha256_file(rp),
               "utc_start": time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(time.time() - R.wall)),
               "utc_end": time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())}
        log.w("RUN %s: X %s obj-s/s, timed %d calls in %.2f s (call %.1f to %.1f ms), %s%s; VM busy %s" % (
            tag, "%.1f" % X if X else "-", tc, wall, row["call_min_ms"], row["call_max_ms"],
            "VALID" if row["valid"] else ("STOPPED by the 1,000-ms rule: " + (R.abort or "") if R.rc == 6 else "FAILED " +
                                          ",".join(fails)), "" if row["marks"] in (0, None) else "; marks %s" % row["marks"],
            "%.3f" % vm if vm is not None else "NA"))
        return row

    for c in cfgs:
        row = one(c, 1, 1)
        if not row["valid"] and not row["stopped"] and row["failed"] and all(
                f.startswith("memory") or f.startswith("util") or f == "device" for f in row["failed"]):
            rows.append(row)
            row = one(c, 2, 1)
        rows.append(row)
    best = {}
    for fmt in FMT3:
        v = [r for r in rows if r["fmt"] == fmt and r["valid"] and r["X"]]
        if v:
            best[fmt] = max(v, key=lambda r: r["X"])["B"]
    for fmt, B in sorted(best.items()):
        c = [x for x in cfgs if x["fmt"] == fmt and x["B"] == B][0]
        for rep in (2, 3):
            row = one(c, 1, rep)
            if not row["valid"] and not row["stopped"] and row["failed"] and all(
                    f.startswith("memory") or f.startswith("util") or f == "device" for f in row["failed"]):
                rows.append(row)
                row = one(c, 2, rep)
            rows.append(row)
    jp = os.path.join(od, "j2.json")
    with open(jp, "w", encoding="ascii", newline="\n") as f:
        json.dump({"rows": rows, "best": best, "s": s, "desktop_test": G.test}, f, indent=1)
    log.w("per-run records: out/%s/j2.json SHA-256 %s" % (sub, i_lib.sha256_file(jp)))
    for fmt in FMT3:
        for B in sorted(set(r["B"] for r in rows)):
            last = [r for r in rows if r["fmt"] == fmt and r["B"] == B and r["rep"] == 1]
            if last:
                r = last[-1]
                log.w("FIG J2 %s B=%d s=%d: X %s obj-s/s (%s)" % (fmt, B, s, "%.1f" % r["X"] if r["X"] else "-",
                                                                   "valid" if r["valid"] else ("stopped by the rule" if
                                                                                               r["stopped"] else "void")))
        if fmt in best:
            xs = sorted(r["X"] for r in rows if r["fmt"] == fmt and r["B"] == best[fmt] and r["valid"] and r["X"])
            log.w("FIG J2 %s best batch %d: %d valid samples, median %s, range %s to %s obj-s/s" % (
                fmt, best[fmt], len(xs), "%.1f" % xs[len(xs) // 2] if xs else "-", "%.1f" % xs[0] if xs else "-",
                "%.1f" % xs[-1] if xs else "-"))
    sys.exit(1 if log.close() else 0)


GPU_J3_CRIT = """gpu-j3: J3, a catalogue day on the card (a measurement, with one equality check at each format).
 the lanes: DEBRIS-H's 2,688 seed objects less seed index 1595 (DEBRIS-H decayed it 5.8 h after T_s; I3's rule): 2,687,
    in seed index order, made here from the staged base (its SHA-256 the staged plan's);
 the span, at binary64 and binary256 at the chosen s, --keep-every 40 / s, warm-up 8, --abort-ms 1000: the whole day
    from T_s if the projection is at most 60 minutes, else 6 hours; the projection is (5,760 / s calls) x 2 chunks
    (2,048 and 639 lanes, each a launch) x J0c's 2,048-lane call time at that format;
 the measurement: the span's wall time (the timed region) against its simulated time (86,400 or 21,600 s);
 the check: the 16 lanes drawn at staging (random.Random(20261124), plan.json) each equal, at every 40-step boundary of
    the span, the desktop's software-executor replay of the day (in/j3/ref-<fmt>.seg.bin), state and lane byte, bit for
    bit; a checked lane that is marked is judged only after the desktop's replay (phase 2);
 marks: every mark is counted by format, run and segment, with its lane's seed index, for phase 2's replay;
 validity: the device line equals J0's; nvidia-smi before and after (as J2's thresholds, when given)."""


def gpu_j3(a):
    p = gp_paths(os.path.abspath(a.root))
    log = i_lib.Log(p["logs"], "gpu_j3", SCRIPT, [GPU_J3_CRIT], keep_dir=None, modules=MODULES)
    if not gp_expected(p, log):
        sys.exit(log.close() or 1)
    j0 = j0_info(p)
    j0c = j0c_info(p)
    s = int(j0c["chosen_s"])
    N = SEG40 // s
    plan = json.load(open(os.path.join(p["in"], "plan.json"), "rb"))
    G = Gpu(a, p, log)
    j3 = plan["j3"]
    order = [i for i in range(2688) if i != j3["exclude"]]
    nl = int(a.test_lanes) if a.test_lanes else len(order)
    od, sub = attempt_dir(p["out"], "j3")
    log.w("this attempt's outputs: out/%s; J0's: %s; J0c's: %s" % (sub, j0["_dir"], j0c["_dir"]))
    res = {"s": s, "desktop_test": G.test, "formats": {}}
    for fmt in ("fp64", "fp256"):
        lane = plan["base"][fmt]["lane_bytes"]
        ip = os.path.join(p["work"], "j3-init-%s.bin" % fmt)
        h = slice_lanes(os.path.join(p["in"], plan["base"][fmt]["path"]), lane, order, ip)
        log.check(h == j3["init_sha256"][fmt], "%s: J3's INIT (%d lanes) is the staged plan's (%s)" % (fmt, len(order), h[:16]))
        if nl != len(order):
            ip2 = os.path.join(p["work"], "j3-init-%s-L%d.bin" % (fmt, nl))
            slice_lanes(ip, lane, range(nl), ip2)
            ip = ip2
        proj = (5760 // s) * 2 * j0c["c2048_ms"][fmt] / 1000.0
        hours = 24 if proj <= 3600.0 else 6
        if a.test_hours:
            hours = int(a.test_hours)
        rp = os.path.join(p["work"], "j3-runs-%s-s%d-h%d.bin" % (fmt, s, hours))
        derived_runs(p, plan, fmt, s, rp, nruns=hours)
        log.w("%s: projection %.0f s (%.1f min) for the day: the span is %d hours%s" % (
            fmt, proj, proj / 60.0, hours, " (a desktop test's cut)" if a.test_hours else ""))
        tag = "j3-%s" % fmt
        G.lock_take(tag)
        try:
            sb = G.smi("before " + tag)
            G.ps()
            R = G.run(tag, os.path.join(p["in"], plan["images"][fmt][str(s)]), rp, ip, nl, s, N, sub=sub)
            sa = G.smi("after " + tag, settle=2.0)
        finally:
            G.lock_drop(tag)
        tc = rep_int(R, "timed_calls", 0)
        wall = (rep_int(R, "timed_end_ns", 0) - rep_int(R, "timed_start_ns", 0)) / 1e9
        sim = hours * 3600.0
        ok = R.rc == 0 and same_device(G, R, j0)
        if not G.test and a.mem_max_mib is not None:
            ok &= all(d.get("mem") is not None and d["mem"] <= float(a.mem_max_mib) and d["util"] <= float(a.util_max)
                      for d in (sb, sa))
        draw = [q for q in j3["draw"] if q < nl]
        diffs, marked = [], []
        if R.rc == 0:
            red = reduce40(read(R.pre + ".seg.bin"), nl, 7, ESZ[fmt], N, [6 * N] * hours, kept_every=N)
            got = lane_slice(red, nl, 7, ESZ[fmt], draw)
            ref = read(os.path.join(p["in"], j3["ref"][fmt]["seg"]))
            if len(draw) != 16:
                ref = lane_slice(ref, 16, 7, ESZ[fmt], [j3["draw"].index(q) for q in draw])
            diffs, ncmp = compare40(got, ref, len(draw), 7, ESZ[fmt], "j3", nrec=6 * hours)
            mk = read(R.pre + ".marks.bin")
            rec = 12 + plan["i3"]["nscr"][fmt] * ESZ[fmt] + 7 * ESZ[fmt]
            for o in range(0, len(mk), rec):
                r_, s_, l_ = struct.unpack_from("<3I", mk, o)
                marked.append((r_, s_, l_, order[l_]))
            mlanes = set(m[2] for m in marked)
            hard = [d for d in diffs if draw[d[3]] not in mlanes]
            log.check(not hard and ncmp == 6 * hours and draw, "%s check: %d of the 16 drawn lanes (those in this run) against "
                      "the desktop's replay at %d boundaries: %d differences (%d in marked lanes, pending replay)%s" % (
                          fmt, len(draw), ncmp, len(diffs), len(diffs) - len(hard), (" " + str(hard[:6])) if hard else ""))
        log.check(ok, "%s run: exit %s, device line J0's: %s, nvidia-smi within the thresholds" % (
            fmt, R.rc, same_device(G, R, j0)))
        res["formats"][fmt] = {"hours": hours, "proj_s": proj, "rc": R.rc, "abort": R.abort, "timed_calls": tc,
                               "wall_s": wall, "sim_s": sim, "realtime_factor": sim / wall if wall > 0 else None,
                               "lanes": nl, "marks": marked, "diffs": len(diffs), "valid": ok,
                               "call_max_ms": rep_int(R, "call_max_ns", 0) / 1e6, "smi_before": sb.get("line"),
                               "smi_after": sa.get("line")}
        log.w("FIG J3 %s s=%d: %d lanes, %d simulated hours in %.1f s of wall time: %.1f times real time (MEASURED); "
              "marks %d" % (fmt, s, nl, hours, wall, sim / wall if wall > 0 else float("nan"), len(marked)))
    with open(os.path.join(od, "j3.json"), "w", encoding="ascii", newline="\n") as f:
        json.dump(res, f, indent=1)
    sys.exit(1 if log.close() else 0)


# ------------------------------------------------------------------ phase 2 on the desktop: compare, replay, analyze

def gpu_dir(cfg, a):
    g = a.gpu or os.path.join(cfg["dj"], "gpu", a.run)
    for d in ("out", "logs"):
        if not os.path.isdir(os.path.join(g, d)):
            raise SystemExit("the GPU's records are not at %s (need out/ and logs/)" % redact(cfg, g))
    return g


def stage_dir(cfg, a):
    return os.path.join(cfg["dj"], "gpu-stage", a.run, "in")


COMPARE_CRIT = """compare (phase 2, desktop): J1 and J3 recomputed from the GPU's records as the lead copied them (ledger
debris-j/gpu/<run>/), against the desktop's references, with the criteria of gpu-j1 and gpu-j3 unchanged:
(a) each of I1's 32 cases: the card's .seg.bin and .marks.bin equal, byte for byte, the desktop's s = 1 output (E1's,
    ledger debris-j/desktop/e1/); REDUCE has R1's SHA-256;
(b) I3's day at binary64, binary128 and binary256: the card's 64-lane file, reduced, lane-sliced, equals the box's 8
    files (ledger debris-i/box/out/i3/) at every 40-step boundary run;
C-J1, C-J2, C-J3 as gpu-j1 states them, on the card's files;
J3: the 16 drawn lanes of the card's day equal the desktop's replays (ledger debris-j/desktop/j3ref/) at every boundary;
the device: every stdout of the card's runs names J0's device line; every provenance file's status is DONE (or ABORTED
    where the rule stopped a J2 run) and names the image, runs and INIT it ran;
marks: every mark record in every .marks.bin of the card's runs is listed (format, mode, run, segment, lane) for the
    replay; a gate's criterion counts only states that are unmarked or replayed equal."""


def mode_compare(cfg, a):
    g = gpu_dir(cfg, a)
    ind = stage_dir(cfg, a)
    log = i_lib.Log(cfg["logs"], "compare", SCRIPT, [COMPARE_CRIT], keep_dir=cfg["kept"], modules=MODULES)
    cpu = i_lib.Cpu("compare", os.path.join(cfg["scratch"], "cpu.tsv"))
    plan = json.load(open(os.path.join(ind, "plan.json"), "rb"))
    dj0, dj0c = latest_dir(os.path.join(g, "out"), "j0", "j0.json"), latest_dir(os.path.join(g, "out"), "j0c", "j0c.json")
    dj1 = latest_dir(os.path.join(g, "out"), "j1", "j1.json")
    j0 = json.load(open(os.path.join(dj0, "j0.json"), "rb"))
    j0c = json.load(open(os.path.join(dj0c, "j0c.json"), "rb"))
    log.w("the attempts compared: %s, %s, %s" % (os.path.basename(dj0), os.path.basename(dj0c), os.path.basename(dj1)))
    s = int(j0c["chosen_s"])
    N = SEG40 // s
    j1 = json.load(open(os.path.join(dj1, "j1.json"), "rb"))
    hours = int(j1.get("hours", 24))
    log.w("the GPU's records: %s; J0's device line names %r; the chosen s %d" % (
        redact(cfg, g), device_fields(j0["device"]).get("name"), s))
    # the device lines and provenance
    nrun = bad = 0
    for dp, _dn, fns in os.walk(os.path.join(g, "out")):
        for fn in fns:
            if fn.endswith(".stdout.txt") and not fn.startswith(("c0a", "c0b", "c0c")):
                lines = read(os.path.join(dp, fn)).decode("utf-8", "replace").splitlines()
                dev = [x[7:] for x in lines if x.startswith("device ")]
                nrun += 1
                if dev and dev[0] != j0["device"]:
                    bad += 1
                    log.w("  %s: its device line is not J0's" % fn)
    log.check(nrun > 0 and bad == 0, "the device: %d stdout files of the card's runs, %d name another device line" % (nrun, bad))
    # (a)
    e1 = os.path.join(cfg["desk"], "e1")
    ok_a, outs = True, {}
    for c in plan["i1"]:
        pre = os.path.join(dj1, "a-" + c["case"])
        if not os.path.isfile(pre + ".seg.bin"):
            ok_a &= log.check(False, "(a) %s: no output" % c["case"])
            continue
        outs[c["case"]] = pre
        sb, mb = read(pre + ".seg.bin"), read(pre + ".marks.bin")
        db, dm = read(os.path.join(e1, c["case"] + ".s1.seg.bin")), read(os.path.join(e1, c["case"] + ".s1.marks.bin"))
        red = i_lib.sha256_bytes(reduce40(sb, c["lanes"], c["nst"], c["esz"], 40, c["nseg"]))
        ok_a &= log.check(sb == db and mb == dm and red == c["r1"], "(a) %s: the card's .seg.bin equals the desktop's: %s; "
                          ".marks.bin: %s; REDUCE %s (R1's %s)" % (c["case"], sb == db, mb == dm, red[:16], c["r1"][:16]))
    # (b)
    for fmt in FMT3:
        pre = os.path.join(dj1, "b-%s" % fmt)
        if not os.path.isfile(pre + ".seg.bin"):
            log.check(False, "(b) %s: no output" % fmt)
            continue
        boxes = [read(os.path.join(cfg["ibox"], "prog-%s-b%d.seg.bin" % (fmt, b))) for b in range(8)]
        d, ncmp = j1b_compare(read(pre + ".seg.bin"), 64, 7, ESZ[fmt], N, [6 * N] * hours, N, boxes, nrec=6 * hours)
        log.check(not d and ncmp == 8 * 6 * hours, "(b) %s at s = %d: %d records of 8 lanes against the box's, %d "
                  "differences%s" % (fmt, s, ncmp, len(d), (" " + str(d[:6])) if d else ""))
    # C-J1
    pre = os.path.join(dj1, "cj1-fp256")
    if os.path.isfile(pre + ".seg.bin"):
        boxes = [read(os.path.join(cfg["ibox"], "prog-fp256-b%d.seg.bin" % b)) for b in range(8)]
        d, ncmp = j1b_compare(read(pre + ".seg.bin"), 64, 7, 32, N, [6 * N], N, boxes, nrec=6)
        hit = sorted(set((8 * x[0] + x[4], x[3]) for x in d))
        log.check(hit == [(CJ1_LANE, k) for k in range(1, 7)], "C-J1 (control) on the card: differing (lane, boundary) %s" % hit[:8])
    # C-J2
    for fmt in FMT4:
        k7, k2 = "i1-program-d7-%s" % fmt, "i1-program-d2-%s" % fmt
        if k7 in outs and k2 in outs:
            c7 = [c for c in plan["i1"] if c["case"] == k7][0]
            r7 = reduce40(read(outs[k7] + ".seg.bin"), 16, 7, ESZ[fmt], 40, c7["nseg"])
            r2 = reduce40(read(outs[k2] + ".seg.bin"), 16, 7, ESZ[fmt], 40, c7["nseg"])
            dd, ncmp = compare40(r2, r7, 16, 7, ESZ[fmt], "d2/d7")
            st = set((x[0], x[3]) for x in dd if x[4] == "state")
            log.check(len(st) == 16 * ncmp == 64, "C-J2 (control) %s on the card: %d of %d lane-boundaries differ" % (
                fmt, len(st), 16 * ncmp))
    # C-J3
    pre = os.path.join(dj1, "b-fp64")
    if os.path.isfile(pre + ".seg.bin"):
        boxes = [bytearray(read(os.path.join(cfg["ibox"], "prog-fp64-b%d.seg.bin" % b))) for b in range(8)]
        rec = seg_records(bytes(boxes[CJ3_BATCH]), 8, 7, 8)[CJ3_REC]
        boxes[CJ3_BATCH][rec[2] - 8 + CJ3_BYTE] ^= 0x01
        d, ncmp = j1b_compare(read(pre + ".seg.bin"), 64, 7, 8, N, [6 * N] * hours, N, [bytes(x) for x in boxes],
                              nrec=6 * hours)
        if CJ3_REC < 6 * hours:
            log.check((CJ3_BATCH, CJ3_REC, 2) in [(x[0], x[1], x[4]) for x in d], "C-J3 (control) on the card's binary64 "
                      "day: reported %s" % [(x[0], x[1], x[4]) for x in d][:4])
        else:
            log.w("C-J3: record 77 is past the %d hours run: not run" % hours)
    # J3
    marks = []
    try:
        j3p = os.path.join(latest_dir(os.path.join(g, "out"), "j3", "j3.json"), "j3.json")
    except SystemExit:
        j3p = ""
    if j3p:
        j3 = json.load(open(j3p, "rb"))
        order = [i for i in range(2688) if i != plan["j3"]["exclude"]]
        for fmt, r in sorted(j3["formats"].items()):
            pre = os.path.join(os.path.dirname(j3p), "j3-%s" % fmt)
            if r["rc"] != 0:
                log.check(False, "J3 %s: exit %s" % (fmt, r["rc"]))
                continue
            red = reduce40(read(pre + ".seg.bin"), r["lanes"], 7, ESZ[fmt], N, [6 * N] * r["hours"], kept_every=N)
            draw = [q for q in plan["j3"]["draw"] if q < r["lanes"]]
            got = lane_slice(red, r["lanes"], 7, ESZ[fmt], draw)
            ref = read(os.path.join(cfg["desk"], "j3ref", "j3ref-%s.seg.bin" % fmt))
            if len(draw) != 16:
                ref = lane_slice(ref, 16, 7, ESZ[fmt], [plan["j3"]["draw"].index(q) for q in draw])
            dd, ncmp = compare40(got, ref, len(draw), 7, ESZ[fmt], "j3", nrec=6 * r["hours"])
            mk = read(pre + ".marks.bin")
            rl = 12 + plan["i3"]["nscr"][fmt] * ESZ[fmt] + 7 * ESZ[fmt]
            ml = set()
            for o in range(0, len(mk), rl):
                rr, ss, ll = struct.unpack_from("<3I", mk, o)
                ml.add(ll)
                marks.append(("j3", fmt, rr, ss, ll, order[ll]))
            hard = [x for x in dd if draw[x[3]] not in ml]
            log.check(not hard and ncmp == 6 * r["hours"] and draw, "J3 %s: %d of the 16 drawn lanes (those run) against the "
                      "desktop's replay at %d boundaries: %d differences, %d of them in marked lanes" % (
                          fmt, len(draw), ncmp, len(dd), len(dd) - len(hard)))
    # every mark of the card's runs
    for dp, _dn, fns in os.walk(os.path.join(g, "out")):
        for fn in sorted(fns):
            if fn.endswith(".marks.bin") and os.path.getsize(os.path.join(dp, fn)) and "j3-" not in fn:
                marks.append(("other", fn, os.path.getsize(os.path.join(dp, fn))))
    log.w("marks on the card: %d records%s" % (len(marks), (": " + str(marks[:10])) if marks else ""))
    cpu.close()
    sys.exit(1 if log.close() else 0)


REPLAY_CRIT = """replay: a marked lane-segment of the card replayed by cftc's reference interpreter (cft_golden.lang.run at
9e8ff270, mpmath), from the mark record's boundary state before the mark (the lane's whole scratch: its state and lane
params) with the run's bank params, for the segment's s steps; the replay's state is compared with the card's state
after the segment (the NaN rule: equal bits, or both NaN). Equal: the run stands. Not equal: that lane's later states
are void and the lane is redone from the replayed state. Its selftest (no mark on the card needed): unmarked
lane-segments of the desktop's own outputs, replayed the same way, must equal the executor's state (E1's I1 program at
degree 7, binary64, s = 1, run 0's segment 1, lanes 0 and 1; and E1(iii)'s binary256 at s = 8, segment 1, lane 0)."""


def replay_one(cfg, fmt, s, stem, runs_b, r, pre_words, post_words, golden):
    lang, sf, F = golden
    src = os.path.join(cfg["systems"], stem + ".cftl")
    key = (stem, fmt)
    if key not in REPLAY_GRAPHS:
        REPLAY_GRAPHS[key] = lang.compile_text(read(src), os.path.basename(src), fmt).graph
    gph = REPLAY_GRAPHS[key]
    man, nst, nscr, names = manifest_state(cfg, stem)
    lane_names = [e["name"] for e in man["scratch"]["layout"] if e["kind"] != "state"]
    if [x[0] for x in gph.lane] != lane_names:
        raise SystemExit("the graph's lane params are not the manifest's order")
    p = runs_parse(runs_b)
    esz = p["esz"]
    rec = runs_b[p["off0"] + r * p["rec"]:p["off0"] + (r + 1) * p["rec"]]
    bank = rec[8 + esz:8 + esz + p["ncon"] * esz]
    bankv = {}
    for bnk in man["bank"]:
        if bnk["kind"] == "param":
            bankv[bnk["name"]] = int.from_bytes(bank[bnk["slot"] * esz:(bnk["slot"] + 1) * esz], "little")
    rr = lang.run(gph, [pre_words[:nst]], s, lane_params=[pre_words[nst:]], param_bits=bankv)
    got = rr.states[0]
    fm = F[fmt]
    same = all(x == y or (sf.is_nan(fm, x) and sf.is_nan(fm, y)) for x, y in zip(got, post_words))
    return same, got, int(rr.flags)


REPLAY_GRAPHS = {}


def golden_mods(cfg):
    sys.path.insert(0, os.path.join(cfg["fp256"], "python"))
    from cft_golden import formats, softfloat
    from cft_golden import lang
    return lang, softfloat, {"fp32": formats.FP32, "fp64": formats.FP64, "fp128": formats.FP128, "fp256": formats.FP256}


def words(b, esz):
    return [int.from_bytes(b[i:i + esz], "little") for i in range(0, len(b), esz)]


def mode_replay(cfg, a):
    log = i_lib.Log(cfg["logs"], "replay", SCRIPT, [REPLAY_CRIT], keep_dir=cfg["kept"], modules=MODULES)
    cpu = i_lib.Cpu("replay", os.path.join(cfg["scratch"], "cpu.tsv"))
    golden = golden_mods(cfg)
    e1 = os.path.join(cfg["desk"], "e1")
    # selftest 1: I1 d7 fp64, s = 1, run 0 segment 1, lanes 0 and 1
    c = [x for x in i1_cases(cfg) if x["case"] == "i1-program-d7-fp64"][0]
    runs_b = read(os.path.join(e1, c["case"] + ".s1.runs.bin"))
    p = runs_parse(runs_b)
    init = read(c["init"])
    seg = read(os.path.join(e1, c["case"] + ".s1.seg.bin"))
    recs = seg_records(seg, 16, 7, 8)
    lane_b = p["nscr"] * 8
    rec0 = runs_b[p["off0"]:p["off0"] + p["rec"]]
    shv = rec0[8 + 8 + p["ncon"] * 8:]
    shslots = struct.unpack_from("<%dI" % p["nsh"], runs_b, 32)
    for lane in (0, 1):
        pre = bytearray(init[lane * lane_b:(lane + 1) * lane_b])
        for i, sl in enumerate(shslots):
            pre[sl * 8:(sl + 1) * 8] = shv[i * 8:(i + 1) * 8]
        r, s_, so, lo = recs[0]
        post = words(seg[so + lane * 56:so + (lane + 1) * 56], 8)
        same, got, fl = replay_one(cfg, "fp64", 1, "program-d7-fp64", runs_b, 0, words(bytes(pre), 8), post, golden)
        log.check(same, "selftest: I1 d7 binary64 s = 1, run 0 segment 1, lane %d: the interpreter's state equals the "
                  "executor's (flags 0x%02x, the executor's lane byte 0x%02x)" % (lane, fl, seg[lo + lane]))
    # selftest 2: E1(iii) fp256 s = 8, segment 1, lane 0
    runs_b = read(os.path.join(e1, "i3b0-fp256.s8.runs.bin"))
    p = runs_parse(runs_b)
    plan = json.load(open(os.path.join(cfg["istage"], "i3", "plan.json"), "rb"))
    init = read(os.path.join(cfg["istage"], "i3", plan["batches"][0]["init"]["fp256"]))
    seg = read(os.path.join(e1, "i3b0-fp256.s8.seg.bin"))
    recs = seg_records(seg, 8, 7, 32)
    lane_b = p["nscr"] * 32
    rec0 = runs_b[p["off0"]:p["off0"] + p["rec"]]
    shv = rec0[8 + 32 + p["ncon"] * 32:]
    shslots = struct.unpack_from("<%dI" % p["nsh"], runs_b, 32)
    pre = bytearray(init[0:lane_b])
    for i, sl in enumerate(shslots):
        pre[sl * 32:(sl + 1) * 32] = shv[i * 32:(i + 1) * 32]
    r, s_, so, lo = recs[0]
    post = words(seg[so:so + 7 * 32], 32)
    same, got, fl = replay_one(cfg, "fp256", 8, "program-d7-fp256", runs_b, 0, words(bytes(pre), 32), post, golden)
    log.check(same, "selftest: E1(iii) binary256 s = 8, run 0 segment 1, lane 0: the interpreter's state equals the "
              "executor's (flags 0x%02x, lane byte 0x%02x)" % (fl, seg[lo]))
    # the card's marks
    if a.gpu or os.path.isdir(os.path.join(cfg["dj"], "gpu", a.run)):
        g = gpu_dir(cfg, a)
        ind = stage_dir(cfg, a)
        plan = json.load(open(os.path.join(ind, "plan.json"), "rb"))
        n = 0
        for dp, _dn, fns in os.walk(os.path.join(g, "out")):
            for fn in sorted(fns):
                if not fn.endswith(".marks.bin") or not os.path.getsize(os.path.join(dp, fn)):
                    continue
                pv = prov_read(os.path.join(dp, fn[:-len(".marks.bin")] + ".prov.txt"))
                img = pv["image"].split()[0]
                fmt = image_parse(read(os.path.join(g, img) if os.path.isfile(os.path.join(g, img)) else
                                       os.path.join(ind, img[3:])))["format"]
                stem = os.path.basename(img)[:-len(".cftp")]
                s = int(pv["seg_steps"])
                runs_rel = pv["runs"].split()[0]
                rpath = os.path.join(g, runs_rel) if os.path.isfile(os.path.join(g, runs_rel)) else os.path.join(ind, runs_rel[3:])
                runs_b = read(rpath)
                if i_lib.sha256_bytes(runs_b) != pv["runs"].split()[2]:
                    raise SystemExit("%s: the runs file found is not the one the run names" % fn)
                rp = runs_parse(runs_b)
                esz = rp["esz"]
                mk = read(os.path.join(dp, fn))
                rl = 12 + rp["nscr"] * esz + rp["nst"] * esz
                for o in range(0, len(mk), rl):
                    rr, ss, ll = struct.unpack_from("<3I", mk, o)
                    pre = words(mk[o + 12:o + 12 + rp["nscr"] * esz], esz)
                    post = words(mk[o + 12 + rp["nscr"] * esz:o + rl], esz)
                    same, got, fl = replay_one(cfg, fmt, s, stem, runs_b, rr, pre, post, golden)
                    n += 1
                    log.check(True, "mark %s run %d segment %d lane %d: the replay %s the card's state" % (
                        fn, rr, ss, ll, "EQUALS" if same else "DIFFERS FROM"))
        log.w("the card's marks replayed: %d" % n)
    cpu.close()
    sys.exit(1 if log.close() else 0)


ANALYZE_CRIT = """analyze (phase 2, desktop): J0c's table, J2's statistics and J3's measurement from the GPU's own records
(out/j0c/j0c.json, out/j2/j2.json, out/j3/j3.json), as gpu-j0c, gpu-j2 and gpu-j3 defined them before the data:
J2's X = B x 15 s x s x timed calls / timed wall time (object-seconds a second); each format's best batch: the median and
range of its valid samples; beside the box: X on the card over the box's I5 X at 36 workers (DEBRIS-I's
studies/debris-i/box/logs/box_i5.001.log, the same program and format), a ratio of rates from one sample on each side;
J3: the simulated span over its wall time. No pass condition."""


def mode_analyze(cfg, a):
    g = gpu_dir(cfg, a)
    log = i_lib.Log(cfg["logs"], "analyze", SCRIPT, [ANALYZE_CRIT], keep_dir=cfg["kept"], modules=MODULES)
    box = {}
    for ln in open(os.path.join(cfg["repo"], "studies", "debris-i", "box", "logs", "box_i5.001.log"), encoding="ascii"):
        if ln.startswith("FIG prog-") and " W=36:" in ln:
            w = ln.split()
            box[w[1][len("prog-"):]] = float(w[4])
    log.w("the box's I5 X at W = 36 (READ, DEBRIS-I's box_i5.001.log): %s" % box)
    j0c = json.load(open(os.path.join(latest_dir(os.path.join(g, "out"), "j0c", "j0c.json"), "j0c.json"), "rb"))
    s = j0c.get("chosen_s")
    for fmt, steps in sorted(j0c["ladder"].items()):
        for st in steps:
            log.w("FIG J0c %s s=%d: 8 lanes %s ms, %d lanes %s ms (warm-ups %.1f and %.1f ms)" % (
                fmt, st["s"], ["%.2f" % x for x in st["L8"]["calls_ms"]], st.get("L2048", {}).get("lanes", 2048),
                ["%.2f" % x for x in st.get("L2048", {}).get("calls_ms", [])], st["L8"]["warmup_ms"],
                st.get("L2048", {}).get("warmup_ms", -1)))
    log.w("FIG J0c the choice: s = %s" % s)
    try:
        jp = os.path.join(latest_dir(os.path.join(g, "out"), "j2", "j2.json"), "j2.json")
    except SystemExit:
        jp = ""
    if jp:
        j2 = json.load(open(jp, "rb"))
        for r in j2["rows"]:
            log.w("FIG J2 %s B=%d s=%d rep %d try %d: X %s, timed %d calls in %.2f s, %s" % (
                r["fmt"], r["B"], r["s"], r["rep"], r["attempt"], "%.1f" % r["X"] if r["X"] else "-", r["timed_calls"],
                r["wall_s"], "valid" if r["valid"] else ("stopped by the 1,000-ms rule" if r["stopped"] else
                                                         "void: " + ",".join(r["failed"]))))
        for fmt, B in sorted(j2["best"].items()):
            xs = sorted(r["X"] for r in j2["rows"] if r["fmt"] == fmt and r["B"] == B and r["valid"] and r["X"])
            med = xs[len(xs) // 2] if xs else None
            log.w("FIG J2 %s best batch %d: %d samples, median %s, range %s to %s; against the box's %s at W = 36: %s "
                  "(rates over rates)" % (fmt, B, len(xs), "%.1f" % med if med else "-", "%.1f" % xs[0] if xs else "-",
                                         "%.1f" % xs[-1] if xs else "-", box.get(fmt),
                                         "%.2f" % (med / box[fmt]) if med and fmt in box else "-"))
    try:
        jp = os.path.join(latest_dir(os.path.join(g, "out"), "j3", "j3.json"), "j3.json")
    except SystemExit:
        jp = ""
    if jp:
        j3 = json.load(open(jp, "rb"))
        for fmt, r in sorted(j3["formats"].items()):
            log.w("FIG J3 %s: %d lanes, %d simulated hours in %.1f s: %s times real time; marks %d" % (
                fmt, r["lanes"], r["hours"], r["wall_s"], "%.2f" % r["realtime_factor"] if r["realtime_factor"] else "-",
                len(r["marks"])))
    sys.exit(1 if log.close() else 0)


GPUCOPY_CRIT = """gpucopy: the repository's copies of the GPU's aggregate records (studies/debris-j/gpu/<run>/), made from the
ledger's debris-j/gpu/<run>/ as the lead copied it from cft-gpu: every log of logs/, and the json results of each
out/<mode>.<NNN>/ (j0.json, j0c.json, j1.json, j2-plan.json, j2.json, j3.json; no state, no INIT, no output file), each
with the run folder's path written as <root> and every PCI bus address (bus dddd:bb:dd.f) as "bus <redacted>"; the lines
changed are counted for each copy. Asserted: after the copy, no file under studies/debris-j/gpu/<run>/ holds a bus
address, the run folder's path, or a home path of the desktop."""


def mode_gpucopy(cfg, a):
    import re
    g = gpu_dir(cfg, a)
    dest = os.path.join(cfg["study"], "gpu", a.run)
    if os.path.exists(dest):
        raise SystemExit("%s exists: the copy goes to a new folder" % redact(cfg, dest))
    log = i_lib.Log(cfg["logs"], "gpucopy", SCRIPT, [GPUCOPY_CRIT], keep_dir=cfg["kept"], modules=MODULES)
    roots = set()
    for fn in os.listdir(os.path.join(g, "logs")):
        for ln in read(os.path.join(g, "logs", fn)).decode("utf-8", "replace").splitlines():
            m = re.search(r"(/root/[A-Za-z0-9._/-]*?)/(in|out|work|build|logs)/", ln)
            if m:
                roots.add(m.group(1))
    bus = re.compile(r"bus [0-9a-fA-F]{4}:[0-9a-fA-F]{2}:[0-9a-fA-F]{2}\.[0-9a-fA-F]")
    items = [(os.path.join(g, "logs", fn), os.path.join(dest, "logs", fn)) for fn in sorted(os.listdir(os.path.join(g, "logs")))]
    for d in sorted(os.listdir(os.path.join(g, "out"))):
        for fn in ("j0.json", "j0c.json", "j1.json", "j2-plan.json", "j2.json", "j3.json"):
            src = os.path.join(g, "out", d, fn)
            if os.path.isfile(src):
                items.append((src, os.path.join(dest, "out", d, fn)))
    for src, dst in items:
        text = read(src).decode("utf-8", "replace")
        out_lines, changed = [], 0
        for ln in text.split("\n"):
            new = bus.sub("bus <redacted>", ln)
            for r in sorted(roots, key=len, reverse=True):
                new = new.replace(r, "<root>")
            new = redact(cfg, new)
            changed += new != ln
            out_lines.append(new)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        write_new(dst, "\n".join(out_lines).encode("utf-8"))
        log.w("copied %s: %d lines changed; SHA-256 %s (the ledger's %s)" % (
            os.path.relpath(dst, cfg["study"]).replace("\\", "/"), changed, i_lib.sha256_file(dst), i_lib.sha256_file(src)))
    bad = []
    for dp, _dn, fns in os.walk(dest):
        for fn in fns:
            t = read(os.path.join(dp, fn)).decode("utf-8", "replace")
            if bus.search(t) or "/root/" in t or "C:/Users" in t or "C:\\Users" in t or "/c/Users" in t:
                bad.append(fn)
    log.check(not bad and items, "%d files copied; none holds a bus address, the run folder's path or a home path%s" % (
        len(items), (": " + str(bad)) if bad else ""))
    sys.exit(1 if log.close() else 0)


def mode_hostload(cfg, a):
    """The desktop's own CPU load, sampled every second from Windows' GetSystemTimes (busy = 1 - idle / (kernel + user),
    kernel time including idle), written as TSV lines (UTC time, busy share). The lead runs it beside J2 and J3."""
    import ctypes
    import ctypes.wintypes as w
    k = ctypes.WinDLL("kernel32", use_last_error=True)
    FT = w.FILETIME

    def now():
        i, kk, u = FT(), FT(), FT()
        k.GetSystemTimes(ctypes.byref(i), ctypes.byref(kk), ctypes.byref(u))
        f = lambda x: (x.dwHighDateTime << 32) | x.dwLowDateTime  # noqa: E731
        return f(i), f(kk), f(u)

    dur = float(a.seconds)
    with open(a.out, "x", encoding="ascii", newline="\n") as fo:
        fo.write("# hostload: the desktop's CPU busy share each second (GetSystemTimes), j_harness.py %s\n" %
                 i_lib.sha256_file(SCRIPT))
        t_end = time.time() + dur
        a0 = now()
        while time.time() < t_end:
            time.sleep(1.0)
            a1 = now()
            idle, kern, user = (a1[0] - a0[0]), (a1[1] - a0[1]), (a1[2] - a0[2])
            busy = 1.0 - idle / float(max(1, kern + user))
            fo.write("%s\t%.4f\n" % (time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime()), busy))
            fo.flush()
            a0 = a1


# ------------------------------------------------------------------ main

def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("mode")
    ap.add_argument("--cfg")
    ap.add_argument("--width", default="2")
    ap.add_argument("--only", default="")
    ap.add_argument("--formats", default="")
    ap.add_argument("--run", default="r1", help="stage: the run folder's name under gpu-stage/")
    ap.add_argument("--gpu", default="", help="compare, analyze, replay: the GPU's records copied to the ledger")
    ap.add_argument("--seconds", default="0", help="hostload: how long to sample")
    ap.add_argument("--out", default="", help="hostload: the output file")
    # the GPU modes (every path and the toolchain given by the lead)
    ap.add_argument("--root")
    ap.add_argument("--lock")
    ap.add_argument("--lock-wait", default="120")
    ap.add_argument("--expect-device")
    ap.add_argument("--other-device", default="NVIDIA GeForce RTX 4070")
    ap.add_argument("--smi-index")
    ap.add_argument("--cuda-visible")
    ap.add_argument("--hip-root")
    ap.add_argument("--hip-arch")
    ap.add_argument("--hip-cuda")
    ap.add_argument("--mem-max-mib")
    ap.add_argument("--util-max")
    ap.add_argument("--desktop-test", action="store_true", help="the GPU modes on the desktop's software executor")
    ap.add_argument("--jrun", default="", help="desktop test: the j_run to run")
    ap.add_argument("--test-hours", default="")
    ap.add_argument("--test-lanes", default="")
    ap.add_argument("--test-batches", default="")
    ap.add_argument("--test-segments", default="")
    ap.add_argument("--s", default="")
    ap.add_argument("--test-abort-ms", default="")
    ap.add_argument("--test-stop-ms", default="")
    a = ap.parse_args()
    for k in ("expect_device", "other_device"):       # '+' stands for a space (j_gpu.sh's note on wsl.exe)
        if getattr(a, k):
            setattr(a, k, getattr(a, k).replace("+", " "))
    desk = {"compile": mode_compile, "e1": mode_e1, "jgate": mode_jgate, "controls": mode_controls, "j3ref": mode_j3ref,
            "stage": mode_stage, "gpucopy": mode_gpucopy, "buildgate": mode_buildgate}
    gpu = {"gpu-j0": gpu_j0, "gpu-j0c": gpu_j0c, "gpu-j1": gpu_j1, "gpu-j2": gpu_j2, "gpu-j3": gpu_j3}
    if a.mode in desk:
        desk[a.mode](cfg_load(a.cfg), a)
    elif a.mode in gpu:
        if not a.root:
            raise SystemExit("--root is required")
        if not a.desktop_test:
            need = ["lock", "expect_device", "smi_index", "cuda_visible"] + (
                ["hip_root", "hip_arch", "hip_cuda"] if a.mode == "gpu-j0" else []) + (
                ["mem_max_mib", "util_max"] if a.mode == "gpu-j2" else [])
            miss = [n for n in need if not getattr(a, n)]
            if miss:
                raise SystemExit("%s needs %s" % (a.mode, ", ".join("--" + n.replace("_", "-") for n in miss)))
            if any(getattr(a, n) for n in ("test_hours", "test_lanes", "test_batches", "test_segments", "s", "jrun",
                                           "test_abort_ms", "test_stop_ms")):
                raise SystemExit("the --test-* options, --s and --jrun are for a desktop test only")
        gpu[a.mode](a)
    elif a.mode in ("compare", "analyze", "replay", "hostload"):
        globals()["mode_" + a.mode](cfg_load(a.cfg) if a.cfg else None, a)
    else:
        raise SystemExit("unknown mode %s" % a.mode)


if __name__ == "__main__":
    main()
