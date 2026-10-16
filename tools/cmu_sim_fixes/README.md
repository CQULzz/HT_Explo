# Independent CMU shutdown fix

Apply `clean_shutdown.patch` inside the separate CMU checkout at the base
commit recorded in `manifest.json`, then build `vehicle_simulator`,
`terrain_analysis`, `terrain_analysis_ext` and `sensor_scan_generation` in that workspace.
The three 100/200 Hz loops now reuse an executor created before their loop.
All four nodes treat signals as stop requests, destroy their publishers and
TF entities with a valid ROS context, then shut down the context explicitly.
They no longer create guard conditions every iteration with `spin_some(node)`;
that construction could race ROS context shutdown on SIGINT.

The HT trial harness sends SIGINT only to a `ros2 launch` parent, which forwards
it to its children. For `ros2 run` it signals the group because that wrapper does
not forward SIGINT. `current/shutdown.json` records signals, return codes and
any forced escalation. Existing unrelated CMU workspace changes are excluded.
