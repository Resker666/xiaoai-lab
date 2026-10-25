# 实验 003：XiaoAiAgent + Ollama/Qwen 语音闭环（M1，文本预检通过）

**2026-10-25：Windows 上已通过真实 Qwen 文本、上游模型工厂与只读时间工具预检；所有者已使用可选入口完成短信验证，查到两台 L05C，并通过改名明确目标设备。MIOT 对应及 L05C TTS 尚未实机验证。** 本仓库没有 Xiaomi Bridge 实现。版本与边界见[预检记录](results/2026-10-25-m1-preflight.md)、[验证适配记录](results/2026-10-25-m1-account-verification.md)及[设备绑定记录](results/2026-10-25-m1-device-binding.md)。M0 的人工五次时延仍待补录，不据此宣称整个里程碑已验收。

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

本次已实测 `qwen3:8b`。该模型可在 `llm.extra` 中加入以下配置，关闭思考输出并约束首次试验的生成量；这些值是本次实验选择，不代表通用最佳性能参数：

```yaml
extra:
  reasoning: false
  num_predict: 256
  num_ctx: 4096
  keep_alive: "1m"
  client_kwargs:
    timeout: 60
    trust_env: false
```

参考配置的 `xiaomi.did` 使用 `${MI_DID}` 占位符。先查询设备，再在同一终端设置实际 `MI_DID`，避免多音箱账户自动选择错误设备。

## 3. 无账号的模型适配层预检

在上游目录及其 Python 3.12 环境内运行：

```powershell
.\.venv\Scripts\python.exe -c "import asyncio; from src.config import get_config; from src.llm_factory import create_llm; from src.tools.builtin import register_builtin_tools; llm = create_llm(get_config().llm, tools=register_builtin_tools()); print(asyncio.run(llm.ainvoke('用一句话解释什么是 RTOS')).content)"
```

这一步验证上游配置 → ChatOllama → 模型（含工具绑定）的单次文本请求；不触发小米登录，不证明多轮工具执行或语音闭环。失败时记录“适配层/模型阶段失败”。成功后私下保存 `git rev-parse HEAD`、`python --version`、`python -m pip freeze`、Ollama 版本/模型 tag；上游依赖与可选适配包都需记录。

## 4. 由设备所有者设置账号并发现设备

仅在上述预检完成后，在当前 PowerShell 会话设置凭据，避免写入脚本/命令历史中的字面密码：

```powershell
$env:PYTHONUTF8 = '1'
$env:LANGSMITH_TRACING = 'false'
$env:LANGCHAIN_TRACING_V2 = 'false'
$env:MI_USER = Read-Host '小米账号（仅当前进程环境）'
$securePassword = Read-Host '小米密码' -AsSecureString
$env:MI_PASS = [System.Net.NetworkCredential]::new('', $securePassword).Password
.\.venv\Scripts\python.exe main.py --list-devices
```

判断成功应看是否列出目标设备，而不是仅看进程退出码：该提交在部分登录/配置错误路径也会正常返回。实机型号与云端设备信息需由所有者私下核对。

输出包含账号/设备标识，**不要上传原件**。私下核对目标，在下一阶段把对应 `deviceID` 放入当前终端的 `MI_DID`；配置由 `${MI_DID}` 读取，多设备时不要依赖自动选择。确认 `.mi.token` / `config.yaml` 在上游目录被忽略：`git check-ignore .mi.token config.yaml`。Token 默认位于当前工作目录；始终从上游根目录运行，不在 XiaoAi-Lab 内登录。

macOS 使用 `read -r MI_USER; export MI_USER` 与 `read -rs MI_PASS; export MI_PASS` 输入当前 shell 的环境变量（不要粘贴字面凭据到命令行）。实验结束后清理当前会话变量。

遇到验证码或风控时遵循官方验证流程；即使上游错误提示建议关闭二次验证，也不应照做。不要把密码放在 `--password` 命令参数中。

### 可选短信／邮箱验证入口

固定上游在登录响应缺少 `userId` 时直接抛错。需要额外验证的响应可能出现这种情况；此报错本身不能证明密码错误或确定本次原因。不要反复试密码、关闭二次验证或公开原始响应／验证链接。

本仓库的可选入口复用 [Yonsm/MiService](https://github.com/Yonsm/MiService/tree/a1727f7817819cae89f20ea197c030aaa199b96d) 的短信／邮箱验证，不修改 XiaoAiAgent 源文件。仅在其独立环境中安装固定源码依赖（MIT，源码版本 3.0.2，包含短信发送补全；不能用 PyPI 3.0.1 替代）。在 XiaoAiAgent 根目录执行：

```powershell
.\.venv\Scripts\python.exe -m pip install -r ../xiaoai-lab/config/requirements-xiaoaiagent-otp.txt
# 保持此前设置 MI_USER / MI_PASS 的同一个终端：
.\.venv\Scripts\python.exe ../xiaoai-lab/scripts/xiaoaiagent_otp.py --list-devices
```

需要验证时会向账号的绑定手机／邮箱请求验证码，并在本机隐藏输入。验证码只在该终端输入，不发到聊天或写入报告。不支持的图片验证码／协议变化会报错停止，不保证每个账号均可完成验证。入口只输出分类后的登录失败原因与数值代码，并抑制依赖中可能包含原始响应的账号日志；上游设备列表和启动日志仍含个人标识，保留本机。

成功时打印所选设备字段的 JSON 列表。`online: null` 表示接口未提供状态，不能当作离线。多台同型号设备时，在 App 中将实验音箱改成唯一名称，再查询确认名称变化对应的条目；不要依赖列表顺序。

私下核对 L05C 条目并设置 `MI_DID`。随后用同一入口启动监听：

```powershell
$env:MI_DID = Read-Host '输入目标 L05C 所在行的 deviceID（仅本机）'
.\.venv\Scripts\python.exe ../xiaoai-lab/scripts/xiaoaiagent_otp.py
```

入口先检查凭据；监听模式还要求显式设置 `MI_DID`，且实际读取的配置必须使用同一个设备，否则拒绝启动。设备查询调用现有 `MiNAService`，失败时不会进入上游建议关闭二次验证的错误处理。查询或账号验证失败返回 1，预检不通过返回 2；退出 0 仍不能代替设备列表或实际声音验收。原生 `main.py` 入口继续存在，但不使用这里的验证适配器。macOS 将 Python 路径替换为 `.venv/bin/python`。源码依赖仅用于此实验，M0 的安装和 CLI 不需要它。

可选入口还替换上游的 MIOT 标识解析：优先使用选中设备直接返回的数字 DID；否则要求名称在小爱设备列表与 MIOT 设备列表中均唯一对应，并拒绝型号冲突。它不按型号或列表顺序选第一台。名称未同步、匹配不唯一或查询失败时不会启动音箱监听；看到失败后停止程序并核对，不把仅存活的 HTTP 服务当作语音桥接成功。

## 5. 真机语音验收与记录

```powershell
$env:LANGSMITH_TRACING = 'false'
$env:LANGCHAIN_TRACING_V2 = 'false'
$env:MI_DID = Read-Host '输入目标 L05C 所在行的 deviceID（仅留在本机）'
if ([string]::IsNullOrWhiteSpace($env:MI_DID)) { throw '请先明确选择目标音箱' }
.\.venv\Scripts\python.exe ../xiaoai-lab/scripts/xiaoaiagent_otp.py
# 结束程序后清理当前会话：
Remove-Item Env:MI_USER, Env:MI_PASS, Env:MI_DID
Remove-Variable securePassword
```

启动后需看到音箱监听成功的日志；仅出现 FastAPI 服务启动不代表音箱初始化成功。该提交在音箱初始化失败后仍可能保留 HTTP 服务。

对音箱说一条包含触发词的普通问题，例如“小爱同学，帮我用一句话解释什么是 RTOS”。按顺序记录：设备列表识别 → 新对话进入轮询 → Agent 文本生成 → TTS 发送 → **亲耳听到播报**。TTS API 成功日志不等于声音验收。记录是否双重回答；保留原生回答时可能发生。

失败时标注首次失败阶段、时间、版本和脱敏错误。需要 debug 时临时设 `xiaomi.debug: true`，日志会包含语音和标识，仅保留私有。不要把“HTTP 正常”记成“L05C 兼容”，也不要把“没有开放 TCP 端口”当成云端桥接失败。

只有实机完整播报至少一次 Agent 回复才能验收 Issue #2；连续对话、MCP/电脑控制、延迟优化留给后续里程碑。
