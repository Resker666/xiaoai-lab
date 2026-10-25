# XiaoAi-Lab development contract

## Scope and evidence

- Work in small changes tied to the current milestone and GitHub Issue. Finish M0 diagnostics before M1 integration; do not bundle M2–M4 features.
- Windows is the primary development machine. The Mac mini M4 (16 GB) is a separate Ollama/Qwen host; do not assume they share a LAN or that either has a model installed.
- The target is XiaoAi Play Enhanced L05C. Distinguish **software tested**, **upstream source claim**, **hypothesis**, and **hardware untested** in documentation and reports. Never infer real device support from mocks, an open TCP port, or a healthy HTTP endpoint.
- Real hardware, firmware version, account authorization and voice playback require a human experiment. Supply exact commands, version references and a record template. Keep acceptance unchecked until evidence exists.

## Architecture

- Prefer maintained upstream implementations for Xiaomi authentication, cloud protocols and voice bridging. Research upstream source/configuration at a recorded commit before copying instructions; respect its license.
- M0 remains Python 3.10+ with no third-party runtime dependencies. Use clear, typed, focused modules; use C only for justified embedded work.
- Keep diagnostics, CLI/report I/O, future bridge adapters, Agent logic and tools separate. `config/bridge.example.yaml` is an upstream reference, not a configuration consumed by this CLI.
- `doctor` checks the selected Ollama environment; `probe` connects only to one explicitly supplied numeric RFC1918 IPv4 host. No subnet discovery, credential attempts or application payloads. Validate every input before network activity; bound timeouts, port count and response size.
- TCP results describe connection outcomes, not SSH access, application identity or device compatibility. Cloud dialogue polling is not local microphone streaming or fully offline ASR.

## Privacy and device safety

- Never commit Xiaomi usernames/passwords, tokens, cookies, DID/MAC/serial numbers, actual device IPs, voice records, captures or raw debug logs. Use placeholders in examples.
- Keep reports under ignored `reports/` or outside the repository. Ignore rules are not redaction: manually inspect staged changes and any information intended for publication.
- Never flash firmware, unlock/root devices, brute-force credentials, change hardware wiring or send unknown write commands as part of routine development. Hardware work needs an explicit experiment scope and verified pin/electrical information.
- Preserve account security verification. Keep Ollama/bridge services on loopback by default; cross-machine access needs explicit network/access-control design.
- Future MCP/computer tools must use allowlists and confirmation for sensitive actions; never expose arbitrary shell execution.

## Tests and verification

From an installed project environment:

```text
python -m pip install -e .
python -m unittest discover -s tests -v
python -m compileall -q src tests
python -m xiaoai_lab --help
git diff --check
```

- First run existing tests to establish the baseline. For behavior changes/bug fixes, add a meaningful failing test, observe the failure, implement the smallest fix and run the complete suite.
- Automated tests must work without L05C, Xiaomi credentials, Ollama, internet or LAN access. Mock external socket boundaries; use a loopback HTTP server for HTTP contract tests. Never scan a real device during automated tests.
- Cover invalid inputs before network calls, refusals/timeouts/local network errors, malformed HTTP/JSON, CLI exit codes and report overwrite protection. Avoid tests that merely mirror constants or prose.
- Keep Windows/macOS/Linux and the minimum Python version in CI. Report exactly which environments ran locally and which were only configured for CI.

## Git and delivery

- Reuse a suitable checkout, create an independent branch, and deliver through a Pull Request. Do not push to main, merge a PR or rewrite shared history without explicit authorization.
- Before committing, inspect `git status`, the full staged diff and ignored report paths. Stage explicit files; avoid `git add .` with experimental data present.
- Every delivery explains the reason, affected files, exact tests/results and remaining issues. Link the Issue without automatically closing hardware acceptance based on software tests.
- Update documentation with any CLI/schema behavior change. Record upstream commit/date and separate source inspection from installation, inference and physical-device verification.
