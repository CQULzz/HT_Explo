# 9盒基线独立重复性核查

逐数组比较 208 帧；源时间、车体位姿、地图坐标、显式HT参数与实际CUDA/Numba后端一致。

| 数组 | 最大绝对差 | 有限数值不同数 | NaN位置不同数 |
|---|---:|---:|---:|
| probabilities | 0.592354283 | 56010348 | 512 |
| raw | 1.1092934 | 656863 | 3452 |
| ht_elevation | 1.07594115 | 1477061 | 2567 |
| ht_valid | 1 | 64 | 0 |
| ht_observation_valid | 0 | 0 | 0 |
| ht_obstacle | 1 | 2581 | 0 |
| ht_measured_valid | 1 | 2567 | 0 |
| ht_interpolated | 0 | 0 | 0 |

共同context有效位置的T=0.5分类翻转数：10208；物理/上下文/障碍等mask值变化总数：5212。

记录车位中心8方向累计翻转：0；0.6m诊断圈内概率翻转：97，障碍掩码差异：95。诊断圈不代替完整生产足迹检查。

CuPy参数差异：{"plugin_config_file": {"previous": "/home/lzz/my test/HT_Explo-real-round2-20261028/cupy_rebuild/plugins.yaml", "fresh": "/media/lzz/My Passport/HT_Explo_urdf_visual_candidate_2026-10-28/run_data/cupy_rebuild/plugins.yaml"}}；两份plugin文件实际内容一致：True。

与旧运行源码相比，本次所核验9个HT推理模块逐字节一致：True。基线混淆标志：True。

此处比较数值与掩码，不以NPZ、pickle或CDR字节哈希替代语义比较。单个重复控制不能证明未来GPU运行绝对确定，也不能验证ARM/实时执行。
