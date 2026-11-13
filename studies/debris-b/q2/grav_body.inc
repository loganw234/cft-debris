/* grav_body.inc - DEBRIS-B Q2. Spherical-harmonic gravity by the Cunningham
   (V, W) recursion in Earth-fixed Cartesian coordinates, with unnormalised
   coefficients, written from the published formulas (Cunningham 1970;
   Montenbruck & Gill 2000, section 3.2). Included twice by q2bench.c: once
   with REAL = double (SFX _d) and once with REAL = __float128 (SFX _q).

   Operation count per call, read off the loops below (L = nmax + 1):
     setup                         13 mul + 2 add + 2 div + 1 sqrt
     V[n][0], n = 2..L             5 flops each            (L - 1 trips)
     diagonal V[m][m], W[m][m]     8 flops each            (L trips)
     sub-diagonal V[m+1][m]        3 flops each            (L - 1 trips)
     column V[n][m], n >= m+2      8 flops each            ((L-1)(L-2)/2 trips)
     zonal sums (m = 0)            7 flops each            (nmax - n0 + 1 trips)
     tesseral sums (m >= 1)        28 flops each           (sum of n over n0..nmax)
     central term (nmin = 0)       3 flops
     scaling                       4 mul + 1 div
   q2bench.c's grav_flops() evaluates these sums. */
#define CAT_(a, b) a##b
#define CAT(a, b) CAT_(a, b)

static REAL CAT(Cu, SFX)[NA][NA], CAT(Su, SFX)[NA][NA];
static REAL CAT(An, SFX)[NA + 2][NA + 2], CAT(Bn, SFX)[NA + 2][NA + 2];
static REAL CAT(Vw, SFX)[NA + 2][NA + 2], CAT(Ww, SFX)[NA + 2][NA + 2];

static void CAT(grav_tables, SFX)(int N)
{
    for (int n = 0; n <= N; n++)
        for (int m = 0; m <= n; m++) {
            CAT(Cu, SFX)[n][m] = (REAL)GCu[n][m];
            CAT(Su, SFX)[n][m] = (REAL)GSu[n][m];
        }
    for (int n = 0; n <= N + 1; n++)
        for (int m = 0; m <= n; m++)
            if (n >= m + 2) {
                CAT(An, SFX)[n][m] = (REAL)(2 * n - 1) / (REAL)(n - m);
                CAT(Bn, SFX)[n][m] = (REAL)(n + m - 1) / (REAL)(n - m);
            }
}

/* acceleration (km/s^2) at Earth-fixed position r (km) from degrees
   nmin..nmax; nmin = 0 includes the central term, degree 1 is absent by
   construction (geocentric frame) */
static void CAT(grav_accel, SFX)(const REAL r[3], int nmin, int nmax, REAL a[3])
{
    REAL (*V)[NA + 2] = CAT(Vw, SFX);
    REAL (*W)[NA + 2] = CAT(Ww, SFX);
    REAL (*An)[NA + 2] = CAT(An, SFX);
    REAL (*Bn)[NA + 2] = CAT(Bn, SFX);
    REAL (*Cu)[NA] = CAT(Cu, SFX);
    REAL (*Su)[NA] = CAT(Su, SFX);
    const REAL Re = (REAL)R_EARTH, GM = (REAL)GM_EARTH;
    REAL x = r[0], y = r[1], z = r[2];
    REAL r2 = x * x + y * y + z * z;
    REAL ir2 = (REAL)1 / r2;
    REAL rho = Re * Re * ir2;
    REAL x0 = Re * x * ir2, y0 = Re * y * ir2, z0 = Re * z * ir2;
    int L = nmax + 1;
    V[0][0] = Re / SQRT(r2);
    W[0][0] = 0;
    V[1][0] = z0 * V[0][0];
    W[1][0] = 0;
    for (int n = 2; n <= L; n++) {
        REAL p = An[n][0] * z0, q = Bn[n][0] * rho;
        V[n][0] = p * V[n - 1][0] - q * V[n - 2][0];
        W[n][0] = 0;
    }
    for (int m = 1; m <= L; m++) {
        REAL c = (REAL)(2 * m - 1);
        V[m][m] = c * (x0 * V[m - 1][m - 1] - y0 * W[m - 1][m - 1]);
        W[m][m] = c * (x0 * W[m - 1][m - 1] + y0 * V[m - 1][m - 1]);
        if (m < L) {
            REAL c1 = (REAL)(2 * m + 1) * z0;
            V[m + 1][m] = c1 * V[m][m];
            W[m + 1][m] = c1 * W[m][m];
        }
        for (int n = m + 2; n <= L; n++) {
            REAL p = An[n][m] * z0, q = Bn[n][m] * rho;
            V[n][m] = p * V[n - 1][m] - q * V[n - 2][m];
            W[n][m] = p * W[n - 1][m] - q * W[n - 2][m];
        }
    }
    REAL ax = 0, ay = 0, az = 0;
    if (nmin == 0) {
        ax -= V[1][1];
        ay -= W[1][1];
        az -= V[1][0];
    }
    int n0 = nmin < 2 ? 2 : nmin;
    for (int n = n0; n <= nmax; n++) {
        REAL C0 = Cu[n][0];
        ax -= C0 * V[n + 1][1];
        ay -= C0 * W[n + 1][1];
        az -= (REAL)(n + 1) * C0 * V[n + 1][0];
        for (int m = 1; m <= n; m++) {
            REAL C = Cu[n][m], S = Su[n][m];
            REAL F = (REAL)0.5 * (REAL)(n - m + 1) * (REAL)(n - m + 2);
            REAL t1 = C * V[n + 1][m + 1] + S * W[n + 1][m + 1];
            REAL t2 = C * V[n + 1][m - 1] + S * W[n + 1][m - 1];
            REAL t3 = S * V[n + 1][m + 1] - C * W[n + 1][m + 1];
            REAL t4 = S * V[n + 1][m - 1] - C * W[n + 1][m - 1];
            REAL t5 = C * V[n + 1][m] + S * W[n + 1][m];
            ax += (REAL)(-0.5) * t1 + F * t2;
            ay += (REAL)0.5 * t3 + F * t4;
            az -= (REAL)(n - m + 1) * t5;
        }
    }
    REAL k = GM / (Re * Re);
    a[0] = k * ax;
    a[1] = k * ay;
    a[2] = k * az;
}
#undef CAT
#undef CAT_
