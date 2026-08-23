# Backend Runtime API 使用旧数据库依赖路径

## 1. 发现时间

2026-08-23

## 2. 现象

开发者本地执行 `uv run python run.py` 时，Uvicorn reload 子进程在导入 `app.main` 阶段失败：

```text
ModuleNotFoundError: No module named 'app.api.dependencies'
```

失败位置为 `backend/app/api/runtime.py`，该模块仍从已完成迁移的 `app.api.dependencies` 导入 `get_db`。

## 3. 根因

Backend 数据库 FastAPI 依赖已经收敛到 canonical `app.dependencies.db.get_db`，但 Runtime API 路由未同步完成 import 路径迁移，导致服务启动阶段才暴露旧入口引用。

该问题属于模块化整改中的“生产代码 import 未全量切换”问题，不应通过重新创建 `app.api.dependencies` 兼容垫片解决。

## 4. 修复

将 `backend/app/api/runtime.py` 的数据库依赖切换为：

```python
from app.dependencies.db import get_db
```

同时补充 Runtime API 模块中文职责说明，明确 API 层只负责协议、身份和租户上下文适配，查询业务规则继续由既有 Service 承担，避免产生第二套查询实现。

## 5. 验证要求

本次修复提交后必须由开发者本地实际执行：

```powershell
cd backend
uv run python -c "from app.main import app; print('APP_IMPORT_OK')"
uv run pytest -q
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\module-refactor\01_backend_module_refactor_gate.ps1
```

在开发者反馈实际结果前，不将上述测试标记为 Passed。

## 6. 工程纪律

禁止重新建立 `app.api.dependencies` 兼容入口、转发模块或第二套数据库 Session 实现。数据库 HTTP 依赖的正式入口保持 `app.dependencies.db`，其底层 Session 生命周期继续由 Infrastructure 层负责。
