#!/bin/bash
set -eo pipefail
cd '/home/lzz/my test/HT_Explo-fixposition'
while [[ $(systemctl --user show ht-sparse-height-4scene.service -p MainPID --value) != 0 ]]; do sleep 5; done
source /opt/ros/jazzy/setup.bash
python3 -u presentations/finalize_tare_multiscene.py "$(python3 -c 'import json; print(json.load(open(".git/indoor-input-runtime/job.json"))["suite"])')" --state .git/indoor-input-runtime/job.json --allow-interrupted
