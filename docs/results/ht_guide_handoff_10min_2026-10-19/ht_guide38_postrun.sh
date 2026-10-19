#!/usr/bin/env bash
set -eo pipefail
cd '/home/lzz/my test/HT_Explo-fixposition'
source /opt/ros/jazzy/setup.bash
ht_guide_trial="$(cat /tmp/ht_guide38_run_path)/garage"
python3 /tmp/audit_ht_execution_geometry_scene.py "$ht_guide_trial" --output "$ht_guide_trial/execution_geometry_audit" > /tmp/ht_guide38_geometry_audit.log 2>&1
python3 presentations/audit_cupy_latency.py "$ht_guide_trial" --output "$ht_guide_trial/latency_audit" > /tmp/ht_guide38_latency_audit.log 2>&1
python3 presentations/audit_blocked_commands.py "$ht_guide_trial" --output "$ht_guide_trial/blocked_commands.json" > /tmp/ht_guide38_blocked_audit.log 2>&1
python3 presentations/audit_pose_admissibility_changes.py "$ht_guide_trial" --output "$ht_guide_trial/pose_admission_audit.json" --capture-final "$ht_guide_trial/final_pose_snapshot.npz" > /tmp/ht_guide38_pose_audit.log 2>&1
python3 presentations/audit_ht_context_dumps.py "$ht_guide_trial" --verify-model --output "$ht_guide_trial/context_consistency.json" > /tmp/ht_guide38_context_audit.log 2>&1
python3 /tmp/audit_ht_search_termination_direct.py "$ht_guide_trial" --output "$ht_guide_trial/search_audit" > /tmp/ht_guide38_search_audit.log 2>&1
python3 /tmp/audit_ht_cell_coverage.py "$ht_guide_trial" --output "$ht_guide_trial/cell_coverage_audit" > /tmp/ht_guide38_cell_audit.log 2>&1
printf 'All repeat audits completed.\n'

python3 presentations/audit_ht_search_scheduling.py "$ht_guide_trial" --output "$ht_guide_trial/scheduling_audit" > /tmp/ht_guide38_scheduling_audit.log

python3 /tmp/audit_ht_recovery_wins.py "$ht_guide_trial" --output "$ht_guide_trial/recovery_wins.json" > /tmp/ht_guide38_wins_audit.log

python3 /tmp/audit_ht_stop_episodes.py "$ht_guide_trial" --output "$ht_guide_trial/stop_episodes.json"
python3 /tmp/audit_ht_context_integrity.py "$ht_guide_trial" --output "$ht_guide_trial/context_integrity.json" > /tmp/ht_guide38_context_integrity.log

python3 presentations/audit_ht_source_age_alignment.py "$ht_guide_trial" --output "$ht_guide_trial/source_age_alignment.json" > /tmp/ht_guide38_source_age.log

python3 presentations/audit_ht_scan_delivery_trace.py "$ht_guide_trial" --output "$ht_guide_trial/scan_delivery_trace.json" > /tmp/ht_guide38_scan_delivery.log
python3 presentations/audit_ht_guide_handoff.py "$ht_guide_trial" --output "$ht_guide_trial/guide_handoff_audit.json" > /tmp/ht_guide38_handoff.log
