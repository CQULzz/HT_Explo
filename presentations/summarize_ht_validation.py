#!/usr/bin/env python3
"""Audit recorded input delivery and actual execution pauses after a live trial."""
import argparse
import json
from pathlib import Path
import cv2
import rosbag2_py
from rclpy.serialization import deserialize_message
from sensor_msgs.msg import PointCloud2
from geometry_msgs.msg import TwistStamped
from nav_msgs.msg import Path as RosPath
from std_msgs.msg import Bool, String


def main():
    parser=argparse.ArgumentParser();parser.add_argument('folder',type=Path);args=parser.parse_args();folder=args.folder.resolve()
    summary=json.loads((folder/'summary.json').read_text())
    stats=json.loads((folder/'current/cupy_processing_stats.json').read_text())
    origin=json.loads((folder/'current/measurement_started.json').read_text())['wall_time']
    reader=rosbag2_py.SequentialReader();reader.open(rosbag2_py.StorageOptions(uri=str(folder/'original_bag'),storage_id='mcap'),rosbag2_py.ConverterOptions('',''))
    reader.set_filter(rosbag2_py.StorageFilter(topics=['/registered_scan','/cmd_vel','/ht_navigation_allowed','/ht_xytheta_path','/ht_follower_status']))
    frames=0;processed_span=0;commands=0;zero=0;turn=0;permission_stale=0;permission_false=0;path_stale=0
    permission=False;permission_t=-1e30;path_t=-1e30
    follower_reason=None;zero_reasons={}
    while reader.has_next():
        topic,payload,ns=reader.read_next();t=ns/1e9
        if topic=='/registered_scan':
            msg=deserialize_message(payload,PointCloud2);stamp=msg.header.stamp.sec+msg.header.stamp.nanosec*1e-9
            if stats['first_cloud_source_stamp_s']-1e-6<=stamp<=stats['last_cloud_source_stamp_s']+1e-6:frames+=1
            if stats['first_cloud_source_stamp_s']-1e-6<=stamp<=stats['last_processed_cloud_source_stamp_s']+1e-6:processed_span+=1
        elif topic=='/ht_navigation_allowed':permission=deserialize_message(payload,Bool).data;permission_t=t
        elif topic=='/ht_follower_status':follower_reason=deserialize_message(payload,String).data
        elif topic=='/ht_xytheta_path':
            if deserialize_message(payload,RosPath).poses:path_t=t
        elif origin<=t<origin+summary['duration_s']:
            msg=deserialize_message(payload,TwistStamped);v=abs(msg.twist.linear.x);w=abs(msg.twist.angular.z);commands+=1
            if v<.01 and w>.05:turn+=1
            if v<.01 and w<.05:
                zero+=1
                if follower_reason is not None:zero_reasons[follower_reason]=zero_reasons.get(follower_reason,0)+1
                if t-permission_t>1.5:permission_stale+=1
                elif not permission:permission_false+=1
                elif t-path_t>3.:path_stale+=1
    result={'bag_frames_in_callback_source_span':frames,'received_callbacks':stats['received_cloud_callbacks'],
            'bag_frames_in_successful_processing_source_span':processed_span,'processed_clouds':stats['processed_clouds'],
            'commands':commands,'fully_zero_commands':zero,'stationary_turn_commands':turn,
            'zero_with_expired_permission':permission_stale,'zero_with_false_permission':permission_false,
            'zero_with_expired_path':path_stale,
            'zero_by_follower_reason':zero_reasons,
            'notes':['Delivery counts refer to recorded source-stamp intervals. Shutdown may interrupt a final callback.',
                     'Permission age >1.5s is a legacy diagnostic, not a stop condition when the follower independently validates HT. Path expiry remains3s.',
                     'Follower reasons are matched by receive order; counts near reason transitions can differ by one control sample.']}
    (folder/'delivery_and_pause_audit.json').write_text(json.dumps(result,indent=2)+'\n')
    video=folder/'visuals/current_ht_exploration.mp4'
    if video.exists():
        capture=cv2.VideoCapture(str(video));capture.set(cv2.CAP_PROP_POS_MSEC,min(30000,summary['duration_s']*500));ok,frame=capture.read()
        if ok:cv2.imwrite(str(folder/'visuals/video_preview.png'),frame)
        result['video']={'frames':int(capture.get(cv2.CAP_PROP_FRAME_COUNT)),'fps':capture.get(cv2.CAP_PROP_FPS),'width':int(capture.get(cv2.CAP_PROP_FRAME_WIDTH)),'height':int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))};capture.release()
        (folder/'delivery_and_pause_audit.json').write_text(json.dumps(result,indent=2)+'\n')
    lines=['# 当前 HT 控车验证','',f"记录 {summary['duration_s']:.0f} 秒，行驶 {summary['distance_m']:.2f} 米，到访 {summary['visited_1m_xy_cells']} 个1米轨迹格；探索完成：{summary['exploration_finished']}。",'',
           '运行按预设时长结束，不代表探索完成。1米轨迹格仅统计车走过的位置，不是探索面积或体积。','',
           '建图已修正坐标与历史融合。本轮如含 /ht_follower_status，则使用独立HT执行校验；控制许可年龄超过1.5秒仅是旧版诊断，不能再直接解释为停车原因。路径仍须在3秒以内，地图和传感器仍须新鲜，显式禁止信号仍停车。','',
           '本轮由当前 HT/XYθ 规划与跟踪器实际控车，非原版轨迹离线计算。视频紫线来自实际发布的 /ht_xytheta_path，右下角显示实际姿态路径。','',
           f"HT 状态：{summary['ht_status_callbacks']}；最大 HT 图年龄 {summary['ht_map_age_max_s']:.3f} 秒。",'',
           f"点云对应时间窗口：录包 {frames} 帧，接收 {stats['received_cloud_callbacks']} 帧；成功处理窗口录包 {processed_span} 帧，完成融合 {stats['processed_clouds']} 帧。",'',
           f"接收排队：中位数 {stats['queue_age_median_s']:.3f} 秒，P95 {stats['queue_age_p95_s']:.3f} 秒，最大 {stats['queue_age_max_s']:.3f} 秒。",'',
           f"完全零速指令 {zero}/{commands}，其中许可超过1.5秒未续期 {permission_stale} 次、许可为假 {permission_false} 次、路径超过3秒 {path_stale} 次。原地转向指令另计 {turn} 次。",'',
           f"执行端报告的零速原因（按录包接收顺序对应）：{zero_reasons}。",'',
           '上述次数是20Hz控制指令样本数，不是停车事件次数；过期状态与零速同时出现，不能仅据此排除其他停车条件。summary.json 的 zero_cmd_fraction 按线速度统计，包含原地转向，不能当作完全停车比例。','',
           '最后一帧点云可能在结束时被中断，接收数与融合数应分别核对。日志末尾的 KeyboardInterrupt 与仿真节点退出异常发生在脚本主动停止阶段，应与运行期间故障区分。','',
           f"TARE /runtime 指标中位数 {summary['planner_runtime_median_s']:.3f} 秒、P95 {summary['planner_runtime_p95_s']:.3f} 秒；该指标不等于整条感知到控制链路的延迟。",'',
           '地图坐标、分层历史和真实观测时间已修正；远处噪声、未知区及执行停顿仍应结合视频检查，不能宣称探索已全部解决。模型八通道物理角度仍待实车标定。','',
           '[视频](visuals/current_ht_exploration.mp4) · [预览](visuals/video_preview.png) · [八通道地图](visuals/late_eight_direction_ht.png) · [原始指标](summary.json) · [接收与停顿审计](delivery_and_pause_audit.json)']
    (folder/'REPORT.md').write_text('\n'.join(lines)+'\n')
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
