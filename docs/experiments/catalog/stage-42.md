# 阶段42：原TARE＋HT五场景计划与实际采集（含中断/失败）

[返回总索引](INDEX.md)

- 阶段标签：[`ht-stage-20261020-tare-multiscene`](https://github.com/CQULzz/HT_Explo/tree/ht-stage-20261020-tare-multiscene)。
- 归档标签提交：[`dccfcc93232f0f27f9ae2d63b59ae93c4c1168c4`](https://github.com/CQULzz/HT_Explo/commit/dccfcc93232f0f27f9ae2d63b59ae93c4c1168c4)。
- 记录的实验候选：[`dccfcc9`](https://github.com/CQULzz/HT_Explo/tree/dccfcc93232f0f27f9ae2d63b59ae93c4c1168c4)
- [GitHub Release：完整数据及附件](https://github.com/CQULzz/HT_Explo/releases/tag/ht-stage-20261020-tare-multiscene)。

归档提交、实验设施提交与实际导航代码可能不同。运行时源码快照、补丁、参数及二进制哈希以原实验清单为准；视频不是另一个代码版本的验收证据。

## 改动及实现

计划使用同阶段41导航逻辑在五场景独立录制；实际完成及中断见逐组记录，增加参数/话题/分工/视频及数据核验

原TARE确定访问顺序，HT负责指定航点XYθ路由；本轮不改算法

## 验证与剩余问题

五场景实际结果见报告；采集状态：garage=RECORDED, campus=RECORDED, indoor=FAILED, forest=PENDING, tunnel=PENDING

garage:存在超过10秒完全停车，见状态和地形诊断；indoor:未获得完整且通过检查的记录；indoor:分工未通过或缺少执行样本，见审计；forest:未获得完整且通过检查的记录；forest:分工未通过或缺少执行样本，见审计；tunnel:未获得完整且通过检查的记录；tunnel:分工未通过或缺少执行样本，见审计；没有同限制原版新配对、实车与全局SE2可达性保证

## 报告及版本证据

- [docs/results/ht_tare_native_5scene_10min_2026-10-20/REPORT.md](https://github.com/CQULzz/HT_Explo/blob/main/docs/results/ht_tare_native_5scene_10min_2026-10-20/REPORT.md)
- [冻结清单](https://github.com/CQULzz/HT_Explo/blob/main/docs/results/ht_tare_native_5scene_10min_2026-10-20/frozen_job.json)：candidate_commit=`dccfcc93232f0f27f9ae2d63b59ae93c4c1168c4`；navigation_control_commit=`68701319b333165dd9cd5acf8e226ba52c174434`；duration_per_scene_s=`600`
- 原版本总表记录的控制提交：`68701319b333165dd9cd5acf8e226ba52c174434`。这是历史字段，不能替代运行时快照/补丁核对。

## 可直接下载的视频

- [ht-stage-20261020-tare-multiscene-garage.mp4](https://github.com/CQULzz/HT_Explo/releases/download/ht-stage-20261020-tare-multiscene/ht-stage-20261020-tare-multiscene-garage.mp4) — 9873122 bytes；`sha256:dc48083e7c86cc6468fe8827aaeb9e4ec794ce5da0cfeca649e0696505690015`。
- [ht-stage-20261020-tare-multiscene-campus.mp4](https://github.com/CQULzz/HT_Explo/releases/download/ht-stage-20261020-tare-multiscene/ht-stage-20261020-tare-multiscene-campus.mp4) — 59098995 bytes；`sha256:f19f72787bd1db2be3508cf272a8a0f869abefb1c12b7a49f9003a0401feaed4`。

## 完整数据及上传回执

- [docs/experiments/publications/stage42.json](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/publications/stage42.json)

完整附件名、大小、SHA256、下载URL见[index.json](index.json)中本阶段的`release_assets`；历史分片按`content_key`分组，不能把同一Release内不同目录的分片混合。

## 早期历史目录与包内视频

以下为研究阶段关联，不保证阶段标签等于实际测量源码。没有提交记录的保持待确认；下载匹配的归档包后按包内路径查找视频。

无早期历史目录关联。
