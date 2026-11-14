from pathlib import Path
import shutil
r=Path('/home/lzz/ht_campus_pcd_20261114')
for name in ['run.py','simulation.launch.py']:
    dest=r/'setup'/('initial_'+name)
    if not dest.exists():shutil.copy2(r/name,dest)
(r/'scene_assets/camera_without_sensor.sdf').write_text('<sdf version="1.6"><model name="camera"><static>true</static><link name="camera_link"/></model></sdf>')
p=r/'simulation.launch.py';s=p.read_text()
s=s.replace('from launch.actions import OpaqueFunction,IncludeLaunchDescription,DeclareLaunchArgument','from launch.actions import OpaqueFunction,IncludeLaunchDescription,DeclareLaunchArgument,TimerAction')
s=s.replace("module=SourceFileLoader('ht_only_vehicle',str(source)).load_module();original=module.Node", "module=SourceFileLoader('ht_only_vehicle',str(source)).load_module();original=module.Node\n spawn_index=[0]\n if scene=='campus':module.TimerAction=lambda **kw: TimerAction(period=90.,actions=kw['actions'])")
anchor='  return original(*args,**kwargs)'
s=s.replace(anchor,"""  if scene=='campus' and kwargs.get('package')=='gazebo_ros' and kwargs.get('executable')=='spawn_entity.py':
   arguments=kwargs.get('arguments',[])
   arguments=[str(ROOT/'scene_assets/camera_without_sensor.sdf') if isinstance(a,str) and a.endswith('/urdf/camera.urdf.xacro') else a for a in arguments]
   kwargs['arguments']=[*arguments,'-timeout','180.0']
   result=original(*args,**kwargs);delay=60.+spawn_index[0]*2.;spawn_index[0]+=1
   return TimerAction(period=delay,actions=[result])
"""+anchor)
p.write_text(s)
collect=Path('/home/lzz/HT_Explo_execution_20261113/tools/cmu_minimal/collect.py').read_text().replace('deadline=time.monotonic()+90','deadline=time.monotonic()+300').replace('Inputs not ready in 90 seconds','Inputs not ready in 300 seconds')
(r/'startup_collect.py').write_text(collect)
p=r/'run.py';s=p.read_text().replace("PROJECT/'tools/cmu_minimal/collect.py'", "ROOT/'startup_collect.py'").replace('duration+150','duration+420')
s=s.replace("files += [ROOT/'run.py'", "files += [ROOT/'startup_collect.py']\n files += [ROOT/'run.py'")
s=s.replace("files += [p for p in (ROOT/'scene_assets').rglob('*') if p.is_file()]", "files += [p for p in (ROOT/'scene_assets').rglob('*') if p.is_file()]\n files += [p for p in Path('/home/lzz/cmu_sim_20261110/src/vehicle_simulator/mesh/campus').rglob('*') if p.is_file()]")
p.write_text(s)
print('Startup-only correction: delayed spawn/controller; unused RGB camera removed; unchanged LiDAR/world collision/HT/TARE')
