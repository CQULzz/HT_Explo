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
elif [[ "${1:-}" == '--frozen-garage' ]]; then
  ht_playlist="$ht_repo_root/docs/results/ht_frozen_garage_10min_2026-10-19/videos.m3u"
  printf '阶段36：同冻结版本车库完整10分钟；187.25米，7900.375立方米。\n'
  printf '末分钟20.805米，最长全零4.95秒；仍有71次搜索超时、地图和路径过期，尚未稳定。\n'
elif [[ "${1:-}" == '--serial-mapper' ]]; then
  ht_playlist="$ht_repo_root/docs/results/ht_serial_mapper_10min_2026-10-19/videos.m3u"
  printf '阶段37：地图调度修复，车库完整10分钟；179.78米，4522.625立方米。\n'
  printf '地图/路径过期0，最长停车1.15秒；但观测体积较阶段36退步42.8%%，转向和回访增加。\n'
elif [[ "${1:-}" == '--guide-handoff' ]]; then
  ht_playlist="$ht_repo_root/docs/results/ht_guide_handoff_10min_2026-10-19/videos.m3u"
  printf '阶段38：任务交接修复，车库完整10分钟；202.58米，5807立方米。\n'
  printf '较37体积+28.4%%、回访减少，仍低于36且搜索超时增加。\n'
elif [[ "${1:-}" == '--successor-pruning' ]]; then
  ht_playlist="$ht_repo_root/docs/results/ht_successor_pruning_10min_2026-10-20/videos.m3u"
  printf '阶段39：搜索支配边剪枝，车库完整10分钟；199.69米，6483立方米。\n'
  printf '体积较38提高11.6%%，超时81到65；末分钟新增/完全停车仍有退步，尚未追平TARE。\n'
  printf '阶段38加 --guide-handoff；阶段37加 --serial-mapper；阶段36加 --frozen-garage。\n'
elif [[ "${1:-}" == '--tare-waypoint' ]]; then
  ht_playlist="$ht_repo_root/docs/results/ht_tare_waypoint_10min_2026-10-20/videos.m3u"
  printf '阶段40：原TARE多视点TSP + HT航点路由，600秒192.93米、8467.000立方米。\n'
  printf '旧阶段39加 --successor-pruning；更早版本选项保留。\n'
else
  ht_playlist="$ht_repo_root/docs/results/ht_tare_boundaries_10min_2026-10-20/videos.m3u"
  printf '阶段41：原TARE多视点TSP + HT航点路由，600秒181.31米、8660.125立方米。\n'
  printf '阶段40加 --tare-waypoint，阶段39加 --successor-pruning；更早选项保留。\n'
fi
if [[ ! -f "$ht_playlist" ]] || ! rg -q '^[^#[:space:]]' "$ht_playlist"; then
  printf '未找到完整视频播放列表：%s\n' "$ht_playlist"
  exit 1
fi
exec /usr/bin/vlc --no-one-instance --avcodec-hw=none --vout=xcb_x11 -- "$ht_playlist"
