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
    c["logs"] = os.path.join(c["study"], "logs")
    c["kept"] = os.path.join(c["study"], "scripts")
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
    for k, tok in (("ledger", "<ledger>"), ("repo", "<repo>"), ("scratch", "<scratch>")):
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
            w = ln.split()
            R.segs.append({"run": int(w[1]), "seg": int(w[2]), "flags": int(w[4], 16), "bus": int(w[6], 16),
                           "call_ns": int(w[8]), "marked": int(w[10]),
                           "lanes": [int(x) for x in w[12:]] if len(w) > 12 else []})
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


# ------------------------------------------------------------------ main

def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("mode")
    ap.add_argument("--cfg")
    ap.add_argument("--width", default="3")
    ap.add_argument("--only", default="")
    a, _rest = ap.parse_known_args()
    desk = {"compile": mode_compile, "e1": mode_e1}
    if a.mode in desk:
        desk[a.mode](cfg_load(a.cfg), a)
    else:
        raise SystemExit("unknown mode %s" % a.mode)


if __name__ == "__main__":
    main()
