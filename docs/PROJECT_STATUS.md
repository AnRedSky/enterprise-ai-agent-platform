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

本轮直接基于远端 `main` 继续提交，不创建兼容分支或兼容垫片。用户当前本地基线反馈为：

```text
1a9d195 fix(refactor): complete vector retrieval provider module description
6ac3112 fix(refactor): restore ollama embedding client type annotation
ed57fa8 fix(refactor): correct ollama embedding provider adapter signature
2b7f7c7 fix(refactor): complete ollama embedding provider module description
```

用户此前本地 Module Refactor Gate：

```text
APP_IMPORT_OK
Tool targeted tests: 8 passed
Workflow and trigger tests: 101 passed, 191 deselected
Backend regression: 383 passed, 2 skipped, 35 deselected
```

以上结果是用户实际反馈；本轮新增提交后的 Gate / Regression **尚未由本地环境重新执行，不预填通过**。

## 本轮新增整改

1. **Workflow Runtime canonical 化**
   - `app/runtime/workflow_runtime.py` 已物理删除。
   - `WorkflowRuntime` 已归位到 `app/runtime/workflow/runtime.py`。
   - `app/runtime/workflow/__init__.py` 统一暴露 `WorkflowRuntime`、Circuit Breaker。
   - `WorkflowExecutionService` 与 Workflow Runtime 测试全部切换到 canonical import。
   - 不增加兼容转发文件，不新增第二套 Runtime 实现。

2. **清理失效 Agent Runtime 残留**
   - 删除 `app/runtime/agent_runtime.py`。
   - 该旧模块未形成生产唯一执行入口，并引用已不存在的旧模型入口；继续保留会制造错误/重复 Runtime 边界。
   - 本轮不为目录结构制造空壳 `runtime/agent` 实现，后续仅在存在明确生产职责时建立 canonical Runtime。

3. **清理 Tool 重复实现**
   - 删除 `app/tools/registry.py`。
   - Tool 正式领域入口保持 `app.services.tool`。
   - `app.tools` 继续只承担 HTTP / Schema 等技术执行能力。

4. **测试目录边界整改**
   - `tests/test_dependency_boundary.py` 已迁移到 `tests/unit/test_dependency_boundary.py`。
   - Module Refactor Gate 新增 root `tests/test_*.py` 禁止检查。

5. **开发验证脚本目录整改**
   - `scripts/test_ollama_embedding.py` 已迁移为 `scripts/dev/validate_ollama_embedding.py`。
   - 修正脚本从新目录运行时的 Backend Root 定位。
   - Module Refactor Gate 增加 root-level Ollama 验证脚本残留检查。

6. **Module Refactor Gate 收紧**
   - 增加 canonical Workflow Runtime required file 检查。
   - 增加 `agent_runtime.py`、`workflow_runtime.py`、`app/tools/registry.py` 等旧路径检查。
   - 增加旧 import 搜索。
   - 增加 root `tests` 与开发脚本目录边界检查。
   - 继续强制 `职责：` / `边界：` 模块说明检查。

7. **文档同步**
   - 更新 `docs/00-architecture/BACKEND_MODULE_MIGRATION_MAP.md`，记录 Workflow Runtime、Tool Registry、测试与脚本目录的本轮归位。
   - 当前文档仍明确：API `v1/<domain>`、Governance、Runtime 其余领域等重构未完成，不得转入主线。

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

- Workflow：canonical Runtime 已完成，本地 Gate / Regression 待重新执行
- Tool：重复 Registry 已清理，本地 Gate / Regression 待重新执行
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

## 本轮提交

- `95496b1`：move workflow runtime into canonical module
- `4b2a748`：expose canonical workflow runtime entrypoint
- `6308d9c`：use canonical workflow runtime import
- `6ac279c`：update workflow runtime timeout test import
- `2a87a7e`：update workflow runtime unit test import
- `bbfac6a`：remove legacy workflow runtime module
- `e7cb8d8`：remove stale unused agent runtime module
- `a027cc5`：remove duplicate legacy tool registry
- `ed4a981` / `241a0bd`：move dependency boundary test to unit tests
- `01bf1d6`：enforce canonical runtime and test module boundaries
- `4cc2e44` / `054c74a`：move Ollama validation to `scripts/dev` and remove root-level script
- `616a59f`：update module migration documentation

当前远端 `main` 最新提交为 `616a59f6c89d61dcd05070a4cd63143bf322a18f`。

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

# 4. Ollama 本地 Embedding 环境验证（仅在配置并启动 Ollama 后执行）
uv run python .\scripts\dev\validate_ollama_embedding.py
```

如果 Gate 报告任何旧 import、旧模块路径、重复实现或模块说明缺失，必须修正实际引用后再次执行；**不得通过兼容垫片或重新暴露旧模块名绕过 Gate。**

## 下一执行任务

1. 开发者本地同步最新 `main`。
2. 执行 `01_backend_module_refactor_gate.ps1`，取得本轮真实 blocker。
3. 执行 `02_backend_dependency_boundary_gate.ps1`。
4. 对 Workflow / Tool / Runtime 其余领域完成 targeted tests、旧路径搜索、重复实现审查。
5. 完成 Governance 与 API `v1/<domain>` 收敛。
6. 全部重构领域通过 Module Refactor Gate + Backend Regression 后，才恢复 Phase 2.4 主线。

模块化目录、职责与迁移规则继续以 `docs/00-architecture/BACKEND_MODULE_ARCHITECTURE.md` 与 `docs/00-architecture/BACKEND_MODULE_MIGRATION_MAP.md` 为准。
