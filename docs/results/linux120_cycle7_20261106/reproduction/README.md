# Read-only/derived-data reproduction

No Gazebo starts here. Use a sourced ROS2 Jazzy environment with current built tare_planner types, NumPy/SciPy/matplotlib/OpenCV and Python mcap.

`python audit_contexts.py RUN --decoder-deps OPTIONAL_MCAP_DIRECTORY` verifies recorded sparse tensors/masks against the exact-source MCAP publication, retaining window-external contexts. It regenerates CONTEXT_VERIFICATION.json.

`python summarize_batch.py BATCH_ROOT` reads all six preserved attempts, their existing independent BAG/VIDEO_VERIFICATION files and ledger, and regenerates compact metrics/figure under BATCH_ROOT/repo/docs/results/linux120_cycle7_20261106. It does not reclassify failures or start models.

`python make_paired_videos.py BATCH_ROOT` creates two paired observer-trajectory videos and decodes every output frame; refuses existing outputs. These are2D telemetry overlays, not camera recordings.

query_recorded_maps.cpp is the diagnostic helper built against this worktree's production ht_cost archive and the same ROS/grid_map include/link flags as ht_xytheta_offline. It deserializes original CDR into the real decoder, uses an isolated ROS domain (211 in this batch), the original prior anchor/time, and a clock of source+1ms to isolate terrain rejection. It never publishes a chassis command. Results are not a real-time replay, reachability certificate or full-route safety proof. Source CDR and pose-query list are in each raw run directory; generator/CRC verification was the preserved /home/lzz/HT_pcd_sim_20261105/verify_bag.py.

These scripts are evidence reproduction for this closed six-attempt batch, not authorization to run another simulation.
