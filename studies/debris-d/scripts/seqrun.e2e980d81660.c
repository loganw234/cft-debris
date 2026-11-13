/* seqrun.c - DEBRIS-D's own driver (cft-debris, MIT): run a cftc image on
 * libcft's software backend, cft_open(NULL, ...), segment by segment, and
 * write what each segment left in the lanes.
 *
 *   seqrun <image.cftp> <bank|-> <scratch_in.bin> <n> <segments> <out_prefix>
 *          [--time R]
 *
 * Every segment is one cft_program_run_ex of the image (the image's own
 * REPEAT count is the segment's steps). Segment k+1 starts from segment
 * k's scratch_out: a lane's first min(n_scratch_in, n_scratch_out) slots
 * are carried, the rest of its scratch_in (its lane params) kept.
 * Written per segment k (1-based):
 *   <out_prefix>.seg<k>.bin    the scratch_out block, lane-major, raw
 *   <out_prefix>.seg<k>.lanes  the n lane bytes (R23): [4:0] IEEE flags,
 *                              [5] deposit overflow, [6] strict range,
 *                              [7] the mark
 * and one line on stdout:
 *   seg <k> flags 0x<flags_out> bus 0x<bus_out> marked <count> lanes <hex>
 *
 * --time R: after the segments, run segment 1's input R times (not
 * chained), timing the R runs with QueryPerformanceCounter, and fold
 * every run's scratch_out into a printed checksum; then time the same
 * fold alone over the same bytes R times (the control loop, with the run
 * removed). Prints
 *   time runs <R> seconds <t_run> fold_only_seconds <t_fold> checksum <x>
 * Rates are computed by the caller from the image's manifest.
 */
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <windows.h>

#include "cft.h"

static void die(const char *what) { fprintf(stderr, "seqrun: %s\n", what); exit(2); }

static void die_st(const char *what, cft_status st)
{
    fprintf(stderr, "seqrun: %s: %s (%d)\n", what, cft_strerror(st), (int)st);
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

static void spill(const char *path, const void *p, size_t len)
{
    FILE *f = fopen(path, "wb");
    if (!f) { perror(path); exit(2); }
    if (len && fwrite(p, 1, len, f) != len) die("short write");
    fclose(f);
}

static uint64_t fold(const uint8_t *p, size_t len, uint64_t x)
{
    for (size_t i = 0; i + 8 <= len; i += 8) {
        uint64_t w;
        memcpy(&w, p + i, 8);
        x = (x ^ w) * 0x100000001b3ULL;
    }
    return x;
}

int main(int argc, char **argv)
{
    if (argc < 7)
        die("usage: seqrun <image.cftp> <bank|-> <scratch_in.bin> <n> <segments> <out_prefix> [--time R]");
    const char *img_path = argv[1], *bank_path = argv[2], *sin_path = argv[3];
    size_t n = (size_t)strtoul(argv[4], NULL, 10);
    int segments = atoi(argv[5]);
    const char *prefix = argv[6];
    long timeR = 0;
    if (argc >= 9 && !strcmp(argv[7], "--time")) timeR = atol(argv[8]);

    size_t img_bytes, bank_bytes = 0, sin_bytes;
    uint8_t *img = slurp(img_path, &img_bytes);
    uint8_t *bank = NULL;
    if (strcmp(bank_path, "-")) bank = slurp(bank_path, &bank_bytes);
    uint8_t *sin0 = slurp(sin_path, &sin_bytes);

    cft_device *dev = NULL;
    cft_status st = cft_open(NULL, 0, &dev);
    if (st != CFT_OK) die_st("cft_open", st);
    cft_program *prog = NULL;
    st = cft_program_load(dev, img, img_bytes, &prog);
    if (st != CFT_OK) die_st("cft_program_load", st);
    cft_program_info info;
    memset(&info, 0, sizeof info);
    info.struct_size = sizeof info;
    st = cft_program_get_info(prog, &info);
    if (st != CFT_OK) die_st("cft_program_get_info", st);
    size_t esz = cft_format_size(info.format);
    printf("build_id %s\n", cft_build_id());
    printf("image %s insns %u consts %u scratch_in %u scratch_out %u scratch_used %u esz %u deposits %u\n",
           img_path, info.n_insns, info.n_consts, info.n_scratch_in, info.n_scratch_out,
           info.scratch_used, (unsigned)esz, info.max_deposits);
    size_t in_bytes = n * info.n_scratch_in * esz, out_bytes = n * info.n_scratch_out * esz;
    if (sin_bytes != in_bytes) die("scratch_in is not n * n_scratch_in elements");

    uint8_t *A = (uint8_t *)calloc(n ? n * esz : 1, 1);
    size_t dep_bytes = n * (size_t)info.max_deposits * esz;
    uint8_t *dep = (uint8_t *)calloc(dep_bytes ? dep_bytes : 1, 1);
    uint32_t *counts = (uint32_t *)calloc(n ? n : 1, sizeof(uint32_t));
    uint8_t *cur = (uint8_t *)malloc(in_bytes ? in_bytes : 1);
    uint8_t *out = (uint8_t *)calloc(out_bytes ? out_bytes : 1, 1);
    uint8_t *lf = (uint8_t *)calloc(n ? n : 1, 1);
    if (!A || !dep || !counts || !cur || !out || !lf) die("out of memory");
    memcpy(cur, sin0, in_bytes);
    size_t carry = info.n_scratch_in < info.n_scratch_out ? info.n_scratch_in : info.n_scratch_out;

    for (int k = 1; k <= segments; k++) {
        uint32_t flags = 0, bus = 0;
        cft_run_args ra;
        memset(&ra, 0, sizeof ra);
        ra.struct_size = sizeof ra;
        ra.a = A;
        ra.n = n;
        ra.bank = bank;
        ra.bank_bytes = bank ? bank_bytes : 0;
        ra.scratch_in = cur;
        ra.scratch_in_bytes = in_bytes;
        ra.scratch_out = out;
        ra.scratch_out_bytes = out_bytes;
        ra.deposits = dep;
        ra.counts = counts;
        ra.flags_out = &flags;
        ra.bus_out = &bus;
        ra.lane_flags = lf;
        ra.lane_flags_bytes = n;
        st = cft_program_run_ex(prog, &ra);
        if (st != CFT_OK) die_st("cft_program_run_ex", st);
        char path[1024];
        snprintf(path, sizeof path, "%s.seg%d.bin", prefix, k);
        spill(path, out, out_bytes);
        snprintf(path, sizeof path, "%s.seg%d.lanes", prefix, k);
        spill(path, lf, n);
        unsigned marked = 0;
        for (size_t i = 0; i < n; i++) marked += (lf[i] >> 7) & 1u;
        printf("seg %d flags 0x%x bus 0x%x marked %u lanes ", k, flags, bus, marked);
        for (size_t i = 0; i < n; i++) printf("%02x", lf[i]);
        printf("\n");
        for (size_t i = 0; i < n; i++)
            memcpy(cur + i * info.n_scratch_in * esz, out + i * info.n_scratch_out * esz, carry * esz);
    }

    if (timeR > 0) {
        LARGE_INTEGER f, t0, t1, t2, t3;
        QueryPerformanceFrequency(&f);
        uint64_t x = 0xcbf29ce484222325ULL;
        memcpy(cur, sin0, in_bytes);
        QueryPerformanceCounter(&t0);
        for (long r = 0; r < timeR; r++) {
            uint32_t flags = 0, bus = 0;
            cft_run_args ra;
            memset(&ra, 0, sizeof ra);
            ra.struct_size = sizeof ra;
            ra.a = A;
            ra.n = n;
            ra.bank = bank;
            ra.bank_bytes = bank ? bank_bytes : 0;
            ra.scratch_in = cur;
            ra.scratch_in_bytes = in_bytes;
            ra.scratch_out = out;
            ra.scratch_out_bytes = out_bytes;
            ra.deposits = dep;
            ra.counts = counts;
            ra.flags_out = &flags;
            ra.bus_out = &bus;
            ra.lane_flags = lf;
            ra.lane_flags_bytes = n;
            st = cft_program_run_ex(prog, &ra);
            if (st != CFT_OK) die_st("cft_program_run_ex", st);
            x = fold(out, out_bytes, x ^ (uint64_t)flags);
        }
        QueryPerformanceCounter(&t1);
        uint64_t y = 0xcbf29ce484222325ULL;
        QueryPerformanceCounter(&t2);
        for (long r = 0; r < timeR; r++) {
            out[r % (out_bytes ? out_bytes : 1)] ^= (uint8_t)r; /* keep the fold from being hoisted */
            y = fold(out, out_bytes, y ^ (uint64_t)r);
        }
        QueryPerformanceCounter(&t3);
        double tr = (double)(t1.QuadPart - t0.QuadPart) / (double)f.QuadPart;
        double tf = (double)(t3.QuadPart - t2.QuadPart) / (double)f.QuadPart;
        printf("time runs %ld seconds %.6f fold_only_seconds %.6f checksum %016llx fold_checksum %016llx\n",
               timeR, tr, tf, (unsigned long long)x, (unsigned long long)y);
    }
    cft_program_free(prog);
    cft_close(dev);
    return 0;
}
