# 阶段18：五环境各10分钟与15fps录像（已完成记录）

[返回总索引](INDEX.md)

- 阶段标签：[`ht-stage-20261017-multiscene-10min`](https://github.com/CQULzz/HT_Explo/tree/ht-stage-20261017-multiscene-10min)。
- 归档标签提交：[`6d6998f00f5fa9358a7c212b41da6f395ba492a5`](https://github.com/CQULzz/HT_Explo/commit/6d6998f00f5fa9358a7c212b41da6f395ba492a5)。
- 记录的实验候选：现代发布回执无记录；查下方原始清单，待确认。
- [GitHub Release：完整数据及附件](https://github.com/CQULzz/HT_Explo/releases/tag/ht-stage-20261017-multiscene-10min)。

归档提交、实验设施提交与实际导航代码可能不同。运行时源码快照、补丁、参数及二进制哈希以原实验清单为准；视频不是另一个代码版本的验收证据。

## 改动及实现

参数化仿真/规划场景，串行运行Garage、Campus、Indoor、Forest、Tunnel各600秒；原生相机960×540、15fps，裁剪初始化、编码和完整解码核验。

各组独立地图与进程，独立视频/数据/资源审计，完成一组退出与编码后才进入下一组；底部状态条显示时间、速度、任务和地图/相机年龄，提供播放列表和预览。

## 验证与剩余问题

五环境均记录600秒，五段H.264完整解码及13项采集/进程验证通过；车库189.57m、校园199.76m、森林168.09m持续推进；室内3.11m与隧道26.33m持续受阻。视频599.933至600秒，允许1帧误差。

室内0.6m候选视点漏掉窄走廊安全区域；隧道返航目标周围足迹含未知格，未到家；地图年龄仍有超过3秒的尾延迟，森林激光平均4.02Hz。10分钟独立重启测试不代表连续一小时、实车或全覆盖通过。 2026-10-18复核确认本阶段含晚HT拦截仍发布非零候选Twist的缺陷，阶段21修正；历史记录保留，不能由原通过项推断该晚分支正确停车。

## 报告及版本证据

- [docs/experiments/ht_multiscene_10min.md](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/ht_multiscene_10min.md)
- [docs/results/ht_multiscene_10min_2026-10-17/REPORT.md](https://github.com/CQULzz/HT_Explo/blob/main/docs/results/ht_multiscene_10min_2026-10-17/REPORT.md)
- 原版本总表记录的控制提交：`f1c84854ccc147d40d7f9120c9713ba5e11c736c`。这是历史字段，不能替代运行时快照/补丁核对。

## 可直接下载的视频

本Release没有独立视频附件；请查历史目录内的视频及原报告。

## 完整数据及上传回执

- [docs/experiments/legacy_archive/receipts/ht_multiscene_10min_2026-10-17_11-37-52.json](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/legacy_archive/receipts/ht_multiscene_10min_2026-10-17_11-37-52.json)

完整附件名、大小、SHA256、下载URL见[index.json](index.json)中本阶段的`release_assets`；历史分片按`content_key`分组，不能把同一Release内不同目录的分片混合。

## 早期历史目录与包内视频

以下为研究阶段关联，不保证阶段标签等于实际测量源码。没有提交记录的保持待确认；下载匹配的归档包后按包内路径查找视频。

### ht_multiscene_10min_2026-10-17_11-37-52

- 数据分片前缀：`legacy-ht_multiscene_10min_2026-10-17_11-37-52-f7fc48ff77b8`。
- [上传回执](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/legacy_archive/receipts/ht_multiscene_10min_2026-10-17_11-37-52.json) · [包内逐文件SHA256清单](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/legacy_archive/inventories/ht_multiscene_10min_2026-10-17_11-37-52.json)。
- 原测量源码记录：`[{"path": "campus/manifest.json", "recorded_commits": {"git_head": "c086bb1ab21ca88e54e8ed0bf4797892fa6de74d"}, "planned_duration_s": 600, "working_tree_patch_preserved": true}, {"path": "forest/manifest.json", "recorded_commits": {"git_head": "c086bb1ab21ca88e54e8ed0bf4797892fa6de74d"}, "planned_duration_s": 600, "working_tree_patch_preserved": true}, {"path": "garage/manifest.json", "recorded_commits": {"git_head": "6d6998f00f5fa9358a7c212b41da6f395ba492a5"}, "planned_duration_s": 600, "working_tree_patch_preserved": true}, {"path": "indoor/manifest.json", "recorded_commits": {"git_head": "c086bb1ab21ca88e54e8ed0bf4797892fa6de74d"}, "planned_duration_s": 600, "working_tree_patch_preserved": true}, {"path": "tunnel/manifest.json", "recorded_commits": {"git_head": "c086bb1ab21ca88e54e8ed0bf4797892fa6de74d"}, "planned_duration_s": 600, "working_tree_patch_preserved": true}]`。
- 原状态证据：`[{"path": "suite.json", "state": "COMPLETED", "runs": [{"scenario": "garage", "state": "RECORDED", "elapsed_measurement_s": 643.9}, {"scenario": "campus", "state": "RECORDED", "elapsed_measurement_s": 696.7}, {"scenario": "indoor", "state": "RECORDED", "elapsed_measurement_s": 626.8}, {"scenario": "forest", "state": "RECORDED", "elapsed_measurement_s": 693.8}, {"scenario": "tunnel", "state": "RECORDED", "elapsed_measurement_s": 630.4}], "reason": null}]`。
- 包内视频：`campus/camera_15fps.mp4`；176139131 bytes；SHA256 `8fb3121615bc44a74ed323d058effe00df39effcfbb6803681a427974b1a4f9c`。
- 包内视频：`campus/camera_h264.mp4`；67743651 bytes；SHA256 `4a63f45de4bdd6c330c3dc32f5237f4cef250a1c0c05e04619e152a014fe2faf`。
- 包内视频：`forest/camera_15fps.mp4`；365747002 bytes；SHA256 `2efbb36026a4af7355bcfb520f9922555321d02612e232656791d849e6d81075`。
- 包内视频：`forest/camera_h264.mp4`；90059195 bytes；SHA256 `0ec261a878a639ade0762affa4f8b652df187f81ba2a5b5986bd8a4269727805`。
- 包内视频：`garage/camera_15fps.mp4`；43231760 bytes；SHA256 `0e00838ab1c445d0afd28b2a93d85ea778cadc83e2981c17609539ec07431846`。
- 包内视频：`garage/camera_h264.mp4`；9912953 bytes；SHA256 `b070803bbb6cf78514a35dd01df8de1b76f225ef9e4f9a9b059ddb3ef4a9a5ba`。
- 包内视频：`indoor/camera_15fps.mp4`；31055097 bytes；SHA256 `74d6b4471bcdbdfbcf9422da55ffec3240eb2a7208b9d063f7acb415f5ab7b9b`。
- 包内视频：`indoor/camera_h264.mp4`；2666214 bytes；SHA256 `fc215d1f9ba1e35c2b475549e7b7627774d8446d04c9cc8e89266890ebb13bd8`。
- 包内视频：`tunnel/camera_15fps.mp4`；36033479 bytes；SHA256 `85eec9ba6b086829b47528e0fce805f2673cd6b1ea51fd2168a896b229cfbed0`。
- 包内视频：`tunnel/camera_h264.mp4`；3155704 bytes；SHA256 `031f91590d32a7ed206341c78efbb7263b46d5fe95020ebee4937cb1719fa38f`。
