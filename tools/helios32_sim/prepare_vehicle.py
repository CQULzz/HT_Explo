"""Derive the heading-consistent CMU sensor carrier from its pinned source.

CMU's original scanner is heading-fixed and registration intentionally omits yaw.
The Scout scanner rotates with the chassis, so both sides must change together.
The vehicle's velocity integration and terrain estimation are unchanged.
"""
from pathlib import Path
import argparse,hashlib,json
def derive(source,target):
    data=source.read_bytes();digest=hashlib.sha256(data).hexdigest()
    if digest!='2ef539a2dbfd886df254e92a1053e33ea04eb777ca333bfadf000d25371e0eb9':raise ValueError('Unexpected CMU baseline; inspect before adapting')
    text=data.decode()
    def replace(old,new):
        nonlocal text
        if text.count(old)!=1:raise ValueError('Unexpected source at '+old[:60])
        text=text.replace(old,new)
    replace('float terrainRecPitch = terrainPitch;\n\n  if (use_gazebo_time)', 'float terrainRecPitch = terrainPitch;\n  float vehicleRecYaw = vehicleYaw;\n\n  if (use_gazebo_time)')
    replace('terrainRecPitch = terrainPitchStack[odomRecIDPointer];','terrainRecPitch = terrainPitchStack[odomRecIDPointer];\n    vehicleRecYaw = vehicleYawStack[odomRecIDPointer];')
    replace('float sinTerrainRecRoll = sin(terrainRecRoll);','const float scanRoll=terrainRecRoll*cos(vehicleRecYaw)+terrainRecPitch*sin(vehicleRecYaw);\n  const float scanPitch=-terrainRecRoll*sin(vehicleRecYaw)+terrainRecPitch*cos(vehicleRecYaw);\n  float sinTerrainRecRoll = sin(scanRoll);')
    replace('float cosTerrainRecRoll = cos(terrainRecRoll);','float cosTerrainRecRoll = cos(scanRoll);')
    replace('float sinTerrainRecPitch = sin(terrainRecPitch);','float sinTerrainRecPitch = sin(scanPitch);')
    replace('float cosTerrainRecPitch = cos(terrainRecPitch);','float cosTerrainRecPitch = cos(scanPitch);')
    replace('float pointX3 = pointX2 + vehicleRecX;','float pointX3 = cos(vehicleRecYaw)*pointX2-sin(vehicleRecYaw)*pointY2 + vehicleRecX;')
    replace('float pointY3 = pointY2 + vehicleRecY;','float pointY3 = sin(vehicleRecYaw)*pointX2+cos(vehicleRecYaw)*pointY2 + vehicleRecY;')
    replace('quat_tf.setRPY(terrainRoll, terrainPitch, 0);','quat_tf.setRPY(vehicleRoll, vehiclePitch, vehicleYaw);')
    # A SIGINT may invalidate the ROS context between the loop check and spin.
    # Preserve runtime errors while permitting a normal shutdown in that race.
    replace('  while (status)\n  {','  try {\n  while (status)\n  {')
    replace('  return 0;\n}', '  } catch (const rclcpp::exceptions::RCLError &) {\n    if (rclcpp::ok()) throw;\n  }\n  return 0;\n}')
    text='// CMU AEDE vehicle carrier, upstream commit 158e67b; upstream package license BSD.\n// Adaptation: rotate scanner with body and apply the matching yaw in registration.\n'+text
    text='\n'.join(line.rstrip() for line in text.splitlines())+'\n'
    target.write_text(text)
    target.with_suffix('.source.json').write_text(json.dumps({'upstream_commit':'158e67b31b644ed1e8b06eb1d7f70e183cc62591','input_sha256':digest,'output_sha256':hashlib.sha256(text.encode()).hexdigest(),'changes':['scanner body heading','matching roll/pitch/yaw registration','read existing historical yaw stack','handle ROS-context shutdown race','strip trailing whitespace'],'unchanged':['velocity integration','terrain fitting','control laws']},indent=2))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('source',type=Path);p.add_argument('output',type=Path);a=p.parse_args();derive(a.source,a.output)
