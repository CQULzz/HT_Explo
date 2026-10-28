#!/usr/bin/env bash
# Explicit offline reproduction; replace exported paths with extracted inputs.
# Does not start drivers, simulation, command publishers or controllers.
set -eo pipefail
: "${HT_REPLAY_REPO:?Set to the independent HT workspace}"
: "${HT_REPLAY_OUTPUT:?Set to a completely new output directory}"
: "${HT_REPLAY_RAW:?Set to raw_inputs/selected_raw_inputs.pkl.gz from this Release}"
: "${HT_REPLAY_CUPY:?Set to independent elevation_mapping_cupy package directory}"
: "${HT_REPLAY_PYTHON:?Set to the CUDA-enabled Python executable}"
cd "$HT_REPLAY_REPO"
source scripts/source_real_scout.sh
export ROS_DOMAIN_ID=182 ROS_LOCALHOST_ONLY=1 RMW_IMPLEMENTATION=rmw_fastrtps_cpp
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=4
export PYTHONPATH="$PWD/src/ht_scout_bridge:$PWD/tools/ht_cupy_bridge:$HT_REPLAY_CUPY/script:${PYTHONPATH:-}"
# The archived environment report records the required CUDA runtime/NVRTC libs.
mkdir "$HT_REPLAY_OUTPUT"
git rev-parse HEAD > "$HT_REPLAY_OUTPUT/CHECKOUT.txt"
"$HT_REPLAY_PYTHON" tools/check_ht_compute.py --require-cuda --cupy --require-numba
"$HT_REPLAY_PYTHON" docs/results/real_round2_2026-10-28/rebuild_cupy_maps.py \
  --input "$HT_REPLAY_RAW" --package-dir "$HT_REPLAY_CUPY" \
  --output "$HT_REPLAY_OUTPUT/cupy_rebuild"
for ht_replay_variant in before after; do
  "$HT_REPLAY_PYTHON" docs/results/real_round2_2026-10-28/experiment.py --stage ht \
    --archive "$HT_REPLAY_REPO" --input "$HT_REPLAY_OUTPUT/cupy_rebuild/${ht_replay_variant}_native_maps.pkl" \
    --device cuda --quality-backend numba --commit "$(git rev-parse HEAD)" \
    --output "$HT_REPLAY_OUTPUT/ht_${ht_replay_variant}"
  python3 tools/ht_cupy_bridge/prepare_xytheta_replay.py \
    --maps "$HT_REPLAY_OUTPUT/ht_${ht_replay_variant}/maps" \
    --output "$HT_REPLAY_OUTPUT/planner_input_${ht_replay_variant}" --frame-stride 1
  build_real/tare_planner/ht_xytheta_offline \
    --batch "$HT_REPLAY_OUTPUT/planner_input_${ht_replay_variant}/queries.tsv" \
    --output "$HT_REPLAY_OUTPUT/${ht_replay_variant}.json"
done
# Repeated CuPy results are not guaranteed identical: see same-filter control.
# Old archived absolute map paths in JSON/index files require relocation before
# analysing archived CDR directly. Recompute preparation above writes new paths.
