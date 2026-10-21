# 阶段34｜逐段验算简单SE2连接，600秒但退出诊断异常

## 改了什么

HT路径调用先验算原地转向后前进/倒车的两个简单SE2连接，再回退原Hybrid A*。每0.05rad/0.05m调用相同HT、几何、未知、失败记忆和航向谓词。没有侧移，速度/安全门槛/实际参数/0.15秒单目标与0.35秒周期配置未变；连接和图搜索共用截止。连接车头角可连续变化，原32航向键和两种曲率动作保留。

## 实现了什么功能

阶段33长停车中的公开HT/几何冻结重建可找到简单恢复路线，原搜索需6709/8633次检查，较小恢复预算超时；新连接112/126次检查通过。公开话题不等于精确内部状态重放，不把微基准作为全场景固定加速比。新增倒车/无侧移、禁行中间朝向、无效起点、半径/时间上限和连接受阻后绕障回归，全部4个CTest通过。

## 实验与验证

实测391fa0f，室内完整600秒168.77m/2169.875m³，末尾EXPLORING。最后一分钟14.826m，最后平移指令600.001s，最长全零3.600s。前轮151.57m/2480m³、最长35.8s；历史阶段30仍为169.57m/3321.25m³，不能只比较失败轮。754次搜索中513次使用验算连接，退出{'REACHED': 704, 'TIME_LIMIT': 42, 'EXHAUSTED': 1, 'INVALID_START': 7}。

12/13项采集核验通过，退出时1份诊断NPZ损坏、原异常和坏文件完整保留；57份可读上下文核验通过、overall仍failed。视频9000帧/600.000000s完整解码。[完整报告、五轮对比、地图与视频](https://github.com/CQULzz/HT_Explo/blob/codex/ht8dir-v1/docs/results/ht_checked_connections_10min_2026-10-19/REPORT.md)。附件包含整轮已录制数据、精选结果和独立MP4；激光源秒抽样、地图周期快照，不是所有传感器无损记录。

## 存在什么问题

最大单次搜索0.253844s，图搜索每32展开检查截止和单次谓词长尾仍可能超过名义预算。简单连接优先可行，可能增加转向或改变收益，不保证时间最优。地图/路径时效、全局未连接或不可观察任务、同版重复/多环境、独立真值覆盖与实车尚未全部验收；SE2运动学加执行限速不等于完整轮胎/滑移动力学证明，不标稳定或无缺陷。

<!-- repository-catalog-start -->
## 代码、视频与完整数据的对应关系

- [阶段34完整索引：实际实验候选、导航代码、报告、视频及数据回执](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/catalog/stage-34.md)
- [本阶段归档源码](https://github.com/CQULzz/HT_Explo/tree/391fa0f98fc2a0adab2c018b4c5a1c7c29efff91)：`391fa0f98fc2a0adab2c018b4c5a1c7c29efff91`。这是归档锚点；实际测量源码、运行patch与二进制哈希以原清单为准。
- [完整实验总目录](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/catalog/INDEX.md) · [分支和标签规则](https://github.com/CQULzz/HT_Explo/blob/main/docs/REPOSITORY_GUIDE.md)

早期历史目录只关联到研究阶段，未知测量提交保持待确认；补充回放视频不代表新的导航实验。原有报告、失败记录与全部附件保留。
<!-- repository-catalog-end -->
