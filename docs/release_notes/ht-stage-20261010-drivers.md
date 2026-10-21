# 阶段06：Fixposition与Helios32驱动接入

**状态：实验里程碑，不是稳定版；尚未完成实车完整验证。**

归档提交：[d63b9b8](https://github.com/CQULzz/HT_Explo/commit/d63b9b8db2c9aecea20aa2390fc89cfc0fd5ed30)。类型：功能。
实际控制/功能来源：[d63b9b8](https://github.com/CQULzz/HT_Explo/commit/d63b9b8db2c9aecea20aa2390fc89cfc0fd5ed30)。

## 改了什么

将Fixposition、RoboSense驱动源码及依赖纳入本工作区，补实车配置和启动接线。

## 实现了什么功能

提供定位/里程计与Helios32点云输入入口，工作区构建不依赖相邻驱动工作区。

## 实验与验证

源码、配置及构建接线按仓库留档；不是完整实车探索验收。

## 存在什么问题

硬件IP、雷达型号、TF/外参、时间同步、方向标定和底盘控制仍需实车确认；有驱动不等于已能安全实车探索。

## 报告与代码

- [THIRD_PARTY.md](https://github.com/CQULzz/HT_Explo/blob/codex/ht8dir-v1/THIRD_PARTY.md)
- [src/tare_planner/launch/explore_ht_fixposition.launch.py](https://github.com/CQULzz/HT_Explo/blob/codex/ht8dir-v1/src/tare_planner/launch/explore_ht_fixposition.launch.py)
- [src/tare_planner/config/rslidar_helios32.yaml](https://github.com/CQULzz/HT_Explo/blob/codex/ht8dir-v1/src/tare_planner/config/rslidar_helios32.yaml)
- [全部版本对照](https://github.com/CQULzz/HT_Explo/blob/codex/ht8dir-v1/VERSIONS.md#stage-06)
- [该阶段源码](https://github.com/CQULzz/HT_Explo/tree/d63b9b8db2c9aecea20aa2390fc89cfc0fd5ed30)

<!-- repository-catalog-start -->
## 代码、视频与完整数据的对应关系

- [阶段06完整索引：实际实验候选、导航代码、报告、视频及数据回执](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/catalog/stage-06.md)
- [本阶段归档源码](https://github.com/CQULzz/HT_Explo/tree/d63b9b8db2c9aecea20aa2390fc89cfc0fd5ed30)：`d63b9b8db2c9aecea20aa2390fc89cfc0fd5ed30`。这是归档锚点；实际测量源码、运行patch与二进制哈希以原清单为准。
- [完整实验总目录](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/catalog/INDEX.md) · [分支和标签规则](https://github.com/CQULzz/HT_Explo/blob/main/docs/REPOSITORY_GUIDE.md)

早期历史目录只关联到研究阶段，未知测量提交保持待确认；补充回放视频不代表新的导航实验。原有报告、失败记录与全部附件保留。
<!-- repository-catalog-end -->
