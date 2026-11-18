from pathlib import Path
import difflib,json,shutil
root=Path('/home/lzz/tare_native_campus_20261118');p=root/'project/src/tare_planner/src/sensor_coverage_planner/sensor_coverage_planner_ground.cpp';old=p.read_text();new=old.replace('  this->declare_parameter<bool>("kAutoStart", false);','  this->declare_parameter<bool>("kAutoStart", false);\n  this->declare_parameter<bool>("kUseFrontier", true); // Bind the upstream ROS2 YAML parameter.')
assert new!=old;p.write_text(new);(root/'setup/frontier_ros2_parameter.patch').write_text(''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile='upstream/sensor_coverage_planner_ground.cpp',tofile='runtime/sensor_coverage_planner_ground.cpp')))
for name in ['local_planner','terrain_analysis','terrain_analysis_ext','sensor_scan_generation','vehicle_simulator']:shutil.copytree(Path('/home/lzz/cmu_sim_20261110/src')/name,root/'project/src'/name,symlinks=True)
(root/'env.sh').write_text('''source /opt/ros/humble/setup.bash
source /home/lzz/ht_execution_300s_20261113/install_cmu/local_setup.bash
export ROS_DOMAIN_ID=205 ROS_LOCALHOST_ONLY=1
export OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=1
export GAZEBO_MASTER_URI=http://127.0.0.1:11589
export GAZEBO_MODEL_PATH=/usr/share/gazebo-11/models:/opt/ros/humble/share:/home/lzz/cmu_sim_20261110/src/vehicle_simulator/mesh
export GAZEBO_MODEL_DATABASE_URI=
export ROS_LOG_DIR=/home/lzz/tare_native_campus_20261118/ros_logs
export LD_LIBRARY_PATH=/home/lzz/tare_native_campus_20261118/project/src/tare_planner/or-tools/lib:$LD_LIBRARY_PATH
''')
(root/'build.sh').write_text('set -e\nsource /home/lzz/tare_native_campus_20261118/env.sh\ncd /home/lzz/tare_native_campus_20261118/project\ncolcon build --packages-select local_planner terrain_analysis terrain_analysis_ext sensor_scan_generation vehicle_simulator tare_planner --parallel-workers 2 --cmake-args -DCMAKE_BUILD_TYPE=Release > /home/lzz/tare_native_campus_20261118/setup/build.log 2>&1\n')
print('isolated sources restored plus one ROS2 parameter-binding line')
print('reference',Path('/home/lzz/ht_campus_to_finish_20261118/analysis/CAMPUS_REFERENCE.json').read_text())
