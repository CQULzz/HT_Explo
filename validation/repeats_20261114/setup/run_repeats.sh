set -eo pipefail
R=/home/lzz/ht_repeat_20261114
source "$R/env.sh"
Xvfb :88 -screen 0 1280x720x24 > "$R/setup/xvfb.log" 2>&1 &
XVFB_PID=$!
trap 'kill "$XVFB_PID" 2>/dev/null || true' EXIT
sleep 2
for name in repeat_01 repeat_02; do
  "$R/venv/bin/python" "$R/run.py" --duration 300 --name "$name" --scene indoor > "$R/setup/$name.log" 2>&1
done
echo REPEATS_COMPLETE
