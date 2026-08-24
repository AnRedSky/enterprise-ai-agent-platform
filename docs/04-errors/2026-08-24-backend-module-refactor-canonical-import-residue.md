# 2026-08-24 Backend 模块重构 canonical import 残留

## 1. 错误

Workflow Runtime 与 Trigger 领域完成物理迁移后，远端 `main` 仍存在两处已删除旧模块路径的残留引用：

- `app/services/workflow_scheduler/runtime.py` 仍引用已删除的 `app.services.workflow_trigger`；
- `tests/unit/test_circuit_breaker_half_open_concurrency.py` 仍引用已删除的 `app.services.circuit_breaker`。

因此出现：

```text
ModuleNotFoundError: No module named 'app.services.workflow_trigger'
```

以及 Module Refactor Gate 报告：

```text
Legacy import path still exists: app\.services\.circuit_breaker
```

## 2. 根因

领域代码完成物理迁移后，部分调度器和并发测试没有同步切换到新的正式入口。旧模块文件已删除，兼容垫片也被治理规则明确禁止，因此旧 import 不能继续工作。

## 3. 修复

- `app.services.workflow_trigger` → `app.services.trigger`；
- `app.services.circuit_breaker` → `app.runtime.workflow.circuit_breaker`；
- 为 CircuitBreaker 并发测试补充中文模块职责、边界和关键依赖说明；
- 不恢复旧文件、不新增兼容转发、不复制第二套实现。

对应提交：`0d3dba6 fix(refactor): finish canonical trigger and circuit imports`

## 4. 验证要求

本错误的修复结果必须由本地开发环境实际执行确认，不以 GitHub Actions 作为验收依据：

```powershell
cd backend
uv run python -c "from app.main import app; print('APP_IMPORT_OK')"
git grep -n -E "app\.services\.workflow_trigger|app\.services\.workflow_trigger_schedule|app\.services\.webhook_trigger|app\.services\.circuit_breaker" -- "*.py"
uv run pytest -q tests/unit/test_circuit_breaker.py tests/unit/test_circuit_breaker_half_open_concurrency.py tests/unit/test_workflow_trigger.py tests/unit/test_workflow_trigger_schedule.py tests/unit/test_webhook_trigger.py
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\module-refactor\01_backend_module_refactor_gate.ps1
uv run pytest -q
```

在上述命令未由本地实际执行并反馈前，不得记录 Module Refactor Gate 或 Backend Regression 已通过。
