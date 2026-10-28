# 相同过滤输入的负控制独立核查

415帧逐帧检查：负控制两套mask逐位相同，并等于主实验9盒before；原始点云、时间、R/t和全部里程计字节不变。

**元数据说明：**控制header里的旧 `mask_variant_provenance.new_profile_sha256` 是来源候选阶段的14盒历史哈希；活动 `mask_variant_profiles` 实际both9盒。以逐帧mask及活动profile为准，不应把历史来源字段误读为控制after用了14盒；未改pickle。

| 对比 | native elevation最大差/m | HT T最大差 | HT T平均绝对差 | 有效context中0.5翻转 | 车中心8方向翻转 | 记录车头中心翻转 |
|---|---:|---:|---:|---:|---:|---:|
| identical_mask_control | 1.5618699789047241 | 0.613599852 | 0.000514259143 | 16766 | 0 | 0 |
| filter_treatment | 1.1092934012413025 | 0.595428616 | 0.000571352404 | 11106 | 0 | 0 |
| between_run_old_baselines | 未另算native | 0.608879253 | 0.000526785322 | 16590 | 0 | 0 |

| 对比 | context mask变化格-帧 | physical observation变化 | obstacle变化 | measured变化 |
|---|---:|---:|---:|---:|
| identical_mask_control | 5 | 0 | 2810 | 2871 |
| filter_treatment | 3 | 87 | 3064 | 4291 |
| between_run_old_baselines | 3 | 0 | 2928 | 3033 |

这里报告的是实际观测差异，不能把所有变化归因于新增五盒。相同mask仍有变化则是重复链本身的变化，具体机制尚未由本对照隔离；不能只凭此命名为某个GPU kernel bug。单次负控制也不能当作稳定方差分布或直接扣除的误差项。

没有给负控制再做C++查询，没有启动实车、仿真或控制器；不能据地图显示改善声称停车已修复。详细各帧、各数组和边界见JSON。
