#!/usr/bin/env bash
set -euo pipefail
ht_replay_repo="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
ht_replay_folder="$ht_replay_repo/docs/results/ht_tare_matched_rviz_replay_2026-10-21"
ht_replay_files=("$ht_replay_folder/rviz_comparison_4x.mp4" "$ht_replay_folder/detail/rviz_detail_4x.mp4")
if (( $# )); then
  ht_replay_files=("$@")
fi
for ht_replay_file in "${ht_replay_files[@]}"; do
  if [[ ! -f "$ht_replay_file" ]]; then
    printf '视频不存在：%s\n见报告中的GitHub Release下载链接。\n' "$ht_replay_file" >&2
    exit 1
  fi
done
exec /usr/bin/vlc --no-one-instance --avcodec-hw=none --vout=xcb_x11 -- "${ht_replay_files[@]}"
