#!/bin/bash
set -e
source /opt/ros/jazzy/setup.bash
source '/home/lzz/my test/ht_cupy_gpu_ws_20261028/install_stable/setup.bash'
export ROS_DOMAIN_ID=191
export PYTHONPATH='/home/lzz/my test/ht_cupy_gpu_ws_20261028/src/elevation_mapping_cupy_2204/elevation_mapping_cupy/script':${PYTHONPATH}
PY='/home/lzz/.venvs/ht_real_gpu_20261028/bin/python'
R='/home/lzz/my test/HT_Explo-real-review-20261028'
I='/media/lzz/My Passport/HT_newbags_replay_20261028/inputs'
O='/media/lzz/My Passport/HT_wide_view_repeat_2026-10-29_15-53-04'
C='/home/lzz/my test/ht_cupy_gpu_ws_20261028/src/elevation_mapping_cupy_2204/elevation_mapping_cupy'
"$PY" "$R/tools/ht_cupy_bridge/replay_newbags_rviz.py" --bag "$I/rosbag2_2026_10_28-17_00_43/rosbag2_2026_10_28-17_00_43" --output "$O/moving" --cupy-package "$C" --surface-registration > "$O/moving.log" 2>&1
"$PY" "$R/tools/ht_cupy_bridge/replay_newbags_rviz.py" --bag "$I/rosbag2_2026_10_28-16_53_17/rosbag2_2026_10_28-16_53_17" --output "$O/stationary" --cupy-package "$C" --surface-registration > "$O/stationary.log" 2>&1
