# WSL Scout PCD r01: D3D12 candidate rejected

Tested `fe464fd10935da1e986ef25e79f02bdecf163453`. Full 120.3 simulation seconds, frozen files unchanged. Renderer log attests D3D12 (NVIDIA GeForce RTX 5060 Ti). Commands stayed isolated to /sim/cmd_vel. The only execution candidate is explicit GPU rendering selection; scene, sensor rate/resolution, physics, learned weights, TARE ordering and strict safety gates were unchanged. Added read-only mapper statistics and isolated render logs.

|120s trial|Cumulative GT XY m|Sampled free volume m³|HT source age p50/p95 s|Zero command telemetry fraction|
|---|---:|---:|---|---:|
|r00 EGL/llvmpipe|0.8783|377.08|1.020 / 1.190|99.16%|
|r01 WSLg/D3D12|0.7358|373.36|0.980 / 1.168|98.33%|

Both missions remain incomplete and mostly stationary. Distance includes initial gravity settling/slip; free volume is source-second sampled LiDAR ray-voxel union, not ground-truth coverage. The small latency difference and worse travel do not establish a useful navigation improvement. TARE sampling and closed-loop paths are nondeterministic; one trial per backend is not a causal proof. Old 233s scene-edge blocking is outside this 120s window.

**Rejected as a stable default**: Gazebo stayed alive through collection but SIGINT cleanup returned SIGSEGV (-11). The harness exits nonzero, preserving full_requested_duration=true and the separate shutdown code; this is complete data with failed clean shutdown, not a crash-free successful run. EGL remains default.

New mapper timing evidence: 482 processed scans, mean 0.2373 s including decoding/TF/map-lock wait/fusion; source queue age median 0.48 s, P95 0.59 s. Publish callbacks mean 0.228 s and variance callbacks mean 0.237 s also include lock waiting and cannot be added as disjoint CPU time. Only 23 pose and 13 time callbacks ran; low-rate statistics callback never ran during collection, final statistics were written after executor shutdown. This supports further investigation of map-lock contention/scheduling, not a proven individual kernel cause. HT callback p50 0.1663 s. No stamps or age thresholds were relaxed.

All MCAP messages and available CRCs were checked; complete 241/241 frame video decoded (120.5s,2fps, actual 2D trajectory/telemetry, not a Gazebo camera). See BAG_VERIFICATION.json for per-file counts/source spans/SHA256. Full raw run and runtime archives included, with per-file inventories and part hashes. Excluded only regenerable query_cdr and __pycache__; preserved all MCAP and failures. Source-second sampled LiDAR is not full-rate raw sensor/CuPy recording.

Reproduction assets and identical HT installed binaries are in r00: https://github.com/CQULzz/HT_Explo/releases/tag/ht-wsl120-baseline-20261105-r00 . This run's manifest freezes actual binaries/config/weights. External private mapper core remains separate and is not redistributed; pinned authenticated upstream and patch installer are documented in r00. Concatenate each label's multipart tar pieces in numeric order to extract.
