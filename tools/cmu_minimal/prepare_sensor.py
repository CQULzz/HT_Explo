"""Prepare the corrected Helios32/opaque Scout profile.

Historical transparent assets stay in old experiment directories; this entry
does not remove collision geometry or overwrite those historical inputs.
"""
from pathlib import Path
import runpy
runpy.run_path(str(Path(__file__).resolve().parents[1]/'helios32_sim/prepare_assets.py'),run_name='__main__')
