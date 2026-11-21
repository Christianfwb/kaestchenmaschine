"""Fail-closed Windows per-process commit cap; parent additionally caps wall time."""
import ctypes as c
from ctypes import wintypes as w

class Basic(c.Structure):
    _fields_=[('PerProcessUserTimeLimit',c.c_int64),('PerJobUserTimeLimit',c.c_int64),('LimitFlags',w.DWORD),
              ('MinimumWorkingSetSize',c.c_size_t),('MaximumWorkingSetSize',c.c_size_t),('ActiveProcessLimit',w.DWORD),
              ('Affinity',c.c_size_t),('PriorityClass',w.DWORD),('SchedulingClass',w.DWORD)]
class IO(c.Structure):
    _fields_=[(s,c.c_uint64) for s in ('ReadOperationCount','WriteOperationCount','OtherOperationCount','ReadTransferCount','WriteTransferCount','OtherTransferCount')]
class Extended(c.Structure):
    _fields_=[('BasicLimitInformation',Basic),('IoInfo',IO),('ProcessMemoryLimit',c.c_size_t),('JobMemoryLimit',c.c_size_t),
              ('PeakProcessMemoryUsed',c.c_size_t),('PeakJobMemoryUsed',c.c_size_t)]
class Memory(c.Structure):
    _fields_=[('cb',w.DWORD),('PageFaultCount',w.DWORD)]+[(s,c.c_size_t) for s in
        ('PeakWorkingSetSize','WorkingSetSize','QuotaPeakPagedPoolUsage','QuotaPagedPoolUsage','QuotaPeakNonPagedPoolUsage','QuotaNonPagedPoolUsage','PagefileUsage','PeakPagefileUsage','PrivateUsage')]

k=c.WinDLL('kernel32',use_last_error=True)
k.GetCurrentProcess.restype=w.HANDLE
k.CreateJobObjectW.argtypes=[c.c_void_p,w.LPCWSTR];k.CreateJobObjectW.restype=w.HANDLE
k.SetInformationJobObject.argtypes=[w.HANDLE,c.c_int,c.c_void_p,w.DWORD]
k.AssignProcessToJobObject.argtypes=[w.HANDLE,w.HANDLE]
p=c.WinDLL('psapi',use_last_error=True)
p.GetProcessMemoryInfo.argtypes=[w.HANDLE,c.c_void_p,w.DWORD]
_job=None

def install(limit=2*1024**3):
    global _job
    _job=k.CreateJobObjectW(None,None)
    if not _job: raise c.WinError(c.get_last_error())
    info=Extended();info.BasicLimitInformation.LimitFlags=0x100 # JOB_OBJECT_LIMIT_PROCESS_MEMORY
    info.ProcessMemoryLimit=limit
    if not k.SetInformationJobObject(_job,9,c.byref(info),c.sizeof(info)): raise c.WinError(c.get_last_error())
    if not k.AssignProcessToJobObject(_job,k.GetCurrentProcess()): raise c.WinError(c.get_last_error())
    return limit

def memory():
    m=Memory();m.cb=c.sizeof(m)
    if not p.GetProcessMemoryInfo(k.GetCurrentProcess(),c.byref(m),c.sizeof(m)): raise c.WinError(c.get_last_error())
    return dict(rss_bytes=m.WorkingSetSize,peak_rss_bytes=m.PeakWorkingSetSize,private_bytes=m.PrivateUsage,peak_commit_bytes=m.PeakPagefileUsage)
