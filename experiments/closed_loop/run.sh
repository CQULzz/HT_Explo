#!/usr/bin/env bash
set -eo pipefail
cd "$(dirname "$0")/../.."
source /opt/ros/jazzy/setup.bash
source ../autonomous_exploration_development_environment/install/setup.bash
source install/setup.bash
python3 experiments/closed_loop/prepare.py
export HT_DOWNWARD_LIDAR=${HT_DOWNWARD_LIDAR:-0}
python3 experiments/closed_loop/run.py "$@"
