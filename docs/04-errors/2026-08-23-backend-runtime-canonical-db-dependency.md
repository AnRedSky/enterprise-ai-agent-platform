# Backend Runtime / Scheduler 使用旧数据库依赖路径

## 1. 发现时间

2026-08-23

## 2. 现象

开发者执行 `uv run python run.py` 时，Uvicorn reload 子进程在导入 `app.main` 阶段失败。

第一阶段错误：

```text
ModuleNotFoundError: No module named 'app.api.dependencies'
```

完成 Runtime API 依赖路径迁移后，继续暴露第二阶段错误：

```text
ImportError: cannot import name 'SessionLocal' from 'app.dependencies.db'
```

失败位置为 `backend/app/services/workflow_scheduler/runtime.py`。

## 3. 根因

Backend 数据库边界已经完成拆分：

- `app.dependencies.db.get_db`：唯一正式的 FastAPI 请求级数据库依赖适配入口。
- `app.infrastructure.db.SessionLocal`：唯一正式的应用服务层数据库 Session 工厂。
- Infrastructure 层负责 Engine / Session 生命周期；API 层不应创建第二套 Session 实现。

Runtime API 已经错误地继续引用旧的 `app.api.dependencies`，而 Scheduler Runtime 在迁移后又把 Infrastructure 层的 `SessionLocal` 错误地从 `app.dependencies.db` 导入。

这属于数据库依赖边界迁移未完成的 import 漏洞，不能通过重新增加 `SessionLocal` 转发、兼容模块或第二套数据库实现解决。

## 4. 修复

### Runtime API

保持：

```python
from app.dependencies.db import get_db
```

API 层继续只负责 FastAPI Handler 的数据库依赖适配。

### Scheduler Runtime

切换为：

```python
from app.infrastructure.db import SessionLocal
```

Scheduler Runtime 作为应用服务层直接使用 Infrastructure 提供的正式 Session 工厂，并继续复用既有 `WorkflowTriggerService` 执行 Scheduled Trigger，避免重复实现 Workflow 执行逻辑。

同时补充 Scheduler Runtime 中文模块职责说明，明确其只负责调度轮询、恢复窗口和幂等分发。

## 5. 验证要求

本次修复提交后必须由开发者本地实际执行：

```powershell
cd backend

uv run python -c "from app.main import app; print('APP_IMPORT_OK')"

uv run pytest -q

powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\module-refactor\01_backend_module_refactor_gate.ps1

powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\integration\01_scheduler_persistence_gate.ps1
```

服务启动验证：

```powershell
uv run python run.py
```

然后访问：

```text
http://127.0.0.1:8000/docs
```

在开发者反馈实际结果前，不将上述测试标记为 Passed。

## 6. 工程纪律

禁止：

- 重新建立 `app.api.dependencies` 兼容入口；
- 在 `app.dependencies.db` 中重新导出 `SessionLocal` 作为兼容垫片；
- 在 Scheduler Runtime 内创建独立 Engine / Session 实现；
- 重复实现 `WorkflowTriggerService` 已承担的 Scheduled Trigger 执行逻辑。

正式边界保持：

```text
FastAPI API
    -> app.dependencies.db.get_db
    -> app.infrastructure.db.get_db_session

Application Service / Scheduler
    -> app.infrastructure.db.SessionLocal
```
