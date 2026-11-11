# HT-only local traversability experiment

The tested candidate removes CMU local point-cloud collision voting, rotation veto and terrain penalties. Native TARE exploration remains upstream. The full HT gate (eight scores, occupied/support/context masks, TTL and braking sweep) remains active. This is **not a score-only neural controller** or a geometry-free TARE implementation.

Results: [Chinese report](../../docs/results/ht_only_local_20261111/REPORT.md). Both 600-second runs blocked eventually; the candidate is experimental, not accepted as a replacement navigation stack.

## Version and local workspace

- User-map runtime: `f93535ab6277fb008c2456bb962fc86f9e7dc229`.
- Indoor runtime: `8248a95` (only dependency/parameter-capture infrastructure differs).
- Native TARE: `b6760adb4280b379567c76f4e684ce628e28ef71`, previously documented Frontier parameter declaration patch only.
- Official CMU: `158e67b31b644ed1e8b06eb1d7f70e183cc62591`.
- Local evidence/dependencies: `/home/lzz/ht_only_20261111`. Exact original source/parameters/binaries are retained in each run's `frozen_runtime.tar.gz` and `FREEZE.json`.
- Source meshes: verified recovery from the user's earlier release; see the prior user-PCD report. Installed mapper, sensor and native TARE prefixes are read-only links to the preceding experiments.

`env.local.bash` records the required local ROS/dependency prefixes. `config/` contains the actual two local-planner launch configurations. These scripts describe this workspace, not a self-contained installer for another machine.

## Rebuild / offline checks

```bash
source /home/lzz/ht_only_20261111/env.sh
colcon --log-base /home/lzz/ht_only_20261111/build_logs build \
  --base-paths /home/lzz/HT_Explo_ht_only_20261111/src/cmu_local_planner_ht \
  --build-base /home/lzz/ht_only_20261111/build_gate \
  --install-base /home/lzz/ht_only_20261111/install_gate \
  --cmake-args -DCMAKE_BUILD_TYPE=Release
/home/lzz/ht_only_20261111/build_gate/cmu_local_planner_ht/ht_gate_test
```

`replay.py` is the original static-input replay, including planner and follower, with no vehicle/actuator. It refuses to overwrite its output directory. Additional read-only analyses in `analysis/` preserve source-stamped snapshots, diagnose quality rejections, audit recorded outputs, query chassis/mesh contacts, run separately labelled archived-Scout probes and render recorded trajectories. Several analyses require the retained prior experiment assets; filenames and source hashes in the report make that dependency explicit.

`audit_commands.py` in `tools/cmu_minimal` independently checks accepted command candidates against the exact recorded HT maps. `analysis/match_published_commands.py` additionally associates recorded nonzero outputs. Its strict 100ms receipt matching leaves one user-map output unmatched; the targeted raw window finds its unique same-velocity allowed candidate 328ms earlier. Those limitations and delayed odometry headers are retained in the report rather than erased.

## Simulation runner / closed budget

`run.py --name NAME --scene user_pcd|indoor --duration 600` preflights mapper/CUDA imports, consumes one formal startup slot, freezes inputs, records MCAP and metrics, and retains failures. Dedicated Xvfb `:88` is an external local prerequisite. `simulation.launch.py` runs only the virtual CMU vehicle.

**The current ledger is closed at 3/3 attempts. Do not reset it or automatically start a fourth run.** A future explicitly authorized batch needs its own ledger/output directory. The `PLAN.md` contains the original candidate/recovery design; recovery has only static feasibility evidence, no implemented or closed-loop-tested second candidate.

Final navigation code has no changes after the last tested version. Later commits add only reports, provenance, launch-config copies and analysis utilities. Original main/real/history refs are unchanged. Full new MCAP/video remains local with SHA256 receipts; no Release, hardware deployment or raw-data pruning was performed.
