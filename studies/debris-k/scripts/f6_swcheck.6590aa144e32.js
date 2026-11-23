// f6_swcheck.js - cft-debris M1 (DEBRIS-F): the two-fill check of the lead's ruling - NRLMSISE-00's inputs as Orekit
// 13.1.9's own CssiSpaceWeatherData gives them from one copy of SW-Last5Years.txt, at every hour of a span.
// cft-debris, MIT licence (see LICENSE at the repository root). Written by DEBRIS-F, 2026-11-16. Orekit is called
// through Nashorn, never copied.
//
//   java -cp <jars> jdk.nashorn.tools.Shell f6_swcheck.js -- <dir holding the copy and tai-utc.dat> <out> <start> <hours>
// start: an ISO UTC date-time; writes per hour: the date, getDailyFlux, getAverageFlux and getAp's seven (Java hex).
var args = arguments;
var DIR = args[0], OUT = args[1], START = args[2], HOURS = parseInt(args[3]);
var File = java.io.File;
var DataContext = Java.type('org.orekit.data.DataContext');
var DirectoryCrawler = Java.type('org.orekit.data.DirectoryCrawler');
var TimeScalesFactory = Java.type('org.orekit.time.TimeScalesFactory');
var AbsoluteDate = Java.type('org.orekit.time.AbsoluteDate');
var Cssi = Java.type('org.orekit.models.earth.atmosphere.data.CssiSpaceWeatherData');
var Double = Java.type('java.lang.Double');
var PrintWriter = Java.type('java.io.PrintWriter');
DataContext.getDefault().getDataProvidersManager().addProvider(new DirectoryCrawler(new File(DIR)));
var utc = TimeScalesFactory.getUTC();
var sw = new Cssi(Cssi.DEFAULT_SUPPORTED_NAMES);
var t0 = new AbsoluteDate(START, utc);
var out = new PrintWriter(OUT);
out.println('# f6_swcheck: ' + DIR + '; supported names ' + Cssi.DEFAULT_SUPPORTED_NAMES + '; data ' + sw.getMinDate().toString(utc) + ' to ' + sw.getMaxDate().toString(utc));
for (var h = 0; h <= HOURS; h++) {
  var d = t0.shiftedBy(3600.0 * h);
  var ap = sw.getAp(d);
  var s = d.toString(utc) + ' ' + Double.toHexString(sw.getDailyFlux(d)) + ' ' + Double.toHexString(sw.getAverageFlux(d));
  for (var i = 0; i < ap.length; i++) s += ' ' + Double.toHexString(ap[i]);
  out.println(s);
}
out.close();
print('f6_swcheck: ' + (HOURS + 1) + ' hours from ' + START);
