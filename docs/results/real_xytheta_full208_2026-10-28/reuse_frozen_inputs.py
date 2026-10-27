#!/usr/bin/env python3
"""Reuse frozen CDR bytes only after proving differences are CDR1 alignment padding.

Input preparation only: no navigation, publication, timestamp refresh, field
normalization, or model change. Run before the actual C++ comparison.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import struct

from grid_map_msgs.msg import GridMap
from rclpy.serialization import deserialize_message


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read(path: Path):
    return json.loads(path.read_text())


def require(condition, explanation):
    if not condition:
        raise ValueError(explanation)


class Cdr1Layout:
    """Parse GridMap's XCDR1 field lengths; record only alignment padding.

    Alignment is relative to the payload after the four-byte encapsulation.
    Reject unknown encodings or trailing bytes rather than guessing padding.
    """

    def __init__(self, data: bytes):
        require(data[:2] in (b"\x00\x00", b"\x00\x01"), "Require plain big/little-endian CDR1")
        require(len(data) >= 4, "Truncated CDR encapsulation")
        self.data = data
        self.endian = ">" if data[:2] == b"\x00\x00" else "<"
        self.pos = 4
        self.padding = set()

    def take(self, size, alignment=1):
        padded = self.pos + (-(self.pos - 4) % alignment)
        require(padded + size <= len(self.data), "Truncated CDR field")
        self.padding.update(range(self.pos, padded))
        start = padded
        self.pos = padded + size
        return self.data[start:self.pos]

    def uint32(self):
        return struct.unpack(self.endian + "I", self.take(4, 4))[0]

    def string(self):
        count = self.uint32()
        require(count > 0, "CDR string lacks terminating NUL")
        value = self.take(count)
        require(value[-1:] == b"\x00", "Unterminated CDR string")

    def grid_map(self):
        self.take(4, 4)  # Header.stamp.sec
        self.take(4, 4)  # Header.stamp.nanosec
        self.string()  # Header.frame_id
        self.take(10 * 8, 8)  # GridMapInfo: resolution, lengths, Pose
        for _ in range(2):  # layers, basic_layers
            for _ in range(self.uint32()):
                self.string()
        for _ in range(self.uint32()):  # Float32MultiArray[] data
            for _ in range(self.uint32()):  # layout.dim
                self.string()
                self.take(4, 4)  # dimension.size
                self.take(4, 4)  # dimension.stride
            self.take(4, 4)  # layout.data_offset (a field, not CDR padding)
            self.take(self.uint32() * 4, 4)  # float32[] data
        self.take(2, 2)  # outer_start_index
        self.take(2, 2)  # inner_start_index
        require(self.pos == len(self.data), "Unparsed/trailing CDR bytes")
        return self.padding


def prove_equal(fresh: bytes, frozen: bytes, label: str):
    require(len(fresh) == len(frozen), f"{label}: CDR lengths differ")
    new = deserialize_message(fresh, GridMap)
    old = deserialize_message(frozen, GridMap)
    fields = ("header", "info", "layers", "basic_layers", "outer_start_index", "inner_start_index")
    for name in fields:
        require(getattr(new, name) == getattr(old, name), f"{label}: {name} differs")
    require(len(new.data) == len(old.data), f"{label}: layer data count differs")
    require(len(new.data) == len(new.layers), f"{label}: layer/data count mismatch")
    layer_checks = []
    for name, current, previous in zip(new.layers, new.data, old.data):
        require(current.layout == previous.layout, f"{label}/{name}: layout differs")
        current_bytes = current.data.tobytes()
        previous_bytes = previous.data.tobytes()
        require(current_bytes == previous_bytes, f"{label}/{name}: float32 bit patterns differ")
        layer_checks.append({"layer": name, "layout_identical": True,
                             "float32_bytes_identical": True, "data_bytes": len(current_bytes),
                             "data_sha256": digest(current_bytes)})
    fresh_padding = Cdr1Layout(fresh).grid_map()
    frozen_padding = Cdr1Layout(frozen).grid_map()
    require(fresh_padding == frozen_padding, f"{label}: CDR padding locations differ")
    differences = [i for i, (a, b) in enumerate(zip(fresh, frozen)) if a != b]
    require(set(differences) <= fresh_padding, f"{label}: non-padding serialized bytes differ")
    return {"decoded_header_info_layers_basic_layers_indices_identical": True,
            "all_layouts_and_float32_bits_identical": True, "layers": layer_checks,
            "all_differences_are_parsed_cdr1_alignment_padding": True,
            "differing_byte_offsets": differences,
            "differing_bytes": [{"offset": i, "fresh": fresh[i], "frozen": frozen[i]}
                                for i in differences],
            "parsed_padding_offsets": sorted(fresh_padding)}


def indexed_maps(meta):
    result = {}
    for row in meta["maps"]:
        require(row["label"] not in result, "Duplicate map label in metadata")
        result[row["label"]] = row
    return result


def checked_bytes(row):
    path = Path(row["file"])
    data = path.read_bytes()
    require(digest(data) == row["sha256"], f"Metadata/file SHA256 mismatch: {path}")
    return path, data


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", required=True, type=Path)
    parser.add_argument("--previous", required=True, type=Path)
    args = parser.parse_args()
    data, previous = args.data.resolve(), args.previous.resolve()
    require(data != previous, "Current and previous directories must differ")
    for role in ("before", "after"):
        require(not (data / (role + ".json")).exists(), "C++ result already exists; refuse input mutation")
    audit_dir = data / "serialization_audit"
    require(not audit_dir.exists() and not (data / "PADDING_AUDIT.json").exists(),
            "Serialization audit already exists; refuse repeat/partial execution")
    metadata_path = data / "input/metadata.json"
    metadata_bytes = metadata_path.read_bytes()
    current = json.loads(metadata_bytes)
    old_meta_path = previous / "input/metadata.json"
    old_meta_bytes = old_meta_path.read_bytes()
    old = json.loads(old_meta_bytes)
    for key in ("source_cdr_pickle_sha256", "maps_index_sha256"):
        require(current[key] == old[key], f"Different preparation source: {key}")
    # Independently check source files, rather than trusting matching labels.
    for path_key, hash_key in (("source_cdr_pickle", "source_cdr_pickle_sha256"),
                               ("maps_index", "maps_index_sha256")):
        for meta in (current, old):
            source_path = Path(meta[path_key])
            require(digest(source_path.read_bytes()) == meta[hash_key], f"Source SHA256 mismatch: {source_path}")
    current_maps, old_maps = indexed_maps(current), indexed_maps(old)
    require(set(old_maps) <= set(current_maps), "Previous map subset is not present")
    # Validate all pairs before creating audit directories or replacing bytes.
    verified = []
    for label, old_row in old_maps.items():
        row = current_maps[label]
        for key in ("kind", "input_sha256", "input_index", "stamp_ns", "frame_id",
                    "map_yaw", "start", "shape", "resolution", "goal"):
            require(row.get(key) == old_row.get(key), f"{label}: metadata source field differs: {key}")
        if "input_npz" in row:
            for item in (row, old_row):
                require(digest(Path(item["input_npz"]).read_bytes()) == item["input_sha256"],
                        f"{label}: source NPZ SHA256 mismatch")
        target, fresh = checked_bytes(row)
        require(target.resolve().is_relative_to((data / "input/maps").resolve()), "Map target escapes input/maps")
        frozen_path, frozen = checked_bytes(old_row)
        evidence = prove_equal(fresh, frozen, label)
        verified.append((row, target, fresh, frozen, {
            "label": label, "current_file": str(target), "previous_file": str(frozen_path),
            "fresh_sha256": digest(fresh), "frozen_sha256": digest(frozen),
            "size_bytes": len(fresh), "requires_byte_reuse": fresh != frozen, **evidence}))
    audit_dir.mkdir()
    fresh_dir = audit_dir / "fresh_CDR"
    fresh_dir.mkdir()
    (audit_dir / "input_metadata.before_reuse.json").write_bytes(metadata_bytes)
    (audit_dir / "previous_metadata.json").write_bytes(old_meta_bytes)
    changed = 0
    for row, target, fresh, frozen, evidence in verified:
        if fresh != frozen:
            archive_path = fresh_dir / target.name
            require(not archive_path.exists(), "Duplicate fresh CDR archive target")
            archive_path.write_bytes(fresh)
            evidence["fresh_archive"] = str(archive_path)
            target.write_bytes(frozen)
            changed += 1
        row["sha256"] = digest(frozen)
        row["reused_frozen_cdr"] = {
            "previous_file": evidence["previous_file"], "sha256": digest(frozen),
            "fresh_sha256": digest(fresh), "bytes_replaced": fresh != frozen,
            "decoded_fields_and_float32_bits_verified_identical": True,
            "only_cdr1_alignment_padding_differed": True}
    current["frozen_cdr_reuse"] = {
        "previous_directory": str(previous), "verified_overlap_maps": len(verified),
        "padding_different_files_replaced": changed,
        "original_metadata_archive": str(audit_dir / "input_metadata.before_reuse.json"),
        "scope": "Original frozen CDR bytes reused after field, float32-bit and CDR1-padding proof; no source stamp, map value or query changed"}
    metadata_path.write_text(json.dumps(current, ensure_ascii=False, indent=2) + "\n")
    audit = {"status": "complete", "created_utc": datetime.now(timezone.utc).isoformat(),
             "data": str(data), "previous": str(previous), "maps_verified": len(verified),
             "padding_different_files_replaced": changed,
             "original_metadata_sha256": digest(metadata_bytes),
             "previous_metadata_sha256": digest(old_meta_bytes),
             "updated_metadata_sha256": digest(metadata_path.read_bytes()),
             "source_cdr_pickle_sha256": current["source_cdr_pickle_sha256"],
             "maps_index_sha256": current["maps_index_sha256"],
             "no_nonpadding_value_changes": True, "query_file_unchanged": True,
             "maps": [item[-1] for item in verified]}
    (data / "PADDING_AUDIT.json").write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"status": "complete", "maps_verified": len(verified),
                      "padding_different_files_replaced": changed}))


if __name__ == "__main__":
    main()
