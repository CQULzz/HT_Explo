#!/usr/bin/env bash
set -euo pipefail
task_root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
set +u
source "$task_root/scripts/real_scout_environment.sh"
set -u
cd "$task_root"
export CMAKE_BUILD_PARALLEL_LEVEL="${BUILD_JOBS:-2}"
export MAKEFLAGS="-j${BUILD_JOBS:-2}"
colcon --log-base log_real build --executor sequential \
  --base-paths src/tare_planner src/ht_scout_bridge \
  --build-base build_real --install-base install_real \
  --packages-select tare_planner ht_scout_bridge \
  --cmake-args -DCMAKE_BUILD_TYPE=Release
