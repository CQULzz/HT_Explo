# 实车分支、固定版本与实验资料

更新时间：2026-10-29。此页标注最近两版；更早版本保持原有tag和归档，不重打标签。

## Branch用途

| Branch | 用途 |
|---|---|
| [`real/scout-helios32`](https://github.com/CQULzz/HT_Explo/tree/real/scout-helios32) | Scout + Helios32实车专用外参、输入桥接、HT、TARE/XYθ代码及离线实验记录；本次只向此分支追加代码/文档 |
| `main` | 保留原仿真/实验归档基线，本次未改动 |
| `develop` | 保留通用开发候选，本次未改动 |

本地审查分支`real/scout-review-20261028`使用不同导入祖先，不是部署分支。GitHub版本以远端分支、以下固定tag和发布回执为准。每个tag固定当轮代码与报告，后续分支的文档提交不意味着tag变化。

## Tag、代码与资料对应

| Tag | tag指向的完整提交 | 算法修复提交 | 资料 |
|---|---|---|---|
| [`real-scout-wheel-shadow-20261029`](https://github.com/CQULzz/HT_Explo/tree/real-scout-wheel-shadow-20261029) | `93a554d8c9d5d31724286e02d6f29ed83093cffe` | `a54bd0c8ef4bdce4da196db36b16415412ff2984` | [Release](https://github.com/CQULzz/HT_Explo/releases/tag/real-scout-wheel-shadow-20261029)、[报告](../results/real_wheel_occlusion_2026-10-29/REPORT.md) |
| [`real-scout-wide-replay-20261029`](https://github.com/CQULzz/HT_Explo/tree/real-scout-wide-replay-20261029) | `3b4f483e3bff909d35882a60d9474e84350878ac` | 沿用上一版过滤；本版新增两个离线可视化工具，未改建图、HT、规划或控制行为 | [Release](https://github.com/CQULzz/HT_Explo/releases/tag/real-scout-wide-replay-20261029)、[报告](../results/real_wide_replay_2026-10-29/REPORT.md) |

过滤修复版：默认车体过滤接入有界轮胎遮挡射线检查，保留原几何/外参、近地面保护和可见上部结构保护。保存两段录包、配准开/关四组候选、关闭过滤回归、全部点云掩码、失败尝试、图表和视频。46项相关检查通过；未验证实车闭环或ARM性能。

大视野复测版：移动录包358/358扫描融合、64帧HT；静止录包643扫描中641帧融合、117帧HT，开始两帧缺精确时间TF。181帧保存数组与上一版对应已开启配准的结果逐元素一致。视频移动段在前、静止段在后，共100.2秒：

- [环境全屏版1080p](https://github.com/CQULzz/HT_Explo/releases/download/real-scout-wide-replay-20261029/HT_wide_environment.mp4)
- [全局/局部高程、八方向HT和半透明XYθ四视图4K](https://github.com/CQULzz/HT_Explo/releases/download/real-scout-wide-replay-20261029/HT_wide_four_views_4K.mp4)
- [完整本轮数据ZIP，547454015字节](https://github.com/CQULzz/HT_Explo/releases/download/real-scout-wide-replay-20261029/HT_wide_repeat_full_data.zip)
- [完整文件清单](https://github.com/CQULzz/HT_Explo/releases/download/real-scout-wide-replay-20261029/FULL_DATA_MANIFEST.json)、[发布大小/SHA256校验回执](https://github.com/CQULzz/HT_Explo/releases/download/real-scout-wide-replay-20261029/PUBLICATION_RECEIPT.json)

原始两段录包在前一版`real-scout-newbags-20261028`的已验证附件中；本轮ZIP通过RAW_SOURCE_ASSETS引用，不重复打包原始录包。

## 源码位置与限制

- 完整探索/TARE/TSP与XYθ执行代码：[src/tare_planner](../../src/tare_planner)。
- HT推理、历史高程融合与局部规划工具：[tools/ht_cupy_bridge](../../tools/ht_cupy_bridge)。
- 实车外参与输入适配：[src/ht_scout_bridge](../../src/ht_scout_bridge)。
- 新增大视野工具：`prepare_replay_scene.py`、`record_wide_replay.py`，均在`tools/ht_cupy_bridge`；灰色环境点只作显示，不回馈建图/HT。青线是录包轨迹。

上述版本均未解决静止盲区、全部近车低分或移动末段残余低分，也不能作为实车闭环成功或ARM实时性证明。只做离线，不启动设备、仿真、控制或车辆；不把本轮显示范围扩大解释为规划范围扩大。

复现实验需使用新输出目录，具体命令、参数与源码哈希见对应Release和报告；完整数据、视频与失败记录保存在Release附件，不放进大文件Git历史。
