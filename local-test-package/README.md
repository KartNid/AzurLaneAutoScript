# 本地 1440P 只读验证包

1. 将本 ZIP 解压到一个新目录；不要覆盖 `L:\000\AzurLaneAutoScript`。
2. 启动模拟器，将游戏停留在主页。验证目标是 `127.0.0.1:16448`；请先暂停现有 Alas 自动任务，避免检测过程中画面自行切换。
3. 双击解压目录中的 `run-local-test.cmd`。

脚本已预设借用 `L:\000\AzurLaneAutoScript\toolkit\python.exe`。如果该文件不存在，会提示输入包含 `toolkit\python.exe` 的 Alas 目录。Python 依赖来自已有 Alas；本包不安装或覆盖该目录，也不启动 GUI、刷图或更新器。

报告生成在本解压目录的 `log\resolution_probe\时间戳\resolution-report.zip`。请将这个报告 ZIP 发回当前对话，便于核对截图、页面识别及 OCR 读数。

这是只读验证：不发送点击、滑动或游戏任务，不安装模拟器内应用，不改变模拟器分辨率。输入坐标会计算并标注在截图上，尚未实际注入，因此不能据此声称点击、拖拽等操作已完成实机验证。

本包包含本次修改的完整源码、资源、测试以及经 Android 官方仓库校验的 Windows ADB。未包含你的账号配置、Git 凭据、云端 Python 虚拟环境或其他私人文件。`SOURCE_MANIFEST.json` 记录文件校验信息，`tools/platform-tools/ORIGIN.json` 记录 ADB 官方来源与校验值。

当前对话仅有云端执行能力，尚未在你的 Windows 上执行此包。源码验证、离线截图验证和失败诊断流程已在云端测试；Windows 启动脚本与实际模拟器连接仍需本地运行。

如果使用 EN/JP/TW 服务，可在 PowerShell 中指定：

```powershell
& 'L:\000\AzurLaneAutoScript\toolkit\python.exe' '.\dev_tools\resolution_probe.py' --adb '.\tools\platform-tools\adb.exe' --serial 127.0.0.1:16448 --server en
```
