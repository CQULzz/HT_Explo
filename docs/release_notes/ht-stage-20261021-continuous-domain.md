# 阶段46：连续规划范围解耦与室内复测

## 改了什么

连续XYθ查询改用空间网格/既有高度范围，不再因最近覆盖格非候选而把真实车辆起点判到规划范围外。原TARE覆盖范围函数、六函数/TSP、HT/几何硬门槛、速度和搜索上限不变。

## 实现了什么功能

覆盖视点候选与连续车辆状态分开检查；原TARE决定访问顺序，HT在真实连续位置给指定航点找路线。真正碰撞、禁入区、越界及HT拒绝仍不能通行。

## 实验与验证

实测冻结`07c1abd334f83cb8d602e2234134b4286862c916`，室内采集状态RECORDED，实测600.0s，187.22m / 3934.25m³，末任务EXPLORING。四CTest、六函数SHA通过；空几何/非候选覆盖格的旧代码失败反例保留。

[同室内阶段45→46比较图、报告和视频](https://github.com/CQULzz/HT_Explo/blob/codex/ht8dir-v1/docs/results/ht_continuous_domain_10min_2026-10-21/REPORT.md)。每版本单次闭环，采样自由体积并集不是实际覆盖真值。完整已录数据以stage46.json远端大小与SHA回执为准，非全频原始传感器无损录制。

## 存在什么问题

- 森林8000次展开上限与隧道53s结束线索本轮未复测，不能宣称已解决
- 单次600s不证明所有环境、长时运行或真实车辆稳定；无新增同限制原版TARE配对

<!-- repository-catalog-start -->
## 代码、视频与完整数据的对应关系

- [阶段46完整索引：实际实验候选、导航代码、报告、视频及数据回执](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/catalog/stage-46.md)
- [本阶段归档源码](https://github.com/CQULzz/HT_Explo/tree/07c1abd334f83cb8d602e2234134b4286862c916)：`07c1abd334f83cb8d602e2234134b4286862c916`。这是归档锚点；实际测量源码、运行patch与二进制哈希以原清单为准。
- [完整实验总目录](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/catalog/INDEX.md) · [分支和标签规则](https://github.com/CQULzz/HT_Explo/blob/main/docs/REPOSITORY_GUIDE.md)

早期历史目录只关联到研究阶段，未知测量提交保持待确认；补充回放视频不代表新的导航实验。原有报告、失败记录与全部附件保留。
<!-- repository-catalog-end -->
