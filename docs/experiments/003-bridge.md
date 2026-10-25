# 实验 003：XiaoAiAgent + Ollama/Qwen 语音闭环（M1，待执行）

**本次仅核对公开源码，未安装/运行上游、未验证真实 Ollama 推理、未登录小米或验证 L05C TTS。** 本仓库没有 Xiaomi Bridge；先完成 M0 私有基线，再由设备所有者按阶段执行本实验。

## 已核对的来源与边界

2026-10-25 检查 [Nex-Z/XiaoAiAgent 提交 c856d2a](https://github.com/Nex-Z/XiaoAiAgent/tree/c856d2a39d156299d0b7e50a84e6421834a64004)。以下为源码事实，不是本项目实机结论：

| 来源 | 结论及影响 |
|---|---|
| [pyproject.toml](https://github.com/Nex-Z/XiaoAiAgent/blob/c856d2a39d156299d0b7e50a84e6421834a64004/pyproject.toml) | 上游要求 Python **3.12+**；本仓库 M0 的 3.10+ 环境不能直接复用。依赖只设下限，无锁文件，安装可复现性仍须记录。 |
| [src/llm_factory.py](https://github.com/Nex-Z/XiaoAiAgent/blob/c856d2a39d156299d0b7e50a84e6421834a64004/src/llm_factory.py) | 已有 `provider: ollama` → `ChatOllama`；需要另外安装 `langchain-ollama`。使用模型实际 tag 和 Ollama 根 URL，不需要云端 API key。 |
| [src/config.py](https://github.com/Nex-Z/XiaoAiAgent/blob/c856d2a39d156299d0b7e50a84e6421834a64004/src/config.py) | YAML 的 `${MI_USER}`/`${MI_PASS}` 从**进程环境变量**替换；没有自动读取 `.env` 的配置。仅复制 `.env.example` 不够。 |
| [src/xiaomi/speaker.py](https://github.com/Nex-Z/XiaoAiAgent/blob/c856d2a39d156299d0b7e50a84e6421834a64004/src/xiaomi/speaker.py) | 轮询小米云端对话，L05C 使用 MIOT TTS；`deviceID` 与 MIOT 数字 DID 有区别。上游有自动选择/匹配设备行为，多音箱账户须明确选中自有 L05C。 |
| [config.yaml.example](https://github.com/Nex-Z/XiaoAiAgent/blob/c856d2a39d156299d0b7e50a84e6421834a64004/config.yaml.example) | `use_command: true`，`tts_command: [5,3]`、`wake_command: [5,4]` 是该修订的上游配置，仍需 L05C 固件实测。不要与 MiGPT 参数互换。 |
| [src/agent.py](https://github.com/Nex-Z/XiaoAiAgent/blob/c856d2a39d156299d0b7e50a84e6421834a64004/src/agent.py) | Agent 自动绑定已注册工具；需验证选择的 Qwen tag 支持工具调用，模型列表可读不足以证明 Agent 能用。 |

上游目录树此修订没有 LICENSE 文件；本仓库不复制/分发其实现，后续若要移植代码须先澄清许可证。内置 `get_weather` 返回演示数据，并非真实天气接口，不能当作技能实测结论。

## 1. 在音箱所在网络选择一台主机

优先 Windows 主力机；也可使用在同一可达网络的 Mac mini。不要假定公司 Mac 与家中音箱同网，不要为实验直接公开 11434/8000。先在所选主机执行 M0 `doctor`、`ollama list`，记录模型 tag 与版本。`doctor` 仅检查 [Ollama `/api/tags`](https://docs.ollama.com/api/tags) 模型列表，不能证明生成能力。

Windows 可先用已有模型执行普通推理（提示中不包含个人信息）：

```powershell
ollama --version
ollama list
$model = Read-Host '输入 ollama list 中已安装的 Qwen 完整 tag'
ollama run $model '用一句话解释什么是 RTOS'
```

未安装模型时先自行选择适合硬件且支持工具调用的 Qwen tag，再安装；本实验不预设 16 GB Mac 或当前 Windows 的模型速度、显存或可用容量。

## 2. 在本仓库外建立上游独立环境

从本仓库根目录开始，以下命令在 Windows PowerShell 执行，需要预先安装 Python 3.12+：

```powershell
git clone https://github.com/Nex-Z/XiaoAiAgent.git ../XiaoAiAgent
Set-Location ../XiaoAiAgent
git checkout --detach c856d2a39d156299d0b7e50a84e6421834a64004
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .
.\.venv\Scripts\python.exe -m pip install langchain-ollama
Copy-Item ../xiaoai-lab/config/bridge.example.yaml config.yaml
```

若目录已经存在，先检查其中的版本及修改，不要覆盖现有上游 `config.yaml`。安装失败时停在此阶段，记录 Python 版本和脱敏后的依赖错误，不继续账号登录。macOS 对应使用 `python3.12 -m venv .venv`、`.venv/bin/python -m pip ...` 和 `cp`。

手动编辑 `config.yaml`：`llm.model` 填真实 tag；`provider: ollama`、`api_key: ""`、`base_url: http://127.0.0.1:11434`；保留 `server.host: 127.0.0.1`、`mcp_servers: []`、`mute_xiaoai: false`、`trigger_word: "帮我"`。配置属于上游，XiaoAi-Lab CLI 不读取它。

## 3. 无账号的模型适配层预检

在上游目录及其 Python 3.12 环境内运行：

```powershell
.\.venv\Scripts\python.exe -c "import asyncio; from src.config import get_config; from src.llm_factory import create_llm; from src.tools.builtin import register_builtin_tools; llm = create_llm(get_config().llm, tools=register_builtin_tools()); print(asyncio.run(llm.ainvoke('用一句话解释什么是 RTOS')).content)"
```

这一步验证上游配置 → ChatOllama → 模型（含工具绑定）的单次文本请求；不触发小米登录，不证明多轮工具执行或语音闭环。失败时记录“适配层/模型阶段失败”。成功后私下保存 `git rev-parse HEAD`、`python --version`、`python -m pip freeze`、Ollama 版本/模型 tag；上游依赖与可选适配包都需记录。

## 4. 由设备所有者设置账号并发现设备

仅在上述预检完成后，在当前 PowerShell 会话设置凭据，避免写入脚本/命令历史中的字面密码：

```powershell
$env:MI_USER = Read-Host '小米账号（仅当前进程环境）'
$securePassword = Read-Host '小米密码' -AsSecureString
$env:MI_PASS = [System.Net.NetworkCredential]::new('', $securePassword).Password
.\.venv\Scripts\python.exe main.py --list-devices
```

输出包含账号/设备标识，**不要上传原件**。私下核对目标并填入上游 `xiaomi.did`，多设备时不要依赖自动选择。确认 `.mi.token` / `config.yaml` 在上游目录被忽略：`git check-ignore .mi.token config.yaml`。Token 默认位于当前工作目录；始终从上游根目录运行，不在 XiaoAi-Lab 内登录。

macOS 使用 `read -r MI_USER; export MI_USER` 与 `read -rs MI_PASS; export MI_PASS` 输入当前 shell 的环境变量（不要粘贴字面凭据到命令行）。实验结束后清理当前会话变量。

遇到验证码或风控时遵循官方验证流程；即使上游错误提示建议关闭二次验证，也不应照做。不要把密码放在 `--password` 命令参数中。

## 5. 真机语音验收与记录

```powershell
.\.venv\Scripts\python.exe main.py
# 结束程序后清理当前会话：
Remove-Item Env:MI_USER, Env:MI_PASS
Remove-Variable securePassword
```

对音箱说一条包含触发词的普通问题，例如“小爱同学，帮我用一句话解释什么是 RTOS”。按顺序记录：设备列表识别 → 新对话进入轮询 → Agent 文本生成 → TTS 发送 → **亲耳听到播报**。TTS API 成功日志不等于声音验收。记录是否双重回答；保留原生回答时可能发生。

失败时标注首次失败阶段、时间、版本和脱敏错误。需要 debug 时临时设 `xiaomi.debug: true`，日志会包含语音和标识，仅保留私有。不要把“HTTP 正常”记成“L05C 兼容”，也不要把“没有开放 TCP 端口”当成云端桥接失败。

只有实机完整播报至少一次 Agent 回复才能验收 Issue #2；连续对话、MCP/电脑控制、延迟优化留给后续里程碑。
