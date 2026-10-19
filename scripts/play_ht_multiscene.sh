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
elif [[ "${1:-}" == '--recovery-slot' ]]; then
  ht_playlist="$ht_repo_root/docs/results/ht_recovery_search_slot_10min_2026-10-19/videos.m3u"
elif [[ "${1:-}" == '--checked-connections' ]]; then
  ht_playlist="$ht_repo_root/docs/results/ht_checked_connections_10min_2026-10-19/videos.m3u"
  printf '阶段34完整视频，但退出时一份诊断NPZ损坏，原失败记录保留。\n'
elif [[ "${1:-}" == '--atomic-context' ]]; then
  ht_playlist="$ht_repo_root/docs/results/ht_atomic_context_10min_2026-10-19/videos.m3u"
  printf '阶段35室内完整10分钟：退出诊断修复；169.10米，2674.75立方米。\n'
  printf '末分钟17.364米，最长全零4.2秒；仍有51次搜索超时和13条地图过期状态，尚未稳定。\n'
else
  ht_playlist="$ht_repo_root/docs/results/ht_frozen_garage_10min_2026-10-19/videos.m3u"
  printf '最新阶段36：同冻结版本车库完整10分钟；187.25米，7900.375立方米。\n'
  printf '末分钟20.805米，最长全零4.95秒；仍有71次搜索超时、地图和路径过期，尚未稳定。\n'
  printf '室内阶段35加 --atomic-context，阶段34加 --checked-connections，阶段33加 --recovery-slot；历史五环境加 --previous。\n'
fi
if [[ ! -f "$ht_playlist" ]] || ! rg -q '^[^#[:space:]]' "$ht_playlist"; then
  printf '未找到完整视频播放列表：%s\n' "$ht_playlist"
  exit 1
fi
exec /usr/bin/vlc --no-one-instance --avcodec-hw=none --vout=xcb_x11 -- "$ht_playlist"
