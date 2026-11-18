from pathlib import Path
import shutil
r=Path('/home/lzz/ht_window_recovery_20261118');r.mkdir(exist_ok=False)
s=Path('/mnt/c/Users/李哲舟/Desktop/python code/work/ht_execution_fixes/src/cmu_local_planner_ht');shutil.copytree(s,r/'baseline/src/cmu_local_planner_ht')
(r/'setup').mkdir();(r/'analysis').mkdir()
(r/'env.sh').write_text('source /opt/ros/humble/setup.bash\nsource /home/lzz/ht_initial_labels_20261116/install/setup.bash\nexport ROS_DOMAIN_ID=211\nexport ROS_LOCALHOST_ONLY=1\nexport ROS_LOG_DIR=/home/lzz/ht_window_recovery_20261118/ros_logs\n')
(r/'extract.sh').write_text('set -e\nsource /home/lzz/ht_campus_repeat_1200s_20261118/env.sh\n/home/lzz/ht_campus_repeat_1200s_20261118/venv/bin/python /mnt/d/HT-Window-Recovery-20261118/extract_fixture.py\n')
