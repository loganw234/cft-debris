/* g_calib.c - cft-debris M1 (DEBRIS-G), G1's clock calibration: a fixed-work loop of dependent integer additions.
 *
 * cft-debris, MIT licence (see LICENSE at the repository root). Written by DEBRIS-G, 2026-11-17.
 *
 *   g_calib <iterations>
 *
 * Each iteration is a chain of 8 dependent additions (inline assembly: the optimiser can neither fold nor remove
 * them), then the accumulator is stored through a volatile. The count is read at run time. At one addition a cycle
 * (BELIEVED for such a chain on this part) the run takes 8 x iterations cycles; the harness divides the additions by
 * the wall time for an implied clock, beside the kernel's frequency reading. The build log keeps the loop's
 * disassembly. The protocol is m1g's: READY, one byte 'G', the run, TIMED_DONE, one byte 'Q', REPORT lines.
 */
#ifdef __linux__
#define _GNU_SOURCE
#endif
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#ifdef _WIN32
#include <fcntl.h>
#include <io.h>
#include <windows.h>
#else
#include <sched.h>
#include <time.h>
#include <unistd.h>
#endif

static volatile uint64_t sink;

static int64_t now_ns(void)
{
#ifdef _WIN32
    LARGE_INTEGER c, f;
    QueryPerformanceCounter(&c);
    QueryPerformanceFrequency(&f);
    return (c.QuadPart / f.QuadPart) * 1000000000LL + (c.QuadPart % f.QuadPart) * 1000000000LL / f.QuadPart;
#else
    struct timespec t;
    if (clock_gettime(CLOCK_MONOTONIC, &t)) abort();
    return (int64_t)t.tv_sec * 1000000000LL + t.tv_nsec;
#endif
}
static int64_t cpu_ns(void)
{
#ifdef _WIN32
    ULONG64 c = 0;
    QueryProcessCycleTime(GetCurrentProcess(), &c);
    return (int64_t)((double)c / 2.5);
#else
    struct timespec t;
    if (clock_gettime(CLOCK_PROCESS_CPUTIME_ID, &t)) abort();
    return (int64_t)t.tv_sec * 1000000000LL + t.tv_nsec;
#endif
}
static int which_cpu(void)
{
#ifdef __linux__
    return sched_getcpu();
#else
    return -1;
#endif
}
static int read_byte(void)
{
    unsigned char b = 0;
#ifdef _WIN32
    int r = _read(0, &b, 1);
#else
    ssize_t r = read(0, &b, 1);
#endif
    return r == 1 ? (int)b : -1;
}

/* the loop: noinline so that the disassembly of this function alone is the loop */
__attribute__((noinline)) uint64_t calib_loop(uint64_t n, uint64_t k)
{
    uint64_t acc = 0;
    for (uint64_t i = 0; i < n; i++) {
#if defined(__x86_64__)
        __asm__ volatile("add %1, %0\n\tadd %1, %0\n\tadd %1, %0\n\tadd %1, %0\n\tadd %1, %0\n\tadd %1, %0\n\tadd %1, %0\n\tadd %1, %0"
                         : "+r"(acc)
                         : "r"(k));
#else
        __asm__ volatile("" : "+r"(acc));
        acc += k; acc += k; acc += k; acc += k; acc += k; acc += k; acc += k; acc += k;
#endif
        sink = acc;
    }
    return acc;
}

int main(int argc, char **argv)
{
    if (argc < 2) { fprintf(stderr, "usage: g_calib <iterations>\n"); return 2; }
#ifdef _WIN32
    _setmode(0, _O_BINARY);
    _setmode(1, _O_BINARY);
#endif
    const uint64_t n = strtoull(argv[1], NULL, 10);
    const uint64_t k = (uint64_t)strtoull(argc > 2 ? argv[2] : "3", NULL, 10);
    printf("READY\n");
    fflush(stdout);
    const int64_t c_ready = cpu_ns();
    int b = read_byte();
    const int64_t t_rel = now_ns(), c_rel = cpu_ns();
    const int cpu0 = which_cpu();
    if (b != 'G') return 2;
    uint64_t acc = calib_loop(n, k);
    const int64_t t_end = now_ns(), c_end = cpu_ns();
    const int cpu1 = which_cpu();
    printf("TIMED_DONE\n");
    fflush(stdout);
    (void)read_byte();
    printf("REPORT kind calib\nREPORT iterations %llu\nREPORT additions %llu\n", (unsigned long long)n, (unsigned long long)(8 * n));
    printf("REPORT accumulator_ok %d\n", acc == 8ULL * n * k);
    printf("REPORT t_release_read_ns %lld\nREPORT t_start_ns %lld\nREPORT t_end_ns %lld\n", (long long)t_rel, (long long)t_rel, (long long)t_end);
    printf("REPORT cpu_ready_ns %lld\nREPORT cpu_release_ns %lld\nREPORT cpu_start_ns %lld\nREPORT cpu_end_ns %lld\n", (long long)c_ready, (long long)c_rel,
           (long long)c_rel, (long long)c_end);
    printf("REPORT cpu_at_start %d\nREPORT cpu_at_end %d\nDONE\n", cpu0, cpu1);
    fflush(stdout);
    return acc == 8ULL * n * k ? 0 : 3;
}
