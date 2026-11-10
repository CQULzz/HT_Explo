# 用户录制点云场景：当前最小八方向版本

来源是用户 `20261103_190624` 录包导出的 `local_map.npy`，56849个XYZ点。原始独立PCD未找到；从本项目历史Release选择恢复点云数组、地面/障碍网格、原场景及起点元数据，逐文件核对历史SHA256。另将数组无损导出为binary PCD，明确不冒充遗失的原始PCD。

恢复入口为 `source/recover_map.py`（本机 `/home/lzz/pcd_test_20261110`），原始发布为 `ht-scout-pcd-fix-20261105-v1`；只下载选定资产的HTTP区间，未重新下载或核验全部历史分卷。库存JSON与仓库历史发布回执SHA256一致。

`prepare.py` 将原地面/障碍网格原样接入Gazebo Classic的CMU vehicleSimulator；保留原XY起点，通过测量三角网求得地面高度，CMU sensor位于地面上方0.75m。检查起点半径0.45m加地图离散余量范围的1305个样本都有测量地面。地面最长跨接边0.8m、障碍体素0.16m，缺测洞不补地面。

原网格仅约±15m，任务边界显式设为±13.5m，并使用上游TARE已有的导航/覆盖边界接口。没有给HT制造通行区域，也没有把历史TARE/XYθ规划器作为本轮运行入口。

算法与CMU已测最小八方向版一致：独立上游TARE、CMU局部路径与跟踪、HT路径及命令检查；速度0.5m/s、检查半径0.45m、门槛0.5、源龄1s、严格未知。沿用64线向下观察传感器与4Hz mapper。该仿真检查当前算法在录制地图重建场景中的行为，不复刻原车雷达误差及滑移动力学。

先 source `/home/lzz/cmu_test_20261110/env.sh`，再 source其 `install_cmu/setup.bash`、`install_mapper/setup.bash`、`install_native/setup.bash`、`install_gate/setup.bash`。Xvfb使用`:88`。

运行 `python3 tools/user_pcd/run.py --attempt 1`，完整600秒。输出在 `/home/lzz/pcd_test_20261110/runs`；冻结源文件/运行资产/二进制，保存MCAP、参数、状态、CSV、日志及失败记录。完整原始数据留本机，不创建Release，不清理未备份数据。
