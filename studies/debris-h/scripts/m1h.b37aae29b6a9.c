/* m1h.c - cft-debris M1 (DEBRIS-H): the service's driver - a live worker that steps at the wall clock, with
 * checkpoints, pauses and restarts (mode run), and re-propagation from a checkpoint (mode seg).
 *
 * cft-debris, MIT licence (see LICENSE at the repository root). Written by DEBRIS-H, 2026-11-18, from DEBRIS-G's
 * tests/m1g.c (its SHA-256, its clocks, the model and the kind's set-up, and its step-major loop over batches of
 * lanes) and DEBRIS-F's tests/m1f.c (hex in and out, and the prediction's rule: whole steps, then one short step
 * landing on the target), both cft-debris's own, MIT. src/ is used as it is.
 *
 *   m1h run --kind K --table T --track NAME --run DIR --first F --count N --lanes L --k0 K0 --kend KE
 *           --unix-ref U --t-ref TR --allow A --ckpt-every C --worker I --nworkers W
 *           (--seed FILE:SHA256 | --init FILE:SHA256 [--init FILE:SHA256 ...]) [--pause NAME ...] [--cr]
 *   m1h seg --kind K --table T (--seed FILE:SHA256 | --init FILE:SHA256 ...) --targets FILE --out FILE [--lanes L] [--cr]
 *
 * TIME. M1's host time is TDB seconds from jd_epoch 2461329.5. A run's origin ts (the seed's T_s, or the checkpoint's
 * ts) is the model's t0, and step k ends at t_k = ts + 15 k (src/m1_physics.h, ph_rk4: t = t0 + (step0 + j) h, never
 * accumulated, so a run restarted from step k's state with its step index is the same run). The clock map (U, TR):
 * step k is due at the POSIX time U + (t_k - TR). Due times are read on CLOCK_REALTIME, durations on CLOCK_MONOTONIC
 * (on Windows, for tests: GetSystemTimePreciseAsFileTime and QueryPerformanceCounter).
 *
 * RUN. The slice is the objects F .. F+N-1 of the seed's index, cut into batches of L lanes in index order. Before
 * step k: while a pause file (default PAUSE and PAUSE.disk in the run folder) exists, wait, checking every 5 s, and
 * log the pause; if step k is due more than A x 15 s ahead, sleep until its due time less A x 15 s, plus this
 * worker's stagger I x 15 / W s. Then every batch takes one rk4 step (step-major). After step k: log k, its start,
 * finish and due times (POSIX s) and its lag (finish - due); evaluate every live object's state - finite, and its
 * distance from the centre above 6,498.137 km; an object found below is marked decayed from step k and not
 * evaluated again; a non-finite state of a live object stops the worker (exit 4) with its index. At every multiple
 * of C, and at KE: write the checkpoint (each state in the kind's bytes and as binary64, with bc, cram and the
 * decay step) to a temporary name, flushed, then renamed to ckpt/<track>/kKKKKKK.wIIofWW.txt, or, if that exists
 * (a restart), to the first free .rN.txt name: no file is ever overwritten. On SIGTERM: finish the current step,
 * then exit (code 10). A run from a seed writes checkpoint 0 (the seed's states as the kind holds them) first.
 * Every step log is a new file, steps/<track>/wIIofWW.kK0.N.log; nothing is deleted.
 *
 * SEG. For each target line "idx kc E e" (an epoch, a C99 hex float) or "idx kc N n": the object's state at step kc
 * from the given checkpoint files (whose SHA-256 are checked first), then whole steps to the last grid point
 * ts + 15 M at or before e and one short step landing on e, or n whole steps. Its output: "R idx kc mode t decay"
 * then each state in the kind's bytes and as binary64. Targets of mode N that share kc and n run as batches of up
 * to L lanes; mode E runs each object as its own one-lane batch.
 */
#ifdef __linux__
#define _GNU_SOURCE
#endif
#define __USE_MINGW_ANSI_STDIO 1
#include <errno.h>
#include <fcntl.h>
#include <math.h>
#include <signal.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include "m1.h"
#ifdef _WIN32
#include <direct.h>
#include <io.h>
#include <process.h>
#include <windows.h>
#else
#include <time.h>
#include <unistd.h>
#endif

#define JD_EPOCH 2461329.5
#define RMIN 6498137.0 /* 120 km above 6,378.137 km */
#define HSTEP 15.0
static char DL[512] = "";
static m1_gfc G;
static m1_de DE;
static m1_ftab FT;
static volatile sig_atomic_t g_term = 0;

/* ------------------------------------------------------------------ SHA-256 (DEBRIS-G's plain implementation) */
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
    unsigned char buf[65536];
    size_t n;
    while ((n = fread(buf, 1, sizeof buf, f)) > 0) sha_add(&s, buf, n);
    fclose(f);
    sha_end(&s, out);
}

/* ------------------------------------------------------------------ clocks, files */
static double now_rt(void) /* POSIX seconds, CLOCK_REALTIME */
{
#ifdef _WIN32
    FILETIME ft;
    GetSystemTimePreciseAsFileTime(&ft);
    uint64_t v = ((uint64_t)ft.dwHighDateTime << 32) | ft.dwLowDateTime;
    return (double)(v - 116444736000000000ULL) / 1e7;
#else
    struct timespec t;
    if (clock_gettime(CLOCK_REALTIME, &t)) abort();
    return (double)t.tv_sec + (double)t.tv_nsec * 1e-9;
#endif
}
static double now_mono(void)
{
#ifdef _WIN32
    LARGE_INTEGER c, f;
    QueryPerformanceCounter(&c);
    QueryPerformanceFrequency(&f);
    return (double)c.QuadPart / (double)f.QuadPart;
#else
    struct timespec t;
    if (clock_gettime(CLOCK_MONOTONIC, &t)) abort();
    return (double)t.tv_sec + (double)t.tv_nsec * 1e-9;
#endif
}
static void sleep_s(double d)
{
    if (!(d > 0)) return;
#ifdef _WIN32
    Sleep((DWORD)(d * 1000.0));
#else
    struct timespec ts;
    ts.tv_sec = (time_t)d;
    ts.tv_nsec = (long)((d - (double)ts.tv_sec) * 1e9);
    nanosleep(&ts, NULL); /* SIGTERM ends it early */
#endif
}
static int my_pid(void)
{
#ifdef _WIN32
    return (int)_getpid();
#else
    return (int)getpid();
#endif
}
static int exists(const char *p)
{
    struct stat st;
    return stat(p, &st) == 0;
}
static void mkdir_p(const char *path)
{
    char b[1024];
    snprintf(b, sizeof b, "%s", path);
    for (char *p = b + 1; *p; p++) {
        if (*p == '/' || *p == '\\') {
            char c = *p;
            *p = 0;
#ifdef _WIN32
            _mkdir(b);
#else
            mkdir(b, 0755);
#endif
            *p = c;
        }
    }
#ifdef _WIN32
    _mkdir(b);
#else
    mkdir(b, 0755);
#endif
    if (!exists(b)) m1_die("cannot create %s", b);
}
static FILE *open_new(const char *path) /* exclusive creation: NULL if the file exists */
{
#ifdef _WIN32
    int fd = _open(path, _O_WRONLY | _O_CREAT | _O_EXCL | _O_BINARY, _S_IREAD | _S_IWRITE);
    return fd < 0 ? NULL : _fdopen(fd, "wb");
#else
    int fd = open(path, O_WRONLY | O_CREAT | O_EXCL, 0644);
    return fd < 0 ? NULL : fdopen(fd, "wb");
#endif
}
static void flush_sync(FILE *f)
{
    fflush(f);
#ifdef _WIN32
    _commit(_fileno(f));
#else
    fsync(fileno(f));
#endif
}
static int rename_noreplace(const char *from, const char *to) /* 0, or -1 with errno EEXIST if to exists */
{
#ifdef _WIN32
    if (exists(to)) { errno = EEXIST; return -1; }
    return rename(from, to); /* MoveFile semantics: fails if to exists */
#else
    return renameat2(AT_FDCWD, from, AT_FDCWD, to, RENAME_NOREPLACE);
#endif
}

/* ------------------------------------------------------------------ hex, options */
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
static double d_of_hex16(const char *s)
{
    uint64_t u = 0;
    if (strlen(s) != 16) m1_die("binary64 hex \"%s\"", s);
    for (int i = 0; i < 16; i++) {
        int v = hexval(s[i]);
        if (v < 0) m1_die("binary64 hex \"%s\"", s);
        u = (u << 4) | (uint64_t)v;
    }
    double d;
    memcpy(&d, &u, 8);
    return d;
}
static void p64(FILE *f, double d)
{
    uint64_t u;
    memcpy(&u, &d, 8);
    fprintf(f, " %016llx", (unsigned long long)u);
}
static const char *opt(int argc, char **argv, const char *o, const char *def)
{
    for (int i = 2; i + 1 < argc; i++)
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
    for (int i = 2; i < argc; i++)
        if (!strcmp(argv[i], o)) return 1;
    return 0;
}
static int opts(int argc, char **argv, const char *o, const char **out, int cap)
{
    int n = 0;
    for (int i = 2; i + 1 < argc; i++)
        if (!strcmp(argv[i], o)) {
            if (n == cap) m1_die("too many %s", o);
            out[n++] = argv[i + 1];
        }
    return n;
}
static m1_model model_real(double t0)
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
    m.t0 = t0;
    return m;
}
static void load_inputs(const char *table)
{
    const char *e = getenv("M1_DOWNLOADS");
    if (!e || !*e) m1_die("M1_DOWNLOADS must name the downloads folder (gfc, DE421 and its header)");
    snprintf(DL, sizeof DL, "%s", e);
    char a[768], b[768];
    snprintf(a, sizeof a, "%sEIGEN6-C4.gfc/EIGEN6-C4.gfc", DL);
    if (m1_gfc_load(&G, a, M1_NMAX)) m1_die("gfc: %s", G.err);
    snprintf(a, sizeof a, "%slnxp1900p2053.421/lnxp1900p2053.421", DL);
    snprintf(b, sizeof b, "%sheader.421/header.421", DL);
    if (m1_de_open(&DE, a, b)) m1_die("de421: %s", DE.err);
    if (m1_ftab_load(&FT, table)) m1_die("frame table: %s", FT.err);
}
#ifndef _WIN32
static void on_term(int s)
{
    (void)s;
    g_term = 1;
}
#endif

/* ------------------------------------------------------------------ the objects */
typedef struct {
    long idx;
    long decay;           /* the step at which it was found below 6,498.137 km, or -1 */
    double ts, bc, cram;  /* the run's origin, and the object's bc and cram (binary64) */
    long k;               /* the step of the state */
    unsigned char *y;     /* 6 x esz, the kind's bytes */
    int found;
} Obj;

/* a FILE:SHA256 argument: check the file's hash before anything reads it */
static void split_checked(const char *arg, char *path, size_t cap)
{
    const char *c = strrchr(arg, ':');
    if (!c || strlen(c + 1) != 64) m1_die("%s is not FILE:SHA256", arg);
    size_t n = (size_t)(c - arg);
    if (n >= cap) m1_die("path too long");
    memcpy(path, arg, n);
    path[n] = 0;
    char got[65];
    sha_file(path, got);
    if (strcmp(got, c + 1)) m1_die("refused: %s has SHA-256 %s, not %s", path, got, c + 1);
}

/* the seed: "idx cat flags Ts x y z vx vy vz bc cram", every real a C99 hex float; the catalogue number is read past */
static void load_seed(const char *arg, const m1_vt *vt, m1_ctx *c, Obj *O, long first, long count, double *ts_out)
{
    char path[1024];
    split_checked(arg, path, sizeof path);
    FILE *f = fopen(path, "rb");
    if (!f) m1_die("cannot read %s", path);
    char *line = (char *)malloc(1 << 16);
    long n = 0;
    double ts = NAN;
    while (fgets(line, 1 << 16, f)) {
        if (line[0] == '#' || line[0] == '\n' || line[0] == '\r') continue;
        char *p = line, *e;
        long idx = strtol(p, &e, 10);
        if (e == p || idx != n) m1_die("seed line %ld has index %ld", n, idx);
        p = e;
        (void)strtol(p, &e, 10); /* the catalogue number: never kept or printed */
        p = e;
        (void)strtol(p, &e, 10); /* flags */
        p = e;
        double v[9];
        for (int j = 0; j < 9; j++) {
            v[j] = strtod(p, &e);
            if (e == p) m1_die("bad seed line %ld", n);
            p = e;
        }
        if (n == 0) ts = v[0];
        if (v[0] != ts) m1_die("seed line %ld: a second T_s", n);
        if (idx >= first && idx < first + count) {
            Obj *o = &O[idx - first];
            if (o->found) m1_die("seed index %ld twice", idx);
            o->found = 1;
            o->idx = idx;
            o->decay = -1;
            o->ts = v[0];
            o->k = 0;
            o->bc = v[7];
            o->cram = v[8];
            for (int i = 0; i < 6; i++) vt->from_f64(c, o->y + (size_t)i * vt->esz, &v[1 + i], 1);
        }
        n++;
    }
    fclose(f);
    free(line);
    *ts_out = ts;
}

/* a checkpoint: header "# m1h checkpoint track T kind K k N ts X ..."; lines "idx decay k0..k5 d0..d5 bc cram".
   want(idx, k) says where an object goes (NULL: not wanted) */
typedef Obj *(*want_fn)(void *u, long idx, long k);
static void load_ckpt(const char *arg, const m1_vt *vt, const char *kname, want_fn want, void *u)
{
    char path[1024];
    split_checked(arg, path, sizeof path);
    FILE *f = fopen(path, "rb");
    if (!f) m1_die("cannot read %s", path);
    char *line = (char *)malloc(1 << 16);
    long k = -1, nlines = 0, endn = -1;
    double ts = NAN;
    while (fgets(line, 1 << 16, f)) {
        if (!strncmp(line, "# m1h checkpoint", 16)) {
            char *p = strstr(line, " kind ");
            if (!p || strncmp(p + 6, kname, strlen(kname)) || (p[6 + strlen(kname)] != ' ')) m1_die("%s is not a %s checkpoint", path, kname);
            p = strstr(line, " k ");
            if (!p) m1_die("%s: no k", path);
            k = strtol(p + 3, NULL, 10);
            p = strstr(line, " ts ");
            if (!p) m1_die("%s: no ts", path);
            ts = strtod(p + 4, NULL);
            continue;
        }
        if (!strncmp(line, "# end ", 6)) { endn = strtol(line + 6, NULL, 10); continue; }
        if (line[0] == '#' || line[0] == '\n' || line[0] == '\r') continue;
        if (k < 0) m1_die("%s: a line before the header", path);
        char tok[16][80];
        if (sscanf(line, "%79s %79s %79s %79s %79s %79s %79s %79s %79s %79s %79s %79s %79s %79s %79s %79s", tok[0], tok[1], tok[2], tok[3],
                   tok[4], tok[5], tok[6], tok[7], tok[8], tok[9], tok[10], tok[11], tok[12], tok[13], tok[14], tok[15]) != 16)
            m1_die("%s: a short line", path);
        nlines++;
        long idx = strtol(tok[0], NULL, 10);
        Obj *o = want(u, idx, k);
        if (!o) continue;
        if (o->found) m1_die("object %ld at step %ld twice in the checkpoints given", idx, k);
        o->found = 1;
        o->idx = idx;
        o->decay = strtol(tok[1], NULL, 10);
        o->ts = ts;
        o->k = k;
        for (int i = 0; i < 6; i++) unhex(tok[2 + i], o->y + (size_t)i * vt->esz, vt->esz);
        o->bc = d_of_hex16(tok[14]);
        o->cram = d_of_hex16(tok[15]);
    }
    fclose(f);
    free(line);
    if (endn != nlines) m1_die("%s is incomplete (%ld lines, end mark %ld)", path, nlines, endn);
}

/* ------------------------------------------------------------------ batches */
typedef struct {
    size_t n;
    long first_slot;
    void *y[6], *bc, *cram;
} Batch;
static void batch_fill(Batch *b, const m1_vt *vt, m1_ctx *c, Obj *const *ob, size_t n)
{
    const size_t es = vt->esz;
    b->n = n;
    for (int i = 0; i < 6; i++) {
        b->y[i] = calloc(n, es);
        for (size_t l = 0; l < n; l++) memcpy((unsigned char *)b->y[i] + l * es, ob[l]->y + (size_t)i * es, es);
    }
    b->bc = calloc(n, es);
    b->cram = calloc(n, es);
    for (size_t l = 0; l < n; l++) {
        vt->from_f64(c, (unsigned char *)b->bc + l * es, &ob[l]->bc, 1);
        vt->from_f64(c, (unsigned char *)b->cram + l * es, &ob[l]->cram, 1);
    }
}
static void batch_free(Batch *b)
{
    for (int i = 0; i < 6; i++) free(b->y[i]);
    free(b->bc);
    free(b->cram);
}
/* one object's line: idx decay, the six in the kind's bytes, the six as binary64, bc, cram */
static void obj_line(FILE *f, const m1_vt *vt, m1_ctx *c, long idx, long decay, Batch *b, size_t l, double bc, double cram)
{
    const size_t es = vt->esz;
    fprintf(f, "%ld %ld", idx, decay);
    for (int i = 0; i < 6; i++) phex(f, (unsigned char *)b->y[i] + l * es, es);
    for (int i = 0; i < 6; i++) {
        double d;
        vt->to_f64(c, &d, (unsigned char *)b->y[i] + l * es, 1);
        p64(f, d);
    }
    p64(f, bc);
    p64(f, cram);
    fputc('\n', f);
}

/* ------------------------------------------------------------------ mode run */
typedef struct {
    Obj *O;
    long first, count, k0;
} RunWant;
static Obj *run_want(void *u, long idx, long k)
{
    RunWant *w = (RunWant *)u;
    if (k != w->k0) m1_die("a checkpoint at step %ld, not k0 %ld", k, w->k0);
    if (idx < w->first || idx >= w->first + w->count) return NULL;
    return &w->O[idx - w->first];
}

static const char *g_pause[8];
static int g_npause = 0;
static char g_run[512];
static int paused(void)
{
    char p[1024];
    for (int i = 0; i < g_npause; i++) {
        snprintf(p, sizeof p, "%s/%s", g_run, g_pause[i]);
        if (exists(p)) return 1;
    }
    return 0;
}
static void pause_wait(FILE *sl)
{
    if (!paused()) return;
    const double t0 = now_rt();
    fprintf(sl, "p %.6f\n", t0);
    fflush(sl);
    while (paused() && !g_term) sleep_s(5.0);
    const double t1 = now_rt();
    fprintf(sl, "P %.6f %.6f %.3f\n", t0, t1, t1 - t0);
    fflush(sl);
}

static int mode_run(int argc, char **argv)
{
    const char *kname = need(argc, argv, "--kind"), *table = need(argc, argv, "--table"), *track = need(argc, argv, "--track");
    snprintf(g_run, sizeof g_run, "%s", need(argc, argv, "--run"));
    const long first = atol(need(argc, argv, "--first")), count = atol(need(argc, argv, "--count")), lanes = atol(need(argc, argv, "--lanes"));
    const long k0 = atol(need(argc, argv, "--k0")), kend = atol(need(argc, argv, "--kend")), ck = atol(need(argc, argv, "--ckpt-every"));
    const double unix_ref = strtod(need(argc, argv, "--unix-ref"), NULL), t_ref = strtod(need(argc, argv, "--t-ref"), NULL);
    const double allow_s = HSTEP * atof(need(argc, argv, "--allow"));
    const int wk = atoi(need(argc, argv, "--worker")), nw = atoi(need(argc, argv, "--nworkers"));
    const int cr = has(argc, argv, "--cr");
    const int nosync = has(argc, argv, "--no-sync"); /* tests only: checkpoints flushed but not fsync'd (H6's 113,000 small files) */
    /* tests only (H2): SIGKILL to itself right after step K is logged and its checkpoint written; pause files honoured
       only before steps after K. A native64 worker passes 120 steps in well under a second, too fast for a gate to
       time a kill or a pause from outside. */
    const long tkill = atol(opt(argc, argv, "--test-kill-after", "-1")), tpause = atol(opt(argc, argv, "--test-pause-from", "-1"));
    if (count < 1 || lanes < 1 || ck < 1 || kend < k0 || nw < 1 || wk < 0 || wk >= nw || !(allow_s >= 0)) m1_die("bad run arguments");
    g_npause = opts(argc, argv, "--pause", g_pause, 8);
    if (!g_npause) { g_pause[0] = "PAUSE"; g_pause[1] = "PAUSE.disk"; g_npause = 2; }
    const double stagger = (double)wk * HSTEP / (double)nw;
    load_inputs(table);
    const m1_vt *vt = m1_vt_by_name(kname);
    if (!vt) m1_die("no kind %s", kname);
    m1_ctx c;
    memset(&c, 0, sizeof c);
    if (cft_open(NULL, 0, &c.dev) != CFT_OK) m1_die("cft_open(NULL) failed");
    c.cr_transc = cr;
    const size_t es = vt->esz;
    Obj *O = (Obj *)calloc((size_t)count, sizeof(Obj));
    for (long i = 0; i < count; i++) O[i].y = (unsigned char *)calloc(6, es);
    /* the kind must exist before the seed's values are converted: set up with a provisional origin, then the real one */
    m1_model m0 = model_real(0.0);
    if (vt->setup(&c, &m0, &G, &DE, (size_t)lanes)) m1_die("setup %s", kname);
    const char *seed = opt(argc, argv, "--seed", NULL);
    const char *inits[4096];
    const int ninit = opts(argc, argv, "--init", inits, 4096);
    double ts = NAN;
    if (seed && ninit) m1_die("--seed or --init, not both");
    if (seed) {
        if (k0 != 0) m1_die("a run from the seed starts at k0 = 0");
        load_seed(seed, vt, &c, O, first, count, &ts);
    } else if (ninit) {
        RunWant w = {O, first, count, k0};
        for (int i = 0; i < ninit; i++) load_ckpt(inits[i], vt, kname, run_want, &w);
        ts = O[0].ts;
    } else m1_die("--seed or --init is required");
    for (long i = 0; i < count; i++) {
        if (!O[i].found) m1_die("object %ld is in no file given", first + i);
        if (O[i].ts != ts) m1_die("object %ld: another origin", first + i);
    }
    c.model.t0 = ts;
    if (ts + HSTEP * (double)k0 < FT.t0 + 3.0 * FT.h || ts + HSTEP * (double)kend + HSTEP > FT.t0 + (double)(FT.nk - 4) * FT.h)
        m1_die("the run's span is not inside the frame table");
    const long nb = (count + lanes - 1) / lanes;
    Batch *B = (Batch *)calloc((size_t)nb, sizeof(Batch));
    for (long b = 0; b < nb; b++) {
        size_t n = (size_t)(count - b * lanes < lanes ? count - b * lanes : lanes);
        Obj **ob = (Obj **)malloc(n * sizeof(Obj *));
        for (size_t l = 0; l < n; l++) ob[l] = &O[b * lanes + (long)l];
        batch_fill(&B[b], vt, &c, ob, n);
        B[b].first_slot = b * lanes;
        free(ob);
    }
    char dir[1024], path[1200];
    snprintf(dir, sizeof dir, "%s/steps/%s", g_run, track);
    mkdir_p(dir);
    FILE *sl = NULL;
    for (int n = 1; n < 10000 && !sl; n++) {
        snprintf(path, sizeof path, "%s/w%02dof%02d.k%06ld.%d.log", dir, wk, nw, k0, n);
        sl = open_new(path);
    }
    if (!sl) m1_die("cannot create a step log in %s", dir);
    snprintf(dir, sizeof dir, "%s/ckpt/%s", g_run, track);
    mkdir_p(dir);
#ifndef _WIN32
    struct sigaction sa;
    memset(&sa, 0, sizeof sa);
    sa.sa_handler = on_term;
    sigemptyset(&sa.sa_mask);
    sigaction(SIGTERM, &sa, NULL); /* no SA_RESTART: a sleep ends at once */
#endif
    fprintf(sl, "# m1h step log track %s kind %s cr %d worker %d nworkers %d first %ld count %ld lanes %ld batches %ld k0 %ld kend %ld ckpt_every %ld "
            "ts %a t_ref %a unix_ref %.6f allow_s %.3f stagger_s %.6f pid %d frame_sha256 %s build_id %s no_sync %d test_kill_after %ld "
            "test_pause_from %ld started %.6f\n",
            track, kname, cr, wk, nw, first, count, lanes, nb, k0, kend, ck, ts, t_ref, unix_ref, allow_s, stagger, my_pid(), FT.sha256,
            cft_build_id(), nosync, tkill, tpause, now_rt());
    fprintf(sl, "# S k start finish due lag compute_s (POSIX s; lag = finish - due) | p pause-start | P start end s | C k file | D k idx r | X reason\n");
    fflush(sl);

    long ckw = 0;
    char cname[1400];
    /* the checkpoint at step k: a temporary name, flushed, renamed to a name that does not exist */
    #define WRITE_CKPT(KK)                                                                                                    \
        do {                                                                                                                  \
            char tmp[1400];                                                                                                   \
            snprintf(tmp, sizeof tmp, "%s/.k%06ld.w%02dof%02d.%d.tmp", dir, (long)(KK), wk, nw, my_pid());                    \
            FILE *cf = open_new(tmp);                                                                                         \
            if (!cf) m1_die("cannot create %s", tmp);                                                                         \
            fprintf(cf, "# m1h checkpoint track %s kind %s k %ld ts %a t %a first %ld count %ld worker %d nworkers %d lanes %ld\n", \
                    track, kname, (long)(KK), ts, ts + HSTEP * (double)(KK), first, count, wk, nw, lanes);                    \
            fprintf(cf, "# columns: idx decay_step x y z vx vy vz (the kind's bytes, hex, most significant first) "            \
                        "x y z vx vy vz bc cram (binary64 bits, hex)\n");                                                     \
            for (long b_ = 0; b_ < nb; b_++)                                                                                   \
                for (size_t l_ = 0; l_ < B[b_].n; l_++) {                                                                      \
                    Obj *o_ = &O[B[b_].first_slot + (long)l_];                                                                 \
                    obj_line(cf, vt, &c, o_->idx, o_->decay, &B[b_], l_, o_->bc, o_->cram);                                     \
                }                                                                                                             \
            fprintf(cf, "# end %ld\n", count);                                                                                \
            if (nosync) fflush(cf); else flush_sync(cf);                                                                      \
            fclose(cf);                                                                                                       \
            int r_ = 0;                                                                                                       \
            for (;; r_++) {                                                                                                   \
                if (r_ == 0) snprintf(cname, sizeof cname, "%s/k%06ld.w%02dof%02d.txt", dir, (long)(KK), wk, nw);             \
                else snprintf(cname, sizeof cname, "%s/k%06ld.w%02dof%02d.r%d.txt", dir, (long)(KK), wk, nw, r_);            \
                if (rename_noreplace(tmp, cname) == 0) break;                                                                 \
                if (errno != EEXIST && errno != EACCES) m1_die("cannot rename %s: %s", tmp, strerror(errno));               \
                if (r_ > 1000) m1_die("no free checkpoint name for %s", tmp);                                                 \
            }                                                                                                                 \
            fprintf(sl, "C %ld %s\n", (long)(KK), cname);                                                                     \
            fflush(sl);                                                                                                       \
            ckw++;                                                                                                            \
        } while (0)

    if (seed) WRITE_CKPT(0);
    double *d = (double *)malloc((size_t)lanes * 6 * sizeof(double));
    long k = k0;
    int code = 0;
    const char *why = "done";
    while (k < kend) {
        const long kk = k + 1;
        /* before step kk: a pause, then the allowance and the stagger */
        for (;;) {
            if (tpause < 0 || kk > tpause) pause_wait(sl);
            if (g_term) break;
            const double due = unix_ref + (ts + HSTEP * (double)kk - t_ref);
            const double now = now_rt();
            if (due - now > allow_s) {
                const double target = due - allow_s + stagger;
                if (target > now) { sleep_s(target - now < 5.0 ? target - now : 5.0); continue; }
            }
            break;
        }
        if (g_term) { why = "sigterm"; code = 10; break; }
        const double due = unix_ref + (ts + HSTEP * (double)kk - t_ref);
        const double t_start = now_rt(), m_start = now_mono();
        for (long b = 0; b < nb; b++) vt->rk4(&c, B[b].y, B[b].bc, B[b].cram, "15", k, 1, NULL, NULL, B[b].n);
        const double t_fin = now_rt(), m_fin = now_mono();
        k = kk;
        fprintf(sl, "S %ld %.6f %.6f %.6f %.6f %.6f\n", k, t_start, t_fin, due, t_fin - due, m_fin - m_start);
        /* the end checks of every live object */
        long bad = -1;
        for (long b = 0; b < nb && bad < 0; b++) {
            const size_t n = B[b].n;
            for (int i = 0; i < 6; i++) vt->to_f64(&c, d + (size_t)i * n, B[b].y[i], n);
            for (size_t l = 0; l < n; l++) {
                Obj *o = &O[B[b].first_slot + (long)l];
                if (o->decay >= 0) continue;
                int fin = 1;
                for (int i = 0; i < 6; i++) fin &= isfinite(d[(size_t)i * n + l]) ? 1 : 0;
                if (!fin) { bad = o->idx; break; }
                const double x = d[l], y = d[n + l], z = d[2 * n + l], r = sqrt(x * x + y * y + z * z);
                if (!(r > RMIN)) {
                    o->decay = k;
                    fprintf(sl, "D %ld %ld %.3f\n", k, o->idx, r);
                }
            }
        }
        fflush(sl);
        if (bad >= 0) {
            fprintf(sl, "X nonfinite k %ld idx %ld\n", k, bad);
            fflush(sl);
            fprintf(stderr, "m1h: object %ld is not finite at step %ld\n", bad, k);
            return 4;
        }
        if (k % ck == 0 || k == kend) WRITE_CKPT(k);
        if (k == tkill) {
            fprintf(sl, "X test-kill after step %ld at %.6f\n", k, now_rt());
            fflush(sl);
#ifdef _WIN32
            TerminateProcess(GetCurrentProcess(), 137);
#else
            raise(SIGKILL);
#endif
        }
        if (g_term && k < kend) { why = "sigterm"; code = 10; break; }
    }
    fprintf(sl, "X %s k %ld checkpoints %ld at %.6f cft_flags 0x%x\n", why, k, ckw, now_rt(), (unsigned)c.cft_flags);
    flush_sync(sl);
    fclose(sl);
    printf("m1h run track %s worker %d of %d: %s at step %ld, %ld checkpoints\n", track, wk, nw, why, k, ckw);
    vt->teardown(&c);
    cft_close(c.dev);
    return code;
}

/* ------------------------------------------------------------------ mode seg */
typedef struct {
    long idx, kc;
    int mode;           /* 'E' or 'N' */
    double e;           /* mode E: the epoch (TDB s) */
    long n;             /* mode N: whole steps */
    Obj o;
} Tgt;
typedef struct {
    Tgt *T;
    long nt;
} SegWant;
static Obj *seg_want(void *u, long idx, long k)
{
    SegWant *w = (SegWant *)u;
    for (long i = 0; i < w->nt; i++)
        if (w->T[i].idx == idx && w->T[i].kc == k && !w->T[i].o.found) return &w->T[i].o;
    return NULL;
}
static void seg_out(FILE *f, const m1_vt *vt, m1_ctx *c, Tgt *t, double tt, Batch *b, size_t l)
{
    fprintf(f, "R %ld %ld %c %a", t->idx, t->kc, t->mode, tt);
    fputc(' ', f);
    obj_line(f, vt, c, t->o.idx, t->o.decay, b, l, t->o.bc, t->o.cram);
}
static int mode_seg(int argc, char **argv)
{
    const char *kname = need(argc, argv, "--kind"), *table = need(argc, argv, "--table");
    const char *tpath = need(argc, argv, "--targets"), *outp = need(argc, argv, "--out");
    const long lanes = atol(opt(argc, argv, "--lanes", "64"));
    const int cr = has(argc, argv, "--cr");
    load_inputs(table);
    const m1_vt *vt = m1_vt_by_name(kname);
    if (!vt) m1_die("no kind %s", kname);
    m1_ctx c;
    memset(&c, 0, sizeof c);
    if (cft_open(NULL, 0, &c.dev) != CFT_OK) m1_die("cft_open(NULL) failed");
    c.cr_transc = cr;
    m1_model m0 = model_real(0.0);
    if (vt->setup(&c, &m0, &G, &DE, (size_t)(lanes > 0 ? lanes : 1))) m1_die("setup %s", kname);
    const size_t es = vt->esz;
    /* the targets */
    FILE *f = fopen(tpath, "rb");
    if (!f) m1_die("cannot read %s", tpath);
    long cap = 256, nt = 0;
    Tgt *T = (Tgt *)calloc((size_t)cap, sizeof(Tgt));
    char line[512];
    while (fgets(line, sizeof line, f)) {
        if (line[0] == '#' || line[0] == '\n' || line[0] == '\r') continue;
        long idx, kc;
        char md[8], val[128];
        if (sscanf(line, "%ld %ld %7s %127s", &idx, &kc, md, val) != 4 || (md[0] != 'E' && md[0] != 'N')) m1_die("bad target line: %s", line);
        if (nt == cap) { cap *= 2; T = (Tgt *)realloc(T, (size_t)cap * sizeof(Tgt)); memset(T + nt, 0, (size_t)(cap - nt) * sizeof(Tgt)); }
        Tgt *t = &T[nt++];
        t->idx = idx;
        t->kc = kc;
        t->mode = md[0];
        if (md[0] == 'E') t->e = strtod(val, NULL);
        else t->n = atol(val);
        t->o.y = (unsigned char *)calloc(6, es);
    }
    fclose(f);
    if (!nt) m1_die("no targets in %s", tpath);
    SegWant w = {T, nt};
    const char *seed = opt(argc, argv, "--seed", NULL);
    const char *inits[4096];
    const int ninit = opts(argc, argv, "--init", inits, 4096);
    if (seed) {
        /* from the seed: every target must start at kc = 0 */
        long maxidx = 0;
        for (long i = 0; i < nt; i++) {
            if (T[i].kc != 0) m1_die("a target from the seed must have kc = 0");
            if (T[i].idx > maxidx) maxidx = T[i].idx;
        }
        Obj *O = (Obj *)calloc((size_t)maxidx + 1, sizeof(Obj));
        for (long i = 0; i <= maxidx; i++) O[i].y = (unsigned char *)calloc(6, es);
        double ts;
        load_seed(seed, vt, &c, O, 0, maxidx + 1, &ts);
        for (long i = 0; i < nt; i++) {
            Obj *s = &O[T[i].idx];
            if (!s->found) m1_die("object %ld is not in the seed", T[i].idx);
            unsigned char *y = T[i].o.y;
            T[i].o = *s;
            T[i].o.y = y;
            memcpy(y, s->y, 6 * es);
        }
    }
    for (int i = 0; i < ninit; i++) load_ckpt(inits[i], vt, kname, seg_want, &w);
    for (long i = 0; i < nt; i++)
        if (!T[i].o.found) m1_die("target %ld (object %ld at step %ld) is in no file given", i, T[i].idx, T[i].kc);
    FILE *fo = open_new(outp);
    if (!fo) m1_die("cannot create %s (it must not exist)", outp);
    fprintf(fo, "# m1h seg kind %s cr %d targets %ld lanes %ld frame_sha256 %s build_id %s\n", kname, cr, nt, lanes, FT.sha256, cft_build_id());
    fprintf(fo, "# columns: R idx kc mode t idx decay_step x y z vx vy vz (the kind's bytes) x y z vx vy vz bc cram (binary64 bits)\n");
    char *done = (char *)calloc((size_t)nt, 1);
    for (long i = 0; i < nt; i++) {
        if (done[i]) continue;
        Tgt *t = &T[i];
        c.model.t0 = t->o.ts;
        if (t->mode == 'E') {
            const long M = (long)floor((t->e - t->o.ts) / HSTEP);
            const double tg = t->o.ts + HSTEP * (double)M, hs = t->e - tg;
            if (M < t->kc) m1_die("target %ld: the epoch %a is before its checkpoint's step %ld", i, t->e, t->kc);
            if (tg + hs != t->e || hs < 0 || hs >= HSTEP) m1_die("target %ld: the epoch %a is not exact on the grid", i, t->e);
            Obj *ob = &t->o;
            Batch b;
            batch_fill(&b, vt, &c, &ob, 1);
            if (M > t->kc) vt->rk4(&c, b.y, b.bc, b.cram, "15", t->kc, M - t->kc, NULL, NULL, 1);
            if (hs > 0) vt->rk4_short(&c, b.y, b.bc, b.cram, tg, hs, M + 1, NULL, NULL, 1);
            seg_out(fo, vt, &c, t, t->e, &b, 0);
            batch_free(&b);
            done[i] = 1;
        } else {
            /* every later mode-N target with the same kc, n and origin, up to the lane count */
            Obj **ob = (Obj **)malloc((size_t)lanes * sizeof(Obj *));
            long *who = (long *)malloc((size_t)lanes * sizeof(long));
            size_t n = 0;
            for (long j = i; j < nt && (long)n < lanes; j++)
                if (!done[j] && T[j].mode == 'N' && T[j].kc == t->kc && T[j].n == t->n && T[j].o.ts == t->o.ts) {
                    ob[n] = &T[j].o;
                    who[n++] = j;
                }
            Batch b;
            batch_fill(&b, vt, &c, ob, n);
            if (t->n > 0) vt->rk4(&c, b.y, b.bc, b.cram, "15", t->kc, t->n, NULL, NULL, n);
            for (size_t l = 0; l < n; l++) {
                seg_out(fo, vt, &c, &T[who[l]], t->o.ts + HSTEP * (double)(t->kc + t->n), &b, l);
                done[who[l]] = 1;
            }
            batch_free(&b);
            free(ob);
            free(who);
        }
        fflush(fo);
    }
    fprintf(fo, "# end %ld cft_flags 0x%x\n", nt, (unsigned)c.cft_flags);
    flush_sync(fo);
    fclose(fo);
    printf("m1h seg %s: %ld targets\n", kname, nt);
    vt->teardown(&c);
    cft_close(c.dev);
    return 0;
}

int main(int argc, char **argv)
{
    if (argc < 2) m1_die("usage: m1h run|seg ...");
    if (!strcmp(argv[1], "run")) return mode_run(argc, argv);
    if (!strcmp(argv[1], "seg")) return mode_seg(argc, argv);
    m1_die("no mode %s", argv[1]);
    return 2;
}
