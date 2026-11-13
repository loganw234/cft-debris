// DEBRIS-C, M1b: Orekit's JPL ephemeris reader on DE421 (no orekit-data; a DirectoryCrawler on the
// DE421 binary's own download directory only). Writes positions and velocities for m1b_check.py:
//  (a) every testpo.421 point inside the binary's coverage whose target and centre are bodies 1..13
//      (Orekit exposes no nutations or librations): target minus centre, ICRF axes, m and m/s;
//      (10,3) and (3,10) use the geocentric Moon directly, as JPL's reader does;
//  (b) geocentric Sun, Moon, Mercury, Venus, Mars, Jupiter and Saturn (GCRF, m) at Lasser et al.'s
//      2,880 epochs, given in GPS time; Orekit converts to the ephemeris' own time scale itself.
// usage: m1b_orekit.js -- <testpo.421> <00orbit_icrf.txt> <out_testpo> <out_bodies>
var TESTPO = arguments[0], ORB = arguments[1], OUT1 = arguments[2], OUT2 = arguments[3];
var File = java.io.File;
var Double = java.lang.Double;
var Files = java.nio.file.Files, Paths = java.nio.file.Paths;
var DataContext = Java.type("org.orekit.data.DataContext");
var DirectoryCrawler = Java.type("org.orekit.data.DirectoryCrawler");
var TimeScalesFactory = Java.type("org.orekit.time.TimeScalesFactory");
var AbsoluteDate = Java.type("org.orekit.time.AbsoluteDate");
var FramesFactory = Java.type("org.orekit.frames.FramesFactory");
var CBF = Java.type("org.orekit.bodies.CelestialBodyFactory");
var DE_DIR = "C:/Users/logan/source/repos/cft-debris-downloads/lnxp1900p2053.421";
var fs = new File(DE_DIR).listFiles();
if (fs.length !== 1 || fs[0].getName() !== "lnxp1900p2053.421") throw "the DE421 directory must hold the binary only";
DataContext.getDefault().getDataProvidersManager().addProvider(new DirectoryCrawler(new File(DE_DIR)));
var tdb = TimeScalesFactory.getTDB(), gps = TimeScalesFactory.getGPS();
var icrf = FramesFactory.getICRF(), gcrf = FramesFactory.getGCRF();
var B = {1: CBF.getMercury(), 2: CBF.getVenus(), 3: CBF.getEarth(), 4: CBF.getMars(), 5: CBF.getJupiter(),
         6: CBF.getSaturn(), 7: CBF.getUranus(), 8: CBF.getNeptune(), 9: CBF.getPluto(), 10: CBF.getMoon(),
         11: CBF.getSun(), 12: CBF.getSolarSystemBarycenter(), 13: CBF.getEarthMoonBarycenter()};
var JD0 = 2414992.5, JD1 = 2469808.5; // the binary's own coverage (its header record)
function hx(v) { return Double.toHexString(v.getX()) + " " + Double.toHexString(v.getY()) + " " + Double.toHexString(v.getZ()); }

var lines = Files.readAllLines(Paths.get(TESTPO));
var out = new java.io.PrintWriter(new java.io.BufferedWriter(new java.io.FileWriter(OUT1)));
var started = false, n = 0, skipped = 0;
for (var i = 0; i < lines.size(); i++) {
  var s = ("" + lines.get(i)).trim();
  if (!started) { if (s === "EOT") started = true; continue; }
  var t = s.split(/\s+/);
  if (t.length < 7) continue;
  var jed = parseFloat(t[2]), tg = parseInt(t[3]), ct = parseInt(t[4]);
  if (jed < JD0 || jed > JD1 || tg > 13 || ct > 13 || ct < 1) { skipped++; continue; }
  var jdInt = Math.floor(jed);               // jed = jdInt + 0.5 exactly in testpo.421
  var date = AbsoluteDate.createJDDate(jdInt, (jed - jdInt) * 86400.0, tdb);
  var p, v;
  if ((tg === 10 && ct === 3) || (tg === 3 && ct === 10)) {
    var pv = B[10].getPVCoordinates(date, gcrf);
    p = pv.getPosition(); v = pv.getVelocity();
    if (tg === 3) { p = p.negate(); v = v.negate(); }
  } else {
    var a = B[tg].getPVCoordinates(date, icrf), b = B[ct].getPVCoordinates(date, icrf);
    p = a.getPosition().subtract(b.getPosition()); v = a.getVelocity().subtract(b.getVelocity());
  }
  out.println(i + " " + hx(p) + " " + hx(v));
  n++;
}
out.close();
print("# testpo points written: " + n + ", skipped (outside coverage, or nutation/libration/centre 0): " + skipped);

var ol = Files.readAllLines(Paths.get(ORB));
var T0 = new AbsoluteDate(2008, 7, 3, 0, 0, 0.0, gps);
var out2 = new java.io.PrintWriter(new java.io.BufferedWriter(new java.io.FileWriter(OUT2)));
var k = 0;
var bodies = [11, 10, 1, 2, 4, 5, 6];
for (var i = 0; i < ol.size(); i++) {
  var s = ("" + ol.get(i)).trim();
  if (s.length === 0 || s.charAt(0) === '#' || s.charAt(0) === 'g') continue;
  var t = s.split(/\s+/);
  if (t.length !== 10) continue;
  // the epoch: GPS MJD; 54650 + k * 30 s, k the row index (asserted against the file's MJD below)
  var date = T0.shiftedBy(30.0 * k);
  var mjd = parseFloat(t[0]);
  if (Math.abs(mjd - (54650.0 + 30.0 * k / 86400.0)) > 1e-9) throw "epoch grid mismatch at row " + k;
  var row = t[0];
  for (var j = 0; j < bodies.length; j++) row += " " + hx(B[bodies[j]].getPosition(date, gcrf));
  out2.println(row);
  k++;
}
out2.close();
print("# Lasser epochs written: " + k + " (Sun, Moon, Mercury, Venus, Mars, Jupiter, Saturn; GCRF, m)");
