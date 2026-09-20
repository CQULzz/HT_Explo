# 使用方法与证据索引

在仓库根目录运行：

```bash
python3 experiments/traversability/audit_local_evidence.py --root /home/lzz/下载
python3 experiments/traversability/plot_local_evidence.py
```

第一条仅用 Python 标准库，约 1–2 秒；第二条需要 matplotlib。无需模型训练、ROS 或模型 API。原始目录只读，输出在本目录。

- `REPORT.md`：结论、指标与限制。
- `audit.json`：全量标签计数、SHA-256、混淆矩阵重算、历史结果来源。
- `historical_curves.csv`：所有可解析的历史高度偏移曲线，保留每条来源，未挑选最好结果。
- `height_bias.png`：同一 Scout `infer_new1` 归档中的三网络对照。

原始材料（相对于下载目录）：

|位置|用途|
|---|---|
|`train_data/sum_train_scout_infer_new1/*/ht_result_dict.txt`|梯度 HT、原始高程 ViT、参考网络的高度偏移准确率|
|`original_scout/mini_25_training/runs/formal/{teacher,student}/test_metrics.json`|完整测试集的危险误放/安全误拒统计|
|`data_scout/traversability_sim_label/split_train_val_mini_25/`|1,929,808 条标签及位置、方向、耗时、偏差、高差|
|`data_scout/traversability_sim_data_train_height/`|1591 张高程图，含山地及结构化障碍等地形名称|
|`ht_tra_classification_scout_mapping/utils/dataloader.py:347`|偏移加在整体物理高程上，不改变地形相对坡度|
|`ht_tra_classification_scout_mapping/utils/utils_fit.py:175`|历史偏移测试只统计准确率，没有误放率|
|`ht_tra_classification_scout_mapping/txt_annotation_frontcar_repeatdata_teacher_elefilesave_multiprocess_plane_onelabel_returntime_new.py:646`|通过标签含耗时、横向偏差条件；完整标签溯源仍需原始运动日志|
|`ht_traversability_classification_hunterse/` 与 `train_data/sum_train_hunter_se_infer/`|另一车型的网络和历史对照，不能混作 Scout 结果|
|`Untitled.ipynb`|空 notebook，无可用结果|

高差大于 0.2 m 是本审计的描述性分层，不代表车辆安全阈值或坡度真值。20.4 万条测试记录属于该层，可用于下一轮复杂地形评估，但目前没有这部分样本的逐项模型预测，因此不能计算其单独的误放率。当前包也不等于已有探索系统加载了这些权重。
