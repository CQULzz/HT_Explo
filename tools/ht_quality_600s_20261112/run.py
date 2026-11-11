"""Repeat the frozen height-quality candidate for 600s with separate evidence."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path

ROOT = Path('/home/lzz/ht_quality_600s_20261112')
PROJECT = Path('/home/lzz/HT_Explo_quality_20261111')
PREVIOUS = Path('/home/lzz/ht_quality_20261111/runs/cmu_quality_300s_01')

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--name', default='cmu_quality_600s_01')
    args = parser.parse_args()
    spec = importlib.util.spec_from_file_location('quality_runner', PROJECT/'tools/ht_height_quality/run.py')
    runner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runner)
    baseline = json.loads((PREVIOUS/'FREEZE.json').read_text())
    current = runner.freeze()
    if current != baseline:
        raise RuntimeError('Previous frozen candidate changed; refusing a different navigation version')
    ledger = json.loads((ROOT/'BUDGET.json').read_text())
    if ledger['status'] != 'active':
        raise RuntimeError('600s repeat ledger is closed')
    receipt = {'previous_run': str(PREVIOUS), 'previous_files': len(baseline),
               'all_previous_frozen_files_unchanged': True,
               'navigation_parameters_changed': False, 'duration_s': 600}
    (ROOT/'evidence/BASELINE_MATCH.json').write_text(json.dumps(receipt, indent=2))
    runner.ROOT = ROOT
    runner.PY = ROOT/'venv/bin/python'
    original_freeze = runner.freeze
    def freeze():
        result = original_freeze()
        result[str(Path(__file__).resolve())] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
        return result
    runner.freeze = freeze
    runner.case(args.name, 'indoor', 600.)

if __name__ == '__main__':
    main()
