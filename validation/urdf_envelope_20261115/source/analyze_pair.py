from pathlib import Path
import csv,json,collections,math,shutil
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from matplotlib.font_manager import FontProperties
root=Path('/home/lzz/ht_urdf_compare_20261115');out=Path('/mnt/d/HT-URDF-Compare-20261115/analysis');out.mkdir(exist_ok=True)
font=FontProperties(fname='/mnt/c/Windows/Fonts/msyh.ttc')
labels=['原0.6×0.6米包络','URDF整车外接长方体']
reports=[];series=[]
for variant,label in zip(['baseline','urdf'],labels):
    run=root/'runs'/f'{variant}_campus_600s_01';result=json.loads((run/'RESULT.json').read_text());assert result['collection_complete'] and result['freeze_unchanged']
    rows=list(csv.DictReader((run/'observations/metrics.csv').open()));series.append(rows)
    events=[json.loads(v) for v in (run/'observations/events.jsonl').read_text().splitlines()];start=json.loads((run/'observations/START.json').read_text())['clock']
    command_reasons=collections.Counter();selection_reasons=collections.Counter();recoveries=[];last=None;moving=0;audits=0
    for e in events:
        if e['time']<start:continue
        d=e['data']
        if e['kind']=='/ht_minimal/command_audit':
            audits+=1
            if not d['allowed']:command_reasons[d['reason']]+=1
            else:moving+=int(abs(d['linear_candidate'])>1e-8 or abs(d['angular_candidate'])>1e-8)
        if e['kind']=='/ht_minimal/local_selection':
            for key,value in d.get('rejections',{}).items():selection_reasons[key]+=value
        if e['kind']=='/ht_minimal/recovery':
            state=d.get('state');active=d.get('active')
            if (state,active)!=last:recoveries.append({'elapsed_s':e['time']-start,'state':state,'active':active,'detail':d});last=(state,active)
    t=np.array([float(r['elapsed_s']) for r in rows]);distance=np.array([float(r['distance_m']) for r in rows]);volume=np.array([float(r['sampled_free_volume_m3']) for r in rows])
    measured=result['summary'];report={'label':label,'variant':variant,'elapsed_s':measured['elapsed_s'],'distance_m':measured['distance_m'],'sampled_free_volume_m3':measured['sampled_free_volume_m3'],'finish':measured['finish'],'last_30s_distance_m':float(distance[-1]-np.interp(t[-1]-30,t,distance)),
        'command_rejections':dict(command_reasons),'local_selection_rejections':dict(selection_reasons),'command_audits':audits,'allowed_moving_candidates':moving,'recoveries':recoveries,'freeze_unchanged':True,'exit_codes':result['exit_codes'],'ht_source_age_s':measured['ht_source_age_s']}
    reports.append(report)
    target=out/variant;target.mkdir(exist_ok=True)
    for name in ['RESULT.json','FREEZE.json','ENVIRONMENT.json','COMMANDS.json','localPlanner.yaml','pathFollower.yaml','tare_planner_node.yaml','cupy_to_ht_bridge.yaml']:
        if (run/name).exists():shutil.copy2(run/name,target/name)
    shutil.copy2(run/'observations/metrics.csv',target/'metrics.csv')
    shutil.copy2(run/'observations/SUMMARY.json',target/'SUMMARY.json')
fig,axs=plt.subplots(2,1,figsize=(10,7),sharex=True)
for rows,label in zip(series,labels):
    axs[0].plot([float(r['elapsed_s']) for r in rows],[float(r['distance_m']) for r in rows],label=label)
    axs[1].plot([float(r['elapsed_s']) for r in rows],[float(r['sampled_free_volume_m3']) for r in rows],label=label)
axs[0].set_ylabel('累计XY里程 / 米',fontproperties=font);axs[1].set_ylabel('采样观测体积代理 / m³',fontproperties=font);axs[1].set_xlabel('实验时间 / 秒',fontproperties=font)
for ax in axs:ax.legend(prop=font);ax.grid(alpha=.25)
fig.suptitle('campus 同配置各600秒：包络及其地面支撑范围对比',fontproperties=font);fig.tight_layout();fig.savefig(out/'progress_comparison.png',dpi=150);plt.close(fig)
fig,ax=plt.subplots(figsize=(9,7))
for rows,label in zip(series,labels):ax.plot([float(r['x']) for r in rows],[float(r['y']) for r in rows],label=label)
ax.scatter([float(series[0][0]['x'])],[float(series[0][0]['y'])],marker='*',s=120,color='green',label='共同起点');ax.axis('equal');ax.grid(alpha=.25);ax.legend(prop=font);ax.set_xlabel('X / m');ax.set_ylabel('Y / m');fig.tight_layout();fig.savefig(out/'trajectory_comparison.png',dpi=150);plt.close(fig)
env=json.loads((root/'setup/URDF_ENVELOPE.json').read_text());lo=np.array(env['min_xyz']);hi=np.array(env['max_xyz'])
fig,axs=plt.subplots(1,2,figsize=(10,5))
for ax in axs:
    ax.add_patch(Rectangle((-.3,-.3),.6,.6,fill=False,color='tab:blue',lw=2,label='原包络'))
    ax.add_patch(Rectangle(lo[:2],*(hi-lo)[:2],fill=False,color='tab:orange',lw=2,label='URDF包络'))
    ax.plot(0,0,'k+');ax.set_aspect('equal');ax.set_xlim(-.75,.75);ax.set_ylim(-.75,.75);ax.grid(alpha=.25);ax.legend(prop=font)
axs[0].set_title('车身俯视投影：前后及两侧覆盖扩大',fontproperties=font)
axs[1].scatter([.44],[0],c='red',s=70);axs[1].annotate('距中心前方0.44米的障碍\n旧包络放行，新包络拒绝',(.44,0),(-.70,.58),fontproperties=font,arrowprops={'arrowstyle':'->'})
axs[1].set_title('固定地图回归：车头漏检得到拦截',fontproperties=font)
fig.tight_layout();fig.savefig(out/'body_envelope_comparison.png',dpi=150);plt.close(fig)
(out/'COMPARISON.json').write_text(json.dumps({'runs':reports,'envelope':env,'scope':json.loads((root/'EXPERIMENT_SCOPE.json').read_text()),'qualification':'One pair, not deterministic TARE: differences in route/volume alone do not establish universal improvement.'},indent=2,ensure_ascii=False))
print(json.dumps([{k:r[k] for k in ['variant','elapsed_s','distance_m','sampled_free_volume_m3','finish','last_30s_distance_m','command_rejections']} for r in reports],indent=2))
