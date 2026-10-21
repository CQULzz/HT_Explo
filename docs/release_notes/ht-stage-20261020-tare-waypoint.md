## 改了什么

恢复原TARE六个核心函数体与多视点TSP，HT只处理odom到原航点的XYθ路线；保留原航点延伸，同源历史高程替代导航地形。先行计划e2370b0，实测42966cb22b0f719df035391f3850b9a654f161e1。

## 实现了什么功能

TARE访问顺序/原航点/原路线分支/局部目标/实际执行轨迹分别录包。仿真地形输入隔离，原TARE地形话题无发布者。HT无路发零，不替换收益目标。

## 实验与验证

车库完整600秒192.93m、8467.000m³，较39体积+30.6%。13项采集、4项CTest，视频完整解码；原六函数SHA一致，接口违例0。报告、数据、视频和历次多角度图册随附；raw.tar分卷包含本轮全部已录数据，采样传感器范围以报告为准。

## 存在什么问题

XYθ搜索时间上限42次、展开上限38次；最长完全停车0.75s，末60秒新增731.724m³/移动20.80m；末尾EXPLORING。 单次闭环不证明一般优越；没有同运动约束的新原版600秒配对。局部HT/几何采样不是连续安全或独立物理覆盖真值，尚未完成多环境和实车验收。


构造回归另有失败：HT删点后原BFS仍标记另一侧连通/候选，但实际最短路为空。近家rush-home也存在前视无输出时被包装层错误拦住的源条件反例；本轮没有触发返航。

<!-- repository-catalog-start -->
## 代码、视频与完整数据的对应关系

- [阶段40完整索引：实际实验候选、导航代码、报告、视频及数据回执](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/catalog/stage-40.md)
- [本阶段归档源码](https://github.com/CQULzz/HT_Explo/tree/42966cb22b0f719df035391f3850b9a654f161e1)：`42966cb22b0f719df035391f3850b9a654f161e1`。这是归档锚点；实际测量源码、运行patch与二进制哈希以原清单为准。
- [完整实验总目录](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/catalog/INDEX.md) · [分支和标签规则](https://github.com/CQULzz/HT_Explo/blob/main/docs/REPOSITORY_GUIDE.md)

早期历史目录只关联到研究阶段，未知测量提交保持待确认；补充回放视频不代表新的导航实验。原有报告、失败记录与全部附件保留。
<!-- repository-catalog-end -->
