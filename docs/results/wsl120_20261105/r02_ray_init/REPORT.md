# WSL Scout PCD r02: coalesced visibility event initialization

Tested commit `aa89e9cb693e7a54e98a62de0fd3467cc819afb2`; external mapper module before df7e7e71460a836f8f0361442058586f1fc6e4e87087754013e776d8531bd0bb, after 4e133c7e00332d2860f2d1e5205cf18964caecc8f29307da5ed7f6287c1d6da5. Explicit hash-verified patch/installer are in the tested commit; mapper stays in its independent workspace.

The ray event buffers formerly received the same defaults in a strided per-point GPU loop. Four coalesced array fills now initialize the identical memory on the same CUDA stream. Event slot ordering, ray emission/visibility, sorting/reduction, source age, probabilities, footprints, scene, sensors and TARE decisions are unchanged. No geometry or safety threshold was loosened. EGL/llvmpipe remains the backend, matching r00; the crashing D3D12 backend is not used.

12 CUDA fixtures compared **every byte** of all event buffers, maps, new maps, metadata and statistics: all equal, including empty scans, block boundaries, missing terrain, age boundaries, invalid returns and active/inactive drift. Paired warmed synthetic fusion p50 improved 201.0→126.7 ms (37.0%); this is offline service timing and not a vehicle throughput claim. The independent mapper rebuilt successfully. Baseline module for reproducibility is part of the validation archive; this entire module was originally introduced by the already-public deterministic_fusion.patch, not unrelated private upstream code.

|Full 120s trial|GT cumulative XY m|Sampled free volume m³|HT publication source age p50/p95 s|Zero command telemetry fraction|
|---|---:|---:|---|---:|
|r00 EGL baseline|0.8783|377.08|1.020 / 1.190|99.16%|
|r02 coalesced initialization|0.9928|438.832|0.970 / 1.180|92.05%|

The full trial ran 120.3 simulation seconds, unchanged frozen files, verified llvmpipe, all managed exit codes zero. Both missions remain **incomplete**, mostly stopped; near-vehicle missing support and map freshness holds remain. The optimization improves the measured kernel and this single trial's command activity/volume, but is insufficient to restore sustained exploration. GT distance includes gravity settling/slip; sampled ray-voxel volume is not ground-truth scene coverage. Nondeterministic closed-loop paths and one trial per version limit causal interpretation of aggregate metrics. Short trials do not assess the original scene-edge fault after ~233s.

All recorded MCAP messages, available CRCs, source spans and SHA256 checked (BAG_VERIFICATION.json); video all 241/241 frames decoded (120.5 s at2fps). Actual 2D trajectory/telemetry video, not a Gazebo camera. Full recorded run, runtime and validation archives retained, with all MCAP; excluded only regenerable query_cdr and __pycache__. Recording includes controls, poses, status, published HT, source-second sampled LiDAR and 10s map snapshots, not full-rate raw sensor/CuPy input.

Reproduction scene/model assets and unchanged HT installed binaries: https://github.com/CQULzz/HT_Explo/releases/tag/ht-wsl120-baseline-20261105-r00 . Use that pinned upstream + stable patches, then apply install_ray_initialization.py and rebuild. Runtime manifest freezes actual installed module bytes. Concatenate each archive label's numeric parts, then extract; inventories and receipt provide SHA256 verification.

Migration limitation discovered during profiling: mapper_core.yaml requests enable_builtin_traversability=false, but the reconstructed pinned core has no such parameter field, so the wrapper silently ignores it and the built-in CNN still runs. It costs ~2 ms in the isolated profile, not the measured dominant ~81 ms ray emitter. r02 preserves that baseline behavior instead of silently changing a second mechanism. This flag/config mismatch remains to be addressed explicitly. Other source artifacts from dual-boot Linux remain unchanged; no real vehicle output.
