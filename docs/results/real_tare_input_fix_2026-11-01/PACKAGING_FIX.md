# DDS配置安装补丁（r1）

最终安装核对发现，主候选95fa279b中的可选DDS XML已在源码中，但setup.py只安装YAML，构建后share目录缺少XML。补丁只在data_files中加入config/*.xml，已在全新独立colcon安装目录确认XML逐字节一致，安装后的node、launch和标定也与源文件一致。运行算法不变，没有新增行为实验、设备或仿真。

原实验tag real-scout-tare-input-fix-20261101保持95fa279b，不移动；部署源码tag为real-scout-tare-input-fix-20261101-r1。原候选325项Python、8组C++、81帧原点实验和全部传输成功/异常结果原样保留。PACKAGING_CHECK.json核对其余220项冻结源文件一致；确切数量以JSON为准。

完整原始录包、科学归档、图表和视频继续使用[原实验Release](https://github.com/CQULzz/HT_Explo/releases/tag/real-scout-tare-input-fix-20261101)的已验证附件，不重复上传或解压。REUSED_DATA_ASSETS.json逐项记录原附件大小、SHA和下载地址，并在本补丁发布前重新核对远端。r1附件另保存本次安装日志、前后setup.py、差异、安装XML和核验结果。源码与附件确切提交见PACKAGING_RELEASE_RECEIPT.json。

仍有一次正式传输连续9帧缺口，提前完成、完整TARE闭环和ARM吞吐未验收；包装补丁不改变这些结论。
