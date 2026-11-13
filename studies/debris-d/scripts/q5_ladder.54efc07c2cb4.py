"""q5_ladder.py - DEBRIS-D, Q5's ladder (cft-debris, MIT). COMPUTED only:
device time per LEO object-day, real-time capacity and the speed-up at ESA's
sizes, from labelled inputs. Nothing here is MEASURED; each input names its
source.

Inputs:
  P  instructions a step, MEASURED from cftc's manifests (Q2): j2dragrot-rk4
     (J2, C22/S22, rotation, exponential drag); field7 (degree 7, the largest
     that fits sw's 256 slots and the 512-slot bank, so loadable on hip:N);
     field20: ESTIMATE 30,000 to 40,000 at every format (basis: a quadratic
     fit to degrees 6, 7, 8 gives 29,900; Q1's degree-20/degree-8 count ratio
     on the degree-8 image's gravity share gives 32,400; spills may add up to
     a quarter more: degree 8 already spills 265 slots).
  S  steps an object-day, MEASURED (Q4): rk4 at 30 s (2,880; 83 m a day), 15 s
     (5,760; 3.3 m), 7.5 s (11,520; 0.15 m), 0.9375 s (92,160; where binary64's
     own rounding, 1.3e-5 m, meets the truncation).
     IAS15 beside it (not a v1 route): 559 steps and 16,449 evaluations
     (MEASURED, Q4, real EIGEN-6C4 degree 20 with drag); each evaluation priced
     at a quarter of an rk4 step's instructions, plus IAS15's own arithmetic in
     its FMA form, ESTIMATE 7,000 instructions a step (Q1's READ count, about
     600 FMA-class operations a coordinate an iteration x 3 coordinates x 3.9
     iterations, one instruction each on the generic tier's interpreter).
  R  lane-instructions a second, kernel only, resident, at 1M lanes: COMPUTED
     from GPU-A's lane-programs a second (GPU-A-hip.md:844-854, MEASURED there)
     x the routine's instructions (LANGUAGE.md:466 and :504; sin 406/382/389,
     atan 176/186/203 at fp64/fp128/fp256); the low and high of the sin and
     atan programs. fp128: ESTIMATE, the card's fp64 rate over its measured
     elementwise fp64/fp128 FMA ratio (GPU-A-hip.md:506-509: 4070 1.68, 5060 Ti
     1.85, RX 7600 1.45). CPU: MEASURED (Q3, this host, one core, the software
     executor on our images); six cores BELIEVED linear. MI300X: ESTIMATE, the
     RX 7600's rate x 6.5 to 15.5 (GPU-A's MI300X generic fp256 FMA ESTIMATE,
     0.5 to 1.2e9 a second (GPU-E-mi300x-ring.md:310-311, READ), over the RX
     7600's MEASURED 77.4e6 (GPU-A-hip.md:485)).

usage: python -I -B q5_ladder.py   (writes logs/q5_ladder.NNN.log)
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tools"))
import dd  # noqa: E402

DAY = 86400.0
P = {"j2dragrot": {"fp64": (4541, 4541), "fp128": (4505, 4505), "fp256": (4605, 4605)},
     "field7": {"fp64": (8302, 8302), "fp128": (8291, 8291), "fp256": (8396, 8396)},
     "field20": {"fp64": (30000, 40000), "fp128": (30000, 40000), "fp256": (30000, 40000)}}
S = {"rk4 30 s": 2880, "rk4 15 s": 5760, "rk4 7.5 s": 11520, "rk4 0.9375 s": 92160}
IAS15 = (559, 16449, 7000)
SIN = {"fp64": 406, "fp128": 382, "fp256": 389}
ATAN = {"fp64": 176, "fp128": 186, "fp256": 203}
# GPU-A lane-programs a second (sin, atan), low and high
GPUA = {"RTX 5060 Ti": {"fp64": ((5.97e6, 5.97e6), (13.3e6, 13.3e6)), "fp256": ((1.25e6, 1.25e6), (2.65e6, 2.65e6)),
                        "fp256 fixed": ((12.8e6, 12.8e6), (23.9e6, 23.9e6))},
        "RTX 4070": {"fp64": ((4.9e6, 5.3e6), (10.2e6, 10.9e6)), "fp256": ((1.8e6, 1.9e6), (3.8e6, 4.1e6)),
                     "fp256 fixed": ((3.8e6, 3.9e6), (7.4e6, 7.8e6))},
        "RX 7600": {"fp64": ((2.67e6, 2.67e6), (5.75e6, 5.75e6)), "fp256": ((0.98e6, 0.98e6), (2.04e6, 2.04e6)),
                    "fp256 fixed": ((3.5e6, 3.5e6), (6.8e6, 6.9e6))}}
FMA_RATIO_64_128 = {"RTX 5060 Ti": 720 / 390, "RTX 4070": 690 / 411, "RX 7600": 229 / 158}
CPU1 = {"fp64": 1.163e7, "fp128": 1.031e7, "fp256": 0.802e7}   # lane-instructions/s, one core (Q3 MEASURED)
MI_LO, MI_HI = 0.5e9 / 77.4e6, 1.2e9 / 77.4e6
SIZES = [28149, 47393, 68450, 1.5e6, 230e6]


def rates():
    R = {}
    for card, d in GPUA.items():
        for key in ("fp64", "fp256", "fp256 fixed"):
            fmt = "fp256" if key.startswith("fp256") else "fp64"
            (s_lo, s_hi), (a_lo, a_hi) = d[key]
            vals = [s_lo * SIN[fmt], s_hi * SIN[fmt], a_lo * ATAN[fmt], a_hi * ATAN[fmt]]
            R[(card, key)] = (min(vals), max(vals))
        lo, hi = R[(card, "fp64")]
        R[(card, "fp128 (ESTIMATE)")] = (lo / FMA_RATIO_64_128[card], hi / FMA_RATIO_64_128[card])
    lo, hi = R[("RX 7600", "fp64")]
    R[("MI300X (ESTIMATE)", "fp64")] = (lo * MI_LO, hi * MI_HI)
    lo, hi = R[("RX 7600", "fp256")]
    R[("MI300X (ESTIMATE)", "fp256")] = (lo * MI_LO, hi * MI_HI)
    lo, hi = R[("RX 7600", "fp128 (ESTIMATE)")]
    R[("MI300X (ESTIMATE)", "fp128 (ESTIMATE)")] = (lo * MI_LO, hi * MI_HI)
    for fmt in ("fp64", "fp128", "fp256"):
        R[("CPU one core", fmt)] = (CPU1[fmt], CPU1[fmt])
        R[("CPU six cores (BELIEVED linear)", fmt)] = (6 * CPU1[fmt], 6 * CPU1[fmt])
    return R


def fmt_of(key):
    return "fp64" if key.startswith("fp64") else ("fp128" if key.startswith("fp128") else "fp256")


def main():
    log = dd.Log(__file__, "q5_ladder")
    log.criteria("none asserted: a ladder of COMPUTED figures from the labelled inputs in this script's docstring; "
                 "the one check is arithmetic: each rate range has low <= high (asserted)")
    R = rates()
    for k, (lo, hi) in R.items():
        assert lo <= hi
    log.w("RATES lane-instructions a second (kernel only, resident, 1M lanes for the cards):")
    for (dev, key), (lo, hi) in sorted(R.items()):
        log.w("  %-34s %-18s %.3g to %.3g" % (dev, key, lo, hi))
    for model in ("j2dragrot", "field7", "field20"):
        log.w("")
        log.w("MODEL %s: seconds of device time an object-day | objects in real time (one simulated day a day)" % model)
        for (dev, key), (rlo, rhi) in sorted(R.items()):
            f = fmt_of(key)
            plo, phi = P[model][f]
            cells = []
            for sname, steps in S.items():
                tlo, thi = plo * steps / rhi, phi * steps / rlo
                cells.append("%s: %.3g-%.3g s | %.3g-%.3g" % (sname, tlo, thi, DAY / thi, DAY / tlo))
            st, ev, own = IAS15
            ilo = (ev * plo / 4 + st * own) / rhi
            ihi = (ev * phi / 4 + st * own) / rlo
            cells.append("IAS15 (not v1): %.3g-%.3g s | %.3g-%.3g" % (ilo, ihi, DAY / ihi, DAY / ilo))
            log.w("  %-30s %-17s %s" % (dev, key, " ; ".join(cells)))
    log.w("")
    log.w("SPEED-UP at ESA's sizes, field20 at rk4 15 s (simulated days a wall day = 86400 / (N x t_obj)); "
          "below 1 is slower than real time; no occupancy loss below the device's resident lanes is applied:")
    for (dev, key), (rlo, rhi) in sorted(R.items()):
        f = fmt_of(key)
        plo, phi = P["field20"][f]
        tlo, thi = plo * S["rk4 15 s"] / rhi, phi * S["rk4 15 s"] / rlo
        log.w("  %-30s %-17s " % (dev, key) + "  ".join("N=%.3g: %.3g-%.3g" % (n, DAY / (n * thi), DAY / (n * tlo))
                                                         for n in SIZES))
    rc = log.close()
    sys.exit(1 if rc else 0)


if __name__ == "__main__":
    main()
