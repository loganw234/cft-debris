// k_orekit_fit.js - cft-debris (DEBRIS-K), the pilot's comparator (C): Orekit 13.1.9 fitted on its own to (R)'s
// pseudo-observations, then propagated to each of the object's references with the same forces.
// cft-debris, MIT licence (see LICENSE at the repository root). Copied by DEBRIS-K, 2026-11-23, from DEBRIS-F's
// tests/f6_orekit_fit.js (cft-debris's own, MIT). What changed: an object carries several targets ("T k tai" lines
// after its observations, ascending), and the fitted propagator is propagated to each in turn, one "C" line each; the
// OBJ line drops tai1 and adds the count of targets. The model, the estimator and the CPU limit are DEBRIS-F's.
// Orekit is called through Nashorn, never copied.
//
//   java -cp <jars> jdk.nashorn.tools.Shell k_orekit_fit.js -- <in> <out> <data_dir> <gfc_dir> <de421_dir> <cpu_limit_s>
// in: per object "OBJ key tai0 x y z vx vy vz nobs ntarget" (the SGP4 state at the span's start, GCRF), then
//     "O j tai x y z" lines, then "T k tai" lines; tai seconds from 2026-10-16T00:00:00 TAI.
// The model: Holmes-Featherstone 20x20 from the de-duplicated EIGEN6-C4.gfc copy on the ITRF (IERS 2010, simple EOP);
// the Sun and the Moon as point masses from DE421; drag from NRLMSISE00 with CelesTrak's SW-Last5Years.txt (CSSI
// format, through Orekit's own loader from a normalised copy: see below) on the WGS84 ellipsoid, IsotropicDrag(area 0.01 m^2, Cd estimated from 2.0) on a mass of 1 kg, so that
// Cd A/(2m) starts at M1's bc of 0.01 m^2/kg; radiation pressure with Orekit's conical shadow on a sphere of
// 6378136.3 m, IsotropicRadiationSingleCoefficient(0.01 m^2, Cr 1.0): cram = 0.01 m^2/kg as M1's.
// The estimator: BatchLSEstimator with Gauss-Newton, Position measurements (sigma 1 m, weight 1), the Cartesian
// state and the drag coefficient estimated, at most 10 iterations, parameters convergence threshold 0.1 (with the
// position scale of 1 m); Dormand-Prince 8(5,3) with steps 0.001 to 300 s and a position tolerance of 1 m.
// It stops starting new objects once the JVM's process CPU time reaches cpu_limit_s.
var args = arguments;
var IN = args[0], OUT = args[1], DATA = args[2], GFC = args[3], DE = args[4], LIMIT = parseFloat(args[5]);
var File = java.io.File;
var DataContext = Java.type('org.orekit.data.DataContext');
var DirectoryCrawler = Java.type('org.orekit.data.DirectoryCrawler');
var FramesFactory = Java.type('org.orekit.frames.FramesFactory');
var IERSConventions = Java.type('org.orekit.utils.IERSConventions');
var Constants = Java.type('org.orekit.utils.Constants');
var TimeScalesFactory = Java.type('org.orekit.time.TimeScalesFactory');
var AbsoluteDate = Java.type('org.orekit.time.AbsoluteDate');
var DateComponents = Java.type('org.orekit.time.DateComponents');
var TimeComponents = Java.type('org.orekit.time.TimeComponents');
var Vector3D = Java.type('org.hipparchus.geometry.euclidean.threed.Vector3D');
var GravityFieldFactory = Java.type('org.orekit.forces.gravity.potential.GravityFieldFactory');
var HolmesFeatherstone = Java.type('org.orekit.forces.gravity.HolmesFeatherstoneAttractionModel');
var ThirdBodyAttraction = Java.type('org.orekit.forces.gravity.ThirdBodyAttraction');
var CelestialBodyFactory = Java.type('org.orekit.bodies.CelestialBodyFactory');
var OneAxisEllipsoid = Java.type('org.orekit.bodies.OneAxisEllipsoid');
var NRLMSISE00 = Java.type('org.orekit.models.earth.atmosphere.NRLMSISE00');
var Cssi = Java.type('org.orekit.models.earth.atmosphere.data.CssiSpaceWeatherData');
var DragForce = Java.type('org.orekit.forces.drag.DragForce');
var IsotropicDrag = Java.type('org.orekit.forces.drag.IsotropicDrag');
var SolarRadiationPressure = Java.type('org.orekit.forces.radiation.SolarRadiationPressure');
var IsoRad = Java.type('org.orekit.forces.radiation.IsotropicRadiationSingleCoefficient');
var CartesianOrbit = Java.type('org.orekit.orbits.CartesianOrbit');
var PositionAngleType = Java.type('org.orekit.orbits.PositionAngleType');
var PVCoordinates = Java.type('org.orekit.utils.PVCoordinates');
var NumericalPropagatorBuilder = Java.type('org.orekit.propagation.conversion.NumericalPropagatorBuilder');
var DP853Builder = Java.type('org.orekit.propagation.conversion.DormandPrince853IntegratorBuilder');
var BatchLSEstimator = Java.type('org.orekit.estimation.leastsquares.BatchLSEstimator');
var GaussNewtonOptimizer = Java.type('org.hipparchus.optim.nonlinear.vector.leastsquares.GaussNewtonOptimizer');
var Position = Java.type('org.orekit.estimation.measurements.Position');
var ObservableSatellite = Java.type('org.orekit.estimation.measurements.ObservableSatellite');
var ManagementFactory = Java.type('java.lang.management.ManagementFactory');
var Double = Java.type('java.lang.Double');
var PrintWriter = Java.type('java.io.PrintWriter');
function hx(x) { return Double.toHexString(x); }
function px(s) { return Double.parseDouble(s); }
var dpm = DataContext.getDefault().getDataProvidersManager();
dpm.addProvider(new DirectoryCrawler(new File(DATA)));
dpm.addProvider(new DirectoryCrawler(new File(GFC)));
dpm.addProvider(new DirectoryCrawler(new File(DE)));
var utc = TimeScalesFactory.getUTC(), tai = TimeScalesFactory.getTAI();
var REF = new AbsoluteDate(new DateComponents(2026, 10, 16), TimeComponents.H00, tai);
var eop = FramesFactory.getEOPHistory(IERSConventions.IERS_2010, true);
var chk = new AbsoluteDate(new DateComponents(DateComponents.MODIFIED_JULIAN_EPOCH, 61360), TimeComponents.H00, utc);
var u = eop.getUT1MinusUTC(chk);
if (!(Math.abs(u - (-0.0704999)) < 1e-9)) { print('EOP NOT LOADED: UT1-UTC at MJD 61360 = ' + u); java.lang.System.exit(4); }
var gcrf = FramesFactory.getGCRF(), itrf = FramesFactory.getITRF(IERSConventions.IERS_2010, true);
var gp = GravityFieldFactory.getNormalizedProvider(20, 20);
var sun = CelestialBodyFactory.getSun(), moon = CelestialBodyFactory.getMoon();
var wgs = new OneAxisEllipsoid(Constants.WGS84_EARTH_EQUATORIAL_RADIUS, Constants.WGS84_EARTH_FLATTENING, itrf);
var sphere = new OneAxisEllipsoid(6378136.3, 0.0, itrf);
// NRLMSISE-00's inputs through Orekit's own CssiSpaceWeatherData, from the data folder given, which holds the lead-approved
// copy of CelesTrak's SW-Last5Years.txt normalised in three ways (tests/f6_swcopy.py --stage3; DEBRIS-F's ledger): Orekit
// 13.1.9's loader refuses the file as served.
var sw = new Cssi(Cssi.DEFAULT_SUPPORTED_NAMES);
var atm = new NRLMSISE00(sw, sun, wgs, utc);
var osb = ManagementFactory.getOperatingSystemMXBean();
function cpu() { return osb.getProcessCpuTime() / 1e9; }
var out = new PrintWriter(OUT);
out.println('# f6_orekit_fit: java ' + java.lang.System.getProperty('java.version') + '; EOP loaded (UT1-UTC at MJD 61360 = ' + u + '); mu ' + gp.getMu() +
            '; space weather: Orekit CssiSpaceWeatherData from ' + DATA + ', ' + sw.getMinDate().toString(utc) + ' to ' + sw.getMaxDate().toString(utc) + '; CPU limit ' + LIMIT + ' s');
out.println('# columns: C key k x y z (GCRF at target k, m, Java hex) iterations cd_fitted rms_m | X key reason');
var br = new java.io.BufferedReader(new java.io.FileReader(IN));
var line, cur = null, obs = [], tgt = [], nfit = 0, stopped = false;
function finish() {
  if (cur == null) return;
  if (cpu() >= LIMIT) { stopped = true; cur = null; obs = []; tgt = []; return; }
  try {
    var d0 = new AbsoluteDate(REF, px(cur[2]));
    var orbit = new CartesianOrbit(new PVCoordinates(new Vector3D(px(cur[3]), px(cur[4]), px(cur[5])), new Vector3D(px(cur[6]), px(cur[7]), px(cur[8]))), gcrf, d0, gp.getMu());
    var b = new NumericalPropagatorBuilder(orbit, new DP853Builder(0.001, 300.0, 1.0), PositionAngleType.MEAN, 1.0);
    b.setMass(1.0);
    b.addForceModel(new HolmesFeatherstone(itrf, gp));
    b.addForceModel(new ThirdBodyAttraction(sun));
    b.addForceModel(new ThirdBodyAttraction(moon));
    b.addForceModel(new DragForce(atm, new IsotropicDrag(0.01, 2.0)));
    b.addForceModel(new SolarRadiationPressure(sun, sphere, new IsoRad(0.01, 1.0)));
    var drv = b.getPropagationParametersDrivers().getDrivers();
    for (var i = 0; i < drv.size(); i++) if (drv.get(i).getName() == 'drag coefficient') drv.get(i).setSelected(true);
    var est = new BatchLSEstimator(new GaussNewtonOptimizer(), b);
    est.setParametersConvergenceThreshold(0.1);
    est.setMaxIterations(10);
    est.setMaxEvaluations(20);
    var sat = new ObservableSatellite(0);
    for (var j = 0; j < obs.length; j++) est.addMeasurement(new Position(new AbsoluteDate(REF, px(obs[j][2])), new Vector3D(px(obs[j][3]), px(obs[j][4]), px(obs[j][5])), 1.0, 1.0, sat));
    var props = est.estimate();
    var cd = NaN;
    var ed = est.getPropagatorParametersDrivers(true).getDrivers();
    for (var i = 0; i < ed.size(); i++) if (ed.get(i).getName() == 'drag coefficient') cd = ed.get(i).getValue();
    if (tgt.length != parseInt(cur[10])) throw 'targets ' + tgt.length + ' of ' + cur[10];
    for (var q = 0; q < tgt.length; q++) {
      var p = props[0].propagate(new AbsoluteDate(REF, px(tgt[q][2]))).getPVCoordinates(gcrf).getPosition();
      out.println('C ' + cur[1] + ' ' + tgt[q][1] + ' ' + hx(p.getX()) + ' ' + hx(p.getY()) + ' ' + hx(p.getZ()) + ' ' + est.getIterationsCount() + ' ' + hx(cd) + ' ' + hx(est.getOptimum().getRMS()));
    }
    nfit++;
  } catch (e) {
    out.println('X ' + cur[1] + ' ' + String(e).replace(/\s+/g, '_').substring(0, 200));
  }
  out.flush();
  cur = null;
  obs = [];
  tgt = [];
}
while ((line = br.readLine()) !== null) {
  if (line.indexOf('#') == 0 || line.trim().length() == 0) continue;
  var f = line.trim().split(/\s+/);
  if (f[0] == 'OBJ') { finish(); if (!stopped) cur = f; }
  else if (f[0] == 'O' && cur != null) obs.push(f);
  else if (f[0] == 'T' && cur != null) tgt.push(f);
}
finish();
br.close();
out.println('# fitted ' + nfit + (stopped ? ' (stopped early at the CPU limit)' : '') + '; JVM process CPU ' + cpu().toFixed(1) + ' s');
out.close();
print('f6_orekit_fit: fitted ' + nfit + (stopped ? ' (stopped early)' : ''));
