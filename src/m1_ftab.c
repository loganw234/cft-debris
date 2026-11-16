/* m1_ftab.c - cft-debris M1 (DEBRIS-F): loading the frame table that src/m1_nodes.c's m1n_build writes.
 * cft-debris, MIT licence (see LICENSE at the repository root). Written by DEBRIS-F, 2026-11-16.
 * The file: text header lines ("key value"), "END", then nk x ncol binary256 elements, little-endian. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "m1.h"
#include "m1_nodes.h"

int m1_ftab_load(m1_ftab *ft, const char *path)
{
    memset(ft, 0, sizeof *ft);
    FILE *f = fopen(path, "rb");
    if (!f) { snprintf(ft->err, sizeof ft->err, "cannot read %s", path); return -1; }
    char line[4096];
    int got = 0, end = 0;
    while (fgets(line, sizeof line, f)) {
        if (!strcmp(line, "END\n")) { end = 1; break; }
        char key[64];
        if (sscanf(line, "%63s", key) != 1) continue;
        const char *v = line + strlen(key);
        if (!strcmp(key, "jd_epoch")) { ft->jd_epoch = strtod(v, NULL); got |= 1; }
        else if (!strcmp(key, "t0")) { ft->t0 = strtod(v, NULL); got |= 2; }
        else if (!strcmp(key, "h")) { ft->h = strtod(v, NULL); got |= 4; }
        else if (!strcmp(key, "nk")) { ft->nk = atol(v); got |= 8; }
        else if (!strcmp(key, "ncol")) { ft->ncol = atoi(v); got |= 16; }
        else if (!strcmp(key, "note")) { snprintf(ft->note, sizeof ft->note, "%s", v + 1); ft->note[strcspn(ft->note, "\r\n")] = 0; }
    }
    if (!end || got != 31 || ft->nk < 8 || ft->ncol != 12) {
        fclose(f);
        snprintf(ft->err, sizeof ft->err, "%s: bad header", path);
        return -1;
    }
    size_t ne = (size_t)ft->nk * (size_t)ft->ncol;
    ft->raw = (unsigned char *)malloc(ne * 32);
    if (!ft->raw || fread(ft->raw, 32, ne, f) != ne) {
        fclose(f);
        snprintf(ft->err, sizeof ft->err, "%s: short payload", path);
        return -1;
    }
    fclose(f);
    if (m1n_sha256_file(path, ft->sha256)) { snprintf(ft->err, sizeof ft->err, "%s: unreadable", path); return -1; }
    return 0;
}

void m1_ftab_free(m1_ftab *ft)
{
    free(ft->raw);
    ft->raw = NULL;
}
