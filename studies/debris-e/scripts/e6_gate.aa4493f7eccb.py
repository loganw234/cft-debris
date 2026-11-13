# e6_gate.py - cft-debris M1, gate E6: Orekit 13.1.9, force by force, at 1,000
# sampled LEO states. cft-debris, MIT licence (see LICENSE at the repository
# root). Written by DEBRIS-E, 2026-11-13.
#
#   python -I -B tests/e6_gate.py
#
# Prerequisite: the de-duplicated coefficient file for Orekit, derived by
# tests/e6_gfc_copy.py into the scratch (Orekit refuses the download's
# duplicated (0, 0) line; lead.md 2026-11-12 18:07).
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gatelib as g  # noqa: E402

CRITERIA = """
The states (tests/m1run.c mode e6, seed 0xE6): 1,000 LEO states 300 to 800 km up, directions uniform, speed
   0.99 to 1.01 of circular perpendicular to r, epochs 0 to 20 days after 2008-07-03 00:00 TDB in whole seconds,
   area 0.5 to 20 m^2, mass 50 to 2000 kg, Cd 2.0 to 2.4, Cr 1.0 to 1.8. Ours at native64 and at cft64; Orekit
   on the same binary64 states. Matched inputs are listed by tests/e6_orekit.js's header, copied below.
TOLERANCES, each with its basis, each below the planted change it must catch:
D1 gravity (EIGEN-6C4 degrees 2..20, our Cunningham recursion against Orekit's Holmes-Featherstone, both on
   the uniform frame): |da| <= 1e-14 m/s^2 at every state. Basis: DEBRIS-C measured the two to 2.3e-15 m/s^2
   at degree 180 on the benchmark day; the frame's rounding adds about |a| x 4e-16 = 6e-18. The plant: C20 x
   1.01, about 1.2e-4 m/s^2, 1e10 TOL.
D2 drag (one band, matched): |da| <= 1e-9 x |a_drag(Orekit)| at every state. Basis: the same formula both
   sides; rounding differences of a few 1e-16 and Orekit's altitude from its ellipsoid at flattening 0
   (BELIEVED within 1e-6 m, 2e-11 relative in density). The plant: Cd x 1.01, 1e-2 relative, 1e7 TOL.
D3 radiation pressure, where both models call the state sunlit (our nu = 1 and Orekit's lighting ratio = 1):
   |da| <= 1e-9 x |a_srp(Orekit)|; where both call it umbra (0 and 0): |da| <= 1e-20 m/s^2 (both exactly 0).
   Basis: the same formula; two readers of DE421 agree to about 1.5e-14 AU (DEBRIS-C, Orekit's reader against
   testpo.421 once dates are built right), 2.2 m of 1.5e11 m, 1.5e-11 relative. The plant: Cr x 1.01, 1e-2.
D4 the three planted controls must each break their tolerance at some state: drag (Cd 1% off, our side),
   radiation (Cr 1% off, our side) and gravity (C20 1% off, our side), each at cft64.
REPORTED, no pass condition: penumbra states (|da| and the two shadow functions); states the two models
   classify differently; native64 against cft64 bit for bit; the Sun positions of the two readers; and as a
   figure only, NRLMSISE00's density (F10.7 150, Ap 15) against the one-band exponential atmosphere.
"""
N, SEED = 1000, "0xE6"
JAVA = "C:/Program Files/Java/jre-1.8/bin/java.exe"
JARS = ["orekit-13.1.9.jar", "hipparchus-core-4.0.3.jar", "hipparchus-geometry-4.0.3.jar", "hipparchus-ode-4.0.3.jar",
        "hipparchus-fitting-4.0.3.jar", "hipparchus-optim-4.0.3.jar", "hipparchus-filtering-4.0.3.jar",
        "hipparchus-stat-4.0.3.jar"]
GFC_DIR = "C:/Users/logan/source/repos/cft-debris-scratch/DEBRIS-E/gfc_dedup"
DE_DIR = g.DOWNLOADS + "lnxp1900p2053.421"
W = os.path.join(g.WORK, "e6")
os.makedirs(W, exist_ok=True)


def ours(log, kind, plant=None):
    st = os.path.join(W, "states_%s%s.txt" % (kind, "_" + plant if plant else ""))
    fo = os.path.join(W, "forces_%s%s.txt" % (kind, "_" + plant if plant else ""))
    g.run([g.exe("O2"), "e6", kind, N, SEED, st, fo] + (["--plant", plant] if plant else []), log)
    rows, _ = g.read_rows(fo)
    nb = g.FMT[kind]
    out = {}
    for r in rows:
        v = [float(g.value(h, nb)) for h in r[1:]]
        out[int(r[0])] = {"grav": v[0:3], "drag": v[3:6], "srp": v[6:9], "nu": v[9], "sun": v[10:13], "hex": r[1:]}
    return st, out


def orekit(log, states):
    out = os.path.join(W, "orekit.txt")
    cp = ";".join(g.DOWNLOADS + j + "/" + j for j in JARS)
    for j in JARS:
        log.w("# jar %s sha256 %s" % (j, g.sha256(g.DOWNLOADS + j + "/" + j)))
    p = g.run([JAVA, "-cp", cp, "jdk.nashorn.tools.Shell", os.path.join(g.REPO, "tests", "e6_orekit.js"), "--",
               states, out, GFC_DIR, DE_DIR], log)
    log.w("# " + p.stdout.decode().strip())
    rows, head = g.read_rows(out)
    for h in head:
        log.w("# orekit header: " + h.lstrip("# "))
    res = {}
    for r in rows:
        v = [float.fromhex(x) for x in r[1:]]
        res[int(r[0])] = {"grav": v[0:3], "drag": v[3:6], "srp": v[6:9], "lr": v[9], "sun": v[10:13], "rhoE": v[13],
                          "rhoN": v[14]}
    return res


def norm(a):
    return math.sqrt(sum(x * x for x in a))


def diff(a, b):
    return norm([x - y for x, y in zip(a, b)])


def compare(log, label, us, ok_):
    worst = {"grav": 0.0, "drag": 0.0, "sun_lit": 0.0, "umbra": 0.0}
    fails = {"grav": 0, "drag": 0, "srp": 0}
    cls = {"sunlit": 0, "umbra": 0, "penumbra": 0, "disagree": 0}
    pen = []
    for i, o in ok_.items():
        u = us[i]
        dg = diff(u["grav"], o["grav"])
        worst["grav"] = max(worst["grav"], dg)
        fails["grav"] += dg > 1e-14
        dd = diff(u["drag"], o["drag"]) / norm(o["drag"])
        worst["drag"] = max(worst["drag"], dd)
        fails["drag"] += dd > 1e-9
        nu, lr = u["nu"], o["lr"]
        if nu == 1.0 and lr == 1.0:
            cls["sunlit"] += 1
            ds = diff(u["srp"], o["srp"]) / norm(o["srp"])
            worst["sun_lit"] = max(worst["sun_lit"], ds)
            fails["srp"] += ds > 1e-9
        elif nu == 0.0 and lr == 0.0:
            cls["umbra"] += 1
            ds = diff(u["srp"], o["srp"])
            worst["umbra"] = max(worst["umbra"], ds)
            fails["srp"] += ds > 1e-20
        elif 0.0 < nu < 1.0 and 0.0 < lr < 1.0:
            cls["penumbra"] += 1
            pen.append((i, nu, lr, diff(u["srp"], o["srp"]), norm(o["srp"])))
        else:
            cls["disagree"] += 1
            pen.append((i, nu, lr, diff(u["srp"], o["srp"]), norm(o["srp"])))
    log.w("# %s: classes %s; worst: gravity %.3e m/s^2, drag %.3e relative, radiation sunlit %.3e relative, "
          "umbra %.3e m/s^2" % (label, cls, worst["grav"], worst["drag"], worst["sun_lit"], worst["umbra"]))
    return worst, fails, cls, pen


def main():
    log = g.Log("e6_gate", os.path.abspath(__file__), CRITERIA)
    log.w("# gravity file for Orekit: %s/EIGEN6-C4.gfc sha256 %s" % (GFC_DIR, g.sha256(GFC_DIR + "/EIGEN6-C4.gfc")))
    st64, n64 = ours(log, "native64")
    stc, c64 = ours(log, "cft64")
    log.check(open(st64, "rb").read().split(b"\n", 1)[1] == open(stc, "rb").read().split(b"\n", 1)[1],
              "the same 1,000 states at native64 and cft64")
    ok_ = orekit(log, stc)
    log.check(len(ok_) == N and len(c64) == N, "Orekit evaluated all %d states" % N)
    same = sum(1 for i in c64 if c64[i]["hex"] == n64[i]["hex"])
    log.w("REPORTED native64 against cft64 (C library transcendentals at native64): %d of %d states bit for bit" % (same, N))
    dsun = max(diff(c64[i]["sun"], ok_[i]["sun"]) for i in ok_)
    log.w("REPORTED the Sun, our DE421 reader against Orekit's: max |d| %.3e m (%.3e AU)" % (dsun, dsun / 1.495978707e11))
    for kind, us in (("cft64", c64), ("native64", n64)):
        worst, fails, cls, pen = compare(log, kind, us, ok_)
        log.check(fails["grav"] == 0, "D1 %s gravity: max |da| %.3e m/s^2 <= 1e-14 at all %d states" % (kind, worst["grav"], N))
        log.check(fails["drag"] == 0, "D2 %s drag: max |da|/|a| %.3e <= 1e-9 at all %d states" % (kind, worst["drag"], N))
        log.check(fails["srp"] == 0 and cls["sunlit"] > 0 and cls["umbra"] > 0,
                  "D3 %s radiation: sunlit %d states, max |da|/|a| %.3e <= 1e-9; umbra %d states, max |da| %.3e <= 1e-20"
                  % (kind, cls["sunlit"], worst["sun_lit"], cls["umbra"], worst["umbra"]))
        for (i, nu, lr, d, a) in pen:
            log.w("REPORTED %s penumbra or disagreement, state %d: our nu %.12f, Orekit's ratio %.12f, |da| %.3e m/s^2 "
                  "of |a| %.3e" % (kind, i, nu, lr, d, a))
    for plant, key in (("drag", "drag"), ("srp", "srp"), ("grav", "grav")):
        _, up = ours(log, "cft64", plant)
        worst, fails, cls, _ = compare(log, "cft64 plant " + plant, up, ok_)
        log.check(fails[key] > 0, "D4 control: %s planted 1%% off breaks its tolerance at %d of %d states" %
                  (plant, fails[key], N))
    ratios = sorted(o["rhoN"] / o["rhoE"] for o in ok_.values())
    log.w("REPORTED figure: NRLMSISE00 (F10.7 150, Ap 15) over the one-band exponential density at the 1,000 states: "
          "min %.3g, median %.3g, max %.3g" % (ratios[0], ratios[len(ratios) // 2], ratios[-1]))
    return log.close()


if __name__ == "__main__":
    sys.exit(main())
