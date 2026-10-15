#!/usr/bin/env python3
"""Compare Garage XYtheta runs from their first nonzero registered-scan sample."""
import csv
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
import numpy as np

FONT_FILE = '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc'
font_manager.fontManager.addfont(FONT_FILE)
plt.rcParams['font.family'] = font_manager.FontProperties(fname=FONT_FILE).get_name()
plt.rcParams['axes.unicode_minus'] = False

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'results' / 'xytheta_comparison_2026-10-12'
RUNS = [
    ('早期硬门槛（旧跟踪器）', 'xytheta_hard_garage_2026-10-12', '#9a9a9a'),
    ('进展视点原型（旧跟踪器）', 'xytheta_hard_garage_stepping_2026-10-12', '#c88721'),
    ('上一轮 XYθ（许可超时 0.5 秒）', 'xytheta_hard_garage_final_2026-10-12', '#3976b7'),
    ('本轮 XYθ（许可超时 1.5 秒）', 'xytheta_permission_fixed_garage_synced_2026-10-12', '#df4d3f'),
]

def load(name):
    with (ROOT / 'results' / name / 'timeseries.csv').open(newline='') as f:
        rows = list(csv.DictReader(f))
    valid = [r for r in rows if float(r['observed_free_volume_m3']) > 0]
    if not valid:
        raise RuntimeError(f'{name}: no valid scan')
    first = valid[0]
    t0, v0, d0 = (float(first[k]) for k in ('time_s','observed_free_volume_m3','distance_m'))
    result=[]
    for r in valid:
        t=float(r['time_s'])-t0
        if t > 90.001:break
        result.append((t,float(r['distance_m'])-d0,
                       float(r['observed_free_volume_m3'])-v0,r['mission_state'],r['execution_status']))
    return result

def at(data, seconds, column):
    if data[-1][0] < seconds-1.5:
        return None
    prior=[r for r in data if r[0]<=seconds+0.5]
    return prior[-1][column] if prior else None

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    fig, axes=plt.subplots(2,1,figsize=(11,8),sharex=True,layout='constrained')
    summary=[]
    for label,name,color in RUNS:
        data=load(name)
        t=np.array([r[0] for r in data]);d=np.array([r[1] for r in data]);v=np.array([r[2] for r in data])
        axes[0].plot(t,d,label=label,color=color,lw=2.4)
        axes[1].plot(t,v,label=label,color=color,lw=2.4)
        summary.append({'run':name,'label':label,'duration_s':round(float(t[-1]),2),
                        'distance_30s_m':at(data,30,1),'distance_45s_m':at(data,45,1),
                        'distance_90s_m':at(data,90,1),'new_volume_30s_m3':at(data,30,2),
                        'new_volume_45s_m3':at(data,45,2),'new_volume_90s_m3':at(data,90,2),
                        'final_mission_state':data[-1][3], 'final_execution_status':data[-1][4]})
    axes[0].set_ylabel('累计行驶距离 (m)')
    axes[1].set_ylabel('新增自由空间体积 (m$^3$)')
    axes[1].set_xlabel('首帧有效点云后的时间 (s)')
    for ax in axes:
        ax.grid(alpha=.25)
        ax.set_xlim(0,90)
    axes[0].legend(loc='upper left',fontsize=9,framealpha=1)
    fig.suptitle('车库 XYθ 探索：历次实测进展\n'
                 '地图历史不同；此图是观察性对比，并非严格 A/B 测试',fontsize=13)
    fig.savefig(OUT/'garage_xytheta_comparison.png',dpi=180,bbox_inches='tight')
    fig.savefig(OUT/'garage_xytheta_comparison.svg',bbox_inches='tight')
    plt.close(fig)
    with (OUT/'comparison_summary.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=summary[0].keys());w.writeheader();w.writerows(summary)
    (OUT/'comparison_notes.json').write_text(json.dumps({
        'alignment':'first nonzero registered-scan volume; distance and volume reset to zero there',
        'horizon_s':90,'runs':summary,
        'caveat':'Different start positions and map histories; new run was staged near old run start before metrics.'
    },ensure_ascii=False,indent=2))
    print(json.dumps(summary,ensure_ascii=False))

if __name__=='__main__':main()
