/* k_fit.c - cft-debris (DEBRIS-K): (H)'s fit, M1's least squares over pseudo-observations at given times, and M1's
 * decay rule over a propagation.
 *
 * cft-debris, MIT licence (see LICENSE at the repository root). Copied by DEBRIS-K, 2026-11-23, from cft-debris's own
 * code (MIT):
 *   - DEBRIS-F's tests/m1f.c (SHA-256 635c0fe21957c288f3a37c4a566b3533b08bcc1ec0e167943103383a1a7108ea): the input
 *     loader, the kind's set-up, the model, the object reader, the observation callback, the span run, the least
 *     squares (lsq) and the Gauss-Newton fit (mode fit), and the hex and option helpers, unchanged in their arithmetic;
 *   - DEBRIS-H's tests/m1h.c (SHA-256 b37aae29b6a9ce91c77aa4aab7e8481730247f19ad679f2fb04e17239e3de2f7): M1's decay
 *     rule, RMIN = 6,498,137.0 m (120 km above 6,378.137 km): an object is decayed from the first step at whose end its
 *     distance from the centre is not above RMIN; and its frame-table span check.
 * What changed:
 *   - fit: each pseudo-observation line carries its own time, "O k t x y z" (TDB s from jd_epoch 2461329.5, C99 hex).
 *     Each time must be t0 + 15 j exactly for a whole j >= 0, strictly ascending. The span runs rk4 at 15 s from t0 to
 *     the last observation's step, and the callback keeps every lane's position at each observation's step (m1f.c
 *     keeps every 8th step). Given the times t0 + 120 k, k = 0 to nobs - 1, it is m1f.c's fit, operation for operation;
 *   - decay (new): from each object's (t0, state, bc, cram), whole rk4 steps of 15 s in chunks of 40, the distance from
 *     the centre tested after every step as m1h.c's run tests it, to the first decayed step or to the last whole step
 *     at or before the object's end time;
 *   - M1_DOWNLOADS must name the downloads folder (as m1h.c requires), so no home folder is compiled in;
 *   - m1f.c's other modes (f1, f4, frames, traj, prop, time) are left out: DEBRIS-K's predictions run m1f.c's prop.
 *
 *   k_fit fit   <table> <in> <out> [--maxit 10] [--cr]           (native64)
 *     in: "OBJ id t0 x y z vx vy vz bc cram fitbc nobs 0" (m1f.c's line), then nobs lines "O k t x y z"
 *   k_fit decay <kind> <table> <in> <out> [--cr]
 *     in: "OBJ id t0 x y z vx vy vz bc cram tend"; out: "DECAY id step t r" or "LIVE id step t r" or "NONFINITE id step t"
 */
#define __USE_MINGW_ANSI_STDIO 1
#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "m1.h"

#define JD_EPOCH 2461329.5
#define RMIN 6498137.0 /* m1h.c: 120 km above 6,378.137 km */
#define HSTEP 15.0
static char DL[512] = "";
static m1_gfc G;
static m1_de DE;
static m1_ftab FT;

static char *dlpath(const char *rel)
{
    static char buf[8][768];
    static int k = 0;
    char *b = buf[k++ & 7];
    snprintf(b, 768, "%s%s", DL, rel);
    return b;
}
static const char *opt(int argc, char **argv, const char *o, const char *def)
{
    for (int i = 0; i + 1 < argc; i++)
        if (!strcmp(argv[i], o)) return argv[i + 1];
    return def;
}
static int has(int argc, char **argv, const char *o)
{
    for (int i = 0; i < argc; i++)
        if (!strcmp(argv[i], o)) return 1;
    return 0;
}
static void load_inputs(const char *table)
{
    const char *e = getenv("M1_DOWNLOADS");
    if (!e || !*e) m1_die("M1_DOWNLOADS must name the downloads folder (gfc, DE421 and its header)");
    snprintf(DL, sizeof DL, "%s", e);
    if (m1_gfc_load(&G, dlpath("EIGEN6-C4.gfc/EIGEN6-C4.gfc"), M1_NMAX)) m1_die("gfc: %s", G.err);
    if (m1_de_open(&DE, dlpath("lnxp1900p2053.421/lnxp1900p2053.421"), dlpath("header.421/header.421"))) m1_die("de421: %s", DE.err);
    if (m1_ftab_load(&FT, table)) m1_die("frame table: %s", FT.err);
}

typedef struct K {
    const m1_vt *vt;
    m1_ctx c;
} K;
static void kopen(K *k, const char *name, const m1_model *m, size_t lanes, int cr)
{
    k->vt = m1_vt_by_name(name);
    if (!k->vt) m1_die("no kind %s", name);
    memset(&k->c, 0, sizeof k->c);
    if (cft_open(NULL, 0, &k->c.dev) != CFT_OK) m1_die("cft_open(NULL) failed");
    k->c.cr_transc = cr;
    if (k->vt->setup(&k->c, m, &G, &DE, lanes)) m1_die("setup %s", name);
}
static void kclose(K *k)
{
    k->vt->teardown(&k->c);
    cft_close(k->c.dev);
}
static void *vnew(const K *k, size_t n)
{
    void *p = calloc(n ? n : 1, k->vt->esz);
    if (!p) m1_die("out of memory");
    return p;
}
static void kind_header(FILE *f, const K *k)
{
    fprintf(f, "# kind %s esz %lu native %d cr_transc %d build_id %s table %s sha256 %s\n", k->vt->name,
            (unsigned long)k->vt->esz, k->vt->native, k->c.cr_transc, cft_build_id(), FT.raw ? FT.note : "-",
            FT.raw ? FT.sha256 : "-");
}
static void ops_footer(FILE *f, const K *k)
{
    static const char *nm[M1_NOP] = {"add", "sub", "mul", "div", "sqrt", "fma", "neg", "cmp", "sel",
                                     "exp", "sin", "cos", "asin", "acos", "cvt"};
    fprintf(f, "# lane-ops");
    for (int i = 0; i < M1_NOP; i++) fprintf(f, " %s=%llu", nm[i], (unsigned long long)k->c.nops[i]);
    fprintf(f, "\n# cft_flags 0x%x\n", (unsigned)k->c.cft_flags);
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
static void span_check(double t0, long nsteps)
{
    /* m1h.c's check: the run's span inside the frame table's interior */
    if (t0 < FT.t0 + 3.0 * FT.h || t0 + HSTEP * (double)nsteps + HSTEP > FT.t0 + (double)(FT.nk - 4) * FT.h)
        m1_die("the span from %a over %ld steps is not inside the frame table", t0, nsteps);
}

/* ------------------------------------------------------------------ fit: objects with timed observations */
typedef struct {
    char id[32];
    double t0;            /* the origin (TDB s), a multiple of 2^-20 */
    double y[6], bc, cram;
    int fitbc;
    long nobs;            /* pseudo-observations at t0 + 15 ostep[k] */
    double (*obs)[3];
    long *ostep;
} Obj;

static Obj *read_objs(const char *path, long *nobj)
{
    FILE *f = fopen(path, "rb");
    if (!f) m1_die("cannot read %s", path);
    long cap = 64, n = 0;
    Obj *O = (Obj *)calloc((size_t)cap, sizeof(Obj));
    long *got_o = (long *)calloc((size_t)cap, sizeof(long));
    char line[2048];
    Obj *cur = NULL;
    while (fgets(line, sizeof line, f)) {
        if (line[0] == '#') continue;
        if (!strncmp(line, "OBJ ", 4)) {
            if (n == cap) {
                cap *= 2;
                O = (Obj *)realloc(O, (size_t)cap * sizeof(Obj));
                got_o = (long *)realloc(got_o, (size_t)cap * sizeof(long));
            }
            cur = &O[n];
            memset(cur, 0, sizeof *cur);
            got_o[n] = 0;
            n++;
            long ntarget = 0;
            if (sscanf(line + 4, "%31s %la %la %la %la %la %la %la %la %la %d %ld %ld", cur->id, &cur->t0, &cur->y[0], &cur->y[1], &cur->y[2],
                       &cur->y[3], &cur->y[4], &cur->y[5], &cur->bc, &cur->cram, &cur->fitbc, &cur->nobs, &ntarget) != 13)
                m1_die("bad OBJ line: %s", line);
            if (cur->nobs < 2) m1_die("object %s: fewer than 2 observations", cur->id);
            cur->obs = malloc((size_t)cur->nobs * sizeof *cur->obs);
            cur->ostep = malloc((size_t)cur->nobs * sizeof(long));
        } else if (!strncmp(line, "O ", 2) && cur) {
            long kk;
            double t, q[3];
            if (sscanf(line + 2, "%ld %la %la %la %la", &kk, &t, &q[0], &q[1], &q[2]) != 5) m1_die("bad O line");
            long i = got_o[n - 1]++;
            if (i >= cur->nobs || kk != i) m1_die("object %s: observation %ld out of order", cur->id, kk);
            const double jd = (t - cur->t0) / HSTEP;
            const long j = (long)jd;
            if (jd != (double)j || j < 0 || cur->t0 + HSTEP * (double)j != t) m1_die("object %s: observation %ld at %a is not t0 + 15 j", cur->id, kk, t);
            if (i > 0 && j <= cur->ostep[i - 1]) m1_die("object %s: observation %ld not after the one before", cur->id, kk);
            cur->ostep[i] = j;
            memcpy(cur->obs[i], q, sizeof q);
        }
    }
    fclose(f);
    for (long i = 0; i < n; i++)
        if (got_o[i] != O[i].nobs) m1_die("object %s: observations incomplete", O[i].id);
    free(got_o);
    *nobj = n;
    return O;
}

/* positions at each observation's step of an rk4 run at 15 s */
typedef struct {
    double (*pos)[8][3];  /* [obs][lane][xyz] */
    const long *ostep;
    long nobs, next;
    size_t n;
    const m1_vt *vt;
    m1_ctx *c;
} ObsCb;
static void obs_cb(void *u, long step, double t, void *const y[6], size_t n)
{
    ObsCb *o = (ObsCb *)u;
    (void)t;
    if (o->next >= o->nobs || o->ostep[o->next] != step) return;
    const long k = o->next++;
    double tmp[8];
    for (int i = 0; i < 3; i++) {
        o->vt->to_f64(o->c, tmp, y[i], n);
        for (size_t l = 0; l < n; l++) o->pos[k][l][i] = tmp[l];
    }
}

/* one native64 run of n lanes (states yl, bc bl) over the span: positions at the observation times */
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
    ObsCb o = {pos, ob->ostep, ob->nobs, 0, n, k->vt, &k->c};
    obs_cb(&o, 0, ob->t0, y, n);
    k->c.model.t0 = ob->t0;
    k->vt->rk4(&k->c, y, bc, cram, "15", 0, ob->ostep[ob->nobs - 1], obs_cb, &o, n);
    if (o.next != ob->nobs) m1_die("object %s: %ld of %ld observation steps reached", ob->id, o.next, ob->nobs);
    for (int i = 0; i < 6; i++) free(y[i]);
    free(bc);
    free(cram);
}

/* the least-squares step (m1f.c's, unchanged): solve min |J dp - r| by the normal equations, columns scaled to unit
   norm, Cholesky in long double */
static int lsq(int np, long nr, double *J /* nr x np */, const double *r, double *dp)
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

/* m1f.c's B4, unchanged but for the observation steps: Gauss-Newton at native64; parameters the state at the span's
   start (6) and bc where fitbc; partials by finite differences as lanes of the same batch (lane 0 nominal, lanes 1..6
   the state perturbed by 1 m and 1e-3 m/s, lane 7 bc + 1e-4 m^2/kg); stop when every |dp_i| is below its threshold
   (1e-8 |r|, 1e-8 |v|, 1e-5 max(|bc|, 1e-3)) with that update applied, or after maxit iterations. */
static int mode_fit(int argc, char **argv)
{
    if (argc < 5) m1_die("usage: fit <table> <in> <out> [--maxit 10]");
    const int maxit = atoi(opt(argc, argv, "--maxit", "10"));
    long nobj;
    Obj *O = read_objs(argv[3], &nobj);
    m1_model m = model_real();
    K k;
    kopen(&k, "native64", &m, 8, has(argc, argv, "--cr"));
    FILE *f = fopen(argv[4], "wb");
    if (!f) m1_die("cannot write %s", argv[4]);
    kind_header(f, &k);
    fprintf(f, "# k_fit fit objects %ld maxit %d; per object: FIT id converged iterations rms_m maxres_m nobs fitbc t0 x y z vx vy vz bc (%%a); then ITER lines\n", nobj, maxit);
    static const double DSTEP[7] = {1.0, 1.0, 1.0, 1e-3, 1e-3, 1e-3, 1e-4};
    for (long ob = 0; ob < nobj; ob++) {
        Obj *o = &O[ob];
        span_check(o->t0, o->ostep[o->nobs - 1]);
        const int np = o->fitbc ? 7 : 6;
        double p[7] = {o->y[0], o->y[1], o->y[2], o->y[3], o->y[4], o->y[5], o->bc};
        double (*pos)[8][3] = malloc((size_t)o->nobs * sizeof *pos);
        const long nr = 3 * o->nobs;
        double *J = malloc((size_t)nr * 7 * sizeof(double)), *res = malloc((size_t)nr * sizeof(double));
        int it, conv = 0;
        double rms = 0, maxres = 0;
        for (it = 1; it <= maxit; it++) {
            double yl[8][6], bl[8];
            size_t n = (size_t)np + 1;
            for (size_t l = 0; l < n; l++) {
                for (int i = 0; i < 6; i++) yl[l][i] = p[i];
                bl[l] = p[6];
                if (l >= 1 && l <= 6) yl[l][l - 1] += DSTEP[l - 1];
                if (l == 7) bl[l] += DSTEP[6];
            }
            span_run(&k, o, yl, bl, n, pos);
            double ss = 0;
            maxres = 0;
            for (long q = 0; q < o->nobs; q++)
                for (int i = 0; i < 3; i++) {
                    double rr = o->obs[q][i] - pos[q][0][i];
                    res[3 * q + i] = rr;
                    ss += rr * rr;
                    for (int c = 0; c < np; c++) J[(3 * q + i) * np + c] = (pos[q][c + 1][i] - pos[q][0][i]) / DSTEP[c];
                }
            for (long q = 0; q < o->nobs; q++) {
                double d2 = res[3 * q] * res[3 * q] + res[3 * q + 1] * res[3 * q + 1] + res[3 * q + 2] * res[3 * q + 2];
                if (sqrt(d2) > maxres) maxres = sqrt(d2);
            }
            rms = sqrt(ss / (double)o->nobs);   /* RMS of the position residual's length */
            double dp[7] = {0};
            if (lsq(np, nr, J, res, dp)) { fprintf(f, "ITER %s %d singular\n", o->id, it); break; }
            double rn = sqrt(p[0] * p[0] + p[1] * p[1] + p[2] * p[2]), vn = sqrt(p[3] * p[3] + p[4] * p[4] + p[5] * p[5]);
            int small = 1;
            for (int c = 0; c < np; c++) {
                double scale = c < 3 ? 1e-8 * rn : c < 6 ? 1e-8 * vn : 1e-5 * (fabs(p[6]) > 1e-3 ? fabs(p[6]) : 1e-3);
                if (fabs(dp[c]) > scale) small = 0;
            }
            fprintf(f, "ITER %s %d rms %a maxres %a dp", o->id, it, rms, maxres);
            for (int c = 0; c < np; c++) fprintf(f, " %a", dp[c]);
            fputc('\n', f);
            fflush(f);
            for (int c = 0; c < np; c++) p[c] += dp[c];
            if (small) { conv = 1; break; }
        }
        if (it > maxit) it = maxit;
        fprintf(f, "FIT %s %d %d %a %a %ld %d %a %a %a %a %a %a %a %a\n", o->id, conv, it, rms, maxres, o->nobs, o->fitbc, o->t0, p[0], p[1], p[2], p[3],
                p[4], p[5], p[6]);
        fflush(f);
        free(pos);
        free(J);
        free(res);
    }
    ops_footer(f, &k);
    fclose(f);
    kclose(&k);
    return 0;
}

/* ------------------------------------------------------------------ decay: M1's rule (m1h.c's RMIN) */
typedef struct {
    const m1_vt *vt;
    m1_ctx *c;
    long decay;           /* the first step found not above RMIN, or -1 */
    long bad;             /* the first step with a non-finite state, or -1 */
    double r_at, r_last;
} DecCb;
static void dec_cb(void *u, long step, double t, void *const y[6], size_t n)
{
    DecCb *o = (DecCb *)u;
    (void)t;
    (void)n;
    if (o->decay >= 0 || o->bad >= 0) return;
    double d[6];
    for (int i = 0; i < 6; i++) o->vt->to_f64(o->c, &d[i], y[i], 1);
    int fin = 1;
    for (int i = 0; i < 6; i++) fin &= isfinite(d[i]) ? 1 : 0;
    if (!fin) { o->bad = step; return; }
    const double r = sqrt(d[0] * d[0] + d[1] * d[1] + d[2] * d[2]);
    o->r_last = r;
    if (!(r > RMIN)) { o->decay = step; o->r_at = r; }
}
static int mode_decay(int argc, char **argv)
{
    if (argc < 6) m1_die("usage: decay <kind> <table> <in> <out>");
    FILE *fi = fopen(argv[4], "rb");
    if (!fi) m1_die("cannot read %s", argv[4]);
    m1_model m = model_real();
    K k;
    kopen(&k, argv[2], &m, 1, has(argc, argv, "--cr"));
    FILE *f = fopen(argv[5], "wb");
    if (!f) m1_die("cannot write %s", argv[5]);
    kind_header(f, &k);
    fprintf(f, "# k_fit decay: rk4 at 15 s from t0; RMIN %.1f m (m1h.c); columns DECAY|LIVE id step t r_m, or NONFINITE id step t\n", RMIN);
    char line[2048];
    long nobj = 0;
    while (fgets(line, sizeof line, fi)) {
        if (strncmp(line, "OBJ ", 4)) continue;
        char id[32];
        double t0, yv[6], bcv, cramv, tend;
        if (sscanf(line + 4, "%31s %la %la %la %la %la %la %la %la %la %la", id, &t0, &yv[0], &yv[1], &yv[2], &yv[3], &yv[4], &yv[5], &bcv, &cramv, &tend) != 11)
            m1_die("bad OBJ line: %s", line);
        const long nend = (long)floor((tend - t0) / HSTEP);
        if (nend < 1) m1_die("object %s: its end is not a step after its origin", id);
        span_check(t0, nend);
        void *y[6], *bc = vnew(&k, 1), *cram = vnew(&k, 1);
        for (int i = 0; i < 6; i++) {
            y[i] = vnew(&k, 1);
            k.vt->from_f64(&k.c, y[i], &yv[i], 1);
        }
        k.vt->from_f64(&k.c, bc, &bcv, 1);
        k.vt->from_f64(&k.c, cram, &cramv, 1);
        k.c.model.t0 = t0;
        DecCb o = {k.vt, &k.c, -1, -1, 0.0, 0.0};
        long step = 0;
        while (step < nend && o.decay < 0 && o.bad < 0) {
            const long ns = nend - step < 40 ? nend - step : 40;
            k.vt->rk4(&k.c, y, bc, cram, "15", step, ns, dec_cb, &o, 1);
            step += ns;
        }
        if (o.bad >= 0) fprintf(f, "NONFINITE %s %ld %a\n", id, o.bad, t0 + HSTEP * (double)o.bad);
        else if (o.decay >= 0) fprintf(f, "DECAY %s %ld %a %.3f\n", id, o.decay, t0 + HSTEP * (double)o.decay, o.r_at);
        else fprintf(f, "LIVE %s %ld %a %.3f\n", id, step, t0 + HSTEP * (double)step, o.r_last);
        fflush(f);
        for (int i = 0; i < 6; i++) free(y[i]);
        free(bc);
        free(cram);
        nobj++;
    }
    fclose(fi);
    fprintf(f, "# objects %ld\n", nobj);
    ops_footer(f, &k);
    fclose(f);
    kclose(&k);
    return 0;
}

int main(int argc, char **argv)
{
    if (argc < 2) m1_die("usage: k_fit fit|decay ...");
    const char *mode = argv[1];
    const char *table = !strcmp(mode, "fit") ? (argc > 2 ? argv[2] : NULL) : (argc > 3 ? argv[3] : NULL);
    if (!table) m1_die("no frame table given");
    load_inputs(table);
    if (!strcmp(mode, "fit")) return mode_fit(argc, argv);
    if (!strcmp(mode, "decay")) return mode_decay(argc, argv);
    m1_die("no mode %s", mode);
    return 2;
}
