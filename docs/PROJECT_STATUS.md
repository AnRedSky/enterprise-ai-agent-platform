# 项目状态

## 当前阶段

- Repository: `AnRedSky/enterprise-ai-agent-platform`
- Branch: `main`
- 当前架构基线：远端 `main` 提交 `e2f71dbfdb1e038e50f16d034442690d22fd1c37`。
- Phase 2.2 Retrieval Production Quality：**已正式关闭**。
- Phase 2.3 Model Provider Governance：**已正式关闭**。
- 当前：**Phase 2.4 Durable Scheduler Contract-first 实现中；已完成 Contract、持久化模型、Migration 与原子仓储第一版，尚未完成本地 Persistence Gate、API Contract 与 Scheduler Runtime 闭环。**
- 下一正式工作：**完成 Scheduler Persistence Gate，然后进入 API Contract 与 Real API。**

## Backend 模块化架构整改

本次暂停功能开发，先完成 Backend 模块化架构设计确认，并以远端 `main` 实际目录为基线建立迁移设计。

已形成正式架构文档：

- `docs/00-architecture/BACKEND_MODULE_ARCHITECTURE.md`：Backend 长期目录、职责、依赖方向、新功能开发模板。
- `docs/00-architecture/BACKEND_MODULE_MIGRATION_MAP.md`：当前实际文件到目标领域模块的迁移映射。

目标结构采用：

```text
backend/app/
├── api/
├── core/
├── dependencies/
├── middleware/
├── models/
├── schemas/
├── services/
├── runtime/
├── infrastructure/
└── utils/
```

其中：

- `services/<domain>/` 承担领域业务规则；
- `runtime/` 承担执行与运行时编排；
- `infrastructure/` 承担 DB、Redis、外部 Provider、HTTP 等技术适配；
- `utils/` 仅允许无业务语义的纯工具；
- `models/` 继续承担 ORM 持久化模型，不因目录重构迁入 `infrastructure/db`；
- `middleware/` 与 `dependencies/` 保持 HTTP 生命周期和 FastAPI DI 的职责分离。

当前 `services/workflow_scheduler/` 已经具备领域子模块形态，可作为后续迁移的参考模板。fileciteturn21file0L2-L2

**当前仅完成架构设计与文档基线，不代表代码目录迁移已经完成。**

## Phase 2.3 最终本地验收结果

此前开发者在 `main` 基线实际执行：

```text
Targeted usage/governance tests: 40 passed
Backend Regression: 358 passed, 35 deselected
Alembic upgrade heads: passed
Tenant Safe Real API Gate: 35 passed
```

以上结果来自开发者本地实际执行，不使用 GitHub Actions 作为开发测试、质量门禁或验收依据。

## Phase 2.4 当前进度

Scheduler 已形成独立功能子模块：

```text
backend/app/services/workflow_scheduler/
├── __init__.py
├── contract.py
├── models.py
├── time.py
├── lease.py
├── misfire.py
├── repository.py
└── runtime.py
```

其中 `contract.py` 仅保留薄兼容入口；领域 Contract 按模型、时间、lease、misfire 拆分，Repository 与 Runtime 继续保持独立职责。

当前已经完成：

- Scheduler Contract；
- `WorkflowSchedule` / `WorkflowScheduleSlot` 持久化模型；
- `0028_durable_scheduler_persistence` Migration；
- PostgreSQL 原子 lease claim / release；
- PostgreSQL slot 唯一键幂等 claim；
- WorkflowExecution 与 slot 绑定基础能力。

当前**不得记录 Phase 2.4 Passed**。仍需本地完成 Migration / Repository Gate，并确认 API Contract、Runtime 闭环、tenant isolation、misfire、Audit / Trace 与 Real API acceptance。

## Phase 2.4 下一执行任务

1. 执行 Scheduler targeted tests；
2. 执行 `uv run alembic upgrade heads` 与 `uv run alembic current`；
3. 执行 Backend Regression；
4. 核查 lease / slot repository 的真实 PostgreSQL 行为与竞态；
5. 完成 Scheduler API Contract；
6. 将 Runtime 接入 persistence / lease / slot；
7. 创建 Tenant Safe Real API Gate，覆盖多实例 lease、重复 claim、misfire、状态与 tenant isolation。

## 开发纪律

- 远端 `main` 是唯一开发基线；不创建功能分支。
- 未实际执行的测试不得记录为 Passed。
- Runtime 数据继续使用 PostgreSQL；JSON/JSONL 仅用于版本化 evaluation dataset/result/baseline。
- 新业务代码不得硬编码具体模型名称。
- Secret 不进入 Git、数据库明文、报告或 trace/audit。
- 代码、Phase、Acceptance、Error、Status 必须保持可追溯。
- 代码中的功能说明和注释统一使用中文；技术标识保持原文。
- 当前阶段同一业务功能必须按领域职责组织为子模块包，禁止继续向公共 services 目录新增同功能零散文件；仅允许保留薄兼容入口。
- Backend 模块化设计与后续新功能开发统一参照 `docs/00-architecture/BACKEND_MODULE_ARCHITECTURE.md`；具体迁移按 `docs/00-architecture/BACKEND_MODULE_MIGRATION_MAP.md` 执行。
