set -e
source /home/lzz/ht_window_recovery_20261118/env.sh
cmake --build /home/lzz/ht_window_recovery_20261118/candidate/build/cmu_local_planner_ht --target ht_recovery_return_test -j2 > /home/lzz/ht_window_recovery_20261118/setup/build_final_test.log 2>&1
ctest --test-dir /home/lzz/ht_window_recovery_20261118/candidate/build/cmu_local_planner_ht --output-on-failure > /home/lzz/ht_window_recovery_20261118/analysis/ctest.log 2>&1
cat /home/lzz/ht_window_recovery_20261118/analysis/ctest.log
