#!/usr/bin/env bash
set -euo pipefail
task_root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
set +u
source /opt/ros/jazzy/setup.bash
set -u
cd "$task_root"
export CMAKE_BUILD_PARALLEL_LEVEL=2
export MAKEFLAGS=-j2
colcon --log-base log_standalone build --executor sequential \
  --build-base build_standalone --install-base install_standalone \
  --packages-select tare_planner --cmake-args -DCMAKE_BUILD_TYPE=Release
