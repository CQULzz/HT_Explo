#!/usr/bin/env python3
"""Add marginal gain and observed trajectory revisitation to the revision atlas."""
import argparse,csv,hashlib,json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

def rows(p):
    with p.open() as f:return list(csv.DictReader(f))

def main():
    ap=argparse.ArgumentParser();ap.add_argument('atlas',type=Path);a=ap.parse_args();out=a.atlas
    records=json.loads((out/'measurements.json').read_text());result=[]
    plt.rcParams.update({'font.family':'Noto Sans CJK JP','axes.unicode_minus':False})
    for r in records:
        folder=Path(r['folder']);vpath=(out/'recomputed_metrics'/Path(r['metric_provenance']).name/'observation_volume.csv') if r['metric_recomputed'] else folder/'observation_volume.csv'
        v=rows(vpath);motion=rows(folder/'timeseries.csv')
        gained=float(v[-1]['observed_free_volume_m3'])-float(np.interp(540,[float(x['time_s']) for x in v],[float(x['observed_free_volume_m3']) for x in v]))
        cells=np.floor(np.array([[float(x['x_m']),float(x['y_m'])] for x in motion])).astype(int)
        entered=[]
        for cell in cells:
            key=tuple(cell)
            if not entered or entered[-1]!=key:entered.append(key)
        repeats=max(0,len(entered)-len(set(entered)));denom=max(1,len(entered)-1)
        result.append(dict(id=r['id'],scene=r['scene'],last60_gain_m3=gained,last60_distance_m=r['last60_m'],
            last60_gain_per_m=gained/r['last60_m'] if r['last60_m'] is not None and r['last60_m']>=1 else None,
            entered_grid_cells=len(entered),repeated_entries=repeats,repeat_entry_fraction=repeats/denom,
            input_sha256={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in [vpath,folder/'timeseries.csv']}))
    (out/'efficiency.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    with (out/'efficiency.csv').open('w') as f:
        w=csv.DictWriter(f,fieldnames=[k for k in result[0] if k!='input_sha256'],extrasaction='ignore');w.writeheader();w.writerows(result)
    for scene in ['indoor','garage']:
        group=[r for r in result if r['scene']==scene];names=[r['id'] for r in group];x=np.arange(len(group));colors=plt.cm.turbo(np.linspace(.03,.95,len(group)))
        fig,axes=plt.subplots(3,1,figsize=(max(12,len(group)*.6),10),layout='constrained')
        for axis,key,title,ylabel in [(axes[0],'last60_gain_m3','最后一分钟新增观测体积','m³'),(axes[1],'last60_gain_per_m','最后一分钟每米新增观测（距离<1m时不计算）','m³/m'),(axes[2],'repeat_entry_fraction','1m轨迹格重复进入占比（不把原地停留算回访）','比例')]:
            axis.bar(x,[np.nan if r[key] is None else r[key] for r in group],color=colors);axis.set(xticks=x,xticklabels=names,title=title,ylabel=ylabel);axis.tick_params(axis='x',rotation=65);axis.grid(axis='y',alpha=.2)
        fig.suptitle(('室内' if scene=='indoor' else '车库')+'：有效增益与回访；轨迹网格受分辨率/边界抖动影响，不是物理覆盖真值')
        stem=scene+'_09_efficiency';fig.savefig(out/(stem+'.png'),dpi=170,bbox_inches='tight');fig.savefig(out/(stem+'.pdf'),bbox_inches='tight');plt.close(fig)
    with (out/'REPORT.md').open('a') as f:f.write('\n## 有效增益与回访\n\n最后一分钟体积差除以该分钟里程，里程<1m不计算；没有用初始扫描体积抬高每米增益。1m轨迹格按连续进入序列去除原地重复采样，重复进入之前已到访格的次数除以总进入次数（不含起点）；格边界抖动可能影响数值，不是真值覆盖率或全局探索最优性。\n\n![室内有效增益与回访](indoor_09_efficiency.png)\n\n![车库有效增益与回访](garage_09_efficiency.png)\n')
    print('Added two efficiency/revisitation figures; evidence in efficiency.json')

if __name__=='__main__':main()
