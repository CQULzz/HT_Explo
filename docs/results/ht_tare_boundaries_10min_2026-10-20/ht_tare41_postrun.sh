#!/usr/bin/env bash
set -eo pipefail
cd '/home/lzz/my test/HT_Explo-fixposition'
source /opt/ros/jazzy/setup.bash
ht_trial="$(cat /tmp/ht_tare41_run_path)/garage"
python3 presentations/audit_tare_waypoint.py "$ht_trial" --output "$ht_trial/tare_waypoint_audit" > /tmp/ht_tare41_contract_audit.log 2>&1
python3 /tmp/audit_ht_execution_geometry_scene.py "$ht_trial" --output "$ht_trial/execution_geometry_audit" > /tmp/ht_tare41_geometry_audit.log 2>&1
python3 presentations/audit_cupy_latency.py "$ht_trial" --output "$ht_trial/latency_audit" > /tmp/ht_tare41_latency_audit.log 2>&1
python3 presentations/audit_blocked_commands.py "$ht_trial" --output "$ht_trial/blocked_commands.json" > /tmp/ht_tare41_blocked_audit.log 2>&1
python3 presentations/audit_pose_admissibility_changes.py "$ht_trial" --output "$ht_trial/pose_admission_audit.json" --capture-final "$ht_trial/final_pose_snapshot.npz" > /tmp/ht_tare41_pose_audit.log 2>&1
python3 presentations/audit_ht_context_dumps.py "$ht_trial" --verify-model --output "$ht_trial/context_consistency.json" > /tmp/ht_tare41_context_audit.log 2>&1
python3 /tmp/audit_ht_stop_episodes.py "$ht_trial" --output "$ht_trial/stop_episodes.json" > /tmp/ht_tare41_stops.log 2>&1
python3 /tmp/audit_ht_context_integrity.py "$ht_trial" --output "$ht_trial/context_integrity.json" > /tmp/ht_tare41_context_integrity.log 2>&1
python3 presentations/audit_ht_source_age_alignment.py "$ht_trial" --output "$ht_trial/source_age_alignment.json" > /tmp/ht_tare41_source_age.log 2>&1
python3 presentations/audit_ht_scan_delivery_trace.py "$ht_trial" --output "$ht_trial/scan_delivery_trace.json" > /tmp/ht_tare41_scan_delivery.log 2>&1
