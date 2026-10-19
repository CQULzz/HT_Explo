#!/usr/bin/env bash
set -eo pipefail
cd '/home/lzz/my test/HT_Explo-fixposition'
python3 - <<'PY'
from pathlib import Path
import time
p=Path(Path('/tmp/ht_prune39_run_path').read_text().strip());deadline=time.monotonic()+900
while not (p/'FINISHED.json').exists():
 if time.monotonic()>deadline:raise TimeoutError('Trial did not finish; retain partial data')
 time.sleep(3)
PY
bash /tmp/ht_prune39_postrun.sh > /tmp/ht_prune39_postrun.log 2>&1
python3 presentations/archive_ht_multiscene.py "$(cat /tmp/ht_prune39_run_path)" --scenarios garage --output docs/results/ht_successor_pruning_10min_2026-10-20 > /tmp/ht_prune39_base_archive.log 2>&1
python3 presentations/compare_ht_iterations.py --run '阶段36=docs/results/ht_frozen_garage_10min_2026-10-19/garage' --run '阶段38=docs/results/ht_guide_handoff_10min_2026-10-19/garage' --run "阶段39=$(cat /tmp/ht_prune39_run_path)/garage" --output docs/results/ht_successor_pruning_10min_2026-10-20/comparison > /tmp/ht_prune39_comparison.log 2>&1
python3 presentations/plot_ht_guide_handoff.py --run '阶段36=docs/results/ht_frozen_garage_10min_2026-10-19/garage' --run '阶段38=docs/results/ht_guide_handoff_10min_2026-10-19/garage' --run '阶段39=docs/results/ht_successor_pruning_10min_2026-10-20/garage' --title '车库同条件600秒：阶段39支配边提前剪枝；对照阶段36/38' --stem pruning_comparison --output docs/results/ht_successor_pruning_10min_2026-10-20/comparison > /tmp/ht_prune39_plot.log 2>&1
python3 /tmp/archive_prune39_round.py > /tmp/ht_prune39_archive.log 2>&1
python3 presentations/plot_ht_revision_history.py --metrics-root presentations/scheduled_results/ht_revision_metric_reanalysis_2026-10-19 --output docs/results/ht_successor_pruning_10min_2026-10-20/history > /tmp/ht_prune39_history.log 2>&1
python3 presentations/plot_ht_revision_efficiency.py docs/results/ht_successor_pruning_10min_2026-10-20/history > /tmp/ht_prune39_efficiency.log 2>&1
python3 /tmp/finalize_prune39_reports.py > /tmp/ht_prune39_finalize.log 2>&1
