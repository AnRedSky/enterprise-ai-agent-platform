# 项目状态

## 当前阶段

- Repository: `AnRedSky/enterprise-ai-agent-platform`
- Branch: `main`
- 当前架构基线：远端 `main` 持续执行 Backend 模块化整改。
- Phase 2.2 Retrieval Production Quality：**已正式关闭**。
- Phase 2.3 Model Provider Governance：**已正式关闭**。
- 当前：**Phase 2.4 Durable Scheduler Contract-first + Persistence 第一版已完成；同时继续执行 Backend 模块化整改，主线任务暂停，直到既有重构任务全部完成。**

## 最新 main 基线

本轮继续直接基于远端 `main` 开发，所有代码变更直接提交 `main`，不创建兼容分支或兼容垫片。

开发准则明确要求：模块重构必须完成生产/测试 import 全量切换、旧文件删除、旧路径搜索为 0、重复实现检查、中文模块说明、targeted tests 与 Backend Regression 后才能标记完成；GitHub Actions 不作为开发测试或验收依据。

## 本轮实际代码变更

1. 完成 Model Service 从 `app/services/model_provider.py` 到 `app/services/model/` 的物理迁移。
2. 完成 Model Governance Contract 从 `app/services/model_provider_governance_contract.py` 到 `app/services/model/contract.py` 的迁移。
3. 完成 Model Routing 从旧 Contract 文件中独立归位到 `app/services/model/routing.py`，避免 API/Runtime 重复实现路由规则。
4. 完成 Runtime Model Governance 从 `app/services/runtime_model_governance.py` 到 `app/services/model/governance.py` 的迁移。
5. 完成 Model Gateway 从 `app/runtime/model_gateway.py` 到 `app/runtime/model/gateway.py` 的迁移。
6. 将 Model Provider Contract、OpenAI-compatible Provider、Mock Provider 统一收敛到 `app/infrastructure/providers/`。
7. 删除旧 Model Service、Governance、Runtime Provider 文件，不保留兼容垫片。
8. 更新 Chat、Workflow Runtime、Model Provider API 与 Model 相关测试的正式 import 路径。
9. Module Refactor Gate 增加 Model 目录、旧路径、旧 import、Provider 文件及 Model targeted tests 检查。
10. 新增/重构 Model 模块补充中文职责、边界和关键依赖说明。
11. 未新增数据库 Migration；Model 数据结构不因目录重构发生变化。
12. 修复 Model 迁移后 `UsageAccountingService` 对已删除旧 Contract 路径的残留引用，切换到 `app.services.model.contract` 正式入口。
13. 修复 Memory 治理测试对已删除 `app.services.memory_service` 的旧入口引用，切换到 `app.services.memory` 正式入口，并补充中文测试模块说明。
14. 修复 Workflow canonical import 后形成的 `WorkflowExecutionService -> WorkflowRuntime -> app.services.workflow` 循环依赖；Runtime 在未注入 Execution Service 时才延迟解析正式入口，不恢复旧模块。
15. 修复 Module Refactor Gate 的 PowerShell ParserError：统一明确字符串、数组、函数参数与 Gate 调用结构，并保留失败退出码传播。
16. 新增 `docs/04-errors/2026-08-24-backend-module-refactor-gate-parser-error.md`，记录 Gate 脚本解析错误及修复方案。

## 当前模块重构完成度

已完成：

- Agent
- Knowledge + Provider
- Memory
- Model + Provider

Workflow 当前状态：**代码迁移与 canonical import 已完成，领域 targeted tests 已恢复，但 Module Refactor Gate 因脚本 ParserError 尚未完成本地验收，因此暂不标记为迁移完成。**

仍未完成：

- Workflow Gate 最终验收
- Trigger
- Organization
- Governance
- Observability
- Tool
- API `v1/<domain>` 收敛
- Runtime 其他领域目录收敛

因此，**本轮仍不得转入新的业务主线开发**。后续继续按 Migration Map 逐领域完成物理迁移，直到全部重构单元满足验收条件。

## 本地验证原则

本轮代码修复不能由仓库端代替开发者本地测试。当前用户已实际反馈 Workflow targeted tests：`40 passed in 1.40s`，并确认 `from app.main import app` 返回 `APP_IMPORT_OK`；Module Refactor Gate 当前反馈为 PowerShell ParserError，因此 Gate 结果不得记录为通过。

### 当前修复后的完整本地验证流程

```powershell
cd backend

git fetch origin
git reset --hard origin/main
git log -3 --oneline

uv run python -c "from app.main import app; print('APP_IMPORT_OK')"

git grep -n -E "app\.services\.workflow_execution|app\.services\.workflow_governance|app\.services\.workflow_registry" -- "*.py"

uv run pytest -q `
  tests/unit/test_workflow_execution_state_machine.py `
  tests/unit/test_workflow_execution_concurrency.py `
  tests/unit/test_workflow_execution_idempotency.py `
  tests/unit/test_workflow_execution_governance.py `
  tests/unit/test_workflow_execution_retry_transition.py `
  tests/unit/test_workflow_governance.py `
  tests/unit/test_workflow_publish_governance.py `
  tests/unit/test_workflow_retry_budget.py `
  tests/unit/test_workflow_retry_policy.py `
  tests/unit/test_workflow_runtime.py `
  tests/unit/test_workflow_runtime_timeout.py `
  tests/unit/test_webhook_trigger.py

powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\module-refactor\01_backend_module_refactor_gate.ps1

uv run pytest -q
```

若 Gate 报告任何旧 import、旧模块路径或重复实现，必须修正实际引用后再次执行；**不得通过兼容垫片或重新暴露旧模块名绕过 Gate。**

## 下一执行任务：继续模块化整改

优先顺序保持：

1. Workflow：先完成修复后 Module Refactor Gate 本地验收并完成迁移记录；
2. Trigger 领域物理迁移：Scheduled / Webhook Trigger 统一进入 Trigger 子模块；
3. Organization / Governance / Observability 按实际职责完成领域收敛；
4. Tool Service 与 `app/tools/` 技术实现完成唯一 Runtime 边界；
5. API 收敛到 `app/api/v1/<domain>/`，保持现有 HTTP Contract 不变；
6. Runtime 其他领域目录完成职责收敛；
7. 全部重构领域逐一通过 Module Refactor Gate 后，才恢复 Phase 2.4 主线后续任务。

模块化目录、职责与迁移规则继续以 `docs/00-architecture/BACKEND_MODULE_ARCHITECTURE.md` 与 `docs/00-architecture/BACKEND_MODULE_MIGRATION_MAP.md` 为准。