# Historical direction verification and performance reuse

## What was already verified

`codex/ht8dir-v1@0574439` contains the historical direction trace, preserved at [evidence/HT_DIRECTION_TRACE_0574439.md](evidence/HT_DIRECTION_TRACE_0574439.md). That investigation traced Scout teacher/student yaw order and image/GridMap axes. Channel order is 0:+X, 1:+X+Y, 2:+Y, 3:-X+Y, 4:-X, 5:-X-Y, 6:-Y, 7:+X-Y. Current hardware configuration retains identity channel order and zero heading offset. Current checkpoint SHA256 is identical to the recorded old weight: 0a79b865d012aa633fbb9913fc4031908dfe188ec9e161ef5a3fbb34a3f8c4d4.

The old branch set ht_directions_calibrated=true to permit user-authorized low-speed trials using that mapping. Its own report explicitly says this was not physical one-direction slope calibration. Flat-ground movement and later best-probability trials cannot establish the eight directional responses on asymmetric terrain. Therefore saying “no direction verification has been done” is inaccurate; code mapping evidence already exists and need not be rediscovered.

The old bridge also experimented with a 0.4825 m front-reference-to-body-center shift. Current code uses configuration semantics and separate physical support/obstacle layers; the later 2026-10-18 configuration-gate report records remaining uncertainty about full label/reference-point reconstruction. Do not blindly add the old shift or rotate channels 180 degrees. Reference position, channel orientation and physical model validity are separate checks. This review does not change calibration flags or authorize motion.

## Performance evidence to reuse

- Historical BLAS/OpenMP control: keep BLAS single-threaded for small plane fits, with separate PyTorch thread selection. Already present; do not multiply threads blindly. See release_notes/ht-stage-20261017-blas-threads.md.
- Historical runtime diagnosis: align source scan/map stamps across mapper queue/TF/lock, map export, DDS, HT callback and publication. See fixes/2026-10-19_garage_latency.md and experiments/next_latency_diagnosis.md. A stale input cannot become fresh through faster network inference, and relabelling its stamp is not a fix.
- Old real-car cadence and map-publication improvements included newest pending work, single coherent GPU->CPU map export and avoiding unused-layer serialization. Equivalent useful pieces have already been applied where compatible. The older simpler/smaller-grid pipeline's 8–9 Hz observations are not end-to-end acceptance for the current historical/physical-support pipeline.
- Current identical-input profile averages roughly 146 ms for two quality-filter calls, 82 ms for historical window selection, 24 ms fusion and 15 ms HT context preparation per frame. Strict-FP32 NCHW network is around 41 ms in the isolated benchmark. Profiling and concurrency add overhead; use per-stage measurements rather than summing unrelated live runs.

## Next candidate priorities

1. Compile or GPU-accelerate the two quality-filter neighborhood kernels, preserving both source-quality rejection and fused-crop denoising. Do not simply remove one call: they serve different inputs/purposes. Test observed/rejected/edge masks, metric heights and threshold decisions on identical captured input and step/hole/post/ramp fixtures.
2. Reduce historical window selection Python/tile gathers using cached geometry/index maps or a compiled mode-selection kernel. Preserve surface references, multimodal floor separation, rejected observations and per-cell expiry. Cache invalidation must include observation, reference/pose and age changes, not merely center XY.
3. Reuse mapper lock/queue instrumentation to measure remaining source-age tails before changing external mapping. Keep measured timestamps and bound memory; no larger TTL as a substitute for reducing latency.
4. Continue latest-input and optional-display serialization work already implemented. Only reduce published fields after checking actual subscribers; physical support/obstacle layers remain required.

Each candidate needs same-input numerical/gate comparison and a stationary live timing check first. 10 Hz requires about 100 ms end to end; the present 380 ms callback needs more than another small scheduling adjustment. These performance checks need no vehicle movement. Physical direction/drive response acceptance, if requested later, requires explicit motion authorization and suitable terrain.
