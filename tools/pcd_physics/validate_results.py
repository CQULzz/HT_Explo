"""Postcheck recorded results without rerunning or changing dynamics."""
from pathlib import Path
import json,math
ROOT=Path('/home/lzz/pcd_physics_20261110')
rows=json.loads((ROOT/'RESULTS.json').read_text());validated=[]
for d in rows:
 item={k:d.get(k) for k in ['case','gear','friction','flat_control','center_only','status','clean_pass','maximum_progress_m','chassis_contact_s','max_chassis_penetration_m','max_tilt_deg','center_crossing']}
 if d['status']=='UNSUPPORTED_INITIAL_WHEEL_LOCATION':item['assessment']='INCONCLUSIVE_MISSING_MESH_SUPPORT'
 elif d['center_only']:
  final=d['final_pose'];xy=d['case']['xy'];yaw=math.radians(d['case']['heading_deg']);distance=math.dist([final['x'],final['y']],xy);error=abs(math.degrees(math.atan2(math.sin(final['yaw']-yaw),math.cos(final['yaw']-yaw))))
  item.update(final_center_xy_error_m=distance,final_center_yaw_error_deg=error)
  item['assessment']='POSE_SUPPORTED_WITHOUT_CHASSIS_CONTACT' if d.get('clean_pass') and distance<=.1 and error<=15 else 'INCONCLUSIVE_INITIAL_CONTACT_OR_POSE_DISPLACEMENT'
 elif d.get('clean_pass'):item['assessment']='CROSSED_REQUESTED_POSE_AND_SEGMENT'
 else:item['assessment']='SPECIFIED_STRAIGHT_PROBE_NOT_COMPLETED'
 validated.append(item)
output=json.dumps(validated,indent=2);existing=ROOT/'VALIDATED_RESULTS.json'
if existing.exists():assert json.loads(existing.read_text())==validated
else:existing.write_text(output)
print('Validated',len(validated),'recorded local trials')
