# M1 无账号软件预检记录：Windows + XiaoAiAgent + Qwen

## 验证范围

2026-10-25，在 Windows 主力机完成独立上游环境搭建和真实本地模型调用。此记录没有小米账号登录、账户设备发现或音箱 TTS 播报结果；M1 的实机语音闭环尚未验收。

设备所有者另行确认型号 L05C、固件 1.62.28 及原生问答成功；固件保持不变。原生问答成功不能用来证明 Agent 闭环，M0 人工五次时延仍待补录。

## 固定来源和环境

- 上游：[Nex-Z/XiaoAiAgent c856d2a39d156299d0b7e50a84e6421834a64004](https://github.com/Nex-Z/XiaoAiAgent/tree/c856d2a39d156299d0b7e50a84e6421834a64004)，在单独目录以 detached HEAD 检出，没有修改其跟踪源码。
- 工具：独立环境内的 uv 0.13.5；托管 Python 3.12.15。托管运行时与缓存保存在本机忽略目录，未替换 M0 的 Python 3.11.9 环境；禁用 Python 注册表注册和 PATH 安装。
- 上游依赖按其 pyproject.toml 安装，额外安装 `langchain-ollama`。`pip check` 通过；完整 `pip freeze` 保留在本地私有实验产物中。
- 模型：已安装的 `qwen3:8b`；Ollama 服务端 0.33.2。使用本机回环地址，无云端 LLM API key。

| 核心包 | 实际安装版本 |
|---|---|
| langchain-ollama | 1.1.0 |
| langchain-core | 1.7.0 |
| langgraph | 1.2.17 |
| ollama Python client | 0.6.3 |
| fastapi | 0.162.0 |
| pydantic | 2.14.1 |

以上是一次已运行环境的版本记录，不是覆盖所有平台/版本的兼容性声明。

## 实际执行结果

| 检查 | 结果 | 能证明的范围 |
|---|---|---|
| 原始 Ollama `/api/chat` 单次生成 | 成功回复“连接成功” | 本地模型能实际生成文本，超出了 tags 列表检查 |
| 固定上游 editable install + Ollama 适配包 | 安装成功，`pip check` 无破损依赖 | 该 Windows/Python 环境能解析安装依赖 |
| `python main.py --help` | 成功 | 主入口及其依赖可导入；未触发登录 |
| `create_llm(config.llm, tools=register_builtin_tools())` 后真实 `ainvoke` | 回复“适配成功”，约 2.92 秒 | 上游配置 → 工厂 → 工具绑定 → ChatOllama → Qwen 文本请求 |
| 上游 `Agent.graph.ainvoke` 只读时间工具往返 | 成功，消息链存在 `get_current_time` 的 ToolMessage，随后生成最终回答，约 1.14 秒 | LangGraph 能路由至工具、接收真实工具返回并结束一轮回答 |
| XiaoAi-Lab 原有自动化套件 | 34 项通过 | M0 软件回归；不充当真实音箱验收 |

耗时仅为本次样本；不代表音箱语音时延或稳定性能。时间工具来自上游，不是新增的电脑控制能力。上游内置天气工具返回演示数据，此次没有调用它，也没有启用外部 MCP 服务器。

## 本次配置选择

`provider: ollama`，`model: qwen3:8b`，`api_key` 为空；`llm.extra` 使用 `reasoning: false`、`num_predict: 256`、`num_ctx: 4096`、`keep_alive: 1m`，HTTP 客户端 timeout=60 秒且不读取代理环境。文本实验关闭 LangSmith tracing。

桥接服务绑定 127.0.0.1；`mute_xiaoai: false`、`trigger_word: 帮我`、`use_command: true`，TTS/wake 参数沿用固定上游。`MI_USER`、`MI_PASS`、`MI_DID` 由设备所有者在自己的终端输入；配置和 Token 被上游 Git 忽略。本次尚未填入凭据或运行账号设备查询。

## 下一步及未解决项

按[实验 003](../003-bridge.md)在本机设置账号、运行 `--list-devices`，核对目标并显式设置 `MI_DID`，再启动监听。记录新的语音记录、Agent 回复、TTS 下发和实际听到的内容；不能仅凭 TTS 成功日志验收。保留原生回答时需记录是否双重播报。

账号风控、设备 ID/MIOT DID 对应、固件 1.62.28 的 TTS 行为、云端对话接口可用性均尚未实测。上游此修订没有 LICENSE 文件；当前仅单独运行它，不复制或分发其实现。升级依赖或上游提交后，应重新执行这些预检并保存新的版本记录。
