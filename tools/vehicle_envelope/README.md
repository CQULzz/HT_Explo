Opt-in URDF body envelope

`from_urdf.py` derives one base_link-aligned box enclosing the union of visual
and collision geometry in a fixed-joint expanded URDF. The Scout source is
CQULzz/eletranskit_scout@cf0b73d7d01b4b6a2718c7ff3124f4b7a3368c36.
Expand its scout_sensor_rack.urdf.xacro using xacro before running the script.
Mesh paths are resolved through `--package-dir`; unsupported geometry fails.

For the pinned source the bounds are approximately
`[-0.4649301,-0.3497950,-0.2351843]` to
`[0.4649308,0.3497950,0.6502001]` metres in base_link.
These include wheels and sensor-rack visuals, which lack complete collision tags.

Set both localPlanner and pathFollower parameters:

- `ht_use_urdf_envelope: true`
- `ht_body_min_xyz` / `ht_body_max_xyz`: generated bounds, including their offset
- `vehicleLength` / `vehicleWidth`: generated XY size, also matching metadata
- `ht_validity_radius`: at least `required_support_radius` (0.581822302 m here)

`scout_envelope.yaml` provides these scoped overrides for both nodes. Existing
legacy launch configurations are retained for the comparison; opt in explicitly
with this file or the equivalent generated launch parameters.

The Gate checks the rotating XY projection against the raw hard-occupancy map
throughout path, recovery and braking sweeps. Z bounds are recorded, not used to
relax 2D obstacle columns or claim 3D/roll/pitch clearance. The support circle
must enclose the entire new body; HT threshold, unknown policy, map timeout and
controller are unchanged. This is a planning envelope, not a physical contact
simulation or a real-vehicle deployment.

Without the opt-in flag the old configured rectangle is retained.
The experiment harness and full recording live in
`/home/lzz/ht_urdf_compare_20261115`; Windows artifacts are under
`D:/HT-URDF-Compare-20261115`.
