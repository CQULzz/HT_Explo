set -eo pipefail
source /home/lzz/ht_600s_20261114/env.sh
export ROS_DOMAIN_ID=217 DISPLAY=:89
export XDG_RUNTIME_DIR=/tmp/ht-rviz-video-runtime
mkdir -p "$XDG_RUNTIME_DIR"
chmod 700 "$XDG_RUNTIME_DIR"
R=/mnt/d/HT-Execution-300s/rviz_video_20261114
Xvfb :89 -screen 0 1920x1080x24 > "$R/xvfb.log" 2>&1 &
XVP=$!
trap 'kill ${PLAYER:-} ${RV1:-} ${RV2:-} "$XVP" 2>/dev/null || true' EXIT
sleep 2
python3 /mnt/d/HT-Execution-300s/setup/rviz_video_player.py > "$R/player.log" 2>&1 &
PLAYER=$!
rviz2 -d "$R/overview.rviz" --ros-args -r __node:=rviz_overview > "$R/rviz_overview.log" 2>&1 &
RV1=$!
rviz2 -d "$R/detail.rviz" --ros-args -r __node:=rviz_detail > "$R/rviz_detail.log" 2>&1 &
RV2=$!
echo "Xvfb=$XVP player=$PLAYER RViz=$RV1,$RV2"
while kill -0 "$PLAYER" && kill -0 "$RV1" && kill -0 "$RV2"; do
 if test -f "$R/STOP"; then break; fi
 sleep 2
done
