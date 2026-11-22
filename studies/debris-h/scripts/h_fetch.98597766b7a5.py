# h_fetch.py - cft-debris M1 (DEBRIS-H), H-d: the fetcher of CelesTrak's updates, one slot a run. Standard library only.
# cft-debris, MIT licence (see LICENSE at the repository root). Written by DEBRIS-H, 2026-11-18, from the rules of the
# lead's dispatch\fetch_f.py and fetch_h.py (cft-debris's own, MIT) and CelesTrak's usage policy as the lead read it
# on 2026-11-18 (ledger lead.md, 06:16).
#
#   python3 -I -B h_fetch.py slot <fetch dir> <j> --sh0-unix U --sh0-dir D [--test-base http://127.0.0.1:PORT/PATH]
#                            [--stop-on-first-noresponse]
#
# THE RULES, fixed here:
# - Slot j (1 to 24) is due at S_H0's request time U + 3 j hours; no request is made in a slot whose time has not
#   come, in a slot already attempted, or after the stop file <fetch dir>/STOP exists.
# - A slot makes one request for each of the four groups' CSV, in the order stations, fengyun-1c-debris,
#   iridium-33-debris, cosmos-2251-debris, each starting 10 s after the previous one started. The URLs are fixed:
#   https://celestrak.org/NORAD/elements/gp.php?GROUP=<group>&FORMAT=csv (live mode: any other host is refused);
#   test mode takes a base URL on 127.0.0.1 (any other host is refused) and keeps the query.
# - Each request asks for compressed transfer (Accept-Encoding: gzip), sends the fixed User-Agent below (a generic
#   client name, no personal details), follows no redirect and is never retried. A body may come uncompressed or
#   gzip-compressed; any other Content-Encoding fails the body's check.
# - Each body is checked before it is kept: UTF-8 CSV whose header is CelesTrak's 17 columns in order, with at least
#   one row, every row of 17 fields. Rows of another ephemeris type are kept and counted. A body with fewer than half
#   the rows of that group's previous body (S_H0's for slot 1) is kept and logged as a finding; so is a body equal
#   to the previous one.
# - At the first response that is not HTTP 200, or a body that fails its check, the fetcher writes STOP and makes no
#   further request, in this slot or any later one (the policy: stop at once and report to a person).
# - A request with no response (none within 60 s, or a DNS or connection error) ends its slot, with nothing retried;
#   the next slot tries again. A second such slot in a row writes STOP; with --stop-on-first-noresponse (decision
#   7(b)) the first does.
# - Each body is stored decompressed under a name of its own (slotJJ/gp-<group>.csv; a rejected one as
#   slotJJ/rejected-gp-<group>.body), never overwriting, with both sizes, its SHA-256 and the response's Date and
#   Last-Modified headers in the append-only request log requests.tsv; each slot's outcome goes to slots.tsv.
import argparse
import csv
import gzip
import hashlib
import http.client
import io
import os
import socket
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

UA = "cft-debris-research-client/1.1 (low-volume: four CSV files every 3 hours)"
LIVE = "https://celestrak.org/NORAD/elements/gp.php"
GROUPS = ["stations", "fengyun-1c-debris", "iridium-33-debris", "cosmos-2251-debris"]
COLUMNS = ["OBJECT_NAME", "OBJECT_ID", "EPOCH", "MEAN_MOTION", "ECCENTRICITY", "INCLINATION", "RA_OF_ASC_NODE",
           "ARG_OF_PERICENTER", "MEAN_ANOMALY", "EPHEMERIS_TYPE", "CLASSIFICATION_TYPE", "NORAD_CAT_ID", "ELEMENT_SET_NO",
           "REV_AT_EPOCH", "BSTAR", "MEAN_MOTION_DOT", "MEAN_MOTION_DDOT"]
SLOT_S = 3 * 3600.0
SPACING_S = 10.0
TIMEOUT_S = 60.0
NSLOTS = 24


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None  # a 3xx then surfaces as an HTTPError, which stops the fetcher


OPENER = urllib.request.build_opener(NoRedirect)


def url_ok(url, live):
    u = urllib.parse.urlsplit(url)
    if live:
        return u.scheme == "https" and u.hostname == "celestrak.org" and u.port is None and not u.username and not u.password
    return u.scheme == "http" and u.hostname == "127.0.0.1" and not u.username and not u.password


def urls(base, live):
    b = LIVE if live else base
    return [(g, "%s?GROUP=%s&FORMAT=csv" % (b, g)) for g in GROUPS]


def check_body(body):
    """(ok, reason, rows, rows of another ephemeris type)"""
    try:
        txt = body.decode("utf-8")
    except UnicodeDecodeError:
        return False, "not UTF-8", 0, 0
    try:
        rd = csv.reader(io.StringIO(txt, newline=""))
        head = next(rd, None)
        if head != COLUMNS:
            return False, "the header is not the 17 columns", 0, 0
        n = other = 0
        for r in rd:
            if not r:
                continue
            if len(r) != 17:
                return False, "a row of %d fields" % len(r), n, other
            n += 1
            if r[9] != "0":
                other += 1
    except csv.Error as e:
        return False, "csv: %s" % e, 0, 0
    if n < 1:
        return False, "no rows", 0, 0
    return True, "", n, other


def append(path, line):
    with open(path, "ab") as f:
        f.write((line + "\n").encode("utf-8"))
        f.flush()
        os.fsync(f.fileno())


def write_new(path, data):
    with open(path, "xb") as f:
        f.write(data)
        f.flush()
        os.fsync(f.fileno())


def read_slots(d):
    p = os.path.join(d, "slots.tsv")
    out = []
    if os.path.exists(p):
        for ln in open(p, encoding="utf-8"):
            q = ln.rstrip("\n").split("\t")
            if q and q[0].isdigit():
                out.append(q)
    return out


def previous_body(d, g, sh0_dir):
    """the group's latest body kept before this slot, else S_H0's"""
    p = os.path.join(d, "requests.tsv")
    last = None
    if os.path.exists(p):
        for ln in open(p, encoding="utf-8"):
            q = ln.rstrip("\n").split("\t")
            if len(q) > 10 and q[1] == g and q[4] == "200" and q[13] == "kept":
                last = os.path.join(d, q[9])
    if last is None:
        for c in (os.path.join(sh0_dir, "gp-%s-SH0.csv" % g), os.path.join(sh0_dir, "gp-%s-SH0" % g, "gp-%s-SH0.csv" % g)):
            if os.path.exists(c):
                last = c
                break
    if last is None:
        return None, None
    b = open(last, "rb").read()
    return check_body(b)[2], hashlib.sha256(b).hexdigest()


def stop(d, why):
    p = os.path.join(d, "STOP")
    if not os.path.exists(p):
        write_new(p, ("STOP at %s: %s\n" % (time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), why)).encode("utf-8"))


def run_slot(d, j, sh0_unix, sh0_dir, base=None, first_noresp_stops=False, opener=None, now=time.time, sleep=time.sleep):
    """one slot; returns (exit code, status). Exit codes: 0 done, 2 stopped now, 3 refused (no request), 4 ended by no response"""
    live = base is None
    opener = opener or OPENER
    os.makedirs(d, exist_ok=True)
    rq = os.path.join(d, "requests.tsv")
    if not os.path.exists(rq):
        append(rq, "# slot\tgroup\turl\tt_request\toutcome\twire_bytes\tbody_bytes\tsha256\tcontent_encoding\tfile\tdate\tlast_modified\trows\tkept\trows_other_type\tfindings")
    sl = os.path.join(d, "slots.tsv")
    if not os.path.exists(sl):
        append(sl, "# slot\tstatus\tbodies\tnote\tt_start\tt_end")
    t0 = now()

    def refuse(why):
        print("refused (no request made): %s" % why)
        return 3, "refused: " + why
    if os.path.exists(os.path.join(d, "STOP")):
        return refuse("the stop file exists")
    if not 1 <= j <= NSLOTS:
        return refuse("slot %d is outside 1..%d" % (j, NSLOTS))
    done = read_slots(d)
    if any(int(q[0]) == j for q in done):
        return refuse("slot %d was attempted already" % j)
    if done and j < max(int(q[0]) for q in done):
        return refuse("slot %d is earlier than a slot attempted already" % j)
    due = sh0_unix + j * SLOT_S
    if t0 < due:
        return refuse("slot %d is due at %.3f, %.0f s from now" % (j, due, due - t0))
    plan = urls(base, live)
    for g, u in plan:
        if not url_ok(u, live):
            return refuse("%s mode refuses %s" % ("live" if live else "test", u))
    prev_noresp = bool(done) and done[-1][1] == "noresponse"
    sdir = os.path.join(d, "slot%02d" % j)
    os.makedirs(sdir, exist_ok=True)
    bodies, status, note = 0, "ok", ""
    for i, (g, u) in enumerate(plan):
        if i:
            wait = t_req + SPACING_S - now()
            if wait > 0:
                sleep(wait)
        t_req = now()
        req = urllib.request.Request(u, headers={"User-Agent": UA, "Accept-Encoding": "gzip"})
        try:
            with opener.open(req, timeout=TIMEOUT_S) as r:
                code, hdr, raw = r.status, r.headers, r.read()
        except urllib.error.HTTPError as e:
            append(rq, "%d\t%s\t%s\t%.3f\t%d\t\t\t\t\t\t%s\t\t\t\t\tthe response is not 200 (%s; Location %s; Retry-After %s)" % (
                j, g, u, t_req, e.code, e.headers.get("Date", "") if e.headers else "", e.reason, e.headers.get("Location", "") if e.headers else "",
                e.headers.get("Retry-After", "") if e.headers else ""))
            stop(d, "slot %d %s: HTTP %d %s" % (j, g, e.code, e.reason))
            append(sl, "%d\tstopped\t%d\tHTTP %d for %s\t%.3f\t%.3f" % (j, bodies, e.code, g, t0, now()))
            print("STOP: HTTP %d for %s" % (e.code, g))
            return 2, "stopped: HTTP %d" % e.code
        except (urllib.error.URLError, socket.timeout, TimeoutError, ConnectionError, OSError, http.client.HTTPException) as e:
            why = "%s: %s" % (type(e).__name__, getattr(e, "reason", e))
            append(rq, "%d\t%s\t%s\t%.3f\tnoresponse\t\t\t\t\t\t\t\t\t\t\t%s" % (j, g, u, t_req, why.replace("\t", " ")))
            again = prev_noresp or first_noresp_stops
            if again:
                stop(d, "slot %d %s: no response (%s)%s" % (j, g, why, ", the second slot in a row" if prev_noresp else ", and decision 7(b)"))
            append(sl, "%d\tnoresponse\t%d\tno response for %s: %s%s\t%.3f\t%.3f" % (j, bodies, g, why.replace("\t", " "), "; STOP written" if again else "", t0, now()))
            print("slot ended: no response for %s (%s)%s" % (g, why, "; STOP" if again else ""))
            return (2 if again else 4), "noresponse"
        if code != 200:
            append(rq, "%d\t%s\t%s\t%.3f\t%d\t\t\t\t\t\t%s\t\t\t\t\tthe response is not 200" % (j, g, u, t_req, code, hdr.get("Date", "")))
            stop(d, "slot %d %s: HTTP %d" % (j, g, code))
            append(sl, "%d\tstopped\t%d\tHTTP %d for %s\t%.3f\t%.3f" % (j, bodies, code, g, t0, now()))
            return 2, "stopped: HTTP %d" % code
        enc = (hdr.get("Content-Encoding") or "").strip().lower()
        wire = len(raw)
        reason = ""
        body = raw
        if enc == "gzip":
            try:
                body = gzip.decompress(raw)
            except (OSError, EOFError) as e:
                reason = "gzip: %s" % e
        elif enc not in ("", "identity"):
            reason = "Content-Encoding %s" % enc
        ok, why, nrows, nother = (False, reason, 0, 0) if reason else check_body(body)
        sha = hashlib.sha256(body).hexdigest()
        if not ok:
            fn = "slot%02d/rejected-gp-%s.body" % (j, g)
            write_new(os.path.join(d, fn), body)
            append(rq, "%d\t%s\t%s\t%.3f\t200\t%d\t%d\t%s\t%s\t%s\t%s\t%s\t%d\trejected\t%d\tthe body fails its check: %s" % (
                j, g, u, t_req, wire, len(body), sha, enc or "none", fn, hdr.get("Date", ""), hdr.get("Last-Modified", ""), nrows, nother, why))
            stop(d, "slot %d %s: the body fails its check (%s)" % (j, g, why))
            append(sl, "%d\tstopped\t%d\tthe body for %s fails its check: %s\t%.3f\t%.3f" % (j, bodies, g, why, t0, now()))
            print("STOP: the body for %s fails its check: %s" % (g, why))
            return 2, "stopped: body"
        prows, psha = previous_body(d, g, sh0_dir)
        find = []
        if nother:
            find.append("FINDING %d rows of another ephemeris type (kept, never checked)" % nother)
        if prows is not None and nrows < 0.5 * prows:
            find.append("FINDING %d rows, under half the previous body's %d" % (nrows, prows))
        if psha is not None and psha == sha:
            find.append("FINDING equal to the previous body")
        fn = "slot%02d/gp-%s.csv" % (j, g)
        write_new(os.path.join(d, fn), body)
        bodies += 1
        append(rq, "%d\t%s\t%s\t%.3f\t200\t%d\t%d\t%s\t%s\t%s\t%s\t%s\t%d\tkept\t%d\t%s" % (
            j, g, u, t_req, wire, len(body), sha, enc or "none", fn, hdr.get("Date", ""), hdr.get("Last-Modified", ""), nrows, nother, "; ".join(find)))
        print("kept %s: %d rows, %d bytes (%d on the wire, %s), sha256 %s %s" % (g, nrows, len(body), wire, enc or "none", sha, "; ".join(find)))
    append(sl, "%d\tok\t%d\t%s\t%.3f\t%.3f" % (j, bodies, note, t0, now()))
    return 0, status


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["slot"])
    ap.add_argument("dir")
    ap.add_argument("slot", type=int)
    ap.add_argument("--sh0-unix", type=float, required=True)
    ap.add_argument("--sh0-dir", required=True)
    ap.add_argument("--test-base")
    ap.add_argument("--stop-on-first-noresponse", action="store_true")
    a = ap.parse_args()
    print("h_fetch.py sha256 %s; slot %d; %s" % (hashlib.sha256(open(os.path.abspath(__file__), "rb").read()).hexdigest(), a.slot,
                                              "test mode, base %s" % a.test_base if a.test_base else "live mode"))
    code, st = run_slot(a.dir, a.slot, a.sh0_unix, a.sh0_dir, base=a.test_base, first_noresp_stops=a.stop_on_first_noresponse)
    print("slot %d: %s (exit %d)" % (a.slot, st, code))
    return code


if __name__ == "__main__":
    sys.exit(main())
