# Windows ADB 服务崩溃的本次修复记录

本记录对应2026-10-24的本地实测，供恢复相同环境时参照，不由1440P插件自动执行。

## 故障依据

Alas启动时出现 `ConnectionResetError / WinError 10054`、目标设备未找到，
最终提示人工接管。Windows临时目录中的 `adb.log` 在对应时间记录：

```text
Version 29.0.6-6198805
fdevent.cpp:96] Check failed: 1UL == erased (1UL=1, erased=0)
```

这是ADB主机服务的致命断言。仅凭Alas通用错误提示，不能认定代理或网络工具是原因。
任务重试后恢复并完成T1至T6开荒；随后在任务空闲时处理服务升级。

## 实际部署

1. 备份原 `config/deploy.yaml`、ADB及配套DLL。
2. 将已安装MuMu12提供的ADB36.0.0-13206524及其匹配的 `AdbWinApi.dll`、
   `AdbWinUsbApi.dll` 复制到该Alas的独立目录 `toolkit/adb36/`。
   原 `toolkit/Lib/site-packages/adbutils/binaries/` 保持原样。
3. 仅调整该Alas的部署配置：

   ```yaml
   AdbExecutable: ./toolkit/adb36/adb.exe
   ReplaceAdb: false
   ```

   `ReplaceAdb=false` 避免启动器将所选ADB覆盖到其他模拟器目录。
   保留原启动器、源码和更新器，不修改游戏任务或购买配置。
4. 用户确认其他模拟器任务已停止后，关闭旧5037服务，再由新路径启动服务并连接
   用户指定的目标设备。共享服务重启会短暂断开其他模拟器连接。

正式切换前曾在5038独立端口验证候选版本，测试后关闭该独立服务。
独立服务仍可能自动发现本机模拟器，测试期间只对授权目标发出读取命令。
不将预编译ADB或本机配置、账号信息、完整运行日志提交到本仓库。

## 验证结果与限制

- 实际5037服务进程的可执行路径为新部署目录。
- 新启动的原版 `ConnectionAttr.adb_binary` 解析到新路径，`adbutils` 属性读取通过。
- 目标设备连续100次Android版本查询及2560×1440原始PNG截图通过。
- 旧ADB29客户端可访问新服务，访问前后服务PID未变。
- `alas.json` 哈希保持不变，其他模拟器程序文件未修改。

本次读取验证通过不等于已证明长期无崩溃。以后若复发，保留对应时间的主机
`adb.log` 和Alas日志继续诊断；不要全局降低识别阈值或更改游戏任务偏好来绕过。

## 回滚

在所有相关模拟器任务停止后，恢复备份的 `config/deploy.yaml`，关闭新版共享ADB服务，
使用原路径ADB重新启动服务，再连接原目标设备。独立的 `toolkit/adb36/` 可保留，
恢复配置后原版不会选择它。插件0.1.1及其商店、周回标题修复无需因此卸载。
