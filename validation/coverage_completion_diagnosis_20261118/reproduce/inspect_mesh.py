from pathlib import Path
import importlib.util
r=Path('/home/lzz/cmu_sim_20261110/src/vehicle_simulator/mesh/campus');print((r/'model.sdf').read_text());print((r/'meshes/campus.dae').open().read(1300));print({p:bool(importlib.util.find_spec(p)) for p in ['trimesh','collada','lxml','rtree']})
