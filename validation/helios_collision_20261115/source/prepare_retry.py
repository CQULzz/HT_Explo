from pathlib import Path
import json,xml.etree.ElementTree as ET
root=Path('/home/lzz/ht_helios_collision_20261115');assets=root/'common_sensor'
camera=ET.Element('sdf',version='1.7');m=ET.SubElement(camera,'model',name='camera');l=ET.SubElement(m,'link',name='pose_anchor');ET.SubElement(l,'gravity').text='false';ET.SubElement(l,'kinematic').text='true';ET.ElementTree(camera).write(assets/'camera.sdf',encoding='unicode')
budget=json.loads((root/'BUDGET.json').read_text());budget['attempts'][0]['state']='ABORTED_INFRA_UNUSED_CAMERA_ENTITY';budget['attempts'][0]['reason']='Carrier still updates virtual camera entity. Restore empty pose anchor; actual physical camera remains in opaque Scout mesh.';(root/'BUDGET.json').write_text(json.dumps(budget,indent=2))
