#!/usr/bin/env bash
# Reusable local verification; no model/API calls. Output directory must be new.
set -eo pipefail
cd "$(dirname "$0")/../.."
output=${1:?Usage: verify_remediation.sh OUTPUT_DIRECTORY [DURATION=90] [PAIRS=2]}
duration=${2:-90}
pairs=${3:-2}
source /opt/ros/jazzy/setup.bash
source ../autonomous_exploration_development_environment/install/setup.bash
MAKEFLAGS=-j3 colcon build --packages-select tare_planner --symlink-install --cmake-args -DCMAKE_BUILD_TYPE=Release
source install/setup.bash
ROS_DOMAIN_ID=72 colcon test --packages-select tare_planner
colcon test-result --verbose
HT_DOWNWARD_LIDAR=0 bash experiments/closed_loop/run.sh --duration "$duration" --pairs "$pairs" --output "$output"
python3 experiments/closed_loop/analyze.py "$output"
