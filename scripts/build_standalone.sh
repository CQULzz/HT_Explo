#!/usr/bin/env bash
set -euo pipefail

workspace="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
set +u
source /opt/ros/jazzy/setup.bash
set -u

# Ubuntu's JSON headers are needed to compile the vendored Fixposition SDK.
# Keep a local copy when the system development package is unavailable.
if [[ ! -f /usr/share/cmake/nlohmann_json/nlohmann_jsonConfig.cmake ]]; then
  dependency_root="$workspace/.local_deps/root"
  if [[ ! -f "$dependency_root/usr/share/cmake/nlohmann_json/nlohmann_jsonConfig.cmake" ]]; then
    mkdir -p "$workspace/.local_deps/pkg" "$dependency_root"
    (cd "$workspace/.local_deps/pkg" && apt download nlohmann-json3-dev)
    dpkg-deb -x "$workspace"/.local_deps/pkg/nlohmann-json3-dev_*.deb "$dependency_root"
  fi
  export CMAKE_PREFIX_PATH="$dependency_root/usr:${CMAKE_PREFIX_PATH:-}"
  export CPATH="$dependency_root/usr/include:${CPATH:-}"
fi

cd "$workspace"
colcon --log-base log_standalone build \
  --build-base build_standalone \
  --install-base install_standalone \
  --packages-up-to tare_planner fixposition_driver_ros2 rslidar_sdk \
  --cmake-args -DCMAKE_BUILD_TYPE=Release
