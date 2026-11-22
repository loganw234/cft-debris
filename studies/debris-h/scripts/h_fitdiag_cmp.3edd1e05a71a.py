# h_fitdiag_cmp.py - cft-debris M1 (DEBRIS-H): reads tests/h_fitdiag.c's dumps. The desktop's (mpmath).
# cft-debris, MIT licence (see LICENSE at the repository root). Written by DEBRIS-H, 2026-11-18.
#
#   python -I -B h_fitdiag_cmp.py cr  <prefix.calls> [--only E|A|C] [--limit N]
#       each logged call's result against the correctly rounded value (mpmath at 200 bits, rounded to nearest binary64)
#   python -I -B h_fitdiag_cmp.py cmp <prefix A> <prefix B>
#       two machines' dumps: the first call that differs (function, argument, both results, the correctly rounded
#       value), how many calls differ, and whether the lanes' positions, the residuals, J and dp are equal
import struct
import sys

import mpmath

FN = {"E": mpmath.exp, "A": mpmath.asin, "C": mpmath.acos, "S": mpmath.sin, "K": mpmath.cos}
NAME = {"E": "exp", "A": "asin", "C": "acos", "S": "sin", "K": "cos"}


def f64(h):
    return struct.unpack(">d", bytes.fromhex(h))[0]


def h64(x):
    return struct.pack(">d", x).hex()


def cr(f, x):
    with mpmath.workprec(200):
        return float(FN[f](mpmath.mpf(x)))


def ulps(a, b):
    ia = struct.unpack(">q", struct.pack(">d", a))[0]
    ib = struct.unpack(">q", struct.pack(">d", b))[0]
    return abs(ia - ib)


def cmd_cr(path, only, limit):
    n, bad, first = {}, {}, {}
    for i, ln in enumerate(open(path, encoding="ascii")):
        if limit and i >= limit:
            break
        f, a, r = ln.split()
        if only and f != only:
            continue
        x, y = f64(a), f64(r)
        c = cr(f, x)
        n[f] = n.get(f, 0) + 1
        if c != y:
            bad[f] = bad.get(f, 0) + 1
            first.setdefault(f, []).append((i, a, r, h64(c), ulps(c, y)))
    for f in sorted(n):
        print("%s: %d calls, %d not correctly rounded%s" % (NAME[f], n[f], bad.get(f, 0),
              "; first: " + "; ".join("call %d arg %s got %s CR %s (%d ulp)" % t for t in first.get(f, [])[:3]) if bad.get(f) else ""))


def load_jr(prefix):
    P, R, D = {}, {}, {}
    for ln in open(prefix + ".jr", encoding="ascii"):
        p = ln.split()
        if p[0] == "P":
            P[(int(p[1]), int(p[2]))] = p[3:6]
        elif p[0] == "R":
            R[(int(p[1]), int(p[2]))] = p[3:]
        elif p[0] == "D":
            D[int(p[1])] = p[2:]
    return P, R, D


def cmd_cmp(pa, pb):
    fa, fb = open(pa + ".calls", encoding="ascii"), open(pb + ".calls", encoding="ascii")
    i, ndiff, first, argdiv = 0, 0, None, None
    for la, lb in zip(fa, fb):
        if la != lb:
            ndiff += 1
            fa_, aa, ra = la.split()
            fb_, ab, rb = lb.split()
            if aa != ab or fa_ != fb_:
                if argdiv is None:
                    argdiv = (i, la.strip(), lb.strip())
                    break
            elif first is None:
                first = (i, fa_, aa, ra, rb)
        i += 1
    print("calls compared: %d; differing before the arguments part: %d" % (i, ndiff - (1 if argdiv else 0)))
    if first:
        j, f, a, ra, rb = first
        c = h64(cr(f, f64(a)))
        print("the first differing call: #%d %s(%s) = %s (A) and %s (B); correctly rounded %s; A %s, B %s" % (
            j, NAME[f], a, ra, rb, c, "is CR" if ra == c else "is not CR (%d ulp)" % ulps(f64(ra), f64(c)),
            "is CR" if rb == c else "is not CR (%d ulp)" % ulps(f64(rb), f64(c))))
    if argdiv:
        print("the arguments first part at call #%d: %s | %s" % argdiv)
    Pa, Ra, Da = load_jr(pa)
    Pb, Rb, Db = load_jr(pb)
    lanes = sorted({l for _, l in Pa})
    for l in lanes:
        d = [q for (q, ll) in Pa if ll == l and Pa[(q, l)] != Pb.get((q, l))]
        print("lane %d: positions differ at %d of %d observations%s" % (l, len(d), sum(1 for (_, ll) in Pa if ll == l),
                                                                    (", first at observation %d" % min(d)) if d else ""))
    nr = sum(1 for k in Ra if k[0] == 1)
    rdiff = sum(1 for k in Ra if Ra[k][0] != Rb.get(k, [None])[0])
    jdiff = sum(1 for k in Ra if Ra[k][1:] != Rb.get(k, [None])[1:])
    print("iteration 1: residuals differ in %d of %d rows; J differs in %d of %d rows; dp %s" % (
        rdiff, nr, jdiff, nr, "equal" if Da.get(1) == Db.get(1) else "differs: %s | %s" % (Da.get(1), Db.get(1))))


def main():
    a = sys.argv[1:]
    if a[0] == "cr":
        only = a[a.index("--only") + 1] if "--only" in a else None
        limit = int(a[a.index("--limit") + 1]) if "--limit" in a else 0
        cmd_cr(a[1], only, limit)
    else:
        cmd_cmp(a[1], a[2])


if __name__ == "__main__":
    main()
