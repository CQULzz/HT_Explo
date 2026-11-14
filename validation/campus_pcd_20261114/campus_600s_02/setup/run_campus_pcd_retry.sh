set -eo pipefail
R=/home/lzz/ht_campus_pcd_20261114
source "$R/env.sh"
Xvfb :88 -screen 0 1280x720x24 > "$R/setup/xvfb_retry.log" 2>&1 &
XVFB_PID=$!
trap 'kill "$XVFB_PID" 2>/dev/null || true' EXIT
sleep 2
"$R/venv/bin/python" "$R/run.py" --duration 600 --name campus_600s_02 --scene campus > "$R/setup/campus_600s_02.log" 2>&1
"$R/venv/bin/python" "$R/run.py" --duration 600 --name user_pcd_600s_01 --scene user_pcd > "$R/setup/user_pcd_600s_01.log" 2>&1
echo CAMPUS_PCD_COMPLETE
