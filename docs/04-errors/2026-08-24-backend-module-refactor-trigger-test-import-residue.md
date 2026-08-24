# 2026-08-24 Backend 模块重构 Trigger 测试 import 残留

## 1. 错误

Trigger 领域完成物理迁移并删除旧入口后，Backend Regression 仍有两处测试引用已删除的旧模块路径：

- `tests/integration/test_webhook_trigger_integration.py` 引用 `app.services.webhook_trigger`；
- `tests/unit/test_webhook_trigger_config.py` 引用 `app.services.workflow_trigger_schedule`。

旧模块文件已经删除，因此 `uv run pytest -q` 在测试收集阶段出现 `ModuleNotFoundError`。

## 2. 根因

Trigger 的正式入口已经统一为 `app.services.trigger`，但本轮迁移遗漏了 integration/unit 两个测试文件。根据模块重构规则，测试必须跟随生产代码迁移，不能恢复旧入口或增加兼容垫片。

## 3. 修复

- `WebhookTriggerService` 测试 import 切换为 `app.services.trigger`；
- `validate_trigger_config` / `verify_webhook_secret` 测试 import 切换为 `app.services.trigger`；
- 不恢复 `app.services.webhook_trigger`、`app.services.workflow_trigger_schedule`；
- 不增加兼容转发文件或第二套 Trigger 实现。

对应提交：`affc8f82 fix(refactor): switch remaining trigger test imports`

## 4. 本地验证要求

```powershell
cd backend

git fetch origin
git reset --hard origin/main

uv run python -c "from app.main import app; print('APP_IMPORT_OK')"

git grep -n -E "app\.services\.workflow_trigger|app\.services\.workflow_trigger_schedule|app\.services\.webhook_trigger|app\.services\.circuit_breaker" -- "*.py"

uv run pytest -q `
  tests/unit/test_circuit_breaker.py `
  tests/unit/test_circuit_breaker_half_open_concurrency.py `
  tests/unit/test_workflow_trigger.py `
  tests/unit/test_workflow_trigger_schedule.py `
  tests/unit/test_webhook_trigger.py `
  tests/unit/test_webhook_trigger_config.py `
  tests/integration/test_webhook_trigger_integration.py

powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\module-refactor\01_backend_module_refactor_gate.ps1

uv run pytest -q
```

在开发者本地重新执行前，不得声称上述 Gate 或 Regression 已通过。

## 5. 下一结构性 blocker

当前 Module Refactor Gate 在清除 Trigger 测试残留后预计会继续检查 `app/services/` 根目录。当前远端 main 仍存在 Organization、Observability、Retrieval Evaluation、Runtime Query、Session、Tool、Usage 等根目录 Service 文件；这些属于后续完整物理迁移工作，不能通过修改 Gate 排除，也不能使用兼容垫片绕过。
