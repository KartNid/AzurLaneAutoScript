# Alas 1440P 外置插件 0.1.0

在原版 720P Alas 上加载 2560×1440 兼容层，保留 1280×720 支持。
原版源码、启动器、游戏资源和在线更新继续由上游管理；插件独立安装、停用和卸载。

原版没有通用设备插件 API。此插件通过 Python 的 `.pth` 启动入口注册导入适配器，
在内存中加载 1440P 兼容逻辑。安装位置为所选 Python 环境的 `site-packages`，
原版 Git 跟踪的文件保持不变。

## 安装

1. 准备一份**原版 Alas**。可使用上游的 [官方安装包](https://github.com/LmeSzinc/AzurLaneAutoScript/releases/tag/v2026.10.09)，
   先运行原版 `Alas.exe` 完成安装和在线更新，再退出 Alas。
   安装步骤参见上游 [安装 Wiki](https://github.com/LmeSzinc/AzurLaneAutoScript/wiki/Installation_cn)。
2. 解压本插件，双击 `install-plugin.cmd`，输入原版 Alas 的目录。
   插件会使用该目录的 `toolkit\python.exe` 安装并检查启动加载能力。
3. 将模拟器设置为 1280×720 或 2560×1440，继续通过**原版 `Alas.exe`** 启动。
   成功加载时会输出 `[Alas 1440P plugin 0.1.0] active`。

也可以在命令行安装：

```powershell
& 'D:\Alas\toolkit\python.exe' 'D:\Alas1440PPlugin\install.py' --alas 'D:\Alas'
```

手动部署的用户应使用实际运行 Alas 的 Python 执行 `install.py`。
安装器会检查兼容性和 `.pth` 加载；失败时回滚本次插件安装。

请在原版安装上使用本插件。已经包含 `module/device/resolution.py` 的旧 1440P 修改版会被拒绝，
以免重复缩放。插件不会替你切换 Git 分支、重置源码或迁移旧实例配置。
同一个 Python 环境可以登记多份原版 Alas；移动安装目录后需要重新运行安装器登记新路径。

## 在线更新

保持原版 `config/deploy.yaml` 的仓库、分支和自动更新设置，例如官方 GitHub 仓库或官方 CDN、
`Branch: master`、`AutoUpdate: true`。插件安装器不修改这些设置。

更新流程仍为：`Alas.exe` → 原版安装/更新器 → 原版桌面端 → Python 主进程及任务进程。
每个 Python 进程都会重新注册插件；第一次导入相关设备模块时检查适配点。
原版 `git reset --hard` 不会覆盖 `site-packages` 中的插件。

上游修改任务、资源以及未适配的函数时，使用更新后的代码。
上游改动插件依赖的方法时，插件会报出 `CompatibilityError`，要求更新插件；
对相关方法的结构检查不能保证所有未来上游变化都兼容。

可在原版目录中检查状态和接口兼容性：

```powershell
.\toolkit\python.exe -m alas_1440p status
.\toolkit\python.exe -m alas_1440p check --alas .
```

## 停用与卸载

退出所有 Alas 进程后，可暂时停用插件：

```powershell
.\toolkit\python.exe -m alas_1440p disable
# 恢复时执行：
.\toolkit\python.exe -m alas_1440p enable
```

完全卸载请双击 `uninstall-plugin.cmd` 并输入同一原版目录。
停用或卸载后重新启动，并将模拟器设置回原版支持的 1280×720。
停用命令作用于该 Python 环境中登记的所有实例；卸载器可单独移除指定目录的登记。

## 兼容逻辑与诊断

截图经方向校正后缩放到 1280×720，原版识别、OCR 与地图算法使用同一识别坐标系；
点击、长按、滑动、拖拽及多点触控在设备后端映射回实际分辨率。
覆盖 ADB、uiautomator2、minitouch、MaaTouch、Hermit、scrcpy 和 nemu_ipc 输入，
包含 DroidCast_raw 原始帧、Android 控件树与后宅持续按压的适配。

插件迁移了已有 1440P 逻辑。插件化解决更新与部署耦合，
**现有识别失败和部分关卡控制异常仍需具体关卡、截图、日志和控制后端来定位**。
本版本是验证版，尚未完成 Windows 和模拟器实机验收。

通用商店识别、主线周回/自律异常的本地调试，可将
[本地调试提示词](LOCAL_DEBUG_PROMPT.zh-CN.md)交给本地 Codex 窗口继续取证和修复。

可在原版目录中采集只读识别报告：

```powershell
.\toolkit\python.exe -m alas_1440p probe --serial 127.0.0.1:16448
```

请将序列号替换成你的模拟器序列号。脚本保存原始截图、归一化截图和识别标注，
报告位于 `log/resolution_probe`。它不会发送点击、滑动或启动游戏任务。
报告含游戏画面，分享前可自行检查内容。

## 开发与验证

适配基线为上游 `master@4d88c22d875de3192f8cae2f993e4fe0593114e0`；
兼容逻辑来自原 `feature/1440p-support@2efcbcb4d07bcff5798e577e9f26c4d6d30dc6a4`。
`alas_1440p/patches.json` 保存 16 个模块、47 处适配的结构校验和代码。
加载器仅改写内存中的语法树，不覆盖上游文件或缓存修改后的 `.pyc`。

使用已有 Alas 测试环境运行：

```bash
ALAS_PLUGIN_TEST_ROOT=/path/to/official/Alas python -m pytest tests /path/to/official/Alas/tests -q
```

构建适配清单需要 Python 3.9+ 及同时包含两个源提交的 Git 仓库：

```bash
python tools/generate_manifest.py --repo /path/to/AzurLaneAutoScript
```

当前验证：1472 passed、8 skipped；详情见 `VALIDATION.md`。
插件及衍生代码遵循仓库的 GPL-3.0 许可，见 `LICENSE`。
