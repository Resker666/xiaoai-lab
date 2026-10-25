# 发布与同步 GitHub（Resker666/xiaoai-lab）

仓库已创建： https://github.com/Resker666/xiaoai-lab

## 首次克隆

```bash
git clone https://github.com/Resker666/xiaoai-lab.git
cd xiaoai-lab
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
xiaoai-lab doctor
```

Windows PowerShell 激活虚拟环境的命令是 `.\.venv\Scripts\Activate.ps1`（如执行策略禁止，可用 `.\.venv\Scripts\python.exe` 直接运行 Python）。

## 以后同步

```bash
git pull --ff-only
git switch -c feat/your-small-change
git status --short
git add <EXPLICIT_REVIEWED_FILES>
git commit -m "docs: record sanitized L05C findings"
git push -u origin feat/your-small-change
# 在 GitHub 从此分支向 main 创建 Pull Request，说明 Issue、变更和验证证据。
```

同步已有工作分支前先确认当前分支及工作区状态；不要覆盖其他人的未提交变更。合并 PR 和推送 main 需要维护者明确确认，不是日常交付步骤。真机尚未验收时，PR 使用 `Refs #1`，不要自动关闭 M0 Issue。

不要在已有远端仓库上再次执行 `gh repo create` 或 `git init`；如果从旧 ZIP 工作目录迁移，请优先重新 `git clone` 再复制你需要的未跟踪实验笔记（必须脱敏）。

提交前检查：

```bash
git status --short
git diff --cached --stat
git diff --cached
git check-ignore reports/doctor.json reports/probe.json
```

确认没有 `.env`、小米账户、密码、Token、设备 DID、IP 和语音原始记录。敏感调试日志保留在仓库外。
