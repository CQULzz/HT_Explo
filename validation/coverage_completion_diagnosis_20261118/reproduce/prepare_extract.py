from pathlib import Path
p=Path('/mnt/d/HT-TARE-Coverage-Diagnosis-20261118/extract.sh');p.write_text('set -e\nsource /home/lzz/tare_native_campus_20261118/env.sh\n/usr/bin/python3 /mnt/d/HT-TARE-Coverage-Diagnosis-20261118/extract_task_clouds.py > /home/lzz/ht_tare_coverage_diagnosis_20261118/task_clouds.log 2>&1\n')
