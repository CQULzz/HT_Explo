# 完整原始数据保存方式

用户于2026-10-19确认：GitHub保留全部完整数据，本机保留最近两轮。报告、对比图、可播放MP4和必要回归样本继续保留在仓库中。正在写入、上传或使用的目录不清理；未核对完整远端备份的数据也不删除。

`prune_published_ht_raw.py`逐项核对已发布Release所有附件的uploaded状态、字节数及SHA256，并下载核对原始逐文件清单。本地每个文件和清单完全一致、且远端包含完整raw.tar后，才允许移除旧完整目录或旧本地压缩包。旧符号链接信息另留在清理回执；清单不一致时保留原数据并报告原因。

```bash
# 只查看，不删除
python3 scripts/prune_published_ht_raw.py --keep 2
# 按已确认的保存政策执行
python3 scripts/prune_published_ht_raw.py --keep 2 --apply
```

[逐轮清理回执](local_raw_retention.json)记录原路径、完整Release、远端验证时间、原始清单摘要和移除时间。[发布回执](publications/)记录每份远端附件的大小/SHA256。旧[无损压缩索引](local_raw_archives.json)保留历史记录，状态github_only_per_user_retention_policy表示旧本地压缩包也按政策清理，不能再用本地restore命令。

需要重新分析旧轮时，从相应Release下载完整raw.tar（大包可能按part000、part001分卷），先对照发布回执核对SHA256，再解包；仓库中的报告/视频不等于全部原始MCAP。源秒抽样激光和周期地图的原始采集范围没有因此变成全传感器无损记录。

删除旧原始目录前，实际C++回归需要的阶段22冻结HT样本已逐字节保留在[fixtures/mixed_turn_stop.txt](../fixes/fixtures/mixed_turn_stop.txt)。后续设置HT_CONFIGURATION_FIXTURE指向该文件；其余既有回归样本和模型、独立仿真/建图工作区不受清理影响。未纳入已校验完整发布回执的历史数据暂时保留。
