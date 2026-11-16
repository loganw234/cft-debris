/* m1_nodes.c - cft-debris M1 (DEBRIS-F): the Earth's orientation at binary256 (the frame table's node
 * routine) and the host time scales. See m1_nodes.h for the equations and their sources.
 *
 * cft-debris, MIT licence (see LICENSE at the repository root). Written by DEBRIS-F, 2026-11-16.
 * Every binary256 operation is one libcft host call over a batch of lanes (one lane a time), round to
 * nearest even, on the software backend. The IERS tables, the Earth orientation file and tai-utc.dat are
 * read at run time from the downloads folder; their numbers enter as decimal strings, each converted once
 * by cft_from_decimal_char. No third-party source is copied here.
 */
#include <ctype.h>
#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "m1_nodes.h"

typedef struct { unsigned char b[32]; } q_t;
#define QF CFT_FP256

/* ------------------------------------------------------------------ libcft, binary256, n lanes */
static cft_device *DV;
static void qck(cft_status st, const char *w)
{
    if (st != CFT_OK) {
        fprintf(stderr, "m1_nodes: libcft %s: %s (%s)\n", w, cft_strerror(st), cft_last_error());
        exit(3);
    }
}
static q_t *qv(size_t n)
{
    q_t *p = (q_t *)calloc(n ? n : 1, sizeof(q_t));
    if (!p) { fprintf(stderr, "m1_nodes: out of memory (%lu)\n", (unsigned long)n); exit(3); }
    return p;
}
static void qrun(cft_op op, q_t *d, const q_t *a, const q_t *b, const q_t *c, size_t n, unsigned sm)
{
    cft_elem_args x;
    uint32_t fl = 0;
    memset(&x, 0, sizeof x);
    x.struct_size = sizeof x;
    x.a = a; x.b = b; x.c = c; x.d = d; x.n = n; x.scalar_mask = sm; x.flags_out = &fl;
    qck(cft_run_ex(DV, op, QF, CFT_RNE, &x), cft_op_name(op));
}
/* s? = 1 when that operand is one element applied to every lane */
static void qadd(q_t *d, const q_t *a, int sa, const q_t *b, int sb, size_t n) { qrun(CFT_ADD, d, a, NULL, b, n, (sa ? 1u : 0u) | (sb ? 4u : 0u)); }
static void qsub(q_t *d, const q_t *a, int sa, const q_t *b, int sb, size_t n) { qrun(CFT_SUB, d, a, NULL, b, n, (sa ? 1u : 0u) | (sb ? 4u : 0u)); }
static void qmul(q_t *d, const q_t *a, int sa, const q_t *b, int sb, size_t n) { qrun(CFT_MUL, d, a, b, NULL, n, (sa ? 1u : 0u) | (sb ? 2u : 0u)); }
static void qfma(q_t *d, const q_t *a, int sa, const q_t *b, int sb, const q_t *c, int sc, size_t n)
{
    qrun(CFT_FMA, d, a, b, c, n, (sa ? 1u : 0u) | (sb ? 2u : 0u) | (sc ? 4u : 0u));
}
static void qneg(q_t *d, const q_t *a, size_t n) { qrun(CFT_NEG, d, a, NULL, NULL, n, 0u); }
static void qfill(q_t *d, const q_t *s, size_t n) { for (size_t i = 0; i < n; i++) d[i] = s[0]; }
static void qdiv(q_t *d, const q_t *a, const q_t *b, size_t n)
{
    uint32_t fl = 0;
    qck(cft_div(DV, QF, CFT_RNE, a, b, d, n, &fl, NULL), "cft_div");
}
static void qdivs(q_t *d, const q_t *a, int sa, const q_t *b, int sb, size_t n)
{
    q_t *aa = (q_t *)a, *bb = (q_t *)b;
    if (sa) { aa = qv(n); qfill(aa, a, n); }
    if (sb) { bb = qv(n); qfill(bb, b, n); }
    qdiv(d, aa, bb, n);
    if (sa) free(aa);
    if (sb) free(bb);
}
static void qsqrt(q_t *d, const q_t *a, size_t n)
{
    uint32_t fl = 0;
    qck(cft_sqrt(DV, QF, CFT_RNE, a, d, n, &fl, NULL), "cft_sqrt");
}
static void qdec1(q_t *d, const char *s)
{
    size_t bad = 0;
    uint32_t fl = 0;
    const char *in[1] = {s};
    if (cft_from_decimal_char(DV, QF, CFT_RNE, in, d, 1, &bad, &fl) != CFT_OK) {
        fprintf(stderr, "m1_nodes: decimal \"%s\" refused\n", s);
        exit(3);
    }
}
static void qf64(q_t *d, const double *s, size_t n)
{
    uint32_t fl = 0;
    qck(cft_convert(DV, CFT_FP64, QF, CFT_RNE, s, d, n, &fl), "cft_convert");
}
static void qto64(double *d, const q_t *s, size_t n)
{
    uint32_t fl = 0;
    qck(cft_convert(DV, QF, CFT_FP64, CFT_RNE, s, d, n, &fl), "cft_convert");
}
static void qi64(q_t *d, const int64_t *s, size_t n)
{
    uint32_t fl = 0;
    qck(cft_cvt_from_i64(DV, QF, CFT_RNE, s, d, n, &fl), "cft_cvt_from_i64");
}
static void qcos(q_t *d, const q_t *a, size_t n) { uint32_t fl = 0; qck(cft_cos(DV, QF, CFT_RNE, a, d, n, &fl), "cft_cos"); }
static void qsin(q_t *d, const q_t *a, size_t n) { uint32_t fl = 0; qck(cft_sin(DV, QF, CFT_RNE, a, d, n, &fl), "cft_sin"); }
static void qcospi(q_t *d, const q_t *a, size_t n) { uint32_t fl = 0; qck(cft_cospi(DV, QF, CFT_RNE, a, d, n, &fl), "cft_cospi"); }
static void qsinpi(q_t *d, const q_t *a, size_t n) { uint32_t fl = 0; qck(cft_sinpi(DV, QF, CFT_RNE, a, d, n, &fl), "cft_sinpi"); }

/* ------------------------------------------------------------------ host time scales (B1) */
int m1n_leaps_load(const char *path, m1n_leap *tab, int cap)
{
    FILE *f = fopen(path, "rb");
    if (!f) return -1;
    char line[256];
    int n = 0;
    while (fgets(line, sizeof line, f)) {
        char *p = strstr(line, "=JD"), *q = strstr(line, "TAI-UTC="), *r = strstr(line, "MJD -"), *s = strstr(line, ") X");
        if (!p || !q || !r || !s || n >= cap) continue;
        if (sscanf(p + 3, "%lf", &tab[n].jd) != 1 || sscanf(q + 8, "%lf", &tab[n].a) != 1 ||
            sscanf(r + 5, "%lf", &tab[n].mjd0) != 1 || sscanf(s + 3, "%lf", &tab[n].rate) != 1)
            continue;
        n++;
    }
    fclose(f);
    return n;
}
double m1n_tai_minus_utc(const m1n_leap *tab, int n, double mjd_utc)
{
    int k = -1;
    for (int i = 0; i < n; i++)
        if (tab[i].jd - 2400000.5 <= mjd_utc) k = i;
    if (k < 0) return 0.0;
    return tab[k].a + (mjd_utc - tab[k].mjd0) * tab[k].rate;
}
/* USNO Circular 179 (Kaplan 2005), eq. (2.6): TDB - TT in seconds, T in Julian centuries of TT from J2000.0;
   stated there to be good to about 10 us from 1600 to 2200 (the model's limit). */
double m1n_tdb_minus_tt(double T)
{
    return 0.001657 * sin(628.3076 * T + 6.2401) + 0.000022 * sin(575.3385 * T + 4.2970) +
           0.000014 * sin(1256.6152 * T + 6.1969) + 0.000005 * sin(606.9777 * T + 4.0212) +
           0.000005 * sin(52.9691 * T + 0.4444) + 0.000002 * sin(21.3299 * T + 5.5431) +
           0.000010 * T * sin(628.3076 * T + 4.2490);
}

/* ------------------------------------------------------------------ the inputs */
#define NARG 14
typedef struct {
    int nterm;
    int *jpow, *arg;          /* per term: power of t, distinct-argument index */
    q_t *as, *ac;             /* per term: sin and cos coefficients, uas */
    q_t poly[6];              /* uas */
} series_t;

typedef struct {
    int mjd;
    q_t v[5];                 /* xp, yp (rad), UT1-UTC (s), dX, dY (rad) */
    double d[5];              /* the same as binary64, for aux output */
    int bulb;                 /* Bulletin B values used */
} eoprow_t;

struct m1n_ctx {
    double jd_epoch, mjd_epoch;
    series_t ser[3];          /* X, Y, s + XY/2 */
    int nargs;
    int (*argm)[NARG];        /* distinct arguments' multipliers */
    int mmax[NARG];
    int *byarg_start, *byarg_s, *byarg_t;   /* terms grouped by argument */
    eoprow_t *eop;
    int neop;
    m1n_leap leap[64];
    int nleap;
    q_t K_ONE, K_TWO, K_HALF, K_PI, K_TWOPI, K_AS2R, K_UAS2R, K_MAS2R, K_86400, K_JC, K_SPRIME, K_ERA0, K_ERA1;
    q_t K_DAY0;               /* (mjd_epoch - 51544.5) days */
    q_t K_DAY0S;              /* the same in seconds */
    q_t dl_c[5][5];           /* Delaunay polynomials, arcsec, powers 0..4 */
    q_t pl_c[9][3];           /* planetary arguments, rad, powers 0..2 */
    q_t taylor_s[12], taylor_c[12];   /* 1/((2m)(2m+1)) and 1/((2m-1)(2m)) */
    double plant_dx, plant_xp;
    char inputs[2048];
};

int m1n_sha256_file(const char *path, char out[65]);

static char *trim(char *s)
{
    while (*s == ' ' || *s == '\t') s++;
    size_t n = strlen(s);
    while (n && (s[n - 1] == ' ' || s[n - 1] == '\r' || s[n - 1] == '\n' || s[n - 1] == '\t')) s[--n] = 0;
    return s;
}

static int find_arg(m1n_ctx *N, const int *m, int *cap)
{
    for (int a = 0; a < N->nargs; a++)
        if (!memcmp(N->argm[a], m, sizeof(int) * NARG)) return a;
    if (N->nargs == *cap) {
        *cap *= 2;
        N->argm = (int (*)[NARG])realloc(N->argm, (size_t)*cap * sizeof(int[NARG]));
    }
    memcpy(N->argm[N->nargs], m, sizeof(int) * NARG);
    return N->nargs++;
}

/* one IERS table: the polynomial part, then "j = J  Number of terms = K" blocks of
   "i a_s a_c l l' F D Om L_Me L_Ve L_E L_Ma L_J L_Sa L_U L_Ne p_A" rows */
static int load_series(m1n_ctx *N, series_t *S, const char *path, int *cap)
{
    FILE *f = fopen(path, "rb");
    if (!f) { fprintf(stderr, "m1_nodes: cannot read %s\n", path); return -1; }
    char line[1024];
    int want_poly = 0, have_poly = 0, j = -1, cap_t = 4096;
    S->nterm = 0;
    S->jpow = (int *)malloc(cap_t * sizeof(int));
    S->arg = (int *)malloc(cap_t * sizeof(int));
    S->as = qv(cap_t);
    S->ac = qv(cap_t);
    for (int p = 0; p < 6; p++) qdec1(&S->poly[p], "0");
    while (fgets(line, sizeof line, f)) {
        char *s = trim(line);
        if (!*s) continue;
        if (!strncmp(s, "Polynomial part", 15)) { want_poly = 1; continue; }
        if (want_poly && !have_poly && (isdigit((unsigned char)s[0]) || s[0] == '-' || s[0] == '+')) {
            /* tokens: [sign] number [t | t^k] ... */
            char buf[1024], *tok;
            snprintf(buf, sizeof buf, "%s", s);
            int sign = 1, pend = 0;
            char num[64] = {0};
            for (tok = strtok(buf, " "); tok; tok = strtok(NULL, " ")) {
                if (!strcmp(tok, "+")) { sign = 1; continue; }
                if (!strcmp(tok, "-")) { sign = -1; continue; }
                if (tok[0] == 't') {
                    int pw = (tok[1] == '^') ? atoi(tok + 2) : 1;
                    if (!pend || pw < 1 || pw > 5) { fprintf(stderr, "m1_nodes: polynomial parse %s\n", path); return -1; }
                    qdec1(&S->poly[pw], num);
                    pend = 0;
                    continue;
                }
                if (pend) qdec1(&S->poly[0], num);
                snprintf(num, sizeof num, "%s%s", sign < 0 ? "-" : "", tok);
                pend = 1;
                sign = 1;
            }
            if (pend) qdec1(&S->poly[0], num);
            have_poly = 1;
            continue;
        }
        if (!strncmp(s, "j = ", 4)) { j = atoi(s + 4); continue; }
        if (j < 0) continue;
        int i, m[NARG];
        char as[64], ac[64];
        if (sscanf(s, "%d %63s %63s %d %d %d %d %d %d %d %d %d %d %d %d %d %d", &i, as, ac, &m[0], &m[1], &m[2], &m[3], &m[4],
                   &m[5], &m[6], &m[7], &m[8], &m[9], &m[10], &m[11], &m[12], &m[13]) != 17)
            continue;
        if (S->nterm == cap_t) { fprintf(stderr, "m1_nodes: too many terms in %s\n", path); return -1; }
        S->jpow[S->nterm] = j;
        S->arg[S->nterm] = find_arg(N, m, cap);
        qdec1(&S->as[S->nterm], as);
        qdec1(&S->ac[S->nterm], ac);
        for (int k = 0; k < NARG; k++)
            if (abs(m[k]) > N->mmax[k]) N->mmax[k] = abs(m[k]);
        S->nterm++;
    }
    fclose(f);
    if (!have_poly || S->nterm == 0) { fprintf(stderr, "m1_nodes: %s: no polynomial or no terms\n", path); return -1; }
    return 0;
}

/* finals2000A: columns per readme.finals2000A (1-based, inclusive). Each quantity from Bulletin B where
   the row carries it, else Bulletin A - the rule Orekit's loader follows (DEBRIS-F's probe, MJD 61270);
   dX and dY blank in both are taken as 0, as Orekit does (lead.md, Phase 0). */
static int field(const char *line, int a, int b, char *out, size_t cap)
{
    size_t len = strlen(line);
    out[0] = 0;
    if ((size_t)a > len) return 0;
    size_t n = 0;
    for (int c = a; c <= b && (size_t)c <= len; c++)
        if (line[c - 1] != ' ' && line[c - 1] != '\r' && line[c - 1] != '\n' && n + 1 < cap) out[n++] = line[c - 1];
    out[n] = 0;
    return n > 0;
}
static int load_eop(m1n_ctx *N, const char *path)
{
    FILE *f = fopen(path, "rb");
    if (!f) { fprintf(stderr, "m1_nodes: cannot read %s\n", path); return -1; }
    char line[512];
    int cap = 512;
    N->eop = (eoprow_t *)calloc(cap, sizeof(eoprow_t));
    N->neop = 0;
    static const int A[5][2] = {{19, 27}, {38, 46}, {59, 68}, {98, 106}, {117, 125}};
    static const int B[5][2] = {{135, 144}, {145, 154}, {155, 165}, {166, 175}, {176, 185}};
    q_t AS = N->K_AS2R, MAS = N->K_MAS2R;
    while (fgets(line, sizeof line, f)) {
        char mj[32];
        if (!field(line, 8, 15, mj, sizeof mj)) continue;
        if (N->neop == cap) { fprintf(stderr, "m1_nodes: EOP file too long\n"); return -1; }
        eoprow_t *r = &N->eop[N->neop];
        r->mjd = (int)floor(atof(mj) + 0.5);
        if (N->neop && r->mjd != N->eop[N->neop - 1].mjd + 1) { fprintf(stderr, "m1_nodes: EOP rows not daily\n"); return -1; }
        r->bulb = 0;
        for (int q = 0; q < 5; q++) {
            char v[32];
            int fromb = field(line, B[q][0], B[q][1], v, sizeof v);
            if (fromb) r->bulb = 1;
            else if (!field(line, A[q][0], A[q][1], v, sizeof v)) {
                if (q >= 3) snprintf(v, sizeof v, "0");
                else { fprintf(stderr, "m1_nodes: EOP MJD %d lacks quantity %d\n", r->mjd, q); return -1; }
            }
            q_t x;
            qdec1(&x, v);
            r->d[q] = atof(v);
            if (q == 0 || q == 1) qmul(&r->v[q], &x, 1, &AS, 1, 1);
            else if (q == 2) r->v[q] = x;
            else qmul(&r->v[q], &x, 1, &MAS, 1, 1);
        }
        N->neop++;
    }
    fclose(f);
    return N->neop > 8 ? 0 : -1;
}

void m1n_plant(m1n_ctx *n, double dx_rad, double xp_rad)
{
    n->plant_dx = dx_rad;
    n->plant_xp = xp_rad;
}
const char *m1n_inputs(const m1n_ctx *n) { return n->inputs; }

m1n_ctx *m1n_open(const char *dl, double jd_epoch)
{
    m1n_ctx *N = (m1n_ctx *)calloc(1, sizeof(m1n_ctx));
    if (!N) return NULL;
    if (!DV && cft_open(NULL, 0, &DV) != CFT_OK) { fprintf(stderr, "m1_nodes: cft_open(NULL) failed\n"); return NULL; }
    N->jd_epoch = jd_epoch;
    N->mjd_epoch = jd_epoch - 2400000.5;
    if (N->mjd_epoch != floor(N->mjd_epoch)) { fprintf(stderr, "m1_nodes: jd_epoch must be an integer MJD\n"); return NULL; }
    /* constants: decimal strings, each converted once */
    qdec1(&N->K_ONE, "1");
    qdec1(&N->K_TWO, "2");
    qdec1(&N->K_HALF, "0.5");
    qdec1(&N->K_PI, "3.141592653589793238462643383279502884197169399375105820974944592307816406286208998628034825342117068");
    qmul(&N->K_TWOPI, &N->K_PI, 1, &N->K_TWO, 1, 1);
    q_t c648000, c1e6, c1e3;
    qdec1(&c648000, "648000");
    qdec1(&c1e6, "1000000");
    qdec1(&c1e3, "1000");
    qdivs(&N->K_AS2R, &N->K_PI, 1, &c648000, 1, 1);          /* rad per arcsec */
    qdivs(&N->K_UAS2R, &N->K_AS2R, 1, &c1e6, 1, 1);          /* rad per uas */
    qdivs(&N->K_MAS2R, &N->K_AS2R, 1, &c1e3, 1, 1);          /* rad per mas */
    qdec1(&N->K_86400, "86400");
    qdec1(&N->K_JC, "3155760000");                         /* seconds in a Julian century */
    q_t sp;
    qdec1(&sp, "-47e-6");                                  /* s' = -47 uas t, eq. (5.13), arcsec */
    qmul(&N->K_SPRIME, &sp, 1, &N->K_AS2R, 1, 1);
    qdec1(&N->K_ERA0, "0.7790572732640");                  /* eq. (5.14) */
    qdec1(&N->K_ERA1, "1.00273781191135448");
    char d0[64];
    snprintf(d0, sizeof d0, "%.1f", N->mjd_epoch - 51544.5);
    qdec1(&N->K_DAY0, d0);
    qmul(&N->K_DAY0S, &N->K_DAY0, 1, &N->K_86400, 1, 1);
    /* eq. (5.43): Delaunay arguments, arcsec (the degree constants times 3600, exact decimals) */
    static const char *DL[5][5] = {
        {"485868.249036", "1717915923.2178", "31.8792", "0.051635", "-0.00024470"},
        {"1287104.793048", "129596581.0481", "-0.5532", "0.000136", "-0.00001149"},
        {"335779.526232", "1739527262.8478", "-12.7512", "-0.001037", "0.00000417"},
        {"1072260.703692", "1602961601.2090", "-6.3706", "0.006593", "-0.00003169"},
        {"450160.398036", "-6962890.5431", "7.4722", "0.007702", "-0.00005939"}};
    for (int a = 0; a < 5; a++)
        for (int p = 0; p < 5; p++) qdec1(&N->dl_c[a][p], DL[a][p]);
    /* eq. (5.44): the planets' mean longitudes and the general precession, rad */
    static const char *PL[9][3] = {
        {"4.402608842", "2608.7903141574", "0"}, {"3.176146697", "1021.3285546211", "0"},
        {"1.753470314", "628.3075849991", "0"},  {"6.203480913", "334.0612426700", "0"},
        {"0.599546497", "52.9690962641", "0"},   {"0.874016757", "21.3299104960", "0"},
        {"5.481293872", "7.4781598567", "0"},    {"5.311886287", "3.8133035638", "0"},
        {"0", "0.02438175", "0.00000538691"}};
    for (int a = 0; a < 9; a++)
        for (int p = 0; p < 3; p++) qdec1(&N->pl_c[a][p], PL[a][p]);
    /* Taylor reciprocals for small angles: sin: 1/((2m)(2m+1)), cos: 1/((2m-1)(2m)), m = 1..12 */
    for (int m = 1; m <= 12; m++) {
        int64_t a = (int64_t)(2 * m) * (2 * m + 1), b = (int64_t)(2 * m - 1) * (2 * m);
        q_t qa, qb;
        qi64(&qa, &a, 1);
        qi64(&qb, &b, 1);
        qdivs(&N->taylor_s[m - 1], &N->K_ONE, 1, &qa, 1, 1);
        qdivs(&N->taylor_c[m - 1], &N->K_ONE, 1, &qb, 1, 1);
    }
    /* the files */
    char p[1024], h[65];
    const char *files[6] = {"tab5.2a.txt/tab5.2a.txt", "tab5.2b.txt/tab5.2b.txt", "tab5.2d.txt/tab5.2d.txt",
                            "finals2000A.daily/finals2000A.daily", "tai-utc.dat/tai-utc.dat", NULL};
    N->inputs[0] = 0;
    for (int i = 0; files[i]; i++) {
        snprintf(p, sizeof p, "%s%s", dl, files[i]);
        if (m1n_sha256_file(p, h)) { fprintf(stderr, "m1_nodes: cannot read %s\n", p); return NULL; }
        size_t L = strlen(N->inputs);
        snprintf(N->inputs + L, sizeof N->inputs - L, "%s%s %s", L ? "; " : "", files[i], h);
    }
    int cap = 2048;
    N->argm = (int (*)[NARG])malloc((size_t)cap * sizeof(int[NARG]));
    for (int s = 0; s < 3; s++) {
        snprintf(p, sizeof p, "%s%s", dl, files[s]);
        if (load_series(N, &N->ser[s], p, &cap)) return NULL;
    }
    /* terms grouped by argument */
    int tot = N->ser[0].nterm + N->ser[1].nterm + N->ser[2].nterm;
    N->byarg_start = (int *)calloc((size_t)N->nargs + 1, sizeof(int));
    N->byarg_s = (int *)malloc((size_t)tot * sizeof(int));
    N->byarg_t = (int *)malloc((size_t)tot * sizeof(int));
    for (int s = 0; s < 3; s++)
        for (int t = 0; t < N->ser[s].nterm; t++) N->byarg_start[N->ser[s].arg[t] + 1]++;
    for (int a = 0; a < N->nargs; a++) N->byarg_start[a + 1] += N->byarg_start[a];
    int *fill = (int *)calloc((size_t)N->nargs, sizeof(int));
    for (int s = 0; s < 3; s++)
        for (int t = 0; t < N->ser[s].nterm; t++) {
            int a = N->ser[s].arg[t], at = N->byarg_start[a] + fill[a]++;
            N->byarg_s[at] = s;
            N->byarg_t[at] = t;
        }
    free(fill);
    snprintf(p, sizeof p, "%s%s", dl, files[3]);
    if (load_eop(N, p)) return NULL;
    snprintf(p, sizeof p, "%s%s", dl, files[4]);
    N->nleap = m1n_leaps_load(p, N->leap, 64);
    if (N->nleap < 10) { fprintf(stderr, "m1_nodes: tai-utc.dat: %d entries\n", N->nleap); return NULL; }
    size_t L = strlen(N->inputs);
    snprintf(N->inputs + L, sizeof N->inputs - L, "; terms X %d Y %d S %d, distinct arguments %d, EOP rows %d (MJD %d..%d), leap entries %d",
             N->ser[0].nterm, N->ser[1].nterm, N->ser[2].nterm, N->nargs, N->neop, N->eop[0].mjd, N->eop[N->neop - 1].mjd, N->nleap);
    return N;
}

void m1n_close(m1n_ctx *N)
{
    if (!N) return;
    for (int s = 0; s < 3; s++) {
        free(N->ser[s].jpow); free(N->ser[s].arg); free(N->ser[s].as); free(N->ser[s].ac);
    }
    free(N->argm); free(N->byarg_start); free(N->byarg_s); free(N->byarg_t); free(N->eop);
    free(N);
}

/* ------------------------------------------------------------------ the series by angle addition */
/* complex product (ar + i ai)(br + i bi), lanes; conj flips b's imaginary part */
static void cmul(q_t *dr, q_t *di, const q_t *ar, const q_t *ai, const q_t *br, const q_t *bi, int conj, q_t *t1, q_t *t2, size_t n)
{
    /* re = ar br - ai bi' ; im = ai br + ar bi'  with bi' = conj ? -bi : bi */
    qmul(t1, ai, 0, bi, 0, n);                 /* ai bi */
    if (!conj) qneg(t1, t1, n);                /* -ai bi' */
    qmul(t2, ai, 0, br, 0, n);                 /* ai br */
    if (conj) {
        q_t *t3 = qv(n);
        qneg(t3, ar, n);
        qfma(di, t3, 0, bi, 0, t2, 0, n);      /* ai br - ar bi */
        free(t3);
    } else {
        qfma(di, ar, 0, bi, 0, t2, 0, n);      /* ai br + ar bi */
    }
    qfma(dr, ar, 0, br, 0, t1, 0, n);
}

/* X, Y, S (= s + XY/2) in rad at tc (TT Julian centuries from J2000), n lanes */
static void series_eval(m1n_ctx *N, const q_t *tc, size_t n, q_t *out[3])
{
    q_t *phi = qv(n), *t1 = qv(n), *t2 = qv(n);
    q_t **pr[NARG], **pi[NARG];
    for (int k = 0; k < NARG; k++) {
        int mm = N->mmax[k] ? N->mmax[k] : 1;
        pr[k] = (q_t **)calloc((size_t)mm + 1, sizeof(q_t *));
        pi[k] = (q_t **)calloc((size_t)mm + 1, sizeof(q_t *));
        /* the argument */
        if (k < 5) {
            qfma(phi, &N->dl_c[k][4], 1, tc, 0, &N->dl_c[k][3], 1, n);
            qfma(phi, phi, 0, tc, 0, &N->dl_c[k][2], 1, n);
            qfma(phi, phi, 0, tc, 0, &N->dl_c[k][1], 1, n);
            qfma(phi, phi, 0, tc, 0, &N->dl_c[k][0], 1, n);
            qmul(phi, phi, 0, &N->K_AS2R, 1, n);
        } else if (k < 13) {
            qfma(phi, &N->pl_c[k - 5][1], 1, tc, 0, &N->pl_c[k - 5][0], 1, n);
        } else {
            qfma(phi, &N->pl_c[8][2], 1, tc, 0, &N->pl_c[8][1], 1, n);
            qmul(phi, phi, 0, tc, 0, n);
        }
        if (!N->mmax[k]) continue;
        pr[k][1] = qv(n);
        pi[k][1] = qv(n);
        qcos(pr[k][1], phi, n);
        qsin(pi[k][1], phi, n);
        for (int m = 2; m <= N->mmax[k]; m++) {
            pr[k][m] = qv(n);
            pi[k][m] = qv(n);
            cmul(pr[k][m], pi[k][m], pr[k][m - 1], pi[k][m - 1], pr[k][1], pi[k][1], 0, t1, t2, n);
        }
    }
    q_t *acc[3][5];
    q_t zero;
    qdec1(&zero, "0");
    for (int s = 0; s < 3; s++)
        for (int j = 0; j < 5; j++) { acc[s][j] = qv(n); qfill(acc[s][j], &zero, n); }
    q_t *zr = qv(n), *zi = qv(n), *wr = qv(n), *wi = qv(n);
    for (int a = 0; a < N->nargs; a++) {
        int first = 1;
        for (int k = 0; k < NARG; k++) {
            int m = N->argm[a][k];
            if (!m) continue;
            int am = abs(m);
            if (first) {
                memcpy(zr, pr[k][am], n * sizeof(q_t));
                if (m > 0) memcpy(zi, pi[k][am], n * sizeof(q_t));
                else qneg(zi, pi[k][am], n);
                first = 0;
            } else {
                cmul(wr, wi, zr, zi, pr[k][am], pi[k][am], m < 0, t1, t2, n);
                q_t *x = zr; zr = wr; wr = x;
                x = zi; zi = wi; wi = x;
            }
        }
        if (first) { /* the zero argument: cos 1, sin 0 */
            qfill(zr, &N->K_ONE, n);
            qfill(zi, &zero, n);
        }
        for (int e = N->byarg_start[a]; e < N->byarg_start[a + 1]; e++) {
            int s = N->byarg_s[e], t = N->byarg_t[e], j = N->ser[s].jpow[t];
            qfma(acc[s][j], &N->ser[s].as[t], 1, zi, 0, acc[s][j], 0, n);
            qfma(acc[s][j], &N->ser[s].ac[t], 1, zr, 0, acc[s][j], 0, n);
        }
    }
    for (int s = 0; s < 3; s++) {
        /* polynomial (Horner), uas */
        q_t *v = out[s];
        qfma(v, &N->ser[s].poly[5], 1, tc, 0, &N->ser[s].poly[4], 1, n);
        for (int p = 3; p >= 0; p--) qfma(v, v, 0, tc, 0, &N->ser[s].poly[p], 1, n);
        /* the non-polynomial part, acc_0 + t (acc_1 + t (acc_2 + t (acc_3 + t acc_4))) */
        qfma(t1, acc[s][4], 0, tc, 0, acc[s][3], 0, n);
        qfma(t1, t1, 0, tc, 0, acc[s][2], 0, n);
        qfma(t1, t1, 0, tc, 0, acc[s][1], 0, n);
        qfma(t1, t1, 0, tc, 0, acc[s][0], 0, n);
        qadd(v, v, 0, t1, 0, n);
        qmul(v, v, 0, &N->K_UAS2R, 1, n);
    }
    for (int s = 0; s < 3; s++)
        for (int j = 0; j < 5; j++) free(acc[s][j]);
    for (int k = 0; k < NARG; k++) {
        for (int m = 1; m <= N->mmax[k]; m++) { free(pr[k][m]); free(pi[k][m]); }
        free(pr[k]); free(pi[k]);
    }
    free(zr); free(zi); free(wr); free(wi); free(phi); free(t1); free(t2);
}

/* ------------------------------------------------------------------ pieces */
/* Lagrange weights at u (lanes) for the npts consecutive integer nodes jlo..jlo+npts-1:
   w_j = c_j prod_{i != j} (u - i), c_j = 1 / prod_{i != j} (j - i) */
static void lag_weights(m1n_ctx *N, const q_t *u, int jlo, int npts, q_t **w, size_t n)
{
    q_t **d = (q_t **)malloc((size_t)npts * sizeof(q_t *));
    for (int i = 0; i < npts; i++) {
        d[i] = qv(n);
        int64_t ji = jlo + i;
        q_t qj;
        qi64(&qj, &ji, 1);
        qsub(d[i], u, 0, &qj, 1, n);
    }
    for (int j = 0; j < npts; j++) {
        int64_t den = 1;
        for (int i = 0; i < npts; i++)
            if (i != j) den *= (int64_t)(j - i);
        q_t qd, c;
        qi64(&qd, &den, 1);
        qdivs(&c, &N->K_ONE, 1, &qd, 1, 1);
        qfill(w[j], &c, n);
        for (int i = 0; i < npts; i++)
            if (i != j) qmul(w[j], w[j], 0, d[i], 0, n);
    }
    for (int i = 0; i < npts; i++) free(d[i]);
    free(d);
}

/* cos and sin of small angles x (|x| < 1e-3, checked), by Taylor series to x^24 */
static void small_cs(m1n_ctx *N, const q_t *x, q_t *c, q_t *s, size_t n)
{
    double *xd = (double *)malloc(n * sizeof(double));
    qto64(xd, x, n);
    for (size_t i = 0; i < n; i++)
        if (!(fabs(xd[i]) < 1e-3)) { fprintf(stderr, "m1_nodes: small angle %g out of range\n", xd[i]); exit(3); }
    free(xd);
    q_t *x2 = qv(n), *t = qv(n), *nx2 = qv(n);
    qmul(x2, x, 0, x, 0, n);
    qneg(nx2, x2, n);
    /* sin x = x (1 - x2/(2.3) (1 - x2/(4.5) (... (1 - x2/(24.25))))) */
    qfill(t, &N->K_ONE, n);
    for (int m = 12; m >= 1; m--) {
        q_t *u = qv(n);
        qmul(u, nx2, 0, &N->taylor_s[m - 1], 1, n);
        qfma(t, u, 0, t, 0, &N->K_ONE, 1, n);
        free(u);
    }
    qmul(s, x, 0, t, 0, n);
    qfill(t, &N->K_ONE, n);
    for (int m = 12; m >= 1; m--) {
        q_t *u = qv(n);
        qmul(u, nx2, 0, &N->taylor_c[m - 1], 1, n);
        qfma(t, u, 0, t, 0, &N->K_ONE, 1, n);
        free(u);
    }
    memcpy(c, t, n * sizeof(q_t));
    free(x2); free(t); free(nx2);
}

/* the Earth orientation data at UTC seconds from mjd_epoch 0h UTC (lanes): 4-point Lagrange on the daily
   rows (two either side), as Orekit's EOPHistory with its default degree 3 (getInterpolationDegree() = 3,
   DEBRIS-F's probe). out[0..4]: xp, yp, UT1-UTC, dX, dY. */
static void eop_at(m1n_ctx *N, const q_t *utc_s, size_t n, q_t *out[5], double *aux_rows)
{
    double *x = (double *)malloc(n * sizeof(double));
    qto64(x, utc_s, n);
    int *k = (int *)malloc(n * sizeof(int));
    q_t *u = qv(n), *g = qv(n), *base = qv(n);
    int64_t *bs = (int64_t *)malloc(n * sizeof(int64_t));
    for (size_t l = 0; l < n; l++) {
        double mjd = N->mjd_epoch + x[l] / 86400.0;
        int r = (int)floor(mjd) - N->eop[0].mjd;
        /* at the file's ends the four rows are the first or last four (u then runs outside [0, 1)) */
        if (r < -1 || r > N->neop) { fprintf(stderr, "m1_nodes: MJD %.6f outside the EOP file\n", mjd); exit(3); }
        if (r < 1) r = 1;
        if (r + 2 >= N->neop) r = N->neop - 3;
        k[l] = r;
        bs[l] = (int64_t)(N->eop[r].mjd - (int)N->mjd_epoch) * 86400;
        if (aux_rows) aux_rows[l] = N->eop[r].bulb;
    }
    qi64(base, bs, n);
    qsub(u, utc_s, 0, base, 0, n);
    qdivs(u, u, 0, &N->K_86400, 1, n);
    q_t *w[4];
    for (int j = 0; j < 4; j++) w[j] = qv(n);
    lag_weights(N, u, -1, 4, w, n);
    for (int q = 0; q < 5; q++) {
        for (int j = 0; j < 4; j++) {
            for (size_t l = 0; l < n; l++) g[l] = N->eop[k[l] + j - 1].v[q];
            if (j == 0) qmul(out[q], w[0], 0, g, 0, n);
            else qfma(out[q], w[j], 0, g, 0, out[q], 0, n);
        }
    }
    for (int j = 0; j < 4; j++) free(w[j]);
    free(x); free(k); free(u); free(g); free(base); free(bs);
}

/* the time scales of lanes t (TDB s from jd_epoch): TT s, UTC s (from mjd_epoch 0h in each scale), TT
   centuries; TDB-TT by eq. (2.6) at TT (two fixed-point passes), on the host in binary64 */
static void times_at(m1n_ctx *N, const double *t, size_t n, q_t *tt, q_t *utc, q_t *tc, double *g_out, double *dat_out)
{
    double *g = (double *)malloc(n * sizeof(double)), *dat = (double *)malloc(n * sizeof(double));
    for (size_t l = 0; l < n; l++) {
        double T0 = ((N->mjd_epoch - 51544.5) * 86400.0 + t[l]) / 3155760000.0;
        double gg = m1n_tdb_minus_tt(T0);
        gg = m1n_tdb_minus_tt(T0 - gg / 3155760000.0);
        g[l] = gg;
        double mjd_utc = N->mjd_epoch + (t[l] - gg - 32.184 - 37.0) / 86400.0;
        dat[l] = m1n_tai_minus_utc(N->leap, N->nleap, mjd_utc);
        double mjd2 = N->mjd_epoch + (t[l] - gg - 32.184 - dat[l]) / 86400.0;
        double dat2 = m1n_tai_minus_utc(N->leap, N->nleap, mjd2);
        if (dat2 != dat[l]) { fprintf(stderr, "m1_nodes: time %.3f sits on a leap second\n", t[l]); exit(3); }
        if (g_out) g_out[l] = gg;
        if (dat_out) dat_out[l] = dat[l];
    }
    q_t *tq = qv(n), *gq = qv(n), *dq = qv(n), c32;
    qf64(tq, t, n);
    qf64(gq, g, n);
    qf64(dq, dat, n);
    qdec1(&c32, "32.184");
    qsub(tt, tq, 0, gq, 0, n);
    qsub(utc, tt, 0, &c32, 1, n);
    qsub(utc, utc, 0, dq, 0, n);
    qadd(tc, tt, 0, &N->K_DAY0S, 1, n);
    qdivs(tc, tc, 0, &N->K_JC, 1, n);
    free(tq); free(gq); free(dq); free(g); free(dat);
}

/* M = Q R W at lanes, given X, Y, S (rad), the EOP quantities, ERA's cos and sin, TT centuries.
   m[9] row-major (GCRS <- ITRS). */
static void assemble(m1n_ctx *N, const q_t *X, const q_t *Y, const q_t *S, q_t *eop[5], const q_t *cE, const q_t *sE,
                     const q_t *tc, size_t n, q_t *m[9], double *aux, int aux_stride)
{
    q_t *Xc = qv(n), *Yc = qv(n), *s = qv(n), *t = qv(n), *X2 = qv(n), *Y2 = qv(n), *XY = qv(n), *Z = qv(n), *a = qv(n), *na = qv(n);
    q_t *q0[9], *Q[9], *P[9], *Wm[9], *RW[9];
    for (int i = 0; i < 9; i++) { q0[i] = qv(n); Q[i] = qv(n); P[i] = qv(n); Wm[i] = qv(n); RW[i] = qv(n); }
    /* X, Y with the observed offsets; s = (s + XY/2) - XY/2 with the corrected X, Y (as Orekit's CIRF does) */
    qadd(Xc, X, 0, eop[3], 0, n);
    qadd(Yc, Y, 0, eop[4], 0, n);
    if (N->plant_dx != 0.0) { q_t pd; qf64(&pd, &N->plant_dx, 1); qadd(Xc, Xc, 0, &pd, 1, n); }
    qmul(XY, Xc, 0, Yc, 0, n);
    qmul(t, XY, 0, &N->K_HALF, 1, n);
    qsub(s, S, 0, t, 0, n);
    qmul(X2, Xc, 0, Xc, 0, n);
    qmul(Y2, Yc, 0, Yc, 0, n);
    qadd(t, X2, 0, Y2, 0, n);
    qsub(t, &N->K_ONE, 1, t, 0, n);
    qsqrt(Z, t, n);
    qadd(t, &N->K_ONE, 1, Z, 0, n);
    qdivs(a, &N->K_ONE, 1, t, 0, n);
    qneg(na, a, n);
    /* eq. (5.10) */
    qfma(q0[0], na, 0, X2, 0, &N->K_ONE, 1, n);
    qmul(q0[1], na, 0, XY, 0, n);
    memcpy(q0[2], Xc, n * sizeof(q_t));
    memcpy(q0[3], q0[1], n * sizeof(q_t));
    qfma(q0[4], na, 0, Y2, 0, &N->K_ONE, 1, n);
    memcpy(q0[5], Yc, n * sizeof(q_t));
    qneg(q0[6], Xc, n);
    qneg(q0[7], Yc, n);
    memcpy(q0[8], Z, n * sizeof(q_t));
    q_t *cs = qv(n), *ss = qv(n), *u = qv(n);
    small_cs(N, s, cs, ss, n);
    for (int i = 0; i < 3; i++) { /* times R3(s) = [[c, s, 0], [-s, c, 0], [0, 0, 1]] */
        qmul(u, q0[3 * i + 1], 0, ss, 0, n);
        qneg(u, u, n);
        qfma(Q[3 * i], q0[3 * i], 0, cs, 0, u, 0, n);
        qmul(u, q0[3 * i + 1], 0, cs, 0, n);
        qfma(Q[3 * i + 1], q0[3 * i], 0, ss, 0, u, 0, n);
        memcpy(Q[3 * i + 2], q0[3 * i + 2], n * sizeof(q_t));
    }
    /* W = R3(-s') R2(xp) R1(yp), eq. (5.3) */
    q_t *xp = qv(n), *cx = qv(n), *sx = qv(n), *cy = qv(n), *sy = qv(n), *cp = qv(n), *sp = qv(n), *spr = qv(n);
    memcpy(xp, eop[0], n * sizeof(q_t));
    if (N->plant_xp != 0.0) { q_t pd; qf64(&pd, &N->plant_xp, 1); qadd(xp, xp, 0, &pd, 1, n); }
    small_cs(N, xp, cx, sx, n);
    small_cs(N, eop[1], cy, sy, n);
    qmul(spr, &N->K_SPRIME, 1, tc, 0, n);
    small_cs(N, spr, cp, sp, n);
    /* P = R2(xp) R1(yp) = [[cx, sx sy, -sx cy], [0, cy, sy], [sx, -cx sy, cx cy]] */
    memcpy(P[0], cx, n * sizeof(q_t));
    qmul(P[1], sx, 0, sy, 0, n);
    qmul(P[2], sx, 0, cy, 0, n);
    qneg(P[2], P[2], n);
    q_t zero;
    qdec1(&zero, "0");
    qfill(P[3], &zero, n);
    memcpy(P[4], cy, n * sizeof(q_t));
    memcpy(P[5], sy, n * sizeof(q_t));
    memcpy(P[6], sx, n * sizeof(q_t));
    qmul(P[7], cx, 0, sy, 0, n);
    qneg(P[7], P[7], n);
    qmul(P[8], cx, 0, cy, 0, n);
    for (int j = 0; j < 3; j++) { /* R3(-s') = [[c, -s, 0], [s, c, 0], [0, 0, 1]] */
        qmul(u, sp, 0, P[3 + j], 0, n);
        qneg(u, u, n);
        qfma(Wm[j], cp, 0, P[j], 0, u, 0, n);
        qmul(u, cp, 0, P[3 + j], 0, n);
        qfma(Wm[3 + j], sp, 0, P[j], 0, u, 0, n);
        memcpy(Wm[6 + j], P[6 + j], n * sizeof(q_t));
    }
    for (int j = 0; j < 3; j++) { /* R3(-ERA) = [[c, -s, 0], [s, c, 0], [0, 0, 1]], eq. (5.5) */
        qmul(u, sE, 0, Wm[3 + j], 0, n);
        qneg(u, u, n);
        qfma(RW[j], cE, 0, Wm[j], 0, u, 0, n);
        qmul(u, cE, 0, Wm[3 + j], 0, n);
        qfma(RW[3 + j], sE, 0, Wm[j], 0, u, 0, n);
        memcpy(RW[6 + j], Wm[6 + j], n * sizeof(q_t));
    }
    for (int i = 0; i < 3; i++)
        for (int j = 0; j < 3; j++) {
            qmul(m[3 * i + j], Q[3 * i], 0, RW[j], 0, n);
            qfma(m[3 * i + j], Q[3 * i + 1], 0, RW[3 + j], 0, m[3 * i + j], 0, n);
            qfma(m[3 * i + j], Q[3 * i + 2], 0, RW[6 + j], 0, m[3 * i + j], 0, n);
        }
    if (aux) {
        double *d = (double *)malloc(n * sizeof(double));
        const q_t *src[7] = {Xc, Yc, s, eop[0], eop[1], eop[2], NULL};
        int col[6] = {0, 1, 2, 4, 5, 6};
        for (int c = 0; c < 6; c++) {
            qto64(d, src[c], n);
            for (size_t l = 0; l < n; l++) aux[l * aux_stride + col[c]] = d[l];
        }
        qto64(d, eop[3], n);
        for (size_t l = 0; l < n; l++) aux[l * aux_stride + 7] = d[l];
        qto64(d, eop[4], n);
        for (size_t l = 0; l < n; l++) aux[l * aux_stride + 8] = d[l];
        free(d);
    }
    for (int i = 0; i < 9; i++) { free(q0[i]); free(Q[i]); free(P[i]); free(Wm[i]); free(RW[i]); }
    free(Xc); free(Yc); free(s); free(t); free(X2); free(Y2); free(XY); free(Z); free(a); free(na);
    free(cs); free(ss); free(u); free(xp); free(cx); free(sx); free(cy); free(sy); free(cp); free(sp); free(spr);
}

/* ERA's turns (0.7790572732640 + 1.00273781191135448 Tu, eq. 5.14) at lanes, reduced by an integer on the host */
static void era_turns(m1n_ctx *N, const q_t *utc, const q_t *dut1, q_t *f, size_t n)
{
    q_t *tu = qv(n);
    qadd(tu, utc, 0, dut1, 0, n);                       /* UT1 s from mjd_epoch 0h */
    qdivs(tu, tu, 0, &N->K_86400, 1, n);
    qadd(tu, tu, 0, &N->K_DAY0, 1, n);                  /* Tu */
    qfma(f, &N->K_ERA1, 1, tu, 0, &N->K_ERA0, 1, n);
    double *fd = (double *)malloc(n * sizeof(double));
    int64_t *k = (int64_t *)malloc(n * sizeof(int64_t));
    qto64(fd, f, n);
    for (size_t l = 0; l < n; l++) k[l] = (int64_t)floor(fd[l]);
    q_t *kq = qv(n);
    qi64(kq, k, n);
    qsub(f, f, 0, kq, 0, n);
    free(fd); free(k); free(kq); free(tu);
}

/* ------------------------------------------------------------------ direct evaluation */
static void direct_M(m1n_ctx *N, const double *t, size_t n, q_t *m[9], double *aux)
{
    q_t *tt = qv(n), *utc = qv(n), *tc = qv(n), *e[5], *X = qv(n), *Y = qv(n), *S = qv(n), *f = qv(n), *f2 = qv(n), *cE = qv(n), *sE = qv(n);
    double *g = (double *)malloc(n * sizeof(double));
    for (int q = 0; q < 5; q++) e[q] = qv(n);
    times_at(N, t, n, tt, utc, tc, g, NULL);
    q_t *xs[3] = {X, Y, S};
    series_eval(N, tc, n, xs);
    eop_at(N, utc, n, e, NULL);
    era_turns(N, utc, e[2], f, n);
    qadd(f2, f, 0, f, 0, n);
    qcospi(cE, f2, n);
    qsinpi(sE, f2, n);
    assemble(N, X, Y, S, e, cE, sE, tc, n, m, aux, 10);
    if (aux) {
        double *d = (double *)malloc(n * sizeof(double));
        qto64(d, f, n);
        for (size_t l = 0; l < n; l++) { aux[l * 10 + 3] = d[l]; aux[l * 10 + 9] = g[l]; }
        free(d);
    }
    for (int q = 0; q < 5; q++) free(e[q]);
    free(tt); free(utc); free(tc); free(X); free(Y); free(S); free(f); free(f2); free(cE); free(sE); free(g);
}

/* Omega from M at t - eps, t, t + eps: [Omega x] = Mdot M^T, Mdot = (M+ - M-) / (2 eps); each component the
   mean of the antisymmetric pair */
static void omega_from(m1n_ctx *N, q_t *mm[9], q_t *m0[9], q_t *mp[9], const q_t *inv2eps, size_t n, q_t *om[3])
{
    q_t *md[9], *A[9];
    for (int i = 0; i < 9; i++) {
        md[i] = qv(n);
        A[i] = qv(n);
        qsub(md[i], mp[i], 0, mm[i], 0, n);
        qmul(md[i], md[i], 0, inv2eps, 1, n);
    }
    for (int i = 0; i < 3; i++)
        for (int j = 0; j < 3; j++) {
            qmul(A[3 * i + j], md[3 * i], 0, m0[3 * j], 0, n);
            qfma(A[3 * i + j], md[3 * i + 1], 0, m0[3 * j + 1], 0, A[3 * i + j], 0, n);
            qfma(A[3 * i + j], md[3 * i + 2], 0, m0[3 * j + 2], 0, A[3 * i + j], 0, n);
        }
    qsub(om[0], A[7], 0, A[5], 0, n);
    qsub(om[1], A[2], 0, A[6], 0, n);
    qsub(om[2], A[3], 0, A[1], 0, n);
    for (int k = 0; k < 3; k++) qmul(om[k], om[k], 0, &N->K_HALF, 1, n);
    for (int i = 0; i < 9; i++) { free(md[i]); free(A[i]); }
}

#define EPS_S 0.125
int m1n_direct(m1n_ctx *N, const double *t, size_t nt, unsigned char *out, double *aux)
{
    q_t *m0[9], *mm[9], *mp[9], *om[3];
    for (int i = 0; i < 9; i++) { m0[i] = qv(nt); mm[i] = qv(nt); mp[i] = qv(nt); }
    for (int k = 0; k < 3; k++) om[k] = qv(nt);
    double *tm = (double *)malloc(nt * sizeof(double)), *tp = (double *)malloc(nt * sizeof(double));
    for (size_t l = 0; l < nt; l++) { tm[l] = t[l] - EPS_S; tp[l] = t[l] + EPS_S; }
    direct_M(N, t, nt, m0, aux);
    direct_M(N, tm, nt, mm, NULL);
    direct_M(N, tp, nt, mp, NULL);
    q_t i2e;
    qdec1(&i2e, "4");   /* 1 / (2 x 0.125 s) */
    omega_from(N, mm, m0, mp, &i2e, nt, om);
    for (size_t l = 0; l < nt; l++) {
        for (int i = 0; i < 9; i++) memcpy(out + (l * M1N_NCOL + i) * 32, &m0[i][l], 32);
        for (int k = 0; k < 3; k++) memcpy(out + (l * M1N_NCOL + 9 + k) * 32, &om[k][l], 32);
    }
    for (int i = 0; i < 9; i++) { free(m0[i]); free(mm[i]); free(mp[i]); }
    for (int k = 0; k < 3; k++) free(om[k]);
    free(tm); free(tp);
    return 0;
}

int m1n_times(m1n_ctx *N, const double *t, size_t n, double *out)
{
    q_t *tt = qv(n), *utc = qv(n), *tc = qv(n), *e[5], *ta = qv(n), c32;
    double *g = (double *)malloc(n * sizeof(double)), *dat = (double *)malloc(n * sizeof(double)), *d = (double *)malloc(n * sizeof(double));
    for (int q = 0; q < 5; q++) e[q] = qv(n);
    times_at(N, t, n, tt, utc, tc, g, dat);
    eop_at(N, utc, n, e, NULL);
    qdec1(&c32, "32.184");
    qsub(ta, tt, 0, &c32, 1, n);
    qto64(d, ta, n);
    for (size_t l = 0; l < n; l++) { out[5 * l] = d[l]; out[5 * l + 1] = dat[l]; out[5 * l + 2] = 32.184; out[5 * l + 3] = g[l]; }
    qto64(d, e[2], n);
    for (size_t l = 0; l < n; l++) out[5 * l + 4] = d[l];
    for (int q = 0; q < 5; q++) free(e[q]);
    free(tt); free(utc); free(tc); free(ta); free(g); free(dat); free(d);
    return 0;
}
double m1n_dat(const m1n_ctx *N, double mjd_utc) { return m1n_tai_minus_utc(N->leap, N->nleap, mjd_utc); }
int m1n_set_leaps(m1n_ctx *N, const char *path)
{
    char h[65];
    N->nleap = m1n_leaps_load(path, N->leap, 64);
    if (N->nleap < 1 || m1n_sha256_file(path, h)) return -1;
    size_t L = strlen(N->inputs);
    snprintf(N->inputs + L, sizeof N->inputs - L, "; LEAP TABLE REPLACED: %s %s (%d entries)", path, h, N->nleap);
    return 0;
}

/* ------------------------------------------------------------------ the table */
#define NC_PTS 8   /* coarse interpolation: 8-point Lagrange, nodes K-3 .. K+4 */
#define CHUNK 1024

int m1n_build(m1n_ctx *N, double t0, double h, long nk, const char *path, const char *note)
{
    if (nk < 8 || !(h > 0) || frexp(h, &(int){0}) != 0.5) { fprintf(stderr, "m1_nodes: h must be a power of two\n"); return -1; }
    const double H = 64.0 * h;
    const double tlast = t0 + (double)(nk - 1) * h;
    /* coarse nodes, covering every t_k +- eps with an 8-point stencil */
    const double TC0 = H * floor((t0 - EPS_S) / H) - 3.0 * H;
    const long NCo = (long)floor((tlast + EPS_S - TC0) / H) + 5;
    double *tcs = (double *)malloc((size_t)NCo * sizeof(double));
    for (long K = 0; K < NCo; K++) tcs[K] = TC0 + (double)K * H;
    q_t *ctt = qv(NCo), *cut = qv(NCo), *ctc = qv(NCo), *CX = qv(NCo), *CY = qv(NCo), *CS = qv(NCo);
    times_at(N, tcs, NCo, ctt, cut, ctc, NULL, NULL);
    q_t *cx[3] = {CX, CY, CS};
    series_eval(N, ctc, NCo, cx);
    /* ERA by angle addition: z_k = z_0 e^k, e = exp(2 pi i Delta), Delta = 1.00273781191135448 h / 86400 turns */
    q_t B, Dl, Dl2, er, ei, f0q, f02;
    q_t h_q;
    qf64(&h_q, &h, 1);
    qdivs(&B, &N->K_ERA1, 1, &N->K_86400, 1, 1);
    qmul(&Dl, &B, 1, &h_q, 1, 1);
    qadd(&Dl2, &Dl, 1, &Dl, 1, 1);
    qcospi(&er, &Dl2, 1);
    qsinpi(&ei, &Dl2, 1);
    q_t tt0, ut0, tc0, *e0[5], g0q;
    for (int q = 0; q < 5; q++) e0[q] = qv(1);
    double g0, dat0;
    times_at(N, &t0, 1, &tt0, &ut0, &tc0, &g0, &dat0);
    eop_at(N, &ut0, 1, e0, NULL);
    era_turns(N, &ut0, e0[2], &f0q, 1);
    qadd(&f02, &f0q, 1, &f0q, 1, 1);
    q_t *zr = qv(nk), *zi = qv(nk), t1, t2;
    qcospi(&zr[0], &f02, 1);
    qsinpi(&zi[0], &f02, 1);
    for (long k = 1; k < nk; k++) cmul(&zr[k], &zi[k], &zr[k - 1], &zi[k - 1], &er, &ei, 0, &t1, &t2, 1);
    qf64(&g0q, &g0, 1);
    FILE *f = fopen(path, "wb");
    if (!f) { fprintf(stderr, "m1_nodes: cannot write %s\n", path); return -1; }
    fprintf(f, "M1FRAME 1\njd_epoch %.1f\nt0 %a\nh %a\nnk %ld\nncol %d\nformat binary256-le\neps %a\nH %a\nTC0 %a\nNC %ld\n",
            N->jd_epoch, t0, h, nk, M1N_NCOL, EPS_S, H, TC0, NCo);
    fprintf(f, "t0_dec %.9f\ntlast_dec %.9f\nplant_dx %a\nplant_xp %a\nnote %s\ninputs %s\nEND\n", t0, tlast, N->plant_dx, N->plant_xp,
            note ? note : "", N->inputs);
    q_t i2e;
    qdec1(&i2e, "4");
    for (long c0 = 0; c0 < nk; c0 += CHUNK) {
        size_t n = (size_t)((nk - c0) < CHUNK ? (nk - c0) : CHUNK);
        q_t *mset[3][9], *om[3];
        for (int o = 0; o < 3; o++)
            for (int i = 0; i < 9; i++) mset[o][i] = qv(n);
        for (int k = 0; k < 3; k++) om[k] = qv(n);
        for (int o = 0; o < 3; o++) {
            const double tau = (o == 0) ? -EPS_S : (o == 1) ? 0.0 : EPS_S;
            double *t = (double *)malloc(n * sizeof(double)), *g = (double *)malloc(n * sizeof(double)), *dat = (double *)malloc(n * sizeof(double));
            for (size_t l = 0; l < n; l++) t[l] = t0 + (double)(c0 + (long)l) * h + tau;
            q_t *tt = qv(n), *utc = qv(n), *tc = qv(n), *e[5], *X = qv(n), *Y = qv(n), *S = qv(n), *u = qv(n), *gq = qv(n);
            for (int q = 0; q < 5; q++) e[q] = qv(n);
            times_at(N, t, n, tt, utc, tc, g, dat);
            for (size_t l = 0; l < n; l++)
                if (dat[l] != dat0) { fprintf(stderr, "m1_nodes: a leap second inside the table's window\n"); return -1; }
            eop_at(N, utc, n, e, NULL);
            /* coarse interpolation of X, Y, S: K = floor((t - TC0)/H), u = (t - TC0 - K H)/H, exact */
            long *K = (long *)malloc(n * sizeof(long));
            double *ud = (double *)malloc(n * sizeof(double));
            for (size_t l = 0; l < n; l++) {
                K[l] = (long)floor((t[l] - TC0) / H);
                ud[l] = (t[l] - TC0 - (double)K[l] * H) / H;
                if (K[l] < 3 || K[l] + 4 >= NCo) { fprintf(stderr, "m1_nodes: coarse stencil out of range\n"); return -1; }
            }
            qf64(u, ud, n);
            q_t *w[NC_PTS], *gath = qv(n);
            for (int j = 0; j < NC_PTS; j++) w[j] = qv(n);
            lag_weights(N, u, -3, NC_PTS, w, n);
            q_t *dst[3] = {X, Y, S}, *src[3] = {CX, CY, CS};
            for (int s = 0; s < 3; s++)
                for (int j = 0; j < NC_PTS; j++) {
                    for (size_t l = 0; l < n; l++) gath[l] = src[s][K[l] + j - 3];
                    if (j == 0) qmul(dst[s], w[0], 0, gath, 0, n);
                    else qfma(dst[s], w[j], 0, gath, 0, dst[s], 0, n);
                }
            /* ERA: 2 pi (f0 + k Delta + delta), delta = B (tau - (g - g0) + (dut1 - dut1_0)) turns, cos and sin of
               2 pi delta by Taylor, rotated by z_k */
            q_t *dl = qv(n), *x = qv(n), *cd = qv(n), *sd = qv(n), *cE = qv(n), *sE = qv(n), *a1 = qv(n), *a2 = qv(n);
            q_t tq;
            qf64(&tq, &tau, 1);
            qf64(gq, g, n);
            qsub(dl, e[2], 0, e0[2], 1, n);                 /* dut1 - dut1_0 */
            qsub(gq, gq, 0, &g0q, 1, n);                    /* g - g0 */
            qsub(dl, dl, 0, gq, 0, n);
            qadd(dl, dl, 0, &tq, 1, n);
            qmul(dl, dl, 0, &B, 1, n);
            qmul(x, dl, 0, &N->K_TWOPI, 1, n);
            small_cs(N, x, cd, sd, n);
            for (size_t l = 0; l < n; l++) { a1[l] = zr[c0 + (long)l]; a2[l] = zi[c0 + (long)l]; }
            q_t *s1 = qv(n), *s2 = qv(n);
            cmul(cE, sE, a1, a2, cd, sd, 0, s1, s2, n);
            assemble(N, X, Y, S, e, cE, sE, tc, n, mset[o], NULL, 0);
            for (int j = 0; j < NC_PTS; j++) free(w[j]);
            for (int q = 0; q < 5; q++) free(e[q]);
            free(gath); free(K); free(ud); free(t); free(g); free(dat); free(tt); free(utc); free(tc); free(X); free(Y); free(S); free(u);
            free(gq); free(dl); free(x); free(cd); free(sd); free(cE); free(sE); free(a1); free(a2); free(s1); free(s2);
        }
        omega_from(N, mset[0], mset[1], mset[2], &i2e, n, om);
        unsigned char *buf = (unsigned char *)malloc(n * M1N_NCOL * 32);
        for (size_t l = 0; l < n; l++) {
            for (int i = 0; i < 9; i++) memcpy(buf + (l * M1N_NCOL + i) * 32, &mset[1][i][l], 32);
            for (int k = 0; k < 3; k++) memcpy(buf + (l * M1N_NCOL + 9 + k) * 32, &om[k][l], 32);
        }
        fwrite(buf, 32, n * M1N_NCOL, f);
        free(buf);
        for (int o = 0; o < 3; o++)
            for (int i = 0; i < 9; i++) free(mset[o][i]);
        for (int k = 0; k < 3; k++) free(om[k]);
    }
    fclose(f);
    for (int q = 0; q < 5; q++) free(e0[q]);
    free(tcs); free(ctt); free(cut); free(ctc); free(CX); free(CY); free(CS); free(zr); free(zi);
    return 0;
}

/* ------------------------------------------------------------------ SHA-256 (FIPS 180-4), for the logs */
typedef struct { uint32_t h[8]; uint64_t len; unsigned char buf[64]; size_t nb; } sha_t;
static const uint32_t SK[64] = {
    0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5, 0xd807aa98, 0x12835b01,
    0x243185be, 0x550c7dc3, 0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174, 0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc,
    0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da, 0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7, 0xc6e00bf3, 0xd5a79147,
    0x06ca6351, 0x14292967, 0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13, 0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85,
    0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3, 0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070, 0x19a4c116, 0x1e376c08,
    0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3, 0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208,
    0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2};
#define ROR(x, n) (((x) >> (n)) | ((x) << (32 - (n))))
static void sha_block(sha_t *s, const unsigned char *p)
{
    uint32_t w[64], a, b, c, d, e, f, g, h;
    for (int i = 0; i < 16; i++) w[i] = (uint32_t)p[4 * i] << 24 | (uint32_t)p[4 * i + 1] << 16 | (uint32_t)p[4 * i + 2] << 8 | p[4 * i + 3];
    for (int i = 16; i < 64; i++) {
        uint32_t s0 = ROR(w[i - 15], 7) ^ ROR(w[i - 15], 18) ^ (w[i - 15] >> 3), s1 = ROR(w[i - 2], 17) ^ ROR(w[i - 2], 19) ^ (w[i - 2] >> 10);
        w[i] = w[i - 16] + s0 + w[i - 7] + s1;
    }
    a = s->h[0]; b = s->h[1]; c = s->h[2]; d = s->h[3]; e = s->h[4]; f = s->h[5]; g = s->h[6]; h = s->h[7];
    for (int i = 0; i < 64; i++) {
        uint32_t S1 = ROR(e, 6) ^ ROR(e, 11) ^ ROR(e, 25), ch = (e & f) ^ (~e & g), t1 = h + S1 + ch + SK[i] + w[i];
        uint32_t S0 = ROR(a, 2) ^ ROR(a, 13) ^ ROR(a, 22), mj = (a & b) ^ (a & c) ^ (b & c), t2 = S0 + mj;
        h = g; g = f; f = e; e = d + t1; d = c; c = b; b = a; a = t1 + t2;
    }
    s->h[0] += a; s->h[1] += b; s->h[2] += c; s->h[3] += d; s->h[4] += e; s->h[5] += f; s->h[6] += g; s->h[7] += h;
}
int m1n_sha256_file(const char *path, char out[65])
{
    FILE *f = fopen(path, "rb");
    if (!f) return -1;
    sha_t s = {{0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a, 0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19}, 0, {0}, 0};
    unsigned char b[65536];
    size_t r;
    while ((r = fread(b, 1, sizeof b, f)) > 0) {
        for (size_t i = 0; i < r; i++) {
            s.buf[s.nb++] = b[i];
            if (s.nb == 64) { sha_block(&s, s.buf); s.nb = 0; }
        }
        s.len += r;
    }
    fclose(f);
    uint64_t bits = s.len * 8;
    s.buf[s.nb++] = 0x80;
    if (s.nb > 56) { while (s.nb < 64) s.buf[s.nb++] = 0; sha_block(&s, s.buf); s.nb = 0; }
    while (s.nb < 56) s.buf[s.nb++] = 0;
    for (int i = 7; i >= 0; i--) s.buf[s.nb++] = (unsigned char)(bits >> (8 * i));
    sha_block(&s, s.buf);
    for (int i = 0; i < 8; i++) snprintf(out + 8 * i, 9, "%08x", s.h[i]);
    return 0;
}
