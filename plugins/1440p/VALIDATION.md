# 验证记录

验证日期：2026-10-23。

## 上游参照

- [安装 Wiki](https://github.com/LmeSzinc/AzurLaneAutoScript/wiki/Installation_cn)：
  原版通过 `Alas.exe` 在启动时执行在线更新；直接启动桌面端会绕过该更新步骤。
- [上游源码](https://github.com/LmeSzinc/AzurLaneAutoScript/tree/4d88c22d875de3192f8cae2f993e4fe0593114e0)：
  `deploy/git.py` 采用 fetch、reset --hard、pull；`gui.py`、任务进程和 OCR 服务使用 Python 多进程。
- [官方 Easy Install v0.4.13](https://github.com/LmeSzinc/AzurLaneAutoScript/releases/tag/v2026.10.09)：
  实际下载并检查 `AlasApp_0.4.13_full.7z`，大小 289112550 字节。
  SHA256 与 GitHub 附件 digest 一致：
  `54e33f2172079cdeab404d788a968c68eece090fb3c43aaab8263c5592e6e06b`。

官方安装包内含 `toolkit/Lib/site.py` 及已有 `.pth` 文件，未包含禁用标准路径的 `python*._pth`。
检查了 `console.bat`、`config/deploy.yaml`、site 路径与 `.pth` 处理逻辑；保留原版启动入口和配置。
本次未在 Windows 上执行官方安装包。

## 自动验证

在 Linux Python 3.7.16 项目依赖环境，以**未修改的上游源码**加载插件：

- 既有 720P/1440P 截图、旋转、模板、OCR 调用、地图、控件树及各控制后端回归：140 项通过。
- 新增插件检查：不修改源文件、保留上游新增功能、接口变更时中止加载、拒绝重复适配、
  原版更新器保持启用，以及完整安装/重装/子进程/模拟更新/停用/恢复/卸载流程。
- 通过独立 Python 虚拟环境的真实 `.pth` 启动，使用 `multiprocessing` 的 `spawn` 模式检查子进程。
- 在隔离源码仓库执行 `git reset --hard HEAD` 后，插件仍能加载；卸载后新进程找不到插件。
- 与上游完整测试合并执行：**1472 passed、8 skipped**。8 项跳过为上游未提供截图的海岛兑换测试。
- Python 3.7 与当前构建解释器均通过 16 个模块的接口及语法检查。
- 上游测试工作树的 Git 跟踪文件没有改动。
- 最终 ZIP 解压后完成逐文件校验、安装和 CLI 诊断：2560×1440 合成主页图归一化为
  1280×720，并识别为 `page_main`。未注入设备操作，也未执行真实 OCR。
- 从该 ZIP 安装后再次卸载，重新导入原版 ADB 类，确认恢复原版函数签名且不含插件坐标转换方法。

## 尚需实机验证

Windows 官方 Python 下安装、原版启动器和实际在线更新；游戏主页识别、OCR、
出现异常的关卡及其截图/控制后端。以上自动测试不代表这些问题已经修复。
