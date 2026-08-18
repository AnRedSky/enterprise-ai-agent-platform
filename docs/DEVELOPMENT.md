# 开发文档

## 1. 技术基线

- Backend：FastAPI + Python 3.12
- Frontend：Vue 3 + TypeScript + Vite
- Database：PostgreSQL
- Cache：Redis
- Migration：Alembic
- Test：pytest / Vitest
- CI：GitHub Actions

## 2. 分层原则

```text
API → Service → Runtime → Gateway / Tool / Memory / Knowledge
                    ↓
                 Repository
                    ↓
               PostgreSQL / Redis
```

API 层只负责协议适配与鉴权；业务规则进入 Service；Agent 执行进入 Runtime；模型供应商差异必须封装在 Model Gateway；Tool 必须经过 Registry 和权限校验；Knowledge/RAG 必须保持独立领域边界，并通过 contract 接入 Runtime。

## 3. Agent 执行标识

每次执行至少保持以下关联：

`request_id`、`trace_id`、`session_id`、`agent_id`、`agent_version`、`model_id`、`execution_id`。

## 4. Phase 1.3 优先级

1. Model Gateway：OpenAI-compatible Provider、流式、Usage、超时与错误边界。
2. Tool Runtime：Schema、权限、超时、执行限制与审计。
3. Memory：Session 上下文与长期记忆基础能力。
4. Observability：执行链路、耗时、Token、错误与审计。
5. Vue 管理端：登录、Agent、Session、调试。

Phase 1.3 核心执行闭环已完成，后续开发不得破坏既有 Agent / Runtime / Tool / Audit 能力。

## 5. Phase 1.4 当前执行基线

Phase 1.4 目标为 Knowledge / RAG 闭环，按以下顺序推进：

1. Knowledge Registry：KnowledgeBase、Document、Version、Owner/RBAC、CRUD 与分页。
2. Document ingestion：parser、清洗、chunk、状态机与版本追踪。
3. Retrieval contract：Embedding、Retriever、Reranker contract，以及统一 source / score / citation 结果。
4. Runtime integration：Context Assembly、权限过滤、execution/trace 关联、citation/observability。
5. Frontend Knowledge 管理与 Retrieval Debug。
6. 联调与全量回归。

当前 main 分支已完成前端业务视图的模块化骨架：每个功能视图采用 `index.vue + components/`，`index.vue` 只负责页面入口和组件编排。Agents、Tools、Runtime、Dashboard、AuditLog、Login 均遵循该结构；旧 `_legacy` 不再作为运行时 UI 入口。

## 6. 前端目录与测试约束

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
- 前端业务组件不得依赖 `_legacy` 页面实现。
- 前端功能模块按 `index.vue → components/` 组织，复杂页面继续拆分为语义明确的子组件。
- 前后端手工测试脚本必须保持独立，不合并为单一业务测试文件。

## 7. 开发与联调顺序

每个 Phase 1.4 小版本必须按以下顺序推进：

1. Backend contract + migration + pytest
2. Frontend API types + Vitest
3. API scenario / 手工验收脚本
4. Runtime integration
5. 前后端联调
6. `backend pytest` + `frontend npm test` + `frontend npm run build`
7. 更新验收文档后直接提交 `main`

禁止先做孤立 UI，再反向修改 API；禁止前后端各自定义不同的领域模型。

## 8. 开发约束

- 所有 API 使用 `/api/v1`。
- 数据库结构必须通过 Alembic 迁移变更。
- 不提交 `.env`、密钥、日志、构建产物、IDE 配置、临时压缩包或个人文件。
- 不允许任意 Python、Shell 或未经授权的 URL 执行作为 Tool。
- 新功能必须有对应测试；修复必须补回归测试。
- Commit 使用 Conventional Commits，例如 `feat:`, `fix:`, `docs:`, `test:`, `chore:`。
- 统一只使用 `main` 分支开发，禁止创建新的功能分支。
