/* i_run.c - cft-debris DEBRIS-I: the program's driver. Runs a cftc image on libcft's software executor, run by run
 * and segment by segment, filling each run's values, carrying the state, and keeping every boundary state, every lane's
 * flags and every mark.
 *
 * cft-debris, MIT licence (see LICENSE at the repository root). Written by DEBRIS-I, 2026-11-23, from DEBRIS-D's
 * studies/debris-d/tools/seqrun.c (cft-debris's own, MIT): its open at a depth, its load and its segment loop with the
 * carried scratch. The READY / G / TIMED_DONE / Q protocol of mode rate is DEBRIS-G's tests/m1g.c's (MIT).
 *
 *   i_run run  --image IMG.cftp --runs RUNS.bin --init INIT.bin --lanes N --depth D --out PREFIX
 *   i_run rate --image IMG.cftp --runs RUNS.bin --init INIT.bin --lanes N --depth D --out PREFIX
 *
 * RUNS.bin (tests/i_vals.py writes it; little-endian): "DBIR", u32 version 1, u32 esz, u32 n_consts, u32 n_scratch
 * (the lane's state and lane params), u32 n_state, u32 nruns, u32 n_shared, then n_shared u32 scratch slots (the lane
 * params every lane shares: the run's data); then each run: u32 nseg, u32 t_slot, esz bytes (t's encoding at the run's
 * start), n_consts x esz bytes (the run's whole bank), n_shared x esz bytes (the shared lane params' values).
 * INIT.bin: N lanes x n_scratch x esz bytes, each lane's state and lane params at the first run's start (the lane's own
 * values, bc among them, are kept from it and rewritten at every run's start).
 * At each run's start the driver writes every lane param of every lane - the shared ones from the run, the lane's own
 * from INIT - whether or not its value changed; then it requires each lane's t to equal the run's start, bit for bit.
 * Each segment is one cft_program_run_ex (the image's REPEAT count is the segment's steps).
 * Written: PREFIX.seg.bin (per segment: u32 run, u32 seg, then N x n_state x esz state bytes, then N lane bytes),
 *          PREFIX.marks.bin (per marked lane-segment: u32 run, u32 seg, u32 lane, then the lane's n_scratch x esz
 *          scratch at the segment's start - the boundary state before the mark - then its n_state x esz state after),
 *          and on stdout one line a segment: "seg <run> <seg> flags 0x.. bus 0x.. marked <k> [lanes <i> ...]".
 * Lane byte (R23): [4:0] the IEEE flags, [5] deposit overflow, [6] strict range, [7] the mark.
 * Mode rate: the same runs, with the timed region between the release byte 'G' and TIMED_DONE, then REPORT lines; its
 * per-segment file is written after the timed region (the states are kept in memory).
 */
#ifdef __linux__
#define _GNU_SOURCE
#endif
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#ifdef _WIN32
#include <fcntl.h>
#include <io.h>
#include <windows.h>
#else
#include <sched.h>
#include <time.h>
#include <unistd.h>
#endif
#include "cft.h"

static void die(const char *what) { fprintf(stderr, "i_run: %s\n", what); exit(2); }
static void die_st(const char *what, cft_status st)
{
    fprintf(stderr, "i_run: %s: %s (%d): %s\n", what, cft_strerror(st), (int)st, cft_last_error());
    exit(2);
}
static uint8_t *slurp(const char *path, size_t *len)
{
    FILE *f = fopen(path, "rb");
    if (!f) { perror(path); exit(2); }
    fseek(f, 0, SEEK_END);
    long L = ftell(f);
    fseek(f, 0, SEEK_SET);
    uint8_t *b = (uint8_t *)malloc(L > 0 ? (size_t)L : 1);
    if (!b) die("out of memory");
    if (L > 0 && fread(b, 1, (size_t)L, f) != (size_t)L) die("short read");
    fclose(f);
    *len = (size_t)L;
    return b;
}
static const char *opt(int argc, char **argv, const char *o, const char *def)
{
    for (int i = 1; i + 1 < argc; i++)
        if (!strcmp(argv[i], o)) return argv[i + 1];
    return def;
}
static const char *need(int argc, char **argv, const char *o)
{
    const char *v = opt(argc, argv, o, NULL);
    if (!v) { fprintf(stderr, "i_run: %s is required\n", o); exit(2); }
    return v;
}
static uint32_t rd32(const uint8_t *p) { uint32_t v; memcpy(&v, p, 4); return v; }

/* ------------------------------------------------------------------ SHA-256 (DEBRIS-G's m1g.c's) */
typedef struct { uint32_t h[8]; uint64_t len; unsigned char buf[64]; size_t nb; } Sha;
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
static void sha_mem(const void *p, size_t n, char out[65])
{
    Sha s;
    sha_init(&s);
    sha_add(&s, p, n);
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

int main(int argc, char **argv)
{
    if (argc < 2 || (strcmp(argv[1], "run") && strcmp(argv[1], "rate")))
        die("usage: i_run run|rate --image IMG --runs RUNS --init INIT --lanes N --depth D --out PREFIX");
    const int rate = !strcmp(argv[1], "rate");
#ifdef _WIN32
    _setmode(0, _O_BINARY);
#endif
    const char *img_path = need(argc, argv, "--image"), *runs_path = need(argc, argv, "--runs"),
               *init_path = need(argc, argv, "--init"), *prefix = need(argc, argv, "--out");
    const size_t n = (size_t)strtoul(need(argc, argv, "--lanes"), NULL, 10);
    const unsigned depth = (unsigned)strtoul(need(argc, argv, "--depth"), NULL, 10);
    size_t img_bytes, runs_bytes, init_bytes;
    uint8_t *img = slurp(img_path, &img_bytes);
    uint8_t *R = slurp(runs_path, &runs_bytes);
    uint8_t *init = slurp(init_path, &init_bytes);
    char sha_img[65], sha_runs[65], sha_init_[65];
    sha_mem(img, img_bytes, sha_img);
    sha_mem(R, runs_bytes, sha_runs);
    sha_mem(init, init_bytes, sha_init_);
    if (runs_bytes < 32 || memcmp(R, "DBIR", 4) || rd32(R + 4) != 1) die("runs file: not DBIR version 1");
    const size_t esz = rd32(R + 8), ncon = rd32(R + 12), nscr = rd32(R + 16), nst = rd32(R + 20), nruns = rd32(R + 24),
                 nsh = rd32(R + 28);
    if (runs_bytes < 32 + 4 * nsh) die("runs file: short header");
    uint32_t *shslot = (uint32_t *)malloc((nsh ? nsh : 1) * 4);
    for (size_t i = 0; i < nsh; i++) {
        shslot[i] = rd32(R + 32 + 4 * i);
        if (shslot[i] < nst || shslot[i] >= nscr) die("runs file: a shared slot outside the lane params");
    }
    const size_t run_rec = 8 + esz + ncon * esz + nsh * esz;
    size_t off0 = 32 + 4 * nsh;
    if (runs_bytes != off0 + nruns * run_rec) die("runs file: its length is not its header's");
    if (init_bytes != n * nscr * esz) die("init file: not lanes x n_scratch x esz bytes");
    /* which lane-param slots are the lane's own (kept from INIT) */
    unsigned char *shared = (unsigned char *)calloc(nscr, 1);
    for (size_t i = 0; i < nsh; i++) shared[shslot[i]] = 1;

    cft_device *dev = NULL;
    cft_open_args oa;
    memset(&oa, 0, sizeof oa);
    oa.struct_size = sizeof oa;
    oa.artifact = NULL;
    oa.scratch_depth = depth;
    cft_status st = cft_open_ex(&oa, &dev);
    if (st != CFT_OK) die_st("cft_open_ex", st);
    cft_program *prog = NULL;
    st = cft_program_load(dev, img, img_bytes, &prog);
    if (st != CFT_OK) die_st("cft_program_load", st);
    cft_program_info info;
    memset(&info, 0, sizeof info);
    info.struct_size = sizeof info;
    st = cft_program_get_info(prog, &info);
    if (st != CFT_OK) die_st("cft_program_get_info", st);
    if (cft_format_size(info.format) != esz) die("the image's format is not the runs file's");
    if (info.n_consts != ncon) die("the image's bank size is not the runs file's");
    if (info.n_scratch_in != nscr || info.n_scratch_out != nscr) die("the image's scratch is not the runs file's");
    printf("i_run %s build_id %s depth %u\n", argv[1], cft_build_id(), depth);
    printf("image %s sha256 %s insns %u consts %u scratch_in %u scratch_out %u scratch_used %u esz %u\n", img_path, sha_img,
           info.n_insns, info.n_consts, info.n_scratch_in, info.n_scratch_out, info.scratch_used, (unsigned)esz);
    printf("runs %s sha256 %s nruns %lu shared %lu\ninit %s sha256 %s lanes %lu\n", runs_path, sha_runs, (unsigned long)nruns,
           (unsigned long)nsh, init_path, sha_init_, (unsigned long)n);
    fflush(stdout);

    const size_t lane_b = nscr * esz, all_b = n * lane_b;
    uint8_t *cur = (uint8_t *)malloc(all_b ? all_b : 1), *out = (uint8_t *)calloc(all_b ? all_b : 1, 1);
    uint8_t *A = (uint8_t *)calloc(n ? n * esz : 1, 1);
    size_t dep_bytes = n * (size_t)info.max_deposits * esz;
    uint8_t *dep = (uint8_t *)calloc(dep_bytes ? dep_bytes : 1, 1);
    uint32_t *counts = (uint32_t *)calloc(n ? n : 1, sizeof(uint32_t));
    uint8_t *lf = (uint8_t *)calloc(n ? n : 1, 1);
    if (!cur || !out || !A || !dep || !counts || !lf) die("out of memory");
    memcpy(cur, init, all_b);
    size_t nseg_all = 0;
    for (size_t r = 0; r < nruns; r++) nseg_all += rd32(R + off0 + r * run_rec);
    /* the per-segment records, kept in memory (written at the end in mode rate, as they come in mode run) */
    const size_t segrec = 8 + n * nst * esz + n;
    uint8_t *segs = rate ? (uint8_t *)malloc(nseg_all * segrec + 1) : NULL;
    char path[1024];
    snprintf(path, sizeof path, "%s.seg.bin", prefix);
    FILE *fs = rate ? NULL : fopen(path, "wb");
    snprintf(path, sizeof path, "%s.marks.bin", prefix);
    FILE *fm = fopen(path, "wb");
    if ((!rate && !fs) || !fm || (rate && !segs)) die("cannot write the outputs");
    uint8_t *pre = (uint8_t *)malloc(all_b ? all_b : 1);
    unsigned long marks_total = 0;
    uint32_t flags_all = 0;

    int64_t t_start = 0, c_start = 0, c_ready = 0;
    int cpu_start = -1;
    char affin_ready[256], affin_start[256], affin_end[256];
    if (rate) {
        affinity_str(affin_ready, sizeof affin_ready);
        printf("READY\n");
        fflush(stdout);
        c_ready = cpu_ns();
        int eof = 0;
        int b = read_byte(&eof);
        t_start = now_ns();
        c_start = cpu_ns();
        cpu_start = which_cpu();
        affinity_str(affin_start, sizeof affin_start);
        if (eof || b != 'G') die("the release byte was not 'G'");
    }
    size_t segk = 0;
    for (size_t r = 0; r < nruns; r++) {
        const uint8_t *rr = R + off0 + r * run_rec;
        const uint32_t nseg = rd32(rr), tslot = rd32(rr + 4);
        const uint8_t *tenc = rr + 8, *bank = rr + 8 + esz, *shv = rr + 8 + esz + ncon * esz;
        for (size_t l = 0; l < n; l++) {
            uint8_t *ln = cur + l * lane_b;
            const uint8_t *iv = init + l * lane_b;
            for (size_t j = nst; j < nscr; j++)
                if (!shared[j]) memcpy(ln + j * esz, iv + j * esz, esz);
            for (size_t i = 0; i < nsh; i++) memcpy(ln + (size_t)shslot[i] * esz, shv + i * esz, esz);
            if (tslot != 0xffffffffu && memcmp(ln + (size_t)tslot * esz, tenc, esz)) {
                fprintf(stderr, "i_run: run %lu lane %lu: t is not the run's start\n", (unsigned long)r, (unsigned long)l);
                exit(4);
            }
        }
        for (uint32_t s = 1; s <= nseg; s++) {
            uint32_t flags = 0, bus = 0;
            memcpy(pre, cur, all_b);
            cft_run_args ra;
            memset(&ra, 0, sizeof ra);
            ra.struct_size = sizeof ra;
            ra.a = A;
            ra.n = n;
            ra.bank = bank;
            ra.bank_bytes = ncon * esz;
            ra.scratch_in = cur;
            ra.scratch_in_bytes = all_b;
            ra.scratch_out = out;
            ra.scratch_out_bytes = all_b;
            ra.deposits = dep;
            ra.counts = counts;
            ra.flags_out = &flags;
            ra.bus_out = &bus;
            ra.lane_flags = lf;
            ra.lane_flags_bytes = n;
            st = cft_program_run_ex(prog, &ra);
            if (st != CFT_OK) die_st("cft_program_run_ex", st);
            flags_all |= flags;
            unsigned marked = 0;
            for (size_t l = 0; l < n; l++)
                if (lf[l] & 0x80) {
                    marked++;
                    uint32_t h3[3] = {(uint32_t)r, s, (uint32_t)l};
                    fwrite(h3, 4, 3, fm);
                    fwrite(pre + l * lane_b, 1, lane_b, fm);
                    fwrite(out + l * lane_b, 1, nst * esz, fm);
                }
            marks_total += marked;
            uint8_t *rec = rate ? segs + segk * segrec : NULL;
            uint32_t h2[2] = {(uint32_t)r, s};
            if (rate) {
                memcpy(rec, h2, 8);
                for (size_t l = 0; l < n; l++) memcpy(rec + 8 + l * nst * esz, out + l * lane_b, nst * esz);
                memcpy(rec + 8 + n * nst * esz, lf, n);
            } else {
                fwrite(h2, 4, 2, fs);
                for (size_t l = 0; l < n; l++) fwrite(out + l * lane_b, 1, nst * esz, fs);
                fwrite(lf, 1, n, fs);
                printf("seg %lu %u flags 0x%x bus 0x%x marked %u", (unsigned long)r, s, flags, bus, marked);
                if (marked) {
                    printf(" lanes");
                    for (size_t l = 0; l < n; l++)
                        if (lf[l] & 0x80) printf(" %lu", (unsigned long)l);
                }
                printf("\n");
            }
            segk++;
            memcpy(cur, out, all_b); /* the whole lane is carried: state and lane params */
        }
    }
    int64_t t_end = 0, c_end = 0;
    int cpu_end = -1;
    if (rate) {
        t_end = now_ns();
        c_end = cpu_ns();
        cpu_end = which_cpu();
        affinity_str(affin_end, sizeof affin_end);
        printf("TIMED_DONE\n");
        fflush(stdout);
        int eof2 = 0;
        (void)read_byte(&eof2);
        snprintf(path, sizeof path, "%s.seg.bin", prefix);
        fs = fopen(path, "wb");
        if (!fs) die("cannot write the segment file");
        fwrite(segs, 1, nseg_all * segrec, fs);
    }
    fclose(fs);
    fclose(fm);
    /* the final states, lane by lane */
    char sha_final[65];
    {
        Sha s;
        sha_init(&s);
        for (size_t l = 0; l < n; l++) sha_add(&s, cur + l * lane_b, nst * esz);
        sha_end(&s, sha_final);
    }
    printf("REPORT segments %lu\nREPORT marks %lu\nREPORT flags 0x%x\nREPORT final_states_sha256 %s\n",
           (unsigned long)segk, marks_total, flags_all, sha_final);
    if (rate) {
        unsigned long steps = 0;
        /* steps a segment: the image's REPEAT count, from the info (the runs file gives segments only) */
        steps = (unsigned long)segk; /* segments; the harness multiplies by the image's steps a segment */
        printf("REPORT lanes %lu\nREPORT segments_done %lu\n", (unsigned long)n, steps);
        printf("REPORT t_start_ns %lld\nREPORT t_end_ns %lld\n", (long long)t_start, (long long)t_end);
        printf("REPORT cpu_ready_ns %lld\nREPORT cpu_start_ns %lld\nREPORT cpu_end_ns %lld\n", (long long)c_ready,
               (long long)c_start, (long long)c_end);
        printf("REPORT cpu_at_start %d\nREPORT cpu_at_end %d\n", cpu_start, cpu_end);
        printf("REPORT affinity_ready %s\nREPORT affinity_start %s\nREPORT affinity_end %s\n", affin_ready, affin_start,
               affin_end);
    }
    printf("DONE\n");
    fflush(stdout);
    cft_program_free(prog);
    cft_close(dev);
    return 0;
}
