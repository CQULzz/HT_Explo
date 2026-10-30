"""Read-only process/GC evidence. Never tune GC, affinity, power or clocks."""
import ctypes
import gc
from pathlib import Path
import resource
import time


class RuntimeProbe:
    def __init__(self):
        self.gc_seconds=0.;self.gc_counts=[0,0,0];self._gc_start=None;self.closed=False
        try:
            self._cpu=ctypes.CDLL(None).sched_getcpu
            self._cpu.restype=ctypes.c_int
        except (OSError,AttributeError):self._cpu=lambda:None
        self._callback=self._on_gc
        gc.callbacks.append(self._callback)

    def _on_gc(self,phase,info):
        if phase=='start':self._gc_start=time.monotonic()
        else:
            if self._gc_start is not None:self.gc_seconds+=time.monotonic()-self._gc_start
            self._gc_start=None
            generation=info.get('generation',-1)
            if 0<=generation<3:self.gc_counts[generation]+=1

    def begin(self):
        return (time.monotonic(),time.thread_time(),resource.getrusage(resource.RUSAGE_SELF),
                self._cpu(),self.gc_seconds,tuple(self.gc_counts))

    def finish(self,start,slow_threshold=.1):
        ended=time.monotonic();cpu_time=time.thread_time();usage=resource.getrusage(resource.RUSAGE_SELF)
        core=self._cpu()
        result={'wall_s':ended-start[0],'thread_cpu_s':cpu_time-start[1],
                'process_cpu_s':usage.ru_utime+usage.ru_stime-start[2].ru_utime-start[2].ru_stime,
                'cpu_start':start[3],'cpu_end':core,'gc_s':self.gc_seconds-start[4],
                'gc_collections':[a-b for a,b in zip(self.gc_counts,start[5])],
                'minor_faults':usage.ru_minflt-start[2].ru_minflt,'major_faults':usage.ru_majflt-start[2].ru_majflt,
                'voluntary_context_switches':usage.ru_nvcsw-start[2].ru_nvcsw,
                'involuntary_context_switches':usage.ru_nivcsw-start[2].ru_nivcsw,
                'rss_peak_kib':usage.ru_maxrss}
        if result['wall_s']>=slow_threshold and core is not None and core>=0:
            base=Path(f'/sys/devices/system/cpu/cpu{core}')
            evidence={}
            for label,relative in [('reported_frequency_khz','cpufreq/scaling_cur_freq'),
                                   ('core_throttle_count','thermal_throttle/core_throttle_count'),
                                   ('package_throttle_count','thermal_throttle/package_throttle_count')]:
                try:evidence[label]=int((base/relative).read_text().strip())
                except (OSError,ValueError):evidence[label]=None
            evidence['sample_monotonic_s']=time.monotonic()
            evidence['scope']='post-callback OS report, not a frequency trace or a proven cause'
            result['slow_frame_host_evidence']=evidence
        return result

    def close(self):
        if self.closed:return
        self.closed=True
        if self._callback in gc.callbacks:gc.callbacks.remove(self._callback)
