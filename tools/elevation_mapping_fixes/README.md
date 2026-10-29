# Independent CuPy mapping patches

HT and CuPy retain separate source, build and install trees. The installer
supports the upstream commit recorded in `manifest.json` and applies two ordered
stages:

1. `cupy_ht_mapping.patch`: coordinate export, actual accepted-observation age,
   scan/TF/publication scheduling and cloud QoS corrections.
2. `deterministic_fusion.patch`: immutable-prior point decisions, ordered GPU
   reductions and separately committed visibility cleanup. The four candidate
   file hashes are recorded in `deterministic_manifest.json`.

```bash
source /opt/ros/jazzy/setup.bash
python3 tools/install_elevation_fixes.py --workspace /path/to/independent_cupy_ws
# Add --build only when the independent workspace build is wanted.
```

The checkout must be at
`<workspace>/src/elevation_mapping_cupy_2204` and contain the recorded upstream
Git commit. The installer does not clone, reset, force-checkout or overwrite
unknown edits. It first builds the complete upstream → base → stable sequence
in a temporary directory, validates the final hashes, and compares every managed
file with the three supported complete states. A clean upstream checkout, an
exact base-patched checkout and an already stable checkout are supported. Mixed
stages or other edits to managed files fail before any source/config writes.
Unrelated files are preserved. Repeating a successful install changes no files.
Write failures restore files already written during that invocation.

The generated `config/trial_core.yaml` uses the actual independent package path
`elevation_mapping_cupy/config/core/weights.dat`; ROS 1 `rospack` substitution is
not used. It explicitly enables deterministic fusion. Previously generated
known configs can migrate; modified trial configs are preserved and cause
preflight failure instead of being silently replaced. `--build` runs only
`colcon build --packages-select elevation_mapping_cupy` after installation; a
build failure leaves the verified sources installed and is reported as failure.
The installer never launches ROS nodes, simulation, vehicle drivers or control.

The stable backend retains legacy thresholds and the Gaussian batch-update
contract, but replaces formerly racy execution with defined staged semantics.
Point acceptance reads one prior map; candidates are reduced in original point
order. Rays read a fixed post-integration map and use deterministic reductions,
including an explicit upper-bound minimum. Visibility cleanup remains enabled
when requested by the mapping profile. This is not bit equivalence to an
arbitrary previous GPU schedule. It also restores FP32 geometry: legacy GPU
helpers implicitly converted coordinates, rotation entries and rays to actual
half precision. Ordered sums use FP64 before FP32 map storage. These precision
changes are part of the candidate and are recorded in the experiment, rather
than described as a mere scheduling change. Legacy fusion remains available by setting
`enable_deterministic_fusion: false`; the real Scout mapper profile explicitly
selects `true`. No HT probability threshold is reduced.

The base patch keeps per-cell observation timestamps separate from the legacy
elapsed-time layer. Rejected returns, retained cells, visibility rays and idle
map publication cannot renew direct observation age. Map headers retain the
last successfully integrated scan timestamp. Raw point-cloud subscribers retain
best-effort compatibility unless the independent profile requests reliable
transport; registered geometry-filtered sensor-frame clouds use the supplied
reliable profile.

The CUDA regression tests cover analytic Gaussian/drift expectations, repeated
state bits, unknown/source-age behavior, stale-obstacle cleanup and preservation
of actual flat ground, steps and fresh wall hits. They do not establish ARM
performance, physical calibration or vehicle closed-loop readiness. Full
recorded-input repeatability and planning results belong to the separately
frozen experiment report; do not infer them from synthetic tests.

CPU-only installer regression:

```bash
python3 -m pytest -q tools/test_install_elevation_fixes.py
```

## Optional scan-to-map surface registration candidate

The 2026-10-29 recorded-data audit found millimetre residuals within individual
ground scans but centimetre discrepancies when repeated observations were
transformed to the same world cells. This is inconsistent registration across
frames, not evidence that the physical floor developed new small obstacles.
It does not identify Fixposition, TF timing, mounting motion or another upstream
component as the sole physical cause.

An explicit third stage installs `surface_registration.patch`:

```bash
python3 tools/install_elevation_fixes.py --workspace /path/to/independent_cupy_ws --surface-registration
```

It estimates one bounded rigid Z/tilt correction from recent, observed, locally
continuous scan-to-map overlap. A spatial subset is withheld from fitting and
checks the actual rigid transform before acceptance. Insufficient overlap,
stale/unknown references, large corrections and lack of improvement retain the
original pose. No HT score, threshold, output colour or assumed vehicle passage
enters the fit. The algorithm does not smooth the height raster, fill holes,
change odometry/TF or reduce measurement variance. Parameters in
`RegistrationConfig` are engineering bounds, not measured calibration errors.

The mapper default remains disabled. The explicit installer flag enables it in
the independent trial core. The separate HT profile
`src/ht_scout_bridge/config/mapper_surface_registered.yaml` enables the candidate;
`mapper_for_ht.yaml` remains unchanged. Do not interpret this offline candidate
as physical localization calibration or real vehicle acceptance: the external
registered-scan/TF chain is not rewritten by it. The two recorded clips cannot
establish ARM timing or safe closed-loop motion. A frame-wide moving platform
or a coherent wrong reference may be ambiguous with pose error.

Recorded-input verification uses the unchanged original profile unless the
replay explicitly requests the candidate:

```bash
python3 tools/ht_cupy_bridge/replay_newbags_rviz.py --bag /path/to/bag \
  --output /path/to/new-output --cupy-package /path/to/independent/package \
  --surface-registration
```

The installer still refuses unknown edits before writes. It accepts upstream,
base, stable, and already surface-registered complete states when requested;
omitting the flag cannot silently downgrade an installed surface candidate.

## Optional publication-demand performance patch (2026-10-30)

Install the base/stable (or explicit surface candidate) first. Then use the
separate, publication-only mode:

```bash
python3 tools/install_elevation_fixes.py --workspace /path/to/independent_cupy_ws --publication-performance
```

This mode checks the exact known ROS-wrapper hash, stages and verifies
`publication_performance.patch`, and changes only that wrapper. Existing fusion
sources and every trial config stay byte-for-byte unchanged; it does not enable
surface registration. Unknown wrapper edits are refused before writes, repeated
installation is a no-op, and write failures restore the original bytes. Do not
combine this flag with `--surface-registration` or run an older installer over
the new wrapper; unsupported mixed stages are deliberately refused.

With no subscribers, a normal live publisher returns before acquiring map
locks, running output plugins or copying GPU layers. Subsequent subscribers get
a fresh coherent map on a later timer tick. Offline preloaded playback retains
unconditional publication by default; each publisher config can explicitly set
`publish_without_subscribers: true` for recording/capture. Direct offline capture
proxies without a subscription-count interface retain their prior behavior.
Counts are included in `publication_skipped_no_subscribers` when processing
statistics are enabled. Equal source timestamps are not deduplicated: variance
and crop geometry may still change. All necessary output/age semantics remain.

Build this package in the independent workspace's existing build/install roots.
This task uses `--build-base build_stable --install-base install_stable`; it does
not copy CuPy source into HT/src or copy x86 binaries/caches to Jetson. Source,
byte-parity checks and timing limits are in
`docs/results/real_input_pipeline_2026-10-30/REPORT.md`.

Its compact fixture contains actual tracked files extracted with
`git show 88f4c0...:path`; provenance and SHA256 are inside the archive. Each test
creates a temporary minimal Git repository, so running it cannot alter the
independent working checkout.
