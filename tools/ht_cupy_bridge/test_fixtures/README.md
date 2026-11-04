# Recorded floor/reference regression

pcd_surface_260s.npz contains the original source height, variance, age and evidence flags cropped from the source260.0s /ht_real/ht_evidence message in the 2026-11-05 recorded-PCD baseline simulation. The fixture also stores the same-stamp simulated base_link height/XY and map geometry. It contains measured posterior data, not simulator truth inserted into mapping.

The independently checked133-cell diagnostic body-box subset was classified stale_off_surface;132 cells match the immutable scene floor mesh within4.55mm. The new estimator rejects that mixed-height plane fit (RMS>2.5cm) and retains existing compatible measured history using its calibrated-height reference. Actual holes remain unobserved; timestamps are unchanged. See the experiment report and full MCAP release assets for provenance.

Original evidence: /home/lzz/HT_pcd_sim_20261105/baseline_600s/bag/bag_0.mcap, source260000000000ns. This is a local diagnostic crop, not an exact replay of every historical plane-estimator state.
