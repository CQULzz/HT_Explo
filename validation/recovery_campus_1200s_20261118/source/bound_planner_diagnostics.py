from pathlib import Path
p=Path('/mnt/d/HT-Recovery-Campus-1200s-20261118/postprocess_long.py');s=p.read_text();s=s.replace("diagnostics=[l for l in lines if 'EXPLORATION_DIAG' in l]", "diagnostics=[l for l in lines if 'EXPLORATION_DIAG' in l and (lambda m: m is not None and start<=float(m[1])<=end)(re.search(r'\\[([0-9]{10}\\.[0-9]+)\\]',l))]");p.write_text(s)
