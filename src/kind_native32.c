/* kind_native32.c - cft-debris M1: the native32 kind (C float, IEEE binary32
 * in hardware). cft-debris, MIT licence (see LICENSE at the repository root).
 * Build: -std=c11 -ffp-contract=off -mfma (decision 3); see tests/build.sh. */
#define KNAME native32
#define KIND_ID M1_NATIVE32
#define K_NATIVE 1
#define K_BITS 32
#define K_REAL float
#include "m1_kind.h"
