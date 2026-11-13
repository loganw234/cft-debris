/* opbench.c - DEBRIS-D's own driver (cft-debris, MIT): time one libcft
 * host operation on the software backend, cft_open(NULL, ...), and write
 * its results for an outside check.
 *
 *   opbench <op> <fp64|fp128|fp256> <args.bin> <n> <min_seconds> <out.bin>
 *
 * op: add mul fma div sqrt exp log pow sin cos atan2
 * args.bin holds n elements of a, then (for add, mul, fma, div, pow,
 * atan2) n of b, then (fma) n of c, little-endian, the format's width.
 * For atan2 the first operand is y and the second x (cft_atan2(a=y, b=x)).
 *
 * 1. one call over the n arguments; its results go to out.bin, its flags
 *    to stdout;
 * 2. the timed loop: calls over the same n arguments, repeated until
 *    min_seconds have passed (at least 3 calls), every result folded into
 *    a printed checksum; then
 * 3. the control loop: the same fold, the same number of times, with the
 *    operation removed.
 * Prints:  op <op> fmt <fmt> n <n> calls <R> seconds <t> ns_per_element
 *          <x> fold_only_seconds <tf> ratio <t/tf> checksum <c> flags 0x<f>
 */
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <windows.h>

#include "cft.h"

static void die(const char *w) { fprintf(stderr, "opbench: %s\n", w); exit(2); }

static uint64_t fold(const uint8_t *p, size_t len, uint64_t x)
{
    for (size_t i = 0; i + 8 <= len; i += 8) {
        uint64_t w;
        memcpy(&w, p + i, 8);
        x = (x ^ w) * 0x100000001b3ULL;
    }
    return x;
}

static double now(void)
{
    LARGE_INTEGER f, t;
    QueryPerformanceFrequency(&f);
    QueryPerformanceCounter(&t);
    return (double)t.QuadPart / (double)f.QuadPart;
}

static cft_status call(cft_device *dev, const char *op, cft_format fmt, const uint8_t *a,
                       const uint8_t *b, const uint8_t *c, uint8_t *d, size_t n, uint32_t *fl)
{
    uint32_t bus = 0;
    /* cft.h: CFT_ADD is d = a + c (b ignored), CFT_MUL d = a * b, CFT_FMA d = a*b + c */
    if (!strcmp(op, "add")) return cft_run(dev, CFT_ADD, fmt, CFT_RNE, a, NULL, b, d, n, fl, &bus);
    if (!strcmp(op, "mul")) return cft_run(dev, CFT_MUL, fmt, CFT_RNE, a, b, NULL, d, n, fl, &bus);
    if (!strcmp(op, "fma")) return cft_run(dev, CFT_FMA, fmt, CFT_RNE, a, b, c, d, n, fl, &bus);
    if (!strcmp(op, "div")) return cft_div(dev, fmt, CFT_RNE, a, b, d, n, fl, &bus);
    if (!strcmp(op, "sqrt")) return cft_sqrt(dev, fmt, CFT_RNE, a, d, n, fl, &bus);
    if (!strcmp(op, "exp")) return cft_exp(dev, fmt, CFT_RNE, a, d, n, fl);
    if (!strcmp(op, "log")) return cft_log(dev, fmt, CFT_RNE, a, d, n, fl);
    if (!strcmp(op, "pow")) return cft_pow(dev, fmt, CFT_RNE, a, b, d, n, fl);
    if (!strcmp(op, "sin")) return cft_sin(dev, fmt, CFT_RNE, a, d, n, fl);
    if (!strcmp(op, "cos")) return cft_cos(dev, fmt, CFT_RNE, a, d, n, fl);
    if (!strcmp(op, "atan2")) return cft_atan2(dev, fmt, CFT_RNE, a, b, d, n, fl);
    die("unknown op");
    return CFT_OK;
}

int main(int argc, char **argv)
{
    if (argc != 7) die("usage: opbench <op> <fmt> <args.bin> <n> <min_seconds> <out.bin>");
    const char *op = argv[1];
    cft_format fmt = !strcmp(argv[2], "fp64") ? CFT_FP64 : !strcmp(argv[2], "fp128") ? CFT_FP128
                   : !strcmp(argv[2], "fp256") ? CFT_FP256 : (cft_format)-1;
    if ((int)fmt < 0) die("format");
    size_t n = (size_t)strtoul(argv[4], NULL, 10);
    double mins = atof(argv[5]);
    size_t esz = cft_format_size(fmt);
    int nin = (!strcmp(op, "fma")) ? 3 : (!strcmp(op, "sqrt") || !strcmp(op, "exp") || !strcmp(op, "log")
              || !strcmp(op, "sin") || !strcmp(op, "cos")) ? 1 : 2;
    FILE *f = fopen(argv[3], "rb");
    if (!f) die("args");
    uint8_t *buf = (uint8_t *)malloc(n * esz * 3 + 8);
    if (fread(buf, 1, n * esz * nin, f) != n * esz * nin) die("short args file");
    fclose(f);
    const uint8_t *a = buf, *b = nin > 1 ? buf + n * esz : NULL, *c = nin > 2 ? buf + 2 * n * esz : NULL;
    uint8_t *d = (uint8_t *)calloc(n * esz + 8, 1);
    cft_device *dev = NULL;
    cft_status st = cft_open(NULL, 0, &dev);
    if (st != CFT_OK) die("cft_open");
    uint32_t flags = 0;
    st = call(dev, op, fmt, a, b, c, d, n, &flags);
    if (st != CFT_OK) { fprintf(stderr, "opbench: %s: %s\n", op, cft_strerror(st)); return 2; }
    FILE *o = fopen(argv[6], "wb");
    if (!o) die("out");
    fwrite(d, 1, n * esz, o);
    fclose(o);
    uint64_t x = 0xcbf29ce484222325ULL;
    long R = 0;
    double t0 = now(), t1;
    do {
        uint32_t fl = 0;
        st = call(dev, op, fmt, a, b, c, d, n, &fl);
        if (st != CFT_OK) die("timed call");
        x = fold(d, n * esz, x ^ fl);
        R++;
        t1 = now();
    } while (t1 - t0 < mins || R < 3);
    uint64_t y = 0xcbf29ce484222325ULL;
    double t2 = now();
    for (long r = 0; r < R; r++) {
        d[(size_t)r % (n * esz)] ^= (uint8_t)r;
        y = fold(d, n * esz, y ^ (uint64_t)r);
    }
    double t3 = now();
    double tr = t1 - t0, tf = t3 - t2;
    printf("op %s fmt %s n %lu calls %ld seconds %.6f ns_per_element %.2f fold_only_seconds %.6f ratio %.1f "
           "checksum %016llx fold %016llx flags 0x%x build_id %s\n",
           op, argv[2], (unsigned long)n, R, tr, tr / ((double)R * (double)n) * 1e9, tf,
           tf > 0 ? tr / tf : 1e30, (unsigned long long)x, (unsigned long long)y, flags, cft_build_id());
    cft_close(dev);
    return 0;
}
