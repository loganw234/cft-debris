/* m1_common.c - cft-debris M1: what every kind shares - the arena of
 * temporaries, the error exit, and the table of kinds.
 * cft-debris, MIT licence (see LICENSE at the repository root). Written by
 * DEBRIS-E, 2026-11-13. */
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "m1.h"

void m1_die(const char *fmt, ...)
{
    va_list ap;
    fprintf(stderr, "m1: ");
    va_start(ap, fmt);
    vfprintf(stderr, fmt, ap);
    va_end(ap);
    fprintf(stderr, "\n");
    fflush(stderr);
    exit(3);
}

void *m1_tmp(m1_ctx *c, size_t bytes)
{
    size_t at = (c->arena_used + 63) & ~(size_t)63;
    if (at + bytes > c->arena_cap)
        m1_die("arena exhausted: %lu + %lu > %lu bytes", (unsigned long)at, (unsigned long)bytes,
               (unsigned long)c->arena_cap);
    c->arena_used = at + bytes;
    return c->arena + at;
}

const m1_vt *m1_vt_of(m1_kind k)
{
    switch (k) {
    case M1_NATIVE32: return &m1_vt_native32;
    case M1_NATIVE64: return &m1_vt_native64;
    case M1_CFT32: return &m1_vt_cft32;
    case M1_CFT64: return &m1_vt_cft64;
    case M1_CFT128: return &m1_vt_cft128;
    case M1_CFT256: return &m1_vt_cft256;
    default: return NULL;
    }
}

const m1_vt *m1_vt_by_name(const char *name)
{
    for (int k = 0; k < M1_NKIND; k++)
        if (!strcmp(m1_vt_of((m1_kind)k)->name, name)) return m1_vt_of((m1_kind)k);
    return NULL;
}
