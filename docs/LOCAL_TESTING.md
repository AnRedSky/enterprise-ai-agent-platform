# 本地功能测试与验收步骤

> 目标：在 Windows 本地电脑完成 Enterprise AI Agent Platform 的功能验收。本文以 `main` 分支当前实现为准。

## 1. 当前完成度评估

| 模块 | 当前状态 | 本地验收方式 |
|---|---|---|
| FastAPI 基础 API | 已实现 | `/health`、Swagger |
| JWT 注册/登录 | 已实现 | 注册、登录、Bearer 鉴权 |
| RBAC | 已实现 | 普通用户/管理员隔离测试 |
| Agent Registry / Version | 已实现 | Agent 创建、版本查询、版本创建 |
| Session / Message | 已实现 | Chat 后查询消息 |
| Model Gateway | 已实现 Mock + OpenAI-compatible | Mock Chat、真实 Provider 可选 |
| SSE Chat Runtime | 已实现 | 浏览器/PowerShell 调用 `/stream` |
| Tool Registry / Tool Runtime | 已实现基础能力 | Schema、权限、超时、审计 |
| Memory | 已实现基础能力 | Chat memory context、过期/可见性测试 |
| Observability | 已实现核心链路 | Execution / Event / Token / Error 查询 |
| Runtime / Audit 查询 | 已实现 | RBAC、过滤、分页、Timeline |
| Vue 管理端 | 已实现基础页面 | Dashboard、Agents、Runtime、Audit |
| Phase 1.4-A Knowledge Registry | **本地手工验收通过** | `run_knowledge_registry_scenario.ps1` |
| Phase 1.4-B Document ingestion / Chunk | **已开发，待本地验收** | `run_knowledge_ingestion_scenario.ps1` |
| Retrieval / Runtime Knowledge | 待开发 | 后续 Phase 1.4-C/D |
| 生产级能力 | 尚未完整 | 监控、部署、高可用、密钥管理等仍需后续阶段 |

结论：**当前不是“全部生产完成”，而是 Phase 1.3 核心执行闭环已形成，Phase 1.4-A 已完成本地验收，Phase 1.4-B 已进入本地验收阶段。**

## 2. Windows 环境准备

### 2.1 启动 PostgreSQL 和 Redis

```powershell
docker compose up -d postgres redis
docker compose ps
```

### 2.2 配置后端

```powershell
cd backend
uv sync
```

### 2.3 数据库迁移

```powershell
uv run alembic upgrade head
```

Phase 1.4-B 新增 migration：`0008_knowledge_ingestion`。

### 2.4 启动后端

```powershell
uv run uvicorn app.main:app --reload --port 8000
```

## 3. 自动化测试

### Backend

```powershell
cd backend
uv run pytest -q
```

### Frontend

```powershell
cd frontend
npm install
npm test
npm run build
```

前后端测试脚本保持独立。

## 4. API 手工测试

既有 Identity、Agent、Runtime、Tool 等验收步骤保持不变。

## 5. SSE Chat 验收

既有 SSE 验收步骤保持不变，重点检查 `start` / `delta` / `done` 事件及 execution/trace 关联。

## 6. Session / Message 验收

既有 Session / Message 验收步骤保持不变。

## 7. Runtime / Observability 验收

既有 Execution、Timeline、AuditLog 验收步骤保持不变。

## 8. RBAC 手工验收

既有 Owner isolation、Admin cross-owner 验收步骤保持不变。

## 9. Tool Runtime 验收

既有 Tool Schema、权限、超时、审计、安全边界验收步骤保持不变。

## 10. Memory 验收

既有 Memory visibility、expiry、limit 验收步骤保持不变。

## 11. Vue 管理端验收

既有 Dashboard、Agents、Runtime、Audit 验收步骤保持不变。

## 12. Phase 1.4 Knowledge Registry 验收

### 12.1 Registry 场景

```powershell
cd backend
powershell -ExecutionPolicy Bypass -File .\scripts\run_knowledge_registry_scenario.ps1
```

当前已验证：

- Knowledge Base CRUD
- Document CRUD
- Version 创建与列表
- Document 分页
- 删除后 404
- Owner/RBAC 隔离

### 12.2 Document ingestion / Chunk 场景

```powershell
cd backend
powershell -ExecutionPolicy Bypass -File .\scripts\run_knowledge_ingestion_scenario.ps1
```

预期覆盖：

- Auth
- Knowledge Base / Document / Version
- 文本清洗
- 确定性 Chunk
- Chunk 持久化
- `pending → processing → ready`
- Chunk 与 Version 关联
- 同一 Version 重复摄取保持幂等

### 12.3 后端统一手工入口

```powershell
cd backend
powershell -ExecutionPolicy Bypass -File .\scripts\run_manual_test_suite.ps1 -Mode knowledge
```

`-Mode all` 会依次执行通用 API、Knowledge Registry、Knowledge ingestion 与 Backend regression tests；Frontend 测试仍由 `frontend/scripts/run_manual_frontend_suite.ps1` 独立执行。

## 13. Phase 1.4-B 重点验收项

1. Version 有 `ingestion_status`。
2. 摄取开始进入 `processing`。
3. 正常文本最终为 `ready`。
4. 空文本最终为 `failed` 并返回明确错误。
5. Chunk 必须关联 `document_version_id`。
6. Chunk `chunk_index` 在 Version 内唯一且从 0 递增。
7. `char_start / char_end` 可追溯原始清洗文本位置。
8. `content_hash` 稳定，可用于后续增量判断。
9. 重复摄取不会累积重复 Chunk。
10. 未授权用户不能读取其他 Owner 的 Version / Chunk。

## 14. 浏览器端安全验收

既有浏览器端 Token、受保护路由、URL 不泄露 Token 等验收步骤保持不变。

## 15. 最终验收记录模板

```text
测试日期：
Git commit：
Windows：
Python：
Node.js：
Docker：

[ ] docker compose postgres/redis
[ ] alembic upgrade head
[ ] /health
[ ] Swagger
[ ] 注册
[ ] 登录
[ ] 401 未认证
[ ] Agent CRUD/Version
[ ] SSE Chat
[ ] Session/Message
[ ] Execution
[ ] Timeline
[ ] AuditLog
[ ] RBAC owner isolation
[ ] Admin cross-owner
[ ] Tool schema/permission/timeout/audit
[ ] Memory visibility/expiry/limit
[ ] Vue Dashboard
[ ] Vue Agents
[ ] Vue Runtime
[ ] Vue Audit
[ ] Knowledge Registry scenario
[ ] Knowledge ingestion scenario
[ ] frontend npm test
[ ] frontend npm run build
[ ] backend uv run pytest -q

发现问题：
1.
2.
3.
```

## 16. 当前验收结论规则

- **通过**：自动化测试通过 + 当前阶段核心手工场景全部通过。
- **条件通过**：核心功能通过，但存在已知 warning/生产化缺口。
- **不通过**：认证、RBAC、数据隔离、Runtime 链路、Tool 安全边界或当前阶段核心 Knowledge 场景失败。
