from pathlib import Path
p=Path('/mnt/d/HT-Campus-Repeat-1200s-20261118/analyze_backtracking.py');s=p.read_text();s=s.replace("summary={'overall':part(np.ones(len(d),bool))", "summary={'proximity_sensitivity':{str(radius):{'route_revisit_distance_m':float(d[nearest<=radius].sum()),'route_revisit_fraction':float(d[nearest<=radius].sum()/d.sum()) if d.sum() else None} for radius in [1.,3.,5.]},'overall':part(np.ones(len(d),bool))");p.write_text(s)
import ast;ast.parse(s);print('Revisit sensitivity thresholds1/3/5m added, before final analysis')
