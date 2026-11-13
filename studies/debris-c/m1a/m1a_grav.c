/* m1a_grav.c - DEBRIS-C, M1a: spherical-harmonic gravity at binary64 along
   Lasser et al.'s TRF orbit, from the real EIGEN-6C4 coefficients.

   Derived from a copy of DEBRIS-B's q2/grav_body.inc (the Cunningham V, W
   recursion in Earth-fixed Cartesian coordinates, Montenbruck & Gill 2000,
   section 3.2). What changed from DEBRIS-B's kernel, and why:
   1. Normalisation. DEBRIS-B's recursion is unnormalised: V_mm grows like
      (2m-1)!! and the unnormalised coefficients shrink by the inverse
      factor, which overflows binary64 long before degree 180. Here every
      V, W is fully normalised (V-bar = N_nm V, N_nm^2 = (2-d_m0)(2n+1)
      (n-m)!/(n+m)!), so the recursion coefficients become the standard
      normalised Legendre ones:
        column     a(n,m) = sqrt((2n-1)(2n+1) / ((n-m)(n+m)))
                   b(n,m) = sqrt((2n+1)(n+m-1)(n-m-1) / ((2n-3)(n+m)(n-m)))
        sub-diag   V(m+1,m) = sqrt(2m+3) z0 V(m,m)
        diagonal   d(1) = sqrt(3), d(m>=2) = sqrt((2m+1)/(2m))
      and each acceleration term carries the ratio N_nm / N_(n+1,m') of
      the normalisations it mixes (fA, fB, fz, f1 below; derived in the
      study, section "M1a").
   2. Coefficients: the real EIGEN-6C4 file (gfc lines), with GM and the
      reference radius from its header, not synthetic draws.
   3. Sizes: degree 180, so arrays of 183; units metres, not km.
   4. Degree range: nmin..nmax (default 2..180, Lasser et al.'s range); the
      central term (n = 0) and degree 1 are never summed.
   The loop order (n ascending, m ascending) is DEBRIS-B's.

   usage: m1a_grav <EIGEN6-C4.gfc> <00orbit_itrf.txt> <nmin> <nmax> <out.txt> [plant_epoch]
   Writes one line per epoch: the time and the three acceleration
   components (m/s^2), each as a C99 hex float (%a) and as %.17e.
   plant_epoch >= 0 nudges that epoch's x component by one ulp (nextafter
   towards +inf) before it is written: M3's control on the output hash.
   Version 2 adds an optional 7th argument n,m,dC: dC is added to C-bar(n,m)
   after the file is read (M1a's domain demonstration, m1a_domain.py). With
   six arguments version 2 computes exactly what version 1 did. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>

#define NMAXC 180
#define NA (NMAXC + 3)

static double Cb[NA][NA], Sb[NA][NA];
static int seen[NA][NA];
static double GM = 0.0, RE = 0.0;
static double An[NA][NA], Bn[NA][NA], Dg[NA], Sd[NA];
static double FA[NA][NA], FB[NA][NA], FZ[NA][NA], F1[NA];
static double V[NA][NA], W[NA][NA];

static void read_gfc(const char *path)
{
    FILE *f = fopen(path, "r");
    if (!f) { perror(path); exit(2); }
    char line[512];
    int in_head = 1, ngfc = 0, nother = 0, ndup = 0, maxdeg = -1;
    char norm[64] = "", tide[64] = "", model[64] = "";
    while (fgets(line, sizeof line, f)) {
        char key[64];
        if (sscanf(line, "%63s", key) != 1) continue;
        if (in_head) {
            if (!strncmp(key, "end_of_head", 11)) { in_head = 0; continue; }
            char val[128];
            if (sscanf(line, "%63s %127s", key, val) == 2) {
                if (!strcmp(key, "earth_gravity_constant")) GM = strtod(val, NULL);
                else if (!strcmp(key, "radius")) RE = strtod(val, NULL);
                else if (!strcmp(key, "max_degree")) maxdeg = atoi(val);
                else if (!strcmp(key, "norm")) snprintf(norm, sizeof norm, "%s", val);
                else if (!strcmp(key, "tide_system")) snprintf(tide, sizeof tide, "%s", val);
                else if (!strcmp(key, "modelname")) snprintf(model, sizeof model, "%s", val);
            }
            continue;
        }
        if (strcmp(key, "gfc")) { nother++; continue; }
        int n, m; double c, s;
        if (sscanf(line, "%*s %d %d %lf %lf", &n, &m, &c, &s) != 4) { fprintf(stderr, "bad line: %s", line); exit(2); }
        if (n < 0 || n > NMAXC || m < 0 || m > n) { fprintf(stderr, "bad degree/order: %s", line); exit(2); }
        if (seen[n][m]) {
            ndup++;
            if (Cb[n][m] != c || Sb[n][m] != s) { fprintf(stderr, "conflicting duplicate (%d,%d)\n", n, m); exit(2); }
        }
        seen[n][m] = 1;
        Cb[n][m] = c;
        Sb[n][m] = s;
        ngfc++;
    }
    fclose(f);
    int missing = 0, missing_deg1 = 0;
    for (int n = 0; n <= NMAXC; n++)
        for (int m = 0; m <= n; m++)
            if (!seen[n][m]) { if (n == 1) missing_deg1++; else missing++; }
    printf("# gfc: model %s, GM %.10e m^3/s^2, radius %.10e m, max_degree %d, norm %s, tide_system %s\n",
           model, GM, RE, maxdeg, norm, tide);
    printf("# gfc: %d gfc lines, %d non-gfc data lines (time-variable keys would be here), %d duplicated (n,m) with equal values, "
           "%d (n,m) missing besides degree 1, degree-1 terms missing: %d (taken as zero)\n",
           ngfc, nother, ndup, missing, missing_deg1);
    if (strcmp(norm, "fully_normalized") || nother != 0 || missing != 0 || maxdeg != NMAXC || GM == 0.0 || RE == 0.0) {
        fprintf(stderr, "the coefficient file is not what the conventions say\n");
        exit(2);
    }
}

static void tables(int L)
{
    for (int n = 0; n <= L; n++)
        for (int m = 0; m <= n; m++)
            if (n >= m + 2) {
                double dn = n, dm = m;
                An[n][m] = sqrt((2 * dn - 1) * (2 * dn + 1) / ((dn - dm) * (dn + dm)));
                Bn[n][m] = sqrt((2 * dn + 1) * (dn + dm - 1) * (dn - dm - 1) / ((2 * dn - 3) * (dn + dm) * (dn - dm)));
            }
    for (int m = 1; m <= L; m++) Dg[m] = (m == 1) ? sqrt(3.0) : sqrt((2.0 * m + 1) / (2.0 * m));
    for (int m = 0; m <= L; m++) Sd[m] = sqrt(2.0 * m + 3);
    for (int n = 0; n < L; n++) {
        double dn = n, q = (2 * dn + 1) / (2 * dn + 3);
        F1[n] = sqrt((2 * dn + 1) * (dn + 1) * (dn + 2) / (2 * (2 * dn + 3)));
        for (int m = 0; m <= n; m++) {
            double dm = m;
            FA[n][m] = sqrt(q * (dn + dm + 1) * (dn + dm + 2));
            FB[n][m] = (m == 0) ? 0.0 : sqrt(((m == 1) ? 2.0 : 1.0) * q * (dn - dm + 1) * (dn - dm + 2));
            FZ[n][m] = sqrt(q * (dn + dm + 1) * (dn - dm + 1));
        }
    }
}

/* acceleration (m/s^2) at Earth-fixed position r (m), degrees nmin..nmax, nmin >= 2 */
static void grav(const double r[3], int nmin, int nmax, double a[3])
{
    const double Re = RE;
    double x = r[0], y = r[1], z = r[2];
    double r2 = x * x + y * y + z * z;
    double ir2 = 1.0 / r2;
    double rho = Re * Re * ir2;
    double x0 = Re * x * ir2, y0 = Re * y * ir2, z0 = Re * z * ir2;
    int L = nmax + 1;
    V[0][0] = Re / sqrt(r2);
    W[0][0] = 0.0;
    for (int m = 0; m <= L; m++) {
        if (m > 0) {
            V[m][m] = Dg[m] * (x0 * V[m - 1][m - 1] - y0 * W[m - 1][m - 1]);
            W[m][m] = Dg[m] * (x0 * W[m - 1][m - 1] + y0 * V[m - 1][m - 1]);
        }
        if (m < L) {
            double c1 = Sd[m] * z0;
            V[m + 1][m] = c1 * V[m][m];
            W[m + 1][m] = c1 * W[m][m];
        }
        for (int n = m + 2; n <= L; n++) {
            double p = An[n][m] * z0, q = Bn[n][m] * rho;
            V[n][m] = p * V[n - 1][m] - q * V[n - 2][m];
            W[n][m] = p * W[n - 1][m] - q * W[n - 2][m];
        }
    }
    double ax = 0, ay = 0, az = 0;
    for (int n = nmin; n <= nmax; n++) {
        double C0 = Cb[n][0];
        ax -= F1[n] * C0 * V[n + 1][1];
        ay -= F1[n] * C0 * W[n + 1][1];
        az -= FZ[n][0] * C0 * V[n + 1][0];
        for (int m = 1; m <= n; m++) {
            double C = Cb[n][m], S = Sb[n][m];
            double t1 = C * V[n + 1][m + 1] + S * W[n + 1][m + 1];
            double t2 = C * V[n + 1][m - 1] + S * W[n + 1][m - 1];
            double t3 = S * V[n + 1][m + 1] - C * W[n + 1][m + 1];
            double t4 = S * V[n + 1][m - 1] - C * W[n + 1][m - 1];
            double t5 = C * V[n + 1][m] + S * W[n + 1][m];
            ax += -0.5 * FA[n][m] * t1 + 0.5 * FB[n][m] * t2;
            ay += 0.5 * FA[n][m] * t3 + 0.5 * FB[n][m] * t4;
            az -= FZ[n][m] * t5;
        }
    }
    double k = GM / (Re * Re);
    a[0] = k * ax;
    a[1] = k * ay;
    a[2] = k * az;
}

int main(int argc, char **argv)
{
    if (argc < 6) {
        fprintf(stderr, "usage: %s gfc orbit_itrf nmin nmax out [plant_epoch]\n", argv[0]);
        return 2;
    }
    int nmin = atoi(argv[3]), nmax = atoi(argv[4]);
    long plant = (argc > 6) ? atol(argv[6]) : -1;
    int pn = -1, pm = -1; double pdc = 0.0;
    if (argc > 7 && sscanf(argv[7], "%d,%d,%lf", &pn, &pm, &pdc) != 3) { fprintf(stderr, "bad coefficient plant\n"); return 2; }
    if (nmin < 2 || nmax > NMAXC || nmin > nmax) { fprintf(stderr, "degree range must be within 2..%d\n", NMAXC); return 2; }
    read_gfc(argv[1]);
    if (pn >= 0) {
        if (pn > NMAXC || pm < 0 || pm > pn) { fprintf(stderr, "bad coefficient plant\n"); return 2; }
        printf("# coefficient plant: C(%d,%d) %.11e -> %.11e\n", pn, pm, Cb[pn][pm], Cb[pn][pm] + pdc);
        Cb[pn][pm] += pdc;
    }
    tables(nmax + 1);
    FILE *f = fopen(argv[2], "r");
    if (!f) { perror(argv[2]); return 2; }
    FILE *o = fopen(argv[5], "w");
    if (!o) { perror(argv[5]); return 2; }
    char line[1024];
    long k = 0;
    while (fgets(line, sizeof line, f)) {
        double t, r[3];
        if (line[0] == '#' || line[0] == 'g') continue;
        int got = sscanf(line, "%lf %lf %lf %lf", &t, &r[0], &r[1], &r[2]);
        if (got != 4) continue; /* the "-6 1 2880" type line */
        double a[3];
        grav(r, nmin, nmax, a);
        if (k == plant) a[0] = nextafter(a[0], INFINITY);
        fprintf(o, "%.18f %a %a %a %.17e %.17e %.17e\n", t, a[0], a[1], a[2], a[0], a[1], a[2]);
        k++;
    }
    fclose(f);
    fclose(o);
    printf("# epochs: %ld, degrees %d..%d, plant_epoch %ld\n", k, nmin, nmax, plant);
#ifdef __FMA__
    printf("# compiled with __FMA__ defined\n");
#else
    printf("# compiled without __FMA__\n");
#endif
#ifdef __FP_FAST_FMA
    printf("# __FP_FAST_FMA defined\n");
#endif
    return 0;
}
