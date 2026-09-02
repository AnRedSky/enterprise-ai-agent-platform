# Scheduler Service Lifecycle Gate PowerShell ParserError

## 1. 发生时间

2026-09-02

## 2. 现象

开发者在 Windows PowerShell 执行：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\workflow\03_scheduler_service_lifecycle_gate.ps1
```

脚本未进入 pytest 阶段，直接在 PowerShell 解析阶段失败，错误包括：

```text
Array index expression is missing or not valid.
The string is missing the terminator: ".
ParserError / MissingArrayIndexExpression
```

同一基线下，`uv run pytest -q -W error tests/unit/test_service_entrypoints.py` 已通过，说明本次阻塞发生在 Gate 编排脚本解析层，而不是 Scheduler Service 生产实现层。

## 3. 根因

Gate 脚本包含中文输出文本。开发者本地 Windows PowerShell 环境对该 UTF-8 文本的读取/解析发生字符集错位，导致字符串内容被错误解码并进一步触发 PowerShell 字符串解析错误。

该问题属于测试入口的跨 Windows PowerShell 编码兼容性问题，不应通过修改 Scheduler Service 生产代码规避。

## 4. 修复

将 `backend/scripts/test/workflow/03_scheduler_service_lifecycle_gate.ps1` 的运行时输出统一为 ASCII 文本，同时保持以下行为不变：

- 使用 `Set-StrictMode -Version Latest`；
- pytest 使用 `-W error`；
- 自动检查受保护服务进程边界；
- 不创建、启动、重启或停止 API、Scheduler、Worker、PostgreSQL、Redis；
- 生命周期测试数据继续由 Mock 自动提供，不要求人工填写 ID、凭据或业务数据；
- 任一测试失败或发现测试期间新增受保护进程时 Gate 立即失败。

## 5. 验证要求

修复后必须在开发者 Windows 环境执行：

```powershell
uv run pytest -q -W error tests/unit/test_service_entrypoints.py
uv run pytest -q -W error tests/unit/test_service_entrypoints.py -k "scheduler_service"
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\workflow\03_scheduler_service_lifecycle_gate.ps1
```

本错误记录只描述已经发生的 ParserError；修复后的 Gate 是否通过，以开发者实际执行结果为准。
