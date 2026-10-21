# 阶段28｜执行几何与跟踪余量：本轮内部完成并返航

## 改了什么

控制器可靠订阅同一collision_cloud，按规划器基础物理半径与高度检查实际位姿、前1m路线和指令圆弧；场景参数显式传给控制器。几何过期/错误坐标系/重叠发全零Twist，反馈带原计划身份。名义平移和目标点额外预留0.12m跟踪余量，实际根状态和原地转向保留既有边界；不放行碰撞根状态，不改HT阈值/时效、速度或搜索预算。

## 实现了什么功能

补齐规划检查几何+HT、执行只检查HT的接口差异。16项控制器ROS回归及全部4个CTest目标通过，包含HT允许而几何拒绝实际指令圆弧时真正发全零Twist。0.12m对应现有到达容差，未证明是跟踪误差上界，可能限制窄通道。

## 实验与验证

实测65efef7，室内同起点完整600秒117.66m/2292.750m³，约272秒触发内部探索结束、352.425秒完成返航，终点距起点0.228m。最终COMPLETED，后段平线是返航完成停车。本轮307份录制几何样本未见既有安全边界重叠；新增几何拒绝分支0次，不把效果单独归功于执行拦截，规划余量与轨迹也变了。

比阶段27的41.9m/815.625m³恢复，但体积仍低于阶段23的3170.5m³约27.7%。13项采集检查、9000帧600秒视频完整解码通过；3次晚HT拒绝均配对全零。58份模型上下文同源图逐值一致、三份权重重放差0。

[报告、四轮对比、数据与视频](https://github.com/CQULzz/HT_Explo/blob/codex/ht8dir-v1/docs/results/ht_execution_geometry_10min_2026-10-18/REPORT.md)。附件含整轮录包、周期地图、神经上下文、CSV、外部冻结源码、精选结果和独立MP4；激光源秒抽样，不是全传感器无损数据。

## 存在什么问题

内部完成不等于场景真值已全部覆盖：完成前全局/局部待探索计数归零，需逐单元核查COVERED转移与重复/多环境验证。体积未超过最好历史轮；HT年龄健康抽样最大3.563s，runtime P95约1.433s。新增几何执行分支闭环未触发，只有回归覆盖；未知动态地形、窄通道、完整动力学和实车均未验收。不标为稳定版。

<!-- repository-catalog-start -->
## 代码、视频与完整数据的对应关系

- [阶段28完整索引：实际实验候选、导航代码、报告、视频及数据回执](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/catalog/stage-28.md)
- [本阶段归档源码](https://github.com/CQULzz/HT_Explo/tree/65efef749493fdfac0960f7b98013ec666d4efff)：`65efef749493fdfac0960f7b98013ec666d4efff`。这是归档锚点；实际测量源码、运行patch与二进制哈希以原清单为准。
- [完整实验总目录](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/catalog/INDEX.md) · [分支和标签规则](https://github.com/CQULzz/HT_Explo/blob/main/docs/REPOSITORY_GUIDE.md)

早期历史目录只关联到研究阶段，未知测量提交保持待确认；补充回放视频不代表新的导航实验。原有报告、失败记录与全部附件保留。
<!-- repository-catalog-end -->
