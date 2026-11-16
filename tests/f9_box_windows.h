/* f9_box_windows.h - cft-debris M1 (DEBRIS-F): the lead's stand-in for <windows.h> when tests/m1f.c is built on
 * Linux, for F9's run on amd-arc-box. tests/f9_box.py copies it to build/shim/windows.h and puts that folder on
 * m1f.c's include path alone.
 * cft-debris, MIT licence (see LICENSE at the repository root). Written by the round's lead, 2026-11-16.
 *
 * m1f.c's time mode (F9) uses two Windows timers. This gives them Linux clocks, and nothing else:
 *   QueryPerformanceCounter, QueryPerformanceFrequency -> CLOCK_MONOTONIC, in nanoseconds (a frequency of 1e9);
 *   QueryThreadCycleTime -> CLOCK_THREAD_CPUTIME_ID, in nanoseconds.
 * So on the box the numbers m1f prints as thread_cycles and per_lane_eval_cycles are the thread's CPU NANOSECONDS,
 * not cycles. clock_gettime needs _POSIX_C_SOURCE >= 199309L under -std=c11; f9_box.py defines it for m1f.c alone.
 * A clock that fails stops the program (abort): a timing is never taken from an unset value.
 */
#ifndef F9_BOX_WINDOWS_H
#define F9_BOX_WINDOWS_H
#include <stdint.h>
#include <stdlib.h>
#include <time.h>

typedef union {
    struct {
        uint32_t LowPart;
        int32_t HighPart;
    } u;
    long long QuadPart;
} LARGE_INTEGER;
typedef unsigned long long ULONG64;
typedef void *HANDLE;

static inline HANDLE GetCurrentThread(void)
{
    return (HANDLE)0;
}
static inline int QueryPerformanceFrequency(LARGE_INTEGER *f)
{
    f->QuadPart = 1000000000LL;
    return 1;
}
static inline int QueryPerformanceCounter(LARGE_INTEGER *c)
{
    struct timespec t;
    if (clock_gettime(CLOCK_MONOTONIC, &t)) abort();
    c->QuadPart = (long long)t.tv_sec * 1000000000LL + (long long)t.tv_nsec;
    return 1;
}
static inline int QueryThreadCycleTime(HANDLE h, ULONG64 *c)
{
    struct timespec t;
    (void)h;
    if (clock_gettime(CLOCK_THREAD_CPUTIME_ID, &t)) abort();
    *c = (ULONG64)t.tv_sec * 1000000000ULL + (ULONG64)t.tv_nsec;
    return 1;
}
#endif
