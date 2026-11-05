from pathlib import Path
import json,sys,shutil
R=Path('/home/w_lzz/ht-iterations-20261105'); root=R/'cycle2'; D=R/'repo/docs/results/wsl120_cycle2_20261105'
stage=sys.argv[1]; pairs=list(zip(sys.argv[2::2],sys.argv[3::2]))
out=['# '+stage+'：同种子配对结果','', '| seed/对比 | 指标 | 基线 | 候选 | 绝对变化 | 相对变化 |','|---|---|---:|---:|---:|---:|']
for base,cand in pairs:
 b=json.loads((root/'reports'/base/'SUMMARY.json').read_text());c=json.loads((root/'reports'/cand/'SUMMARY.json').read_text())
 for name,get in [('GT distance m',lambda x:x['done']['distance']),('Free volume m3',lambda x:x['done']['free_volume']),('HT callback P95 ms',lambda x:x['ht_callback_service_s']['p95']*1000),('Producer source age P95 s',lambda x:x['map_source_age_at_publish_s']['p95']),('Wall s',lambda x:x['run_result']['wall_elapsed'])]:
  u,v=float(get(b)),float(get(c));out.append(f'| {base} → {cand} | {name} | {u:.5f} | {v:.5f} | {v-u:+.5f} | {(v/u-1)*100:+.2f}% |')
 for label in [base,cand]:
  p=root/label/'DELIVERY_AGE.json'
  if p.exists():shutil.copy2(p,D/label/p.name)
 out.append(f'| {base} → {cand} | teardown nonzero | {b["run_result"]["managed_shutdown_nonzero"]} | {c["run_result"]["managed_shutdown_nonzero"]} | — | — |')
out+=['种子只控制TARE采样流/Gazebo，ROS/GPU调度仍有波动；每种子单次配对无法排除调度影响，不宣称统计显著或全场景覆盖。固定场景、配置哈希、命令、实测commit及原始路径见各轮EXPERIMENT_CONTEXT/manifest；环境沿用b00/SEED_SETUP记录。', '', '主源龄指标沿用基线的1Hz生产者性能遥测；DELIVERY_AGE.json额外覆盖MCAP全部已记录HT消息，以录包端最近收到的ROS时钟计算，包含传输/时钟采样，不替换主口径。所有MCAP计数/可用CRC/SHA及视频解码均单独核验。原始大文件仅本地保留，未发布Release。']
(D/(stage+'_COMPARISON.md')).write_text('\n'.join(out)+'\n')
