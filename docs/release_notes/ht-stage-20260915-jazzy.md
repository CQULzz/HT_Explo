# 阶段02：Jazzy编译与起点停滞修复

**状态：实验里程碑，不是稳定版；尚未完成实车完整验证。**

归档提交：[c4b7a41](https://github.com/CQULzz/HT_Explo/commit/c4b7a41d3ae3466c8b5eb043c8f1f3f81b3c9e8d)。类型：功能。
实际控制/功能来源：[c4b7a41](https://github.com/CQULzz/HT_Explo/commit/c4b7a41d3ae3466c8b5eb043c8f1f3f81b3c9e8d)。

## 改了什么

修复包识别、Eigen/GridMap与OR-Tools依赖；跳过过近的起始锚点，补输入校验及故障注入工具。

## 实现了什么功能

可在CMU Garage闭环移动，异常地图输入能停车并恢复。

## 实验与验证

约135秒故障注入试跑行驶40.56米；41项核心、9项ROS检查通过。

## 存在什么问题

使用合成八方向地图，未运行真实HT网络；仍是软代价与旧控制链路，未完成全域探索。

## 报告与代码

- [VALIDATION.md](https://github.com/CQULzz/HT_Explo/blob/codex/ht8dir-v1/VALIDATION.md)
- [全部版本对照](https://github.com/CQULzz/HT_Explo/blob/codex/ht8dir-v1/VERSIONS.md#stage-02)
- [该阶段源码](https://github.com/CQULzz/HT_Explo/tree/c4b7a41d3ae3466c8b5eb043c8f1f3f81b3c9e8d)
