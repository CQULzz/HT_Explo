#!/usr/bin/env bash
set -eo pipefail
cd '/home/lzz/my test/HT_Explo-fixposition'
python3 - <<'PY'
from pathlib import Path
import time
p=Path(Path('/tmp/ht_tare40_run_path').read_text().strip());deadline=time.monotonic()+1200
while not (p/'FINISHED.json').exists():
 if (p/'FAILED.json').exists():raise RuntimeError('Retain failed suite '+str(p))
 if time.monotonic()>deadline:raise TimeoutError('Retain partial suite '+str(p))
 time.sleep(3)
PY
bash /tmp/ht_tare40_postrun.sh > /tmp/ht_tare40_postrun.log 2>&1
python3 presentations/archive_ht_multiscene.py "$(cat /tmp/ht_tare40_run_path)" --scenarios garage --output docs/results/ht_tare_waypoint_10min_2026-10-20 > /tmp/ht_tare40_base_archive.log 2>&1
python3 presentations/compare_ht_iterations.py --run '阶段36=docs/results/ht_frozen_garage_10min_2026-10-19/garage' --run '阶段38=docs/results/ht_guide_handoff_10min_2026-10-19/garage' --run '阶段39=docs/results/ht_successor_pruning_10min_2026-10-20/garage' --run "阶段40 TARE顺序+HT=$(cat /tmp/ht_tare40_run_path)/garage" --output docs/results/ht_tare_waypoint_10min_2026-10-20/comparison > /tmp/ht_tare40_comparison.log 2>&1
python3 /tmp/archive_tare40_round.py > /tmp/ht_tare40_archive.log 2>&1
python3 presentations/plot_ht_revision_history.py --metrics-root presentations/scheduled_results/ht_revision_metric_reanalysis_2026-10-19 --output docs/results/ht_tare_waypoint_10min_2026-10-20/history > /tmp/ht_tare40_history.log 2>&1
python3 presentations/plot_ht_revision_efficiency.py docs/results/ht_tare_waypoint_10min_2026-10-20/history > /tmp/ht_tare40_efficiency.log 2>&1
python3 /tmp/finalize_tare40_reports.py > /tmp/ht_tare40_finalize.log 2>&1
