#!/bin/bash
set -e
R=/home/lzz/ht_helios_collision_20261115
python3 /mnt/d/HT-Helios-Collision-20261115/setup/prepare_retry.py
python3 /mnt/d/HT-Helios-Collision-20261115/setup/prepare_runtime.py
source "$R/env.sh"
export HT_ENVELOPE_CASE=helios32_opaque
Xvfb :96 -screen 0 1920x1080x24 -ac > "$R/setup/xvfb_retry.log" 2>&1 &
xvfb_pid=$!
echo "$xvfb_pid" > "$R/setup/xvfb.pid"
trap 'kill "$xvfb_pid" 2>/dev/null || true' EXIT
"$R/venv/bin/python" "$R/run.py" --duration 600 --name helios32_opaque_campus_600s_02 --scene campus > "$R/setup/formal_retry.log" 2>&1
echo CORRECTED_CHAIN_RETRY_COMPLETE
