/* m1_consts.h - cft-debris M1: every physical and numerical constant, as the
 * exact decimal string each kind converts once (correctly rounded: libcft's
 * cft_from_decimal_char in the cft kinds, the C library's strtod / strtof in
 * the native kinds; E1 holds the two to the same bits), with its source.
 *
 * cft-debris, MIT licence (see LICENSE at the repository root). Written by
 * DEBRIS-E, 2026-11-13.
 *
 * Not here, because they come from the input files: the field's GM and
 * reference radius and its coefficients (the .gfc file's own decimal strings,
 * gfc.c), and DE421's EMRAT and AU (binary64 values in the binary's first
 * record; each kind converts the binary64 value, exact at binary64 and wider).
 */
#ifndef M1_CONSTS_H
#define M1_CONSTS_H

typedef struct m1_const_def {
    const char *name, *dec, *source;
} m1_const_def;

static const m1_const_def M1_CONSTS[] = {
    {"ZERO", "0", "the number"},
    {"ONE", "1", "the number"},
    {"NONE", "-1", "the number"},
    {"TWO", "2", "the number"},
    {"SIX", "6", "the number"},
    {"HALF", "0.5", "the number"},
    {"NHALF", "-0.5", "the number"},
    {"KM", "1000", "metres per kilometre"},
    {"PI", "3.141592653589793238462643383279502884197169399375105820974944592307816406286208998628034825342117068",
     "pi, 100 digits (the 100-digit truncation is 1e-100 from pi, far inside binary256's half-ulp)"},
    {"GM_SUN", "1.32712442076e20", "m^3/s^2, GROOPS's value: Lasser et al.'s 00README_simulation.txt, section 03"},
    {"GM_MOON", "0.49028010560e13", "m^3/s^2, GROOPS's value: Lasser et al.'s 00README_simulation.txt, section 03"},
    {"OMEGA_E", "7.292115e-5", "rad/s, uniform Earth rotation (decision 6): DEBRIS-B's q2bench.c, DEBRIS-D's q4prop.c"},
    {"THETA0", "0.3", "rad, the rotation angle at t = 0: DEBRIS-D's q4prop.c (TH0)"},
    {"R_EARTH", "6378136.3", "m, the body radius for altitude and shadow: DEBRIS-B's q2bench.c (6378.1363 km)"},
    {"R_SUN", "6.96e8", "m, DEBRIS-B's q2bench.c (696000 km)"},
    {"AU_M", "149597870700", "m, the astronomical unit, IAU 2012 Resolution B2 (q2bench.c's 149597870.7 km)"},
    {"P_SUN", "4.56e-6", "N/m^2, solar radiation pressure at 1 AU: DEBRIS-B's q2bench.c"},
};
#define M1_NCONSTS (sizeof M1_CONSTS / sizeof M1_CONSTS[0])

/* the exponential atmosphere: 28 bands, DEBRIS-B's q2bench.c table (base
   altitude, density at the base, scale height), its km turned into m by a
   shift of the decimal point (exact) */
static const char *const M1_ATM_H0[28] = {
    "0", "25000", "30000", "40000", "50000", "60000", "70000", "80000", "90000", "100000", "110000", "120000",
    "130000", "140000", "150000", "180000", "200000", "250000", "300000", "350000", "400000", "450000", "500000",
    "600000", "700000", "800000", "900000", "1000000"};
static const char *const M1_ATM_RHO0[28] = {
    "1.225", "3.899e-2", "1.774e-2", "3.972e-3", "1.057e-3", "3.206e-4", "8.770e-5", "1.905e-5", "3.396e-6",
    "5.297e-7", "9.661e-8", "2.438e-8", "8.484e-9", "3.845e-9", "2.070e-9", "5.464e-10", "2.789e-10", "7.248e-11",
    "2.418e-11", "9.518e-12", "3.725e-12", "1.585e-12", "6.967e-13", "1.454e-13", "3.614e-14", "1.170e-14",
    "5.245e-15", "3.019e-15"};
static const char *const M1_ATM_HS[28] = {
    "7249", "6349", "6682", "7554", "8382", "7714", "6549", "5799", "5382", "5877", "7263", "9473", "12636",
    "16149", "22523", "29740", "37105", "45546", "53628", "53298", "58515", "60828", "63822", "71835", "88667",
    "124640", "181050", "268000"};

#endif
