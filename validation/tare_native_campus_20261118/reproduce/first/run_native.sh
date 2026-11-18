set -e
R=/home/lzz/tare_native_campus_20261118
source "$R/env.sh"
Xvfb :109 -screen 0 1920x1080x24 -ac > "$R/setup/xvfb.log" 2>&1 &
xvfb_pid=$!
trap 'kill "$xvfb_pid" 2>/dev/null || true' EXIT
python3 "$R/run.py" > "$R/setup/run.log" 2>&1
