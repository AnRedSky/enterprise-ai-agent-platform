# 项目状态

## 当前阶段

- Repository: `AnRedSky/enterprise-ai-agent-platform`
- Branch: `main`
- 当前架构基线：远端 `main` 已进入 Backend 模块化整改实施阶段。
- Phase 2.2 Retrieval Production Quality：**已正式关闭**。
- Phase 2.3 Model Provider Governance：**已正式关闭**。
- 当前：**Phase 2.4 Durable Scheduler Contract-first 实现中；已完成 Contract、持久化模型、Migration 与原子仓储第一版，当前正在执行本地 Persistence Gate，尚未完成 API Contract 与 Scheduler Runtime 闭环。**
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
app/infrastructure/providers/
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

### Knowledge：领域与 Provider 均已完成彻底重构

领域模块：

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

技术 Provider：

```text
app/infrastructure/providers/
├── __init__.py
├── embedding.py
├── mock_embedding.py
├── ollama_embedding.py
└── vector_retrieval.py
```

已完成：

- Knowledge 领域 Service / Contract / Retrieval / Indexing 已集中到 `services/knowledge/`；
- Embedding Contract 与 Provider 实现集中到 `infrastructure/providers/`；
- pgvector / InMemory Vector Provider 集中到 `infrastructure/providers/`；
- 生产代码和受影响测试已切换新 import；
- 旧 Provider 文件已删除；
- 未复制第二套 Provider 实现；
- 新增/重构模块补充中文职责说明；
- 模块化 Gate 已增加 Provider 旧路径、重复实现和 Provider targeted tests 检查。

旧 Provider 路径已删除：

```text
app/services/embedding_provider.py
app/services/mock_embedding_provider.py
app/services/ollama_embedding_provider.py
app/services/vector_retrieval_provider.py
```

此前开发者本地实际执行的 targeted 结果：Embedding / Provider 相关 28 passed；Knowledge 相关 26 passed。Backend Regression 在模块导入回归修复前曾因旧 Knowledge import 收集失败，现 `app.main` 已恢复可导入；完整 Regression 与模块化 Gate 仍需重新执行。

### 当前未完成

- Model / Provider 尚未完成 Service、Runtime、Infrastructure 全边界重构；
- Tool 尚未完成领域与技术实现分离；
- Workflow / Trigger 尚未完成；
- Scheduler 尚未完成最终目录收敛；
- Memory / Organization / Governance / Observability 尚未完成；
- Runtime 尚未完成分域；
- API 尚未完成 `api/v1/<domain>` 收敛；
- **整个 Backend 模块化整改不得标记 Passed。**

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
模块职责说明检查 = 0
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
复制 Provider 形成第二套实现
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
- WorkflowExecution 与 slot 绑定基础能力；
- 新增 Scheduler PostgreSQL Repository integration test；
- 新增独立 Scheduler Persistence Gate，包含 Migration、Scheduler targeted tests、Repository PostgreSQL integration 与 Backend Regression。

当前**不得记录 Phase 2.4 Passed**。Persistence Gate 尚未由开发者本地实际执行通过；API Contract、Runtime 闭环、tenant isolation、misfire、Audit / Trace 与 Real API acceptance 仍未完成。

## Phase 2.4 下一执行任务

1. 开发者本地执行 Scheduler Persistence Gate；
2. 根据真实 PostgreSQL 结果修复 lease / slot repository 的竞态或 tenant 边界问题；
3. 完成 Scheduler API Contract；
4. 将 Runtime 接入 persistence / lease / slot；
5. 增加 Tenant Safe Real API Gate，覆盖多实例 lease、重复 claim、misfire、状态与 tenant isolation；
6. 重新执行 Backend Regression Gate；
7. 若涉及用户操作，再进入 Frontend API / UI 与独立 Browser E2E。

## 开发纪律

- 远端 `main` 是唯一开发基线；不创建功能分支。
- 未实际执行的测试不得记录为 Passed。
- Runtime 数据继续使用 PostgreSQL；JSON/JSONL 仅用于版本化 evaluation dataset/result/baseline。
- 新业务代码不得硬编码具体模型名称。
- Secret 不进入 Git、数据库明文、报告或 trace/audit。
- 代码、Phase、Acceptance、Error、Status 必须保持可追溯。
- 代码中的功能说明和注释统一使用中文；技术标识保持原文。
- **每个新增或重构 Python 模块必须提供必要的中文职责说明；类和复杂方法按需补充说明约束与技术原因。**
- 同一业务功能必须按领域职责组织为子模块包，禁止继续向公共 `services` 目录新增同功能零散文件。
- **禁止以兼容垫片、旧入口转发或双实现方式完成模块迁移；领域迁移完成后旧文件必须删除。**
- **每个迁移单元必须执行功能重复实现检查；同一能力只能保留一个正式实现。**
- **Provider 只能在 `app/infrastructure/providers/` 保留正式技术适配实现，禁止在 `services/` 复制第二套 Provider。**
- Backend 模块化设计与后续新功能开发统一参照 `docs/00-architecture/BACKEND_MODULE_ARCHITECTURE.md`；具体迁移按 `docs/00-architecture/BACKEND_MODULE_MIGRATION_MAP.md` 执行。
