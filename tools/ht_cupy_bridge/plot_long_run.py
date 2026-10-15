#!/usr/bin/env python3
"""Plot map freshness, motion and CMU path-stop correlation from probes."""

import argparse
import csv
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


def read_csv(path):
    return list(csv.DictReader(path.open()))


def column(rows, name):
    return np.asarray([float(row[name]) if row[name] else np.nan for row in rows])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", type=Path, required=True)
    args = parser.parse_args()
    rows = read_csv(args.run / "timing.csv")
    t = column(rows, "t_s")
    fig, axes = plt.subplots(3, 1, figsize=(14, 10), sharex=True,
                             gridspec_kw={"height_ratios": [1, 1.25, 1]})
    axes[0].plot(t / 60, column(rows, "ht_map_age_s"), color="#125da0", lw=.8,
                 label="HT map message age at independent subscriber")
    axes[0].axhline(3, color="#c63535", ls="--", label="TARE freshness limit: 3 s")
    axes[0].set(ylabel="Map age (s)", ylim=(0, 3.4))
    axes[0].legend(loc="upper right")
    axes[1].plot(t / 60, column(rows, "odom_speed_mps"), color="#086b91", lw=.9,
                 label="measured ground speed")
    axes[1].plot(t / 60, np.abs(column(rows, "cmd_speed_mps")), color="#df7d16", lw=.7,
                 alpha=.7, label="absolute commanded speed")
    axes[1].plot(t / 60, column(rows, "tare_speed_mps"), color="#7764a6", lw=.7,
                 alpha=.5, label="TARE speed request")
    axes[1].set(ylabel="Speed (m/s)", ylim=(-.03, .65))
    axes[1].legend(loc="upper right", ncol=3)
    axes[2].plot(t / 60, column(rows, "distance_m"), color="#157d54", lw=1.6)
    axes[2].set(xlabel="Minutes since healthy HT exploration", ylabel="Distance traveled (m)")
    for ax in axes:
        ax.grid(alpha=.2)
    fig.suptitle("Campus long run: HT map delivery and stop-go motion")
    fig.tight_layout()
    fig.savefig(args.run / "long_run_timing.png", dpi=170)
    plt.close(fig)

    stutter_file = args.run / "path_stutter.csv"
    if stutter_file.exists():
        probe = read_csv(stutter_file)
        pt = column(probe, "t_s") / 60
        length = column(probe, "path_length")
        cmd = np.abs(column(probe, "cmd_speed_mps"))
        fig, axes = plt.subplots(2, 1, figsize=(13, 7), sharex=True)
        axes[0].plot(pt, length, color="#3263a8", lw=.7)
        axes[0].set(ylabel="CMU /path pose count")
        axes[1].plot(pt, cmd, color="#db7c17", lw=.8)
        axes[1].set(xlabel="Minutes since path probe start", ylabel="|cmd_vel linear.x| (m/s)")
        for ax in axes:
            ax.grid(alpha=.2)
        fig.suptitle("Shorter local paths coincide with stop-go commands")
        fig.tight_layout()
        fig.savefig(args.run / "path_stop_correlation.png", dpi=170)
        plt.close(fig)


if __name__ == "__main__":
    main()
