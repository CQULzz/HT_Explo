# WSL Scout PCD r04: source-ready simulation adapter

Tested `6af4a2041c28fcd0cd3ac21796b17e03aaa29d29`, retaining r02/r03 exact mapper optimizations. The simulation-only adapter no longer delays every scan for an additional80ms after receipt. It forwards original scans when **both measured ground-truth pose and current ROS clock cover the exact integer source timestamp**. TF/odometry is published first; the real input bridge still requires exact TF and original source-time/age gates. Future scans remain queued, all scan data/stamps/physics/rate/scene/TARE/weights/safety thresholds unchanged. Seven unit regressions passed, including nanosecond precision at epoch scale and original object identity.

|120s trial|GT cumulative XY m|Sampled free volume m³|HT publication source age p50/p95 s|Zero command telemetry fraction|
|---|---:|---:|---|---:|
|r00 initial EGL baseline|0.8783|377.08|1.020 / 1.190|99.16%|
|r03 map shifts|2.7743|504.976|0.960 / 1.2185|93.72%|
|r04 source-ready adapter|4.4524|633.184|0.965 / 1.2555|85.77%|

Full120.1 simulation seconds, frozen files unchanged, verifiedEGL/llvmpipe, all managed exits0. Mission **incomplete**, persistent map-age holds remain. Movement/volume increased in this single nondeterministic closed-loop trial; publication-age P95 did not improve. This is not stable exploration acceptance or a proven isolated causal gain. First usable sampled sensor cycle was0.4s versus0.2s in r03, a startup timing consequence retained in READY.json. Distance includes gravity settling/slip; volume is sampled LiDAR ray-voxel union, not ground-truth coverage. Historical late cropped-scene blocking is outside the120s scope.

Adapter final counters:606 scans published, local queue wait p50 0.00070s/P95 0.00089s, source age at adapter publication p50 0.13s/P95 0.15s. These measure only this adapter, not total LiDAR/mapper/HT latency. Downstream delay remains substantial; do not treat near-zero adapter queue as end-to-end success. Original TF/age enforcement was retained.

All MCAP counts/available CRCs/source spans/SHA256 verified, all241/241 video frames decoded120.5s2fps. Full recorded controls/poses/status/publishedHT, source-second sampled LiDAR,10s snapshots/CSV/resources/logs/runtime, plus trajectory/volume/age and actual-speed/command comparisons. Not full-rate raw sensor/CuPy input. Video is2D actual simulated trajectory/telemetry, not Gazebo camera. Every MCAP retained; only regenerablequery_cdr and__pycache__ excluded.

Scene/model/unchangedHT installed binaries: r00 https://github.com/CQULzz/HT_Explo/releases/tag/ht-wsl120-baseline-20261105-r00 . Apply pinned private upstream stable mapper patches, publicr02/r03 installers and rebuild in the separate workspace. Runtime/sourcehash manifests identify actual bytes; private upstream core is not bundled. Concatenate each label's128MiB tar parts in numeric order to extract. Per-file inventories and remote receipt provide SHA256 checks.

Remaining: producer/source age and HT processing/queue delay, timer scheduling, ignored built-in-traversability config field and real near-car support; see earlier reports. D3D12 rejected for shutdown SIGSEGV. Original dual-boot Linux logs/data untouched; no real vehicle output.
