#!/usr/bin/env python3
"""A real (x,y,body-yaw) grid A* over one eight-direction HT map.

This is an offline local-planning prototype. It does not command the vehicle.
HT direction channels describe travel direction: reverse motion queries the
channel opposite to the body yaw. In-place rotation uses a geometric validity
check because HT does not predict rotational traversability.
"""

import argparse
import heapq
import json
import math
from pathlib import Path
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy.ndimage import binary_erosion, percentile_filter, uniform_filter


STEP = ((1, 0), (1, 1), (0, 1), (-1, 1),
        (-1, 0), (-1, -1), (0, -1), (1, -1))


def grid_from_ht(path, stride):
    with np.load(path) as data:
        p = data["probabilities"].astype(np.float32)
        valid = data["valid"].astype(bool)
        center = data["center"]
        native_resolution = float(data["resolution"])
    return grid_from_arrays(p, valid, center, native_resolution, stride)


def grid_from_arrays(p, valid, center, native_resolution, stride):
    cx, cy = center
    n = valid.shape[0]
    # Use a low within-cell quantile so a thin bad strip is not averaged away.
    conservative = np.stack([
        percentile_filter(np.nan_to_num(p[k], nan=0.0), 25, size=stride,
                          mode="constant", cval=0)[stride // 2::stride, stride // 2::stride]
        for k in range(8)])
    support = uniform_filter(valid.astype(np.float32), size=stride,
                             mode="constant")[stride // 2::stride, stride // 2::stride] >= .8
    # Index 0 is the low-X/low-Y side in our planner.
    conservative = conservative[:, ::-1, ::-1]
    support = support[::-1, ::-1]
    # Body clearance: at least one grid-cell radius of supported terrain.
    safe = binary_erosion(support, structure=np.ones((3, 3)), border_value=0)
    nx, ny = safe.shape
    res = native_resolution * stride
    # Centers are transformed from GridMap row/column coordinates exactly.
    source_i = stride // 2 + np.arange(nx) * stride
    source_j = stride // 2 + np.arange(ny) * stride
    x = (cx + (n / 2 - source_i - .5) * native_resolution)[::-1]
    y = (cy + (n / 2 - source_j - .5) * native_resolution)[::-1]
    return x, y, conservative, safe, res


def nearest_index(values, target):
    return int(np.argmin(np.abs(values - target)))


def plan(x, y, p, safe, start, goal, p_min, risk_weight, turn_cost, reverse_factor):
    nx, ny = safe.shape
    si, sj, sk = start
    gi, gj, gk = goal
    if not safe[si, sj] or not safe[gi, gj]:
        raise ValueError("Start or goal lacks a supported body footprint")
    start_state = (si, sj, sk)
    goal_state = (gi, gj, gk)
    queue = [(math.hypot(x[gi] - x[si], y[gj] - y[sj]), 0.0, start_state)]
    dist = {start_state: 0.0}
    parent = {}
    action = {}
    expanded = 0
    reached = None
    while queue:
        _, g, state = heapq.heappop(queue)
        if g > dist.get(state, math.inf) + 1e-9:
            continue
        expanded += 1
        if state == goal_state or (gk is None and state[:2] == (gi, gj)):
            reached = state
            break
        i, j, k = state
        candidates = []
        # A skid/differential-drive chassis may pivot without translating.
        for delta, name in ((1, "rotate_ccw"), (-1, "rotate_cw")):
            candidates.append(((i, j, (k + delta) % 8), turn_cost, name))
        # Reverse preserves body yaw but queries the opposite HT travel layer.
        for sign, name in ((1, "forward"), (-1, "reverse")):
            travel_k = k if sign == 1 else (k + 4) % 8
            di, dj = STEP[travel_k]
            ii, jj = i + di, j + dj
            if ii < 0 or jj < 0 or ii >= nx or jj >= ny or not safe[ii, jj]:
                continue
            if di and dj and (not safe[i + di, j] or not safe[i, j + dj]):
                continue
            ps = min(float(p[travel_k, i, j]), float(p[travel_k, ii, jj]))
            if not math.isfinite(ps) or ps < p_min:
                continue
            length = math.hypot(x[ii] - x[i], y[jj] - y[j])
            move_cost = length * (1 + risk_weight * -math.log(max(ps, 1e-3)))
            if sign == -1:
                move_cost *= reverse_factor
            candidates.append(((ii, jj, k), move_cost, name))
        for next_state, cost, name in candidates:
            new_g = g + cost
            if new_g + 1e-9 < dist.get(next_state, math.inf):
                dist[next_state] = new_g
                parent[next_state] = state
                action[next_state] = name
                h = math.hypot(x[gi] - x[next_state[0]], y[gj] - y[next_state[1]])
                heapq.heappush(queue, (new_g + h, new_g, next_state))
    if reached is None:
        raise RuntimeError(f"No XYθ grid path after expanding {expanded} states")
    states = [reached]
    names = []
    while states[-1] != start_state:
        names.append(action[states[-1]])
        states.append(parent[states[-1]])
    states.reverse()
    names.reverse()
    return states, names, dist[reached], expanded


def save_visual(x, y, p, safe, states, names, output, p_min):
    sys.path.insert(0, str(Path(__file__).with_name(".plotly_vendor")))
    import plotly.graph_objects as go
    fig = go.Figure()
    nx, ny = safe.shape
    # A literal 3D lattice: every horizontal XY grid line is placed at all
    # eight discrete yaw states. The vehicle path runs through grid centers.
    gx, gy, gz = [], [], []
    for k in range(8):
        z = k * 45
        for xi in x:
            gx.extend([xi] * ny + [None])
            gy.extend(list(y) + [None])
            gz.extend([z] * ny + [None])
        for yj in y:
            gx.extend(list(x) + [None])
            gy.extend([yj] * nx + [None])
            gz.extend([z] * nx + [None])
    fig.add_trace(go.Scatter3d(x=gx, y=gy, z=gz, mode="lines",
                               line=dict(color="rgba(105,115,130,0.28)", width=1),
                               name="XYθ grid", hoverinfo="skip"))
    # Red cells are forbidden by poor direction-specific HT probability or
    # insufficient support. Other cells remain visible as grid intersections.
    blocked = ~safe[None, :, :] | (p < p_min)
    bi, bj, bk = np.where(blocked.transpose(1, 2, 0))
    fig.add_trace(go.Scatter3d(x=x[bi], y=y[bj], z=bk * 45,
                               mode="markers", marker=dict(size=3, color="#b42b2b", opacity=.4,
                                                           symbol="square"),
                               name="blocked (cell, yaw)",
                               hovertemplate="x=%{x:.2f}, y=%{y:.2f}, θ=%{z:.0f}°<br>blocked<extra></extra>"))
    sx = [x[i] for i, _, _ in states]
    sy = [y[j] for _, j, _ in states]
    sz = [k * 45 for _, _, k in states]
    hover = ["start"] + names
    # 315° and 0° are adjacent in the planner's periodic theta coordinate;
    # do not draw a misleading line through all intermediate yaw layers.
    path_x, path_y, path_z, path_hover = [], [], [], []
    for q, (xi, yi, zi, label) in enumerate(zip(sx, sy, sz, hover)):
        if q and abs(zi - sz[q - 1]) > 45:
            path_x.append(None); path_y.append(None); path_z.append(None); path_hover.append(None)
        path_x.append(xi); path_y.append(yi); path_z.append(zi); path_hover.append(label)
    fig.add_trace(go.Scatter3d(x=path_x, y=path_y, z=path_z, mode="lines+markers",
                               line=dict(color="#00dfff", width=10),
                               marker=dict(size=4, color="#0037a4"),
                               name="A* XYθ path", text=path_hover,
                               hovertemplate="x=%{x:.2f}, y=%{y:.2f}, θ=%{z:.0f}°"
                                             "<br>action=%{text}<extra></extra>"))
    fig.add_trace(go.Scatter3d(x=[sx[0], sx[-1]], y=[sy[0], sy[-1]],
                               z=[sz[0], sz[-1]], mode="markers+text",
                               text=["START", "GOAL"], textposition="top center",
                               marker=dict(size=10, color=["#00a13c", "#ffb000"]),
                               name="start / goal"))
    fig.update_layout(
        title="A* route through an explicit (x, y, body-yaw) HT grid",
        scene=dict(xaxis_title="X (m)", yaxis_title="Y (m)",
                   zaxis=dict(title="Body yaw θ (degrees)",
                              tickvals=list(range(0, 360, 45)), range=[-10, 325]),
                   aspectmode="manual", aspectratio=dict(x=1, y=1, z=1.4),
                   camera=dict(eye=dict(x=1.8, y=-1.7, z=1.3))),
        annotations=[dict(text="Each grid node is (x,y,body yaw); red nodes are blocked. "
                               "Horizontal cyan = forward/reverse; vertical cyan = pivot turn. "
                               "This is an offline prototype, not a command sent to the car.",
                          x=.5, y=-.05, xref="paper", yref="paper", showarrow=False)],
        width=1200, height=850, margin=dict(l=0, r=0, t=55, b=70))
    fig.write_html(output, include_plotlyjs=True)

    # A static view keeps the grid boundaries, direction-state changes, and
    # top-down route readable without a browser.
    static = output.with_suffix(".png")
    f = plt.figure(figsize=(14, 7), dpi=160)
    ax = f.add_subplot(121, projection="3d")
    for k in range(8):
        for xi in x:
            ax.plot([xi] * ny, y, [k * 45] * ny, color="#aab2bd", lw=.3, alpha=.18)
        for yj in y:
            ax.plot(x, [yj] * nx, [k * 45] * nx, color="#aab2bd", lw=.3, alpha=.18)
    ax.scatter(x[bi], y[bj], bk * 45, color="#bb3030", s=1, alpha=.22)
    for part in np.split(np.arange(len(states)),
                         [q for q in range(1, len(states)) if abs(sz[q] - sz[q - 1]) > 45]):
        ax.plot(np.asarray(sx)[part], np.asarray(sy)[part], np.asarray(sz)[part],
                "o-", color="#0073bf", lw=3, ms=2)
    ax.scatter([sx[0], sx[-1]], [sy[0], sy[-1]], [sz[0], sz[-1]],
               c=["#00a13c", "#ffb000"], s=80)
    ax.set(xlabel="X (m)", ylabel="Y (m)", zlabel="body yaw θ (deg)",
           zticks=np.arange(0, 360, 45), title="XYθ grid and A* path")
    ax.set_box_aspect((1, 1, 1.4))
    ax.view_init(elev=25, azim=-64)
    ax2 = f.add_subplot(122)
    ax2.pcolormesh(x, y, safe.T.astype(float), cmap="RdYlGn", vmin=0, vmax=1,
                   shading="nearest", edgecolors=(0, 0, 0, .25), linewidth=.25)
    ax2.plot(sx, sy, "o-", color="#0065af", ms=2, lw=2)
    ax2.scatter([sx[0], sx[-1]], [sy[0], sy[-1]],
                c=["#00a13c", "#ffb000"], s=80, zorder=5)
    ax2.set(xlabel="X (m)", ylabel="Y (m)",
            title="XY footprint support and route projection\n(direction-specific blocked states are shown at left)")
    ax2.set_aspect("equal")
    f.suptitle("Explicit grid search in (x, y, body yaw): pivot + forward + reverse")
    f.savefig(static, bbox_inches="tight")
    plt.close(f)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--stride", type=int, default=8)
    parser.add_argument("--start", type=float, nargs=3, default=(0, 0, 0), metavar=("X", "Y", "YAW_DEG"))
    parser.add_argument("--goal", type=float, nargs=3, default=(-3, 3, 90), metavar=("X", "Y", "YAW_DEG"))
    parser.add_argument("--p-min", type=float, default=.2)
    parser.add_argument("--risk-weight", type=float, default=1.0)
    parser.add_argument("--turn-cost", type=float, default=.22)
    parser.add_argument("--reverse-factor", type=float, default=1.2)
    args = parser.parse_args()
    x, y, p, safe, resolution = grid_from_ht(args.input, args.stride)
    state = lambda pose: (nearest_index(x, pose[0]), nearest_index(y, pose[1]),
                          round(pose[2] / 45) % 8)
    states, names, cost, expanded = plan(x, y, p, safe, state(args.start),
                                         state(args.goal), args.p_min, args.risk_weight,
                                         args.turn_cost, args.reverse_factor)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    save_visual(x, y, p, safe, states, names, args.output, args.p_min)
    actions = dict(forward=names.count("forward"), reverse=names.count("reverse"),
                   rotate_cw=names.count("rotate_cw"), rotate_ccw=names.count("rotate_ccw"))
    result = {"grid_shape_xytheta": [len(x), len(y), 8], "grid_resolution_m": resolution,
              "start": [float(x[states[0][0]]), float(y[states[0][1]]), states[0][2] * 45],
              "goal": [float(x[states[-1][0]]), float(y[states[-1][1]]), states[-1][2] * 45],
              "states": [[float(x[i]), float(y[j]), int(k * 45)] for i, j, k in states],
              "actions": names, "action_counts": actions, "cost": cost,
              "expanded_states": expanded, "p_min": args.p_min,
              "risk_weight": args.risk_weight, "turn_cost": args.turn_cost,
              "reverse_factor": args.reverse_factor,
              "note": "Offline grid planner only; it does not yet command TARE/CMU."}
    args.output.with_suffix(".json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({k: result[k] for k in ("grid_shape_xytheta", "start", "goal",
                                               "action_counts", "cost", "expanded_states")}))


if __name__ == "__main__":
    main()
