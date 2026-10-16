# 阶段04：真实HT推理与通过性评测工具

**状态：实验里程碑，不是稳定版；尚未完成实车完整验证。**

归档提交：[4315dd9](https://github.com/CQULzz/HT_Explo/commit/4315dd9deaed24245d6fbdd3c8ebe8726f74b476)。类型：评测与接口。
实际控制/功能来源：[df8815c](https://github.com/CQULzz/HT_Explo/commit/df8815c61a22a76d0314d372e4c280ac233ee23c)。

## 改了什么

增加固定通过性评测、数据/模型审计、配对推理和真实学生模型山地闭环。

## 实现了什么功能

将真实八方向预测接入雷达观测高程，区分模型误放/误拒、路线选择和实际车辆通过。

## 实验与验证

山地各2轮60秒中，HT平均新增表面体素550.5，基线606.5，未显示探索提升；暴露HT提前返回造成返航遗漏。

## 存在什么问题

传感器适配且地形来自训练域；旧软代价、近地盲区和返航问题仍在，不能以离线准确率代替闭环效果。

## 报告与代码

- [experiments/traversability/README.md](https://github.com/CQULzz/HT_Explo/blob/codex/ht8dir-v1/experiments/traversability/README.md)
- [experiments/traversability/evidence/REPORT.md](https://github.com/CQULzz/HT_Explo/blob/codex/ht8dir-v1/experiments/traversability/evidence/REPORT.md)
- [experiments/results/mountain_live_20260921/REPORT.md](https://github.com/CQULzz/HT_Explo/blob/codex/ht8dir-v1/experiments/results/mountain_live_20260921/REPORT.md)
- [全部版本对照](https://github.com/CQULzz/HT_Explo/blob/codex/ht8dir-v1/VERSIONS.md#stage-04)
- [该阶段源码](https://github.com/CQULzz/HT_Explo/tree/4315dd9deaed24245d6fbdd3c8ebe8726f74b476)
