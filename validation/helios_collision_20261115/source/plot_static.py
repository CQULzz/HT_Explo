from pathlib import Path
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from matplotlib.font_manager import FontProperties
root=Path('/home/lzz/ht_helios_collision_20261115');out=Path('/mnt/d/HT-Helios-Collision-20261115/analysis');out.mkdir(exist_ok=True)
font=FontProperties(fname='/mnt/c/Windows/Fonts/msyh.ttc');manifest=json.loads((root/'common_sensor_optical/MANIFEST.json').read_text());height=manifest['lidar_height_above_ground_m'];results={r['case']:r for r in json.loads((root/'static_probes_optical/RESULTS.json').read_text())}
fig,axs=plt.subplots(1,2,figsize=(12,5))
for ax,case,title in zip(axs,['transparent','opaque'],['同样32线：透明车体','同样32线：恢复碰撞与遮挡']):
    a=np.load(root/'static_probes_optical'/(case+'.npz'))['filtered'];x=a['x']+.1725;y=a['y'];z=a['z']+height;mask=np.isfinite(x)&(abs(z)<.015)&(abs(x)<1.3)&(abs(y)<1.3)
    ax.scatter(x[mask],y[mask],s=2,c='teal');ax.add_patch(Rectangle((-.4649301,-.349795),.9298609,.69959,fill=False,edgecolor='tab:orange',lw=2,label='整车URDF投影外框'));ax.add_patch(Rectangle((-.44,-.15),.88,.30,fill=False,edgecolor='red',ls='--',lw=1.5,label='实体底盘下方检查区'));ax.plot(.1725,0,'r*',ms=10,label='雷达参考位置')
    ax.set_title(title+'\n底盘下地面回波：'+str(results[case]['ground_points_under_solid_chassis']),fontproperties=font);ax.axis('equal');ax.set_xlim(-1.3,1.3);ax.set_ylim(-1.3,1.3);ax.grid(alpha=.2);ax.legend(prop=font,loc='upper right');ax.set_xlabel('base_link X / m');ax.set_ylabel('base_link Y / m')
fig.tight_layout();fig.savefig(out/'initial_self_occlusion.png',dpi=155);plt.close(fig)
angles=manifest['profile']['vertical_angles_deg'];fig,ax=plt.subplots(figsize=(10,4));ax.scatter(range(1,33),angles);ax.set_xticks(range(1,33));ax.grid(alpha=.25);ax.set_xlabel('通道编号（手册顺序）',fontproperties=font);ax.set_ylabel('垂直角 / 度',fontproperties=font);ax.set_title('RS-Helios-5515 标称32条非均匀线束（非真机DIFOP标定）',fontproperties=font);fig.tight_layout();fig.savefig(out/'nominal_channel_angles.png',dpi=150);plt.close(fig)
print('Static visibility figures prepared')
