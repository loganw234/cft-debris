// DEBRIS-C, M2: written AFTER m2_time.001.log, whose per-repetition thread CPU fractions were well
// below 1 and whose process CPU (12.7 s) was half its wall time. Does this JVM's main thread get a
// whole core on this host? A pure CPU loop, timed over spans of about 2 s, with the thread's own CPU
// time (ThreadMXBean) and the JVM's process CPU time (OperatingSystemMXBean) beside the wall time.
// Asserts nothing; it describes.
var System = java.lang.System;
var MF = java.lang.management.ManagementFactory;
var tmx = MF.getThreadMXBean();
var osx = MF.getOperatingSystemMXBean();
var Arrays = java.util.Arrays;
var src = new (Java.type("double[]"))(2000000);
var rnd = new java.util.Random(1);
for (var i = 0; i < src.length; i++) src[i] = rnd.nextDouble();
for (var r = 0; r < 6; r++) {
  var c0 = tmx.getCurrentThreadCpuTime(), p0 = osx.getProcessCpuTime(), t0 = System.nanoTime();
  var cs = 0.0, n = 0;
  while (System.nanoTime() - t0 < 2.0e9) { var a = Arrays.copyOf(src, src.length); Arrays.sort(a); cs += a[1000]; n++; }
  var t1 = System.nanoTime(), c1 = tmx.getCurrentThreadCpuTime(), p1 = osx.getProcessCpuTime();
  print("span " + r + ": wall " + ((t1 - t0) / 1e9).toFixed(3) + " s, sorts " + n + " (" + ((t1 - t0) / n / 1e6).toFixed(1) +
        " ms each), thread CPU " + ((c1 - c0) / 1e9).toFixed(3) + " s (" + ((c1 - c0) / (t1 - t0)).toFixed(2) +
        "), process CPU " + ((p1 - p0) / 1e9).toFixed(3) + " s, system load " + (osx.getSystemCpuLoad() * 100).toFixed(0) + "%, checksum " + cs);
}
