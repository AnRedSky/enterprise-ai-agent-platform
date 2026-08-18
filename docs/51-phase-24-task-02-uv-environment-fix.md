# Phase 24 Task 02：uv 后端测试环境修复记录

## 本轮目标

承接 Phase 24 Task 02 的 Backend Runtime / Tool / Memory 验证，在进入全量 pytest 前，先消除 uv 项目管理切换带来的依赖配置不一致问题。

## 已修复

### 1. uv 项目依赖配置

`backend/pyproject.toml` 从空依赖改为后端运行时依赖的权威声明，并增加 dev dependency group：

- FastAPI / Uvicorn
- SQLAlchemy / asyncpg / Alembic
- Pydantic / pydantic-settings
- python-jose
- Passlib / bcrypt
- HTTPX
- pytest / pytest-asyncio / aiosqlite

同时加入 pytest 配置：

- `pythonpath = ["."]`
- `testpaths = ["tests"]`
- `asyncio_mode = "auto"`

### 2. Passlib / bcrypt 兼容性

固定 `bcrypt==4.0.1`，避免 Passlib 1.7.4 与新版 bcrypt 后端之间的兼容性问题，并保持 `requirements.txt` 与 `pyproject.toml` 一致。

### 3. CI 改为 uv 驱动

CI 改为：

```bash
uv sync --dev
uv run python -m compileall app
uv run pytest -q
```

并恢复 `push` / `pull_request` 自动触发，同时保留 `workflow_dispatch`。

### 4. 清理无效锁文件

当前仓库中的 `backend/uv.lock` 原先只包含空项目自身，没有反映真实依赖树，因此删除该陈旧锁文件，后续由：

```bash
cd backend
uv sync --dev
```

重新生成真实 `uv.lock`。

## 验证边界

本轮已完成代码与项目配置修复，但当前执行环境无法访问 Python Package Index，因此不能在这里虚构 `uv sync` / `pytest` 的最终通过结果。

用户本地应优先执行：

```bat
cd /d D:\works\AgentWorks\LocalDev\enterprise-ai-agent-platform\backend
uv sync --dev
uv run pytest -q
```

若 collection 正常，再继续按 Phase 24 Task 02 顺序验证 Runtime/RBAC、Tool Runtime、Memory、Model Gateway、Observability。

## 下一步

**保持当前任务不跨级完成：** 以 `uv run pytest -q` 的真实结果为准，先处理剩余失败，再进行全量回归；全部通过后再提交 Task 02 完成记录并进入下一任务。
