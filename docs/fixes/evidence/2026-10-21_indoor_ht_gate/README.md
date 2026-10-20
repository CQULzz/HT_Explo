# 室内HT门禁诊断证据

详见 ../../2026-10-21_indoor_ht_gate.md。

只读离线诊断，室内尚未修复。exact触发模型输入未保存，后续RF噪声统计属于可检验假设，不是已证实神经因果机制。

`counterfactual_fixture.npz`为实际相邻帧候选/当前碰撞/按HT录包重建历史，用于逐点BFS复现；`last_precompletion_map.npz`为接收t13.511985778808594s、源1792497893.335921的HT输出，geometry=(center_x, center_y,resolution)，prob shape=(8,241,241)。所有prob按输出自身坐标，无额外平移。

原始MCAP及上下文路径见主诊断文档。
