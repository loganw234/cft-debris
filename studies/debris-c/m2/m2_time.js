// DEBRIS-C, M2: the density models' cost, and Holmes-Featherstone's, per call at binary64, timed from
// Nashorn on this host. No orekit-data: the objects are built as in M0 (m0/m0_gate.js).
//
// INPUTS (synthetic, constant; implemented in this script, as the brief asks):
//   NRLMSISE00: F10.7 = 150, 81-day average F10.7 = 150, Ap = 15 in all seven slots.
//   JB2008: F10 = F10B = S10 = S10B = XM10 = XM10B = Y10 = Y10B = 150, DSTDTC = 50 K.
// POINTS: 64 LEO points, Lasser et al.'s ICRF positions every 45th epoch of 2008-07-03 (altitudes
//   about 450 to 480 km), each with its own date; the k-th call uses point k mod 64.
// VARIANTS of each density model: (A) the ellipsoid on GCRF itself, so no frame transform is called
//   inside the model (the model's own cost); (B) the ellipsoid on M0's script-built rotating body
//   frame, so every call also crosses into this script's TransformProvider (as M3 runs).
// GRAVITY: HolmesFeatherstoneAttractionModel.gradient(date, position, mu) at degrees 8, 20, 36 and
//   70, from the de-duplicated EIGEN6-C4 copy (lead.md 18:07), Earth-fixed position in.
//
// CONTROLS (criteria written before the run, asserted at the end):
//   1. Overhead. A loop with the model call replaced by a trivial Java call (Vector3D.getX() on the
//      same point, folded into the checksum) is timed in the same way; its per-call time is
//      Nashorn's per-call overhead, reported beside every figure as a LOWER BOUND (the JIT may fold
//      it). PASS iff every model loop is at least 10 times slower per call than the trivial loop.
//      Every timed loop folds every output into a printed checksum.
//   (Control 2, the reference values, is m2/m2_reference.js.)
// The script-implemented inputs are themselves Java-to-script callbacks inside each model call;
// their count per call is measured in a separate counting pass, and the cost of one such callback
// is measured by sorting with a script comparator against Java's own comparator.
// Timing: each figure is the minimum (and median) over REPS repetitions after WARM warm-up
// repetitions; System.nanoTime; the thread's CPU time and the system CPU load (OperatingSystemMXBean)
// are printed for each repetition.

var GFC_DIR = "C:/Users/logan/source/repos/cft-debris-scratch/DEBRIS-C/gfc_dedup";
var DE_DIR = "C:/Users/logan/source/repos/cft-debris-downloads/lnxp1900p2053.421";
var ORB = "C:/Users/logan/source/repos/cft-debris-downloads/00orbit_icrf.txt/00orbit_icrf.txt";
var WARM = 3, REPS = 7, RATIO = 10.0;
var File = java.io.File, Double = java.lang.Double;
var System = java.lang.System;
var MF = java.lang.management.ManagementFactory;
var tmx = MF.getThreadMXBean();
var osx = MF.getOperatingSystemMXBean();
var DataContext = Java.type("org.orekit.data.DataContext");
var DirectoryCrawler = Java.type("org.orekit.data.DirectoryCrawler");
var TimeScalesFactory = Java.type("org.orekit.time.TimeScalesFactory");
var UTCTAIOffsetsLoader = Java.type("org.orekit.time.UTCTAIOffsetsLoader");
var OffsetModel = Java.type("org.orekit.time.OffsetModel");
var DateComponents = Java.type("org.orekit.time.DateComponents");
var AbsoluteDate = Java.type("org.orekit.time.AbsoluteDate");
var FramesFactory = Java.type("org.orekit.frames.FramesFactory");
var Frame = Java.type("org.orekit.frames.Frame");
var Transform = Java.type("org.orekit.frames.Transform");
var TransformProvider = Java.type("org.orekit.frames.TransformProvider");
var Rotation = Java.type("org.hipparchus.geometry.euclidean.threed.Rotation");
var RotationConvention = Java.type("org.hipparchus.geometry.euclidean.threed.RotationConvention");
var Vector3D = Java.type("org.hipparchus.geometry.euclidean.threed.Vector3D");
var GravityFieldFactory = Java.type("org.orekit.forces.gravity.potential.GravityFieldFactory");
var HolmesFeatherstone = Java.type("org.orekit.forces.gravity.HolmesFeatherstoneAttractionModel");
var CelestialBodyFactory = Java.type("org.orekit.bodies.CelestialBodyFactory");
var OneAxisEllipsoid = Java.type("org.orekit.bodies.OneAxisEllipsoid");
var Constants = Java.type("org.orekit.utils.Constants");
var NRLMSISE00 = Java.type("org.orekit.models.earth.atmosphere.NRLMSISE00");
var NRLIn = Java.type("org.orekit.models.earth.atmosphere.NRLMSISE00InputParameters");
var JB2008 = Java.type("org.orekit.models.earth.atmosphere.JB2008");
var JBIn = Java.type("org.orekit.models.earth.atmosphere.JB2008InputParameters");
var ArrayList = Java.type("java.util.ArrayList");

print("# M2 | java " + System.getProperty("java.version") + " " + System.getProperty("java.vm.name") + " | JVM args " +
      MF.getRuntimeMXBean().getInputArguments() + " | processors " + java.lang.Runtime.getRuntime().availableProcessors());
print("# criterion (control 1): every model loop >= " + RATIO + " x slower per call than the trivial-call loop");
var dpm = DataContext.getDefault().getDataProvidersManager();
dpm.addProvider(new DirectoryCrawler(new File(DE_DIR)));
dpm.addProvider(new DirectoryCrawler(new File(GFC_DIR)));
var Loader = Java.extend(UTCTAIOffsetsLoader);
TimeScalesFactory.addUTCTAIOffsetsLoader(new Loader({ loadOffsets: function () {
  var l = new ArrayList(); l.add(new OffsetModel(new DateComponents(2006, 1, 1), 33)); return l; } }));
var utc = TimeScalesFactory.getUTC();
var gps = TimeScalesFactory.getGPS();
var T0 = new AbsoluteDate(2008, 7, 3, 0, 0, 0.0, gps);
var gcrf = FramesFactory.getGCRF();
var OMEGA = 7.292115e-5;
var frameCalls = 0, COUNT = false;
var TP = Java.extend(TransformProvider);
var body = new Frame(gcrf, new TP({
  getTransform: function (date) {
    if (COUNT) frameCalls++;
    var theta = OMEGA * date.durationFrom(T0);
    return new Transform(date, new Rotation(Vector3D.PLUS_K, theta, RotationConvention.FRAME_TRANSFORM), new Vector3D(0.0, 0.0, OMEGA));
  }
}), "BODY-UNIFORM", false);
var sun = CelestialBodyFactory.getSun();
var MIN = new AbsoluteDate(2008, 1, 1, 0, 0, 0.0, gps), MAX = new AbsoluteDate(2009, 1, 1, 0, 0, 0.0, gps);
var AP = Java.to([15.0, 15.0, 15.0, 15.0, 15.0, 15.0, 15.0], "double[]");
var inCalls = 0;
var NRLInImpl = Java.extend(NRLIn), JBInImpl = Java.extend(JBIn);
var nrlIn = new NRLInImpl({
  getMinDate: function () { if (COUNT) inCalls++; return MIN; }, getMaxDate: function () { if (COUNT) inCalls++; return MAX; },
  getDailyFlux: function (d) { if (COUNT) inCalls++; return 150.0; }, getAverageFlux: function (d) { if (COUNT) inCalls++; return 150.0; },
  getAp: function (d) { if (COUNT) inCalls++; return AP; } });
var jbIn = new JBInImpl({
  getMinDate: function () { if (COUNT) inCalls++; return MIN; }, getMaxDate: function () { if (COUNT) inCalls++; return MAX; },
  getF10: function (d) { if (COUNT) inCalls++; return 150.0; }, getF10B: function (d) { if (COUNT) inCalls++; return 150.0; },
  getS10: function (d) { if (COUNT) inCalls++; return 150.0; }, getS10B: function (d) { if (COUNT) inCalls++; return 150.0; },
  getXM10: function (d) { if (COUNT) inCalls++; return 150.0; }, getXM10B: function (d) { if (COUNT) inCalls++; return 150.0; },
  getY10: function (d) { if (COUNT) inCalls++; return 150.0; }, getY10B: function (d) { if (COUNT) inCalls++; return 150.0; },
  getDSTDTC: function (d) { if (COUNT) inCalls++; return 50.0; } });
var earthA = new OneAxisEllipsoid(Constants.WGS84_EARTH_EQUATORIAL_RADIUS, Constants.WGS84_EARTH_FLATTENING, gcrf);
var earthB = new OneAxisEllipsoid(Constants.WGS84_EARTH_EQUATORIAL_RADIUS, Constants.WGS84_EARTH_FLATTENING, body);
var nrlA = new NRLMSISE00(nrlIn, sun, earthA, utc), nrlB = new NRLMSISE00(nrlIn, sun, earthB, utc);
var jbA = new JB2008(jbIn, sun, earthA, utc), jbB = new JB2008(jbIn, sun, earthB, utc);

// the 64 points
var lines = java.nio.file.Files.readAllLines(java.nio.file.Paths.get(ORB));
var P = [], D = [], k = 0;
for (var i = 0; i < lines.size(); i++) {
  var s = ("" + lines.get(i)).trim();
  if (s.length === 0 || s.charAt(0) === '#' || s.charAt(0) === 'g') continue;
  var t = s.split(/\s+/);
  if (t.length !== 10) continue;
  if (k % 45 === 0 && P.length < 64) {
    P.push(new Vector3D(Double.parseDouble(t[1]), Double.parseDouble(t[2]), Double.parseDouble(t[3])));
    D.push(T0.shiftedBy(30.0 * k));
  }
  k++;
}
var altMin = 1e99, altMax = -1e99;
for (var j = 0; j < 64; j++) { var a = earthA.transform(P[j], gcrf, D[j]).getAltitude(); altMin = Math.min(altMin, a); altMax = Math.max(altMax, a); }
print("# points: " + P.length + ", altitudes " + (altMin / 1e3).toFixed(1) + " to " + (altMax / 1e3).toFixed(1) + " km");

var gp = {}, hf = {}, degs = [8, 20, 36, 70];
for (var j = 0; j < degs.length; j++) { gp[degs[j]] = GravityFieldFactory.getNormalizedProvider(degs[j], degs[j]); hf[degs[j]] = new HolmesFeatherstone(body, gp[degs[j]]); }
var MU = gp[8].getMu();

// the timed loops; each returns its checksum
var loops = {
  "empty (no call)": function (n) { var cs = 0.0; for (var i = 0; i < n; i++) cs += (i & 63); return cs; },
  "trivial Java call Vector3D.getX()": function (n) { var cs = 0.0; for (var i = 0; i < n; i++) cs += P[i & 63].getX(); return cs; },
  "NRLMSISE00 getDensity (A: ellipsoid on GCRF)": function (n) { var cs = 0.0; for (var i = 0; i < n; i++) cs += nrlA.getDensity(D[i & 63], P[i & 63], gcrf); return cs; },
  "NRLMSISE00 getDensity (B: script body frame)": function (n) { var cs = 0.0; for (var i = 0; i < n; i++) cs += nrlB.getDensity(D[i & 63], P[i & 63], gcrf); return cs; },
  "JB2008 getDensity (A: ellipsoid on GCRF)": function (n) { var cs = 0.0; for (var i = 0; i < n; i++) cs += jbA.getDensity(D[i & 63], P[i & 63], gcrf); return cs; },
  "JB2008 getDensity (B: script body frame)": function (n) { var cs = 0.0; for (var i = 0; i < n; i++) cs += jbB.getDensity(D[i & 63], P[i & 63], gcrf); return cs; }
};
function hfLoop(deg) {
  var m = hf[deg];
  return function (n) { var cs = 0.0; for (var i = 0; i < n; i++) { var g = m.gradient(T0, P[i & 63], MU); cs += g[0] + g[1] + g[2]; } return cs; };
}
var order = ["empty (no call)", "trivial Java call Vector3D.getX()"];
for (var j = 0; j < degs.length; j++) { loops["HolmesFeatherstone gradient, degree " + degs[j]] = hfLoop(degs[j]); order.push("HolmesFeatherstone gradient, degree " + degs[j]); }
order.push("NRLMSISE00 getDensity (A: ellipsoid on GCRF)", "NRLMSISE00 getDensity (B: script body frame)",
           "JB2008 getDensity (A: ellipsoid on GCRF)", "JB2008 getDensity (B: script body frame)");

function timeLoop(name, f) {
  // version 2 (after m2_time.001.log, whose density repetitions were only 19 to 90 ms long because the
  // calibration ran cold): calibrate twice, warm, to about 0.25 s a repetition. The thread-CPU column
  // is dropped: on this host the tick-sampled counters read about a quarter of the real CPU time
  // (logs/m2_cyclecal.001.log); the runner reports the process's cycle count instead.
  var n = 100, dt = 0;
  for (var pass = 0; pass < 2; pass++) {
    while (true) { var t0 = System.nanoTime(); f(n); dt = System.nanoTime() - t0; if (dt > 1e8 || n > 4e8) break; n *= 4; }
    n = Math.max(100, Math.floor(n * 2.5e8 / dt));
  }
  var per = [], loads = [], sums = [];
  for (var r = 0; r < WARM + REPS; r++) {
    var t0 = System.nanoTime();
    var cs = f(n);
    var t1 = System.nanoTime();
    var load = osx.getSystemCpuLoad();
    if (r >= WARM) { per.push((t1 - t0) / n); loads.push(load * 100); sums.push(cs); }
  }
  var sorted = per.slice().sort(function (a, b) { return a - b; });
  var res = { name: name, n: n, min: sorted[0], med: sorted[Math.floor(sorted.length / 2)], loads: loads, sums: sums };
  print(name + " | n " + n + " | ns/call min " + res.min.toFixed(2) + " median " + res.med.toFixed(2) +
        " | system load % " + loads.map(function (x) { return x.toFixed(0); }).join("/") +
        " | checksums " + sums.map(function (x) { return Double.toHexString(x); }).join(" "));
  return res;
}

var R = {};
for (var j = 0; j < order.length; j++) R[order[j]] = timeLoop(order[j], loops[order[j]]);

// callbacks per call (a separate counting pass, not timed)
COUNT = true;
var counts = {};
var cnames = ["NRLMSISE00 getDensity (A: ellipsoid on GCRF)", "NRLMSISE00 getDensity (B: script body frame)",
              "JB2008 getDensity (A: ellipsoid on GCRF)", "JB2008 getDensity (B: script body frame)"];
for (var j = 0; j < cnames.length; j++) {
  inCalls = 0; frameCalls = 0; loops[cnames[j]](6400);
  counts[cnames[j]] = { inputs: inCalls / 6400, frame: frameCalls / 6400 };
  print("# callbacks per call, " + cnames[j] + ": input-parameter methods " + (inCalls / 6400) + ", body-frame transforms " + (frameCalls / 6400));
}
COUNT = false;

// the cost of one Java-to-script callback: Arrays.sort with a script comparator against Java's own
var NS = 200000, base = [];
var rnd = new java.util.Random(12345);
for (var i = 0; i < NS; i++) base.push(rnd.nextInt());
var src = Java.to(base, "java.lang.Integer[]");
var cmpCount = 0;
var cmpJS = new java.util.Comparator({ compare: function (a, b) { if (COUNT) cmpCount++; return a < b ? -1 : (a > b ? 1 : 0); } });
var cmpJava = java.util.Comparator.naturalOrder();
COUNT = true; var cpy = java.util.Arrays.copyOf(src, NS); java.util.Arrays.sort(cpy, cmpJS); COUNT = false;
var ncmp = cmpCount;
function timeSort(cmp) {
  var best = 1e99;
  for (var r = 0; r < WARM + REPS; r++) {
    var a = java.util.Arrays.copyOf(src, NS);
    var t0 = System.nanoTime(); java.util.Arrays.sort(a, cmp); var t1 = System.nanoTime();
    if (r >= WARM) best = Math.min(best, t1 - t0);
  }
  return best;
}
var tJS = timeSort(cmpJS), tJava = timeSort(cmpJava);
var cb = (tJS - tJava) / ncmp;
print("# callback cost: sort of " + NS + " Integers, " + ncmp + " comparisons: script comparator " + (tJS / 1e6).toFixed(1) +
      " ms, Java comparator " + (tJava / 1e6).toFixed(1) + " ms: " + cb.toFixed(1) + " ns per Java-to-script call (min of " + REPS + ")");

// summary and control 1
var ov = R["trivial Java call Vector3D.getX()"].min;
print("# SUMMARY (ns per call, min over repetitions; overhead = the trivial call's " + ov.toFixed(2) + " ns, a lower bound)");
var ok = true;
for (var j = 2; j < order.length; j++) {
  var r = R[order[j]];
  var ratio = r.min / ov;
  var pass = ratio >= RATIO;
  ok = ok && pass;
  var c = counts[order[j]];
  var corr = c ? r.min - ov - (c.inputs + c.frame) * cb : r.min - ov;
  print((pass ? "PASS " : "FAIL ") + order[j] + ": " + r.min.toFixed(1) + " ns (median " + r.med.toFixed(1) + "), " + ratio.toFixed(0) +
        " x the trivial call" + (c ? "; minus the overhead and " + (c.inputs + c.frame) + " callbacks at " + cb.toFixed(1) + " ns: " + corr.toFixed(1) + " ns" :
        "; minus the overhead: " + corr.toFixed(1) + " ns"));
}
print("# control 1 " + (ok ? "PASS" : "FAIL") + "; empty loop " + R["empty (no call)"].min.toFixed(2) + " ns per iteration");
if (!ok) exit(1);
