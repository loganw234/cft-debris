/* cyclecal.c - DEBRIS-C, M2: written after m2_cpu_check.001.log. A native busy loop of about 2 s,
   three times: wall time (QueryPerformanceCounter), the thread's cycles (QueryThreadCycleTime) and
   its tick-sampled CPU time (GetThreadTimes). If the thread holds a core throughout, cycles per wall
   second is the cycle counter's rate. Asserts nothing; it describes.
   build: gcc -O2 -o cyclecal.exe cyclecal.c */
#include <windows.h>
#include <stdio.h>
#include <stdint.h>

static double ft(FILETIME f) { return (double)(((uint64_t)f.dwHighDateTime << 32) | f.dwLowDateTime) * 1e-7; }

int main(void)
{
    LARGE_INTEGER fq, a, b;
    QueryPerformanceFrequency(&fq);
    HANDLE th = GetCurrentThread();
    for (int r = 0; r < 3; r++) {
        ULONG64 c0, c1;
        FILETIME cr, ex, k0, u0, k1, u1;
        GetThreadTimes(th, &cr, &ex, &k0, &u0);
        QueryThreadCycleTime(th, &c0);
        QueryPerformanceCounter(&a);
        volatile double x = 1.0;
        do {
            for (int i = 0; i < 100000; i++) x = x * 1.0000001 + 1e-9;
            QueryPerformanceCounter(&b);
        } while ((double)(b.QuadPart - a.QuadPart) / fq.QuadPart < 2.0);
        QueryThreadCycleTime(th, &c1);
        GetThreadTimes(th, &cr, &ex, &k1, &u1);
        double wall = (double)(b.QuadPart - a.QuadPart) / fq.QuadPart;
        double cpu = ft(u1) - ft(u0) + ft(k1) - ft(k0);
        printf("span %d: wall %.3f s, thread cycles %llu = %.4g per wall second, GetThreadTimes CPU %.3f s (%.2f of wall), x %g\n",
               r, wall, (unsigned long long)(c1 - c0), (double)(c1 - c0) / wall, cpu, cpu / wall, x);
    }
    return 0;
}
