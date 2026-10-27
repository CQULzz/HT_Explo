#!/usr/bin/env bash
ht_real_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
source "$ht_real_root/scripts/real_scout_environment.sh" || return 1
if [[ ! -f "$ht_real_root/install_real/local_setup.bash" ]]; then
  echo "Build the real Scout workspace first: bash scripts/build_real_scout.sh" >&2
  return 1
fi
source "$ht_real_root/install_real/local_setup.bash"
