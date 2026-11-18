set -e
R=/home/lzz/ht_campus_to_finish_20261118
source "$R/env.sh"
export HT_ENVELOPE_CASE=helios32_crop_box_explicit_labels_to_finish
Xvfb :108 -screen 0 1920x1080x24 -ac > "$R/setup/xvfb.log" 2>&1 &
xvfb_pid=$!
trap 'kill "$xvfb_pid" 2>/dev/null || true' EXIT
"$R/venv/bin/python" "$R/run.py" --duration 0 --name campus_to_finish_01 --scene campus > "$R/setup/run.log" 2>&1
