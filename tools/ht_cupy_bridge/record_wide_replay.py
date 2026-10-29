#!/usr/bin/env python3
"""Record real RViz: 4K four views plus a 1080p full-screen wide environment.

Only visualization MarkerArrays are published in a dedicated ROS domain and
private Xephyr screen. Saved output fields and recorded poses are not changed.
"""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import time

import imageio_ffmpeg
import mss
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, DurabilityPolicy, ReliabilityPolicy
from visualization_msgs.msg import Marker, MarkerArray
import yaml

from record_newbags_rviz import views, cells, color, marker, point, configuration


def context_views(z, trajectory, scene):
    output = views(z, trajectory)
    s = scene['scene_xyz']
    # Muted context is visually distinct from the colored elevation cells.
    colors = np.tile([.65, .71, .77, .55], (len(s), 1))
    output[0].markers.insert(0, cells(20, s, colors, [.14, .14, .14], 'global', typ=Marker.POINTS))
    # Robot outline/trajectory lie just above terrain instead of floating 2 m up.
    for m in output[0].markers:
        if m.id in (2, 3):
            for p in m.points:
                p.z -= 1.75
        if m.id == 4:
            for p in m.points:
                p.z -= 1.45
    center = z['local_center']
    robot_z = z['robot'][2]
    for mid, half, rgba in [(21, 5.82, [.9, .94, 1., 1.]), (22, 4.82, [1., .82, .16, 1.])]:
        m = marker(mid, Marker.LINE_STRIP, 'global')
        m.scale.x = .045
        m.color = color(rgba)
        m.points = [point([center[0] + x, center[1] + y, robot_z + .18])
                    for x, y in [(-half, -half), (half, -half), (half, half), (-half, half), (-half, -half)]]
        output[0].markers.append(m)
    return output


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input', type=Path, required=True)
    p.add_argument('--scene', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--label', required=True)
    p.add_argument('--display', default=':97')
    a = p.parse_args()
    a.output.mkdir(parents=True, exist_ok=False)
    assert not Path('/tmp/.X' + a.display[1:] + '-lock').exists(), 'Private display already in use'
    assert os.environ.get('ROS_DOMAIN_ID') == '192', 'Use this recorder in private ROS domain 192'
    result = json.loads((a.input / 'RESULTS.json').read_text())
    rows = [r for r in result['frames'] if r['output']]
    with np.load(a.scene / rows[-1]['file']) as last_scene:
        bounds = last_scene['scene_xyz']
        lo, hi = bounds.min(0), bounds.max(0)
    center = (lo + hi) / 2
    center[2] = -.25
    # Stable wide view. Use the known terrain footprint for fitting, so isolated
    # distant context points do not shrink the useful environment to a tiny dot.
    with np.load(a.input / 'frames' / rows[-1]['file']) as final:
        map_bounds = final['global_xyz'][:, :2]
        center[:2] = (map_bounds.min(0) + map_bounds.max(0)) / 2
        distance = max(28., float(np.linalg.norm(np.ptp(map_bounds, axis=0)) * .5 / math.sin(math.pi / 8) * 1.18))
    env = os.environ.copy()
    env.update(QT_X11_NO_MITSHM='1', LIBGL_ALWAYS_SOFTWARE='1')
    logs, processes, encoders = [], [], []
    server = None
    node = None
    font_path = '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc'
    title_font = ImageFont.truetype(font_path, 34)
    font = ImageFont.truetype(font_path, 25)
    titles = ['周围环境 + 全局历史高程图｜固定大视野', '局部高程图｜完整 11.64 × 11.64 m',
              'HT 八方向可通过性｜0°～315°', 'HT XYθ 空间｜半透明连续体素']
    notes = ['灰色：周围实测点云｜彩色：高程｜白框：局部地图｜黄框：HT范围',
             '0.04 m 高程网格｜空白：未知｜青色：录包位置和朝向',
             '红 0 → 黄 0.5 → 绿 1｜灰：无效｜显示格 0.08 m',
             '竖轴是方向，不是高度｜体素 0.16 m × 0.16 m × 45°｜α=0.055']
    capture_manifest = []
    try:
        server_log = (a.output / 'xephyr.log').open('w')
        logs.append(server_log)
        server = subprocess.Popen(['/usr/bin/Xephyr', a.display, '-screen', '3840x2160', '-ac', '-br', '-noreset', '-nolisten', 'tcp', '-title', 'HT wide offline RViz'], env=env, stdout=server_log, stderr=subprocess.STDOUT)
        for _ in range(80):
            if server.poll() is not None:
                raise RuntimeError('Private Xephyr exited')
            if Path('/tmp/.X11-unix/X' + a.display[1:]).exists():
                break
            time.sleep(.1)
        else:
            raise RuntimeError('Private display startup timeout')
        env['DISPLAY'] = a.display
        rclpy.init()
        node = Node('offline_wide_rviz_only')
        qos = QoSProfile(depth=1, reliability=ReliabilityPolicy.RELIABLE, durability=DurabilityPolicy.TRANSIENT_LOCAL)
        frames = ['global', 'local', 'directions', 'voxel']
        topics = ['/offline_wide/' + f for f in frames]
        pubs = [node.create_publisher(MarkerArray, t, qos) for t in topics]
        cameras = []
        for i, (topic, frame) in enumerate(zip(topics, frames)):
            config = a.output / f'view_{i}.rviz'
            configuration(config, topic, frame, i, center, distance)
            cfg = yaml.safe_load(config.read_text())
            cfg['Window Geometry'].update(Width=1920, Height=1080, X=i % 2 * 1920, Y=i // 2 * 1080)
            camera = cfg['Visualization Manager']['Views']['Current']
            if i == 0:
                camera.update(Pitch=.9, Yaw=4.71)
            if i == 1:
                camera.update(Distance=17., Pitch=1.35)
            if i == 3:
                camera.update(Distance=18.5)
            cameras.append(camera)
            config.write_text(yaml.safe_dump(cfg, sort_keys=False))
            log = (a.output / f'rviz_{i}.log').open('w')
            logs.append(log)
            processes.append(subprocess.Popen(['/opt/ros/jazzy/bin/rviz2', '-d', str(config), '-geometry', f'1920x1080+{i%2*1920}+{i//2*1080}'], env=env, stdout=log, stderr=subprocess.STDOUT))
        for _ in range(200):
            if any(c.poll() is not None for c in processes):
                raise RuntimeError('RViz exited; inspect logs')
            if all(p.get_subscription_count() for p in pubs):
                break
            time.sleep(.1)
        else:
            raise RuntimeError('RViz subscriber timeout')
        first = np.load(a.input / 'frames' / rows[0]['file'])
        with np.load(a.scene / rows[0]['file']) as scene:
            for pub, msg in zip(pubs, context_views(first, [first['robot']], scene)):
                pub.publish(msg)
        first.close()
        time.sleep(4.)
        ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
        paths = [a.output / (a.label + '_4K_four_views.mp4'), a.output / (a.label + '_wide_environment.mp4')]
        for path, size in zip(paths, ['3840x2160', '1920x1080']):
            log = (a.output / (path.stem + '_encode.log')).open('w')
            logs.append(log)
            encoders.append(subprocess.Popen([ffmpeg, '-hide_banner', '-loglevel', 'error', '-n', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', size, '-r', '10', '-i', '-', '-an', '-c:v', 'libx264', '-threads', '4', '-preset', 'fast', '-crf', '19', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', str(path)], stdin=subprocess.PIPE, stderr=log))
        end = (result['scans'][-1]['stamp_ns'] - result['scans'][0]['stamp_ns']) / 1e9
        offset = (rows[0]['stamp_ns'] - result['scans'][0]['stamp_ns']) / 1e9
        index, last = 0, -1
        trajectory = []
        with mss.MSS(display=a.display) as screen:
            begun = time.monotonic()
            for f in range(math.ceil(end * 10) + 1):
                t = f / 10
                while index + 1 < len(rows) and rows[index + 1]['t_s'] + offset <= t:
                    index += 1
                if last != index:
                    with np.load(a.input / 'frames' / rows[index]['file']) as z, np.load(a.scene / rows[index]['file']) as scene:
                        trajectory.append(z['robot'].copy())
                        for pub, msg in zip(pubs, context_views(z, trajectory, scene)):
                            pub.publish(msg)
                    time.sleep(.35)
                    last = index
                wait = begun + t - time.monotonic()
                if wait > 0:
                    time.sleep(wait)
                if any(c.poll() is not None for c in processes):
                    raise RuntimeError('RViz exited during capture')
                im = Image.frombytes('RGB', (3840, 2160), screen.grab({'left': 0, 'top': 0, 'width': 3840, 'height': 2160}).rgb)
                draw = ImageDraw.Draw(im)
                for k, title in enumerate(titles):
                    x, y = k % 2 * 1920, k // 2 * 1080
                    draw.rectangle((x, y, x + 1920, y + 100), fill=(16, 24, 29))
                    draw.text((x + 24, y + 8), title, fill=(235, 245, 250), font=title_font)
                    draw.text((x + 24, y + 57), f'{a.label}｜原始点云 t={t:05.1f}s｜离线重算 / 实际 RViz｜青线是录包轨迹', fill=(168, 195, 212), font=font)
                    draw.rectangle((x, y + 1035, x + 1920, y + 1080), fill=(16, 24, 29))
                    draw.text((x + 20, y + 1041), notes[k], fill=(205, 220, 230), font=font)
                if f in {0, int(end * 5), int(end * 10)}:
                    im.save(a.output / f'preview_{f:04d}.png')
                encoders[0].stdin.write(im.tobytes())
                encoders[1].stdin.write(im.crop((0, 0, 1920, 1080)).tobytes())
                capture_manifest.append({'video_frame': f, 'source_t_s': t, 'result_frame': rows[index]['file'], 'stamp_ns': rows[index]['stamp_ns']})
        for e in encoders:
            e.stdin.close()
        assert all(e.wait() == 0 for e in encoders)
        encoders = []
        for path in paths:
            subprocess.run([ffmpeg, '-v', 'error', '-i', str(path), '-f', 'null', '-'], check=True)
        manifest = {'actual_rviz': True, 'fresh_reconstruction': str(a.input), 'scene': str(a.scene),
                    'outputs': [{'file': p.name, 'bytes': p.stat().st_size, 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()} for p in paths],
                    'fps': 10, 'source_duration_s': end, 'frames': len(capture_manifest), 'full_decode_passed': True,
                    'camera_views': cameras, 'capture_manifest': capture_manifest,
                    'limits': 'Recorded real inputs only; no control or live robot. Accumulated context is display-only; no inference map changes.'}
        (a.output / 'VIDEO_CHECK.json').write_text(json.dumps(manifest, indent=2) + '\n')
        print(json.dumps({'videos': [str(p) for p in paths], 'frames': len(capture_manifest)}, ensure_ascii=False), flush=True)
    finally:
        for e in encoders:
            e.kill()
            e.wait()
        for c in processes:
            c.terminate()
        for c in processes:
            try:
                c.wait(timeout=10)
            except subprocess.TimeoutExpired:
                c.kill()
                c.wait()
        if node is not None:
            node.destroy_node()
            rclpy.try_shutdown()
        if server is not None:
            server.terminate()
            try:
                server.wait(timeout=10)
            except subprocess.TimeoutExpired:
                server.kill()
                server.wait()
        for log in logs:
            log.close()


if __name__ == '__main__':
    main()
