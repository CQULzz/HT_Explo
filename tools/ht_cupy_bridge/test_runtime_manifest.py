import hashlib
from types import SimpleNamespace
from runtime_manifest import collect_runtime_manifest


def test_actual_import_path_and_content_define_identity(tmp_path,monkeypatch):
    entry=tmp_path/'entry.py';entry.write_text('entry')
    weight=tmp_path/'model.pth';weight.write_bytes(b'weights')
    imported=tmp_path/'other_workspace.py';imported.write_text('actual imported code')
    monkeypatch.setenv('PRIVATE_TOKEN','must-never-be-dumped')
    def collect():
        return collect_runtime_manifest(entry,weight,{'ht_device':'cuda'},
            {'device':'cuda','history_backend':'numba'},{'ht':'/ht_real/traversability'},
            {'model':SimpleNamespace(__file__=str(imported))})
    a=collect();assert a['runtime_id']==collect()['runtime_id']
    assert a['modules']['model']['path']==str(imported)
    assert a['modules']['model']['sha256']==hashlib.sha256(imported.read_bytes()).hexdigest()
    assert 'PRIVATE_TOKEN' not in str(a) and 'must-never-be-dumped' not in str(a)
    imported.write_text('changed installed code');assert collect()['runtime_id']!=a['runtime_id']
    weight.write_bytes(b'new weights');assert collect()['weights']['sha256']!=a['weights']['sha256']


def test_missing_files_are_explicit_not_invented(tmp_path):
    m=collect_runtime_manifest(tmp_path/'missing.py',tmp_path/'missing.pth',{}, {}, {},
        {'unresolved':SimpleNamespace()})
    assert m['entry']['error']=='FileNotFoundError'
    assert m['modules']['unresolved']['error']=='module_has_no_file'
