# h_service.py - cft-debris M1 (DEBRIS-H), H-c: the supervisor of M1's service on amd-arc-box. Standard library only.
# cft-debris, MIT licence (see LICENSE at the repository root). Written by DEBRIS-H, 2026-11-18. Its foreign-load
# accounting follows DEBRIS-G's tests/g_harness.py (/proc/stat's busy jiffies less the service's own CPU).
#
#   python3 -I -B in/tests/h_service.py init  <root> <run> [options]      write <run>/service.json (it must not exist)
#   python3 -I -B in/tests/h_service.py start <root> <run> [--workers TRACK=N ...]   run the service (the lead starts it
#                                                                          with setsid; it outlives its ssh session)
#   python3 -I -B in/tests/h_service.py stop  <root> <run>               SIGTERM to the supervisor named in the run's
#                                                                          starts log (by PID, after checking its command line)
# <root> holds in/ (tests/h_stage.py's) and build/ (tests/h_build.py's); the supervisor works from <root> with relative
# paths, and <run> is relative to it.
#
# WHAT IT DOES (DEBRIS-H's brief, H-c, and the plan's "The design"):
# - One instance per run folder, held by flock on <run>/service.lock; the workers inherit the lock, so no second
#   supervisor can start while any worker of the first lives.
# - Each track (a kind and a seed) runs on its workers, at nice 19, unpinned, each worker a contiguous slice of the
#   seed's objects (tests/m1h.c run). The clock map is computed once, at init (the UTC of T_s) or at the first start
#   (a test's shift), and kept in <run>/clock_map.json, never rewritten.
# - Every checkpoint file a worker writes is hashed and appended to <run>/manifest.tsv. A file for a step that has
#   files already (a restart's rewrite) is compared object by object with them; if any object differs, the track stops.
# - A worker that exits before the end step makes the supervisor stop the rest of its track (SIGTERM: each finishes its
#   step) and restart the whole track from the latest checkpoint whose files all match the manifest and cover every
#   object, logging the checkpoint used. At most 6 restarts of a track in any hour; past that the track stops.
# - Every minute: /proc/stat's busy time less the CPU time of the supervisor and all its descendants (self, reaped
#   children, and every live descendant's utime + stime + cutime + cstime) is the foreign load, logged as a share of
#   the machine's CPUs (36 on the box); free space on <run>'s filesystem (under 5 GB: it creates <run>/PAUSE.disk, its
#   own pause file, and removes that file alone when free space is back above 6 GB); the pause files' state; and
#   <run>/status.json (each track's step, latest lag, latest checkpoint, the latest fetch and check, the restarts, the
#   foreign load).
# - At each slot (S_H0's request time + 3 j hours, j = 1 to 24, while the run lasts) it runs tests/h_fetch.py, then,
#   if the slot archived a body and the fetcher has not stopped, tests/h_check.py, each at nice 19. Only the latest
#   due slot runs; slots missed while the service was down are logged as missed.
# - The kinds' divergence: at every step where the first seed's cft256 and native64 tracks both have a complete
#   checkpoint, the median and largest distance between their binary64 positions over the objects not decayed.
# - At the end step every worker writes its final checkpoint and exits; the supervisor waits for any fetch or check,
#   writes a summary and exits. It never deletes a file (but its own PAUSE.disk), and never overwrites a log.
import argparse
import json
import math
import os
import signal
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import h_lib as H  # noqa: E402

SCRIPT = os.path.abspath(__file__)
WIN = H.WIN
EXE = "build/m1h" + (".exe" if WIN else "")
HOUR = 3600.0
SLOT_S = 3 * HOUR

CRITERIA = """
The supervisor's rules (DEBRIS-H's brief, H-c), fixed in this script: one instance per run folder (flock); the
workers at nice 19, unpinned, the clock map recorded once; every checkpoint hashed into the manifest, a restart's
rewrite compared object by object and a difference stopping the track; a restart of the whole track from the latest
checkpoint whose files all match the manifest and cover every object, at most 6 in any hour; the foreign load, the
free space, the pause files and status.json every minute; the fetcher then the check at each slot, at nice 19; the
kinds' divergence at every checkpoint of the first seed's cft256 and native64 tracks; no file deleted but its own
PAUSE.disk, no log overwritten, and no command line that cft-fp256's night launcher matches.
"""


def now():
    return time.time()


def rel(p):
    return p.replace("\\", "/")


# ------------------------------------------------------------------ init
def cmd_init(a):
    run = a.run
    cfgp = os.path.join(run, "service.json")
    if os.path.exists(cfgp):
        raise SystemExit("refused: %s exists" % cfgp)
    os.makedirs(run, exist_ok=True)
    tracks = []
    for t in a.track:
        name, kind, seed, w = t.split(":")
        tracks.append({"name": name, "kind": kind, "seed": rel(seed), "seed_sha256": H.sha256(seed), "workers": int(w)})
    seeds = {t["seed"]: H.read_seed(t["seed"]) for t in tracks}
    tss = {s["ts"] for s in seeds.values()}
    ns = {len(s["rows"]) for s in seeds.values()}
    if len(tss) != 1 or len(ns) != 1:
        raise SystemExit("the seeds must share T_s and their objects")
    ts = tss.pop()
    cfg = {"ts": ts, "ts_hex": float.hex(ts), "nobj": ns.pop(), "kend": a.kend, "lanes": a.lanes, "allow": a.allow, "ckpt_every": a.ckpt_every,
           "tracks": tracks, "table": rel(a.table), "table_sha256": H.sha256(a.table), "downloads": rel(a.downloads), "exe": EXE,
           "clock": a.clock, "leaps": rel(a.leaps), "pause_files": ["PAUSE", "PAUSE.disk"],
           "disk_pause_gb": a.disk_pause_gb, "disk_resume_gb": a.disk_resume_gb, "max_restarts_per_hour": 6,
           "fetch": a.fetch, "sh0_unix": a.sh0_unix, "sh0_dir": rel(a.sh0_dir) if a.sh0_dir else None, "slots": 24,
           "check": a.check, "java": a.java, "jars": rel(a.jars) if a.jars else None, "orekit": rel(a.orekit) if a.orekit else None,
           "decoder": rel(a.decoder) if a.decoder else None, "seed_meta": rel(a.seed_meta) if a.seed_meta else None,
           "check_procs": a.check_procs, "divergence": a.divergence, "created": now(), "created_by": "h_service.py sha256 %s" % H.sha256(SCRIPT),
           "test": {"kill_after": dict((x.split("=")[0], int(x.split("=")[1])) for x in a.test_kill_after),
                    "pause_from": dict((x.split("=")[0], int(x.split("=")[1])) for x in a.test_pause_from)}}
    if a.fetch != "off" and (a.sh0_unix is None or not a.sh0_dir):
        raise SystemExit("--fetch needs --sh0-unix and --sh0-dir")
    if a.check == "on" and (a.fetch == "off" or not (a.java and a.jars and a.orekit and a.decoder and a.seed_meta)):
        raise SystemExit("--check on needs the fetcher, --java, --jars, --orekit, --decoder and --seed-meta")
    if a.clock == "real":
        H.load_leaps(a.leaps)
        u, tr = H.clock_map(ts)
        cm = {"unix_ref": u, "t_ref": tr, "rule": "real: the UTC of T_s (tai-utc.dat and eq. 2.6)", "tdb_minus_utc_at_ts": H.tdb_minus_utc(ts),
              "made": now()}
        H.write_new(os.path.join(run, "clock_map.json"), json.dumps(cm, indent=1).encode("ascii"))
    H.write_new(cfgp, json.dumps(cfg, indent=1).encode("ascii"))
    print("init %s: %d objects, T_s %r (%s), tracks %s, clock %s" % (run, cfg["nobj"], ts, cfg["ts_hex"], ", ".join("%s %s x%d" % (t["name"], t["kind"], t["workers"]) for t in tracks), a.clock))
    return 0


# ------------------------------------------------------------------ the supervisor
class Service:
    def __init__(self, root, run, overrides, stop_at=None):
        self.root, self.run = root, run
        self.cfg = json.load(open(os.path.join(run, "service.json"), encoding="ascii"))
        self.overrides = overrides
        # tests only: the workers end at this checkpoint this time (the run's end step stays in service.json)
        self.kend = self.cfg["kend"] if stop_at is None else min(self.cfg["kend"], stop_at)
        self.t_start = now()
        self.term = False
        self.workers = {}          # pid -> dict
        self.tracks = {}
        self.fetch_p = None
        self.check_p = None
        self.check_queue = []
        self.div_done = set()
        self.last_minute = 0.0
        self.last_scan = 0.0
        self.load_prev = None
        self.foreign = None
        self.pause_state = {}
        self.disk_paused = os.path.exists(os.path.join(run, "PAUSE.disk"))
        self.last_fetch = None
        self.last_check = None
        self.manifest = []         # dicts
        self.seen_files = set()

    # -------------------------------------------------- logs
    def open_logs(self):
        os.makedirs(os.path.join(self.run, "logs"), exist_ok=True)
        self.log = H.Log("service", os.path.join(self.run, "logs"), SCRIPT, CRITERIA, quiet=True)
        self.log.w("# run %s; config sha256 %s; pid %d; started %.3f" % (self.run, H.sha256(os.path.join(self.run, "service.json")), os.getpid(), self.t_start))
        H.append_line(os.path.join(self.run, "logs", "starts.tsv"), "%.3f\t%d\t%s\tlog %03d" % (self.t_start, os.getpid(), " ".join(sys.argv[1:]), self.log.n))

    def w(self, s):
        self.log.w("%s %s" % (time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime()), s))

    # -------------------------------------------------- the lock
    def lock(self):
        p = os.path.join(self.run, "service.lock")
        self.lockf = open(p, "a+b")
        try:
            if WIN:
                import msvcrt
                self.lockf.seek(0)
                msvcrt.locking(self.lockf.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(self.lockf.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            raise SystemExit("refused: another supervisor, or a worker of one, holds %s" % p)

    # -------------------------------------------------- the clock map
    def clock_map(self):
        p = os.path.join(self.run, "clock_map.json")
        if os.path.exists(p):
            return json.load(open(p, encoding="ascii"))
        c = self.cfg["clock"]
        ts = self.cfg["ts"]
        if c == "past":
            u = now() - HOUR - 15.0 * self.cfg["kend"]
            rule = "past: every step due at once (a test)"
        elif c.startswith("launch:"):
            u = now() + float(c.split(":")[1])
            rule = "launch%+g s: T_s due at the first start's time %+g s (a test)" % (float(c.split(":")[1]), float(c.split(":")[1]))
        else:
            raise SystemExit("clock %s needs clock_map.json from init" % c)
        cm = {"unix_ref": u, "t_ref": ts, "rule": rule, "made": now()}
        H.write_new(p, json.dumps(cm, indent=1).encode("ascii"))
        return cm

    # -------------------------------------------------- the manifest
    def load_manifest(self):
        p = os.path.join(self.run, "manifest.tsv")
        if not os.path.exists(p):
            H.append_line(p, "# seen_unix\ttrack\tk\tfile\tsha256\tfirst\tcount\tworker\tnworkers\tbytes")
            return
        for ln in open(p, encoding="ascii"):
            if ln.startswith("#") or not ln.strip():
                continue
            q = ln.rstrip("\n").split("\t")
            d = {"seen": float(q[0]), "track": q[1], "k": int(q[2]), "file": q[3], "sha": q[4], "first": int(q[5]), "count": int(q[6]),
                 "worker": int(q[7]), "nworkers": int(q[8])}
            self.manifest.append(d)
            self.seen_files.add(d["file"])

    def scan(self):
        for t in self.cfg["tracks"]:
            d = os.path.join(self.run, "ckpt", t["name"])
            if not os.path.isdir(d):
                continue
            for f in sorted(os.listdir(d)):
                if f.startswith(".") or not f.endswith(".txt"):
                    continue
                relp = rel(os.path.join(d, f))
                if relp in self.seen_files:
                    continue
                hdr, rows = H.read_ckpt(relp)
                if not hdr.get("_complete"):
                    continue
                sha = H.sha256(relp)
                rec = {"seen": now(), "track": t["name"], "k": int(hdr["k"]), "file": relp, "sha": sha, "first": int(hdr["first"]),
                       "count": int(hdr["count"]), "worker": int(hdr["worker"]), "nworkers": int(hdr["nworkers"])}
                earlier = [m for m in self.manifest if m["track"] == rec["track"] and m["k"] == rec["k"]]
                self.manifest.append(rec)
                self.seen_files.add(relp)
                H.append_line(os.path.join(self.run, "manifest.tsv"), "%.3f\t%s\t%d\t%s\t%s\t%d\t%d\t%d\t%d\t%d" % (
                    rec["seen"], rec["track"], rec["k"], relp, sha, rec["first"], rec["count"], rec["worker"], rec["nworkers"], os.path.getsize(relp)))
                if earlier:
                    nsame = ndiff = 0
                    for m in earlier:
                        if H.sha256(m["file"]) != m["sha"]:
                            self.w("COMPARE %s k %d: the earlier file %s no longer matches the manifest; not used for the comparison" % (rec["track"], rec["k"], m["file"]))
                            continue
                        _, r0 = H.read_ckpt(m["file"])
                        for idx, row in rows.items():
                            if idx in r0:
                                if r0[idx] == row:
                                    nsame += 1
                                else:
                                    ndiff += 1
                    self.w("REWRITE %s k %d: %s compared with %d earlier file(s): %d objects equal, %d differ" % (rec["track"], rec["k"], relp, len(earlier), nsame, ndiff))
                    if ndiff:
                        self.stop_track(rec["track"], "a restart's checkpoint at step %d differs from the original in %d objects" % (rec["k"], ndiff))

    def complete_at(self, track, k, verify=True):
        """the files covering every object at step k, all matching the manifest; or None"""
        n = self.cfg["nobj"]
        rows = [m for m in self.manifest if m["track"] == track and m["k"] == k]
        if not rows:
            return None
        groups = {}
        for m in rows:
            groups.setdefault(m["nworkers"], []).append(m)
        candidates = list(groups.values()) + [rows]
        for g in candidates:
            cov = [False] * n
            chosen = []
            for m in g:
                rng = range(m["first"], m["first"] + m["count"])
                if any(cov[i] for i in rng):
                    continue
                if verify and H.sha256(m["file"]) != m["sha"]:
                    self.w("REFUSED %s k %d: %s does not match its manifest hash (nothing starts from it)" % (track, k, m["file"]))
                    continue
                for i in rng:
                    cov[i] = True
                chosen.append(m)
            if all(cov):
                return chosen
        return None

    def latest_complete(self, track):
        ks = sorted({m["k"] for m in self.manifest if m["track"] == track}, reverse=True)
        for k in ks:
            ch = self.complete_at(track, k)
            if ch is not None:
                return k, ch
            self.w("INCOMPLETE %s k %d: its files do not cover every object with matching hashes" % (track, k))
        return None, None

    # -------------------------------------------------- workers
    def worker_argv(self, t, i, W, first, count, k0, init):
        c, cm = self.cfg, self.cm
        a = [c["exe"], "run", "--kind", t["kind"], "--table", c["table"], "--track", t["name"], "--run", self.run, "--first", first, "--count", count,
             "--lanes", c["lanes"], "--k0", k0, "--kend", self.kend, "--unix-ref", "%.6f" % cm["unix_ref"], "--t-ref", float.hex(cm["t_ref"]),
             "--allow", c["allow"], "--ckpt-every", c["ckpt_every"], "--worker", i, "--nworkers", W]
        tst = c.get("test", {})
        ka = tst.get("kill_after", {}).get(t["name"])
        if ka is not None and k0 < ka and not self.tracks.get(t["name"], {}).get("restarts"):
            a += ["--test-kill-after", ka]
        pf = tst.get("pause_from", {}).get(t["name"])
        if pf is not None:
            a += ["--test-pause-from", pf]
        if init is None:
            a += ["--seed", "%s:%s" % (t["seed"], t["seed_sha256"])]
        else:
            for m in init:
                if m["first"] < first + count and first < m["first"] + m["count"]:
                    a += ["--init", "%s:%s" % (m["file"], m["sha"])]
        return [str(x) for x in a]

    def spawn(self, argv, nice=True, tag="child"):
        H.assert_safe(argv)
        env = dict(os.environ)
        env["M1_DOWNLOADS"] = self.cfg["downloads"]
        # each child's output to a file of its own (a worker's m1_die message, the fetcher's and the check's lines)
        od = os.path.join(self.run, "logs", "out")
        os.makedirs(od, exist_ok=True)
        _, op = H.next_numbered(od, tag, ".txt")
        fo = open(op, "xb")
        kw = {"stdout": fo, "stderr": subprocess.STDOUT, "env": env}
        if not WIN:
            lockfd = self.lockf.fileno()

            def pre():
                if nice:
                    os.setpriority(os.PRIO_PROCESS, 0, 19)
                try:
                    import ctypes
                    ctypes.CDLL("libc.so.6", use_errno=True).prctl(1, signal.SIGTERM)  # PR_SET_PDEATHSIG
                except Exception:
                    pass
            kw["preexec_fn"] = pre
            kw["pass_fds"] = (lockfd,)
        try:
            return H.popen(argv, **kw)
        finally:
            fo.close()  # the child holds its own copy

    def start_track(self, t, why):
        name = t["name"]
        W = int(self.overrides.get(name, t["workers"]))
        k0, init = self.latest_complete(name)
        if k0 is None:
            k0, init = 0, None
        if k0 >= self.kend:
            self.tracks[name]["state"] = "done"
            self.w("TRACK %s is done already (checkpoint %d)" % (name, k0))
            return
        n = self.cfg["nobj"]
        W = max(1, min(W, n))
        base, extra = divmod(n, W)
        first = 0
        pids = []
        for i in range(W):
            cnt = base + (1 if i < extra else 0)
            argv = self.worker_argv(t, i, W, first, cnt, k0, init)
            p = self.spawn(argv, tag="%s.w%02dof%02d" % (name, i, W))
            self.workers[p.pid] = {"p": p, "track": name, "worker": i, "nworkers": W, "k0": k0, "started": now()}
            H.append_line(os.path.join(self.run, "logs", "workers.tsv"), "%.3f\t%s\t%d\t%d\t%d\t%d\t%s" % (
                now(), name, i, W, p.pid, k0, "seed" if init is None else ",".join(m["file"] for m in init)))
            pids.append(p.pid)
            first += cnt
        tr = self.tracks[name]
        tr.update({"state": "running", "W": W, "k0": k0})
        self.w("START %s (%s): %d workers from %s, k0 %d; pids %s; %s" % (name, t["kind"], W, "the seed" if init is None else "checkpoint %d (%s)" % (
            k0, ", ".join(m["file"] for m in init)), k0, pids, why))

    def stop_track(self, name, why):
        tr = self.tracks[name]
        if tr["state"] in ("stopped",):
            return
        tr["state"] = "stopped"
        tr["why"] = why
        self.w("STOP TRACK %s: %s" % (name, why))
        for pid, wk in list(self.workers.items()):
            if wk["track"] == name and wk["p"].poll() is None:
                self.terminate(wk["p"])

    def terminate(self, p):
        try:
            if WIN:
                p.terminate()
            else:
                os.kill(p.pid, signal.SIGTERM)
        except OSError:
            pass

    def reap(self):
        for pid, wk in list(self.workers.items()):
            rc = wk["p"].poll()
            if rc is None:
                continue
            del self.workers[pid]
            name = wk["track"]
            tr = self.tracks[name]
            self.w("EXIT %s worker %d of %d (pid %d): code %d" % (name, wk["worker"], wk["nworkers"], pid, rc))
            if rc == 0:
                continue
            if tr["state"] == "running":
                tr["state"] = "restarting"
                tr["why"] = "worker %d (pid %d) exited with code %d" % (wk["worker"], pid, rc)
                for pid2, wk2 in self.workers.items():
                    if wk2["track"] == name:
                        self.terminate(wk2["p"])
        for t in self.cfg["tracks"]:
            name = t["name"]
            tr = self.tracks[name]
            alive = [w for w in self.workers.values() if w["track"] == name]
            if alive:
                continue
            if tr["state"] == "running":
                self.scan()  # the final checkpoint may not be in the manifest yet
                k, _ = self.latest_complete(name)
                tr["state"] = "done" if k == self.kend else "restarting"
                if tr["state"] == "done":
                    self.w("TRACK %s done: checkpoint %d complete" % (name, k))
                else:
                    tr["why"] = "every worker exited, the end step's checkpoint incomplete"
            if tr["state"] == "restarting" and not self.term:
                self.scan()
                recent = [x for x in tr["restarts"] if now() - x < HOUR]
                if len(recent) >= self.cfg["max_restarts_per_hour"]:
                    self.stop_track(name, "a 7th restart within an hour (restarts at %s)" % recent)
                    continue
                tr["restarts"].append(now())
                self.start_track(t, "RESTART %d: %s" % (len(tr["restarts"]), tr.get("why")))

    # -------------------------------------------------- the minute
    def own_cpu(self):
        """CPU seconds of this process, its reaped children and every live descendant"""
        import resource
        s = resource.getrusage(resource.RUSAGE_SELF)
        c = resource.getrusage(resource.RUSAGE_CHILDREN)
        tot = s.ru_utime + s.ru_stime + c.ru_utime + c.ru_stime
        tck = os.sysconf("SC_CLK_TCK")
        procs = {}
        for d in os.listdir("/proc"):
            if not d.isdigit():
                continue
            try:
                with open("/proc/%s/stat" % d, encoding="ascii", errors="replace") as f:
                    st = f.read()
            except OSError:
                continue
            r = st[st.rfind(")") + 2:].split()
            procs[int(d)] = (int(r[1]), int(r[11]) + int(r[12]) + int(r[13]) + int(r[14]))
        me = os.getpid()
        desc, frontier = set(), {me}
        while frontier:
            nxt = {p for p, (pp, _) in procs.items() if pp in frontier and p not in desc}
            desc |= nxt
            frontier = nxt
        return tot + sum(procs[p][1] for p in desc) / tck

    def minute(self):
        t = now()
        if not WIN:
            busy = H.stat_busy() / os.sysconf("SC_CLK_TCK")
            own = self.own_cpu()
            ncpu = H.cpu_count_stat()
            if self.load_prev is not None:
                t0, b0, o0 = self.load_prev
                dt = t - t0
                fcpu = (busy - b0) - (own - o0)
                share = fcpu / (ncpu * dt) if dt > 0 else float("nan")
                self.foreign = {"t0": t0, "t1": t, "share": share, "ncpu": ncpu}
                self.w("LOAD %.3f %.3f busy_cpu_s %.2f own_cpu_s %.2f foreign_cpu_s %.2f foreign_share %.5f ncpu %d" % (t0, t, busy - b0, own - o0, fcpu, share, ncpu))
            self.load_prev = (t, busy, own)
        # the disk
        try:
            if WIN:
                import shutil
                free = shutil.disk_usage(self.run).free
            else:
                st = os.statvfs(self.run)
                free = st.f_bavail * st.f_frsize
        except OSError:
            free = None
        pd = os.path.join(self.run, "PAUSE.disk")
        if free is not None:
            if free < self.cfg["disk_pause_gb"] * 1e9 and not os.path.exists(pd):
                H.write_new(pd, ("free %d bytes at %.3f\n" % (free, t)).encode("ascii"))
                self.disk_paused = True
                self.w("DISK free %.2f GB under %g GB: PAUSE.disk created" % (free / 1e9, self.cfg["disk_pause_gb"]))
            elif free > self.cfg["disk_resume_gb"] * 1e9 and self.disk_paused and os.path.exists(pd):
                os.remove(pd)  # the supervisor's own pause file: the one file it removes
                self.disk_paused = False
                self.w("DISK free %.2f GB above %g GB: PAUSE.disk removed" % (free / 1e9, self.cfg["disk_resume_gb"]))
        self.status(free)

    def pauses(self):
        for f in self.cfg["pause_files"]:
            e = os.path.exists(os.path.join(self.run, f))
            if self.pause_state.get(f) != e:
                if f in self.pause_state or e:
                    self.w("PAUSEFILE %s %s" % (f, "present" if e else "absent"))
                self.pause_state[f] = e

    def track_progress(self, name):
        d = os.path.join(self.run, "steps", name)
        best = (None, None)
        if not os.path.isdir(d):
            return best
        for f in os.listdir(d):
            p = os.path.join(d, f)
            try:
                with open(p, "rb") as fh:
                    fh.seek(max(0, os.path.getsize(p) - 4096))
                    tail = fh.read().decode("ascii", "replace").splitlines()
            except OSError:
                continue
            for ln in reversed(tail):
                q = ln.split()
                if q and q[0] == "S" and len(q) >= 6:
                    k, lag = int(q[1]), float(q[5])
                    if best[0] is None or k > best[0]:
                        best = (k, lag)
                    break
        return best

    def status(self, free):
        st = {"time": now(), "pid": os.getpid(), "tracks": {}, "foreign": self.foreign, "free_bytes": free, "pause": self.pause_state,
              "last_fetch": self.last_fetch, "last_check": self.last_check, "fetch_stopped": os.path.exists(os.path.join(self.run, "fetch", "STOP"))}
        for t in self.cfg["tracks"]:
            n = t["name"]
            k, lag = self.track_progress(n)
            ks = sorted({m["k"] for m in self.manifest if m["track"] == n})
            tr = self.tracks[n]
            st["tracks"][n] = {"state": tr["state"], "workers": tr.get("W"), "step": k, "lag_s": lag, "latest_checkpoint": ks[-1] if ks else None,
                               "restarts": len(tr["restarts"])}
        p = os.path.join(self.run, "status.json")
        tmp = p + ".%d.tmp" % os.getpid()
        with open(tmp, "w", encoding="ascii", newline="\n") as f:
            json.dump(st, f, indent=1)
        os.replace(tmp, p)

    # -------------------------------------------------- the kinds' divergence
    def divergence(self):
        dv = self.cfg.get("divergence")
        if not dv:
            return
        a, b = dv.split(",")
        ka = {m["k"] for m in self.manifest if m["track"] == a}
        kb = {m["k"] for m in self.manifest if m["track"] == b}
        for k in sorted((ka & kb) - self.div_done):
            ca, cb = self.complete_at(a, k, verify=False), self.complete_at(b, k, verify=False)
            if ca is None or cb is None:
                continue
            ra, rb = {}, {}
            for m in ca:
                ra.update(H.read_ckpt(m["file"])[1])
            for m in cb:
                rb.update(H.read_ckpt(m["file"])[1])
            ds = []
            for i in ra:
                if ra[i][0] >= 0 or rb[i][0] >= 0:
                    continue
                pa = [H.f64(x) for x in ra[i][2][:3]]
                pb = [H.f64(x) for x in rb[i][2][:3]]
                ds.append(H.dist(pa, pb))
            self.div_done.add(k)
            if ds:
                self.w("DIV %s-%s k %d t %s n %d median_m %.6e max_m %.6e zero %d" % (a, b, k, float.hex(self.cfg["ts"] + 15.0 * k), len(ds), H.median(ds), max(ds),
                                                                                 sum(1 for x in ds if x == 0.0)))

    # -------------------------------------------------- slots
    def slots(self):
        c = self.cfg
        if c["fetch"] == "off":
            return
        fdir = os.path.join(self.run, "fetch")
        if self.fetch_p is not None:
            rc = self.fetch_p.poll()
            if rc is None:
                return
            j = self.fetch_j
            self.fetch_p = None
            res = self.slot_result(j)
            self.last_fetch = {"slot": j, "code": rc, "result": res, "time": now()}
            self.w("FETCH slot %d ended: code %d, %s" % (j, rc, res))
            if c["check"] == "on" and res and res.get("bodies", 0) > 0 and not os.path.exists(os.path.join(fdir, "STOP")):
                self.check_queue.append(j)
        if self.check_p is not None:
            rc = self.check_p.poll()
            if rc is not None:
                self.last_check = {"slot": self.check_j, "code": rc, "time": now()}
                self.w("CHECK slot %d ended: code %d" % (self.check_j, rc))
                self.check_p = None
        if self.check_p is None and self.check_queue:
            j = self.check_queue.pop(0)
            argv = ["python3" if not WIN else sys.executable, "-I", "-B", "in/tests/h_check.py", "slot", self.run, str(j), "--procs", str(c["check_procs"])]
            self.check_p = self.spawn(argv, tag="check.slot%02d" % j)
            self.check_j = j
            self.w("CHECK slot %d started (pid %d)" % (j, self.check_p.pid))
        if self.fetch_p is not None or os.path.exists(os.path.join(fdir, "STOP")):
            return
        t = now()
        j = int(math.floor((t - c["sh0_unix"]) / SLOT_S))
        if j < 1 or j > c["slots"]:
            return
        if t > self.end_unix:
            return
        done = self.slots_attempted()
        if j in done or (done and j <= max(done)):
            return
        missed = [x for x in range(1, j) if x not in done and (not done or x > max(done))]
        if missed:
            self.w("SLOTS missed while the service was down: %s" % missed)
        argv = ["python3" if not WIN else sys.executable, "-I", "-B", "in/tests/h_fetch.py", "slot", fdir, str(j), "--sh0-unix", "%.3f" % c["sh0_unix"],
                "--sh0-dir", c["sh0_dir"]]
        if c["fetch"].startswith("test:"):
            argv += ["--test-base", c["fetch"][5:]]
        self.fetch_p = self.spawn(argv, tag="fetch.slot%02d" % j)
        self.fetch_j = j
        self.w("FETCH slot %d started (pid %d), due %.3f" % (j, self.fetch_p.pid, c["sh0_unix"] + j * SLOT_S))

    def slots_attempted(self):
        p = os.path.join(self.run, "fetch", "slots.tsv")
        out = set()
        if os.path.exists(p):
            for ln in open(p, encoding="ascii"):
                q = ln.split("\t")
                if q and q[0].isdigit():
                    out.add(int(q[0]))
        return out

    def slot_result(self, j):
        p = os.path.join(self.run, "fetch", "slots.tsv")
        res = None
        if os.path.exists(p):
            for ln in open(p, encoding="ascii"):
                q = ln.rstrip("\n").split("\t")
                if q and q[0] == str(j) and len(q) >= 4:
                    res = {"status": q[1], "bodies": int(q[2]), "note": q[3]}
        return res

    # -------------------------------------------------- the loop
    def on_term(self, *_):
        self.term = True

    def stop_requested(self):
        p = os.path.join(self.run, "STOP")
        return os.path.exists(p) and os.path.getmtime(p) > self.t_start

    def main(self):
        self.lock()
        self.open_logs()
        signal.signal(signal.SIGTERM, self.on_term)
        self.cm = self.clock_map()
        c = self.cfg
        self.end_unix = self.cm["unix_ref"] + (c["ts"] + 15.0 * c["kend"] - self.cm["t_ref"])
        self.w("CLOCK unix_ref %.6f t_ref %s (%s); the end step %d is due at %.3f" % (self.cm["unix_ref"], float.hex(self.cm["t_ref"]), self.cm["rule"], c["kend"], self.end_unix))
        for t in c["tracks"]:
            H.assert_safe(self.worker_argv(t, 0, 1, 0, 1, 0, None))
            if H.sha256(t["seed"]) != t["seed_sha256"]:
                self.w("REFUSED: %s does not match service.json's hash" % t["seed"])
                return self.log.close()
        if H.sha256(c["table"]) != c["table_sha256"]:
            self.w("REFUSED: the frame table does not match service.json's hash")
            return self.log.close()
        if WIN:
            self.w("# desktop: nice, the death signal, flock and /proc are skipped here (msvcrt's lock instead)")
        self.load_manifest()
        self.scan()
        for t in c["tracks"]:
            self.tracks[t["name"]] = {"state": "new", "restarts": []}
            self.start_track(t, "start of the supervisor")
        last_tick_min = 0.0
        while True:
            t = now()
            if self.term or self.stop_requested():
                self.w("STOP requested: SIGTERM to every worker and child; waiting for them")
                break
            self.reap()
            if t - self.last_scan >= 5.0:
                self.scan()
                self.divergence()
                self.last_scan = t
            self.pauses()
            self.slots()
            if t - last_tick_min >= 60.0:
                self.minute()
                last_tick_min = t
            states = {n: tr["state"] for n, tr in self.tracks.items()}
            if all(s in ("done", "stopped") for s in states.values()) and self.fetch_p is None and self.check_p is None and not self.check_queue:
                if c["fetch"] == "off" or t > self.end_unix or os.path.exists(os.path.join(self.run, "fetch", "STOP")):
                    self.scan()
                    self.divergence()
                    self.w("END: tracks %s" % states)
                    break
            time.sleep(1.0)
        # stop everything still running
        kids = [w["p"] for w in self.workers.values()] + [p for p in (self.fetch_p, self.check_p) if p is not None]
        for p in kids:
            if p.poll() is None:
                self.terminate(p)
        t0 = now()
        while any(p.poll() is None for p in kids) and now() - t0 < 300:
            time.sleep(0.5)
        for p in kids:
            if p.poll() is None:
                self.w("a child (pid %d) did not exit within 300 s of SIGTERM; left running" % p.pid)
        self.reap_final()
        self.scan()
        self.divergence()
        self.minute()
        self.summary()
        return self.log.close()

    def reap_final(self):
        for pid, wk in list(self.workers.items()):
            rc = wk["p"].poll()
            self.w("EXIT %s worker %d of %d (pid %d): code %s (at the supervisor's end)" % (wk["track"], wk["worker"], wk["nworkers"], pid, rc))
            del self.workers[pid]

    def summary(self):
        lines = ["# h_service summary, %s; log service.%03d.log" % (time.strftime("%Y-%m-%d %H:%M:%S %z"), self.log.n)]
        for t in self.cfg["tracks"]:
            n = t["name"]
            tr = self.tracks[n]
            ks = sorted({m["k"] for m in self.manifest if m["track"] == n})
            k, lag = self.track_progress(n)
            lines.append("track %s kind %s state %s workers %s restarts %d last_step %s last_lag_s %s checkpoints %d latest %s%s" % (
                n, t["kind"], tr["state"], tr.get("W"), len(tr["restarts"]), k, lag, len(ks), ks[-1] if ks else None,
                ("; " + tr["why"]) if tr.get("why") and tr["state"] == "stopped" else ""))
        lines.append("fetch: last %s; stopped %s" % (self.last_fetch, os.path.exists(os.path.join(self.run, "fetch", "STOP"))))
        lines.append("check: last %s" % self.last_check)
        lines.append("manifest: %d files" % len(self.manifest))
        _, p = H.next_numbered(os.path.join(self.run, "logs"), "summary", ".txt")
        H.write_new(p, ("\n".join(lines) + "\n").encode("ascii"))
        for ln in lines:
            self.w("SUMMARY " + ln)


def cmd_stop(a):
    p = os.path.join(a.run, "logs", "starts.tsv")
    last = [ln.split("\t") for ln in open(p, encoding="ascii") if ln.strip()][-1]
    pid = int(last[1])
    if WIN:
        H.write_new(os.path.join(a.run, "STOP"), ("stop requested at %.3f\n" % now()).encode("ascii"))
        print("wrote %s/STOP for pid %d" % (a.run, pid))
        return 0
    cl = open("/proc/%d/cmdline" % pid, "rb").read().replace(b"\0", b" ").decode("utf-8", "replace")
    if "h_service.py" not in cl or a.run not in cl:
        raise SystemExit("refused: pid %d is not this run's supervisor (%s)" % (pid, cl))
    os.kill(pid, signal.SIGTERM)
    print("SIGTERM sent to pid %d (%s)" % (pid, cl.strip()))
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["init", "start", "stop"])
    ap.add_argument("root")
    ap.add_argument("run")
    ap.add_argument("--track", action="append", default=[], help="NAME:KIND:SEEDFILE:WORKERS")
    ap.add_argument("--kend", type=int, default=17280)
    ap.add_argument("--lanes", type=int, default=64)
    ap.add_argument("--allow", type=int, default=4)
    ap.add_argument("--ckpt-every", type=int, default=40)
    ap.add_argument("--table", default="in/frame_h0.bin")
    ap.add_argument("--downloads", default="in/dl/")
    ap.add_argument("--leaps", default="in/orekit/tai-utc.dat")
    ap.add_argument("--clock", default="real", help="real | past | launch:+60 | launch:-600")
    ap.add_argument("--disk-pause-gb", type=float, default=5.0)
    ap.add_argument("--disk-resume-gb", type=float, default=6.0)
    ap.add_argument("--fetch", default="off", help="off | live | test:http://127.0.0.1:PORT/path")
    ap.add_argument("--sh0-unix", type=float)
    ap.add_argument("--sh0-dir")
    ap.add_argument("--check", default="off", choices=["off", "on"])
    ap.add_argument("--java")
    ap.add_argument("--jars")
    ap.add_argument("--orekit")
    ap.add_argument("--decoder")
    ap.add_argument("--seed-meta")
    ap.add_argument("--check-procs", type=int, default=4)
    ap.add_argument("--divergence", default=None, help="TRACK_A,TRACK_B: the first seed's cft256 and native64 tracks")
    ap.add_argument("--workers", action="append", default=[], help="TRACK=N (start only)")
    ap.add_argument("--stop-at", type=int, default=None, help="start only, tests: the workers end at this checkpoint this time")
    ap.add_argument("--test-kill-after", action="append", default=[], help="init only, tests (H2): TRACK=K")
    ap.add_argument("--test-pause-from", action="append", default=[], help="init only, tests (H2): TRACK=K")
    a = ap.parse_args()
    H.assert_safe([sys.executable] + sys.argv)  # the supervisor's own command line, as cft-fp256's launcher would see it
    os.chdir(a.root)
    a.run = rel(a.run)
    if a.cmd == "init":
        if not a.track:
            raise SystemExit("init needs --track NAME:KIND:SEEDFILE:WORKERS (one or more)")
        return cmd_init(a)
    if a.cmd == "stop":
        return cmd_stop(a)
    ov = dict(x.split("=") for x in a.workers)
    return Service(a.root, a.run, ov, a.stop_at).main()


if __name__ == "__main__":
    sys.exit(main())
