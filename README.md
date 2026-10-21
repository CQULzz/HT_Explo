# HT_Explo：TARE探索决策＋HT地形与XYθ路线

本仓库包含**完整探索源码**。TARE负责覆盖、TSP访问顺序和当前航点选择；HT方向可通过性作为硬约束，在`(x,y,θ)`空间规划从里程计位姿到当前航点的路线，再由独立跟踪器执行。视频播放脚本只是辅助工具。

当前为研究原型。最近已完整归档的导航代码是`07c1abd`，阶段47室内、48校园分别做了原TARE与HT各600秒对照；仍有检查失败及场景限制，不能称为实车稳定版。`develop`另有输入校验候选，**没有完整600秒验收**，不能把旧视频当成它的运行结果。

开发候选新增了实车接口、扫描时刻匹配、实际指令间隔限幅与跳变/时钟回退停用；仅离线通过，见[评估与修正报告](validation/real_vehicle_offline_fix_2026-10-22/REPORT.md)。用户已确认外部配准与标定存在，实际总launch/TF待补。

[版本改动与已知问题](VERSIONS.md) · [全部实验、视频和原始数据](docs/experiments/catalog/INDEX.md) · [分支/标签规则](docs/REPOSITORY_GUIDE.md)

## 代码在哪里

| 功能 | 源码入口 |
|---|---|
| TARE探索主流程、当前航点与HT路由衔接 | [tare_waypoint_router.cpp](src/tare_planner/src/sensor_coverage_planner/tare_waypoint_router.cpp) / [tare_original.cpp](src/tare_planner/src/sensor_coverage_planner/tare_original.cpp) |
| 原TARE局部覆盖与访问顺序、TSP求解 | [局部覆盖](src/tare_planner/src/local_coverage_planner/tare_original.cpp) / [TSP](src/tare_planner/src/tsp_solver/tsp_solver.cpp) |
| XYθ搜索及车辆运动约束 | [xytheta_planner.h](src/tare_planner/include/ht_cost/xytheta_planner.h) / [ht_route.cpp](src/tare_planner/src/local_coverage_planner/ht_route.cpp) |
| HT地图、方向和足迹硬约束 | [ht_cost_map.cpp](src/tare_planner/src/ht_cost/ht_cost_map.cpp) |
| 路线跟踪与速度指令 | [xytheta_follower.cpp](src/tare_planner/src/ht_cost/xytheta_follower.cpp) |
| 历史高程融合、HT推理与模型权重 | [cupy_to_ht.py](tools/ht_cupy_bridge/cupy_to_ht.py) / [model.py](tools/ht_cupy_bridge/model.py) / [权重](tools/ht_cupy_bridge/student_best_epoch_weights.pth) |
| ROS启动与参数 | [HT入口](src/tare_planner/launch/explore_ht.launch.py) / [参数](src/tare_planner/config/ht.yaml) |
| Fixposition与速腾雷达驱动 | [fixposition_driver](src/fixposition_driver) / [rslidar_sdk](src/rslidar_sdk) |

## 分支选择

| 分支 | 用途 | 验证范围 |
|---|---|---|
| [`main`](https://github.com/CQULzz/HT_Explo/tree/main) | 默认入口；已完成实验归档的导航基线、报告与回放工具 | 导航沿用`07c1abd`；看阶段47/48具体限制 |
| [`develop`](https://github.com/CQULzz/HT_Explo/tree/develop) | 输入校验、实车接口及执行时序候选，附离线审查记录 | 离线检查；600秒仿真未验收 |
| [`visualization/xytheta`](https://github.com/CQULzz/HT_Explo/tree/visualization/xytheta) | 半透明体素回放及八方向数值审计 | 重放阶段48已有数据，没有新导航实验 |

旧`codex/*`分支和全部48个阶段标签保留以兼容历史链接；新开发使用`develop`，导航与可视化里程碑分别用`nav/*`、`viz/*`。每个分支均是完整仓库快照，区别在于改动范围。

## 最近的实验与视频

| 实验 | 导航代码 | 资料 |
|---|---|---|
| 阶段48：Campus，原TARE/HT各600秒 | HT `07c1abd`；实验入口 `f7fd77b` | [代码、报告、所有视频、完整录包](docs/experiments/catalog/stage-48.md) |
| 阶段47：室内，原TARE/HT各600秒 | HT `07c1abd`；实验入口 `1ded85a` | [代码、报告、所有视频、完整录包](docs/experiments/catalog/stage-47.md) |
| 阶段48半透明体素补充 | 回放代码 `13b46a9`；数据仍来自阶段48 | [说明与八方向图](docs/results/ht_xytheta_transparent_voxels_2026-10-22/REPORT.md) / [视频下载](https://github.com/CQULzz/HT_Explo/releases/download/ht-stage-20261021-campus-matched/stage48-xytheta-transparent-voxels-4x.mp4) |

历史资料按阶段统一登记：48个阶段、62个早期目录及其包内视频见[总索引](docs/experiments/catalog/INDEX.md)。归档提交、实际实验候选、导航提交分别记录；未知版本不会强行配对。大录包和视频主要在GitHub Release附件，不能只看Git目录判断是否已上传。

## 构建与复核入口

已有验证环境为Ubuntu 24.04 / ROS 2 Jazzy；独立工作区构建脚本：

```bash
bash scripts/build_standalone.sh
source /opt/ros/jazzy/setup.bash
source install_standalone/setup.bash
python3 scripts/check_tare_waypoint_contract.py
python3 scripts/build_repository_catalog.py --check
```

构建仍需对应系统依赖；CMU仿真和CuPy高程建图属于独立工作区，并非只运行TARE节点就自动具备完整输入链。启动与依赖细节见[已有构建验证](VALIDATION.md)、[HT桥接说明](tools/ht_cupy_bridge/README.md)及[实验复现入口](docs/REPOSITORY_GUIDE.md)。

[原README完整历史副本](docs/history/README_before_repository_organization_2026-10-22.md) · [原版本页历史副本](docs/history/VERSIONS_before_repository_organization_2026-10-22.md) · [实验要求](AGENTS.md)

基于[CMU原版TARE](https://github.com/caochao39/tare_planner)研究框架扩展；原项目说明与引用保留在上述历史副本中。
