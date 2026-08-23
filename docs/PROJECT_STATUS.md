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

## 当前模块重构完成度

已完成：

- Agent
- Knowledge + Provider
- Memory
- Model + Provider

仍未完成：

- Workflow
- Trigger
- Organization
- Governance
- Observability
- Tool
- API `v1/<domain>` 收敛
- Runtime 其他领域目录收敛

因此，**本轮仍不得转入新的业务主线开发**。后续继续按 Migration Map 逐领域完成物理迁移，直到全部重构单元满足验收条件。

## 本地验证原则

本轮代码提交由远端仓库直接完成，当前不能声称新增 Model 迁移已经在开发者本地执行通过。必须以用户本地实际输出作为测试结论。

### Model 本轮完整本地验证流程

```powershell
cd backend
uv sync --dev
uv run python -c "from app.main import app; print('APP_IMPORT_OK')"

# 1. Model 定向测试
uv run pytest -q tests/unit/test_model_gateway.py tests/unit/test_model_provider_governance_contract.py tests/unit/test_runtime_model_governance.py

# 2. 模块重构 Gate：会检查旧文件、旧 import、重复实现、Provider 边界及 Backend Regression
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\module-refactor\01_backend_module_refactor_gate.ps1

# 3. 全量回归（Gate 已执行一次；如需单独记录则再次执行）
uv run pytest -q
```

若 Gate 报告旧 Model import 或旧模块路径，必须修正实际引用后再次执行；**不得通过兼容垫片或重新暴露旧模块名绕过 Gate。**

## 下一执行任务：继续模块化整改

优先顺序保持：

1. Workflow 领域物理迁移：Registry / Execution / Governance 与 Runtime 分离；
2. Trigger 领域物理迁移：Scheduled / Webhook Trigger 统一进入 Trigger 子模块；
3. Organization / Governance / Observability 按实际职责完成领域收敛；
4. Tool Service 与 `app/tools/` 技术实现完成唯一 Runtime 边界；
5. API 收敛到 `app/api/v1/<domain>/`，保持现有 HTTP Contract 不变；
6. Runtime 其他领域目录完成职责收敛；
7. 全部重构领域逐一通过 Module Refactor Gate 后，才恢复 Phase 2.4 主线后续任务。

模块化目录、职责与迁移规则继续以 `docs/00-architecture/BACKEND_MODULE_ARCHITECTURE.md` 与 `docs/00-architecture/BACKEND_MODULE_MIGRATION_MAP.md` 为准。
