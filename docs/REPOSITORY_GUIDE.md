# GitHub分支、标签与实验资料

整理日期：2026-10-22。源码、完整已录数据和辅助视频工具分别登记；没有修改导航算法或重跑实验。机器可读规则见[repository_layout.json](repository_layout.json)，逐阶段清单见[实验总索引](experiments/catalog/INDEX.md)。本次实际分支、标签、源码和附件核验结果见[发布回执](repository_organization_receipt.json)。

## 分支职责

| 分支 | 内容 | 使用边界 |
|---|---|---|
| `main` | 默认分支；`ffab5bd`完整归档基线，加`13b46a9`可视化与本次资料索引 | 导航源文件沿用阶段47/48，导航改动锚点`07c1abd`；有已知问题，不代表实车通过 |
| `develop` | 保留`3f589d8`输入校验，并新增实车话题/QoS、扫描位姿匹配、实际指令间隔及定位跳变停用修复；见`validation/real_vehicle_offline_fix_2026-10-22/REPORT.md` | 没有完整600秒仿真验收；见该分支`validation/logic_resolution_2026-10-22/`；中止记录保留 |
| `visualization/xytheta` | 指向`13b46a9`：半透明体素及八方向数据审计 | 只重放阶段48数据；不作为新的探索能力对照 |
| `codex/ht8dir-v1` | 原默认开发分支 | 原提交保留，不强推、不重写；作为历史兼容入口 |
| `codex/ht-transparent-voxels-20261022` | 原可视化分支 | 保留原链接，与`visualization/xytheta`的起始代码相同 |

本次不改变当前本机工作区分支，也不重置未提交文件。使用Git私有索引发布分支，避免把并行进行中的候选修复混入已归档导航基线。

## 标签含义

| 标签 | 代码提交 | 意义 |
|---|---|---|
| `nav/ht-soft-cost-20260914` | `46f9642` | 早期HT八方向软代价集成 |
| `nav/ht-xytheta-20261015` | `322ec85` | 高程坐标、历史融合和XYθ阶段代码快照 |
| `nav/tare-waypoint-20261020` | `42966cb` | 恢复原TARE覆盖/TSP顺序，HT路由odom到当前航点 |
| `nav/tare-ht-20261021` | `07c1abd` | 当前已做室内/校园配对的导航改动锚点 |
| `viz/xytheta-transparent-20261022` | `13b46a9` | 半透明体素回放和八方向审计，不是导航修改 |
| 原有`ht-stage-*`及`ht-garage-repeat-*` | 逐阶段保持原提交 | 48个历史实验归档锚点，对应同名Release |

`nav/*`是可追溯的算法里程碑，不表示所有场景通过。一个算法版本可以有多轮实验；一个实验Release也可能包括后补的视频。可视化补充不会改动原实验的候选提交或结论。

阶段47：实验入口`1ded85a`，HT导航`07c1abd`；阶段48：入口`f7fd77b`，HT导航仍为`07c1abd`。`develop`的`3f589d8`不能用这两轮旧数据代表验收。

## 怎样找到某次实验

1. 打开[实验总索引](experiments/catalog/INDEX.md)，选择阶段。
2. 看“归档标签提交”“记录的实验候选”“冻结清单”三项，复核实际导航、上游TARE版本、源码快照及patch。
3. 看原报告的采集、任务和验收状态。`RECORDED`、完整备份、车辆运动或视频可解码，都不自动等于导航验收通过。
4. 独立视频有直接下载链接、大小及SHA256。早期包内视频列出精确包内路径和SHA256，需要先下载对应数据包再解压。
5. 完整MCAP/NPZ及日志在同阶段Release；分片前缀与上传回执逐一对应。不同历史目录在同一Release中时，不能混拼分片。

早期62个目录关联到研究阶段，部分原始清单没有准确的测量提交；这类仅保留原始证据并标为待确认，不推断“阶段标签=测量代码”。失败、短录、中止和未运行记录不会被改成成功。

## 下载与校验

在[阶段详情页](experiments/catalog/INDEX.md)选定Release资产。例如只下载校园回放视频：

```bash
gh release download ht-stage-20261021-campus-matched \
  --repo CQULzz/HT_Explo --pattern 'stage48-xytheta-transparent-voxels-4x.mp4' \
  --dir stage48-video
sha256sum stage48-video/stage48-xytheta-transparent-voxels-4x.mp4
```

完整数据包格式按其清单区分：有`.tar`、`.tar.zst.partNNN`等。分片按数字顺序拼接，核对每片大小/SHA256后再解包；历史恢复细节见[legacy_archive/README.md](experiments/legacy_archive/README.md)。源码和小型报告在Git中，大MCAP和视频放Release，避免把大文件反复写进Git历史。

## 复现与验证命令

以下命令先从独立checkout执行；不要在有未提交改动的共享工作区直接切换版本：

```bash
git clone --branch main git@github.com:CQULzz/HT_Explo.git
cd HT_Explo
git show nav/tare-ht-20261021 --stat
python3 scripts/build_repository_catalog.py --check
python3 scripts/publish_version_notes.py --dry-run
python3 scripts/check_tare_waypoint_contract.py
```

`--check`用保存的远端快照核对生成索引，不访问GitHub；重新核对远端附件元数据并更新索引：

```bash
python3 scripts/build_repository_catalog.py --refresh-remote
```

它比较发布回执的大小、GitHub服务端SHA256与上传状态，**不重新下载所有载荷**。索引包含未出现在现有回执中的远端额外附件，不能把额外附件自动称为已由回执验证。

已验证环境为Ubuntu 24.04、ROS 2 Jazzy、Python 3.12。完整运行还依赖独立的CMU仿真、CuPy高程工作区和对应系统/模型依赖。构建入口为`bash scripts/build_standalone.sh`；原构建说明见[VALIDATION.md](../VALIDATION.md)。HT入口`ros2 launch tare_planner explore_ht.launch.py scenario:=campus`只启动TARE规划节点，不代替高程、HT推理、跟踪器或仿真。

原TARE/HT配对实验入口为`presentations/run_matched_tare_comparison.py`，参数：`--scenario indoor|garage|campus --output <新目录> --encoder <ffmpeg绝对路径> --domain <独立ROS域>`。每组固定600秒，要求源码干净冻结；运行前先按对应`frozen_job.json`及参数快照配齐独立依赖。本次整理不自动启动该实验。

## 后续维护

- 新导航修改从`develop`分支提交；冻结后按[AGENTS.md](../AGENTS.md)完成600秒、图表、视频和完整数据发布，再评估合入`main`。未通过的候选仍可保留，但必须写明失败。
- 新阶段增加`docs/version_history.json`条目、原报告、发布回执及Release，然后刷新总索引。禁止移动已有阶段标签来“补对应”。
- 新可视化工具放`visualization/*`；给旧实验追加视频须写清数据来源、回放提交及补充回执。
- 原48个Release说明增加统一索引入口，并保留原说明和全部附件。原README及版本页保存在[history](history)，其中旧“当前状态”只代表当时记录。
