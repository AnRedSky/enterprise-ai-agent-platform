# 开发准则

> **唯一开发准则**：本文件是项目后续开发、联调、测试、验收与提交顺序的唯一工程执行基线。若其他文档与本文件冲突，以本文件为准，并在发现冲突后及时修正文档。

## 1. 技术基线

- Backend：FastAPI + Python 3.12
- Frontend：Vue 3 + TypeScript + Vite
- Database：PostgreSQL
- Cache：Redis
- Migration：Alembic
- Test：pytest / Vitest
- CI：GitHub Actions

## 2. 固定开发顺序

所有新功能必须严格按照以下顺序推进，禁止跳步或倒序：

```text
① 需求 / 架构文档确认
        ↓
② Backend Domain + API Contract
        ↓
③ Database Migration + Backend pytest
        ↓
④ Frontend API Types + Vitest
        ↓
⑤ Frontend UI（index.vue + components/）
        ↓
⑥ Backend API Scenario / 手工验收脚本
        ↓
⑦ Frontend / Backend 联调
        ↓
⑧ Runtime Integration（需要时）
        ↓
⑨ Backend pytest + Frontend npm test + Frontend npm run build
        ↓
⑩ 更新开发 / 验收文档
        ↓
⑪ 直接提交 main
```

### 强制规则

1. 后端 Contract 是前后端唯一业务契约，前端不得自行发明领域字段。
2. 涉及数据库的数据结构必须先有 Alembic migration，再开发依赖该结构的业务代码。
3. 后端 pytest 通过后，才进入前端 API 类型与 UI 实现。
4. 前端测试必须与业务源码分离；测试只放在 `frontend/tests/`。
5. Runtime Integration 必须在基础 API Contract 稳定、手工场景可验收后进行。
6. 联调完成后必须执行前后端全量回归和生产构建。
7. 验收文档必须在代码提交前同步更新，避免“代码已完成、规划仍显示待开发”。
8. 所有功能直接提交 `main`，禁止创建新的功能分支。

## 3. 分层原则

```text
API → Service → Runtime → Gateway / Tool / Memory / Knowledge
                    ↓
                 Repository
                    ↓
               PostgreSQL / Redis
```

API 层只负责协议适配与鉴权；业务规则进入 Service；Agent 执行进入 Runtime；模型供应商差异必须封装在 Model Gateway；Tool 必须经过 Registry 和权限校验；Knowledge/RAG 必须保持独立领域边界，并通过 contract 接入 Runtime。

## 4. Agent 执行标识

每次执行至少保持以下关联：

`request_id`、`trace_id`、`session_id`、`agent_id`、`agent_version`、`model_id`、`execution_id`。

## 5. Phase 1.3 优先级

1. Model Gateway：OpenAI-compatible Provider、流式、Usage、超时与错误边界。
2. Tool Runtime：Schema、权限、超时、执行限制与审计。
3. Memory：Session 上下文与长期记忆基础能力。
4. Observability：执行链路、耗时、Token、错误与审计。
5. Vue 管理端：登录、Agent、Session、调试。

Phase 1.3 核心执行闭环已完成，后续开发不得破坏既有 Agent / Runtime / Tool / Audit 能力。

## 6. Phase 1.4 当前执行基线

Phase 1.4 目标为 Knowledge / RAG 闭环，固定按以下顺序推进：

1. Knowledge Registry：KnowledgeBase、Document、Version、Owner/RBAC、CRUD 与分页。
2. Document ingestion：parser、清洗、chunk、状态机与版本追踪。
3. Retrieval contract：Embedding、Retriever、Reranker contract，以及统一 source / score / citation 结果。
4. Runtime integration：Context Assembly、权限过滤、execution/trace 关联、citation/observability。
5. Frontend Knowledge 管理与 Retrieval Debug。
6. 联调与全量回归。

当前开发位置：**Phase 1.4-B Document ingestion / Chunk 本地验收阶段**。Phase 1.4-A Knowledge Registry 已完成本地手工验收，后续不得跳过 1.4-B 的 migration、pytest、手工场景验收直接进入 Retrieval。

## 7. 前端目录与测试约束

Frontend 业务源码与测试严格分离：

```text
frontend/
├── src/
│   ├── api/             # API client / 类型
│   └── views/
│       └── <feature>/
│           ├── index.vue
│           └── components/
└── tests/
    ├── api/
    ├── views/
    └── setup.ts
```

- `frontend/src/` 禁止新增 `*.test.*`。
- Vitest 只执行 `frontend/tests/**/*.test.ts`。
- **Frontend 业务源码统一使用 TypeScript：API、router、composables/store 等代码必须使用 `.ts`；禁止 `.js` 与 `.ts` 同名实现并存。迁移完成后必须删除旧 `.js` 文件。**
- Vue 单文件组件统一使用 `<script setup lang="ts">`。
- 前端业务组件不得依赖 `_legacy` 页面实现。
- 每个功能模块使用 `index.vue + components/`；`index.vue` 只负责页面入口与组件编排。
- 前后端手工测试脚本必须保持独立，不合并为单一业务测试文件。

## 8. 文件命名与目录规则

文件命名必须表达**领域 + 职责 + 阶段**，禁止使用会造成语义歧义的名称。

### Backend

- API：`backend/app/api/<domain>.py`
- Model：`backend/app/models/<domain>.py`
- Schema：`backend/app/schemas/<domain>.py`
- Service：`backend/app/services/<domain>_service.py` 或已有明确职责命名。
- Test：`backend/tests/test_<domain>_<scope>.py`
- Migration：`backend/alembic/versions/<4位序号>_<domain_or_change>.py`
- 手工 API 场景：`backend/scripts/run_<domain>_scenario.ps1`

### Frontend

- API：`frontend/src/api/<domain>.ts`
- 页面入口：`frontend/src/views/<domain>/index.vue`
- 页面组件：`frontend/src/views/<domain>/components/<Purpose>.vue`
- API Test：`frontend/tests/api/<domain>.test.ts`
- View Test：`frontend/tests/views/<Domain>.test.ts`
- 前端手工测试：`frontend/scripts/run_manual_frontend_suite.ps1`，领域专项脚本可使用 `run_<domain>_scenario.ps1`。

### 禁止

- 禁止 `new_*`、`temp_*`、`test_*` 作为业务源码文件名。
- 禁止同一领域同时存在 `foo.py`、`foo_service.py`、`foo_manager.py` 且职责没有明确边界。
- 禁止 `.js` / `.ts` 同名业务实现并存；迁移完成后必须删除旧实现。
- 禁止把生成文件、缓存文件、测试产物放入业务源码目录。
- `_legacy` 只能作为明确的历史迁移目录，禁止作为运行时入口；迁移完成后应删除冗余实现。
- 若发现同一职责存在多个候选文件，先确定唯一 canonical 文件，再继续开发。

## 9. 开发、联调、测试与提交顺序

每个 Phase 1.4 小版本必须执行：

1. Backend contract + migration + pytest
2. Frontend API types + Vitest
3. Frontend UI
4. API scenario / 手工验收脚本
5. Runtime integration
6. 前后端联调
7. `backend pytest` + `frontend npm test` + `frontend npm run build`
8. 更新开发规划与验收文档
9. 直接提交 `main`

禁止先做孤立 UI，再反向修改 API；禁止前后端各自定义不同的领域模型。

## 10. 开发约束

- 所有 API 使用 `/api/v1`。
- 数据库结构必须通过 Alembic 迁移变更。
- 不提交 `.env`、密钥、日志、构建产物、IDE 配置、临时压缩包或个人文件。
- 不允许任意 Python、Shell 或未经授权的 URL 执行作为 Tool。
- 新功能必须有对应测试；修复必须补回归测试。
- Commit 使用 Conventional Commits，例如 `feat:`, `fix:`, `docs:`, `test:`, `chore:`。
- 所有开发直接提交 `main`，禁止创建新的功能分支。
