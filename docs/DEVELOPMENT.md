# 开发准则

> **唯一开发准则**：本文件是项目后续开发、联调、测试、验收与提交顺序的唯一工程执行基线。若其他文档与本文件冲突，以本文件为准，并在发现冲突后及时修正文档。

## 1. 技术基线

- Backend：FastAPI + Python 3.12+
- Backend 包管理与运行：**uv / `backend/.venv`**
- Frontend：Vue 3 + TypeScript + Vite
- Database：PostgreSQL
- Cache：Redis
- Migration：Alembic
- Test：pytest / Vitest
- CI：当前本地开发阶段**不执行、不配置、不触发 GitHub Actions CI**；后续进入部署阶段再单独启用。

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
⑤ Frontend UI（index.vue + components）
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
9. 当前本地开发阶段不得在 GitHub 仓库执行或触发 CI；测试由开发者本地同步代码后执行，并将结果反馈用于后续修复。
10. Backend 的 Python 包安装、测试、脚本与服务运行统一使用 `uv run ...`，禁止绕过项目 `.venv` 使用系统 Python 安装或运行项目依赖。
11. 本地真实 Provider 的 endpoint、API key、model 等配置必须写入未提交的 `backend/.env`；Git 仓库只维护 `.env.example`，禁止提交密钥。
12. **项目状态与可追溯性必须持续维护**：任何功能任务开始、完成、延期、阻塞或变更范围时，必须同步更新项目状态文档、相关技术/设计文档及必要代码注释；不得仅通过聊天、Issue 或 Commit 信息作为唯一记录。
13. **功能完成必须立即形成文档闭环**：任务完成后必须立即新增或更新对应开发/验收文档，至少记录实现细节、涉及文件/接口、测试命令及结果、已知问题、解决方案和剩余风险。
14. **每次任务文档必须包含下一阶段任务清单**：明确任务描述、优先级（P0/P1/P2/P3）、前置依赖和预期完成时间；已完成任务不得继续标记为待开发。
15. **任务必须有责任人**：每项未完成任务必须明确责任角色/责任人、当前状态、开始时间、目标时间、阻塞项和所需资源；任务发生转移时必须同步更新记录。
16. **时间节点必须可追踪**：计划至少记录里程碑、目标日期、实际完成日期；发生延期必须记录原因、影响范围和新的目标日期。
17. **资源协调必须显式记录**：真实 Provider、数据库、测试数据、开发环境、外部服务及其他依赖必须在任务计划中注明负责人和准备状态；不得将未确认的资源状态写成“已完成”。
18. **变更必须可追溯**：代码、数据库 migration、API contract、配置、技术设计和文档之间的关联应通过 Commit、任务记录、文档链接或明确的变更说明建立可追溯关系。
19. **代码注释应记录设计意图而非重复代码**：涉及复杂业务规则、降级策略、兼容逻辑、数据迁移和 provider 替换策略时，应补充必要注释，并与设计文档保持一致。
20. **测试结果必须真实记录**：文档只能记录开发者实际执行并反馈的测试结果；不得将未执行的本地测试、真实 Provider 联调或质量门禁写成通过。

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
6. Retrieval Evaluation：Evaluation Dataset + Recall@K / Precision@K / MRR。
7. 真实 Embedding / Vector DB provider 替换性验证。

当前开发位置：**Phase 1.4-E Retrieval Evaluation / Provider Replacement Validation**。1.4-A/B/C/D 已完成本地验收；1.4-E 已完成 lexical-v2 baseline、OpenAI-compatible Embedding contract、provider-neutral Vector Retrieval、pgvector indexing、vector retrieval API、显式 lexical fallback、5 条 Evaluation Dataset 与 baseline quality gate。

当前继续推进 **Retrieval Evaluation**：质量评估必须对 lexical-v2 与真实 vector provider 使用相同 Dataset、Knowledge Base scope、top-k 与相关性标注，并至少记录 Recall@K、Precision@K、MRR、平均 latency、provider error rate。质量门禁不得把 provider 错误隐藏在成功率之外。

本阶段新增 `RetrievalEvaluationObservation` 与 provider quality-gate runner；真实 provider 结果通过 JSONL 导入评测，不提交任何真实 endpoint、API key 或运行产物。当前质量门禁仍只允许本地执行，不执行 GitHub Actions CI。

### 6.1 Phase 1.4-E Vector Retrieval 配置

`backend/app/core/config.py` 与 `backend/.env.example` 必须同步维护以下配置：

```text
VECTOR_PROVIDER=none
VECTOR_DB_URL=
VECTOR_DB_COLLECTION=knowledge_chunks
VECTOR_TOP_K=5
VECTOR_MIN_SCORE=0.0
```

说明：

- `VECTOR_PROVIDER=none`：默认不连接真实 Vector DB。
- `VECTOR_DB_URL`：真实 Vector DB endpoint，由本地 `.env` 提供。
- `VECTOR_DB_COLLECTION`：向量集合/索引名称。
- `VECTOR_TOP_K`：默认向量检索返回数量。
- `VECTOR_MIN_SCORE`：向量相似度最低阈值，范围 `0..1`。
- Embedding 与 Vector DB 配置分离，禁止把具体供应商参数写死在 Knowledge Runtime。

## 6.2 项目功能状态与推进计划

本节是当前项目功能状态的统一摘要。详细实现证据以各 Phase 技术/验收文档、代码与本地测试反馈为准；状态不得与这些证据冲突。

### 已完成模块

| 模块 | 状态 | 完成范围 | 验收/证据 |
|---|---|---|---|
| Phase 1.3 Agent / Runtime 核心闭环 | 已完成 | Agent、Runtime、Tool、Audit 等既有执行链路 | 本地回归已建立；后续不得破坏 |
| Knowledge Registry | 已完成 | KnowledgeBase、Document、Version、Owner/RBAC、CRUD、分页 | Phase 1.4-A 验收文档 |
| Document Ingestion | 已完成 | parser、清洗、chunk、状态机、版本追踪 | Phase 1.4-B 验收文档 |
| Retrieval Contract | 已完成 | Embedding、Retriever、Reranker contract、source/score/citation | Phase 1.4-C 验收文档 |
| Runtime Knowledge Integration | 已完成 | Context Assembly、权限过滤、execution/trace、citation/observability | Phase 1.4-D 验收文档 |
| Knowledge Frontend / Retrieval Debug | 已完成 | Knowledge 管理及 Retrieval Debug UI/API | Phase 1.4-D/E 验收文档 |
| lexical-v2 baseline | 已完成 | 固定 Evaluation Dataset 与 lexical baseline | Phase 1.4-E 文档 |
| pgvector indexing / Vector Retrieval | 已完成实现 | embedding → vector index → vector retrieval、显式 lexical fallback | 代码与测试；真实 Provider 仍需本地验证 |
| Retrieval Evaluation Quality Gate | 已完成实现 | Recall@K、Precision@K、MRR、latency、error rate、baseline gate | runner + pytest；真实 Provider 结果尚待导入 |

### 未完成 / 待验收任务

| ID | 任务 | 优先级 | 状态 | 责任角色 | 目标时间 | 依赖/资源 |
|---|---|---|---|---|---|---|
| 1.4-E-01 | 使用真实 Embedding Provider 完成 5 条 Dataset 端到端向量入库与检索 | P0 | 待本地联调 | Backend / Knowledge | 2026-08-20 | 本地 `.env`、Embedding API、PostgreSQL/pgvector |
| 1.4-E-02 | 采集真实 vector `vector_results.jsonl` 并执行 Quality Gate | P0 | 待 01 完成 | Backend / QA | 2026-08-20 | 01、固定 Dataset、同一 top-k/scope |
| 1.4-E-03 | 比较 lexical-v2 与真实 vector 的 Recall/Precision/MRR/latency/error rate，确认是否达标 | P0 | 待 02 完成 | Knowledge / QA | 2026-08-20 | 02、baseline |
| 1.4-E-04 | 修复真实 Provider 联调发现的问题并补回归测试 | P0 | 待评测结果 | Backend | 2026-08-21 | 03、真实错误样本 |
| 1.4-E-05 | 完成 Provider Replacement Validation 验收文档与阶段结论 | P0 | 待 03/04 | Tech Lead | 2026-08-21 | 测试结果、配置说明、已知问题 |
| 1.4-F-01 | Hybrid Retrieval（lexical + vector）设计与 Contract | P1 | 未开始 | Architecture / Backend | 2026-08-24 | 1.4-E 验收通过 |
| 1.4-F-02 | Hybrid scoring / rerank 与 evaluation | P1 | 未开始 | Backend / Knowledge / QA | 2026-08-26 | 1.4-F-01 |
| 1.4-F-03 | Hybrid Retrieval UI / Debug 展示 | P1 | 未开始 | Frontend | 2026-08-27 | 1.4-F-02 |

> 时间节点是当前计划目标，不代表实际完成；发生延期必须在下一次状态更新中记录原因、影响和新目标日期。

### 责任与资源协调原则

- **Tech Lead / 架构**：维护状态基线、技术设计、任务优先级、跨模块依赖和最终阶段结论。
- **Backend / Knowledge**：负责 API contract、indexing、retrieval provider、错误边界、migration 与后端测试。
- **Frontend**：负责 API types、Knowledge UI、Retrieval Debug 和前端回归。
- **QA / 验收**：负责 Dataset 一致性、测试场景、Quality Gate、验收证据和已知问题登记。
- **开发环境负责人**：确保 PostgreSQL/pgvector、Embedding Provider、Redis 等本地依赖可用；真实密钥只进入未提交 `backend/.env`。

任何任务进入“阻塞”状态时，必须立即记录阻塞原因、责任方、资源缺口、影响任务和预计解除时间。

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
- 离线评测数据：`backend/evaluation/<domain>_dataset.jsonl`
- 离线评测 runner：`backend/scripts/evaluate_<domain>.py`

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

当前阶段所有测试均由本地开发环境执行。GitHub Actions CI 暂不作为本地开发验收环节。

### 9.1 功能任务完成后的强制文档闭环

每完成一个功能任务，必须在同一开发周期内立即更新对应文档，并至少包含以下内容：

```text
功能任务
├── 实现细节
│   ├── API / Contract
│   ├── Domain / Service
│   ├── Database / Migration（如适用）
│   ├── Frontend / UI（如适用）
│   └── 关键设计与代码注释
├── 变更记录
│   ├── Commit
│   ├── 涉及文件
│   └── 关联任务/里程碑
├── 测试结果
│   ├── Backend pytest
│   ├── Frontend npm test
│   ├── Frontend npm run build
│   └── 场景/真实 Provider 验收（如适用）
├── 已知问题 / 风险
├── 解决方案 / 临时措施
└── 下一阶段任务清单
    ├── 任务描述
    ├── 优先级
    ├── 责任角色
    ├── 前置依赖
    └── 目标时间
```

如果测试或真实 Provider 未执行，必须明确标记为“未执行/待验收”，不得以代码存在替代运行证据。

### 9.2 状态更新频率

- 任务开始：登记负责人、开始时间、目标时间和依赖资源。
- 任务完成：立即登记实际完成时间、Commit、测试结果和文档。
- 任务阻塞：立即登记阻塞原因、责任方、影响、资源缺口和解除时间。
- 任务延期：立即更新原因、新目标时间和影响范围。
- 阶段完成：更新阶段验收结论，并同步更新本文件第 6.2 节。

## 10. 开发约束

- 所有 API 使用 `/api/v1`。
- 数据库结构必须通过 Alembic 迁移变更。
- 不提交 `.env`、密钥、日志、构建产物、IDE 配置、临时压缩包或个人文件。
- 不允许任意 Python、Shell 或未经授权的 URL 执行作为 Tool。
- 新功能必须有对应测试；修复必须补回归测试。
- Commit 使用 Conventional Commits，例如 `feat:`, `fix:`, `docs:`, `test:`, `chore:`。
- 所有开发直接提交 `main`，禁止创建新的功能分支。
