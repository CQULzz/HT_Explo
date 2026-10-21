# 仿真复测与报告复现

本轮冻结运行提交为`e640c0c1867fbe9408007c9f7b3e51bb9e66b801`，算法继承`develop@8b10207`；报告生成代码是随后添加的离线设施，不能冒充实测导航修改。实车入口、Scout外参未参与。

## 构建和回归

本工作树使用自己的构建/安装目录，不source邻接HT实车工作区。外部CMU仿真与CuPy保持独立，仅在各自节点进程中加载对应ROS环境。桥接中的CuPy回归测试另需可导入独立mapper测试依赖。

```bash
bash scripts/build_sim_check.sh
source /opt/ros/jazzy/setup.bash
source install_standalone/setup.bash
export ROS_DOMAIN_ID=229
export ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST
HT_CONFIGURATION_FIXTURE="$PWD/docs/fixes/fixtures/mixed_turn_stop.txt" \
  ctest --test-dir build_standalone/tare_planner --output-on-failure
python3 scripts/check_tare_waypoint_contract.py

# 以下source仅用于执行独立mapper相关Python测试，不参与HT编译。
source '../elevation_mapping_cupy_ws/install/setup.bash'
python3 -m pytest -q tools/ht_cupy_bridge
```

如果使用sparse checkout，须保留`docs/fixes`、`validation/logic_resolution_2026-10-22`、`docs/results/ht_continuous_geometry_10min_2026-10-18/geometry_capture`和`docs/results/ht_latency_diagnosis_10min_2026-10-18/geometry_capture`。四个GTest用例还需要额外历史捕获fixture，未提供时会明确SKIP，不能算通过。

## 600秒实测

使用空的新输出目录；先冻结提交和二进制，运行期间不修改源码、参数或模型。独立构建成功后，在只加载ROS基础环境的新终端执行：

```bash
source /opt/ros/jazzy/setup.bash
python3 presentations/run_ht_multiscene.py \
  --duration 600 --scenarios indoor campus --domain 226 \
  --encoder /path/to/ffmpeg \
  --output /path/to/new_suite
```

本轮实际输出为`presentations/scheduled_results/ht_sim_check_2026-10-22`。runner记录候选源码/外部配置与实际二进制哈希；`nav_source_inventory.json`是运行期间另外核验的133个已提交运行文件补充清单，注明采集时间，不冒充测前快照。

每个场景启动后，在对应ROS域使用`capture_parameters.py`只读抓取参数；该辅助工具先等DDS发现和参数服务，不依赖立即执行`ros2 param dump`能看见全部节点。

```bash
ROS_DOMAIN_ID=227 ROS_LOCALHOST_ONLY=1 \
python3 validation/sim_check_2026-10-22/capture_parameters.py \
  --wait-file /path/to/new_suite/campus/current/measurement_started.json \
  --output /path/to/new_suite/campus/current/effective_parameters
```

## 离线归档、审计、报告

两场完成且视频时长/完整解码通过后执行；不要覆盖现有归档：

```bash
source /opt/ros/jazzy/setup.bash
python3 presentations/archive_ht_multiscene.py /path/to/new_suite \
  --scenarios indoor campus --output /path/to/new_archive
python3 validation/sim_check_2026-10-22/assess_runs.py \
  --suite /path/to/new_suite --output /path/to/new_archive
python3 validation/sim_check_2026-10-22/build_report.py \
  --report docs/planning/2026-10-22_planning_principles.md \
  --report /path/to/new_archive/REPORT.md
```

最后一步需要Markdown、Matplotlib、WeasyPrint及中文字体。若系统未安装报告工具，可用`pip --target`装入单独缓存目录并通过该目录PYTHONPATH执行，不改系统Python。FFmpeg需有libx264编码器。

`assess_runs.py`读取已有10-21室内/校园TARE与HT结果作历史参照，没有在本轮重新运行原TARE；它保留体积口径校验、输入CSV哈希、任务完成条件日志、命令上限/变化率审计。原始录制检查与导航效果的判断分开报告。

发布标签固定到实测冻结提交；大MCAP放Release分片附件，不写入Git历史。发布后以逐文件清单和远端大小/SHA256核验回执为准。对旧录包的清理回执另见`docs/experiments/legacy_archive/local_pruning_2026-10-22_sim_check.json`。
