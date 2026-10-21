"""Render explanatory figures and printable reports; never launches ROS nodes."""
from pathlib import Path
import argparse
import html
import math
import markdown
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'docs/planning/figures'
plt.rcParams.update({'font.family': 'Noto Sans CJK JP', 'axes.unicode_minus': False,
                     'font.size': 11, 'savefig.facecolor': 'white'})


def explanatory_figures():
    OUT.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(12, 5.1))
    ax.set(xlim=(0, 12), ylim=(0, 5)); ax.axis('off')
    boxes = [
        (0.2, 3.25, '点云＋定位', '#e6eef9'),
        (2.6, 3.25, 'CuPy高程\n历史融合与局部裁剪', '#e6eef9'),
        (5.1, 3.25, 'HT八方向场\nT(x,y,θk)', '#dcf1e6'),
        (7.55, 3.25, 'XYθ局部路由\n运动学原语＋硬检查', '#dcf1e6'),
        (9.95, 3.25, '跟踪器\n限幅＋候选命令复检', '#fff0d6'),
        (2.6, 0.75, 'TARE覆盖估计\n全局/局部TSP', '#e6eef9'),
        (5.1, 0.75, 'TARE原生waypoint\n同分支局部目标', '#e6eef9'),
        (9.95, 0.75, '速度命令→仿真\n新观测反馈', '#fff0d6'),
    ]
    for x, y, label, color in boxes:
        ax.add_patch(FancyBboxPatch((x, y), 1.8, 1.05, boxstyle='round,pad=0.1',
                                   facecolor=color, edgecolor='#526c85'))
        ax.text(x+.9, y+.525, label, ha='center', va='center', fontsize=10)
    links = [((2, 3.78), (2.5, 3.78)), ((4.4, 3.78), (5, 3.78)),
             ((6.9, 3.78), (7.45, 3.78)), ((9.35, 3.78), (9.85, 3.78)),
             ((4.4, 1.28), (5, 1.28)), ((6.9, 1.28), (8.45, 3.15)),
             ((6, 3.15), (4.2, 1.9)), ((1.1, 3.15), (2.8, 1.9)),
             ((10.85, 3.15), (10.85, 1.9))]
    for a, b in links:
        ax.add_patch(FancyArrowPatch(a, b, arrowstyle='-|>', mutation_scale=15, color='#526c85'))
    ax.text(6, 4.72, '当前执行模式：tare_waypoint', ha='center', fontsize=16, weight='bold')
    ax.text(6, .13, '结构示意：图中方框不是额外的ROS节点；全局访问顺序与局部可执行连接分开计算。',
            ha='center', fontsize=10, color='#586579')
    fig.savefig(OUT/'architecture.png', dpi=160, bbox_inches='tight'); plt.close(fig)

    fig = plt.figure(figsize=(12, 5.1), layout='constrained')
    ax = fig.add_subplot(121)
    for sign, speed, style in [(1, .5, '-'), (-1, .25, '--')]:
        duration = .4/speed
        for angle in [0, math.pi/16, -math.pi/16, math.pi/8, -math.pi/8]:
            omega = angle/duration; times = np.linspace(0, duration, 60)
            v = sign*speed
            x = v*times if abs(omega)<1e-12 else v/omega*np.sin(omega*times)
            y = np.zeros_like(times) if abs(omega)<1e-12 else v/omega*(1-np.cos(omega*times))
            color = '#246cbe' if sign>0 else '#dd7b22'
            ax.plot(x, y, style, color=color)
            ax.arrow(x[-1], y[-1], .035*math.cos(angle), .035*math.sin(angle),
                     width=.001, head_width=.014, length_includes_head=True, color=color)
    ax.plot(0, 0, 'ko', ms=5)
    ax.set(aspect='equal', xlabel='相对X / m', ylabel='相对Y / m',
           title='0.4m平移原语：蓝色前进、橙色倒车\n另允许v=0的原地旋转')
    ax.set_ylim(-.14, .14); ax.grid(alpha=.2)
    ax = fig.add_subplot(122, projection='polar')
    for k in range(32):
        angle = k*math.pi/16
        ax.plot([angle, angle], [.8, 1.], color='#687689', lw=1)
    for k in range(8):
        angle = k*math.pi/4
        ax.plot([angle, angle], [0, .76], color='#25865e', lw=2)
    ax.set_ylim(0, 1); ax.set_yticks([])
    ax.set_xticks(np.arange(8)*math.pi/4, [f'{k*45}°' for k in range(8)])
    ax.set_title('内侧8条绿线：HT预测方向\n外圈32刻度：搜索航向键', pad=22)
    fig.suptitle('由当前运动原语公式绘制的示意，不是实测路线', fontsize=15)
    fig.savefig(OUT/'motion_principles.png', dpi=160, bbox_inches='tight'); plt.close(fig)


def render(path):
    from weasyprint import HTML
    body = markdown.markdown(path.read_text(), extensions=['tables', 'fenced_code'])
    title = html.escape(path.stem)
    css = '''
    @page { size:A4; margin:16mm 15mm; @bottom-center { content: counter(page); color:#637184; font-size:9pt; } }
    body { font-family:"Noto Sans CJK SC","Noto Sans CJK JP",sans-serif; font-size:10pt; line-height:1.65; color:#243447; }
    h1 { font-size:22pt; line-height:1.35; color:#173e60; }
    h2 { font-size:14pt; margin-top:1.3em; color:#173e60; break-after:avoid; }
    p { text-align:justify; }
    img { width:100%; object-fit:contain; }
    table { width:100%; border-collapse:collapse; font-size:8.8pt; }
    td,th { border:1px solid #cbd5df; padding:5px 7px; vertical-align:top; }
    th { background:#e9f0f6; } tr { break-inside:avoid; }
    pre { white-space:pre-wrap; background:#f1f5f8; padding:9px; font-size:8.5pt; }
    code { overflow-wrap:anywhere; } a { color:#1466a3; text-decoration:none; }
    '''
    document = f'<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>{title}</title><style>{css}</style><body>{body}</body></html>'
    path.with_suffix('.html').write_text(document)
    HTML(string=document, base_url=str(path.parent)).write_pdf(path.with_suffix('.pdf'))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--report', type=Path, action='append')
    args = parser.parse_args()
    explanatory_figures()
    for path in args.report or [ROOT/'docs/planning/2026-10-22_planning_principles.md']:
        render(path)
