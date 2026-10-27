#!/usr/bin/env python3
"""Prepare CDR GridMaps and fixed offline XY-theta queries; never publishes ROS.

Only use trusted local replay inputs: their original source archive is a pickle.
The NPZ arrays already use GridMap row=-X, column=-Y coordinates.  They are
serialized column-major, exactly as CupyToHt publishes them; no image flip or
transpose is involved.  Missing NPZ orientation is recovered from the verified
original source CDR, rather than assumed from the visualized image.
"""
from __future__ import annotations

import argparse
from array import array
from copy import deepcopy
import hashlib
import json
import math
from pathlib import Path
import pickle

import numpy as np
from grid_map_msgs.msg import GridMap
from rclpy.serialization import deserialize_message, serialize_message
from std_msgs.msg import Float32MultiArray, MultiArrayDimension, MultiArrayLayout


LAYERS = [f"ht_dir_{k}" for k in range(8)] + [
    "ht_valid", "ht_observation_valid", "ht_obstacle", "ht_elevation"
]
SCOPE = (
    "Offline fixed XY-theta route queries on recorded HT fields; no TARE benefit "
    "selection, no new vehicle trajectory, no controller, no closed-loop experiment"
)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def stamp_ns(message: GridMap) -> int:
    return message.header.stamp.sec * 10**9 + message.header.stamp.nanosec


def map_yaw(message: GridMap) -> float:
    q = message.info.pose.orientation
    v = np.asarray([q.x, q.y, q.z, q.w], dtype=float)
    if not np.isfinite(v).all() or not math.isclose(float(v @ v), 1, abs_tol=1e-6):
        raise ValueError("Original source map has an invalid orientation")
    if abs(q.x) > 1e-6 or abs(q.y) > 1e-6:
        raise ValueError("Original source map is not planar")
    return math.atan2(2 * q.w * q.z, 1 - 2 * q.z * q.z)


def grid_message(layers, center, resolution, template=None, *, synthetic=False):
    shape = np.asarray(layers["ht_valid"]).shape
    if len(shape) != 2 or min(shape) <= 0 or not math.isfinite(resolution) or resolution <= 0:
        raise ValueError("Invalid map dimensions/resolution")
    rows, cols = shape
    if not np.isfinite(center).all() or np.asarray(center).shape != (2,):
        raise ValueError("Invalid map center")
    m = GridMap()
    if template is not None:
        m.header = deepcopy(template.header)
        m.info = deepcopy(template.info)
    elif synthetic:
        m.header.frame_id = "map"
        m.header.stamp.sec = 1
        m.info.pose.orientation.w = 1.0
    else:
        raise ValueError("A real map requires original header/orientation evidence")
    m.info.resolution = float(resolution)
    m.info.length_x = rows * resolution
    m.info.length_y = cols * resolution
    m.info.pose.position.x, m.info.pose.position.y = map(float, center)
    m.layers = LAYERS.copy()
    m.basic_layers = ["ht_valid"]
    m.outer_start_index = m.inner_start_index = 0
    for name in LAYERS:
        values = np.asarray(layers[name], dtype=np.float32)
        if values.shape != shape:
            raise ValueError(f"Layer shape mismatch: {name}")
        if name.startswith("ht_dir_"):
            valid = np.asarray(layers["ht_valid"]) >= .5
            if not np.isfinite(values[valid]).all() or np.any((values[valid] < 0) | (values[valid] > 1)):
                raise ValueError(f"Invalid probability at claimed valid cells: {name}")
        d = Float32MultiArray()
        d.layout = MultiArrayLayout(dim=[
            MultiArrayDimension(label="column_index", size=cols, stride=rows * cols),
            MultiArrayDimension(label="row_index", size=rows, stride=rows)], data_offset=0)
        d.data = array("f", values.flatten(order="F").tobytes())
        m.data.append(d)
    return m


def synthetic_fixtures():
    """Analytic fixtures are independent of all measured terrain/model outputs."""
    side, resolution = 251, .04  # 10.04m square, fully physically supported.
    i, j = np.indices((side, side))
    x = (side / 2 - i - .5) * resolution
    y = (side / 2 - j - .5) * resolution

    def terrain():
        return {**{f"ht_dir_{k}": np.full((side, side), .1, np.float32) for k in range(8)},
                "ht_valid": np.ones((side, side), np.float32),
                "ht_observation_valid": np.ones((side, side), np.float32),
                "ht_obstacle": np.zeros((side, side), np.float32),
                "ht_elevation": np.zeros((side, side), np.float32)}

    corridor = terrain()
    corridor["ht_dir_0"][np.abs(y) <= .8] = .95
    yield ("synthetic_reverse_theta0", corridor, (0., 0., 0.), (-1.2, 0.),
           {"expected": "PLANNED with reverse translation", "scope": "Synthetic directional corridor",
            "description": "Only body-yaw channel 0 passes; goal is behind start. Configuration score semantics are required; displacement bearing is not body yaw."})

    turn = terrain()
    for k in range(8):
        turn[f"ht_dir_{k}"][:] = .95
    band = (y >= .6) & (y <= 2.2)
    for k in range(8):
        if k not in (2, 6):
            turn[f"ht_dir_{k}"][band] = .1
    # Wall meets the -X map edge. Its only passage is around the +X end;
    # 0.6m footprint inflation must be used by the real HT gate.
    wall = (x <= .45) & (y >= .9) & (y <= 1.3)
    turn["ht_obstacle"][wall] = 1
    turn["ht_elevation"][wall] = .8
    for k in range(8):
        turn[f"ht_dir_{k}"][wall] = .05
    yield ("synthetic_directional_turn_wall", turn, (0., 0., 0.), (0., 2.8),
           {"expected": "PLANNED with heading changes and +X obstacle detour", "scope": "Synthetic directional wall bypass",
            "description": "Middle Y band permits only body headings 90/270 degrees; lower and upper turning areas permit all headings. Physical wall blocks the direct lateral route. This field is not uniformly green."})

    yield ("synthetic_low_probability", terrain(), (0., 0., 0.), (1.5, 0.),
           {"expected": "INVALID_START", "scope": "Synthetic negative control",
            "description": "Fully supported map with T=0.1 in every direction; startup prior cannot override low scores."})


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--maps", required=True, type=Path)
    p.add_argument("--output", required=True, type=Path)
    p.add_argument("--frame-stride", type=int, default=5,
                   help="Select every Nth successful real frame, retaining the final frame (default: 5)")
    p.add_argument("--heading-probe-stride", type=int, default=0,
                   help="Add counterfactual heading probes every Nth selected real frame and at the final frame; 0 disables them")
    a = p.parse_args()
    if a.frame_stride < 1:
        p.error("--frame-stride must be a positive integer")
    if a.heading_probe_stride < 0:
        p.error("--heading-probe-stride must be 0 (disabled) or a positive integer")
    maps_dir = a.maps.resolve()
    index_path = maps_dir / "index.json"
    index = json.loads(index_path.read_text())
    source_path = Path(index["source"])
    if not source_path.is_absolute():
        source_path = (maps_dir / source_path).resolve()
    actual_source_sha = sha256(source_path)
    if actual_source_sha != index["source_sha256"]:
        raise ValueError("Original source CDR archive SHA256 does not match replay index")
    # Input archive is a trusted local experiment artifact, not an uploaded pickle.
    with source_path.open("rb") as f:
        archive = pickle.load(f)
    sources = sorted((deserialize_message(b, GridMap) for b in archive["maps"]), key=stamp_ns)
    frames = [v for v in index["frames"] if v.get("output") and v.get("file")]
    if not frames:
        raise ValueError("No successful real frames in index")
    selected = frames[::a.frame_stride]
    if selected[-1]["file"] != frames[-1]["file"]:
        selected.append(frames[-1])
    probe_indices = set()
    if a.heading_probe_stride:
        probe_indices.update(range(0, len(selected), a.heading_probe_stride))
        probe_indices.add(len(selected) - 1)
    a.output.mkdir(parents=True, exist_ok=False)
    out = a.output.resolve()
    (out / "maps").mkdir()
    records, queries = [], []
    probe_frame_labels = []
    for selected_index, f in enumerate(selected):
        source = sources[int(f["input_index"])]
        if stamp_ns(source) != int(f["stamp_ns"]) or source.header.frame_id != "map":
            raise ValueError("Source CDR stamp/frame differs from indexed HT result")
        source_yaw = map_yaw(source)
        npz_path = maps_dir / f["file"]
        with np.load(npz_path, allow_pickle=False) as d:
            # The producer explicitly rejects non-axis-aligned source geometry.
            # Confirm the actual CDR as well before filling a missing NPZ yaw.
            if "yaw" not in d and abs(source_yaw) > 1e-6:
                raise ValueError("NPZ omits yaw but original source map is rotated")
            if "yaw" in d and abs(math.remainder(float(d["yaw"]) - source_yaw, 2 * math.pi)) > 1e-6:
                raise ValueError("NPZ yaw disagrees with original CDR orientation")
            layers = {name: d[name].copy() for name in LAYERS}
            probabilities = d["probabilities"]
            if probabilities.shape != (8, *layers["ht_valid"].shape):
                raise ValueError("Stacked probability shape mismatch")
            for k in range(8):
                if not np.array_equal(probabilities[k], layers[f"ht_dir_{k}"], equal_nan=True):
                    raise ValueError("Saved stacked and named directional layers disagree")
            center, resolution, robot = d["center"], float(d["resolution"]), d["robot"].copy()
            if robot.shape != (3,) or not np.isfinite(robot).all():
                raise ValueError("Missing/invalid recorded start pose")
            m = grid_message(layers, center, resolution, source)
        target = out / "maps" / f"{npz_path.stem}.cdr"
        target.write_bytes(serialize_message(m))
        record = {"label": npz_path.stem, "kind": "recorded", "file": str(target),
                  "sha256": sha256(target), "input_npz": str(npz_path), "input_sha256": sha256(npz_path),
                  "input_index": int(f["input_index"]), "stamp_ns": stamp_ns(m), "frame_id": m.header.frame_id,
                  "map_yaw": source_yaw, "orientation_source": "SHA256-verified original CDR; source contract also rejects rotated geometry",
                  "start": robot.tolist(), "shape": list(layers["ht_valid"].shape), "resolution": resolution}
        records.append(record)
        for k in range(8):
            angle = k * math.pi / 4
            queries.append((str(target), *map(float, robot), float(robot[0] + 1.5 * math.cos(angle)),
                            float(robot[1] + 1.5 * math.sin(angle)), f"recorded_{npz_path.stem}_goal_{k * 45:03d}deg"))
        if selected_index in probe_indices:
            # These are different initial conditions, not rotations from the
            # recorded pose. Reuse the original map bytes without changing
            # terrain, support, observation stamps, or the recorded main group.
            probe_frame_labels.append(npz_path.stem)
            for k in range(8):
                angle = k * math.pi / 4
                label = (f"counterfactual_heading_frame_{int(f['input_index']):04d}"
                         f"_yaw_{k * 45:03d}deg")
                queries.append((str(target), float(robot[0]), float(robot[1]), angle,
                                float(robot[0] + 1.5), float(robot[1]), label))

    for label, layers, start, goal, evidence in synthetic_fixtures():
        m = grid_message(layers, np.zeros(2), .04, synthetic=True)
        target = out / "maps" / f"{label}.cdr"
        target.write_bytes(serialize_message(m))
        queries.append((str(target), *start, *goal, label))
        records.append({"label": label, "kind": "synthetic", "file": str(target), "sha256": sha256(target),
                        "start": start, "goal": goal, "map_yaw": 0., "stamp_ns": stamp_ns(m),
                        "timestamp_scope": "Artificial fixture timestamp, not a recorded observation", **evidence})
    query_path = out / "queries.tsv"
    query_path.write_text("".join("\t".join(str(v) if isinstance(v, str) else format(v, ".17g") for v in row) + "\n" for row in queries))
    metadata = {"scope": SCOPE, "maps_index": str(index_path), "maps_index_sha256": sha256(index_path),
                "source_cdr_pickle": str(source_path), "source_cdr_pickle_sha256": actual_source_sha,
                "producer_orientation_contract": "tools/ht_cupy_bridge/cupy_to_ht.py:decode_elevation_source",
                "canonical_grid": "row points toward -map X; column toward -map Y for yaw=0; F-order storage; circular starts zero",
                "query_columns": ["mapfile", "start_x", "start_y", "start_yaw", "goal_x", "goal_y", "label"],
                "query_file": str(query_path), "query_sha256": sha256(query_path), "query_header": False,
                "frame_stride": a.frame_stride,
                "real_query_selection": f"Every {a.frame_stride}th successful recorded frame plus final frame; 8 world-frame goals 1.5m from recorded start, preserving recorded body yaw",
                "heading_probe_stride": a.heading_probe_stride,
                "counterfactual_heading_frames": len(probe_indices),
                "counterfactual_heading_frame_labels": probe_frame_labels,
                "counterfactual_heading_queries": len(probe_indices) * 8,
                "counterfactual_heading_selection": (
                    f"Every {a.heading_probe_stride}th selected real frame plus final selected frame"
                    if a.heading_probe_stride else "Disabled"),
                "counterfactual_heading_scope": (
                    "Separate diagnostic group: replace only initial body yaw by k*pi/4 "
                    "for k=0..7 at the same recorded XY, with a common world +X goal 1.5m away. "
                    "Original map fields, probabilities and source stamps are unchanged. "
                    "These changed initial conditions do not establish that the recorded vehicle "
                    "can rotate into those headings, and must not count as recorded navigation success."),
                "query_groups": {"recorded": len(selected) * 8,
                                 "counterfactual_heading": len(probe_indices) * 8,
                                 "synthetic": 3},
                "synthetic_assumptions": "Configuration/body-yaw semantics, unchanged T>=0.5 hard gate, 0.6m physical radius; synthetic controls are not model accuracy evidence",
                "recorded_frames": len(selected), "synthetic_frames": 3, "queries": len(queries), "maps": records}
    (out / "metadata.json").write_text(json.dumps(metadata, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({"output": str(out), "real_frames": len(selected), "queries": len(queries)}))


if __name__ == "__main__":
    main()
