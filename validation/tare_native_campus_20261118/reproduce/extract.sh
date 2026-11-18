set -e
source /home/lzz/tare_native_campus_20261118/env.sh
/usr/bin/python3 /mnt/d/TARE-Native-Campus-20261118/first_extract_terminal.py
/usr/bin/python3 /mnt/d/TARE-Native-Campus-20261118/repeat_extract_terminal.py
/usr/bin/python3 /mnt/d/TARE-Native-Campus-20261118/navigation_diagnostic.py > /mnt/d/TARE-Native-Campus-20261118/navigation_diagnostic.log
