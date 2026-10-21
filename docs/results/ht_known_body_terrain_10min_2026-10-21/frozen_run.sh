#!/bin/bash
set -eo pipefail
cd '/home/lzz/my test/HT_Explo-fixposition'
source /opt/ros/jazzy/setup.bash
if [[ $(git rev-parse HEAD) != 15e197eca16bee3dea1fcd3870a05ee84f2ecd12 ]]; then exit 10; fi
if [[ -n $(git status --porcelain) ]]; then exit 11; fi
export HT_PROFILE_CUPY=1
observer_pid=''
finish() {
 task_return=$?
 if [[ -n "$observer_pid" ]] && kill -0 "$observer_pid" 2>/dev/null; then kill "$observer_pid" 2>/dev/null || true; wait "$observer_pid" 2>/dev/null || true; fi
 exit "$task_return"
}
trap finish EXIT
python3 -u presentations/capture_tare_multiscene_runtime.py '/home/lzz/my test/HT_Explo-fixposition/presentations/scheduled_results/ht_known_body_terrain_10min_2026-10-21_12-49-46' --domain 224 > .git/terrain-gate-runtime/parameters.log 2>&1 &
observer_pid=$!
python3 -u presentations/run_ht_multiscene.py --duration 600 --scenarios indoor --domain 224 --encoder '/home/lzz/my test/HT_Explo-fixposition/.git/experiment-tools/python/imageio_ffmpeg/binaries/ffmpeg-linux-x86_64-v7.0.2' --output '/home/lzz/my test/HT_Explo-fixposition/presentations/scheduled_results/ht_known_body_terrain_10min_2026-10-21_12-49-46'
wait "$observer_pid"
observer_pid=''
