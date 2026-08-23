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
8. **功能重复实现检查必须是每个迁移单元的 Gate**：新旧文件、同职责 Service、重复 Provider、重复 Runtime 均必须检查。
9. **模块说明必须随代码迁移**：每个新增或重构模块文件必须有简短中文模块说明，说明职责、边界及必要的外部依赖；不得用无意义注释堆砌代码。

## 4. 一级目录迁移

| 当前 | 目标 | 动作 | 状态 |
|---|---|---|---|
| `app/api/` | `app/api/v1/` | 按 Domain 收敛 | 待迁移 |
| `app/core/` | `app/core/` | 保留并清理 | 进行中 |
| `app/dependencies/` | `app/dependencies/` | 保留，技术实现下沉 | 待迁移 |
| 不存在 | `app/middleware/` | 新建 | 已建立基础目录 |
| `app/models/` | `app/models/` | 保留 | 不迁移 |
| `app/schemas/` | `app/schemas/` | 保留并整理 | 待迁移 |
| `app/services/*.py` | `app/services/<domain>/` | 彻底分领域迁移 | 进行中 |
| `app/runtime/` | `app/runtime/<domain>/` | 按执行职责分域 | 待迁移 |
| 不存在 | `app/infrastructure/` | 新建 | 已建立基础目录 |
| 不存在 | `app/utils/` | 新建并严格限制 | 已建立基础目录 |
| `app/tools/` | `app/tools/` | 保留技术实现与注册机制 | 待细化 |

## 5. Agent：彻底迁移完成

```text
app/services/agent/
├── __init__.py
├── service.py
└── repository.py
```

原 `app/services/agent_registry.py` 与 `app/services/agent/registry.py` 已删除；生产代码直接使用 `app.services.agent`，不存在兼容垫片或双实现。

## 6. Knowledge：领域与 Provider 已完成物理迁移

### 领域模块

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

### Provider 技术适配

```text
app/infrastructure/providers/
├── __init__.py
├── embedding.py
├── mock_embedding.py
├── ollama_embedding.py
└── vector_retrieval.py
```

Embedding Contract 只保留 `infrastructure/providers/embedding.py` 一份正式定义；Knowledge 领域仅引用该 Contract，不再复制 Provider 实现。

已删除：

```text
app/services/embedding_provider.py
app/services/mock_embedding_provider.py
app/services/ollama_embedding_provider.py
app/services/vector_retrieval_provider.py
```

Knowledge 的 `vector_indexing.py` 与 `vector_retrieval.py` 已直接依赖 `app.infrastructure.providers`，因此不存在旧 Service Provider 与新 Infrastructure Provider 双实现。

## 7. Model

### 当前

```text
app/services/model_provider.py
app/services/model_provider_governance_contract.py
app/services/runtime_model_governance.py
app/services/circuit_breaker.py
app/runtime/model_gateway.py
app/runtime/provider.py
app/runtime/openai_provider.py
```

### 目标

```text
app/services/model/
├── __init__.py
├── contract.py
├── provider.py
├── governance.py
├── routing.py
└── ...

app/infrastructure/providers/
└── <具体外部 Provider 适配>
```

必须先建立调用关系，再进行物理迁移；不得通过旧路径垫片完成迁移，也不得复制一套新 Provider。

## 8. Memory

```text
app/services/memory_service.py
        ↓
app/services/memory/service.py

app/runtime/memory_context.py
        ↓
app/runtime/memory/...
```

Service 与 Runtime 必须彻底分离，旧 `memory_service.py` 完成迁移后删除。

## 9. Workflow

```text
app/services/workflow_registry.py
app/services/workflow_execution.py
app/services/workflow_governance.py
        ↓
app/services/workflow/

app/runtime/workflow_runtime.py
        ↓
app/runtime/workflow/...
```

## 10. Trigger

```text
app/services/workflow_trigger.py
app/services/workflow_trigger_schedule.py
app/services/webhook_trigger.py
        ↓
app/services/trigger/
```

## 11. Scheduler

当前 `app/services/workflow_scheduler/` 已经满足领域模块化要求，暂不重命名。若后续收敛到 `scheduler`，必须一次性完成全部 import、测试、文档迁移并删除旧目录。

## 12. Organization / Governance / Observability

```text
app/services/organization.py
app/services/session_service.py
app/services/observability_service.py
app/services/usage_accounting.py
        ↓
app/services/organization/
app/services/governance/
app/services/observability/
```

最终领域归属必须基于实际职责判断，不得机械归类。

## 13. Tool

```text
app/services/tool_audit.py
app/services/tool_observability.py
app/services/tool_rbac.py
app/services/tool_repository.py
app/services/tool_runtime_service.py
        ↓
app/services/tool/
```

`app/tools/` 保留 Tool Registry、Schema、HTTP Executor 等技术实现；不得形成第二套 Tool Runtime。

## 14. Runtime

```text
app/runtime/
├── agent/
├── workflow/
├── memory/
├── trigger/
└── ...
```

Runtime 只负责执行编排；外部 Provider 技术适配归 `infrastructure/providers/`。

## 15. API

最终收敛为：

```text
app/api/v1/
├── agents/
├── auth/
├── knowledge/
├── models/
├── organizations/
├── runtime/
├── tools/
├── triggers/
└── workflows/
```

API URL、HTTP Method、Request/Response Contract 不变；迁移完成后旧 Router 删除，不保留转发 Router。

## 16. 每个迁移单元验收

1. 全仓搜索旧 import 路径，结果为 0；
2. 旧文件已删除；
3. 不存在重复实现；
4. 生产代码只存在一个正式入口；
5. 受影响测试已切换；
6. 每个新增/重构模块有必要的中文职责说明；
7. targeted tests；
8. Backend Regression；
9. 必要时 Real API / Tenant Safe Real API；
10. Alembic `upgrade heads` / `current`，确认没有因目录重构产生数据库变化；
11. 更新 Migration Map、PROJECT_STATUS 与开发记录。

**只有代码、import、测试、重复实现检查、模块说明和文档全部完成，才能将领域标记为迁移完成。**
