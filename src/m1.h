/* m1.h - cft-debris M1, the CPU reference propagator: the public interface.
 *
 * cft-debris, MIT licence (see LICENSE at the repository root). Written by
 * DEBRIS-E, 2026-11-13.
 *
 * One force-model source (m1_physics.h) is compiled once per NUMBER KIND:
 *   native32  C float,  IEEE binary32 in hardware
 *   native64  C double, IEEE binary64 in hardware
 *   cft32, cft64, cft128, cft256  libcft's software backend (cft_open(NULL,..))
 * through a number layer whose every operation acts on a batch of LANES, one
 * object a lane (m1_ops_native.h, m1_ops_cft.h). Each kind exports one table
 * of entry points, m1_vt, so that drivers are written once for every kind.
 *
 * Vectors are arrays of n lanes, each element esz bytes, in the kind's own
 * encoding (IEEE interchange encodings, little-endian). A "scalar" operand is
 * one element that applies to every lane (scalar masks below).
 */
#ifndef M1_H
#define M1_H

#include <stddef.h>
#include <stdint.h>
#include "cft.h"

typedef enum m1_kind {
    M1_NATIVE32 = 0, M1_NATIVE64, M1_CFT32, M1_CFT64, M1_CFT128, M1_CFT256, M1_NKIND
} m1_kind;

#define M1_NMAX 180              /* gravity degree supported */

/* operation counters: lane-operations, by kind of operation */
enum {
    M1_OP_ADD, M1_OP_SUB, M1_OP_MUL, M1_OP_DIV, M1_OP_SQRT, M1_OP_FMA, M1_OP_NEG,
    M1_OP_CMP, M1_OP_SEL, M1_OP_EXP, M1_OP_SIN, M1_OP_COS, M1_OP_ASIN, M1_OP_ACOS,
    M1_OP_CVT, M1_NOP
};

/* generic operations the drivers may issue through m1_vt.op */
typedef enum m1_opcode {
    M1_ADD, M1_SUB, M1_MUL, M1_DIV, M1_FMA, M1_SQRT, M1_NEG, M1_EXP, M1_SIN, M1_COS,
    M1_ASIN, M1_ACOS, M1_CMPLT, M1_CMPLE, M1_SELECT
} m1_opcode;

/* scalar-mask bits: operand 1, 2, 3, 4 is one element applied to every lane */
#define M1_S1 1u
#define M1_S2 2u
#define M1_S3 4u
#define M1_S4 8u

/* ------------------------------------------------------------------ inputs */

/* the .gfc file, kept as decimal strings (gfc.c) */
typedef struct m1_gfc {
    char gm[64], radius[64], modelname[64], norm[64], tide[64];
    int max_degree;
    int nmax;                 /* coefficients kept: degree 0..nmax */
    char **c, **s;            /* triangular index n(n+1)/2 + m; NULL = absent (zero) */
    int ngfc, ndup, nother, nmissing, nmissing_deg1, ndexp;
    char err[256];
} m1_gfc;
int  m1_gfc_load(m1_gfc *g, const char *path, int nmax);
void m1_gfc_free(m1_gfc *g);
#define M1_TRI(n, m) ((size_t)(n) * ((size_t)(n) + 1) / 2 + (size_t)(m))

/* the DE421 binary (de421.c): host part only - the header, the records,
   and the choice of a record and sub-interval for a time */
typedef struct m1_de {
    double ss[3];             /* first JED, last JED, record length (days) */
    double au_km, emrat;      /* from the binary's first record */
    int ipt[13][3];           /* offset (1-based), coefficients, sub-intervals */
    int ncoeff, numde, ncon;
    long nrec;
    unsigned char *raw;       /* the whole file */
    size_t rawlen;
    char err[256];
} m1_de;
int  m1_de_open(m1_de *de, const char *bin_path, const char *header_path);
void m1_de_close(m1_de *de);
const double *m1_de_record(const m1_de *de, long i);
/* series k (0 Mercury .. 9 Moon, 10 Sun; 2 is the EMB) at the time
   jd0 + sec/86400, jd0 a JED that is a multiple of 1/2 day and sec seconds:
   the record, the sub-interval, and the time since the sub-interval's start
   in seconds (exact whenever (jd0 - first JED)*86400 + sec is). Returns 0, or
   -1 outside the coverage. */
int m1_de_locate(const m1_de *de, int k, double jd0, double sec, long *rec, int *sub, double *dt_sec);
#define M1_SER_EMB 2
#define M1_SER_MOON 9
#define M1_SER_SUN 10

/* ---------------------------------------------------------------- the model */

#define M1_MAXBANDS 28
typedef struct m1_model {
    int central, nmin, nmax, sun, moon, drag, srp;   /* forces on (1) or off (0) */
    int nbands;               /* the exponential atmosphere: 28 (q2bench.c's table) or 1 */
    const char *band_h0, *band_rho0, *band_hs;        /* nbands == 1: decimal strings (m, kg/m^3, m) */
    double jd_epoch;          /* TDB JED of t = 0, a multiple of 1/2 day */
} m1_model;

/* ------------------------------------------------------------------ context */

typedef struct m1_ctx {
    m1_kind kind;
    size_t esz;
    cft_device *dev;          /* libcft software handle */
    int cr_transc;            /* native kinds: route exp, sin, cos, asin, acos to libcft */
    int ctl_round64;          /* E3's planted control: one intermediate rounded to binary64 */
    int ctl_c20;              /* E6/E7 planted controls: C20 scaled by (1 + ctl_c20_rel) */
    double ctl_c20_rel;
    uint64_t nops[M1_NOP];
    uint32_t cft_flags;       /* sticky IEEE flags raised inside libcft calls */
    const m1_gfc *gfc;
    const m1_de *de;
    m1_model model;
    int nmax;                 /* gravity tables built to this degree */
    void *k;                  /* the kind's own data */
    unsigned char *arena;     /* temporaries */
    size_t arena_cap, arena_used;
    unsigned char *vw;        /* the gravity recursion's V and W tables */
    size_t vw_cap;
} m1_ctx;

/* the per-series locations of n lanes, for the ephemeris */
typedef struct m1_ephq {
    const long *rec[3];       /* [0] Moon, [1] Sun, [2] EMB */
    const int *sub[3];
    const double *dt_sec[3];  /* seconds since the sub-interval's start (host values) */
} m1_ephq;

typedef void (*m1_table_cb)(void *u, const char *name, const void *p, size_t count);
typedef void (*m1_step_cb)(void *u, long step, double t, void *const y[6], size_t n);

typedef struct m1_vt {
    m1_kind kind;
    const char *name;
    size_t esz;
    int native;
    /* setup: constants, coefficients and derived tables (to model->nmax);
       returns 0 or a negative error */
    int  (*setup)(m1_ctx *c, const m1_model *model, const m1_gfc *g, const m1_de *de, size_t max_lanes);
    void (*teardown)(m1_ctx *c);
    void (*tables)(m1_ctx *c, m1_table_cb cb, void *u);
    /* conversions into and out of the kind */
    void (*from_f64)(m1_ctx *c, void *d, const double *s, size_t n);
    void (*from_dec)(m1_ctx *c, void *d, const char *const *s, size_t n);
    void (*to_f64)(m1_ctx *c, double *d, const void *s, size_t n);
    /* one generic operation (drivers) */
    void (*op)(m1_ctx *c, m1_opcode op, void *d, const void *a, const void *b, const void *e,
               size_t n, unsigned sm);
    /* kernels; a[], r[] etc. are arrays of 3 vectors */
    void (*grav)(m1_ctx *c, void *const a[3], const void *const rb[3], int nmin, int nmax, size_t n);
    void (*central)(m1_ctx *c, void *const a[3], const void *const r[3], size_t n);
    void (*third)(m1_ctx *c, void *const a[3], const void *const r[3], const void *const s[3],
                  int s_scalar, int body, size_t n);       /* body 0 the Sun, 1 the Moon */
    void (*series)(m1_ctx *c, void *const out[3], int k, const long *rec, const int *sub,
                   const double *dt_sec, size_t n);      /* km, as the file stores it */
    void (*bodies)(m1_ctx *c, void *const sun[3], void *const moon[3], const m1_ephq *q, size_t n);
    void (*pleph)(m1_ctx *c, void *const out[3], int target, int center, const m1_ephq *q, size_t n); /* AU */
    void (*rotate)(m1_ctx *c, void *const rb[3], const void *const r[3], const void *t, int t_scalar,
                   int inverse, size_t n);
    void (*drag)(m1_ctx *c, void *const a[3], const void *const r[3], const void *const v[3],
                 const void *bc, size_t n);
    void (*shadow_geom)(m1_ctx *c, void *const g[3], const void *const r[3], const void *const rs[3],
                        int rs_scalar, size_t n);       /* sin A, sin B, cos C */
    void (*srp)(m1_ctx *c, void *const a[3], void *nu, const void *const r[3], const void *const rs[3],
                int rs_scalar, const void *cram, size_t n);
    void (*accel)(m1_ctx *c, void *const a[3], double t, const void *const y[6], const void *bc,
                  const void *cram, size_t n);
    int  (*rk4)(m1_ctx *c, void *const y[6], const void *bc, const void *cram, const char *h_dec,
                long step0, long nsteps, m1_step_cb cb, void *u, size_t n);
} m1_vt;

extern const m1_vt m1_vt_native32, m1_vt_native64, m1_vt_cft32, m1_vt_cft64, m1_vt_cft128, m1_vt_cft256;
const m1_vt *m1_vt_of(m1_kind k);
const m1_vt *m1_vt_by_name(const char *name);

/* the arena (m1_common.c) */
void *m1_tmp(m1_ctx *c, size_t bytes);
void  m1_die(const char *fmt, ...);

#endif
