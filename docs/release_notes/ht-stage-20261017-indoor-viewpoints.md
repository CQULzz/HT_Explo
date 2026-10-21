# 阶段19｜室内视点细化：恢复推进，仍有停顿回访

标签固定源码，验证与问题以本说明为准。C++规划仍为bd0c2c2，HT桥接仍为f1c8485。

## 改了什么

室内视点从50×50、0.6m改为100×100、0.3m，保持30×30m范围；原HT分辨率、概率阈值、足迹半径、运动学搜索和控制速度不变。

## 实现了什么功能

为窄HT支撑带提供候选端点，保留原参数失败视频；新增实际栅格、足迹硬门槛、时间戳与配置归档。

## 实验与验证

独立600秒补测、9000帧完整解码及13项采集/进程核验通过。里程3.11→145.28m，近似观测347.875→1900.25m³，全零指令98.2%→23.0%；运行中实际参数读取与源哈希证明仅室内视点配置不同。

## 存在什么问题

仍有最长39.80秒停车和2.3%倒车；第6至7.5分钟行驶22.94m仅增8.375m³，低收益回访未消失。活跃搜索耗时P95为1.576秒、HT年龄最大4.67秒。隧道返航未知足迹问题未解决；每配置一次，不能视为所有场景通过。

证据：[REPORT.md](https://github.com/CQULzz/HT_Explo/blob/codex/ht8dir-v1/docs/results/ht_indoor_sampling_comparison_2026-10-17/REPORT.md) · [REPORT.md](https://github.com/CQULzz/HT_Explo/blob/codex/ht8dir-v1/docs/results/ht_indoor_viewpoint_10min_2026-10-17/REPORT.md) · [README.md](https://github.com/CQULzz/HT_Explo/blob/codex/ht8dir-v1/docs/results/ht_multiscene_10min_2026-10-17/indoor/diagnostics/README.md)

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
| `ht_indoor_dense_10min_2026-10-17_12-38-24` | 0.2891 | `legacy-ht_indoor_dense_10min_2026-10-17_12-38-24-bc5da6325e75` |

下载同一前缀的全部 `.tar.zst.partNNN`、`-files.json` 与 `-verified.json`；核对回执后按数字顺序合并解压。大MCAP/NPZ在Release附件，未加入Git历史。
<!-- legacy-full-data-end -->

<!-- repository-catalog-start -->
## 代码、视频与完整数据的对应关系

- [阶段19完整索引：实际实验候选、导航代码、报告、视频及数据回执](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/catalog/stage-19.md)
- [本阶段归档源码](https://github.com/CQULzz/HT_Explo/tree/f3d1eeedae814f99d0db94673c7abadc8eaf7439)：`f3d1eeedae814f99d0db94673c7abadc8eaf7439`。这是归档锚点；实际测量源码、运行patch与二进制哈希以原清单为准。
- [完整实验总目录](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/catalog/INDEX.md) · [分支和标签规则](https://github.com/CQULzz/HT_Explo/blob/main/docs/REPOSITORY_GUIDE.md)

早期历史目录只关联到研究阶段，未知测量提交保持待确认；补充回放视频不代表新的导航实验。原有报告、失败记录与全部附件保留。
<!-- repository-catalog-end -->
