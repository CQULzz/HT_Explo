set -e
source /home/lzz/ht_window_recovery_20261118/env.sh
cd /home/lzz/ht_window_recovery_20261118/candidate
colcon build --packages-select cmu_local_planner_ht --cmake-args -DCMAKE_BUILD_TYPE=Release > /home/lzz/ht_window_recovery_20261118/setup/build_candidate.log 2>&1
ctest --test-dir build/cmu_local_planner_ht --output-on-failure > /home/lzz/ht_window_recovery_20261118/analysis/ctest.log 2>&1
cat /home/lzz/ht_window_recovery_20261118/analysis/ctest.log
