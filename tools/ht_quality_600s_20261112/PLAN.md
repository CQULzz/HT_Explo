# 600-second repeat of the frozen HT height-quality candidate

The user explicitly requested one more 10-minute experiment on 2026-11-12.
Reuse the previous frozen navigation code, mapper, weights, parameters, official
CMU indoor scene, start and 0.5 m/s limits. Check the previous 232-file manifest
before launching. Do not change navigation behavior during this repeat.

Keep the old closed 300s ledger intact. Record to the independent root
`/home/lzz/ht_quality_600s_20261112`; runtime/configuration/installations there
link to the existing frozen candidate. Collect 600 full seconds even if motion
stops or exploration finishes. Plan one successful run; at most two launches,
with the second reserved only for a demonstrated infrastructure failure.

Preserve MCAP, CSV, logs, parameters, manifests and failed attempts. Compare
distance, sampled observed free volume, task state, stop duration and recovery
with the old 600s geometry+HT / HT-only runs and the recent 300s test over its
actual measured interval. Independently audit the exact recorded HT maps and
actual output associations. Save plots and a decodable recorded-trajectory
video. Submit code and compact evidence on the existing independent branch;
no Release, hardware deployment or deletion of unbacked data. Stop afterwards.
