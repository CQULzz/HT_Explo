# 阶段37：地图串行执行与独立TF接收，修复调度长等待

[返回总索引](INDEX.md)

- 阶段标签：[`ht-stage-20261019-serial-mapper`](https://github.com/CQULzz/HT_Explo/tree/ht-stage-20261019-serial-mapper)。
- 归档标签提交：[`d6d87878a4e8982e3a4850a5a17f8e1be1608a24`](https://github.com/CQULzz/HT_Explo/commit/d6d87878a4e8982e3a4850a5a17f8e1be1608a24)。
- 记录的实验候选：[`d6d8787`](https://github.com/CQULzz/HT_Explo/tree/d6d87878a4e8982e3a4850a5a17f8e1be1608a24)
- [GitHub Release：完整数据及附件](https://github.com/CQULzz/HT_Explo/releases/tag/ht-stage-20261019-serial-mapper)。

归档提交、实验设施提交与实际导航代码可能不同。运行时源码快照、补丁、参数及二进制哈希以原实验清单为准；视频不是另一个代码版本的验收证据。

## 改动及实现

CuPy主执行器改为单线程，TF由独立子节点/单线程接收；融合与安全门槛保留

真实TF回放复现原四线程P95 1.106s，修复布局.0021s；实际ROS等待未来TF及关闭回归通过

## 验证与剩余问题

完整车库600秒179.78m/4522.625m³，13项采集通过，HT年龄P950.842s/最大1.840s

探索体积较阶段36下降42.8%，原地转向21.7%→27.0%，回访增加；仍47次搜索超时。仅单轮车库验证，不代表多环境或实车稳定。

## 报告及版本证据

- [docs/results/ht_serial_mapper_10min_2026-10-19/REPORT.md](https://github.com/CQULzz/HT_Explo/blob/main/docs/results/ht_serial_mapper_10min_2026-10-19/REPORT.md)
- 原版本总表记录的控制提交：`391fa0f98fc2a0adab2c018b4c5a1c7c29efff91`。这是历史字段，不能替代运行时快照/补丁核对。

## 可直接下载的视频

- [ht-stage-20261019-serial-mapper-garage.mp4](https://github.com/CQULzz/HT_Explo/releases/download/ht-stage-20261019-serial-mapper/ht-stage-20261019-serial-mapper-garage.mp4) — 9224657 bytes；`sha256:98cb374875baa95905160e04d59c16a4a376b4ef176635b4defb394a89cb38f8`。

## 完整数据及上传回执

- [docs/experiments/publications/stage37.json](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/publications/stage37.json)

完整附件名、大小、SHA256、下载URL见[index.json](index.json)中本阶段的`release_assets`；历史分片按`content_key`分组，不能把同一Release内不同目录的分片混合。

## 早期历史目录与包内视频

以下为研究阶段关联，不保证阶段标签等于实际测量源码。没有提交记录的保持待确认；下载匹配的归档包后按包内路径查找视频。

无早期历史目录关联。
