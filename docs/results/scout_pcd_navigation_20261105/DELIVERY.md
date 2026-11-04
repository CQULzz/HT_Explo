# PCD simulation delivery completed

Release: https://github.com/CQULzz/HT_Explo/releases/tag/ht-scout-pcd-fix-20261105-v1

Tested navigation code: `53fcb471ee9b36bf238355d530a9f00d02a6ab14`. The existing 600.3-second simulation and original results were recovered from the physical dual-boot Linux ext4 partition using read-only access. No simulation was rerun and no navigation parameters or tested binaries were changed during publication recovery.

The complete prior and current existing evidence was packed into three archives: `previous-evidence`, `navigation-fix`, and `tested-install`. All archive entries were read back and checked against per-file SHA-256 inventories. All 12 existing MCAP files were included (8 prior-run files plus 4 current/diagnostic files), including failed and partial captures. No full-rate raw LiDAR data beyond what was originally recorded is claimed.

37 evidence assets (13,934,834,407 bytes) were individually checked against GitHub-reported sizes and SHA-256 digests before the draft was published. The receipt itself was uploaded and verified separately. Full asset URLs and hashes are recorded in [PUBLICATION_RECEIPT.json](PUBLICATION_RECEIPT.json).

Installation symlinks were materialized during read-only export; resolved source paths and original file modes are preserved in the installation inventory. Caches, duplicate `.git` directories, regenerable `query_cdr`, and the unused `baseline_install` copy were excluded. All source recordings remain intact on the Linux partition.

The release uploader was corrected to resolve draft release IDs through `gh release view`; GitHub's tag REST endpoint returned 404 for the draft. Existing publication receipts are verified instead of blindly re-uploaded.

The experiment completed its requested duration, but the exploration mission did not complete: motion stopped at the scene crop boundary, map-age holds remain, and mapper cleanup required a forced exit after collection. See [README.md](README.md) for the original results and limits. This release is experimental and does not represent physical-vehicle acceptance.
