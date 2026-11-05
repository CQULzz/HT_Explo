# 循环4：建图串行执行与独立TF接收候选

用户继续要求解决问题，上一条“暂不运行仿真”仍有效。本轮正式仿真0次，无Gazebo/ROS录包播放/控制命令/实车/部署/Release。已在独立runtime准备可选候选，默认仍multi，只有显式--mapper-executor single才选择新拓扑；不能将本轮结果称作1秒源龄闭环验收。

## 证据与假设

循环3从旧录包确认超限42轮进入HT时源龄P95已经0.940s，HT内部排队P95不足1ms，重点应在上游调度。当前runtime的点云、pose/variance/time和发布都经过map_access_lock，MultiThreadedExecutor(4)不能把地图关键操作并行化。实际TransformListener(self.tf_buffer,self)的spin_thread默认False（已检查本机Jazzy实现），并非注释声称的独立线程。旧r05有干扰的GIL抽样中，mapper有540/1397=38.65%的GIL样本叶帧位于rclpy执行器；不是总CPU或根因归属百分比，仅支持检查调度开销的假设。

候选假设：地图操作按一条执行器线程处理，减少无效线程池/锁竞争；把TF放独立节点/执行器，保证地图回调等待精确源时刻变换时仍能接收TF。不能仅把地图线程改成单线程，否则同线程等待TF会饿死接收回调。新增真实ROS机制测试复现了这一反例，未把当前四线程旧模式说成已被证明死锁。

## 修改

新增mapper_execution.py：single模式地图执行器+TfListenerWorker。独立接收节点继承context、namespace、use_sim_time及/tf、/tf_static、/clock重映射，避免把owner节点同时放进两个executor；线程健康错误上抛，关闭可重复并join；初始化、回调/执行器停止异常均清理TF、节点、context与信号处理器。

install_mapper_execution.py只接受当前已知wrapper的完整SHA256或候选SHA256。helper也验证；未知编辑/软链拒绝写入，写失败回滚，重复执行不重写。只准备runtime中的两个文件，不更改独立CuPy核心/配置，不启动进程。实际runtime已安装候选包装器，默认模式仍multi。manifest和mapper_execution.patch可审计全部变化。

run_sim.py新增--mapper-executor multi/single（默认multi），清单记录选择，只给mapper子进程设置模式。single在创建运行目录或子进程前校验实际wrapper/helper哈希；未正确安装直接失败。当前仅用--help和禁止Popen的测试核验入口，未启动runner。

## 验证结果

20项检查通过（0.91s）：阻塞回调中接收准确TF、独立ROS时钟和重映射、关闭与故障传播、真实包装器的两种拓扑（GPU对象替换为测试桩，未运行建图/物理）、构造失败/执行器异常清理；安装器干跑/幂等/未知文件与软链保护/失败回滚；single预检禁止启动子进程；既有地图发布合同4项。

共用单线程接收TF的反例在0.6秒等待后仍无变换；独立TF在约0.061s收到发送线程50ms后发送的同一源时刻变换，原stamp与平移0.37检查通过。并非真实雷达端到端延迟。开发中补获并修复初始化/退出异常时未清理接收线程的反例，失败日志保留。

旧publication_demand测试曾从独立install导入另一份wrapper（那份不含runtime的无订阅跳过逻辑），造成1失败/17通过；保留cycle4-final-tests.log。已增加CUPY_WRAPPER_UNDER_TEST明确测试实际runtime文件，原断言未改，最终通过。AST比较确认：除了__init__外，ElevationMappingNode的每个方法与原runtime完全相同，包含点云融合、TF时间选择、地图移动、variance/time更新、发布源戳、观测年龄与层序列化；修改的是调度、入口和清理。

## 调度层负载对比

同一进程/ROS版本，三组回调共用一把锁，周期20ms、原生工作释放GIL的替代负载sleep4ms，三次交替配对，每窗约2秒并预热0.3秒。无地图/点云/模型、无机器人命令；CPU为进程process_time，墙钟为monotonic。详细每次结果见JSON，不能用其替代源龄/探索仿真。

| 中位指标 n=3/模式 | multi | single | 变化 |
|---|---:|---:|---:|
| CPU核当量 | 0.077728 | 0.029007 | -62.68% |
| 完成回调/秒 | 149.641 | 149.752 | +0.07% |

单窗回调约300次，CPU降低没有以减少处理量换取；三对均降低CPU，但样本少、负载合成，不能证明实际CuPy/HT源龄降低，更不能声称P95<1秒。基准测量helper文件与最终helper相同，随后仅补包装器异常清理，不影响基准代码路径；源码及数据SHA256见PROVENANCE。

## 下一步与限制

新模式已准备并通过离线机制测试，未默认启用，尚需在用户恢复仿真后以同种子120秒对照multi/single并复跑，核对地图内容/源时间、安全状态、源龄P95与探索体积。调度外的适配器、GPU服务、发布/传输也可能占延迟，不能认为单个候选消除了全部原因。未知/几何/概率0.5/1秒门限均未放宽，既有录包与双系统Linux未改写。仍不自动新开仿真。
