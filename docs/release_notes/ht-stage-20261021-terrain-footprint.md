# 阶段45：已知障碍足迹反馈与室内复测

## 改了什么

把既有车体已知障碍门禁反馈给原TARE地形聚合与精确位置查询，修复暂缺HT预测时旧可行历史未失效的问题。保留未知探索引导与严格路径执行，原TSP/访问顺序、模型/滤波/0.5阈值、车体尺寸、搜索预算和速度不变。

## 实现了什么功能

原TARE地形提示避免选择已知车体足迹碰到墙的中心；HT仍在XYθ空间为其指定航点找完整可执行路线。不把未知引导当行驶许可，不证明全局SE2连通。

## 实验与验证

实测冻结`15e197eca16bee3dea1fcd3870a05ee84f2ecd12`，室内采集状态RECORDED，实测600.0s，169.14m / 3625.625m³，末任务BLOCKED。四CTest50.65s、六函数SHA通过；旧代码失败反例和中途缺测历史反例均保留。

[同室内阶段44→45比较图、报告和视频](https://github.com/CQULzz/HT_Explo/blob/codex/ht8dir-v1/docs/results/ht_known_body_terrain_10min_2026-10-21/REPORT.md)。每版本单次闭环，采样自由体积并集不是实际覆盖真值。完整已录数据以stage45.json远端大小与SHA回执为准，非全频原始传感器无损录制。

## 存在什么问题

- 室内末状态BLOCKED，仍有路线问题
- 最长完全停车65.060s，结合任务状态判断
- 森林8000次展开上限与隧道53s结束线索本轮未复测，不能宣称已解决
- 单次600s不证明所有环境、长时运行或真实车辆稳定；无新增同限制原版TARE配对

<!-- repository-catalog-start -->
## 代码、视频与完整数据的对应关系

- [阶段45完整索引：实际实验候选、导航代码、报告、视频及数据回执](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/catalog/stage-45.md)
- [本阶段归档源码](https://github.com/CQULzz/HT_Explo/tree/15e197eca16bee3dea1fcd3870a05ee84f2ecd12)：`15e197eca16bee3dea1fcd3870a05ee84f2ecd12`。这是归档锚点；实际测量源码、运行patch与二进制哈希以原清单为准。
- [完整实验总目录](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/catalog/INDEX.md) · [分支和标签规则](https://github.com/CQULzz/HT_Explo/blob/main/docs/REPOSITORY_GUIDE.md)

早期历史目录只关联到研究阶段，未知测量提交保持待确认；补充回放视频不代表新的导航实验。原有报告、失败记录与全部附件保留。
<!-- repository-catalog-end -->
