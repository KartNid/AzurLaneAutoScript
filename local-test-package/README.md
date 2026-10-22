# Alas 1440P 预发布包

本包包含本次 1440P 改造的完整源码、资源、测试和 Windows ADB，并已合并上游最新修改。
源代码提交：`2a2eff18c03830bb35102687bd4728d5b125db6d`
上游 master：`4d88c22d875de3192f8cae2f993e4fe0593114e0`

## 在当前电脑上验证

1. 解压到新目录，不要覆盖 `L:\000\AzurLaneAutoScript`。
2. 启动模拟器，唤醒屏保/锁屏，进入游戏主页并暂停已有 Alas 自动任务。
3. 双击 `run-local-test.cmd`。默认连接 `127.0.0.1:16448`，借用已有的
   `L:\000\AzurLaneAutoScript\toolkit\python.exe`；找不到时会提示输入安装目录。
4. 将本解压目录 `log\resolution_probe\时间戳\resolution-report.zip` 发回对话。

验证入口只读取截图与识别结果，不会启动刷图任务或发送点击、滑动。
本包提供完整应用源码，但不包含 Python 解释器和第三方 Python 依赖，不能视为自带运行环境的一键安装包。
需要运行完整 Alas 时，请按照项目安装文档配置运行环境，并参照 `doc/Resolution.md` 设置分辨率。
使用本分支时应关闭自动更新，避免更新器切回上游 720P 版本。

## 验证范围

合并后测试：1467 项通过、8 项跳过；跳过原因是上游未提供海岛兑换测试所需截图。
1440P 相关自动测试全部通过；离线 720P/1440P 识别经过验证。
此前模拟器报告确认 2560×1440 截图及缩放正常，但当时画面停在屏保/锁屏，主页识别、OCR
和真实点击、滑动等仍待实机验证，因此本版本作为预发布提供。

`SOURCE_MANIFEST.json` 记录源提交与文件校验信息。`tools/platform-tools/ORIGIN.json`
记录 Windows ADB 的 Android 官方来源与校验值。本包未包含账号配置、密钥或用户报告。
