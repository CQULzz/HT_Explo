# 阶段44：稀疏高程纹理修正与四场景600秒验证

## 改了什么

允许至少两对对称真实观测邻居有限去噪，保护连贯小台阶/窄柱，保留方差权重、最多2cm调整与原未知/障碍门槛。启动及首次TARE运行各45s逐帧保留推理与前端输入以捕获早停；原TARE六函数/TSP、HT权重/归一化/0.5阈值、速度和导航C++未改。

## 实现了什么功能

原TARE决定访问顺序，HT为指定航点提供硬门禁下的XYθ路线；多环境记录与输入诊断可追溯。

## 实验与验证

实测冻结提交`454efa230fae337cfa8f87b2aa87ee9917040621`。69项桥接回归与源数据录制检查、六函数SHA、10项中断/归档回归通过；同一个后续输入重放部分平地分数提高，精确旧触发帧未保存，离线分数变化不等于车辆可达。

| 场景 | 采集 | 实测s | 里程m | 近似观测体积m³ | 末任务 |
|---|---|---:|---:|---:|---|
| indoor | RECORDED | 600.0 | 62.88 | 1849.25 | BLOCKED |
| garage | RECORDED | 600.0 | 224.11 | 9809.375 | EXPLORING |
| forest | RECORDED | 600.0 | 46.32 | 8377.875 | BLOCKED |
| tunnel | RECORDED | 600.0 | 25.62 | 448.875 | COMPLETED |

[报告、图、视频和审计](https://github.com/CQULzz/HT_Explo/blob/codex/ht8dir-v1/docs/results/ht_sparse_height_4scene_10min_2026-10-21/REPORT.md)。室内旧中断记录只比较实际569.501s，车库保留历次完整600s对照，不补齐缺失或把跨场景体积排名。完整MCAP/上下文等以本Release附件及stage44.json大小/SHA校验为准；非全频原始传感器无损录制。

## 存在什么问题

- indoor末状态BLOCKED，不能称探索成功
- indoor记录中5次XYθ搜索达到展开上限，不能据此断言无路
- indoor最长完全停车412.53s，需结合任务/门禁解释
- forest末状态BLOCKED，不能称探索成功
- forest记录中754次XYθ搜索达到展开上限，不能据此断言无路
- forest最长完全停车436.05s，需结合任务/门禁解释
- tunnel最长完全停车529.38s，需结合任务/门禁解释
- tunnel在53.0s采样报告exploration_finished，是否真实全覆盖尚未验证；COMPLETED只表示任务返航条件满足

粗视点地形可行性不等于完整SE2可达性；未知训练噪声分布与低置信厘米孤立物辨识仍有限制。单次轨迹不隔离所有随机因素；无新增同限制原版TARE配对、完整动力学或实车验证。

<!-- repository-catalog-start -->
## 代码、视频与完整数据的对应关系

- [阶段44完整索引：实际实验候选、导航代码、报告、视频及数据回执](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/catalog/stage-44.md)
- [本阶段归档源码](https://github.com/CQULzz/HT_Explo/tree/454efa230fae337cfa8f87b2aa87ee9917040621)：`454efa230fae337cfa8f87b2aa87ee9917040621`。这是归档锚点；实际测量源码、运行patch与二进制哈希以原清单为准。
- [完整实验总目录](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/catalog/INDEX.md) · [分支和标签规则](https://github.com/CQULzz/HT_Explo/blob/main/docs/REPOSITORY_GUIDE.md)

早期历史目录只关联到研究阶段，未知测量提交保持待确认；补充回放视频不代表新的导航实验。原有报告、失败记录与全部附件保留。
<!-- repository-catalog-end -->
