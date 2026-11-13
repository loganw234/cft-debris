#!/usr/bin/env python3
"""DEBRIS-B, Q3 sweep: run an unchanged copy of DEBRIS-A's port_roundtrip.py
against the preserved port binary in the ledger.

  python -I -B run_port_copy.py <dir holding the five copied .py files> <port_roundtrip.py args...>

What this wrapper does, and nothing else:
- checks that the five .py files in <dir> are byte-identical to DEBRIS-A's
  (their SHA-256 against studies/SHA256SUMS), so the copies are unchanged;
- checks the port binary's SHA-256 against the value the plan states;
- imports port_roundtrip from <dir> and sets its module global EXE to the
  preserved copy (DEBRIS-A's file names the cft-rebound-seam build);
- wraps subprocess.run so that each child's CPU time is read from Windows
  (GetProcessTimes) after it exits; port_roundtrip.py itself is not edited;
- prints the CPU time of every child and of this Python process at the end.
"""
import ctypes
import ctypes.wintypes as W
import hashlib
import os
import subprocess
import sys
import time

EXE = r"C:\Users\logan\source\repos\cft-debris-ledger\tools\ias15_cft.exe"
EXE_SHA = "9d5cb048ee63e609bad448237476443c651623a96d7fe5f0340fd8cd5d8aa048"
SUMS = r"C:\Users\logan\source\repos\cft-debris\studies\SHA256SUMS"
FIVE = ["check_ref.py", "leo_roundtrip.py", "meo_geo.py", "port_roundtrip.py", "var_check.py"]


def sha(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


K32 = ctypes.WinDLL("kernel32", use_last_error=True)


class FILETIME(ctypes.Structure):
    _fields_ = [("lo", W.DWORD), ("hi", W.DWORD)]


def proc_cpu(handle):
    c, e, k, u = FILETIME(), FILETIME(), FILETIME(), FILETIME()
    ok = K32.GetProcessTimes(W.HANDLE(int(handle)), ctypes.byref(c), ctypes.byref(e),
                             ctypes.byref(k), ctypes.byref(u))
    if not ok:
        raise OSError(ctypes.get_last_error(), "GetProcessTimes failed")
    f = lambda t: ((t.hi << 32) | t.lo) * 1e-7  # noqa: E731
    return f(u), f(k)


CHILD = []


def run_counted(cmd, **kw):
    """subprocess.run(cmd, stdout=PIPE, stderr=PIPE, text=True, env=env), as
    port_roundtrip.run calls it, plus the child's CPU time."""
    with subprocess.Popen(cmd, **kw) as p:
        out, err = p.communicate()
        u, s = proc_cpu(p._handle)
        rc = p.returncode
    CHILD.append((" ".join(cmd[1:9]), u, s))
    print("# child cpu: user %.2f s + sys %.2f s | %s" % (u, s, " ".join(cmd[1:9])), flush=True)
    return subprocess.CompletedProcess(cmd, rc, out, err)


def main():
    d = os.path.abspath(sys.argv[1])
    sums = {}
    for line in open(SUMS):
        h, _, name = line.strip().partition(" *")
        sums[name] = h
    for f in FIVE:
        got = sha(os.path.join(d, f))
        assert got == sums["debris-a/" + f], (f, got)
    h = sha(EXE)
    assert h == EXE_SHA, h
    print("# DEBRIS-B wrapper: the five .py copies in %s match SHA256SUMS; EXE overridden to %s (sha256 %s)"
          % (d, EXE, h), flush=True)
    sys.path.insert(0, d)
    import port_roundtrip as P
    assert os.path.dirname(os.path.abspath(P.__file__)) == d, P.__file__
    P.EXE = EXE
    subprocess.run = run_counted
    sys.argv = [os.path.join(d, "port_roundtrip.py")] + sys.argv[2:]
    t0 = time.perf_counter()
    rc = P.main()
    wall = time.perf_counter() - t0
    cu = sum(c[1] for c in CHILD)
    cs = sum(c[2] for c in CHILD)
    own = time.process_time()
    print("# CPU: children user %.2f s + sys %.2f s; this Python process %.2f s; total %.2f s; wall %.1f s"
          % (cu, cs, own, cu + cs + own, wall), flush=True)
    return rc


if __name__ == "__main__":
    sys.exit(main())
