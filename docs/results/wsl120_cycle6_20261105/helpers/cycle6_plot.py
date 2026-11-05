from pathlib import Path
import json,csv
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
R=Path('/home/w_lzz/ht-iterations-20261105/cycle6');D=R/'reports';D.mkdir(exist_ok=True)
pairs=[('Seed 42, first','multi42_b01','single42_c01'),('Seed 99','multi99_b02','single99_c02'),('Seed 42, repeat','multi42_r01','single42_r01')]
fig,axs=plt.subplots(3,3,figsize=(15,11))
for i,(name,base,candidate) in enumerate(pairs):
 for label,color in [(base,'#2563eb'),(candidate,'#e87919')]:
  p=R/label;x=json.loads((p/'COMPACT.json').read_text());rows=[q for q in csv.DictReader((p/'metrics.csv').open()) if float(q['elapsed_sim'])>=0];origin=float(rows[0]['sim_time'])-float(rows[0]['elapsed_sim']);t=[float(q['elapsed_sim']) for q in rows];tt=[];ages=[]
  for line in (p/'events.jsonl').open():
   q=json.loads(line)
   if q['topic']=='ht_performance':tt.append(q['time']-origin);ages.append(json.loads(q['data'])['source_age_at_publish_s'])
  axs[i,0].plot(tt,ages,color=color,label=f"{x['mode']} P95={x['age']['p95']:.3f}s",alpha=.8)
  axs[i,1].plot(t,[float(q['distance_m']) for q in rows],color=color,label=x['mode'])
  axs[i,2].plot(t,[float(q['observed_free_volume_m3']) for q in rows],color=color,label=x['mode'])
 axs[i,0].axhline(1,color='#b91c1c',linestyle='--',linewidth=1,label='1s gate')
 for j,(ylabel,title) in enumerate([('Source age (s)','HT source age (1Hz producer telemetry)'),('GT distance (m)','Cumulative ground-truth XY distance'),('Observed free volume (m³)','Sampled ray-voxel volume proxy')]):
  ax=axs[i,j];ax.set(xlabel='Elapsed simulation (s)',ylabel=ylabel);ax.set_title(name+'\n'+title,fontsize=10);ax.grid(alpha=.2);ax.legend(fontsize=8);ax.set_xlim(0,121)
fig.suptitle('120-second mapper comparison: same navigation, paired seeds, frozen artifacts',fontsize=14)
fig.tight_layout(rect=(0,.03,1,.96));fig.text(.015,.012,'All runs retained. First multi42 observer exited -2 at teardown; see report. Distance includes initial settling. No universal coverage/safety certification.',fontsize=9)
fig.savefig(D/'PAIRED_OVERVIEW.png',dpi=150);plt.close(fig)
print(D/'PAIRED_OVERVIEW.png')
