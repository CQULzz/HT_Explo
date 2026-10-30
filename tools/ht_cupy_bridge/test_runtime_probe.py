import gc
import time
from runtime_probe import RuntimeProbe


def test_probe_observes_gc_without_changing_gc_or_cpu_settings():
    before=list(gc.callbacks);enabled=gc.isenabled();threshold=gc.get_threshold()
    probe=RuntimeProbe()
    try:
        start=probe.begin()
        cycle=[];cycle.append(cycle);del cycle;gc.collect()
        row=probe.finish(start,slow_threshold=0)
        assert row['wall_s']>=row['gc_s']>=0 and row['thread_cpu_s']>=0
        assert sum(row['gc_collections'])>=1 and row['rss_peak_kib']>0
        assert gc.isenabled()==enabled and gc.get_threshold()==threshold
    finally:probe.close();probe.close()
    assert list(gc.callbacks)==before
