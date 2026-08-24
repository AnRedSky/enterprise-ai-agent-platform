# 项目状态

## 当前阶段

- Repository: `AnRedSky/enterprise-ai-agent-platform`
- Branch: `main`
- 当前架构基线：远端 `main` 持续执行 Backend 模块化整改。
- Phase 2.2 Retrieval Production Quality：**已正式关闭**。
- Phase 2.3 Model Provider Governance：**已正式关闭**。
- Phase 2.4 Durable Scheduler Contract-first + Persistence：**第一版已完成**。
- 当前：**继续执行 Backend 模块化整改，主线任务暂停，必须完成全部既有重构任务后才能恢复主线。**

## 最新 main 基线

本轮直接基于远端 `main` 继续提交，不创建兼容分支或兼容垫片。远端最新基线为：

```text
af7a127 fix(refactor): update workflow retry policy import
84e4550 fix(refactor): update workflow retry budget import
5ac383f fix(refactor): update workflow retry transition import
399946a fix(refactor): update workflow runtime test import
1b42b26 fix(refactor): use canonical workflow runtime import
2a29e09 fix(refactor): use canonical workflow runtime import
6bc137a test(refactor): update dependency gate for unit test boundary
```

本轮用户本地实际反馈：

```text
APP_IMPORT_OK
Module Refactor Gate: 失败，发现 tests/unit/test_workflow_execution_retry_transition.py 仍引用旧 WorkflowRuntime 路径
Dependency Boundary Gate: 失败，Gate 将 canonical app.dependencies.db.get_db 错误识别为 legacy
pytest: 1 个 collection error，原因同为旧 WorkflowRuntime 测试 import
```

以上结果来自用户本地实际执行；修复后的 Module Refactor Gate / Dependency Boundary Gate / Backend Regression **尚未由本地环境重新执行，不预填通过**。

## 本轮整改

1. **修复遗漏的 Workflow Runtime 测试 import**
   - `tests/unit/test_workflow_execution_retry_transition.py` 切换为 `from app.runtime.workflow import WorkflowRuntime`。
   - 补充测试模块中文职责与验证范围说明。
   - 不增加 `app/runtime/workflow_runtime.py` 兼容垫片。

2. **修正 Dependency Boundary Gate 的错误判定**
   - `app.dependencies.db` 是当前架构定义的 canonical FastAPI 数据库依赖入口，不属于 legacy 路径。
   - Gate 删除对 `app.dependencies.db` 的错误 legacy 匹配。
   - 保留旧 `app/api/dependencies.py`、`app.core.database`、`app.core.db`、`app.database` 等历史路径检查。
   - canonical implementation 继续要求 `app/dependencies` 复用 `app.infrastructure.db` Session。

3. **保持单一 Runtime / Provider / Service 入口**
   - Workflow Runtime 继续唯一使用 `app.runtime.workflow`。
   - 不恢复旧 Runtime 路径，不复制 Runtime 实现。
   - Provider 继续集中在 `app.infrastructure.providers`。

## 当前模块重构完成度

### 已完成代码迁移 / 进入最终 Gate

- Agent
- Knowledge + Provider
- Memory
- Model + Provider
- Trigger
- Organization
- Observability
- Retrieval Evaluation
- Runtime Query
- Session
- Usage Accounting

### 正在整改 / 尚未最终验收

- Workflow：canonical Runtime 已完成；本轮补齐最后遗漏测试 import 后，待本地 Gate / Regression 实际验收
- Tool：重复 Registry 已清理，待本地 Gate / Regression 实际验收
- Runtime：继续检查其他 Runtime 领域边界

### 尚未完成

- Module Refactor Gate 最终全量验收
- Backend Regression 最终全量验收
- 全量旧 import 搜索确认 0
- 全部重构领域重复实现审查
- Governance 领域其余职责收敛
- API `v1/<domain>` 收敛
- Runtime 其他领域目录收敛

**因此当前仍不得恢复 Phase 2.4 主线任务。**

## 文档与错误记录

本轮新增错误记录：

- `docs/04-errors/2026-08-24-backend-module-refactor-gate-false-positive-and-workflow-test-import.md`

错误记录说明：本轮本地反馈暴露了一个真实遗漏的测试旧 import，以及 Dependency Boundary Gate 对 canonical `app.dependencies.db` 的错误规则匹配。两者均属于模块重构 Gate 本身的工程问题，已在本轮修正。

## 本地自动化验证流程

```powershell
cd backend

git fetch origin
git reset --hard origin/main
git log -8 --oneline

uv run python -c "from app.main import app; print('APP_IMPORT_OK')"

# 1. 模块化 Gate：结构、旧路径、模块说明、targeted tests、Backend Regression
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\module-refactor\01_backend_module_refactor_gate.ps1

# 2. 数据库依赖边界 Gate
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\module-refactor\02_backend_dependency_boundary_gate.ps1

# 3. 全量回归（Gate 已执行，可单独再次确认）
uv run pytest -q
```

如果 Gate 报告任何旧 import、旧模块路径、重复实现或模块说明缺失，必须修正实际引用后再次执行；**不得通过兼容垫片或重新暴露旧模块名绕过 Gate。**

## 下一执行任务

1. 开发者本地同步本轮最新 `main`。
2. 重新执行 Module Refactor Gate，确认 Workflow 测试旧 import 已归零。
3. 执行 Dependency Boundary Gate，确认 canonical `app.dependencies.db` 不再被误报。
4. 若上述 Gate 通过，继续对 Workflow / Tool / Runtime 其余领域执行 targeted tests、旧路径搜索、重复实现审查。
5. 完成 Governance 与 API `v1/<domain>` 收敛。
6. 全部重构领域通过 Module Refactor Gate + Backend Regression 后，才恢复 Phase 2.4 主线。

模块化目录、职责与迁移规则继续以 `docs/00-architecture/BACKEND_MODULE_ARCHITECTURE.md` 与 `docs/00-architecture/BACKEND_MODULE_MIGRATION_MAP.md` 为准。
