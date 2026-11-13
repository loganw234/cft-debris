// DEBRIS-C, M1a: Orekit's HolmesFeatherstoneAttractionModel along Lasser et al.'s TRF orbit.
// Conventions (established before the comparison; see m1a_compare.py's header):
// - coefficients: the de-duplicated copy of the benchmark's EIGEN6-C4.gfc (lead.md 18:07 ruling),
//   read by Orekit's own ICGEM reader through a DirectoryCrawler on the copy's own directory;
// - GM and the reference radius: the file's (provider.getMu(), provider.getAe());
// - degrees: gradient() is "the gradient of the non-central part" and its sums start at
//   n = max(2, m) (READ via WebFetch, the class source at tag 13.1.9 on GitHub), so it covers
//   degrees 2..N, Lasser et al.'s range: nothing is added or subtracted;
// - positions are Earth-fixed, so gradient() takes them directly in the body frame; the frame's
//   orientation does not enter (the field is static: the file has gfc keys only).
// usage: m1a_orekit.js -- <gfc dir> <orbit_itrf.txt> <degree> <out file>
var GFC_DIR = arguments[0], ORB = arguments[1], DEG = parseInt(arguments[2]), OUT = arguments[3];
var File = java.io.File;
var Files = java.nio.file.Files;
var Paths = java.nio.file.Paths;
var Double = java.lang.Double;
var DataContext = Java.type("org.orekit.data.DataContext");
var DirectoryCrawler = Java.type("org.orekit.data.DirectoryCrawler");
var TimeScalesFactory = Java.type("org.orekit.time.TimeScalesFactory");
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

var fs = new File(GFC_DIR).listFiles();
if (fs.length !== 1 || fs[0].getName() !== "EIGEN6-C4.gfc") throw "the gravity directory must hold EIGEN6-C4.gfc only";
DataContext.getDefault().getDataProvidersManager().addProvider(new DirectoryCrawler(new File(GFC_DIR)));
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
var gp = GravityFieldFactory.getNormalizedProvider(DEG, DEG);
var hf = new HolmesFeatherstone(body, gp);
var mu = gp.getMu();
print("# provider: degree " + gp.getMaxDegree() + ", order " + gp.getMaxOrder() + ", mu " + Double.toHexString(mu) + " (" + mu +
      "), ae " + gp.getAe() + ", tide system " + gp.getTideSystem());
print("# loaded: " + DataContext.getDefault().getDataProvidersManager().getLoadedDataNames());
var lines = Files.readAllLines(Paths.get(ORB));
var out = new java.io.PrintWriter(new java.io.BufferedWriter(new java.io.FileWriter(OUT)));
var k = 0;
for (var i = 0; i < lines.size(); i++) {
  var s = ("" + lines.get(i)).trim();
  if (s.length === 0 || s.charAt(0) === '#' || s.charAt(0) === 'g') continue;
  var t = s.split(/\s+/);
  if (t.length !== 10) continue;
  var p = new Vector3D(Double.parseDouble(t[1]), Double.parseDouble(t[2]), Double.parseDouble(t[3]));
  var g = hf.gradient(T0.shiftedBy(30.0 * k), p, mu);
  out.println(t[0] + " " + Double.toHexString(g[0]) + " " + Double.toHexString(g[1]) + " " + Double.toHexString(g[2]));
  k++;
}
out.close();
print("# epochs: " + k + ", degree " + DEG + ", written to " + OUT);
