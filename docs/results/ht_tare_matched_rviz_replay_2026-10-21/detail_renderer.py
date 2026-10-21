#!/usr/bin/env python3
"""Visual-only replay of stage47 evidence in actual RViz; never publishes controls.

Source MCAPs/archives are read-only. The private pickle cache is trusted local
derived data, not an interchange format. Source events use bag receipt time;
point geometry and the rolling GridMap indexing are preserved. Only display
density is reduced. No simulation, inference, planner, or follower is launched.
"""
import argparse
import bisect
import collections
import csv
import hashlib
import json
import math
import os
from pathlib import Path
import pickle
import signal
import subprocess
import time

import numpy as np
import yaml


def sha(path):
    return hashlib.file_digest(Path(path).open('rb'), 'sha256').hexdigest()


def prepare(suite, cache):
    import rosbag2_py
    from rclpy.serialization import deserialize_message
    from rosidl_runtime_py.utilities import get_message
    from sensor_msgs_py.point_cloud2 import read_points_numpy
    topics = {'/state_estimation': 'pose', '/endurance/registered_scan': 'scan',
              '/global_path': 'global', '/local_path': 'coverage',
              '/tare_coverage_route': 'coverage', '/ht_xytheta_path': 'execution',
              '/way_point': 'waypoint', '/ht_route_goal': 'route_goal',
              '/ht_traversability/global_local': 'ht',
              '/ht_follower_status': 'follower', '/ht_execution_status': 'status'}
    result = {'schema': 1, 'duration_s': 600, 'sources': {}, 'data': {}}
    for name in ('original', 'ht'):
        base = suite/name
        origin = json.loads((base/'current/measurement_started.json').read_text())['wall_time']
        r = rosbag2_py.SequentialReader()
        r.open(rosbag2_py.StorageOptions(uri=str(base/'evidence_bag'), storage_id='mcap'),
               rosbag2_py.ConverterOptions('', ''))
        types = {v.name: get_message(v.type) for v in r.get_all_topics_and_types() if v.name in topics}
        r.set_filter(rosbag2_py.StorageFilter(topics=list(types)))
        events, initial, counts, last = [], {}, collections.Counter(), {}
        while r.has_next():
            topic, raw, ns = r.read_next()
            t = ns/1e9-origin
            if t > 600:
                continue
            kind = topics[topic]
            # Visual update limits: pose10Hz, status2Hz. Paths/maps are kept.
            rate = .1 if kind == 'pose' else .5 if kind in ('follower', 'status') else 0
            if t >= 0 and t-last.get(topic, -1e6) < rate:
                continue
            m = deserialize_message(raw, types[topic])
            last[topic] = t
            if hasattr(m, 'header') and m.header.frame_id not in ('map', ''):
                raise ValueError(f'Unsupported source frame: {topic}: {m.header.frame_id}')
            if kind == 'pose':
                p, q = m.pose.pose.position, m.pose.pose.orientation
                v = (p.x, p.y, p.z, math.atan2(2*(q.w*q.z+q.x*q.y), 1-2*(q.y*q.y+q.z*q.z)))
            elif kind == 'scan':
                if t < 0:
                    continue
                xyz = np.asarray(read_points_numpy(m, field_names=('x', 'y', 'z'), skip_nans=True), np.float32)
                _, idx = np.unique(np.floor(xyz/.18).astype(np.int32), axis=0, return_index=True)
                v = xyz[idx]
            elif kind in ('global', 'coverage', 'execution'):
                v = np.array([(p.pose.position.x, p.pose.position.y, p.pose.position.z,
                               math.atan2(2*(p.pose.orientation.w*p.pose.orientation.z+p.pose.orientation.x*p.pose.orientation.y),
                                          1-2*(p.pose.orientation.y**2+p.pose.orientation.z**2))) for p in m.poses], np.float32).reshape(-1, 4)
            elif kind in ('waypoint', 'route_goal'):
                v = (m.point.x, m.point.y, m.point.z)
            elif kind == 'ht':
                n, k = round(m.info.length_x/m.info.resolution), round(m.info.length_y/m.info.resolution)
                def layer(key):
                    a = np.asarray(m.data[m.layers.index(key)].data, np.float32).reshape((n, k), order='F')
                    return np.roll(a, (-m.outer_start_index, -m.inner_start_index), (0, 1))[::3, ::3].copy()
                # GridMap index0 is the positive-X/positive-Y corner, not minXY.
                x = m.info.pose.position.x + (n/2-np.arange(0, n, 3)-.5)*m.info.resolution
                y = m.info.pose.position.y + (k/2-np.arange(0, k, 3)-.5)*m.info.resolution
                valid = layer('ht_valid') > .5
                scores = np.stack([layer('ht_dir_'+str(i)) for i in range(8)])
                valid &= np.all(np.isfinite(scores), axis=0)
                v = {'x': x, 'y': y, 'p': scores, 'valid': valid, 'display_cell_m': 3*m.info.resolution,
                     'source_resolution_m': m.info.resolution,
                     'source_age_s': ns/1e9-m.header.stamp.sec-m.header.stamp.nanosec*1e-9}
            else:
                v = m.data
            counts[kind] += 1
            if t < 0:
                initial[kind] = (0., kind, v)
            else:
                events.append((float(t), kind, v))
        events = sorted(list(initial.values())+events, key=lambda e: e[0])
        rows = list(csv.DictReader((base/'current/timeseries.csv').open()))
        volume = list(csv.DictReader((base/'current/observation_volume.csv').open()))
        result['data'][name] = {'events': events, 'rows': rows, 'volume': volume}
        result['sources'][name] = {'bag': str(base/'evidence_bag'), 'origin_wall_time': origin,
                                  'metadata_sha256': sha(base/'evidence_bag/metadata.yaml'),
                                  'display_events': dict(counts), 'event_count': len(events)}
        print(name, len(events), dict(counts), flush=True)
    cache.parent.mkdir(parents=True, exist_ok=True)
    with cache.open('wb') as f:
        pickle.dump(result, f, protocol=5)
    cache.with_suffix('.json').write_text(json.dumps({k:v for k,v in result.items() if k != 'data'}, indent=2)+'\n')


def configs(out):
    def topic(t):
        return {'Value': t, 'Depth': 2, 'History Policy': 'Keep Last',
                'Reliability Policy': 'Reliable', 'Durability Policy': 'Volatile'}
    def make(name, prefix, view, x):
        displays = []
        if view == 'global':
            displays.append({'Class': 'rviz_default_plugins/Grid', 'Name': 'Common10m grid',
                             'Enabled': True, 'Alpha': .28, 'Cell Size': 10., 'Plane Cell Count': 30,
                             'Color': '95; 117; 138', 'Line Style': {'Value': 'Lines', 'Line Width': .03},
                             'Plane': 'XY', 'Reference Frame': 'map'})
            displays.append({'Class': 'rviz_default_plugins/PointCloud2', 'Name': 'Observed lidar surfaces',
                             'Enabled': True, 'Topic': topic(prefix+'/cloud'), 'Color Transformer': 'RGB8',
                             'Position Transformer': 'XYZ', 'Style': 'Points', 'Size (Pixels)': 2,
                             'Size (m)': .18, 'Decay Time': 0, 'Alpha': 1, 'Use Fixed Frame': True})
        displays.append({'Class': 'rviz_default_plugins/MarkerArray', 'Name': 'Recorded routes and robot',
                         'Enabled': True, 'Marker Topic': topic(prefix+'/'+view), 'Topic': topic(prefix+'/'+view)})
        if view == 'global':
            camera = {'Class': 'rviz_default_plugins/TopDownOrtho', 'Scale': 6.7, 'X': 42., 'Y': 10., 'Angle': 0.,
                      'Target Frame': 'map', 'Near Clip Distance': .01}
        elif view == 'local':
            camera = {'Class': 'rviz_default_plugins/TopDownOrtho', 'Scale': 67., 'X': 0., 'Y': 0., 'Angle': 0.,
                      'Target Frame': 'map', 'Near Clip Distance': .01}
        else:
            camera = {'Class': 'rviz_default_plugins/Orbit', 'Distance': 25., 'Pitch': .46, 'Yaw': .8,
                      'Focal Point': {'X': 0., 'Y': 0., 'Z': 5.25}, 'Target Frame': 'map',
                      'Near Clip Distance': .01, 'Focal Shape Fixed Size': True, 'Focal Shape Size': .05}
        cfg = {'Panels': [], 'Visualization Manager': {'Class': '', 'Displays': displays, 'Enabled': True,
                'Global Options': {'Fixed Frame': 'map', 'Background Color': '20; 27; 35', 'Frame Rate': 15},
                'Name': 'root', 'Tools': [{'Class': 'rviz_default_plugins/MoveCamera'}],
                'Views': {'Current': dict(camera, Name='Current View'), 'Saved': []}},
               'Window Geometry': {'X': x, 'Y': 68, 'Width': 960, 'Height': 800,
                                   'Hide Left Dock': True, 'Hide Right Dock': True}}
        (out/(name+'.rviz')).write_text(yaml.safe_dump(cfg, sort_keys=False))
    make('original_global', '/recorded_rviz/original', 'global', 0)
    make('ht_global', '/recorded_rviz/ht', 'global', 960)
    make('ht_local', '/recorded_rviz/ht', 'local', 0)
    make('ht_xytheta', '/recorded_rviz/ht', 'theta', 960)


def replay(cache, out, encoder, mode, display, speed, fps, limit):
    import rclpy
    from rclpy.node import Node
    from visualization_msgs.msg import Marker, MarkerArray
    from geometry_msgs.msg import Point
    from std_msgs.msg import ColorRGBA, Header
    from sensor_msgs.msg import PointCloud2, PointField
    from PIL import ImageGrab, ImageDraw, ImageFont
    import cv2
    data = pickle.loads(cache.read_bytes())
    rclpy.init()
    node = Node('recorded_rviz_visualization_only')
    prefixes = {n: '/recorded_rviz/'+n for n in ('original', 'ht')}
    pubs = {n: {k: node.create_publisher(MarkerArray, prefixes[n]+'/'+k, 2) for k in ('global', 'local', 'theta')}
            for n in prefixes}
    clouds = {n: node.create_publisher(PointCloud2, p+'/cloud', 2) for n,p in prefixes.items()}
    publisher_names = sorted([p.topic_name for group in pubs.values() for p in group.values()]+
                             [p.topic_name for p in clouds.values()])
    processes = []
    config_names = ('original_global', 'ht_global') if mode == 'comparison' else ('ht_local', 'ht_xytheta')
    for name in config_names:
        log = (out/(name+'.log')).open('w')
        processes.append(subprocess.Popen(['rviz2', '-d', str(out/(name+'.rviz')), '--ros-args', '-r', '__node:='+name],
                                         env=dict(os.environ, DISPLAY=display, LIBGL_ALWAYS_SOFTWARE='1', QT_QPA_PLATFORM='xcb'),
                                         stdout=log, stderr=subprocess.STDOUT))
        log.close()
    # Allow both real RViz renderers to start and discover visualization topics.
    time.sleep(7)
    state = {n: {'idx': 0, 'pose': (0., 0., .75, 0.), 'trail': [], 'surface': {}, 'events': data['data'][n]['events']}
             for n in prefixes}
    fonts = '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc'
    font = ImageFont.truetype(fonts, 23)
    small = ImageFont.truetype(fonts, 20)
    large = ImageFont.truetype(fonts, 29)
    stats = {}
    for n in prefixes:
        rows, vol = data['data'][n]['rows'], data['data'][n]['volume']
        stats[n] = {'t': np.array([float(r['t_s']) for r in rows]), 'rows': rows,
                    'vt': np.array([float(r['time_s']) for r in vol]), 'v': vol}

    def marker(typ, idx, color, scale, pts=None):
        m = Marker(); m.header.frame_id = 'map'; m.ns = 'recorded_'+mode; m.id = idx; m.type = typ
        m.action = Marker.ADD; m.pose.orientation.w = 1.; m.color = ColorRGBA(r=color[0], g=color[1], b=color[2], a=color[3])
        m.scale.x, m.scale.y, m.scale.z = scale
        if pts is not None:
            m.points = [Point(x=float(p[0]), y=float(p[1]), z=float(p[2])) for p in pts]
        return m

    def routes(s, local=False, theta=False):
        result = []
        ox, oy = s['pose'][:2] if local else (0., 0.)
        for idx, (key, col, width) in enumerate((('trail', (0., .85, 1., 1.), .18),
                ('global', (.75, .7, .9, .8), .10), ('coverage', (1., .78, .15, 1.), .16),
                ('execution', (.15, 1., .35, 1.), .20))):
            if key not in s or len(s[key]) < 2:
                continue
            p = np.array(s[key], dtype=float)
            xyz = p[:, :3].copy(); xyz[:, 0] -= ox; xyz[:, 1] -= oy; xyz[:, 2] = .18+idx*.05
            if theta:
                # The complete historical trail is already in the global
                # comparison. In a moving localtheta view it obscures the map.
                if p.shape[1] != 4 or key != 'execution':
                    continue
                # Theta is periodic. Split wrap jumps; do not draw a false
                # vertical crossing from315deg to0deg (or vice versa).
                a = np.mod(p[:, 3], 2*np.pi); xyz[:, 2] = a/(np.pi/4)*1.5+.08
                seg = np.stack((xyz[:-1], xyz[1:]), 1)
                seg = seg[np.abs(np.diff(a)) <= np.pi]
                result.append(marker(Marker.LINE_LIST, idx, col, (width*.8, 0., 0.), seg.reshape(-1, 3)))
            else:
                if local and key == 'trail' and 'ht' in s:
                    h = s['ht']
                    inside = ((p[:,0] >= h['x'].min()) & (p[:,0] <= h['x'].max()) &
                              (p[:,1] >= h['y'].min()) & (p[:,1] <= h['y'].max()))
                    segments = np.stack((xyz[:-1], xyz[1:]), 1)[inside[:-1] & inside[1:]]
                    result.append(marker(Marker.LINE_LIST, idx, col, (width*.4, 0., 0.), segments.reshape(-1,3)))
                else:
                    result.append(marker(Marker.LINE_STRIP, idx, col, (width*(.4 if local else 1.), 0., 0.), xyz))
        px, py, pz, yaw = s['pose']
        robotz = ((yaw%(2*np.pi))/(np.pi/4)*1.5+.2) if theta else .6
        arrow = marker(Marker.ARROW, 10, (0., .8, 1., 1.), (.10 if local else .35, .28 if local else .8, .35),
                       [(px-ox, py-oy, robotz), (px-ox+1.2*np.cos(yaw), py-oy+1.2*np.sin(yaw), robotz)])
        result.append(arrow)
        if not theta:
            for i,key in enumerate(('waypoint', 'route_goal')):
                if key in s:
                    w = s[key]; m = marker(Marker.SPHERE, 20+i, (1., .25, .8, 1.) if i else (1., .9, .2, 1.),
                                           (.45 if local else .9, .45 if local else .9, .45))
                    m.pose.position = Point(x=float(w[0]-ox), y=float(w[1]-oy), z=.65+i*.2)
                    result.append(m)
        return result

    def ht_markers(s, theta=False):
        if 'ht' not in s:
            return []
        h = s['ht']; xx, yy = np.meshgrid(h['x']-s['pose'][0], h['y']-s['pose'][1], indexing='ij')
        # Preserve the eight actual discrete score layers. No angular interpolation.
        selected = range(8) if theta else [int(np.floor((s['pose'][3]%(2*np.pi))/(np.pi/4)+.5))%8]
        result = []
        for k in selected:
            ok = h['valid']; p = h['p'][k]
            z = 1.5*k if theta else 0.
            if theta:
                # Unknown cells transparent in the layered view to avoid hiding
                # lower layers. The local2D view explicitly renders them gray.
                ids = ok
            else:
                ids = np.ones_like(ok)
            points = np.column_stack((xx[ids], yy[ids], np.full(ids.sum(), z)))
            vals = p[ids]; valid = ok[ids]
            colors = np.column_stack((np.interp(vals, [0., .5, 1.], [1., 1., .12]),
                                      np.interp(vals, [0., .5, 1.], [.15, .85, .7]),
                                      np.interp(vals, [0., .5, 1.], [.1, .15, .3]), np.full(len(vals), .88 if theta else 1.)))
            colors[~valid] = (.38, .42, .47, 1.)
            m = marker(Marker.CUBE_LIST, 100+k, (1., 1., 1., 1.),
                       (h['display_cell_m']*.93, h['display_cell_m']*.93, .012), points)
            m.colors = [ColorRGBA(r=float(r), g=float(g), b=float(b), a=float(a)) for r,g,b,a in colors]
            result.append(m)
            if theta:
                label = marker(Marker.TEXT_VIEW_FACING, 200+k, (.92, .94, 1., 1.), (0., 0., .48))
                label.text = str(45*k)+' deg'; label.pose.position = Point(x=5.8, y=-5.5, z=z)
                result.append(label)
        if theta:
            label = marker(Marker.TEXT_VIEW_FACING, 208, (.92, .94, 1., 1.), (0., 0., .4))
            label.text = '360 = 0 deg'; label.pose.position = Point(x=5.8, y=-5.5, z=12.)
            result.append(label)
        return result

    def publish_cloud(n, s):
        if not s['surface']:
            return
        xyz = np.array(list(s['surface'].values()), np.float32)
        # These are actual observed returns, never synthetic free-space voxels.
        height = np.clip(xyz[:, 2]/3, 0., 1.)
        rgb = np.column_stack((170+65*height, 184-45*height, 199-85*height)).astype(np.uint32)
        rgb = (rgb[:, 0]<<16)|(rgb[:, 1]<<8)|rgb[:, 2]
        packed = np.empty(len(xyz), dtype=[('x','<f4'), ('y','<f4'), ('z','<f4'), ('rgb','<u4')])
        for i,k in enumerate(('x','y','z')):
            packed[k] = xyz[:, i]
        packed['rgb'] = rgb
        msg = PointCloud2(); msg.header = Header(frame_id='map'); msg.height = 1; msg.width = len(xyz)
        msg.fields = [PointField(name=k, offset=4*i, datatype=PointField.FLOAT32 if i<3 else PointField.UINT32, count=1)
                      for i,k in enumerate(('x','y','z','rgb'))]
        msg.point_step = 16; msg.row_step = 16*len(xyz); msg.is_dense = True; msg.data = packed.tobytes()
        clouds[n].publish(msg)

    def advance(t, do_detail):
        for n,s in state.items():
            changed = False
            while s['idx'] < len(s['events']) and s['events'][s['idx']][0] <= t:
                et, kind, v = s['events'][s['idx']]; s['idx'] += 1
                if kind == 'pose':
                    s['pose'] = v
                    if not s['trail'] or np.linalg.norm(np.array(v[:2])-np.array(s['trail'][-1][:2])) > .08:
                        s['trail'].append(v)
                elif kind == 'scan':
                    # Common15m display radius; filtering relative to current
                    # received sensor pose is visualization only.
                    v = v[np.linalg.norm(v-np.array(s['pose'][:3]), axis=1) <= 15.]
                    cells = np.floor(v/.18).astype(np.int32)
                    s['surface'].update(zip(map(tuple, cells), v))
                    changed = True
                else:
                    s[kind] = v
            if mode == 'comparison':
                if changed:
                    publish_cloud(n, s)
                pubs[n]['global'].publish(MarkerArray(markers=routes(s)))
            elif n == 'ht' and do_detail:
                # Delete old path segments if a new path has become empty.
                clear = Marker(); clear.action = Marker.DELETEALL
                pubs[n]['local'].publish(MarkerArray(markers=[clear]+ht_markers(s)+routes(s, local=True)))
                pubs[n]['theta'].publish(MarkerArray(markers=[clear]+ht_markers(s, theta=True)+routes(s, local=True, theta=True)))
        rclpy.spin_once(node, timeout_sec=0)

    def hud(im, t):
        d = ImageDraw.Draw(im)
        d.rectangle((0, 0, 1920, 67), fill='#0b121b')
        d.rectangle((0, 868, 1920, 1080), fill='#0b121b')
        title = '原版 TARE    |    当前 HT + TARE：全程探索对比' if mode == 'comparison' else 'HT 局部规划细节    |    八方向 XYθ 可通过性空间'
        d.text((22, 9), title, font=large, fill='white')
        d.text((1275, 13), f'真实 RViz 录包回放 ×{speed:g}   实验 {t:06.1f} / 600 s', font=font, fill='#8ad9ff')
        names = [('original', '原版 TARE'), ('ht', '当前 HT + TARE')] if mode == 'comparison' else [('ht', '局部 XY：当前最近的 45° 方向层'), ('ht', 'XYθ：0°～315°，间隔 45°')]
        for col,(n,label) in enumerate(names):
            x = col*960+22; st = stats[n]; j = max(0, bisect.bisect_right(st['t'], t)-1); row = st['rows'][j]
            vi = max(0, bisect.bisect_right(st['vt'], t)-1); vol = st['v'][vi]
            d.text((x, 875), label, font=font, fill='white')
            d.text((x, 911), f"里程 {float(row['distance_m']):.1f} m    累计观测自由体积 ≈ {float(vol['observed_free_volume_m3']):.0f} m³", font=small, fill='#d2dfec')
            if mode == 'comparison':
                d.text((x, 943), '青线：实际轨迹    黄线：TARE 局部访问路线    黄球：当前航点', font=small, fill='#d2dfec')
                d.text((x, 975), '浅灰：累计激光返回点    '+('淡紫：TARE 全局路线' if n=='original' else '绿线：HT 实际下发路径    粉球：HT 路段目标'), font=small, fill='#d2dfec')
            else:
                h = state['ht'].get('ht'); age = h['source_age_s'] if h else float('nan')
                layer = int(np.floor((state['ht']['pose'][3]%(2*np.pi))/(np.pi/4)+.5))%8
                detail = f'当前显示方向 {layer*45}°    图在发布时龄 {age:.2f} s' if col==0 else '竖轴是车头角度 θ；层间距仅用于显示，不是地形高度'
                d.text((x, 943), detail, font=small, fill='#d2dfec')
                d.text((x, 975), '绿：高可通过性  红：低  灰：无效（右侧无效格透明）', font=small, fill='#d2dfec')
        d.text((22, 1021), '黄：TARE 路线｜绿：HT 下发路径｜青：实际轨迹。仅回放，不重新规划；网格显示抽稀，未记录的搜索树无法恢复。' if mode!='comparison' else
               '两轮各 600 秒、同尺度俯视图（网格 10 m）；点云为观测表面，数值为统一射线指标。回放不能证明实时性或无故障。', font=small, fill='#94a9bd')
        d.rectangle((0, 1070, int(1920*t/600), 1079), fill='#3ebae5')
        return im

    dest = out/('rviz_'+mode+'_4x.mp4')
    enc = subprocess.Popen([str(encoder), '-y', '-loglevel', 'warning', '-f', 'rawvideo', '-pix_fmt', 'rgb24',
                            '-s', '1920x1080', '-r', str(fps), '-i', '-', '-an', '-c:v', 'libx264',
                            '-threads', '3', '-preset', 'veryfast', '-crf', '23', '-pix_fmt', 'yuv420p',
                            '-movflags', '+faststart', str(dest)], stdin=subprocess.PIPE,
                           stderr=(out/(mode+'_encoder.log')).open('w'))
    capture_log = []; frames = int(limit/speed*fps)+1; deadline = time.monotonic(); last_detail = -1
    try:
        for frame in range(frames):
            t = min(limit, frame/fps*speed)
            detail = int(t*2) != last_detail
            advance(t, detail)
            last_detail = int(t*2)
            # Let RViz draw received DDS messages before taking this frame.
            wait = deadline+1/fps-time.monotonic()
            if wait>0:
                time.sleep(wait)
            im = ImageGrab.grab(xdisplay=display).convert('RGB')
            im = hud(im, t)
            enc.stdin.write(im.tobytes())
            capture_log.append({'frame': frame, 'experiment_t_s': t, 'capture_wall': time.time()})
            if frame in (min(frames-1, int(30/speed*fps)), min(frames-1, int(180/speed*fps)), frames-1):
                im.save(out/(mode+f'_t{int(t):03}.jpg'), quality=92)
            deadline = max(deadline+1/fps, time.monotonic()-.05)
            if frame%int(fps*10)==0:
                print(mode, f't={t:.1f}', f'frame={frame}/{frames}', flush=True)
    finally:
        enc.stdin.close(); enc.wait()
        for proc in processes:
            proc.send_signal(signal.SIGINT)
        for proc in processes:
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill(); proc.wait()
        node.destroy_node(); rclpy.shutdown()
    if enc.returncode:
        raise RuntimeError('Video encoder failed')
    (out/(mode+'_capture.json')).write_text(json.dumps({'mode': mode, 'frames': frames, 'fps': fps,
        'source_duration_s': limit, 'video_duration_s': frames/fps, 'speed': speed, 'display': display,
        'capture': 'PIL ImageGrab of actual RViz2 windows on isolated Xvfb plus labelled HUD',
        'first_frame': capture_log[0], 'last_frame': capture_log[-1], 'video_sha256': sha(dest),
        'publishers': publisher_names,
        'source_metadata': data['sources'], 'video_bytes': dest.stat().st_size}, indent=2)+'\n')


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--suite', type=Path)
    ap.add_argument('--cache', type=Path, required=True)
    ap.add_argument('--output', type=Path)
    ap.add_argument('--prepare', action='store_true')
    ap.add_argument('--mode', choices=['comparison', 'detail'])
    ap.add_argument('--encoder', type=Path)
    ap.add_argument('--display', default=':98')
    ap.add_argument('--speed', type=float, default=4)
    ap.add_argument('--fps', type=int, default=10)
    ap.add_argument('--limit', type=float, default=600)
    a = ap.parse_args()
    if a.prepare:
        prepare(a.suite.resolve(), a.cache.resolve())
    else:
        a.output.mkdir(parents=True, exist_ok=True); configs(a.output)
        replay(a.cache, a.output.resolve(), a.encoder, a.mode, a.display, a.speed, a.fps, a.limit)


if __name__ == '__main__':
    main()
