"""i_partb.py - cft-debris DEBRIS-I, part B: the tests of B2 (tests/i_service.py, the skipped slot's log line) and B3
(tests/i_fetch.py and tests/i3_server.py, each request's time to its first byte and to its last). Standard library only.
Nothing is requested of any host but 127.0.0.1; the server is started here and stopped by its PID.

cft-debris, MIT licence (see LICENSE at the repository root). Written by DEBRIS-I, 2026-11-23.

usage: python -I -B i_partb.py <work dir> <log dir>
"""
import importlib.util
import json
import math
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import i_lib  # noqa: E402

CRIT = """B2 (tests/i_service.py): a run folder with the fetch stop file in place; the scheduler (Service.slots, the clock
    replaced, the fetcher's start replaced by a record of its arguments) ticks at slot 1's and slot 2's due times plus
    10 s, three times each; the stop file is renamed; it ticks at slot 3's due time plus 10 s; then slot 4 falls due with
    no tick (the service down) and it ticks at slot 5's. PASS: "SLOT 1 skipped under the stop file" and "SLOT 2 ..."
    each logged exactly once; no "missed while the service was down" line names slot 1 or 2; slot 3's fetch starts;
    at slot 5 the line "SLOTS missed while the service was down: [4]" (the old text, for a slot the service was not
    running for).
 B2's control: DEBRIS-H's tests/h_service.py, unchanged, on the same ticks, must log "SLOTS missed while the service
    was down: [1, 2]" at slot 3 (the old text for the slots under the stop) and no "skipped" line.
B3 (tests/i_fetch.py against tests/i3_server.py on 127.0.0.1): a slot of four requests (spacing removed for the test):
    with the server's 5 s delay before its response, the fetcher must log a time to the first byte of at least 5 s; with
    no delay, under 1 s.
 B3's control: with the delay moved after the first byte (delay_after_first 5 s), the time to the first byte must stay
    under 1 s and the time to the last byte must pass 5 s."""


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def b2(work, modfile, tag):
    m = load("svc_" + tag, os.path.join(HERE, modfile))
    run = os.path.join(work, "b2-%s" % tag)
    os.makedirs(os.path.join(run, "fetch"))
    sh0 = 1_800_000_000.0
    cfg = {"ts": 0.0, "kend": 5760, "fetch": "test:http://127.0.0.1:9/x", "sh0_unix": sh0, "sh0_dir": "x", "slots": 24,
           "check": "off", "check_procs": 1, "tracks": []}
    with open(os.path.join(run, "service.json"), "w", encoding="ascii", newline="\n") as f:
        json.dump(cfg, f)
    open(os.path.join(run, "fetch", "STOP"), "w").write("planted\n")
    svc = m.Service(work, run, {})
    svc.end_unix = sh0 + 25 * m.SLOT_S
    lines = []
    svc.w = lambda s: lines.append(s)
    clock = [0.0]
    m.now = lambda: clock[0]

    class P:
        def __init__(self, j):
            self.pid, self.j = 4242, j

        def poll(self):
            # the fetcher's run: it records the slot as attempted, as h_fetch.py does, and ends
            with open(os.path.join(run, "fetch", "slots.tsv"), "a", encoding="ascii") as f:
                f.write("%d\tok\t4\t\t0\t0\n" % self.j)
            return 0

    started = []

    def spawn(argv, nice=True, tag="child"):
        j = int(argv[argv.index("slot") + 2])
        started.append(j)
        return P(j)
    svc.spawn = spawn
    for j in (1, 2):
        for k in range(3):
            clock[0] = sh0 + j * m.SLOT_S + 10 + k
            svc.slots()
    os.rename(os.path.join(run, "fetch", "STOP"), os.path.join(run, "fetch", "STOP.renamed"))
    clock[0] = sh0 + 3 * m.SLOT_S + 10
    svc.slots()
    clock[0] = sh0 + 3 * m.SLOT_S + 20
    svc.slots()   # the fetch of slot 3 ends
    clock[0] = sh0 + 5 * m.SLOT_S + 10
    svc.slots()
    return lines, started


def b3(work, log):
    srv = os.path.join(HERE, "i3_server.py")
    body = ",".join(["OBJECT_NAME", "OBJECT_ID", "EPOCH", "MEAN_MOTION", "ECCENTRICITY", "INCLINATION", "RA_OF_ASC_NODE",
                     "ARG_OF_PERICENTER", "MEAN_ANOMALY", "EPHEMERIS_TYPE", "CLASSIFICATION_TYPE", "NORAD_CAT_ID",
                     "ELEMENT_SET_NO", "REV_AT_EPOCH", "BSTAR", "MEAN_MOTION_DOT", "MEAN_MOTION_DDOT"]) + "\r\n" + \
        ",".join(["TEST OBJECT", "2000-000A", "2026-11-20T00:00:00.000000", "15.5", "0.001", "51.6", "10", "20", "30",
                  "0", "U", "99999", "999", "1000", "0.0001", "0.00001", "0"]) + "\r\n"
    bf = os.path.join(work, "b3-body.csv")
    open(bf, "wb").write(body.encode("ascii"))
    fet = load("ifetch", os.path.join(HERE, "i_fetch.py"))
    out = {}
    for name, resp in (("delay5", {"status": 200, "body_file": bf, "delay": 5}),
                       ("none", {"status": 200, "body_file": bf}),
                       ("after5", {"status": 200, "body_file": bf, "delay_after_first": 5})):
        d = os.path.join(work, "b3-%s" % name)
        os.makedirs(d)
        sc = os.path.join(d, "scenario.json")
        json.dump({"responses": [resp] * 4}, open(sc, "w", encoding="utf-8"))
        pf = os.path.join(d, "port")
        p = subprocess.Popen([sys.executable, "-I", "-B", srv, sc, os.path.join(d, "server-requests.log"), pf])
        try:
            for _ in range(100):
                if os.path.exists(pf) and open(pf).read().strip():
                    break
                time.sleep(0.1)
            port = int(open(pf).read())
            sh0 = time.time() - 4 * 3 * 3600.0
            code, st = fet.run_slot(os.path.join(d, "fetch"), 1, sh0, d, base="http://127.0.0.1:%d/gp.php" % port,
                                    sleep=lambda s: None)
        finally:
            p.kill()   # by its PID: started here
            p.wait()
        rows = [ln.rstrip("\n").split("\t") for ln in open(os.path.join(d, "fetch", "requests.tsv"), encoding="utf-8")
                if not ln.startswith("#")]
        tf = [float(r[-2]) for r in rows]
        tl = [float(r[-1]) for r in rows]
        log.w("B3 %s: slot code %d (%s); %d requests; first byte %s s; last byte %s s" % (name, code, st, len(rows), tf, tl))
        out[name] = (code, tf, tl)
    return out


def main():
    work, logdir = sys.argv[1], sys.argv[2]
    os.makedirs(work, exist_ok=True)
    log = i_lib.Log(logdir, "partb", os.path.abspath(__file__), [CRIT], keep_dir=os.path.join(os.path.dirname(logdir), "scripts"),
                    modules=[os.path.join(HERE, n) for n in ("i_lib.py", "i_service.py", "i_fetch.py", "i3_server.py")])
    for n in ("h_service.py", "h_fetch.py", "h3_server.py"):
        log.w("DEBRIS-H's %s (unchanged, read only): SHA-256 %s" % (n, i_lib.sha256_file(os.path.join(HERE, n))))
    lines, started = b2(work, "i_service.py", "new")
    for ln in lines:
        log.w("  B2 new: " + ln)
    sk1 = [ln for ln in lines if ln.startswith("SLOT 1 skipped under the stop file")]
    sk2 = [ln for ln in lines if ln.startswith("SLOT 2 skipped under the stop file")]
    missed = [ln for ln in lines if "missed while the service was down" in ln]
    log.check(len(sk1) == 1 and len(sk2) == 1, "B2 slots 1 and 2 each logged once as skipped under the stop file")
    log.check(not any(("1" in ln.split(":")[1].replace(" ", "").strip("[]").split(",")) or
                      ("2" in ln.split(":")[1].replace(" ", "").strip("[]").split(",")) for ln in missed),
              "B2 no 'missed while the service was down' line names slot 1 or 2")
    log.check(3 in started, "B2 slot 3's fetch starts after the rename (fetches started: %s)" % started)
    log.check(missed == ["SLOTS missed while the service was down: [4]"], "B2 slot 4, due while the service was down, keeps "
              "the old line (missed lines: %s)" % missed)
    lines0, started0 = b2(work, "h_service.py", "old")
    for ln in lines0:
        log.w("  B2 control (h_service.py): " + ln)
    log.check(any(ln == "SLOTS missed while the service was down: [1, 2]" for ln in lines0) and
              not any("skipped" in ln for ln in lines0),
              "B2 control: the unchanged h_service.py logs the old text for the slots under the stop, and no skipped line")
    r = b3(work, log)
    log.check(r["delay5"][0] == 0 and min(r["delay5"][1]) >= 5.0, "B3 a 5 s delay before the response: every time to the "
              "first byte at least 5 s")
    log.check(r["none"][0] == 0 and max(r["none"][1]) < 1.0, "B3 no delay: every time to the first byte under 1 s")
    log.check(r["after5"][0] == 0 and max(r["after5"][1]) < 1.0 and min(r["after5"][2]) > 5.0,
              "B3 control: the delay after the first byte: the first byte under 1 s, the last byte past 5 s")
    sys.exit(1 if log.close() else 0)


if __name__ == "__main__":
    main()
