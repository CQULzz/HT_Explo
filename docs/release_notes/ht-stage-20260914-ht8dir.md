# 阶段01：八方向HT软代价初版

**状态：实验里程碑，不是稳定版；尚未完成实车完整验证。**

归档提交：[46f9642](https://github.com/CQULzz/HT_Explo/commit/46f9642221ff7e251e601818a45fe041831b928c)。类型：功能。
实际控制/功能来源：[46f9642](https://github.com/CQULzz/HT_Explo/commit/46f9642221ff7e251e601818a45fe041831b928c)。

## 改了什么

将HT八方向概率接入有向边代价、最短路与局部TSP；保留TARE覆盖采样和全局引导。

## 实现了什么功能

按边的移动方向计算长度、风险和未知长度代价，输出经检查的短航点。

## 实验与验证

初始归档以本地核心检查为主；后续Jazzy构建发现包识别、OR-Tools和起点停滞问题。

## 存在什么问题

低概率仍可能被选中；没有真实XYθ状态搜索、车体朝向连续性或真实HT闭环部署证明。

## 报告与代码

- [release_manifest.json](https://github.com/CQULzz/HT_Explo/blob/codex/ht8dir-v1/release_manifest.json)
- [VALIDATION.md](https://github.com/CQULzz/HT_Explo/blob/codex/ht8dir-v1/VALIDATION.md)
- [全部版本对照](https://github.com/CQULzz/HT_Explo/blob/codex/ht8dir-v1/VERSIONS.md#stage-01)
- [该阶段源码](https://github.com/CQULzz/HT_Explo/tree/46f9642221ff7e251e601818a45fe041831b928c)
