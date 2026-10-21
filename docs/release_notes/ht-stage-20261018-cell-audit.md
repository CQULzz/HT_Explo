# 阶段29｜逐单元证据证明正收益任务被遗漏/提前核销

## 改了什么

增加单元状态转移、收益/候选数、访问/图节点、车位置与HT时戳日志；修复almost_covered的range-for中erase同一vector导致的迭代器失效。覆盖规则、HT/几何门槛和速度未改。本轮仍用于定位完成判据问题，不宣称已经修好。

## 实现了什么功能

可区分收益归零、无候选、未选中进入almost、移出邻域后置COVERED。全部4个CTest目标通过；明确保存两个尚未修正的实际C++状态复现失败，不能把期望断言失败当作通过。

## 实验与验证

实测b601015，完整室内600秒133.17m/2025.125m³，453秒内部结束、517.244秒完成返航；比阶段28体积少约11.7%。5709条单元日志中33个单元有收益却仍UNSEEN，结束时12个最后已记录的收益为正，但部分记录较旧，不当作物理真值。

(24,0)m单元451.695秒还有19个覆盖收益视点/63个前沿收益视点，452.889秒仅因移出邻域从EXPLORING变COVERED，453.023秒触发完成。实际ViewPointManager/GridWorld最小C++复现同时确认：未选中的正收益单元不登记、移出邻域误核销。下一轮修正任务登记/保留语义，保持硬通行门槛。

13项采集检查通过；视频8999帧599.933秒，完整解码并满足600秒时长容差。414份几何样本无既有半径重叠，14次晚HT拒绝全部配对全零；59份模型上下文输出一致，三份重放差0。

[报告、单元转移、失败复现、四轮比较及视频](https://github.com/CQULzz/HT_Explo/blob/codex/ht8dir-v1/docs/results/ht_cell_audit_10min_2026-10-18/REPORT.md)。附件保留整轮录包、日志、周期图、网络上下文、CSV、外部源码和MP4；激光源秒抽样，不是无损全传感器记录。

## 存在什么问题

内部完成不等于全部覆盖；正收益任务登记/核销规则已复现但本轮尚未修正。HT健康年龄最大4.096s，最后执行状态HT_MAP_STALE而mission已COMPLETED、实际保持零；16次PATH_DISCONTINUITY仍待核查。体积不及阶段28/23，不能称性能改善；重复、多环境、真值覆盖、窄通道与动力学未验收。

<!-- repository-catalog-start -->
## 代码、视频与完整数据的对应关系

- [阶段29完整索引：实际实验候选、导航代码、报告、视频及数据回执](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/catalog/stage-29.md)
- [本阶段归档源码](https://github.com/CQULzz/HT_Explo/tree/b6010156cc26431cc23bac33ac543982f7d5e4c1)：`b6010156cc26431cc23bac33ac543982f7d5e4c1`。这是归档锚点；实际测量源码、运行patch与二进制哈希以原清单为准。
- [完整实验总目录](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/catalog/INDEX.md) · [分支和标签规则](https://github.com/CQULzz/HT_Explo/blob/main/docs/REPOSITORY_GUIDE.md)

早期历史目录只关联到研究阶段，未知测量提交保持待确认；补充回放视频不代表新的导航实验。原有报告、失败记录与全部附件保留。
<!-- repository-catalog-end -->
