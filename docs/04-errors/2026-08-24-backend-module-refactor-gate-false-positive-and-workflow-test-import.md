# Backend 模块重构 Gate：Workflow 测试旧入口与数据库依赖 Gate 误报

## 1. 发生时间

2026-08-24

## 2. 问题范围

Backend 模块化整改阶段的本地验证。

## 3. 实际现象

本地执行 Module Refactor Gate 时发现：

```text
tests/unit/test_workflow_execution_retry_transition.py:10:from app.runtime.workflow_runtime import WorkflowRuntime
Legacy import path still exists: app\.runtime\.workflow_runtime
```

同时，Backend Dependency Boundary Gate 在 canonical 数据库依赖已经位于 `app.dependencies.db` 的情况下，将所有 `from app.dependencies.db import get_db` 识别为 legacy dependency path，导致 Gate 失败。

完整 Backend Regression 的 collection error 同样来自 Workflow 测试的旧 import：

```text
ModuleNotFoundError: No module named 'app.runtime.workflow_runtime'
```

## 4. 原因分析

### 4.1 Workflow 测试迁移遗漏

生产代码已经统一使用 `app.runtime.workflow.WorkflowRuntime`，旧 `app/runtime/workflow_runtime.py` 已删除，但最后一个 Workflow retry transition 单元测试仍保留旧 import。该问题属于测试跟随领域迁移不完整，而不是生产 Runtime 缺少兼容入口。

### 4.2 Dependency Boundary Gate 规则错误

`app.dependencies.db` 按当前 Backend 模块架构是 canonical FastAPI 数据库依赖入口，负责向 API 提供数据库依赖，并复用 `app.infrastructure.db` 的 Session 实现。Gate 却把该 canonical 路径本身加入 legacy pattern，形成规则自相矛盾。

## 5. 修复

1. 将 `tests/unit/test_workflow_execution_retry_transition.py` 切换到 `from app.runtime.workflow import WorkflowRuntime`。
2. 为该测试补充中文模块职责与验证范围说明。
3. 从 Dependency Boundary Gate 删除 `app.dependencies.db` 的 legacy 匹配。
4. Dependency Boundary Gate 继续检查真正的历史路径：`app/api/dependencies.py`、`app.core.database`、`app.core.db`、`app.database`。
5. 不创建旧 Runtime 兼容垫片，不恢复旧模块路径，不增加第二套实现。

## 6. 验证要求

修复后必须由本地环境实际执行：

```powershell
cd backend
uv run python -c "from app.main import app; print('APP_IMPORT_OK')"
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\module-refactor\01_backend_module_refactor_gate.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\module-refactor\02_backend_dependency_boundary_gate.ps1
uv run pytest -q
```

本错误记录创建时，修复后的测试结果尚未执行，因此不得提前标记为通过。

## 7. 工程结论

模块重构必须同时完成生产代码 import、测试 import、旧文件删除、旧路径搜索和 Gate 规则一致性。Gate 自身不得把 canonical 路径定义为 legacy 路径；否则会阻断真实迁移验收并诱导错误的兼容实现。
