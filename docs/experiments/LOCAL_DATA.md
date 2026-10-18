# 本地原始记录的无损归档

完整原始记录已经发布并核对GitHub Release附件大小和SHA256。为满足后续实验磁盘门槛，部分旧轮的本地原始目录完整压缩为presentations/local_raw_archives下的tar.gz；每个普通文件、字节数、SHA256以及内部符号链接逐项核对，全部通过后才移除未压缩副本。报告、对比图和可直接播放的MP4仍在docs/results中。

[完整索引](local_raw_archives.json)包含原路径、压缩包SHA256、逐文件清单与GitHub备份地址。不是删除唯一原始记录：本地压缩包保留全部原始文件，GitHub同时保留独立完整附件。阶段27已经实际执行“压缩→完整还原→逐文件校验→再次收起”，验证往返一致；阶段28也已完整解压流校验。

需要对旧轮跑离线分析时，先还原对应目录：

```bash
python3 scripts/archive_verified_ht_raw.py restore docs/experiments/publications/stage27.json
```

分析完收起：

```bash
python3 scripts/archive_verified_ht_raw.py archive docs/experiments/publications/stage27.json
```

每次收起前会重新检查所有已发布附件的远端大小/摘要、测量提交与本地完整清单；目录若有新文件或内容变化会拒绝使用旧压缩包收起。还原到原来同一工作区绝对路径，避免内部符号链接指向其他位置。正在测量、录包、发布或分析中的目录不能收起；工具只处理工作区自建ht_实验目录。

压缩包在.gitignore排除，完整数据从Release或本地压缩包获取，不写入Git大文件历史。
