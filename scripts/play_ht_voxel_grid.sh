#!/usr/bin/env bash
set -euo pipefail
ht_grid_repo="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
if (( $# )); then
  exec bash "$ht_grid_repo/scripts/play_rviz_comparison.sh" "$@"
fi
exec bash "$ht_grid_repo/scripts/play_rviz_comparison.sh" \
  "$ht_grid_repo/docs/results/ht_xytheta_voxel_grid_2026-10-22/video/xytheta_voxel_grid_4x.mp4"
