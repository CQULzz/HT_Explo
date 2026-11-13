set -eo pipefail
R=/home/lzz/ht_execution_300s_20261113
python3 -m venv --system-site-packages "$R/venv"
"$R/venv/bin/pip" install -i https://mirrors.aliyun.com/pypi/simple --timeout 120 numpy==1.26.4 torch==2.8.0 cupy-cuda12x==13.6.0 numba==0.61.2 ruamel.yaml simple-parsing scikit-image networkx shapely > "$R/setup/install_python.log" 2>&1
echo PYTHON_COMPLETE
