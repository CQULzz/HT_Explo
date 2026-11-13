# HT execution fixes — 2026-11-13

Base: `5e5eef4f1e179b15e20e231ea39bf7bff592d7d4`. Scope: the current CMU HT-only adapter. No model, TARE objective ordering, mapper, or hardware deployment changes.

## Obstacle inflation

The old circular obstacle envelope could reject a pose next to a wall even when the configured rectangular vehicle envelope was clear. Both localPlanner and pathFollower now check raw `ht_obstacle` cells against the body rectangle at the actual yaw. Swept commands and graph edges use the same predicate. Grid-cell extent and between-sample translation/rotation have explicit conservative padding. Empty regions use an integral-image early exit.

The envelope comes from `vehicleLength`/`vehicleWidth`, both 0.6 m in the recorded CMU localPlanner profile. pathFollower now declares the same parameters and defaults. **Set both nodes to identical dimensions if changing the vehicle.** These are the existing CMU navigation envelope, not newly measured Scout URDF geometry. The rectangle must fit within `ht_validity_radius`; invalid configuration fails startup. A changed sensor/body reference requires proper frame configuration before use.

No cells are erased and arrival does not override an obstacle actually overlapping the body. HT scores, unknown-support footprint, boundary and TTL remain enforced. Consequently this fixes circular-inflation false blocking, not every possible invalid-current-pose case. Real Scout execution in the separate `ht_scout_bridge` chain is not deployed or changed here.

Command audit messages identify `oriented_box_v1`, body dimensions and support radius. The independent Python auditor supports this contract and retains legacy `circle_v1`. Historical receipts are unchanged; the old circular audit formula must not be used to certify new box-envelope commands.

## Recovery control

- Replace the slow proportional segment-end velocity tail with braking-distance bounds; retain 0.15 m/s linear and 0.5 rad/s angular recovery limits and existing acceleration bounds.
- Complete translations within 1 cm along-track / 1.5 cm cross-track / 0.04 rad heading, allowing at most 2 cm along-track overshoot. Turns complete within 0.02 rad. Actual connecting motion remains gated; poses are never snapped to the planned path.
- Stop and release recovery after two seconds without measurable segment-error improvement.
- Apply updated speed limits every cycle, including the follower's inclination slowdown. Lower positive limits use bounded deceleration; pause/zero-limit/invalid-map stops remain immediate.

The discrete recovery action graph, whole-route execution policy and per-segment stops remain. Search cost still approximates time and does not fully optimize acceleration/settling cost; further route optimization is separate work.

## Validation

`ht_execution_test` covers circular false blocking, straight/reverse wall exit, intermediate turn-corner collision, command braking sweep, real body collision, unknown support, low HT score, invalid body dimensions, fixed-route timing with acceleration/sweep checks, endpoint overshoot, lateral miss, dynamic/zero limits, no-progress exit, and public reverse search/execution. The existing `ht_gate_test` remains unchanged.

`controller_comparison.cpp` contains the extracted baseline and candidate follow functions, with identical fixed routes, 20 ms control and 5 ms yaw-first integration. Routes approximate the two recorded recovery shapes; this is **not raw-bag replay**. Results:

| Route | Baseline | Fixed | Reduction |
|---|---:|---:|---:|
| Turn then forward | 7.80 s | 6.14 s | 21.3% |
| Turn, short reverse, turn, forward | 11.92 s | 8.52 s | 28.5% |

`test_audit.py`: six independent Python footprint/legacy/TTL checks. Final build and verbose CTest results are adjacent to this file. The older hard-coded `ht_recovery_test` recorded-map fixture is absent on this host, so it was compiled but not executed. No new Gazebo/600-second experiment or real-vehicle run occurred; prior experiment budgets remain closed. This candidate has offline verification, not hardware acceptance.

Reproduce (ROS 2 Jazzy, OpenCV and package dependencies installed):

```bash
source /opt/ros/jazzy/setup.bash
cmake -S src/cmu_local_planner_ht -B build_execution
cmake --build build_execution -j2
ROS_DOMAIN_ID=214 ROS_LOCALHOST_ONLY=1 ctest --test-dir build_execution -V
python3 validation/execution_20261113/test_audit.py
g++ -std=c++17 validation/execution_20261113/controller_comparison.cpp -o /tmp/controller_comparison
/tmp/controller_comparison
```

The earlier mapper observation-variance lifecycle finding and exploration-efficiency diagnosis are outside this patch.
