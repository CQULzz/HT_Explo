# Frozen-candidate 600s repeat

`run.py` checks the previous 232-file navigation manifest, uses a separate
ledger and data directory, and calls the existing runner with a 600s duration.
The retry also used a temporary `systemd-inhibit sleep:idle` process. No mapper,
neural model, TARE, path selection or control parameters were changed.

The first attempt was interrupted by a host reboot after a clock jump and GPU
driver errors. Its raw files remain unchanged. `inspect_interrupted.py` parses
diagnostic copies in memory and explicitly marks this attempt incomplete.

Offline tools for the completed second attempt:

- `analyze.py`: equal-window metrics, recovery episodes, plots and a decodable
  trajectory video; the old 300s measurement is never extrapolated to 600s.
- `inspect_progress.py`: compare actual motion and new observed-volume growth.
- `audit_boundary.py`: supplement any output/audit timestamp boundary mismatch
  after the unchanged command-map audit and output matcher have run.
- `finalize.py`: verify frozen files, hash all original bag files and close the
  completed ledger. It does not recover or overwrite the interrupted bag.
- `write_report.py`: render the final report and compact evidence.
- `resource_monitor.py`: sparse read-only CPU/memory/power/clock snapshots.

Data: `/home/lzz/ht_quality_600s_20261112`. Run the analysis under its `env.sh`
and existing ROS/CuPy Python environment. Full MCAP and video are local only;
do not prune data without a verified complete remote backup. No Release or
hardware deployment is part of this repeat.
