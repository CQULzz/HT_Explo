# Independent CuPy mapping fixes

Apply `cupy_ht_mapping.patch` to the separate repository/version recorded in
`manifest.json`. HT and CuPy retain separate `src`, build and install trees.
The HT-side bridge is included in `../ht_cupy_bridge`, including its own model
checkpoint; it does not import a neighbouring bridge workspace.

```bash
source /opt/ros/jazzy/setup.bash
python3 tools/install_elevation_fixes.py --workspace /path/to/elevation_mapping_cupy_ws --build
```

The patch fixes the duplicated coordinate flip, tracks true per-cell scan
times, uses bounded reliable transport for registered world clouds, and
separates point ingestion from periodic callbacks. Periodic TF lookups do not
wait for old scans. A complete map copy/mutation is locked, while TF waits and
ROS serialization happen outside that lock. Four executor workers serve
TF, scans, maintenance timers and the separate map publication group. A busy
maintenance callback no longer blocks publication merely by occupying its
callback group; actual map access still uses the coherent snapshot lock.
The trial publishes height, variance and observation age, omitting the unused
CuPy traversability output (the HT directional output remains authoritative).
On shutdown the worker pool is joined before node destruction.

Map headers carry the last successfully integrated scan's timestamp, so an
idle publishing timer cannot disguise stale perception as a fresh map.
Raw sensor subscribers retain best-effort compatibility unless their profile
explicitly requests reliable transport. `qos_reliability` and `queue_depth`
are per-subscriber options; the supplied profile is for CMU registered clouds.

The core GPU tests cover real world coordinates through ROS serialization,
true observation ages, map shifts, rejected outliers, repeated publications
and nonblocking pose timers. The HT-side tests cover multiple surfaces,
unknown handling, preserved posts/steps, ramp selection and world indexing.

Generated bags and videos stay local in `presentations/scheduled_results`.
Run a fresh current-HT Garage trial and render its actual published XYθ path:

```bash
python3 presentations/run_ht_validation.py --duration 180
```

Set `HT_SIM_WS` and `HT_CUPY_WS` if those independent workspaces are located
elsewhere. The current-HT validation does not require the original TARE
baseline workspace. Original-vs-current comparison does require that baseline.
