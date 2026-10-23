# Alas 1440P 插件：本地调试提示词

> 历史说明：下文为0.1.0故障交接背景。商店导航和13-4周回标题的1440P识别问题已在
> 0.1.1修复，请以当前源码、实际安装版本和 `VALIDATION.md` 的实机记录为准。

使用方式：在本地 Codex 窗口打开插件源码或原版 Alas 所在的工作区，将下方“提示词正文”到文末的内容完整粘贴过去。路径不必提前填写，让本地助手先确认实际安装位置。若只下载了插件 ZIP，也可以开始取证；涉及完整回归时再准备上游源码和测试依赖。

---

## 提示词正文

请接手 Alas 1440P 外置插件的本地调试，实际复现并修复下述两个问题。先检查当前工作区和运行环境，再动手，不要停在给建议或仅阅读源码。

### 任务背景与现有成果

这是 `LmeSzinc/AzurLaneAutoScript` 的 2560×1440 兼容项目，继续支持 1280×720。此前曾直接修改整个 Alas，现在已迁移为外置 Python 插件，以保留原版的启动器、在线更新和资源更新。

源码仓库：`https://github.com/KartNid/AzurLaneAutoScript`

- 当前开发分支：`feature/1440p-plugin`。
- 最初插件提交：`5e3554402ddf07603a9713f6de02b44fcea592e1`，版本 `0.1.0`。开始时检查是否已有更新，以本地实际版本为准，保留用户已有修改。
- 插件源码：`plugins/1440p/`；安装包：`plugin-package/Alas-1440P-Plugin-0.1.0.zip`。
- 适配基线：上游 `master@4d88c22d875de3192f8cae2f993e4fe0593114e0`。这只是已验证基线，不表示本地必须回退到这个提交。
- 旧整体修改分支：`feature/1440p-support`，提交 `2efcbcb4d07bcff5798e577e9f26c4d6d30dc6a4`，仅用于参考，不作为当前修复主线。
- 上游 Wiki：`https://github.com/LmeSzinc/AzurLaneAutoScript/wiki/Installation_cn`。
- 参考官方安装包：上游 Release `v2026.10.09` 的 `AlasApp_0.4.13_full.7z`，客户端 0.4.13。

云端此前在 Linux Python 3.7.16 环境完成过 1472 项通过、8 项跳过的测试，包括模拟更新、子进程加载及卸载恢复。大部分图像测试使用合成画面或放大的 720P 模板；这些结果不能证明真实 1440P 的商店、关卡和 Windows 启动流程都正常。**下面两个实测故障尚未定位和修复。**

### 用户反馈的两个故障

1. 在“通用商店”界面无法识图。需要区分：商店页面未被识别、导航/标签切换失败、商品图标匹配失败、货币/价格 OCR 失败，还是点击后进入了错误界面。
2. 在“主线图”执行战斗时，即使勾选“使用周回模式”，仍无法进入用户预期的自动战斗。需要确认停留在选关、地图准备、舰队准备、海图自动寻敌，还是战斗中的自动开关。

**务必区分三个独立设置，不要把它们合并成一个布尔开关：**

- `Campaign_UseClearMode`：“使用周回模式”。
- `Campaign_UseAutoSearch`：“使用自律寻敌”。
- `Fleet_Fleet1Mode` / `Fleet_Fleet2Mode`：舰队战斗模式，其中 `combat_auto` 为自律战斗。

只勾选第一项不能证明后两项已启用。但这只是需要检查的条件，不能据此认定用户配置错误。关卡是否解锁、通关进度、开关识别、状态转移和点击坐标也必须核实。

### 第一步：确认运行的到底是哪份代码

先从当前工作区及用户指定目录确认以下三者，路径可能不同：原版 Alas 安装目录、插件开发源码目录、实际运行的 Python 解释器。不要在整块硬盘无目标地扫描。存在多份安装且无法判断时，再向用户问一个简短问题。

Windows 官方安装通常使用 `<原版目录>\toolkit\python.exe`。使用它执行检查，不要误用系统 Python。以下 PowerShell 命令中的路径由你替换为实际值：

```powershell
$alasRoot = 'D:\实际原版Alas目录'
$pluginRoot = 'D:\实际源码目录\plugins\1440p'
$alasPython = Join-Path $alasRoot 'toolkit\python.exe'
Set-Location $alasRoot
& $alasPython -c 'import sys, sysconfig; print(sys.executable); print(sys.version); print(sysconfig.get_path("purelib"))'
& $alasPython -m alas_1440p status
& $alasPython -m alas_1440p check --alas $alasRoot
```

记录插件实际包路径、版本、启用状态、登记的根目录及原版源码提交。检查该解释器是否也是 `config/deploy.yaml` 中原版实际使用的解释器。

插件由 `site-packages/alas_1440p.pth` 在每个 Python 进程启动时注册。`loader.py` 使用导入钩子，按 `patches.json` 的结构校验将适配应用到内存中的 AST；上游源文件不被覆盖。首次加载适配模块时通常输出 `[Alas 1440P plugin 0.1.0] active: ...`。

**修改开发目录不等于更新了实际安装副本。** 改动后应退出本次测试的 Alas 主进程和任务子进程，用目标解释器重新执行开发目录中的安装器，再从原版 `Alas.exe` 启动并验证加载路径。只关闭桌面窗口可能仍有托盘或任务进程存活；只处理已确认属于本次测试安装的进程。

```powershell
& $alasPython (Join-Path $pluginRoot 'install.py') --alas $alasRoot
```

即使源文件路径或 `inspect.getsource()` 看起来是原版，也不能据此断定插件没加载：适配在内存中发生，`get_source()` 返回的仍可能是原版源码。结合模块的 `__alas_1440p_version__`、实际包路径和 `alas_1440p.loader._finder.loaded` 判断。只有导入相关模块后，`loaded` 才会包含它们。

### 第二步：现场复现并保存证据

读取日志、配置中与故障有关的字段、已有截图，以及离线测试可以直接进行。商店复现优先停留在页面读取和识别，不用实际购买来证明识图成功。需要用户把游戏切到特定界面时，给出简短、具体的操作要求。

分别为商店和主线故障记录：时间、游戏区服、模拟器及 Android 分辨率/DPI、实例序列号、截图方式、控制方式、任务/关卡名、最后正常步骤、实际停留界面。序列号从当前任务和 `adb devices` 等确认，不要直接套用旧环境的 `127.0.0.1:16448`。

保存以下证据到独立调试目录：

- 模拟器原始 PNG，确认它确实是 2560×1440。桌面截图不能替代设备原始截图。
- 同一帧经插件处理后的 1280×720 图，以及模板搜索区、匹配框、点击位置标注图。
- 失败前后的日志，保留时间戳、状态切换和按钮名。
- 对应模板的匹配分数、搜索范围、位置偏移；涉及颜色状态时保存颜色计数和阈值，涉及 OCR 时保存实际裁剪及预处理图。
- 仅记录相关配置字段，尤其当前实例的 `Alas.Emulator`、当前任务的 `Campaign` 和 `Fleet`。不要把其他实例、模板默认值或无关凭据当成当前生效配置。

已安装插件提供只读采集命令。在目标界面停稳后运行，替换真实序列号：

```powershell
& $alasPython -m alas_1440p probe --alas $alasRoot --serial '实际序列号' --skip-ocr
```

已有原始截图可离线检查：

```powershell
& $alasPython -m alas_1440p probe --alas $alasRoot --image 'D:\调试目录\native.png' --skip-ocr
```

默认报告位于原版目录的 `log/resolution_probe/<时间戳>/resolution-report.zip`。这份工具目前主要检查截图归一化、页面模板与主页 OCR；它不会自动分析商店商品或周回开关。必要时补充针对性离线诊断，不能把其退出码为 0 当成两个故障都已通过。

采集 PNG 应使用 Python `subprocess` 的二进制输出写入文件，或现有采集脚本。避免用 Windows PowerShell 5.1 的文本重定向直接保存 `adb exec-out screencap -p`，以免损坏 PNG。

### 第三步：按实际调用链定位

通用商店重点检查这些上游路径：

- `module/ui/ui.py`、`module/ui/page.py`：`page_munitions` / `MUNITIONS_CHECK` 是否识别。
- `module/shop/ui.py`、`module/ui/switch.py`：`shop_nav_250814`、`shop_tab_250814`、`NAV_GENERAL`、`TAB_GENERAL`。
- `module/shop/shop_reward.py`、`module/shop/shop_general.py`、`module/shop/base.py`：实际进入了哪个阶段，商品网格是否与画面一致。
- `module/statistics/item.py`：商品有效性、模板匹配、货币类型、价格 OCR，是否被过滤为零个商品。
- `module/base/button.py`、`module/base/base.py`：RGB/luma/binary 匹配及颜色判断。先测量失败原因，不要直接全局降低匹配阈值。

主线流程重点检查：

- `module/handler/fast_forward.py`：`map_get_info()`、`handle_fast_forward()`、`handle_auto_search()`、`SwitchClearMode.get()`、`SwitchAutoSearch.get()`。
- 记录 `map_clear_percentage`、`map_has_clear_mode`、`map_is_clear_mode`、`map_is_auto_search`、`MAP_CLEAR_ALL_THIS_TIME` 以及相关配置。当前代码会因未识别到周回条件或标题、选项未启用、需要完成三星等条件关闭自律寻敌。
- `CLEAR_MODE_TITLE`、`CLEAR_MODE_CHECK`、`AUTO_SEARCH_TITLE` 系列、`AUTO_SEARCH_CHECK`：模板是否匹配，关联偏移和开关颜色计数是否正确。
- `module/map/map_operation.py`、`module/handler/auto_search.py`、`module/map/map_fleet_preparation.py`：准备界面、舰队角色、自律开关和实际点击后的状态转移。
- 若已经进入战斗但没有自律，检查 `module/combat/combat.py`、`module/combat/combat_auto.py` 的自动开关设置与当前舰队战斗模式，不能只看地图周回选项。

插件层重点检查 `alas_1440p/resolution.py`、`loader.py`、`patching.py`、`patches.json`：截图是否旋转/缩放一次，识别坐标是否维持 1280×720，输入是否在正确的后端转换一次，设备真实尺寸是否被某个缩小输出的截图后端错误覆盖。以上均是排查项，不是已经确认的根因。

### 修复方式与验证要求

保持“原版源码 + 独立插件”的架构。必要时可在隔离开发副本验证上游算法修改，但交付修复应进入插件并经过实际加载验证，原版更新器继续保留。不要以关闭更新、强制开启自动战斗或全局降低识别阈值来掩盖故障。

`tools/generate_manifest.py` 当前固定读取旧基线与旧 1440P 提交来生成适配清单，且需要 Python 3.9+，不能直接用 Alas 的 Python 3.7 运行。不要盲目重新生成并覆盖正在修复的 `patches.json`，否则会丢失新改动。需要新增适配时，维护对应源码/清单及兼容性检查，验证它在目标上游版本上真实执行。

先用保存的真实失败帧建立能失败的回归，再修复、确认转为通过。尽可能比较同一界面状态下的三种组合：720P 原版、720P 加插件、1440P 加插件。切换分辨率后重连并重启测试进程，避免旧缓存和触控服务状态混入。

回归至少覆盖：商店页面与商品识别；未选中/已选中周回和自律寻敌开关；关卡未解锁或条件不足时不误判；实际使用的截图/控制后端；720P 保持正常。离线测试通过后，再验证现场的正确状态转移和按钮落点。

完整测试需使用具备项目依赖及 pytest 的环境。不要为了跑测试直接升级原版依赖：

```powershell
$env:ALAS_PLUGIN_TEST_ROOT = $alasRoot
& $alasPython -m pytest (Join-Path $pluginRoot 'tests') (Join-Path $alasRoot 'tests') -q
Remove-Item Env:ALAS_PLUGIN_TEST_ROOT
```

若该解释器没有 pytest 或缺少测试依赖，先说明缺项，再准备独立测试环境；不要把没有运行的测试列为通过。上面的环境变量只应临时设置；若原先已有值，请恢复原值。

### 最后交付

用中文报告两个故障各自的复现条件、根因、修改位置、实际加载的插件版本，以及离线和实机验证结果。区分已确认修复、配置原因和仍未复现的部分。提供可安装插件与卸载方式，保留原版在线更新。结束前在工作区留下 `LOCAL_DEBUG_HANDOFF.md`，记录路径、版本、复现步骤、证据位置、修改和未完成事项，方便下一个本地窗口继续。

现在先确认本地实际加载环境，收集通用商店和主线自动流程的首个失败证据，再进行最小修复。
