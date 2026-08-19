# 开发命令参考

> 本文件用于后续维护，统一项目运行、测试、迁移与验收命令。

## Backend

```powershell
cd backend
uv sync
uv run alembic upgrade head
uv run pytest -q
uv run uvicorn app.main:app --reload
```

安装依赖：

```powershell
uv add <package>
uv add --dev <package>
uv sync
```

禁止：

```powershell
python -m alembic ...
alembic ...
pip install ...
python -m pytest ...
```

原因：项目 Backend 使用 `uv` 管理隔离环境。直接调用系统 Python 或全局命令可能命中其他 Python 安装，造成依赖缺失、版本不一致或 `ModuleNotFoundError`。

## Frontend

```powershell
cd frontend
npm ci
npm test
npm run build
```

开发服务：

```powershell
npm run dev
```

## Knowledge Runtime 场景

```powershell
cd backend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_runtime_knowledge_scenario.ps1
```

脚本内部的数据库迁移必须使用项目环境：

```powershell
uv run alembic upgrade head
```

## 完成判定

不能仅根据 `npm test` 判定前端完成。必须同时通过：

```text
npm test
npm run build
```

Backend 同理必须通过 pytest、Alembic migration 和领域手工场景。
