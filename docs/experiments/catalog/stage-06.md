# 阶段06：Fixposition与Helios32驱动接入

[返回总索引](INDEX.md)

- 阶段标签：[`ht-stage-20261010-drivers`](https://github.com/CQULzz/HT_Explo/tree/ht-stage-20261010-drivers)。
- 归档标签提交：[`d63b9b8db2c9aecea20aa2390fc89cfc0fd5ed30`](https://github.com/CQULzz/HT_Explo/commit/d63b9b8db2c9aecea20aa2390fc89cfc0fd5ed30)。
- 记录的实验候选：现代发布回执无记录；查下方原始清单，待确认。
- [GitHub Release：完整数据及附件](https://github.com/CQULzz/HT_Explo/releases/tag/ht-stage-20261010-drivers)。

归档提交、实验设施提交与实际导航代码可能不同。运行时源码快照、补丁、参数及二进制哈希以原实验清单为准；视频不是另一个代码版本的验收证据。

## 改动及实现

将Fixposition、RoboSense驱动源码及依赖纳入本工作区，补实车配置和启动接线。

提供定位/里程计与Helios32点云输入入口，工作区构建不依赖相邻驱动工作区。

## 验证与剩余问题

源码、配置及构建接线按仓库留档；不是完整实车探索验收。

硬件IP、雷达型号、TF/外参、时间同步、方向标定和底盘控制仍需实车确认；有驱动不等于已能安全实车探索。

## 报告及版本证据

- [THIRD_PARTY.md](https://github.com/CQULzz/HT_Explo/blob/main/THIRD_PARTY.md)
- [src/tare_planner/launch/explore_ht_fixposition.launch.py](https://github.com/CQULzz/HT_Explo/blob/main/src/tare_planner/launch/explore_ht_fixposition.launch.py)
- [src/tare_planner/config/rslidar_helios32.yaml](https://github.com/CQULzz/HT_Explo/blob/main/src/tare_planner/config/rslidar_helios32.yaml)
- 原版本总表记录的控制提交：`d63b9b8db2c9aecea20aa2390fc89cfc0fd5ed30`。这是历史字段，不能替代运行时快照/补丁核对。

## 可直接下载的视频

本Release没有独立视频附件；请查历史目录内的视频及原报告。

## 完整数据及上传回执

没有对应上传回执；不能据此宣称存在完整录包。

完整附件名、大小、SHA256、下载URL见[index.json](index.json)中本阶段的`release_assets`；历史分片按`content_key`分组，不能把同一Release内不同目录的分片混合。

## 早期历史目录与包内视频

以下为研究阶段关联，不保证阶段标签等于实际测量源码。没有提交记录的保持待确认；下载匹配的归档包后按包内路径查找视频。

无早期历史目录关联。
