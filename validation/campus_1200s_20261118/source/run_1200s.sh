set -e
R=/home/lzz/ht_campus_1200s_20261118
source "$R/env.sh"
export HT_ENVELOPE_CASE=helios32_crop_box_explicit_labels
Xvfb :105 -screen 0 1920x1080x24 -ac > "$R/setup/xvfb.log" 2>&1 &
xvfb_pid=$!
trap 'kill "$xvfb_pid" 2>/dev/null || true' EXIT
"$R/venv/bin/python" "$R/run.py" --duration 1200 --name explicit_labels_campus_1200s_03 --scene campus > "$R/setup/run_observer_retry.log" 2>&1
