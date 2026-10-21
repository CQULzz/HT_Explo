#!/bin/bash
set -eo pipefail
cd '/home/lzz/my test/HT_Explo-fixposition'
while [[ $(systemctl --user show ht-sparse-height-post.service -p MainPID --value) != 0 ]]; do sleep 5; done
if [[ $(systemctl --user show ht-sparse-height-post.service -p Result --value) != success ]]; then echo 'Postprocessing failed; preserve all data'; exit 21; fi
source /opt/ros/jazzy/setup.bash
export OPENBLAS_NUM_THREADS=1
if [[ ! -f docs/results/ht_sparse_height_4scene_10min_2026-10-21/remaining_issues.json ]]; then
  python3 -u .git/indoor-input-runtime/extra.py
fi
python3 -u .git/indoor-input-runtime/publish.py
