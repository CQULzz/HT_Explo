source /opt/ros/humble/setup.bash
source /home/lzz/ht_execution_300s_20261113/install_cmu/local_setup.bash
export ROS_DOMAIN_ID=205 ROS_LOCALHOST_ONLY=1
export OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=1
export GAZEBO_MASTER_URI=http://127.0.0.1:11589
export GAZEBO_MODEL_PATH=/usr/share/gazebo-11/models:/opt/ros/humble/share:/home/lzz/cmu_sim_20261110/src/vehicle_simulator/mesh
export GAZEBO_MODEL_DATABASE_URI=
export ROS_LOG_DIR=/home/lzz/tare_native_campus_20261118/ros_logs
export LD_LIBRARY_PATH=/home/lzz/tare_native_campus_20261118/project/src/tare_planner/or-tools/lib:$LD_LIBRARY_PATH

source /home/lzz/tare_native_campus_20261118/project/install/local_setup.bash
