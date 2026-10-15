#!/usr/bin/env python3
"""Stack the eight HT P(x,y,theta) layers into one XY-theta space."""

import argparse
import json
from pathlib import Path
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import colors
import numpy as np


def load_layers(path, stride):
    with np.load(path) as data:
        probabilities = data["probabilities"]
        valid = data["valid"].astype(bool)
        center = data["center"]
        resolution = float(data["resolution"])
    if probabilities.shape[0] != 8 or probabilities.shape[1:] != valid.shape:
        raise ValueError("Expected eight HT layers on one XY grid")
    n, m = valid.shape
    x = center[0] + (n / 2 - np.arange(n) - .5) * resolution
    y = center[1] + (m / 2 - np.arange(m) - .5) * resolution
    # The first GridMap indices correspond to the largest world X/Y positions.
    x, y = x[::-1][::stride], y[::-1][::stride]
    valid = np.flipud(np.fliplr(valid.T))[::stride, ::stride]
    p = np.stack([np.flipud(np.fliplr(layer.T))[::stride, ::stride]
                  for layer in probabilities])
    p = np.where(valid[None, :, :], p, np.nan)
    return x, y, p, resolution, valid


def save_html(x, y, p, output):
    # Kept local to this command so users can still make the PNG without Plotly.
    sys.path.insert(0, str(Path(__file__).with_name(".plotly_vendor")))
    import plotly.graph_objects as go

    xx, yy = np.meshgrid(x, y)
    fig = go.Figure()
    for k in range(8):
        plane = p[k]
        fig.add_trace(go.Surface(
            x=xx, y=yy, z=np.full_like(xx, 45.0 * k), surfacecolor=plane,
            customdata=plane, cmin=0, cmax=1, colorscale="RdYlGn",
            opacity=.68, connectgaps=False, name=f"θ={45*k}°",
            showscale=k == 0,
            colorbar=dict(title="HT P(pass)", len=.75) if k == 0 else None,
            hovertemplate="x=%{x:.2f} m<br>y=%{y:.2f} m<br>θ=%{z:.0f}°"
                          "<br>HT P(pass)=%{customdata:.3f}<extra></extra>"))
    buttons = [dict(label="All eight θ slices", method="update",
                    args=[{"visible": [True] * 8}])]
    for k in range(8):
        buttons.append(dict(label=f"Only θ={45*k}°", method="update",
                            args=[{"visible": [j == k for j in range(8)]}]))
    fig.update_layout(
        title="HT P(x,y,θ): eight directional maps in one XYθ space",
        scene=dict(xaxis_title="X (m)", yaxis_title="Y (m)",
                   zaxis=dict(title="Travel direction θ (degrees)",
                              tickvals=list(range(0, 360, 45)), range=[-12, 327]),
                   aspectmode="manual", aspectratio=dict(x=1, y=1, z=1.5),
                   camera=dict(eye=dict(x=1.65, y=-1.8, z=1.1))),
        updatemenus=[dict(buttons=buttons, x=.01, y=.98, xanchor="left", yanchor="top")],
        annotations=[dict(text="Each horizontal slice is the SAME XY terrain at one of HT's eight travel directions. "
                               "Color is probability; missing cells are transparent. Drag to rotate; use the menu to isolate a slice.",
                          x=.5, y=-.05, xref="paper", yref="paper", showarrow=False)],
        margin=dict(l=0, r=0, t=55, b=70), width=1200, height=850)
    fig.write_html(output, include_plotlyjs=True, full_html=True)


def save_png(x, y, p, output):
    xx, yy = np.meshgrid(x, y)
    norm = colors.Normalize(vmin=0, vmax=1)
    cmap = plt.get_cmap("RdYlGn")
    fig = plt.figure(figsize=(16, 8), dpi=160)
    for index, azim in enumerate([-65, 110]):
        ax = fig.add_subplot(1, 2, index + 1, projection="3d")
        for k in range(8):
            layer = p[k]
            color = cmap(norm(np.nan_to_num(layer, nan=0)))
            color[..., 3] = np.where(np.isfinite(layer), .58, 0)
            ax.plot_surface(xx, yy, np.full_like(xx, k * 45),
                            facecolors=color, shade=False, rstride=1, cstride=1,
                            linewidth=0, antialiased=False)
        ax.set(xlabel="X (m)", ylabel="Y (m)", zlabel="θ (degrees)",
               zlim=(-10, 325), zticks=np.arange(0, 360, 45),
               title="All 8 HT slices, viewed from " + ("front" if index == 0 else "back"))
        ax.view_init(elev=20, azim=azim)
        ax.set_box_aspect((1, 1, 1.5))
    fig.colorbar(plt.cm.ScalarMappable(norm=norm, cmap=cmap), ax=fig.axes,
                 shrink=.65, pad=.03, label="HT predicted traversability probability")
    fig.suptitle("HT directional traversability field P(x, y, θ)\n"
                 "Same XY grid repeated at θ = 0°, 45°, ..., 315°; transparent = unsupported",
                 fontsize=15)
    fig.savefig(output, bbox_inches="tight")
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True, help="NPZ from ht_direction_terrain.py")
    parser.add_argument("--output", type=Path, required=True, help="HTML output")
    parser.add_argument("--stride", type=int, default=2, help="Display sampling only; original NPZ is untouched")
    args = parser.parse_args()
    if args.stride < 1:
        parser.error("--stride must be at least 1")
    x, y, p, resolution, valid = load_layers(args.input, args.stride)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    save_html(x, y, p, args.output)
    save_png(x, y, p, args.output.with_suffix(".png"))
    meta = {"xy_shape_displayed": list(p.shape[1:]), "theta_layers_deg": list(range(0, 360, 45)),
            "stride": args.stride, "source_resolution_m": resolution,
            "display_resolution_m": resolution * args.stride,
            "valid_xy_cells_displayed": int(valid.sum()),
            "probability_min_max": [float(np.nanmin(p)), float(np.nanmax(p))]}
    args.output.with_suffix(".json").write_text(json.dumps(meta, indent=2) + "\n")
    print(json.dumps(meta))


if __name__ == "__main__":
    main()
