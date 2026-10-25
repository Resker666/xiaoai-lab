# 实验 003：通过现有开源工程验证 L05C AI 语音闭环（M1）

**注意：** 这是在你自己的电脑和账号上执行的教程，仓库暂未实现 Xiaomi Bridge。不要上传你实际使用的上游 `config.yaml` 或 Token。

## 1. 在 Mac mini 上验证 Ollama

```bash
ollama list
# 根据本机已安装模型的实际名称，在下面的上游 config.yaml 中填写 model
```

## 2. 单独克隆上游

```bash
git clone https://github.com/Nex-Z/XiaoAiAgent.git
cd XiaoAiAgent
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
python -m pip install langchain-ollama
```

## 3. 依照上游 README 配置

- 复制上游的 `config.yaml.example` 为 `config.yaml`（命令 `cp config.yaml.example config.yaml`）；不要提交它。
- `llm.provider: ollama`；`llm.model` 改为 `ollama list` 给出的实际模型名称，`base_url: http://localhost:11434`。
- `xiaomi.hardware: "L05C"`、`use_command: true`、`tts_command: [5,3]`。
- 初次试验先设 `mute_xiaoai: false`，`trigger_word: "帮我"`，避免接管全部原生功能。
- Xiaomi 用户名和密码使用环境变量 `MI_USER`、`MI_PASS`，按上游文档实际格式引用。
- 不同项目的 `wake_command`/`wakeUpCommand` **不是可直接互换的参数**；不要盲目将 MiGPT 的 `[5,1]` 搬到 XiaoAiAgent 的 `wake_command`，使用上游当前版示例或提出 issue 核对。

## 4. 先发现设备，再做语音实验

```bash
python main.py --list-devices
python main.py
```

对音箱说：**「小爱同学，帮我 用一句话解释什么是 RTOS」**。

记录四项：设备列表是否能看到 L05C、是否收到新的语音记录、是否生成 Agent 回答、音箱是否读出 TTS；然后观察是否产生双重回复。

**常见问题：** Xiaomi 账号风控/异地验证码，设备 DID 配错，L05C 可能需要 `use_command: true`，以及某些机型不能连续对话。安全验证请遵守官方流程，不建议关闭二次验证。

参考： https://github.com/Nex-Z/XiaoAiAgent 、https://github.com/yihong0618/xiaogpt 、https://github.com/idootop/mi-gpt/blob/main/docs/compatibility.md
