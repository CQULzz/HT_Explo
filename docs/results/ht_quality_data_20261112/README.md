**精简实验数据已上传并校验｜2026-11-12**

首次查看建议先读[交接说明：做了什么、验证结果与不足](HANDOFF.md)，也可[下载同版Markdown附件](https://github.com/CQULzz/HT_Explo/releases/download/ht-quality-data-20261112/HT_QUALITY_HANDOFF_20261112.md)。文档附件的大小/SHA回执见[DOCUMENT_UPLOAD_RECEIPT.json](DOCUMENT_UPLOAD_RECEIPT.json)。

按用户最新要求，本轮不再上传视频，原始大MCAP录包留本机。上传内容为CSV指标、JSON审计、实际参数、地图快照、必要日志和运行冻结证据。两包合计43,493,126字节（约43.5MB），包含802个常规证据文件；**不含原始MCAP或视频，不构成原始录包的完整远端备份**。

[GitHub数据附件](https://github.com/CQULzz/HT_Explo/releases/tag/ht-quality-data-20261112)绑定对应分支提交`9f683e1be84633fdc9c9da7fc9ffc11aef18463a`。3个实验数据附件的远端大小及SHA256均已逐一验证，回执见[REMOTE_RECEIPT.json](REMOTE_RECEIPT.json)，文件范围及包内SHA见[DATA_MANIFEST.json](DATA_MANIFEST.json)。

- [ht_quality_20261111--data-no-video.tar.gz](https://github.com/CQULzz/HT_Explo/releases/download/ht-quality-data-20261112/ht_quality_20261111--data-no-video.tar.gz)：19,874,931字节，远端SHA256已核对。
- [DATA_MANIFEST.json](https://github.com/CQULzz/HT_Explo/releases/download/ht-quality-data-20261112/DATA_MANIFEST.json)：11,177字节，远端SHA256已核对。
- [ht_quality_600s_20261112--data-no-video.tar.gz](https://github.com/CQULzz/HT_Explo/releases/download/ht-quality-data-20261112/ht_quality_600s_20261112--data-no-video.tar.gz)：23,618,195字节，远端SHA256已核对。

可直接浏览[300秒数据](../ht_height_quality_20261111/data/)及[600秒数据](../ht_height_quality_600s_20261112/data/)，包括原始CSV指标、结果与命令审计、运行参数。数据包内保留中断记录及原NUL字节，不把失败首轮当成功；共享依赖仅作索引。旧全量上传计划已取消，旧草稿及传输残留不算完整备份。本机原始数据全部保留，不清理。已有历史视频不重复上传，也不改写Git历史。
