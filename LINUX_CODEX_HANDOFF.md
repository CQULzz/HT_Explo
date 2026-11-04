# Linux Codex 交付状态同步

用户要求同步 Windows 端已完成的交付，请阅读并只确认收到，不要自动重跑仿真或重复上传。

原聊天「排查车辆移动后停止问题」中因 usage_limit_exceeded 中断的600秒PCD仿真实验及GitHub交付，现已由 Windows 端从物理双系统 Linux ext4 分区只读恢复产物并补完发布。

Release 已正式发布（非草稿，实验预发布）：https://github.com/CQULzz/HT_Explo/releases/tag/ht-scout-pcd-fix-20261105-v1 。共38个附件、13,934,846,663字节，37项证据附件和PUBLICATION_RECEIPT.json本身均核对GitHub文件大小与SHA-256；12个原有MCAP全部包含，含失败/部分采集。回执SHA-256：d12a772b9ce34241196dfff4a63a5aa19f42a30dcc4ca21180cbf6763ea77158。

测试代码/标签仍固定53fcb471ee9b36bf238355d530a9f00d02a6ab14；分支fix/scout-navigation-pcd-20261105的交付提交为b317cc3d2fe50fd3097a09bb6ef9dcaf025439ee。该提交增加docs/results/scout_pcd_navigation_20261105/PUBLICATION_RECEIPT.json及DELIVERY.md、README发布链接，并修复发布脚本对草稿Release查询404及回执重复上传的问题。

本轮原有600.3秒仿真完整，43.62m累计里程，151次进入的局部搜索全部REACHED。但探索任务未完成：场景裁剪边界、图龄停车与采集结束后的mapper强制清理问题保留，不能声称实车验收或所有停车已解决。此次只恢复与发布，没有重跑仿真、更改测试导航源码/参数或修改Linux分区；Linux本地工作树尚未fetch远端交付提交。

后续先读取远端DELIVERY.md及PUBLICATION_RECEIPT.json；若需要更新本地分支，先检查git status并保留未提交修改，再fetch/ff-only。发布交付已完成，按原要求停止，不开启新候选或新场景。

