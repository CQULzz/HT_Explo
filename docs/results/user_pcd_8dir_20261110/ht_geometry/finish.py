from pathlib import Path
import json,struct
import numpy as np
import rosbag2_py
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap,BoundaryNorm
from matplotlib.patches import Circle,Patch
ROOT=Path('/home/lzz/pcd_test_20261110');OUT=ROOT/'analysis/ht_geometry/exact';result=json.loads((OUT/'RESULT.json').read_text());start=json.loads((ROOT/'runs/user_pcd_8dir_600s_01/observations/START.json').read_text())['clock'];wanted={round(start+f['ht_source_elapsed_s'],6):f for f in result['frames']}
reader=rosbag2_py.SequentialReader();reader.open(rosbag2_py.StorageOptions(uri=str(ROOT/'runs/user_pcd_8dir_600s_01/bag'),storage_id='mcap'),rosbag2_py.ConverterOptions('',''));reader.set_filter(rosbag2_py.StorageFilter(topics=['/ht_traversability/global_local']))
while reader.has_next() and wanted:
 topic,data,received=reader.read_next();assert data[:2]==b'\x00\x01';sec,nsec=struct.unpack_from('<iI',data,4);source=sec+nsec*1e-9;k=round(source,6)
 if k in wanted:
  f=wanted.pop(k);f['ht_age_s_at_bag_receipt']=received/1e9-source
assert not wanted
result['maximum_sample_ht_receipt_age_s']=max(f['ht_age_s_at_bag_receipt'] for f in result['frames']);assert result['maximum_sample_ht_receipt_age_s']<=1
(OUT/'RESULT.json').write_text(json.dumps(result,indent=2))
plt.rcParams.update({'font.family':'sans-serif','font.sans-serif':['Noto Sans CJK JP','DejaVu Sans'],'axes.unicode_minus':False})
f=np.load(OUT/'frame_07.npz');common=f['common'];ht=f['ht_any'];count=f['geometry_count'];classes=np.zeros(ht.shape,dtype=int);classes[common&ht&(count==0)]=1;classes[common&~ht&(count==0)]=2;classes[common&ht&(count>=2)]=3;classes[common&~ht&(count>=2)]=4;classes[common&(count==1)]=5
colors=['#f1f5f9','#0f766e','#2563eb','#dc2626','#475569','#f59e0b'];cmap=ListedColormap(colors);fig,axes=plt.subplots(1,2,figsize=(13,6));x,y=f['x'],f['y'];axes[0].pcolormesh(x,y,classes,cmap=cmap,vmin=-.5,vmax=5.5,shading='nearest');axes[0].set(aspect='equal',xlabel='地图 X / m',ylabel='地图 Y / m',title='约59秒：统一0.45m圆形足迹的逐点对照\nHT点通过=至少一个方向通过完整HT门禁')
labels=['域外/未比较','两者通过','几何未检出障碍、HT拒绝','HT通过、几何包络内≥2障碍','两者拒绝','几何包络内仅1个障碍，单列'];axes[0].legend(handles=[Patch(color=c,label=l) for c,l in zip(colors,labels)],fontsize=8,loc='lower left')
e=next(e for e in result['counterexamples'] if 59<=e['ht_source_elapsed_s']<61);cx,cy=e['x'],e['y'];ob=f['obstacles'];near=ob[np.linalg.norm(ob[:,:2]-[cx,cy],axis=1)<1.];axes[1].scatter(near[:,0],near[:,1],c=near[:,3],cmap='autumn',s=45,vmin=.15,vmax=.3);axes[1].add_patch(Circle((cx,cy),.45,fill=False,color='black',lw=2));axes[1].scatter(cx,cy,c='#0f766e',s=70);axes[1].set(xlim=(cx-.75,cx+.75),ylim=(cy-.75,cy+.75),aspect='equal',xlabel='地图 X / m',ylabel='地图 Y / m',title=f'反例 ({cx:.3f}, {cy:.3f})\nHT方向3={e["eight_scores"][3]:.3f}，圆内6个CMU障碍体素')
axes[1].text(.03,.03,'HT支撑有效、occupied=false\n几何高度值约0.151～0.156，门限0.15m\n比较规则的分歧，不能据此判定真实地形对错',transform=axes[1].transAxes,fontsize=9,bbox={'facecolor':'white','alpha':.9})
fig.suptitle('HT不是几何判据的严格子集：来自同源时间戳数据的反例\n几何为点/足迹包络对照，不是完整CMU路径组碰撞评分重算',fontsize=12);fig.tight_layout();fig.savefig(OUT/'comparison.png',dpi=160);plt.close(fig)
print('maximum HT receipt age',result['maximum_sample_ht_receipt_age_s']);print('HT allow / geometric proxy conflict fraction',result['fraction_ht_allowed_states_with_geometric_proxy_reject'])
