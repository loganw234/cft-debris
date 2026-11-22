# h3_server.py - cft-debris M1 (DEBRIS-H), gate H3's local HTTP server: planted responses on 127.0.0.1, for the
# fetcher's tests. Standard library only. It never serves another address.
# cft-debris, MIT licence (see LICENSE at the repository root). Written by DEBRIS-H, 2026-11-18.
#
#   python -I -B h3_server.py <scenario.json> <request log (JSON lines)> <port file>
# The scenario: {"responses": [{"status": 200, "body_file": PATH, "gzip": true|false, "headers": {...}, "delay": s}, ...]};
# request i (counted from 0, every path) gets responses[i]; past the list, 500. Each request is logged with its time,
# path, User-Agent and Accept-Encoding before any delay. The port (chosen by the system) is written to the port file.
import gzip
import json
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

SCEN = json.load(open(sys.argv[1], encoding="utf-8"))["responses"]
LOG = sys.argv[2]
LOCK = threading.Lock()
COUNT = [0]


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *args):
        pass

    def do_GET(self):
        with LOCK:
            i = COUNT[0]
            COUNT[0] += 1
            with open(LOG, "a", encoding="utf-8") as f:
                f.write(json.dumps({"i": i, "t": time.time(), "path": self.path, "ua": self.headers.get("User-Agent"),
                                    "ae": self.headers.get("Accept-Encoding")}) + "\n")
        r = SCEN[i] if i < len(SCEN) else {"status": 500, "text": "no more planned responses"}
        if r.get("delay"):
            time.sleep(r["delay"])
        body = open(r["body_file"], "rb").read() if r.get("body_file") else r.get("text", "").encode("utf-8")
        hdr = dict(r.get("headers", {}))
        if r.get("gzip"):
            body = gzip.compress(body)
            hdr["Content-Encoding"] = "gzip"
        try:
            self.send_response(r["status"])
            for k, v in hdr.items():
                self.send_header(k, v)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Last-Modified", "Mon, 16 Nov 2026 12:00:00 GMT")
            self.end_headers()
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            pass


srv = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
with open(sys.argv[3], "w", encoding="ascii") as f:
    f.write(str(srv.server_address[1]))
srv.serve_forever()
