from pathlib import Path
import json,csv,math
ROOT=Path('/home/lzz/ht_recovery_20261111');OUT=ROOT/'delivery'
def read(p):return json.loads(Path(p).read_text())
a=ROOT/'runs/cmu_recovery_300s_01';b=ROOT/'runs/cmu_recovery_300s_02';sa=read(a/'observations/SUMMARY.json');sb=read(b/'observations/SUMMARY.json');aa=read(a/'COMMAND_AUDIT.json');ab=read(b/'COMMAND_AUDIT.json');ma=read(a/'PUBLISHED_COMMAND_MATCH.json');mb=read(b/'PUBLISHED_COMMAND_MATCH.json');fixture=read(ROOT/'analysis/FIXTURE_AUDIT.json');episodes=read(ROOT/'analysis/RECOVERY_EPISODES.json');ep=episodes[b.name]['episodes'][0];stop=read(ROOT/'analysis/final_stop/RESULT.json');preview=read(ROOT/'analysis/final_stop/PREVIEW_CHECK.json');raw=read(ROOT/'evidence/RAW_SHA256.json')
report=f'''# HT局部搜索与动作执行：问题二修复及300秒实验

2026-11-11。独立分支 `sim/ht-local-recovery-20261111`。结论：**局部恢复能力已在旧现场回归和一次实时仿真中验证；持续探索尚未通过，修正版后段因当前车位进入HT占用膨胀范围而停车。**

## 先澄清“方差”

此前“方差过大”指高程地图的高度估计方差，单位m²，用于表示高度估计不确定性；它不是HT输出分数的统计方差。高程方差0.25m²对应高度标准差0.5m，与HT通过分数0.5没有量纲关系。模型目前是确定性单次推理，没有输出用户提出的“同方向多次扰动预测分数标准差”。

**本轮按用户“问题二先改”修改局部搜索与执行；没有实现HT分数的 μ−σ 判据，没有把高程标准差加减到HT分数，也没有改变高程质量、硬占用、未知和地图时效规则。** 之前用“方差”简称两个不同变量造成了歧义，本报告明确区分。

## 修改内容与边界

- `ht_recovery.hpp`：围绕实际车位，在约4厘米地图步长的 `(x,y,yaw)` 状态空间做有界A*搜索。包含八个车头朝向、前进、倒车、原地转向；旋转过程连续查询HT，不能跳过低分朝向。搜索半径3米、预算20ms；失败不等于连续空间无解。
- 路线保留车头朝向，进退由位移与车身朝向的符号确定。连续共线段合并；独立执行器按转向/移动段闭环执行，使用实测位置、朝向判定段落完成。恢复命令由该执行器直接产生，恢复路径可视化不再交给旧XY跟踪器重新解释。
- 发布前用同一跟踪控制律模拟整段路线，并检查其反应/制动预测；实际执行时再次检查每条最终命令。内部预测关闭审计输出以免把模拟命令混进实测审计，实际输出检查保持开启。
- 原生局部命令连续0.4秒没有可接受的非零运动后，才从静止接管。恢复速度0.15m/s、角速度0.5rad/s；正常恢复轮廓线/角加速度上限2.5m/s²和3rad/s²。失效或取消时停车；不从未知/占用起点强行逃逸。
- 增加0.2秒里程计时效保护。地图仍为1秒TTL、HT分数0.5、有效性半径0.45米＋原栅格余量，保留任务边界。恢复完成以实际子路线执行结果计数，不把原地转向或触发过搜索当作成功。
- TARE目标、覆盖与探索完成判据不改；接收TARE目标。当前前缀仍朝新目标取得进展时继续执行；目标变得不兼容或任务结束则取消/停车。没有向TARE回写完成或更换目标顺序。

本地恢复的 `COMPLETED` 是一次局部动作完成，独立于 `/exploration_finish`，不代表探索完成。`progress_m` 是到上次恢复起点的距离，交回正常跟踪后仍可能增长；本报告只使用相应EXECUTING起点和首次COMPLETED事件计算恢复位移，不把后续正常行驶算进去。

## 离线回归：原有可行前缀现在能执行

使用旧indoor停车位置的原始HT消息，旧原生命令及其角速度投影仍被拒绝。新搜索得到路线，并由连续速度命令、CMU同款200Hz“先更新yaw再积分XY”的模型闭环执行。

| 项目 | 结果 |
| --- | ---: |
| 执行用时 | {fixture['simulated_duration_s']:.2f}s |
| 净位移 | {fixture['movement_m']:.6f}m |
| 向启动时目标推进 | {fixture['goal_distance_reduction_m']:.6f}m |
| 独立核验的非零命令 | {fixture['moving_commands']} |
| HT扫掠越限 | 0 |
| 最低扫掠分数 | {fixture['minimum_swept_score']:.6f} |
| 最大线/角加速度 | {fixture['max_linear_accel']:.3f}m/s² / {fixture['max_angular_accel']:.3f}rad/s² |

这是固定记录地图下的控制闭环回归：HT查询时钟固定在原快照有效时间，不改变原消息时间戳，不代表13秒内有新的传感器观测或验证了长期TTL。测试还合成了目标发布间隔和兼容目标更新，以验证TARE的目标保持语义。不是轮地接触动力学或实车通行验证。

原24项门禁/边界检查＋9项恢复回归通过，共33项。新增回归覆盖：旧拒绝命令、新执行进展、非周期目标保持/兼容更新、里程计与地图过期、倒车保持实际车头通道、反向新目标取消、未知和占用起点拒绝；倒车回归同时使用20ms/1ms/19ms控制周期抖动检查加速度限制。

离线开发中发现并修正了陈旧里程计检查被目标过期提前返回跳过、靠近目标时恢复被提前退出的问题；原失败日志保留。独立Python回归审计曾因NumPy布尔值不能JSON序列化而失败，修复的是报告序列化，没有改判定结果。没有把失败日志删除后当成首次通过。

![旧现场控制执行](stalled_pose_execution.png)

## 按用户要求进行300秒完整仿真

每轮代码、二进制、参数与场景冻结，记录完整300秒。原先600秒要求由本次用户明确的5分钟覆盖。旧账本不重置，本批最多两次正式启动，实际2/2。

| 版本 | 时长/s | 里程/m | 采样自由体积/m³ | 结束状态 |
| --- | ---: | ---: | ---: | --- |
| 首轮，`31ce321` | {sa['elapsed_s']:.3f} | {sa['distance_m']:.3f} | {sa['sampled_free_volume_m3']:.3f} | 仍探索，但发现新增目标超时语义缺陷 |
| 修正版，`5d91b4b` | {sb['elapsed_s']:.3f} | {sb['distance_m']:.3f} | {sb['sampled_free_volume_m3']:.3f} | 完成1次恢复，后段HT占用阻塞，finish=false |

首轮暴露：TARE初始两次目标消息相隔约5.2秒，我新增的3秒目标超时不符合这种非周期目标发布方式，会提前退出恢复，退出事件还漏记。首轮恢复只触发，不能计为完成。完整首轮记录保留；取消这个错误超时、支持兼容目标更新并补齐退出诊断后，使用第二个300秒名额作必要复测。总启动上限保持两次，没有第三次。

场景、起点、传感器、原生TARE和指标口径一致，但轨迹、观测、调度和后续目标不同；单次里程差不能证明算法普遍优劣。图中的历史HT独立结果是旧600秒记录里最后一条≤300秒的截取，不是新跑的原生基线。自由体积是统一采样射线体素并集，不是覆盖真值。

![轨迹对比](trajectory_comparison.png)

![进展对比](progress_comparison.png)

## 实时恢复成功的具体证据

修正版在任务约 **{ep['start_elapsed_s']:.3f}秒**启动恢复，约 **{ep['end_elapsed_s']:.3f}秒**完成：

- 耗时 **{ep['duration_s']:.3f}秒**；净位移 **{ep['net_displacement_m']:.6f}米**；到启动时固定TARE目标的距离减少 **{ep['fixed_initial_goal_distance_reduction_m']:.6f}米**。
- 路线包含转向、短距离移动、再次转向和前进，实际发布的5个位姿保留车头朝向。实际里程计与计划对照见图；不是将固定动作硬编码到这个地点。
- 期间 **6次兼容目标更新**保持当前前缀，未重启恢复。该次完成前没有HT执行失效或目标取消；搜索约14.975ms，处于20ms预算内。
- 恢复完成后交回原有正常跟踪，任务仍为探索；没有发布探索完成信号。

![实时恢复](online_recovery.png)

视频和图背景使用恢复启动时的HT占用快照，轨迹来自随后实时里程计；实际逐命令检查使用不断更新的各自原始HT消息，不能把背景快照当作整个片段唯一地图。

## HT门禁与发布命令审计

| 项目 | 首轮 | 修正版 |
| --- | ---: | ---: |
| 独立核验的候选审计记录 | {aa['counts']['command_audits']} | {ab['counts']['command_audits']} |
| 非零放行候选 | {aa['counts']['allowed_moving']} | {ab['counts']['allowed_moving']} |
| 独立HT越限 | 0 | 0 |
| 原图未匹配的候选 | 0 | 0 |
| 放行扫掠最低分 | {aa['minimum_allowed_swept_score']:.6f} | {ab['minimum_allowed_swept_score']:.6f} |
| 放行最大地图源龄/s | {aa['maximum_allowed_source_age_s']:.6f} | {ab['maximum_allowed_source_age_s']:.6f} |
| HT接收源龄P95/s | {sa['ht_source_age_s']['p95']:.6f} | {sb['ht_source_age_s']['p95']:.6f} |

修正版 **{mb['published_nonzero_commands']}条记录的非零输出全部关联到已通过的候选**：速度相等、接收时间相近，再独立重算候选对应精确HT原图的车身朝向、足迹、反应与制动扫掠。最大接收关联时间差约{mb['maximum_receive_time_delta_s']*1000:.2f}ms，控制时刻距命令里程计头最大约{mb['maximum_control_minus_odometry_stamp_s']*1000:.2f}ms。相同速度连续重复时，近邻关联不保证唯一发布对应。

首轮关联器留有1条窗口边界输出未匹配：命令里程计头在300秒内，录包接收稍晚于最后采样时刻；候选审计按控制时刻截取。保留严格关联失败结果，没有宣称首轮所有输出都核验通过。不同候选审计和实际输出数量不要求一一相等，原生候选可能在恢复接管或时效保护后未发布。

上述核验不能升级为HT网络真实地形准确率、车辆实际连续运动无风险或实车制动标定通过。

## 后段为什么仍停

修正版最后非零运动命令约在264.20秒，停在 `(14.63112,48.77520)`，到300秒仍finish=false。最终HT图中当前方向45°通道为 **{stop['eight_scores'][1]:.6f}**，观测支撑/上下文有效，但一个邻近占用格点经原有足迹膨胀覆盖了当前车位，因此零命令的起点检查也返回 `HT_OCCUPIED`。恢复不会绕过这个起点否决。

匹配到同一源时间戳的原始高程：格点约 `(15.06433,48.63158)`，高度0.8414m，方差1.1683m²，观测龄约35.6秒，质量筛选拒绝。官方场景预览点云在该位置15厘米内有36个点，高度范围约−0.043至1.052m，其中有约0.843m高点；因此**不能仅因为方差高就说它是假障碍，也不能直接把本次占用当成之前PCD平地误拒的同一反例**。

目前明确的是“当前位姿被占用包络否决”，没有核定该格点应否清除、真实车体能否绕行或如何在新观测使起点无效时安全退出。本轮没有降低门限、缩小车体包络或放开占用起点来制造通过。局部恢复功能已有成功证据，但原硬占用/高程质量问题和持续探索验收仍未完成。

## 版本、复现与数据

- 源码工作树：`/home/lzz/HT_Explo_recovery_20261111`；测试导航版本`5d91b4b`。报告后的源码哈希再次与该版本核对，控制代码未改。
- 数据根目录：`/home/lzz/ht_recovery_20261111`。完整MCAP、参数、FREEZE、frozen_runtime、COMMANDS、CSV、全部失败/成功日志、旧现场回归、实时恢复原始轨迹/计划、最后占用源帧均保留。
- 两轮原始录包文件合计 **{sum(v['bytes'] for v in raw.values()):,}字节**，逐文件SHA256在`evidence/RAW_SHA256.json`。最后冻结153个文件保持不变，两轮完整采集。
- 仅清理了可重新下载的pip wheel HTTP缓存3,010,129,982字节，包名/版本/大小/SHA已记账；没有卸载依赖或清理实验原始数据。此前其他实验目录仍保留。
- 原main、实车和先前实验分支不改。新分支只提交代码、配置和精简证据，不创建Release，不部署实车。完整新MCAP和视频仍在本机，未宣称完整远端备份。
- 仿真期间未检测到导航子进程提前退出；采集完整后停止。停机阶段仍有既有CMU context退出-6和sensorScanGeneration退出-11，以及未使用相机插件依赖问题；顶层0不能代表每个子进程正常退出。
- CMU采用直接速度积分/设置模型姿态，本次没有新增轮地接触动力学或实车验收。八朝向格点、有界搜索和短测不保证所有连续可行路线都能找到。
- 本批2/2启动结束，仿真与专用Xvfb已停，账本关闭，不自动继续下一轮。

## 图与视频

- [实时仿真中的恢复片段](online_recovery.mp4)
- [完整300秒轨迹记录，10倍速](recovery_300s_10x.mp4)
- [旧停车地图控制回归，固定地图](stalled_pose_execution.mp4)

视频是实际记录数据可视化，不是相机/RViz录像；实时片段与固定地图回归分开标注。所有最终视频完整解码检查，格式与帧数见VIDEO_CHECK.json。
'''
(OUT/'REPORT.md').write_text(report)
summary={'branch':'sim/ht-local-recovery-20261111','tested_navigation_commit':'5d91b4b','problem_two_recovery_demonstrated':True,'continuous_exploration_accepted':False,'probability_std_inference_implemented':False,'fixture':fixture,'episodes':episodes,'first':{'result':read(a/'RESULT.json'),'audit':aa,'published_match':ma},'final':{'result':read(b/'RESULT.json'),'audit':ab,'published_match':mb},'final_stop':stop,'preview_check':preview,'budget':read(ROOT/'BUDGET.json')}
(OUT/'SUMMARY.json').write_text(json.dumps(summary,indent=2));print(OUT/'REPORT.md')
