#!/usr/bin/env bash
set -euo pipefail
ht_repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
if [[ "${1:-}" == '--previous' ]]; then
  ht_playlist="$ht_repo_root/docs/results/ht_multiscene_10min_2026-10-17/videos.m3u"
else
  ht_playlist="$ht_repo_root/docs/results/ht_recovery_10min_2026-10-17/videos.m3u"
  printf '最新修复复测：隧道、室内各10分钟；末段为返航完成后停车。\n'
  printf '查看上一轮五环境，请加 --previous。\n'
fi
if [[ ! -f "$ht_playlist" ]] || ! rg -q '^[^#[:space:]]' "$ht_playlist"; then
  printf '未找到完整视频播放列表：%s\n' "$ht_playlist"
  exit 1
fi
exec /usr/bin/vlc --no-one-instance --avcodec-hw=none --vout=xcb_x11 -- "$ht_playlist"
