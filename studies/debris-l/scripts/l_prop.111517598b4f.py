# l_prop.py - cft-debris (DEBRIS-L): the frames' states. M1's `m1f prop` (native64, DEBRIS-H's frame table) propagates every
# object of DEBRIS-H's seed from T_s to T_s + DELTA k, k = 0 .. 180, through DEBRIS-K's k_pilot.m1f_prop.
# cft-debris, MIT licence (see LICENSE at the repository root). Written by DEBRIS-L, 2026-11-23.
#
#   python -I -B l_prop.py --ledger DIR --scratch DIR --m1f EXE --downloads DIR --logs DIR --keep DIR --cpu TSV [--delta 60]
# Outputs, in the scratch: work/states.npy (float64, [frame, object, x y z vx vy vz] in M1's units, metres and m/s),
# work/groups.npy (int, index into l_lib.GROUPS), work/prop_all_prop.txt (prop's own output, about 150 MB, stays there).
import argparse
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import k_lib as K  # noqa: E402
import k_pilot as KP  # noqa: E402
import l_lib as L  # noqa: E402

SCRIPT = os.path.abspath(__file__)
SEED_SHA = "a67c3b09293a0a1c5a2a16a72c23744d472be31372503ae345f50f633af840b0"
META_SHA = "c229529c76f557074a667182ea67b7fa26199b83e4d5f59f937a4a15b9ca9f3e"
FRAME_SHA = "dd69fe0bc21e903bb3af9f4ee6711a0487cc96d040629bf26e3a3b62a635c82f"
CRITERIA = """
P1 the seed, its meta file and the frame table have the SHA-256 the dispatch note gives;
P2 the seed holds 2,688 objects with one T_s, equal to 2,933,400 s (2026-11-18 22:50:00 TDB), and the groups count 1,991, 582, 109 and 6;
P3 prop's output holds 2,688 x (frames) P lines, every value finite;
P4 (V2a) prop's state at its first target (k = 0, T = T_s) equals the seed's state for every object, bit for bit, and every
   frame time equals T_s + DELTA k exactly (binary64 equality);
P5 the run's log names m1f's SHA-256 and the frame table's.
"""


def main():
    ap = argparse.ArgumentParser()
    for o in ("--ledger", "--scratch", "--m1f", "--downloads", "--logs", "--keep", "--cpu"):
        ap.add_argument(o, required=True)
    ap.add_argument("--delta", type=float, default=L.DELTA_S)
    ap.add_argument("--frames", type=int, default=L.NFRAMES)
    ap.add_argument("--ffmpeg", default="")
    a = ap.parse_args()
    L.set_roots(scratch=a.scratch, ledger=a.ledger, repo=L.HERE_REPO, downloads=a.downloads, msys="C:/msys64")
    cpu = K.CpuAccount("l_prop", a.cpu)
    W = os.path.join(a.scratch, "work")
    os.makedirs(W, exist_ok=True)
    log = L.Log("l_prop", a.logs, SCRIPT, CRITERIA, a.keep, modules=[os.path.join(L.TESTS, "k_pilot.py"), os.path.join(L.TESTS, "l_lib.py"), os.path.join(L.TESTS, "m1f.c")])
    ho = os.path.join(a.ledger, "debris-h")
    seedp = os.path.join(ho, "box", "r2", "seed", "seed1.txt")
    metap = os.path.join(ho, "box", "r2", "seed", "seed_meta.tsv")
    table = os.path.join(ho, "frame_h0.bin")
    ok = True
    for nm, p, h in (("seed1.txt", seedp, SEED_SHA), ("seed_meta.tsv", metap, META_SHA), ("frame_h0.bin", table, FRAME_SHA)):
        got = L.sha256(p)
        ok &= log.check(got == h, "P1 %s sha256 %s" % (nm, got))
    if not ok:
        return log.close()
    log.w("# m1f exe sha256 %s; frame table sha256 %s" % (L.sha256(a.m1f), FRAME_SHA))  # P5
    sd = K.read_seed(seedp)
    grp = L.read_group_table(metap)
    n = len(sd["rows"])
    gi = np.array([L.GROUPS.index(grp[i]) for i in range(n)], dtype=np.int64)
    counts = [int((gi == k).sum()) for k in range(len(L.GROUPS))]
    log.check(n == 2688 and sd["ts"] == L.TS_EXPECT and counts == [1991, 582, 109, 6],
              "P2 %d objects, T_s %.1f s, group counts %s" % (n, sd["ts"], counts))
    ts = sd["ts"]
    targets = [ts + a.delta * k for k in range(a.frames)]
    objs = [(str(i), ts, sd["rows"][i][3], sd["rows"][i][4], sd["rows"][i][5], targets) for i in range(n)]
    ns = type("A", (), {})()
    ns.m1f, ns.table, ns.downloads = a.m1f, table, a.downloads
    out, pout = KP.m1f_prop(ns, log, W, "all", objs)
    log.w("# prop output %s: %d bytes, sha256 %s" % (os.path.basename(pout), os.path.getsize(pout), K.sha256(pout)))
    st = np.zeros((a.frames, n, 6), dtype=np.float64)
    tt = np.zeros((a.frames, n), dtype=np.float64)
    for i in range(n):
        for k, (T, s6, _) in enumerate(out[str(i)]):
            st[k, i] = s6
            tt[k, i] = T
    log.check(bool(np.isfinite(st).all()) and st.shape == (a.frames, n, 6), "P3 %d x %d states, all finite" % (a.frames, n))
    t_ok = all(float(tt[k, i]) == ts + a.delta * k for k in range(a.frames) for i in range(n))
    log.check(t_ok, "P4 every frame time equals T_s + %g k exactly" % a.delta)
    seedst = np.array([sd["rows"][i][3] for i in range(n)], dtype=np.float64)
    same = (st[0].view(np.uint64) == seedst.view(np.uint64)).all(axis=1)
    log.check(bool(same.all()), "P4 k = 0: %d of %d objects' states equal the seed's bit for bit" % (int(same.sum()), n))
    np.save(os.path.join(W, "states.npy"), st)
    np.save(os.path.join(W, "groups.npy"), gi)
    log.w("# states.npy sha256 %s (in the scratch)" % K.sha256(os.path.join(W, "states.npy")))
    c = cpu.close("l_prop log %03d" % log.n)
    log.w("# CPU: %.2f s by cycles / 2.5e9 (this script and every process it started)" % c)
    return log.close()


if __name__ == "__main__":
    sys.exit(main())
