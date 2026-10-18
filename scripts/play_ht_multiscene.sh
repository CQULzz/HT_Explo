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
elif [[ "${1:-}" == '--execution-geometry' ]]; then
  ht_playlist="$ht_repo_root/docs/results/ht_execution_geometry_10min_2026-10-18/videos.m3u"
elif [[ "${1:-}" == '--cell-audit' ]]; then
  ht_playlist="$ht_repo_root/docs/results/ht_cell_audit_10min_2026-10-18/videos.m3u"
elif [[ "${1:-}" == '--pending-gain' ]]; then
  ht_playlist="$ht_repo_root/docs/results/ht_pending_gain_tasks_10min_2026-10-18/videos.m3u"
elif [[ "${1:-}" == '--deferred-gain' ]]; then
  ht_playlist="$ht_repo_root/docs/results/ht_deferred_gain_tasks_10min_2026-10-19/videos.m3u"
elif [[ "${1:-}" == '--deferred-repeat' ]]; then
  ht_playlist="$ht_repo_root/docs/results/ht_deferred_gain_repeat_10min_2026-10-19/videos.m3u"
else
  ht_playlist="$ht_repo_root/docs/results/ht_recovery_search_slot_10min_2026-10-19/videos.m3u"
  printf '最新阶段33室内完整10分钟：普通恢复提前搜索；151.57米，2480立方米。\n'
  printf '末分钟仍行驶15.525米；仍有35.8秒长停车和232次搜索超时，尚未稳定。\n'
  printf '失败复测阶段32加 --deferred-repeat；阶段31加 --deferred-gain；阶段30加 --pending-gain；历史五环境加 --previous。\n'
fi
if [[ ! -f "$ht_playlist" ]] || ! rg -q '^[^#[:space:]]' "$ht_playlist"; then
  printf '未找到完整视频播放列表：%s\n' "$ht_playlist"
  exit 1
fi
exec /usr/bin/vlc --no-one-instance --avcodec-hw=none --vout=xcb_x11 -- "$ht_playlist"
