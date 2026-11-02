# 复核说明

本轮目录为`/home/lzz/HT_near_vehicle_fix_20261102`，GitHub Release附件将保留完整B原ZIP、科学数据、冻结代码/哈希、全部计时与失败记录、图表和视频。

1. 原ZIP只解压一次至本轮`input/`，所有成员SHA256与先前完整性校验匹配。`decode_b.py`逐消息解码，`analyze_b.py`同源点云/地图检查，`trace_ground.py`回查508份实际HT输入。原始分析图与最终校正版均保留；`ANALYSIS_FINAL.json`将无ring回波的初版误标更正为整体角度分位数。
2. `baseline/`、`candidate/`为冻结源码。首次构建漏带历史测试依赖，原失败日志保留，补齐相同测试输入后独立构建成功。构建不改原项目安装，不接实车或独立CuPy工作区。
3. `map_audit.cpp`只在独立localhost ROS域218直接调用接收函数，无话题输入回放或控制发布。它只通过审计夹具读取内部数据，不给生产接口增加可写入口。`build_audit.py`使用各版本原构建的编译/链接参数。
4. `run_map_audit.py`新旧交替运行3遍，最终数据位于`map_benchmark_v4_fixed_anchor`。固定记录锚点以及覆盖整个包的受控60秒测试时段，仅用于先验有效/无先验组件对照，不替代实际任务起止时间。所有早期失败/夹具结果保留于`CHECK_NOTES.json`所列位置。
5. `ctest`在候选独立构建目录运行8组检查；Python对冻结候选的完整ht_scout_bridge测试目录运行117项检查。`FINAL_CHECK.json`与`CANDIDATE_FREEZE.json`记录验收边界；pytest缓存不属于冻结源码。
6. `finalize_results.py`生成最终图与摘要，`render_video.py`输出193帧、1600×900、8fps的记录数据缩时视频，`VIDEO_CHECK.json`验证帧数及全片解码。

外部未修改的OR-Tools SDK、可重建的整套构建目录和Python/Numba缓存可不进入科学归档；完整源码/依赖哈希、关键已构建二进制、测试输出及编译链接记录保留。未取得的车端HT源文件不能由本轮源码快照替代。
