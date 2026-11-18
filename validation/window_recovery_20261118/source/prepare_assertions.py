from pathlib import Path
import shutil
r=Path('/home/lzz/ht_window_recovery_20261118');repo=Path('/mnt/c/Users/李哲舟/Desktop/python code/work/ht_execution_fixes');shutil.copy2(repo/'src/cmu_local_planner_ht/src/ht_recovery_return_test.cpp',r/'candidate/src/cmu_local_planner_ht/src/ht_recovery_return_test.cpp');p=r/'probe_candidate.sh';s=p.read_text().replace('candidate_probe/probe >','candidate_probe/probe --expect-return >');p.write_text(s)
