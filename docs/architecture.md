# 架构决策（草案）

## 两条独立路线

**AI Bridge（拟开发）：** L05C 原生 ASR/播放 → 小米云端账号/MIoT 接口 → 轮询对话 → Agent（本地 Ollama/Qwen 或 API）→ 小米设备 TTS。此路线依赖外部服务可用性和账号授权，不等于设备本地流式音频或离线唤醒。

**Embedded Lab（已开始）：** 设备信息登记 → 单个设备只读 TCP connect 探测 → 流量与协议研究（仅本人设备，敏感数据私有）→ 公开固件与社区研究 → 如果值得，硬件端口调查。

## 模块边界

- `src/xiaoai_lab`：M0 纯标准库工具，当前不连接小米账号。
- `config/bridge.example.yaml`：上游 `Nex-Z/XiaoAiAgent` 参考配置，不由本仓库代码读取。
- `reports/`：个人本地实验记录，gitignore 忽略。
- `docs/experiments/`：可复现步骤与预期结果，不夸大适配进展。

## 体验指标（未来 M2）

语音结束到 Agent 识别事件、Agent 响应耗时、TTS 下发耗时、实际扬声器开始播报的主观/人工计时、失败率。每个指标都标注测量点，避免将整体往返延迟误认为本地推理耗时。
