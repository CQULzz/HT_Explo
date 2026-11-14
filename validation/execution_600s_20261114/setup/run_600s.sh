set -eo pipefail
R=/home/lzz/ht_600s_20261114
source "$R/env.sh"
Xvfb :88 -screen 0 1280x720x24 > "$R/setup/xvfb.log" 2>&1 &
XVFB_PID=$!
trap 'kill "$XVFB_PID" 2>/dev/null || true' EXIT
sleep 2
"$R/venv/bin/python" "$R/run.py" --duration 600 --name execution_600s_01 --scene indoor > "$R/setup/formal_run.log" 2>&1
python3 /home/lzz/HT_Explo_execution_20261113/tools/cmu_minimal/audit_commands.py "$R/runs/execution_600s_01" > "$R/setup/command_audit.log" 2>&1
echo EXPERIMENT_600S_COMPLETE
