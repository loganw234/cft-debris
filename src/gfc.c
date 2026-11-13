/* gfc.c - cft-debris M1: an ICGEM .gfc loader that keeps every coefficient as
 * the decimal string the file writes, so that each number kind converts it
 * once, correctly rounded (m1_physics.h's setup).
 *
 * cft-debris, MIT licence (see LICENSE at the repository root). Written by
 * DEBRIS-E, 2026-11-13; the checks follow DEBRIS-C's m1a_grav.c read_gfc().
 *
 * Read: the header's earth_gravity_constant, radius, max_degree, norm,
 * tide_system and modelname, up to end_of_head; then every "gfc n m C S ..."
 * line. A Fortran exponent letter (D or d) is written as e (counted). A
 * duplicated (n, m) is kept once, and refused unless its values equal the
 * first (EIGEN6-C4.gfc writes (0, 0) twice, as 1.00000000000E+00 and
 * 0.10000000000E+01: lead.md, 2026-11-12 18:07). Any other data key
 * (gfct, trnd, acos, asin) is counted; the caller refuses a file with any.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "m1.h"

static char *dupstr(const char *s)
{
    size_t n = strlen(s);
    char *p = (char *)malloc(n + 1);
    if (!p) m1_die("out of memory");
    memcpy(p, s, n + 1);
    return p;
}

static int fix_exp(char *s)
{
    int k = 0;
    for (char *p = s; *p; p++)
        if (*p == 'D' || *p == 'd') {
            *p = 'e';
            k++;
        }
    return k;
}

int m1_gfc_load(m1_gfc *g, const char *path, int nmax)
{
    memset(g, 0, sizeof *g);
    g->nmax = nmax;
    g->max_degree = -1;
    size_t nt = M1_TRI(nmax, nmax) + 1;
    g->c = (char **)calloc(nt, sizeof(char *));
    g->s = (char **)calloc(nt, sizeof(char *));
    if (!g->c || !g->s) m1_die("out of memory");
    FILE *f = fopen(path, "r");
    if (!f) {
        snprintf(g->err, sizeof g->err, "cannot open %s", path);
        return -1;
    }
    char line[512];
    int head = 1;
    while (fgets(line, sizeof line, f)) {
        char key[64], v1[128], v2[128], v3[128], v4[128];
        if (sscanf(line, "%63s", key) != 1) continue;
        if (head) {
            if (!strncmp(key, "end_of_head", 11)) {
                head = 0;
                continue;
            }
            if (sscanf(line, "%63s %127s", key, v1) == 2) {
                if (!strcmp(key, "earth_gravity_constant")) snprintf(g->gm, sizeof g->gm, "%.60s", v1);
                else if (!strcmp(key, "radius")) snprintf(g->radius, sizeof g->radius, "%.60s", v1);
                else if (!strcmp(key, "max_degree")) g->max_degree = atoi(v1);
                else if (!strcmp(key, "norm")) snprintf(g->norm, sizeof g->norm, "%.60s", v1);
                else if (!strcmp(key, "tide_system")) snprintf(g->tide, sizeof g->tide, "%.60s", v1);
                else if (!strcmp(key, "modelname")) snprintf(g->modelname, sizeof g->modelname, "%.60s", v1);
            }
            continue;
        }
        if (strcmp(key, "gfc")) {
            g->nother++;
            continue;
        }
        if (sscanf(line, "%*s %127s %127s %127s %127s", v1, v2, v3, v4) != 4) {
            snprintf(g->err, sizeof g->err, "bad line: %.200s", line);
            fclose(f);
            return -2;
        }
        int n = atoi(v1), m = atoi(v2);
        if (n < 0 || m < 0 || m > n) {
            snprintf(g->err, sizeof g->err, "bad degree/order: %.200s", line);
            fclose(f);
            return -2;
        }
        g->ndexp += fix_exp(v3) + fix_exp(v4);
        g->ngfc++;
        if (n > nmax) continue;
        size_t i = M1_TRI(n, m);
        if (g->c[i]) {
            g->ndup++;
            if (strtod(g->c[i], NULL) != strtod(v3, NULL) || strtod(g->s[i], NULL) != strtod(v4, NULL)) {
                snprintf(g->err, sizeof g->err, "conflicting duplicate (%d,%d)", n, m);
                fclose(f);
                return -3;
            }
            continue;
        }
        g->c[i] = dupstr(v3);
        g->s[i] = dupstr(v4);
    }
    fclose(f);
    for (int n = 0; n <= nmax; n++)
        for (int m = 0; m <= n; m++)
            if (!g->c[M1_TRI(n, m)]) {
                if (n == 1) g->nmissing_deg1++;
                else g->nmissing++;
            }
    if (strcmp(g->norm, "fully_normalized") || g->nother || g->nmissing || !g->gm[0] || !g->radius[0] ||
        g->max_degree < nmax) {
        snprintf(g->err, sizeof g->err, "the coefficient file is not what the conventions say (norm %s, other keys %d, "
                 "missing %d, max_degree %d)", g->norm, g->nother, g->nmissing, g->max_degree);
        return -4;
    }
    return 0;
}

void m1_gfc_free(m1_gfc *g)
{
    if (g->c) {
        size_t nt = M1_TRI(g->nmax, g->nmax) + 1;
        for (size_t i = 0; i < nt; i++) {
            free(g->c[i]);
            free(g->s[i]);
        }
    }
    free(g->c);
    free(g->s);
    memset(g, 0, sizeof *g);
}
