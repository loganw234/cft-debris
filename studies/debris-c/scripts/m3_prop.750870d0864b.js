// DEBRIS-C, M3: is Orekit bit-reproducible? One LEO object propagated for one day.
// SETUP (as M0, no orekit-data): EIGEN-6C4 gravity to degree and order 20 (HolmesFeatherstone, from the
// de-duplicated copy, lead.md 18:07) on the script-built body frame (uniform rotation about GCRF z at
// 7.292115e-5 rad/s, angle zero at the start), NRLMSISE00 drag with constant script-implemented inputs
// (F10.7 = 150, F10.7A = 150, Ap = 15) on a WGS84 ellipsoid on that frame, the Sun from DE421, UTC from a
// script loader (TAI-UTC 33 s). Drag: IsotropicDrag, cross-section 1 m^2, Cd 2.2; mass 100 kg.
// Initial state: Lasser et al.'s ICRF state at 2008-07-03T00:00:00 GPS (00orbit_icrf.txt, first row),
// taken as GCRF.
// INTEGRATOR: Hipparchus DormandPrince853Integrator, min step 1e-3 s, max step 300 s, absolute and
// relative tolerances from NumericalPropagator.tolerances(1e-3 m, orbit, CARTESIAN); orbit type CARTESIAN;
// central attraction from the provider's mu (NumericalPropagator adds it).
// RECORD: at the end of every integrator step, the state's offset from the start (s) and its position
// and velocity (GCRF), as raw IEEE bits: each written to the per-step file as hex doubles and fed to a
// running SHA-256; the final state's bits are printed as hex doubles.
// usage: m3_prop.js -- <per-step out file> [ulp]   ("ulp": the initial x moved up by one ulp, the control)
// The criterion and its comparison are in m3/m3_compare.py; this script only records.
var OUT = arguments[0], PLANT = arguments.length > 1 && arguments[1] === "ulp";
var GFC_DIR = "C:/Users/logan/source/repos/cft-debris-scratch/DEBRIS-C/gfc_dedup";
var DE_DIR = "C:/Users/logan/source/repos/cft-debris-downloads/lnxp1900p2053.421";
var File = java.io.File, Double = java.lang.Double, Long = java.lang.Long, System = java.lang.System;
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
var DragForce = Java.type("org.orekit.forces.drag.DragForce");
var IsotropicDrag = Java.type("org.orekit.forces.drag.IsotropicDrag");
var NumericalPropagator = Java.type("org.orekit.propagation.numerical.NumericalPropagator");
var DP853 = Java.type("org.hipparchus.ode.nonstiff.DormandPrince853Integrator");
var CartesianOrbit = Java.type("org.orekit.orbits.CartesianOrbit");
var OrbitType = Java.type("org.orekit.orbits.OrbitType");
var PVCoordinates = Java.type("org.orekit.utils.PVCoordinates");
var SpacecraftState = Java.type("org.orekit.propagation.SpacecraftState");
var OrekitStepHandler = Java.type("org.orekit.propagation.sampling.OrekitStepHandler");
var ArrayList = Java.type("java.util.ArrayList");
var MF = java.lang.management.ManagementFactory;

print("# M3 run | java " + System.getProperty("java.version") + " | JVM args " + MF.getRuntimeMXBean().getInputArguments() +
      " | plant: " + (PLANT ? "initial x + 1 ulp" : "none"));
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
var TP = Java.extend(TransformProvider);
var body = new Frame(gcrf, new TP({
  getTransform: function (date) {
    var theta = OMEGA * date.durationFrom(T0);
    return new Transform(date, new Rotation(Vector3D.PLUS_K, theta, RotationConvention.FRAME_TRANSFORM), new Vector3D(0.0, 0.0, OMEGA));
  }
}), "BODY-UNIFORM", false);
var sun = CelestialBodyFactory.getSun();
var MIN = new AbsoluteDate(2008, 1, 1, 0, 0, 0.0, gps), MAX = new AbsoluteDate(2009, 1, 1, 0, 0, 0.0, gps);
var AP = Java.to([15.0, 15.0, 15.0, 15.0, 15.0, 15.0, 15.0], "double[]");
var NRLInImpl = Java.extend(NRLIn);
var nrlIn = new NRLInImpl({
  getMinDate: function () { return MIN; }, getMaxDate: function () { return MAX; },
  getDailyFlux: function (d) { return 150.0; }, getAverageFlux: function (d) { return 150.0; },
  getAp: function (d) { return AP; } });
var earth = new OneAxisEllipsoid(Constants.WGS84_EARTH_EQUATORIAL_RADIUS, Constants.WGS84_EARTH_FLATTENING, body);
var nrl = new NRLMSISE00(nrlIn, sun, earth, utc);
var gp = GravityFieldFactory.getNormalizedProvider(20, 20);
var mu = gp.getMu();
var x0 = 4.366820361360165291e+06;
if (PLANT) x0 = Math.nextUp(x0);
var P0 = new Vector3D(x0, 5.099053558275745250e+06, -1.300567008321003756e+06);
var V0 = new Vector3D(8.362746576977971245e+02, 1.175888884985903360e+03, 7.502914376797413752e+03);
print("# initial x bits " + Long.toHexString(Double.doubleToRawLongBits(P0.getX())) + " (" + Double.toHexString(P0.getX()) + ")");
var orbit = new CartesianOrbit(new PVCoordinates(P0, V0), gcrf, T0, mu);
var tol = NumericalPropagator.tolerances(1.0e-3, orbit, OrbitType.CARTESIAN);
print("# tolerances: absolute " + java.util.Arrays.toString(tol[0]) + " relative " + java.util.Arrays.toString(tol[1]));
var integ = new DP853(1.0e-3, 300.0, tol[0], tol[1]);
var prop = new NumericalPropagator(integ);
prop.setOrbitType(OrbitType.CARTESIAN);
prop.setMu(mu);
prop.addForceModel(new HolmesFeatherstone(body, gp));
prop.addForceModel(new DragForce(nrl, new IsotropicDrag(1.0, 2.2)));
prop.setInitialState(new SpacecraftState(orbit, 100.0));

var md = java.security.MessageDigest.getInstance("SHA-256");
var bb = java.nio.ByteBuffer.allocate(8);
var w = new java.io.PrintWriter(new java.io.BufferedWriter(new java.io.FileWriter(OUT)));
var nsteps = 0;
function feed(d) {
  var bits = Double.doubleToRawLongBits(d);
  bb.clear(); bb.putLong(bits); md.update(bb.array());
  return Double.toHexString(d);
}
prop.setStepHandler(new OrekitStepHandler({
  handleStep: function (interp) {
    var s = interp.getCurrentState();
    var pv = s.getPVCoordinates(gcrf);
    var p = pv.getPosition(), v = pv.getVelocity();
    var t = s.getDate().durationFrom(T0);
    w.println(nsteps + " " + feed(t) + " " + feed(p.getX()) + " " + feed(p.getY()) + " " + feed(p.getZ()) + " " +
              feed(v.getX()) + " " + feed(v.getY()) + " " + feed(v.getZ()));
    nsteps++;
  }
}));
var t0 = System.nanoTime();
var fin = prop.propagate(T0.shiftedBy(86400.0));
var wall = (System.nanoTime() - t0) / 1e9;
w.close();
var pv = fin.getPVCoordinates(gcrf);
var hex = "";
var dig = md.digest();
for (var i = 0; i < dig.length; i++) hex += ("0" + (dig[i] & 0xff).toString(16)).slice(-2);
print("# steps " + nsteps + ", propagation wall " + wall.toFixed(2) + " s");
print("FINAL t " + Double.toHexString(fin.getDate().durationFrom(T0)) + " x " + Double.toHexString(pv.getPosition().getX()) +
      " y " + Double.toHexString(pv.getPosition().getY()) + " z " + Double.toHexString(pv.getPosition().getZ()) +
      " vx " + Double.toHexString(pv.getVelocity().getX()) + " vy " + Double.toHexString(pv.getVelocity().getY()) +
      " vz " + Double.toHexString(pv.getVelocity().getZ()));
print("STEPHASH " + hex);
