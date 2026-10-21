#!/bin/bash
set -eo pipefail
cd '/home/lzz/my test/HT_Explo-fixposition'
while [[ $(systemctl --user show ht-continuous-domain-10min.service -p MainPID --value) != 0 ]]; do sleep 5; done
source /opt/ros/jazzy/setup.bash
export OPENBLAS_NUM_THREADS=1
if [[ ! -f '/home/lzz/my test/HT_Explo-fixposition/docs/results/ht_continuous_domain_10min_2026-10-21/files_sha256.json' ]]; then
 python3 -u presentations/finalize_tare_multiscene.py '/home/lzz/my test/HT_Explo-fixposition/presentations/scheduled_results/ht_continuous_domain_10min_2026-10-21_13-17-09' --state .git/continuous-domain-runtime/job.json --allow-interrupted
fi
if [[ ! -f '/home/lzz/my test/HT_Explo-fixposition/docs/results/ht_continuous_domain_10min_2026-10-21/comparison_metrics.json' ]]; then
 python3 -u .git/continuous-domain-runtime/extra.py
fi
python3 -u .git/continuous-domain-runtime/publish.py
