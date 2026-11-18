from pathlib import Path
import xml.etree.ElementTree as ET,json
r=Path('/home/lzz/tare_native_campus_20261118');text=(r/'setup/tare_ldd.txt').read_text();assert 'not found' not in text,text
s=ET.parse(r/'setup/lidar_expanded.urdf').getroot();sensors=[{'attributes':x.attrib,'update_rate':x.findtext('update_rate'),'horizontal_samples':x.findtext('.//horizontal/samples'),'vertical_samples':x.findtext('.//vertical/samples')} for x in s.findall('.//sensor')]
assert any(x['vertical_samples']=='16' and x['horizontal_samples']=='350' for x in sensors),sensors
text=(r/'observer.py').read_text();assert 'create_subscription(GridMap' not in text and 'n.last_ht is not None' not in text
out={'ldd_resolved':True,'sensors':sensors,'observer_has_no_ht_subscription_or_ht_freshness_dependency':True};(r/'setup/PREFLIGHT.json').write_text(json.dumps(out,indent=2));print(json.dumps(out))
