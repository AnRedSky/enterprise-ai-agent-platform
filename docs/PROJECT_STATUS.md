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
15. 修复 Module Refactor Gate 的 PowerShell ParserError：重新明确脚本结构、失败退出码传播、旧路径检查、模块说明检查与 targeted tests 编排。
16. 新增错误记录，记录 Workflow/Trigger canonical import 残留及本轮修复要求。
17. 完成 Trigger 领域物理迁移：`WorkflowTriggerService`、scheduled/webhook 配置契约、`WebhookTriggerService` 统一归入 `app.services.trigger/`，删除三个旧根目录 Service 文件。
18. 更新 Workflow API、Webhook API 与 Trigger 单元测试的正式 import 路径，并为 Trigger 新模块补充中文职责、边界和关键依赖说明。
19. Module Refactor Gate 进一步收紧为全域 legacy path、重复实现、模块职责/边界说明、Trigger targeted tests 与 Backend Regression 的统一验收入口。
20. 修复 Trigger Scheduler 对已删除 `app.services.workflow_trigger` 的残留引用，切换到 `app.services.trigger` 正式入口。
21. 修复 CircuitBreaker 并发测试对已删除 `app.services.circuit_breaker` 的残留引用，切换到 `app.runtime.workflow.circuit_breaker`，并补充中文测试模块说明。
22. 修复剩余两个 Trigger 测试收集阶段旧 import：`test_webhook_trigger_integration.py` 与 `test_webhook_trigger_config.py` 统一切换到正式 `app.services.trigger` 入口，并记录错误原因。
23. 完成 Organization Service 物理迁移到 `app/services/organization/`，删除 `app/services/organization.py`，保留单一实现并通过 `__init__.py` 暴露正式入口。
24. 完成 Observability Service 物理迁移到 `app/services/observability/`，并同步将 Retrieval Evaluation Trace 的依赖切换到正式 Observability 入口。
25. 完成 `app/services/` 根目录剩余 Retrieval Evaluation、Runtime Query、Session、Tool Audit/Observability/RBAC/Repository/Runtime、Usage Accounting 的物理迁移为领域子模块包；原实现通过 blob 原样迁移，未新增第二套功能实现。
26. 为本轮新增领域包补充中文职责、边界与关键依赖说明；Retrieval Evaluation 统一通过 `app.services.retrieval_evaluation` 暴露质量指标、dataset、baseline、config 与 trace 能力。
27. 删除上述 root service 文件，不使用旧文件转发或兼容实现；当前尚未宣称 Module Refactor Gate / Backend Regression 已通过，必须由开发者本地实际执行确认。

## 当前模块重构完成度

代码迁移完成、待 Gate 验收：

- Agent
- Knowledge + Provider
- Memory
- Model + Provider
- Workflow
- Trigger
- Organization
- Observability
- Retrieval Evaluation
- Runtime Query
- Session
- Tool
- Usage Accounting

仍未完成：

- Module Refactor Gate 最终全量验收
- 生产代码与测试 import 全量旧路径搜索为 0 的本地确认
- Governance 领域其余职责收敛
- API `v1/<domain>` 收敛
- Runtime 其他领域目录收敛
- 全部重构领域的重复实现审查与 targeted tests

因此，**本轮仍不得转入新的业务主线开发**。后续继续按 Migration Map 逐领域完成物理迁移、旧路径清理、测试收敛与 Gate 验收，直到全部重构单元满足验收条件。

## 本地验证原则

本轮代码修复不能由仓库端代替开发者测试。用户此前已实际反馈 Workflow/Trigger targeted tests：`74 passed in 1.97s`，并确认前一基线 `from app.main import app` 返回 `APP_IMPORT_OK`；本轮新增的 root service 物理迁移尚无新的本地 Gate / Regression 通过结果。**在用户本地重新执行 Gate 前，不得记录 Gate 通过。**

### 当前完整本地验证流程

```powershell
cd backend

git fetch origin
git reset --hard origin/main
git log -8 --oneline

uv run python -c "from app.main import app; print('APP_IMPORT_OK')"

git grep -n -E "app\.services\.workflow_execution|app\.services\.workflow_governance|app\.services\.workflow_registry|app\.services\.workflow_trigger|app\.services\.workflow_trigger_schedule|app\.services\.webhook_trigger|app\.services\.circuit_breaker" -- "*.py"

uv run pytest -q `
  tests/unit/test_circuit_breaker.py `
  tests/unit/test_circuit_breaker_half_open_concurrency.py `
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
  tests/unit/test_webhook_trigger.py `
  tests/unit/test_workflow_trigger.py `
  tests/unit/test_workflow_trigger_schedule.py

powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\module-refactor\01_backend_module_refactor_gate.ps1

uv run pytest -q
```

如果 Gate 报告任何旧 import、旧模块路径、重复实现或模块说明缺失，必须修正实际引用后再次执行；**不得通过兼容垫片或重新暴露旧模块名绕过 Gate。**

## 下一执行任务：继续模块化整改

优先顺序保持：

1. 先在本地执行新版 Module Refactor Gate，取得本轮真实结构性 blocker；
2. 修复 Gate 暴露的生产/测试 import、模块说明或重复实现问题，并补充对应错误记录；
3. Workflow / Trigger / Organization / Observability / Retrieval Evaluation / Runtime Query / Session / Tool / Usage Accounting 逐领域完成 targeted tests 与迁移记录；
4. 完成 Governance 领域及 API `v1/<domain>` 收敛，保持现有 HTTP Contract 不变；
5. Runtime 其他领域目录完成职责收敛；
6. 全部重构领域逐一通过 Module Refactor Gate 与 Backend Regression 后，才恢复 Phase 2.4 主线后续任务。

模块化目录、职责与迁移规则继续以 `docs/00-architecture/BACKEND_MODULE_ARCHITECTURE.md` 与 `docs/00-architecture/BACKEND_MODULE_MIGRATION_MAP.md` 为准。
