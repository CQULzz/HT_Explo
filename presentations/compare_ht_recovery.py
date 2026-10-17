#!/usr/bin/env python3
"""Compare completed, same-scene recovery trials; multiple fixes are bundled."""
import argparse
import csv
import json
from pathlib import Path
import shutil

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np


def read(path):return json.loads(path.read_text())


def table(path):
    with path.open() as f:return list(csv.DictReader(f))


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--before-tunnel',type=Path,required=True)
    ap.add_argument('--before-indoor',type=Path,required=True)
    ap.add_argument('--before-tunnel-commands',type=Path,required=True)
    ap.add_argument('--before-indoor-commands',type=Path,required=True)
    ap.add_argument('--after',type=Path,required=True)
    ap.add_argument('--output',type=Path,required=True)
    args=ap.parse_args();out=args.output;out.mkdir(parents=True,exist_ok=False)
    pairs={'tunnel':(args.before_tunnel,args.after/'tunnel'),
           'indoor':(args.before_indoor,args.after/'indoor')}
    before_commands={'tunnel':args.before_tunnel_commands,'indoor':args.before_indoor_commands}
    names={'tunnel':'隧道','indoor':'室内'};labels=['修改前','修改后']
    plt.rcParams.update({'font.family':'Noto Sans CJK JP','axes.unicode_minus':False})
    fig,axes=plt.subplots(2,3,figsize=(15,8),layout='constrained')
    evidence={};lines=['# 停滞修复前后：隧道、室内各10分钟','',
        '本轮同时修改了HT观测支撑语义、拒绝观测的历史记录、停滞恢复与搜索预算，并调整CPU推理布局。它是整包修改前后各一次的同场景试跑，不是单因素消融或重复统计。','',
        '两场景均沿用原生起点、0.5m/s速度上限、0.5概率阈值、0.6m足迹及3秒时效保护。室内前后都使用0.3m视点采样，不能把此前0.6m采样失败轮当成本次比较基线。观测体积为同口径激光射线自由体素并集近似，不是真值覆盖率。','']
    export=[]
    for row,(scene,(before,after)) in enumerate(pairs.items()):
        audits=[read(p/'endurance_audit.json') for p in [before,after]]
        manifests=[read(p/'manifest.json') for p in [before,after]]
        for p,audit in zip([before,after],audits):
            video=read(p/'video_validation.json')
            if audit['duration_s']!=600 or video['full_decode_returncode']!=0 or not video['duration_matches']:
                raise RuntimeError('Incomplete recording: '+str(p))
        hashes=[m['source_hashes'] for m in manifests]
        common=hashes[0].keys()&hashes[1].keys()
        changed={k:dict(before=hashes[0].get(k),after=hashes[1].get(k))
                 for k in hashes[0].keys()|hashes[1].keys() if hashes[0].get(k)!=hashes[1].get(k)}
        locked=[k for k in common if k.endswith(('/'+scene+'.yaml','/ht_trial.yaml','/trial_core.yaml',
            '/trial_setup.yaml','/student_best_epoch_weights.pth','/'+scene+'.world'))]
        if len(locked)<7 or any(hashes[0][k]!=hashes[1][k] for k in locked):
            raise RuntimeError('Scene, model or mapper settings changed: '+scene)
        start=[np.asarray(a['summary']['start_pose_xyyaw']) for a in audits]
        if np.linalg.norm(start[0][:2]-start[1][:2])>.1:
            raise RuntimeError('Mismatched initial XY: '+scene)
        intervals=[]
        for p,label,audit in zip([before,after],labels,audits):
            motion=table(p/'timeseries.csv');volume=table(p/'observation_volume.csv')
            t=np.array([float(r['t_s']) for r in motion]);d=np.array([float(r['distance_m']) for r in motion])
            x=np.array([float(r['x_m']) for r in motion]);y=np.array([float(r['y_m']) for r in motion])
            vt=np.array([float(r['time_s']) for r in volume]);v=np.array([float(r['observed_free_volume_m3']) for r in volume])
            axes[row,0].plot(vt/60,v,label=label);axes[row,1].plot(t/60,d,label=label)
            axes[row,2].plot(x,y,label=label,linewidth=1)
            interval=dict(start_s=360,end_s=450,distance_m=float(np.interp(450,t,d)-np.interp(360,t,d)),
                observed_free_volume_gain_m3=float(np.interp(450,vt,v)-np.interp(360,vt,v)))
            intervals.append(interval)
            e=audit['external_metrics'];s=audit['summary'];m=audit['mission_audit'];age=audit['sampled_map_age_s']
            export.append(dict(scene=scene,version=label,distance_m=s['distance_m'],
                observed_free_volume_m3=e['observed_free_volume_m3'],fully_stopped_fraction=e['fully_stopped_fraction'],
                longest_zero_command_s=e['longest_zero_command_s'],reverse_command_fraction=e['reverse_command_fraction'],
                planner_p95_s=s['planner_runtime_p95_s'],map_age_p95_s=age['p95'],map_age_max_s=age['max'],
                mission=m['last_sampled_mission'],first_completed_s=m['first_completed_sample_s'],
                final_home_distance_m=m['final_distance_to_measurement_start_m']))
        for col,(title,ylabel) in enumerate([('近似观测自由体积','m³'),('累计里程','m'),('实际轨迹','Y / m')]):
            ax=axes[row,col];ax.set(title=names[scene]+'：'+title,ylabel=ylabel,
                xlabel='时间 / 分钟' if col<2 else 'X / m');ax.grid(alpha=.2);ax.legend()
            if col<2:ax.set_xlim(0,10)
            else:ax.set_aspect('equal',adjustable='datalim')
        a,b=export[-2:]
        command_audits=[read(before_commands[scene]),read(after/'mission_commands.json')]
        shutil.copy2(before_commands[scene],out/(scene+'_before_commands.json'))
        for record,commands in zip([a,b],command_audits):
            record['active_longest_zero_command_s']=commands['active_mission']['longest_zero_command_s']
            record['matched_window_s']=commands['matched_window']['duration_s']
            record['matched_longest_zero_command_s']=commands['matched_window']['longest_zero_command_s']
            record['exact_completed_message_s']=commands['first_completed_message_s']
        if abs(a['matched_window_s']-b['matched_window_s'])>1e-6:
            raise RuntimeError('Mismatched command prefix windows')
        lines += ['## '+names[scene],'','| 指标 | 修改前 | 修改后 |','|---|---:|---:|']
        fields=[('实际里程(m)','distance_m','.2f'),('近似观测自由体积(m³)','observed_free_volume_m3','.3f'),
            ('全零指令占比（含完成后停车）','fully_stopped_fraction','.1%'),
            ('任务期间最长全零指令(s)','active_longest_zero_command_s','.2f'),
            ('等长前缀内最长全零指令(s)','matched_longest_zero_command_s','.2f'),
            ('倒车指令占比','reverse_command_fraction','.1%'),('整轮规划耗时P95(s)','planner_p95_s','.3f'),
            ('HT年龄P95(s)','map_age_p95_s','.3f'),('HT年龄最大(s)','map_age_max_s','.3f'),
            ('末尾距起点(m)','final_home_distance_m','.3f')]
        lines += [f'| {title} | {a[key]:{fmt}} | {b[key]:{fmt}} |' for title,key,fmt in fields]
        lines += [f'| 最后任务状态 | {a["mission"]} | {b["mission"]} |',
            f'| 首次COMPLETED消息(s) | {a["exact_completed_message_s"]} | {b["exact_completed_message_s"]} |','',
            f'停车比较另取两轮相同的前{b["matched_window_s"]:.2f}秒，截止于新轮首次COMPLETED；没有把新轮完成后主动停车算成卡死。全600秒原始停车统计仍保留在CSV和原报告中。','',
            f'第6至7.5分钟，修改前行驶{intervals[0]["distance_m"]:.2f}m、新增{intervals[0]["observed_free_volume_gain_m3"]:.3f}m³；修改后行驶{intervals[1]["distance_m"]:.2f}m、新增{intervals[1]["observed_free_volume_gain_m3"]:.3f}m³。这是预先沿用的固定区间，只能描述该区间，不能代表全程效率。','']
        evidence[scene]=dict(before=str(before.resolve()),after=str(after.resolve()),
            before_head=manifests[0]['git_head'],after_head=manifests[1]['git_head'],
            unchanged_scene_model_mapper_inputs=locked,changed_inputs=changed,low_gain_interval=intervals)
    fig.suptitle('整包修改前后各一次600秒；参数与模型核验相同，多项控制/建图语义修改不能分离归因')
    fig.savefig(out/'comparison.png',dpi=170);plt.close(fig)
    lines += ['![同场景修改前后曲线和轨迹](comparison.png)','',
        '**结论与剩余问题：** 隧道本轮成功返航，室内任务期间长停车缩短，但室内总观测体积由1900.250降为1106.750m³（约下降41.8%）。新轮约215秒触发返航，而原轮600秒末仍在探索，轨迹也选择了不同支路，不能宣称探索效率全面提升。代码中的收尾条件是TARE无可连通全局探索任务且局部覆盖队列为空；它不是真值全覆盖判断。新轮触发前最后一条日志仍在追踪远处局部导航引导，提示任务与HT导航的收尾衔接仍需专门验证；没有据此直接把所有未知区说成可达，也没有强制延长行驶来掩盖条件。','',
        '地图尾延迟仍有问题：本轮室内1Hz抽样年龄最大约5.01秒，较前轮4.67秒更差；每组都有8个超过3秒的抽样。森林约4Hz的输入问题本轮没有重测，不能说已经解决。','',
        '一轮目标搜索共享0.35秒预算只约束Hybrid A*查询，不限制视点更新、地图转换及整轮规划时间；表中报告完整规划耗时。3秒时效保护保持生效，仍可能因过期或无安全路线停车。COMPLETED只确认返航检查通过，不等于场景真值全覆盖。','',
        '[本轮完整视频与地图](../ht_recovery_10min_2026-10-17/REPORT.md) · [失败诊断与离线回归](../ht_context_diagnostics_2026-10-17/REPORT.md)','']
    (out/'REPORT.md').write_text('\n'.join(lines))
    (out/'source_difference.json').write_text(json.dumps(evidence,ensure_ascii=False,indent=2)+'\n')
    with (out/'metrics.csv').open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(export[0]),lineterminator='\n');writer.writeheader();writer.writerows(export)
    print(json.dumps(export,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
