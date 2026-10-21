#!/bin/bash
set -eo pipefail
cd '/home/lzz/my test/HT_Explo-fixposition'
source /opt/ros/jazzy/setup.bash
if [[ $(git rev-parse HEAD) != 07c1abd334f83cb8d602e2234134b4286862c916 ]]; then exit 10; fi
if [[ -n $(git status --porcelain) ]]; then exit 11; fi
export HT_PROFILE_CUPY=1
observer_pid=''
finish() {
 task_return=$?
 if [[ -n "$observer_pid" ]] && kill -0 "$observer_pid" 2>/dev/null; then kill "$observer_pid" 2>/dev/null || true; wait "$observer_pid" 2>/dev/null || true; fi
 exit "$task_return"
}
trap finish EXIT
python3 -u presentations/capture_tare_multiscene_runtime.py '/home/lzz/my test/HT_Explo-fixposition/presentations/scheduled_results/ht_continuous_domain_10min_2026-10-21_13-17-09' --domain 225 > .git/continuous-domain-runtime/parameters.log 2>&1 &
observer_pid=$!
python3 -u presentations/run_ht_multiscene.py --duration 600 --scenarios indoor --domain 225 --encoder '/home/lzz/my test/HT_Explo-fixposition/.git/experiment-tools/python/imageio_ffmpeg/binaries/ffmpeg-linux-x86_64-v7.0.2' --output '/home/lzz/my test/HT_Explo-fixposition/presentations/scheduled_results/ht_continuous_domain_10min_2026-10-21_13-17-09'
wait "$observer_pid"
observer_pid=''
