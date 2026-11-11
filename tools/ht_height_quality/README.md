# Coherent elevation quality for HT-only navigation

Independent branch `sim/ht-height-quality-20261111`, parent `1b378f8`.

The mapper now gates height innovations with squared residuals and the combined prior/measurement variance. Protected edge tolerance uses the last accepted observation's standard deviation, so accumulated process uncertainty cannot erase an observed high edge. A rejected scan adds one outlier-variance increment; duplicate returns do not multiply it. The mapper snapshots `observation_variance` with accepted height/time, rolls/clears them together and continues to publish total `variance` independently. The experimental HT entry requires the new layer and rejects missing/malformed input. Existing deployments retain the old decoder default unless explicitly enabled.

HT probability .5, source TTL 1s, support/context/occupied checks, footprint, native TARE, HT-only mode and local recovery speeds are unchanged. No uncertainty sampling of HT scores was added. Legacy CuPy fusion kernels are untouched; this candidate uses the configured deterministic backend only.

The two mapper overrides are installed only onto a hash-verified independent source copy, using `apply_mapper.py`. Base file SHA, full external source inventory and experiment data are retained in `/home/lzz/ht_quality_20261111`. The complete third-party mapper package is not re-vendored into this repository; its MIT license accompanies the overrides.

Validation entry:

```bash
source /home/lzz/ht_quality_20261111/env.sh
/home/lzz/ht_quality_20261111/venv/bin/python -m pytest -q \
  /home/lzz/HT_Explo_quality_20261111/tools/ht_height_quality/test_quality_fix.py
```

55 selected quality/source/pipeline tests pass. One unrelated legacy demand-publication test fails against both the unchanged baseline wrapper and this wrapper; both logs are retained. A historical byte-for-byte model comparison whose archived source is absent from the sparse checkout was deselected; model weights were not changed. The gate binary's 24 boundary/constraint checks pass. Earlier test fixture type/config mistakes and the first missing-build-dependency log are retained.

`replay_arrival.py` uses the original scans at the recorded failed cell, an explicitly stated initial source snapshot and one 5Hz process-variance increment per scan. It is a local GPU diagnostic, not a full mapper-history replay, fresh-perception run or contact simulation. The recorded high surface is retained; variance no longer scales with copies of the scan. See `PLAN.md` for the bounded 300s verification scope. No automatic Release, hardware deployment or raw-data cleanup.
