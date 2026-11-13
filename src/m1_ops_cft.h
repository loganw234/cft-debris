/* m1_ops_cft.h - cft-debris M1: the number layer for the cft kinds.
 *
 * cft-debris, MIT licence (see LICENSE at the repository root). Written by
 * DEBRIS-E, 2026-11-13. Included once per cft kind by m1_kind.h, with K_ESZ
 * the element size and K_CFTFMT the libcft format.
 *
 * Every operation is one call of libcft's host API on the software backend
 * (cft_open(NULL, ...)), over all n lanes at once, round to nearest even:
 *   cft_run_ex with CFT_ADD, CFT_SUB, CFT_MUL, CFT_FMA, CFT_NEG, CFT_CMPLT,
 *   CFT_CMPLE and CFT_SELECT (a scalar operand rides as cft_elem_args's
 *   scalar_mask); cft_div and cft_sqrt (scalars expanded first); cft_exp,
 *   cft_sin, cft_cos, cft_asin and cft_acos (correctly rounded);
 *   cft_convert, cft_from_decimal_char and cft_cvt_from_i64 for conversions.
 * libcft is linked from a build outside the repository; its header is reached
 * by an include path. No libcft source is copied here.
 */
#include <string.h>
#include <stdlib.h>

typedef struct { unsigned char b[K_ESZ]; } KR;

static void k_ck(cft_status st, const char *what)
{
    if (st != CFT_OK) m1_die("libcft %s: %s (%s)", what, cft_strerror(st), cft_last_error());
}

static void k_run(m1_ctx *c, cft_op op, KR *d, const void *a, const void *b, const void *e, size_t n, unsigned cmask)
{
    cft_elem_args x;
    uint32_t fl = 0;
    memset(&x, 0, sizeof x);
    x.struct_size = sizeof x;
    x.a = a;
    x.b = b;
    x.c = e;
    x.d = d;
    x.n = n;
    x.scalar_mask = cmask;
    x.flags_out = &fl;
    k_ck(cft_run_ex(c->dev, op, K_CFTFMT, CFT_RNE, &x), cft_op_name(op));
    c->cft_flags |= fl;
}

/* libcft: CFT_ADD d = a + c, CFT_SUB d = a - c, CFT_MUL d = a * b,
   CFT_FMA d = a*b + c, CFT_SELECT d = (c != 0) ? a : b */
static void k_add(m1_ctx *c, KR *d, const KR *a, const KR *b, size_t n, unsigned sm)
{
    c->nops[M1_OP_ADD] += n;
    k_run(c, CFT_ADD, d, a, NULL, b, n, ((sm & M1_S1) ? 1u : 0u) | ((sm & M1_S2) ? 4u : 0u));
}
static void k_sub(m1_ctx *c, KR *d, const KR *a, const KR *b, size_t n, unsigned sm)
{
    c->nops[M1_OP_SUB] += n;
    k_run(c, CFT_SUB, d, a, NULL, b, n, ((sm & M1_S1) ? 1u : 0u) | ((sm & M1_S2) ? 4u : 0u));
}
static void k_mul(m1_ctx *c, KR *d, const KR *a, const KR *b, size_t n, unsigned sm)
{
    c->nops[M1_OP_MUL] += n;
    k_run(c, CFT_MUL, d, a, b, NULL, n, ((sm & M1_S1) ? 1u : 0u) | ((sm & M1_S2) ? 2u : 0u));
}
static void k_fma(m1_ctx *c, KR *d, const KR *a, const KR *b, const KR *e, size_t n, unsigned sm)
{
    c->nops[M1_OP_FMA] += n;
    k_run(c, CFT_FMA, d, a, b, e, n, sm & 7u);
}
static void k_neg(m1_ctx *c, KR *d, const KR *a, size_t n)
{
    c->nops[M1_OP_NEG] += n;
    k_run(c, CFT_NEG, d, a, NULL, NULL, n, 0u);
}
static void k_cmplt(m1_ctx *c, KR *d, const KR *a, const KR *b, size_t n, unsigned sm)
{
    c->nops[M1_OP_CMP] += n;
    k_run(c, CFT_CMPLT, d, a, b, NULL, n, ((sm & M1_S1) ? 1u : 0u) | ((sm & M1_S2) ? 2u : 0u));
}
static void k_cmple(m1_ctx *c, KR *d, const KR *a, const KR *b, size_t n, unsigned sm)
{
    c->nops[M1_OP_CMP] += n;
    k_run(c, CFT_CMPLE, d, a, b, NULL, n, ((sm & M1_S1) ? 1u : 0u) | ((sm & M1_S2) ? 2u : 0u));
}
static void k_select(m1_ctx *c, KR *d, const KR *cond, const KR *a, const KR *b, size_t n, unsigned sm)
{
    c->nops[M1_OP_SEL] += n;
    k_run(c, CFT_SELECT, d, a, b, cond, n,
          ((sm & M1_S1) ? 4u : 0u) | ((sm & M1_S2) ? 1u : 0u) | ((sm & M1_S3) ? 2u : 0u));
}

/* scalar operands for the entry points that take none: expanded into the arena */
static const KR *k_expand(m1_ctx *c, const KR *s, size_t n)
{
    KR *v = (KR *)m1_tmp(c, n * sizeof(KR));
    for (size_t i = 0; i < n; i++) v[i] = s[0];
    return v;
}
static void k_div(m1_ctx *c, KR *d, const KR *a, const KR *b, size_t n, unsigned sm)
{
    size_t mark = c->arena_used;
    uint32_t fl = 0;
    c->nops[M1_OP_DIV] += n;
    const KR *aa = (sm & M1_S1) ? k_expand(c, a, n) : a;
    const KR *bb = (sm & M1_S2) ? k_expand(c, b, n) : b;
    k_ck(cft_div(c->dev, K_CFTFMT, CFT_RNE, aa, bb, d, n, &fl, NULL), "cft_div");
    c->cft_flags |= fl;
    c->arena_used = mark;
}
static void k_sqrt(m1_ctx *c, KR *d, const KR *a, size_t n)
{
    uint32_t fl = 0;
    c->nops[M1_OP_SQRT] += n;
    k_ck(cft_sqrt(c->dev, K_CFTFMT, CFT_RNE, a, d, n, &fl, NULL), "cft_sqrt");
    c->cft_flags |= fl;
}

/* compound operations: separate calls, each rounding once, in the order the
   native kinds' single expressions round with contraction off */
static void k_ab_p_ce(m1_ctx *c, KR *d, const KR *a, const KR *b, const KR *e, const KR *f, size_t n, unsigned sm)
{
    size_t mark = c->arena_used;
    KR *t = (KR *)m1_tmp(c, n * sizeof(KR)), *u = (KR *)m1_tmp(c, n * sizeof(KR));
    k_mul(c, t, a, b, n, sm & 3u);
    k_mul(c, u, e, f, n, (sm >> 2) & 3u);
    k_add(c, d, t, u, n, 0u);
    c->arena_used = mark;
}
static void k_ab_m_ce(m1_ctx *c, KR *d, const KR *a, const KR *b, const KR *e, const KR *f, size_t n, unsigned sm)
{
    size_t mark = c->arena_used;
    KR *t = (KR *)m1_tmp(c, n * sizeof(KR)), *u = (KR *)m1_tmp(c, n * sizeof(KR));
    k_mul(c, t, a, b, n, sm & 3u);
    k_mul(c, u, e, f, n, (sm >> 2) & 3u);
    k_sub(c, d, t, u, n, 0u);
    c->arena_used = mark;
}
static void k_dot3(m1_ctx *c, KR *d, const KR *x0, const KR *x1, const KR *x2, const KR *y0, const KR *y1,
                   const KR *y2, size_t n)
{
    size_t mark = c->arena_used;
    KR *t = (KR *)m1_tmp(c, n * sizeof(KR)), *u = (KR *)m1_tmp(c, n * sizeof(KR));
    k_mul(c, t, x0, y0, n, 0u);
    k_mul(c, u, x1, y1, n, 0u);
    k_add(c, t, t, u, n, 0u);
    k_mul(c, u, x2, y2, n, 0u);
    k_add(c, d, t, u, n, 0u);
    c->arena_used = mark;
}

#define K_TRANSC(fname, cftfn, opc)                                               \
    static void k_##fname(m1_ctx *c, KR *d, const KR *a, size_t n)                \
    {                                                                             \
        uint32_t fl = 0;                                                          \
        c->nops[opc] += n;                                                        \
        k_ck(cftfn(c->dev, K_CFTFMT, CFT_RNE, a, d, n, &fl), #cftfn);            \
        c->cft_flags |= fl;                                                       \
    }
K_TRANSC(exp, cft_exp, M1_OP_EXP)
K_TRANSC(sin, cft_sin, M1_OP_SIN)
K_TRANSC(cos, cft_cos, M1_OP_COS)
K_TRANSC(asin, cft_asin, M1_OP_ASIN)
K_TRANSC(acos, cft_acos, M1_OP_ACOS)

static void k_from_f64(m1_ctx *c, KR *d, const double *s, size_t n)
{
    uint32_t fl = 0;
    c->nops[M1_OP_CVT] += n;
    if (K_CFTFMT == CFT_FP64) {
        memcpy(d, s, n * sizeof(double));
        return;
    }
    k_ck(cft_convert(c->dev, CFT_FP64, K_CFTFMT, CFT_RNE, s, d, n, &fl), "cft_convert");
}
static void k_from_dec(m1_ctx *c, KR *d, const char *const *s, size_t n)
{
    uint32_t fl = 0;
    size_t bad = 0;
    c->nops[M1_OP_CVT] += n;
    cft_status st = cft_from_decimal_char(c->dev, K_CFTFMT, CFT_RNE, s, d, n, &bad, &fl);
    if (st != CFT_OK) m1_die("cft_from_decimal_char refused \"%s\": %s", (bad < n) ? s[bad] : "?", cft_strerror(st));
}
static void k_from_i64(m1_ctx *c, KR *d, const int64_t *s, size_t n)
{
    uint32_t fl = 0;
    c->nops[M1_OP_CVT] += n;
    k_ck(cft_cvt_from_i64(c->dev, K_CFTFMT, CFT_RNE, s, d, n, &fl), "cft_cvt_from_i64");
}
static void k_to_f64(m1_ctx *c, double *d, const KR *s, size_t n)
{
    uint32_t fl = 0;
    if (K_CFTFMT == CFT_FP64) {
        memcpy(d, s, n * sizeof(double));
        return;
    }
    k_ck(cft_convert(c->dev, K_CFTFMT, CFT_FP64, CFT_RNE, s, d, n, &fl), "cft_convert");
}
/* E3's planted control: round d to binary64 and back, in place */
static void k_round64(m1_ctx *c, KR *d, size_t n)
{
    uint32_t fl = 0;
    if (K_CFTFMT == CFT_FP64) return;
    double *t = (double *)malloc(n * sizeof(double));
    if (!t) m1_die("out of memory");
    k_ck(cft_convert(c->dev, K_CFTFMT, CFT_FP64, CFT_RNE, d, t, n, &fl), "cft_convert");
    k_ck(cft_convert(c->dev, CFT_FP64, K_CFTFMT, CFT_RNE, t, d, n, &fl), "cft_convert");
    free(t);
}
static void k_ops_check(m1_ctx *c)
{
    if (!cft_supports(c->dev, CFT_FMA, K_CFTFMT)) m1_die("libcft refuses FMA at this format");
}
