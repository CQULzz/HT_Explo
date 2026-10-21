# 阶段43：原TARE路线短前缀补搜

## 改了什么

修正固定1/2/3/4米局部终点漏掉同分支短可行段的问题；保留原快速路径，失败后细采样、排除后方锚点，仍共享0.35秒预算。修复中断记录/发布及第四组图表遗漏；不改原TARE六函数、TSP、waypoint访问顺序、HT门槛、模型或运动上限。

## 实现了什么功能

原TARE指定目标，HT在XYθ中给同一原生分支的局部段找完整可执行路径。终点允许不能代替HT扫掠、几何和车辆运动检查。实测代码`d7e0741c1aeeb65f4c0ff404521a4c54f992a330`。

## 实验与验证

车库完整600秒：191.25m / 7013.625m³ / 末状态EXPLORING。补搜尝试0次、成功0次、短于1米成功0次。四组CTest、六函数SHA、10项记录流程回归，以及13项采集检查与完整视频解码通过。

[报告、同场景对比图和视频](https://github.com/CQULzz/HT_Explo/blob/codex/ht8dir-v1/docs/results/ht_tare_short_prefix_10min_2026-10-21/REPORT.md)。完整MCAP/快照等以本Release分卷与stage43.json远端大小/SHA回执为准，不是全频原始传感器无损录制。

## 存在什么问题

路由保持停车0周期，规划P950.432s；实际末状态EXPLORING，不能用采集成功冒充探索成功。单次闭环不是统计证明；短步推进和预算耗尽仍有限制。

室内HT平地低分切断候选连通的问题只做证据诊断，尚未在线修复；未提高速度或放宽分数补体积。没有新原版TARE同限制配对或实车验证。

<!-- repository-catalog-start -->
## 代码、视频与完整数据的对应关系

- [阶段43完整索引：实际实验候选、导航代码、报告、视频及数据回执](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/catalog/stage-43.md)
- [本阶段归档源码](https://github.com/CQULzz/HT_Explo/tree/d7e0741c1aeeb65f4c0ff404521a4c54f992a330)：`d7e0741c1aeeb65f4c0ff404521a4c54f992a330`。这是归档锚点；实际测量源码、运行patch与二进制哈希以原清单为准。
- [完整实验总目录](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/catalog/INDEX.md) · [分支和标签规则](https://github.com/CQULzz/HT_Explo/blob/main/docs/REPOSITORY_GUIDE.md)

早期历史目录只关联到研究阶段，未知测量提交保持待确认；补充回放视频不代表新的导航实验。原有报告、失败记录与全部附件保留。
<!-- repository-catalog-end -->
