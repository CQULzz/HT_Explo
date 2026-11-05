# 给原 Linux Codex 对话的项目同步说明

更新日期：2026-11-05（北京时间）。本文是当前交接入口；历史交接已[单独归档](docs/experiments/handoffs/linux_codex_handoff_history_20261105.md)，不要把旧阶段的暂停、600秒、逐轮Release或“本轮完成”误认为当前状态。

## 给接手对话的第一条说明

你是原 Linux 聊天 `01a1a5cc-f846-7723-8735-190876a2c2f5`（此前记录名称“排查车辆移动后停止问题”）。用户把 Windows/WSL 端后续工作交接回这个原对话。请先读本文及循环6报告，确认项目现状，再回复保留改动、实测结果和待办。本次交接请求只是同步说明，不要仅因收到本文自动启动新实验、合并分支、覆盖 Linux 本地源码或重新发布旧数据；用户另有继续指令时按其授权推进。

**当前结论：建图时效这一项已在三组同条件对照中改善并达标；完整探索、可靠完成判据的全场景验证和评分/路径停车仍未全部解决。没有实车验收或部署。**

## 仓库、版本与阅读顺序

| 项目 | 当前值 |
|---|---|
| GitHub | https://github.com/CQULzz/HT_Explo |
| 本次代码/结果分支 | `fix/scout-wsl120-20261105` |
| 最近完整结果提交 | `e05399a05eba0baa7116c14534425622a36b1646`，已推送并核对远端 |
| 六轮正式实验实际冻结提交 | `7a6a7737d10649fcbac4228cbcf5ecc3eaf09325` |
| 最新保留导航修复 | `eb847992f1cb0d61667a1a37c9b667012568d10c` |
| 可选建图调度实现 | `ec1a14564f6687d9946a50bd48b5cd5ebdc1ddbb` |
| 本文后续提交 | 仅交接文档更新，不是新的实测算法版本；以 `git log -1 -- LINUX_CODEX_HANDOFF.md` 查询 |

先读以下资料，最新结果优先，历史只用于溯源：

1. [循环6最终状态](docs/results/wsl120_cycle6_20261105/STATUS.md)、[三组配对变化](docs/results/wsl120_cycle6_20261105/PAIRED_COMPARISON.md)、[总对比图](docs/results/wsl120_cycle6_20261105/PAIRED_OVERVIEW.png)。
2. [循环5前沿/窗口与几何诊断](docs/results/wsl_offline_cycle5_20261105/REPORT.md)、[循环4调度设计与离线验证](docs/results/wsl_offline_cycle4_20261105/REPORT.md)、[循环3剩余收益抽样修复](docs/results/wsl_offline_cycle3_20261105/REPORT.md)。
3. [循环2边界完成判据及失败记录](docs/results/wsl120_cycle2_20261105/STATUS.md)、[先前WSL恢复/优化阶段](docs/results/wsl120_20261105/STATUS.md)、[迭代总表](docs/experiments/ITERATIONS.md)。
4. `AGENTS.md` 按最新阶段及用户原话理解；后来的120秒、提交推送但不自动Release/部署要求覆盖历史相冲突的600秒/逐轮Release要求。

## 已经做过的事与保留代码

- 原额度中断的600秒实验已经从**真正双系统 Linux 的只读资料**恢复并完成原有GitHub交付，不能再当成未上传任务重复执行。原Release为 https://github.com/CQULzz/HT_Explo/releases/tag/ht-scout-pcd-fix-20261105-v1 。它对应原600秒结果，不代表后续两分钟实验的数据已上传。
- 随后用户授权在**独立WSL**恢复ROS2/CUDA/CuPy并迭代。曾完成GPU射线初始化、整数地图移位及输入适配排队优化；HT使用显式 `--ht-processing-mode worker`，避免推理占住接收线程。详见早期WSL阶段报告。不要用WSL重建的CuPy源码覆盖原Linux定制核心。
- 完成选择入口三处 `>` 修正为 `>=`：匹配原已接受的40个表面点/15个前沿点门限。生产规划路径反例确认原实现会在恰好达标、可达且未访问的任务上错误报局部完成，修复后指定反例通过。
- 剩余抽样范围改用删除、重算后的 `queue_copy`，避免用原队列大小/旧收益选入无效目标、重复/漏选；32个固定种子的指定收益反例通过。
- 前沿继续选择改用前沿自身15点门限，修复15..39点残余任务被表面40点门限截停；构造时拒绝非正采样窗口，默认3不变。四种子×14/15/39/40边界及表面40控制通过。
- 新增可选**串行建图执行器＋独立TF接收节点**。TF节点继承context、namespace、ROS时钟与TF/clock重映射；初始化/异常退出清理有测试。独立接收使地图回调等精确TF时仍能收到变换，地图操作不再在同一锁下堆积多线程竞争。

代码位置：

- `src/tare_planner/src/local_coverage_planner/local_coverage_planner.cpp`、`tare_original.cpp` 及相应测试。
- `tools/ht_cupy_bridge/map_worker.py`、`cupy_to_ht.py`：已有HT worker模式。
- `tools/pcd_sim/mapper_execution.py`、`install_mapper_execution.py`、`mapper_execution_manifest.json`、`run_sim.py`：新建图模式、哈希保护安装器与运行入口。

**选择模式须显式传参：** HT用 `--ht-processing-mode worker`，新建图用 `--mapper-executor single`；建图CLI/包装器默认仍是 `multi`，实车默认配置未切换。只拉取仓库不会自动修补外部runtime或CuPy安装；`install_mapper_execution.py --runtime <实际runtime>` 默认只检查，加 `--apply` 才准备包装器/helper，且不会启动任何进程。

安装器只接受已知wrapper/helper SHA256，未知本地差异、软链或混合状态会拒绝，不能强制覆盖。独立CuPy核心和原Linux定制源码仍须逐文件比对后移植。原Linux的ROS版本/API可能与Jazzy不同，不要直接套用WSL中的私有executor清理细节或软链接路径。

## 最新六次120秒实测

同一导航、场景、参数、模型和产物冻结；371个文件的哈希映射六次完全相同。仅切建图模式，TARE/Gazebo固定42/99种子，42复跑。固定种子不能消除ROS/GPU调度和重建差异。

| 配对 | multi源龄P95（秒） | single源龄P95（秒） | 降低 | 体积代理 multi→single（m³） |
|---|---:|---:|---:|---:|
| 种子42首次 | 0.7780 | 0.5180 | 33.42% | 408.240→631.040 |
| 种子99 | 0.9725 | 0.6420 | 33.98% | 482.024→947.752 |
| 种子42复跑 | 1.0500 | 0.5525 | 47.38% | 716.088→417.296 |

新模式三次均正常退出、文件冻结无变化，P95都低于原1秒门限；这项在当前WSL批次达标。实际pose/time回调约1200次/120秒，旧模式time仅14–107次、pose57–440次，说明定时回调饥饿明显缓解。点云回调墙钟均值约47–65ms，对照150–210ms，含锁/调度等待，不能说成纯GPU耗时。

**不要把上表误读成总体探索已改善：** 体积变化为+54.58%、+96.62%、-41.73%，复跑有明确退步；single三次只有一次内部完成。仍出现 `HT_CURRENT_HEADING_LOW_SCORE`、`PATH_NO_EXECUTABLE_ROUTE`，旧模式还出现支撑缺失/地图过期停车。single99行驶26.08m后无可执行路径；single42复跑17.6秒内部完成、最终体积417.296m³。内部COMPLETED不是全景覆盖证书，较早完成/走得更远均不能单独证明所有可达任务已完成。

主源龄指标保持既有HT生产者**1Hz遥测** `source_age_at_publish_s`；全率录包端 `DELIVERY_AGE` 只作诊断，不能切换评价口径制造通过。自由体积是采样射线体素并集代理，里程含初始沉降，不是独立真值覆盖率。只有两种子、三对，未做长期/多场景/实车或ARM验证。

首次旧模式 `multi42_b01` 的observer退出码-2：完整录至120.3秒，MCAP计数/可用CRC/SHA、视频完整解码及15个数组档案读取均通过，但仍保留FAILED标记，不能称干净通过；其他五次所有受管进程退出0。

已有验证：20项Python调度/TF/安装/发布合同检查通过，最新导航完整9组CTest通过（含完成/未知/几何/过期图/返航控制回归）。本次冻结与这些已测源码/产物匹配，没有为文档更新重新跑测试。

## 下一步应解决什么

1. 优先解释新模式下的朝向低分、支撑缺失、无可执行路径，以及同种子探索量大幅波动。把传感观测、HT支持/方向概率、TARE任务资格、严格路径可行性、最终状态对齐到同一时刻，再提一个可检验假设。不要用全场景剩余点数直接证明“当前有已确认可达的未完成任务”。
2. 完成判据虽修了明确边界/队列反例，但尚无所有场景都不提前完成的证明；后续应验证已确认可达任务的任务级进度和正常返航，不能仅看COMPLETED标记。
3. 旧几何停车已有测量依据：旧99末段点距车约0.7845m，落在原0.8414m圆柱包络及±0.5m高度内，见循环5证据。记录器的云/位姿配对不等于精确跟踪器回调顺序或独立碰撞真值；不要直接缩小包络、豁免当前位姿或删除拦截来“解决”停车。
4. observer退出有清理竞争窗口：先写DONE，再finally释放视频/保存数组/销毁节点，runner看到DONE就发SIGINT。实际原因还需单独核验并修复；不能将退出码强行归零或覆盖失败数据。本批次中没有改采集器，保持对照一致。

后续WSL排查优先显式使用已验证的single模式，保留multi对照；真实Linux移植先验证环境和本地差异。**本次6次测试边界已结束，当前没有在跑的仿真；本次同步说明不自动授权新一轮。** 用户另行要求继续时，保持每次完整120秒，先诊断、必要回归、冻结、同条件对照、保留失败再推送。

约束继续有效：严格未知、概率0.5、1秒时效、固定1.5m/60秒启动许可/锚点、校准外参/权重不放宽；除已证明的正确性修复，不任意改TARE原生目标/TSP策略。不得自动合并到其他分支、强推、发布Release或部署设备。

## 数据在哪里，以及原Linux拿得到什么

以下是**Windows内WSL Ubuntu-24.04**的路径，不是原双系统Linux路径：

| 内容 | WSL位置 |
|---|---|
| 当前源码 | `/home/w_lzz/ht-iterations-20261105/repo` |
| 独立运行目录 | `/home/w_lzz/ht-iterations-20261105/runtime` |
| 当前环境入口 | `/home/w_lzz/ht-iterations-20261105/runtime/env.sh` |
| Python环境 | `/home/w_lzz/ht-iterations-20261105/venv` |
| 独立CuPy工作区 | `/home/lzz/my test/ht_cupy_gpu_ws_20261028` |
| 最新原始数据/本次账本 | `/home/w_lzz/ht-iterations-20261105/cycle6` |
| 之前循环2原始数据 | `/home/w_lzz/ht-iterations-20261105/cycle2` |

WSL运行环境为ROS2 Jazzy/CUDA/CuPy，HT使用RTX5060Ti，Gazebo为EGL/llvmpipe；详情按各轮manifest/环境记录核对。WSL中的 `/home/lzz/HT_stop_fix_20261104/project` 等兼容目录是链接，不能据此覆盖原Linux同名目录。

GitHub当前分支含代码、安装补丁、精简报告、图、哈希/采集核验及命令。**循环2和循环6最新大MCAP/MP4/CSV/地图快照/资源原始日志没有Release或完整远端备份，只留WSL；不能清理，也不能宣称GitHub已有全部最新原始数据。** 原Linux启动后不会天然看到这些WSL路径。需要原始数据时从Windows/WSL另外导出到共享分区并核对SHA，或另按用户要求传输；本次只同步说明，没有复制/上传GB级原始数据。

早期原600秒及WSL r00–r07已有对应Release/校验回执，见早期报告和[历史归档](docs/experiments/handoffs/linux_codex_handoff_history_20261105.md)。不要把早期Release当成本次循环6备份。

## 原Linux安全获取说明的方法

先在实际项目中检查状态和remote，保留本地定制源码、未提交改动和独立CuPy差异。可只获取远端并阅读，不切换/覆盖工作树：

```bash
git status --short --branch
git remote -v
# 确认origin为上面的HT_Explo仓库后：
git fetch origin refs/heads/fix/scout-wsl120-20261105:refs/remotes/origin/fix/scout-wsl120-20261105
git show origin/fix/scout-wsl120-20261105:LINUX_CODEX_HANDOFF.md
git diff --stat HEAD origin/fix/scout-wsl120-20261105
```

本说明不要求reset、clean、强制checkout、合并或重写任何原Linux聊天/源码。先比对，再按用户接下来的任务选择如何移植；不要盲目pull覆盖本地定制实现。

原Linux聊天不会自动知道Windows/WSL发生了什么。**只有用户把本文/链接交给原对话、并由原对话读取后，才算它实际接收了同步；此文件没有篡改、注入或伪造原聊天JSONL。** 本文不含密码、令牌或凭据。
