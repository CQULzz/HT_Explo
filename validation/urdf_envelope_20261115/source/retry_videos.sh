#!/bin/bash
set -e
source /home/lzz/ht_urdf_compare_20261115/env.sh
python3 /mnt/d/HT-URDF-Compare-20261115/setup/archive_failed_video.py
python3 /mnt/d/HT-URDF-Compare-20261115/setup/prepare_video_tools.py
python3 /mnt/d/HT-URDF-Compare-20261115/setup/make_videos.py > /home/lzz/ht_urdf_compare_20261115/setup/videos_retry.log 2>&1
