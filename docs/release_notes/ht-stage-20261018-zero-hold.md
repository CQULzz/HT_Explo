# 阶段21｜拦截命令归零与32航向：修正缺陷，仍有停滞

标签固定实测源码`67ade71`，证据归档`b15c06a`；实际停车消息修复`8e8d2b7`，评估修正`37f0d42`。这是实验版本，不是稳定性验收。

## 改了什么

旧跟踪器晚HT检查拒绝候选控制弧后，只清零内部速度，却发布了已填入非零速度的消息。现明确清零待发Twist的全部六个速度分量。另将搜索从16改为32航向，保留原8通道HT、硬概率门槛、未知区与地图时效要求。

长测激光原本已按绝对源秒采样，评估器再按实验相对秒挑帧会重复丢帧；现长测评估保持原源秒采样，并冻结评估脚本哈希。加入实际拒绝速度、完成队列和全频HT输出的证据记录。

## 实现了什么功能

被拒绝的运动真正收到零速度消息，不再因为该晚分支错误持续微动。真实冻结地图回归证明32航向能够找到16航向漏掉的HT允许路线。额外角度余量和同弧退路检查仍默认关闭，未用放宽硬门槛来掩盖无路。

## 实验与验证

旧实现的晚拒绝分支回归失败，修正后通过；384核心检查、21个ROS用例和8个跟踪器用例通过，4个真实快照均参与。旧联合候选600秒记录有146次拒绝后非零速度；只修消息后的600秒对照37次晚拒绝全部发零，但仍BLOCKED。

同一数据包的评估处理数576→600、跳过0，体积1217.250→1218.250m³，原始轨迹与指令不变。此前两个历史比较轮都已有600个有效分箱，不能用这项统计错误解释其41.8%差异。

最终室内600秒6.64m、432.875m³仍BLOCKED；隧道600秒79.00m、621.375m³，约230.53秒返航完成。19次晚拒绝全部配对且实际发零。室内第29.967秒同世界位姿因新HT地图概率0.998709→0.100057而被拒，新图年龄约0.336秒；上游具体来源尚无完整同源输入证据。

最终室内、隧道每组600秒及15fps视频以[完整实测报告](https://github.com/CQULzz/HT_Explo/blob/codex/ht8dir-v1/docs/results/ht_zero_twist_fine_heading_10min_2026-10-18/REPORT.md)为准；采集与解码核验不等于探索成功。

## 存在什么问题

32航向只解决一张冻结地图的HT漏路，不能推断所有地形或目标可达。HT可能禁止当前姿态，导致搜索起点拒绝；仍须区分地图更新、实际移动与模型语义，不能统一说是算力不足或3秒超时。原215秒收尾未复现，完成条件未改；没有把全局返航提示当作全覆盖证明。

退路、航向余量及联合候选的失败记录均保留；未满600秒的中止场景不作10分钟通过。没有实车或更长时间稳定性验收。

[通俗修复说明](https://github.com/CQULzz/HT_Explo/blob/codex/ht8dir-v1/docs/fixes/2026-10-18_late_hold_zero_twist.md) · [原因核查、反例、回归及数据](https://github.com/CQULzz/HT_Explo/blob/codex/ht8dir-v1/docs/results/ht_completion_cause_audit_2026-10-18/REPORT.md)

室内进一步逐格核对：车位中心概率前后均约0.999846，实际变化是8个原来神经预测无效、物理已观测的邻格开始有有效低概率，经足迹聚合将当前位姿否决。这个预测有效范围与足迹门槛接口尚未修改，不能把聚合最小值下降说成中心预测突变，也不能直接认定噪声或重复膨胀。

<!-- legacy-full-data-start -->
## 历史完整实验数据补归档（2026-10-20）

本阶段关联的 **3 个历史目录**已作为本 Release 的 `legacy-*` 分卷附件补齐，并核对远端大小与 SHA256。

**阶段归属不等于标签就是实际测试提交。** 原始 manifest、测试提交、未提交补丁、源文件哈希、真实时长和失败/中止说明均保留在逐文件清单与数据中；没有证据的提交号仍标为未知。本次仅补数据，不改变原实验结论或标签。

[全部62目录的版本对应、逐文件清单、校验回执与下载恢复方法](https://github.com/CQULzz/HT_Explo/blob/codex/ht8dir-v1/docs/experiments/legacy_archive/README.md)

| 历史目录 | 原始文件GiB | 完整数据前缀 |
|---|---:|---|
| `ht_zero_twist_fine_heading_10min_2026-10-18_02-28-07` | 1.9352 | `legacy-ht_zero_twist_fine_heading_10min_2026-10-18_02-28-07-8bf856929ce9` |
| `ht_zero_twist_verified_10min_2026-10-18_02-13-23` | 0.0000 | `legacy-ht_zero_twist_verified_10min_2026-10-18_02-13-23-945969142b1f` |
| `ht_zero_twist_verified_10min_2026-10-18_02-15-15` | 0.8191 | `legacy-ht_zero_twist_verified_10min_2026-10-18_02-15-15-d396d8641816` |

下载同一前缀的全部 `.tar.zst.partNNN`、`-files.json` 与 `-verified.json`；核对回执后按数字顺序合并解压。大MCAP/NPZ在Release附件，未加入Git历史。
<!-- legacy-full-data-end -->

<!-- repository-catalog-start -->
## 代码、视频与完整数据的对应关系

- [阶段21完整索引：实际实验候选、导航代码、报告、视频及数据回执](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/catalog/stage-21.md)
- [本阶段归档源码](https://github.com/CQULzz/HT_Explo/tree/67ade71c10caa8a8923b9fe9c663d10a9ec75568)：`67ade71c10caa8a8923b9fe9c663d10a9ec75568`。这是归档锚点；实际测量源码、运行patch与二进制哈希以原清单为准。
- [完整实验总目录](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/catalog/INDEX.md) · [分支和标签规则](https://github.com/CQULzz/HT_Explo/blob/main/docs/REPOSITORY_GUIDE.md)

早期历史目录只关联到研究阶段，未知测量提交保持待确认；补充回放视频不代表新的导航实验。原有报告、失败记录与全部附件保留。
<!-- repository-catalog-end -->
