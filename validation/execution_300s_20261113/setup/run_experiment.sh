set -eo pipefail
R=/home/lzz/ht_execution_300s_20261113
source "$R/env.sh"
Xvfb :88 -screen 0 1280x720x24 > "$R/setup/xvfb.log" 2>&1 &
XVFB_PID=$!
trap 'kill "$XVFB_PID" 2>/dev/null || true' EXIT
export DISPLAY=:88
sleep 2
glxinfo -B > "$R/setup/renderer.txt"
"$R/venv/bin/python" -c 'import torch,cupy,elevation_mapping_cupy,grid_map_msgs.msg,rosbag2_py; print(torch.__version__,torch.cuda.get_device_name(0)); print(cupy.arange(5).sum()); print(elevation_mapping_cupy.__file__)' > "$R/setup/gpu_preflight.log" 2>&1
cd "$R/build_gate/cmu_local_planner_ht"
ctest --output-on-failure > "$R/setup/ctest.log" 2>&1
cd "$R"
"$R/venv/bin/python" "$R/run.py" --duration 300 --name execution_300s_02 --scene indoor > "$R/setup/formal_run_02.log" 2>&1
python3 /home/lzz/HT_Explo_execution_20261113/tools/cmu_minimal/audit_commands.py "$R/runs/execution_300s_02" > "$R/setup/command_audit.log" 2>&1
echo EXPERIMENT_COMPLETE
