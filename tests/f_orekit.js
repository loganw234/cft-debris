// f_orekit.js - cft-debris M1 (DEBRIS-F): Orekit 13.1.9 as the referee for the time scales (F2) and the
// Earth's orientation (F3), at instants given as TAI seconds from 2026-10-16T00:00:00 TAI (MJD 61329.0 TAI).
// cft-debris, MIT licence (see LICENSE at the repository root). Written by DEBRIS-F, 2026-11-16.
// Orekit is called through Nashorn, never copied. Its data come from one directory of copies of the approved
// files (finals2000A.daily, tai-utc.dat), through a DirectoryCrawler; nothing is fetched.
//
//   java -cp <jars> jdk.nashorn.tools.Shell f_orekit.js -- <mode> <data_dir> <in> <out>
//     mode frames: per instant, the GCRF <- ITRF rotation (IERS 2010, simple EOP) as a row-major matrix,
//                  the columns being ITRF's unit vectors transformed into GCRF; then Orekit's xp, yp, UT1-UTC, dX, dY
//     mode times:  per instant, TAI-UTC, TT-TAI, TDB-TT and UT1-UTC as Orekit gives them
//     mode leaps:  per line "Y M D h m s" (UTC components), TAI-UTC there, from Orekit's UTC (no EOP needed)
// Every frames or times run asserts first that the Earth orientation data loaded: UT1-UTC at 2026-11-16 00:00
// UTC (MJD 61360) must equal the file's -0.0704999 s to 1e-9 s; without the file Orekit gives 0 there.
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
var Vector3D = Java.type('org.hipparchus.geometry.euclidean.threed.Vector3D');
var Double = Java.type('java.lang.Double');
var PrintWriter = Java.type('java.io.PrintWriter');
DataContext.getDefault().getDataProvidersManager().addProvider(new DirectoryCrawler(new File(DATA)));
var tai = TimeScalesFactory.getTAI(), utc = TimeScalesFactory.getUTC(), tt = TimeScalesFactory.getTT(), tdb = TimeScalesFactory.getTDB();
var REF = new AbsoluteDate(new DateComponents(2026, 10, 16), TimeComponents.H00, tai);
function hx(x) { return Double.toHexString(x); }
var out = new PrintWriter(OUT);
out.println('# f_orekit ' + MODE + ': java ' + java.lang.System.getProperty('java.version') + '; reference epoch ' + REF.toString(tai) + ' TAI');
var eop = null;
if (MODE == 'frames' || MODE == 'times') {
  eop = FramesFactory.getEOPHistory(IERSConventions.IERS_2010, true);
  var chk = new AbsoluteDate(new DateComponents(DateComponents.MODIFIED_JULIAN_EPOCH, 61360), TimeComponents.H00, utc);
  var u = eop.getUT1MinusUTC(chk);
  if (!(Math.abs(u - (-0.0704999)) < 1e-9)) { print('EOP NOT LOADED: UT1-UTC at MJD 61360 = ' + u); java.lang.System.exit(4); }
  out.println('# EOP loaded: UT1-UTC at MJD 61360 0h UTC = ' + u + ' (file -0.0704999); EOP ' + eop.getStartDate().toString(utc) +
              ' to ' + eop.getEndDate().toString(utc) + '; interpolation degree ' + eop.getInterpolationDegree() + '; simple EOP ' + eop.isSimpleEop());
}
var br = new java.io.BufferedReader(new java.io.FileReader(IN));
var line, n = 0;
var MAS = Math.PI / (180 * 3600 * 1000);
if (MODE == 'frames') {
  var gcrf = FramesFactory.getGCRF(), itrf = FramesFactory.getITRF(IERSConventions.IERS_2010, true);
  out.println('# frames: GCRF <- ITRF (IERS_2010, simple EOP); columns: tai_s M00 M01 M02 M10 M11 M12 M20 M21 M22 xp yp ut1_utc dX dY (rad, s; Java hex)');
  while ((line = br.readLine()) !== null) {
    if (line.indexOf('#') == 0 || line.trim().length() == 0) continue;
    var s = Double.parseDouble(line.trim().split(/\s+/)[0]);
    var d = new AbsoluteDate(REF, s);
    var tr = itrf.getTransformTo(gcrf, d);
    var c0 = tr.transformVector(Vector3D.PLUS_I), c1 = tr.transformVector(Vector3D.PLUS_J), c2 = tr.transformVector(Vector3D.PLUS_K);
    var pc = eop.getPoleCorrection(d), nu = eop.getNonRotatinOriginNutationCorrection(d);
    out.println(hx(s) + ' ' + hx(c0.getX()) + ' ' + hx(c1.getX()) + ' ' + hx(c2.getX()) + ' ' + hx(c0.getY()) + ' ' + hx(c1.getY()) + ' ' +
                hx(c2.getY()) + ' ' + hx(c0.getZ()) + ' ' + hx(c1.getZ()) + ' ' + hx(c2.getZ()) + ' ' + hx(pc.getXp()) + ' ' + hx(pc.getYp()) +
                ' ' + hx(eop.getUT1MinusUTC(d)) + ' ' + hx(nu[0]) + ' ' + hx(nu[1]));
    n++;
  }
} else if (MODE == 'times') {
  out.println('# times: columns tai_s tai_minus_utc tt_minus_tai tdb_minus_tt ut1_minus_utc (s; Java hex)');
  while ((line = br.readLine()) !== null) {
    if (line.indexOf('#') == 0 || line.trim().length() == 0) continue;
    var s = Double.parseDouble(line.trim().split(/\s+/)[0]);
    var d = new AbsoluteDate(REF, s);
    var taiutc = -utc.offsetFromTAI(d).toDouble();
    var tttai = tt.offsetFromTAI(d).toDouble();
    var tdbtt = tdb.offsetFromTAI(d).toDouble() - tttai;
    out.println(hx(s) + ' ' + hx(taiutc) + ' ' + hx(tttai) + ' ' + hx(tdbtt) + ' ' + hx(eop.getUT1MinusUTC(d)));
    n++;
  }
} else if (MODE == 'leaps') {
  out.println('# leaps: columns Y M D h m s tai_minus_utc (Orekit UTC from the crawled tai-utc.dat; Java hex)');
  while ((line = br.readLine()) !== null) {
    if (line.indexOf('#') == 0 || line.trim().length() == 0) continue;
    var f = line.trim().split(/\s+/);
    var d = new AbsoluteDate(new DateComponents(parseInt(f[0]), parseInt(f[1]), parseInt(f[2])),
                             new TimeComponents(parseInt(f[3]), parseInt(f[4]), Double.parseDouble(f[5])), utc);
    out.println(line.trim() + ' ' + hx(-utc.offsetFromTAI(d).toDouble()));
    n++;
  }
}
br.close();
out.println('# instants ' + n);
out.close();
print('f_orekit ' + MODE + ': ' + n + ' instants written to ' + OUT);
