/* fmacheck.c - cft-debris, DEBRIS-E's E1 finding on this host's fma: the C
 * library's routine (built without -mfma) and the instruction (built with
 * -mfma), each beside libcft's CFT_FMA and beside the unfused a*b + c (two
 * roundings: the negative control, which an exact checker must report wrong).
 *
 * cft-debris, MIT licence (see LICENSE at the repository root). Written by
 * DEBRIS-E, 2026-11-13. The cases are the lead's (cft-debris-ledger\tools\
 * fmacheck\fmacheck.c, sha256 7e8c06da...f9fe80): the same seeded xorshift64
 * and the same formulas, so the same 20,000 cases.
 *
 *   fmacheck [n]   prints, a case a line: a b c fma(a,b,c) a*b+c CFT_FMA(a,b,c)
 *                  as C99 hex doubles (tests/e1_fma.py checks them exactly).
 * Built -std=c11 -O2 -ffp-contract=off, once without -mfma and once with it.
 */
#define __USE_MINGW_ANSI_STDIO 1
#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include "cft.h"

static uint64_t s = 0x9E3779B97F4A7C15ull;
static uint64_t next(void)
{
    s ^= s << 13;
    s ^= s >> 7;
    s ^= s << 17;
    return s;
}
static double mant(void) { return 1.0 + (double)(next() >> 12) * 0x1p-52; } /* [1, 2) */

int main(int argc, char **argv)
{
    long n = argc > 1 ? atol(argv[1]) : 20000;
    double *a = malloc(n * sizeof(double)), *b = malloc(n * sizeof(double)), *c = malloc(n * sizeof(double));
    double *r = malloc(n * sizeof(double)), *u = malloc(n * sizeof(double)), *x = malloc(n * sizeof(double));
    if (!a || !b || !c || !r || !u || !x) return 2;
    for (long i = 0; i < n; i++) {
        a[i] = mant();
        b[i] = mant();
        c[i] = mant() * ldexp(1.0, -(int)(next() % 40) - 1);
        if (next() & 1) c[i] = -c[i];
        r[i] = fma(a[i], b[i], c[i]);
        u[i] = a[i] * b[i] + c[i];
    }
    cft_device *dev = NULL;
    uint32_t fl = 0;
    if (cft_open(NULL, 0, &dev) != CFT_OK) return 3;
    if (cft_run(dev, CFT_FMA, CFT_FP64, CFT_RNE, a, b, c, x, (size_t)n, &fl, NULL) != CFT_OK) return 4;
    cft_close(dev);
#ifdef __FMA__
    printf("# fmacheck built with __FMA__ (the instruction)\n");
#else
    printf("# fmacheck built without __FMA__ (the C library's routine)\n");
#endif
    for (long i = 0; i < n; i++) printf("%a %a %a %a %a %a\n", a[i], b[i], c[i], r[i], u[i], x[i]);
    return 0;
}
