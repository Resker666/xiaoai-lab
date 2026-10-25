# 实验 002：自有 L05C 局域网 TCP 服务探测（M0）

**前提：** 设备已联网，能从路由器 DHCP 列表核对 IP；电脑与音箱之间网络可达，未开启会隔离设备的访客网络。

```bash
xiaoai-lab probe --ip 192.168.1.105
```

替换成你**自己的**音箱 IP；不要直接探测示例地址。工具默认仅尝试 TCP 22、23、80、443、8080、8443 的连接，不发送应用层协议内容。不扫描 UDP、mDNS、miIO，不自动发现设备，也不会收集 MAC/DID。

Windows PowerShell 中从路由器核对 IP 后运行：

```powershell
$speakerIp = Read-Host '输入从自家路由器核对的 L05C IPv4'
$stamp = Get-Date -Format 'yyyyMMdd-HHmmss-fff'
.\.venv\Scripts\xiaoai-lab.exe probe --ip $speakerIp --timeout 0.6 --output "reports/probe-$stamp.json"
$LASTEXITCODE
# 可选：缩小或调整明确要测试的端口，例如：
.\.venv\Scripts\xiaoai-lab.exe probe --ip $speakerIp --ports 80,443 --timeout 1
```

只接受单个数字 RFC1918 IPv4；不接受域名、CIDR、回环/公网/链路本地地址。保守拒绝末尾 .0/.255，以避免家用 /24 中常见的网段或广播地址；这会拒绝某些非 /24 子网中的合法主机，并非根据真实掩码判断。自定义端口必须为 1..65535，最多 32 个不同端口；重复项去重保序，非法列表在发起任何连接前整体拒绝。每个连接超时为 (0, 10] 秒，默认 0.6 秒；串行执行，默认等待预算约为 6 × 0.6 秒加系统开销，完整命令并没有严格的总耗时保证。

## 如何解释

- `open`：TCP 连接成功，不表示存在可用 SSH shell，也不表示已获得权限。
- `closed`：连接被明确拒绝，不能确定拒绝来自设备还是中间网络设备。
- `timeout`：在超时内未连接成功，可能是过滤、离线或丢包；不能直接判定“端口关闭”。
- `unreachable`：系统报告网络或主机不可达，核对路由、访客隔离与设备在线状态。
- `permission_denied`：系统拒绝连接操作，核对本机防火墙、权限或运行环境限制，不要据此判断音箱服务。
- `error`：其他连接错误，私下记录数值 `error_code`（若有）和系统环境；不自动解释成关闭。
- `elapsed_ms` 是一次 TCP 连接耗时，不是音箱响应、语音或推理延迟。工具版本 0.2.0 起以这些细分状态替代旧的 `not_open_or_filtered`。
- 未开放端口不妨碍 MIoT/小米云端途径的 AI 接入。

命令退出 0 表示探测结束，即使所有端口关闭/超时也不算实验失败；参数错误退出 2，报告保存失败退出 1。报告内的 `device_tested: false` 不会因成功连接而改为 true，因为工具无法核对设备型号或完成声音验收。将命令、退出码、JSON 路径和观察写入[私有基线表](templates/m0-record.md)。**原始报告含实际 IP，没有自动脱敏，不直接上传。**

可以选用本机安装的 nmap 复核：`nmap -sT -Pn -p 22,23,80,443,8080,8443 <YOUR_L05C_IP>`。

**禁止：** 对未授权 IP 探测、扫整个网段、登录口令爆破、发送未知协议负载或对设备写入。
