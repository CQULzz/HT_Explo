set -eo pipefail
R=/home/lzz/ht_execution_300s_20261113
P=/home/lzz/HT_Explo_execution_20261113
source /opt/ros/humble/setup.bash
export CMAKE_BUILD_PARALLEL_LEVEL=3 MAKEFLAGS=-j3
cd "$R"
colcon --log-base build_logs_cmu build --base-paths /home/lzz/cmu_sim_20261110/src --packages-select vehicle_simulator terrain_analysis terrain_analysis_ext sensor_scan_generation local_planner --build-base build_cmu --install-base install_cmu --executor sequential --cmake-args -DCMAKE_BUILD_TYPE=Release -DBUILD_TESTING=OFF > setup/build_cmu.log 2>&1
source install_cmu/setup.bash
colcon --log-base build_logs_native build --base-paths /home/lzz/tare_native_20261110/src --build-base build_native --install-base install_native --executor sequential --cmake-args -DCMAKE_BUILD_TYPE=Release -DBUILD_TESTING=OFF > setup/build_native.log 2>&1
colcon --log-base build_logs_gate build --base-paths "$P/src/cmu_local_planner_ht" --build-base build_gate --install-base install_gate --executor sequential --cmake-args -DCMAKE_BUILD_TYPE=Release > setup/build_gate.log 2>&1
colcon --log-base build_logs_mapper build --base-paths "$R/mapper_source/elevation_mapping_cupy_2204" --packages-up-to elevation_mapping_cupy --build-base build_mapper --install-base install_mapper --executor sequential --cmake-args -DCMAKE_BUILD_TYPE=Release -DBUILD_TESTING=OFF > setup/build_mapper.log 2>&1
echo BUILD_COMPLETE
