# Publish the current quality-fix experiments

The user requested upload of the latest code and experiments to the matching
branch on 2026-11-12. Code, reports, plots and small videos belong to
`sim/ht-height-quality-20261111`. Full original data is prepared as experiment
release assets tied to that branch's corresponding source/report commits:

| Experiment | Data tag | Code/report commit |
|---|---|---|
| 300s quality fix | ht-quality-300s-20261111 | 68e5330 |
| 600s repeat, including interrupted first trial | ht-quality-600s-20261112 | 03521b8 |

`prepare.py` rechecks the original raw-data receipts, inventories every regular
file, archives non-MCAP evidence, verifies archive member bytes, and makes
uniquely named hardlinks to the unchanged MCAPs. Shared dependency symlinks are
recorded rather than followed. `SOURCE_REFERENCE.json` links to the exact full
source commit/archive in GitHub; tested runtime snapshots remain in each
evidence archive. No large MCAP is added to Git history.

`upload.py` uses the user's normal `gh auth login` session, checks repository
write access, creates exact-commit tags, uploads into draft experiment releases,
and verifies each remote asset's size and GitHub SHA256 digest. A release is
published only after all its assets verify. Valid existing assets are never
overwritten. Partial uploads owned by this run are preserved under distinct
incomplete names if a retry is necessary. The complete local source data is
retained regardless of upload status.

Prepared assets and upload receipts:
`/home/lzz/ht_quality_github_20261112`. Files named `REMOTE_RECEIPT` are only
complete when `status` is `complete_verified`; preparing files or uploading
only some assets is not a complete remote backup.

After downloading all assets for a tag with GitHub's release UI or
`gh release download TAG --repo CQULzz/HT_Explo --dir DOWNLOAD_DIR`, restore:

```bash
python3 tools/ht_quality_upload_20261112/restore.py \
  --manifest DOWNLOAD_DIR/TAG--MANIFEST.json \
  --assets-dir DOWNLOAD_DIR --output NEW_EMPTY_OUTPUT_PATH
```

The restored complete bag retains its original filenames and metadata. The
interrupted trial remains incomplete, including its original NUL bytes and
missing metadata. External ROS/CMU/Python installations must be supplied
separately; frozen runtime archives, source and parameter evidence are included.
No hardware deployment, new simulation or data pruning is authorized here.
