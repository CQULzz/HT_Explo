from pathlib import Path
import importlib.util
import json
from types import SimpleNamespace
import subprocess
import pytest
from collection_lifecycle import write_completion, await_observer_exit


def test_marker_refuses_existing_and_incomplete_collection(tmp_path):
    write_completion(tmp_path,None)
    assert not (tmp_path/'DONE.json').exists()
    write_completion(tmp_path,{'elapsed_sim':120.1})
    assert json.loads((tmp_path/'DONE.json').read_text())=={'elapsed_sim':120.1}
    with pytest.raises(FileExistsError):write_completion(tmp_path,{'elapsed_sim':999})


@pytest.mark.parametrize('result',[0,-2,1,'timeout'])
def test_observer_exit_is_waited_and_real_failures_are_retained(result):
    calls=[]
    def wait(timeout):
        calls.append(timeout)
        if result=='timeout':raise subprocess.TimeoutExpired('observer',timeout)
        return result
    observer=SimpleNamespace(wait=wait)
    if result==0:await_observer_exit([('observer',observer)],timeout=.5)
    else:
        with pytest.raises(RuntimeError):await_observer_exit([('observer',observer)],timeout=.5)
    assert calls==[.5]


@pytest.mark.parametrize('fail_close',[False,True])
def test_actual_observer_main_marks_done_only_after_close_and_destroy(tmp_path,monkeypatch,fail_close):
    spec=importlib.util.spec_from_file_location('observer_under_test',Path(__file__).with_name('observe.py'))
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    calls=[]
    class Fake:
        def __init__(self,*args):self.completion={'elapsed_sim':120.2}
        def close(self):
            assert not (tmp_path/'DONE.json').exists();calls.append('close')
            if fail_close:raise OSError('video close failed')
        def destroy_node(self):
            assert not (tmp_path/'DONE.json').exists();calls.append('destroy')
    monkeypatch.setattr(module,'Observer',Fake)
    monkeypatch.setattr(module.rclpy,'init',lambda:calls.append('init'))
    monkeypatch.setattr(module.rclpy,'spin',lambda node:calls.append('spin'))
    monkeypatch.setattr(module.rclpy,'try_shutdown',lambda:calls.append('shutdown'))
    if fail_close:
        with pytest.raises(OSError):module.main([str(tmp_path)])
        assert not (tmp_path/'DONE.json').exists()
    else:
        module.main([str(tmp_path)])
        assert json.loads((tmp_path/'DONE.json').read_text())['elapsed_sim']==120.2
    assert calls==['init','spin','close','destroy','shutdown']
