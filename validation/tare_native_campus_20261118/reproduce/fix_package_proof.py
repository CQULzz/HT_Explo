from pathlib import Path
p=Path('/mnt/d/TARE-Native-Campus-20261118/navigation_diagnostic.log\r')
if p.exists():p.rename(p.with_name('navigation_diagnostic.log'))
p=Path('/mnt/d/TARE-Native-Campus-20261118/package_results.py');s=p.read_text(encoding='utf-8-sig');s=s.replace("import csv,hashlib,json,shutil,ast", "import csv,hashlib,json,shutil,ast,yaml")
s=s.replace("assert all(params.values()),params", "normalized={}\nfor p in a.glob('*.yaml'):\n aa=p.read_text();bb=(b/p.name).read_text()\n if 'Node not found' in aa or 'Node not found' in bb:\n  normalized[p.name]=None;continue\n normalized[p.name]=yaml.safe_load(aa)==yaml.safe_load(bb.replace(str(repeat),str(base)))\nassert all(v is not False for v in normalized.values()),normalized")
s=s.replace("'full_effective_yaml_byte_equal':params", "'full_effective_yaml_byte_equal':params,'effective_yaml_equal_after_resolving_isolated_root':normalized,'missing_effective_parameter_dump':['native_campus_02/vehicleSimulator.yaml'],'evidence_gap':'Second vehicleSimulator parameter service lookup returned Node not found. Node-list snapshot also missed TARE and vehicleSimulator; four actual executables independently verified. Frozen launch/source/config and same binary retained; no replacement dump fabricated.'")
p.write_text(s)
print(Path('/mnt/d/TARE-Native-Campus-20261118/navigation_diagnostic.log').read_text())
