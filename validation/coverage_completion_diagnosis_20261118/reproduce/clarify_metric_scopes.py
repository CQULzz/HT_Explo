from pathlib import Path
p=Path('/mnt/d/HT-TARE-Coverage-Diagnosis-20261118/REPORT_zh.md');s=p.read_text(encoding='utf-8-sig').replace('UNSEEDED_COMPONENTS.json保留分块几何证据，不将不连通的保守点云图等同物理不可达。','UNSEEDED_COMPONENTS.json保留分块几何证据，其unobserved_cells仍沿用旧15m口径，本文只引用几何高差，不用该字段统计全距离遗漏；不将不连通的保守点云图等同物理不可达。');p.write_text(s)
