# 阶段48：Campus原TARE与HT各600秒

## 改了什么

冻结设施`f7fd77b66fc442752599ead359e8aa60e7773ae4`；HT导航/二进制保持`07c1abd334f83cb8d602e2234134b4286862c916`，原TARE适配基线`b6760adb4280b379567c76f4e684ce628e28ef71`。只扩展实验入口支持campus，没有修导航或调优。

## 实现了什么功能

同一campus原生起点、先原版后HT、各完整600秒；运动上限前进0.5m/s、倒车0.25m/s、角速度0.8rad/s，常规加速度0.5m/s²、1.2rad/s²，明确零运动保持例外。保留原版限幅前后指令、参数、MCAP、相机与实际RViz回放。

## 实验与验证

- 原TARE同运动上限：600秒、223.53m、17048.250m³，末任务EXPLORING，最长零运动指令区间0.500s。
- 当前HT＋原TARE决策：600秒、218.28m、17722.250m³，末任务EXPLORING，最长零运动指令区间0.950s。

采集总体状态：COMPLETED_WITH_ISSUES；失败检查：{'original': ['no_child_lifecycle_exception'], 'ht': ['normal_acceleration']}。
运行时视点网格：{'original': {'number_x': 40, 'number_y': 40, 'resolution_x': 1.2, 'resolution_y': 1.2}, 'ht': {'number_x': 40, 'number_y': 40, 'resolution_x': 1.2, 'resolution_y': 1.2}}。没有沿用室内的网格差异说明。

[多角度曲线、轨迹、参数、视频和限制](https://github.com/CQULzz/HT_Explo/blob/codex/ht8dir-v1/docs/results/ht_tare_campus_matched_10min_2026-10-21/REPORT.md)。

## 存在什么问题

原TARE两CMU节点采后SIGINT退出异常；HT有一次常规角加速度差分审计超限，未修改导航/控制来规避检查。原始日志和相邻控制指令均保留。
单次顺序端到端对照，地形、几何与跟踪器不同；体积为统一源秒射线采样近似，不是真值覆盖率，也不能归因于HT单模块。离线RViz回放不证明原运行实时性。
失败与采后异常照实保留。完整已录数据以docs/experiments/publications/stage48.json的远端大小/SHA回执为准。

<!-- repository-catalog-start -->
## 代码、视频与完整数据的对应关系

- [阶段48完整索引：实际实验候选、导航代码、报告、视频及数据回执](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/catalog/stage-48.md)
- [本阶段归档源码](https://github.com/CQULzz/HT_Explo/tree/f7fd77b66fc442752599ead359e8aa60e7773ae4)：`f7fd77b66fc442752599ead359e8aa60e7773ae4`。这是归档锚点；实际测量源码、运行patch与二进制哈希以原清单为准。
- [完整实验总目录](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/catalog/INDEX.md) · [分支和标签规则](https://github.com/CQULzz/HT_Explo/blob/main/docs/REPOSITORY_GUIDE.md)

早期历史目录只关联到研究阶段，未知测量提交保持待确认；补充回放视频不代表新的导航实验。原有报告、失败记录与全部附件保留。
<!-- repository-catalog-end -->
