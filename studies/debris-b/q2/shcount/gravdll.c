/* gravdll.c - DEBRIS-B Q2: the binary64 spherical-harmonic kernel of
   q2bench.c (grav_body.inc, the same synthetic coefficients and seed) as a
   DLL, so ias15_evals_sh.py can call it from a REBOUND force. */
#include <math.h>
#include <stdint.h>
#define GM_EARTH 398600.4415
#define R_EARTH 6378.1363
#define NA 72
static uint64_t sm_state;
static uint64_t splitmix64(void)
{
    uint64_t z = (sm_state += 0x9E3779B97F4A7C15ULL);
    z = (z ^ (z >> 30)) * 0xBF58476D1CE4E5B9ULL;
    z = (z ^ (z >> 27)) * 0x94D049BB133111EBULL;
    return z ^ (z >> 31);
}
static double urand(void) { return (double)(splitmix64() >> 11) * 0x1p-53; }
static double sgn(void) { return (splitmix64() & 1) ? 1.0 : -1.0; }
static double GCu[NA][NA], GSu[NA][NA];
static void grav_coeffs(int N)
{
    sm_state = 0x5EED000000000000ULL + (uint64_t)N;
    for (int n = 2; n <= N; n++)
        for (int m = 0; m <= n; m++) {
            double kaula = 1e-5 / ((double)n * (double)n);
            double cb = (n == 2 && m == 0) ? -4.841651437908150e-4 : sgn() * kaula * (0.5 + urand());
            double sb = (m == 0) ? 0.0 : sgn() * kaula * (0.5 + urand());
            double lnf = 0.5 * (log(m == 0 ? 1.0 : 2.0) + log(2.0 * n + 1.0) + lgamma(n - m + 1.0) - lgamma(n + m + 1.0));
            double f = exp(lnf);
            GCu[n][m] = cb * f;
            GSu[n][m] = sb * f;
        }
}
#define REAL double
#define SQRT sqrt
#define SFX _d
#include "grav_body.inc"
__declspec(dllexport) int grav_init(int N)
{
    if (N < 2 || N > 70) return -1;
    grav_coeffs(N);
    grav_tables_d(N);
    return 0;
}
__declspec(dllexport) void grav_eval(const double *r, int nmin, int nmax, double *a) { grav_accel_d(r, nmin, nmax, a); }
