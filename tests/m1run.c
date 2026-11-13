/* m1run.c - cft-debris M1: the gates' driver. Runs one number kind on one
 * gate's inputs and writes every result as the hexadecimal of its encoding
 * (most significant byte first), so the gates compare bits, not printouts.
 *
 * cft-debris, MIT licence (see LICENSE at the repository root). Written by
 * DEBRIS-E, 2026-11-13.
 *
 *   m1run tables  <kind> <nmax> <out>
 *   m1run e1      <kernel> <kind> <nlanes> <seed> <out> [--cr] [--nmin a] [--nmax b]
 *                 kernels: grav central third cheb shadowgeom srp drag rot
 *   m1run traj    <kind> <nsteps> <h> <out> [--cr] [--plant lane] [--round64] [--every k]
 *                 [--step0 s --from file]
 *   m1run lasser  <kind> <stride> <nmin> <nmax> <out>
 *   m1run lasser3 <kind> <stride> <out>
 *   m1run testpo  <kind> <out> [--plant]
 *   m1run e6      <kind> <nstates> <seed> <states_out> <forces_out> [--plant drag|srp|grav]
 *   m1run time    <kind> <nlanes> <min_seconds> <out>
 * Inputs: the downloads folder (M1_DOWNLOADS overrides it), read only.
 */
#define __USE_MINGW_ANSI_STDIO 1
#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <windows.h>
#include "m1.h"

static char DL[512] = "C:/Users/logan/source/repos/cft-debris-downloads/";
static char *dlpath(const char *rel)
{
    static char buf[8][768];
    static int k = 0;
    char *b = buf[k++ & 7];
    snprintf(b, 768, "%s%s", DL, rel);
    return b;
}
#define P_GFC "EIGEN6-C4.gfc/EIGEN6-C4.gfc"
#define P_DEBIN "lnxp1900p2053.421/lnxp1900p2053.421"
#define P_DEHDR "header.421/header.421"
#define P_ITRF "00orbit_itrf.txt/00orbit_itrf.txt"
#define P_ICRF "00orbit_icrf.txt/00orbit_icrf.txt"
#define P_TESTPO "testpo.421/testpo.421"

static m1_gfc G;
static m1_de DE;

typedef struct K {
    const m1_vt *vt;
    m1_ctx c;
} K;

static void load_inputs(void)
{
    const char *e = getenv("M1_DOWNLOADS");
    if (e && *e) snprintf(DL, sizeof DL, "%s", e);
    if (m1_gfc_load(&G, dlpath(P_GFC), M1_NMAX)) m1_die("gfc: %s", G.err);
    if (m1_de_open(&DE, dlpath(P_DEBIN), dlpath(P_DEHDR))) m1_die("de421: %s", DE.err);
}

static void kopen(K *k, const char *name, const m1_model *m, size_t max_lanes, int cr, int round64, int c20,
                  double c20rel)
{
    k->vt = m1_vt_by_name(name);
    if (!k->vt) m1_die("no kind %s", name);
    memset(&k->c, 0, sizeof k->c);
    if (cft_open(NULL, 0, &k->c.dev) != CFT_OK) m1_die("cft_open(NULL) failed");
    k->c.cr_transc = cr;
    k->c.ctl_round64 = round64;
    k->c.ctl_c20 = c20;
    k->c.ctl_c20_rel = c20rel;
    if (k->vt->setup(&k->c, m, &G, &DE, max_lanes)) m1_die("setup %s", name);
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
    fprintf(f, "# kind %s esz %lu native %d cr_transc %d round64 %d c20 %d build_id %s\n", k->vt->name,
            (unsigned long)k->vt->esz, k->vt->native, k->c.cr_transc, k->c.ctl_round64, k->c.ctl_c20, cft_build_id());
}
static void ops_footer(FILE *f, const K *k)
{
    static const char *nm[M1_NOP] = {"add", "sub", "mul", "div", "sqrt", "fma", "neg", "cmp", "sel",
                                     "exp", "sin", "cos", "asin", "acos", "cvt"};
    fprintf(f, "# lane-ops");
    for (int i = 0; i < M1_NOP; i++) fprintf(f, " %s=%llu", nm[i], (unsigned long long)k->c.nops[i]);
    fprintf(f, "\n# cft_flags 0x%x\n", (unsigned)k->c.cft_flags);
}

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
static double urange(double a, double b) { return a + (b - a) * urand(); }
/* a direction uniform on the sphere, times radius rad */
static void rdir(double rad, double *x, double *y, double *z)
{
    double zz = 2.0 * urand() - 1.0, ph = 6.283185307179586 * urand(), s = sqrt(1.0 - zz * zz);
    *x = rad * s * cos(ph);
    *y = rad * s * sin(ph);
    *z = rad * zz;
}

/* ------------------------------------------------------------- the model */
static m1_model model_default(int nmax)
{
    m1_model m;
    memset(&m, 0, sizeof m);
    m.central = 1;
    m.nmin = 2;
    m.nmax = nmax;
    m.sun = m.moon = m.drag = m.srp = 1;
    m.nbands = 28;
    m.jd_epoch = 2454650.5; /* 2008-07-03 00:00 TDB */
    return m;
}

/* ---------------------------------------------------------------- tables */
static FILE *TBL;
static size_t TBL_ESZ;
static void tbl_cb(void *u, const char *name, const void *p, size_t count)
{
    (void)u;
    for (size_t i = 0; i < count; i++) {
        fprintf(TBL, "%s %lu", name, (unsigned long)i);
        phex(TBL, (const unsigned char *)p + i * TBL_ESZ, TBL_ESZ);
        fputc('\n', TBL);
    }
}
static int mode_tables(int argc, char **argv)
{
    if (argc < 5) m1_die("usage: tables <kind> <nmax> <out>");
    int nmax = atoi(argv[3]);
    m1_model m = model_default(nmax);
    K k;
    kopen(&k, argv[2], &m, 64, 0, 0, 0, 0);
    TBL = fopen(argv[4], "w");
    if (!TBL) m1_die("cannot write %s", argv[4]);
    TBL_ESZ = k.vt->esz;
    kind_header(TBL, &k);
    fprintf(TBL, "# gfc %s GM %s radius %s max_degree %d norm %s tide %s gfc_lines %d dup %d other %d missing %d "
                 "missing_deg1 %d Dexp %d\n",
            G.modelname, G.gm, G.radius, G.max_degree, G.norm, G.tide, G.ngfc, G.ndup, G.nother, G.nmissing,
            G.nmissing_deg1, G.ndexp);
    fprintf(TBL, "# de421 ss %.1f %.1f %.1f nrec %ld ncoeff %d au_km %a emrat %a\n", DE.ss[0], DE.ss[1], DE.ss[2],
            DE.nrec, DE.ncoeff, DE.au_km, DE.emrat);
    k.vt->tables(&k.c, tbl_cb, NULL);
    ops_footer(TBL, &k);
    fclose(TBL);
    kclose(&k);
    return 0;
}

/* -------------------------------------------------------------------- E1 */
static int has_opt(int argc, char **argv, const char *o)
{
    for (int i = 0; i < argc; i++)
        if (!strcmp(argv[i], o)) return 1;
    return 0;
}
static const char *opt_val(int argc, char **argv, const char *o, const char *def)
{
    for (int i = 0; i + 1 < argc; i++)
        if (!strcmp(argv[i], o)) return argv[i + 1];
    return def;
}

/* n lanes of nin binary64 inputs -> kind vectors */
static void **kin(K *k, double *const *in, int nin, size_t n)
{
    void **v = (void **)calloc((size_t)nin, sizeof(void *));
    for (int j = 0; j < nin; j++) {
        v[j] = vnew(k, n);
        k->vt->from_f64(&k->c, v[j], in[j], n);
    }
    return v;
}
static double **dnew(int nin, size_t n)
{
    double **d = (double **)calloc((size_t)nin, sizeof(double *));
    for (int j = 0; j < nin; j++) d[j] = (double *)calloc(n, sizeof(double));
    return d;
}

static void write_inputs(const char *out, double *const *in, int nin, size_t n)
{
    char path[600];
    snprintf(path, sizeof path, "%s.in", out);
    FILE *f = fopen(path, "w");
    if (!f) m1_die("cannot write %s", path);
    fprintf(f, "# the kernel's binary64 inputs, a lane a line (hex of the encoding)\n");
    for (size_t i = 0; i < n; i++) {
        fprintf(f, "%lu", (unsigned long)i);
        for (int j = 0; j < nin; j++) phex(f, &in[j][i], 8);
        fputc('\n', f);
    }
    fclose(f);
}

static int mode_e1(int argc, char **argv)
{
    if (argc < 7) m1_die("usage: e1 <kernel> <kind> <nlanes> <seed> <out> [--cr] [--nmin a] [--nmax b]");
    const char *kern = argv[2];
    size_t n = (size_t)atol(argv[4]);
    sm_state = strtoull(argv[5], NULL, 0);
    const int cr = has_opt(argc, argv, "--cr");
    const int nmin = atoi(opt_val(argc, argv, "--nmin", "2")), nmax = atoi(opt_val(argc, argv, "--nmax", "20"));
    m1_model m = model_default(nmax);
    K k;
    kopen(&k, argv[3], &m, n, cr, 0, 0, 0);
    FILE *f = fopen(argv[6], "w");
    if (!f) m1_die("cannot write %s", argv[6]);
    kind_header(f, &k);
    fprintf(f, "# e1 kernel %s nlanes %lu seed %s nmin %d nmax %d\n", kern, (unsigned long)n, argv[5], nmin, nmax);
    int nout = 0;
    void *out[16];
    if (!strcmp(kern, "grav") || !strcmp(kern, "central")) {
        /* lanes vary in direction (uniform on the sphere) and radius (grav: 6,600 to 8,000 km;
           central: 6,600 to 43,000 km) */
        double **in = dnew(3, n);
        for (size_t i = 0; i < n; i++)
            rdir(!strcmp(kern, "grav") ? urange(6.6e6, 8.0e6) : urange(6.6e6, 4.3e7), &in[0][i], &in[1][i], &in[2][i]);
        write_inputs(argv[6], in, 3, n);
        void **v = kin(&k, in, 3, n);
        for (int j = 0; j < 3; j++) out[j] = vnew(&k, n);
        nout = 3;
        if (!strcmp(kern, "grav")) k.vt->grav(&k.c, out, (const void *const *)v, nmin, nmax, n);
        else k.vt->central(&k.c, out, (const void *const *)v, n);
    } else if (!strcmp(kern, "third")) {
        /* r: LEO (6,600 to 8,000 km); the Sun 1.47e11 to 1.52e11 m and the Moon 3.56e8 to 4.07e8 m away,
           each direction uniform */
        double **in = dnew(9, n);
        for (size_t i = 0; i < n; i++) {
            rdir(urange(6.6e6, 8.0e6), &in[0][i], &in[1][i], &in[2][i]);
            rdir(urange(1.47e11, 1.52e11), &in[3][i], &in[4][i], &in[5][i]);
            rdir(urange(3.56e8, 4.07e8), &in[6][i], &in[7][i], &in[8][i]);
        }
        write_inputs(argv[6], in, 9, n);
        void **v = kin(&k, in, 9, n);
        for (int j = 0; j < 6; j++) out[j] = vnew(&k, n);
        nout = 6;
        k.vt->third(&k.c, out, (const void *const *)v, (const void *const *)(v + 3), 0, 0, n);
        k.vt->third(&k.c, out + 3, (const void *const *)v, (const void *const *)(v + 6), 0, 1, n);
    } else if (!strcmp(kern, "cheb")) {
        /* lanes vary in epoch: a JED uniform over DE421's coverage (a whole half-day) plus seconds
           that are multiples of 1/1024 s, so each lane's time since its sub-interval is exact */
        long *rec[3];
        int *sub[3];
        double *dt[3];
        for (int j = 0; j < 3; j++) {
            rec[j] = (long *)calloc(n, sizeof(long));
            sub[j] = (int *)calloc(n, sizeof(int));
            dt[j] = (double *)calloc(n, sizeof(double));
        }
        static const int ser[3] = {M1_SER_MOON, M1_SER_SUN, M1_SER_EMB};
        double nhalf = floor((DE.ss[1] - DE.ss[0]) * 2.0) - 1.0;
        for (size_t i = 0; i < n; i++) {
            double jd0 = DE.ss[0] + 0.5 * floor(urand() * nhalf);
            double sec = floor(urand() * 43200.0 * 1024.0) / 1024.0;
            for (int j = 0; j < 3; j++)
                if (m1_de_locate(&DE, ser[j], jd0, sec, &rec[j][i], &sub[j][i], &dt[j][i])) m1_die("locate");
        }
        {
            char path[600];
            snprintf(path, sizeof path, "%s.in", argv[6]);
            FILE *fi = fopen(path, "w");
            if (!fi) m1_die("cannot write %s", path);
            fprintf(fi, "# lane, then for the Moon, the Sun and the EMB: record, sub-interval, seconds into it (%%a)\n");
            for (size_t i = 0; i < n; i++) {
                fprintf(fi, "%lu", (unsigned long)i);
                for (int j = 0; j < 3; j++) fprintf(fi, " %ld %d %a", rec[j][i], sub[j][i], dt[j][i]);
                fputc('\n', fi);
            }
            fclose(fi);
        }
        for (int j = 0; j < 15; j++) out[j] = vnew(&k, n);
        nout = 15;
        for (int j = 0; j < 3; j++) k.vt->series(&k.c, out + 3 * j, ser[j], rec[j], sub[j], dt[j], n);
        m1_ephq q = {{rec[0], rec[1], rec[2]}, {sub[0], sub[1], sub[2]}, {dt[0], dt[1], dt[2]}};
        k.vt->bodies(&k.c, out + 9, out + 12, &q, n);
    } else if (!strcmp(kern, "shadowgeom") || !strcmp(kern, "srp")) {
        /* r: LEO (6,600 to 7,500 km), the Sun 1.47e11 to 1.52e11 m away, directions uniform;
           cram 0.005 to 0.05 m^2/kg */
        double **in = dnew(7, n);
        for (size_t i = 0; i < n; i++) {
            rdir(urange(6.6e6, 7.5e6), &in[0][i], &in[1][i], &in[2][i]);
            rdir(urange(1.47e11, 1.52e11), &in[3][i], &in[4][i], &in[5][i]);
            in[6][i] = urange(0.005, 0.05);
        }
        write_inputs(argv[6], in, 7, n);
        void **v = kin(&k, in, 7, n);
        if (!strcmp(kern, "shadowgeom")) {
            for (int j = 0; j < 3; j++) out[j] = vnew(&k, n);
            nout = 3;
            k.vt->shadow_geom(&k.c, out, (const void *const *)v, (const void *const *)(v + 3), 0, n);
        } else {
            for (int j = 0; j < 4; j++) out[j] = vnew(&k, n);
            nout = 4;
            k.vt->srp(&k.c, out, out[3], (const void *const *)v, (const void *const *)(v + 3), 0, v[6], n);
        }
    } else if (!strcmp(kern, "drag")) {
        /* r: 100 to 1,100 km up (bands 9 to 27), direction uniform; v: 7.0 to 8.0 km/s, direction
           uniform; bc 0.002 to 0.05 m^2/kg */
        double **in = dnew(7, n);
        for (size_t i = 0; i < n; i++) {
            rdir(6378136.3 + urange(1.0e5, 1.1e6), &in[0][i], &in[1][i], &in[2][i]);
            rdir(urange(7.0e3, 8.0e3), &in[3][i], &in[4][i], &in[5][i]);
            in[6][i] = urange(0.002, 0.05);
        }
        write_inputs(argv[6], in, 7, n);
        void **v = kin(&k, in, 7, n);
        for (int j = 0; j < 3; j++) out[j] = vnew(&k, n);
        nout = 3;
        k.vt->drag(&k.c, out, (const void *const *)v, (const void *const *)(v + 3), v[6], n);
    } else if (!strcmp(kern, "rot")) {
        /* t: 0 to 10 days in multiples of 1/1024 s; r: LEO, direction uniform */
        double **in = dnew(4, n);
        for (size_t i = 0; i < n; i++) {
            in[0][i] = floor(urand() * 864000.0 * 1024.0) / 1024.0;
            rdir(urange(6.6e6, 8.0e6), &in[1][i], &in[2][i], &in[3][i]);
        }
        write_inputs(argv[6], in, 4, n);
        void **v = kin(&k, in, 4, n);
        for (int j = 0; j < 3; j++) out[j] = vnew(&k, n);
        nout = 3;
        k.vt->rotate(&k.c, out, (const void *const *)(v + 1), v[0], 0, 0, n);
    } else {
        m1_die("no kernel %s", kern);
    }
    for (size_t i = 0; i < n; i++) {
        fprintf(f, "%lu", (unsigned long)i);
        for (int j = 0; j < nout; j++) phex(f, (const unsigned char *)out[j] + i * k.vt->esz, k.vt->esz);
        fputc('\n', f);
    }
    ops_footer(f, &k);
    fclose(f);
    kclose(&k);
    return 0;
}

/* ------------------------------------------------------------------ traj */
/* the eight lanes of E2, E3 and E8: near-circular LEO orbits, 350 to 700 km
   up, inclinations 0.1 to 98.6 degrees; positions m, velocities m/s;
   bc = Cd A/(2m) and cram = Cr A/m in m^2/kg */
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
        fprintf(o->f, "S %ld %.3f %lu", step, t, (unsigned long)l);
        for (int i = 0; i < 6; i++) phex(o->f, (const unsigned char *)y[i] + l * o->esz, o->esz);
        fputc('\n', o->f);
    }
}
static cft_format kind_fmt(m1_kind k)
{
    switch (k) {
    case M1_NATIVE32: case M1_CFT32: return CFT_FP32;
    case M1_NATIVE64: case M1_CFT64: return CFT_FP64;
    case M1_CFT128: return CFT_FP128;
    default: return CFT_FP256;
    }
}
static int mode_traj(int argc, char **argv)
{
    if (argc < 6) m1_die("usage: traj <kind> <nsteps> <h> <out> [--cr] [--plant lane] [--round64] [--every k]");
    const size_t n = 8;
    long nsteps = atol(argv[3]);
    const char *h = argv[4];
    const int cr = has_opt(argc, argv, "--cr"), r64 = has_opt(argc, argv, "--round64");
    const int plant = atoi(opt_val(argc, argv, "--plant", "-1"));
    const int pcomp = atoi(opt_val(argc, argv, "--plant-comp", "0")); /* the component planted: 0 x .. 5 vz */
    const long every = atol(opt_val(argc, argv, "--every", "1"));
    const long step0 = atol(opt_val(argc, argv, "--step0", "0"));
    const char *from = opt_val(argc, argv, "--from", NULL);
    m1_model m = model_default(20);
    K k;
    kopen(&k, argv[2], &m, n, cr, r64, 0, 0);
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
        /* a segment restarted from a boundary state written by an earlier run (lines "S step t lane hex*6") */
        FILE *fi = fopen(from, "r");
        if (!fi) m1_die("cannot read %s", from);
        char line[1024];
        int got = 0;
        while (fgets(line, sizeof line, fi)) {
            long st;
            double tt;
            unsigned long l;
            char hx[6][80];
            if (sscanf(line, "S %ld %lf %lu %79s %79s %79s %79s %79s %79s", &st, &tt, &l, hx[0], hx[1], hx[2], hx[3],
                       hx[4], hx[5]) != 9)
                continue;
            if (st != step0 || l >= n) continue;
            for (int i = 0; i < 6; i++) unhex(hx[i], (unsigned char *)y[i] + l * k.vt->esz, k.vt->esz);
            got++;
        }
        fclose(fi);
        if (got != (int)n) m1_die("%s holds %d lanes at step %ld, not %lu", from, got, step0, (unsigned long)n);
    }
    if (plant >= 0 && plant < (int)n) {
        /* E2's negative control: one ulp up in lane `plant`'s component pcomp (0 = x) */
        if (pcomp < 0 || pcomp > 5) m1_die("--plant-comp 0..5");
        unsigned char *p = (unsigned char *)y[pcomp] + (size_t)plant * k.vt->esz;
        if (k.vt->kind == M1_NATIVE64) {
            double v;
            memcpy(&v, p, 8);
            v = nextafter(v, INFINITY);
            memcpy(p, &v, 8);
        } else if (k.vt->kind == M1_NATIVE32) {
            float v;
            memcpy(&v, p, 4);
            v = nextafterf(v, INFINITY);
            memcpy(p, &v, 4);
        } else {
            unsigned char t[32];
            if (cft_next_up(k.c.dev, kind_fmt(k.vt->kind), p, t, 1, NULL) != CFT_OK) m1_die("cft_next_up");
            memcpy(p, t, k.vt->esz);
        }
    }
    FILE *f = fopen(argv[5], "w");
    if (!f) m1_die("cannot write %s", argv[5]);
    kind_header(f, &k);
    fprintf(f, "# traj nsteps %ld h %s step0 %ld plant %d plant_comp %d every %ld lanes %lu model central 1 nmin 2 nmax 20 sun 1 "
               "moon 1 drag 1 (28 bands) srp 1 jd_epoch %.1f\n",
            nsteps, h, step0, plant, pcomp, every, (unsigned long)n, m.jd_epoch);
    TrajOut o = {f, k.vt->esz, every};
    traj_cb(&o, step0, (double)step0 * strtod(h, NULL), y, n);
    k.vt->rk4(&k.c, y, bc, cram, h, step0, nsteps, traj_cb, &o, n);
    ops_footer(f, &k);
    fclose(f);
    kclose(&k);
    return 0;
}

/* ---------------------------------------------------------------- lasser */
typedef struct {
    char t[64], x[3][64];
} OrbRow;
static OrbRow *read_orbit(const char *path, long *nrows)
{
    FILE *f = fopen(path, "r");
    if (!f) m1_die("cannot read %s", path);
    long cap = 4096, n = 0;
    OrbRow *r = (OrbRow *)malloc((size_t)cap * sizeof(OrbRow));
    char line[1024];
    while (fgets(line, sizeof line, f)) {
        if (line[0] == '#' || line[0] == 'g') continue;
        char a[10][64];
        int got = sscanf(line, "%63s %63s %63s %63s %63s %63s %63s %63s %63s %63s", a[0], a[1], a[2], a[3], a[4], a[5],
                         a[6], a[7], a[8], a[9]);
        if (got != 10) continue;
        if (n == cap) {
            cap *= 2;
            r = (OrbRow *)realloc(r, (size_t)cap * sizeof(OrbRow));
        }
        snprintf(r[n].t, 64, "%s", a[0]);
        for (int i = 0; i < 3; i++) snprintf(r[n].x[i], 64, "%s", a[1 + i]);
        n++;
    }
    fclose(f);
    *nrows = n;
    return r;
}
static int mode_lasser(int argc, char **argv)
{
    if (argc < 7) m1_die("usage: lasser <kind> <stride> <nmin> <nmax> <out>");
    long stride = atol(argv[3]);
    int nmin = atoi(argv[4]), nmax = atoi(argv[5]);
    long nr;
    OrbRow *R = read_orbit(dlpath(P_ITRF), &nr);
    m1_model m = model_default(nmax);
    /* lanes per batch: V and W at degree nmax+1 for every lane within about 192 MB */
    const m1_vt *vt = m1_vt_by_name(argv[2]);
    if (!vt) m1_die("kind");
    size_t ntri = M1_TRI(nmax + 1, nmax + 1) + 1;
    size_t chunk = (size_t)(192.0e6 / (2.0 * ntri * vt->esz));
    if (chunk > 512) chunk = 512;
    if (chunk < 1) chunk = 1;
    K k;
    kopen(&k, argv[2], &m, chunk, 0, 0, 0, 0);
    FILE *f = fopen(argv[6], "w");
    if (!f) m1_die("cannot write %s", argv[6]);
    kind_header(f, &k);
    fprintf(f, "# lasser gravity, Earth-fixed, degrees %d..%d, every %ld-th of %ld epochs, %lu lanes a batch\n", nmin,
            nmax, stride, nr, (unsigned long)chunk);
    long *idx = (long *)malloc((size_t)nr * sizeof(long));
    long ns = 0;
    for (long i = 0; i < nr; i += stride) idx[ns++] = i;
    void *r[3], *a[3];
    for (int j = 0; j < 3; j++) {
        r[j] = vnew(&k, chunk);
        a[j] = vnew(&k, chunk);
    }
    const char **s = (const char **)malloc(chunk * sizeof(char *));
    for (long b = 0; b < ns; b += (long)chunk) {
        size_t nl = (size_t)((ns - b) < (long)chunk ? (ns - b) : (long)chunk);
        for (int j = 0; j < 3; j++) {
            for (size_t l = 0; l < nl; l++) s[l] = R[idx[b + (long)l]].x[j];
            k.vt->from_dec(&k.c, r[j], s, nl);
        }
        k.vt->grav(&k.c, a, (const void *const *)r, nmin, nmax, nl);
        for (size_t l = 0; l < nl; l++) {
            fprintf(f, "%ld %s", idx[b + (long)l], R[idx[b + (long)l]].t);
            for (int j = 0; j < 3; j++) phex(f, (const unsigned char *)a[j] + l * k.vt->esz, k.vt->esz);
            fputc('\n', f);
        }
        fflush(f);
    }
    ops_footer(f, &k);
    fclose(f);
    kclose(&k);
    return 0;
}

/* TDB - TT, s: the two-term form DEBRIS-C's m1b_check.py used (g = 357.53 + 0.98560028 (JD - 2451545) deg) */
static double tdb_minus_tt(double jd)
{
    double g = (357.53 + 0.98560028 * (jd - 2451545.0)) * (3.141592653589793 / 180.0);
    return 0.001657 * sin(g) + 0.000014 * sin(2.0 * g);
}
static int mode_lasser3(int argc, char **argv)
{
    if (argc < 5) m1_die("usage: lasser3 <kind> <stride> <out>");
    long stride = atol(argv[3]);
    long nr;
    OrbRow *R = read_orbit(dlpath(P_ICRF), &nr);
    m1_model m = model_default(0);
    size_t chunk = 512;
    K k;
    kopen(&k, argv[2], &m, chunk, 0, 0, 0, 0);
    FILE *f = fopen(argv[4], "w");
    if (!f) m1_die("cannot write %s", argv[4]);
    kind_header(f, &k);
    fprintf(f, "# lasser3 direct tides (Sun, Moon), ICRF, every %ld-th of %ld epochs; TT = GPS + 51.184 s, TDB - TT "
               "two-term\n",
            stride, nr);
    long *idx = (long *)malloc((size_t)nr * sizeof(long));
    long ns = 0;
    for (long i = 0; i < nr; i += stride) idx[ns++] = i;
    void *r[3], *sun[3], *moon[3], *as[3], *am[3];
    for (int j = 0; j < 3; j++) {
        r[j] = vnew(&k, chunk);
        sun[j] = vnew(&k, chunk);
        moon[j] = vnew(&k, chunk);
        as[j] = vnew(&k, chunk);
        am[j] = vnew(&k, chunk);
    }
    long *rec[3];
    int *sub[3];
    double *dt[3];
    for (int j = 0; j < 3; j++) {
        rec[j] = (long *)calloc(chunk, sizeof(long));
        sub[j] = (int *)calloc(chunk, sizeof(int));
        dt[j] = (double *)calloc(chunk, sizeof(double));
    }
    static const int ser[3] = {M1_SER_MOON, M1_SER_SUN, M1_SER_EMB};
    const char **s = (const char **)malloc(chunk * sizeof(char *));
    const double jd0 = 2454650.5; /* MJD 54650.0, GPS */
    for (long b = 0; b < ns; b += (long)chunk) {
        size_t nl = (size_t)((ns - b) < (long)chunk ? (ns - b) : (long)chunk);
        for (size_t l = 0; l < nl; l++) {
            long e = idx[b + (long)l];
            double mjd = strtod(R[e].t, NULL);
            if (fabs(mjd - (54650.0 + 30.0 * e / 86400.0)) > 1e-9) m1_die("epoch %ld is not 30 s apart", e);
            double sec = 30.0 * e + 51.184;
            sec += tdb_minus_tt(jd0 + sec / 86400.0);
            for (int j = 0; j < 3; j++)
                if (m1_de_locate(&DE, ser[j], jd0, sec, &rec[j][l], &sub[j][l], &dt[j][l])) m1_die("locate");
        }
        for (int j = 0; j < 3; j++) {
            for (size_t l = 0; l < nl; l++) s[l] = R[idx[b + (long)l]].x[j];
            k.vt->from_dec(&k.c, r[j], s, nl);
        }
        m1_ephq q = {{rec[0], rec[1], rec[2]}, {sub[0], sub[1], sub[2]}, {dt[0], dt[1], dt[2]}};
        k.vt->bodies(&k.c, sun, moon, &q, nl);
        k.vt->third(&k.c, as, (const void *const *)r, (const void *const *)sun, 0, 0, nl);
        k.vt->third(&k.c, am, (const void *const *)r, (const void *const *)moon, 0, 1, nl);
        for (size_t l = 0; l < nl; l++) {
            fprintf(f, "%ld %s", idx[b + (long)l], R[idx[b + (long)l]].t);
            for (int j = 0; j < 3; j++) phex(f, (const unsigned char *)as[j] + l * k.vt->esz, k.vt->esz);
            for (int j = 0; j < 3; j++) phex(f, (const unsigned char *)am[j] + l * k.vt->esz, k.vt->esz);
            fputc('\n', f);
        }
    }
    ops_footer(f, &k);
    fclose(f);
    kclose(&k);
    return 0;
}

/* ---------------------------------------------------------------- testpo */
typedef struct {
    long line;
    double jed;
    int t, c, x;
    char val[64];
} TpRow;
static int mode_testpo(int argc, char **argv)
{
    if (argc < 4) m1_die("usage: testpo <kind> <out> [--plant]");
    const int plant = has_opt(argc, argv, "--plant");
    FILE *fi = fopen(dlpath(P_TESTPO), "r");
    if (!fi) m1_die("testpo");
    long cap = 8192, nt = 0, ln = 0, skipped = 0;
    TpRow *T = (TpRow *)malloc((size_t)cap * sizeof(TpRow));
    char line[512];
    int started = 0;
    while (fgets(line, sizeof line, fi)) {
        ln++;
        if (!started) {
            char w[16];
            if (sscanf(line, "%15s", w) == 1 && !strcmp(w, "EOT")) started = 1;
            continue;
        }
        char de[16], date[32], jed[64], v[64];
        int t, c, x;
        if (sscanf(line, "%15s %31s %63s %d %d %d %63s", de, date, jed, &t, &c, &x, v) != 7) continue;
        int ok = (t == 3 || t == 10 || t == 11 || t == 12 || t == 13) && (c == 3 || c == 10 || c == 11 || c == 12 || c == 13);
        if (!ok || x < 1 || x > 3) continue;
        double j = strtod(jed, NULL);
        if (!(j >= DE.ss[0] && j <= DE.ss[1])) {
            skipped++;
            continue;
        }
        if (nt == cap) {
            cap *= 2;
            T = (TpRow *)realloc(T, (size_t)cap * sizeof(TpRow));
        }
        T[nt].line = ln - 1; /* 0-based line index, as DEBRIS-C's script */
        T[nt].jed = j;
        T[nt].t = t;
        T[nt].c = c;
        T[nt].x = x;
        snprintf(T[nt].val, 64, "%s", v);
        nt++;
    }
    fclose(fi);
    static const int ser[3] = {M1_SER_MOON, M1_SER_SUN, M1_SER_EMB};
    long prec = -1, pline = -1;
    int psub = 0, pcomp = 0;
    if (plant) {
        /* E5's planted control (version 2): the Moon's first coefficient OF THE COORDINATE the first selected
           point involving the Moon tests, in that point's sub-interval, raised by 1e-3 km in the record itself.
           (Version 1 planted in x whatever the point tested, and the point tested another: no point moved.) */
        for (long i = 0; i < nt; i++)
            if (T[i].t == 10 || T[i].c == 10) {
                double dts;
                if (m1_de_locate(&DE, M1_SER_MOON, T[i].jed, 0.0, &prec, &psub, &dts)) m1_die("locate");
                pcomp = T[i].x - 1;
                pline = T[i].line;
                break;
            }
        if (prec < 0) m1_die("no Moon point to plant");
        double *rr = (double *)(DE.raw + (size_t)(prec + 2) * (size_t)DE.ncoeff * 8);
        int at = DE.ipt[M1_SER_MOON][0] - 1 + DE.ipt[M1_SER_MOON][1] * (pcomp + 3 * psub);
        rr[at] += 1e-3;
    }
    m1_model m = model_default(0);
    K k;
    kopen(&k, argv[2], &m, (size_t)nt, 0, 0, 0, 0);
    FILE *f = fopen(argv[3], "w");
    if (!f) m1_die("cannot write %s", argv[3]);
    kind_header(f, &k);
    fprintf(f, "# testpo points %ld (bodies 3 10 11 12 13, coordinates 1-3, inside JED %.1f..%.1f), skipped outside "
               "%ld, plant %d (record %ld sub %d coordinate %d line %ld)\n",
            nt, DE.ss[0], DE.ss[1], skipped, plant, prec, psub, pcomp + 1, pline);
    /* each (target, centre) pair is one batch */
    long *rec[3];
    int *sub[3];
    double *dt[3];
    for (int j = 0; j < 3; j++) {
        rec[j] = (long *)calloc((size_t)nt, sizeof(long));
        sub[j] = (int *)calloc((size_t)nt, sizeof(int));
        dt[j] = (double *)calloc((size_t)nt, sizeof(double));
    }
    long *pick = (long *)malloc((size_t)nt * sizeof(long));
    void *o[3];
    for (int j = 0; j < 3; j++) o[j] = vnew(&k, (size_t)nt);
    static const int B[5] = {3, 10, 11, 12, 13};
    for (int a = 0; a < 5; a++)
        for (int b = 0; b < 5; b++) {
            long np = 0;
            for (long i = 0; i < nt; i++)
                if (T[i].t == B[a] && T[i].c == B[b]) pick[np++] = i;
            if (!np) continue;
            for (long l = 0; l < np; l++)
                for (int j = 0; j < 3; j++)
                    if (m1_de_locate(&DE, ser[j], T[pick[l]].jed, 0.0, &rec[j][l], &sub[j][l], &dt[j][l])) m1_die("locate");
            m1_ephq q = {{rec[0], rec[1], rec[2]}, {sub[0], sub[1], sub[2]}, {dt[0], dt[1], dt[2]}};
            k.vt->pleph(&k.c, o, B[a], B[b], &q, (size_t)np);
            for (long l = 0; l < np; l++) {
                const TpRow *r = &T[pick[l]];
                fprintf(f, "%ld %.1f %d %d %d %s", r->line, r->jed, r->t, r->c, r->x, r->val);
                phex(f, (const unsigned char *)o[r->x - 1] + (size_t)l * k.vt->esz, k.vt->esz);
                fprintf(f, " rec %ld\n", rec[0][l]);
            }
        }
    ops_footer(f, &k);
    fclose(f);
    kclose(&k);
    return 0;
}

/* -------------------------------------------------------------------- E6 */
static int mode_e6(int argc, char **argv)
{
    if (argc < 7) m1_die("usage: e6 <kind> <nstates> <seed> <states_out> <forces_out> [--plant drag|srp|grav]");
    size_t n = (size_t)atol(argv[3]);
    sm_state = strtoull(argv[4], NULL, 0);
    const char *plant = opt_val(argc, argv, "--plant", "none");
    m1_model m = model_default(20);
    m.nbands = 1;
    m.band_h0 = "400000";
    m.band_rho0 = "3.725e-12";
    m.band_hs = "58515";
    K k;
    kopen(&k, argv[2], &m, n, 0, 0, !strcmp(plant, "grav"), 0.01);
    /* the states: LEO, 300 to 800 km up, direction uniform, speed circular times 0.99 to 1.01 in a random
       direction perpendicular-ish to r; epochs t = 0 to 20 days after 2008-07-03 00:00 TDB in whole seconds;
       area 0.5 to 20 m^2, mass 50 to 2000 kg, Cd 2.0 to 2.4, Cr 1.0 to 1.8 */
    double **in = dnew(15, n);
    for (size_t i = 0; i < n; i++) {
        double r = 6378136.3 + urange(3.0e5, 8.0e5), x, y, z, ux, uy, uz;
        rdir(r, &x, &y, &z);
        rdir(1.0, &ux, &uy, &uz);
        double d = (ux * x + uy * y + uz * z) / r;
        ux -= d * x / r;
        uy -= d * y / r;
        uz -= d * z / r;
        double un = sqrt(ux * ux + uy * uy + uz * uz), v = sqrt(3.986004415e14 / r) * urange(0.99, 1.01);
        in[0][i] = floor(urand() * 20.0 * 86400.0);
        in[1][i] = x;
        in[2][i] = y;
        in[3][i] = z;
        in[4][i] = v * ux / un;
        in[5][i] = v * uy / un;
        in[6][i] = v * uz / un;
        in[7][i] = urange(0.5, 20.0);   /* A */
        in[8][i] = urange(50.0, 2000.0); /* mass */
        in[9][i] = urange(2.0, 2.4);    /* Cd */
        in[10][i] = urange(1.0, 1.8);   /* Cr */
        double cdp = !strcmp(plant, "drag") ? 1.01 : 1.0, crp = !strcmp(plant, "srp") ? 1.01 : 1.0;
        in[11][i] = (in[9][i] * cdp) * in[7][i] / (2.0 * in[8][i]); /* bc */
        in[12][i] = (in[10][i] * crp) * in[7][i] / in[8][i];       /* cram */
    }
    FILE *fs = fopen(argv[5], "w");
    if (!fs) m1_die("cannot write %s", argv[5]);
    fprintf(fs, "# e6 states: i t_tdb_s x y z vx vy vz area mass cd cr (C99 hex floats, binary64); epoch JD %.1f TDB "
                "seed %s plant %s\n",
            m.jd_epoch, argv[4], plant);
    for (size_t i = 0; i < n; i++) {
        fprintf(fs, "%lu", (unsigned long)i);
        for (int j = 0; j < 11; j++) fprintf(fs, " %a", in[j][i]);
        fputc('\n', fs);
    }
    fclose(fs);
    /* our forces, per lane, each at its own epoch */
    void *t = vnew(&k, n), *r[3], *v[3], *bc = vnew(&k, n), *cram = vnew(&k, n);
    void *rb[3], *gb[3], *gi[3], *ad[3], *as[3], *nu = vnew(&k, n), *sun[3], *moon[3];
    k.vt->from_f64(&k.c, t, in[0], n);
    for (int j = 0; j < 3; j++) {
        r[j] = vnew(&k, n);
        v[j] = vnew(&k, n);
        rb[j] = vnew(&k, n);
        gb[j] = vnew(&k, n);
        gi[j] = vnew(&k, n);
        ad[j] = vnew(&k, n);
        as[j] = vnew(&k, n);
        sun[j] = vnew(&k, n);
        moon[j] = vnew(&k, n);
        k.vt->from_f64(&k.c, r[j], in[1 + j], n);
        k.vt->from_f64(&k.c, v[j], in[4 + j], n);
    }
    k.vt->from_f64(&k.c, bc, in[11], n);
    k.vt->from_f64(&k.c, cram, in[12], n);
    k.vt->rotate(&k.c, rb, (const void *const *)r, t, 0, 0, n);
    k.vt->grav(&k.c, gb, (const void *const *)rb, 2, 20, n);
    k.vt->rotate(&k.c, gi, (const void *const *)gb, t, 0, 1, n);
    k.vt->drag(&k.c, ad, (const void *const *)r, (const void *const *)v, bc, n);
    long *rec[3];
    int *sub[3];
    double *dt[3];
    static const int ser[3] = {M1_SER_MOON, M1_SER_SUN, M1_SER_EMB};
    for (int j = 0; j < 3; j++) {
        rec[j] = (long *)calloc(n, sizeof(long));
        sub[j] = (int *)calloc(n, sizeof(int));
        dt[j] = (double *)calloc(n, sizeof(double));
    }
    for (size_t i = 0; i < n; i++)
        for (int j = 0; j < 3; j++)
            if (m1_de_locate(&DE, ser[j], m.jd_epoch, in[0][i], &rec[j][i], &sub[j][i], &dt[j][i])) m1_die("locate");
    m1_ephq q = {{rec[0], rec[1], rec[2]}, {sub[0], sub[1], sub[2]}, {dt[0], dt[1], dt[2]}};
    k.vt->bodies(&k.c, sun, moon, &q, n);
    k.vt->srp(&k.c, as, nu, (const void *const *)r, (const void *const *)sun, 0, cram, n);
    FILE *f = fopen(argv[6], "w");
    if (!f) m1_die("cannot write %s", argv[6]);
    kind_header(f, &k);
    fprintf(f, "# e6 forces: i grav(3, inertial, degrees 2..20) drag(3) srp(3) nu sun(3, geocentric m); plant %s; "
               "atmosphere one band h0 400000 m rho0 3.725e-12 kg/m^3 H 58515 m\n",
            plant);
    void *cols[13] = {gi[0], gi[1], gi[2], ad[0], ad[1], ad[2], as[0], as[1], as[2], nu, sun[0], sun[1], sun[2]};
    for (size_t i = 0; i < n; i++) {
        fprintf(f, "%lu", (unsigned long)i);
        for (int j = 0; j < 13; j++) phex(f, (const unsigned char *)cols[j] + i * k.vt->esz, k.vt->esz);
        fputc('\n', f);
    }
    ops_footer(f, &k);
    fclose(f);
    kclose(&k);
    return 0;
}

/* ------------------------------------------------------------------- E9 */
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
    if (argc < 6) m1_die("usage: time <kind> <nlanes> <min_seconds> <out>");
    size_t n = (size_t)atol(argv[3]);
    double mins = atof(argv[4]);
    m1_model m = model_default(20);
    K k;
    kopen(&k, argv[2], &m, n, has_opt(argc, argv, "--cr"), 0, 0, 0);
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
    FILE *f = fopen(argv[5], "w");
    if (!f) m1_die("cannot write %s", argv[5]);
    kind_header(f, &k);
    /* 1: force evaluations (the whole model, degree 20, 28-band drag, Sun, Moon, SRP), repeated */
    long ne = 0;
    double t0 = now_s(), t1;
    uint64_t c0 = my_cycles();
    do {
        k.vt->accel(&k.c, a, 60.0 * (double)(ne % 1000), (const void *const *)y, bc, cram, n);
        ne++;
        t1 = now_s();
    } while (t1 - t0 < mins || ne < 2);
    uint64_t c1 = my_cycles();
    fprintf(f, "accel lanes %lu evals %ld wall_s %.6f per_lane_eval_us %.3f thread_cycles %llu per_lane_eval_cycles %.0f\n",
            (unsigned long)n, ne, t1 - t0, (t1 - t0) / ((double)ne * n) * 1e6, (unsigned long long)(c1 - c0),
            (double)(c1 - c0) / ((double)ne * n));
    /* 2: rk4 steps at 15 s */
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
    if (argc < 2) m1_die("usage: m1run <mode> ...");
    load_inputs();
    const char *mode = argv[1];
    if (!strcmp(mode, "tables")) return mode_tables(argc, argv);
    if (!strcmp(mode, "e1")) return mode_e1(argc, argv);
    if (!strcmp(mode, "traj")) return mode_traj(argc, argv);
    if (!strcmp(mode, "lasser")) return mode_lasser(argc, argv);
    if (!strcmp(mode, "lasser3")) return mode_lasser3(argc, argv);
    if (!strcmp(mode, "testpo")) return mode_testpo(argc, argv);
    if (!strcmp(mode, "e6")) return mode_e6(argc, argv);
    if (!strcmp(mode, "time")) return mode_time(argc, argv);
    m1_die("no mode %s", mode);
    return 2;
}
