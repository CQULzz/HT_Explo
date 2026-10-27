# 本机离线GPU环境

原系统Python的PyTorch为`2.11.0+cpu`。硬件实际为RTX 5060 Ti 16GB、驱动580.178.04、计算能力12.0；先前CPU回放不能代表默认CUDA入口。
本轮单独建立`/home/lzz/.venvs/ht_real_gpu_20261028`，没有替换系统CPU环境：

```bash
python3 -m venv --without-pip --system-site-packages ~/.venvs/ht_real_gpu_20261028
python3 -m pip --python ~/.venvs/ht_real_gpu_20261028/bin/python install \
  --no-cache-dir 'torch==2.11.0+cu128' --index-url https://download.pytorch.org/whl/cu128
```

安装方式依据[PyTorch官方安装入口](https://pytorch.org/get-started/locally/)，具体版本以本轮pip日志和实际运算检查为准。
CuPy使用已有13.6.0；显式提供虚拟环境里的NVRTC和CUDA运行库搜索路径。
Numba另装0.65.1、llvmlite 0.47.0，NumPy保持1.26.4。系统coverage 7.4.4与该Numba导入不兼容；仅在虚拟环境升级coverage到7.17.0，原失败日志保留。

```bash
source scripts/source_real_scout.sh
source ~/.venvs/ht_real_gpu_20261028/bin/activate
export LD_LIBRARY_PATH="$VIRTUAL_ENV/lib/python3.12/site-packages/nvidia/cuda_nvrtc/lib:$VIRTUAL_ENV/lib/python3.12/site-packages/nvidia/cuda_runtime/lib:${LD_LIBRARY_PATH:-}"
python tools/check_ht_compute.py --require-cuda --cupy --require-numba
```

CuPy源码放在独立工作区`/home/lzz/my test/ht_cupy_gpu_ws_20261028`，基线`88f4c0c`。
已经应用HT仓库原有`tools/elevation_mapping_fixes/cupy_ht_mapping.patch`。它用接受点的源时间记录观测年龄；该补丁与目前查到的上游基线一致。
先由独立CuPy进程读取准备好的原始点云生成序列化GridMap，再由HT进程读取这些数据。HT运行包不导入相邻CuPy源码，也不启动任何设备。

这是x86_64/Jazzy的离线环境，不是Jetson/ARM64环境镜像。目标Jetson需要自身匹配的CUDA/PyTorch构建，并核对外部mapper补丁和新`/ht_real/lidar_filtered`接线。不要把此目录的二进制复制到Jetson。

首次GPU回放使用域235，FastDDS因端口超限而启动失败；失败目录和日志已保留。有效复测使用本机隔离域181。
