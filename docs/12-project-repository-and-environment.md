# 项目仓库与开发环境维护记录

## 1. 项目仓库

- GitHub 仓库：`https://github.com/AnRedSky/enterprise-ai-agent-platform`
- 默认开发分支：`main`
- 项目代码、文档、测试与验收记录统一以该仓库 `main` 为当前工程基线。

## 2. Backend 使用 uv 管理

后端项目必须使用项目自身的 `uv` 环境运行与安装依赖，禁止使用系统 Python、全局 pip 或系统级 Alembic 代替项目环境。

Backend 技术基线：

- FastAPI
- Python `>=3.12`
- PostgreSQL
- Redis
- SQLAlchemy
- Alembic
- pytest
- 包管理：`uv`

依赖与环境文件：

```text
backend/
├── pyproject.toml
├── uv.lock
└── .venv/
```

其中 `.venv/` 为本地虚拟环境，不提交 Git；`pyproject.toml` 为依赖声明，`uv.lock` 为锁定依赖版本。

## 3. Backend 标准操作

进入后端目录后，所有 Python/Alembic/pytest 操作优先通过 `uv run`：

```powershell
cd backend
uv sync
uv run alembic upgrade head
uv run pytest -q
```

启动服务：

```powershell
uv run uvicorn app.main:app --reload
```

安装运行依赖：

```powershell
uv add <package>
```

安装开发依赖：

```powershell
uv add --dev <package>
```

同步锁定环境：

```powershell
uv sync
```

## 4. 后端手工验收脚本

所有 Backend 手工场景脚本也必须使用项目 `uv` 环境。脚本内部调用 Python、Alembic 或 pytest 时，不得依赖机器上的全局 Python/Alembic。

例如 Runtime + Knowledge 场景应确保数据库迁移使用：

```powershell
uv run alembic upgrade head
```

而不是：

```powershell
python -m alembic upgrade head
alembic upgrade head
```

这样可以避免 Windows 环境中 `python`、`alembic` 指向其他 Python 安装，导致 `ModuleNotFoundError` 或依赖版本不一致。

## 5. Frontend 环境

Frontend 使用 Node.js + npm：

```powershell
cd frontend
npm ci
npm test
npm run build
```

前端业务源码统一使用 TypeScript / Vue SFC：

- API：`.ts`
- Vue 页面与组件：`.vue` + `<script setup lang="ts">`
- 测试：`tests/**/*.test.ts`
- 禁止恢复旧 `.js` / `.jsx` 业务实现。

## 6. 开发与验收原则

每次功能完成后至少执行：

```text
Backend uv sync / pytest
        ↓
Alembic migration upgrade
        ↓
Backend scenario
        ↓
Frontend npm test
        ↓
Frontend npm run build
        ↓
前后端联调
        ↓
更新开发/验收文档
        ↓
提交 main
```

特别注意：**测试通过不等于生产构建通过**。前端 Vitest 与 `vue-tsc -b && vite build` 必须同时通过后，才能认为前端功能完成。

## 7. 提交约束

- 所有功能直接提交 `main`，不创建功能分支。
- Commit 使用 Conventional Commits，例如 `feat:`, `fix:`, `docs:`, `test:`, `chore:`。
- 不提交 `.env`、密钥、`backend/.venv`、`frontend/node_modules`、构建产物及临时文件。
- 新增 Python 依赖必须通过 `uv add` / `uv add --dev` 管理，并同步 `uv.lock`。
