from pathlib import Path
p=Path('/mnt/d/HT-TARE-Coverage-Diagnosis-20261118/extract_full_range.py');s=p.read_text(encoding='utf-8-sig').replace("Path('/home/lzz/tare_native_campus_repeat_20261118/runs/native_campus_02')","Path('/home/lzz/ht_campus_to_finish_20261118/runs/campus_to_finish_01')").replace('native_full_range_','ht_full_range_').replace('native_ROI_','ht_ROI_').replace("'FULL_RANGE_OBSERVATION_CHECK.json'","'HT_FULL_RANGE_OBSERVATION_CHECK.json'")
# Native connected-ground seeds remain reference coordinates only; do not claim identical body reachability.
s=s.replace("print(json.dumps(summary,indent=2))","print(json.dumps(summary,indent=2))")
(Path('/mnt/d/HT-TARE-Coverage-Diagnosis-20261118/extract_ht_full_range.py')).write_text(s)
Path('/mnt/d/HT-TARE-Coverage-Diagnosis-20261118/ht_full_range.sh').write_text('set -e\nsource /home/lzz/tare_native_campus_20261118/env.sh\n/usr/bin/python3 /mnt/d/HT-TARE-Coverage-Diagnosis-20261118/extract_ht_full_range.py > /home/lzz/ht_tare_coverage_diagnosis_20261118/ht_full_range.log 2>&1\n')
