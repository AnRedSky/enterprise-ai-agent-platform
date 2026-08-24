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

截至本轮：

- `7053f448`：补齐 `app/services/observability/service.py` 的 `职责：`、`边界：`、`关键依赖：` 模块说明，并为类及关键方法补充中文设计意图说明；不改变既有 Execution / ExecutionEvent 持久化职责，也未引入新的可观测性实现入口。
- `0c828a0e`：补齐 `app/services/knowledge/hybrid_service.py` 的 `职责：`、`边界：`、`关键依赖：` 模块说明，保持既有 Knowledge 服务复用关系不变。
- `4f44fb64`：记录 `hybrid_service.py` 模块说明 Gate 阻塞、分析与本地验证要求。
- `087d3d8f`：补齐 `app/services/workflow_scheduler/__init__.py` 的 `职责：`、`边界：`、`关键依赖：` 模块说明；该问题是在按 Gate 规则进行静态检查时提前发现并修复，未作为本地实际失败结果记录。

## 本轮实际代码变更

1. 完成 Model Service、Governance Contract、Routing、Runtime Governance、Model Gateway 与 Provider 的物理迁移。
2. 完成 Memory、Agent、Knowledge、Workflow、Trigger、Organization、Observability、Retrieval Evaluation、Runtime Query、Session、Usage Accounting 等既有迁移单元的代码归位，并持续执行最终 Gate 验收。
3. 修复 Workflow canonical import 循环依赖；修复 Trigger Scheduler、CircuitBreaker 与 Trigger 测试的旧入口残留。
4. 修复 Module Refactor Gate 的 PowerShell ParserError，并持续收紧旧路径、重复实现与模块说明检查。
5. 完成 Tool 领域的最终代码归位：`app.services.tool` 统一承载 Tool Runtime、RBAC、Audit、Observability 与 Repository；`app.tools` 仅承载 HTTP/Schema 技术执行。
6. 删除 `app/services/tool_audit`、`tool_observability`、`tool_rbac`、`tool_repository`、`tool_runtime_service` 五个旧领域包，不保留兼容转发。
7. 更新 Tool API 与受影响单元/集成测试到 `app.services.tool` 正式入口，避免测试通过旧模块名继续维持双入口。
8. 为 Tool 新模块补充中文职责、边界和关键依赖说明，并把 Tool 模块纳入 Module Refactor Gate 的 required files、legacy paths 与 targeted tests 检查。
9. 修复 Module Refactor Gate 的中文源码编码问题：模块说明检查改由 Python 按 UTF-8 读取，避免 Windows PowerShell 5.1 默认代码页导致正则字符串损坏。
10. 本轮没有新增数据库 Migration；目录重构不改变 Tool 数据结构。
11. 修正 Runtime Query Module Refactor Gate 的 canonical package 误报：删除会匹配正式 `app.services.runtime_query` package 的 legacy grep 规则，同时保留旧根文件 `app/services/runtime_query.py` 的物理路径检查；并为 Runtime Query Service 补充中文模块职责、边界与关键依赖说明。
12. 修复 Knowledge 模块说明 Gate 阻塞：`app/services/knowledge/__init__.py` 增加固定 `职责：`、`边界：` 与 `关键依赖：` 声明，不改变 Knowledge 与 Provider 的职责边界。
13. 按现有 Gate 的固定 `职责：` / `边界：` 校验规则持续补齐 Knowledge、Workflow Scheduler 等 required module description 文件。
14. 修复 `app/services/knowledge/hybrid_service.py` 的模块说明缺失，仅增加职责、边界与关键依赖说明；该服务继续复用既有词法检索、向量检索和混合融合服务，没有新增重复实现。
15. 修复 `app/services/observability/service.py` 模块说明缺失，补充职责、边界、关键依赖及关键方法中文 docstring；保持现有可观测性唯一服务入口与 Execution / ExecutionEvent 数据模型不变。

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

**当前最新用户反馈的直接 blocker 已修复：`app/services/observability/service.py` 缺少固定职责/边界/关键依赖模块说明。修复后尚未获得开发者新的 Gate 实际执行结果，因此不得预填 Gate Passed。**

因此，**本轮仍不得转入新的业务主线开发**。后续继续按 Migration Map 逐领域完成物理迁移、旧路径清理、测试收敛与 Gate 验收，直到全部重构单元满足验收条件。

## 本地验证原则

仓库端不能代替开发者本地测试。本轮用户此前反馈的 Workflow/Trigger targeted tests `101 passed, 191 deselected`、Retrieval Evaluation targeted tests `38 passed`、Tool targeted tests `11 passed` 均为用户实际反馈结果；**Module Refactor Gate 与完整 Backend Regression 尚无本轮通过结果，不得预填通过。**

### 当前完整本地验证流程

```powershell
cd backend

git fetch origin
git reset --hard origin/main
git log -8 --oneline

uv run python -c "from app.main import app; print('APP_IMPORT_OK')"

git grep -n -E "app\.services\.circuit_breaker|app\.services\.workflow_trigger|app\.services\.workflow_trigger_schedule|app\.services\.webhook_trigger|app\.services\.tool_audit|app\.services\.tool_observability|app\.services\.tool_rbac|app\.services\.tool_repository|app\.services\.tool_runtime_service|app\.services\.observability_service|app\.services\.retrieval_evaluation_" -- "*.py"

uv run pytest -q `
  tests/unit/test_tool_audit.py `
  tests/unit/test_tool_runtime.py `
  tests/unit/test_tool_runtime_service.py `
  tests/unit/test_tool_runtime_failures.py `
  tests/unit/test_tool_runtime_security.py `
  tests/unit/test_retrieval_evaluation.py `
  tests/unit/test_retrieval_evaluation_baseline.py `
  tests/unit/test_retrieval_evaluation_config.py `
  tests/unit/test_retrieval_evaluation_dataset.py `
  tests/unit/test_retrieval_evaluation_runner.py `
  tests/unit/test_retrieval_quality_gate.py `
  tests/unit/test_retrieval_evaluation_trace_bootstrap.py `
  tests/unit/test_vector_knowledge_retrieval.py `
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

1. 在本地同步最新 `main`，重新执行 Module Refactor Gate，取得下一条真实结构性 blocker；
2. 修复 Gate 暴露的生产/测试 import、模块说明或重复实现问题，并同步记录已经发生的工程错误；
3. 对 Workflow、Trigger、Organization、Observability、Retrieval Evaluation、Runtime Query、Session、Tool、Usage Accounting 逐领域完成 targeted tests 与迁移记录；
4. 完成 Governance 领域及 API `v1/<domain>` 收敛，保持现有 HTTP Contract 不变；
5. Runtime 其他领域目录完成职责收敛；
6. 全部重构领域逐一通过 Module Refactor Gate 与 Backend Regression 后，才恢复 Phase 2.4 主线后续任务。

模块化目录、职责与迁移规则继续以 `docs/00-architecture/BACKEND_MODULE_ARCHITECTURE.md` 与 `docs/00-architecture/BACKEND_MODULE_MIGRATION_MAP.md` 为准。
