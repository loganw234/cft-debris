/* m1i.c - cft-debris M1 (DEBRIS-I): M1's side of the program's gates - its kernels at given inputs (I2), its
 * trajectories with the switches set to the program's forces or to its full model (I0, I3), the frame at given times
 * (the frame's fit), and a timed batch run (I5).
 *
 * cft-debris, MIT licence (see LICENSE at the repository root). Written by DEBRIS-I, 2026-11-23, from DEBRIS-E's
 * tests/m1run.c (its kernels' calls and hex output), DEBRIS-F's tests/m1f.c (the frame mode), DEBRIS-G's tests/m1g.c
 * (its SHA-256, its clocks and its READY / G / TIMED_DONE / Q protocol) and DEBRIS-H's tests/m1h.c (the seed's
 * format), all cft-debris's own, MIT. src/ is linked as it is.
 *
 *   m1i frames <kind> --table T --times FILE --out FILE
 *   m1i kern   <part> <kind> --table T --in FILE --out FILE [--nmax N] [--om X Y Z]
 *              parts: central (x y z), grav (rb: 3), tides (x y z sx sy sz mx my mz), bodies (t), frame (t),
 *              drag (x y z vx vy vz bc; Omega from --om, three binary64 hex)
 *   m1i traj   <kind> --table T --seed FILE:SHA256 --idx LIST --nsteps S --every K --out FILE
 *              [--model prog|full] [--nmax N] [--srp 0|1] [--bands 28|1] [--cr] [--plant-x INDEX]
 *   m1i rate   <kind> --table T --seed FILE:SHA256 --first F --count N --lanes L --steps S --out DIR --tag TAG
 *              [--nmax N] [--cr]
 * Times are TDB seconds from jd_epoch 2461329.5. Every input real is the hexadecimal of a binary64 encoding (16 digits,
 * most significant first), or a C99 hex float where so named; every output is the hexadecimal of its encoding in the
 * kind (most significant byte first). The seed's lines are "idx cat flags T_s x y z vx vy vz bc cram": the catalogue
 * number is read past and never kept or printed.
 * The models: prog is the program's forces - central, degrees 2..N (default 7), the Sun, the Moon, drag through the
 * 28 bands (or one, --bands 1, with M1's band of 400 km's values), the IERS frame from the table, no radiation pressure;
 * full is M1's full model - degree 20 and radiation pressure besides. --nmax, --srp and --bands change one switch.
 * Each run is rk4 at 15 s from the seed's T_s (the model's t0), t = t0 + j h on the host.
 */
#ifdef __linux__
#define _GNU_SOURCE
#endif
#define __USE_MINGW_ANSI_STDIO 1
#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "m1.h"
#ifdef _WIN32
#include <fcntl.h>
#include <io.h>
#include <windows.h>
#else
#include <sched.h>
#include <time.h>
#include <unistd.h>
#endif

#define JD_EPOCH 2461329.5
#define PASS_STEPS 5760L
static char DL[768] = "";
static m1_gfc G;
static m1_de DE;
static m1_ftab FT;

/* ------------------------------------------------------------------ SHA-256 (m1g.c's) */
typedef struct {
    uint32_t h[8];
    uint64_t len;
    unsigned char buf[64];
    size_t nb;
} Sha;
static const uint32_t SK[64] = {
    0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5, 0xd807aa98, 0x12835b01,
    0x243185be, 0x550c7dc3, 0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174, 0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc,
    0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da, 0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7, 0xc6e00bf3, 0xd5a79147,
    0x06ca6351, 0x14292967, 0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13, 0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85,
    0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3, 0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070, 0x19a4c116, 0x1e376c08,
    0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3, 0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208,
    0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2};
#define ROR(x, n) (((x) >> (n)) | ((x) << (32 - (n))))
static void sha_block(Sha *s, const unsigned char *p)
{
    uint32_t w[64], a, b, c, d, e, f, g, h;
    for (int i = 0; i < 16; i++)
        w[i] = ((uint32_t)p[4 * i] << 24) | ((uint32_t)p[4 * i + 1] << 16) | ((uint32_t)p[4 * i + 2] << 8) | p[4 * i + 3];
    for (int i = 16; i < 64; i++) {
        uint32_t s0 = ROR(w[i - 15], 7) ^ ROR(w[i - 15], 18) ^ (w[i - 15] >> 3);
        uint32_t s1 = ROR(w[i - 2], 17) ^ ROR(w[i - 2], 19) ^ (w[i - 2] >> 10);
        w[i] = w[i - 16] + s0 + w[i - 7] + s1;
    }
    a = s->h[0]; b = s->h[1]; c = s->h[2]; d = s->h[3]; e = s->h[4]; f = s->h[5]; g = s->h[6]; h = s->h[7];
    for (int i = 0; i < 64; i++) {
        uint32_t S1 = ROR(e, 6) ^ ROR(e, 11) ^ ROR(e, 25), ch = (e & f) ^ (~e & g);
        uint32_t t1 = h + S1 + ch + SK[i] + w[i];
        uint32_t S0 = ROR(a, 2) ^ ROR(a, 13) ^ ROR(a, 22), mj = (a & b) ^ (a & c) ^ (b & c);
        uint32_t t2 = S0 + mj;
        h = g; g = f; f = e; e = d + t1; d = c; c = b; b = a; a = t1 + t2;
    }
    s->h[0] += a; s->h[1] += b; s->h[2] += c; s->h[3] += d; s->h[4] += e; s->h[5] += f; s->h[6] += g; s->h[7] += h;
}
static void sha_init(Sha *s)
{
    static const uint32_t iv[8] = {0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a, 0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19};
    memcpy(s->h, iv, sizeof iv);
    s->len = 0;
    s->nb = 0;
}
static void sha_add(Sha *s, const void *data, size_t n)
{
    const unsigned char *p = (const unsigned char *)data;
    s->len += n;
    while (n) {
        size_t k = 64 - s->nb < n ? 64 - s->nb : n;
        memcpy(s->buf + s->nb, p, k);
        s->nb += k; p += k; n -= k;
        if (s->nb == 64) { sha_block(s, s->buf); s->nb = 0; }
    }
}
static void sha_end(Sha *s, char out[65])
{
    uint64_t bits = s->len * 8;
    unsigned char pad = 0x80, z = 0, lb[8];
    sha_add(s, &pad, 1);
    while (s->nb != 56) sha_add(s, &z, 1);
    for (int i = 0; i < 8; i++) lb[i] = (unsigned char)(bits >> (56 - 8 * i));
    sha_add(s, lb, 8);
    for (int i = 0; i < 8; i++) snprintf(out + 8 * i, 9, "%08x", s->h[i]);
}
static void sha_file(const char *path, char out[65])
{
    FILE *f = fopen(path, "rb");
    if (!f) m1_die("cannot read %s", path);
    Sha s;
    sha_init(&s);
    unsigned char buf[1 << 15];
    size_t n;
    while ((n = fread(buf, 1, sizeof buf, f)) > 0) sha_add(&s, buf, n);
    fclose(f);
    sha_end(&s, out);
}

/* ------------------------------------------------------------------ clocks (m1g.c's) */
static int64_t now_ns(void)
{
#ifdef _WIN32
    LARGE_INTEGER c, f;
    QueryPerformanceCounter(&c);
    QueryPerformanceFrequency(&f);
    int64_t sec = c.QuadPart / f.QuadPart, rem = c.QuadPart % f.QuadPart;
    return sec * 1000000000LL + rem * 1000000000LL / f.QuadPart;
#else
    struct timespec t;
    if (clock_gettime(CLOCK_MONOTONIC, &t)) abort();
    return (int64_t)t.tv_sec * 1000000000LL + t.tv_nsec;
#endif
}
static int64_t cpu_ns(void)
{
#ifdef _WIN32
    ULONG64 c = 0;
    QueryProcessCycleTime(GetCurrentProcess(), &c);
    return (int64_t)((double)c / 2.5);
#else
    struct timespec t;
    if (clock_gettime(CLOCK_PROCESS_CPUTIME_ID, &t)) abort();
    return (int64_t)t.tv_sec * 1000000000LL + t.tv_nsec;
#endif
}
static int which_cpu(void)
{
#ifdef __linux__
    return sched_getcpu();
#else
    return -1;
#endif
}
static void affinity_str(char *b, size_t n)
{
#ifdef __linux__
    cpu_set_t s;
    size_t o = 0;
    b[0] = 0;
    if (sched_getaffinity(0, sizeof s, &s)) { snprintf(b, n, "error"); return; }
    for (int i = 0; i < CPU_SETSIZE; i++)
        if (CPU_ISSET(i, &s)) o += (size_t)snprintf(b + o, n - o, "%s%d", o ? "," : "", i);
#else
    snprintf(b, n, "NA");
#endif
}
static int read_byte(int *eof)
{
    unsigned char b = 0;
#ifdef _WIN32
    int r = _read(0, &b, 1);
#else
    ssize_t r = read(0, &b, 1);
#endif
    *eof = (r != 1);
    return r == 1 ? (int)b : -1;
}

/* ------------------------------------------------------------------ options, hex */
static const char *opt(int argc, char **argv, const char *o, const char *def)
{
    for (int i = 1; i + 1 < argc; i++)
        if (!strcmp(argv[i], o)) return argv[i + 1];
    return def;
}
static const char *need(int argc, char **argv, const char *o)
{
    const char *v = opt(argc, argv, o, NULL);
    if (!v) m1_die("%s is required", o);
    return v;
}
static int has(int argc, char **argv, const char *o)
{
    for (int i = 1; i < argc; i++)
        if (!strcmp(argv[i], o)) return 1;
    return 0;
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
/* 16 hex digits, most significant first, as a binary64 */
static double hex64(const char *s)
{
    uint64_t u = 0;
    if (strlen(s) < 16) m1_die("hex \"%s\" is not 16 digits", s);
    for (int i = 0; i < 16; i++) {
        int v = hexval(s[i]);
        if (v < 0) m1_die("hex \"%s\"", s);
        u = (u << 4) | (uint64_t)v;
    }
    double d;
    memcpy(&d, &u, 8);
    return d;
}

/* ------------------------------------------------------------------ inputs and the model */
static void load_inputs(const char *table)
{
    const char *e = getenv("M1_DOWNLOADS");
    if (!e || !*e) m1_die("M1_DOWNLOADS must name the downloads folder (gfc, DE421 and its header), ending in /");
    snprintf(DL, sizeof DL, "%s", e);
    char a[1024], b[1024];
    snprintf(a, sizeof a, "%sEIGEN6-C4.gfc/EIGEN6-C4.gfc", DL);
    if (m1_gfc_load(&G, a, M1_NMAX)) m1_die("gfc: %s", G.err);
    snprintf(a, sizeof a, "%slnxp1900p2053.421/lnxp1900p2053.421", DL);
    snprintf(b, sizeof b, "%sheader.421/header.421", DL);
    if (m1_de_open(&DE, a, b)) m1_die("de421: %s", DE.err);
    if (table && strcmp(table, "-") && m1_ftab_load(&FT, table)) m1_die("frame table: %s", FT.err);
}
/* the one band, if asked: M1's band of 400 km (index 20 of src/m1_consts.h's table), as decimal strings */
static const char *B1_H0 = "400000", *B1_RHO = "3.725e-12", *B1_HS = "58515";
static m1_model model_of(int argc, char **argv, double t0)
{
    m1_model m;
    memset(&m, 0, sizeof m);
    const char *md = opt(argc, argv, "--model", "prog");
    int full = !strcmp(md, "full");
    if (!full && strcmp(md, "prog")) m1_die("--model is prog or full");
    m.central = 1;
    m.nmin = 2;
    m.nmax = atoi(opt(argc, argv, "--nmax", full ? "20" : "7"));
    m.sun = m.moon = m.drag = 1;
    m.srp = atoi(opt(argc, argv, "--srp", full ? "1" : "0"));
    m.nbands = atoi(opt(argc, argv, "--bands", "28"));
    if (m.nbands == 1) {
        m.band_h0 = B1_H0;
        m.band_rho0 = B1_RHO;
        m.band_hs = B1_HS;
    }
    m.jd_epoch = JD_EPOCH;
    m.frame = 1;
    m.ftab = &FT;
    m.t0 = t0;
    return m;
}
static void model_line(FILE *f, const m1_model *m)
{
    fprintf(f, "# model central %d nmin %d nmax %d sun %d moon %d drag %d srp %d nbands %d frame %d jd_epoch %.1f t0 %a\n",
            m->central, m->nmin, m->nmax, m->sun, m->moon, m->drag, m->srp, m->nbands, m->frame, m->jd_epoch, m->t0);
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
    fprintf(f, "# m1i kind %s esz %lu native %d cr_transc %d build_id %s table %s sha256 %s\n", k->vt->name,
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

/* ------------------------------------------------------------------ frames */
static int mode_frames(int argc, char **argv)
{
    if (argc < 3) m1_die("usage: frames <kind> --table T --times FILE --out FILE");
    load_inputs(need(argc, argv, "--table"));
    m1_model m = model_of(argc, argv, 0.0);
    K k;
    kopen(&k, argv[2], &m, 1, 0);
    FILE *fi = fopen(need(argc, argv, "--times"), "rb");
    if (!fi) m1_die("cannot read the times");
    FILE *f = fopen(need(argc, argv, "--out"), "wb");
    if (!f) m1_die("cannot write the output");
    kind_header(f, &k);
    fprintf(f, "# frames: t (C99 hex float), then M (9, row-major, GCRS <- ITRS) and Omega (3), the kind's encodings\n");
    char line[256];
    void *m12 = vnew(&k, 12);
    long n = 0;
    while (fgets(line, sizeof line, fi)) {
        if (line[0] == '#' || line[0] == '\n' || line[0] == '\r') continue;
        char *e;
        double t = strtod(line, &e);
        if (e == line) m1_die("bad time line %ld", n);
        k.vt->frame_at(&k.c, m12, t);
        fprintf(f, "%a", t);
        for (int j = 0; j < 12; j++) phex(f, (const unsigned char *)m12 + (size_t)j * k.vt->esz, k.vt->esz);
        fputc('\n', f);
        n++;
    }
    fclose(fi);
    ops_footer(f, &k);
    fclose(f);
    kclose(&k);
    fprintf(stderr, "m1i frames: %ld times\n", n);
    return 0;
}

/* ------------------------------------------------------------------ kernels at given inputs */
static int mode_kern(int argc, char **argv)
{
    if (argc < 4) m1_die("usage: kern <part> <kind> --table T --in FILE --out FILE [--nmax N] [--om X Y Z]");
    const char *part = argv[2];
    load_inputs(need(argc, argv, "--table")); /* the model has frame = 1, so every kind needs the table */
    int nin = 0;
    if (!strcmp(part, "central") || !strcmp(part, "grav")) nin = 3;
    else if (!strcmp(part, "tides")) nin = 9;
    else if (!strcmp(part, "bodies") || !strcmp(part, "frame")) nin = 1;
    else if (!strcmp(part, "drag")) nin = 7;
    else m1_die("no part %s", part);
    /* read the inputs: "idx h h h ..." */
    FILE *fi = fopen(need(argc, argv, "--in"), "rb");
    if (!fi) m1_die("cannot read the inputs");
    size_t cap = 1024, n = 0;
    double *in = (double *)malloc(cap * (size_t)nin * sizeof(double));
    char *line = (char *)malloc(1 << 16);
    while (fgets(line, 1 << 16, fi)) {
        if (line[0] == '#' || line[0] == '\n' || line[0] == '\r') continue;
        if (n == cap) { cap *= 2; in = (double *)realloc(in, cap * (size_t)nin * sizeof(double)); }
        char *p = line, *e;
        long idx = strtol(p, &e, 10);
        if (e == p || idx != (long)n) m1_die("input line %lu has index %ld", (unsigned long)n, idx);
        p = e;
        for (int j = 0; j < nin; j++) {
            while (*p == ' ') p++;
            in[n * (size_t)nin + (size_t)j] = hex64(p);
            p += 16;
        }
        n++;
    }
    fclose(fi);
    free(line);
    m1_model m = model_of(argc, argv, 0.0);
    K k;
    kopen(&k, argv[3], &m, n, 0);
    const size_t es = k.vt->esz;
    /* the inputs in the kind, component-major */
    void *v[9];
    double *tmp = (double *)malloc(n * sizeof(double));
    for (int j = 0; j < nin; j++) {
        v[j] = vnew(&k, n);
        for (size_t i = 0; i < n; i++) tmp[i] = in[i * (size_t)nin + (size_t)j];
        k.vt->from_f64(&k.c, v[j], tmp, n);
    }
    FILE *f = fopen(need(argc, argv, "--out"), "wb");
    if (!f) m1_die("cannot write the output");
    kind_header(f, &k);
    model_line(f, &m);
    fprintf(f, "# kern %s lanes %lu\n", part, (unsigned long)n);
    int nout = 0;
    void *out[12];
    if (!strcmp(part, "central") || !strcmp(part, "grav")) {
        for (int j = 0; j < 3; j++) out[j] = vnew(&k, n);
        nout = 3;
        if (!strcmp(part, "grav")) k.vt->grav(&k.c, out, (const void *const *)v, 2, m.nmax, n);
        else k.vt->central(&k.c, out, (const void *const *)v, n);
    } else if (!strcmp(part, "tides")) {
        for (int j = 0; j < 6; j++) out[j] = vnew(&k, n);
        nout = 6;
        k.vt->third(&k.c, out, (const void *const *)v, (const void *const *)(v + 3), 0, 0, n);
        k.vt->third(&k.c, out + 3, (const void *const *)v, (const void *const *)(v + 6), 0, 1, n);
    } else if (!strcmp(part, "bodies")) {
        /* each lane's time: M1's own choice of record and sub-interval (m1_de_locate) */
        long *rec[3];
        int *sub[3];
        double *dt[3];
        static const int ser[3] = {M1_SER_MOON, M1_SER_SUN, M1_SER_EMB};
        for (int j = 0; j < 3; j++) {
            rec[j] = (long *)calloc(n, sizeof(long));
            sub[j] = (int *)calloc(n, sizeof(int));
            dt[j] = (double *)calloc(n, sizeof(double));
            for (size_t i = 0; i < n; i++)
                if (m1_de_locate(&DE, ser[j], JD_EPOCH, in[i], &rec[j][i], &sub[j][i], &dt[j][i])) m1_die("locate");
        }
        for (int j = 0; j < 6; j++) out[j] = vnew(&k, n);
        nout = 6;
        m1_ephq q = {{rec[0], rec[1], rec[2]}, {sub[0], sub[1], sub[2]}, {dt[0], dt[1], dt[2]}};
        k.vt->bodies(&k.c, out, out + 3, &q, n);
        for (size_t i = 0; i < n; i++)
            fprintf(f, "# locate %lu %ld %d %ld %d %ld %d\n", (unsigned long)i, rec[0][i], sub[0][i], rec[1][i], sub[1][i],
                    rec[2][i], sub[2][i]);
    } else if (!strcmp(part, "frame")) {
        for (int j = 0; j < 12; j++) out[j] = vnew(&k, n);
        nout = 12;
        void *m12 = vnew(&k, 12);
        for (size_t i = 0; i < n; i++) {
            k.vt->frame_at(&k.c, m12, in[i]);
            for (int j = 0; j < 12; j++) memcpy((unsigned char *)out[j] + i * es, (unsigned char *)m12 + (size_t)j * es, es);
        }
    } else { /* drag */
        double om[3];
        for (int j = 0; j < 3; j++) {
            const char *s = NULL;
            for (int a = 1; a + 3 < argc; a++)
                if (!strcmp(argv[a], "--om")) s = argv[a + 1 + j];
            if (!s) m1_die("drag needs --om X Y Z");
            om[j] = hex64(s);
        }
        void *omk = vnew(&k, 3);
        k.vt->from_f64(&k.c, omk, om, 3);
        for (int j = 0; j < 3; j++) out[j] = vnew(&k, n);
        nout = 3;
        k.vt->drag_om(&k.c, out, (const void *const *)v, (const void *const *)(v + 3), v[6], omk, n);
    }
    for (size_t i = 0; i < n; i++) {
        fprintf(f, "%lu", (unsigned long)i);
        for (int j = 0; j < nout; j++) phex(f, (const unsigned char *)out[j] + i * es, es);
        fputc('\n', f);
    }
    ops_footer(f, &k);
    fclose(f);
    kclose(&k);
    free(tmp);
    free(in);
    return 0;
}

/* ------------------------------------------------------------------ the seed */
typedef struct {
    long idx;
    double v[9]; /* T_s x y z vx vy vz bc cram */
} Seed;
static Seed *read_seed(const char *arg, long *np, char sha_vals[65])
{
    char path[1024];
    const char *c = strrchr(arg, ':');
    if (!c || strlen(c + 1) != 64) m1_die("%s is not FILE:SHA256", arg);
    size_t pl = (size_t)(c - arg);
    if (pl >= sizeof path) m1_die("path too long");
    memcpy(path, arg, pl);
    path[pl] = 0;
    char got[65];
    sha_file(path, got);
    if (strcmp(got, c + 1)) m1_die("refused: %s has SHA-256 %s, not %s", path, got, c + 1);
    FILE *f = fopen(path, "rb");
    if (!f) m1_die("cannot read %s", path);
    long cap = 4096, n = 0;
    Seed *S = (Seed *)malloc((size_t)cap * sizeof(Seed));
    char *line = (char *)malloc(1 << 16);
    Sha sh;
    sha_init(&sh);
    while (fgets(line, 1 << 16, f)) {
        if (line[0] == '#' || line[0] == '\n' || line[0] == '\r') continue;
        if (n == cap) { cap *= 2; S = (Seed *)realloc(S, (size_t)cap * sizeof(Seed)); }
        char *p = line, *e;
        S[n].idx = strtol(p, &e, 10);
        if (e == p || S[n].idx != n) m1_die("seed line %ld has index %ld", n, S[n].idx);
        p = e;
        (void)strtol(p, &e, 10); /* the catalogue number: never kept or printed */
        p = e;
        (void)strtol(p, &e, 10); /* flags */
        p = e;
        for (int j = 0; j < 9; j++) {
            S[n].v[j] = strtod(p, &e);
            if (e == p) m1_die("bad seed line %ld", n);
            p = e;
            sha_add(&sh, &S[n].v[j], 8);
        }
        if (S[n].v[0] != S[0].v[0]) m1_die("seed line %ld: a second T_s", n);
        n++;
    }
    fclose(f);
    free(line);
    sha_end(&sh, sha_vals);
    *np = n;
    return S;
}
static long *parse_list(const char *s, long *nout)
{
    long cap = 64, n = 0;
    long *L = (long *)malloc((size_t)cap * sizeof(long));
    const char *p = s;
    while (*p) {
        char *e;
        long a = strtol(p, &e, 10);
        if (e == p) m1_die("bad list %s", s);
        long b = a;
        if (*e == '-') { p = e + 1; b = strtol(p, &e, 10); }
        for (long x = a; x <= b; x++) {
            if (n == cap) { cap *= 2; L = (long *)realloc(L, (size_t)cap * sizeof(long)); }
            L[n++] = x;
        }
        p = e;
        if (*p == ',') p++;
    }
    *nout = n;
    return L;
}

/* ------------------------------------------------------------------ trajectories */
typedef struct {
    FILE *f;
    long every;
    const K *k;
    const long *idx;
} TrajU;
static void traj_cb(void *u, long step, double t, void *const y[6], size_t n)
{
    TrajU *U = (TrajU *)u;
    if (step % U->every) return;
    for (size_t l = 0; l < n; l++) {
        fprintf(U->f, "S %ld %ld %a", U->idx[l], step, t);
        for (int i = 0; i < 6; i++) phex(U->f, (const unsigned char *)y[i] + l * U->k->vt->esz, U->k->vt->esz);
        fputc('\n', U->f);
    }
}
static int mode_traj(int argc, char **argv)
{
    if (argc < 3) m1_die("usage: traj <kind> --table T --seed FILE:SHA256 --idx LIST --nsteps S --every K --out FILE ...");
    load_inputs(need(argc, argv, "--table"));
    long ns;
    char sha_vals[65];
    Seed *S = read_seed(need(argc, argv, "--seed"), &ns, sha_vals);
    long n;
    long *idx = parse_list(need(argc, argv, "--idx"), &n);
    for (long i = 0; i < n; i++)
        if (idx[i] < 0 || idx[i] >= ns) m1_die("index %ld outside the seed's %ld", idx[i], ns);
    const long nsteps = atol(need(argc, argv, "--nsteps")), every = atol(need(argc, argv, "--every"));
    const long plant = atol(opt(argc, argv, "--plant-x", "-1"));
    if (nsteps < 1 || every < 1) m1_die("--nsteps and --every must be positive");
    const double t0 = S[0].v[0];
    m1_model m = model_of(argc, argv, t0);
    K k;
    kopen(&k, argv[2], &m, (size_t)n, has(argc, argv, "--cr"));
    const size_t es = k.vt->esz;
    void *y[6], *bc = vnew(&k, (size_t)n), *cram = vnew(&k, (size_t)n);
    double *tmp = (double *)malloc((size_t)n * sizeof(double));
    for (int i = 0; i < 6; i++) {
        y[i] = vnew(&k, (size_t)n);
        for (long l = 0; l < n; l++) {
            double v = S[idx[l]].v[1 + i];
            if (i == 0 && idx[l] == plant) v = nextafter(v, INFINITY); /* C2's control: one binary64 ulp up */
            tmp[l] = v;
        }
        k.vt->from_f64(&k.c, y[i], tmp, (size_t)n);
    }
    for (long l = 0; l < n; l++) tmp[l] = S[idx[l]].v[7];
    k.vt->from_f64(&k.c, bc, tmp, (size_t)n);
    for (long l = 0; l < n; l++) tmp[l] = S[idx[l]].v[8];
    k.vt->from_f64(&k.c, cram, tmp, (size_t)n);
    FILE *f = fopen(need(argc, argv, "--out"), "wb");
    if (!f) m1_die("cannot write the output");
    kind_header(f, &k);
    model_line(f, &m);
    fprintf(f, "# traj objects %ld nsteps %ld every %ld seed_values_sha256 %s plant_x %ld\n", n, nsteps, every, sha_vals, plant);
    fprintf(f, "# lines: S idx step t(host, C99 hex) x y z vx vy vz (the kind's encodings)\n");
    TrajU U = {f, every, &k, idx};
    traj_cb(&U, 0, t0, y, (size_t)n);
    k.vt->rk4(&k.c, y, bc, cram, "15", 0, nsteps, traj_cb, &U, (size_t)n);
    ops_footer(f, &k);
    fclose(f);
    kclose(&k);
    (void)es;
    return 0;
}

/* ------------------------------------------------------------------ a timed batch run (I5), m1g.c's protocol */
static int mode_rate(int argc, char **argv)
{
    if (argc < 3) m1_die("usage: rate <kind> --table T --seed FILE:SHA256 --first F --count N --lanes L --steps S --out D --tag T");
#ifdef _WIN32
    _setmode(0, _O_BINARY);
    _setmode(1, _O_BINARY);
#endif
    load_inputs(need(argc, argv, "--table"));
    long ns;
    char sha_vals[65];
    Seed *S = read_seed(need(argc, argv, "--seed"), &ns, sha_vals);
    const long first = atol(need(argc, argv, "--first")), count = atol(need(argc, argv, "--count")),
               lanes = atol(need(argc, argv, "--lanes")), steps = atol(need(argc, argv, "--steps"));
    const char *outd = need(argc, argv, "--out"), *tag = need(argc, argv, "--tag");
    if (count < 1 || lanes < 1 || steps < 1 || first < 0 || first + count > ns) m1_die("bad slice or steps");
    const double t0 = S[0].v[0];
    m1_model m = model_of(argc, argv, t0);
    K k;
    kopen(&k, argv[2], &m, (size_t)lanes, has(argc, argv, "--cr"));
    const size_t es = k.vt->esz;
    long nb = (count + lanes - 1) / lanes;
    typedef struct { size_t n; void *y[6], *yi[6], *bc, *cram; } Bt;
    Bt *B = (Bt *)calloc((size_t)nb, sizeof(Bt));
    double *tmp = (double *)malloc((size_t)lanes * sizeof(double));
    for (long b = 0; b < nb; b++) {
        Bt *bt = &B[b];
        long f0 = first + b * lanes;
        bt->n = (size_t)(count - b * lanes < lanes ? count - b * lanes : lanes);
        bt->bc = vnew(&k, bt->n);
        bt->cram = vnew(&k, bt->n);
        for (int i = 0; i < 6; i++) {
            bt->y[i] = vnew(&k, bt->n);
            bt->yi[i] = vnew(&k, bt->n);
            for (size_t l = 0; l < bt->n; l++) tmp[l] = S[f0 + (long)l].v[1 + i];
            k.vt->from_f64(&k.c, bt->y[i], tmp, bt->n);
            memcpy(bt->yi[i], bt->y[i], bt->n * es);
        }
        for (size_t l = 0; l < bt->n; l++) tmp[l] = S[f0 + (long)l].v[7];
        k.vt->from_f64(&k.c, bt->bc, tmp, bt->n);
        for (size_t l = 0; l < bt->n; l++) tmp[l] = S[f0 + (long)l].v[8];
        k.vt->from_f64(&k.c, bt->cram, tmp, bt->n);
    }
    const long npass = (steps + PASS_STEPS - 1) / PASS_STEPS;
    char affin_ready[256], affin_start[256], affin_end[256];
    affinity_str(affin_ready, sizeof affin_ready);
    printf("INFO m1i rate kind %s nobj %ld lanes %ld batches %ld steps %ld passes %ld\n", k.vt->name, count, lanes, nb, steps, npass);
    printf("READY\n");
    fflush(stdout);
    const int64_t c_ready = cpu_ns();
    int eof = 0;
    int bch = read_byte(&eof);
    const int64_t t_start = now_ns(), c_start = cpu_ns();
    const int cpu_start = which_cpu();
    affinity_str(affin_start, sizeof affin_start);
    if (eof || bch != 'G') m1_die("the release byte was %d, not 'G'", bch);
    long done = 0;
    for (long ps = 0; ps < npass; ps++) {
        const long nst = (ps == npass - 1) ? steps - ps * PASS_STEPS : PASS_STEPS;
        if (ps > 0)
            for (long b = 0; b < nb; b++)
                for (int i = 0; i < 6; i++) memcpy(B[b].y[i], B[b].yi[i], B[b].n * es);
        for (long st = 0; st < nst; st++) {
            for (long b = 0; b < nb; b++) k.vt->rk4(&k.c, B[b].y, B[b].bc, B[b].cram, "15", st, 1, NULL, NULL, B[b].n);
            done++;
        }
    }
    const int64_t t_end = now_ns(), c_end = cpu_ns();
    const int cpu_end = which_cpu();
    affinity_str(affin_end, sizeof affin_end);
    printf("TIMED_DONE\n");
    fflush(stdout);
    int eof2 = 0;
    (void)read_byte(&eof2);
    char path[1024], sha_final[65];
    snprintf(path, sizeof path, "%s/%s.obj.txt", outd, tag);
    FILE *fo = fopen(path, "wb");
    if (!fo) m1_die("cannot write %s", path);
    fprintf(fo, "# m1i rate final states: seed index, the six components in the kind's bytes (hex); kind %s steps %ld\n",
            k.vt->name, steps);
    Sha sh;
    sha_init(&sh);
    for (long b = 0; b < nb; b++)
        for (size_t l = 0; l < B[b].n; l++) {
            fprintf(fo, "%ld", first + b * lanes + (long)l);
            for (int i = 0; i < 6; i++) {
                const unsigned char *p = (const unsigned char *)B[b].y[i] + l * es;
                phex(fo, p, es);
                sha_add(&sh, p, es);
            }
            fputc('\n', fo);
        }
    fclose(fo);
    sha_end(&sh, sha_final);
    printf("REPORT kind %s\nREPORT cr %d\nREPORT build_id %s\nREPORT frame_table_sha256 %s\n", k.vt->name, k.c.cr_transc,
           cft_build_id(), FT.sha256);
    printf("REPORT model nmax %d srp %d nbands %d\n", m.nmax, m.srp, m.nbands);
    printf("REPORT seed_values_sha256 %s\n", sha_vals);
    printf("REPORT nobj %ld\nREPORT lanes %ld\nREPORT batches %ld\nREPORT steps %ld\nREPORT passes %ld\nREPORT steps_done %ld\n",
           count, lanes, nb, steps, npass, done);
    printf("REPORT objsec %.1f\n", (double)count * 15.0 * (double)done);
    printf("REPORT t_start_ns %lld\nREPORT t_end_ns %lld\n", (long long)t_start, (long long)t_end);
    printf("REPORT cpu_ready_ns %lld\nREPORT cpu_start_ns %lld\nREPORT cpu_end_ns %lld\n", (long long)c_ready,
           (long long)c_start, (long long)c_end);
    printf("REPORT cpu_at_start %d\nREPORT cpu_at_end %d\n", cpu_start, cpu_end);
    printf("REPORT affinity_ready %s\nREPORT affinity_start %s\nREPORT affinity_end %s\n", affin_ready, affin_start, affin_end);
    printf("REPORT final_states_sha256 %s\n", sha_final);
    printf("REPORT cft_flags 0x%x\n", (unsigned)k.c.cft_flags);
    printf("DONE\n");
    fflush(stdout);
    free(tmp);
    kclose(&k);
    return 0;
}

int main(int argc, char **argv)
{
    if (argc < 2) m1_die("usage: m1i frames|kern|traj|rate ...");
    if (!strcmp(argv[1], "frames")) return mode_frames(argc, argv);
    if (!strcmp(argv[1], "kern")) return mode_kern(argc, argv);
    if (!strcmp(argv[1], "traj")) return mode_traj(argc, argv);
    if (!strcmp(argv[1], "rate")) return mode_rate(argc, argv);
    m1_die("no mode %s", argv[1]);
    return 2;
}
