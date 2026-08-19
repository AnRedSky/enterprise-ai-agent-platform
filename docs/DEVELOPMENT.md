# 开发准则

> **唯一开发准则**：本文件是项目后续开发、联调、测试、验收与提交顺序的工程执行基线。若其他文档与本文件冲突，以本文件为准，并及时修正文档。

## 1. 技术基线

- Backend：FastAPI + Python 3.12+
- Backend 包管理与运行：**uv / `backend/.venv`**
- Frontend：Vue 3 + TypeScript + Vite
- Database：PostgreSQL
- Cache：Redis
- Migration：Alembic
- Backend Test：pytest
- Frontend Test：Vitest

## 2. 本地手动测试原则

项目开发阶段的测试、联调、验收均以**开发者本地手动执行**为准。

禁止把 GitHub Actions workflow 作为开发测试、质量门禁或验收依据；不得通过 workflow 代替本地测试。

每个需要测试的任务必须同时提供：

1. 明确的测试步骤；
2. 可重复执行的测试命令；
3. 必要时提供 `backend/scripts/*.ps1` 或 `frontend/scripts/*.ps1` 本地测试脚本；
4. 测试结果只能记录开发者实际执行并反馈的结果，不得预填未执行的“通过”；
5. 真实 Provider、数据库、外部 endpoint 等联调必须在本地完成。

## 3. 固定开发顺序

所有新功能严格按照以下顺序推进：

```text
① 需求 / 架构文档确认
        ↓
② Backend Domain + API Contract
        ↓
③ Database Migration + Backend pytest
        ↓
④ Frontend API Types + Vitest
        ↓
⑤ Frontend UI
        ↓
⑥ Backend API Scenario / 本地手工验收脚本
        ↓
⑦ Frontend / Backend 联调
        ↓
⑧ Runtime Integration（需要时）
        ↓
⑨ Backend pytest + Frontend npm test + Frontend npm run build
        ↓
⑩ 更新开发 / 验收文档
        ↓
⑪ 提交 main
```

### 强制规则

1. 后端 Contract 是前后端唯一业务契约，前端不得自行发明领域字段。
2. 涉及数据库的数据结构必须先有 Alembic migration，再开发依赖该结构的业务代码。
3. 后端 pytest 通过后，才进入前端 API 类型与 UI 实现。
4. 前端测试必须与业务源码分离；测试只放在 `frontend/tests/`。
5. Runtime Integration 必须在基础 API Contract 稳定、手工场景可验收后进行。
6. 联调完成后必须执行前后端全量回归和生产构建。
7. 验收文档必须在代码提交前同步更新。
8. 功能完成、延期、阻塞或范围变更时，必须同步更新状态文档。
9. 所有功能直接提交 `main`，不得创建新的功能分支作为长期开发分支。
10. Backend 的 Python 包安装、测试、脚本与服务运行统一使用 `uv run ...`。
11. 真实 Provider 的 endpoint、API key、model 等配置只能写入未提交的 `backend/.env`。
12. Secret 禁止提交到 Git 仓库。
13. 每项未完成任务必须明确责任角色、状态、开始时间、目标时间、阻塞项和资源依赖。
14. 代码、数据库 migration、API contract、配置、技术设计和文档之间必须建立可追溯关系。
15. 复杂业务规则、降级策略、兼容逻辑和 provider 替换策略必须通过代码注释与设计文档记录设计意图。

## 4. 分层原则

```text
API → Service → Runtime → Gateway / Tool / Memory / Knowledge
                    ↓
                 Repository
                    ↓
               PostgreSQL / Redis
```

API 层只负责协议适配与鉴权；业务规则进入 Service；Agent 执行进入 Runtime；模型供应商差异封装在 Model Gateway；Tool 必须经过 Registry 和权限校验；Knowledge/RAG 保持独立领域边界。

## 5. 测试体系

遵循：

```text
Unit Test
    ↓
Integration Test
    ↓
Agent / Retrieval Evaluation
    ↓
Load Test
    ↓
Production Verification
```

核心模块要求 Unit Test Coverage ≥ 80%，核心安全模块 ≥ 90%。

测试重点包括：

- API Contract
- Service / Domain
- Database / Migration
- Agent Runtime
- Tool Runtime
- Knowledge / RAG
- Memory
- RBAC / Security
- Observability
- Frontend API / UI

Knowledge / RAG 评测至少记录：

- Recall@K
- Precision@K
- MRR
- latency
- provider error rate

质量门禁不得通过隐藏 provider error 来提高成功率。

## 6. Phase 1.4 Knowledge / RAG 推进基线

固定顺序：

```text
Knowledge Registry
    ↓
Document Ingestion
    ↓
Retrieval Contract
    ↓
Runtime Knowledge Integration
    ↓
Lexical Retrieval
    ↓
Vector / pgvector Retrieval
    ↓
Hybrid Retrieval
    ↓
Retrieval Evaluation
    ↓
Retrieval Debug / Runtime Trace
```

### 当前阶段

**Phase 1.4-G-02 已完成：Runtime execution / trace 与 Retrieval Debug 关联已完成并通过本地 Backend 回归。当前主线进入 Phase 1.5 Workflow / Governance。**

G-02 已验证：

1. Runtime trace metadata contract 可持久化；
2. Retrieval span 可关联 `top_k / result_count / retrieval_sources / citations` 等真实元数据；
3. Runtime execution / events 查询继续遵守 RBAC scope；
4. 前端 Timeline 展示后端真实 metadata，不重新计算业务分数；
5. PostgreSQL migration `0012_execution_event_metadata` 已到 head；
6. 开发者本地 `uv run pytest -q`：**152 passed，0 warnings**。

### Phase 1.5 开发入口规则

Phase 1.5 开发基线已建立，具体范围、领域边界、状态机、数据模型、API contract、RBAC / audit 要求、验收场景与任务拆解统一见 `docs/13-phase-1.5-workflow-governance-plan.md`。

当前唯一下一开发项：**1.5-A Workflow Definition Contract**。在该 Backend Contract、Migration、pytest 与 Backend 手工验收完成前，不进入 Frontend Workflow UI，也不实现 Workflow Runtime Engine。

## 7. Git / 提交规范

采用 Conventional Commits：

```text
feat: 新增能力
fix: 修复问题
refactor: 重构
perf: 性能优化
test: 测试
docs: 文档
chore: 工程维护
security: 安全修复
```

提交前至少完成与本任务相关的本地测试，并在任务文档记录实际结果。

## 8. 文档闭环

每个任务完成后必须更新对应开发/验收文档，至少记录：

- 实现范围
- 涉及文件 / API
- 数据库变更
- 本地测试步骤与命令
- 实际测试结果
- 已知问题
- 解决方案
- 剩余风险
- 下一阶段任务
- 责任角色
- 目标时间

禁止仅通过聊天、Issue 或 Commit 信息作为唯一项目状态记录。
