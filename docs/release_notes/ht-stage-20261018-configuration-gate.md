# 阶段23｜HT配置得分与物理障碍分层：恢复推进，仍有短停

实测代码`149566de09c48a528140b6ec950c08c5fa29539c`，结果归档`68746de`。此标签固定候选代码，不表示稳定验收。

## 改了什么

新增独立ht_obstacle层；HT参考位置/车头方向得分按0.5硬门槛查询，实测障碍和缺测仍保留0.6m足迹检查；修正启动先验混用观测支持的额外漏洞。

## 实现了什么功能

将整车方向预测与点障碍分开处理；不再把相邻车辆配置低分作为点障碍二次膨胀。概率门槛、物理障碍、缺测和3秒时效约束仍生效。

## 实验与验证

390项核心、25地图/规划、11跟踪器回归及5实际快照通过；室内完整600秒134.00m、3170.500m³，BLOCKED抽样7.8%，212次晚拦截均发零。

[通俗报告](https://github.com/CQULzz/HT_Explo/blob/codex/ht8dir-v1/docs/results/ht_configuration_gate_10min_2026-10-18/REPORT.md) · [同条件对比图](https://github.com/CQULzz/HT_Explo/blob/codex/ht8dir-v1/docs/results/ht_configuration_gate_10min_2026-10-18/comparison/comparison.png) · [视频](https://github.com/CQULzz/HT_Explo/releases/download/ht-stage-20261018-configuration-gate/ht-stage-20261018-configuration-gate-indoor.mp4)

本页附件提供完整本轮记录目录的raw.tar、精选结果results.tar、逐文件SHA256与录像。录制范围为全频已发布HT/控制/位姿/状态、按源秒抽样激光和周期地图快照，不能表述为全部原始激光/CuPy输入。tar分卷时先按part编号合并再解包。本地原件与失败记录均保留。

## 存在什么问题

最终约2秒BLOCKED，未观察其未来恢复；最长全零6.20s，HT地图年龄最大约5.996s，规划P95 1.616s。无探索完成或多场景/实车稳定性结论。

车辆动力学仅含运动学搜索与执行限速/限加速度，参考点和方向独立物理标定尚未重新验收。
