# Recorded-PCD simulation runner

Use a separately restored runtime directory from the experiment Release (scene, model assets, observer, adapter and mapper wrapper). The runner is not a hardware launcher. Source the isolated runtime environment first, then pass `--runtime`, `--project`, `--mapper-workspace`, `--output-root`, a new `--label`, and an isolated `--domain`. Default requested duration is120 simulation seconds.

Each run freezes installed files, parameters and runtime scripts, records MCAP/CSV/video, and writes the real requested/recorded duration. A critical ROS launch child exit fails collection even when the ros2 launch parent remains alive. Failed startup data is retained and never reported as a completed trial. The legacy full_600_sim_s flag remains false for a valid120-second run; use full_requested_duration and verify source spans.


`--render-backend egl` retains the headless EGL baseline. On the tested NVIDIA WSLg host, `--render-backend wsl-d3d12` explicitly selects Mesa D3D12, the NVIDIA adapter and the WSL D3D12 libraries for Gazebo only, and omits headless EGL. The renderer log is isolated under the run's Gazebo HOME, copied into `ogre2.log`, checked during collection, and attested in RUN_RESULT.json. A fallback or absent renderer log fails verification. Sensors, scene, physics, model and navigation thresholds are unchanged. The mapper writes read-only timing counters into mapper_stats.json.

A complete recording and clean shutdown are separate facts. Nonzero managed shutdown codes remain in RUN_RESULT.json and cause the harness to exit nonzero even after a complete duration; do not claim a crash-free candidate from complete collection alone. A render-only check on this host returned SIGSEGV during D3D12 SIGINT cleanup despite working LiDAR/clock, so this backend is experimental until the full run is evaluated.
