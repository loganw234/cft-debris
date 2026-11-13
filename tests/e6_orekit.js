// e6_orekit.js - cft-debris M1, gate E6's referee side: Orekit 13.1.9's force models at the sampled states
// written by tests/m1run.c (mode e6), with every input matched to ours.
// cft-debris, MIT licence (see LICENSE at the repository root). Written by DEBRIS-E, 2026-11-13. The setup
// (data providers, the script-built UTC, the uniform body frame) follows DEBRIS-C's
// studies/debris-c/m0/m0_gate.js (cft-debris's own, MIT). Orekit is called, never copied.
//
//   java -cp <jars> jdk.nashorn.tools.Shell e6_orekit.js -- <states.txt> <out.txt> <gfc_dir> <de_dir>
//
// Matched inputs (each printed in the output's header):
//   - the body frame: a uniform rotation about GCRF's z at OMEGA = 7.292115e-5 rad/s, angle THETA0 = 0.3 rad at
//     T0 = 2008-07-03T00:00:00 TDB, theta = THETA0 + OMEGA t with t in TDB seconds after T0, as ours (version 2);
//   - every date: T0's day plus whole days and seconds, built in TDB from components (no createJDDate);
//   - the Sun: Orekit's own reader of the same DE421 file (CelestialBodyFactory.getSun(), position in GCRF);
//   - gravity: the de-duplicated copy of the benchmark's EIGEN6-C4.gfc (values identical to ours), degree and
//     order 20, Holmes-Featherstone on the body frame;
//   - drag: SimpleExponentialAtmosphere on a OneAxisEllipsoid of radius R_EARTH = 6378136.3 m and flattening 0
//     on the body frame, rho0 3.725e-12 kg/m^3 at h0 400000 m, scale height 58515 m; IsotropicDrag(A, Cd), mass m;
//   - radiation pressure: ConicallyShadowedLightFluxModel(kRef = P_SUN AU^2, R_SUN, Sun, R_EARTH) with
//     P_SUN 4.56e-6 N/m^2, AU 149597870700 m, R_SUN 6.96e8 m; IsotropicRadiationSingleCoefficient(A, Cr);
//   - NRLMSISE00 (a figure only): F10.7 = 150 (daily and average) and Ap = 15 throughout, on the same ellipsoid.
var args = arguments;
var STATES = args[0], OUT = args[1], GFC_DIR = args[2], DE_DIR = args[3];
var OMEGA = 7.292115e-5, THETA0 = 0.3, R_EARTH = 6378136.3, R_SUN = 6.96e8, P_SUN = 4.56e-6, AU = 149597870700.0;
var RHO0 = 3.725e-12, H0 = 400000.0, HS = 58515.0;

var File = java.io.File;
var ArrayList = Java.type("java.util.ArrayList");
var DataContext = Java.type("org.orekit.data.DataContext");
var DirectoryCrawler = Java.type("org.orekit.data.DirectoryCrawler");
var TimeScalesFactory = Java.type("org.orekit.time.TimeScalesFactory");
var UTCTAIOffsetsLoader = Java.type("org.orekit.time.UTCTAIOffsetsLoader");
var OffsetModel = Java.type("org.orekit.time.OffsetModel");
var DateComponents = Java.type("org.orekit.time.DateComponents");
var TimeComponents = Java.type("org.orekit.time.TimeComponents");
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
var SimpleExponentialAtmosphere = Java.type("org.orekit.models.earth.atmosphere.SimpleExponentialAtmosphere");
var NRLMSISE00 = Java.type("org.orekit.models.earth.atmosphere.NRLMSISE00");
var NRLIn = Java.type("org.orekit.models.earth.atmosphere.NRLMSISE00InputParameters");
var DragForce = Java.type("org.orekit.forces.drag.DragForce");
var IsotropicDrag = Java.type("org.orekit.forces.drag.IsotropicDrag");
var ConicalFlux = Java.type("org.orekit.forces.radiation.ConicallyShadowedLightFluxModel");
var RadiationPressureModel = Java.type("org.orekit.forces.radiation.RadiationPressureModel");
var IsoRad = Java.type("org.orekit.forces.radiation.IsotropicRadiationSingleCoefficient");
var CartesianOrbit = Java.type("org.orekit.orbits.CartesianOrbit");
var PVCoordinates = Java.type("org.orekit.utils.PVCoordinates");
var SpacecraftState = Java.type("org.orekit.propagation.SpacecraftState");
var Double = Java.type("java.lang.Double");
var PrintWriter = Java.type("java.io.PrintWriter");

function hx(x) { return Double.toHexString(x); }

var dpm = DataContext.getDefault().getDataProvidersManager();
dpm.addProvider(new DirectoryCrawler(new File(DE_DIR)));
dpm.addProvider(new DirectoryCrawler(new File(GFC_DIR)));
var Loader = Java.extend(UTCTAIOffsetsLoader);
TimeScalesFactory.addUTCTAIOffsetsLoader(new Loader({
  loadOffsets: function () { var l = new ArrayList(); l.add(new OffsetModel(new DateComponents(2006, 1, 1), 33)); return l; }
}));
var tdb = TimeScalesFactory.getTDB();
var D0 = new DateComponents(2008, 7, 3);
var T0 = new AbsoluteDate(D0, TimeComponents.H00, tdb);
function dateAt(t) {           // t whole seconds after T0, in TDB
  var d = Math.floor(t / 86400.0), s = t - 86400.0 * d;
  return new AbsoluteDate(new DateComponents(D0, d), new TimeComponents(s), tdb);
}
function tdbSince(date) {      // TDB seconds from T0 to date
  return date.durationFrom(T0) + (tdb.offsetFromTAI(date).toDouble() - tdb.offsetFromTAI(T0).toDouble());
}
var gcrf = FramesFactory.getGCRF();
var TP = Java.extend(TransformProvider);
var bodyProvider = new TP({
  getTransform: function (date) {
    if (!(date instanceof AbsoluteDate)) throw new java.lang.UnsupportedOperationException("field transforms are not implemented");
    // version 2: the angle runs on TDB seconds since T0, as ours does; durationFrom alone is TAI seconds, which
    // drift from TDB's by up to 5.7e-4 s over E6's 20 days (E6's log 001 failed D1 on that mismatch)
    var theta = THETA0 + OMEGA * tdbSince(date);
    return new Transform(date, new Rotation(Vector3D.PLUS_K, theta, RotationConvention.FRAME_TRANSFORM), new Vector3D(0.0, 0.0, OMEGA));
  }
});
var body = new Frame(gcrf, bodyProvider, "BODY-UNIFORM-E6", false);
var earth = new OneAxisEllipsoid(R_EARTH, 0.0, body);
var sun = CelestialBodyFactory.getSun();
var gp = GravityFieldFactory.getNormalizedProvider(20, 20);
var hf = new HolmesFeatherstone(body, gp);
var atm = new SimpleExponentialAtmosphere(earth, RHO0, H0, HS);
var flux = new ConicalFlux(P_SUN * AU * AU, R_SUN, sun, R_EARTH);
var MIN = new AbsoluteDate(2008, 1, 1, 0, 0, 0.0, tdb), MAX = new AbsoluteDate(2009, 1, 1, 0, 0, 0.0, tdb);
var APS = Java.to([15.0, 15.0, 15.0, 15.0, 15.0, 15.0, 15.0], "double[]");
var NRLInImpl = Java.extend(NRLIn);
var nrlIn = new NRLInImpl({
  getMinDate: function () { return MIN; }, getMaxDate: function () { return MAX; },
  getDailyFlux: function (d) { return 150.0; }, getAverageFlux: function (d) { return 150.0; },
  getAp: function (d) { return APS; }
});
var nrl = new NRLMSISE00(nrlIn, sun, earth, TimeScalesFactory.getUTC());

var out = new PrintWriter(OUT);
out.println("# e6_orekit: java " + java.lang.System.getProperty("java.version") + "; mu " + gp.getMu() + " ae " + gp.getAe() +
            " degree " + gp.getMaxDegree() + " order " + gp.getMaxOrder() + " tide " + gp.getTideSystem());
out.println("# matched: OMEGA " + OMEGA + " THETA0 " + THETA0 + " T0 " + T0.toString(tdb) + " TDB; R_EARTH " + R_EARTH +
            " flattening 0; R_SUN " + R_SUN + "; kRef = P_SUN AU^2 = " + (P_SUN * AU * AU) + "; rho0 " + RHO0 + " h0 " + H0 +
            " H " + HS + "; Sun: Orekit's DE421 reader (" + DE_DIR + "); gravity file directory " + GFC_DIR);
out.println("# columns: i grav(3) drag(3) srp(3) lighting_ratio sun_gcrf(3) rho_exp rho_nrlmsise00 (Java hex doubles)");
var br = new java.io.BufferedReader(new java.io.FileReader(STATES));
var line, n = 0;
while ((line = br.readLine()) !== null) {
  if (line.indexOf("#") == 0 || line.trim().length() == 0) continue;
  var f = line.trim().split(/\s+/);
  var i = f[0], t = Double.parseDouble(f[1]);
  var p = new Vector3D(Double.parseDouble(f[2]), Double.parseDouble(f[3]), Double.parseDouble(f[4]));
  var v = new Vector3D(Double.parseDouble(f[5]), Double.parseDouble(f[6]), Double.parseDouble(f[7]));
  var area = Double.parseDouble(f[8]), mass = Double.parseDouble(f[9]), cd = Double.parseDouble(f[10]), cr = Double.parseDouble(f[11]);
  var date = dateAt(t);
  var orbit = new CartesianOrbit(new PVCoordinates(p, v), gcrf, date, gp.getMu());
  var st = new SpacecraftState(orbit, mass);
  var ag = hf.acceleration(st, hf.getParameters(date));
  var drag = new DragForce(atm, new IsotropicDrag(area, cd));
  var ad = drag.acceleration(st, drag.getParameters(date));
  var srp = new RadiationPressureModel(flux, new IsoRad(area, cr));
  var as = srp.acceleration(st, srp.getParameters(date));
  var lr = flux.getLightingRatio(st);
  var sp = sun.getPosition(date, gcrf);
  var rhoE = atm.getDensity(date, p, gcrf), rhoN = nrl.getDensity(date, p, gcrf);
  out.println(i + " " + hx(ag.getX()) + " " + hx(ag.getY()) + " " + hx(ag.getZ()) + " " + hx(ad.getX()) + " " + hx(ad.getY()) + " " +
              hx(ad.getZ()) + " " + hx(as.getX()) + " " + hx(as.getY()) + " " + hx(as.getZ()) + " " + hx(lr) + " " + hx(sp.getX()) + " " +
              hx(sp.getY()) + " " + hx(sp.getZ()) + " " + hx(rhoE) + " " + hx(rhoN));
  n++;
}
br.close();
out.println("# states " + n);
out.close();
print("e6_orekit: " + n + " states written to " + OUT);
