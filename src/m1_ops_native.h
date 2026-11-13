/* m1_ops_native.h - cft-debris M1: the number layer for the native kinds.
 *
 * cft-debris, MIT licence (see LICENSE at the repository root). Written by
 * DEBRIS-E, 2026-11-13. Included once per native kind by m1_kind.h, with
 * K_BITS 32 or 64 and K_REAL float or double.
 *
 * Exact IEEE arithmetic, one operation one rounding, as libcft computes it:
 *   - the build passes -ffp-contract=off (no implicit fusion), no -ffast-math,
 *     and -mfma; FLT_EVAL_METHOD must be 0 (checked below);
 *   - every fused multiply-add is written through _mm_fmadd_sd / _mm_fmadd_ss,
 *     which emit vfmadd at every optimisation level (a plain fma() call is the
 *     C library's routine at -O0, and that routine is not correctly rounded on
 *     this host: DEBRIS-E's plan, decision 3);
 *   - square root through _mm_sqrt_sd / _mm_sqrt_ss, the instruction;
 *   - exp, sin, cos, asin and acos are the C library's, or libcft's correctly
 *     rounded host functions when c->cr_transc is set (E1's and E2's control).
 * Every operation acts on n lanes; an operand whose scalar-mask bit is set is
 * one element applied to every lane.
 * The compound operations (ab_p_ce, ab_m_ce, dot3) are written as ONE C
 * expression a lane, so that a build with -ffp-contract=fast can fuse them
 * (E8's control); with contraction off they round exactly as the cft kinds'
 * separate calls do.
 */
#include <immintrin.h>
#include <float.h>
#include <math.h>
#include <string.h>
#include <stdlib.h>
#include <errno.h>

#if !defined(FLT_EVAL_METHOD) || FLT_EVAL_METHOD != 0
#error "M1's native kinds need FLT_EVAL_METHOD == 0"
#endif
#ifndef __FMA__
#error "M1's native kinds are built with -mfma (decision 3)"
#endif
#ifdef __FAST_MATH__
#error "M1 is never built with -ffast-math"
#endif

typedef K_REAL KR;

#if K_BITS == 64
#define K_CFTFMT CFT_FP64
static inline KR k_fma1(KR a, KR b, KR e)
{
    return _mm_cvtsd_f64(_mm_fmadd_sd(_mm_set_sd(a), _mm_set_sd(b), _mm_set_sd(e)));
}
static inline KR k_sqrt1(KR a)
{
    __m128d x = _mm_set_sd(a);
    return _mm_cvtsd_f64(_mm_sqrt_sd(x, x));
}
#define K_LIBM(f) f
#define K_STRTO(s, e) strtod((s), (e))
#else
#define K_CFTFMT CFT_FP32
static inline KR k_fma1(KR a, KR b, KR e)
{
    return _mm_cvtss_f32(_mm_fmadd_ss(_mm_set_ss(a), _mm_set_ss(b), _mm_set_ss(e)));
}
static inline KR k_sqrt1(KR a)
{
    __m128 x = _mm_set_ss(a);
    return _mm_cvtss_f32(_mm_sqrt_ss(x));
}
#define K_LIBM(fn) fn##f
#define K_STRTO(s, e) strtof((s), (e))
#endif

#define K_STRIDE(sm, bit) (((sm) & (bit)) ? (size_t)0 : (size_t)1)

static void k_ck(cft_status st, const char *what)
{
    if (st != CFT_OK) m1_die("libcft %s: %s (%s)", what, cft_strerror(st), cft_last_error());
}

static void k_add(m1_ctx *c, KR *d, const KR *a, const KR *b, size_t n, unsigned sm)
{
    const size_t sa = K_STRIDE(sm, M1_S1), sb = K_STRIDE(sm, M1_S2);
    c->nops[M1_OP_ADD] += n;
    for (size_t i = 0; i < n; i++) d[i] = a[i * sa] + b[i * sb];
}
static void k_sub(m1_ctx *c, KR *d, const KR *a, const KR *b, size_t n, unsigned sm)
{
    const size_t sa = K_STRIDE(sm, M1_S1), sb = K_STRIDE(sm, M1_S2);
    c->nops[M1_OP_SUB] += n;
    for (size_t i = 0; i < n; i++) d[i] = a[i * sa] - b[i * sb];
}
static void k_mul(m1_ctx *c, KR *d, const KR *a, const KR *b, size_t n, unsigned sm)
{
    const size_t sa = K_STRIDE(sm, M1_S1), sb = K_STRIDE(sm, M1_S2);
    c->nops[M1_OP_MUL] += n;
    for (size_t i = 0; i < n; i++) d[i] = a[i * sa] * b[i * sb];
}
static void k_div(m1_ctx *c, KR *d, const KR *a, const KR *b, size_t n, unsigned sm)
{
    const size_t sa = K_STRIDE(sm, M1_S1), sb = K_STRIDE(sm, M1_S2);
    c->nops[M1_OP_DIV] += n;
    for (size_t i = 0; i < n; i++) d[i] = a[i * sa] / b[i * sb];
}
static void k_fma(m1_ctx *c, KR *d, const KR *a, const KR *b, const KR *e, size_t n, unsigned sm)
{
    const size_t sa = K_STRIDE(sm, M1_S1), sb = K_STRIDE(sm, M1_S2), se = K_STRIDE(sm, M1_S3);
    c->nops[M1_OP_FMA] += n;
    for (size_t i = 0; i < n; i++) d[i] = k_fma1(a[i * sa], b[i * sb], e[i * se]);
}
static void k_sqrt(m1_ctx *c, KR *d, const KR *a, size_t n)
{
    c->nops[M1_OP_SQRT] += n;
    for (size_t i = 0; i < n; i++) d[i] = k_sqrt1(a[i]);
}
static void k_neg(m1_ctx *c, KR *d, const KR *a, size_t n)
{
    c->nops[M1_OP_NEG] += n;
    for (size_t i = 0; i < n; i++) d[i] = -a[i];
}
/* predicates: 1 or +0, as libcft's CFT_CMPLT and CFT_CMPLE */
static void k_cmplt(m1_ctx *c, KR *d, const KR *a, const KR *b, size_t n, unsigned sm)
{
    const size_t sa = K_STRIDE(sm, M1_S1), sb = K_STRIDE(sm, M1_S2);
    c->nops[M1_OP_CMP] += n;
    for (size_t i = 0; i < n; i++) d[i] = (a[i * sa] < b[i * sb]) ? (KR)1 : (KR)0;
}
static void k_cmple(m1_ctx *c, KR *d, const KR *a, const KR *b, size_t n, unsigned sm)
{
    const size_t sa = K_STRIDE(sm, M1_S1), sb = K_STRIDE(sm, M1_S2);
    c->nops[M1_OP_CMP] += n;
    for (size_t i = 0; i < n; i++) d[i] = (a[i * sa] <= b[i * sb]) ? (KR)1 : (KR)0;
}
/* d = cond != 0 ? a : b (bits moved intact) */
static void k_select(m1_ctx *c, KR *d, const KR *cond, const KR *a, const KR *b, size_t n, unsigned sm)
{
    const size_t sc = K_STRIDE(sm, M1_S1), sa = K_STRIDE(sm, M1_S2), sb = K_STRIDE(sm, M1_S3);
    c->nops[M1_OP_SEL] += n;
    for (size_t i = 0; i < n; i++) {
        KR x = (cond[i * sc] != (KR)0) ? a[i * sa] : b[i * sb];
        memcpy(&d[i], &x, sizeof(KR));
    }
}

/* the compound operations: one expression a lane (see the header comment) */
static void k_ab_p_ce(m1_ctx *c, KR *d, const KR *a, const KR *b, const KR *e, const KR *f, size_t n, unsigned sm)
{
    const size_t sa = K_STRIDE(sm, M1_S1), sb = K_STRIDE(sm, M1_S2), se = K_STRIDE(sm, M1_S3), sf = K_STRIDE(sm, M1_S4);
    c->nops[M1_OP_MUL] += 2 * n;
    c->nops[M1_OP_ADD] += n;
    for (size_t i = 0; i < n; i++) d[i] = a[i * sa] * b[i * sb] + e[i * se] * f[i * sf];
}
static void k_ab_m_ce(m1_ctx *c, KR *d, const KR *a, const KR *b, const KR *e, const KR *f, size_t n, unsigned sm)
{
    const size_t sa = K_STRIDE(sm, M1_S1), sb = K_STRIDE(sm, M1_S2), se = K_STRIDE(sm, M1_S3), sf = K_STRIDE(sm, M1_S4);
    c->nops[M1_OP_MUL] += 2 * n;
    c->nops[M1_OP_SUB] += n;
    for (size_t i = 0; i < n; i++) d[i] = a[i * sa] * b[i * sb] - e[i * se] * f[i * sf];
}
/* (x0 y0 + x1 y1) + x2 y2, all vectors */
static void k_dot3(m1_ctx *c, KR *d, const KR *x0, const KR *x1, const KR *x2, const KR *y0, const KR *y1,
                   const KR *y2, size_t n)
{
    c->nops[M1_OP_MUL] += 3 * n;
    c->nops[M1_OP_ADD] += 2 * n;
    for (size_t i = 0; i < n; i++) d[i] = x0[i] * y0[i] + x1[i] * y1[i] + x2[i] * y2[i];
}

/* the transcendentals: the C library's, or libcft's (c->cr_transc) */
#define K_TRANSC(fname, cftfn, opc)                                                         \
    static void k_##fname(m1_ctx *c, KR *d, const KR *a, size_t n)                          \
    {                                                                                       \
        c->nops[opc] += n;                                                                  \
        if (c->cr_transc) {                                                                 \
            uint32_t fl = 0;                                                                \
            k_ck(cftfn(c->dev, K_CFTFMT, CFT_RNE, a, d, n, &fl), #cftfn);                  \
            c->cft_flags |= fl;                                                             \
        } else {                                                                            \
            for (size_t i = 0; i < n; i++) d[i] = K_LIBM(fname)(a[i]);                      \
        }                                                                                   \
    }
K_TRANSC(exp, cft_exp, M1_OP_EXP)
K_TRANSC(sin, cft_sin, M1_OP_SIN)
K_TRANSC(cos, cft_cos, M1_OP_COS)
K_TRANSC(asin, cft_asin, M1_OP_ASIN)
K_TRANSC(acos, cft_acos, M1_OP_ACOS)

/* conversions into the kind: from binary64 (C's conversion, round to nearest
   even; exact for native64), from decimal (the C library's strtod / strtof),
   from integers (C's conversion, one rounding) */
static void k_from_f64(m1_ctx *c, KR *d, const double *s, size_t n)
{
    c->nops[M1_OP_CVT] += n;
    for (size_t i = 0; i < n; i++) d[i] = (KR)s[i];
}
static void k_from_dec(m1_ctx *c, KR *d, const char *const *s, size_t n)
{
    c->nops[M1_OP_CVT] += n;
    for (size_t i = 0; i < n; i++) {
        char *end = NULL;
        errno = 0;
        d[i] = K_STRTO(s[i], &end);
        if (end == s[i] || *end != '\0') m1_die("decimal conversion stopped short in \"%s\"", s[i]);
    }
}
static void k_from_i64(m1_ctx *c, KR *d, const int64_t *s, size_t n)
{
    c->nops[M1_OP_CVT] += n;
    for (size_t i = 0; i < n; i++) d[i] = (KR)s[i];
}
static void k_to_f64(m1_ctx *c, double *d, const KR *s, size_t n)
{
    (void)c;
    for (size_t i = 0; i < n; i++) d[i] = (double)s[i];
}
/* E3's planted control applies to the cft kinds; for a native kind it is a no-op */
static void k_round64(m1_ctx *c, KR *d, size_t n)
{
    (void)c;
    (void)d;
    (void)n;
}
static void k_ops_check(m1_ctx *c)
{
    (void)c;
    __builtin_cpu_init();
    if (!__builtin_cpu_supports("fma")) m1_die("this CPU has no FMA3; the native kinds need it (decision 3)");
}
