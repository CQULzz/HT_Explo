#!/bin/bash
set -e
R=/home/lzz/ht_helios_collision_20261115
source "$R/env.sh"
for entity in robot lidar camera; do gz sdf -k "$R/common_sensor_optical/$entity.sdf"; done > "$R/setup/sdf_validation.log" 2>&1
export ROS_DOMAIN_ID=229 GAZEBO_MASTER_URI=http://127.0.0.1:11518
python3 /mnt/d/HT-Helios-Collision-20261115/setup/static_probes.py > "$R/setup/static_optical.log" 2>&1
python3 /mnt/d/HT-Helios-Collision-20261115/setup/verify_static.py
export ROS_DOMAIN_ID=232 GAZEBO_MASTER_URI=http://127.0.0.1:11520
python3 /mnt/d/HT-Helios-Collision-20261115/setup/check_rotation.py > "$R/setup/rotation_optical.log" 2>&1
python3 /mnt/d/HT-Helios-Collision-20261115/setup/plot_static.py
echo FINAL_PROBES_COMPLETE
