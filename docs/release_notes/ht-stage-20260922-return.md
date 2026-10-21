# 阶段05：起点先验、降级预算与返航状态

**状态：实验里程碑，不是稳定版；尚未完成实车完整验证。**

归档提交：[29f80bc](https://github.com/CQULzz/HT_Explo/commit/29f80bc76789a7075f4dfb987cb2e51bfbb56add)。类型：功能。
实际控制/功能来源：[b847710](https://github.com/CQULzz/HT_Explo/commit/b8477101476bfbff09c97f22190fa0c7c40ee54c)。

## 改了什么

固定起点并限制缺测先验，累计未知降级预算；补任务状态、到家停车确认、返航拼接和单调检查点。

## 实现了什么功能

区分探索结束与真正返航完成；地图故障时停车，恢复后继续；提供可复用回归验证。

## 实验与验证

限定山地小场景中一组基线/HT均到家完成；另有地图暂停6秒恢复检查。

## 存在什么问题

小样本且HT运行有约52秒几何降级，不能称为纯HT或全域完成；仍是软风险代价与CMU控制器，非当前XYθ。

## 报告与代码

- [docs/HT_TARE_REMEDIATION_IMPLEMENTED.md](https://github.com/CQULzz/HT_Explo/blob/codex/ht8dir-v1/docs/HT_TARE_REMEDIATION_IMPLEMENTED.md)
- [experiments/results/remediation_stock_20260922/REPORT.md](https://github.com/CQULzz/HT_Explo/blob/codex/ht8dir-v1/experiments/results/remediation_stock_20260922/REPORT.md)
- [experiments/results/remediation_map_outage_20260922/REPORT.md](https://github.com/CQULzz/HT_Explo/blob/codex/ht8dir-v1/experiments/results/remediation_map_outage_20260922/REPORT.md)
- [全部版本对照](https://github.com/CQULzz/HT_Explo/blob/codex/ht8dir-v1/VERSIONS.md#stage-05)
- [该阶段源码](https://github.com/CQULzz/HT_Explo/tree/29f80bc76789a7075f4dfb987cb2e51bfbb56add)

<!-- repository-catalog-start -->
## 代码、视频与完整数据的对应关系

- [阶段05完整索引：实际实验候选、导航代码、报告、视频及数据回执](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/catalog/stage-05.md)
- [本阶段归档源码](https://github.com/CQULzz/HT_Explo/tree/29f80bc76789a7075f4dfb987cb2e51bfbb56add)：`29f80bc76789a7075f4dfb987cb2e51bfbb56add`。这是归档锚点；实际测量源码、运行patch与二进制哈希以原清单为准。
- [完整实验总目录](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/catalog/INDEX.md) · [分支和标签规则](https://github.com/CQULzz/HT_Explo/blob/main/docs/REPOSITORY_GUIDE.md)

早期历史目录只关联到研究阶段，未知测量提交保持待确认；补充回放视频不代表新的导航实验。原有报告、失败记录与全部附件保留。
<!-- repository-catalog-end -->
