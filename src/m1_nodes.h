/* m1_nodes.h - cft-debris M1 (DEBRIS-F): the Earth's orientation, IERS Conventions (2010), CIO-based,
 * computed at binary256 through libcft - the node routine of the frame table, and the host time scales.
 *
 * cft-debris, MIT licence (see LICENSE at the repository root). Written by DEBRIS-F, 2026-11-16.
 *
 *   [GCRS] = Q(t) R(t) W(t) [ITRS]                       IERS Conventions (2010), chapter 5, eq. (5.1)
 *   Q from X, Y (tab5.2a, tab5.2b), s (tab5.2d) and dX, dY  eq. (5.10), (5.16)
 *   R = R3(-ERA), ERA from UT1                              eq. (5.5), (5.14)
 *   W = R3(-s') R2(xp) R1(yp), s' = -47 uas t                eq. (5.3), (5.13)
 * Time: M1's t is TDB seconds from jd_epoch (an integer MJD here). TT = TDB - (TDB-TT), the latter from USNO
 * Circular 179, eq. (2.6); TAI = TT - 32.184 s; UTC = TAI - (TAI-UTC) from tai-utc.dat; UT1 = UTC + (UT1-UTC).
 * The series are evaluated by angle addition: the sines and cosines of the 14 fundamental arguments only,
 * their integer multiples by complex multiplication, each term a product of at most 6 of them.
 * The input files are read from the downloads folder at run time; none is copied into the repository.
 */
#ifndef M1_NODES_H
#define M1_NODES_H
#include <stddef.h>
#include "cft.h"

#define M1N_NCOL 12          /* M (row-major, 9: GCRS <- ITRS), then Omega (3, rad/s, GCRS components) */

typedef struct m1n_ctx m1n_ctx;

/* the host time scales (B1), binary64 / exact integers */
typedef struct m1n_leap { double jd, a, mjd0, rate; } m1n_leap;
int    m1n_leaps_load(const char *path, m1n_leap *tab, int cap);              /* returns the count, or -1 */
double m1n_tai_minus_utc(const m1n_leap *tab, int n, double mjd_utc);        /* s */
double m1n_tdb_minus_tt(double t_tt_centuries);                             /* s, Circular 179 eq. (2.6) */

/* open: the series tables, the Earth orientation file, the leap seconds, from dl (the downloads folder,
   ending in '/'); jd_epoch must be an integer MJD + 2400000.5. Returns NULL with a message on stderr. */
m1n_ctx *m1n_open(const char *dl, double jd_epoch);
void     m1n_close(m1n_ctx *n);
const char *m1n_inputs(const m1n_ctx *n);   /* the input files and their SHA-256, for logs */

/* the time scales alone at n times t (TDB s from jd_epoch): out n x 5 binary64 - TAI s from mjd_epoch 0h TAI,
   TAI-UTC, TT-TAI, TDB-TT, UT1-UTC (s); UT1-UTC by the same binary256 interpolation the frame uses */
int m1n_times(m1n_ctx *n, const double *t, size_t nt, double *out);
/* TAI-UTC (s) at a UTC MJD, from the leap table in use; and replace that table (a control) */
double m1n_dat(const m1n_ctx *n, double mjd_utc);
int    m1n_set_leaps(m1n_ctx *n, const char *path);

/* plants (controls): added to every evaluation from now on (radians) */
void m1n_plant(m1n_ctx *n, double dx_rad, double xp_rad);

/* direct evaluation at n times t (TDB s from jd_epoch, binary64, exact): the series at each time itself,
   ERA's cosine and sine by cospi/sinpi. out: n x 12 binary256 elements (32 bytes each), row-major per time.
   aux (may be NULL): n x 10 binary64 - X, Y, s, ERA (turns, fraction), xp, yp, UT1-UTC, dX, dY, TDB-TT. */
int m1n_direct(m1n_ctx *n, const double *t, size_t nt, unsigned char *out, double *aux);

/* the table: fine nodes t_k = t0 + k h for k = 0..nk-1 (h a power of two, seconds), the slow quantities at
   coarse nodes every H = 64 h interpolated to them (8-point Lagrange), ERA advanced by angle addition, and
   Omega from central differences of M at t_k +- 1/8 s. Writes path (a text header, "END\n", then nk x 12
   binary256 elements, little-endian as libcft stores them). Returns 0. */
int m1n_build(m1n_ctx *n, double t0, double h, long nk, const char *path, const char *note);

/* SHA-256 of a file, lowercase hex (FIPS 180-4); 0, or -1 if unreadable */
int m1n_sha256_file(const char *path, char out[65]);

#endif
