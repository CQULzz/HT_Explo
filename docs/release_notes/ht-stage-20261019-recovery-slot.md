# 阶段33｜普通恢复目标提前搜索，完整600秒

## 改了什么

首个主要目标后安排首个普通恢复目标，避免主要目标超时一直挤掉恢复。已有正收益路线则跳过恢复，已承诺目标成功仍优先；保留backtrack尾部和既有预留。HT、物理几何、速度、0.15秒单目标与0.35秒周期配置不改。新头文件纳入冻结清单；实际参数与阶段32一致。

## 实现了什么功能

针对阶段32的482轮调度挤占，恢复目标现在能提前获得搜索机会。旧顺序等价提取版在确定性预算回归中失败，新版通过；全部4个CTest目标通过。单元用例只证明调度机会，不假装重放真实物理可达性。

## 实验与验证

实测ba7942c，室内完整600秒151.57m/2480.000m³，末尾EXPLORING；末分钟15.525m，最后平移指令600.001s，最长全零35.800s。前轮阶段32为5.66m/419.750m³，但较好历史阶段30仍有169.57m/3321.25m³，不能只选最差前轮宣称普遍提升。

“主要全超时且有替代未尝试”周期0轮，前轮482；完整查询与恢复/回退机会记录保留。13项采集核验通过，视频9000帧/600.000000秒完整解码。

[报告、四轮对比、地图、日志与视频](https://github.com/CQULzz/HT_Explo/blob/codex/ht8dir-v1/docs/results/ht_recovery_search_slot_10min_2026-10-19/REPORT.md)。附件保存整轮已录制数据与独立MP4；激光源秒抽样、地图周期快照，不是全部传感器无损录制。

## 存在什么问题

本轮搜索退出{'REACHED': 610, 'TIME_LIMIT': 232, 'EXHAUSTED': 4, 'INVALID_START': 14}，几何查询计时占搜索墙钟93.5%，含调度等待；最大单次搜索0.281605s，原截止检查长尾仍在。地图/路径时效、未连接或暂不可观察任务、独立真值覆盖、同版重复/多环境与实车尚未全部验收，不能称为无缺陷或稳定版本。

<!-- repository-catalog-start -->
## 代码、视频与完整数据的对应关系

- [阶段33完整索引：实际实验候选、导航代码、报告、视频及数据回执](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/catalog/stage-33.md)
- [本阶段归档源码](https://github.com/CQULzz/HT_Explo/tree/ba7942ce176378d68b0eeab99a4f4bb9a5e68913)：`ba7942ce176378d68b0eeab99a4f4bb9a5e68913`。这是归档锚点；实际测量源码、运行patch与二进制哈希以原清单为准。
- [完整实验总目录](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/catalog/INDEX.md) · [分支和标签规则](https://github.com/CQULzz/HT_Explo/blob/main/docs/REPOSITORY_GUIDE.md)

早期历史目录只关联到研究阶段，未知测量提交保持待确认；补充回放视频不代表新的导航实验。原有报告、失败记录与全部附件保留。
<!-- repository-catalog-end -->
