# WSL Scout PCD baseline r00 (120 s)

Tested code: `354b79d164c1e5d42603603fae64dbb65a533a42`; execution: WSL Ubuntu 24.04 / ROS2 Jazzy / CUDA RTX 5060 Ti. Original dual-boot Linux evidence and source remain unchanged.

The valid trial `baseline120_b` completed 120.3 simulation seconds with unchanged frozen files. Ground-truth cumulative XY distance 0.8783 m, sampled observed free volume 377.08 m³; exploration **incomplete**, mostly stopped. Distance includes initial physics settling/slip. ~99.16% of ~2 Hz telemetry samples had zero commands. HT source age at publication p50 1.02 s / p95 1.19 s exceeds the unchanged 1 s gate. Current-pose support rejections also remain. These are diagnostic results, not successful navigation acceptance.

Gazebo used llvmpipe software rendering (Ogre log included). A separate render-only D3D12 environment check received LiDAR and clock and stayed alive until explicit shutdown; SIGINT cleanup returned -11. This is a candidate lead, not a completed navigation trial.

`baseline120_a` is a failed startup capture (missing threadpoolctl dependency); it is retained separately and does not count as a 120 s trial. The dependency and child-exit detection were corrected before the valid baseline. Eight C++ test groups passed across initial run + geometry-fixture retry; the initial missing-fixture failure and retry are both included. No new Python suite result is claimed.

Bag verification checked all 34,994 messages and available MCAP CRCs; raw MCAP SHA256 d2530f9f11936ddd8982a634fe44c7e9bcb81827d082d7901a010ef0a78ad338. Video fully decoded 241/241 frames, 120.5 s, 2 fps. Video is actual simulated 2D trajectory/telemetry, not a Gazebo camera.

Recording scope: all recorded controls, ground-truth/odometry, status, published HT maps; LiDAR sampled per source second; 10 s snapshots, logs, CSV, resource samples, frozen file hashes, video. This is **not full-rate raw LiDAR / CuPy input**. Regenerable query_cdr and __pycache__ are omitted and declared in inventories. Complete partial MCAP from the failed start is included.

Multipart archives are uncompressed tar streams split at 512 MiB: concatenate each label's parts in numeric order then extract. Per-file inventories, whole-tar and part SHA256s, EVIDENCE_MANIFEST and PUBLICATION_RECEIPT document verification. Private external mapper core is not redistributed: authenticated upstream Unmanned-Systems-Lab/elevation_mapping_cupy_2204 at 88f4c0c2eb3542faeb7bd8fa9df2f18bd25eed91 plus the public repo's verified install_elevation_fixes.py patches; workspace stays separate. CUDA/ROS packages are installed independently, not bundled. Historic scene/model assets already published in the previous release are included for reproducibility.

No safety/unknown/freshness thresholds, source stamps, learned weights, footprint or TARE target ordering changed. The older 600 s scene-edge failure cannot be assessed by this 120 s start-location trial. No real vehicle was controlled.
