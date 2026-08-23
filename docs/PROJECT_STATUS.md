# 项目状态

## 当前阶段

- Repository: `AnRedSky/enterprise-ai-agent-platform`
- Branch: `main`
- 当前架构基线：远端 `main` 已进入 Backend 模块化整改实施阶段。
- Phase 2.2 Retrieval Production Quality：**已正式关闭**。
- Phase 2.3 Model Provider Governance：**已正式关闭**。
- 当前：**Phase 2.4 Durable Scheduler Contract-first 实现中；已完成 Contract、持久化模型、Migration 与原子仓储第一版，尚未完成本地 Persistence Gate、API Contract 与 Scheduler Runtime 闭环。**
- Backend 模块化整改与 Phase 2.4 并行但职责独立；目录重构不得改变既有业务行为。

## Backend 模块化架构整改

本次整改以远端 `main` 当前真实目录为基线，执行原则统一为：**完整重构、无兼容垫片、无双实现、无旧入口保留，并对功能重复实现进行强制检查。**

正式架构文档：

- `docs/00-architecture/BACKEND_MODULE_ARCHITECTURE.md`：Backend 长期目录、职责、依赖方向、新功能开发模板及完整重构规则。
- `docs/00-architecture/BACKEND_MODULE_MIGRATION_MAP.md`：当前文件到目标领域模块的迁移映射与验收要求。

目标结构：

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

### 已完成 / 已纠偏

基础目录已经建立：

```text
app/infrastructure/
app/infrastructure/db/
app/middleware/
app/utils/
```

Agent 已完成彻底领域重构：

```text
app/services/agent/
├── __init__.py
├── service.py
└── repository.py
```

生产代码直接引用新领域入口；旧 `agent_registry.py` 与旧 `agent/registry.py` 已删除，不允许重新建立。

此前曾采用兼容入口方式进行 Agent 迁移，该做法已判定不符合最终重构要求并纠正，工程错误已记录在 `docs/04-errors/`。

### Knowledge：本轮已完成彻底领域重构

目标领域已经建立：

```text
app/services/knowledge/
├── __init__.py
├── contract.py
├── registry.py
├── ingestion.py
├── retrieval.py
├── vector_indexing.py
├── vector_retrieval.py
├── hybrid.py
└── hybrid_service.py
```

生产 API 与受影响测试已经切换到新领域路径；旧 Knowledge Service / Contract / Hybrid / Vector Retrieval 文件已经删除。

本轮**没有复制 Provider 实现到新目录**。以下 Provider 技术实现仍属于下一独立迁移单元：

```text
app/services/embedding_provider.py
app/services/mock_embedding_provider.py
app/services/ollama_embedding_provider.py
app/services/vector_retrieval_provider.py
```

后续统一迁移到 `app/infrastructure/providers/`，完成后删除旧 Provider 文件，禁止新旧双实现。

### 当前未完成

- Knowledge Provider 尚未完成 `infrastructure/providers` 迁移；
- Model / Provider 尚未完成 Service、Runtime、Infrastructure 边界重构；
- Tool 尚未完成领域与技术实现分离；
- Workflow / Trigger 尚未完成；
- Scheduler 尚未完成最终目录收敛；
- Memory / Organization / Governance / Observability 尚未完成；
- Runtime 尚未完成分域；
- API 尚未完成 `api/v1/<domain>` 收敛；
- **本轮 Knowledge/Agent 迁移尚未在当前远端环境实际执行 pytest，因此不得记录 targeted tests 或 Backend Regression Passed。**
- **不得记录整个模块化整改 Passed。**

### 完整重构原则

每个领域必须一次性完成：

```text
建立目标领域
 ↓
职责拆分
 ↓
生产代码 import 全量切换
 ↓
测试 import 全量切换
 ↓
删除旧文件
 ↓
全仓旧路径搜索 = 0
 ↓
重复实现检查 = 0
 ↓
领域测试
 ↓
Backend Regression
```

禁止：

```text
旧文件 → 新模块转发
旧实现 + 新实现并存
旧目录长期保留
只改目录名不改职责
```

### 业务不变原则

目录重构必须满足：

```text
API Path 不变
HTTP Method 不变
Request / Response Contract 不变
权限行为不变
Tenant Isolation 不变
数据库模型与 Migration 不变
Runtime 行为不变
Provider 行为不变
错误语义不变
```

仅允许改变：

```text
文件位置
模块边界
import 路径
内部职责组织
```

如果发现必须改变业务行为才能完成目录迁移，必须暂停该迁移单元并单独形成设计变更。

## Phase 2.3 最终本地验收结果

此前开发者在 `main` 基线实际执行：

```text
Targeted usage/governance tests: 40 passed
Backend Regression: 358 passed, 35 deselected
Alembic upgrade heads: passed
Tenant Safe Real API Gate: 35 passed
```

以上结果来自此前开发者本地实际执行，不使用 GitHub Actions 作为开发测试、质量门禁或验收依据。

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
- 同一业务功能必须按领域职责组织为子模块包，禁止继续向公共 `services` 目录新增同功能零散文件。
- **禁止以兼容垫片、旧入口转发或双实现方式完成模块迁移；领域迁移完成后旧文件必须删除。**
- **每个迁移单元必须执行功能重复实现检查；同一能力只能保留一个正式实现。**
- Backend 模块化设计与后续新功能开发统一参照 `docs/00-architecture/BACKEND_MODULE_ARCHITECTURE.md`；具体迁移按 `docs/00-architecture/BACKEND_MODULE_MIGRATION_MAP.md` 执行。
