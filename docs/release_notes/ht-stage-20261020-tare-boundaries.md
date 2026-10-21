## 改了什么

在40恢复原TARE覆盖/TSP的基础上修正地形顶点掩码与BFS不一致、近家HOME优先级。实测68701319b333165dd9cd5acf8e226ba52c174434。先保存真实失败反例，再修改；原TARE六核心函数体、所有实际参数、模型和融合不变。

## 实现了什么功能

同一周期BFS和候选图共用HT掩码，异步更新在下一周期切换；执行仍依据最新HT。原近家HOME目标不再被缺失的前视输出拦住，无放宽安全门槛或更换收益目标。

## 实验与验证

真实ROS图构造、异步更新、解除禁行、HOME无前视/原分支回归和原4项CTest通过；六函数SHA一致。车库完整600秒181.31m/8660.125m³，较40+2.3%、较39+33.6%。13项采集与视频完整解码通过；全数据、视频和历次图册随附。

## 存在什么问题

搜索时间上限34次、展开上限57次，最长完全停车0.25s，末60秒新增671.645m³/移动16.56m；末尾EXPLORING。 单次轨迹不能证明某一边界修复导致体积变化；若本轮没有触发返航，只能说返航单元/分支回归通过。尚无同运动限制新原版配对、完整全局SE2可达或实车安全保证。

<!-- repository-catalog-start -->
## 代码、视频与完整数据的对应关系

- [阶段41完整索引：实际实验候选、导航代码、报告、视频及数据回执](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/catalog/stage-41.md)
- [本阶段归档源码](https://github.com/CQULzz/HT_Explo/tree/68701319b333165dd9cd5acf8e226ba52c174434)：`68701319b333165dd9cd5acf8e226ba52c174434`。这是归档锚点；实际测量源码、运行patch与二进制哈希以原清单为准。
- [完整实验总目录](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/catalog/INDEX.md) · [分支和标签规则](https://github.com/CQULzz/HT_Explo/blob/main/docs/REPOSITORY_GUIDE.md)

早期历史目录只关联到研究阶段，未知测量提交保持待确认；补充回放视频不代表新的导航实验。原有报告、失败记录与全部附件保留。
<!-- repository-catalog-end -->
