/* h_fitdiag.c - cft-debris M1 (DEBRIS-H): a diagnostic of DEBRIS-F's fit (tests/m1f.c fit) on two machines.
 *
 * cft-debris, MIT licence (see LICENSE at the repository root). Written by DEBRIS-H, 2026-11-18. It copies, unchanged in
 * what they compute, tests/m1f.c's object reader (the OBJ and O lines), span_run, obs_cb and lsq (DEBRIS-F's,
 * cft-debris's own, MIT), and adds dumps. src/ is used as it is.
 *
 *   h_fitdiag <table> <fit input> <key> <out prefix> [--iters N]
 *
 * It runs N iterations (default 1) of m1f fit's Gauss-Newton for the object <key> of <fit input>, exactly as m1f does,
 * and writes:
 *   <prefix>.calls  every call the native kinds make to the C library's exp, asin, acos, sin and cos during the first
 *                   iteration's span, one a line: "E|A|C|S|K argument result" (binary64 bits, hex). The program is linked
 *                   with -Wl,--wrap=exp,--wrap=asin,--wrap=acos,--wrap=sin,--wrap=cos, so the kind objects' calls come
 *                   here first and go on to the C library's own functions;
 *   <prefix>.jr     for each iteration: the residuals (3 x nobs), J (3 x nobs x np, row-major) and lsq's dp, as %a;
 *                   and the 8 lanes' positions at every observation of the first iteration;
 * and prints m1f's ITER and FIT lines, the x87 control word and MXCSR at main.
 */
#define __USE_MINGW_ANSI_STDIO 1
#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "m1.h"

#define JD_EPOCH 2461329.5
static m1_gfc G;
static m1_de DE;
static m1_ftab FT;

/* ------------------------------------------------------------------ the wrapped C library */
static FILE *g_calls = NULL;
static unsigned long long g_ncalls = 0;
double __real_exp(double), __real_asin(double), __real_acos(double), __real_sin(double), __real_cos(double);
static void logcall(char f, double x, double y)
{
    if (!g_calls) return;
    uint64_t a, b;
    memcpy(&a, &x, 8);
    memcpy(&b, &y, 8);
    fprintf(g_calls, "%c %016llx %016llx\n", f, (unsigned long long)a, (unsigned long long)b);
    g_ncalls++;
}
double __wrap_exp(double x) { double y = __real_exp(x); logcall('E', x, y); return y; }
double __wrap_asin(double x) { double y = __real_asin(x); logcall('A', x, y); return y; }
double __wrap_acos(double x) { double y = __real_acos(x); logcall('C', x, y); return y; }
double __wrap_sin(double x) { double y = __real_sin(x); logcall('S', x, y); return y; }
double __wrap_cos(double x) { double y = __real_cos(x); logcall('K', x, y); return y; }

/* ------------------------------------------------------------------ m1f.c's set-up */
static const char *opt(int argc, char **argv, const char *o, const char *def)
{
    for (int i = 0; i + 1 < argc; i++)
        if (!strcmp(argv[i], o)) return argv[i + 1];
    return def;
}
static m1_model model_real(void)
{
    m1_model m;
    memset(&m, 0, sizeof m);
    m.central = 1;
    m.nmin = 2;
    m.nmax = 20;
    m.sun = m.moon = m.drag = m.srp = 1;
    m.nbands = 28;
    m.jd_epoch = JD_EPOCH;
    m.frame = 1;
    m.ftab = &FT;
    return m;
}
typedef struct K {
    const m1_vt *vt;
    m1_ctx c;
} K;
static void *vnew(const K *k, size_t n)
{
    void *p = calloc(n ? n : 1, k->vt->esz);
    if (!p) m1_die("out of memory");
    return p;
}
typedef struct {
    char id[32];
    double t0;
    double y[6], bc, cram;
    int fitbc;
    long nobs;
    double (*obs)[3];
} Obj;
static int read_obj(const char *path, const char *key, Obj *o)
{
    FILE *f = fopen(path, "rb");
    if (!f) m1_die("cannot read %s", path);
    char line[2048];
    int in = 0, done = 0;
    long got = 0, nt = 0;
    while (fgets(line, sizeof line, f) && !done) {
        if (!strncmp(line, "OBJ ", 4)) {
            if (in) { done = 1; break; }
            char id[32];
            if (sscanf(line + 4, "%31s", id) != 1) continue;
            if (strcmp(id, key)) continue;
            in = 1;
            memset(o, 0, sizeof *o);
            if (sscanf(line + 4, "%31s %la %la %la %la %la %la %la %la %la %d %ld %ld", o->id, &o->t0, &o->y[0], &o->y[1], &o->y[2], &o->y[3], &o->y[4],
                       &o->y[5], &o->bc, &o->cram, &o->fitbc, &o->nobs, &nt) != 13)
                m1_die("bad OBJ line");
            o->obs = malloc((size_t)o->nobs * sizeof *o->obs);
        } else if (in && !strncmp(line, "O ", 2)) {
            long kk;
            double q[3];
            if (sscanf(line + 2, "%ld %la %la %la", &kk, &q[0], &q[1], &q[2]) != 4 || kk != got) m1_die("bad O line");
            memcpy(o->obs[got++], q, sizeof q);
        }
    }
    fclose(f);
    if (!in || got != o->nobs) m1_die("object %s not found whole in %s", key, path);
    return 0;
}

typedef struct {
    double (*pos)[8][3];
    long nobs;
    size_t n;
    const m1_vt *vt;
    m1_ctx *c;
} ObsCb;
static void obs_cb(void *u, long step, double t, void *const y[6], size_t n)
{
    ObsCb *o = (ObsCb *)u;
    (void)t;
    if (step % 8) return;
    long k = step / 8;
    if (k >= o->nobs) return;
    double tmp[8];
    for (int i = 0; i < 3; i++) {
        o->vt->to_f64(o->c, tmp, y[i], n);
        for (size_t l = 0; l < n; l++) o->pos[k][l][i] = tmp[l];
    }
}
static void span_run(K *k, const Obj *ob, double yl[8][6], double *bl, size_t n, double (*pos)[8][3])
{
    void *y[6], *bc = vnew(k, n), *cram = vnew(k, n);
    double tmp[8];
    for (int i = 0; i < 6; i++) {
        y[i] = vnew(k, n);
        for (size_t l = 0; l < n; l++) tmp[l] = yl[l][i];
        k->vt->from_f64(&k->c, y[i], tmp, n);
    }
    k->vt->from_f64(&k->c, bc, bl, n);
    for (size_t l = 0; l < n; l++) tmp[l] = ob->cram;
    k->vt->from_f64(&k->c, cram, tmp, n);
    ObsCb o = {pos, ob->nobs, n, k->vt, &k->c};
    obs_cb(&o, 0, ob->t0, y, n);
    k->c.model.t0 = ob->t0;
    k->vt->rk4(&k->c, y, bc, cram, "15", 0, 8 * (ob->nobs - 1), obs_cb, &o, n);
    for (int i = 0; i < 6; i++) free(y[i]);
    free(bc);
    free(cram);
}
static int lsq(int np, long nr, double *J, const double *r, double *dp)
{
    long double A[8][8] = {{0}}, b[8] = {0}, sc[8];
    for (int i = 0; i < np; i++) {
        long double s = 0;
        for (long q = 0; q < nr; q++) s += (long double)J[q * np + i] * J[q * np + i];
        sc[i] = s > 0 ? 1.0L / sqrtl(s) : 1.0L;
    }
    for (int i = 0; i < np; i++) {
        for (int j = 0; j <= i; j++) {
            long double s = 0;
            for (long q = 0; q < nr; q++) s += (long double)J[q * np + i] * J[q * np + j];
            A[i][j] = A[j][i] = s * sc[i] * sc[j];
        }
        long double s = 0;
        for (long q = 0; q < nr; q++) s += (long double)J[q * np + i] * r[q];
        b[i] = s * sc[i];
    }
    for (int i = 0; i < np; i++) {
        for (int j = 0; j < i; j++) {
            long double s = A[i][j];
            for (int q = 0; q < j; q++) s -= A[i][q] * A[j][q];
            A[i][j] = s / A[j][j];
        }
        long double s = A[i][i];
        for (int q = 0; q < i; q++) s -= A[i][q] * A[i][q];
        if (!(s > 0)) return -1;
        A[i][i] = sqrtl(s);
    }
    long double z[8];
    for (int i = 0; i < np; i++) {
        long double s = b[i];
        for (int q = 0; q < i; q++) s -= A[i][q] * z[q];
        z[i] = s / A[i][i];
    }
    for (int i = np - 1; i >= 0; i--) {
        long double s = z[i];
        for (int q = i + 1; q < np; q++) s -= A[q][i] * z[q];
        z[i] = s / A[i][i];
    }
    for (int i = 0; i < np; i++) dp[i] = (double)(z[i] * sc[i]);
    return 0;
}

int main(int argc, char **argv)
{
    if (argc < 5) m1_die("usage: h_fitdiag <table> <fit input> <key> <out prefix> [--iters N]");
    unsigned short cw = 0;
    unsigned int mx = 0;
#if defined(__x86_64__) || defined(__i386__)
    __asm__ volatile("fnstcw %0" : "=m"(cw));
    __asm__ volatile("stmxcsr %0" : "=m"(mx));
#endif
    printf("x87 control word 0x%04x, MXCSR 0x%08x, sizeof(long double) %u\n", cw, mx, (unsigned)sizeof(long double));
    const int iters = atoi(opt(argc, argv, "--iters", "1"));
    const char *e = getenv("M1_DOWNLOADS");
    if (!e || !*e) m1_die("M1_DOWNLOADS must name the downloads folder");
    char a1[768], a2[768];
    snprintf(a1, sizeof a1, "%sEIGEN6-C4.gfc/EIGEN6-C4.gfc", e);
    if (m1_gfc_load(&G, a1, M1_NMAX)) m1_die("gfc: %s", G.err);
    snprintf(a1, sizeof a1, "%slnxp1900p2053.421/lnxp1900p2053.421", e);
    snprintf(a2, sizeof a2, "%sheader.421/header.421", e);
    if (m1_de_open(&DE, a1, a2)) m1_die("de421: %s", DE.err);
    if (m1_ftab_load(&FT, argv[1])) m1_die("frame table: %s", FT.err);
    Obj ob;
    read_obj(argv[2], argv[3], &ob);
    m1_model m = model_real();
    K k;
    k.vt = m1_vt_by_name("native64");
    memset(&k.c, 0, sizeof k.c);
    if (cft_open(NULL, 0, &k.c.dev) != CFT_OK) m1_die("cft_open(NULL) failed");
    if (k.vt->setup(&k.c, &m, &G, &DE, 8)) m1_die("setup");
    char path[1024];
    snprintf(path, sizeof path, "%s.calls", argv[4]);
    FILE *fc = fopen(path, "wb");
    snprintf(path, sizeof path, "%s.jr", argv[4]);
    FILE *fj = fopen(path, "wb");
    if (!fc || !fj) m1_die("cannot write %s.*", argv[4]);
    static const double DSTEP[7] = {1.0, 1.0, 1.0, 1e-3, 1e-3, 1e-3, 1e-4};
    const int np = ob.fitbc ? 7 : 6;
    double p[7] = {ob.y[0], ob.y[1], ob.y[2], ob.y[3], ob.y[4], ob.y[5], ob.bc};
    double (*pos)[8][3] = malloc((size_t)ob.nobs * sizeof *pos);
    const long nr = 3 * ob.nobs;
    double *J = malloc((size_t)nr * 7 * sizeof(double)), *res = malloc((size_t)nr * sizeof(double));
    int it, conv = 0;
    double rms = 0, maxres = 0;
    for (it = 1; it <= iters; it++) {
        double yl[8][6], bl[8];
        size_t n = (size_t)np + 1;
        for (size_t l = 0; l < n; l++) {
            for (int i = 0; i < 6; i++) yl[l][i] = p[i];
            bl[l] = p[6];
            if (l >= 1 && l <= 6) yl[l][l - 1] += DSTEP[l - 1];
            if (l == 7) bl[l] += DSTEP[6];
        }
        if (it == 1) g_calls = fc;
        span_run(&k, &ob, yl, bl, n, pos);
        g_calls = NULL;
        double ss = 0;
        maxres = 0;
        for (long q = 0; q < ob.nobs; q++)
            for (int i = 0; i < 3; i++) {
                double rr = ob.obs[q][i] - pos[q][0][i];
                res[3 * q + i] = rr;
                ss += rr * rr;
                for (int c = 0; c < np; c++) J[(3 * q + i) * np + c] = (pos[q][c + 1][i] - pos[q][0][i]) / DSTEP[c];
            }
        for (long q = 0; q < ob.nobs; q++) {
            double d2 = res[3 * q] * res[3 * q] + res[3 * q + 1] * res[3 * q + 1] + res[3 * q + 2] * res[3 * q + 2];
            if (sqrt(d2) > maxres) maxres = sqrt(d2);
        }
        rms = sqrt(ss / (double)ob.nobs);
        double dp[7] = {0};
        int bad = lsq(np, nr, J, res, dp);
        if (it == 1)
            for (long q = 0; q < ob.nobs; q++)
                for (size_t l = 0; l < n; l++) fprintf(fj, "P %ld %lu %a %a %a\n", q, (unsigned long)l, pos[q][l][0], pos[q][l][1], pos[q][l][2]);
        for (long q = 0; q < nr; q++) {
            fprintf(fj, "R %d %ld %a", it, q, res[q]);
            for (int c = 0; c < np; c++) fprintf(fj, " %a", J[q * np + c]);
            fputc('\n', fj);
        }
        fprintf(fj, "D %d %d", it, bad);
        for (int c = 0; c < np; c++) fprintf(fj, " %a", dp[c]);
        fputc('\n', fj);
        printf("ITER %s %d rms %a maxres %a dp", ob.id, it, rms, maxres);
        for (int c = 0; c < np; c++) printf(" %a", dp[c]);
        printf("\n");
        if (bad) break;
        double rn = sqrt(p[0] * p[0] + p[1] * p[1] + p[2] * p[2]), vn = sqrt(p[3] * p[3] + p[4] * p[4] + p[5] * p[5]);
        int small = 1;
        for (int c = 0; c < np; c++) {
            double scale = c < 3 ? 1e-8 * rn : c < 6 ? 1e-8 * vn : 1e-5 * (fabs(p[6]) > 1e-3 ? fabs(p[6]) : 1e-3);
            if (fabs(dp[c]) > scale) small = 0;
        }
        for (int c = 0; c < np; c++) p[c] += dp[c];
        if (small) { conv = 1; break; }
    }
    if (it > iters) it = iters;
    printf("FIT %s %d %d %a %a  calls logged in the first iteration %llu\n", ob.id, conv, it, rms, maxres, g_ncalls);
    fclose(fc);
    fclose(fj);
    k.vt->teardown(&k.c);
    cft_close(k.c.dev);
    return 0;
}
