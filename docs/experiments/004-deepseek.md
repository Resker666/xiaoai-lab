# 实验 004：复用 XiaoAiAgent 接入 DeepSeek API

2026-10-25：DeepSeek Flash 配置已通过固定上游模型工厂、已安装的 `langchain-deepseek 1.1.1` 和 LangGraph 的模拟 HTTP 工具往返。所有者按本机切换步骤后反馈可用，记为所有者的实际可用性确认；未收集真实请求日志、回答内容或时延，不能据此独立核验每个环节或推断长期稳定性。

## 模型与来源

官方当前列出的模型为 `deepseek-flash` 和 `deepseek-v4-pro`；本次按所有者的响应／成本偏好选择前者，使用 `https://api.deepseek.com`，见[官方首次调用](https://api-docs.deepseek.com/)。上游固定提交的旧默认模型名 `deepseek-chat` 不作为本次配置依据。

两者均支持工具调用；语音试验先关闭思考，参数为 `extra_body.thinking.type: disabled`，见[官方工具调用示例](https://api-docs.deepseek.com/guides/tool_calls/)。API 按 token 计费，单价以[官方价格](https://api-docs.deepseek.com/quick_start/pricing/)为准。识别后的问题文本、对话上下文和工具结果会发送到 DeepSeek；模型计算改在云端，音箱唤醒／识别／播放链路仍沿用实验 003。

## 1. 替换模型配置块

沿用[实验 003](003-bridge.md)的独立 Python 3.12+ 环境和固定上游；它已依赖 `langchain-deepseek`，无需更换小米认证或 TTS 实现。本仓库 M0 CLI 仍无第三方运行依赖。

先把当前上游 `config.yaml` 备份到被忽略的 `reports/`，保留回退 Ollama 的方式。将[模型配置示例](../../config/llm.deepseek.example.yaml)中的**整个 llm 节**替换到上游配置，保留 `xiaomi`、`server`、`mcp_servers` 原样。不要用该文件覆盖完整配置，也不要保留 Ollama 的 `reasoning`、`num_predict`、`num_ctx`、`keep_alive`、`client_kwargs`。

配置引用 `${DEEPSEEK_API_KEY}`；不要写入真实 Key。当前参数限制每次模型请求最多生成 512 token，超时 60 秒，SDK 自动重试为 0。Agent 执行工具时可能有多次模型请求；这不是整轮对话的总费用或总时长限制。

## 2. 在所有者终端输入 Key

在保留了 `MI_USER` / `MI_PASS` / `MI_DID` 的原 PowerShell 中停止旧进程（Ctrl+C），保持位于独立 XiaoAiAgent 根目录，执行：

```powershell
$deepseekKey = Read-Host '输入 DeepSeek API Key（仅本机）' -AsSecureString
$env:DEEPSEEK_API_KEY = [System.Net.NetworkCredential]::new('', $deepseekKey).Password
$env:LANGSMITH_TRACING = 'false'
$env:LANGCHAIN_TRACING_V2 = 'false'
```

在提示出现后再输入 Key，不要把 Key 写成命令参数、放入 Git 或发到聊天中。上游不会自动加载 `.env`；环境变量必须由启动进程继承。

## 3. 先做一次真实文本预检

以下命令会发送一个小的付费模型请求，不登录小米或操作音箱：

```powershell
if ([string]::IsNullOrWhiteSpace($env:DEEPSEEK_API_KEY)) { throw '请先设置 DEEPSEEK_API_KEY' }
.\.venv\Scripts\python.exe -c "import asyncio; from src.config import get_config; from src.llm_factory import create_llm; print(asyncio.run(create_llm(get_config().llm).ainvoke('只回复：DeepSeek连接成功。')).content)"
```

本机另外准备了私有 `reports/deepseek-check.py`，可用独立上游解释器运行；它在 Key 缺失时先退出，真实失败只显示异常类型和 HTTP 状态，不输出原始错误或 Key。该私有助手不随仓库分发；上面的命令是可复现的通用路径。遇到 401 先检查 Key，402 检查余额，429 稍后重试；不要上传原始错误响应。

成功生成文本后，在同一终端运行：

```powershell
.\.venv\Scripts\python.exe ../xiaoai-lab/scripts/xiaoaiagent_otp.py
```

确认音箱监听已启动，再问一个带“帮我”的普通问题；核对终端 Agent 回复与实际播报，并按[复测表](templates/m1-record.md)记录 DeepSeek 模型名、等待时间、重复或漏答。使用现有 `mute_xiaoai` 设置，原生抢占问题的固件效果仍需单独确认。

## 回退与验证边界

停止桥接后，将本机备份的原 Ollama 配置恢复为上游 `config.yaml`，再用原可选入口启动。没有实现自动故障转移。实验结束可用 `Remove-Item Env:DEEPSEEK_API_KEY` 和 `Remove-Variable deepseekKey` 清理当前终端变量。

离线预检已验证：实际工厂生成 ChatDeepSeek，模型名、非思考开关、`max_tokens` 正确序列化，没有 Ollama 参数泄漏；通过模拟工具调用和真实只读时间工具，向模型回传工具结果并结束一轮回答。这只证明已安装适配层的请求／响应与 Agent 路由兼容；所有者的后续可用反馈单独记录，不将模拟结果当作真实云端工具调用或声音证据。尚无耗时、token 用量、成功率、费用及原生抢占改善数据，维护代理未读取 Key 或另行发送付费请求。
