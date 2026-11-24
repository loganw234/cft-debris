/* j_run.c - cft-debris DEBRIS-J: the program's driver on a device. DEBRIS-I's tests/i_run.c, copied, with the four
 * additions of DEBRIS-J's design (studies/DEBRIS-J-plan.md, "The driver is DEBRIS-I's, with four additions"), so that
 * one driver runs a cftc image on libcft's software executor or on cft-fp256's hip:N device.
 *
 * cft-debris, MIT licence (see LICENSE at the repository root). Written by DEBRIS-J, 2026-11-23, as a copy of
 * tests/i_run.c (DEBRIS-I's, cft-debris's own, MIT; itself from DEBRIS-D's studies/debris-d/tools/seqrun.c and DEBRIS-G's
 * tests/m1g.c, both cft-debris's own, MIT).
 *
 *   j_run run  --image IMG.cftp --runs RUNS.bin --init INIT.bin --lanes N --depth D --out PREFIX [options]
 *   j_run rate --image IMG.cftp --runs RUNS.bin --init INIT.bin --lanes N --depth D --out PREFIX [options]
 *   j_run load --image IMG.cftp [--image IMG2.cftp ...] --depth D --out PREFIX [--artifact A] [--expect-device NAME]
 *
 * WHAT DIFFERS FROM i_run.c (each change in the copy is one of these; everything else is i_run.c's, line for line):
 *  (1) --artifact A: cft_open_ex's artifact, e.g. hip:0; absent, NULL - the software executor, as i_run opens.
 *  (2) the device's identity:
 *      - stderr is captured around cft_open_ex into PREFIX.open.txt, then copied to this process's stderr;
 *      - the line CFT_HIP_INFO=1 makes a GPU open print ("cft hip: <artifact> = <name> (...)") is printed on stdout as
 *        "device <line>", or "device none" where the open printed none (always on the software executor);
 *      - --expect-device NAME: unless that line exists and its device name is NAME exactly, the driver stops, exit 5,
 *        before any image loads;
 *      - cft_get_caps' backend, seq_features and max_scratch are printed on stdout ("caps ...");
 *      - mode load: the open and the lines above, then each --image loaded, its line printed and the program freed;
 *        nothing runs (J0's check that every image of the round loads). Exit 3 if any image is refused.
 *  (3) the provenance and the call times:
 *      - PREFIX.prov.txt, written last: the mode, cft_build_id(), the artifact, the device line, the caps, the depth,
 *        --seg-steps (the steps a segment, as the caller states it), --keep-every, --warmup-lanes, every input's
 *        SHA-256 and every output's SHA-256 and bytes (hashed as written), the counts, and the status (DONE, or
 *        ABORTED with the call that stopped it);
 *      - each segment's stdout line carries its call's wall time, "call_ns <ns>", between "bus" and "marked";
 *      - --warmup-lanes W (default 0): before the runs, one call of the first W lanes of INIT, at the first run's
 *        values written as at a run's start, for one segment; its output is discarded and its time printed
 *        ("warmup lanes W call_ns <ns>");
 *      - --abort-ms M (default 0, none): every call after the process's first (the warm-up's where there is one, else
 *        the first segment's) that takes more than M ms of wall time stops the driver after that segment's lines and
 *        records, exit 6, with "ABORT ..." on stdout and stderr and the provenance marked ABORTED;
 *      - REPORT lines for the timed region: calls, timed_calls, timed_start_ns (the start of the first call after the
 *        process's first), timed_end_ns (the end of the last call), call_max_ns and call_min_ns over the timed calls,
 *        warmup_ns;
 *      - a write error on any output is refused (exit 2) rather than left silent.
 *  (4) --keep-every N (default 1): a segment's record is written to PREFIX.seg.bin only when the segment's number in
 *      its run is a multiple of N or is the run's last; its lane bytes are then the OR of the lane bytes of every
 *      segment since the run's previous record (or the run's start). With N = 1 every record is written, each with
 *      its own lane bytes: i_run's file, byte for byte. Every mark is still written to PREFIX.marks.bin.
 *  Beside these, the program's name in its own messages is j_run.
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
 * Written: PREFIX.seg.bin (per kept segment: u32 run, u32 seg, then N x n_state x esz state bytes, then N lane bytes),
 *          PREFIX.marks.bin (per marked lane-segment: u32 run, u32 seg, u32 lane, then the lane's n_scratch x esz
 *          scratch at the segment's start - the boundary state before the mark - then its n_state x esz state after),
 *          PREFIX.open.txt (the open's stderr), PREFIX.prov.txt (the provenance), and on stdout one line a segment:
 *          "seg <run> <seg> flags 0x.. bus 0x.. call_ns <ns> marked <k> [lanes <i> ...]".
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
#define J_DUP _dup
#define J_DUP2 _dup2
#define J_CLOSE _close
#define J_FILENO _fileno
#else
#include <sched.h>
#include <time.h>
#include <unistd.h>
#define J_DUP dup
#define J_DUP2 dup2
#define J_CLOSE close
#define J_FILENO fileno
#endif
#include "cft.h"

static void die(const char *what) { fprintf(stderr, "j_run: %s\n", what); exit(2); }
static void die_st(const char *what, cft_status st)
{
    fprintf(stderr, "j_run: %s: %s (%d): %s\n", what, cft_strerror(st), (int)st, cft_last_error());
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
    if (!v) { fprintf(stderr, "j_run: %s is required\n", o); exit(2); }
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

/* (3) an output, hashed and counted as it is written */
typedef struct { FILE *f; Sha h; uint64_t bytes; } Out;
static void out_open(Out *o, const char *path)
{
    o->f = fopen(path, "wb");
    if (!o->f) { perror(path); die("cannot write the outputs"); }
    sha_init(&o->h);
    o->bytes = 0;
}
static void out_w(Out *o, const void *p, size_t n)
{
    if (n && fwrite(p, 1, n, o->f) != n) die("a write to an output failed");
    sha_add(&o->h, p, n);
    o->bytes += n;
}
static void out_close(Out *o, char hex[65])
{
    if (fflush(o->f) || ferror(o->f) || fclose(o->f)) die("an output could not be closed");
    o->f = NULL;
    sha_end(&o->h, hex);
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

/* ------------------------------------------------------------------ (2) the device's identity */
static char g_open_txt[8192];   /* what the open wrote on stderr */
static char g_line[2048];       /* the "cft hip: <artifact> = ..." line, or "" */
static char g_name[256];        /* the device's name from that line, or "" */
static cft_caps g_caps;

/* Open the device with stderr captured into PREFIX.open.txt; copy it to the real stderr; find the device's line. */
static cft_status open_captured(const char *artifact, unsigned depth, const char *prefix, cft_device **dev)
{
    char path[1024];
    snprintf(path, sizeof path, "%s.open.txt", prefix);
    FILE *cap = fopen(path, "w+b");
    if (!cap) { perror(path); die("cannot write the open's capture"); }
    fflush(stderr);
    int saved = J_DUP(2);
    if (saved < 0 || J_DUP2(J_FILENO(cap), 2) < 0) die("cannot capture stderr around the open");
    cft_open_args oa;
    memset(&oa, 0, sizeof oa);
    oa.struct_size = sizeof oa;
    oa.artifact = artifact;
    oa.scratch_depth = depth;
    cft_status st = cft_open_ex(&oa, dev);
    fflush(stderr);
    if (J_DUP2(saved, 2) < 0) die("cannot restore stderr after the open");
    J_CLOSE(saved);
    fflush(cap);
    long L = ftell(cap);
    if (L < 0) L = 0;
    if ((size_t)L >= sizeof g_open_txt) L = (long)sizeof g_open_txt - 1;
    rewind(cap);
    size_t got = fread(g_open_txt, 1, (size_t)L, cap);
    g_open_txt[got] = 0;
    fclose(cap);
    fputs(g_open_txt, stderr);
    fflush(stderr);
    g_line[0] = 0;
    g_name[0] = 0;
    if (artifact) {
        char head[300];
        snprintf(head, sizeof head, "cft hip: %s = ", artifact);
        const char *p = g_open_txt;
        while (p && *p) {
            const char *e = strchr(p, '\n');
            size_t n = e ? (size_t)(e - p) : strlen(p);
            if (n > strlen(head) && !strncmp(p, head, strlen(head))) {
                size_t k = n < sizeof g_line - 1 ? n : sizeof g_line - 1;
                memcpy(g_line, p, k);
                g_line[k] = 0;
                if (k && g_line[k - 1] == '\r') g_line[k - 1] = 0;
                const char *nm = g_line + strlen(head), *par = strstr(nm, " (");
                size_t m = par ? (size_t)(par - nm) : strlen(nm);
                if (m >= sizeof g_name) m = sizeof g_name - 1;
                memcpy(g_name, nm, m);
                g_name[m] = 0;
                break;
            }
            p = e ? e + 1 : NULL;
        }
    }
    return st;
}

/* After the open: the device line, the check against --expect-device (before any image loads), the caps. */
static void device_lines(cft_device *dev, const char *expect)
{
    printf("device %s\n", g_line[0] ? g_line : "none");
    fflush(stdout);
    if (expect && strcmp(g_name, expect)) {
        fprintf(stderr, "j_run: the device is \"%s\", not the expected \"%s\": stopped before any image loads\n",
                g_line[0] ? g_name : "(no device line: CFT_HIP_INFO=1 unset, or not a GPU handle)", expect);
        printf("DEVICE MISMATCH expected \"%s\" got \"%s\"\n", expect, g_name);
        fflush(stdout);
        exit(5);
    }
    memset(&g_caps, 0, sizeof g_caps);
    g_caps.struct_size = sizeof g_caps;
    cft_status st = cft_get_caps(dev, &g_caps);
    if (st != CFT_OK) die_st("cft_get_caps", st);
    printf("caps backend %s seq_features 0x%x max_scratch %u abi %u\n", g_caps.backend, g_caps.seq_features,
           g_caps.max_scratch, g_caps.abi_version);
    fflush(stdout);
}

static void prov_head(FILE *p, const char *mode, const char *artifact, unsigned depth)
{
    fprintf(p, "j_run provenance 1\nmode %s\nbuild_id %s\nartifact %s\ndevice %s\n", mode, cft_build_id(),
            artifact ? artifact : "none (the software executor)", g_line[0] ? g_line : "none");
    fprintf(p, "caps backend %s seq_features 0x%x max_scratch %u abi %u\ndepth %u\n", g_caps.backend,
            g_caps.seq_features, g_caps.max_scratch, g_caps.abi_version, depth);
}

static int mode_load(int argc, char **argv)
{
    const char *prefix = need(argc, argv, "--out"), *artifact = opt(argc, argv, "--artifact", NULL);
    const unsigned depth = (unsigned)strtoul(need(argc, argv, "--depth"), NULL, 10);
    cft_device *dev = NULL;
    cft_status st = open_captured(artifact, depth, prefix, &dev);
    if (st != CFT_OK) die_st("cft_open_ex", st);
    printf("j_run load build_id %s depth %u\n", cft_build_id(), depth);
    device_lines(dev, opt(argc, argv, "--expect-device", NULL));
    char path[1024];
    snprintf(path, sizeof path, "%s.prov.txt", prefix);
    FILE *pv = fopen(path, "wb");
    if (!pv) die("cannot write the provenance");
    prov_head(pv, "load", artifact, depth);
    int refused = 0, nimg = 0;
    for (int i = 1; i + 1 < argc; i++) {
        if (strcmp(argv[i], "--image")) continue;
        size_t len;
        uint8_t *img = slurp(argv[i + 1], &len);
        char sha[65];
        sha_mem(img, len, sha);
        cft_program *prog = NULL;
        st = cft_program_load(dev, img, len, &prog);
        nimg++;
        if (st != CFT_OK) {
            refused++;
            printf("load %s sha256 %s status %s (%d): %s\n", argv[i + 1], sha, cft_strerror(st), (int)st, cft_last_error());
            fprintf(pv, "load %s sha256 %s status %d\n", argv[i + 1], sha, (int)st);
        } else {
            cft_program_info info;
            memset(&info, 0, sizeof info);
            info.struct_size = sizeof info;
            st = cft_program_get_info(prog, &info);
            if (st != CFT_OK) die_st("cft_program_get_info", st);
            printf("load %s sha256 %s status CFT_OK insns %u consts %u scratch_in %u scratch_out %u scratch_used %u "
                   "esz %u\n", argv[i + 1], sha, info.n_insns, info.n_consts, info.n_scratch_in, info.n_scratch_out,
                   info.scratch_used, (unsigned)cft_format_size(info.format));
            fprintf(pv, "load %s sha256 %s status 0\n", argv[i + 1], sha);
            cft_program_free(prog);
        }
        fflush(stdout);
        free(img);
    }
    fprintf(pv, "images %d refused %d\nstatus DONE\n", nimg, refused);
    if (fclose(pv)) die("the provenance could not be closed");
    printf("REPORT images %d\nREPORT refused %d\nDONE\n", nimg, refused);
    fflush(stdout);
    cft_close(dev);
    return refused ? 3 : (nimg ? 0 : 2);
}

int main(int argc, char **argv)
{
    if (argc >= 2 && !strcmp(argv[1], "load"))
        return mode_load(argc, argv);
    if (argc < 2 || (strcmp(argv[1], "run") && strcmp(argv[1], "rate")))
        die("usage: j_run run|rate --image IMG --runs RUNS --init INIT --lanes N --depth D --out PREFIX [--artifact A] "
            "[--expect-device NAME] [--seg-steps S] [--keep-every N] [--warmup-lanes W] [--abort-ms M]; "
            "j_run load --image IMG [--image IMG ...] --depth D --out PREFIX [--artifact A] [--expect-device NAME]");
    const int rate = !strcmp(argv[1], "rate");
#ifdef _WIN32
    _setmode(0, _O_BINARY);
#endif
    const char *img_path = need(argc, argv, "--image"), *runs_path = need(argc, argv, "--runs"),
               *init_path = need(argc, argv, "--init"), *prefix = need(argc, argv, "--out");
    const size_t n = (size_t)strtoul(need(argc, argv, "--lanes"), NULL, 10);
    const unsigned depth = (unsigned)strtoul(need(argc, argv, "--depth"), NULL, 10);
    const char *artifact = opt(argc, argv, "--artifact", NULL), *expect = opt(argc, argv, "--expect-device", NULL),
               *seg_steps = opt(argc, argv, "--seg-steps", "unstated");
    const unsigned long keep_every = strtoul(opt(argc, argv, "--keep-every", "1"), NULL, 10);
    const size_t warm = (size_t)strtoul(opt(argc, argv, "--warmup-lanes", "0"), NULL, 10);
    const double abort_ms = strtod(opt(argc, argv, "--abort-ms", "0"), NULL);
    if (keep_every < 1) die("--keep-every is at least 1");
    if (warm > n) die("--warmup-lanes is at most --lanes");
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
    cft_status st = open_captured(artifact, depth, prefix, &dev);
    if (st != CFT_OK) die_st("cft_open_ex", st);
    printf("j_run %s build_id %s depth %u artifact %s seg_steps %s keep_every %lu warmup_lanes %lu abort_ms %g\n",
           argv[1], cft_build_id(), depth, artifact ? artifact : "none", seg_steps, keep_every, (unsigned long)warm,
           abort_ms);
    device_lines(dev, expect);
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
    uint8_t *acc = (uint8_t *)calloc(n ? n : 1, 1); /* (4) the lane bytes since the run's last record */
    if (!cur || !out || !A || !dep || !counts || !lf || !acc) die("out of memory");
    memcpy(cur, init, all_b);
    size_t nseg_all = 0;
    for (size_t r = 0; r < nruns; r++) nseg_all += rd32(R + off0 + r * run_rec);
    /* the per-segment records, kept in memory (written at the end in mode rate, as they come in mode run) */
    const size_t segrec = 8 + n * nst * esz + n;
    uint8_t *segs = rate ? (uint8_t *)malloc(nseg_all * segrec + 1) : NULL;
    char path[1024];
    Out fs, fm;
    memset(&fs, 0, sizeof fs);
    snprintf(path, sizeof path, "%s.seg.bin", prefix);
    if (!rate) out_open(&fs, path);
    snprintf(path, sizeof path, "%s.marks.bin", prefix);
    out_open(&fm, path);
    if (rate && !segs) die("cannot write the outputs");
    uint8_t *pre = (uint8_t *)malloc(all_b ? all_b : 1);
    unsigned long marks_total = 0;
    uint32_t flags_all = 0;

    /* (3) the calls' clock: the process's first call is the warm-up's, or the first segment's */
    unsigned long calls = 0, timed_calls = 0, records = 0;
    int64_t warm_ns = -1, timed_start = 0, timed_end = 0, call_max = 0, call_min = 0;
    int aborted = 0;
    char abort_txt[256] = "";
    if (warm) {
        /* one segment of the first W lanes at the first run's values, written as at a run's start; discarded */
        const uint8_t *rr = R + off0;
        const uint8_t *bank0 = rr + 8 + esz, *shv0 = rr + 8 + esz + ncon * esz;
        const size_t wb = warm * lane_b;
        uint8_t *wcur = (uint8_t *)malloc(wb), *wout = (uint8_t *)calloc(wb, 1), *wlf = (uint8_t *)calloc(warm, 1);
        uint8_t *wA = (uint8_t *)calloc(warm * esz, 1);
        uint8_t *wdep = (uint8_t *)calloc(warm * (size_t)info.max_deposits * esz + 1, 1);
        uint32_t *wcnt = (uint32_t *)calloc(warm, sizeof(uint32_t));
        if (!wcur || !wout || !wlf || !wA || !wdep || !wcnt || !nruns) die("the warm-up: out of memory, or no run");
        memcpy(wcur, init, wb);
        for (size_t l = 0; l < warm; l++)
            for (size_t i = 0; i < nsh; i++) memcpy(wcur + l * lane_b + (size_t)shslot[i] * esz, shv0 + i * esz, esz);
        uint32_t wflags = 0, wbus = 0;
        cft_run_args wa;
        memset(&wa, 0, sizeof wa);
        wa.struct_size = sizeof wa;
        wa.a = wA;
        wa.n = warm;
        wa.bank = bank0;
        wa.bank_bytes = ncon * esz;
        wa.scratch_in = wcur;
        wa.scratch_in_bytes = wb;
        wa.scratch_out = wout;
        wa.scratch_out_bytes = wb;
        wa.deposits = wdep;
        wa.counts = wcnt;
        wa.flags_out = &wflags;
        wa.bus_out = &wbus;
        wa.lane_flags = wlf;
        wa.lane_flags_bytes = warm;
        int64_t t0 = now_ns();
        st = cft_program_run_ex(prog, &wa);
        warm_ns = now_ns() - t0;
        if (st != CFT_OK) die_st("cft_program_run_ex (the warm-up)", st);
        calls++;
        printf("warmup lanes %lu call_ns %lld flags 0x%x bus 0x%x (discarded)\n", (unsigned long)warm, (long long)warm_ns,
               wflags, wbus);
        fflush(stdout);
        free(wcur); free(wout); free(wlf); free(wA); free(wdep); free(wcnt);
    }

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
    for (size_t r = 0; r < nruns && !aborted; r++) {
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
                fprintf(stderr, "j_run: run %lu lane %lu: t is not the run's start\n", (unsigned long)r, (unsigned long)l);
                exit(4);
            }
        }
        memset(acc, 0, n);
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
            const int64_t c0 = now_ns();
            st = cft_program_run_ex(prog, &ra);
            const int64_t c1 = now_ns(), cns = c1 - c0;
            if (st != CFT_OK) die_st("cft_program_run_ex", st);
            calls++;
            if (calls >= 2) {
                if (!timed_calls) {
                    timed_start = c0;
                    call_max = call_min = cns;
                }
                timed_calls++;
                timed_end = c1;
                if (cns > call_max) call_max = cns;
                if (cns < call_min) call_min = cns;
                if (abort_ms > 0 && (double)cns > abort_ms * 1e6) {
                    aborted = 1;
                    snprintf(abort_txt, sizeof abort_txt, "call %lu (run %lu segment %u) took %.1f ms, over %g ms", calls,
                             (unsigned long)r, s, cns / 1e6, abort_ms);
                }
            }
            flags_all |= flags;
            unsigned marked = 0;
            for (size_t l = 0; l < n; l++)
                if (lf[l] & 0x80) {
                    marked++;
                    uint32_t h3[3] = {(uint32_t)r, s, (uint32_t)l};
                    out_w(&fm, h3, 12);
                    out_w(&fm, pre + l * lane_b, lane_b);
                    out_w(&fm, out + l * lane_b, nst * esz);
                }
            marks_total += marked;
            for (size_t l = 0; l < n; l++) acc[l] |= lf[l];
            const int keep = (s % keep_every == 0) || s == nseg;
            uint32_t h2[2] = {(uint32_t)r, s};
            if (keep) {
                uint8_t *rec = rate ? segs + records * segrec : NULL;
                if (rate) {
                    memcpy(rec, h2, 8);
                    for (size_t l = 0; l < n; l++) memcpy(rec + 8 + l * nst * esz, out + l * lane_b, nst * esz);
                    memcpy(rec + 8 + n * nst * esz, acc, n);
                } else {
                    out_w(&fs, h2, 8);
                    for (size_t l = 0; l < n; l++) out_w(&fs, out + l * lane_b, nst * esz);
                    out_w(&fs, acc, n);
                }
                records++;
                memset(acc, 0, n);
            }
            if (!rate) {
                printf("seg %lu %u flags 0x%x bus 0x%x call_ns %lld marked %u", (unsigned long)r, s, flags, bus,
                       (long long)cns, marked);
                if (marked) {
                    printf(" lanes");
                    for (size_t l = 0; l < n; l++)
                        if (lf[l] & 0x80) printf(" %lu", (unsigned long)l);
                }
                printf("\n");
            }
            segk++;
            memcpy(cur, out, all_b); /* the whole lane is carried: state and lane params */
            if (aborted) break;
        }
    }
    int64_t t_end = 0, c_end = 0;
    int cpu_end = -1;
    char sha_seg[65] = "", sha_marks[65] = "";
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
        out_open(&fs, path);
        out_w(&fs, segs, records * segrec);
    }
    out_close(&fs, sha_seg);
    out_close(&fm, sha_marks);
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
    printf("REPORT records %lu\nREPORT calls %lu\nREPORT timed_calls %lu\nREPORT timed_start_ns %lld\n"
           "REPORT timed_end_ns %lld\nREPORT call_max_ns %lld\nREPORT call_min_ns %lld\nREPORT warmup_ns %lld\n",
           records, calls, timed_calls, (long long)timed_start, (long long)timed_end, (long long)call_max,
           (long long)call_min, (long long)warm_ns);
    printf("REPORT seg_sha256 %s\nREPORT marks_sha256 %s\n", sha_seg, sha_marks);
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
    /* (3) the provenance */
    snprintf(path, sizeof path, "%s.prov.txt", prefix);
    FILE *pv = fopen(path, "wb");
    if (!pv) die("cannot write the provenance");
    prov_head(pv, argv[1], artifact, depth);
    fprintf(pv, "seg_steps %s\nkeep_every %lu\nwarmup_lanes %lu\nabort_ms %g\n", seg_steps, keep_every,
            (unsigned long)warm, abort_ms);
    fprintf(pv, "image %s sha256 %s insns %u consts %u scratch_in %u scratch_out %u scratch_used %u esz %u\n", img_path,
            sha_img, info.n_insns, info.n_consts, info.n_scratch_in, info.n_scratch_out, info.scratch_used,
            (unsigned)esz);
    fprintf(pv, "runs %s sha256 %s nruns %lu shared %lu\ninit %s sha256 %s lanes %lu\n", runs_path, sha_runs,
            (unsigned long)nruns, (unsigned long)nsh, init_path, sha_init_, (unsigned long)n);
    fprintf(pv, "out %s.seg.bin sha256 %s bytes %llu\nout %s.marks.bin sha256 %s bytes %llu\n", prefix, sha_seg,
            (unsigned long long)fs.bytes, prefix, sha_marks, (unsigned long long)fm.bytes);
    {
        char sha_open[65];
        sha_mem(g_open_txt, strlen(g_open_txt), sha_open);
        fprintf(pv, "out %s.open.txt sha256 %s bytes %lu\n", prefix, sha_open, (unsigned long)strlen(g_open_txt));
    }
    fprintf(pv, "segments %lu records %lu marks %lu flags 0x%x calls %lu timed_calls %lu\nfinal_states_sha256 %s\n",
            (unsigned long)segk, records, marks_total, flags_all, calls, timed_calls, sha_final);
    fprintf(pv, "timed_start_ns %lld timed_end_ns %lld call_max_ns %lld call_min_ns %lld warmup_ns %lld\n",
            (long long)timed_start, (long long)timed_end, (long long)call_max, (long long)call_min, (long long)warm_ns);
    if (aborted)
        fprintf(pv, "status ABORTED %s\n", abort_txt);
    else
        fprintf(pv, "status DONE\n");
    if (fclose(pv)) die("the provenance could not be closed");
    if (aborted) {
        printf("ABORT %s\n", abort_txt);
        fflush(stdout);
        fprintf(stderr, "j_run: ABORT %s\n", abort_txt);
        cft_program_free(prog);
        cft_close(dev);
        return 6;
    }
    printf("DONE\n");
    fflush(stdout);
    cft_program_free(prog);
    cft_close(dev);
    return 0;
}
