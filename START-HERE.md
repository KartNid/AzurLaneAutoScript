# Alas 1440P Windows x64 预发布

此包基于 `KartNid/AzurLaneAutoScript` 的 `feature/1440p-support` 分支，
提交 `2efcbcb4d07bcff5798e577e9f26c4d6d30dc6a4`。
包含编译后的 Windows x64 Electron 桌面程序、完整 Python 源码、游戏资源、测试和官方 Windows ADB。
Python 解释器和第三方 Python 依赖由已有 Alas 安装提供。

## 启动完整 Alas

1. 将 ZIP 完整解压到新目录。
2. 启动模拟器，选择 1280×720 或 2560×1440，并进入游戏主页。
3. 双击 `run-Alas.cmd`，按提示输入已有 Alas 的安装目录（其中应有 `toolkit\python.exe`）。
   也可以运行 `run-Alas.cmd "已有Alas目录\toolkit\python.exe"`。
4. 在窗口中配置模拟器连接和任务。新包的设置保存在解压目录，已有安装只提供 Python 运行环境。

启动脚本会在本包内生成 `config/deploy.yaml`，指向所选 Python 和本包的 ADB，
并关闭自动更新和定时重启，使程序保持在 1440P 分支。再次启动同样使用 `run-Alas.cmd`。
第一次运行桌面程序前需要先通过此脚本生成配置。

## 分辨率验证

完整说明见 `doc/Resolution.md`。只采集截图和识别报告时可运行
`dev_tools/resolution_probe.bat`，按提示提供已有 Alas 安装目录。

本次源码测试：1467 passed、8 skipped。8 项跳过因上游未提供海岛兑换测试图片。
Windows x64 程序已完成交叉构建和归档检查；Windows 启动、主页 OCR 以及真实设备点击、滑动等仍需实机验证。
本版本标记为预发布。

`RELEASE_MANIFEST.json` 记录源提交、构建版本、依赖锁文件和包内文件的 SHA256。
`build-metadata` 保存本次构建使用的完整 npm 依赖锁文件与打包配置。
