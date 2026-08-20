# 开发命令参考

> 本文件用于后续维护，统一项目运行、测试、迁移与验收命令。测试脚本职责以 `backend/tests/README.md` 与 `backend/scripts/README.md` 为准。

## Backend 基础命令

```powershell
cd backend
uv sync
uv run alembic upgrade head
uv run pytest -q
uv run uvicorn app.main:app --reload
```

## Backend 三类 Gate

### 默认回归

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\regression\01_backend_regression.ps1
```

### Real API

必须在独立运行的 Backend 服务上执行；测试上下文由 bootstrap 自动准备，禁止手工填写 Token / Workflow ID / Execution ID。

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\api-real\01_run_real_api_tests.ps1
```

### 前后端联调 Gate

固定顺序为 Backend regression → migration/head → Real API → Frontend test/build → 浏览器人工联调。

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\integration\01_frontend_backend_gate.ps1
```

Real API Gate 未通过时，禁止进入前后端联调。

## Backend 阶段验收与专项脚本

阶段验收脚本统一归档到：

```text
scripts/test/phase/<phase>/
```

Knowledge/RAG、Embedding 等质量评估统一归档到：

```text
scripts/evaluation/knowledge/
scripts/evaluation/embedding/
```

开发辅助与本地场景复现统一归档到：

```text
scripts/dev/
```

这些目录均不是默认 pytest 回归或 Real API Gate 的替代入口。

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

Frontend 测试独立于 Backend，不由 Backend 测试脚本复制或代执行。

## Knowledge Runtime 开发场景

开发辅助场景统一使用：

```powershell
cd backend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\dev\run_runtime_knowledge_scenario.ps1
```

脚本内部的数据库迁移必须使用项目环境：

```powershell
uv run alembic upgrade head
```

## 完成判定

`pytest`、Real API、Frontend test/build 和前后端联调分别代表不同测试层级，不能相互替代。任何联调前必须先通过 Real API Gate。
