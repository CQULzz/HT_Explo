# HT运行身份与有界诊断（2026-10-30本地候选）

此功能只报告和记录HT进程，不证明独立mapper、外部TF、规划器或车辆正在运行的版本。本版按用户要求上传为候选；HT不约束调度P95验收仍未通过，状态见[实验报告](../results/real_system_foundation_2026-10-30/REPORT.md)。

## 运行身份

标准实车launch将身份话题隔离到`/ht_real/ht_runtime`。它使用reliable、transient-local、depth=1；后加入的订阅者也应请求transient-local。直接HT脚本的话题为`/ht_runtime`。仅启动HT时发布一次，不按地图帧率重复计算文件哈希。

内容包含入口文件、实际导入模块及权重路径/SHA256、模型相关参数、实际设备与后端、CPU线程池、PyTorch/CUDA/NumPy版本、RMW标识和已解析的HT/高程话题。`runtime_id`是该清单的摘要，不是Git提交号，也不是每次进程启动独有的随机ID。入口相同但导入了相邻工作区模块时，实际路径及哈希会显示该差异。

清单不收集任意环境变量、完整命令行或凭据。它不完整覆盖驱动、内核、外部进程和物理标定；这些仍需要独立版本清单。性能话题和逐帧记录引用同一个`runtime_id`。

## 在线与实验记录

HT节点参数`ht_diagnostics_capacity`默认600，必须为正整数。保留的是最近600条成功输出诊断，不是600秒。原直接读取`node.diagnostics[-1]`和遍历仍支持；JSON序列化使用`list(node.diagnostics)`。离线工具的结果同时报告`diagnostics_status`，不能将保留窗口误称全历史。

不设置`HT_DIAGNOSTICS_DUMP`时，没有日志写盘线程。设置到一个新目录下的新文件名，例如`/new/experiment/diagnostics.json`后：

| 文件 | 内容 |
|---|---|
| `diagnostics.json.jsonl` | I/O工作线程追加的逐帧日志，保留作为部分记录/故障证据 |
| `diagnostics.json.runtime.json` | 与记录关联的HT运行身份 |
| `diagnostics.json.status.json` | 退出时记录数、内存淘汰、写出、丢弃及错误状态 |
| `diagnostics.json` | 主入口正常清理时，流式转换的兼容完整JSON数组 |

输出名是原路径追加后缀，故存在`.json.jsonl`。目录需预先存在，文件独占创建；重跑使用新目录，不能覆盖旧结果。程序直接调用`destroy_node()`会关闭并排空日志；需要兼容JSON数组的自定义离线程序还须在退出前调用`node.diagnostics.finalize()`。标准`main()`已调用。

地图回调不等待文件I/O；启用归档后，它会序列化一条记录并尝试放入默认2048条的有界队列。在线环和队列有界不代表整个进程RSS固定，也不限制实验档案的磁盘增长。目录不可用会在初始化时报错；队列满或运行中写盘失败会记录丢失与错误，保留已有日志，不生成声称完整的JSON数组。

`/ht_real/ht_performance`中`diagnostics_before_current_record`说明统计截止上一条完成的逐帧记录。`archive_written`在写盘线程推进，是近似实时进度；以退出后的status作完整性核验。若归档失败，不要把最后600条在线记录替代为完整实验。

此诊断功能不更改地图发布源时间戳、通行阈值、未知或障碍掩码。不能通过重复旧图、放宽超时或关闭检查来提高测得频率。
