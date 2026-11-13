source /opt/ros/humble/setup.bash
source /home/lzz/ht_execution_300s_20261113/install_cmu/setup.bash
source /home/lzz/ht_repeat_20261114/install_native/setup.bash
source /home/lzz/ht_execution_300s_20261113/install_mapper/setup.bash
source /home/lzz/ht_execution_300s_20261113/install_gate/setup.bash
export ROS_DOMAIN_ID=215 ROS_LOCALHOST_ONLY=1
export OMP_NUM_THREADS=3 OPENBLAS_NUM_THREADS=1
export LD_LIBRARY_PATH=/usr/lib/wsl/lib:$LD_LIBRARY_PATH
export ROS_LOG_DIR=/home/lzz/ht_execution_300s_20261113/ros_logs
export LD_LIBRARY_PATH=/home/lzz/ht_execution_300s_20261113/venv/lib/python3.10/site-packages/nvidia/cuda_nvrtc/lib:/home/lzz/ht_execution_300s_20261113/venv/lib/python3.10/site-packages/nvidia/cuda_runtime/lib:$LD_LIBRARY_PATH
export LD_LIBRARY_PATH=/home/lzz/tare_native_20261110/src/tare_planner/or-tools/lib:$LD_LIBRARY_PATH
export GAZEBO_MODEL_PATH=/usr/share/gazebo-11/models:/home/lzz/cmu_sim_20261110/src/vehicle_simulator/mesh
