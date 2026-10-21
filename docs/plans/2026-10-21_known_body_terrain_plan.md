# 阶段45：已知障碍足迹与TARE地形接口统一（先计划，再实施）

User authorized fixing remaining issues. Do not end with only this plan. First
finish stage44 publication, then implement and run at least600s indoor before
claiming a new fix. Each behavioral candidate is published before the next.
No subagents (current developer rule).

## stage44 facts
Measured454efa230fae337cfa8f87b2aa87ee9917040621, results7871a36; four600s all13
collection checks + all32 additional audits passed. Raw9.4GiB publication verified at receipt stage44.json (commit a8a6334). Previous upload used
ht-sparse-height-publish.service, runtime.git/indoor-input-runtime. Wait until
stage44.json remote size/SHA proof AND publisher exits successfully; preserve
already-uploaded parts and source. No navigation hot changes made during tests.
Garage224.11m/9809.375m3 EXPLORING, indoor62.883m/1849.25 BLOCKED,
forest46.32m/8377.875 BLOCKED, tunnel25.616m/448.875 COMPLETED (finished53s,
not full-coverage proof). Report docs/results/ht_sparse_height_4scene_10min_2026-10-21.

## proven new counterexample
Same indoor snapshot frame0060 @593.959s, actual selected branch endpoints1/2/3/4m:
(23.85,-2.35),(23.85,-3.35),(23.85,-4.35),(23.92071,-5.32071).
Center maxP=.99859/.99744/.99503/.97778 and current0.2m coarse cells admissible;
C++ poseSupport all8 headings BLOCKED. See frozen_coarse_footprint_counterexample.json
and terrain_gate_mismatch.png in above report. This is not full terrain-cache
history reconstruction or proof any complete path exists. Forest differs:
754 searches hit8000 expansion cap; do not call it identical to indoor zero-search
prefilter rejection. No mapage>3s sampled in four runs.

## minimal proposed patch (review carefully before implementation)
HtCostMap::receive currently builds0.2m terrain.feasible from existential point
scores before physical footprint dilations. In configuration semantics, a nearby
known wall can therefore be ignored by TARE's terrain view but always block XYtheta.
Move terrain aggregation after blocked_footprint is built; feasible only for an
existing >=.5 score whose known-obstacle footprint is unblocked. Keep ground
height averaging and OR-over-fine-cells semantics. Also exact query guard for
known occupied footprint in scalar/vector terrainAdmissible, using latest_
under same mutex so a coarse cell's other fine center cannot admit an actually
blocked query. Scalar/vector should share helper. For configuration scores,
blocked_footprint channels all contain the same physical-obstacle dilation.

CRITICAL: Do NOT make unknown_footprint a new hard rejection in TARE guidance.
That would surround the local map boundary with an unknown halo, disconnect
unseen frontier and cause false completion. Existing optimistic unknown global
guidance stays; actual pose/path/follower strict unknown policy remains unchanged.
Do not change original six TARE functions/TSP/order, model/normalization/threshold,
footprint radius, velocity, search budgets, or completion latch.

## regression/validation
Add actual ROS grid tests in src/tare_planner/tests/ht_ros_test.cpp,TareTerrainTest:
center allP=.9 + one neighboring measured obstacle -> scalar/vector coarse terrain
reject center, poseSupport BLOCKED; far cells remain allowed; clearing newer obstacle
restores guidance; rolling away retains last observed rejection. Neighbor observation
hole -> guidance remains optimistic, execution UNKNOWN. One good heading still
allows when no physical obstacle. Existing edge-of-map unknown tests must stay valid.
Run old code + new test first to preserve meaningful failure, then patch.
Build Release build_standalone/tare_planner (existing install prefix is independent
install_standalone/tare_planner), CTest4, six-function SHA, install new binaries.
Commit pre-code plan first, then code/evidence; freeze candidate.
Fresh indoor600s (at minimum), same pose/speeds/model/quality as44; no hot edits.
Use existing run_ht_multiscene.py with scenarios indoor, unique output/domain,
profile, parameter observer, video encoder stored under.git/experiment-tools.
Compare directly to44 (single C++ interface change); old42 partial comparison not
an isolated causal control. Record actual gate/route/early-completion behavior,
not only elapsed timer. Publish complete data + video + comparison, verified
receipt and retention. Report remaining forest/tunnel issues honestly.
