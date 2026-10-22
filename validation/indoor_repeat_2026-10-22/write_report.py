"""Write a focused report from completed repeat and preserved prior evidence."""
import csv,json,hashlib,datetime,shutil
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'docs/results/ht_indoor_repeat_2026-10-22'
VAL=ROOT/'validation/indoor_repeat_2026-10-22'
PREV=ROOT/'docs/results/ht_sim_check_2026-10-22/indoor'
RAW=ROOT/'presentations/scheduled_results/ht_indoor_repeat_2026-10-22/indoor'
read=lambda p:json.loads(p.read_text())
rows=lambda p:list(csv.DictReader(p.open()))
def datafile(p,n):return p/n if (p/n).exists() else p/'current'/n
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,d):p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')

def main():
    analysis=read(OUT/'analysis.json')['runs']['indoor'];provenance=read(OUT/'comparison_provenance.json')['indoor']
    plt.rcParams.update({'font.family':'Noto Sans CJK JP','axes.unicode_minus':False})
    fig,axes=plt.subplots(2,3,figsize=(16,9),layout='constrained')
    cases=[('历史原TARE（10-21）',Path(provenance[0]['folder']),'#718196'),
           ('历史HT（07c1abd）',Path(provenance[1]['folder']),'#d28a22'),
           ('上次HT：提前返航',PREV,'#c94045'),('本次HT：相同运行代码',OUT/'indoor','#147d9b')]
    comparisons=[]
    for label,folder,color in cases:
        motionfile=datafile(folder,'timeseries.csv');volfile=datafile(folder,'observation_volume.csv')
        mm=rows(motionfile);vv=rows(volfile);t=np.array([float(r['t_s']) for r in mm]);dist=np.array([float(r['distance_m']) for r in mm])
        vt=np.array([float(r['time_s']) for r in vv]);vol=np.array([float(r['observed_free_volume_m3']) for r in vv])
        axes[0,0].plot(vt/60,vol,label=label,color=color);axes[0,1].plot(t/60,dist,label=label,color=color)
        edges=np.arange(0,601,30);axes[0,2].plot(edges[1:]/60,np.diff(np.interp(edges,vt,vol)),label=label,color=color)
        axes[1,0].plot([float(r['x_m']) for r in mm],[float(r['y_m']) for r in mm],label=label,color=color)
        comparisons.append(dict(label=label,folder=str(folder),distance_m=float(dist[-1]),volume_m3=float(vol[-1]),
            inputs_sha256={str(p):sha(p) for p in [motionfile,volfile]},
            metric_evidence='Same metric definition verified for both current captures by compare_ht_iterations; historical metric/source-second provenance verified in comparison_provenance.json.'))
    for label,folder,color in [cases[2],cases[3]]:
        cfile=VAL/('previous_early_candidates' if folder==PREV else 'repeat_early_candidates')/'candidates.csv';cc=rows(cfile)
        axes[1,1].plot([float(r['t_s']) for r in cc],[int(r['candidates']) for r in cc],color=color,label=label+'：候选')
        axes[1,1].plot([float(r['t_s']) for r in cc],[int(r['unvisited']) for r in cc],color=color,ls='--',label=label+'：未访问')
        hh=rows(folder/'health.csv');origin=read(folder/'manifest.json')
        if folder==PREV:wall=read(ROOT/'presentations/scheduled_results/ht_sim_check_2026-10-22/indoor/current/measurement_started.json')['wall_time']
        else:wall=read(RAW/'current/measurement_started.json')['wall_time']
        hh=[r for r in hh if wall<=float(r['wall_time'])<wall+600]
        axes[1,2].plot([(float(r['wall_time'])-wall)/60 for r in hh],[float(r['map_source_age_s']) for r in hh],color=color,label=label)
    axes[1,1].axvline(13.8174,color='#c94045',ls=':',label='上次锁定返航');axes[1,2].axhline(3,color='black',ls='--',label='超时线')
    titles=[('累计近似观测自由体积','时间 / min','m³'),('实际里程','时间 / min','m'),('每30秒新增体积','时间 / min','m³'),
            ('实际轨迹','X / m','Y / m'),('前35秒视点变化','时间 / s','个'),('两次当前HT地图源年龄','时间 / min','s')]
    for ax,(title,x,y) in zip(axes.flat,titles):ax.set(title=title,xlabel=x,ylabel=y);ax.grid(alpha=.2);ax.legend(fontsize=7)
    axes[1,0].set_aspect('equal',adjustable='datalim');fig.suptitle('室内：同代码重复与历史参照，各完整600秒\n历史TARE/HT未在本轮重新运行；单次轨迹差异不能作为算法优劣或修改收益的统计证明')
    fig.savefig(OUT/'all_comparisons.png',dpi=160);fig.savefig(OUT/'all_comparisons.pdf');plt.close(fig)
    write(OUT/'all_comparisons.json',comparisons)
    old_params=PREV/'effective_parameters';new_params=OUT/'indoor/effective_parameters';param_diffs={}
    for path in sorted(old_params.glob('*.json')):
        before=read(path);after=read(new_params/path.name)
        param_diffs[path.name]={k:{'before':before.get(k),'after':after.get(k)} for k in before.keys()|after.keys() if before.get(k)!=after.get(k)}
    frozen=read(VAL/'frozen_inputs.json');files=frozen['files'];bad=[p for p,h in files.items() if sha(ROOT/p)!=h]
    verification=dict(captured_at=datetime.datetime.now().astimezone().isoformat(),runtime_files_checked=len(files),changed_runtime_files=bad,
        parameter_differences=param_diffs,checks=read(RAW/'suite_validation.json')['checks'],
        speed_and_command_rate_audit=analysis['command_envelope'])
    write(OUT/'repeat_equivalence.json',verification)
    assert not bad and not any(param_diffs.values()),verification
    connectivity=read(VAL/'previous_early_candidates/connectivity_audit.json');critical=connectivity['frames'][1]
    scores=[v['current_grid_max_8dir_score'] for v in critical['boundary_rejected_vertices'] if not v['latest_physical_body_blocked']]
    orig=comparisons[0];hist=comparisons[1];cur=comparisons[3]
    video=read(OUT/'indoor/video_validation.json')
    lines=['# 室内复跑：为什么上次提前结束', '',
       '**本次未改导航代码，完整600秒行驶197.88m，近似观测自由体积3728m³，末状态EXPLORING；上次提前返航未在本轮重现，问题不能视为已修好。**','',
       '测试标签`ht-sim-20261022-indoor-repeat`，实测提交`0087a008f9d8beb26f2efa636f65fbf3e940a268`；运行算法继承`develop@8b10207`。相较上次e640c0c，133个运行文件及72项原manifest输入/二进制哈希一致。三个节点实际参数JSON逐键一致。实车代码/外参未参与。','',
       '| 单次记录（均600s） | 实际里程/m | 近似观测自由体积/m³ | 说明 |','|---|---:|---:|---|']
    for r in comparisons:lines.append(f'| {r["label"]} | {r["distance_m"]:.2f} | {r["volume_m3"]:.3f} | '+('历史参照' if r in comparisons[:2] else '同一运行代码，不同闭环轨迹')+' |')
    lines += ['',f'本次体积相对历史原TARE为{100*(cur["volume_m3"]/orig["volume_m3"]-1):+.2f}%，相对历史HT为{100*(cur["volume_m3"]/hist["volume_m3"]-1):+.2f}%。车辆能持续行驶不等于覆盖效率已恢复。相同场景、原生起点、速度上限和体积定义；初始yaw相差约0.0015rad，在预设0.02rad容差内。不是锁定随机种子的确定性重复，更不是多次统计对照。','',
       '![体积、里程、新增体积、轨迹、视点、地图年龄](all_comparisons.png)','',
       '## 可确认的触发链', '',
       '上次t=12.846s有842个候选、603个未访问；t=13.817s骤降到282/45。全局返回标记已为1，局部选择此时给出complete=1，程序立即将exploration_finished置为true。全局标记本身从首轮即为1，附近目标由局部层处理，不能单独解读为全局TSP故障。','',
       '下一帧t=14.508s候选恢复到811个、未访问576个，但完成标记已经锁定；后续覆盖更新分支停止并清空视点收益，车辆继续返航，约27.6s进入COMPLETED。候选数量恢复不等于收益队列已恢复，不能把后续被清零的收益当成“确实没有可探索区域”。','',
       '565个原候选位置消失，仅3个被同期碰撞视点云直接标记。按日志阶段耗时估计视点检查结束时间，再取之前接收的HT图，简化8邻接图重放得到282个位置，与该帧实际候选集合完全一致（误加0、漏掉0）。去掉HT顶点筛选、保留录下的碰撞顶点，连通位置为872；仅保留最新物理车体障碍门槛为867。','',
       f'切断连通分量的边界中，有9个位置在最新物理车体掩码上未受阻，但HT八方向最高分仅{min(scores):.3f}–{max(scores):.3f}，低于0.5门槛。结合代码，证据有力支持“短时HT地形拒绝→走廊连接被切断→远端候选被整体排除→无目标判定被永久当作探索完成”这一机制。','',
       '![上次关键帧候选变化](diagnosis/previous_early_candidates/transition.png)','',
       '![按视点阶段对齐后的连通性核对](diagnosis/previous_early_candidates/connectivity.png)','',
       '## 证据边界与仍待确认项','',
       '上述重放只使用三帧已发布候选的并集、录下的碰撞顶点和HT地形规则；高度约束、LOS及其他被拒节点没有完整重建。阶段结束时间由日志耗时推算，不是直接记录的内部地图指针。关键帧位置集合完全吻合增强了机制证据，但不能据此声称唯一源级根因已得到严格反事实证明。','',
       '不能直接用视点发布时最新HT图：本例该图已比视点处理阶段更新约一帧，简单重放反而得到823个连通位置。这个未对齐的检查不复现失败；保留在诊断文件中，不能拿它充当成功验证。','',
       '为什么HT在这些位置给出低分、低分是否符合真实地形，尚未用同一输入下的模型/支撑/高程方差逐项隔离；物理掩码未受阻也不证明地形一定可走。不能把问题直接归因于激光噪声、GPU、某个最近输入修正或特定阈值。','',
       '本次相同代码没有重现早停，且原版视点采样每次以random_device初始化随机数。随机选点、传感器与调度差异可产生不同轨迹；不能只凭两次试验判定哪个因素决定了这次分叉，也不能承诺下一次不早退。','',
       '## 本次完整采集与剩余问题','',
       f'地图源年龄P95为{analysis["map_age_p95_s"]:.3f}s，最大{analysis["map_age_max_s"]:.3f}s；超过3秒采样{analysis["map_age_over3s_samples"]}次。600个任务采样均EXPLORING，未触发返航。12,000条实际指令；上限审计通过，常规加速度超限{analysis["command_envelope"]["normal_acceleration_excess_count"]}次（显式全零停止单列，属于运动指令审计，不是完整动力学验证）。','',
       f'XYθ搜索日志{analysis["search_attempts"]}次，终止原因{analysis["search_termination_counts"]}。完整指令审计中最长全零停车约2.30s，另有原地转向；末60秒行驶约21.55m。13项采集检查通过；视频实际{video["decoded_frames"]}帧/{video["fps"]}fps/{video["duration_s"]:.3f}s，完整解码通过，落在600s目标允许1帧误差内；退出后无本轮残留子进程。采集通过不等于全部场景或实车验收。','',
       '建议下一候选先把“暂时无可达收益目标”与“任务完成”分开核验：保留TARE顺序与HT执行硬约束，检查未解决探索单元、等待连续地图复核并记录每个候选的拒绝原因；在同条件多次600秒实验中检验是否减少早退。单纯降低HT阈值、取消碰撞限制或强行让车前进都不能证明原因已修复。本轮没有实施这些行为修改。','',
       '## 数据、视频与复现','',
       '[GitHub完整视频](https://github.com/CQULzz/HT_Explo/releases/download/ht-sim-20261022-indoor-repeat/ht-sim-20261022-indoor-repeat-indoor.mp4) · [GitHub前60秒双视频对比](https://github.com/CQULzz/HT_Explo/releases/download/ht-sim-20261022-indoor-repeat/ht-sim-20261022-indoor-repeat-first60.mp4) · [本机完整视频](indoor/camera_h264.mp4) · [本机双视频](first60_comparison.mp4)','',
       '[采集检查](indoor/suite_validation.json) · [运行/参数一致性](repeat_equivalence.json) · [关键帧重放数据](diagnosis/previous_early_candidates/connectivity_audit.json)','',
       'GitHub发布目标：https://github.com/CQULzz/HT_Explo/releases/tag/ht-sim-20261022-indoor-repeat；上传完成以stage50.json的远端大小/SHA256校验回执为准。完整MCAP、周期地图/模型上下文、CSV、日志与视频放Release，仓库保存报告和索引。激光按源秒抽样，不能称为全频原始传感器无损录制。体积是0.5m自由体素并集近似，不是真值覆盖率。','',
       '运行命令、诊断范围与源码定位见validation/indoor_repeat_2026-10-22/REPRODUCE.md；历史图来自已有记录，原TARE没有在本轮重新运行。']
    (OUT/'REPORT.md').write_text('\n'.join(lines)+'\n')
    write(OUT/'files_sha256.json',{str(p.relative_to(OUT)):sha(p) for p in sorted(OUT.rglob('*')) if p.is_file() and p.name!='files_sha256.json'})
    print(json.dumps(dict(metrics=analysis,verification=verification),ensure_ascii=False,indent=2))

if __name__=='__main__':main()
