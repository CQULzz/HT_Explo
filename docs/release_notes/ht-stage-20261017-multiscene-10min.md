# 阶段18｜五环境各10分钟与15fps录像（已完成记录）

标签固定源码，验证与问题以本说明为准。C++规划仍为bd0c2c2，HT桥接仍为f1c8485。

## 改了什么

参数化仿真/规划场景，串行运行Garage、Campus、Indoor、Forest、Tunnel各600秒；原生相机960×540、15fps，裁剪初始化、编码和完整解码核验。

## 实现了什么功能

各组独立地图与进程，独立视频/数据/资源审计，完成一组退出与编码后才进入下一组；底部状态条显示时间、速度、任务和地图/相机年龄，提供播放列表和预览。

## 实验与验证

五环境均记录600秒，五段H.264完整解码及13项采集/进程验证通过；车库189.57m、校园199.76m、森林168.09m持续推进；室内3.11m与隧道26.33m持续受阻。视频599.933至600秒，允许1帧误差。

## 存在什么问题

室内0.6m候选视点漏掉窄走廊安全区域；隧道返航目标周围足迹含未知格，未到家；地图年龄仍有超过3秒的尾延迟，森林激光平均4.02Hz。10分钟独立重启测试不代表连续一小时、实车或全覆盖通过。

证据：[ht_multiscene_10min.md](https://github.com/CQULzz/HT_Explo/blob/codex/ht8dir-v1/docs/experiments/ht_multiscene_10min.md) · [REPORT.md](https://github.com/CQULzz/HT_Explo/blob/codex/ht8dir-v1/docs/results/ht_multiscene_10min_2026-10-17/REPORT.md)

验证数据与视频归档：[提交 2d74d9c](https://github.com/CQULzz/HT_Explo/commit/2d74d9c7d4e2d68f9fef9fe653a94aa8aa0196a8)。

## 2026-10-18后续复核

2026-10-18复核确认本阶段含晚HT拦截仍发布非零候选Twist的缺陷，阶段21修正；历史记录保留，不能由原通过项推断该晚分支正确停车。 [证据与修正](https://github.com/CQULzz/HT_Explo/blob/codex/ht8dir-v1/docs/results/ht_completion_cause_audit_2026-10-18/REPORT.md)。这不是对所有历史停滞的统一归因。

<!-- legacy-full-data-start -->
## 历史完整实验数据补归档（2026-10-20）

本阶段关联的 **1 个历史目录**已作为本 Release 的 `legacy-*` 分卷附件补齐，并核对远端大小与 SHA256。

**阶段归属不等于标签就是实际测试提交。** 原始 manifest、测试提交、未提交补丁、源文件哈希、真实时长和失败/中止说明均保留在逐文件清单与数据中；没有证据的提交号仍标为未知。本次仅补数据，不改变原实验结论或标签。

[全部62目录的版本对应、逐文件清单、校验回执与下载恢复方法](https://github.com/CQULzz/HT_Explo/blob/codex/ht8dir-v1/docs/experiments/legacy_archive/README.md)

| 历史目录 | 原始文件GiB | 完整数据前缀 |
|---|---:|---|
| `ht_multiscene_10min_2026-10-17_11-37-52` | 2.2031 | `legacy-ht_multiscene_10min_2026-10-17_11-37-52-f7fc48ff77b8` |

下载同一前缀的全部 `.tar.zst.partNNN`、`-files.json` 与 `-verified.json`；核对回执后按数字顺序合并解压。大MCAP/NPZ在Release附件，未加入Git历史。
<!-- legacy-full-data-end -->
