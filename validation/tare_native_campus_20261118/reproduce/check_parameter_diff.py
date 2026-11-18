from pathlib import Path
import difflib
base=Path('/home/lzz/tare_native_campus_20261118/runs/native_campus_01');repeat=Path('/home/lzz/tare_native_campus_repeat_20261118/runs/native_campus_02')
for p in base.glob('*.yaml'):
 b=repeat/p.name
 if p.read_bytes()!=b.read_bytes():
  print(p.name);print(''.join(difflib.unified_diff(p.read_text().splitlines(True),b.read_text().splitlines(True))))
print((Path('/mnt/d/TARE-Native-Campus-20261118/navigation_diagnostic.log')).read_text()[:6000])
