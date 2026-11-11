"""Sparse read-only host snapshots while the requested simulation runs."""
from pathlib import Path
import json
import subprocess
import time

ROOT=Path('/home/lzz/ht_quality_600s_20261112')
RESULT=ROOT/'runs/cmu_quality_600s_02/RESULT.json'

def read(path):
    try:return Path(path).read_text().strip()
    except OSError:return None

with (ROOT/'evidence/RESOURCE_SAMPLES_02.jsonl').open('w') as f:
    for _ in range(25):
        if RESULT.exists():break
        d={'wall_time':time.time(),'monotonic_s':time.monotonic(),
           'boottime_s':time.clock_gettime(time.CLOCK_BOOTTIME),
           'boot_id':read('/proc/sys/kernel/random/boot_id'),
           'loadavg':read('/proc/loadavg'),'meminfo':read('/proc/meminfo'),
           'pressure_memory':read('/proc/pressure/memory'),'pressure_cpu':read('/proc/pressure/cpu'),
           'cpu0_freq_khz':read('/sys/devices/system/cpu/cpu0/cpufreq/scaling_cur_freq'),
           'cpu0_governor':read('/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor'),
           'vmstat':read('/proc/vmstat'),
           'power':{str(p):read(p) for p in Path('/sys/class/power_supply').glob('*/online')}}
        f.write(json.dumps(d)+'\n');f.flush();time.sleep(30)
