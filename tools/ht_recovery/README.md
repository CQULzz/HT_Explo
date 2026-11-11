# HT local pose recovery and explicit motion execution

This experiment implements problem two only. Source elevation variance (m²) is not HT score variance. No probability-standard-deviation inference or mean-minus-std criterion was introduced. Original HT probability/masks/TTL and native TARE exploration remain unchanged.

The candidate adds bounded `(x,y,yaw)` pose search, forward/reverse/in-place-turn actions, collinear segment merging, and an executor that retains body-yaw and travel-sign semantics. Before use, a candidate is rolled out with that same feedback controller and checked with the same HT reaction/braking gate. Execution checks the latest pose/map again for every command. Normal CMU tracking resumes after the local prefix completes. Recovery begins only after 0.4s of zero/rejected normal outputs, not during normal motion.

Files:

- `src/cmu_local_planner_ht/src/ht_recovery.hpp`: search, explicit segment executor, target-update compatibility and diagnostics.
- `pathFollower.cpp`: recovery owns commands while active; normal tracking is not allowed to reinterpret its XY trace.
- `ht_gate.hpp`: only adds an option to suppress simulated-rollout audit messages; real command checks remain audited.
- `ht_recovery_test.cpp`: original blocked command, continuous recovery, retained/updated waypoint semantics, stale odometry/map, reverse body-yaw semantics, incompatible goal cancellation, unknown/occupied start rejection. Reverse execution includes timing jitter.

[Chinese report](../../docs/results/ht_local_recovery_20261111/REPORT.md).

## Tested versions and results

- First formal 300s run: `31ce321`, 147.279m, exposed an incorrect new 3-second waypoint timeout and missing exit diagnostic. Full data retained; not treated as successful completed recovery.
- Corrected formal 300s run: `5d91b4b`, 124.302m, completed one online recovery (11.180s, 0.784m net displacement, 0.763m progress toward its fixed initial target). Six compatible TARE goal updates preserved the prefix.
- The corrected run later stopped on `HT_OCCUPIED` at its current footprint and did not complete exploration. Recovery refuses an invalid origin. Nearby source/scene evidence does not establish that this is a false obstacle. Do not market this as solved continuous exploration or hardware-safe navigation.
- 24 existing gate/boundary checks plus 9 recovery checks pass; independent fixed-map controller verification passes. All 13,105 recorded nonzero outputs in the final run associate with independently checked accepted gate candidates.

Defaults in this experimental launch: speed .15m/s, angular speed .5rad/s, acceleration limits 2.5m/s² and 3rad/s², progress target .75m, search radius 3m and budget 20ms, odometry timeout .2s. HT threshold .5, map TTL 1s and .45m validity radius plus existing grid margin are unchanged. These are simulation settings, not calibrated real-vehicle actuation limits.

TARE waypoints remain valid until replaced/finished, not until an invented publication deadline. Compatible shifted waypoints retain an executing prefix only when its endpoint still advances toward the new goal. Incompatible/nearby replacement goals cancel and stop it. Recovery completion is local, separate from `/exploration_finish`.

## Rebuild and retained fixtures

Local data/dependencies: `/home/lzz/ht_recovery_20261111`. Source the directory's `env.sh` (ROS, CMU, mapper, native TARE and isolated install_gate). Exact sources, configs and binaries are retained in each run's `frozen_runtime.tar.gz` and `FREEZE.json`.

```bash
source /home/lzz/ht_recovery_20261111/env.sh
colcon --log-base /home/lzz/ht_recovery_20261111/build_logs build \
  --base-paths /home/lzz/HT_Explo_recovery_20261111/src/cmu_local_planner_ht \
  --build-base /home/lzz/ht_recovery_20261111/build_gate \
  --install-base /home/lzz/ht_recovery_20261111/install_gate \
  --cmake-args -DCMAKE_BUILD_TYPE=Release
/home/lzz/ht_recovery_20261111/build_gate/cmu_local_planner_ht/ht_gate_test
/home/lzz/ht_recovery_20261111/build_gate/cmu_local_planner_ht/ht_recovery_test
python3 /home/lzz/HT_Explo_recovery_20261111/tools/ht_recovery/audit_fixture.py
```

The C++ blocked-pose fixture uses the unchanged saved original HT map with its query clock fixed at the snapshot's valid time. It integrates feedback motion with CMU's 200Hz yaw-first model; it is not a stream of fresh observations, contact dynamics or a real-vehicle test. The formal simulation uses live sensor maps and ordinary timestamps. Videos distinguish the two.

`run.py --name NAME --scene indoor --duration 300` is the recorded runner, not an invitation to restart: **this batch's 2/2 ledger is closed; do not reset it or auto-start a third trial.** The extra slot initially reserved for infrastructure was used for necessary navigation retest after the actual waypoint-semantics failure, documented in AGENTS and the ledger. A later authorized batch needs its own outputs/ledger.

Full new MCAP and videos remain local with SHA256 receipts. Code/configs/compact evidence are pushed on the new branch; no Release, hardware deployment or raw-data pruning. Analyses are read-only, with retained paths explicit. `progress_m` measures distance from the last recovery origin; count an episode's movement only between its own EXECUTING start and first COMPLETED event, not during later normal driving.
