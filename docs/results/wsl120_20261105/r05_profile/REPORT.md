# WSL Scout PCD r05: unchanged-source diagnostic repeat

Tested code is still `6af4a2041c28fcd0cd3ac21796b17e03aaa29d29` (r04), both mapper optimizations and source-ready adapter unchanged. Full120.3s, frozen files unchanged, EGL/llvmpipe and all managed exits0. Mission incomplete; 3.4754m cumulativeGTXY /571.976m³ sampled ray-voxel union. Includes initial settling/slip. Closed-loop paths are nondeterministic and differ from r04; this repeat also includes profiling overhead and is not an unprofiled performance comparison. No safety/time/geometry/model/TARE changes.

Read-only py-spy0.4.3, two verified owned descendant processes, nonblocking50Hz GIL sampling for45wall seconds starting at20.3simulation seconds. No Python locals collected. Raw stack traces, sampler logs, target/scope metadata and GIL_PROFILE_SUMMARY.json are included with the complete run. HT main executor thread accounted for1068/1353 GIL-holding samples (~78.9%); only473/1353 (~35.0%) had a leaf directly in executors.py, with more in rclpy event-handler/context/callback-group bookkeeping. Mapper main accounted for970/1397 (~69.4%). These are sampled GIL occupancies, not CPU percentages or a proven end-to-end causal gain. They motivate a controlled event-driven worker candidate, not a claim that all delay comes from dispatch.

Complete raw MCAP message counts/availableCRCs/source spans/SHA256 verified; all241/241 trajectory-video frames decoded120.5s2fps. Raw controls/poses/status/publishedHT/source-second sampledLiDAR/10s snapshots/CSV/resources/logs/video/profiles, full runtime and comparison included. Not full-rate raw LiDAR/CuPy input. Video is actual2D trajectory/telemetry, not Gazebo camera. Only regenerablequery_cdr and__pycache__ omitted; everyMCAP retained. All earlier failures remain published. Scene/model/unchangedHT binaries pinned inr00; current tested source and r02/r03 external patches reconstruct the independent mapper. No private upstream core bundled. Concatenate each label's128MiB tar parts numerically to extract.

Measured summary:
```json
{
  "map_source_age_at_publish_s": {
    "p50": 1.039999999999992,
    "p95": 1.284000000000006,
    "max": 1.4099999999999966
  },
  "ht_callback_service_s": {
    "p50": 0.21563492900000014,
    "p95": 0.31920710380000794,
    "max": 0.34007366800000227
  },
  "sampled_zero_command_fraction": 0.899581589958159
}
```
