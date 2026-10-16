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
