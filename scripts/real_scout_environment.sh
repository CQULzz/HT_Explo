#!/usr/bin/env bash
# Source a system ROS distribution without importing vehicle workspace overlays.
ht_ros_distro="${HT_ROS_DISTRO:-${ROS_DISTRO:-jazzy}}"
if [[ ! -f "/opt/ros/$ht_ros_distro/setup.bash" && -z "${HT_ROS_DISTRO:-}" && -f /opt/ros/humble/setup.bash ]]; then
  ht_ros_distro=humble
fi
if [[ ! -f "/opt/ros/$ht_ros_distro/setup.bash" ]]; then
  echo "ROS distribution unavailable: $ht_ros_distro" >&2
  return 1
fi
unset AMENT_PREFIX_PATH CMAKE_PREFIX_PATH COLCON_PREFIX_PATH CMAKE_MODULE_PATH PYTHONPATH
ht_python_user_site="$(python3 -m site --user-site)"
for ht_library_dir in /usr/local/cuda/lib64 "$ht_python_user_site"/nvidia/*/lib; do
  if [[ -d "$ht_library_dir" ]]; then
    export LD_LIBRARY_PATH="$ht_library_dir${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
  fi
done
source "/opt/ros/$ht_ros_distro/setup.bash"
