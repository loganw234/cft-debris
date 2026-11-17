/* m1g.c - cft-debris M1 (DEBRIS-G): the batch driver of the throughput round.
 *
 * cft-debris, MIT licence (see LICENSE at the repository root). Written by DEBRIS-G, 2026-11-17. It reuses the
 * set-up of DEBRIS-F's tests/m1f.c (cft-debris's own, MIT): the model, the inputs' paths and the kind's opening.
 *
 *   m1g run --kind <native32|native64|cft32|cft64|cft128|cft256> [--cr] --table <frame table> --pop <population file>
 *           --first F --count N [--stride K] [--reverse] --lanes L --steps S --out <dir> --tag <name>
 *           [--speed X] [--abort-on-lag] [--bump-x INDEX] [--plant-early-clock]
 *
 * --cr         native kinds: exp, sin, cos, asin, acos from libcft (the kind-mode "with libcft's transcendentals")
 * the slice    objects first, first+K, ..., N of them (population indices); --reverse takes them in the opposite order
 * --lanes L    the slice is cut into batches of L lanes in that order (the last may be shorter)
 * --steps S    the run's total steps of 15 s; passes of 5,760 steps, each from the initial states; the last takes the
 *              rest. The final states are the last pass's. X (object-seconds) counts every pass.
 * --speed X    the paced mode: after each step, if the step's deadline (release + 15 s x steps done / X) lies ahead,
 *              sleep until it. Every step's lag (its finish time less its deadline) is recorded.
 * --bump-x I   G2's control: object I's initial x moved by one ulp of the kind's input format (binary32 kinds: x is
 *              rounded to binary32 and moved to the next binary32 above; the others: the next binary64 above)
 * --plant-early-clock   G1's control C4: the timed region starts before the loading
 *
 * The protocol on standard input and output (the harness's):
 *   the driver loads everything, prints READY, and blocks on one byte, 'G', from standard input (binary mode);
 *   it runs; it prints TIMED_DONE at once when the last step has ended, and blocks on one byte, 'Q' (or end of file)
 *   before it writes its outputs and its REPORT lines, so that the harness reads /proc/stat with the workers idle.
 * Times are nanoseconds of one monotonic clock (Linux CLOCK_MONOTONIC, which all processes share; Windows
 * QueryPerformanceCounter). CPU time: Linux CLOCK_PROCESS_CPUTIME_ID; Windows QueryProcessCycleTime / 2.5 (the part's
 * base clock, 2.5e9 cycles a second: BELIEVED), which on Windows is a functional-test figure only.
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
#include <psapi.h>
#else
#include <sched.h>
#include <sys/resource.h>
#include <time.h>
#include <unistd.h>
#endif

#define JD_EPOCH 2461329.5
#define PASS_STEPS 5760L
#define RMIN 6498137.0 /* 120 km above 6,378.137 km */
static char DL[512] = "";
static m1_gfc G;
static m1_de DE;
static m1_ftab FT;

/* ------------------------------------------------------------------ SHA-256 (a plain implementation) */
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

/* ------------------------------------------------------------------ clocks */
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
static long peak_kb(void)
{
#ifdef _WIN32
    PROCESS_MEMORY_COUNTERS pmc;
    if (!GetProcessMemoryInfo(GetCurrentProcess(), &pmc, sizeof pmc)) return -1;
    return (long)(pmc.PeakWorkingSetSize / 1024);
#else
    struct rusage r;
    if (getrusage(RUSAGE_SELF, &r)) return -1;
    return r.ru_maxrss; /* kilobytes on Linux */
#endif
}
static void sleep_until(int64_t t_ns)
{
    for (;;) {
        int64_t d = t_ns - now_ns();
        if (d <= 0) return;
#ifdef _WIN32
        Sleep((DWORD)(d > 2000000 ? (d - 1000000) / 1000000 : 0));
#else
        struct timespec ts;
        ts.tv_sec = (time_t)(d / 1000000000LL);
        ts.tv_nsec = (long)(d % 1000000000LL);
        nanosleep(&ts, NULL);
#endif
    }
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

/* ------------------------------------------------------------------ inputs */
static char *dlpath(const char *rel)
{
    static char buf[4][768];
    static int k = 0;
    char *b = buf[k++ & 3];
    snprintf(b, 768, "%s%s", DL, rel);
    return b;
}
typedef struct {
    long idx, rep;
    double v[9]; /* t0 x y z vx vy vz bc cram */
} Pop;
static Pop *read_pop(const char *path, long *np, char shaall[65])
{
    FILE *f = fopen(path, "rb");
    if (!f) m1_die("cannot read %s", path);
    long cap = 1024, n = 0;
    Pop *P = (Pop *)malloc((size_t)cap * sizeof(Pop));
    char *line = (char *)malloc(1 << 16);
    Sha sh;
    sha_init(&sh);
    while (fgets(line, 1 << 16, f)) {
        char *p = line, *e;
        if (*p == '#' || *p == '\n' || *p == '\r') continue;
        if (n == cap) { cap *= 2; P = (Pop *)realloc(P, (size_t)cap * sizeof(Pop)); }
        P[n].idx = strtol(p, &e, 10); p = e;
        P[n].rep = strtol(p, &e, 10); p = e;
        (void)strtol(p, &e, 10); p = e; /* the catalogue number: read past, never kept or printed */
        for (int j = 0; j < 9; j++) {
            P[n].v[j] = strtod(p, &e);
            if (e == p) m1_die("bad population line %ld", n);
            p = e;
            sha_add(&sh, &P[n].v[j], 8); /* the parsed binary64's eight bytes (little-endian host) */
        }
        if (P[n].idx != n) m1_die("population line %ld has index %ld", n, P[n].idx);
        n++;
    }
    fclose(f);
    free(line);
    sha_end(&sh, shaall);
    *np = n;
    return P;
}
static const char *opt(int argc, char **argv, const char *o, const char *def)
{
    for (int i = 1; i + 1 < argc; i++)
        if (!strcmp(argv[i], o)) return argv[i + 1];
    return def;
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

typedef struct {
    size_t n;
    void *y[6], *yi[6], *bc, *cram;
    long first_slot; /* position in the slice list of lane 0 */
} Batch;

int main(int argc, char **argv)
{
    const int64_t t_prog = now_ns();
    const int64_t c_prog = cpu_ns();
    if (argc < 2 || strcmp(argv[1], "run")) m1_die("usage: m1g run --kind K [--cr] --table T --pop P --first F --count N [--stride K] [--reverse] --lanes L --steps S --out D --tag T [...]");
#ifdef _WIN32
    _setmode(0, _O_BINARY);
    _setmode(1, _O_BINARY);
#endif
    const char *kname = opt(argc, argv, "--kind", NULL), *table = opt(argc, argv, "--table", NULL),
               *popf = opt(argc, argv, "--pop", NULL), *outd = opt(argc, argv, "--out", NULL), *tag = opt(argc, argv, "--tag", NULL);
    if (!kname || !table || !popf || !outd || !tag) m1_die("--kind, --table, --pop, --out and --tag are required");
    const int cr = has(argc, argv, "--cr"), reverse = has(argc, argv, "--reverse"), plant = has(argc, argv, "--plant-early-clock"),
              abort_lag = has(argc, argv, "--abort-on-lag");
    const long first = atol(opt(argc, argv, "--first", "0")), count = atol(opt(argc, argv, "--count", "0")),
               stride = atol(opt(argc, argv, "--stride", "1")), lanes = atol(opt(argc, argv, "--lanes", "0")),
               steps = atol(opt(argc, argv, "--steps", "0")), bump = atol(opt(argc, argv, "--bump-x", "-1"));
    const double speed = atof(opt(argc, argv, "--speed", "0"));
    if (count < 1 || lanes < 1 || steps < 1 || stride < 1) m1_die("--count, --lanes, --steps, --stride must be positive");

    const char *e = getenv("M1_DOWNLOADS");
    snprintf(DL, sizeof DL, "%s", (e && *e) ? e : "C:/Users/logan/source/repos/cft-debris-downloads/");
    if (m1_gfc_load(&G, dlpath("EIGEN6-C4.gfc/EIGEN6-C4.gfc"), M1_NMAX)) m1_die("gfc: %s", G.err);
    if (m1_de_open(&DE, dlpath("lnxp1900p2053.421/lnxp1900p2053.421"), dlpath("header.421/header.421"))) m1_die("de421: %s", DE.err);
    if (m1_ftab_load(&FT, table)) m1_die("frame table: %s", FT.err);

    long npop;
    char sha_all[65];
    Pop *P = read_pop(popf, &npop, sha_all);
    /* the slice, in processing order */
    long *slice = (long *)calloc((size_t)count, sizeof(long));
    for (long i = 0; i < count; i++) {
        long k = first + i * stride;
        if (k < 0 || k >= npop) m1_die("slice index %ld outside the population (%ld lines)", k, npop);
        slice[reverse ? count - 1 - i : i] = k;
    }
    for (long i = 1; i < count; i++)
        if (P[slice[i]].v[0] != P[slice[0]].v[0]) m1_die("t0 differs inside the slice (the model's t0 belongs to the context)");
    const double t0 = P[slice[0]].v[0];
    if (t0 < FT.t0 + 3.0 * FT.h || t0 + (double)(PASS_STEPS + 1) * 15.0 > FT.t0 + (double)(FT.nk - 4) * FT.h)
        m1_die("t0 %a and a day after it are not inside the frame table", t0);
    char sha_slice[65];
    {
        /* the slice's parsed values in ascending index order */
        long *srt = (long *)malloc((size_t)count * sizeof(long));
        memcpy(srt, slice, (size_t)count * sizeof(long));
        for (long i = 1; i < count; i++) { long x = srt[i], j = i - 1; while (j >= 0 && srt[j] > x) { srt[j + 1] = srt[j]; j--; } srt[j + 1] = x; }
        Sha sh;
        sha_init(&sh);
        for (long i = 0; i < count; i++) sha_add(&sh, P[srt[i]].v, 72);
        sha_end(&sh, sha_slice);
        free(srt);
    }

    const m1_vt *vt = m1_vt_by_name(kname);
    if (!vt) m1_die("no kind %s", kname);
    m1_ctx c;
    memset(&c, 0, sizeof c);
    if (cft_open(NULL, 0, &c.dev) != CFT_OK) m1_die("cft_open(NULL) failed");
    c.cr_transc = cr;
    m1_model model = model_real(t0);
    if (vt->setup(&c, &model, &G, &DE, (size_t)lanes)) m1_die("setup %s", kname);
    const size_t es = vt->esz;
    const int is32 = (!strcmp(kname, "native32") || !strcmp(kname, "cft32"));

    /* batches */
    long nb = (count + lanes - 1) / lanes;
    Batch *B = (Batch *)calloc((size_t)nb, sizeof(Batch));
    for (long b = 0; b < nb; b++) {
        Batch *bt = &B[b];
        bt->first_slot = b * lanes;
        bt->n = (size_t)(count - b * lanes < lanes ? count - b * lanes : lanes);
        bt->bc = calloc(bt->n, es);
        bt->cram = calloc(bt->n, es);
        double *tmp = (double *)malloc(bt->n * sizeof(double));
        for (int i = 0; i < 6; i++) {
            bt->y[i] = calloc(bt->n, es);
            bt->yi[i] = calloc(bt->n, es);
            for (size_t l = 0; l < bt->n; l++) {
                long k = slice[bt->first_slot + (long)l];
                double v = P[k].v[1 + i];
                if (k == bump && i == 0) {
                    if (is32) v = (double)nextafterf((float)v, INFINITY); /* round to binary32, then the next one up */
                    else v = nextafter(v, INFINITY);
                }
                tmp[l] = v;
            }
            vt->from_f64(&c, bt->y[i], tmp, bt->n);
            memcpy(bt->yi[i], bt->y[i], bt->n * es);
        }
        for (size_t l = 0; l < bt->n; l++) tmp[l] = P[slice[bt->first_slot + (long)l]].v[7];
        vt->from_f64(&c, bt->bc, tmp, bt->n);
        for (size_t l = 0; l < bt->n; l++) tmp[l] = P[slice[bt->first_slot + (long)l]].v[8];
        vt->from_f64(&c, bt->cram, tmp, bt->n);
        free(tmp);
    }
    if (bump >= 0) {
        int found = 0;
        for (long i = 0; i < count; i++) found |= (slice[i] == bump);
        if (!found) m1_die("--bump-x %ld is not in the slice", bump);
    }

    const long npass = (steps + PASS_STEPS - 1) / PASS_STEPS;
    int64_t *lag = (speed > 0) ? (int64_t *)calloc((size_t)steps, sizeof(int64_t)) : NULL;
    int endok = 1;
    char affin_ready[256], affin_start[256], affin_end[256];
    affinity_str(affin_ready, sizeof affin_ready);
    printf("INFO kind %s cr %d nobj %ld lanes %ld batches %ld steps %ld passes %ld speed %g bump %ld\n", kname, cr, count, lanes, nb,
           steps, npass, speed, bump);
    printf("READY\n");
    fflush(stdout);
    const int64_t c_ready = cpu_ns();
    int eof = 0;
    int bch = read_byte(&eof);
    const int64_t t_rel = now_ns(), c_rel = cpu_ns();
    const int cpu_start = which_cpu();
    affinity_str(affin_start, sizeof affin_start);
    if (eof || bch != 'G') m1_die("the release byte was %d, not 'G'", bch);
    const int64_t t_start = plant ? t_prog : t_rel; /* the planted fault: the timed region starts before the loading */
    const int64_t c_start = plant ? c_prog : c_rel;

    long done = 0, lag_first_bad = -1;
    int aborted = 0;
    long passes_run = 0;
    for (long ps = 0; ps < npass && !aborted; ps++) {
        const long nst = (ps == npass - 1) ? steps - ps * PASS_STEPS : PASS_STEPS;
        if (ps > 0)
            for (long b = 0; b < nb; b++)
                for (int i = 0; i < 6; i++) memcpy(B[b].y[i], B[b].yi[i], B[b].n * es);
        for (long st = 0; st < nst; st++) {
            for (long b = 0; b < nb; b++) vt->rk4(&c, B[b].y, B[b].bc, B[b].cram, "15", st, 1, NULL, NULL, B[b].n);
            done++;
            if (speed > 0) {
                const int64_t dl = t_rel + (int64_t)((double)done * 15e9 / speed);
                const int64_t now = now_ns();
                lag[done - 1] = now - dl;
                if (now - dl > 15000000000LL && lag_first_bad < 0) lag_first_bad = done;
                if (abort_lag && now - dl > 15000000000LL) { aborted = 1; break; }
                sleep_until(dl);
            }
        }
        passes_run++;
        if (ps < npass - 1 && !aborted) { /* the end checks of a pass that is not the last: inside the timed region */
            for (long b = 0; b < nb; b++) {
                double *d = (double *)malloc(B[b].n * sizeof(double) * 6);
                for (int i = 0; i < 6; i++) vt->to_f64(&c, d + (size_t)i * B[b].n, B[b].y[i], B[b].n);
                for (size_t l = 0; l < B[b].n; l++) {
                    double x = d[l], y = d[B[b].n + l], z = d[2 * B[b].n + l], r = sqrt(x * x + y * y + z * z);
                    int fin = 1;
                    for (int i = 0; i < 6; i++) fin &= isfinite(d[(size_t)i * B[b].n + l]) ? 1 : 0;
                    if (!fin || !(r > RMIN)) endok = 0;
                }
                free(d);
            }
        }
    }
    const int64_t t_end = now_ns(), c_end = cpu_ns();
    const int cpu_endcpu = which_cpu();
    affinity_str(affin_end, sizeof affin_end);
    printf("TIMED_DONE\n");
    fflush(stdout);
    int eof2 = 0;
    (void)read_byte(&eof2); /* 'Q', or end of file: the harness has read /proc/stat */

    /* the last pass's end checks, and the outputs */
    {
        for (long b = 0; b < nb; b++) {
            double *d = (double *)malloc(B[b].n * sizeof(double) * 6);
            for (int i = 0; i < 6; i++) vt->to_f64(&c, d + (size_t)i * B[b].n, B[b].y[i], B[b].n);
            for (size_t l = 0; l < B[b].n; l++) {
                double x = d[l], y = d[B[b].n + l], z = d[2 * B[b].n + l], r = sqrt(x * x + y * y + z * z);
                int fin = 1;
                for (int i = 0; i < 6; i++) fin &= isfinite(d[(size_t)i * B[b].n + l]) ? 1 : 0;
                if (!fin || !(r > RMIN)) endok = 0;
            }
            free(d);
        }
    }
    /* final states, in ascending index order */
    long *ord = (long *)malloc((size_t)count * sizeof(long));
    for (long i = 0; i < count; i++) ord[i] = i;
    for (long i = 1; i < count; i++) { long x = ord[i], j = i - 1; while (j >= 0 && slice[ord[j]] > slice[x]) { ord[j + 1] = ord[j]; j--; } ord[j + 1] = x; }
    char path[1024], sha_final[65];
    snprintf(path, sizeof path, "%s/%s.obj.txt", outd, tag);
    FILE *fo = fopen(path, "wb");
    if (!fo) m1_die("cannot write %s", path);
    fprintf(fo, "# m1g per-object final states: index, the six components in the kind's own bytes (hex, most significant first), then the six as binary64 bits (hex); kind %s cr %d steps %ld\n", kname, cr, steps);
    Sha sh;
    sha_init(&sh);
    for (long q = 0; q < count; q++) {
        long slot = ord[q];
        Batch *bt = &B[slot / lanes];
        size_t l = (size_t)(slot % lanes);
        fprintf(fo, "%ld", slice[slot]);
        for (int i = 0; i < 6; i++) {
            const unsigned char *p = (const unsigned char *)bt->y[i] + l * es;
            phex(fo, p, es);
            sha_add(&sh, p, es);
        }
        for (int i = 0; i < 6; i++) {
            double d;
            vt->to_f64(&c, &d, (const unsigned char *)bt->y[i] + l * es, 1);
            uint64_t u;
            memcpy(&u, &d, 8);
            fprintf(fo, " %016llx", (unsigned long long)u);
        }
        fputc('\n', fo);
    }
    fclose(fo);
    sha_end(&sh, sha_final);

    printf("REPORT kind %s\n", kname);
    printf("REPORT cr %d\n", cr);
    printf("REPORT build_id %s\n", cft_build_id());
    printf("REPORT frame_table_sha256 %s\n", FT.sha256);
    printf("REPORT population_values_sha256 %s\n", sha_all);
    printf("REPORT slice_values_sha256 %s\n", sha_slice);
    printf("REPORT nobj %ld\nREPORT lanes %ld\nREPORT batches %ld\nREPORT steps %ld\nREPORT passes %ld\nREPORT passes_run %ld\n", count, lanes, nb, steps, npass, passes_run);
    printf("REPORT steps_done %ld\n", done);
    printf("REPORT objsec %.1f\n", (double)count * 15.0 * (double)done);
    printf("REPORT t0 %a\n", t0);
    printf("REPORT t_prog_ns %lld\nREPORT t_ready_cpu_ns %lld\n", (long long)t_prog, (long long)c_ready);
    printf("REPORT t_release_read_ns %lld\nREPORT t_start_ns %lld\nREPORT t_end_ns %lld\n", (long long)t_rel, (long long)t_start, (long long)t_end);
    printf("REPORT cpu_ready_ns %lld\nREPORT cpu_release_ns %lld\nREPORT cpu_start_ns %lld\nREPORT cpu_end_ns %lld\n", (long long)c_ready, (long long)c_rel,
           (long long)c_start, (long long)c_end);
    printf("REPORT cpu_at_start %d\nREPORT cpu_at_end %d\n", cpu_start, cpu_endcpu);
    printf("REPORT affinity_ready %s\nREPORT affinity_start %s\nREPORT affinity_end %s\n", affin_ready, affin_start, affin_end);
    printf("REPORT maxrss_kb %ld\n", peak_kb());
    printf("REPORT planted_early_clock %d\n", plant);
    printf("REPORT end_checks_ok %d\n", endok);
    printf("REPORT final_states_sha256 %s\n", sha_final);
    printf("REPORT cft_flags 0x%x\n", (unsigned)c.cft_flags);
    if (speed > 0) {
        printf("REPORT speed %g\nREPORT aborted_on_lag %d\nREPORT first_step_over_15s %ld\n", speed, aborted, lag_first_bad);
        printf("REPORT lag_ns");
        for (long i = 0; i < done; i++) printf(" %lld", (long long)lag[i]);
        printf("\n");
    }
    printf("DONE\n");
    fflush(stdout);
    vt->teardown(&c);
    cft_close(c.dev);
    return endok ? 0 : 3;
}
