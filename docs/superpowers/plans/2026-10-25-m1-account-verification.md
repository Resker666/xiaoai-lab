# M1 account verification compatibility plan

**Problem:** The fixed XiaoAiAgent account implementation indexes `userId` after a code=0 response. Xiaomi can instead return a verification challenge with no completed credentials. The owner's trace proves the indexing failure, but not the actual server response or a wrong password.

**Approach:** Reuse Yonsm/MiService's existing SMS/email verification implementation at a pinned, inspected commit. Add an optional launcher that replaces only the separately cloned upstream's exported account class at runtime. Keep M0 dependency-free and leave upstream tracked source unchanged. Do not implement authentication endpoints or disable account security.

## Interfaces and constraints

- `build_account_class(backend_class, on_failure=None)` returns a compatible subclass, supplies an interactive hidden OTP callback, and converts failed authentication into `LoginNotComplete(reason, code)` containing only allowlisted diagnostic information. The callback preserves a failure exit code even when upstream catches that error.
- `main(argv=None)` accepts `--upstream` and `--list-devices`, validates required environment variables before importing/running the optional backend, patches the account export before importing upstream main, and forwards listener execution only when effective configuration matches MI_DID. Device listing calls the existing MiNAService directly, avoiding upstream's unsafe failure advice.
- Use only the owner's current terminal for real credentials and OTP. All automated verification is offline. Never inspect another process's environment or dump an authentication response, verification URL, cookie, token or username.
- Suppress the optional backend's authentication logging because its exception messages may contain raw responses. Preserve account safety features and the normal device selection flow.
- Pin external dependency to Yonsm/MiService commit `a1727f7817819cae89f20ea197c030aaa199b96d`; its source has SMS/email handling not present in XiaoAiAgent's embedded account implementation. Record the PyPI/source version distinction.

## Tasks

- [x] Add failing tests for code=0 verification challenges, credential/CAPTCHA/rate-limit errors, malformed responses, secret-free messages, successful callback forwarding, stale error reset, and preflight rejection without network/import side effects.
- [x] Implement the optional adapter and launcher; run the complete M0 suite and optional-backend offline contract tests.
- [x] Verify the real pinned backend's challenge dispatch with synthetic responses and a fake OTP flow. This does not prove a real account can log in.
- [x] Update the M1 instructions with one-command retry from the owner's existing terminal; preserve the original entrypoint as a documented alternative.
- [x] Independent read-only review and fresh verification; deliver through a feature-branch PR. Real account verification and voice playback remain pending user execution.

Review caught two issues, now covered by regressions: checking MI_DID without checking effective YAML configuration could still select the first device, and forwarding upstream device-list errors printed advice to disable two-step verification. Listener configuration is now checked before execution; device listing calls the existing service directly. The reviewer reran all 19 authentication tests after these changes and found no blocking regression.

## Review focus

- No raw response/exception text or credentials in surfaced errors/logs.
- Genuine verification callbacks are delegated to the existing library; no fabricated success or bypass.
- Original XiaoAiAgent source and account cache remain intact.
- Missing environment variables or device selection cannot start a login/listener.
- M0 imports, CLI and tests continue without the optional package.
