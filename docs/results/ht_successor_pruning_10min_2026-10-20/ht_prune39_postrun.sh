#!/usr/bin/env bash
set -eo pipefail
cd '/home/lzz/my test/HT_Explo-fixposition'
source /opt/ros/jazzy/setup.bash
ht_prune_trial="$(cat /tmp/ht_prune39_run_path)/garage"
python3 /tmp/audit_ht_execution_geometry_scene.py "$ht_prune_trial" --output "$ht_prune_trial/execution_geometry_audit" > /tmp/ht_prune39_geometry_audit.log 2>&1
python3 presentations/audit_cupy_latency.py "$ht_prune_trial" --output "$ht_prune_trial/latency_audit" > /tmp/ht_prune39_latency_audit.log 2>&1
python3 presentations/audit_blocked_commands.py "$ht_prune_trial" --output "$ht_prune_trial/blocked_commands.json" > /tmp/ht_prune39_blocked_audit.log 2>&1
python3 presentations/audit_pose_admissibility_changes.py "$ht_prune_trial" --output "$ht_prune_trial/pose_admission_audit.json" --capture-final "$ht_prune_trial/final_pose_snapshot.npz" > /tmp/ht_prune39_pose_audit.log 2>&1
python3 presentations/audit_ht_context_dumps.py "$ht_prune_trial" --verify-model --output "$ht_prune_trial/context_consistency.json" > /tmp/ht_prune39_context_audit.log 2>&1
python3 /tmp/audit_ht_search_pruning.py "$ht_prune_trial" --output "$ht_prune_trial/search_audit" > /tmp/ht_prune39_search_audit.log 2>&1
python3 /tmp/audit_ht_cell_coverage.py "$ht_prune_trial" --output "$ht_prune_trial/cell_coverage_audit" > /tmp/ht_prune39_cell_audit.log 2>&1
printf 'All repeat audits completed.\n'

python3 presentations/audit_ht_search_scheduling.py "$ht_prune_trial" --output "$ht_prune_trial/scheduling_audit" > /tmp/ht_prune39_scheduling_audit.log

python3 /tmp/audit_ht_recovery_wins.py "$ht_prune_trial" --output "$ht_prune_trial/recovery_wins.json" > /tmp/ht_prune39_wins_audit.log

python3 /tmp/audit_ht_stop_episodes.py "$ht_prune_trial" --output "$ht_prune_trial/stop_episodes.json"
python3 /tmp/audit_ht_context_integrity.py "$ht_prune_trial" --output "$ht_prune_trial/context_integrity.json" > /tmp/ht_prune39_context_integrity.log

python3 presentations/audit_ht_source_age_alignment.py "$ht_prune_trial" --output "$ht_prune_trial/source_age_alignment.json" > /tmp/ht_prune39_source_age.log

python3 presentations/audit_ht_scan_delivery_trace.py "$ht_prune_trial" --output "$ht_prune_trial/scan_delivery_trace.json" > /tmp/ht_prune39_scan_delivery.log
python3 presentations/audit_ht_guide_handoff.py "$ht_prune_trial" --output "$ht_prune_trial/guide_handoff_audit.json" > /tmp/ht_prune39_handoff.log
