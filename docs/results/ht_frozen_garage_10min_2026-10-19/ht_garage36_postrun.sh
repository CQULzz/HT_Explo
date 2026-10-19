#!/usr/bin/env bash
set -eo pipefail
cd '/home/lzz/my test/HT_Explo-fixposition'
source /opt/ros/jazzy/setup.bash
ht_garage_trial="$(cat /tmp/ht_garage36_run_path)/garage"
python3 /tmp/audit_ht_execution_geometry_scene.py "$ht_garage_trial" --output "$ht_garage_trial/execution_geometry_audit" > /tmp/ht_garage36_geometry_audit.log 2>&1
python3 presentations/audit_cupy_latency.py "$ht_garage_trial" --output "$ht_garage_trial/latency_audit" > /tmp/ht_garage36_latency_audit.log 2>&1
python3 presentations/audit_blocked_commands.py "$ht_garage_trial" --output "$ht_garage_trial/blocked_commands.json" > /tmp/ht_garage36_blocked_audit.log 2>&1
python3 presentations/audit_pose_admissibility_changes.py "$ht_garage_trial" --output "$ht_garage_trial/pose_admission_audit.json" --capture-final "$ht_garage_trial/final_pose_snapshot.npz" > /tmp/ht_garage36_pose_audit.log 2>&1
python3 presentations/audit_ht_context_dumps.py "$ht_garage_trial" --verify-model --output "$ht_garage_trial/context_consistency.json" > /tmp/ht_garage36_context_audit.log 2>&1
python3 /tmp/audit_ht_search_termination_direct.py "$ht_garage_trial" --output "$ht_garage_trial/search_audit" > /tmp/ht_garage36_search_audit.log 2>&1
python3 /tmp/audit_ht_cell_coverage.py "$ht_garage_trial" --output "$ht_garage_trial/cell_coverage_audit" > /tmp/ht_garage36_cell_audit.log 2>&1
printf 'All repeat audits completed.\n'

python3 presentations/audit_ht_search_scheduling.py "$ht_garage_trial" --output "$ht_garage_trial/scheduling_audit" > /tmp/ht_garage36_scheduling_audit.log

python3 /tmp/audit_ht_recovery_wins.py "$ht_garage_trial" --output "$ht_garage_trial/recovery_wins.json" > /tmp/ht_garage36_wins_audit.log

python3 /tmp/audit_ht_stop_episodes.py "$ht_garage_trial" --output "$ht_garage_trial/stop_episodes.json"
python3 /tmp/audit_ht_context_integrity.py "$ht_garage_trial" --output "$ht_garage_trial/context_integrity.json" > /tmp/ht_garage36_context_integrity.log
