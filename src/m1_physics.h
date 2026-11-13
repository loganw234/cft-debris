/* m1_physics.h - cft-debris M1: the force model and the integrator, written
 * ONCE over the number layer and compiled once per number kind (m1_kind.h).
 *
 * cft-debris, MIT licence (see LICENSE at the repository root). Written by
 * DEBRIS-E, 2026-11-13, from this project's own kernels (MIT):
 *   - gravity: DEBRIS-C's studies/debris-c/m1a/m1a_grav.c (the normalised
 *     Cunningham V, W recursion, itself from DEBRIS-B's q2/grav_body.inc,
 *     Montenbruck & Gill 2000, section 3.2), its operations kept in their
 *     order; its derived tables are now computed in each kind from exact
 *     integers (sqrt of an exact quotient), never converted from binary64;
 *   - the exponential atmosphere and the conical shadow: DEBRIS-B's
 *     studies/debris-b/q2/q2bench.c, with their branches turned into selects;
 *   - the third-body form and Earth = EMB - Moon/(1+EMRAT): DEBRIS-C's
 *     studies/debris-c/m1b/m1b_check.py;
 *   - the uniform rotation and rk4: DEBRIS-D's studies/debris-d/q4/q4prop.c.
 * Every lane runs the same operations: no branch depends on a lane's data.
 * The Chebyshev reader's record and sub-interval are chosen on the host and
 * gathered per lane (no counterpart on the GPU route until index tables).
 *
 * Macros expected from the includer: KR (the element type), K_NATIVE, and
 * the k_* operations of m1_ops_native.h or m1_ops_cft.h.
 */
#include "m1_consts.h"

enum {
    C_ZERO, C_ONE, C_NONE, C_TWO, C_SIX, C_HALF, C_NHALF, C_KM, C_PI, C_GMS, C_GMM, C_OMEGA, C_THETA0,
    C_REARTH, C_RSUN, C_AU, C_PSUN, C_N
};

typedef struct KD {
    KR K[C_N];
    KR GM, RE, RE2, KACC, NOMEGA, EMRAT, AUKM, FEM, CTLREL;
    KR SUBLEN[13];
    int nb;
    KR BH0[M1_MAXBANDS], BRHO[M1_MAXBANDS], BHS[M1_MAXBANDS];
    int nmax, L;
    size_t ntri_nmax, ntri_L;
    KR *Cb, *Sb, *An, *Bn, *Dg, *Sd, *F1, *FA, *FB, *FZ, *P1, *PZ0, *hFA, *nhFA, *hFB;
    KR **cache;
    long nrec;
    int ncoeff;
} KD;

#define KK(i) (&D->K[i])
#define TMP(nl) ((KR *)m1_tmp(c, (size_t)(nl) * sizeof(KR)))

static void kfill(KR *d, const KR *s, size_t n)
{
    for (size_t i = 0; i < n; i++) memcpy(&d[i], s, sizeof(KR));
}
static KR *kalloc(size_t n)
{
    KR *p = (KR *)calloc(n ? n : 1, sizeof(KR));
    if (!p) m1_die("out of memory (%lu elements)", (unsigned long)n);
    return p;
}

/* sqrt(num/den) for exact integers, in the kind: one conversion each (exact
   wherever the integer fits the significand), one division, one square root */
static void ksqrt_ratio(m1_ctx *c, KR *d, const int64_t *num, const int64_t *den, size_t n)
{
    size_t mark = c->arena_used;
    KR *a = TMP(n), *b = TMP(n);
    k_from_i64(c, a, num, n);
    k_from_i64(c, b, den, n);
    k_div(c, a, a, b, n, 0);
    k_sqrt(c, d, a, n);
    c->arena_used = mark;
}

/* ------------------------------------------------------------------ setup */

static void ph_teardown(m1_ctx *c)
{
    KD *D = (KD *)c->k;
    if (!D) return;
    KR *tabs[] = {D->Cb, D->Sb, D->An, D->Bn, D->Dg, D->Sd, D->F1, D->FA, D->FB, D->FZ, D->P1, D->PZ0, D->hFA, D->nhFA, D->hFB};
    for (size_t i = 0; i < sizeof tabs / sizeof tabs[0]; i++) free(tabs[i]);
    if (D->cache) {
        for (long i = 0; i < D->nrec; i++) free(D->cache[i]);
        free(D->cache);
    }
    free(D);
    c->k = NULL;
    free(c->arena);
    c->arena = NULL;
    free(c->vw);
    c->vw = NULL;
}

static int ph_setup(m1_ctx *c, const m1_model *model, const m1_gfc *g, const m1_de *de, size_t max_lanes)
{
    KD *D = (KD *)calloc(1, sizeof(KD));
    if (!D) m1_die("out of memory");
    c->k = D;
    c->esz = sizeof(KR);
    c->gfc = g;
    c->de = de;
    c->model = *model;
    c->arena_cap = (size_t)640 * (max_lanes ? max_lanes : 1) * sizeof(KR) + ((size_t)1 << 20);
    c->arena = (unsigned char *)malloc(c->arena_cap);
    c->arena_used = 0;
    if (!c->arena) m1_die("out of memory (arena)");
    k_ops_check(c);

    /* the constants, each from its decimal string, once */
    const char *dec[C_N];
    if (M1_NCONSTS != C_N) m1_die("constant table and indices disagree");
    for (int i = 0; i < C_N; i++) dec[i] = M1_CONSTS[i].dec;
    k_from_dec(c, D->K, dec, C_N);
    k_neg(c, &D->NOMEGA, KK(C_OMEGA), 1);

    /* the field's GM and reference radius: the .gfc header's own strings */
    if (g) {
        const char *gr[2] = {g->gm, g->radius};
        KR t[2];
        k_from_dec(c, t, gr, 2);
        D->GM = t[0];
        D->RE = t[1];
        k_mul(c, &D->RE2, &D->RE, &D->RE, 1, 0);
        k_div(c, &D->KACC, &D->GM, &D->RE2, 1, 0);
    }
    /* DE421's EMRAT and AU (binary64 values in the binary's first record) */
    if (de) {
        double v[2] = {de->emrat, de->au_km};
        KR t[2];
        k_from_f64(c, t, v, 2);
        D->EMRAT = t[0];
        D->AUKM = t[1];
        k_add(c, &D->FEM, KK(C_ONE), &D->EMRAT, 1, 0);
        k_div(c, &D->FEM, KK(C_ONE), &D->FEM, 1, 0);
        int64_t len[13];
        for (int k = 0; k < 13; k++) {
            double s = de->ss[2] * 86400.0 / de->ipt[k][2];
            len[k] = (int64_t)s;
            if ((double)len[k] != s) m1_die("sub-interval length not a whole number of seconds");
        }
        k_from_i64(c, D->SUBLEN, len, 13);
        D->nrec = de->nrec;
        D->ncoeff = de->ncoeff;
        D->cache = (KR **)calloc((size_t)de->nrec, sizeof(KR *));
        if (!D->cache) m1_die("out of memory");
    }
    /* the atmosphere's bands */
    D->nb = model->nbands;
    if (D->nb == 28) {
        k_from_dec(c, D->BH0, M1_ATM_H0, 28);
        k_from_dec(c, D->BRHO, M1_ATM_RHO0, 28);
        k_from_dec(c, D->BHS, M1_ATM_HS, 28);
    } else if (D->nb == 1) {
        k_from_dec(c, D->BH0, &model->band_h0, 1);
        k_from_dec(c, D->BRHO, &model->band_rho0, 1);
        k_from_dec(c, D->BHS, &model->band_hs, 1);
    } else {
        m1_die("the atmosphere has 28 bands or 1");
    }

    /* gravity: coefficients from their decimal strings; derived tables from
       exact integers, in a fixed order */
    int N = model->nmax;
    if (g && N >= 2) {
        if (N > g->nmax || N > M1_NMAX) m1_die("degree %d beyond the coefficients loaded", N);
        int L = N + 1;
        D->nmax = N;
        D->L = L;
        c->nmax = N;
        size_t tN = M1_TRI(N, N) + 1, tL = M1_TRI(L, L) + 1;
        D->ntri_nmax = tN;
        D->ntri_L = tL;
        D->Cb = kalloc(tN);
        D->Sb = kalloc(tN);
        const char **cs = (const char **)malloc(tN * sizeof(char *)), **ss = (const char **)malloc(tN * sizeof(char *));
        for (size_t i = 0; i < tN; i++) {
            cs[i] = g->c[i] ? g->c[i] : "0";
            ss[i] = g->s[i] ? g->s[i] : "0";
        }
        k_from_dec(c, D->Cb, cs, tN);
        k_from_dec(c, D->Sb, ss, tN);
        free(cs);
        free(ss);
        if (c->ctl_c20) {
            /* the planted control of E6 and E7: C20 times (1 + rel), in the kind */
            char buf[64];
            const char *p = buf;
            snprintf(buf, sizeof buf, "%.17g", c->ctl_c20_rel);
            k_from_dec(c, &D->CTLREL, &p, 1);
            k_add(c, &D->CTLREL, KK(C_ONE), &D->CTLREL, 1, 0);
            k_mul(c, &D->Cb[M1_TRI(2, 0)], &D->Cb[M1_TRI(2, 0)], &D->CTLREL, 1, 0);
        }
        D->An = kalloc(tL);
        D->Bn = kalloc(tL);
        D->Dg = kalloc((size_t)L + 1);
        D->Sd = kalloc((size_t)L + 1);
        D->F1 = kalloc((size_t)N + 1);
        D->FA = kalloc(tN);
        D->FB = kalloc(tN);
        D->FZ = kalloc(tN);
        D->P1 = kalloc((size_t)N + 1);
        D->PZ0 = kalloc((size_t)N + 1);
        D->hFA = kalloc(tN);
        D->nhFA = kalloc(tN);
        D->hFB = kalloc(tN);
        KR *zt[] = {D->An, D->Bn, D->FA, D->FB, D->FZ, D->hFA, D->nhFA, D->hFB};
        for (size_t i = 0; i < 8; i++) kfill(zt[i], KK(C_ZERO), i < 2 ? tL : tN);
        kfill(D->Dg, KK(C_ZERO), (size_t)L + 1);
        kfill(D->F1, KK(C_ZERO), (size_t)N + 1);
        kfill(D->P1, KK(C_ZERO), (size_t)N + 1);
        kfill(D->PZ0, KK(C_ZERO), (size_t)N + 1);

        size_t cap = tL + 8;
        int64_t *num = (int64_t *)malloc(cap * sizeof(int64_t)), *den = (int64_t *)malloc(cap * sizeof(int64_t));
        size_t *at = (size_t *)malloc(cap * sizeof(size_t));
        KR *val = kalloc(cap);
        size_t k;
        /* An, Bn: n >= m + 2, n <= L */
        k = 0;
        for (int n = 2; n <= L; n++)
            for (int m = 0; m + 2 <= n; m++) {
                num[k] = (int64_t)(2 * n - 1) * (2 * n + 1);
                den[k] = (int64_t)(n - m) * (n + m);
                at[k++] = M1_TRI(n, m);
            }
        ksqrt_ratio(c, val, num, den, k);
        for (size_t i = 0; i < k; i++) D->An[at[i]] = val[i];
        k = 0;
        for (int n = 2; n <= L; n++)
            for (int m = 0; m + 2 <= n; m++) {
                num[k] = (int64_t)(2 * n + 1) * (n + m - 1) * (n - m - 1);
                den[k] = (int64_t)(2 * n - 3) * (n + m) * (n - m);
                at[k++] = M1_TRI(n, m);
            }
        ksqrt_ratio(c, val, num, den, k);
        for (size_t i = 0; i < k; i++) D->Bn[at[i]] = val[i];
        /* Dg: sqrt(3) at m = 1, sqrt((2m+1)/(2m)) from m = 2; Sd: sqrt(2m+3) */
        k = 0;
        for (int m = 1; m <= L; m++) {
            num[k] = (m == 1) ? 3 : 2 * m + 1;
            den[k] = (m == 1) ? 1 : 2 * m;
            at[k++] = (size_t)m;
        }
        ksqrt_ratio(c, val, num, den, k);
        for (size_t i = 0; i < k; i++) D->Dg[at[i]] = val[i];
        k = 0;
        for (int m = 0; m <= L; m++) {
            num[k] = 2 * m + 3;
            den[k] = 1;
            at[k++] = (size_t)m;
        }
        ksqrt_ratio(c, val, num, den, k);
        for (size_t i = 0; i < k; i++) D->Sd[at[i]] = val[i];
        /* F1[n] = sqrt((2n+1)(n+1)(n+2) / (2(2n+3))), n <= N */
        k = 0;
        for (int n = 0; n <= N; n++) {
            num[k] = (int64_t)(2 * n + 1) * (n + 1) * (n + 2);
            den[k] = (int64_t)2 * (2 * n + 3);
            at[k++] = (size_t)n;
        }
        ksqrt_ratio(c, val, num, den, k);
        for (size_t i = 0; i < k; i++) D->F1[at[i]] = val[i];
        /* FA = sqrt((2n+1)(n+m+1)(n+m+2)/(2n+3)); FB (m >= 1) = sqrt(f (2n+1)(n-m+1)(n-m+2)/(2n+3)),
           f = 2 at m = 1, else 1; FZ = sqrt((2n+1)(n+m+1)(n-m+1)/(2n+3)) */
        k = 0;
        for (int n = 0; n <= N; n++)
            for (int m = 0; m <= n; m++) {
                num[k] = (int64_t)(2 * n + 1) * (n + m + 1) * (n + m + 2);
                den[k] = 2 * n + 3;
                at[k++] = M1_TRI(n, m);
            }
        ksqrt_ratio(c, val, num, den, k);
        for (size_t i = 0; i < k; i++) D->FA[at[i]] = val[i];
        k = 0;
        for (int n = 1; n <= N; n++)
            for (int m = 1; m <= n; m++) {
                num[k] = (int64_t)((m == 1) ? 2 : 1) * (2 * n + 1) * (n - m + 1) * (n - m + 2);
                den[k] = 2 * n + 3;
                at[k++] = M1_TRI(n, m);
            }
        ksqrt_ratio(c, val, num, den, k);
        for (size_t i = 0; i < k; i++) D->FB[at[i]] = val[i];
        k = 0;
        for (int n = 0; n <= N; n++)
            for (int m = 0; m <= n; m++) {
                num[k] = (int64_t)(2 * n + 1) * (n + m + 1) * (n - m + 1);
                den[k] = 2 * n + 3;
                at[k++] = M1_TRI(n, m);
            }
        ksqrt_ratio(c, val, num, den, k);
        for (size_t i = 0; i < k; i++) D->FZ[at[i]] = val[i];
        free(num);
        free(den);
        free(at);
        free(val);
        /* products the kernel would otherwise form at every call, in the same order */
        for (int n = 0; n <= N; n++) {
            k_mul(c, &D->P1[n], &D->F1[n], &D->Cb[M1_TRI(n, 0)], 1, 0);
            k_mul(c, &D->PZ0[n], &D->FZ[M1_TRI(n, 0)], &D->Cb[M1_TRI(n, 0)], 1, 0);
        }
        k_mul(c, D->hFA, D->FA, KK(C_HALF), tN, M1_S2);
        k_mul(c, D->nhFA, D->FA, KK(C_NHALF), tN, M1_S2);
        k_mul(c, D->hFB, D->FB, KK(C_HALF), tN, M1_S2);
    }
    c->arena_used = 0;
    return 0;
}

static void ph_tables(m1_ctx *c, m1_table_cb cb, void *u)
{
    KD *D = (KD *)c->k;
    for (int i = 0; i < C_N; i++) cb(u, M1_CONSTS[i].name, &D->K[i], 1);
    cb(u, "NOMEGA", &D->NOMEGA, 1);
    if (c->gfc) {
        cb(u, "GM_FIELD", &D->GM, 1);
        cb(u, "RE_FIELD", &D->RE, 1);
        cb(u, "RE2", &D->RE2, 1);
        cb(u, "KACC", &D->KACC, 1);
    }
    if (c->de) {
        cb(u, "EMRAT", &D->EMRAT, 1);
        cb(u, "AU_KM", &D->AUKM, 1);
        cb(u, "FEM", &D->FEM, 1);
        cb(u, "SUBLEN", D->SUBLEN, 13);
    }
    cb(u, "ATM_H0", D->BH0, (size_t)D->nb);
    cb(u, "ATM_RHO0", D->BRHO, (size_t)D->nb);
    cb(u, "ATM_HS", D->BHS, (size_t)D->nb);
    if (D->nmax >= 2) {
        cb(u, "Cbar", D->Cb, D->ntri_nmax);
        cb(u, "Sbar", D->Sb, D->ntri_nmax);
        cb(u, "An", D->An, D->ntri_L);
        cb(u, "Bn", D->Bn, D->ntri_L);
        cb(u, "Dg", D->Dg, (size_t)D->L + 1);
        cb(u, "Sd", D->Sd, (size_t)D->L + 1);
        cb(u, "F1", D->F1, (size_t)D->nmax + 1);
        cb(u, "FA", D->FA, D->ntri_nmax);
        cb(u, "FB", D->FB, D->ntri_nmax);
        cb(u, "FZ", D->FZ, D->ntri_nmax);
        cb(u, "P1", D->P1, (size_t)D->nmax + 1);
        cb(u, "PZ0", D->PZ0, (size_t)D->nmax + 1);
        cb(u, "hFA", D->hFA, D->ntri_nmax);
        cb(u, "nhFA", D->nhFA, D->ntri_nmax);
        cb(u, "hFB", D->hFB, D->ntri_nmax);
    }
}

/* ---------------------------------------------------------------- gravity */

/* Earth-fixed acceleration of degrees nmin..nmax (nmin >= 2), m/s^2, at
   Earth-fixed positions rb (m): m1a_grav.c's grav(), operation for operation */
static void ph_grav(m1_ctx *c, KR *const a[3], KR *const rb[3], int nmin, int nmax, size_t n)
{
    KD *D = (KD *)c->k;
    if (nmin < 2 || nmax > D->nmax || nmin > nmax) m1_die("gravity degrees %d..%d outside 2..%d", nmin, nmax, D->nmax);
    size_t mark = c->arena_used;
    const int L = nmax + 1;
    const size_t ntri = M1_TRI(L, L) + 1;
    const size_t need = 2 * ntri * n * sizeof(KR);
    if (c->vw_cap < need) {
        free(c->vw);
        c->vw = (unsigned char *)malloc(need);
        if (!c->vw) m1_die("out of memory (V, W: %lu bytes)", (unsigned long)need);
        c->vw_cap = need;
    }
    KR *Vb = (KR *)c->vw, *Wb = Vb + ntri * n;
#define V(nn, mm) (Vb + M1_TRI(nn, mm) * n)
#define W(nn, mm) (Wb + M1_TRI(nn, mm) * n)
    KR *r2 = TMP(n), *ir2 = TMP(n), *rho = TMP(n), *x0 = TMP(n), *y0 = TMP(n), *z0 = TMP(n);
    KR *t = TMP(n), *p = TMP(n), *q = TMP(n);
    k_dot3(c, r2, rb[0], rb[1], rb[2], rb[0], rb[1], rb[2], n);
    k_div(c, ir2, KK(C_ONE), r2, n, M1_S1);
    k_mul(c, rho, &D->RE2, ir2, n, M1_S1);
    k_mul(c, t, &D->RE, rb[0], n, M1_S1);
    k_mul(c, x0, t, ir2, n, 0);
    k_mul(c, t, &D->RE, rb[1], n, M1_S1);
    k_mul(c, y0, t, ir2, n, 0);
    k_mul(c, t, &D->RE, rb[2], n, M1_S1);
    k_mul(c, z0, t, ir2, n, 0);
    k_sqrt(c, t, r2, n);
    k_div(c, V(0, 0), &D->RE, t, n, M1_S1);
    kfill(W(0, 0), KK(C_ZERO), n);
    for (int m = 0; m <= L; m++) {
        if (m > 0) {
            k_ab_m_ce(c, t, x0, V(m - 1, m - 1), y0, W(m - 1, m - 1), n, 0);
            k_ab_p_ce(c, p, x0, W(m - 1, m - 1), y0, V(m - 1, m - 1), n, 0);
            k_mul(c, V(m, m), &D->Dg[m], t, n, M1_S1);
            k_mul(c, W(m, m), &D->Dg[m], p, n, M1_S1);
        }
        if (m < L) {
            k_mul(c, p, &D->Sd[m], z0, n, M1_S1);
            k_mul(c, V(m + 1, m), p, V(m, m), n, 0);
            k_mul(c, W(m + 1, m), p, W(m, m), n, 0);
        }
        for (int nn = m + 2; nn <= L; nn++) {
            k_mul(c, p, &D->An[M1_TRI(nn, m)], z0, n, M1_S1);
            k_mul(c, q, &D->Bn[M1_TRI(nn, m)], rho, n, M1_S1);
            k_ab_m_ce(c, V(nn, m), p, V(nn - 1, m), q, V(nn - 2, m), n, 0);
            k_ab_m_ce(c, W(nn, m), p, W(nn - 1, m), q, W(nn - 2, m), n, 0);
        }
    }
    KR *ax = TMP(n), *ay = TMP(n), *az = TMP(n);
    KR *t1 = TMP(n), *t2 = TMP(n), *t3 = TMP(n), *t4 = TMP(n), *t5 = TMP(n), *u = TMP(n);
    kfill(ax, KK(C_ZERO), n);
    kfill(ay, KK(C_ZERO), n);
    kfill(az, KK(C_ZERO), n);
    const unsigned SC = M1_S1 | M1_S3;
    for (int nn = nmin; nn <= nmax; nn++) {
        k_mul(c, u, &D->P1[nn], V(nn + 1, 1), n, M1_S1);
        k_sub(c, ax, ax, u, n, 0);
        k_mul(c, u, &D->P1[nn], W(nn + 1, 1), n, M1_S1);
        k_sub(c, ay, ay, u, n, 0);
        k_mul(c, u, &D->PZ0[nn], V(nn + 1, 0), n, M1_S1);
        k_sub(c, az, az, u, n, 0);
        for (int m = 1; m <= nn; m++) {
            const KR *C = &D->Cb[M1_TRI(nn, m)], *S = &D->Sb[M1_TRI(nn, m)];
            k_ab_p_ce(c, t1, C, V(nn + 1, m + 1), S, W(nn + 1, m + 1), n, SC);
            k_ab_p_ce(c, t2, C, V(nn + 1, m - 1), S, W(nn + 1, m - 1), n, SC);
            k_ab_m_ce(c, t3, S, V(nn + 1, m + 1), C, W(nn + 1, m + 1), n, SC);
            k_ab_m_ce(c, t4, S, V(nn + 1, m - 1), C, W(nn + 1, m - 1), n, SC);
            k_ab_p_ce(c, t5, C, V(nn + 1, m), S, W(nn + 1, m), n, SC);
            k_ab_p_ce(c, u, &D->nhFA[M1_TRI(nn, m)], t1, &D->hFB[M1_TRI(nn, m)], t2, n, SC);
            k_add(c, ax, ax, u, n, 0);
            k_ab_p_ce(c, u, &D->hFA[M1_TRI(nn, m)], t3, &D->hFB[M1_TRI(nn, m)], t4, n, SC);
            k_add(c, ay, ay, u, n, 0);
            k_mul(c, u, &D->FZ[M1_TRI(nn, m)], t5, n, M1_S1);
            k_sub(c, az, az, u, n, 0);
        }
    }
    k_mul(c, a[0], &D->KACC, ax, n, M1_S1);
    k_mul(c, a[1], &D->KACC, ay, n, M1_S1);
    k_mul(c, a[2], &D->KACC, az, n, M1_S1);
#undef V
#undef W
    c->arena_used = mark;
}

/* ---------------------------------------------------- central, third body */

static void ph_central(m1_ctx *c, KR *const a[3], KR *const r[3], size_t n)
{
    KD *D = (KD *)c->k;
    size_t mark = c->arena_used;
    KR *r2 = TMP(n), *rn = TMP(n), *k = TMP(n);
    k_dot3(c, r2, r[0], r[1], r[2], r[0], r[1], r[2], n);
    k_sqrt(c, rn, r2, n);
    k_mul(c, k, r2, rn, n, 0);
    k_div(c, k, &D->GM, k, n, M1_S1);
    k_neg(c, k, k, n);
    if (c->ctl_round64) k_round64(c, k, n); /* E3's planted control */
    for (int i = 0; i < 3; i++) k_mul(c, a[i], k, r[i], n, 0);
    c->arena_used = mark;
}

/* a = GM (d/|d|^3 - s/|s|^3), d = s - r: the direct tide of a point mass */
static void ph_third(m1_ctx *c, KR *const a[3], KR *const r[3], KR *const s[3], int s_scalar, int body, size_t n)
{
    KD *D = (KD *)c->k;
    size_t mark = c->arena_used;
    const KR *GMB = body ? KK(C_GMM) : KK(C_GMS);
    const size_t ns = s_scalar ? 1 : n;
    const unsigned sS = s_scalar ? M1_S1 : 0u;
    KR *d[3] = {TMP(n), TMP(n), TMP(n)}, *dd = TMP(n), *nd = TMP(n), *qd = TMP(n);
    KR *s2 = TMP(ns), *sn = TMP(ns), *qs = TMP(ns);
    for (int i = 0; i < 3; i++) k_sub(c, d[i], s[i], r[i], n, sS);
    k_dot3(c, dd, d[0], d[1], d[2], d[0], d[1], d[2], n);
    k_sqrt(c, nd, dd, n);
    k_mul(c, qd, dd, nd, n, 0);
    k_div(c, qd, GMB, qd, n, M1_S1);
    k_dot3(c, s2, s[0], s[1], s[2], s[0], s[1], s[2], ns);
    k_sqrt(c, sn, s2, ns);
    k_mul(c, qs, s2, sn, ns, 0);
    k_div(c, qs, GMB, qs, ns, M1_S1);
    const unsigned sm = s_scalar ? (M1_S3 | M1_S4) : 0u;
    for (int i = 0; i < 3; i++) k_ab_m_ce(c, a[i], qd, d[i], qs, s[i], n, sm);
    c->arena_used = mark;
}

/* ------------------------------------------------------------- ephemeris */

static const KR *ph_record(m1_ctx *c, long i)
{
    KD *D = (KD *)c->k;
    if (i < 0 || i >= D->nrec) m1_die("record %ld outside DE421", i);
    if (!D->cache[i]) {
        D->cache[i] = kalloc((size_t)D->ncoeff);
        k_from_f64(c, D->cache[i], m1_de_record(c->de, i), (size_t)D->ncoeff);
    }
    return D->cache[i];
}

/* series k at n lanes, each with its own record and sub-interval (chosen on
   the host and gathered) and dt seconds into it: positions in km. The normalised
   time is tau = (dt + dt)/len - 1, in the kind; the sum is Clenshaw's, from the
   highest coefficient down, b = fma(2 tau, b1, c_i) - b2. */
static void ph_series(m1_ctx *c, KR *const out[3], int k, const long *rec, const int *sub, const double *dt_sec, size_t n)
{
    KD *D = (KD *)c->k;
    const m1_de *de = c->de;
    if (k < 0 || k > 11) m1_die("series %d", k);
    size_t mark = c->arena_used;
    const int off = de->ipt[k][0], nc = de->ipt[k][1], nsub = de->ipt[k][2];
    KR *dt = TMP(n), *tau = TMP(n), *t2 = TMP(n), *coef = TMP(n), *b0 = TMP(n), *b1 = TMP(n), *b2 = TMP(n);
    k_from_f64(c, dt, dt_sec, n);
    k_add(c, tau, dt, dt, n, 0);
    k_div(c, tau, tau, &D->SUBLEN[k], n, M1_S2);
    k_sub(c, tau, tau, KK(C_ONE), n, M1_S2);
    k_add(c, t2, tau, tau, n, 0);
    const KR **recp = (const KR **)m1_tmp(c, n * sizeof(KR *));
    for (size_t l = 0; l < n; l++) {
        if (sub[l] < 0 || sub[l] >= nsub) m1_die("sub-interval %d of %d", sub[l], nsub);
        recp[l] = ph_record(c, rec[l]);
    }
    for (int j = 0; j < 3; j++) {
        kfill(b1, KK(C_ZERO), n);
        kfill(b2, KK(C_ZERO), n);
        for (int i = nc - 1; i >= 0; i--) {
            for (size_t l = 0; l < n; l++) coef[l] = recp[l][off - 1 + nc * (j + 3 * sub[l]) + i];
            if (i > 0) {
                k_fma(c, b0, t2, b1, coef, n, 0);
                k_sub(c, b0, b0, b2, n, 0);
                KR *tmp = b2;
                b2 = b1;
                b1 = b0;
                b0 = tmp;
            } else {
                k_fma(c, out[j], tau, b1, coef, n, 0);
                k_sub(c, out[j], out[j], b2, n, 0);
            }
        }
    }
    c->arena_used = mark;
}

/* geocentric Sun and Moon, m: Earth = EMB - Moon/(1+EMRAT), Sun - Earth */
static void ph_bodies(m1_ctx *c, KR *const sun[3], KR *const moon[3], const m1_ephq *q, size_t n)
{
    KD *D = (KD *)c->k;
    size_t mark = c->arena_used;
    KR *mo[3] = {TMP(n), TMP(n), TMP(n)}, *su[3] = {TMP(n), TMP(n), TMP(n)}, *em[3] = {TMP(n), TMP(n), TMP(n)};
    KR *t = TMP(n);
    ph_series(c, mo, M1_SER_MOON, q->rec[0], q->sub[0], q->dt_sec[0], n);
    ph_series(c, su, M1_SER_SUN, q->rec[1], q->sub[1], q->dt_sec[1], n);
    ph_series(c, em, M1_SER_EMB, q->rec[2], q->sub[2], q->dt_sec[2], n);
    for (int i = 0; i < 3; i++) {
        k_mul(c, t, &D->FEM, mo[i], n, M1_S1);
        k_sub(c, em[i], em[i], t, n, 0);  /* the Earth, km */
        k_sub(c, su[i], su[i], em[i], n, 0);
        k_mul(c, sun[i], KK(C_KM), su[i], n, M1_S1);
        k_mul(c, moon[i], KK(C_KM), mo[i], n, M1_S1);
    }
    c->arena_used = mark;
}

/* testpo.421's semantics: the target relative to the centre, in AU, for the
   bodies 3 (Earth), 10 (Moon), 11 (Sun), 12 (SSB) and 13 (EMB); (10, 3) and
   (3, 10) use the geocentric Moon directly (DEBRIS-C's m1b_check.py pleph) */
static void ph_ssb(m1_ctx *c, KR *const o[3], int body, KR *const mo[3], KR *const su[3], KR *const em[3], size_t n)
{
    KD *D = (KD *)c->k;
    for (int i = 0; i < 3; i++) {
        switch (body) {
        case 3:
        case 10:
            k_mul(c, o[i], &D->FEM, mo[i], n, M1_S1);
            k_sub(c, o[i], em[i], o[i], n, 0);
            if (body == 10) k_add(c, o[i], o[i], mo[i], n, 0);
            break;
        case 11: memcpy(o[i], su[i], n * sizeof(KR)); break;
        case 12: kfill(o[i], KK(C_ZERO), n); break;
        case 13: memcpy(o[i], em[i], n * sizeof(KR)); break;
        default: m1_die("body %d is not one this reader serves", body);
        }
    }
}
static void ph_pleph(m1_ctx *c, KR *const out[3], int target, int center, const m1_ephq *q, size_t n)
{
    KD *D = (KD *)c->k;
    size_t mark = c->arena_used;
    KR *mo[3] = {TMP(n), TMP(n), TMP(n)}, *su[3] = {TMP(n), TMP(n), TMP(n)}, *em[3] = {TMP(n), TMP(n), TMP(n)};
    KR *pa[3] = {TMP(n), TMP(n), TMP(n)}, *pb[3] = {TMP(n), TMP(n), TMP(n)};
    ph_series(c, mo, M1_SER_MOON, q->rec[0], q->sub[0], q->dt_sec[0], n);
    ph_series(c, su, M1_SER_SUN, q->rec[1], q->sub[1], q->dt_sec[1], n);
    ph_series(c, em, M1_SER_EMB, q->rec[2], q->sub[2], q->dt_sec[2], n);
    if ((target == 10 && center == 3) || (target == 3 && center == 10)) {
        for (int i = 0; i < 3; i++) {
            if (target == 10) memcpy(pa[i], mo[i], n * sizeof(KR));
            else k_neg(c, pa[i], mo[i], n);
        }
    } else {
        ph_ssb(c, pa, target, mo, su, em, n);
        ph_ssb(c, pb, center, mo, su, em, n);
        for (int i = 0; i < 3; i++) k_sub(c, pa[i], pa[i], pb[i], n, 0);
    }
    for (int i = 0; i < 3; i++) k_div(c, out[i], pa[i], &D->AUKM, n, M1_S2);
    c->arena_used = mark;
}

/* ---------------------------------------------------------------- frame */

/* theta = fma(omega, t, theta0); cos and sin of it */
static void ph_angle(m1_ctx *c, KR *ct, KR *st, const KR *t, size_t n)
{
    KD *D = (KD *)c->k;
    size_t mark = c->arena_used;
    KR *th = TMP(n);
    k_fma(c, th, KK(C_OMEGA), t, KK(C_THETA0), n, M1_S1 | M1_S3);
    k_cos(c, ct, th, n);
    k_sin(c, st, th, n);
    c->arena_used = mark;
}
/* inertial -> body (inverse 0): xb = c x + s y, yb = c y - s x, zb = z;
   body -> inertial (inverse 1): x = c xb - s yb, y = s xb + c yb */
static void ph_rot_apply(m1_ctx *c, KR *const o[3], KR *const in[3], const KR *ct, const KR *st, int cs_scalar,
                         int inverse, size_t n)
{
    const unsigned sm = cs_scalar ? (M1_S1 | M1_S3) : 0u;
    if (!inverse) {
        k_ab_p_ce(c, o[0], ct, in[0], st, in[1], n, sm);
        k_ab_m_ce(c, o[1], ct, in[1], st, in[0], n, sm);
    } else {
        k_ab_m_ce(c, o[0], ct, in[0], st, in[1], n, sm);
        k_ab_p_ce(c, o[1], st, in[0], ct, in[1], n, sm);
    }
    if (o[2] != in[2]) memcpy(o[2], in[2], n * sizeof(KR));
}
static void ph_rotate(m1_ctx *c, KR *const rb[3], KR *const r[3], const KR *t, int t_scalar, int inverse, size_t n)
{
    size_t mark = c->arena_used;
    const size_t nt = t_scalar ? 1 : n;
    KR *ct = TMP(nt), *st = TMP(nt);
    ph_angle(c, ct, st, t, nt);
    ph_rot_apply(c, rb, r, ct, st, t_scalar, inverse, n);
    c->arena_used = mark;
}

/* ----------------------------------------------------------------- drag */

/* a = -bc rho |v_rel| v_rel, v_rel = v - omega x r, rho from the band whose
   base is the highest at or below h = |r| - R_EARTH (selects, no branch) */
static void ph_drag(m1_ctx *c, KR *const a[3], KR *const r[3], KR *const v[3], const KR *bc, size_t n)
{
    KD *D = (KD *)c->k;
    size_t mark = c->arena_used;
    KR *rr = TMP(n), *h = TMP(n), *h0 = TMP(n), *rho0 = TMP(n), *hs = TMP(n), *ge = TMP(n), *u = TMP(n);
    KR *vr[3] = {TMP(n), TMP(n), TMP(n)}, *vn = TMP(n), *k = TMP(n);
    k_dot3(c, rr, r[0], r[1], r[2], r[0], r[1], r[2], n);
    k_sqrt(c, rr, rr, n);
    k_sub(c, h, rr, KK(C_REARTH), n, M1_S2);
    kfill(h0, &D->BH0[0], n);
    kfill(rho0, &D->BRHO[0], n);
    kfill(hs, &D->BHS[0], n);
    for (int b = 1; b < D->nb; b++) {
        k_cmple(c, ge, &D->BH0[b], h, n, M1_S1);
        k_select(c, h0, ge, &D->BH0[b], h0, n, M1_S2);
        k_select(c, rho0, ge, &D->BRHO[b], rho0, n, M1_S2);
        k_select(c, hs, ge, &D->BHS[b], hs, n, M1_S2);
    }
    k_sub(c, u, h, h0, n, 0);
    k_div(c, u, u, hs, n, 0);
    k_neg(c, u, u, n);
    k_exp(c, u, u, n);
    k_mul(c, u, rho0, u, n, 0); /* rho */
    k_fma(c, vr[0], KK(C_OMEGA), r[1], v[0], n, M1_S1);
    k_fma(c, vr[1], &D->NOMEGA, r[0], v[1], n, M1_S1);
    memcpy(vr[2], v[2], n * sizeof(KR));
    k_dot3(c, vn, vr[0], vr[1], vr[2], vr[0], vr[1], vr[2], n);
    k_sqrt(c, vn, vn, n);
    k_mul(c, k, bc, u, n, 0);
    k_mul(c, k, k, vn, n, 0);
    k_neg(c, k, k, n);
    for (int i = 0; i < 3; i++) k_mul(c, a[i], k, vr[i], n, 0);
    c->arena_used = mark;
}

/* ------------------------------------------------------- radiation pressure */

/* the shadow's geometry, before its inverse trigonometry: d = r - rs,
   sin A = R_SUN/|d|, sin B = R_EARTH/|r|, cos C = r.d/(|r||d|) clamped to [-1, 1] */
static void ph_geom(m1_ctx *c, KR *const d[3], KR *dn, KR *sa, KR *sb, KR *cc, KR *const r[3], KR *const rs[3],
                    int rs_scalar, size_t n)
{
    KD *D = (KD *)c->k;
    size_t mark = c->arena_used;
    KR *rn = TMP(n), *t = TMP(n), *lt = TMP(n);
    for (int i = 0; i < 3; i++) k_sub(c, d[i], r[i], rs[i], n, rs_scalar ? M1_S2 : 0u);
    k_dot3(c, rn, r[0], r[1], r[2], r[0], r[1], r[2], n);
    k_sqrt(c, rn, rn, n);
    k_dot3(c, dn, d[0], d[1], d[2], d[0], d[1], d[2], n);
    k_sqrt(c, dn, dn, n);
    k_div(c, sa, KK(C_RSUN), dn, n, M1_S1);
    k_div(c, sb, KK(C_REARTH), rn, n, M1_S1);
    k_dot3(c, cc, r[0], r[1], r[2], d[0], d[1], d[2], n);
#if defined(M1_NEGCTL_REORDER) && K_NATIVE
    /* E1's negative control, built for the native kinds only: the division
       reordered, cos C = (r.d / |r|) / |d| */
    k_div(c, t, cc, rn, n, 0);
    k_div(c, cc, t, dn, n, 0);
#else
    k_mul(c, t, rn, dn, n, 0);
    k_div(c, cc, cc, t, n, 0);
#endif
    k_cmplt(c, lt, cc, KK(C_NONE), n, M1_S2);
    k_select(c, cc, lt, KK(C_NONE), cc, n, M1_S2);
    k_cmplt(c, lt, KK(C_ONE), cc, n, M1_S1);
    k_select(c, cc, lt, KK(C_ONE), cc, n, M1_S2);
    c->arena_used = mark;
}
static void ph_shadow_geom(m1_ctx *c, KR *const g[3], KR *const r[3], KR *const rs[3], int rs_scalar, size_t n)
{
    size_t mark = c->arena_used;
    KR *d[3] = {TMP(n), TMP(n), TMP(n)}, *dn = TMP(n);
    ph_geom(c, d, dn, g[0], g[1], g[2], r, rs, rs_scalar, n);
    c->arena_used = mark;
}
/* clamp x to [-1, 1] by selects */
static void kclamp1(m1_ctx *c, KR *x, KR *lt, size_t n)
{
    KD *D = (KD *)c->k;
    k_cmplt(c, lt, x, KK(C_NONE), n, M1_S2);
    k_select(c, x, lt, KK(C_NONE), x, n, M1_S2);
    k_cmplt(c, lt, KK(C_ONE), x, n, M1_S1);
    k_select(c, x, lt, KK(C_ONE), x, n, M1_S2);
}
/* cannonball radiation pressure with a conical shadow (q2bench.c's
   srp_conical, its four cases computed for every lane and selected in its
   order of precedence: sunlit, umbra, annular, penumbra) */
static void ph_srp(m1_ctx *c, KR *const a[3], KR *nu, KR *const r[3], KR *const rs[3], int rs_scalar, const KR *cram,
                   size_t n)
{
    KD *D = (KD *)c->k;
    size_t mark = c->arena_used;
    KR *d[3] = {TMP(n), TMP(n), TMP(n)}, *dn = TMP(n), *sa = TMP(n), *sb = TMP(n), *cc = TMP(n);
    KR *A = TMP(n), *B = TMP(n), *C = TMP(n), *A2 = TMP(n), *B2 = TMP(n), *t = TMP(n), *u = TMP(n), *x = TMP(n);
    KR *y = TMP(n), *lt = TMP(n), *full = TMP(n), *umb = TMP(n), *ann = TMP(n), *nua = TMP(n), *k = TMP(n);
    ph_geom(c, d, dn, sa, sb, cc, r, rs, rs_scalar, n);
    k_asin(c, A, sa, n);
    k_asin(c, B, sb, n);
    k_acos(c, C, cc, n);
    k_add(c, t, A, B, n, 0);
    k_cmple(c, full, t, C, n, 0);           /* C >= A + B: sunlit */
    k_sub(c, t, B, A, n, 0);
    k_cmple(c, umb, C, t, n, 0);            /* C <= B - A: umbra */
    k_sub(c, t, A, B, n, 0);
    k_cmple(c, ann, C, t, n, 0);            /* C <= A - B: annular */
    k_mul(c, A2, A, A, n, 0);
    k_mul(c, B2, B, B, n, 0);
    k_div(c, t, B2, A2, n, 0);
    k_sub(c, nua, KK(C_ONE), t, n, M1_S1);  /* annular: 1 - B^2/A^2 */
    /* penumbra: x = (C^2 + A^2 - B^2)/(2C), y = sqrt(max(A^2 - x^2, 0)) */
    k_mul(c, t, C, C, n, 0);
    k_add(c, t, t, A2, n, 0);
    k_sub(c, t, t, B2, n, 0);
    k_add(c, u, C, C, n, 0);
    k_div(c, x, t, u, n, 0);
    k_mul(c, t, x, x, n, 0);
    k_sub(c, t, A2, t, n, 0);
    k_cmplt(c, lt, t, KK(C_ZERO), n, M1_S2);
    k_select(c, t, lt, KK(C_ZERO), t, n, M1_S2);
    k_sqrt(c, y, t, n);
    k_div(c, t, x, A, n, 0);                /* cos of the half-angle at the Sun's centre */
    kclamp1(c, t, lt, n);
    k_sub(c, u, C, x, n, 0);
    k_div(c, u, u, B, n, 0);                /* ... at the Earth's centre */
    kclamp1(c, u, lt, n);
    k_acos(c, t, t, n);
    k_acos(c, u, u, n);
    k_ab_p_ce(c, t, A2, t, B2, u, n, 0);    /* A^2 acos(ca) + B^2 acos(cb) */
    k_mul(c, u, C, y, n, 0);
    k_sub(c, t, t, u, n, 0);                /* the overlap's area */
    k_mul(c, u, KK(C_PI), A2, n, M1_S1);
    k_div(c, t, t, u, n, 0);
    k_sub(c, nu, KK(C_ONE), t, n, M1_S1);   /* penumbra */
    k_select(c, nu, ann, nua, nu, n, 0);
    k_select(c, nu, umb, KK(C_ZERO), nu, n, M1_S2);
    k_select(c, nu, full, KK(C_ONE), nu, n, M1_S2);
    /* a = nu P (AU/|d|)^2 cram d/|d| */
    k_div(c, t, KK(C_AU), dn, n, M1_S1);
    k_mul(c, t, t, t, n, 0);
    k_mul(c, k, KK(C_PSUN), cram, n, M1_S1);
    k_mul(c, k, k, t, n, 0);
    k_mul(c, k, k, nu, n, 0);
    k_div(c, k, k, dn, n, 0);
    for (int i = 0; i < 3; i++) k_mul(c, a[i], k, d[i], n, 0);
    c->arena_used = mark;
}

/* ------------------------------------------------------- the whole force */

/* where each series stands at t seconds after the model's epoch (host) */
static void ph_locate(m1_ctx *c, double t, long rec[3], int sub[3], double dt[3])
{
    static const int ser[3] = {M1_SER_MOON, M1_SER_SUN, M1_SER_EMB};
    for (int j = 0; j < 3; j++)
        if (m1_de_locate(c->de, ser[j], c->model.jd_epoch, t, &rec[j], &sub[j], &dt[j]))
            m1_die("t = %.3f s is outside DE421's coverage", t);
}

/* the total acceleration at t (host seconds after the epoch, on the grid all
   lanes share), in the inertial frame: (((((central + harmonics) + Sun) +
   Moon) + drag) + radiation pressure); the Sun, the Moon and the frame are
   evaluated once for the batch */
static void ph_accel(m1_ctx *c, KR *const a[3], double t, KR *const y[6], const KR *bc, const KR *cram, size_t n)
{
    KD *D = (KD *)c->k;
    const m1_model *M = &c->model;
    size_t mark = c->arena_used;
    KR *r[3] = {y[0], y[1], y[2]}, *v[3] = {y[3], y[4], y[5]};
    KR *f[3] = {TMP(n), TMP(n), TMP(n)}, *g[3] = {TMP(n), TMP(n), TMP(n)};
    KR sun[3], moon[3], tk, ct, st;
    for (int i = 0; i < 3; i++) kfill(a[i], KK(C_ZERO), n);
    if (M->sun || M->moon || M->srp) {
        long rec[3];
        int sub[3];
        double dt[3];
        ph_locate(c, t, rec, sub, dt);
        m1_ephq q = {{&rec[0], &rec[1], &rec[2]}, {&sub[0], &sub[1], &sub[2]}, {&dt[0], &dt[1], &dt[2]}};
        KR *sp[3] = {&sun[0], &sun[1], &sun[2]}, *mp[3] = {&moon[0], &moon[1], &moon[2]};
        ph_bodies(c, sp, mp, &q, 1);
    }
    if (M->central) {
        ph_central(c, f, r, n);
        for (int i = 0; i < 3; i++) k_add(c, a[i], a[i], f[i], n, 0);
    }
    if (M->nmax >= 2) {
        k_from_f64(c, &tk, &t, 1);
        ph_angle(c, &ct, &st, &tk, 1);
        ph_rot_apply(c, g, r, &ct, &st, 1, 0, n);
        ph_grav(c, f, g, M->nmin, M->nmax, n);
        ph_rot_apply(c, g, f, &ct, &st, 1, 1, n);
        for (int i = 0; i < 3; i++) k_add(c, a[i], a[i], g[i], n, 0);
    }
    if (M->sun) {
        KR *sp[3] = {&sun[0], &sun[1], &sun[2]};
        ph_third(c, f, r, sp, 1, 0, n);
        for (int i = 0; i < 3; i++) k_add(c, a[i], a[i], f[i], n, 0);
    }
    if (M->moon) {
        KR *mp[3] = {&moon[0], &moon[1], &moon[2]};
        ph_third(c, f, r, mp, 1, 1, n);
        for (int i = 0; i < 3; i++) k_add(c, a[i], a[i], f[i], n, 0);
    }
    if (M->drag) {
        ph_drag(c, f, r, v, bc, n);
        for (int i = 0; i < 3; i++) k_add(c, a[i], a[i], f[i], n, 0);
    }
    if (M->srp) {
        KR *sp[3] = {&sun[0], &sun[1], &sun[2]};
        KR *nu = TMP(n);
        ph_srp(c, f, nu, r, sp, 1, cram, n);
        for (int i = 0; i < 3; i++) k_add(c, a[i], a[i], f[i], n, 0);
    }
    (void)D;
    c->arena_used = mark;
}

/* ------------------------------------------------------------------ rk4 */

/* classical rk4 at a fixed step h (a decimal string), from step index step0
   (t = (step0 + j) h on the host's grid) for nsteps steps; cb sees every
   lane's state after every step, so a run cut into segments keeps every
   lane's state at every boundary, and a segment restarted from a boundary
   state with its step0 is the same run (designed for certificates; none is
   written). y is updated in place. */
static int ph_rk4(m1_ctx *c, KR *const y[6], const KR *bc, const KR *cram, const char *h_dec, long step0, long nsteps,
                  m1_step_cb cb, void *u, size_t n)
{
    KD *D = (KD *)c->k;
    size_t mark = c->arena_used;
    KR h, hh, h6;
    char *end = NULL;
    const double hd = strtod(h_dec, &end);
    if (!end || *end) m1_die("step \"%s\"", h_dec);
    k_from_dec(c, &h, &h_dec, 1);
    k_mul(c, &hh, &h, KK(C_HALF), 1, 0);
    k_div(c, &h6, &h, KK(C_SIX), 1, 0);
    KR *k[4][6], *tmp[6];
    for (int s = 0; s < 4; s++)
        for (int i = 0; i < 6; i++) k[s][i] = TMP(n);
    for (int i = 0; i < 6; i++) tmp[i] = TMP(n);
    for (long j = 0; j < nsteps; j++) {
        const double t = (double)(step0 + j) * hd;
        /* k1 */
        for (int i = 0; i < 3; i++) memcpy(k[0][i], y[3 + i], n * sizeof(KR));
        ph_accel(c, &k[0][3], t, y, bc, cram, n);
        for (int i = 0; i < 6; i++) k_fma(c, tmp[i], &hh, k[0][i], y[i], n, M1_S1);
        /* k2 */
        for (int i = 0; i < 3; i++) memcpy(k[1][i], tmp[3 + i], n * sizeof(KR));
        ph_accel(c, &k[1][3], t + 0.5 * hd, tmp, bc, cram, n);
        for (int i = 0; i < 6; i++) k_fma(c, tmp[i], &hh, k[1][i], y[i], n, M1_S1);
        /* k3 */
        for (int i = 0; i < 3; i++) memcpy(k[2][i], tmp[3 + i], n * sizeof(KR));
        ph_accel(c, &k[2][3], t + 0.5 * hd, tmp, bc, cram, n);
        for (int i = 0; i < 6; i++) k_fma(c, tmp[i], &h, k[2][i], y[i], n, M1_S1);
        /* k4 */
        for (int i = 0; i < 3; i++) memcpy(k[3][i], tmp[3 + i], n * sizeof(KR));
        ph_accel(c, &k[3][3], t + hd, tmp, bc, cram, n);
        /* y += h/6 (k1 + 2 k2 + 2 k3 + k4) */
        for (int i = 0; i < 6; i++) {
            k_fma(c, tmp[i], KK(C_TWO), k[1][i], k[0][i], n, M1_S1);
            k_fma(c, tmp[i], KK(C_TWO), k[2][i], tmp[i], n, M1_S1);
            k_add(c, tmp[i], tmp[i], k[3][i], n, 0);
            k_fma(c, y[i], &h6, tmp[i], y[i], n, M1_S1);
        }
        if (cb) cb(u, step0 + j + 1, (double)(step0 + j + 1) * hd, (void *const *)y, n);
    }
    c->arena_used = mark;
    return 0;
}

/* ------------------------------------------------------------ the generic op */

static void ph_op(m1_ctx *c, m1_opcode op, KR *d, const KR *a, const KR *b, const KR *e, size_t n, unsigned sm)
{
    switch (op) {
    case M1_ADD: k_add(c, d, a, b, n, sm); break;
    case M1_SUB: k_sub(c, d, a, b, n, sm); break;
    case M1_MUL: k_mul(c, d, a, b, n, sm); break;
    case M1_DIV: k_div(c, d, a, b, n, sm); break;
    case M1_FMA: k_fma(c, d, a, b, e, n, sm); break;
    case M1_SQRT: k_sqrt(c, d, a, n); break;
    case M1_NEG: k_neg(c, d, a, n); break;
    case M1_EXP: k_exp(c, d, a, n); break;
    case M1_SIN: k_sin(c, d, a, n); break;
    case M1_COS: k_cos(c, d, a, n); break;
    case M1_ASIN: k_asin(c, d, a, n); break;
    case M1_ACOS: k_acos(c, d, a, n); break;
    case M1_CMPLT: k_cmplt(c, d, a, b, n, sm); break;
    case M1_CMPLE: k_cmple(c, d, a, b, n, sm); break;
    case M1_SELECT: k_select(c, d, a, b, e, n, sm); break;
    default: m1_die("op %d", (int)op);
    }
}
