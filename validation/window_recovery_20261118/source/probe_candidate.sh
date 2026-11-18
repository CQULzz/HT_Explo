set -e
source /home/lzz/ht_window_recovery_20261118/env.sh
cmake -S /home/lzz/ht_window_recovery_20261118/probe_project -B /home/lzz/ht_window_recovery_20261118/candidate_probe -DHEADERS=/home/lzz/ht_window_recovery_20261118/candidate/src/cmu_local_planner_ht/src -DCMAKE_BUILD_TYPE=Release > /home/lzz/ht_window_recovery_20261118/setup/configure_candidate_probe.log
cmake --build /home/lzz/ht_window_recovery_20261118/candidate_probe --target probe -j2 > /home/lzz/ht_window_recovery_20261118/setup/build_candidate_probe.log 2>&1
/home/lzz/ht_window_recovery_20261118/candidate_probe/probe --expect-return > /home/lzz/ht_window_recovery_20261118/analysis/candidate_probe.log
cp /home/lzz/ht_window_recovery_20261118/analysis/probe_trace.csv /home/lzz/ht_window_recovery_20261118/analysis/candidate_trace.csv
cat /home/lzz/ht_window_recovery_20261118/analysis/candidate_probe.log
