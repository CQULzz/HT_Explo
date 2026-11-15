#!/bin/bash
set -e
source /home/lzz/ht_helios_collision_20261115/env.sh
export PYTHONPATH=/usr/lib/python3/dist-packages:$PYTHONPATH
/home/lzz/ht_real_baseline_20261115/validation_venv/bin/python /mnt/d/HT-Helios-Collision-20261115/setup/validate_evidence.py
