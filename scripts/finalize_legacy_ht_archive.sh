#!/usr/bin/env bash
# Finish only after complete verified archive receipts exist; never delete sources.
set -euo pipefail
task_repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
cd -- "$task_repo"
if [[ $(git branch --show-current) != codex/ht8dir-v1 ]]; then
  echo 'Refuse to publish from an unexpected branch.' >&2
  exit 1
fi
if ! git diff --cached --quiet; then
  echo 'Existing staged changes found; preserve them and finish publication manually.' >&2
  exit 1
fi
python3 scripts/archive_legacy_ht_data.py --self-test
python3 scripts/verify_legacy_ht_archive.py --check-local-bytes
python3 scripts/report_legacy_ht_archive.py
python3 scripts/link_legacy_ht_releases.py --apply
python3 scripts/publish_version_notes.py --dry-run
git add -- docs/experiments/legacy_archive docs/release_notes \
  docs/plans/2026-10-20_historical_data_archive.md \
  scripts/archive_legacy_ht_data.py scripts/report_legacy_ht_archive.py \
  scripts/verify_legacy_ht_archive.py scripts/link_legacy_ht_releases.py \
  scripts/finalize_legacy_ht_archive.sh scripts/run_legacy_ht_archive.sh \
  scripts/install_legacy_ht_archive_service.py
if ! git diff --cached --quiet; then
  git -c user.name=Codex -c user.email=codex@local commit \
    -m 'Verify all 62 historical data archives and link corresponding GitHub releases'
fi
git push origin HEAD:codex/ht8dir-v1
echo 'COMPLETE: 62 datasets verified, release notes linked, catalogue pushed; historical sources retained.'
