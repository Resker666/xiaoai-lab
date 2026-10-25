# 架构决策（草案）

## 两条独立路线

**AI Bridge（拟开发）：** L05C 原生 ASR/播放 → 小米云端账号/MIoT 接口 → 轮询对话 → Agent（本地 Ollama/Qwen 或 API）→ 小米设备 TTS。此路线依赖外部服务可用性和账号授权，不等于设备本地流式音频或离线唤醒。

**Embedded Lab（已开始）：** 设备信息登记 → 单个设备只读 TCP connect 探测 → 流量与协议研究（仅本人设备，敏感数据私有）→ 公开固件与社区研究 → 如果值得，硬件端口调查。

## 模块边界

- `src/xiaoai_lab`：M0 纯标准库工具，当前不连接小米账号。
- `diagnostics.py`：输入校验、单目标 TCP connect、Ollama tags 合约检查；所有网络参数先校验，连接和响应大小有边界。
- `cli.py`：命令参数、标准输出 JSON、标准错误与退出码；`reports.py`：UTF-8 私有报告保存，拒绝覆盖。
- `config/bridge.example.yaml`：上游 `Nex-Z/XiaoAiAgent` 参考配置，不由本仓库代码读取。
- `reports/`：个人本地实验记录，gitignore 忽略。
- `docs/experiments/`：可复现步骤与预期结果，不夸大适配进展。

## 开发和部署环境

Windows 是当前主开发机；公司 Mac mini M4（16 GB）是另一台候选 Ollama/Qwen 推理机。两机不假定在同一局域网，M0 可分别运行。优先在音箱所在网络的一台电脑完成 M1，不默认跨公司网络访问 Mac，也不默认公开 Ollama 服务。

M0 支持 Python 3.10+；已核对的 XiaoAiAgent 提交要求 Python 3.12+，必须独立虚拟环境。其 Ollama 分支使用 `langchain-ollama` 的 `ChatOllama`，基础地址为 Ollama 根 URL（不是 `/v1`）。版本和配置证据见[实验 003](experiments/003-bridge.md)。

## M0 报告合约（CLI 0.2.0）

`doctor` / `probe` 均包含 `schema_version: 1`、`tool_version`、UTC `recorded_at`、`device_tested: false`。最后一项表示工具无法自动证明目标为 L05C 或完成声音验收；即使 TCP 可达也保持 false。手工设备型号、固件和语音基线记在私有实验表。

`probe` 对每个端口输出 `port`、`status`、`elapsed_ms`，失败时可能附带数值 `error_code`；还记录 `timeout_seconds`。0.1.0 的 `not_open_or_filtered` 改为可区分的连接状态，消费旧输出的脚本需要更新，详情见[实验 002](experiments/002-network.md)。这些耗时是 TCP 连接耗时，不是语音或模型延迟。

所有诊断默认只输出 JSON；`--output` 另存新文件，已存在文件不会覆盖。报告保留实际目标 IP 和模型名，**没有自动脱敏**。退出码 0 表示诊断执行完毕，2 为参数错误，1 为报告保存失败；Ollama 不可达或没有开放端口本身不产生非零退出码。`/api/tags` 可用只证明模型列表接口可读，不能证明推理、工具调用或音箱闭环。

超时为单个 socket 操作的等待上限，不是整个命令的总时限；HTTP 域名解析和持续少量传输可能延长耗时。Ollama HTTP(S) 端点必须由操作者信任，不支持 URL 内嵌凭据、查询参数或片段；为保持请求指向明确，禁用系统代理和 HTTP 重定向。仅 tags GET，不执行推理或安装模型。

## 体验指标（未来 M2）

语音结束到 Agent 识别事件、Agent 响应耗时、TTS 下发耗时、实际扬声器开始播报的主观/人工计时、失败率。每个指标都标注测量点，避免将整体往返延迟误认为本地推理耗时。
