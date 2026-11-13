/* m1x.c - cft-debris M1: the native64 force model and rk4 as a DLL, for E7's
 * REBOUND harness (tests/e7_rebound.py, through ctypes). REBOUND is called
 * from Python as a referee; nothing of it is here.
 *
 * cft-debris, MIT licence (see LICENSE at the repository root). Written by
 * DEBRIS-E, 2026-11-13.
 *
 *   int  m1x_init(const char *downloads, int nmax, double bc, double cram, double c20rel)
 *        the whole model of E2 (central, degrees 2..nmax, Sun, Moon, 28-band drag,
 *        radiation pressure), epoch 2008-07-03 00:00 TDB, one lane, native64 with the
 *        C library's transcendentals; c20rel != 0 plants C20 times (1 + c20rel)
 *   void m1x_accel(double t, const double *y6, double *a3)   the total acceleration
 *   int  m1x_rk4(const char *h, long nsteps, double *y6)     our rk4, in place
 *   long long m1x_nevals(void)                               accelerations evaluated
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "m1.h"

static m1_gfc G;
static m1_de DE;
static m1_ctx C;
static const m1_vt *VT;
static int up = 0;
static double BC, CRAM;
static long long NEV = 0;

static int m1x_setup(const char *downloads, int nmax, double bc, double cram, double c20rel, int srp, int nbands);

__declspec(dllexport) int m1x_init(const char *downloads, int nmax, double bc, double cram, double c20rel)
{
    return m1x_setup(downloads, nmax, bc, cram, c20rel, 1, 28);
}

/* E7's diagnosis: the same with radiation pressure on (1) or off (0), and the atmosphere's 28 bands or
   one band (DEBRIS-D's: 3.725e-12 kg/m^3 at 400 km, scale height 58515 m), so that the model is smooth */
__declspec(dllexport) int m1x_init2(const char *downloads, int nmax, double bc, double cram, double c20rel, int srp,
                                    int nbands)
{
    return m1x_setup(downloads, nmax, bc, cram, c20rel, srp, nbands);
}

static int m1x_setup(const char *downloads, int nmax, double bc, double cram, double c20rel, int srp, int nbands)
{
    char p1[600], p2[600];
    if (up) {
        VT->teardown(&C);
        cft_close(C.dev);
        m1_gfc_free(&G);
        m1_de_close(&DE);
        up = 0;
    }
    snprintf(p1, sizeof p1, "%sEIGEN6-C4.gfc/EIGEN6-C4.gfc", downloads);
    if (m1_gfc_load(&G, p1, nmax)) return -1;
    snprintf(p1, sizeof p1, "%slnxp1900p2053.421/lnxp1900p2053.421", downloads);
    snprintf(p2, sizeof p2, "%sheader.421/header.421", downloads);
    if (m1_de_open(&DE, p1, p2)) return -2;
    VT = &m1_vt_native64;
    memset(&C, 0, sizeof C);
    if (cft_open(NULL, 0, &C.dev) != CFT_OK) return -3;
    C.ctl_c20 = (c20rel != 0.0);
    C.ctl_c20_rel = c20rel;
    m1_model m;
    memset(&m, 0, sizeof m);
    m.central = 1;
    m.nmin = 2;
    m.nmax = nmax;
    m.sun = m.moon = m.drag = 1;
    m.srp = srp;
    m.nbands = nbands;
    m.band_h0 = "400000";
    m.band_rho0 = "3.725e-12";
    m.band_hs = "58515";
    m.jd_epoch = 2454650.5;
    if (VT->setup(&C, &m, &G, &DE, 1)) return -4;
    BC = bc;
    CRAM = cram;
    NEV = 0;
    up = 1;
    return 0;
}

__declspec(dllexport) void m1x_accel(double t, const double *y6, double *a3)
{
    double y[6], a[3];
    void *yp[6], *ap[3];
    memcpy(y, y6, sizeof y);
    for (int i = 0; i < 6; i++) yp[i] = &y[i];
    for (int i = 0; i < 3; i++) ap[i] = &a[i];
    VT->accel(&C, ap, t, (const void *const *)yp, &BC, &CRAM, 1);
    memcpy(a3, a, sizeof a);
    NEV++;
}

__declspec(dllexport) int m1x_rk4(const char *h, long nsteps, double *y6)
{
    void *yp[6];
    for (int i = 0; i < 6; i++) yp[i] = &y6[i];
    return VT->rk4(&C, yp, &BC, &CRAM, h, 0, nsteps, NULL, NULL, 1);
}

__declspec(dllexport) long long m1x_nevals(void) { return NEV; }
