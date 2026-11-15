#!/bin/bash
set -e
R=/home/lzz/ht_urdf_compare_20261115
source "$R/env.sh"
Xvfb :93 -screen 0 1920x1080x24 -ac > "$R/setup/xvfb.log" 2>&1 &
xvfb_pid=$!
echo "$xvfb_pid" > "$R/setup/xvfb.pid"
trap 'kill "$xvfb_pid" 2>/dev/null || true' EXIT
export HT_ENVELOPE_CASE=baseline
"$R/venv/bin/python" "$R/run.py" --duration 600 --name baseline_campus_600s_01 --scene campus > "$R/setup/baseline_run.log" 2>&1
export HT_ENVELOPE_CASE=urdf
"$R/venv/bin/python" "$R/run.py" --duration 600 --name urdf_campus_600s_01 --scene campus > "$R/setup/urdf_run.log" 2>&1
echo PAIR_COMPLETE
