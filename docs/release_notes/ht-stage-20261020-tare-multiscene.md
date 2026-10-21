# 阶段42：原TARE＋HT冻结版本五场景验证

## 改了什么

本轮没有修改导航算法、HT模型、建图融合或运动限制。冻结运行提交`dccfcc93232f0f27f9ae2d63b59ae93c4c1168c4`；72项运行文件/配置/二进制与阶段41导航代码`68701319b333165dd9cd5acf8e226ba52c174434`一致。新增五场景采集、参数与话题隔离检查、路由分工审计、视频、图表和完整数据发布工具。

## 实现了什么功能

沿用原TARE覆盖决策/全局与局部TSP/waypoint，HT在XYθ空间给指定航点找可执行路线；原六函数与ROS2适配参照b6760ad一致。计划场景为车库、校园、室内、森林和隧道，独立起点与高程历史；实际已录场景及中断情况见下表。

## 实验与验证

计划5场景、每组600秒；已获得2组完整且通过检查的记录，其余3组未完成、检查不通过或未启动。 原批次状态为`RUNNING`。实测时长缺失时标未知；最后进度不是最终实测时长。定时采集完成不等于探索成功。

| 场景 | 采集状态 | 实测时长s | 最后进度s | 里程m | 近似观测体积m³ | 末尾任务 | 最长完全停车s | TARE→HT分工检查 |
|---|---|---:|---:|---:|---:|---|---:|---|
| garage | RECORDED | 600.0 | 599.8 | 189.99 | 5299.5 | BLOCKED | 22.132760763168335 | True |
| campus | RECORDED | 600.0 | 600 | 174.32 | 17991.375 | EXPLORING | 1.0991797924041748 | True |
| indoor | FAILED | 未知 | 569.5 | 未知 | 未知 | 未知 | 未知 | 未审计 |
| forest | PENDING | 未知 | 未采到 | 未知 | 未知 | 未知 | 未知 | 未审计 |
| tunnel | PENDING | 未知 | 未采到 | 未知 | 未知 | 未知 | 未知 | 未审计 |

[报告、视频与对比图](https://github.com/CQULzz/HT_Explo/blob/codex/ht8dir-v1/docs/results/ht_tare_native_5scene_10min_2026-10-20/REPORT.md)。原始MCAP和全部已录文件放本Release分卷附件，逐文件清单、资产SHA256和仓库发布回执共同核验；发布是否完成以stage42.json为准。激光按源秒采样，不是全频原始传感器无损录制。

## 存在什么问题

garage:存在超过10秒完全停车，见状态和地形诊断；indoor:未获得完整且通过检查的记录；indoor:分工未通过或缺少执行样本，见审计；forest:未获得完整且通过检查的记录；forest:分工未通过或缺少执行样本，见审计；tunnel:未获得完整且通过检查的记录；tunnel:分工未通过或缺少执行样本，见审计

没有新增同控制约束的原版TARE配对，跨场景体积不可用于算法排名。粗视点图不保证完整SE2可达性；未验证完整轮胎动力学或实车。地图/模型/几何门槛没有为追求体积而放宽。

<!-- repository-catalog-start -->
## 代码、视频与完整数据的对应关系

- [阶段42完整索引：实际实验候选、导航代码、报告、视频及数据回执](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/catalog/stage-42.md)
- [本阶段归档源码](https://github.com/CQULzz/HT_Explo/tree/dccfcc93232f0f27f9ae2d63b59ae93c4c1168c4)：`dccfcc93232f0f27f9ae2d63b59ae93c4c1168c4`。这是归档锚点；实际测量源码、运行patch与二进制哈希以原清单为准。
- [完整实验总目录](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/catalog/INDEX.md) · [分支和标签规则](https://github.com/CQULzz/HT_Explo/blob/main/docs/REPOSITORY_GUIDE.md)

早期历史目录只关联到研究阶段，未知测量提交保持待确认；补充回放视频不代表新的导航实验。原有报告、失败记录与全部附件保留。
<!-- repository-catalog-end -->
