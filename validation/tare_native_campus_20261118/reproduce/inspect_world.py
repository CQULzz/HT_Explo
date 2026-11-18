from pathlib import Path
import xml.etree.ElementTree as ET
for name in ['/home/lzz/cmu_sim_20261110/src/vehicle_simulator/world/campus.world','/home/lzz/ht_helios_collision_20261115/scene_assets/campus.world']:
 r=ET.parse(name).getroot();print(name,'models',[(m.get('name'),m.findtext('pose')) for m in r.findall('.//world/model')],'plugins',[(p.get('name'),p.get('filename')) for p in r.findall('.//world/plugin')])
p=Path('/home/lzz/aede_tare_indoor_baseline_20261117/baseline.launch.py');print(p.read_text()[:12000])
