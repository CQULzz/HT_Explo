# 实际标签接管起点先验：campus 300秒实验

版本11dd46d5561a0b426ebc800e192d9f42d0d8b00d。实际使用独立新HT桥（含ht_measured_valid）和explicit_labels_v1门禁。
圈内未知保留默认可通过先验，明确实际方向/占用标签持久替换；固定初始半径0.65m。圈外规则、地图TTL、TARE不变。雷达保持Helios32标称32×1800、仿真10Hz及外接框裁剪；不保留车体阴影。

## 探索结果

- 输入就绪后300.002104秒墙钟完整采集=True；冻结一致=True。
- 累计里程37.686604m；最后30秒0.000000m。
- 录包接收窗口速度命令15000条，非零3969；finish=True。
- 配准扫描3.5333Hz；HT地图3.5366Hz。
- 地图年龄抽样{"p50": 0.370419979095459, "p95": 0.5659873008728027, "max": 0.7353312969207764}；>1秒占0.00%。配准桥按主机时间重打戳，图龄不是物理测量延迟。
- 仿真实时因子约0.3535；300秒墙钟不代表300秒仿真。
- 观察器命令首个拒绝/放行原因：{"HT_ALLOWED": 15001}。
- 独立原图审计passed=True，计数{"maps": 1068, "command_audits": 15000, "allowed": 15000, "allowed_moving": 3969, "direction_rejection_examples": 25, "direction_distinct_rejections": 25, "direction_examples_map_matched": 25, "unresolved_commands": 0}。缺图未匹配不能写成审计通过，不以邻帧代替。
- 标签锚点及来源：{"anchors": [[-1e-09, 0.0, 0.65]], "policies": ["explicit_labels_v1"], "maximum_actual_label_cells_in_current_window": 725, "maximum_prior_cells": 585, "all_ready": true, "command_samples": 15001}。
- 最终恢复诊断：null。
- 观测自由体积代理3645.625m³；是采样射线观测量，不代表真实覆盖或地面可通行性。

## 证据

MCAP独立读取/可用CRC通过；metadata计数一致=True；归档逐文件与冻结清单一致=True。
launch退出码0；干净退出=False；相关残留0，子节点错误见CLEANUP.json。
预算关闭：1/2次启动，未自动追加探索候选。
完整录包、源码与资产冻结在/home/lzz/ht_labels_300s_20261116/runs/explicit_labels_campus_300s_01。独立视频阶段从本次实际录包生成RViz双视图、全程4倍速，并注明观测投影不等于可通行性。
视频已完成：实际RViz双窗口、完整4倍速80秒、1920×1080/20fps、1600帧全片解码通过，10/40/79秒画面抽查通过。详见VIDEO_VALIDATION.json。Windows只保存精简记录和视频，不新增Release或上传原始MCAP。

本次是单场景300秒短测；不代表普遍探索优劣、实车安全、完整恢复或返航验收。初始先验为用户指定假设。

## 完成与返航时间

TARE在52.101秒发出finish信号；最后一个非零速度采样约79.679秒。最终车体中心距初始中心约0.267m，后续保持停车。末段内部计数uncovered/frontier/exploring/routable均0、local_complete=1，但没有独立场景真值覆盖核验，不能据此认定整个campus完全探索。

## 视频文件

`D:/HT-Labels-300s-20261116/video/rviz_exploration_full_4x.mp4`，约12.53MB。全程保留300秒采集内容及末尾停留，不删减返航/停车段；图例明确绿色近地观测投影不代表可通行性。视频/MCAP仅本地保存，本轮仓库只上传精简结果和复现脚本。

## 补充上传材料与交接

新增[交接文档](HANDOFF_zh.md)、原样关键日志、指标图、首末原始HT地图快照，以及从本次完整冻结归档逐文件校验提取的`runtime_source_config.tar.gz`。源码配置包约1.55MB，包含实际运行源码/配置/权重，排除二进制、场景大资产、视频和MCAP，具体见`SOURCE_BUNDLE_MANIFEST.json`。`PUBLICATION_SCOPE.json`列出精简材料大小和SHA256；不代表原始录包已完成远端备份。

`START_SUPPORT_DIAGNOSIS.json`与`start_support.png`是此前crop_box 60秒的起点缺测诊断，用于解释先验半径；本次300秒原图另存`data/ht_map_first.npz`和`data/ht_map_last.npz`，没有写入执行先验或持久标签。
