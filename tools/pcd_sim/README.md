# Recorded-PCD simulation runner

Use a separately restored runtime directory from the experiment Release (scene, model assets, observer, adapter and mapper wrapper). The runner is not a hardware launcher. Source the isolated runtime environment first, then pass `--runtime`, `--project`, `--mapper-workspace`, `--output-root`, a new `--label`, and an isolated `--domain`. Default requested duration is120 simulation seconds.

Each run freezes installed files, parameters and runtime scripts, records MCAP/CSV/video, and writes the real requested/recorded duration. A critical ROS launch child exit fails collection even when the ros2 launch parent remains alive. Failed startup data is retained and never reported as a completed trial. The legacy full_600_sim_s flag remains false for a valid120-second run; use full_requested_duration and verify source spans.


`--render-backend egl` retains the headless EGL baseline. On the tested NVIDIA WSLg host, `--render-backend wsl-d3d12` explicitly selects Mesa D3D12, the NVIDIA adapter and the WSL D3D12 libraries for Gazebo only, and omits headless EGL. The renderer log is isolated under the run's Gazebo HOME, copied into `ogre2.log`, checked during collection, and attested in RUN_RESULT.json. A fallback or absent renderer log fails verification. Sensors, scene, physics, model and navigation thresholds are unchanged. The mapper writes read-only timing counters into mapper_stats.json.

A complete recording and clean shutdown are separate facts. Nonzero managed shutdown codes remain in RUN_RESULT.json and cause the harness to exit nonzero even after a complete duration; do not claim a crash-free candidate from complete collection alone. A render-only check on this host returned SIGSEGV during D3D12 SIGINT cleanup despite working LiDAR/clock, so this backend is experimental until the full run is evaluated.


The r02 candidate installs `tools/elevation_mapping_fixes/ray_initialization.patch` only in the independent mapper workspace:

```bash
python3 tools/pcd_sim/install_ray_initialization.py --workspace /path/to/cupy_ws
# Rebuild elevation_mapping_cupy in its existing build_stable/install_stable workspace.
```

The installer checks the authentic upstream commit object, before/after source SHA256, managed path and patch context; unknown local changes are rejected, and repeated installation is a no-op. Preserve the original module as `setup/pre-r02-deterministic_fusion.py` in the experiment root for `test_ray_initialization_gpu.py --root ROOT`. The 12-case CUDA regression compares every byte of all emitted event buffers, maps, statistics and point metadata, including empty input, launch-block boundaries, missing terrain, age boundaries, invalid returns and active/inactive drift. Warm paired service timings are offline evidence, not vehicle throughput. Only buffer initialization moves to coalesced fills on the same CUDA stream; event slot order and all ray decisions remain unchanged.
