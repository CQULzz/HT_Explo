#!/usr/bin/env bash
set -euo pipefail
ht_repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
if [[ "${1:-}" == '--previous' ]]; then
  ht_playlist="$ht_repo_root/docs/results/ht_multiscene_10min_2026-10-17/videos.m3u"
elif [[ "${1:-}" == '--recovery' ]]; then
  ht_playlist="$ht_repo_root/docs/results/ht_recovery_10min_2026-10-17/videos.m3u"
elif [[ "${1:-}" == '--fine' ]]; then
  ht_playlist="$ht_repo_root/docs/results/ht_zero_twist_fine_heading_10min_2026-10-18/videos.m3u"
elif [[ "${1:-}" == '--mixed' ]]; then
  ht_playlist="$ht_repo_root/docs/results/ht_mixed_turns_10min_2026-10-18/videos.m3u"
elif [[ "${1:-}" == '--configuration' ]]; then
  ht_playlist="$ht_repo_root/docs/results/ht_configuration_gate_10min_2026-10-18/videos.m3u"
elif [[ "${1:-}" == '--postfilter' ]]; then
  ht_playlist="$ht_repo_root/docs/results/ht_postfilter_obstacles_10min_2026-10-18/videos.m3u"
elif [[ "${1:-}" == '--geometry-index' ]]; then
  ht_playlist="$ht_repo_root/docs/results/ht_geometry_index_10min_2026-10-18/videos.m3u"
  printf '阶段27失败记录：41.90米；136.5秒后几何拒绝起点而停滞。\n'
else
  ht_playlist="$ht_repo_root/docs/results/ht_execution_geometry_10min_2026-10-18/videos.m3u"
  printf '最新阶段28室内完整10分钟：执行几何检查及跟踪余量；117.66米，2292.75立方米。\n'
  printf '约352秒内部完成返航，后段为完成后停车；尚未独立验证全场景覆盖或多环境稳定性。\n'
  printf '上一轮失败加 --geometry-index；阶段26加 --postfilter；较高观测体积的阶段23加 --configuration；历史五环境加 --previous。\n'
fi
if [[ ! -f "$ht_playlist" ]] || ! rg -q '^[^#[:space:]]' "$ht_playlist"; then
  printf '未找到完整视频播放列表：%s\n' "$ht_playlist"
  exit 1
fi
exec /usr/bin/vlc --no-one-instance --avcodec-hw=none --vout=xcb_x11 -- "$ht_playlist"
