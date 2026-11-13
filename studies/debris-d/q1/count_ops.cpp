// count_ops.cpp - DEBRIS-D, Q1 (cft-debris, MIT): count the operations of
// this repository's own force kernels, by class, for one force evaluation.
//
// cnum wraps a double; every arithmetic operator and every math function
// it goes through increments the counter of its class (the counting
// macros of the brief, as C++ operators). count_kernels.inc, written by
// make_count_build.py, is the kernels' own source with `double` turned
// into `cnum`. Counters are reset before each kernel call and read after.
//
// usage: count_ops            prints one line per kernel and degree
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <cstdint>

struct Counts {
    long add, mul, div, sqrt_, neg, cmp, exp_, log_, pow_, sin_, cos_, tan_, asin_, acos_, atan_, atan2_, fmod_, floor_;
};
static Counts K;

struct cnum {
    double v;
    cnum() : v(0) {}
    cnum(double x) : v(x) {}
    cnum(int x) : v(x) {}
    cnum(long x) : v((double)x) {}
    cnum(unsigned long long x) : v((double)x) {}
    explicit operator int() const { return (int)v; }
    explicit operator double() const { return v; }
    cnum &operator+=(cnum b) { K.add++; v += b.v; return *this; }
    cnum &operator-=(cnum b) { K.add++; v -= b.v; return *this; }
    cnum &operator*=(cnum b) { K.mul++; v *= b.v; return *this; }
    cnum &operator/=(cnum b) { K.div++; v /= b.v; return *this; }
};
static inline cnum operator+(cnum a, cnum b) { K.add++; return a.v + b.v; }
static inline cnum operator-(cnum a, cnum b) { K.add++; return a.v - b.v; }
static inline cnum operator*(cnum a, cnum b) { K.mul++; return a.v * b.v; }
static inline cnum operator/(cnum a, cnum b) { K.div++; return a.v / b.v; }
static inline cnum operator-(cnum a) { K.neg++; return -a.v; }
static inline bool operator<(cnum a, cnum b) { K.cmp++; return a.v < b.v; }
static inline bool operator>(cnum a, cnum b) { K.cmp++; return a.v > b.v; }
static inline bool operator<=(cnum a, cnum b) { K.cmp++; return a.v <= b.v; }
static inline bool operator>=(cnum a, cnum b) { K.cmp++; return a.v >= b.v; }
static inline cnum sqrt(cnum a) { K.sqrt_++; return std::sqrt(a.v); }
static inline cnum exp(cnum a) { K.exp_++; return std::exp(a.v); }
static inline cnum log(cnum a) { K.log_++; return std::log(a.v); }
static inline cnum pow(cnum a, cnum b) { K.pow_++; return std::pow(a.v, b.v); }
static inline cnum sin(cnum a) { K.sin_++; return std::sin(a.v); }
static inline cnum cos(cnum a) { K.cos_++; return std::cos(a.v); }
static inline cnum tan(cnum a) { K.tan_++; return std::tan(a.v); }
static inline cnum asin(cnum a) { K.asin_++; return std::asin(a.v); }
static inline cnum acos(cnum a) { K.acos_++; return std::acos(a.v); }
static inline cnum atan(cnum a) { K.atan_++; return std::atan(a.v); }
static inline cnum atan2(cnum a, cnum b) { K.atan2_++; return std::atan2(a.v, b.v); }
static inline cnum fmod(cnum a, cnum b) { K.fmod_++; return std::fmod(a.v, b.v); }

#ifndef M_PI
#define M_PI 3.14159265358979323846
#endif

#include "count_kernels.inc"

static void reset() { std::memset(&K, 0, sizeof K); }
static void report(const char *what) {
    long fmaclass = K.add + K.mul;
    std::printf("%-34s fma_class %7ld (add %ld mul %ld) div %ld sqrt %ld neg %ld cmp %ld exp %ld log %ld pow %ld "
                "sin %ld cos %ld tan %ld asin %ld acos %ld atan %ld atan2 %ld fmod %ld\n",
                what, fmaclass, K.add, K.mul, K.div, K.sqrt_, K.neg, K.cmp, K.exp_, K.log_, K.pow_, K.sin_, K.cos_,
                K.tan_, K.asin_, K.acos_, K.atan_, K.atan2_, K.fmod_);
}

static uint64_t st = 0x9E3779B97F4A7C15ULL;
static double urand() { st ^= st << 13; st ^= st >> 7; st ^= st << 17; return (double)(st >> 11) * 0x1p-53; }

// the third bodies as point masses (DEBRIS-D's own, written for this count):
// a = GM (d/|d|^3 - s/|s|^3), d = s - r, with one root and one division each
static void point_mass(const cnum r[3], const cnum s[3], cnum gm, cnum a[3]) {
    cnum d[3] = {s[0] - r[0], s[1] - r[1], s[2] - r[2]};
    cnum d2 = d[0] * d[0] + d[1] * d[1] + d[2] * d[2];
    cnum s2 = s[0] * s[0] + s[1] * s[1] + s[2] * s[2];
    cnum id3 = 1.0 / (d2 * sqrt(d2));
    cnum is3 = 1.0 / (s2 * sqrt(s2));
    for (int j = 0; j < 3; j++) a[j] = gm * (d[j] * id3 - s[j] * is3);
}

int main() {
    // ---- gravity: DEBRIS-C's kernel, random coefficients (the count does not depend on them)
    for (int n = 0; n <= NMAXC; n++)
        for (int m = 0; m <= n; m++) { gravc::Cb[n][m] = urand() * 1e-6; gravc::Sb[n][m] = urand() * 1e-6; }
    gravc::GM = 3.986004415e14;
    gravc::RE = 6378136.46;
    const int degs[] = {2, 8, 20, 36, 70};
    for (int k = 0; k < 5; k++) {
        int N = degs[k];
        gravc::tables(N + 1);
        cnum r[3] = {cnum(4.1e6), cnum(-3.2e6), cnum(4.4e6)}, a[3];
        reset();
        gravc::grav(r, 2, N, a);
        char what[64];
        std::snprintf(what, sizeof what, "gravity degree %d (2..%d)", N, N);
        report(what);
    }
    // ---- Sun and Moon by Chebyshev (DEBRIS-B's reader), and their point masses
    {
        q2b::ChebBody *bs[3] = {&q2b::MOON, &q2b::SUN, &q2b::EMB};
        for (int i = 0; i < 3; i++) {
            size_t n = (size_t)bs[i]->nrec * bs[i]->nsub * 3 * bs[i]->ncoef;
            bs[i]->c = (cnum *)std::calloc(n, sizeof(cnum));
            for (size_t j = 0; j < n; j++) bs[i]->c[j] = urand();
        }
        cnum moon[3], sun[3];
        reset();
        q2b::cheb_sun_moon(cnum(12345.6), moon, sun);
        report("Sun and Moon positions (Chebyshev)");
        cnum r[3] = {cnum(4100.0), cnum(-3200.0), cnum(4400.0)}, a1[3], a2[3];
        cnum ms[3] = {cnum(3.0e5), cnum(2.0e5), cnum(1.0e5)}, ss[3] = {cnum(1.4e8), cnum(3.0e7), cnum(1.0e7)};
        reset();
        point_mass(r, ms, cnum(4902.8), a1);
        point_mass(r, ss, cnum(1.327e11), a2);
        report("Sun and Moon point masses (both)");
    }
    // ---- the interpolated frame (DEBRIS-B's frame_interp)
    {
        for (int d = 0; d < NEOP; d++) { q2b::EOP[d][0] = 1e-6 * urand(); q2b::EOP[d][1] = 1e-6 * urand(); q2b::EOP[d][2] = urand() - 0.5; }
        q2b::NODE_DT = 3600.0;
        for (int i = 0; i < NNODE; i++) { q2b::NODE[i][0] = 1e-4 * urand(); q2b::NODE[i][1] = 1e-5 * urand(); q2b::NODE[i][2] = 1e-8 * urand(); }
        cnum rg[3] = {cnum(4100.0), cnum(-3200.0), cnum(4400.0)}, ri[3], R[3][3];
        reset();
        q2b::frame_interp(cnum(86400.0 * 3.3), rg, ri, R);
        report("frame, interpolated (X, Y, s nodes)");
    }
    // ---- drag with the exponential atmosphere (DEBRIS-B's atmos_drag), one object
    {
        cnum rv[6] = {cnum(6778.0), cnum(10.0), cnum(-20.0), cnum(0.01), cnum(7.6), cnum(1.0)}, acc[3];
        reset();
        q2b::atmos_drag(rv, 1, cnum(0.01), acc);
        report("drag, exponential atmosphere");
    }
    // ---- radiation pressure with a conical shadow (DEBRIS-B's srp_conical): sunlit, umbra and penumbra
    {
        cnum rs[3] = {cnum(149597870.7), cnum(0.0), cnum(0.0)}, a[3], nu;
        double aa = 6378.1363 + 400.0;
        double B = std::asin(6378.1363 / aa), As = std::asin(696000.0 / 149597870.7);
        double cases[3] = {0.3, M_PI, M_PI - B};   // sunlit, umbra, the shadow's edge
        const char *names[3] = {"SRP conical, sunlit", "SRP conical, umbra", "SRP conical, penumbra"};
        (void)As;
        for (int k = 0; k < 3; k++) {
            cnum r[3] = {cnum(aa * std::cos(cases[k])), cnum(aa * std::sin(cases[k])), cnum(0.0)};
            reset();
            q2b::srp_conical(r, rs, cnum(0.01), a, &nu);
            char what[64];
            std::snprintf(what, sizeof what, "%s (nu %.3f)", names[k], nu.v);
            report(what);
        }
    }
    return 0;
}
