/* q4prop.c - DEBRIS-D, Q4 (cft-debris, MIT): one LEO object for one day under
 * DEBRIS-C's normalised degree-N field (EIGEN-6C4, degrees 2..N, in an Earth
 * turning uniformly at w), the central term, and drag through the exponential
 * atmosphere of Q2's j2dragrot system (rho0 3.725e-12 kg/m^3 at 400 km, H
 * 58,515 m, co-rotating air, Cd A / (2 m) = 0.011 m^2/kg).
 *
 * Built with -DREAL=double or -DREAL="long double" (x87 extended, 64-bit
 * significand); the kernel is make_q4_kernel.py's copy of m1a_grav.c with
 * double turned into REAL, and every input (coefficients, GM, radius, initial
 * state) is read as a binary64 value, so the two builds integrate the same
 * model from the same state and differ only in their arithmetic.
 *
 *   q4prop <rk4|sv> <h> <nsteps> <N> <drag 0|1> <gfc> x y z vx vy vz
 *     (the state as C99 hex floats). sv is Stormer-Verlet, drift-kick-drift,
 *     and refuses drag (the kick would read the velocities).
 *   prints: final x y z vx vy vz (%.21Le), the force evaluations, and REAL's
 *   significand bits.
 * With -DQ4_DLL it builds instead the two calls REBOUND's driver uses:
 *   int  q4_init(const char *gfc, int N)
 *   void q4_force(double t, const double *y6, int drag, double *a3)  (no central term)
 */
#define __USE_MINGW_ANSI_STDIO 1
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <float.h>
#include <tgmath.h>

#ifndef REAL
#define REAL double
#endif

#include "q4_kernel.inc"

static const REAL TH0 = 0.3, WE = 7.292115e-5;
static const REAL RHO0 = 3.725e-12, R0 = 6778137.0, HS = 58515.0, BC = 0.011;
static int NDEG = 20;
static long nevals = 0;

static int read_field(const char *path, int N)
{
    FILE *f = fopen(path, "r");
    if (!f) return -1;
    char line[512];
    int head = 1;
    double gm = 0, re = 0;
    while (fgets(line, sizeof line, f)) {
        char key[64];
        if (sscanf(line, "%63s", key) != 1) continue;
        if (head) {
            if (!strncmp(key, "end_of_head", 11)) head = 0;
            else if (!strcmp(key, "earth_gravity_constant")) sscanf(line, "%*s %lf", &gm);
            else if (!strcmp(key, "radius")) sscanf(line, "%*s %lf", &re);
            continue;
        }
        if (strcmp(key, "gfc")) continue;
        int n, m;
        double c, s;
        if (sscanf(line, "%*s %d %d %lf %lf", &n, &m, &c, &s) != 4) return -2;
        if (n <= NMAXC && m <= n) { Cb[n][m] = (REAL)c; Sb[n][m] = (REAL)s; }
    }
    fclose(f);
    GM = (REAL)gm;
    RE = (REAL)re;
    NDEG = N;
    tables(N + 1);
    return (gm > 0 && re > 0) ? 0 : -3;
}

/* the acceleration without (central = 0) or with (central = 1) the central term */
static void force(REAL t, const REAL y[6], int drag, int central, REAL a[3])
{
    nevals++;
    REAL th = TH0 + WE * t, c = cos(th), s = sin(th);
    REAL rb[3] = {c * y[0] + s * y[1], -s * y[0] + c * y[1], y[2]}, ab[3];
    grav(rb, 2, NDEG, ab);
    a[0] = c * ab[0] - s * ab[1];
    a[1] = s * ab[0] + c * ab[1];
    a[2] = ab[2];
    REAL r2 = y[0] * y[0] + y[1] * y[1] + y[2] * y[2], r = sqrt(r2);
    if (central) {
        REAL k = -GM / (r2 * r);
        a[0] += k * y[0];
        a[1] += k * y[1];
        a[2] += k * y[2];
    }
    if (drag) {
        REAL rho = RHO0 * exp(-(r - R0) / HS);
        REAL vx = y[3] + WE * y[1], vy = y[4] - WE * y[0], vz = y[5];
        REAL v = sqrt(vx * vx + vy * vy + vz * vz);
        REAL k = -BC * rho * v;
        a[0] += k * vx;
        a[1] += k * vy;
        a[2] += k * vz;
    }
}

#ifdef Q4_DLL
__declspec(dllexport) int q4_init(const char *gfc, int N) { return read_field(gfc, N); }
__declspec(dllexport) void q4_force(double t, const double *y6, int drag, double *a3)
{
    REAL y[6], a[3];
    for (int i = 0; i < 6; i++) y[i] = y6[i];
    force(t, y, drag, 0, a);
    for (int i = 0; i < 3; i++) a3[i] = a[i];
}
#else
static void deriv(REAL t, const REAL y[6], int drag, REAL d[6])
{
    REAL a[3];
    force(t, y, drag, 1, a);
    d[0] = y[3]; d[1] = y[4]; d[2] = y[5];
    d[3] = a[0]; d[4] = a[1]; d[5] = a[2];
}

int main(int argc, char **argv)
{
    if (argc != 13) { fprintf(stderr, "usage: q4prop <rk4|sv> <h> <nsteps> <N> <drag> <gfc> x y z vx vy vz\n"); return 2; }
    const char *method = argv[1];
    REAL h = (REAL)strtod(argv[2], NULL);
    long nsteps = atol(argv[3]);
    int N = atoi(argv[4]), drag = atoi(argv[5]);
    if (read_field(argv[6], N)) { fprintf(stderr, "q4prop: cannot read %s\n", argv[6]); return 2; }
    REAL y[6];
    for (int i = 0; i < 6; i++) y[i] = (REAL)strtod(argv[7 + i], NULL);
    if (!strcmp(method, "rk4")) {
        REAL k1[6], k2[6], k3[6], k4[6], tmp[6];
        for (long n = 0; n < nsteps; n++) {
            REAL t = (REAL)n * h;
            deriv(t, y, drag, k1);
            for (int i = 0; i < 6; i++) tmp[i] = y[i] + h / 2 * k1[i];
            deriv(t + h / 2, tmp, drag, k2);
            for (int i = 0; i < 6; i++) tmp[i] = y[i] + h / 2 * k2[i];
            deriv(t + h / 2, tmp, drag, k3);
            for (int i = 0; i < 6; i++) tmp[i] = y[i] + h * k3[i];
            deriv(t + h, tmp, drag, k4);
            for (int i = 0; i < 6; i++) y[i] = y[i] + h / 6 * (k1[i] + 2 * k2[i] + 2 * k3[i] + k4[i]);
        }
    } else if (!strcmp(method, "sv")) {
        if (drag) { fprintf(stderr, "q4prop: refused: stormer-verlet with drag is not separable\n"); return 3; }
        REAL a[3], q1[6];
        for (long n = 0; n < nsteps; n++) {
            REAL t = (REAL)n * h;
            for (int i = 0; i < 3; i++) q1[i] = y[i] + h / 2 * y[3 + i];
            for (int i = 3; i < 6; i++) q1[i] = y[i];
            force(t + h / 2, q1, 0, 1, a);
            for (int i = 0; i < 3; i++) y[3 + i] = y[3 + i] + h * a[i];
            for (int i = 0; i < 3; i++) y[i] = q1[i] + h / 2 * y[3 + i];
        }
    } else { fprintf(stderr, "q4prop: unknown method\n"); return 2; }
    printf("final");
    for (int i = 0; i < 6; i++) printf(" %.21Le", (long double)y[i]);
    printf("\nevals %ld\nmant_dig %d\n", nevals, (int)(sizeof(REAL) == sizeof(double) ? DBL_MANT_DIG : LDBL_MANT_DIG));
    return 0;
}
#endif
