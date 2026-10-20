#!/usr/bin/env bash
set -eo pipefail
task_repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
cd -- "$task_repo"
source /opt/ros/jazzy/setup.bash
task_state="$task_repo/.git/multiscene-runtime/job.json"
task_suite=$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1]))["suite"])' "$task_state")
task_encoder=$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1]))["encoder"])' "$task_state")
task_domain=$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1]))["domain"])' "$task_state")
task_expected=$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1]))["candidate_commit"])' "$task_state")
if [[ $(git rev-parse HEAD) != "$task_expected" ]]; then
  echo 'Candidate HEAD changed before measurement; refusing an unrecorded substitution.' >&2
  exit 1
fi
task_observer=''
function finish_suite_runner() {
  task_return=$?
  if [[ -n "$task_observer" ]] && kill -0 "$task_observer" 2>/dev/null; then
    kill "$task_observer" 2>/dev/null || true
    wait "$task_observer" 2>/dev/null || true
  fi
  systemctl --user start --no-block ht-legacy-archive.service || true
  exit "$task_return"
}
trap finish_suite_runner EXIT
export HT_PROFILE_CUPY=1
python3 scripts/check_tare_waypoint_contract.py > .git/multiscene-runtime/upstream_contract.json
python3 presentations/capture_tare_multiscene_runtime.py "$task_suite" --domain "$task_domain" > .git/multiscene-runtime/runtime_capture.log 2>&1 &
task_observer=$!
python3 -u presentations/run_ht_multiscene.py --duration 600 \
  --scenarios garage campus indoor forest tunnel --domain "$task_domain" \
  --encoder "$task_encoder" --output "$task_suite"
wait "$task_observer"
task_observer=''
python3 presentations/finalize_tare_multiscene.py "$task_suite" --state "$task_state"
