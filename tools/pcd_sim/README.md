# Recorded-PCD simulation runner

Use a separately restored runtime directory from the experiment Release (scene, model assets, observer, adapter and mapper wrapper). The runner is not a hardware launcher. Source the isolated runtime environment first, then pass `--runtime`, `--project`, `--mapper-workspace`, `--output-root`, a new `--label`, and an isolated `--domain`. Default requested duration is120 simulation seconds.

Each run freezes installed files, parameters and runtime scripts, records MCAP/CSV/video, and writes the real requested/recorded duration. A critical ROS launch child exit fails collection even when the ros2 launch parent remains alive. Failed startup data is retained and never reported as a completed trial. The legacy full_600_sim_s flag remains false for a valid120-second run; use full_requested_duration and verify source spans.
