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


The r03 candidate uses `install_map_shift_integers.py --workspace WS` after the stable mapper patches (ray initialization may also be installed). It reads the original GPU-computed int32 XY shift to the host once. The existing roll, pad, age and semantic-map operations reuse those same integers; coordinate rounding and vertical arithmetic stay on the original path. Preserve upstream CRLF: the patch is byte-hash verified and must not be newline-normalized. Thirty CUDA regression moves compare full byte state, including zero moves, half-cell boundaries, negative/diagonal shifts, vertical changes and shifts beyond the map width. The original private core is kept locally for the test, not redistributed; authorized users reproduce it from the pinned private upstream plus public stable patch. Rebuild the independent mapper before a frozen trial.


The r04 simulation adapter forwards a queued scan once ground-truth pose and current ROS clock both cover its original source stamp. It publishes TF/odometry first and no longer adds a fixed80ms wall wait. The real input bridge still requires exact timestamped transforms, checks source age/clock discontinuities and publishes filtered/registered pairs atomically. Future scans remain queued; timestamps, scan data, rate and physics are unchanged. Queue statistics are emitted at shutdown, separate from downstream latency. The20ms retry timer remains as a fallback.


The r06 scheduling candidate is explicitly opt-in with `--ht-processing-mode worker`. Gazebo/navigation-only environment selection declares the attested ROS parameter `ht_processing_mode=worker`; the ordinary hardware/default mode remains `executor`. A SingleThreadedExecutor handles reception/clock/odometry while one condition-driven owner calls the unchanged `on_map` inference body. LatestInput still keeps one monotonic pending source frame. Shutdown clears pending work and joins the in-flight callback before diagnostics/history destruction; worker exceptions propagate to the process and are caught by the existing runner's child-exit detection. The executor mode remains available for matched A/B trials. No GIL switch interval, affinity, safety age or mathematical gates change.
