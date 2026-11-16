// f4_orekit.js - cft-debris M1 (DEBRIS-F), gate F4's referee side: Orekit 13.1.9's gravity (degree and order 20)
// and drag (one exponential band) in Orekit's ITRF (IERS 2010, simple EOP) as the body frame, at the states that
// tests/f4_gate.py samples. cft-debris, MIT licence (see LICENSE at the repository root). Written by DEBRIS-F,
// 2026-11-16, from DEBRIS-E's tests/e6_orekit.js (cft-debris's own, MIT); Orekit is called, never copied.
//
//   java -cp <jars> jdk.nashorn.tools.Shell f4_orekit.js -- <states> <out> <eop_dir> <gfc_dir>
// states: "i tai_s x y z vx vy vz area mass cd" (Java/C99 hex), tai_s from 2026-10-16T00:00:00 TAI, GCRF.
// Matched: the de-duplicated copy of the benchmark's EIGEN6-C4.gfc (values identical to the file M1 reads), degree
// and order 20, Holmes-Featherstone on Orekit's ITRF; SimpleExponentialAtmosphere on a OneAxisEllipsoid of radius
// 6378136.3 m, flattening 0, on the same ITRF (so the atmosphere co-rotates with that frame), rho0 3.725e-12 kg/m^3
// at 400000 m, scale height 58515 m; IsotropicDrag(area, cd) with the mass.
var args = arguments;
var STATES = args[0], OUT = args[1], EOP_DIR = args[2], GFC_DIR = args[3];
var R_EARTH = 6378136.3, RHO0 = 3.725e-12, H0 = 400000.0, HS = 58515.0;
var File = java.io.File;
var DataContext = Java.type('org.orekit.data.DataContext');
var DirectoryCrawler = Java.type('org.orekit.data.DirectoryCrawler');
var FramesFactory = Java.type('org.orekit.frames.FramesFactory');
var IERSConventions = Java.type('org.orekit.utils.IERSConventions');
var TimeScalesFactory = Java.type('org.orekit.time.TimeScalesFactory');
var AbsoluteDate = Java.type('org.orekit.time.AbsoluteDate');
var DateComponents = Java.type('org.orekit.time.DateComponents');
var TimeComponents = Java.type('org.orekit.time.TimeComponents');
var Vector3D = Java.type('org.hipparchus.geometry.euclidean.threed.Vector3D');
var GravityFieldFactory = Java.type('org.orekit.forces.gravity.potential.GravityFieldFactory');
var HolmesFeatherstone = Java.type('org.orekit.forces.gravity.HolmesFeatherstoneAttractionModel');
var OneAxisEllipsoid = Java.type('org.orekit.bodies.OneAxisEllipsoid');
var SimpleExponentialAtmosphere = Java.type('org.orekit.models.earth.atmosphere.SimpleExponentialAtmosphere');
var DragForce = Java.type('org.orekit.forces.drag.DragForce');
var IsotropicDrag = Java.type('org.orekit.forces.drag.IsotropicDrag');
var CartesianOrbit = Java.type('org.orekit.orbits.CartesianOrbit');
var PVCoordinates = Java.type('org.orekit.utils.PVCoordinates');
var SpacecraftState = Java.type('org.orekit.propagation.SpacecraftState');
var Double = Java.type('java.lang.Double');
var PrintWriter = Java.type('java.io.PrintWriter');
function hx(x) { return Double.toHexString(x); }
var dpm = DataContext.getDefault().getDataProvidersManager();
dpm.addProvider(new DirectoryCrawler(new File(EOP_DIR)));
dpm.addProvider(new DirectoryCrawler(new File(GFC_DIR)));
var utc = TimeScalesFactory.getUTC(), tai = TimeScalesFactory.getTAI();
var REF = new AbsoluteDate(new DateComponents(2026, 10, 16), TimeComponents.H00, tai);
var eop = FramesFactory.getEOPHistory(IERSConventions.IERS_2010, true);
var chk = new AbsoluteDate(new DateComponents(DateComponents.MODIFIED_JULIAN_EPOCH, 61360), TimeComponents.H00, utc);
var u = eop.getUT1MinusUTC(chk);
if (!(Math.abs(u - (-0.0704999)) < 1e-9)) { print('EOP NOT LOADED: UT1-UTC at MJD 61360 = ' + u); java.lang.System.exit(4); }
var gcrf = FramesFactory.getGCRF(), itrf = FramesFactory.getITRF(IERSConventions.IERS_2010, true);
var earth = new OneAxisEllipsoid(R_EARTH, 0.0, itrf);
var gp = GravityFieldFactory.getNormalizedProvider(20, 20);
var hf = new HolmesFeatherstone(itrf, gp);
var atm = new SimpleExponentialAtmosphere(earth, RHO0, H0, HS);
var out = new PrintWriter(OUT);
out.println('# f4_orekit: java ' + java.lang.System.getProperty('java.version') + '; EOP loaded: UT1-UTC at MJD 61360 = ' + u +
            '; mu ' + gp.getMu() + ' ae ' + gp.getAe() + ' degree ' + gp.getMaxDegree() + ' order ' + gp.getMaxOrder() + '; body frame ' + itrf.getName());
out.println('# columns: i grav(3) drag(3) omega_itrf_in_gcrf(3) (Java hex)');
var br = new java.io.BufferedReader(new java.io.FileReader(STATES));
var line, n = 0;
while ((line = br.readLine()) !== null) {
  if (line.indexOf('#') == 0 || line.trim().length() == 0) continue;
  var f = line.trim().split(/\s+/);
  var d = new AbsoluteDate(REF, Double.parseDouble(f[1]));
  var p = new Vector3D(Double.parseDouble(f[2]), Double.parseDouble(f[3]), Double.parseDouble(f[4]));
  var v = new Vector3D(Double.parseDouble(f[5]), Double.parseDouble(f[6]), Double.parseDouble(f[7]));
  var area = Double.parseDouble(f[8]), mass = Double.parseDouble(f[9]), cd = Double.parseDouble(f[10]);
  var st = new SpacecraftState(new CartesianOrbit(new PVCoordinates(p, v), gcrf, d, gp.getMu()), mass);
  var ag = hf.acceleration(st, hf.getParameters(d));
  var drag = new DragForce(atm, new IsotropicDrag(area, cd));
  var ad = drag.acceleration(st, drag.getParameters(d));
  var w = itrf.getTransformTo(gcrf, d).getRotationRate();
  var wg = itrf.getTransformTo(gcrf, d).transformVector(w);
  out.println(f[0] + ' ' + hx(ag.getX()) + ' ' + hx(ag.getY()) + ' ' + hx(ag.getZ()) + ' ' + hx(ad.getX()) + ' ' + hx(ad.getY()) + ' ' +
              hx(ad.getZ()) + ' ' + hx(wg.getX()) + ' ' + hx(wg.getY()) + ' ' + hx(wg.getZ()));
  n++;
}
br.close();
out.println('# states ' + n);
out.close();
print('f4_orekit: ' + n + ' states written to ' + OUT);
