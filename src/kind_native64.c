/* kind_native64.c - cft-debris M1: the native64 kind (C double, IEEE binary64
 * in hardware). cft-debris, MIT licence (see LICENSE at the repository root).
 * Build: -std=c11 -ffp-contract=off -mfma (decision 3); see tests/build.sh. */
#define KNAME native64
#define KIND_ID M1_NATIVE64
#define K_NATIVE 1
#define K_BITS 64
#define K_REAL double
#include "m1_kind.h"
