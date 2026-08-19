# 07 - 项目开发规划

## 1. 项目背景

建设企业级 AI Agent 平台，提供 Agent 配置、版本治理、模型接入、会话、Memory、Tool、Runtime、权限、审计、可观测和 Knowledge/RAG 能力。

## 2. 项目目标

- 建立 FastAPI + Vue 的前后端工程基线。
- 建立可扩展的 Agent Runtime。
- 通过 Model Gateway 解耦模型供应商。
- 建立受治理的 Tool Runtime。
- 建立 Session / Memory 上下文能力。
- 建立 RBAC、审计和 Observability 基础。
- 建立 Knowledge / RAG 的文档、版本、分块、检索和引用闭环。
- 为后续 Workflow / Governance / Evaluation 扩展预留边界。

## 3. 技术栈

### Backend

- Python 3.12
- FastAPI
- Pydantic
- SQLAlchemy Async
- Alembic
- PostgreSQL
- Redis
- pytest

### Frontend

- Vue 3
- TypeScript
- Vite
- Element Plus
- Pinia
- Vitest

### Engineering

- GitHub
- GitHub Actions
- Docker Compose

## 4. 功能模块

1. Identity / Authentication
2. RBAC
3. Agent Registry
4. Agent Version
5. Session / Message
6. Model Gateway
7. Tool Registry / Runtime
8. Memory
9. Observability
10. Vue Admin Console
11. Knowledge / RAG
12. Workflow / Governance（后续阶段）
13. Evaluation（后续阶段）

## 5. 开发阶段计划

| 阶段 | 内容 | 状态 |
|---|---|---|
| Phase 1.0 | 工程初始化、FastAPI + Vue | 已完成 |
| Phase 1.2 | Identity、RBAC、Agent、Session、SSE、基础 Tool | 已完成 |
| Phase 1.3-A | Model Gateway | 已完成 |
| Phase 1.3-B | Tool Runtime | 核心能力已完成；后续继续生产化治理 |
| Phase 1.3-C | Memory | 核心能力已完成；后续继续生产化治理 |
| Phase 1.3-D | Observability | 核心执行链路已完成 |
| Phase 1.3-E | Vue 管理端深化 | 基础管理闭环已完成 |
| Phase 1.4-A | Knowledge Registry | **本地手工验收通过：CRUD、Version、分页、删除、Owner/RBAC 闭环通过** |
| Phase 1.4-B | Document ingestion / Chunk | **Backend contract / migration / parser-cleaner / deterministic chunk / persistence / API / pytest / 手工脚本已提交；待本地迁移与回归验收** |
| Phase 1.4-C | Retrieval contract | 待开发 |
| Phase 1.4-D | Runtime Knowledge integration | 待开发 |
| Phase 1.4-F/G | Vue Knowledge / Retrieval Debug | 待开发 |
| Phase 1.5 | Workflow / Governance | 后续 |

详细执行基线见 `docs/11-phase-1.4-knowledge-rag-plan.md`。

## 6. 固定前后端开发顺序

所有功能必须严格执行：

```text
需求 / 架构文档确认
  ↓
Backend Domain + API Contract
  ↓
Database Migration + Backend pytest
  ↓
Frontend API Types + Vitest
  ↓
Frontend UI（index.vue + components/）
  ↓
API Scenario / 手工验收脚本
  ↓
前后端联调
  ↓
Runtime Integration（需要时）
  ↓
Backend pytest + Frontend npm test + Frontend npm run build
  ↓
更新开发 / 验收文档
  ↓
main 提交
```

前端不复制后端业务规则；后端不依赖 Vue 页面结构。API contract 是唯一联调边界。完整规则以 `docs/DEVELOPMENT.md` 为准。

## 7. 测试目录规则

- Backend 测试统一位于 `backend/tests/`。
- Frontend 测试统一位于 `frontend/tests/`。
- Frontend `src/` 只存业务源码，不允许新增 `*.test.*`。
- Frontend Vitest 只执行 `frontend/tests/**/*.test.ts`。
- 前后端手工测试脚本必须保持独立，不合并成一个业务测试文件。

## 8. 文件命名规则

- Backend：API / Model / Schema / Service / Test / Scenario 分别使用明确的 `<domain>`、`<domain>_service`、`test_<domain>_<scope>`、`run_<domain>_scenario` 结构。
- Frontend：API 使用 `<domain>.ts`；页面入口使用 `views/<domain>/index.vue`；组件使用语义化 Purpose 名称；测试统一位于 `frontend/tests`。
- 禁止同职责 `.js` / `.ts` 并存、临时业务文件、无意义 `new_*` / `temp_*` 命名。
- `_legacy` 仅允许作为历史迁移目录，不得作为运行时入口。
- 发现同一职责存在多个候选文件时，必须先确定唯一 canonical 文件并清理冗余文件。

## 9. 分支规则

当前开发统一基于 `main` 最新代码。禁止创建新的功能分支；功能完成后直接提交 `main`。

## 10. Git Commit 规范

采用 Conventional Commits：

- feat
- fix
- refactor
- test
- docs
- chore

提交信息必须说明实现内容或修复细节。

## 11. 交付规则

每个功能模块必须同时交付：

1. 源代码
2. 数据库 Migration（如涉及数据结构）
3. 自动化测试
4. 编号开发文档
5. 规范 Git Commit
6. 手工验收脚本（需要手工验收时）
7. 验收结果与下一步计划

## 12. 禁止提交

严禁提交：

- `.env` / 密钥 / Token
- `node_modules`
- `.venv`
- `__pycache__`
- `dist`
- 日志
- 临时压缩包
- 临时截图
- 个人文件
- 与项目无关的实验文件
