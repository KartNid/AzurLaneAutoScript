# 验证记录

验证日期：2026-10-23。

## 0.1.1 Windows 实机修复

- 原版源码：`4d88c22d875de3192f8cae2f993e4fe0593114e0`，目标 Python 3.7.6。
- 国服，MuMu12 实例4，Android 物理尺寸1440×2560，横屏原图2560×1440，DPI 360。
- 实际后端：`nemu_ipc` 截图、`minitouch` 控制；同时保存 ADB 原始帧作对照。
- 商店 `NAV_GENERAL` 原模板 RGB 匹配为0.843655（阈值0.85），位置偏移为0；
  ADB和nemu_ipc结果一致。顶部军火标签匹配0.979945，7件未售商品的名称、货币与价格正确。
- 关卡准备 `CLEAR_MODE_TITLE` 原模板匹配0.779545，导致 `SwitchClearMode.get()` 返回unknown；
  `map_has_clear_mode=False` 继而关闭内部自律寻敌状态。真实失败帧在修复前稳定失败。
- 新增两个局部模板，只允许已知原生1440P尺寸、国服、原按钮区域和名称；
  保留原模板优先、0.85阈值、原搜索范围、按钮偏移、解锁条件及独立配置项。
- 实机完成周回ON→OFF→ON、自律寻敌OFF→ON。ON青色计数97，OFF白色计数617，
  自律寻敌ON绿色计数72；原颜色阈值分别为50、200、50，未修改。
- 使用原版Alas.exe重新启动主线图2，日志确认clear_mode、Auto_Search on、
  is_auto_search_running、Auto search moving和Auto search combat loading；用户确认已自动寻敌。
- 安装后用同一实际后端完成补给商店→月度商店→补给商店，识别恢复为NAV_GENERAL/TAB_GENERAL；
  只发出两个导航点击，购买次数0，配置文件哈希不变。
- 安装后验证真实主进程及multiprocessing spawn子进程均加载0.1.1与两处新适配。
- 14个真实画面回归，包含未选/已选开关、错误页面、关卡条件不足、独立设置和720P保留原模板。
- 插件与上游测试合并：**1486 passed、8 skipped**。测试依赖隔离到工作区，未升级原版依赖。
- Windows 3.7隔离venv中的spawn会回到base解释器；生命周期测试在此环境使用普通新子进程，
  实际Alas解释器的spawn已另外实测通过，未修改生产环境multiprocessing行为。
- 原版Git跟踪文件保持不变，更新器设置未修改。

## 2026-10-24 日常与活动图实机验证

- 同一国服1440P环境完成本批到期日常；主线按用户设定的石油下限停止。
  小游戏由原版因客户端补丁条件跳过，不计为已执行覆盖。
- `event_20261022_cn` 从T1依次开荒至T6，各关均达到 `100_percent_clear`。
  01:03:36日志同时记录 `Stage T6 cannot increase`、
  `Event.Scheduler.Enable=False` 和 `Reach condition: 100_percent_clear`。
  已验证上下篇切换、关卡递进、海图寻路、交火自律和结算，未自动运行SP。
- 开荒保持 `UseClearMode=false`、`UseAutoSearch=false`，两支舰队均为 `combat_auto`。
  三个选项各自独立；未强制开启周回或海图自律寻敌。
- 启动时的连接重置已定位到旧ADB29.0.6的 `fdevent.cpp:96` 断言崩溃，
  属于主机服务问题；原版日志中的代理提示不足以证明代理是原因。
- 经用户确认其他模拟器任务停止后，单独部署MuMu自带ADB36.0.0及匹配DLL，
  重启5037共享服务，验证实际进程路径、100次属性读取、2560×1440截图和
  原版Alas连接类/adbutils访问均通过。游戏任务配置哈希未变。
  此服务升级不属于插件代码补丁；部署与回滚说明见 [ADB_RECOVERY.zh-CN.md](ADB_RECOVERY.zh-CN.md)。
  长期稳定性仍需后续使用观察，不将一次验证视为永久消除崩溃的证明。

## 0.1.0 历史验证

以下记录属于0.1.0的Linux验证，不代表0.1.1已覆盖所有模拟器、区服和关卡。

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
