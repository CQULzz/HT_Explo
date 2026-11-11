from pathlib import Path
import sys,json,numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from rclpy.serialization import deserialize_message
from grid_map_msgs.msg import GridMap
sys.path.insert(0,'/home/lzz/HT_Explo_ht_only_20261111/tools/cmu_minimal');from audit_commands import decode
root=Path('/home/lzz/ht_only_20261111');data=root/'analysis/live_indoor_stop';r=json.loads((data/'SEARCH.json').read_text());m=decode(deserialize_message((data/'global_local.cdr').read_bytes(),GridMap));route=np.array(r['results'][-1]['path']);rr,cc=np.where(m['occupied']);xx=m['cx']+(m['rows']/2-rr-.5)*m['res'];yy=m['cy']+(m['cols']/2-cc-.5)*m['res']
plt.rcParams.update({'font.family':'sans-serif','font.sans-serif':['Noto Sans CJK JP','DejaVu Sans'],'axes.unicode_minus':False});fig,ax=plt.subplots(figsize=(9,8));ax.scatter(xx,yy,s=1,c='#fecaca',label='HT足迹膨胀后的占用位置');ax.plot(route[:,0],route[:,1],c='#0f766e',lw=2,label='独立搜索的静态HT可行前缀');ax.scatter(*r['start'][:2],s=60,c='#ea580c',label='实际停车点')
for i in range(len(route)):
 if i==0 or i==len(route)-1 or abs(route[i,2]-route[i-1,2])>.2:ax.arrow(route[i,0],route[i,1],.18*np.cos(route[i,2]),.18*np.sin(route[i,2]),width=.012,color='#334155')
ax.set(xlim=(m['cx']-m['rows']*m['res']/2,m['cx']+m['rows']*m['res']/2),ylim=(m['cy']-m['cols']*m['res']/2,m['cy']+m['cols']*m['res']/2),aspect='equal',xlabel='地图X / m',ylabel='地图Y / m',title='CMU停车现场：HT局部空间内存在另一个静态可行前缀');ax.legend(loc='upper right');ax.grid(alpha=.15);fig.text(.5,.055,'前缀长2.357m，向目标接近2.036m，最低分0.651；目标位于局部HT窗口之外。',ha='center',fontsize=11);fig.text(.5,.025,'静态位置/朝向约束检查通过；未验证跟踪、制动、未来地图、完整到达或动力学。',ha='center',fontsize=10);fig.tight_layout(rect=(0,.08,1,1));fig.savefig(root/'delivery/indoor_static_recovery.png',dpi=160)
