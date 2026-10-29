#!/bin/bash
set -e
source /opt/ros/jazzy/setup.bash
export ROS_DOMAIN_ID=192
PY='/home/lzz/.venvs/ht_real_gpu_20261028/bin/python'
R='/home/lzz/my test/HT_Explo-real-review-20261028'
O='/media/lzz/My Passport/HT_wide_view_repeat_2026-10-29_15-53-04'
"$PY" "$R/tools/ht_cupy_bridge/record_wide_replay.py" --input "$O/moving" --scene "$O/scene_moving" --output "$O/video_moving" --label HT_moving > "$O/record_moving_final.log" 2>&1
"$PY" "$R/tools/ht_cupy_bridge/record_wide_replay.py" --input "$O/stationary" --scene "$O/scene_stationary" --output "$O/video_stationary" --label HT_stationary > "$O/record_stationary_final.log" 2>&1
