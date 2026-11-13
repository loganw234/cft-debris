/* de421.c - cft-debris M1: a reader of JPL's DE421 binary (little-endian,
 * lnxp1900p2053.421), the host's part: the header, the records, and the choice
 * of record and sub-interval for a time. The Chebyshev sums are the kinds'
 * (m1_physics.h, ph_series).
 *
 * cft-debris, MIT licence (see LICENSE at the repository root). Written by
 * DEBRIS-E, 2026-11-13, from the layout DEBRIS-C's m1b_check.py (Python, MIT)
 * reads: the first record holds the title (3 x 84 bytes), the constant names
 * (400 x 6), the coverage SS[3] at byte 2652, NCON at 2676, AU (km) at 2680,
 * EMRAT at 2688, the pointers IPT[12][3] at 2696, NUMDE at 2840 and the
 * libration pointers at 2844; header.421 gives NCOEFF (the record holds
 * NCOEFF binary64 values) and the pointers again (GROUP 1050), which must
 * agree with the binary's; data records start at the third record.
 */
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "m1.h"

static int rd_i32(const unsigned char *p)
{
    int v;
    memcpy(&v, p, 4);
    return v;
}
static double rd_f64(const unsigned char *p)
{
    double v;
    memcpy(&v, p, 8);
    return v;
}

int m1_de_open(m1_de *de, const char *bin_path, const char *header_path)
{
    memset(de, 0, sizeof *de);
    /* header.421: NCOEFF and GROUP 1050 */
    FILE *h = fopen(header_path, "r");
    if (!h) {
        snprintf(de->err, sizeof de->err, "cannot open %s", header_path);
        return -1;
    }
    char tok[128];
    int hdr_ipt[39], have_g = 0, ncoeff = 0;
    while (fscanf(h, "%127s", tok) == 1) {
        if (!strcmp(tok, "NCOEFF=")) {
            if (fscanf(h, "%d", &ncoeff) != 1) break;
        } else if (!strcmp(tok, "GROUP")) {
            int gid = 0;
            if (fscanf(h, "%d", &gid) != 1) break;
            if (gid == 1050) {
                for (int i = 0; i < 39; i++)
                    if (fscanf(h, "%d", &hdr_ipt[i]) != 1) break;
                have_g = 1;
            }
        }
    }
    fclose(h);
    if (!have_g || ncoeff <= 0) {
        snprintf(de->err, sizeof de->err, "header.421: NCOEFF or GROUP 1050 not found");
        return -2;
    }
    FILE *f = fopen(bin_path, "rb");
    if (!f) {
        snprintf(de->err, sizeof de->err, "cannot open %s", bin_path);
        return -1;
    }
    fseek(f, 0, SEEK_END);
    long len = ftell(f);
    fseek(f, 0, SEEK_SET);
    de->raw = (unsigned char *)malloc((size_t)len);
    if (!de->raw || fread(de->raw, 1, (size_t)len, f) != (size_t)len) {
        fclose(f);
        snprintf(de->err, sizeof de->err, "cannot read %s", bin_path);
        return -1;
    }
    fclose(f);
    de->rawlen = (size_t)len;
    de->ncoeff = ncoeff;
    size_t rec = (size_t)ncoeff * 8;
    if (de->rawlen % rec) {
        snprintf(de->err, sizeof de->err, "file length %lu is not a whole number of %lu-byte records",
                 (unsigned long)de->rawlen, (unsigned long)rec);
        return -3;
    }
    de->nrec = (long)(de->rawlen / rec) - 2;
    for (int i = 0; i < 3; i++) de->ss[i] = rd_f64(de->raw + 2652 + 8 * i);
    de->ncon = rd_i32(de->raw + 2676);
    de->au_km = rd_f64(de->raw + 2680);
    de->emrat = rd_f64(de->raw + 2688);
    for (int k = 0; k < 12; k++)
        for (int j = 0; j < 3; j++) de->ipt[k][j] = rd_i32(de->raw + 2696 + 12 * k + 4 * j);
    de->numde = rd_i32(de->raw + 2840);
    for (int j = 0; j < 3; j++) de->ipt[12][j] = rd_i32(de->raw + 2844 + 4 * j);
    for (int k = 0; k < 13; k++)
        if (de->ipt[k][0] != hdr_ipt[k] || de->ipt[k][1] != hdr_ipt[13 + k] || de->ipt[k][2] != hdr_ipt[26 + k]) {
            snprintf(de->err, sizeof de->err, "binary pointers differ from header.421 at series %d", k);
            return -4;
        }
    if (fabs(de->nrec * de->ss[2] - (de->ss[1] - de->ss[0])) > 1e-9) {
        snprintf(de->err, sizeof de->err, "coverage %.1f..%.1f is not %ld records of %.1f days", de->ss[0], de->ss[1],
                 de->nrec, de->ss[2]);
        return -5;
    }
    /* every record's own dates: the coverage cut into equal records */
    for (long i = 0; i < de->nrec; i++) {
        const double *r = m1_de_record(de, i);
        if (r[0] != de->ss[0] + i * de->ss[2] || r[1] != r[0] + de->ss[2]) {
            snprintf(de->err, sizeof de->err, "record %ld spans %.3f..%.3f", i, r[0], r[1]);
            return -6;
        }
    }
    return 0;
}

void m1_de_close(m1_de *de)
{
    free(de->raw);
    memset(de, 0, sizeof *de);
}

const double *m1_de_record(const m1_de *de, long i)
{
    return (const double *)(de->raw + (size_t)(i + 2) * (size_t)de->ncoeff * 8);
}

int m1_de_locate(const m1_de *de, int k, double jd0, double sec, long *rec, int *sub, double *dt_sec)
{
    const double reclen = de->ss[2] * 86400.0;
    const int nsub = de->ipt[k][2];
    const double sublen = reclen / nsub;
    const double s = (jd0 - de->ss[0]) * 86400.0 + sec; /* exact for the times this project uses */
    long r = (long)floor(s / reclen);
    if (r == de->nrec && s == de->nrec * reclen) r = de->nrec - 1;
    if (r < 0 || r >= de->nrec) return -1;
    const double w = s - r * reclen;
    int j = (int)floor(w / sublen);
    if (j == nsub) j = nsub - 1;
    *rec = r;
    *sub = j;
    *dt_sec = w - j * sublen;
    return 0;
}
