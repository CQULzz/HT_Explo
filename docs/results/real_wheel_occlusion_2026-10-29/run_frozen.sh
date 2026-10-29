#!/bin/bash
set -e
source /opt/ros/jazzy/setup.bash
source '/home/lzz/my test/ht_cupy_gpu_ws_20261028/install_stable/setup.bash'
export ROS_DOMAIN_ID=187
export PYTHONPATH='/home/lzz/my test/ht_cupy_gpu_ws_20261028/src/elevation_mapping_cupy_2204/elevation_mapping_cupy/script':${PYTHONPATH}
PY='/home/lzz/.venvs/ht_real_gpu_20261028/bin/python'
R='/home/lzz/my test/HT_Explo-real-review-20261028'
I='/media/lzz/My Passport/HT_newbags_replay_20261028/inputs'
O='/media/lzz/My Passport/HT_body_occlusion_fix_2026-10-29'
C='/home/lzz/my test/ht_cupy_gpu_ws_20261028/src/elevation_mapping_cupy_2204/elevation_mapping_cupy'
"$PY" "$R/tools/ht_cupy_bridge/replay_newbags_rviz.py" --bag "$I/rosbag2_2026_10_28-17_00_43/rosbag2_2026_10_28-17_00_43" --output "$O/frozen_disabled_baseline_moving" --cupy-package "$C" --calibration-file "$O/baseline_scout_extrinsics.yaml" --surface-registration > "$O/frozen_disabled_baseline_moving.log" 2>&1
"$PY" "$R/tools/ht_cupy_bridge/replay_newbags_rviz.py" --bag "$I/rosbag2_2026_10_28-16_53_17/rosbag2_2026_10_28-16_53_17" --output "$O/frozen_default_stationary" --cupy-package "$C" > "$O/frozen_default_stationary.log" 2>&1
"$PY" "$R/tools/ht_cupy_bridge/replay_newbags_rviz.py" --bag "$I/rosbag2_2026_10_28-17_00_43/rosbag2_2026_10_28-17_00_43" --output "$O/frozen_default_moving" --cupy-package "$C" > "$O/frozen_default_moving.log" 2>&1
"$PY" "$R/tools/ht_cupy_bridge/replay_newbags_rviz.py" --bag "$I/rosbag2_2026_10_28-16_53_17/rosbag2_2026_10_28-16_53_17" --output "$O/frozen_registered_stationary" --cupy-package "$C" --surface-registration > "$O/frozen_registered_stationary.log" 2>&1
"$PY" "$R/tools/ht_cupy_bridge/replay_newbags_rviz.py" --bag "$I/rosbag2_2026_10_28-17_00_43/rosbag2_2026_10_28-17_00_43" --output "$O/frozen_registered_moving" --cupy-package "$C" --surface-registration > "$O/frozen_registered_moving.log" 2>&1
"$PY" -c 'from pathlib import Path;Path("/media/lzz/My Passport/HT_body_occlusion_fix_2026-10-29/FROZEN_COMPLETE.txt").write_text("Four complete candidate replays and one disabled regression completed.\n")'
