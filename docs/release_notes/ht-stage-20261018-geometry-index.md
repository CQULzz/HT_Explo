# 阶段27｜等价碰撞查询提速，末段仍几何拒绝起点

## 改了什么

固定高度先筛选再建XY索引，不同高度/边界回退原3D查询；安全距离、HT阈值、速度、动作和搜索预算不变。新增逐目标搜索终止原因、拒绝与耗时分项；可靠录制实际碰撞点云和视点。

## 实现了什么功能

6561个真实点云查询重复3次与旧输出一致；800组高度/半径边界对照、全部CTest通过。静态查询微基准3.68倍，仅代表该查询耗时。能区分无效起点、耗尽、时间/展开上限。

## 实验与验证

室内同起点完整600秒41.90m、815.625m³，最终BLOCKED；比上轮116.15m/1258m³退步，不能宣称整体提升。最后移动136.501秒，最后60秒480次搜索全部几何拒绝起点/展开0。第一份安全半径重叠约136.426秒，距障碍0.63736m，小于既有0.641421m。

13项采集检查通过；视频实际8999帧、599.933秒，完整解码通过并满足600秒约定容差。[视频帧数更正](https://github.com/CQULzz/HT_Explo/blob/codex/ht8dir-v1/docs/experiments/ERRATA.md)。59份模型上下文与发布图同源逐值相同，三份冻结模型重算差0。HT年龄抽样最大3.399秒。

[完整报告、轨迹/边界图、四轮比较与视频](https://github.com/CQULzz/HT_Explo/blob/codex/ht8dir-v1/docs/results/ht_geometry_index_10min_2026-10-18/REPORT.md)。附件含整轮已录制数据、精选结果、校验清单及独立MP4。激光源秒抽样，不是全传感器无损采集。实测代码4721764。

## 存在什么问题

仍停滞，实际执行进入几何安全边界而HT允许。最近路线对前一份点云只有约8mm余量，实际横向偏差约12mm；规划器检查几何+HT，控制器只检查HT。录包关联不能单独区分控制偏差、观测变化和时延，不能把半径重叠说成车身接触。下一轮对齐规划/执行约束并留跟踪余量，仍不放行碰撞根状态。建图长尾、收益不足、多环境和动力学验收未解决。

<!-- repository-catalog-start -->
## 代码、视频与完整数据的对应关系

- [阶段27完整索引：实际实验候选、导航代码、报告、视频及数据回执](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/catalog/stage-27.md)
- [本阶段归档源码](https://github.com/CQULzz/HT_Explo/tree/4721764fa77eb634f4a0ba50b1381a05b3790195)：`4721764fa77eb634f4a0ba50b1381a05b3790195`。这是归档锚点；实际测量源码、运行patch与二进制哈希以原清单为准。
- [完整实验总目录](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/catalog/INDEX.md) · [分支和标签规则](https://github.com/CQULzz/HT_Explo/blob/main/docs/REPOSITORY_GUIDE.md)

早期历史目录只关联到研究阶段，未知测量提交保持待确认；补充回放视频不代表新的导航实验。原有报告、失败记录与全部附件保留。
<!-- repository-catalog-end -->
