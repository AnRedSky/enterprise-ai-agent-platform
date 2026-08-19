# 开发准则

> **唯一开发准则**：本文件只维护项目工程开发、测试、验收、分支与提交规则，不记录项目阶段进度。阶段进度统一维护在 `docs/PROJECT_STATUS.md` 及对应 Phase 计划文档中。
>
> 若其他工程规则文档与本文件冲突，以本文件为准，并及时修正文档。

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
5. **前后端测试严格隔离**：Backend 测试脚本只能执行 Backend migration / pytest / Backend API Scenario，不得调用 `npm test`、`npm run build` 或混入 Frontend 测试；Frontend 测试必须独立执行。
6. Runtime Integration 必须在基础 API Contract 稳定、手工场景可验收后进行。
7. 联调完成后必须执行前后端全量回归和生产构建。
8. 验收文档必须在代码提交前同步更新。
9. 功能完成、延期、阻塞或范围变更时，必须同步更新 `docs/PROJECT_STATUS.md` 与对应 Phase 计划文档。
10. **禁止创建任何功能分支、临时分支、开发分支或长期分支；所有开发、修复、文档与测试变更均直接基于并提交 `main`。**
11. 开发前必须以远端 `main` 为当前基线，先同步 / 拉取 `main` 的最新代码，再开始修改。
12. Backend 的 Python 包安装、测试、脚本与服务运行统一使用 `uv run ...`。
13. 真实 Provider 的 endpoint、API key、model 等配置只能写入未提交的 `backend/.env`。
14. Secret 禁止提交到 Git 仓库。
15. 每项未完成任务必须明确责任角色、状态、开始时间、目标时间、阻塞项和资源依赖。
16. 代码、数据库 migration、API contract、配置、技术设计和文档之间必须建立可追溯关系。
17. 复杂业务规则、降级策略、兼容逻辑和 provider 替换策略必须通过代码注释与设计文档记录设计意图。
18. **任何已经发生并完成分析的工程错误必须记录到 `docs/error-tracking/`，不得只记录在聊天、Issue 或 Commit 中。**
19. 错误记录必须包含实际错误、根因、影响、修复方案、预防措施和验证要求；不得预填未执行的测试结果。
20. Migration 变更必须实际执行 `uv run alembic upgrade head` 验证；仅通过静态检查或单元测试不得标记 Migration 已验收。

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

## 6. Git / 提交规范

所有变更直接提交 `main`，不创建分支。采用 Conventional Commits：

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

提交前至少完成与本任务相关的本地测试，并在 `docs/PROJECT_STATUS.md` 或对应 Phase 文档记录实际结果。

## 7. 文档职责边界

### `docs/DEVELOPMENT.md`

只维护长期稳定的工程规则：

- 技术基线
- 开发顺序
- 测试原则
- 前后端测试隔离
- 分支 / main 提交规则
- Migration / Secret / Provider 规则
- 错误记录规则
- 文档闭环规则

### `docs/PROJECT_STATUS.md`

只维护当前项目进度：

- 当前 Phase
- 当前任务
- 完成 / 阻塞 / 待开始状态
- 实际测试结果
- 当前问题
- 下一步任务

### `docs/*phase*.md`

维护对应阶段的领域范围、任务拆解、API / Domain Contract、验收门禁和阶段性实施计划。

### `docs/error-tracking/`

维护已经发生的工程错误及其根因、修复与预防措施，作为后续开发的错误知识库。

## 8. 文档闭环

每个任务完成或发生阻塞后必须同步更新对应文档，至少记录：

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
