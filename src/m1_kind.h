/* m1_kind.h - cft-debris M1: one number kind, assembled. Each src/kind_*.c
 * defines the kind's macros and includes this file once; so the physics
 * (m1_physics.h) is one source compiled once per kind, with no per-kind copy.
 *
 * cft-debris, MIT licence (see LICENSE at the repository root). Written by
 * DEBRIS-E, 2026-11-13.
 *
 * Why C11 and an included header rather than C++ templates: the cft kinds'
 * elements are opaque byte arrays reached only through libcft's C API, the
 * native kinds need intrinsics and exact control of each expression's
 * rounding, and the build checks each kind's object file on its own (vfmadd
 * present, no call to fma); one plain C translation unit per kind keeps every
 * one of those visible, where templates would hide them in instantiations.
 *
 * Expected: KNAME (native32 ...), KIND_ID, K_NATIVE (1 or 0), and
 *   native: K_BITS (32 or 64), K_REAL (float or double)
 *   cft:    K_ESZ (4, 8, 16 or 32), K_CFTFMT (CFT_FP32 ...)
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "m1.h"

#if K_NATIVE
#include "m1_ops_native.h"
#else
#include "m1_ops_cft.h"
#endif
#include "m1_physics.h"

#define KCAT2_(a, b) a##b
#define KCAT2(a, b) KCAT2_(a, b)
#define KSTR_(a) #a
#define KSTR(a) KSTR_(a)

/* the entry points, with void pointers for the drivers */
static int e_setup(m1_ctx *c, const m1_model *m, const m1_gfc *g, const m1_de *de, size_t max_lanes)
{
    c->kind = KIND_ID;
    return ph_setup(c, m, g, de, max_lanes);
}
static void e_from_f64(m1_ctx *c, void *d, const double *s, size_t n) { k_from_f64(c, (KR *)d, s, n); }
static void e_from_dec(m1_ctx *c, void *d, const char *const *s, size_t n) { k_from_dec(c, (KR *)d, s, n); }
static void e_to_f64(m1_ctx *c, double *d, const void *s, size_t n) { k_to_f64(c, d, (const KR *)s, n); }
static void e_op(m1_ctx *c, m1_opcode op, void *d, const void *a, const void *b, const void *e, size_t n, unsigned sm)
{
    ph_op(c, op, (KR *)d, (const KR *)a, (const KR *)b, (const KR *)e, n, sm);
}
static void e_grav(m1_ctx *c, void *const a[3], const void *const rb[3], int nmin, int nmax, size_t n)
{
    ph_grav(c, (KR *const *)a, (KR *const *)rb, nmin, nmax, n);
}
static void e_central(m1_ctx *c, void *const a[3], const void *const r[3], size_t n)
{
    ph_central(c, (KR *const *)a, (KR *const *)r, n);
}
static void e_third(m1_ctx *c, void *const a[3], const void *const r[3], const void *const s[3], int s_scalar, int body,
                    size_t n)
{
    ph_third(c, (KR *const *)a, (KR *const *)r, (KR *const *)s, s_scalar, body, n);
}
static void e_series(m1_ctx *c, void *const out[3], int k, const long *rec, const int *sub, const double *dt, size_t n)
{
    ph_series(c, (KR *const *)out, k, rec, sub, dt, n);
}
static void e_bodies(m1_ctx *c, void *const sun[3], void *const moon[3], const m1_ephq *q, size_t n)
{
    ph_bodies(c, (KR *const *)sun, (KR *const *)moon, q, n);
}
static void e_pleph(m1_ctx *c, void *const out[3], int target, int center, const m1_ephq *q, size_t n)
{
    ph_pleph(c, (KR *const *)out, target, center, q, n);
}
static void e_rotate(m1_ctx *c, void *const rb[3], const void *const r[3], const void *t, int t_scalar, int inverse,
                     size_t n)
{
    ph_rotate(c, (KR *const *)rb, (KR *const *)r, (const KR *)t, t_scalar, inverse, n);
}
static void e_drag(m1_ctx *c, void *const a[3], const void *const r[3], const void *const v[3], const void *bc, size_t n)
{
    ph_drag(c, (KR *const *)a, (KR *const *)r, (KR *const *)v, (const KR *)bc, n);
}
static void e_shadow_geom(m1_ctx *c, void *const g[3], const void *const r[3], const void *const rs[3], int rs_scalar,
                          size_t n)
{
    ph_shadow_geom(c, (KR *const *)g, (KR *const *)r, (KR *const *)rs, rs_scalar, n);
}
static void e_srp(m1_ctx *c, void *const a[3], void *nu, const void *const r[3], const void *const rs[3], int rs_scalar,
                  const void *cram, size_t n)
{
    ph_srp(c, (KR *const *)a, (KR *)nu, (KR *const *)r, (KR *const *)rs, rs_scalar, (const KR *)cram, n);
}
static void e_accel(m1_ctx *c, void *const a[3], double t, const void *const y[6], const void *bc, const void *cram,
                    size_t n)
{
    ph_accel(c, (KR *const *)a, t, (KR *const *)y, (const KR *)bc, (const KR *)cram, n);
}
static int e_rk4(m1_ctx *c, void *const y[6], const void *bc, const void *cram, const char *h_dec, long step0,
                 long nsteps, m1_step_cb cb, void *u, size_t n)
{
    return ph_rk4(c, (KR *const *)y, (const KR *)bc, (const KR *)cram, h_dec, step0, nsteps, cb, u, n);
}

const m1_vt KCAT2(m1_vt_, KNAME) = {
    KIND_ID, KSTR(KNAME), sizeof(KR), K_NATIVE,
    e_setup, ph_teardown, ph_tables, e_from_f64, e_from_dec, e_to_f64, e_op,
    e_grav, e_central, e_third, e_series, e_bodies, e_pleph, e_rotate, e_drag, e_shadow_geom, e_srp, e_accel, e_rk4,
};
