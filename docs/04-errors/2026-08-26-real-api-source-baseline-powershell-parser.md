# 2026-08-26 — Real API Source Baseline PowerShell 脚本解析失败

## 1. 问题

Tenant Safe Real API Gate 在新增 Source Baseline 阶段无法进入业务测试，PowerShell 在解析 `scripts/dev/verify_real_api_source_baseline.ps1` 时直接报 `ParserError`。

典型错误包括：

```text
Unexpected token
The string is missing the terminator
Missing closing '}'
```

因此该问题发生在测试脚本解析阶段，不是 API、Worker、Scheduler 或 Workflow Runtime 业务错误。

## 2. 根因

旧版本脚本在 PowerShell 字符串中混用了 Python/其他语言风格的反斜杠转义，例如：

```powershell
f\"...\"
```

PowerShell 不使用反斜杠转义双引号；这种写法会破坏字符串解析。旧实现同时将 Git root、Backend root 和 `backend/tests/...` 路径假设绑定在一起，在 Backend 本身作为 Git root 的工作树中也存在路径解析风险。

## 3. 修复

已重写 `backend/scripts/dev/verify_real_api_source_baseline.ps1`：

- PowerShell 字符串统一采用合法单引号/双引号语法；
- 正则表达式使用 PowerShell 原生字符串，不再写入反斜杠转义双引号；
- 自动识别 Git root 下的 `tests/api_real` 或 `backend/tests/api_real`；
- 进入实际 Backend root 后再执行 `git status` 与文件读取；
- 增加 `datetime.utcnow()` 源码扫描；
- 保留 `HEAD == origin/main`、关键测试源码清洁、统一 claim-race helper 三项硬检查；
- 脚本仍只读，不启动、停止或重启任何服务。

## 4. 验收边界

该修复提交后必须由开发者本地执行：

```powershell
cd backend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\dev\verify_real_api_source_baseline.ps1
```

通过后再执行正式 Tenant Safe Real API Gate：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\api-real\01_run_real_api_tests_tenant_safe.ps1
```

本错误记录不预填上述命令的结果，只有开发者实际执行结果才能作为验收依据。
