#!/usr/bin/env bash
# Resumable data publication; the completion marker prevents reruns after login.
set -euo pipefail
task_repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
cd -- "$task_repo"
task_runtime="$task_repo/.git/legacy-archive-runtime"
mkdir -p -- "$task_runtime"
if [[ -f "$task_runtime/COMPLETE" ]]; then
  echo 'Historical publication already completed.'
  exit 0
fi
until gh auth token >/dev/null 2>&1 && gh api user --silent >/dev/null 2>&1; do
  echo 'Waiting for existing system-keyring GitHub authentication; unlock in the system dialog. No archive source has been removed.'
  sleep 30
done
python3 -u scripts/archive_legacy_ht_data.py --workers 3
bash scripts/finalize_legacy_ht_archive.sh
date -Is > "$task_runtime/COMPLETE"
