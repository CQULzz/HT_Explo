import json
from pathlib import Path
from threading import Event
import pytest
from diagnostic_history import DiagnosticHistory


def test_online_history_is_bounded_and_reports_eviction():
    h=DiagnosticHistory(3)
    for i in range(10000):h.append({'stamp':i})
    assert list(h)==[{'stamp':i} for i in (9997,9998,9999)]
    assert h[-1]['stamp']==9999
    assert h.status()['seen']==10000 and h.status()['evicted_from_memory']==9997
    h.close();h.close()
    with pytest.raises(RuntimeError):h.append({})


def test_full_archive_survives_memory_eviction_and_is_legacy_json(tmp_path):
    path=tmp_path/'diagnostics.json';h=DiagnosticHistory(2,path,queue_capacity=4096)
    for i in range(3000):h.append({'stamp':i,'surface':{'known':True}})
    h.finalize()
    assert len(h)==2
    assert [r['stamp'] for r in json.loads(path.read_text())]==list(range(3000))
    status=json.loads(Path(str(path)+'.status.json').read_text())
    assert status['archive_written']==status['seen']==3000
    assert status['archive_dropped']==0 and status['closed']
    with pytest.raises(FileExistsError):DiagnosticHistory(2,path)
    path.unlink()
    with pytest.raises(FileExistsError):DiagnosticHistory(2,path)


def test_overflow_is_visible_and_never_claims_full_archive(tmp_path):
    path=tmp_path/'diagnostics.json';h=DiagnosticHistory(2,path,queue_capacity=1)
    entered=Event();release=Event();original=h._file
    class BlockedFile:
        def write(self,item):
            entered.set();assert release.wait(5)
            return original.write(item)
        def flush(self):return original.flush()
        def close(self):return original.close()
    h._file=BlockedFile()
    try:
        h.append({'stamp':0});assert entered.wait(5)
        h.append({'stamp':1});h.append({'stamp':2})
        assert h.status()['archive_dropped']==1
    finally:release.set();h.close()
    with pytest.raises(RuntimeError,match='Incomplete'):h.finalize()
    assert not path.exists()
    assert json.loads(Path(str(path)+'.status.json').read_text())['archive_dropped']==1


def test_io_failure_does_not_block_or_change_latest_diagnostic(tmp_path):
    path=tmp_path/'diagnostics.json';h=DiagnosticHistory(2,path);original=h._file
    class FailedFile:
        def write(self,_):raise OSError('disk unavailable')
        def close(self):return original.close()
    h._file=FailedFile();h.append({'stamp':1});h.close()
    assert h[-1]=={'stamp':1} and h.status()['archive_error']=='OSError'
    with pytest.raises(RuntimeError,match='Incomplete'):h.finalize()
    assert not path.exists()


@pytest.mark.parametrize('capacity',[0,-1,True,1.5])
def test_invalid_capacity_rejected(capacity):
    with pytest.raises(ValueError):DiagnosticHistory(capacity)
