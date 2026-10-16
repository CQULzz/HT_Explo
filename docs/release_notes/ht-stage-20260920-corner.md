# 阶段03：旧有向图拐角修复与重复实验

**状态：实验里程碑，不是稳定版；尚未完成实车完整验证。**

归档提交：[a6c015a](https://github.com/CQULzz/HT_Explo/commit/a6c015a3a3f703d0b0acb880ed0230e08d49f9bd)。类型：功能。
实际控制/功能来源：[df8815c](https://github.com/CQULzz/HT_Explo/commit/df8815c61a22a76d0314d372e4c280ac233ee23c)。

## 改了什么

增加gridEdgeSupported和共用连通检查，拒绝切角；保留修复前失败轮并归档复测。

## 实现了什么功能

修复旧图允许而执行端拒绝的特定对角边，具备重复运行、统计及绘图工具。

## 实验与验证

修复后3轮各300秒未见原219秒持续停滞；52项核心、9项ROS、3项统计检查通过。

## 存在什么问题

HT为80×80米、0.5米栅格、八方向全0.9的合成输入；不是学习模型收益，9轮均未完成全域探索。

## 报告与代码

- [EXPERIMENT_REPORT.md](https://github.com/CQULzz/HT_Explo/blob/codex/ht8dir-v1/EXPERIMENT_REPORT.md)
- [experiments/results/garage_corner_fix_20260920/README.md](https://github.com/CQULzz/HT_Explo/blob/codex/ht8dir-v1/experiments/results/garage_corner_fix_20260920/README.md)
- [全部版本对照](https://github.com/CQULzz/HT_Explo/blob/codex/ht8dir-v1/VERSIONS.md#stage-03)
- [该阶段源码](https://github.com/CQULzz/HT_Explo/tree/a6c015a3a3f703d0b0acb880ed0230e08d49f9bd)
