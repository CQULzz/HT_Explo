#!/usr/bin/env bash
set -eo pipefail
cd '/home/lzz/my test/HT_Explo-fixposition'
python3 - <<'PY'
from pathlib import Path
import time
p=Path(Path('/tmp/ht_tare41_run_path').read_text().strip());deadline=time.monotonic()+1200
while not (p/'FINISHED.json').exists():
 if (p/'FAILED.json').exists():raise RuntimeError('Retain failed suite '+str(p))
 if time.monotonic()>deadline:raise TimeoutError('Retain partial suite '+str(p))
 time.sleep(3)
PY
bash /tmp/ht_tare41_postrun.sh > /tmp/ht_tare41_postrun.log 2>&1
python3 presentations/archive_ht_multiscene.py "$(cat /tmp/ht_tare41_run_path)" --scenarios garage --output docs/results/ht_tare_boundaries_10min_2026-10-20 > /tmp/ht_tare41_base_archive.log 2>&1
python3 presentations/compare_ht_iterations.py --run '阶段39=docs/results/ht_successor_pruning_10min_2026-10-20/garage' --run '阶段40 原TARE+HT=docs/results/ht_tare_waypoint_10min_2026-10-20/garage' --run "阶段41 接口修正=$(cat /tmp/ht_tare41_run_path)/garage" --output docs/results/ht_tare_boundaries_10min_2026-10-20/comparison > /tmp/ht_tare41_comparison.log 2>&1
python3 presentations/plot_tare_route_comparison.py --run '39 HT自选=docs/results/ht_successor_pruning_10min_2026-10-20/garage' --run '40 原TARE+HT=docs/results/ht_tare_waypoint_10min_2026-10-20/garage' --run "41 接口修正=$(cat /tmp/ht_tare41_run_path)/garage" --output docs/results/ht_tare_boundaries_10min_2026-10-20/comparison > /tmp/ht_tare41_readable_plots.log 2>&1
python3 /tmp/archive_tare41_round.py > /tmp/ht_tare41_archive.log 2>&1
python3 presentations/plot_ht_revision_history.py --metrics-root presentations/scheduled_results/ht_revision_metric_reanalysis_2026-10-19 --output docs/results/ht_tare_boundaries_10min_2026-10-20/history > /tmp/ht_tare41_history.log 2>&1
python3 presentations/plot_ht_revision_efficiency.py docs/results/ht_tare_boundaries_10min_2026-10-20/history > /tmp/ht_tare41_efficiency.log 2>&1
python3 /tmp/finalize_tare41_reports.py > /tmp/ht_tare41_finalize.log 2>&1
