# Alas 1440P Windows x64 编译包

源码分支：[`feature/1440p-support`](https://github.com/KartNid/AzurLaneAutoScript/tree/feature/1440p-support)
源码提交：`2efcbcb4d07bcff5798e577e9f26c4d6d30dc6a4`

下载以下两个 ZIP，并将它们解压到**同一个目标目录**。
两者都包含共同的顶层目录 `Alas-1440P-Windows-x64`，应将内容合并到这一个目录中。

- [源码、资源与启动脚本](./Alas-1440P-Source-and-Launcher-20261023.zip)
- [编译后的 Windows x64 桌面程序](./Alas-1440P-Desktop-Windows-x64-20261023.zip)
- [SHA256 校验文件](./SHA256SUMS.txt)
- [运行说明](./START-HERE.md)

在同一下载目录中也可以使用 PowerShell 解压：

```powershell
Expand-Archive .\Alas-1440P-Source-and-Launcher-20261023.zip -DestinationPath .\Alas1440P
Expand-Archive .\Alas-1440P-Desktop-Windows-x64-20261023.zip -DestinationPath .\Alas1440P -Force
```

解压后双击 `Alas1440P\Alas-1440P-Windows-x64\run-Alas.cmd`，
按提示选择已有 Alas 安装目录，提供其中的 Python 解释器与依赖。
本包支持 1280×720 与 2560×1440，完整测试结果为 1467 passed、8 skipped。
Windows 实际启动和模拟器操作尚需实机验证，作为预发布提供。

此分支仅用于提供二进制下载。源码分支未改动。
由于当前云端认证访问 GitHub Release 附件上传端点返回 401，Release 说明通过固定提交链接提供这些文件。
