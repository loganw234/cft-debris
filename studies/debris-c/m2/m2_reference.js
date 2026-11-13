// DEBRIS-C, M2, control 2 ("a fast wrong answer is still wrong"): Orekit's NRLMSISE00 held to
// published reference values.
// REFERENCE (READ via WebFetch, https://pynrlmsise00.readthedocs.io/en/stable/README.html, the
// "C model interface" example, which wraps the C version of NRLMSISE-00):
//   gtd7(2009, 172, 29000, 400, 60, -70, 16, 150, 150, 4) ->
//   d = [666517.690495152, 113880555.97522168, 19982109.255734544, 402276.3585712511, 3557.464994515886,
//        4.074713532757222e-15, 34753.12399717142, 4095913.2682930017, 26672.73209335869]
//   (d[5] total mass density in g/cm^3; the others number densities in cm^-3: He, O, N2, O2, Ar, -, H,
//   N, anomalous O), t = [1250.5399435607994, 1241.4161300191206] K.
//   Inputs: day of year 172, 29000 s UT, 400 km, geodetic latitude 60 deg, longitude -70 deg, local
//   solar time 16 h, F10.7A 150, F10.7 150, daily Ap 4.
// HOW: as Orekit's own legacy test does (READ via WebFetch, NRLMSISE00Test.java at tag 13.1.9 on
//   GitHub): the package-private NRLMSISE00$Output is built by reflection with those inputs and
//   ap = {4, 100, 100, 100, 100, 100, 100} (switch 9 = 1 uses the daily value only), and gtd7(400)
//   is called. Orekit's default switches are all 1, so switch 0 = 1 gives SI units: number
//   densities in m^-3 (x 1e6) and mass density in kg/m^3 (x 1e3).
// CRITERION (stated before the run, asserted): each of the nine densities within a relative 1e-10 of
//   the reference. Basis: the reference is a binary64 run of the same algorithm printed to 16 or 17
//   digits; an independent binary64 port is expected within ~1e-14 relative; a wrong coefficient or
//   term moves a density by far more than 1e-10.
// LIMIT: this exercises the model's core (Output.gtd7), not the public getDensity path M2 times,
//   which adds the geodetic conversion, the Sun's position and the local solar time.
var NRLMSISE00 = Java.type("org.orekit.models.earth.atmosphere.NRLMSISE00");
var NRLIn = Java.type("org.orekit.models.earth.atmosphere.NRLMSISE00InputParameters");
var OneAxisEllipsoid = Java.type("org.orekit.bodies.OneAxisEllipsoid");
var Constants = Java.type("org.orekit.utils.Constants");
var FramesFactory = Java.type("org.orekit.frames.FramesFactory");
var TimeScalesFactory = Java.type("org.orekit.time.TimeScalesFactory");
var UTCTAIOffsetsLoader = Java.type("org.orekit.time.UTCTAIOffsetsLoader");
var OffsetModel = Java.type("org.orekit.time.OffsetModel");
var DateComponents = Java.type("org.orekit.time.DateComponents");
var ArrayList = Java.type("java.util.ArrayList");
var Integer = java.lang.Integer, Double = java.lang.Double;
var REL = 1e-10;
var REF = [666517.690495152, 113880555.97522168, 19982109.255734544, 402276.3585712511, 3557.464994515886,
           4.074713532757222e-15, 34753.12399717142, 4095913.2682930017, 26672.73209335869];
var SCALE = [1e6, 1e6, 1e6, 1e6, 1e6, 1e3, 1e6, 1e6, 1e6];
var NAMES = ["He", "O", "N2", "O2", "Ar", "total mass", "H", "N", "anomalous O"];
var Loader = Java.extend(UTCTAIOffsetsLoader);
TimeScalesFactory.addUTCTAIOffsetsLoader(new Loader({ loadOffsets: function () {
  var l = new ArrayList(); l.add(new OffsetModel(new DateComponents(2006, 1, 1), 33)); return l; } }));
var utc = TimeScalesFactory.getUTC();
var earth = new OneAxisEllipsoid(Constants.WGS84_EARTH_EQUATORIAL_RADIUS, Constants.WGS84_EARTH_FLATTENING, FramesFactory.getGCRF());
var atm = new NRLMSISE00(null, null, earth, utc);
var OutCls = java.lang.Class.forName("org.orekit.models.earth.atmosphere.NRLMSISE00$Output");
var D = Double.TYPE;
var ctor = OutCls.getDeclaredConstructor(NRLMSISE00.class, Integer.TYPE, D, D, D, D, D, D, Java.type("double[]").class);
ctor.setAccessible(true);
var ap = Java.to([4.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0], "double[]");
var out = ctor.newInstance(atm, 172, 29000.0, 60.0, -70.0, 16.0, 150.0, 150.0, ap);
var gtd7 = OutCls.getDeclaredMethod("gtd7", D); gtd7.setAccessible(true);
var getD = OutCls.getDeclaredMethod("getDensity", Integer.TYPE); getD.setAccessible(true);
gtd7.invoke(out, 400.0);
var ok = true;
print("# control 2: NRLMSISE00 core vs the published reference; criterion: relative difference < " + REL + " for all nine densities");
for (var i = 0; i < 9; i++) {
  var got = getD.invoke(out, Integer.valueOf(i | 0)); // version 2: an explicit Integer (version 1 failed at i = 1, m2_reference.001.log)
  var want = REF[i] * SCALE[i];
  var rel = Math.abs(got - want) / Math.abs(want);
  var pass = rel < REL;
  ok = ok && pass;
  print((pass ? "PASS " : "FAIL ") + "d[" + i + "] " + NAMES[i] + ": Orekit " + got + " reference " + want + " relative difference " + rel.toExponential(3));
}
// the temperatures, printed for the record (not asserted: the getter is not part of the declared API)
var fs = OutCls.getDeclaredFields();
for (var i = 0; i < fs.length; i++) {
  if (fs[i].getName().toLowerCase().indexOf("temp") >= 0) {
    fs[i].setAccessible(true);
    var v = fs[i].get(out);
    print("# field " + fs[i].getName() + ": " + (v !== null && v.length !== undefined ? java.util.Arrays.toString(v) : v) + " (reference t = [1250.5399435607994, 1241.4161300191206])");
  }
}
print("# control 2 " + (ok ? "PASS" : "FAIL"));
if (!ok) exit(1);
