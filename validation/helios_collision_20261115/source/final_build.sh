#!/bin/bash
set -e
R=/home/lzz/ht_helios_collision_20261115
REPO='/mnt/c/Users/李哲舟/Desktop/python code/work/ht_execution_fixes'
source "$R/env.sh"
python3 "$REPO/tools/helios32_sim/prepare_vehicle.py" /home/lzz/cmu_sim_20261110/src/vehicle_simulator/src/vehicleSimulator.cpp "$REPO/src/helios32_sim/src/vehicleSimulator.cpp"
cp "$REPO/src/helios32_sim/src/vehicleSimulator.cpp" "$R/project/src/helios32_sim/src/"
cp "$REPO/src/helios32_sim/src/vehicleSimulator.source.json" "$R/project/src/helios32_sim/src/"
mv "$R/common_sensor_optical" "$R/common_sensor_optical_before_unique_names"
mv "$R/static_probes_optical" "$R/static_probes_optical_before_unique_names"
mv "$R/rotation_probe_optical" "$R/rotation_probe_optical_before_unique_names"
cp "$R/setup/static_optical.log" "$R/setup/static_optical_before_unique_names.log"
cp "$R/setup/rotation_optical.log" "$R/setup/rotation_optical_before_unique_names.log"
python3 "$REPO/tools/helios32_sim/prepare_assets.py" --package-dir /mnt/d/HT-URDF-Compare-20261115/setup/eletranskit_scout/src/ele_scout_kit --output "$R/common_sensor_optical"
cd "$R/project"
colcon build --packages-select helios32_sim --build-base "$R/build" --install-base "$R/install" --executor sequential > "$R/setup/vehicle_final_build.log" 2>&1
echo FINAL_BUILD_COMPLETE
