# 开发准则

> **唯一开发准则**：本文件只维护项目工程开发、测试、验收、分支与提交规则，不记录项目阶段进度。阶段进度统一维护在 `docs/PROJECT_STATUS.md` 及对应 `docs/02-phases/PHASE_x_y.md` / `docs/03-acceptance/PHASE_x_y_ACCEPTANCE.md` 中。
>
> 若其他工程规则文档与本文件冲突，以本文件为准，并及时修正文档。

## 1. 技术基线

- Backend：FastAPI + Python 3.12+
- Backend 包管理与运行：uv / `backend/.venv`
- Frontend：Vue 3 + TypeScript + Vite
- Database：PostgreSQL
- Cache：Redis
- Migration：Alembic
- Backend Test：pytest
- Frontend Test：Vitest
- Browser E2E：Playwright

## 2. 本地测试原则

项目开发阶段测试、联调、验收以开发者本地实际执行结果为准。禁止把 GitHub Actions workflow 作为开发测试、质量门禁或验收依据。

每个需要测试的任务必须提供明确、可重复执行的命令；测试结果只能记录实际执行并反馈的结果，不得预填“通过”。真实 Provider、数据库、外部 endpoint 等联调必须在本地完成。

### 测试实现与脚本编排严格分离

```text
backend/tests/             = 测试实现与断言
backend/scripts/test/      = Backend 测试 Gate 与顺序编排
backend/scripts/evaluation = 质量评估
backend/scripts/dev/       = Backend 开发辅助/场景复现
frontend/tests/            = Frontend 测试实现与断言
frontend/scripts/test/     = Frontend 测试 Gate 与顺序编排
```

Backend 测试四层目录必须保持：

```text
unit → integration → api_contract → api_real
```

`backend/tests` 根目录禁止新增 `test_*.py`；根目录仅保留测试基础设施文件。

## 3. 测试 Gate 隔离

```text
Backend Gate
① Backend default regression
        ↓
② Database migration/head verification
        ↓
③ Real HTTP API Gate

Frontend Gate
① Frontend test
        ↓
② Frontend production build

Browser / Frontend-Backend E2E
① Browser
        ↓
② Real Frontend
        ↓
③ Real Backend HTTP
```

Backend、Frontend、Browser 三层 Gate 必须保持脚本、工作目录、运行时、依赖和失败状态独立。

- Backend 脚本不得调用 `npm test` 或 `npm run build`。
- Frontend 脚本不得调用 `uv run pytest`、Alembic migration 或 Real API Gate。
- Browser E2E 不重复 Backend / Frontend regression。
- 不创建一个同时编排 Backend 与 Frontend 的 Full Regression Gate。

## 4. 固定入口

Backend default regression：

```powershell
cd backend
uv run pytest -q
```

Backend Release / Regression Gate：

```powershell
cd backend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\release\01_backend_regression_gate.ps1
```

Frontend Release / Regression Gate：

```powershell
cd frontend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\release\01_frontend_regression_gate.ps1
```

Browser E2E Organization Gate：

```powershell
cd frontend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\e2e\02_run_organization_e2e.ps1
```

Browser E2E Workflow Trigger Gate：

```powershell
cd frontend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\e2e\01_run_workflow_trigger_e2e.ps1
```

Real API 唯一入口：

```powershell
cd backend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\api-real\01_run_real_api_tests.ps1
```

Tenant Safe Real API Gate：

```powershell
cd backend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\api-real\01_run_real_api_tests_tenant_safe.ps1
```

模块化整改 Gate：

```powershell
cd backend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\module-refactor\01_backend_module_refactor_gate.ps1
```

## 5. 固定开发顺序

```text
① 需求 / 架构文档确认
② Backend Domain + API Contract
③ Database Migration + Backend tests
④ Frontend API Types + Vitest
⑤ Frontend UI
⑥ Real API Gate
⑦ Backend Gate 与 Frontend Gate 分别执行
⑧ Frontend / Backend 联调
⑨ Browser / Frontend-Backend E2E（如范围需要）
⑩ 更新开发 / 验收文档
⑪ 提交 main
```

### 强制规则

1. 后端 Contract 是前后端唯一业务契约。
2. 涉及数据库的数据结构必须先有 Alembic migration，再开发依赖该结构的业务代码。
3. Backend 测试通过后，才进入前端 API 类型与 UI 实现。
4. 前端测试必须与业务源码分离，只放在 `frontend/tests/`。
5. Runtime Integration 必须在基础 API Contract 稳定、Real API 可验收后进行。
6. 联调完成后必须分别执行 Backend Gate、Frontend Gate，以及独立 E2E Gate。
7. 验收文档必须在代码提交前同步更新。
8. 功能完成、延期、阻塞或范围变更时，必须同步更新 `PROJECT_STATUS.md` 与对应 Phase 文档。
9. **禁止创建任何功能分支、临时分支、开发分支或长期分支；所有开发、修复、文档与测试变更均直接基于并提交 `main`。**
10. 开发前必须以远端 `main` 为当前基线，先同步 / 拉取 `main` 最新代码。
11. Backend 的 Python 包安装、测试、脚本与服务运行统一使用 `uv run ...`。
12. **真实 Provider 的 endpoint、API key、model 等运行配置原则上只能写入未提交的 `backend/.env` / `backend/.env.local`；允许提交 `backend/.env.dev` 作为统一本地开发 profile，但该文件只能包含无 Secret 的本地服务地址、兼容占位值和已确认可用的开发默认值，禁止写入真实远程凭据、Token、密码或其他 Secret。`.env.dev` 不得被当作 Real Provider baseline 或验收结果。**
13. Secret 禁止提交到 Git 仓库。
14. 代码、数据库 migration、API contract、配置、技术设计和文档之间必须建立可追溯关系。
15. 复杂业务规则、降级策略、兼容逻辑和 provider 替换策略必须通过代码注释与设计文档记录设计意图。
16. **任何已经发生并完成分析的工程错误必须记录到 `docs/04-errors/`。**
17. Migration 变更必须实际执行 `uv run alembic upgrade head` 验证。
18. **同一任务产生的多个文档变更原则上必须作为一个原子提交一次性提交；禁止为了记录单个文档修改而连续创建多个仅包含单一文档的中间提交。**
19. 文档批量提交前应一次性完成 Phase、Acceptance、Project Status、治理规则及错误记录的评估；只有确有独立工程意义的后续事实变化，才允许再次单独提交文档。
20. 代码与其对应的 Phase/Acceptance/错误记录属于同一交付单元时，应尽量在同一个提交中完成；若测试反馈导致后续修复，则按新的实际修复形成下一原子提交。
21. **代码中的功能说明、设计意图和注释统一使用中文表述；Python docstring、TypeScript/Vue 注释、数据库 migration 说明以及复杂业务规则注释均不得使用英文自然语言作为主要说明。协议字段名、类名、函数名、异常码、第三方库名称等代码标识按技术约定保留原文，不要求翻译。**
22. **当前阶段同一业务功能的代码必须按领域职责组织为子模块包；禁止继续把 Contract、Service、Repository、Runtime 等同一功能的代码零散堆放在 `app/services/` 或其他公共目录。子模块通过 `__init__.py` 暴露正式入口。领域迁移完成后必须删除旧文件、旧目录和旧模块路径；禁止使用兼容垫片、旧入口转发、代理文件或双实现维持旧路径。**
23. **Backend 领域模块的目录、职责、迁移规则和新项目开发模板统一参照 `docs/00-architecture/BACKEND_MODULE_ARCHITECTURE.md`；当前项目具体旧文件到目标模块的迁移以 `docs/00-architecture/BACKEND_MODULE_MIGRATION_MAP.md` 为准。**
24. **模块重构属于完整交付单元：生产代码 import、测试 import、旧文件删除、旧路径搜索、领域测试和 Backend Regression 必须全部完成后，才允许将该领域标记为迁移完成。**
25. **每个新增或重构的 Python 模块必须提供简短中文职责说明，至少说明模块负责什么、明确边界以及必要的关键外部依赖；复杂业务规则和非显然技术约束必须在对应类/方法附近补充中文 docstring 或注释。禁止用空洞注释替代清晰职责设计。**
26. **同一外部能力只能保留一个正式 Provider 实现入口。Provider 技术适配统一进入 `app/infrastructure/providers/`；领域 Service 不得复制第二套 Provider，也不得以不同文件名实现相同外部协议。每个 Provider 迁移单元必须执行旧路径、重复实现和 targeted tests Gate。**
27. **新增或修改业务能力前，必须先检索现有领域包、Service、Repository、Runtime、Provider、工具函数及测试，确认没有已有正式实现；若已有实现满足职责，应扩展原实现而不是新增平行模块。代码评审和提交说明必须能够说明为何没有产生重复能力。**
28. **新增模块不仅要检查文件级重复，还必须检查职责和规则重复：相同业务规则只能保留一个正式计算/校验入口，测试不得通过复制生产算法形成第二套实现；跨模块复用必须通过正式领域入口，不得复制代码片段。**
29. **每个新增或重构模块必须提供必要中文说明：模块说明职责与边界；类说明核心职责；函数/方法说明用途、关键参数、返回值及重要副作用或事务边界；参数命名已经足够显然且为简单 getter/setter 时可不写冗余说明。**
30. **涉及时间槽、幂等、租约、misfire、权限、tenant boundary、状态机、降级或并发控制等非显然规则时，必须在规则实现附近写明“为什么这样做”和边界条件；不得只描述代码做了什么。任何因兼容旧 Contract 而保留的逻辑必须说明兼容对象、移除条件及不可扩展边界。**
31. **测试脚本必须是可重复执行的自动化入口；不得要求开发者手工修改测试文件或生产代码才能完成验收。若测试依赖本地服务，Gate 脚本必须明确前置服务、环境变量、数据库状态、启动命令和失败条件，并在输出中区分“脚本未执行”“执行失败”和“执行通过”。**
32. **Real API 测试必须验证真实 HTTP + 真实 PostgreSQL 持久化链路；可以直接调用 Runtime 做确定性补充验证，但不得用 Mock、JSON fixture 或进程内假数据替代真实持久化业务流程。涉及后台生命周期的验收必须单独验证 Scheduler 是否实际启动并运行。**

## 6. 分层原则

```text
API → Service → Runtime → Gateway / Tool / Memory / Knowledge
                    ↓
                 Repository
                    ↓
               PostgreSQL / Redis
```

API 层只负责协议适配与鉴权；业务规则进入 Service；Agent 执行进入 Runtime；模型供应商差异封装在 Model Gateway；Tool 必须经过 Registry 和权限校验；Knowledge/RAG 保持独立领域边界。

## 7. Git / 提交规范

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

提交前至少完成与本任务相关的本地测试，并在 `PROJECT_STATUS.md` 或对应 Phase 文档记录实际结果。测试体系整改类任务可以只进行静态目录/脚本结构验收，但不得声称未执行的功能测试已通过。

## 8. 文档职责

- `PROJECT_STATUS.md`：当前状态。
- `01-governance/DOCUMENTATION.md`：文档治理。
- `02-phases/`：阶段计划。
- `03-acceptance/`：阶段验收。
- `04-errors/`：工程错误。

禁止仅通过聊天、Issue 或 Commit 信息作为唯一项目状态记录。
