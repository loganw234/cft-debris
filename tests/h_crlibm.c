/* h_crlibm.c - cft-debris M1 (DEBRIS-H): an experiment for the fit diagnostic: exp, asin and acos correctly rounded
 * (round to nearest even), computed by libcft's cft_exp, cft_asin and cft_acos at binary64, in place of the C library's.
 *
 * cft-debris, MIT licence (see LICENSE at the repository root). Written by DEBRIS-H, 2026-11-18. Linked into a copy of
 * tests/h_fitdiag.c's program, it defines these three symbols, so the diagnostic's wrappers (__real_exp and so on) reach
 * them instead of the C library: the fit then runs as it would on a machine whose C library is correctly rounded on
 * every call it makes. src/ and tests/h_fitdiag.c are used as they are.
 */
#include <stdint.h>
#include <stdlib.h>
#include "cft.h"

static cft_device *dev = NULL;
static double cr1(cft_status (*fn)(cft_device *, cft_format, cft_round, const void *, void *, size_t, uint32_t *), double x)
{
    if (!dev && cft_open(NULL, 0, &dev) != CFT_OK) abort();
    double y;
    uint32_t fl = 0;
    if (fn(dev, CFT_FP64, CFT_RNE, &x, &y, 1, &fl) != CFT_OK) abort();
    return y;
}
double exp(double x) { return cr1(cft_exp, x); }
double asin(double x) { return cr1(cft_asin, x); }
double acos(double x) { return cr1(cft_acos, x); }
