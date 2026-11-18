from pathlib import Path
src=Path('/mnt/d/HT-Campus-1200s-20261118/extract_maps.py').read_text()
src=src.replace('ht_campus_1200s_20261118/runs/explicit_labels_campus_1200s_03','ht_campus_repeat_1200s_20261118/runs/explicit_labels_campus_repeat_1200s_01').replace('validation/campus_1200s_20261118/data','validation/campus_repeat_1200s_20261118/data')
Path('/mnt/d/HT-Campus-Repeat-1200s-20261118/extract_maps.py').write_text(src.rstrip()+'\n')
Path('/mnt/d/HT-Campus-Repeat-1200s-20261118/extract.sh').write_text('set -e\nsource /home/lzz/ht_campus_repeat_1200s_20261118/env.sh\n/home/lzz/ht_campus_repeat_1200s_20261118/venv/bin/python /mnt/d/HT-Campus-Repeat-1200s-20261118/extract_maps.py\n')
