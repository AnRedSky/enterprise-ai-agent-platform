# Backend 模块化目录迁移映射表

## 1. 基线

- Repository：`AnRedSky/enterprise-ai-agent-platform`
- 基线分支：`main`
- 本轮原则：**彻底迁移，不使用兼容垫片，不保留旧业务实现入口。**
- 目标：只改变代码组织、依赖关系与模块边界，不改变既有业务行为、API Contract、数据库结构和运行时语义。

## 2. 目标结构

```text
backend/app/
├── api/
├── core/
├── dependencies/
├── middleware/
├── models/
├── schemas/
├── services/
│   ├── agent/
│   ├── model/
│   ├── tool/
│   ├── knowledge/
│   ├── memory/
│   ├── workflow/
│   ├── trigger/
│   ├── scheduler/
│   ├── organization/
│   ├── governance/
│   └── observability/
├── runtime/
│   ├── agent/
│   ├── workflow/
│   ├── memory/
│   └── trigger/
├── infrastructure/
│   ├── db/
│   ├── redis/
│   ├── providers/
│   └── http/
├── utils/
└── main.py
```

## 3. 重构规则

1. **禁止兼容垫片**：旧业务文件迁移完成后必须删除；不得保留 `xxx.py -> 新模块` 的转发文件。
2. **禁止双实现**：同一业务能力只能存在一个正式实现。
3. **禁止仅改目录名**：领域迁移必须同时完成 Service / Repository / Contract / Runtime 的职责重新归位。
4. **禁止业务行为变更**：本次重构不修改既有业务规则、API 路径、HTTP Method、Request/Response Contract、数据库结构和外部 Provider 配置。
5. **import 必须彻底切换**：所有调用方直接引用新模块；全仓搜索确认旧路径不存在。
6. **测试跟随迁移**：受影响测试同步修改 import 与模块路径，不通过兼容代码维持旧测试。
7. **数据库不因目录重构产生 Migration**：只有真实数据库结构变化才允许新增 Alembic Migration。
8. **功能重复实现检查必须是每个迁移单元的 Gate**。
9. **模块说明必须随代码迁移**：每个新增或重构模块文件必须有简短中文模块说明。

## 4. 当前迁移状态

| 领域 | 目标模块 | 状态 | 说明 |
|---|---|---|---|
| Agent | `app/services/agent/` | 已完成 | Service / Repository 已物理迁移，旧入口删除 |
| Knowledge | `app/services/knowledge/` + `app/infrastructure/providers/` | 已完成 | 领域与 Provider 已分离，无旧 Provider 实现 |
| Memory | `app/services/memory/` + `app/runtime/memory/` | 已完成 | Service 与 Runtime 上下文均已迁移，旧入口删除 |
| Model | `app/services/model/` + `app/runtime/model/` + Provider | 已完成 | Service / Contract / Routing / Governance / Runtime Gateway / Provider 已收敛 |
| Workflow | `app/services/workflow/` + `app/runtime/workflow/` | **整改中** | Canonical import 与循环依赖已修复；仍需最终 Gate / Regression 验收 |
| Trigger | `app/services/trigger/` | **代码迁移完成，待 Gate 验收** | Manual / Scheduled / Webhook 已统一进入 Trigger 子模块；旧入口删除 |
| Organization | `app/services/organization/` | **代码迁移完成，待 Gate 验收** | Service 已物理迁移并删除旧根文件 |
| Observability | `app/services/observability/` | **代码迁移完成，待 Gate 验收** | Service 已物理迁移并切换调用方 |
| Retrieval Evaluation | `app/services/retrieval_evaluation/` | **代码迁移完成，待 Gate 验收** | Trace / Dataset / Baseline / Config 已收敛 |
| Runtime Query | `app/services/runtime_query/` | **代码迁移完成，待 Gate 验收** | 旧根 Service 已删除 |
| Session | `app/services/session_service/` | **代码迁移完成，待 Gate 验收** | 旧根 Service 已删除 |
| Tool | `app/services/tool/` + `app/tools/` | **代码迁移完成，待 Gate 验收** | Audit / Observability / RBAC / Repository / Runtime 已统一收敛到 `app.services.tool`，`app.tools` 仅保留 HTTP/Schema 技术实现 |
| Usage Accounting | `app/services/usage_accounting/` | **代码迁移完成，待 Gate 验收** | 旧根 Service 已删除 |
| API | `app/api/v1/<domain>/` | 待迁移 | 当前 Router 仍位于 `app/api/*.py` |

## 5. Memory：彻底迁移完成

```text
app/services/memory_service.py
        ↓
app/services/memory/
├── __init__.py
└── service.py

app/runtime/memory_context.py
        ↓
app/runtime/memory/
├── __init__.py
└── context.py
```

迁移要求已完成：生产入口统一为 `app.services.memory`；Runtime 入口统一为 `app.runtime.memory`；删除旧文件；测试 import 已同步切换；模块说明与 Gate 检查已补齐；未新增数据库 Migration。

## 6. Agent：彻底迁移完成

```text
app/services/agent/
├── __init__.py
├── service.py
└── repository.py
```

原 `app/services/agent_registry.py` 与旧 registry 入口已删除；生产代码直接使用 `app.services.agent`，不存在兼容垫片或双实现。

## 7. Knowledge：领域与 Provider 已完成物理迁移

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

app/infrastructure/providers/
├── embedding.py
├── mock_embedding.py
├── ollama_embedding.py
└── vector_retrieval.py
```

Embedding Contract 只保留 `infrastructure/providers/embedding.py` 一份正式定义；Knowledge 领域不复制 Provider 实现。

## 8. Model：彻底迁移完成

正式结构：

```text
app/services/model/
├── __init__.py
├── contract.py
├── provider.py
├── governance.py
└── routing.py

app/runtime/model/
├── __init__.py
└── gateway.py

app/infrastructure/providers/
├── model.py
├── openai_model.py
└── mock_model.py
```

`ModelProviderService`、Governance Contract、Routing、Runtime Governance、Model Gateway、Provider Contract 均已收敛到唯一正式入口，旧 Service / Runtime Provider 文件删除，不保留兼容垫片。

## 9. Workflow：当前整改状态

Workflow 已完成旧入口物理删除与 canonical import 切换。`WorkflowExecutionService -> WorkflowRuntime -> app.services.workflow` 循环依赖已修复；不恢复旧文件、不增加第二套实现。

当前必须继续完成：

- 本地 Module Refactor Gate；
- Workflow targeted tests；
- Backend Regression；
- 旧路径搜索与重复实现审查。

## 10. Trigger：本轮物理迁移

```text
app/services/trigger/
├── __init__.py
├── service.py
├── schedule.py
└── webhook.py
```

`WorkflowTriggerService`、scheduled/webhook 配置契约、`WebhookTriggerService` 均已归入正式 Trigger 模块；Workflow API、Webhook API 与测试已切换；旧三个根文件删除；新增/重构文件补充中文职责、边界和关键依赖说明。

## 11. Organization / Observability / Retrieval Evaluation / Runtime Query / Session / Usage Accounting

上述领域已完成代码物理迁移并删除旧根 Service。当前状态统一为“代码迁移完成，待 Gate 验收”，不得因为代码已移动就提前宣布重构阶段结束。

验收必须同时满足：旧 import 为 0、旧文件/目录删除、无重复实现、模块说明完整、targeted tests 与 Backend Regression 通过。

## 12. Tool：统一领域入口

正式结构：

```text
app/services/tool/
├── __init__.py
├── audit.py
├── observability.py
├── rbac.py
├── repository.py
└── runtime.py

app/tools/
├── exceptions.py
├── http_executor.py
└── schema.py
```

边界明确为：

- `app.services.tool`：Tool 领域治理、执行编排、权限、审计、可观测性与持久化适配；
- `app.tools`：HTTP/Schema 等底层技术执行能力；
- API 只负责 HTTP Contract 与依赖注入，不复制 Tool Runtime 业务规则。

旧 `tool_audit`、`tool_observability`、`tool_rbac`、`tool_repository`、`tool_runtime_service` 目录已删除，不保留兼容转发。

## 13. 每个迁移单元验收

1. 全仓搜索旧 import 路径，结果为 0；
2. 旧文件和旧目录已删除；
3. 不存在重复实现；
4. 生产代码只存在一个正式入口；
5. 受影响测试已切换；
6. 每个新增/重构模块有必要的中文职责与边界说明；
7. targeted tests；
8. Backend Regression；
9. 必要时 Real API / Tenant Safe Real API；
10. Alembic `upgrade heads` / `current`，确认没有因目录重构产生数据库变化；
11. 更新 Migration Map、PROJECT_STATUS 与必要的 Error 记录。

**只有代码、import、测试、重复实现检查、模块说明和文档全部完成，才能将领域标记为“迁移完成”。**
