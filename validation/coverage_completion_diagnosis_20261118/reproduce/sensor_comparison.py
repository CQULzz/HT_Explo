from pathlib import Path
import json,xml.etree.ElementTree as ET
root=Path('/home/lzz/ht_campus_to_finish_20261118/common_sensor_crop_box');print((root/'MANIFEST.json').read_text()[:5000])
for p in [root/'lidar.sdf',Path('/home/lzz/tare_native_campus_20261118/setup/lidar_expanded.urdf')]:
 e=ET.parse(p).getroot();print('SENSOR',p)
 for sensor in e.iter('sensor'):
  print(ET.tostring(sensor,encoding='unicode')[:5500])
