/* m1nodes.c - cft-debris M1 (DEBRIS-F): the frame node routine's driver.
 *
 * cft-debris, MIT licence (see LICENSE at the repository root). Written by DEBRIS-F, 2026-11-16.
 *
 *   m1nodes direct <times> <out> [--plant-dx rad]   the routine itself at each time (no table)
 *   m1nodes build  <t0> <h> <nk> <out> [--plant-xp rad] [--note text]   the frame table
 *   m1nodes times  <times> <out> [--leaps path]     the time scales at each time (TDB s in, %a out)
 *   m1nodes leaps  <mjds> <out> [--leaps path]      TAI-UTC at UTC MJDs (one %a a line)
 * Times are TDB seconds from jd_epoch (2461329.5, MJD 61329.0 TDB), one C99 hex float a line.
 * direct writes, a time a line: the time (%a), then M (9, row-major, GCRS <- ITRS) and Omega (3, rad/s), each
 * the hexadecimal of its binary256 encoding (most significant byte first), then the auxiliary values (%a):
 * X, Y, s, ERA (turns), xp, yp, UT1-UTC, dX, dY, TDB-TT.
 * Inputs: the downloads folder (M1_DOWNLOADS overrides it), read only.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "m1_nodes.h"

#define JD_EPOCH 2461329.5

static const char *opt(int argc, char **argv, const char *o, const char *def)
{
    for (int i = 0; i + 1 < argc; i++)
        if (!strcmp(argv[i], o)) return argv[i + 1];
    return def;
}
static void phex(FILE *f, const unsigned char *p, size_t esz)
{
    fputc(' ', f);
    for (size_t i = esz; i-- > 0;) fprintf(f, "%02x", p[i]);
}

int main(int argc, char **argv)
{
    if (argc < 2) { fprintf(stderr, "usage: m1nodes direct|build ...\n"); return 2; }
    const char *dl = getenv("M1_DOWNLOADS");
    if (!dl || !*dl) dl = "C:/Users/logan/source/repos/cft-debris-downloads/";
    m1n_ctx *N = m1n_open(dl, JD_EPOCH);
    if (!N) return 3;
    if (!strcmp(argv[1], "direct")) {
        if (argc < 4) { fprintf(stderr, "usage: m1nodes direct <times> <out>\n"); return 2; }
        double pdx = strtod(opt(argc, argv, "--plant-dx", "0"), NULL);
        m1n_plant(N, pdx, 0.0);
        FILE *fi = fopen(argv[2], "rb");
        if (!fi) { fprintf(stderr, "cannot read %s\n", argv[2]); return 3; }
        size_t cap = 1024, n = 0;
        double *t = (double *)malloc(cap * sizeof(double));
        char line[256];
        while (fgets(line, sizeof line, fi)) {
            if (line[0] == '#' || line[0] == '\n' || line[0] == '\r') continue;
            if (n == cap) { cap *= 2; t = (double *)realloc(t, cap * sizeof(double)); }
            t[n++] = strtod(line, NULL);
        }
        fclose(fi);
        unsigned char *out = (unsigned char *)malloc(n * M1N_NCOL * 32);
        double *aux = (double *)malloc(n * 10 * sizeof(double));
        m1n_direct(N, t, n, out, aux);
        FILE *f = fopen(argv[3], "wb");
        if (!f) { fprintf(stderr, "cannot write %s\n", argv[3]); return 3; }
        fprintf(f, "# m1nodes direct: jd_epoch %.1f times %lu plant_dx %a\n# inputs %s\n", JD_EPOCH, (unsigned long)n, pdx, m1n_inputs(N));
        fprintf(f, "# columns: t M00 M01 M02 M10 M11 M12 M20 M21 M22 Om0 Om1 Om2 (binary256 hex) X Y s ERA_turns xp yp dut1 dX dY tdb_tt (%%a)\n");
        for (size_t l = 0; l < n; l++) {
            fprintf(f, "%a", t[l]);
            for (int c = 0; c < M1N_NCOL; c++) phex(f, out + (l * M1N_NCOL + c) * 32, 32);
            for (int c = 0; c < 10; c++) fprintf(f, " %a", aux[l * 10 + c]);
            fputc('\n', f);
        }
        fclose(f);
        return 0;
    }
    if (!strcmp(argv[1], "times") || !strcmp(argv[1], "leaps")) {
        if (argc < 4) { fprintf(stderr, "usage: m1nodes times|leaps <in> <out>\n"); return 2; }
        const char *lp = opt(argc, argv, "--leaps", NULL);
        if (lp && m1n_set_leaps(N, lp)) { fprintf(stderr, "cannot load leaps %s\n", lp); return 3; }
        FILE *fi = fopen(argv[2], "rb");
        if (!fi) { fprintf(stderr, "cannot read %s\n", argv[2]); return 3; }
        size_t cap = 1024, n = 0;
        double *t = (double *)malloc(cap * sizeof(double));
        char line[256];
        while (fgets(line, sizeof line, fi)) {
            if (line[0] == '#' || line[0] == '\n' || line[0] == '\r') continue;
            if (n == cap) { cap *= 2; t = (double *)realloc(t, cap * sizeof(double)); }
            t[n++] = strtod(line, NULL);
        }
        fclose(fi);
        FILE *f = fopen(argv[3], "wb");
        if (!f) { fprintf(stderr, "cannot write %s\n", argv[3]); return 3; }
        fprintf(f, "# m1nodes %s: jd_epoch %.1f n %lu\n# inputs %s\n", argv[1], JD_EPOCH, (unsigned long)n, m1n_inputs(N));
        if (!strcmp(argv[1], "times")) {
            double *o = (double *)malloc(n * 5 * sizeof(double));
            m1n_times(N, t, n, o);
            fprintf(f, "# columns: t_tdb tai_s tai_minus_utc tt_minus_tai tdb_minus_tt ut1_minus_utc (%%a)\n");
            for (size_t l = 0; l < n; l++) fprintf(f, "%a %a %a %a %a %a\n", t[l], o[5 * l], o[5 * l + 1], o[5 * l + 2], o[5 * l + 3], o[5 * l + 4]);
        } else {
            fprintf(f, "# columns: mjd_utc tai_minus_utc (%%a)\n");
            for (size_t l = 0; l < n; l++) fprintf(f, "%a %a\n", t[l], m1n_dat(N, t[l]));
        }
        fclose(f);
        return 0;
    }
    if (!strcmp(argv[1], "build")) {
        if (argc < 6) { fprintf(stderr, "usage: m1nodes build <t0> <h> <nk> <out>\n"); return 2; }
        double t0 = strtod(argv[2], NULL), h = strtod(argv[3], NULL);
        long nk = atol(argv[4]);
        double pxp = strtod(opt(argc, argv, "--plant-xp", "0"), NULL);
        m1n_plant(N, 0.0, pxp);
        if (m1n_build(N, t0, h, nk, argv[5], opt(argc, argv, "--note", ""))) return 3;
        printf("built %s: t0 %.3f h %g nk %ld plant_xp %a\n", argv[5], t0, h, nk, pxp);
        return 0;
    }
    fprintf(stderr, "no mode %s\n", argv[1]);
    return 2;
}
