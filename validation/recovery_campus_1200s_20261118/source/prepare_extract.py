from pathlib import Path
old=Path('/mnt/d/HT-Campus-Repeat-1200s-20261118/extract_maps.py').read_text()
s=old.replace('/home/lzz/ht_campus_repeat_1200s_20261118/runs/explicit_labels_campus_repeat_1200s_01','/home/lzz/ht_recovery_campus_1200s_20261118/runs/recovery_campus_1200s_01').replace('validation/campus_repeat_1200s_20261118/data','validation/recovery_campus_1200s_20261118/data')
work=Path('/mnt/d/HT-Recovery-Campus-1200s-20261118');(work/'extract_maps.py').write_text(s.rstrip()+'\n');(work/'extract.sh').write_text('set -e\nsource /home/lzz/ht_recovery_campus_1200s_20261118/env.sh\n/home/lzz/ht_recovery_campus_1200s_20261118/venv/bin/python /mnt/d/HT-Recovery-Campus-1200s-20261118/extract_maps.py\n')
