#!/usr/bin/env bash
set -euo pipefail
ht_voxel_repo="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
if (( $# )); then
  exec bash "$ht_voxel_repo/scripts/play_rviz_comparison.sh" "$@"
fi
exec bash "$ht_voxel_repo/scripts/play_rviz_comparison.sh" \
  "$ht_voxel_repo/docs/results/ht_xytheta_transparent_voxels_2026-10-22/video/rviz_detail_4x.mp4"
