#!/usr/bin/env python3
"""Plot the archived, read-only Garage run 2 diagnostic snapshot."""
import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import numpy as np


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('snapshot',type=Path)
    args=parser.parse_args()
    data=json.loads(args.snapshot.read_text())
    robot=np.array(data['position'])
    route=np.array(data['paths'][0]['xyz'])
    candidates=np.array(data['nearby_geometry']['/viewpoint_vis_cloud']['xyz'])
    points=np.array(data['nearby_geometry']['/collision_cloud']['xyz'])
    resolution=1.2  # Garage viewpoint_manager/resolution_x/y (not coverage resolution).
    fig,ax=plt.subplots(figsize=(7,6),layout='constrained')
    for cell in candidates:
        ax.add_patch(Rectangle(cell[:2]-resolution/2,resolution,resolution,
                               facecolor='#d3e9d3',edgecolor='white',alpha=.65))
    near=points[(points[:,2]>.3)&(points[:,2]<1.4)]
    ax.scatter(near[:,0],near[:,1],s=1,c='#555555',alpha=.3,label='Nearby collision points')
    label='Not a candidate cell'
    for x in (route[0,0],route[1,0]):
        for y in (route[0,1],route[1,1]):
            if np.min(np.linalg.norm(candidates[:,:2]-[x,y],axis=1))<1e-4:
                continue
            ax.add_patch(Rectangle((x-resolution/2,y-resolution/2),resolution,resolution,
                                   facecolor='#f6b3a8',alpha=.6,label=label))
            label=None
    ax.plot(route[:4,0],route[:4,1],'o-',label='Published grid route')
    ax.plot([robot[0],route[1,0]],[robot[1],route[1,1]],'--',color='#c53030',lw=2,
            label='Direct robot-to-next-node segment')
    ax.scatter(*robot[:2],c='black',marker='*',s=150,label='Stopped robot')
    ax.set(xlim=(5.8,8.8),ylim=(25.1,28.6),xlabel='World X (m)',ylabel='World Y (m)',
           title='HT run 2: stalled route near a grid corner')
    ax.set_aspect('equal')
    ax.legend(fontsize=8,loc='upper left')
    fig.savefig(args.snapshot.parent/'stall_geometry.png',dpi=180)
    plt.close(fig)


if __name__=='__main__':
    main()
