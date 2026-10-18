#!/usr/bin/env python3
"""Show the two recorded HT fields queried at one identical world pose."""
import argparse
import json
from pathlib import Path

import cv2
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap,BoundaryNorm
import numpy as np


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('folder',type=Path);args=ap.parse_args()
    event=json.loads((args.folder/'transition.json').read_text())
    plt.rcParams.update({'font.family':'Noto Sans CJK JP','axes.unicode_minus':False})
    fig,axes=plt.subplots(2,2,figsize=(11,10),layout='constrained')
    for col,label in enumerate(('before','after')):
        with np.load(args.folder/(label+'.npz')) as a:
            x,y,yaw=a['robot'];cx,cy,res=a['ht_geometry'];valid=a['ht_ht_valid']>=.5
            physical=a['ht_ht_observation_valid']>=.5;n,m=valid.shape;k=event[label]['heading_bin']
            p=a[f'ht_ht_dir_{k}'];radius=int(np.ceil(.6/res)+1);i,j=np.mgrid[-radius:radius+1,-radius:radius+1]
            kernel=(np.hypot(i,j)*res<=.6+np.sqrt(2)*res).astype('uint8')
            unknown=cv2.dilate((~physical).astype('uint8'),kernel,borderType=cv2.BORDER_CONSTANT,borderValue=1)>0
            blocked=cv2.dilate((valid&(p<.5)).astype('uint8'),kernel,borderType=cv2.BORDER_CONSTANT,borderValue=0)>0
            status=np.where(blocked,2,np.where(unknown|~valid,0,1))
            extent=(cx-n*res/2,cx+n*res/2,cy-m*res/2,cy+m*res/2)
            cmap=plt.get_cmap('RdYlGn').copy();cmap.set_bad('#bfc3c6')
            im=axes[0,col].imshow(np.where(valid,p,np.nan)[::-1,::-1].T,origin='lower',extent=extent,cmap=cmap,vmin=0,vmax=1,interpolation='nearest')
            axes[0,col].set_title(('更新前' if col==0 else '更新后')+f'：HT通道{k}\n足迹最小概率 {event[label]["min_body_p"]:.6f}')
            axes[1,col].imshow(status[::-1,::-1].T,origin='lower',extent=extent,cmap=ListedColormap(['#bfc3c6','#50a66b','#c84b45']),norm=BoundaryNorm([-.5,.5,1.5,2.5],3),interpolation='nearest')
            axes[1,col].set_title('同一世界位姿的硬判定：'+event[label]['status'])
            for ax in axes[:,col]:
                ax.plot(x,y,'b+',ms=12);ax.arrow(x,y,.35*np.cos(yaw),.35*np.sin(yaw),color='blue',width=.012)
                ax.set(xlim=(x-1.6,x+1.6),ylim=(y-1.6,y+1.6),xlabel='世界X / m',ylabel='世界Y / m')
    fig.colorbar(im,ax=axes[0,:],label='HT模型概率；上排灰=神经预测无效；下排为当前足迹硬判定')
    fig.suptitle(f'第{event["time_s"]:.3f}秒：车位不变，新HT地图使起点从允许变成禁止\n两图按世界坐标对齐，数组下标随窗口移动；这是模型判定变化，不是真实地形突然变化的证明',fontsize=13)
    fig.savefig(args.folder/'stationary_map_change.png',dpi=170);plt.close(fig)


if __name__=='__main__':main()
