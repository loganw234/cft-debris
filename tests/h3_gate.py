# h3_gate.py - cft-debris M1 (DEBRIS-H), gate H3: the fetcher, against a local server on 127.0.0.1 only. The desktop's.
# cft-debris, MIT licence (see LICENSE at the repository root). Written by DEBRIS-H, 2026-11-18.
#
#   python -I -B tests/h3_gate.py <root> [--logs DIR] [--keep DIR] [--cpu TSV]
# <root>/in/gp holds DEBRIS-F's S0 and S1 (their bodies are the planted CSV). Each scenario starts tests/h3_server.py on
# 127.0.0.1 (a port the system chooses) and stops it by its PID; nothing outside this machine is ever requested.
import argparse
import gzip
import hashlib
import json
import os
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import h_lib as H  # noqa: E402
import h_fetch as F  # noqa: E402

SCRIPT = os.path.abspath(__file__)

CRITERIA = """
H3, the fetcher (tests/h_fetch.py) against tests/h3_server.py on 127.0.0.1, each scenario with a new fetch folder:
A  two slots of planted 200s, two of the four bodies gzip-compressed and two not in each: one request per file per
   slot, in the groups' order, each at least 10 s after the previous one started (9.9 s allowed for the server's
   clock); every request sends Accept-Encoding: gzip and the fixed User-Agent; every body is stored decompressed, its
   SHA-256 equal to the planted CSV's, with both sizes in the request log (the wire size smaller for a gzip body); a
   second run of slot 1 is refused with no request, and the stored files are unchanged (no file overwritten). In slot
   2, a CSV with a tenth of the previous body's rows is kept and logged as a finding and does not stop the fetcher,
   and a body equal to the previous one is logged as a finding.
CONTROLS, each from a planted response, each must fail as specified (asserted):
 C6  a 301 for the second request stops the fetcher: STOP written, the slot recorded as stopped, and the server's log
     shows no request after it;
 C7  a 503 does the same;
 C8  a 200 whose body is an HTML page does the same, and the rejected body is archived with its SHA-256;
 C9  a response delayed past the 60 s timeout ends its slot only (no STOP); a second such slot in a row writes STOP;
 C10 a slot after a stop makes no request (C6, C7, C8 and C9 each try one);
 C11 test mode refuses a base URL on any host but 127.0.0.1, and live mode refuses any host but celestrak.org, both
     without a request (the CLI's exit and an in-process run whose opener records every call); and live mode makes no
     request in a slot whose time has not come.
"""


def server(work, name, responses):
    sc = os.path.join(work, "%s_scenario.json" % name)
    lg = os.path.join(work, "%s_requests.jsonl" % name)
    pf = os.path.join(work, "%s_port.txt" % name)
    with open(sc, "w", encoding="utf-8", newline="\n") as f:
        json.dump({"responses": responses}, f)
    p = H.popen([sys.executable, "-I", "-B", os.path.join(HERE, "h3_server.py"), sc, lg, pf])
    for _ in range(100):
        if os.path.exists(pf) and open(pf).read().strip():
            break
        time.sleep(0.1)
    port = int(open(pf).read())
    return p, "http://127.0.0.1:%d/NORAD/elements/gp.php" % port, lg


def reqs(lg):
    return [json.loads(ln) for ln in open(lg, encoding="utf-8")] if os.path.exists(lg) else []


def fetch(d, j, base, sh0, sh0_unix):
    argv = [sys.executable, "-I", "-B", os.path.join(HERE, "h_fetch.py"), "slot", d, str(j), "--sh0-unix", "%.3f" % sh0_unix, "--sh0-dir", sh0]
    if base is not None:
        argv += ["--test-base", base]
    p = subprocess.run(argv, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    return p.returncode, p.stdout.decode("utf-8", "replace")


def tsv(path):
    out = []
    if os.path.exists(path):
        for ln in open(path, encoding="utf-8"):
            if not ln.startswith("#") and ln.strip():
                out.append(ln.rstrip("\n").split("\t"))
    return out


def main():
    global HERE
    ap = argparse.ArgumentParser()
    ap.add_argument("root")
    ap.add_argument("--logs", default="logs")
    ap.add_argument("--keep")
    ap.add_argument("--cpu")
    a = ap.parse_args()
    os.chdir(a.root)
    HERE = os.path.relpath(os.path.dirname(SCRIPT))
    cpu = H.CpuAccount("h3_gate", a.cpu)
    log = H.Log("h3_gate", a.logs, SCRIPT, CRITERIA, extra=[os.path.join(HERE, "h_fetch.py"), os.path.join(HERE, "h3_server.py")], keep_dir=a.keep)
    _, work = H.next_numbered("h3", "gate", "")
    os.makedirs(work)
    sh0 = os.path.join(work, "sh0")
    os.makedirs(sh0)
    src = {}
    for g in H.GROUPS:
        for tag in ("S0", "S1"):
            src[(g, tag)] = os.path.join("in/gp", "gp-%s-%s.csv" % (g, tag))
        with open(src[(g, "S0")], "rb") as fi, open(os.path.join(sh0, "gp-%s-SH0.csv" % g), "xb") as fo:
            fo.write(fi.read())
    # a tenth of the iridium group's rows, and an HTML page
    ir = open(src[("iridium-33-debris", "S1")], "rb").read().split(b"\n")
    tenth = os.path.join(work, "iridium_tenth.csv")
    nrow = sum(1 for x in ir[1:] if x.strip())
    with open(tenth, "xb") as f:
        f.write(b"\n".join(ir[:1 + nrow // 10]) + b"\n")
    html = os.path.join(work, "page.html")
    with open(html, "xb") as f:
        f.write(b"<!DOCTYPE html><html><head><title>Not the data</title></head><body><p>A page.</p></body></html>\n")
    now = time.time()
    due = now - 7 * 3 * 3600.0  # S_H0's request 21 h ago: slots 1 to 7 are due
    procs = []
    try:
        # ---- A
        d = os.path.join(work, "A")
        resp = [{"status": 200, "body_file": src[("stations", "S0")], "gzip": False}, {"status": 200, "body_file": src[("fengyun-1c-debris", "S0")], "gzip": True},
                {"status": 200, "body_file": src[("iridium-33-debris", "S0")], "gzip": False}, {"status": 200, "body_file": src[("cosmos-2251-debris", "S0")], "gzip": True},
                {"status": 200, "body_file": src[("stations", "S1")], "gzip": True}, {"status": 200, "body_file": src[("fengyun-1c-debris", "S0")], "gzip": False},
                {"status": 200, "body_file": tenth, "gzip": True}, {"status": 200, "body_file": src[("cosmos-2251-debris", "S1")], "gzip": False}]
        p, base, lg = server(work, "A", resp)
        procs.append(p)
        rc1, o1 = fetch(d, 1, base, sh0, due)
        rc2, o2 = fetch(d, 2, base, sh0, due)
        r = reqs(lg)
        log.w("# A: slot 1 exit %d, slot 2 exit %d; the server saw %d requests" % (rc1, rc2, len(r)))
        groups = [x["path"].split("GROUP=")[1].split("&")[0] for x in r]
        log.check(rc1 == 0 and rc2 == 0 and groups == H.GROUPS * 2, "A one request per file per slot, in the groups' order: %s" % groups)
        gaps = [r[i]["t"] - r[i - 1]["t"] for i in range(1, len(r)) if i != 4]
        log.check(len(gaps) == 6 and min(gaps) >= 9.9, "A within a slot each request at least 10 s after the previous (smallest gap %.2f s)" % (min(gaps) if gaps else -1))
        log.check(all(x["ae"] == "gzip" for x in r) and len(r) == 8, "A every request sent Accept-Encoding: gzip")
        log.check(all(x["ua"] == F.UA for x in r), "A every request sent the fixed User-Agent (%s)" % F.UA)
        rq = tsv(os.path.join(d, "requests.tsv"))
        planted = [resp[i]["body_file"] for i in range(8)]
        ok_sha = all(q[7] == H.sha256(pb) for q, pb in zip(rq, planted)) and len(rq) == 8
        ok_sizes = all(int(q[6]) == os.path.getsize(pb) for q, pb in zip(rq, planted)) and all(
            (int(q[5]) < int(q[6])) == bool(rs["gzip"]) for q, rs in zip(rq, resp))
        ok_files = all(H.sha256(os.path.join(d, q[9])) == q[7] for q in rq)
        log.check(ok_sha and ok_sizes and ok_files, "A each body stored decompressed, its SHA-256 equal to the planted CSV's, with both sizes (the wire size smaller for gzip)")
        log.check("under half" in rq[6][15] and rq[6][13] == "kept" and not os.path.exists(os.path.join(d, "STOP")),
                  "A slot 2's CSV with a tenth of the rows is kept, logged as a finding (%s), and the fetcher goes on" % rq[6][15])
        log.check("equal to the previous body" in rq[5][15], "A slot 2's body equal to the previous one is logged as a finding")
        before = {f: H.sha256(os.path.join(d, "slot01", f)) for f in os.listdir(os.path.join(d, "slot01"))}
        rc3, o3 = fetch(d, 1, base, sh0, due)
        after = {f: H.sha256(os.path.join(d, "slot01", f)) for f in os.listdir(os.path.join(d, "slot01"))}
        log.check(rc3 == 3 and len(reqs(lg)) == 8 and before == after, "A a second run of slot 1 is refused with no request, and no file is overwritten")
        p.kill()  # by PID: started here
        p.wait()
        # ---- C6, C7, C8: a 301, a 503, an HTML 200
        for cname, rs, nreq in (("C6", [{"status": 200, "body_file": src[("stations", "S0")]}, {"status": 301, "headers": {"Location": "https://example.invalid/"}}], 2),
                                ("C7", [{"status": 503, "text": "busy"}], 1),
                                ("C8", [{"status": 200, "body_file": html}], 1)):
            d = os.path.join(work, cname)
            p, base, lg = server(work, cname, rs)
            procs.append(p)
            rc, o = fetch(d, 1, base, sh0, due)
            time.sleep(0.5)
            n1 = len(reqs(lg))
            rc2, o2 = fetch(d, 2, base, sh0, due)
            n2 = len(reqs(lg))
            sl = tsv(os.path.join(d, "slots.tsv"))
            ok = rc == 2 and os.path.exists(os.path.join(d, "STOP")) and n1 == nreq and sl and sl[-1][1] == "stopped"
            extra = ""
            if cname == "C8":
                rq = tsv(os.path.join(d, "requests.tsv"))
                ok = ok and rq and rq[-1][13] == "rejected" and H.sha256(os.path.join(d, rq[-1][9])) == rq[-1][7] == H.sha256(html)
                extra = "; the rejected body archived with its SHA-256"
            log.check(ok, "%s the planted %s stops the fetcher: STOP written, the slot stopped, %d request(s) and none after it%s - failed as specified" % (
                cname, {"C6": "301", "C7": "503", "C8": "HTML 200"}[cname], n1, extra))
            log.check(rc2 == 3 and n2 == n1, "C10 (%s) the slot after the stop makes no request (exit %d)" % (cname, rc2))
            p.kill()
            p.wait()
        # ---- C9: delays past the timeout
        d = os.path.join(work, "C9")
        p, base, lg = server(work, "C9", [{"status": 200, "body_file": src[("stations", "S0")], "delay": 70}, {"status": 200, "body_file": src[("stations", "S0")], "delay": 70}])
        procs.append(p)
        t0 = time.time()
        rc1, o1 = fetch(d, 1, base, sh0, due)
        t1 = time.time()
        stop1 = os.path.exists(os.path.join(d, "STOP"))
        rc2, o2 = fetch(d, 2, base, sh0, due)
        t2 = time.time()
        stop2 = os.path.exists(os.path.join(d, "STOP"))
        sl = tsv(os.path.join(d, "slots.tsv"))
        log.w("# C9: slot 1 ended after %.1f s (exit %d), slot 2 after %.1f s (exit %d)" % (t1 - t0, rc1, t2 - t1, rc2))
        log.check(rc1 == 4 and not stop1 and len(reqs(lg)) >= 1 and sl[0][1] == "noresponse" and 55 <= t1 - t0 <= 75,
                  "C9 a response delayed past the 60 s timeout ends slot 1 only (no STOP)")
        log.check(rc2 == 2 and stop2 and sl[1][1] == "noresponse" and "STOP written" in sl[1][3],
                  "C9 a second such slot in a row writes STOP - as specified")
        n2 = len(reqs(lg))
        rc3, o3 = fetch(d, 3, base, sh0, due)
        log.check(rc3 == 3 and len(reqs(lg)) == n2 == 2, "C10 (C9) the slot after the stop makes no request")
        p.kill()
        p.wait()
        # ---- C11
        d = os.path.join(work, "C11")
        rc, o = fetch(d, 1, "http://example.com/NORAD/elements/gp.php", sh0, due)
        log.check(rc == 3 and "refuse" in o and not os.path.exists(os.path.join(d, "requests.tsv")) or rc == 3 and len(tsv(os.path.join(d, "requests.tsv"))) == 0,
                  "C11 test mode refuses a base URL off 127.0.0.1 without a request (exit %d)" % rc)

        class Rec:
            calls = []

            def open(self, req, timeout=None):
                Rec.calls.append(req.full_url)
                raise AssertionError("no request may be made")
        saved = F.LIVE
        try:
            for bad in ("https://example.org/NORAD/elements/gp.php", "http://celestrak.org/NORAD/elements/gp.php", "https://celestrak.org.example.org/x",
                        "http://127.0.0.1:1/NORAD/elements/gp.php"):
                F.LIVE = bad
                code, st = F.run_slot(os.path.join(work, "C11_live_%d" % len(Rec.calls)), 1, due, sh0, base=None, opener=Rec())
                log.check(code == 3 and not Rec.calls, "C11 live mode refuses %s without a request" % bad)
            F.LIVE = saved
            log.check(F.url_ok(F.LIVE + "?GROUP=stations&FORMAT=csv", True), "C11 live mode accepts its own fixed URL (%s)" % F.LIVE)
            code, st = F.run_slot(os.path.join(work, "C11_notdue"), 1, time.time(), sh0, base=None, opener=Rec())
            log.check(code == 3 and "due" in st and not Rec.calls, "C11 live mode makes no request in a slot whose time has not come")
        finally:
            F.LIVE = saved
    finally:
        for p in procs:
            if p.poll() is None:
                p.kill()  # by PID: every server was started here
                p.wait()
    log.w("# the scenarios' fetch folders and the server's request logs: %s (scratch)" % work.replace("\\", "/"))
    c_ = cpu.close("h3_gate log %03d" % log.n)
    if c_ is not None:
        log.w("# CPU: %.2f s by cycles / 2.5e9 (this script and every process it started)" % c_)
    return log.close()


if __name__ == "__main__":
    sys.exit(main())
