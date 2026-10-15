#!/usr/bin/env python3
"""Render two actual camera streams and trajectories at equal experiment time."""
import argparse
import csv
import json
import subprocess
from pathlib import Path

import cv2
import numpy as np
from cv_bridge import CvBridge
from rclpy.serialization import deserialize_message
from sensor_msgs.msg import Image
from summarize_tare_ht_pair import reader


class Camera:
    def __init__(self,bag,origin):
        self.r=reader(bag,['/camera/image_raw']);self.origin=origin
        self.bridge=CvBridge();self.future=None;self.previous=None;self.advance()
    def advance(self):
        if not self.r.has_next():self.future=None;return
        _,data,ns=self.r.read_next();self.future=(ns/1e9-self.origin,data)
    def at(self,t):
        while self.future is not None and self.future[0]<=t:
            self.previous=self.future;self.advance()
        item=self.previous or self.future
        if item is None:raise RuntimeError('No camera image in recorded bag')
        return self.bridge.imgmsg_to_cv2(deserialize_message(item[1],Image),'bgr8')


def main():
    ap=argparse.ArgumentParser();ap.add_argument('folder',type=Path);ap.add_argument('--encoder',required=True);a=ap.parse_args();p=a.folder.resolve()
    duration=json.loads((p/'pair_summary.json').read_text())['current']['duration_s'];streams=[];all_xy=[]
    for name in ['original','current']:
        origin=json.loads((p/name/'measurement_started.json').read_text())['wall_time'];rows=list(csv.DictReader((p/name/'timeseries.csv').open()));v=list(csv.DictReader((p/name/'observation_volume.csv').open()));xy=np.array([[float(r['x_m']),float(r['y_m'])] for r in rows]);all_xy.append(xy)
        streams.append({'camera':Camera(p/(name+'_bag'),origin),'t':np.array([float(r['t_s']) for r in rows]),'xy':xy,
                        'distance':np.array([float(r['distance_m']) for r in rows]),
                        'vt':np.array([float(r['time_s']) for r in v]),'volume':np.array([float(r['observed_free_volume_m3']) for r in v])})
    points=np.concatenate(all_xy);low=points.min(axis=0)-2;high=points.max(axis=0)+2;span=max(high-low);center=(high+low)/2
    out=p/'comparison.mp4';log=(p/'video_encode.log').open('w')
    proc=subprocess.Popen([a.encoder,'-y','-loglevel','warning','-f','rawvideo','-pix_fmt','bgr24','-s','1600x960','-r','10','-i','-',
                           '-an','-c:v','libx264','-preset','fast','-crf','20','-pix_fmt','yuv420p','-movflags','+faststart','-threads','2',str(out)],stdin=subprocess.PIPE,stderr=log)
    colors=[(190,110,35),(40,140,230)]
    def text(im,label,xy,scale=.65,color=(235,235,235)):
        cv2.putText(im,label,xy,cv2.FONT_HERSHEY_SIMPLEX,scale,color,1,cv2.LINE_AA)
    try:
        for frame_i in range(int(duration*10)):
            t=frame_i/10;im=np.full((960,1600,3),25,np.uint8)
            for k,(s,label) in enumerate(zip(streams,['ORIGINAL TARE','CURRENT HT + XYTHETA'])):
                x=k*800;text(im,label,(x+20,35),.9,colors[k]);text(im,f'Actual recorded camera | t={t:.1f}s',(x+20,65),.6)
                im[80:513,x+15:x+785]=cv2.resize(s['camera'].at(t),(770,433),interpolation=cv2.INTER_AREA)
                traveled=np.interp(t,s['t'],s['distance']);observed=np.interp(t,s['vt'],s['volume'])
                text(im,f'Travel: {traveled:.2f} m',(x+25,550),.75);text(im,f'Observed free space: {observed:.1f} m3',(x+25,580),.7)
                text(im,'Actual XY trajectory | identical world scale',(x+25,610),.6)
                def project(xy):return np.c_[x+400+310*(xy[:,0]-center[0])/span,775-310*(xy[:,1]-center[1])/span].astype(np.int32)
                cv2.rectangle(im,(x+215,615),(x+585,930),(65,65,65),1)
                trail=s['xy'][s['t']<=t]
                if len(trail)>1:cv2.polylines(im,[project(trail)],False,colors[k],2,cv2.LINE_AA)
                now=np.array([[np.interp(t,s['t'],s['xy'][:,i]) for i in range(2)]])
                cv2.circle(im,tuple(project(now)[0]),5,colors[k],-1)
                text(im,f'World scale: {span:.1f} m across',(x+25,945),.5)
            cv2.line(im,(800,0),(800,960),(100,100,100),1);proc.stdin.write(im.tobytes())
        proc.stdin.close();code=proc.wait(timeout=120)
        if code:raise RuntimeError(f'Video encoder failed: {code}')
    finally:
        if proc.poll() is None:proc.terminate();proc.wait(timeout=10)
        log.close()
    v=cv2.VideoCapture(str(out));count=int(v.get(cv2.CAP_PROP_FRAME_COUNT));fps=v.get(cv2.CAP_PROP_FPS)
    if count!=int(duration*10) or fps!=10:raise RuntimeError('Incorrect comparison video duration')
    for index in [0,count//2,count-1]:
        v.set(cv2.CAP_PROP_POS_FRAMES,index);ok,im=v.read()
        if not ok:raise RuntimeError(f'Cannot decode frame {index}')
        if index==count//2:cv2.imwrite(str(p/'comparison_video_preview.jpg'),im)
    v.release();print(out)


if __name__=='__main__':main()
