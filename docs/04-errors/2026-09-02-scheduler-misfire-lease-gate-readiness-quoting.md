# 2026-09-02 Scheduler Misfire / Lease Gate PostgreSQL Readiness 引号解析错误

## 1. 现象

开发者在 Windows PowerShell 本地执行：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\phase-2.4\21_scheduler_misfire_lease_gate.ps1
```

Gate 在 PostgreSQL readiness 阶段输出：

```text
File "<string>", line 8
    await connection.execute(text(SELECT
                                 ^
SyntaxError: '(' was never closed
[NOT EXECUTED] PostgreSQL is not ready; no service lifecycle action was attempted.
```

因此后续 misfire unit regression 与 lease expiry PostgreSQL acceptance 均未执行。

## 2. 根因

Gate 原实现通过 PowerShell 变量保存多行 Python 程序，再使用 `uv run python -c $readiness` 执行。虽然 Python 程序在 PowerShell here-string 中包含合法的嵌套引号，但 `-c` 参数经过 PowerShell / 进程参数边界后存在引号重解析风险，最终传递给 Python 的源码变成了类似：

```python
await connection.execute(text(SELECT 1))
```

Python 因此在 readiness 阶段直接产生 `SyntaxError`。该错误属于测试编排脚本的参数传递缺陷，不是 PostgreSQL readiness 失败，也不是 Scheduler 生产代码缺陷。

## 3. 修复

将 readiness Python 程序改为通过标准输入交给 Python：

```powershell
$readiness | uv run python -
```

这样完整的 Python 源码不会再经过 `python -c` 的命令参数引号重解析，同时保留原有 async SQLAlchemy readiness 检查。

## 4. 边界与治理符合性

- 未增加任何 API、Scheduler、Worker、PostgreSQL 或 Redis 的自动启动、重启、停止逻辑。
- PostgreSQL 不可用时仍只输出 `NOT EXECUTED`，不伪装成业务测试失败。
- misfire 与 lease acceptance 仍由独立测试实现负责断言，Gate 只负责前置检查和顺序编排。
- 所有测试数据继续由测试自动生成，不要求开发者手工填写 ID、tenant 或业务数据。
- 后续本地执行必须以开发者实际输出作为验收证据。

## 5. 后续验证

修复后重新执行：

```powershell
cd backend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\phase-2.4\21_scheduler_misfire_lease_gate.ps1
```

若 Gate 通过，再进入 Scheduler Runtime Real PostgreSQL Acceptance；若失败，应根据新的实际 traceback 继续定位根因，不将本次脚本 SyntaxError 与 Scheduler 业务实现混淆。
