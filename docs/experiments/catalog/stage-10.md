# 阶段10：同版本复跑失败与完整数据发布

[返回总索引](INDEX.md)

- 阶段标签：[`ht-garage-repeat-20261015-1225`](https://github.com/CQULzz/HT_Explo/tree/ht-garage-repeat-20261015-1225)。
- 归档标签提交：[`0b842e4ab71a1ed0249cc32da923a0f51940106a`](https://github.com/CQULzz/HT_Explo/commit/0b842e4ab71a1ed0249cc32da923a0f51940106a)。
- 记录的实验候选：现代发布回执无记录；查下方原始清单，待确认。
- [GitHub Release：完整数据及附件](https://github.com/CQULzz/HT_Explo/releases/tag/ht-garage-repeat-20261015-1225)。

归档提交、实验设施提交与实际导航代码可能不同。运行时源码快照、补丁、参数及二进制哈希以原实验清单为准；视频不是另一个代码版本的验收证据。

## 改动及实现

新增完整视频、CSV/快照/录包下载与校验清单；697ae2e随后补GitHub下载和SHA-256复核。

可以复现并查看约102秒后的失败全过程，保留原Release附件链接。

## 验证与剩余问题

180秒29.76米，最后60秒0米；HT_PATH_BLOCKED对应1562个零速指令样本。

这是失败证据归档，不是算法修复；控车仍为dbce623。上层HT_ASSISTED不代表执行端允许运动。 2026-10-18复核确认本阶段含晚HT拦截仍发布非零候选Twist的缺陷，阶段21修正；历史记录保留，不能由原通过项推断该晚分支正确停车。

## 报告及版本证据

- [docs/results/ht_repeat_2026-10-15/REPORT.md](https://github.com/CQULzz/HT_Explo/blob/main/docs/results/ht_repeat_2026-10-15/REPORT.md)
- [docs/results/ht_repeat_2026-10-15/github_upload_verification.json](https://github.com/CQULzz/HT_Explo/blob/main/docs/results/ht_repeat_2026-10-15/github_upload_verification.json)
- 原版本总表记录的控制提交：`dbce623161087fcaac865b1d4db5305d1cfe2c9c`。这是历史字段，不能替代运行时快照/补丁核对。

## 可直接下载的视频

- [garage_ht_xytheta_180s.mp4](https://github.com/CQULzz/HT_Explo/releases/download/ht-garage-repeat-20261015-1225/garage_ht_xytheta_180s.mp4) — 30521028 bytes；`sha256:735e4e3d908cb41fb10fbd32b46abe93a9832219c745e7db0cda322ee66a67dc`。

## 完整数据及上传回执

- [docs/experiments/legacy_archive/receipts/ht_repeat_publish_2026-10-15.json](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/legacy_archive/receipts/ht_repeat_publish_2026-10-15.json)

完整附件名、大小、SHA256、下载URL见[index.json](index.json)中本阶段的`release_assets`；历史分片按`content_key`分组，不能把同一Release内不同目录的分片混合。

## 早期历史目录与包内视频

以下为研究阶段关联，不保证阶段标签等于实际测量源码。没有提交记录的保持待确认；下载匹配的归档包后按包内路径查找视频。

### ht_repeat_publish_2026-10-15

- 数据分片前缀：`legacy-ht_repeat_publish_2026-10-15-8dc4710712d2`。
- [上传回执](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/legacy_archive/receipts/ht_repeat_publish_2026-10-15.json) · [包内逐文件SHA256清单](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/legacy_archive/inventories/ht_repeat_publish_2026-10-15.json)。
- 原测量源码记录：`[{"path": "manifest.json", "recorded_commits": {"git_head": "dbce623161087fcaac865b1d4db5305d1cfe2c9c"}, "planned_duration_s": 180, "working_tree_patch_preserved": true}]`。
- 原状态证据：`[]`。
- 包内视频：`publish/garage_ht_xytheta_180s.mp4`；30521028 bytes；SHA256 `735e4e3d908cb41fb10fbd32b46abe93a9832219c745e7db0cda322ee66a67dc`。
- 包内视频：`visuals/current_ht_exploration.mp4`；73735905 bytes；SHA256 `9b8d81f63b7cd6c960ca4a207d477385e282a653d8a4e461a3ccebdaab6f6916`。
