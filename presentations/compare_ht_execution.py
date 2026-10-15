#!/usr/bin/env python3
"""Compare two actual HT-driven trials, including unfinished-goal reversals."""
import argparse
import csv
import json
import math
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import rosbag2_py
from rclpy.serialization import deserialize_message
from nav_msgs.msg import Odometry, Path as RosPath


def audit(folder):
    origin=json.loads((folder/'current/measurement_started.json').read_text())['wall_time']
    summary=json.loads((folder/'summary.json').read_text())
    commands=json.loads((folder/'delivery_and_pause_audit.json').read_text())
    reader=rosbag2_py.SequentialReader()
    reader.open(rosbag2_py.StorageOptions(uri=str(folder/'original_bag'),storage_id='mcap'),rosbag2_py.ConverterOptions('',''))
    reader.set_filter(rosbag2_py.StorageFilter(topics=['/ht_xytheta_path','/state_estimation']))
    robot=None;previous_goal=None;paths=[];flips=0;spins=0
    while reader.has_next():
        topic,payload,ns=reader.read_next();t=ns/1e9-origin
        if topic=='/state_estimation':
            msg=deserialize_message(payload,Odometry);p=msg.pose.pose.position
            robot=np.array([p.x,p.y])
        elif robot is not None and 0<=t<=summary['duration_s']:
            msg=deserialize_message(payload,RosPath)
            if len(msg.poses)<2:continue
            points=np.array([[p.pose.position.x,p.pose.position.y] for p in msg.poses])
            goal=points[-1]
            starts_spin=np.linalg.norm(points[1]-points[0])<1e-4
            spins+=starts_spin
            if previous_goal is not None:
                a=previous_goal-robot;b=goal-robot
                if min(np.linalg.norm(a),np.linalg.norm(b))>.8 and np.dot(a,b)<0:
                    flips+=1
            paths.append({'t_s':t,'robot':robot.tolist(),'goal':goal.tolist(),'starts_spin':bool(starts_spin)})
            previous_goal=goal
    result={'duration_s':summary['duration_s'],'distance_m':summary['distance_m'],
            'visited_1m_xy_cells':summary['visited_1m_xy_cells'],
            'fully_stopped_fraction':commands['fully_zero_commands']/max(1,commands['commands']),
            'stationary_turn_fraction':commands['stationary_turn_commands']/max(1,commands['commands']),
            'published_nonempty_paths':len(paths),'paths_starting_spin':int(spins),
            'unfinished_goal_direction_reversals':flips,
            'ht_status_callbacks':summary['ht_status_callbacks'],
            'zero_by_follower_reason':commands.get('zero_by_follower_reason',{}),
            'exploration_finished':summary['exploration_finished']}
    rows=list(csv.DictReader((folder/'current/timeseries.csv').open()))
    times=np.array([float(r['t_s']) for r in rows]);distances=np.array([float(r['distance_m']) for r in rows])
    moving=np.flatnonzero(np.diff(distances)>.005)
    result['last_observed_translation_s']=float(times[moving[-1]+1]) if len(moving) else 0.
    result['distance_last_60_s_m']=float(distances[-1]-np.interp(summary['duration_s']-60,times,distances))
    return result,paths


def main():
    parser=argparse.ArgumentParser();parser.add_argument('before',type=Path);parser.add_argument('after',type=Path)
    args=parser.parse_args();out=args.after/'execution_comparison';out.mkdir(exist_ok=True)
    results={};trials=[]
    for label,folder in [('before',args.before),('after',args.after)]:
        results[label],paths=audit(folder)
        (out/f'{label}_paths.json').write_text(json.dumps(paths,indent=2)+'\n')
        trials.append(list(csv.DictReader((folder/'current/timeseries.csv').open())))
    results['limits']=['One run per version; these are trajectory/control metrics, not explored volume.',
        'A target-direction reversal can be legitimate; count only measures replanning changes before the previous goal is reached.',
        'The after run includes extra local HT execution validation; no HT threshold or speed limit was relaxed.']
    (out/'comparison.json').write_text(json.dumps(results,indent=2)+'\n')
    fig,axes=plt.subplots(1,3,figsize=(15,4.7),layout='constrained')
    for label,rows,color in zip(['Before','After'],trials,['#4477aa','#228833']):
        t=np.array([float(r['t_s']) for r in rows]);x=np.array([float(r['x_m']) for r in rows]);y=np.array([float(r['y_m']) for r in rows])
        d=np.array([float(r['distance_m']) for r in rows])
        axes[0].plot(x,y,color=color,label=label);axes[0].scatter(x[0],y[0],color=color,marker='o');axes[0].scatter(x[-1],y[-1],color=color,marker='x')
        axes[1].plot(t,d,color=color,label=label)
    axes[0].set(xlabel='World X (m)',ylabel='World Y (m)',title='Actual vehicle trajectory');axes[0].axis('equal');axes[0].legend()
    axes[1].set(xlabel='Time (s)',ylabel='Distance (m)',title='Travel distance');axes[1].legend()
    labels=['Fully stopped','Stationary turning'];positions=np.arange(2)
    for i,(label,color) in enumerate([('before','#4477aa'),('after','#228833')]):
        r=results[label];axes[2].bar(positions+(i-.5)*.35,[100*r['fully_stopped_fraction'],100*r['stationary_turn_fraction']],width=.35,label=label.capitalize(),color=color)
    axes[2].set(xticks=positions,xticklabels=labels,ylabel='Control samples (%)',title='Execution interruptions');axes[2].legend()
    for ax in axes:ax.grid(alpha=.2)
    fig.savefig(out/'comparison.png',dpi=180);plt.close(fig)
    print(json.dumps(results,indent=2))


if __name__=='__main__':main()
