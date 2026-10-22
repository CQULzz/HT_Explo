#!/usr/bin/env bash
set -euo pipefail
ht_indoor_repo="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
ht_indoor_result="$ht_indoor_repo/docs/results/ht_indoor_repeat_2026-10-22"
ht_indoor_videos=("$ht_indoor_result/first60_comparison.mp4" "$ht_indoor_result/indoor/camera_h264.mp4")
if (( $# )); then ht_indoor_videos=("$@"); fi
for ht_indoor_video in "${ht_indoor_videos[@]}"; do
  if [[ ! -f "$ht_indoor_video" ]]; then
    printf '视频不存在：%s\n请从本轮GitHub Release下载。\n' "$ht_indoor_video" >&2
    exit 1
  fi
done
exec /usr/bin/vlc --no-one-instance --avcodec-hw=none --vout=xcb_x11 -- "${ht_indoor_videos[@]}"
