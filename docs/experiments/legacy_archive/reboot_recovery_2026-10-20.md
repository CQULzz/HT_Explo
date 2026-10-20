# 重启中断后的恢复记录

本轮继续工作时，系统启动时间约135秒，原临时日志与上传进程已不存在。62个源目录和46份完整发布回执仍在；不是63.405 GiB全部上传完成。

## Git元数据

发现27个零字节对象，包含本地HEAD `64b6e8668d7e9a206e14eef4fde0018950921067`。先将空对象和HEAD/索引/分支引用备份到 `.git/recovery/20261020-143704`，再用GitHub上已存在的同一提交执行 `git fetch --refetch origin codex/ht8dir-v1` 补齐对象。`git fsck --full --no-reflogs` 返回0，只剩正常的dangling对象提示，没有缺失对象或坏引用；工作区没有reset/checkout覆盖，实验源目录没有删除。

这证明发现了重启后的损坏并完成恢复；不能单凭这些现象断言重启或断电的具体原因。

## 后台续传

新增 `scripts/run_legacy_ht_archive.sh`，使用已存GitHub登录，预检认证后再进行大目录打包、续传和最终核验。`ht-legacy-archive.service` 为用户服务，启用为登录后启动；重启后可续传。日志保存在 `.git/legacy-archive-runtime/service.log`，完整发布并推送后写COMPLETE标记，避免完成后每次登录重复上传。

后台服务最多并发3个分卷，总暂存上限1.5 GiB；只有完整数据、清单与所有分卷核验通过才写目录发布回执。不覆盖同名不同内容，不删除源实验目录。

## 认证边界

本次检测到GitHub CLI凭据仍存放在锁定的系统钥匙串中，因此API上传返回401。SSH拉取/推送和Release资产上传使用不同认证，不能用SSH成功推断Release可上传。已通过系统Secret Service打开解锁流程；密码在系统窗口输入，不通过聊天接收。不把钥匙串秘密写进仓库、日志或明文环境文件。钥匙串在以后重启登录时若仍锁住，后台服务每30秒检查一次，完成系统解锁后自动续传，不再重复打包或反复请求未认证上传。用户服务可用 `python3 scripts/install_legacy_ht_archive_service.py --start` 安装与启动。
