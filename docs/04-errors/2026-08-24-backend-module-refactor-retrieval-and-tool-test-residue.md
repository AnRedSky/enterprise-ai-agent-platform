# 2026-08-24 Backend Module Refactor：Retrieval 残留与 Tool Audit 元数据回归

## 1. 问题

本轮 Backend Module Refactor Gate 与本地 targeted tests 暴露两个独立问题：

1. Retrieval Evaluation 已完成物理迁移，但评估脚本与 Trace bootstrap 测试仍引用旧根 Service 路径：
   - `app.services.retrieval_evaluation_dataset`
   - `app.services.retrieval_evaluation_baseline`
   - `app.services.retrieval_evaluation_config`
   - `app.services.retrieval_evaluation_trace`
2. `tests/unit/test_tool_runtime_failures.py` 在干净 SQLite metadata 上执行 `Base.metadata.create_all()` 时，未注册 `workflow_executions`、`workflows`、`workflow_versions` 模型，导致 `AuditLog.workflow_execution_id` 的外键解析失败。

## 2. 根因

### 2.1 Retrieval

模块迁移只完成了正式 Service 目录物理迁移和部分调用方切换，评估脚本与测试存在 import residue。该问题违反模块迁移规则中的“所有调用方直接引用新模块”和“全仓旧路径为 0”要求。

### 2.2 Tool Runtime Test

Tool Runtime 测试本身只验证 Tool/Audit 行为，但 SQLite metadata 是全局 `Base.metadata`。`AuditLog` 与 Workflow Execution 之间存在真实外键关系，因此测试必须显式注册完整的关联模型，而不是删除或弱化数据库约束。

## 3. 修复

- 评估运行器统一从 `app.services.retrieval_evaluation` canonical package 导入公开能力。
- Trace bootstrap 测试统一使用 `app.services.retrieval_evaluation.RetrievalEvaluationTraceService`。
- Tool Runtime failure test 显式注册 `app.models.workflow` 与 `app.models.workflow_execution`，保持真实 SQLAlchemy 外键结构不变。
- 未新增兼容垫片、旧 Service 转发文件或第二套业务实现。

## 4. 验证要求

在本地 Backend 目录执行：

```powershell
uv run python -c "from app.main import app; print('APP_IMPORT_OK')"

uv run pytest -q `
  tests/unit/test_retrieval_evaluation.py `
  tests/unit/test_retrieval_evaluation_baseline.py `
  tests/unit/test_retrieval_evaluation_config.py `
  tests/unit/test_retrieval_evaluation_dataset.py `
  tests/unit/test_retrieval_evaluation_runner.py `
  tests/unit/test_retrieval_quality_gate.py `
  tests/unit/test_retrieval_evaluation_trace_bootstrap.py `
  tests/unit/test_vector_knowledge_retrieval.py

uv run pytest -q `
  tests/unit/test_tool_audit.py `
  tests/unit/test_tool_runtime.py `
  tests/unit/test_tool_runtime_service.py `
  tests/unit/test_tool_runtime_failures.py `
  tests/unit/test_tool_runtime_security.py

powershell -NoProfile -ExecutionPolicy Bypass `
  -File .\scripts\test\module-refactor\01_backend_module_refactor_gate.ps1
```

Gate 通过后继续执行完整 Backend Regression：

```powershell
uv run pytest -q
```

## 5. 完成标准

- `app.services.retrieval_evaluation_` 旧 import 全仓搜索结果为 0；
- Retrieval Evaluation targeted tests 全部通过；
- Tool Runtime targeted tests 全部通过；
- Module Refactor Gate 全部通过；
- Backend Regression 全部通过；
- 不因本次目录重构新增 Alembic Migration；
- 未引入兼容垫片或重复实现。

## 6. 状态

**修复已提交，待本地 Gate 与完整 Regression 验收。**

在验收未完成前，Retrieval Evaluation、Tool、Workflow、Trigger、Organization、Observability、Runtime Query、Session、Usage Accounting 均不得提前标记为“重构阶段最终完成”。
