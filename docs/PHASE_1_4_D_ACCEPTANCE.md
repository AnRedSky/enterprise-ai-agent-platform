# Phase 1.4-D：Runtime + Knowledge 联调验收记录

> 本记录用于固定 Runtime 与 Knowledge 的实际联调门禁，避免仅有单元测试通过而缺少真实链路证据。

## 验收链路

```text
Auth
  → Knowledge Base
  → Document
  → Version
  → Ingest
  → AgentVersion Knowledge Config
  → Runtime Chat
  → Citation
  → Audit / Observability
```

## 开发环境约束

- Backend 使用 uv 管理虚拟环境与依赖。
- Backend 的 Python / Alembic / pytest / 场景脚本统一使用 `uv run`。
- Frontend 使用 npm + package-lock 管理 Node 依赖。
- Frontend 必须同时通过 `npm test` 与 `npm run build`。
- 项目开发直接提交 `main`，不再创建功能分支。

## 联调门禁

- `uv sync`
- `uv run alembic upgrade head`
- `uv run pytest -q`
- `backend/scripts/run_runtime_knowledge_scenario.ps1`
- `frontend/npm test`
- `frontend/npm run build`

## 结果

Phase 1.4-D 的 Runtime Knowledge Scenario 已建立并完成本地回归，后续工作转入 Phase 1.4-F/G 的 Vue Knowledge / Retrieval Debug 前端深化。

## 维护要求

任何 Runtime / Knowledge Contract 变更必须同步更新：

1. Backend API / service contract
2. pytest
3. Runtime Knowledge Scenario
4. Frontend API types
5. Vitest
6. Production build
7. 本验收记录或阶段验收文档
