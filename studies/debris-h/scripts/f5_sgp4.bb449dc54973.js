// f5_sgp4.js - cft-debris M1 (DEBRIS-F), B3's decoder: Orekit 13.1.9's TLE and TLEPropagator (SGP4/SDP4),
// built from CelesTrak's CSV mean elements in the units Orekit's TLE constructor takes, yielding GCRF positions
// and velocities at requested instants through the same Earth orientation file.
// cft-debris, MIT licence (see LICENSE at the repository root). Written by DEBRIS-F, 2026-11-16.
// Orekit is called through Nashorn, never copied.
//
//   java -cp <jars> jdk.nashorn.tools.Shell f5_sgp4.js -- <mode> <data_dir> <in> <out>
//   mode build: per object line, build the TLE and print its getters, or the reason Orekit refused it
//   mode pv:    per object line then its instant lines, the GCRF position and velocity at each instant
// Input, an object a line: "OBJ key satnum class launchYear launchNumber launchPiece ephType elemNo epochUTC
//   n(rad/s) ndot(rad/s^2) nddot(rad/s^3) e i(rad) argp(rad) raan(rad) M(rad) revNo bstar(1/ER) ninst [plant_dn]"
//   with every real a Java/C99 hex float; then (mode pv) "I k tai_s" lines, tai_s seconds from 2026-10-16T00:00:00
//   TAI (MJD 61329.0 TAI). The TLE constructor's argument order, by reflection (DEBRIS-F's probe):
//   (int satelliteNumber, char classification, int launchYear, int launchNumber, String launchPiece,
//    int ephemerisType, int elementNumber, AbsoluteDate epoch, double meanMotion, double meanMotionFirstDerivative,
//    double meanMotionSecondDerivative, double e, double i, double pa, double raan, double meanAnomaly,
//    int revolutionNumberAtEpoch, double bStar, TimeScale utc).
var args = arguments;
var MODE = args[0], DATA = args[1], IN = args[2], OUT = args[3];
var File = java.io.File;
var DataContext = Java.type('org.orekit.data.DataContext');
var DirectoryCrawler = Java.type('org.orekit.data.DirectoryCrawler');
var FramesFactory = Java.type('org.orekit.frames.FramesFactory');
var IERSConventions = Java.type('org.orekit.utils.IERSConventions');
var TimeScalesFactory = Java.type('org.orekit.time.TimeScalesFactory');
var AbsoluteDate = Java.type('org.orekit.time.AbsoluteDate');
var DateComponents = Java.type('org.orekit.time.DateComponents');
var TimeComponents = Java.type('org.orekit.time.TimeComponents');
var TLE = Java.type('org.orekit.propagation.analytical.tle.TLE');
var TLEPropagator = Java.type('org.orekit.propagation.analytical.tle.TLEPropagator');
var Double = Java.type('java.lang.Double');
var Character = Java.type('java.lang.Character');
var PrintWriter = Java.type('java.io.PrintWriter');
DataContext.getDefault().getDataProvidersManager().addProvider(new DirectoryCrawler(new File(DATA)));
var utc = TimeScalesFactory.getUTC(), tai = TimeScalesFactory.getTAI();
var REF = new AbsoluteDate(new DateComponents(2026, 10, 16), TimeComponents.H00, tai);
function hx(x) { return Double.toHexString(x); }
function px(s) { return Double.parseDouble(s); }
var out = new PrintWriter(OUT);
out.println('# f5_sgp4 ' + MODE + ': java ' + java.lang.System.getProperty('java.version'));
var eop = FramesFactory.getEOPHistory(IERSConventions.IERS_2010, true);
var chk = new AbsoluteDate(new DateComponents(DateComponents.MODIFIED_JULIAN_EPOCH, 61360), TimeComponents.H00, utc);
var u = eop.getUT1MinusUTC(chk);
if (!(Math.abs(u - (-0.0704999)) < 1e-9)) { print('EOP NOT LOADED: UT1-UTC at MJD 61360 = ' + u); java.lang.System.exit(4); }
out.println('# EOP loaded: UT1-UTC at MJD 61360 0h UTC = ' + u + ' (file -0.0704999)');
var gcrf = FramesFactory.getGCRF();
function build(f) {
  // f: tokens of the OBJ line
  var dn = (f.length > 21) ? px(f[21]) : 0.0;
  var t = new TLE(parseInt(f[2]), f[3].charAt(0), parseInt(f[4]), parseInt(f[5]), f[6], parseInt(f[7]), parseInt(f[8]),
                  new AbsoluteDate(f[9], utc), px(f[10]) + dn, px(f[11]), px(f[12]), px(f[13]), px(f[14]), px(f[15]), px(f[16]),
                  px(f[17]), parseInt(f[18]), px(f[19]), utc);
  return t;
}
var br = new java.io.BufferedReader(new java.io.FileReader(IN));
var line, nobj = 0, nfail = 0, ninst = 0, cur = null, prop = null, key = null;
out.println(MODE == 'build' ? '# columns: B key ok satnum n ndot nddot e i argp raan M bstar epoch_tai_s ephType | or F key reason' :
            '# columns: V key k tai_s x y z vx vy vz (GCRF, m, m/s, Java hex)');
while ((line = br.readLine()) !== null) {
  if (line.indexOf('#') == 0 || line.trim().length() == 0) continue;
  var f = line.trim().split(/\s+/);
  if (f[0] == 'OBJ') {
    nobj++;
    key = f[1];
    try {
      cur = build(f);
      if (MODE == 'build') {
        out.println('B ' + key + ' ok ' + cur.getSatelliteNumber() + ' ' + hx(cur.getMeanMotion()) + ' ' + hx(cur.getMeanMotionFirstDerivative()) + ' ' +
                    hx(cur.getMeanMotionSecondDerivative()) + ' ' + hx(cur.getE()) + ' ' + hx(cur.getI()) + ' ' + hx(cur.getPerigeeArgument()) + ' ' +
                    hx(cur.getRaan()) + ' ' + hx(cur.getMeanAnomaly()) + ' ' + hx(cur.getBStar()) + ' ' + hx(cur.getDate().durationFrom(REF)) + ' ' +
                    cur.getEphemerisType());
        // the propagator must also build (SGP4 or SDP4 by the period)
        TLEPropagator.selectExtrapolator(cur);
      } else {
        prop = TLEPropagator.selectExtrapolator(cur);
      }
    } catch (e) {
      nfail++;
      cur = null;
      prop = null;
      out.println('F ' + key + ' ' + String(e).replace(/\s+/g, '_').substring(0, 200));
    }
  } else if (f[0] == 'I' && MODE == 'pv') {
    if (prop == null) continue;
    var d = new AbsoluteDate(REF, px(f[2]));
    var pv = prop.getPVCoordinates(d, gcrf);
    var p = pv.getPosition(), v = pv.getVelocity();
    out.println('V ' + key + ' ' + f[1] + ' ' + f[2] + ' ' + hx(p.getX()) + ' ' + hx(p.getY()) + ' ' + hx(p.getZ()) + ' ' + hx(v.getX()) + ' ' +
                hx(v.getY()) + ' ' + hx(v.getZ()));
    ninst++;
  }
}
br.close();
out.println('# objects ' + nobj + ' refused ' + nfail + ' instants ' + ninst);
out.close();
print('f5_sgp4 ' + MODE + ': objects ' + nobj + ' refused ' + nfail + ' instants ' + ninst);
