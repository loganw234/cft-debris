/* q2bench.c - DEBRIS-B, Q2: the cost of a real force evaluation at binary64.

   Kernels (synthetic coefficients in the real models' magnitude ranges,
   drawn from a fixed-seed splitmix64; no zeros, no subnormals):
     grav N        spherical-harmonic gravity to degree and order N
                   (grav_body.inc), Earth-fixed position in, km/s^2 out
     gravq N       the same code at __float128 (libquadmath), for Q3's price
     cheb 0        Chebyshev positions of the Moon (geocentric) and the Sun
                   (geocentric = Sun - EMB + Moon/(1+EMRAT)), DE-like layout
     frame_full 0  GCRS -> ITRS: the CIP X, Y and s+XY/2 series term by term
                   (IERS 2010 Tables 5.2a, 5.2b, 5.2d term counts), the Earth
                   rotation angle, polar motion, the matrix, applied to r
     frame_interp S  the same transformation with X, Y, s interpolated from
                   nodes S seconds apart (6-point Lagrange); ERA exact;
                   xp, yp, dUT1 linear in a daily table
     atmos K       exponential atmosphere (28 bands) and drag, K objects a call
     srp SET       cannonball radiation pressure with a conical shadow;
                   SET 0 = 1024 points round a LEO orbit, SET 1 = penumbra only

   Modes:
     q2bench time <kernel> <param> <ncall> <reps>
         prints one line per repetition (wall ns/call, thread-CPU ns/call,
         thread cycles/call, host load % during the repetition) and the
         checksum, into which every output component of every call is folded.
     q2bench check <kernel> <param>
         prints the inputs, the synthetic coefficients and the outputs as hex
         floats, for q2_check.py's independent evaluation.
     q2bench count <kernel> <param>
         prints the operation count per call, from the loop structure.

   Build (the C rule of the plan: mingw64 first on PATH):
     gcc -O2 -o q2bench.exe q2bench.c -lquadmath
     gcc -O2 -DNO_FORCE -o q2bench_noforce.exe q2bench.c -lquadmath
   In the NO_FORCE build every kernel call in the timed loops is compiled out:
   the first negative control. */
#define _USE_MATH_DEFINES
#include <windows.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <math.h>
#include <quadmath.h>

#ifdef NO_FORCE
#define CALL(stmt) ((void)0)
#define VARIANT "no-force"
#else
#define CALL(stmt) stmt
#define VARIANT "force"
#endif

#define GM_EARTH 398600.4415   /* km^3/s^2 */
#define R_EARTH 6378.1363      /* km */
#define NA 72                  /* coefficient arrays: degree <= 70 */

/* ------------------------------------------------------------------ PRNG */
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

/* -------------------------------------------------------------- gravity */
static double GCu[NA][NA], GSu[NA][NA]; /* unnormalised, from normalised draws */
static double GCbar[NA][NA], GSbar[NA][NA];

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
            GCbar[n][m] = cb;
            GSbar[n][m] = sb;
            GCu[n][m] = cb * f;
            GSu[n][m] = sb * f;
        }
}

#define REAL double
#define SQRT sqrt
#define SFX _d
#include "grav_body.inc"
#undef REAL
#undef SQRT
#undef SFX
#define REAL __float128
#define SQRT sqrtq
#define SFX _q
#include "grav_body.inc"
#undef REAL
#undef SQRT
#undef SFX

static double grav_flops(int nmin, int nmax)
{
    long L = nmax + 1, n0 = nmin < 2 ? 2 : nmin;
    long tess = 0;
    for (long n = n0; n <= nmax; n++) tess += n;
    double f = 13 + 2 + 2 + 1;              /* setup: mul, add, div, sqrt */
    f += 5.0 * (L - 1) + 8.0 * L + 3.0 * (L - 1) + 8.0 * (L - 1) * (L - 2) / 2.0;
    f += 7.0 * (nmax - n0 + 1) + 28.0 * tess;
    if (nmin == 0) f += 3;
    f += 5;
    return f;
}

/* positions: 1024 points on three orbits (LEO 400 km i 51.6, LEO 800 km
   i 98.6, MEO 20,200 km i 55), rotated arbitrarily: Earth-fixed inputs */
#define NPOS 1024
static double POS[NPOS][3], VEL[NPOS][3];
static void make_positions(void)
{
    sm_state = 0xB0B0000000000001ULL;
    for (int i = 0; i < NPOS; i++) {
        double a, inc;
        int kind = i % 3;
        if (kind == 0) { a = 6778.137; inc = 51.6; }
        else if (kind == 1) { a = 7178.137; inc = 98.6; }
        else { a = 26560.0; inc = 55.0; }
        inc *= M_PI / 180.0;
        double node = 2 * M_PI * urand(), u = 2 * M_PI * urand();
        double v = sqrt(GM_EARTH / a);
        double cu = cos(u), su = sin(u), cn = cos(node), sn = sin(node), ci = cos(inc), si = sin(inc);
        POS[i][0] = a * (cn * cu - sn * su * ci);
        POS[i][1] = a * (sn * cu + cn * su * ci);
        POS[i][2] = a * (su * si);
        VEL[i][0] = v * (-cn * su - sn * cu * ci);
        VEL[i][1] = v * (-sn * su + cn * cu * ci);
        VEL[i][2] = v * (cu * si);
    }
}

/* ------------------------------------------------------------ Chebyshev */
typedef struct { const char *name; int ncoef, nsub, nrec; double rec_len; double *c; } ChebBody;
static ChebBody MOON = {"moon", 13, 8, 64, 32 * 86400.0, 0};
static ChebBody SUN = {"sun", 11, 2, 64, 32 * 86400.0, 0};
static ChebBody EMB = {"emb", 13, 2, 64, 32 * 86400.0, 0};
static const double EMRAT = 81.30056822149722;

static void cheb_fill(ChebBody *b, double c0, double c1, double decay, uint64_t seed)
{
    sm_state = seed;
    size_t n = (size_t)b->nrec * b->nsub * 3 * b->ncoef;
    b->c = (double *)malloc(n * sizeof(double));
    for (size_t i = 0; i < n; i++) {
        int k = (int)(i % b->ncoef);
        double mag = (k == 0) ? c0 : c1 * pow(decay, k - 1);
        b->c[i] = sgn() * mag * (0.5 + urand());
    }
}
static void cheb_setup(void)
{
    cheb_fill(&MOON, 3.8e5, 1.6e5, 0.12, 0xC4EB000000000001ULL);
    cheb_fill(&SUN, 1.0e6, 1.0e4, 0.12, 0xC4EB000000000002ULL);
    cheb_fill(&EMB, 1.5e8, 2.0e7, 0.05, 0xC4EB000000000003ULL);
}
static void cheb_body(const ChebBody *b, double t, double out[3])
{
    double sub_len = b->rec_len / b->nsub;
    double u = t / sub_len;
    int idx = (int)u;
    int nint = b->nrec * b->nsub;
    if (idx < 0) idx = 0;
    if (idx >= nint) idx = nint - 1;
    double tau = 2.0 * (u - idx) - 1.0;
    const double *c = b->c + (size_t)idx * 3 * b->ncoef;
    double t2 = 2.0 * tau;
    for (int j = 0; j < 3; j++) {
        const double *cj = c + j * b->ncoef;
        double b1 = 0.0, b2 = 0.0;
        for (int k = b->ncoef - 1; k >= 1; k--) {
            double b0 = t2 * b1 - b2 + cj[k];
            b2 = b1;
            b1 = b0;
        }
        out[j] = tau * b1 - b2 + cj[0];
    }
}
static void cheb_sun_moon(double t, double moon[3], double sun[3])
{
    double s[3], e[3];
    cheb_body(&MOON, t, moon);
    cheb_body(&SUN, t, s);
    cheb_body(&EMB, t, e);
    double f = 1.0 / (1.0 + EMRAT);
    for (int j = 0; j < 3; j++) sun[j] = s[j] - (e[j] - f * moon[j]);
}
static double cheb_flops(void)
{
    /* per body: 1 div + 4 flops (u, tau, t2); per component 3 flops per
       coefficient; the combination: 1 add + 1 div + 3 x 3 */
    double f = 0;
    const ChebBody *bs[3] = {&MOON, &SUN, &EMB};
    for (int i = 0; i < 3; i++) f += 5 + 3.0 * 3 * bs[i]->ncoef;
    return f + 11;
}

/* --------------------------------------------------------------- frame */
#define NFA 14
typedef struct { int mult[NFA]; int out, pw; double as, ac; } NutTerm;
static NutTerm *TERMS;
static int NTERMS;
/* term counts by power of t, for X, Y and s+XY/2: IERS Conventions (2010),
   Tables 5.2a, 5.2b and 5.2d, READ (q2 log says from where) */
static const int TERM_COUNT[3][5] = {{1306, 253, 36, 4, 1}, {962, 277, 30, 5, 1}, {33, 3, 25, 4, 1}};
static double FA[NFA][5];
static const double PX[6] = {-16617.0, 2004191898.0, -429782.9, -198618.34, 7.578, 5.9285};
static const double PY[6] = {-6951.0, -25896.0, -22407274.7, 1900.59, 1112.526, 0.1358};
static const double PS[6] = {94.0, 3808.65, -122.68, -72574.11, 27.98, 15.62};
static const double UAS = 4.848136811095359935899141e-12; /* rad per microarcsecond */

static void frame_setup(void)
{
    sm_state = 0xF4A3000000000001ULL;
    /* fundamental arguments: rad and rad per Julian century^k, in the range of
       l, l', F, D, Omega, the planetary longitudes and p_A */
    static const double rate[NFA] = {8328.69, 628.30, 8433.47, 7771.38, -33.76, 2608.79, 1021.33,
                                     628.31, 334.06, 52.97, 21.33, 7.48, 3.81, 0.0244};
    for (int k = 0; k < NFA; k++) {
        FA[k][0] = 2 * M_PI * urand() + 0.1;
        FA[k][1] = rate[k];
        FA[k][2] = sgn() * 1e-5 * (0.5 + urand());
        FA[k][3] = sgn() * 1e-7 * (0.5 + urand());
        FA[k][4] = sgn() * 1e-9 * (0.5 + urand());
    }
    NTERMS = 0;
    for (int o = 0; o < 3; o++)
        for (int j = 0; j < 5; j++) NTERMS += TERM_COUNT[o][j];
    TERMS = (NutTerm *)malloc(sizeof(NutTerm) * NTERMS);
    int i = 0;
    for (int o = 0; o < 3; o++)
        for (int j = 0; j < 5; j++)
            for (int q = 0; q < TERM_COUNT[o][j]; q++, i++) {
                NutTerm *t = &TERMS[i];
                for (int k = 0; k < NFA; k++) {
                    int v = 1 + (int)(urand() * (k < 5 ? 3 : 2));
                    t->mult[k] = (splitmix64() & 1) ? v : -v;
                }
                t->out = o;
                t->pw = j;
                /* amplitudes log-uniform in [0.1, 1e7] microarcseconds */
                t->as = sgn() * pow(10.0, -1.0 + 8.0 * urand());
                t->ac = sgn() * pow(10.0, -1.0 + 8.0 * urand());
            }
}

static void xys_full(double t, double *X, double *Y, double *s)
{
    double fa[NFA];
    for (int k = 0; k < NFA; k++) fa[k] = FA[k][0] + t * (FA[k][1] + t * (FA[k][2] + t * (FA[k][3] + t * FA[k][4])));
    double acc[3][5] = {{0}};
    for (int i = 0; i < NTERMS; i++) {
        const NutTerm *q = &TERMS[i];
        double arg = 0.0;
        for (int k = 0; k < NFA; k++) arg += q->mult[k] * fa[k];
        acc[q->out][q->pw] += q->as * sin(arg) + q->ac * cos(arg);
    }
    const double *P[3] = {PX, PY, PS};
    double res[3];
    for (int o = 0; o < 3; o++) {
        const double *p = P[o];
        double v = p[0] + t * (p[1] + t * (p[2] + t * (p[3] + t * (p[4] + t * p[5]))));
        double w = acc[o][4];
        for (int j = 3; j >= 0; j--) w = w * t + acc[o][j];
        res[o] = v + w;
    }
    *X = res[0] * UAS;
    *Y = res[1] * UAS;
    *s = res[2] * UAS - 0.5 * (*X) * (*Y);
}

/* rotations, applied on the left: R <- Rx(phi) R, etc., with the IERS sense */
static void rot_x(double phi, double R[3][3])
{
    double c = cos(phi), s = sin(phi);
    for (int j = 0; j < 3; j++) {
        double a1 = R[1][j], a2 = R[2][j];
        R[1][j] = c * a1 + s * a2;
        R[2][j] = -s * a1 + c * a2;
    }
}
static void rot_y(double th, double R[3][3])
{
    double c = cos(th), s = sin(th);
    for (int j = 0; j < 3; j++) {
        double a0 = R[0][j], a2 = R[2][j];
        R[0][j] = c * a0 - s * a2;
        R[2][j] = s * a0 + c * a2;
    }
}
static void rot_z(double psi, double R[3][3])
{
    double c = cos(psi), s = sin(psi);
    for (int j = 0; j < 3; j++) {
        double a0 = R[0][j], a1 = R[1][j];
        R[0][j] = c * a0 + s * a1;
        R[1][j] = -s * a0 + c * a1;
    }
}
static void ident(double R[3][3])
{
    for (int i = 0; i < 3; i++)
        for (int j = 0; j < 3; j++) R[i][j] = (i == j) ? 1.0 : 0.0;
}

/* daily EOP table: xp, yp (rad), dUT1 (s); synthetic, real magnitudes */
#define NEOP 400
static double EOP[NEOP][3];
static void eop_setup(void)
{
    sm_state = 0xE0E0000000000001ULL;
    for (int d = 0; d < NEOP; d++) {
        EOP[d][0] = (0.15 + 0.1 * urand()) * 4.848136811095359935899141e-6;
        EOP[d][1] = (0.35 + 0.1 * urand()) * 4.848136811095359935899141e-6;
        EOP[d][2] = -0.2 + 0.4 * urand();
    }
}

/* t: seconds TT from the table epoch, which is TT JD 2460676.5 (2025-01-01) */
static const double T_EPOCH_JD = 2460676.5;

static void c2t_from_xys(double t, double X, double Y, double s, double R[3][3], double *era_out)
{
    double day = t / 86400.0;
    int d = (int)day;
    if (d < 0) d = 0;
    if (d > NEOP - 2) d = NEOP - 2;
    double f = day - d;
    double xp = EOP[d][0] + f * (EOP[d + 1][0] - EOP[d][0]);
    double yp = EOP[d][1] + f * (EOP[d + 1][1] - EOP[d][1]);
    double dut1 = EOP[d][2] + f * (EOP[d + 1][2] - EOP[d][2]);
    /* UT1 = TT - 69.184 s + dUT1 (TAI-UTC 37 s): days from J2000 UT1 */
    double Tu = (T_EPOCH_JD - 2451545.0) + (t - 69.184 + dut1) / 86400.0;
    double era = 2 * M_PI * (fmod(Tu, 1.0) + 0.7790572732640 + 0.00273781191135448 * Tu);
    era = fmod(era, 2 * M_PI);
    double tc = (T_EPOCH_JD - 2451545.0 + t / 86400.0) / 36525.0;
    double sp = -47e-6 * 4.848136811095359935899141e-6 * tc;
    /* Q^T (celestial to intermediate) from X, Y, s */
    double r2 = X * X + Y * Y;
    double e = (r2 > 0.0) ? atan2(Y, X) : 0.0;
    double dd = atan(sqrt(r2 / (1.0 - r2)));
    double C2I[3][3];
    ident(C2I);
    rot_z(e, C2I);
    rot_y(dd, C2I);
    rot_z(-(e + s), C2I);
    /* polar motion W */
    double Wm[3][3];
    ident(Wm);
    rot_z(sp, Wm);
    rot_y(-xp, Wm);
    rot_x(-yp, Wm);
    /* R = W Rz(era) C2I */
    double A[3][3];
    for (int i = 0; i < 3; i++)
        for (int j = 0; j < 3; j++) A[i][j] = C2I[i][j];
    rot_z(era, A);
    for (int i = 0; i < 3; i++)
        for (int j = 0; j < 3; j++) R[i][j] = Wm[i][0] * A[0][j] + Wm[i][1] * A[1][j] + Wm[i][2] * A[2][j];
    *era_out = era;
}

static void frame_full(double t, const double rg[3], double ri[3], double R[3][3])
{
    double X, Y, s, era;
    double tc = (T_EPOCH_JD - 2451545.0 + t / 86400.0) / 36525.0;
    xys_full(tc, &X, &Y, &s);
    c2t_from_xys(t, X, Y, s, R, &era);
    for (int i = 0; i < 3; i++) ri[i] = R[i][0] * rg[0] + R[i][1] * rg[1] + R[i][2] * rg[2];
}

/* interpolation nodes for X, Y, s */
#define NNODE 2000
static double NODE_DT;
static double NODE[NNODE][3];
static void nodes_setup(double spacing)
{
    NODE_DT = spacing;
    for (int i = 0; i < NNODE; i++) {
        double t = i * spacing;
        double tc = (T_EPOCH_JD - 2451545.0 + t / 86400.0) / 36525.0;
        xys_full(tc, &NODE[i][0], &NODE[i][1], &NODE[i][2]);
    }
}
static void xys_interp(double t, double *X, double *Y, double *s)
{
    double u = t / NODE_DT;
    int j = (int)u;
    int i0 = j - 2;
    if (i0 < 0) i0 = 0;
    if (i0 > NNODE - 6) i0 = NNODE - 6;
    double x = u - i0;
    double w[6];
    for (int i = 0; i < 6; i++) {
        double num = 1.0, den = 1.0;
        for (int k = 0; k < 6; k++)
            if (k != i) {
                num *= (x - k);
                den *= (double)(i - k);
            }
        w[i] = num / den;
    }
    double v[3] = {0, 0, 0};
    for (int i = 0; i < 6; i++)
        for (int c = 0; c < 3; c++) v[c] += w[i] * NODE[i0 + i][c];
    *X = v[0];
    *Y = v[1];
    *s = v[2];
}
static void frame_interp(double t, const double rg[3], double ri[3], double R[3][3])
{
    double X, Y, s, era;
    xys_interp(t, &X, &Y, &s);
    c2t_from_xys(t, X, Y, s, R, &era);
    for (int i = 0; i < 3; i++) ri[i] = R[i][0] * rg[0] + R[i][1] * rg[1] + R[i][2] * rg[2];
}
static double c2t_flops(void)
{
    /* EOP lookup 1 div + 3x(1 mul 2 add) + 3; ERA ~8; s' 4; X,Y->e,d 6 flops;
       each rotation 12 mul + 6 add over 3 columns -> 18 (7 rotations);
       matrix product 27 mul + 18 add; transcendental calls counted apart */
    return 1 + 9 + 3 + 8 + 4 + 6 + 7 * 18 + 45;
}
static int c2t_transcendentals(void) { return 7 * 2 + 1 + 1 + 1 + 2; } /* 7 sin/cos pairs, atan2, atan, sqrt, 2 fmod */

/* ---------------------------------------------------------- atmosphere */
static const double ATM_H0[28] = {0, 25, 30, 40, 50, 60, 70, 80, 90, 100, 110, 120, 130, 140, 150, 180, 200, 250,
                                  300, 350, 400, 450, 500, 600, 700, 800, 900, 1000};
static const double ATM_RHO0[28] = {1.225, 3.899e-2, 1.774e-2, 3.972e-3, 1.057e-3, 3.206e-4, 8.770e-5, 1.905e-5,
                                    3.396e-6, 5.297e-7, 9.661e-8, 2.438e-8, 8.484e-9, 3.845e-9, 2.070e-9, 5.464e-10,
                                    2.789e-10, 7.248e-11, 2.418e-11, 9.518e-12, 3.725e-12, 1.585e-12, 6.967e-13,
                                    1.454e-13, 3.614e-14, 1.170e-14, 5.245e-15, 3.019e-15};
static const double ATM_HS[28] = {7.249, 6.349, 6.682, 7.554, 8.382, 7.714, 6.549, 5.799, 5.382, 5.877, 7.263,
                                  9.473, 12.636, 16.149, 22.523, 29.740, 37.105, 45.546, 53.628, 53.298, 58.515,
                                  60.828, 63.822, 71.835, 88.667, 124.64, 181.05, 268.00};
static const double OMEGA_E = 7.292115e-5;
static void atmos_drag(const double *rv, int K, double B, double *acc)
{
    for (int i = 0; i < K; i++) {
        const double *p = rv + 6 * i;
        double r = sqrt(p[0] * p[0] + p[1] * p[1] + p[2] * p[2]);
        double h = r - R_EARTH;
        int lo = 0, hi = 27;
        while (lo < hi) {
            int mid = (lo + hi + 1) >> 1;
            if (ATM_H0[mid] <= h) lo = mid;
            else hi = mid - 1;
        }
        double rho = ATM_RHO0[lo] * exp(-(h - ATM_H0[lo]) / ATM_HS[lo]);
        double vx = p[3] + OMEGA_E * p[1], vy = p[4] - OMEGA_E * p[0], vz = p[5];
        double v = sqrt(vx * vx + vy * vy + vz * vz);
        double k = -0.5e3 * B * rho * v;
        acc[3 * i] = k * vx;
        acc[3 * i + 1] = k * vy;
        acc[3 * i + 2] = k * vz;
    }
}
/* per object: |r| 5 flops + sqrt; h 1; band search 5 compares; rho 3 flops +
   1 div + exp; v_rel 4; |v| 5 + sqrt; k 3; a 3 */
static double atmos_flops(void) { return 5 + 1 + 3 + 1 + 4 + 5 + 3 + 3; }

/* LEO states for the atmosphere: 200-700 km */
#define NATM 4096
static double ATM_RV[NATM][6];
static void atmos_setup(void)
{
    sm_state = 0xA7A7000000000001ULL;
    for (int i = 0; i < NATM; i++) {
        double a = R_EARTH + 200.0 + 500.0 * urand();
        double inc = M_PI * urand(), node = 2 * M_PI * urand(), u = 2 * M_PI * urand();
        double v = sqrt(GM_EARTH / a);
        double cu = cos(u), su = sin(u), cn = cos(node), sn = sin(node), ci = cos(inc), si = sin(inc);
        ATM_RV[i][0] = a * (cn * cu - sn * su * ci);
        ATM_RV[i][1] = a * (sn * cu + cn * su * ci);
        ATM_RV[i][2] = a * (su * si);
        ATM_RV[i][3] = v * (-cn * su - sn * cu * ci);
        ATM_RV[i][4] = v * (-sn * su + cn * cu * ci);
        ATM_RV[i][5] = v * (cu * si);
    }
}

/* ----------------------------------------------- radiation pressure */
static const double R_SUN = 696000.0, AU_KM = 149597870.7, P_SUN = 4.56e-6;
static void srp_conical(const double r[3], const double rs[3], double cram, double a[3], double *nu_out)
{
    double d[3] = {r[0] - rs[0], r[1] - rs[1], r[2] - rs[2]};
    double rn = sqrt(r[0] * r[0] + r[1] * r[1] + r[2] * r[2]);
    double dn = sqrt(d[0] * d[0] + d[1] * d[1] + d[2] * d[2]);
    double A = asin(R_SUN / dn);
    double B = asin(R_EARTH / rn);
    double cosc = (r[0] * d[0] + r[1] * d[1] + r[2] * d[2]) / (rn * dn);
    if (cosc > 1.0) cosc = 1.0;
    if (cosc < -1.0) cosc = -1.0;
    double C = acos(cosc);
    double nu;
    if (C >= A + B) nu = 1.0;
    else if (C <= B - A) nu = 0.0;
    else if (C <= A - B) nu = 1.0 - (B * B) / (A * A);
    else {
        double x = (C * C + A * A - B * B) / (2.0 * C);
        double y2 = A * A - x * x;
        double y = sqrt(y2 > 0.0 ? y2 : 0.0);
        double ca = x / A, cb = (C - x) / B;
        if (ca > 1.0) ca = 1.0;
        if (ca < -1.0) ca = -1.0;
        if (cb > 1.0) cb = 1.0;
        if (cb < -1.0) cb = -1.0;
        double area = A * A * acos(ca) + B * B * acos(cb) - C * y;
        nu = 1.0 - area / (M_PI * A * A);
    }
    double q = AU_KM / dn;
    double k = nu * P_SUN * cram * q * q / dn * 1e-3;
    a[0] = k * d[0];
    a[1] = k * d[1];
    a[2] = k * d[2];
    *nu_out = nu;
}
/* sunlit or umbra: 3 + 8 + 8 flops, 2 sqrt, 2 div, 2 asin, 1 acos, 2 compares;
   penumbra adds 12 flops, 3 div, 1 sqrt, 2 acos; the scaling 6 mul + 2 div */
#define NSRP 1024
static double SRP_R[NSRP][3], SRP_S[3];
static void srp_setup(int set)
{
    /* Sun along +x at 1 AU; satellite on a 400 km circular orbit in the
       x-y plane (the plane that contains the Sun line, so it passes the
       shadow's axis) */
    SRP_S[0] = AU_KM;
    SRP_S[1] = 0.0;
    SRP_S[2] = 0.0;
    double a = R_EARTH + 400.0;
    if (set == 0) {
        for (int i = 0; i < NSRP; i++) {
            double u = 2 * M_PI * (i + 0.37) / NSRP;
            SRP_R[i][0] = a * cos(u);
            SRP_R[i][1] = a * sin(u);
            SRP_R[i][2] = 1.0 + 0.001 * i;
        }
    } else {
        /* the shadow's edge at a 400 km orbit: Earth's apparent radius
           asin(R/a) seen against a Sun of apparent radius ~R_SUN/AU; the
           penumbra lies where the Sun's centre is within one solar radius of
           the Earth's limb: sample that band only */
        double B = asin(R_EARTH / a), As = asin(R_SUN / AU_KM);
        for (int i = 0; i < NSRP; i++) {
            double c = (B - As) + (2.0 * As) * (i + 0.5) / NSRP; /* separation */
            /* separation c between the Earth's centre (at -r) and the Sun
               (at ~+x): position at angle pi - c from +x, approximately */
            double u = M_PI - c;
            SRP_R[i][0] = a * cos(u);
            SRP_R[i][1] = a * sin(u);
            SRP_R[i][2] = 0.0;
        }
    }
}

/* --------------------------------------------------------------- timing */
static double qpc(void)
{
    LARGE_INTEGER c, f;
    QueryPerformanceCounter(&c);
    QueryPerformanceFrequency(&f);
    return (double)c.QuadPart / (double)f.QuadPart;
}
static uint64_t thread_cycles(void)
{
    ULONG64 c = 0;
    QueryThreadCycleTime(GetCurrentThread(), &c);
    return (uint64_t)c;
}
static double ft(FILETIME f) { return (double)(((uint64_t)f.dwHighDateTime << 32) | f.dwLowDateTime) * 1e-7; }
static double thread_cpu(void)
{
    FILETIME a, b, k, u;
    GetThreadTimes(GetCurrentThread(), &a, &b, &k, &u);
    return ft(k) + ft(u);
}
static void sys_times(double *idle, double *total)
{
    FILETIME i, k, u;
    GetSystemTimes(&i, &k, &u);
    *idle = ft(i);
    *total = ft(k) + ft(u); /* kernel time includes idle */
}

static volatile double SINK;

static double run_kernel(const char *kernel, int param, long ncall, double *cs_out)
{
    double cs = 0.0;
    double a[3] = {1e-9, 2e-9, 3e-9};
    double t0 = qpc();
    if (!strcmp(kernel, "grav")) {
        for (long i = 0; i < ncall; i++) {
            const double *r = POS[i & (NPOS - 1)];
            CALL(grav_accel_d(r, 0, param, a));
            cs += a[0] + 1.0000001 * a[1] + 1.0000002 * a[2];
        }
    } else if (!strcmp(kernel, "gravq")) {
        __float128 aq[3] = {1e-9Q, 2e-9Q, 3e-9Q}, rq[3];
        for (long i = 0; i < ncall; i++) {
            const double *r = POS[i & (NPOS - 1)];
            rq[0] = r[0];
            rq[1] = r[1];
            rq[2] = r[2];
            CALL(grav_accel_q(rq, 0, param, aq));
            cs += (double)aq[0] + 1.0000001 * (double)aq[1] + 1.0000002 * (double)aq[2];
        }
    } else if (!strcmp(kernel, "cheb")) {
        double mo[3] = {1, 2, 3}, su[3] = {4, 5, 6};
        double span = 64 * 32 * 86400.0;
        for (long i = 0; i < ncall; i++) {
            double t = fmod(1234.5 + 377.3 * (double)i, span);
            CALL(cheb_sun_moon(t, mo, su));
            cs += mo[0] + 1.0000001 * mo[1] + 1.0000002 * mo[2] + 1.0000003 * su[0] + 1.0000004 * su[1] +
                  1.0000005 * su[2];
        }
    } else if (!strcmp(kernel, "frame_full") || !strcmp(kernel, "frame_interp")) {
        int full = !strcmp(kernel, "frame_full");
        double R[3][3] = {{1, 0, 0}, {0, 1, 0}, {0, 0, 1}}, ri[3] = {1, 2, 3};
        double span = (NNODE - 8) * NODE_DT;
        if (full) span = 365.0 * 86400.0;
        for (long i = 0; i < ncall; i++) {
            double t = fmod(3.0 * NODE_DT + 37.3 * (double)i, span);
            const double *rg = POS[i & (NPOS - 1)];
            if (full) {
                CALL(frame_full(t, rg, ri, R));
            } else {
                CALL(frame_interp(t, rg, ri, R));
            }
            double m = 0.0;
            for (int p = 0; p < 3; p++)
                for (int q = 0; q < 3; q++) m += (1.0 + 1e-7 * (3 * p + q)) * R[p][q];
            cs += ri[0] + 1.0000001 * ri[1] + 1.0000002 * ri[2] + m;
        }
    } else if (!strcmp(kernel, "atmos")) {
        int K = param;
        static double acc[NATM * 3];
        for (int j = 0; j < 3 * K; j++) acc[j] = 1e-12 * (j + 1);
        long nb = NATM / K;
        for (long i = 0; i < ncall; i++) {
            const double *rv = ATM_RV[(i % nb) * K];
            CALL(atmos_drag(rv, K, 0.022, acc));
            for (int j = 0; j < K; j++) cs += acc[3 * j] + 1.0000001 * acc[3 * j + 1] + 1.0000002 * acc[3 * j + 2];
        }
    } else if (!strcmp(kernel, "srp")) {
        double nu = 0.5;
        for (long i = 0; i < ncall; i++) {
            const double *r = SRP_R[i & (NSRP - 1)];
            CALL(srp_conical(r, SRP_S, 0.026, a, &nu));
            cs += a[0] + 1.0000001 * a[1] + 1.0000002 * a[2] + 1e-9 * nu;
        }
    } else {
        fprintf(stderr, "unknown kernel %s\n", kernel);
        exit(2);
    }
    double t1 = qpc();
    *cs_out = cs;
    SINK = cs;
    return t1 - t0;
}

static void setup(const char *kernel, int param)
{
    make_positions();
    if (!strcmp(kernel, "grav") || !strcmp(kernel, "gravq")) {
        if (param < 2 || param > 70) {
            fprintf(stderr, "degree 2..70\n");
            exit(2);
        }
        grav_coeffs(param);
        grav_tables_d(param);
        grav_tables_q(param);
    } else if (!strcmp(kernel, "cheb")) {
        cheb_setup();
    } else if (!strcmp(kernel, "frame_full") || !strcmp(kernel, "frame_interp")) {
        frame_setup();
        eop_setup();
        nodes_setup(!strcmp(kernel, "frame_interp") ? (double)param : 3600.0);
    } else if (!strcmp(kernel, "atmos")) {
        atmos_setup();
    } else if (!strcmp(kernel, "srp")) {
        srp_setup(param);
    }
}

static void hexv(const char *tag, const double *v, int n)
{
    printf("%s", tag);
    for (int i = 0; i < n; i++) printf(" %a", v[i]);
    printf("\n");
}

static int do_check(const char *kernel, int param)
{
    setup(kernel, param);
    printf("# q2bench check %s %d\n", kernel, param);
    if (!strcmp(kernel, "grav") || !strcmp(kernel, "gravq")) {
        printf("GM %a R %a N %d\n", GM_EARTH, R_EARTH, param);
        for (int n = 2; n <= param; n++)
            for (int m = 0; m <= n; m++) printf("CS %d %d %a %a\n", n, m, GCu[n][m], GSu[n][m]);
        static const int pick[4] = {0, 1, 2, 301};
        for (int q = 0; q < 4; q++) {
            const double *r = POS[pick[q]];
            hexv("POS", r, 3);
            int half = param / 2;
            if (!strcmp(kernel, "grav")) {
                double a_full[3], a_pert[3], a_band[3];
                grav_accel_d(r, 0, param, a_full);
                grav_accel_d(r, 2, param, a_pert);
                grav_accel_d(r, half + 1, param, a_band);
                hexv("FULL", a_full, 3);
                hexv("PERT", a_pert, 3);
                printf("BANDLO %d\n", half + 1);
                hexv("BAND", a_band, 3);
            } else {
                __float128 rq[3] = {r[0], r[1], r[2]}, aq[3];
                char buf[64];
                const char *tags[3] = {"FULLQ", "PERTQ", "BANDQ"};
                int nmins[3] = {0, 2, half + 1};
                for (int k = 0; k < 3; k++) {
                    grav_accel_q(rq, nmins[k], param, aq);
                    printf("%s", tags[k]);
                    for (int c = 0; c < 3; c++) {
                        quadmath_snprintf(buf, sizeof buf, "%.40Qe", aq[c]);
                        printf(" %s", buf);
                    }
                    printf("\n");
                }
                printf("BANDLO %d\n", half + 1);
            }
        }
    } else if (!strcmp(kernel, "cheb")) {
        const ChebBody *bs[3] = {&MOON, &SUN, &EMB};
        for (int b = 0; b < 3; b++) {
            printf("BODY %s %d %d %d %a\n", bs[b]->name, bs[b]->ncoef, bs[b]->nsub, bs[b]->nrec, bs[b]->rec_len);
        }
        printf("EMRAT %a\n", EMRAT);
        static const double ts[5] = {1234.5, 400000.25, 1.5e7, 9.99e7, 1.7e8};
        for (int q = 0; q < 5; q++) {
            double t = ts[q], mo[3], su[3];
            cheb_sun_moon(t, mo, su);
            printf("T %a\n", t);
            /* the coefficients this time uses, for each body */
            for (int b = 0; b < 3; b++) {
                const ChebBody *bb = bs[b];
                double sub_len = bb->rec_len / bb->nsub;
                int idx = (int)(t / sub_len);
                printf("COEF %s %d", bb->name, idx);
                for (int k = 0; k < 3 * bb->ncoef; k++) printf(" %a", bb->c[(size_t)idx * 3 * bb->ncoef + k]);
                printf("\n");
            }
            hexv("MOON", mo, 3);
            hexv("SUN", su, 3);
        }
    } else if (!strcmp(kernel, "frame_full") || !strcmp(kernel, "frame_interp")) {
        int full = !strcmp(kernel, "frame_full");
        printf("NTERMS %d\n", NTERMS);
        printf("TEPOCH %a\n", T_EPOCH_JD);
        for (int k = 0; k < NFA; k++) hexv("FA", FA[k], 5);
        hexv("PX", PX, 6);
        hexv("PY", PY, 6);
        hexv("PS", PS, 6);
        if (full) {
            for (int i = 0; i < NTERMS; i++) {
                const NutTerm *q = &TERMS[i];
                printf("TERM %d %d", q->out, q->pw);
                for (int k = 0; k < NFA; k++) printf(" %d", q->mult[k]);
                printf(" %a %a\n", q->as, q->ac);
            }
        }
        for (int d = 0; d < NEOP; d++) hexv("EOP", EOP[d], 3);
        printf("NODEDT %a\n", NODE_DT);
        static const double ts[4] = {3.0 * 3600 + 1234.5, 86400.0 * 17.3, 86400.0 * 41.77, 86400.0 * 80.01};
        for (int q = 0; q < 4; q++) {
            double t = ts[q], R[3][3], ri[3], X, Y, s, era;
            const double *rg = POS[q * 7];
            double tc = (T_EPOCH_JD - 2451545.0 + t / 86400.0) / 36525.0;
            printf("T %a\n", t);
            hexv("RG", rg, 3);
            if (full) {
                xys_full(tc, &X, &Y, &s);
                frame_full(t, rg, ri, R);
            } else {
                double u = t / NODE_DT;
                int j = (int)u, i0 = j - 2;
                if (i0 < 0) i0 = 0;
                if (i0 > NNODE - 6) i0 = NNODE - 6;
                printf("NODEI0 %d\n", i0);
                for (int i = 0; i < 6; i++) hexv("NODE", NODE[i0 + i], 3);
                xys_interp(t, &X, &Y, &s);
                frame_interp(t, rg, ri, R);
                double Xf, Yf, sf;
                xys_full(tc, &Xf, &Yf, &sf);
                double fv[3] = {Xf, Yf, sf};
                hexv("XYSFULL", fv, 3);
            }
            c2t_from_xys(t, X, Y, s, R, &era);
            double xv[4] = {X, Y, s, era};
            hexv("XYSE", xv, 4);
            hexv("RI", ri, 3);
            for (int p = 0; p < 3; p++) hexv("ROW", R[p], 3);
        }
    } else if (!strcmp(kernel, "atmos")) {
        double acc[3 * 16];
        atmos_drag(ATM_RV[0], 16, 0.022, acc);
        printf("B %a REARTH %a OMEGA %a\n", 0.022, R_EARTH, OMEGA_E);
        for (int i = 0; i < 28; i++) printf("BAND %a %a %a\n", ATM_H0[i], ATM_RHO0[i], ATM_HS[i]);
        for (int i = 0; i < 16; i++) {
            hexv("RV", ATM_RV[i], 6);
            hexv("ACC", acc + 3 * i, 3);
        }
    } else if (!strcmp(kernel, "srp")) {
        printf("RSUN %a REARTH %a AU %a PSUN %a CRAM %a\n", R_SUN, R_EARTH, AU_KM, P_SUN, 0.026);
        hexv("SUNPOS", SRP_S, 3);
        int step = NSRP / 16;
        for (int i = 0; i < NSRP; i += step) {
            double a[3], nu;
            srp_conical(SRP_R[i], SRP_S, 0.026, a, &nu);
            hexv("R", SRP_R[i], 3);
            printf("NU %a\n", nu);
            hexv("ACC", a, 3);
        }
        /* one annular case: a body far beyond the Earth's shadow cone apex */
        {
            double r[3] = {-3.0e6, 1.0, 0.0}, a[3], nu;
            srp_conical(r, SRP_S, 0.026, a, &nu);
            hexv("R", r, 3);
            printf("NU %a\n", nu);
            hexv("ACC", a, 3);
        }
    }
    return 0;
}

static int do_count(const char *kernel, int param)
{
    setup(kernel, param);
    if (!strcmp(kernel, "grav") || !strcmp(kernel, "gravq")) {
        printf("grav N=%d: %.0f flops a call (+1 sqrt, 3 div counted in), %d coefficient pairs\n", param,
               grav_flops(0, param), (param + 1) * (param + 2) / 2 - 3);
    } else if (!strcmp(kernel, "cheb")) {
        printf("cheb: %.0f flops a call, Moon %d + Sun %d + EMB %d coefficients x 3 components\n", cheb_flops(),
               MOON.ncoef, SUN.ncoef, EMB.ncoef);
    } else if (!strcmp(kernel, "frame_full")) {
        printf("frame_full: %d terms; each 14 multiply-adds for its argument (int x double) + 1 sin + 1 cos + "
               "2 mul + 2 add; series %ld flops + %d sin/cos pairs; then the matrix: %.0f flops + %d "
               "transcendental calls; apply 15\n",
               NTERMS, (long)NTERMS * (28 + 4) + 14 * 8 + 3 * 18, NTERMS, c2t_flops(), c2t_transcendentals());
    } else if (!strcmp(kernel, "frame_interp")) {
        printf("frame_interp: 6-point Lagrange weights 6 x (5 sub, 10 mul) + 6 div = 96; 3 x 6 MAC = 36; "
               "the matrix: %.0f flops + %d transcendental calls; apply 15\n",
               c2t_flops(), c2t_transcendentals());
    } else if (!strcmp(kernel, "atmos")) {
        printf("atmos: %.0f flops an object + 2 sqrt + 1 exp + 5 compares\n", atmos_flops());
    } else if (!strcmp(kernel, "srp")) {
        printf("srp: sunlit/umbra ~33 flops + 2 sqrt + 2 asin + 1 acos + 4 div; penumbra +12 flops + 1 sqrt "
               "+ 2 acos + 3 div\n");
    }
    return 0;
}

int main(int argc, char **argv)
{
    if (argc >= 4 && !strcmp(argv[1], "check")) return do_check(argv[2], atoi(argv[3]));
    if (argc >= 4 && !strcmp(argv[1], "count")) return do_count(argv[2], atoi(argv[3]));
    if (argc < 6 || strcmp(argv[1], "time")) {
        fprintf(stderr, "usage: q2bench time <kernel> <param> <ncall> <reps> | check <kernel> <param> | count ...\n");
        return 2;
    }
    const char *kernel = argv[2];
    int param = atoi(argv[3]);
    long ncall = atol(argv[4]);
    int reps = atoi(argv[5]);
    setup(kernel, param);
    double cs;
    run_kernel(kernel, param, ncall / 10 + 1, &cs); /* warm-up */
    printf("# %s %s param=%d ncall=%ld reps=%d\n", VARIANT, kernel, param, ncall, reps);
    for (int r = 0; r < reps; r++) {
        double i0, tot0, i1, tot1;
        sys_times(&i0, &tot0);
        double c0 = thread_cpu();
        uint64_t y0 = thread_cycles();
        double w = run_kernel(kernel, param, ncall, &cs);
        uint64_t y1 = thread_cycles();
        double c1 = thread_cpu();
        sys_times(&i1, &tot1);
        double load = (tot1 - tot0) > 0 ? 100.0 * (1.0 - (i1 - i0) / (tot1 - tot0)) : -1.0;
        printf("rep %d wall_ns_per_call %.3f cpu_ns_per_call %.3f cycles_per_call %.1f host_load_pct %.0f "
               "wall_s %.4f checksum %.17g\n",
               r, 1e9 * w / ncall, 1e9 * (c1 - c0) / ncall, (double)(y1 - y0) / ncall, load, w, cs);
    }
    return 0;
}
