# h_itest.py - cft-debris M1 (DEBRIS-H): the desktop's integration test of the service's slot: the supervisor runs the
# fetcher against a local server on 127.0.0.1 (a thread of this script), then the check, on a small seed. A functional
# test, never a gate: it exercises tests/h_service.py's slot schedule, tests/h_fetch.py's test mode and tests/h_check.py
# together, which the gates test apart.
# cft-debris, MIT licence (see LICENSE at the repository root). Written by DEBRIS-H, 2026-11-18.
#
#   python -I -B tests/h_itest.py <root> --java JAVA [--logs DIR] [--keep DIR] [--cpu TSV]
# <root>: a staged root (in/, build/). Its seed: T_s 2026-11-16 06:00:00 TDB, so that DEBRIS-F's S1 holds sets later
# than T_s; objects: the first 8 of F6's pairs (catalogue order) that h_seed.py's rules keep and whose S1 epoch is at
# least 10 minutes after T_s, and the first 2 objects whose S1 row equals their S0 row. Tracks A64 and A64f (native64,
# so that the run is quick); the slot's bodies are S1's four files.
import argparse
import gzip
import json
import os
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import h_lib as H  # noqa: E402

SCRIPT = os.path.abspath(__file__)
TS = "2026-11-16T06:00:00"
KEND = 1680

CRITERIA = """
A FUNCTIONAL TEST (no gate): the supervisor, with the fetcher in test mode against this script's server on 127.0.0.1
and the check on, runs slot 1 (due at the start) on a seed of 10 objects at T_s 2026-11-16 06:00 TDB, a native64
track (A64 from seed 1), 1,680 steps with the clock map such that the end step is due 20 s after
the start (one track, A64, so that this script, the supervisor, its worker and the fetcher stay within the desktop's
4 processes; the check handles the tracks it finds). Expected: slot 1's four bodies kept; the check run for slot 1 with T1 and T3 passing; the per-object table
listing every eligible object as checked; the counts naming the objects whose S1 set is not later than their seed's.
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root")
    ap.add_argument("--java", required=True)
    ap.add_argument("--logs", default="logs")
    ap.add_argument("--keep")
    ap.add_argument("--cpu")
    a = ap.parse_args()
    os.chdir(a.root)
    here = os.path.relpath(os.path.dirname(SCRIPT))
    cpu = H.CpuAccount("h_itest", a.cpu)
    log = H.Log("h_itest", a.logs, SCRIPT, CRITERIA, extra=[os.path.join(here, f) for f in ("h_service.py", "h_fetch.py", "h_check.py", "h_seed.py")],
                keep_dir=a.keep)
    H.load_leaps("in/orekit/tai-utc.dat")
    _, W = H.next_numbered("itest", "run", "")
    os.makedirs(W)
    ts = float((H.mjd_of(2026, 11, 16) - H.MJD_E) * 86400 + 6 * 3600)
    s0 = {}
    s1 = {}
    for g in H.GROUPS:
        for r in H.read_gp("in/gp/gp-%s-S0.csv" % g, g):
            s0[r["NORAD_CAT_ID"]] = r
        for r in H.read_gp("in/gp/gp-%s-S1.csv" % g, g):
            s1[r["NORAD_CAT_ID"]] = r
    keys = [ln.split("\t")[0] for ln in open("in/ledger/f6_pairs.001.tsv", encoding="ascii") if not ln.startswith("#") and not ln.startswith("key")]
    sets = {}
    for r in s0.values():
        k = H.set_key(r)
        if k not in sets or int(r["NORAD_CAT_ID"]) < int(sets[k]["NORAD_CAT_ID"]):
            sets[k] = r
    kept = {r["NORAD_CAT_ID"] for r in sets.values()}
    late = [k for k in sorted(keys, key=int) if k in kept and float(H.epoch_tdb(s1[k])) >= ts + 600][:8]
    equal = [k for k in sorted(s0, key=int) if k in s1 and k in kept and all(s0[k][c] == s1[k][c] for c in H.COLUMNS)][:2]
    sel = late + equal
    log.w("# objects: %d with later S1 sets after T_s, %d with equal rows" % (len(late), len(equal)))
    seedd = os.path.join(W, "seed")
    for s in (1, 2):
        H.run([sys.executable, "-I", "-B", os.path.join(here, "h_seed.py"), "fit", "--seed", s, "--gp", "in/gp", "--tag", "S0", "--ts", TS, "--table",
               "in/frame_h0.bin", "--m1f", "build/m1f" + (".exe" if H.WIN else ""), "--java", a.java, "--jars", "in/jars", "--orekit", "in/orekit",
               "--decoder", "in/tests/f5_sgp4.js", "--leaps", "in/orekit/tai-utc.dat", "--out", seedd, "--logs", os.path.join(W, "logs"),
               "--procs", 1, "--jprocs", 1, "--test", "--select", ",".join(sel)], log)
    H.run([sys.executable, "-I", "-B", os.path.join(here, "h_seed.py"), "combine", "--fit1", os.path.join(seedd, "fit1.001.tsv"), "--fit2",
           os.path.join(seedd, "fit2.001.tsv"), "--out", seedd, "--logs", os.path.join(W, "logs")], log)
    sh0 = os.path.join(W, "sh0")
    os.makedirs(sh0)
    for g in H.GROUPS:
        with open("in/gp/gp-%s-S0.csv" % g, "rb") as fi, open(os.path.join(sh0, "gp-%s-SH0.csv" % g), "xb") as fo:
            fo.write(fi.read())
    bodies = {g: open("in/gp/gp-%s-S1.csv" % g, "rb").read() for g in H.GROUPS}
    seen = []

    class Hd(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, *x):
            pass

        def do_GET(self):
            g = self.path.split("GROUP=")[1].split("&")[0]
            seen.append((time.time(), self.path, self.headers.get("User-Agent"), self.headers.get("Accept-Encoding")))
            b = bodies[g]
            hdr = {}
            if H.GROUPS.index(g) % 2:
                b = gzip.compress(b)
                hdr["Content-Encoding"] = "gzip"
            self.send_response(200)
            for k, v in hdr.items():
                self.send_header(k, v)
            self.send_header("Content-Length", str(len(b)))
            self.end_headers()
            self.wfile.write(b)
    srv = ThreadingHTTPServer(("127.0.0.1", 0), Hd)
    th = threading.Thread(target=srv.serve_forever, daemon=True)
    th.start()
    base = "http://127.0.0.1:%d/NORAD/elements/gp.php" % srv.server_address[1]
    run = os.path.join(W, "svc")
    sh0_unix = time.time() - 3 * 3600.0 - 30.0
    rc, out, err = H.run([sys.executable, "-I", "-B", os.path.join(here, "h_service.py"), "init", ".", run,
                          "--track", "A64:native64:%s:1" % os.path.join(seedd, "seed1.txt"),
                          "--kend", KEND, "--clock", "launch:-%d" % (KEND * 15 - 20), "--fetch", "test:" + base, "--sh0-unix", "%.3f" % sh0_unix,
                          "--sh0-dir", sh0, "--check", "on", "--java", a.java, "--jars", "in/jars", "--orekit", "in/orekit", "--decoder", "in/tests/f5_sgp4.js",
                          "--seed-meta", os.path.join(seedd, "seed_meta.tsv"), "--check-procs", 1], log)
    t0 = time.time()
    rc, out, err = H.run([sys.executable, "-I", "-B", os.path.join(here, "h_service.py"), "start", ".", run], log, check=False, timeout=1800)
    log.w("# the service ran %.1f s, exit %d; the server saw %d requests" % (time.time() - t0, rc, len(seen)))
    srv.shutdown()
    sl = [ln.rstrip("\n").split("\t") for ln in open(os.path.join(run, "fetch", "slots.tsv"), encoding="utf-8") if ln[0].isdigit()]
    log.check(len(sl) == 1 and sl[0][0] == "1" and sl[0][1] == "ok" and sl[0][2] == "4", "slot 1 fetched: %s" % sl)
    clog = [f for f in os.listdir(os.path.join(run, "logs")) if f.startswith("check_slot01.")]
    txt = open(os.path.join(run, "logs", clog[0]), encoding="utf-8").read() if clog else ""
    log.check(bool(clog) and "PASS T1" in txt and "PASS T3" in txt and "# PASS" in txt, "the check of slot 1 ran, T1 and T3 passing")
    for ln in txt.splitlines():
        if ln.startswith("MEASURED") or ln.startswith("# counts"):
            log.w("#   check: " + ln)
    tab = os.path.join(run, "checks", "slot01.tsv")
    rows = [ln.rstrip("\n").split("\t") for ln in open(tab, encoding="ascii") if not ln.startswith("#")][1:] if os.path.exists(tab) else []
    nchk = sum(1 for r in rows if r[3] == "checked")
    log.check(nchk >= 1 and all(r[3] in ("checked",) for r in rows), "the per-object table: %d rows, %d checked" % (len(rows), nchk))
    svl = "".join(open(os.path.join(run, "logs", f), encoding="utf-8").read() for f in os.listdir(os.path.join(run, "logs")) if f.startswith("service."))
    log.check("FETCH slot 1 started" in svl and "CHECK slot 1 started" in svl and "END:" in svl, "the supervisor ran the fetcher, then the check, then ended")
    c_ = cpu.close("h_itest log %03d" % log.n)
    if c_ is not None:
        log.w("# CPU: %.2f s by cycles / 2.5e9 (this script and every process it started)" % c_)
    return log.close()


if __name__ == "__main__":
    sys.exit(main())
