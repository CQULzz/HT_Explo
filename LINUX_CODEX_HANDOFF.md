# 最新交接：循环4可选建图调度，尚未运行仿真

先读docs/results/wsl_offline_cycle4_20261105/REPORT.md。runtime已准备single地图执行器+独立TF接收候选，runner显式--mapper-executor single选择，默认multi不变；20项离线检查通过，三对合成调度负载CPU约下降63%、处理量相近。这不是地图源龄闭环验收，用户仍要求暂不启动仿真；禁止自动开启。补丁/installer验证wrapper/helper SHA，不覆盖未知CuPy差异。不发布Release或硬件部署，旧原始数据继续保留。此文件需离线Linux拉取后阅读。

---

# 最新交接：循环3离线候选，禁止自动启动仿真

用户明确要求先诊断和改代码，暂不运行仿真。本轮只读取cycle2数据、修复剩余收益抽样对原队列的3处误用、补充反例并通过完整9组CTest；没有新的120秒成绩，不能称已闭环验收。先读docs/results/wsl_offline_cycle3_20261105/REPORT.md和PROVENANCE.json。地图上游延迟、前沿继续选择门限及几何阻塞仍待解决；旧仿真结果不适用于当前候选。仅代码/精简记录推送，不发布Release或部署。原Linux聊天不会自动收到交接，需拉取本分支阅读。

---

# 最新交接：2026-11-05 循环2完成判据优化

本轮8次×120秒预算已耗尽，停止。先读docs/results/wsl120_cycle2_20261105/STATUS.md；最终实测0ba80ed722c0dd5aa3c53d005d27c3f7f2c3203d，分支fix/scout-wsl120-20261105。保留40/15边界完成修复与种子入口，队列候选因源龄硬约束失败已撤回，原始数据在WSL cycle2保留。按最新用户要求本轮只推送精简Git记录，不发布Release或部署；这一要求覆盖下方旧交接的逐轮Release要求。未声称全局验收通过，未经新预算授权不得续跑。

---

# 最新交接：2026-11-05 WSL两分钟迭代

原Linux Codex聊天 `01a1a5cc-f846-7723-8735-190876a2c2f5` 的用户/助手历史与PROJECT_HANDOFF已完整通读；原始日志/实验数据保持只读。当前执行环境是用户新授权的WSL Ubuntu-24.04/Jazzy，不是把双系统日志误当WSL日志。

继续前请先读 `docs/results/wsl120_20261105/STATUS.md` 与 `docs/experiments/ITERATIONS.md`。最新实测代码8e06489fe3fabed32cda97239ca7c713e50586cf，分支fix/scout-wsl120-20261105，两个无采样正式复测标签r06/r07均指向它；后续文档提交不是新候选。

每轮完整120秒（不再600秒），冻结/保留坏数据/先发布核验再下一候选。显式`--ht-processing-mode worker`已重复验证降低HT延迟：215→64ms，地图发布源龄0.965→0.55–0.58s，严格1秒门限不变；两次内部返航完成，但TARE覆盖/早返航判据尚需独立验真，不能称全场景探索或实车通过。

WSL工程 `/home/w_lzz/ht-iterations-20261105/repo`，独立运行文件在其同级runtime；`/home/lzz/...`兼容路径是WSL内链接，不是原双系统Linux目录。CuPy核心为固定私有上游+公共稳定补丁重建，原Linux定制核心不可盲覆盖。两个优化安装器检查前后SHA256，不匹配就保留本地差异、单独移植；权重/概率/未知/时效/足迹/TARE顺序均不可放宽。实车默认旧执行器，未部署设备。

最新完整数据：https://github.com/CQULzz/HT_Explo/releases/tag/ht-wsl120-worker-repeat-20261105-r07 ，当前HT安装产物在r06，场景模型在r00。r00–r07含坏结果均已发布并校验SHA256/大小，报告有逐项回执。Windows发布辅助程序与配置在D:/HT-Resume，已用当前GitHub账号完成；不要把密码/令牌写进交接。

此文件是持久交接，不会自动注入离线原Linux聊天。原Linux Codex需要拉取/读取该分支后才能获知更新；原始会话JSONL未被伪造或改写。下面保留上一轮交接以便溯源。

---

# Linux Codex 交付状态同步

用户要求同步 Windows 端已完成的交付，请阅读并只确认收到，不要自动重跑仿真或重复上传。

原聊天「排查车辆移动后停止问题」中因 usage_limit_exceeded 中断的600秒PCD仿真实验及GitHub交付，现已由 Windows 端从物理双系统 Linux ext4 分区只读恢复产物并补完发布。

Release 已正式发布（非草稿，实验预发布）：https://github.com/CQULzz/HT_Explo/releases/tag/ht-scout-pcd-fix-20261105-v1 。共38个附件、13,934,846,663字节，37项证据附件和PUBLICATION_RECEIPT.json本身均核对GitHub文件大小与SHA-256；12个原有MCAP全部包含，含失败/部分采集。回执SHA-256：d12a772b9ce34241196dfff4a63a5aa19f42a30dcc4ca21180cbf6763ea77158。

测试代码/标签仍固定53fcb471ee9b36bf238355d530a9f00d02a6ab14；分支fix/scout-navigation-pcd-20261105的交付提交为b317cc3d2fe50fd3097a09bb6ef9dcaf025439ee。该提交增加docs/results/scout_pcd_navigation_20261105/PUBLICATION_RECEIPT.json及DELIVERY.md、README发布链接，并修复发布脚本对草稿Release查询404及回执重复上传的问题。

本轮原有600.3秒仿真完整，43.62m累计里程，151次进入的局部搜索全部REACHED。但探索任务未完成：场景裁剪边界、图龄停车与采集结束后的mapper强制清理问题保留，不能声称实车验收或所有停车已解决。此次只恢复与发布，没有重跑仿真、更改测试导航源码/参数或修改Linux分区；Linux本地工作树尚未fetch远端交付提交。

后续先读取远端DELIVERY.md及PUBLICATION_RECEIPT.json；若需要更新本地分支，先检查git status并保留未提交修改，再fetch/ff-only。发布交付已完成，按原要求停止，不开启新候选或新场景。

