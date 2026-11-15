"""Prepare the current Helios32 Scout profile (box crop by default).

Historical transparent assets stay in old experiment directories; this entry
does not overwrite those historical inputs. New crop assets omit body collisions;
--self-filter collision_identity retains opaque geometry in a new output folder.
"""
from pathlib import Path
import runpy
runpy.run_path(str(Path(__file__).resolve().parents[1]/'helios32_sim/prepare_assets.py'),run_name='__main__')
