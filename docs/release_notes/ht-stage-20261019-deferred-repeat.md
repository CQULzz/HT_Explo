# 阶段32｜相同导航程序复测，早期长期停滞

## 改了什么

导航行为没有变化，继续使用阶段31的b05ed9e程序；实测提交867ba1f仅增加文档、发布回执和播放入口。63份源码/配置/二进制/权重哈希一致，实际参数逐项对照保存在报告。此前清理pip HTTP缓存后可用磁盘增加，是环境差异，不能作单变量因果归因。

## 实现了什么功能

补齐完整600秒重复验证和逐周期恢复目标调度审计。明确区分采集通过与探索稳定，不掩盖失败复测。

## 实验与验证

室内完整600秒，5.66m、419.750m³；最后平移指令14.002秒，最长全零586.040秒，末分钟0m，最终BLOCKED。原阶段31为162.71m/2703.875m³，同源码结果差异很大，尚不稳定。

482轮在有排队替代目标时只尝试主要目标并全部超时、未尝试恢复目标；60秒后489轮中482轮符合，另外7轮曾尝试恢复目标。主要目标常占完0.35秒预算；不能以此证明恢复目标本身可达。13项采集检查通过，视频9000帧600秒完整解码；601个源秒扫描、跳过0，按同一时间窗口/采样规则计算，非全部原始激光。

[完整失败报告、三轮对比与视频](https://github.com/CQULzz/HT_Explo/blob/codex/ht8dir-v1/docs/results/ht_deferred_gain_repeat_10min_2026-10-19/REPORT.md)。附件保存全部已录制原始数据、CSV、日志、周期图、模型上下文、精选报告及独立MP4。

## 存在什么问题

长时间重复主要目标超时，普通恢复目标缺少预算保障。下一候选优先改调度并验证，不放宽HT/物理几何或提高总预算。搜索性能、地图时效、不可达任务、覆盖真值、其他环境与实车仍未验收。本轮不是稳定版本。

<!-- repository-catalog-start -->
## 代码、视频与完整数据的对应关系

- [阶段32完整索引：实际实验候选、导航代码、报告、视频及数据回执](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/catalog/stage-32.md)
- [本阶段归档源码](https://github.com/CQULzz/HT_Explo/tree/867ba1f5d40c813291bbb148fad2d5fc5b8907d1)：`867ba1f5d40c813291bbb148fad2d5fc5b8907d1`。这是归档锚点；实际测量源码、运行patch与二进制哈希以原清单为准。
- [完整实验总目录](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/catalog/INDEX.md) · [分支和标签规则](https://github.com/CQULzz/HT_Explo/blob/main/docs/REPOSITORY_GUIDE.md)

早期历史目录只关联到研究阶段，未知测量提交保持待确认；补充回放视频不代表新的导航实验。原有报告、失败记录与全部附件保留。
<!-- repository-catalog-end -->
