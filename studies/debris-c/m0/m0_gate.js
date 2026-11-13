// DEBRIS-C, M0: the gate. Can Orekit 13.1.9 run here, on this Java 8 runtime, without orekit-data?
// Builds every Orekit object M1 to M3 need, and calls each once.
//
// CRITERION (written before the run, asserted below): every call returns finite values.
// STOP RULES (from the brief): a LinkageError (NoSuchMethodError, UnsupportedClassVersionError,
// NoClassDefFoundError, ...) means this runtime cannot run that path; an OrekitException asking
// for a data file means a download. Either stops that leg; the script reports which, per call.
//
// Data registered: Orekit's DirectoryCrawler on the DE421 binary's own download directory and on
// the EIGEN-6C4 file's own directory, and nowhere else (never the downloads root).
// UTC: built through TimeScalesFactory.addUTCTAIOffsetsLoader with a loader written here that
// returns TAI-UTC = 33 s from 2006-01-01 (READ, IERS EOP Centre's TAI-UTC table: 33 s from
// 2006 Jan. 1 to 2009 Jan. 1). Every epoch used is on 2008-07-03, inside that offset's validity.
// Body frame: a frame turning uniformly about GCRF's z axis at 7.292115e-5 rad/s, built here as a
// TransformProvider, with its angle zero at 2008-07-03T00:00:00 GPS.

var DOWN = "C:/Users/logan/source/repos/cft-debris-downloads/";
var DE_DIR = DOWN + "lnxp1900p2053.421";
// version 2: the gravity file's directory may be given as the first script argument. The re-run
// after run 001 passes the de-duplicated copy's own directory (lead.md 18:07 ruling; derived by
// m0/derive_gfc_copy.py, SHA-256 of the copy bf296183bf9c...); with no argument it is the download.
var GFC_DIR = (typeof arguments !== "undefined" && arguments.length > 0) ? arguments[0] : DOWN + "EIGEN6-C4.gfc";
var CRITERION = "every call returns finite values";

var File = java.io.File;
var ArrayList = Java.type("java.util.ArrayList");
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
var DragForce = Java.type("org.orekit.forces.drag.DragForce");
var IsotropicDrag = Java.type("org.orekit.forces.drag.IsotropicDrag");
var NumericalPropagator = Java.type("org.orekit.propagation.numerical.NumericalPropagator");
var DP853 = Java.type("org.hipparchus.ode.nonstiff.DormandPrince853Integrator");
var CartesianOrbit = Java.type("org.orekit.orbits.CartesianOrbit");
var OrbitType = Java.type("org.orekit.orbits.OrbitType");
var PVCoordinates = Java.type("org.orekit.utils.PVCoordinates");
var SpacecraftState = Java.type("org.orekit.propagation.SpacecraftState");
var OrekitException = Java.type("org.orekit.errors.OrekitException");

var results = [];
function isFiniteAll(v) {
  if (v === null || v === undefined) return false;
  if (typeof v === "number") return isFinite(v);
  for (var i = 0; i < v.length; i++) if (!(typeof v[i] === "number" && isFinite(v[i]))) return false;
  return v.length > 0;
}
function describe(e) {
  if (e instanceof java.lang.Throwable) {
    var s = [], t = e, k = 0;
    while (t !== null && k < 6) { s.push(t.getClass().getName() + ": " + t.getMessage()); t = t.getCause(); k++; }
    return s.join(" <- caused by ");
  }
  return "JS error: " + e;
}
function kind(e) {
  if (e instanceof java.lang.LinkageError) return "LINKAGE";
  var t = e, k = 0;
  while (t instanceof java.lang.Throwable && k < 6) {
    if (t instanceof java.lang.LinkageError) return "LINKAGE";
    var m = ("" + t.getMessage()).toLowerCase();
    if (t instanceof OrekitException && (m.indexOf("no ") >= 0 || m.indexOf("unable to find") >= 0 ||
        m.indexOf("not found") >= 0) && (m.indexOf("data") >= 0 || m.indexOf("file") >= 0 || m.indexOf("loaded") >= 0))
      return "DATA";
    t = t.getCause(); k++;
  }
  return "OTHER";
}
// run one call; f returns [label-of-values, numeric value or array]
function step(name, f) {
  try {
    var r = f();
    var ok = isFiniteAll(r.values);
    results.push({ name: name, ok: ok, kind: ok ? "" : "NONFINITE" });
    print((ok ? "PASS " : "FAIL ") + name + " | " + r.text);
    return r.obj;
  } catch (e) {
    var k = kind(e);
    results.push({ name: name, ok: false, kind: k });
    print("FAIL " + name + " | " + k + " | " + describe(e));
    return null;
  }
}

print("# M0 gate | criterion: " + CRITERION);
print("# java " + java.lang.System.getProperty("java.version") + " | " + java.lang.System.getProperty("java.vm.name") +
      " " + java.lang.System.getProperty("java.vm.version") + " | os.arch " + java.lang.System.getProperty("os.arch"));
print("# orekit.data.path property: " + java.lang.System.getProperty("orekit.data.path"));

// the two data directories, each holding its one file only
function onlyFile(dir, name) {
  var fs = new File(dir).listFiles();
  if (fs === null || fs.length !== 1 || fs[0].getName() !== name)
    throw new java.lang.IllegalStateException("directory " + dir + " does not hold exactly " + name);
}
onlyFile(DE_DIR, "lnxp1900p2053.421");
onlyFile(GFC_DIR, "EIGEN6-C4.gfc");
var dpm = DataContext.getDefault().getDataProvidersManager();
print("# providers before: " + dpm.getProviders().size());
dpm.addProvider(new DirectoryCrawler(new File(DE_DIR)));
dpm.addProvider(new DirectoryCrawler(new File(GFC_DIR)));
print("# providers after: " + dpm.getProviders().size() + " (DirectoryCrawler on " + DE_DIR + " and " + GFC_DIR + ")");

// UTC from a script-written loader
var Loader = Java.extend(UTCTAIOffsetsLoader);
var loaderCalls = 0;
TimeScalesFactory.addUTCTAIOffsetsLoader(new Loader({
  loadOffsets: function () {
    loaderCalls++;
    var l = new ArrayList();
    l.add(new OffsetModel(new DateComponents(2006, 1, 1), 33));
    return l;
  }
}));
var gps = TimeScalesFactory.getGPS();
var T0 = new AbsoluteDate(2008, 7, 3, 0, 0, 0.0, gps);
var utc = step("UTC: TimeScalesFactory.getUTC() and offsetFromTAI(2008-07-03T00:00:00 GPS)", function () {
  var u = TimeScalesFactory.getUTC();
  var off = u.offsetFromTAI(T0).toDouble();
  if (off !== -33.0) throw new java.lang.IllegalStateException("UTC-TAI is " + off + " s, not -33 s");
  return { obj: u, values: [off], text: "UTC-TAI = " + off + " s; loader called " + loaderCalls + " time(s); T0 in UTC = " + T0.toString(u) };
});

// the body frame
var gcrf = FramesFactory.getGCRF();
var OMEGA = 7.292115e-5;
var TP = Java.extend(TransformProvider);
var bodyProvider = new TP({
  getTransform: function (date) {
    if (!(date instanceof AbsoluteDate)) throw new java.lang.UnsupportedOperationException("field transforms are not implemented");
    var theta = OMEGA * date.durationFrom(T0);
    return new Transform(date, new Rotation(Vector3D.PLUS_K, theta, RotationConvention.FRAME_TRANSFORM), new Vector3D(0.0, 0.0, OMEGA));
  }
});
var body = new Frame(gcrf, bodyProvider, "BODY-UNIFORM", false);
// a position: Lasser et al.'s ICRF position at 54650.0 GPS (00orbit_icrf.txt, first row)
var P0 = new Vector3D(4.366820361360165291e+06, 5.099053558275745250e+06, -1.300567008321003756e+06);
var V0 = new Vector3D(8.362746576977971245e+02, 1.175888884985903360e+03, 7.502914376797413752e+03);
var T1 = T0.shiftedBy(3600.0);
step("body frame: getTransformTo(GCRF) at T0 + 1 h, applied to the position", function () {
  var tr = body.getTransformTo(gcrf, T1);
  var p = tr.transformPosition(P0);
  var w = tr.getRotationRate();
  return { obj: tr, values: [p.getX(), p.getY(), p.getZ(), w.getZ()], text: "r = " + p + ", rate z = " + w.getZ() };
});

// gravity: EIGEN-6C4 from its own directory, Holmes-Featherstone on the body frame
var gp180 = step("gravity provider: GravityFieldFactory.getNormalizedProvider(180, 180)", function () {
  var g = GravityFieldFactory.getNormalizedProvider(180, 180);
  return { obj: g, values: [g.getMu(), g.getAe(), g.getMaxDegree(), g.getMaxOrder()],
           text: "mu " + g.getMu() + ", ae " + g.getAe() + ", degree " + g.getMaxDegree() + ", order " + g.getMaxOrder() + ", tide system " + g.getTideSystem() };
});
var hf180 = null;
if (gp180 !== null) {
  hf180 = step("HolmesFeatherstoneAttractionModel(body, provider 180): gradient at the position, in the body frame", function () {
    var hf = new HolmesFeatherstone(body, gp180);
    var pb = gcrf.getTransformTo(body, T0).transformPosition(P0);
    var g = hf.gradient(T0, pb, gp180.getMu());
    return { obj: hf, values: g, text: "gradient " + g[0] + " " + g[1] + " " + g[2] + " m/s^2" };
  });
}
var gp20 = step("gravity provider: GravityFieldFactory.getNormalizedProvider(20, 20)", function () {
  var g = GravityFieldFactory.getNormalizedProvider(20, 20);
  return { obj: g, values: [g.getMu(), g.getAe(), g.getMaxDegree()], text: "degree " + g.getMaxDegree() };
});

// the Sun from DE421 through Orekit's JPL loader
var sun = step("Sun: CelestialBodyFactory.getSun().getPosition(T0, GCRF)", function () {
  var s = CelestialBodyFactory.getSun();
  var p = s.getPosition(T0, gcrf);
  return { obj: s, values: [p.getX(), p.getY(), p.getZ()], text: "r = " + p + " m, |r| = " + p.getNorm() + " m" };
});

// the ellipsoid on the body frame
var earth = step("OneAxisEllipsoid(WGS84 a, f, body).transform(position, GCRF, T0)", function () {
  var e = new OneAxisEllipsoid(Constants.WGS84_EARTH_EQUATORIAL_RADIUS, Constants.WGS84_EARTH_FLATTENING, body);
  var gpnt = e.transform(P0, gcrf, T0);
  return { obj: e, values: [gpnt.getLatitude(), gpnt.getLongitude(), gpnt.getAltitude()],
           text: "lat " + gpnt.getLatitude() + " rad, lon " + gpnt.getLongitude() + " rad, alt " + gpnt.getAltitude() + " m" };
});

// atmosphere inputs: synthetic, constant (the same as M2 and M3 use)
var MIN = new AbsoluteDate(2008, 1, 1, 0, 0, 0.0, gps);
var MAX = new AbsoluteDate(2009, 1, 1, 0, 0, 0.0, gps);
var AP = Java.to([15.0, 15.0, 15.0, 15.0, 15.0, 15.0, 15.0], "double[]");
var NRLInImpl = Java.extend(NRLIn);
var nrlIn = new NRLInImpl({
  getMinDate: function () { return MIN; }, getMaxDate: function () { return MAX; },
  getDailyFlux: function (d) { return 150.0; }, getAverageFlux: function (d) { return 150.0; },
  getAp: function (d) { return AP; }
});
var JBInImpl = Java.extend(JBIn);
var jbIn = new JBInImpl({
  getMinDate: function () { return MIN; }, getMaxDate: function () { return MAX; },
  getF10: function (d) { return 150.0; }, getF10B: function (d) { return 150.0; },
  getS10: function (d) { return 150.0; }, getS10B: function (d) { return 150.0; },
  getXM10: function (d) { return 150.0; }, getXM10B: function (d) { return 150.0; },
  getY10: function (d) { return 150.0; }, getY10B: function (d) { return 150.0; },
  getDSTDTC: function (d) { return 50.0; }
});
var nrl = null, jb = null;
if (sun !== null && earth !== null && utc !== null) {
  nrl = step("NRLMSISE00(inputs, Sun, ellipsoid, script UTC).getDensity(T0, position, GCRF)", function () {
    var m = new NRLMSISE00(nrlIn, sun, earth, utc);
    var rho = m.getDensity(T0, P0, gcrf);
    return { obj: m, values: [rho], text: "rho = " + rho + " kg/m^3 (local solar time mode " + m.getLocalSolarTimeMode() + ")" };
  });
  jb = step("JB2008(inputs, Sun, ellipsoid, script UTC).getDensity(T0, position, GCRF)", function () {
    var m = new JB2008(jbIn, sun, earth, utc);
    var rho = m.getDensity(T0, P0, gcrf);
    return { obj: m, values: [rho], text: "rho = " + rho + " kg/m^3" };
  });
}

// one NumericalPropagator step with that gravity (degree 20, as M3) and NRLMSISE00 drag
if (gp20 !== null && nrl !== null) {
  step("NumericalPropagator, DP853, HolmesFeatherstone 20x20 + NRLMSISE00 drag: propagate T0 -> T0 + 30 s", function () {
    var mu = gp20.getMu();
    var orbit = new CartesianOrbit(new PVCoordinates(P0, V0), gcrf, T0, mu);
    var tol = NumericalPropagator.tolerances(1.0e-3, orbit, OrbitType.CARTESIAN);
    var integ = new DP853(1.0e-3, 300.0, tol[0], tol[1]);
    var prop = new NumericalPropagator(integ);
    prop.setOrbitType(OrbitType.CARTESIAN);
    prop.setMu(mu);
    prop.addForceModel(new HolmesFeatherstone(body, gp20));
    prop.addForceModel(new DragForce(nrl, new IsotropicDrag(1.0, 2.2)));
    prop.setInitialState(new SpacecraftState(orbit, 100.0));
    var s = prop.propagate(T0.shiftedBy(30.0));
    var p = s.getPosition(), v = s.getPVCoordinates().getVelocity();
    return { obj: s, values: [p.getX(), p.getY(), p.getZ(), v.getX(), v.getY(), v.getZ()],
             text: "r = " + p + ", v = " + v };
  });
} else {
  results.push({ name: "NumericalPropagator step", ok: false, kind: "SKIPPED (a prerequisite failed)" });
  print("FAIL NumericalPropagator step | SKIPPED: a prerequisite failed");
}

print("# loaded data names: " + dpm.getLoadedDataNames());
var nfail = 0;
for (var i = 0; i < results.length; i++) if (!results[i].ok) { nfail++; print("# failed: " + results[i].name + " [" + results[i].kind + "]"); }
print("# M0 " + (nfail === 0 ? "PASS" : "FAIL") + ": " + (results.length - nfail) + " of " + results.length + " calls returned finite values (criterion: " + CRITERION + ")");
if (nfail !== 0) exit(1);
