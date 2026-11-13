"""cpurun.py - run one command and charge its CPU to DEBRIS-D's budget.

DEBRIS-D's own tool (cft-debris, MIT). Usage:
    python -I -B cpurun.py <label> <ledger.tsv> -- <command> [args...]

How it counts (the Rules' CPU line):
  * the wrapper puts itself in a fresh Windows job object, so every process
    the command starts (make -> gcc -> cc1 -> as -> ld ...) joins the job;
  * while the command runs it polls the job's process-id list every 10 ms
    and opens a query handle on each new process, so that its cycle count
    can still be read after it exits;
  * at the end it sums QueryProcessCycleTime over every process it caught
    (the wrapper's own included) and divides by 2.5e9 cycles a second
    (the part's base clock; taking it as the counter's rate is BELIEVED);
  * beside it, the job's own accounting (user + kernel time, the
    GetProcessTimes kind, which under-reports on this host) and the
    number of processes the job saw against the number caught.
A process that lived less than one poll can be missed by the cycle sum;
the job's time and process counts still include it, and the line says how
many were missed.
"""
import ctypes
import ctypes.wintypes as w
import os
import subprocess
import sys
import time

k32 = ctypes.WinDLL("kernel32", use_last_error=True)
k32.CreateJobObjectW.restype = w.HANDLE
k32.CreateJobObjectW.argtypes = [ctypes.c_void_p, w.LPCWSTR]
k32.GetCurrentProcess.restype = w.HANDLE
k32.AssignProcessToJobObject.argtypes = [w.HANDLE, w.HANDLE]
k32.AssignProcessToJobObject.restype = w.BOOL
k32.QueryInformationJobObject.argtypes = [w.HANDLE, ctypes.c_int, ctypes.c_void_p,
                                          w.DWORD, ctypes.POINTER(w.DWORD)]
k32.QueryInformationJobObject.restype = w.BOOL
k32.OpenProcess.argtypes = [w.DWORD, w.BOOL, w.DWORD]
k32.OpenProcess.restype = w.HANDLE
k32.QueryProcessCycleTime.argtypes = [w.HANDLE, ctypes.POINTER(ctypes.c_ulonglong)]
k32.QueryProcessCycleTime.restype = w.BOOL
k32.GetProcessTimes.argtypes = [w.HANDLE] + [ctypes.POINTER(w.FILETIME)] * 4
k32.GetProcessTimes.restype = w.BOOL

PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
JobObjectBasicAccountingInformation = 1
JobObjectBasicProcessIdList = 3
HZ = 2.5e9


class BASIC_ACCOUNTING(ctypes.Structure):
    _fields_ = [("TotalUserTime", ctypes.c_longlong),
                ("TotalKernelTime", ctypes.c_longlong),
                ("ThisPeriodTotalUserTime", ctypes.c_longlong),
                ("ThisPeriodTotalKernelTime", ctypes.c_longlong),
                ("TotalPageFaultCount", w.DWORD),
                ("TotalProcesses", w.DWORD),
                ("ActiveProcesses", w.DWORD),
                ("TotalTerminatedProcesses", w.DWORD)]


def pid_list(job):
    n = 1024
    buf = (ctypes.c_byte * (8 + 8 * n))()
    if not k32.QueryInformationJobObject(job, JobObjectBasicProcessIdList, buf,
                                         ctypes.sizeof(buf), None):
        return []
    count = ctypes.cast(buf, ctypes.POINTER(w.DWORD))[1]
    ids = ctypes.cast(ctypes.addressof(buf) + 8, ctypes.POINTER(ctypes.c_size_t))
    return [ids[i] for i in range(count)]


def ft(f):
    return ((f.dwHighDateTime << 32) | f.dwLowDateTime) / 1e7


def main():
    if len(sys.argv) < 5 or sys.argv[3] != "--":
        sys.exit("usage: cpurun.py <label> <ledger.tsv> -- <command> [args...]")
    label, ledger, cmd = sys.argv[1], sys.argv[2], sys.argv[4:]
    job = k32.CreateJobObjectW(None, None)
    if not job:
        sys.exit("CreateJobObject failed")
    if not k32.AssignProcessToJobObject(job, k32.GetCurrentProcess()):
        sys.exit("AssignProcessToJobObject(self) failed: %d" % ctypes.get_last_error())
    handles = {}
    me = os.getpid()
    t0 = time.perf_counter()
    p = subprocess.Popen(cmd)
    while True:
        for pid in pid_list(job):
            if pid not in handles:
                h = k32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
                if h:
                    handles[pid] = h
        if p.poll() is not None:
            break
        time.sleep(0.01)
    wall = time.perf_counter() - t0
    cyc_total = 0
    pt_total = 0.0
    for pid, h in handles.items():
        c = ctypes.c_ulonglong(0)
        if k32.QueryProcessCycleTime(h, ctypes.byref(c)):
            cyc_total += c.value
        a, b, kt, ut = w.FILETIME(), w.FILETIME(), w.FILETIME(), w.FILETIME()
        if k32.GetProcessTimes(h, ctypes.byref(a), ctypes.byref(b), ctypes.byref(kt), ctypes.byref(ut)):
            pt_total += ft(kt) + ft(ut)
    acct = BASIC_ACCOUNTING()
    k32.QueryInformationJobObject(job, JobObjectBasicAccountingInformation,
                                  ctypes.byref(acct), ctypes.sizeof(acct), None)
    job_s = (acct.TotalUserTime + acct.TotalKernelTime) / 1e7
    caught = len(handles)
    line = "\t".join([
        time.strftime("%Y-%m-%d %H:%M:%S"), label, "%.3f" % wall,
        "%d" % cyc_total, "%.3f" % (cyc_total / HZ), "%.3f" % pt_total,
        "%.3f" % job_s, "%d" % acct.TotalProcesses, "%d" % caught,
        "%d" % p.returncode, " ".join(cmd)])
    with open(ledger, "a", encoding="utf-8", newline="\n") as f:
        f.write(line + "\n")
    sys.stderr.write("[cpurun] %s wall %.2fs cycles/2.5e9 %.2fs procs-times %.2fs job %.2fs "
                     "processes %d caught %d exit %d\n" % (label, wall, cyc_total / HZ, pt_total,
                                                          job_s, acct.TotalProcesses, caught, p.returncode))
    sys.exit(p.returncode)


if __name__ == "__main__":
    main()
