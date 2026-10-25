# 实验 001：设备与 AI 环境基线（M0）

**目标：** 在不拆机、不刷机、不提供账号凭据的情况下，识别设备信息、验证开发机条件并记录原生体验。

## 准备

1. 从音箱底部核对硬件型号 `L05C`，记录固件版本（从小爱音箱/米家 App 中查看，若找不到就标记未知）。
2. 检查音箱能否在自家 Wi-Fi 下正常唤醒、响应与播报；通过路由器 DHCP 设备列表确定它的 IPv4 地址。
3. 在 Windows 或 Mac 本地执行 `python -m pip install -e .` 和 `xiaoai-lab doctor`。当前以 Windows 为主；Mac mini 不在身边时无需等待 Mac 完成本机软件检查。
4. 如果 Mac mini 上运行 Ollama：`ollama list`，再执行 `xiaoai-lab doctor`，确认检测到模型。

## Windows PowerShell 执行与保存

在本仓库根目录运行；不需要激活脚本或修改执行策略：

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .
$stamp = Get-Date -Format 'yyyyMMdd-HHmmss-fff'
.\.venv\Scripts\xiaoai-lab.exe doctor --timeout 1.5 --output "reports/doctor-$stamp.json"
$LASTEXITCODE
New-Item -ItemType Directory -Path reports -Force | Out-Null
Copy-Item docs/experiments/templates/m0-record.md "reports/m0-$stamp.md"
```

`--output` 自动创建父目录、以 UTF-8 写入新文件；已存在时退出 1，不覆盖旧实验。stdout 同样输出 JSON；PowerShell 5.1 的 `>` 编码可能不同，优先使用 `--output`。

Mac 上可使用独立环境后执行：

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e .
.venv/bin/xiaoai-lab doctor --output "reports/doctor-$(date +%Y%m%d-%H%M%S).json"
```

Ollama `status: unavailable` 表示本次未读到可用服务，不等于已证明未安装；`invalid_response` 表示响应不是预期的模型列表。`ok` 和空模型列表也可能同时出现。`doctor` 不下载模型、不执行推理、不登录小米，不能判断 16 GB 内存的实际模型速度。若 Ollama 在另一台可信主机，可明确指定 `--ollama-url`，但不应为此公开公司 Mac 或跨公网暴露端口。

## 记录（复制到 reports/ 或仓库外的个人实验笔记）

优先填写[完整模板](templates/m0-record.md)，其中含 5 次计时表、计时起止点、失败记录及公开摘要检查。工具不猜测固件版本，查不到时必须写“未知”。

| 项目 | 实测结果 |
|---|---|
| 日期 / 固件版本 | 待测 |
| 铭牌硬件型号 | 待核对 |
| Wi-Fi / 蓝牙是否正常 | 待测 |
| 原生唤醒及回答是否正常 | 待测 |
| 单次原生问答耗时 | 待测（建议重复 5 次） |
| Python / OS | `doctor` 输出 |
| Ollama 模型 | `doctor` 输出 |
| L05C 设备 IP | 私下记录，不上传仓库 |

### M0 验收

- [ ] 确认实物型号与固件版本（不可查则明确标记未知）
- [ ] `xiaoai-lab doctor` 运行成功
- [ ] 如果要做网络研究，继续 [实验 002](002-network.md)
- [ ] 日志、截图脱敏后才在 Issue 交流
