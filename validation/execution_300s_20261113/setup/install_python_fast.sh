set -eo pipefail
R=/home/lzz/ht_execution_300s_20261113
"$R/venv/bin/pip" install --no-deps /mnt/d/HT-Execution-300s/setup/torch-2.8.0-cp310-cp310-manylinux_2_28_x86_64.whl
"$R/venv/bin/pip" install -i https://mirrors.aliyun.com/pypi/simple --timeout 120 numpy==1.26.4 cupy-cuda12x==13.6.0 numba==0.61.2 ruamel.yaml simple-parsing scikit-image networkx shapely filelock typing-extensions sympy==1.14.0 jinja2 fsspec triton==3.4.0
echo PYTHON_COMPLETE
