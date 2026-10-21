# 阶段12：最新原版TARE配对评测

[返回总索引](INDEX.md)

- 阶段标签：[`ht-stage-20261016-tare-compare`](https://github.com/CQULzz/HT_Explo/tree/ht-stage-20261016-tare-compare)。
- 归档标签提交：[`07ab0067dc7f47dc6eb7e5e2b9924f79f2ed9a24`](https://github.com/CQULzz/HT_Explo/commit/07ab0067dc7f47dc6eb7e5e2b9924f79f2ed9a24)。
- 记录的实验候选：现代发布回执无记录；查下方原始清单，待确认。
- [GitHub Release：完整数据及附件](https://github.com/CQULzz/HT_Explo/releases/tag/ht-stage-20261016-tare-compare)。

归档提交、实验设施提交与实际导航代码可能不同。运行时源码快照、补丁、参数及二进制哈希以原实验清单为准；视频不是另一个代码版本的验收证据。

## 改动及实现

增加同场景/同前进目标的独立配对运行、公共自由体积统计、对比图和分屏视频。

明确量化原版与当前完整系统差距；与上阶段相比没有再升级运动规划算法。

## 验证与剩余问题

180秒原版/HT里程81.08/54.52米，估计自由体积6242.625/3224.625m³；HT体积约为原版51.7%。

每组一次且倒车/角速度/加速度未完全对齐，是端到端比较；HT转向、停车和回访更多，未追平原版。 2026-10-18复核确认本阶段含晚HT拦截仍发布非零候选Twist的缺陷，阶段21修正；历史记录保留，不能由原通过项推断该晚分支正确停车。

## 报告及版本证据

- [docs/results/tare_ht_pair_2026-10-16/REPORT.md](https://github.com/CQULzz/HT_Explo/blob/main/docs/results/tare_ht_pair_2026-10-16/REPORT.md)
- 原版本总表记录的控制提交：`3912e37df7541799c354bf568ff8f3d5b0383aab`。这是历史字段，不能替代运行时快照/补丁核对。

## 可直接下载的视频

本Release没有独立视频附件；请查历史目录内的视频及原报告。

## 完整数据及上传回执

- [docs/experiments/legacy_archive/receipts/tare_ht_pair_2026-10-16.json](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/legacy_archive/receipts/tare_ht_pair_2026-10-16.json)
- [docs/experiments/legacy_archive/receipts/version_publication_2026-10-16.json](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/legacy_archive/receipts/version_publication_2026-10-16.json)

完整附件名、大小、SHA256、下载URL见[index.json](index.json)中本阶段的`release_assets`；历史分片按`content_key`分组，不能把同一Release内不同目录的分片混合。

## 早期历史目录与包内视频

以下为研究阶段关联，不保证阶段标签等于实际测量源码。没有提交记录的保持待确认；下载匹配的归档包后按包内路径查找视频。

### tare_ht_pair_2026-10-16

- 数据分片前缀：`legacy-tare_ht_pair_2026-10-16-504953128d02`。
- [上传回执](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/legacy_archive/receipts/tare_ht_pair_2026-10-16.json) · [包内逐文件SHA256清单](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/legacy_archive/inventories/tare_ht_pair_2026-10-16.json)。
- 原测量源码记录：`[{"path": "manifest.json", "recorded_commits": {"current_commit": "919d826f340c11e34421a738e80d2a2e85066eb9", "upstream_commit": "b6760adb4280b379567c76f4e684ce628e28ef71"}, "planned_duration_s": 180, "working_tree_patch_preserved": true}]`。
- 原状态证据：`[]`。
- 包内视频：`comparison.mp4`；6947842 bytes；SHA256 `52158a6160e518cf43ae8ac4ac807486177b68a914dd51ff3992e55a550e1931`。

### version_publication_2026-10-16

- 数据分片前缀：`legacy-version_publication_2026-10-16-4faa0fe5078d`。
- [上传回执](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/legacy_archive/receipts/version_publication_2026-10-16.json) · [包内逐文件SHA256清单](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/legacy_archive/inventories/version_publication_2026-10-16.json)。
- 原测量源码记录：`[]`。
- 原状态证据：`[]`。
