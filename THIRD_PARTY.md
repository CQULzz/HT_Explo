# Vendored ROS 2 drivers

These source snapshots live in this workspace's `src/` and are built into
`install_standalone/`. Keep the license files in each source directory.

| Directory | Upstream | Revision | License |
| --- | --- | --- | --- |
| `src/fixposition_driver` | https://github.com/fixposition/fixposition_driver | `4e73ba8dec448d565f14c57d1a336f18b5a32981` | MIT |
| `src/fixposition_driver/fixposition-sdk` | https://github.com/fixposition/fixposition-sdk | `ecb0b9cefa80722a98da3634a635fc5a55e6f423` | see bundled license |
| `src/rslidar_sdk` | https://github.com/RoboSense-LiDAR/rslidar_sdk | `8b4b4b7ff910799260347821084c59e1c73d50d5` | 3-clause BSD |
| `src/rslidar_sdk/src/rs_driver` | https://github.com/RoboSense-LiDAR/rs_driver | `897b14d3bdb6186a75df27ba51b65b5bd5557723` | see bundled license |
| `src/rslidar_msg` | https://github.com/RoboSense-LiDAR/rslidar_msg | `fe8a95cb242bd294cc3d5e3422f2093fb49a56ee` | 3-clause BSD |

The Fixposition SDK's top-level `CMakeLists.txt` was renamed to
`CMakeLists.txt.colcon-disabled` and ROS 1/example directories have
`COLCON_IGNORE` files, following the upstream ROS 2 setup script. This keeps
colcon focused on the eight ROS 2 packages used here.
