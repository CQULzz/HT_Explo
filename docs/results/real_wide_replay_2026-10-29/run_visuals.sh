#!/bin/bash
set -e
source /opt/ros/jazzy/setup.bash
export ROS_DOMAIN_ID=192
export PYTHONPATH='/home/lzz/my test/HT_Explo-real-review-20261028/src/ht_scout_bridge':${PYTHONPATH}
PY='/home/lzz/.venvs/ht_real_gpu_20261028/bin/python'
R='/home/lzz/my test/HT_Explo-real-review-20261028'
I='/media/lzz/My Passport/HT_newbags_replay_20261028/inputs'
O='/media/lzz/My Passport/HT_wide_view_repeat_2026-10-29_15-53-04'
"$PY" "$R/tools/ht_cupy_bridge/prepare_replay_scene.py" --input "$O/moving" --bag "$I/rosbag2_2026_10_28-17_00_43/rosbag2_2026_10_28-17_00_43" --output "$O/scene_moving" > "$O/scene_moving.log" 2>&1
"$PY" "$R/tools/ht_cupy_bridge/record_wide_replay.py" --input "$O/moving" --scene "$O/scene_moving" --output "$O/video_moving" --label HT_moving > "$O/record_moving.log" 2>&1
"$PY" "$R/tools/ht_cupy_bridge/prepare_replay_scene.py" --input "$O/stationary" --bag "$I/rosbag2_2026_10_28-16_53_17/rosbag2_2026_10_28-16_53_17" --output "$O/scene_stationary" > "$O/scene_stationary.log" 2>&1
"$PY" "$R/tools/ht_cupy_bridge/record_wide_replay.py" --input "$O/stationary" --scene "$O/scene_stationary" --output "$O/video_stationary" --label HT_stationary > "$O/record_stationary.log" 2>&1
