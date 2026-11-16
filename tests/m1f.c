/* m1f.c - cft-debris M1 (DEBRIS-F): the driver of the real frame, the fit and the predictions.
 *
 * cft-debris, MIT licence (see LICENSE at the repository root). Written by DEBRIS-F, 2026-11-16. Its PRNG,
 * hex output and the eight lanes of E2/E8 are DEBRIS-E's tests/m1run.c (cft-debris's own, MIT).
 *
 *   m1f f1    <kind> <table> <nlanes> <seed> <out> [--cr]
 *   m1f f4    <kind> <table> <states> <out> [--plant-bc rel]
 *   m1f frames <kind> <table> <times> <out>
 *   m1f traj  <kind> <table> <t0> <nsteps> <h> <out> [--short hs] [--step0 s --from file] [--cr] [--every k]
 *   m1f fit   <table> <in> <out> [--maxit 10] [--cr]                          (native64)
 *   m1f prop  <kind> <table> <in> <out> [--cr] [--round64]
 *   m1f time  <kind> <table> <nlanes> <min_seconds> <out> [--cr]
 * Times are TDB seconds from jd_epoch 2461329.5 (MJD 61329.0 TDB). Every result is the hexadecimal of its
 * encoding (most significant byte first) or a C99 hex float, so gates compare bits.
 * The force model of fit, prop and traj: central + EIGEN-6C4 degrees 2..20 in the IERS 2010 frame from the
 * table, the Sun and the Moon from DE421, drag through the 28-band table co-rotating with the table's Omega,
 * and radiation pressure with the conical shadow; rk4 at a fixed step.
 */
#define __USE_MINGW_ANSI_STDIO 1
#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "m1.h"

#define JD_EPOCH 2461329.5
static char DL[512] = "C:/Users/logan/source/repos/cft-debris-downloads/";
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
    if (e && *e) snprintf(DL, sizeof DL, "%s", e);
    if (m1_gfc_load(&G, dlpath("EIGEN6-C4.gfc/EIGEN6-C4.gfc"), M1_NMAX)) m1_die("gfc: %s", G.err);
    if (m1_de_open(&DE, dlpath("lnxp1900p2053.421/lnxp1900p2053.421"), dlpath("header.421/header.421"))) m1_die("de421: %s", DE.err);
    if (table && strcmp(table, "-") && m1_ftab_load(&FT, table)) m1_die("frame table: %s", FT.err);
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
static void phex(FILE *f, const void *p, size_t esz)
{
    const unsigned char *b = (const unsigned char *)p;
    fputc(' ', f);
    for (size_t i = esz; i-- > 0;) fprintf(f, "%02x", b[i]);
}
static int hexval(int ch)
{
    if (ch >= '0' && ch <= '9') return ch - '0';
    if (ch >= 'a' && ch <= 'f') return ch - 'a' + 10;
    if (ch >= 'A' && ch <= 'F') return ch - 'A' + 10;
    return -1;
}
static void unhex(const char *s, void *p, size_t esz)
{
    unsigned char *b = (unsigned char *)p;
    if (strlen(s) != 2 * esz) m1_die("hex \"%s\" is not %lu bytes", s, (unsigned long)esz);
    for (size_t i = 0; i < esz; i++) {
        int hi = hexval(s[2 * (esz - 1 - i)]), lo = hexval(s[2 * (esz - 1 - i) + 1]);
        if (hi < 0 || lo < 0) m1_die("hex \"%s\"", s);
        b[i] = (unsigned char)(hi * 16 + lo);
    }
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

/* ------------------------------------------------------------------ PRNG (DEBRIS-E's) */
static uint64_t sm_state;
static uint64_t splitmix64(void)
{
    uint64_t z = (sm_state += 0x9E3779B97F4A7C15ULL);
    z = (z ^ (z >> 30)) * 0xBF58476D1CE4E5B9ULL;
    z = (z ^ (z >> 27)) * 0x94D049BB133111EBULL;
    return z ^ (z >> 31);
}
static double urand(void) { return (double)(splitmix64() >> 11) * 0x1p-53; }
static double urange(double a, double b) { return a + (b - a) * urand(); }
static void rdir(double rad, double *x, double *y, double *z)
{
    double zz = 2.0 * urand() - 1.0, ph = 6.283185307179586 * urand(), s = sqrt(1.0 - zz * zz);
    *x = rad * s * cos(ph);
    *y = rad * s * sin(ph);
    *z = rad * zz;
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

/* ------------------------------------------------------------------ F1 */
/* each lane: its own stage time t (uniform over the table's interior, a multiple of 2^-21 s), a position r
   (6,600 to 8,000 km, direction uniform), a vector b (1e-6 to 1e-1, direction uniform), a velocity v (7 to 8 km/s)
   and bc (0.002 to 0.05 m^2/kg); outputs: the 12 interpolated values, M^T r, M b, and drag at (r, v, bc) with the
   lane's Omega (28 bands) */
static int mode_f1(int argc, char **argv)
{
    if (argc < 7) m1_die("usage: f1 <kind> <table> <nlanes> <seed> <out>");
    size_t n = (size_t)atol(argv[4]);
    sm_state = strtoull(argv[5], NULL, 0);
    m1_model m = model_real();
    K k;
    kopen(&k, argv[2], &m, 16, has(argc, argv, "--cr"));
    const double lo = FT.t0 + 3.0 * FT.h, hi = FT.t0 + (double)(FT.nk - 4) * FT.h;
    FILE *fi, *f;
    char path[700];
    snprintf(path, sizeof path, "%s.in", argv[6]);
    fi = fopen(path, "wb");
    f = fopen(argv[6], "wb");
    if (!fi || !f) m1_die("cannot write %s", argv[6]);
    fprintf(fi, "# f1 inputs, a lane a line: t x y z bx by bz vx vy vz bc (%%a)\n");
    kind_header(f, &k);
    fprintf(f, "# f1 lanes %lu seed %s; columns: lane M00..M22 Om0..Om2 (M^T r)0..2 (M b)0..2 drag0..2\n", (unsigned long)n, argv[5]);
    unsigned char m12[12 * 32], kin[11 * 32], o3[3][32], o4[3][32], o5[3][32];
    for (size_t l = 0; l < n; l++) {
        double in[11];
        in[0] = floor(urange(lo, hi) * 2097152.0) / 2097152.0;
        rdir(urange(6.6e6, 8.0e6), &in[1], &in[2], &in[3]);
        rdir(pow(10.0, urange(-6.0, -1.0)), &in[4], &in[5], &in[6]);
        rdir(urange(7.0e3, 8.0e3), &in[7], &in[8], &in[9]);
        in[10] = urange(0.002, 0.05);
        fprintf(fi, "%lu", (unsigned long)l);
        for (int j = 0; j < 11; j++) fprintf(fi, " %a", in[j]);
        fputc('\n', fi);
        const size_t es = k.vt->esz;
        k.vt->from_f64(&k.c, kin, in + 1, 10);
        k.vt->frame_at(&k.c, m12, in[0]);
        void *r[3] = {kin, kin + es, kin + 2 * es}, *b[3] = {kin + 3 * es, kin + 4 * es, kin + 5 * es};
        void *v[3] = {kin + 6 * es, kin + 7 * es, kin + 8 * es};
        void *a[3] = {o3[0], o3[1], o3[2]}, *c[3] = {o4[0], o4[1], o4[2]}, *d[3] = {o5[0], o5[1], o5[2]};
        k.vt->frame_apply(&k.c, a, (const void *const *)r, m12, 0, 1);
        k.vt->frame_apply(&k.c, c, (const void *const *)b, m12, 1, 1);
        k.vt->drag_om(&k.c, d, (const void *const *)r, (const void *const *)v, kin + 9 * es, m12 + 9 * es, 1);
        fprintf(f, "%lu", (unsigned long)l);
        for (int j = 0; j < 12; j++) phex(f, m12 + j * es, es);
        for (int j = 0; j < 3; j++) phex(f, a[j], es);
        for (int j = 0; j < 3; j++) phex(f, c[j], es);
        for (int j = 0; j < 3; j++) phex(f, d[j], es);
        fputc('\n', f);
    }
    ops_footer(f, &k);
    fclose(f);
    fclose(fi);
    kclose(&k);
    return 0;
}

/* ------------------------------------------------------------------ frames (F3b) */
/* the table's interpolation in the kind at given host times (one %a a line): M (9) and Omega (3), hex */
static int mode_frames(int argc, char **argv)
{
    if (argc < 6) m1_die("usage: frames <kind> <table> <times> <out>");
    m1_model m = model_real();
    K k;
    kopen(&k, argv[2], &m, 16, 0);
    FILE *fi = fopen(argv[4], "rb"), *f = fopen(argv[5], "wb");
    if (!fi || !f) m1_die("cannot open %s or %s", argv[4], argv[5]);
    kind_header(f, &k);
    fprintf(f, "# frames: columns t (%%a) M00..M22 Om0..Om2 (hex of the kind's encoding)\n");
    char line[256];
    unsigned char m12[12 * 32];
    while (fgets(line, sizeof line, fi)) {
        if (line[0] == '#' || line[0] == '\n' || line[0] == '\r') continue;
        double t = strtod(line, NULL);
        k.vt->frame_at(&k.c, m12, t);
        fprintf(f, "%a", t);
        for (int j = 0; j < 12; j++) phex(f, m12 + j * k.vt->esz, k.vt->esz);
        fputc('\n', f);
    }
    fclose(fi);
    ops_footer(f, &k);
    fclose(f);
    kclose(&k);
    return 0;
}

/* ------------------------------------------------------------------ F4 */
/* states: lines "i t x y z vx vy vz bc" (%a), t a stage time inside the table; outputs per state: gravity
   (degrees 2..20, inertial, through the table's M at t) and drag (one band: 3.725e-12 kg/m^3 at 400 km, scale
   height 58,515 m, as E6; co-rotating with the table's Omega at t) */
static int mode_f4(int argc, char **argv)
{
    if (argc < 6) m1_die("usage: f4 <kind> <table> <states> <out> [--plant-bc rel]");
    const double pbc = strtod(opt(argc, argv, "--plant-bc", "0"), NULL);
    m1_model m = model_real();
    m.nbands = 1;
    m.band_h0 = "400000";
    m.band_rho0 = "3.725e-12";
    m.band_hs = "58515";
    FILE *fi = fopen(argv[4], "rb");
    if (!fi) m1_die("cannot read %s", argv[4]);
    size_t cap = 2048, n = 0;
    double(*S)[8] = malloc(cap * sizeof *S);
    char line[1024];
    while (fgets(line, sizeof line, fi)) {
        if (line[0] == '#') continue;
        unsigned long i;
        double v[8];
        if (sscanf(line, "%lu %la %la %la %la %la %la %la %la", &i, &v[0], &v[1], &v[2], &v[3], &v[4], &v[5], &v[6], &v[7]) != 9) continue;
        if (n == cap) m1_die("too many states");
        memcpy(S[n++], v, sizeof v);
    }
    fclose(fi);
    K k;
    kopen(&k, argv[2], &m, n, 0);
    const size_t es = k.vt->esz;
    unsigned char *R[3], *RB[3], *GB[3], *GI[3], *AD[3], *M12 = vnew(&k, 12 * n), *bc = vnew(&k, n), tmp[8 * 32];
    for (int j = 0; j < 3; j++) { R[j] = vnew(&k, n); RB[j] = vnew(&k, n); GB[j] = vnew(&k, n); GI[j] = vnew(&k, n); AD[j] = vnew(&k, n); }
    for (size_t l = 0; l < n; l++) {
        double bcv = S[l][7] * (1.0 + pbc);
        k.vt->from_f64(&k.c, tmp, &S[l][1], 6);
        k.vt->from_f64(&k.c, bc + l * es, &bcv, 1);
        for (int j = 0; j < 3; j++) memcpy(R[j] + l * es, tmp + j * es, es);
        k.vt->frame_at(&k.c, M12 + 12 * l * es, S[l][0]);
        void *r1[3] = {R[0] + l * es, R[1] + l * es, R[2] + l * es}, *b1[3] = {RB[0] + l * es, RB[1] + l * es, RB[2] + l * es};
        k.vt->frame_apply(&k.c, b1, (const void *const *)r1, M12 + 12 * l * es, 0, 1);
    }
    void *rb[3] = {RB[0], RB[1], RB[2]}, *gb[3] = {GB[0], GB[1], GB[2]};
    k.vt->grav(&k.c, gb, (const void *const *)rb, 2, 20, n);
    for (size_t l = 0; l < n; l++) {
        void *g1[3] = {GB[0] + l * es, GB[1] + l * es, GB[2] + l * es}, *i1[3] = {GI[0] + l * es, GI[1] + l * es, GI[2] + l * es};
        k.vt->frame_apply(&k.c, i1, (const void *const *)g1, M12 + 12 * l * es, 1, 1);
        unsigned char vv[3 * 32];
        k.vt->from_f64(&k.c, vv, &S[l][4], 3);
        void *r1[3] = {R[0] + l * es, R[1] + l * es, R[2] + l * es}, *v1[3] = {vv, vv + es, vv + 2 * es};
        void *d1[3] = {AD[0] + l * es, AD[1] + l * es, AD[2] + l * es};
        k.vt->drag_om(&k.c, d1, (const void *const *)r1, (const void *const *)v1, bc + l * es, M12 + (12 * l + 9) * es, 1);
    }
    FILE *f = fopen(argv[5], "wb");
    if (!f) m1_die("cannot write %s", argv[5]);
    kind_header(f, &k);
    fprintf(f, "# f4 states %lu plant_bc %a; columns: i grav(3, inertial, degrees 2..20) drag(3, one band)\n", (unsigned long)n, pbc);
    for (size_t l = 0; l < n; l++) {
        fprintf(f, "%lu", (unsigned long)l);
        for (int j = 0; j < 3; j++) phex(f, GI[j] + l * es, es);
        for (int j = 0; j < 3; j++) phex(f, AD[j] + l * es, es);
        fputc('\n', f);
    }
    ops_footer(f, &k);
    fclose(f);
    kclose(&k);
    return 0;
}

/* ------------------------------------------------------------------ traj (F8) */
static const struct {
    const char *y[6], *bc, *cram;
} LANES8[8] = {
    {{"6778136.3", "0.0", "0.0", "-0.0", "4763.308132757748", "6009.79917725315"}, "0.011", "0.02"},
    {{"4727067.458866317", "3431293.8886403306", "3338992.8961416413", "-2427.16246539213", "-3097.617308706853",
      "6619.419907658179"}, "0.005", "0.01"},
    {{"-4558081.580743138", "4295834.082553983", "2842263.3234511204", "-4439.039075485846", "-5911.6932581067085",
      "1816.2114308748667"}, "0.02", "0.03"},
    {{"903678.4634067558", "521739.0041087581", "6899676.7944407435", "3777.043324987265", "-6542.030941266833",
      "4.573536163795741e-13"}, "0.008", "0.015"},
    {{"2353437.148945508", "-3516052.054593197", "5359305.632890503", "6769.953149445514", "-745.9542878719845",
      "-3462.2905682322225"}, "0.015", "0.025"},
    {{"6970601.661523341", "-1229100.4045408047", "6176.8360310422495", "1304.412232270023", "7397.660848372243",
      "-11.354062572265523"}, "0.012", "0.012"},
    {{"3464068.150000003", "5999942.036681126", "8.401949178997247e-10", "-914.2113563995073", "527.82017271347",
      "-7511.271351578038"}, "0.006", "0.028"},
    {{"-3369375.9914005348", "5348893.427315517", "-2389362.0029564826", "-3964.7088578513403", "-4598.271207866931",
      "-4702.9574373125815"}, "0.018", "0.018"},
};
typedef struct {
    FILE *f;
    size_t esz;
    long every;
} TrajOut;
static void traj_cb(void *u, long step, double t, void *const y[6], size_t n)
{
    TrajOut *o = (TrajOut *)u;
    if (o->every > 1 && step % o->every) return;
    for (size_t l = 0; l < n; l++) {
        fprintf(o->f, "S %ld %a %lu", step, t, (unsigned long)l);
        for (int i = 0; i < 6; i++) phex(o->f, (const unsigned char *)y[i] + l * o->esz, o->esz);
        fputc('\n', o->f);
    }
}
static int mode_traj(int argc, char **argv)
{
    if (argc < 8) m1_die("usage: traj <kind> <table> <t0> <nsteps> <h> <out>");
    const size_t n = 8;
    m1_model m = model_real();
    m.t0 = strtod(argv[4], NULL);
    long nsteps = atol(argv[5]);
    const char *h = argv[6];
    const double hs = strtod(opt(argc, argv, "--short", "0"), NULL);
    const long every = atol(opt(argc, argv, "--every", "1"));
    const long step0 = atol(opt(argc, argv, "--step0", "0"));
    const char *from = opt(argc, argv, "--from", NULL);
    K k;
    kopen(&k, argv[2], &m, n, has(argc, argv, "--cr"));
    void *y[6], *bc = vnew(&k, n), *cram = vnew(&k, n);
    const char *s[8];
    for (int i = 0; i < 6; i++) {
        y[i] = vnew(&k, n);
        for (size_t l = 0; l < n; l++) s[l] = LANES8[l].y[i];
        k.vt->from_dec(&k.c, y[i], s, n);
    }
    for (size_t l = 0; l < n; l++) s[l] = LANES8[l].bc;
    k.vt->from_dec(&k.c, bc, s, n);
    for (size_t l = 0; l < n; l++) s[l] = LANES8[l].cram;
    k.vt->from_dec(&k.c, cram, s, n);
    if (from) {
        FILE *fi = fopen(from, "rb");
        if (!fi) m1_die("cannot read %s", from);
        char line[1024];
        int got = 0;
        while (fgets(line, sizeof line, fi)) {
            long st;
            double tt;
            unsigned long l;
            char hx[6][80];
            if (sscanf(line, "S %ld %la %lu %79s %79s %79s %79s %79s %79s", &st, &tt, &l, hx[0], hx[1], hx[2], hx[3], hx[4], hx[5]) != 9) continue;
            if (st != step0 || l >= n) continue;
            for (int i = 0; i < 6; i++) unhex(hx[i], (unsigned char *)y[i] + l * k.vt->esz, k.vt->esz);
            got++;
        }
        fclose(fi);
        if (got != (int)n) m1_die("%s holds %d lanes at step %ld", from, got, step0);
    }
    FILE *f = fopen(argv[7], "wb");
    if (!f) m1_die("cannot write %s", argv[7]);
    kind_header(f, &k);
    fprintf(f, "# traj t0 %a nsteps %ld h %s step0 %ld short %a every %ld lanes 8 (E8's), the real frame, jd_epoch %.1f\n", m.t0, nsteps, h, step0,
            hs, every, m.jd_epoch);
    TrajOut o = {f, k.vt->esz, every};
    const double hd = strtod(h, NULL);
    traj_cb(&o, step0, m.t0 + (double)step0 * hd, y, n);
    k.vt->rk4(&k.c, y, bc, cram, h, step0, nsteps, traj_cb, &o, n);
    if (hs > 0) {
        TrajOut o1 = {f, k.vt->esz, 1};
        k.vt->rk4_short(&k.c, y, bc, cram, m.t0 + (double)(step0 + nsteps) * hd, hs, step0 + nsteps + 1, traj_cb, &o1, n);
    }
    ops_footer(f, &k);
    fclose(f);
    kclose(&k);
    return 0;
}

/* ------------------------------------------------------------------ objects: prop and fit */
typedef struct {
    char id[32];
    double t0;            /* the origin (TDB s), a multiple of 2^-20 */
    double y[6], bc, cram;
    int fitbc;
    long nobs;            /* pseudo-observations at t0 + 120 k, k = 0..nobs-1 */
    double (*obs)[3];
    long ntarget;
    double *target;       /* prediction times (prop) */
} Obj;

static Obj *read_objs(const char *path, long *nobj)
{
    FILE *f = fopen(path, "rb");
    if (!f) m1_die("cannot read %s", path);
    long cap = 64, n = 0;
    Obj *O = (Obj *)calloc((size_t)cap, sizeof(Obj));
    long *got_o = (long *)calloc((size_t)cap, sizeof(long)), *got_t = (long *)calloc((size_t)cap, sizeof(long));
    char line[2048];
    Obj *cur = NULL;
    while (fgets(line, sizeof line, f)) {
        if (line[0] == '#') continue;
        if (!strncmp(line, "OBJ ", 4)) {
            if (n == cap) {
                cap *= 2;
                O = (Obj *)realloc(O, (size_t)cap * sizeof(Obj));
                got_o = (long *)realloc(got_o, (size_t)cap * sizeof(long));
                got_t = (long *)realloc(got_t, (size_t)cap * sizeof(long));
            }
            cur = &O[n];
            memset(cur, 0, sizeof *cur);
            got_o[n] = got_t[n] = 0;
            n++;
            if (sscanf(line + 4, "%31s %la %la %la %la %la %la %la %la %la %d %ld %ld", cur->id, &cur->t0, &cur->y[0], &cur->y[1], &cur->y[2],
                       &cur->y[3], &cur->y[4], &cur->y[5], &cur->bc, &cur->cram, &cur->fitbc, &cur->nobs, &cur->ntarget) != 13)
                m1_die("bad OBJ line: %s", line);
            cur->obs = cur->nobs ? malloc((size_t)cur->nobs * sizeof *cur->obs) : NULL;
            cur->target = cur->ntarget ? malloc((size_t)cur->ntarget * sizeof(double)) : NULL;
        } else if (!strncmp(line, "O ", 2) && cur) {
            long kk;
            double q[3];
            if (sscanf(line + 2, "%ld %la %la %la", &kk, &q[0], &q[1], &q[2]) != 4) m1_die("bad O line");
            long i = got_o[n - 1]++;
            if (i >= cur->nobs || kk != i) m1_die("object %s: observation %ld out of order", cur->id, kk);
            memcpy(cur->obs[i], q, sizeof q);
        } else if (!strncmp(line, "T ", 2) && cur) {
            long kk;
            double t;
            if (sscanf(line + 2, "%ld %la", &kk, &t) != 2) m1_die("bad T line");
            long i = got_t[n - 1]++;
            if (i >= cur->ntarget || kk != i) m1_die("object %s: target %ld out of order", cur->id, kk);
            cur->target[i] = t;
        }
    }
    fclose(f);
    for (long i = 0; i < n; i++)
        if (got_o[i] != O[i].nobs || got_t[i] != O[i].ntarget) m1_die("object %s: observations or targets incomplete", O[i].id);
    free(got_o);
    free(got_t);
    *nobj = n;
    return O;
}

/* positions at every 8th step (120 s) of an rk4 run at 15 s */
typedef struct {
    double (*pos)[8][3];  /* [obs][lane][xyz] */
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
    ObsCb o = {pos, ob->nobs, n, k->vt, &k->c};
    obs_cb(&o, 0, ob->t0, y, n);
    k->c.model.t0 = ob->t0;
    k->vt->rk4(&k->c, y, bc, cram, "15", 0, 8 * (ob->nobs - 1), obs_cb, &o, n);
    for (int i = 0; i < 6; i++) free(y[i]);
    free(bc);
    free(cram);
}

/* the least-squares step: solve min |J dp - r| by the normal equations, columns scaled to unit norm,
   Cholesky in long double */
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

/* B4: Gauss-Newton at native64. Parameters: the state at the span's start (6) and bc where fitbc; partials by
   finite differences as lanes of the same batch: lane 0 nominal, lanes 1..6 the state perturbed by 1 m and
   1e-3 m/s, lane 7 bc + 1e-4 m^2/kg. Each iteration applies its update; stop when every |dp_i| is below its
   threshold - 1e-8 |r| for a position (about 7 cm), 1e-8 |v| for a velocity (about 75 um/s), 1e-5 max(|bc|,
   1e-3 m^2/kg) for bc - that last update applied, or after maxit iterations. (The thresholds sit about 100 times
   above the iteration's noise floor that a development fit of one object showed: 3e-4 m, 5e-7 m/s and 3e-7 of bc,
   from the model's band edges and shadow edges.) The RMS reported is the last evaluated iterate's. */
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
    fprintf(f, "# fit objects %ld maxit %d; per object: FIT id converged iterations rms_m maxres_m nobs fitbc t0 x y z vx vy vz bc (%%a); then ITER lines\n", nobj, maxit);
    static const double DSTEP[7] = {1.0, 1.0, 1.0, 1e-3, 1e-3, 1e-3, 1e-4};
    for (long ob = 0; ob < nobj; ob++) {
        Obj *o = &O[ob];
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

/* predictions: each object from its origin t0 on the grid t0 + 15 j; at each target T (ascending): whole steps to
   the last grid time at or before T, then, on a copy, one short step hs = T - (t0 + 15 N) landing on T exactly
   (T and t0 multiples of 2^-20 s); the main state stays on the grid. Writes P id T x y z vx vy vz (%a). */
static int mode_prop(int argc, char **argv)
{
    if (argc < 6) m1_die("usage: prop <kind> <table> <in> <out>");
    long nobj;
    Obj *O = read_objs(argv[4], &nobj);
    m1_model m = model_real();
    K k;
    kopen(&k, argv[2], &m, 1, has(argc, argv, "--cr"));
    k.c.ctl_round64 = has(argc, argv, "--round64"); /* F7's control, E3's: the central term's -GM/r^3 rounded to binary64 */
    const size_t es = k.vt->esz;
    FILE *f = fopen(argv[5], "wb");
    if (!f) m1_die("cannot write %s", argv[5]);
    kind_header(f, &k);
    fprintf(f, "# prop objects %ld; columns: P id T x y z vx vy vz (binary64 of the kind's state, %%a), then the kind's hex\n", nobj);
    for (long ob = 0; ob < nobj; ob++) {
        Obj *o = &O[ob];
        void *y[6], *yc[6], *bc = vnew(&k, 1), *cram = vnew(&k, 1);
        for (int i = 0; i < 6; i++) {
            y[i] = vnew(&k, 1);
            yc[i] = vnew(&k, 1);
            k.vt->from_f64(&k.c, y[i], &o->y[i], 1);
        }
        k.vt->from_f64(&k.c, bc, &o->bc, 1);
        k.vt->from_f64(&k.c, cram, &o->cram, 1);
        k.c.model.t0 = o->t0;
        long step = 0;
        for (long q = 0; q < o->ntarget; q++) {
            const double T = o->target[q];
            const long N = (long)floor((T - o->t0) / 15.0);
            if (N < step) m1_die("object %s: targets not ascending", o->id);
            if (N > step) k.vt->rk4(&k.c, y, bc, cram, "15", step, N - step, NULL, NULL, 1);
            step = N;
            const double tg = o->t0 + 15.0 * (double)N, hs = T - tg;
            if (tg + hs != T || hs < 0 || hs >= 15.0) m1_die("object %s: target %a is not exact on the grid", o->id, T);
            for (int i = 0; i < 6; i++) memcpy(yc[i], y[i], es);
            if (hs > 0) k.vt->rk4_short(&k.c, yc, bc, cram, tg, hs, N + 1, NULL, NULL, 1);
            double out[6];
            for (int i = 0; i < 6; i++) k.vt->to_f64(&k.c, &out[i], yc[i], 1);
            fprintf(f, "P %s %a", o->id, T);
            for (int i = 0; i < 6; i++) fprintf(f, " %a", out[i]);
            for (int i = 0; i < 6; i++) phex(f, yc[i], es);
            fputc('\n', f);
        }
        fflush(f);
        for (int i = 0; i < 6; i++) { free(y[i]); free(yc[i]); }
        free(bc);
        free(cram);
    }
    ops_footer(f, &k);
    fclose(f);
    kclose(&k);
    return 0;
}

/* ------------------------------------------------------------------ F9 */
/* DEBRIS-E's E9 in the real frame: the whole model's force evaluation (degree 20, 28 bands, the Sun, the Moon, radiation
   pressure, the frame interpolated once a stage time), repeated at stage times inside the table, then rk4 steps at
   15 s from t0 = 1,000,000 s; wall time (QueryPerformanceCounter) and the thread's cycles */
#include <windows.h>
static double now_s(void)
{
    LARGE_INTEGER c, fq;
    QueryPerformanceCounter(&c);
    QueryPerformanceFrequency(&fq);
    return (double)c.QuadPart / (double)fq.QuadPart;
}
static uint64_t my_cycles(void)
{
    ULONG64 c = 0;
    QueryThreadCycleTime(GetCurrentThread(), &c);
    return (uint64_t)c;
}
static int mode_time(int argc, char **argv)
{
    if (argc < 7) m1_die("usage: time <kind> <table> <nlanes> <min_seconds> <out>");
    size_t n = (size_t)atol(argv[4]);
    double mins = atof(argv[5]);
    m1_model m = model_real();
    m.t0 = 1000000.0;
    K k;
    kopen(&k, argv[2], &m, n, has(argc, argv, "--cr"));
    void *y[6], *a[3], *bc = vnew(&k, n), *cram = vnew(&k, n);
    const char **s = (const char **)malloc(n * sizeof(char *));
    for (int i = 0; i < 6; i++) {
        y[i] = vnew(&k, n);
        for (size_t l = 0; l < n; l++) s[l] = LANES8[l % 8].y[i];
        k.vt->from_dec(&k.c, y[i], s, n);
    }
    for (int i = 0; i < 3; i++) a[i] = vnew(&k, n);
    for (size_t l = 0; l < n; l++) s[l] = LANES8[l % 8].bc;
    k.vt->from_dec(&k.c, bc, s, n);
    for (size_t l = 0; l < n; l++) s[l] = LANES8[l % 8].cram;
    k.vt->from_dec(&k.c, cram, s, n);
    FILE *f = fopen(argv[6], "wb");
    if (!f) m1_die("cannot write %s", argv[6]);
    kind_header(f, &k);
    long ne = 0;
    double t0 = now_s(), t1;
    uint64_t c0 = my_cycles();
    do {
        k.vt->accel(&k.c, a, 1000000.0 + 60.0 * (double)(ne % 1000), (const void *const *)y, bc, cram, n);
        ne++;
        t1 = now_s();
    } while (t1 - t0 < mins || ne < 2);
    uint64_t c1 = my_cycles();
    fprintf(f, "accel lanes %lu evals %ld wall_s %.6f per_lane_eval_us %.3f thread_cycles %llu per_lane_eval_cycles %.0f\n",
            (unsigned long)n, ne, t1 - t0, (t1 - t0) / ((double)ne * n) * 1e6, (unsigned long long)(c1 - c0),
            (double)(c1 - c0) / ((double)ne * n));
    long st = 0;
    t0 = now_s();
    c0 = my_cycles();
    do {
        k.vt->rk4(&k.c, y, bc, cram, "15", st, 1, NULL, NULL, n);
        st++;
        t1 = now_s();
    } while (t1 - t0 < mins || st < 2);
    c1 = my_cycles();
    double per_step = (t1 - t0) / st;
    fprintf(f, "rk4 lanes %lu steps %ld wall_s %.6f per_step_s %.6f per_object_day_s %.3f thread_cycles %llu\n",
            (unsigned long)n, st, t1 - t0, per_step, per_step * 5760.0 / (double)n, (unsigned long long)(c1 - c0));
    ops_footer(f, &k);
    fclose(f);
    kclose(&k);
    return 0;
}

int main(int argc, char **argv)
{
    if (argc < 2) m1_die("usage: m1f <mode> ...");
    const char *mode = argv[1];
    const char *table = !strcmp(mode, "fit") ? argv[2] : (argc > 3 ? argv[3] : NULL);
    load_inputs(table);
    if (!strcmp(mode, "f1")) return mode_f1(argc, argv);
    if (!strcmp(mode, "f4")) return mode_f4(argc, argv);
    if (!strcmp(mode, "frames")) return mode_frames(argc, argv);
    if (!strcmp(mode, "traj")) return mode_traj(argc, argv);
    if (!strcmp(mode, "fit")) return mode_fit(argc, argv);
    if (!strcmp(mode, "prop")) return mode_prop(argc, argv);
    if (!strcmp(mode, "time")) return mode_time(argc, argv);
    m1_die("no mode %s", mode);
    return 2;
}
