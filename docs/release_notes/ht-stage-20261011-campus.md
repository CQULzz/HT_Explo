# 阶段07：Campus地图传输与前瞻航点

**状态：实验里程碑，不是稳定版；尚未完成实车完整验证。**

归档提交：[087c42d](https://github.com/CQULzz/HT_Explo/commit/087c42d45801a34a355cac936488efe19141768d)。类型：功能。
实际控制/功能来源：[83b44a3](https://github.com/CQULzz/HT_Explo/commit/83b44a37c2e905022c1d396a738092eabdaa3aee)。

## 改了什么

HT地图改可靠订阅；只沿已检查且近乎直线的路段跨过近航点；补倒车和探索局限审计。

## 实现了什么功能

改善大地图送达和CMU路径末端频繁减速，旧控制器继续实际控车。

## 实验与验证

15分钟367.85米、该轮HT_MAP_STALE为0；另5分钟对照零线速占比11.2%→5.8%。

## 存在什么问题

长测倒车占48.4%，另一短测79.3%；旧长测缺XY轨迹/探索体积。此时没有实际XYθ闭环，不能用里程代表探索效果。

## 报告与代码

- [validation/results/HT_long_run_report_2026-10-11.md](https://github.com/CQULzz/HT_Explo/blob/codex/ht8dir-v1/validation/results/HT_long_run_report_2026-10-11.md)
- [全部版本对照](https://github.com/CQULzz/HT_Explo/blob/codex/ht8dir-v1/VERSIONS.md#stage-07)
- [该阶段源码](https://github.com/CQULzz/HT_Explo/tree/087c42d45801a34a355cac936488efe19141768d)

<!-- repository-catalog-start -->
## 代码、视频与完整数据的对应关系

- [阶段07完整索引：实际实验候选、导航代码、报告、视频及数据回执](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/catalog/stage-07.md)
- [本阶段归档源码](https://github.com/CQULzz/HT_Explo/tree/087c42d45801a34a355cac936488efe19141768d)：`087c42d45801a34a355cac936488efe19141768d`。这是归档锚点；实际测量源码、运行patch与二进制哈希以原清单为准。
- [完整实验总目录](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/catalog/INDEX.md) · [分支和标签规则](https://github.com/CQULzz/HT_Explo/blob/main/docs/REPOSITORY_GUIDE.md)

早期历史目录只关联到研究阶段，未知测量提交保持待确认；补充回放视频不代表新的导航实验。原有报告、失败记录与全部附件保留。
<!-- repository-catalog-end -->
