#!/bin/bash
set -e
source /opt/ros/jazzy/setup.bash
source '/home/lzz/my test/ht_cupy_gpu_ws_20261028/install_stable/setup.bash'
export ROS_DOMAIN_ID=183
export PYTHONPATH='/home/lzz/my test/ht_cupy_gpu_ws_20261028/src/elevation_mapping_cupy_2204/elevation_mapping_cupy/script':${PYTHONPATH}
'/home/lzz/.venvs/ht_real_gpu_20261028/bin/python' '/media/lzz/My Passport/HT_texture_source_fix_2026-10-29/run_provenance.py' "$@"
