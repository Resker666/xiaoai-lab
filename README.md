# XiaoAi-Lab 🎙️

> 把小爱音箱 Play 增强版（L05C）变成可扩展的 AI Agent 语音终端，同时开展可复现、低风险的嵌入式研究。

**状态：M0 工程脚手架完成；尚未在真实 L05C 上验证。** 当前代码提供本地环境检查与授权局域网 TCP 端口探测，**不包含刷机、Root、SSH 解锁或声称已完成的 AI 语音接入**。

## 项目目标

- **AI 体验：** L05C 继续负责小爱原生唤醒/语音识别/播放；Mac mini + Ollama/Qwen 运行 Agent，通过已有小米接口尝试接入（先验证，再优化）。
- **嵌入式研究：** 记录 L05C 设备基线、局域网暴露服务、通信协议、固件与 NuttX 资料；后期视必要性探索 UART，默认只读。
- **工程质量：** 可复现实验、明确兼容性边界、绝不提交账号密码、Cookie、Token、语音记录与设备唯一标识。

## 已知约束

- L05C 在 [xiaoai-patch](https://github.com/duhow/xiaoai-patch) 中标注为 **NuttX**，该项目不支持它的刷机补丁；不应假定有 Linux shell/SSH。
- [MiGPT L05C 兼容表](https://github.com/idootop/mi-gpt/blob/main/docs/compatibility.md) 标注为基本功能可用，但建议关闭 `streamResponse`，不支持现成的连续对话体验。
- [XiaoAiAgent](https://github.com/Nex-Z/XiaoAiAgent) 针对 L05C，采用轮询小米对话记录与设备 TTS；云端语音桥接 **不是本地麦克风音频流**。

## 架构

```text
[L05C：唤醒 / ASR / 扬声器]
                |
       小米账户/云端设备接口
                |
     [未来：XiaoAi Bridge]
                |
       [Agent / Tools / MCP]
                |
        [Ollama / Qwen]

平行研究路线：[设备信息] → [只读局域网探测] → [协议/固件资料] → [可选 UART]
```

目前仓库的 `src/xiaoai_lab` **只有 M0 诊断工具**；桥接与 Agent 尚在路线图中，绝不混淆计划与已实现的功能。

## 5 分钟启动 M0 实验

要求 Python **3.10+**，Windows PowerShell / macOS / Linux 均可。

```bash
python -m pip install -e .
xiaoai-lab doctor
```

`doctor` 检查 Python、平台以及当前机器上 Ollama `/api/tags` 的可达性和模型名。没有运行 Ollama 时报告 `unavailable` 是正常结果。

如果你知道**自己这台音箱**的局域网 IPv4 地址（例如从路由器 DHCP 设备列表找到），可以选择只读扫描常见 TCP 服务：

```bash
xiaoai-lab probe --ip 192.168.1.105
```

> 注意：`192.168.1.105` **只是占位地址**，必须换成你的实际 L05C IP；只能对你拥有或获授权管理的设备运行。没有开放 TCP 端口不代表不存在调试通道。此命令不认证、不爆破、不写设备、不扫描整个网段。

更多操作及记录模板见 [实验 001：设备基线](docs/experiments/001-baseline.md) 与 [实验 002：局域网服务](docs/experiments/002-network.md)。

### Windows PowerShell 完整示例

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .
.\.venv\Scripts\xiaoai-lab.exe doctor
.\.venv\Scripts\xiaoai-lab.exe probe --ip 192.168.1.105
```

### Mac mini（Ollama 在本机运行）

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
ollama list                    # 前提：已安装并运行 Ollama
xiaoai-lab doctor
```

## 下一步：M1 语音闭环验证（基于现有项目）

先参考 [实验 003](docs/experiments/003-bridge.md) 单独克隆 `Nex-Z/XiaoAiAgent`，按上游 README 配置 `xiaomi.hardware: L05C`、`use_command: true`，**先执行 `python main.py --list-devices`，再验证语音 TTS**。初次测试建议保留小爱原生回答并设置触发词，不要直接接管全部对话。

> 本仓库**不复制** XiaoAiAgent 源码，不声称自己的 `config/bridge.example.yaml` 已能驱动当前 CLI；该配置文件只是上游手动参考模板，具体参数随上游版本变化，以其 README 为准。

## 仓库结构

```text
XiaoAi-Lab/
├── README.md                      # 项目介绍与入口
├── LICENSE                        # MIT
├── pyproject.toml                 # 无第三方依赖的 M0 CLI
├── src/xiaoai_lab/                # doctor / probe
├── tests/                         # unittest 模拟测试
├── config/bridge.example.yaml     # 上游 XiaoAiAgent 配置参考
├── docs/
│   ├── architecture.md
│   ├── roadmap.md
│   ├── security.md
│   └── experiments/
│       ├── 001-baseline.md
│       ├── 002-network.md
│       ├── 003-bridge.md
│       └── 004-firmware.md
├── reports/                       # 本地私有实验产物，默认忽略
└── .github/workflows/ci.yml
```

## 路线图与验收

参见 [开发里程碑](docs/roadmap.md) 与 [发布到 GitHub](docs/publish.md)。M0 验收：能运行 `doctor`、对真实设备的 IP 运行授权 `probe`、记录当前固件与语音基线；M1 验收：L05C 真实完成一次 Agent 语音问答。

## 贡献与授权

欢迎通过 Issue 提交**脱敏**的 L05C 固件版本、设备行为、探测结论和兼容性经验。代码采用 [MIT License](LICENSE)；上游项目分别遵循其自身许可证。
