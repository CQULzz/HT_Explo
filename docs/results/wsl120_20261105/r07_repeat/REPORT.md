# WSL Scout PCD r07: unchanged worker-mode repeat

Same tested commit `8e06489fe3fabed32cda97239ca7c713e50586cf`, same installed bytes/config/weights, `--ht-processing-mode worker`, EGL/llvmpipe. Independent120.3s trial, no profiling, unchanged frozen files, every managed exit0. Both r02/r03 equivalent mapper optimizations and source-ready adapter retained. No model math, source timestamps, probability/unknown/age/geometry gates or TARE ordering changed. Hardware/default mode remains legacy executor; this is an explicit WSL simulation option.

|Trial|HT callback p50/P95 ms|Publication source age p50/P95 s|GT cumulativeXY m|Sampled free m³|
|---|---|---|---:|---:|
|r04 executor reference|215.1 /321.1|0.965 /1.2555|4.4524|633.184|
|r06 worker|64.0 /78.5|0.580 /0.807|5.6161|527.192|
|r07 same worker repeat|64.0 /77.1|0.550 /0.748|6.7256|540.36|

This repeats the latency improvement on two unprofiled120s trials. During r07's pre-completion phase, callback p50/P95 64.9/76.4ms, publication source age0.500/0.724s. First internal completed telemetry29.8s; before completion28.07% of~2Hz telemetry samples had zero commands. Whole-run82.85% zero includes intentional post-return parking, not82.85% blocked navigation. The output recorder continued to120.3s despite early internal completion. Mission state is internalCOMPLETED in both r06/r07.

**Do not equate internal completion with full-scene coverage.** Native TARE completion audit's last transition has uncovered/frontier76/21 inr06 and4/9 inr07, respectively, with global_return=1/local_complete=1. These are threshold/reachability counters, not a proved completion bug or independent coverage certificate. The early-return/coverage criterion needs separate validation while preserving original TARE target ordering. Sampled free volume remains lower thanr04, paths are nondeterministic, and the120s trials do not assess the old233s cropped-scene-edge failure or real hardware. Distance includes initial physics settling/slip; free volume is source-second sampled LiDAR ray-voxel union, not scene-truth coverage.

All recorded MCAP counts/availableCRCs/source spans/SHA256 checked, all241/241 video frames decoded120.5s2fps. Full raw run/runtime/phase metrics/completion audit/comparison and speed/command plots retained. All controls/poses/status/publishedHT, source-second sampledLiDAR,10s snapshots,CSV/resources/logs/video; not full-rate raw LiDAR/CuPy. Actual2D trajectory/telemetry video, not Gazebo camera. EveryMCAP included; excluded only regenerablequery_cdr/__pycache__. Source tag is exact tested code, never a later documentation commit.

Current HT installed bundle and9 scheduling/ROS regression evidence: https://github.com/CQULzz/HT_Explo/releases/tag/ht-wsl120-worker-20261105-r06 . Originalscene/model assets: r00. Private mapper core stays separate, pinned upstream+public stable/r02/r03 patches; no private core bundled. Concatenate numeric128MiB tar parts bylabel, extract and verify inventories/receiptSHA256. All earlier failed starts/failed D3D12 cleanup remain in earlier immutable Releases. Original dual-boot Linux logs/data remain unchanged. Updated repository handoff/index records execution paths, two-minute policy and remaining coverage validation.
