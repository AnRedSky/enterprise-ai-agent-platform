# Backend 模块化目录迁移映射表

## 1. 基线

- Repository：`AnRedSky/enterprise-ai-agent-platform`
- 基线分支：`main`
- 基线提交：`e2f71dbfdb1e038e50f16d034442690d22fd1c37`
- 基线来源：远端 `main` 递归目录树。
- 本文件是迁移设计，不代表目录迁移已经完成。

当前仓库已经存在 `app/api`、`app/core`、`app/dependencies`、`app/models`、`app/runtime`、`app/schemas`、`app/services`、`app/tools`；其中 `app/services/workflow_scheduler/` 已经是领域子模块。fileciteturn20file0L2-L2

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

## 3. 一级目录迁移

| 当前 | 目标 | 动作 | 说明 |
|---|---|---|---|
| `app/api/` | `app/api/v1/` | 逐步整理 | 当前 Router 按文件堆放，后续按 API Domain 收敛；保持 HTTP Contract 不变 |
| `app/core/` | `app/core/` | 保留并清理 | 仅保留应用核心能力 |
| `app/dependencies/` | `app/dependencies/` | 保留并扩展 | 与 middleware 保持边界 |
| 不存在 | `app/middleware/` | 新建 | Request/Response 横向处理 |
| `app/models/` | `app/models/` | 保留 | 当前 ORM 模型不因目录重构迁移到 infrastructure |
| `app/schemas/` | `app/schemas/` | 保留并整理 | API DTO；不替代 Domain Contract |
| `app/services/*.py` | `app/services/<domain>/` | 分领域迁移 | 本次整改核心 |
| `app/services/workflow_scheduler/` | `app/services/scheduler/` | 暂缓，优先评估 | 当前模块已成熟，不直接机械移动；确认 API/import 影响后再执行 |
| `app/runtime/` | `app/runtime/` | 保留并逐步分域 | Runtime 与 Service 分离 |
| 不存在 | `app/infrastructure/` | 新建 | DB、Redis、Provider、HTTP 技术适配 |
| 不存在 | `app/utils/` | 新建并严格限制 | 只允许无业务语义的纯工具 |
| `app/tools/` | `app/tools/` | 暂保留 | Tool Registry / Tool 基础实现；与 `services/tool` 边界后续细化 |

## 4. Services 领域映射

### 4.1 Agent

```text
当前：
app/services/agent_registry.py

目标：
app/services/agent/
├── __init__.py
├── registry.py
└── ...
```

当前没有独立 `agent_service.py`；因此不为了形式新增 Service 文件。

### 4.2 Model

```text
当前：
app/services/model_provider.py
app/services/model_provider_governance_contract.py
app/services/runtime_model_governance.py
app/services/circuit_breaker.py

app/runtime/model_gateway.py
app/runtime/provider.py
app/runtime/openai_provider.py

目标：
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

`runtime/model_gateway.py`、`runtime/provider.py` 等是否迁移必须根据运行时依赖图进一步确认；不能仅按文件名移动。

### 4.3 Knowledge

```text
当前：
app/services/embedding_provider.py
app/services/mock_embedding_provider.py
app/services/ollama_embedding_provider.py
app/services/knowledge_ingestion.py
app/services/knowledge_registry.py
app/services/knowledge_retrieval.py
app/services/knowledge_retrieval_contract.py
app/services/knowledge_vector_indexing.py
app/services/hybrid_knowledge_retrieval.py
app/services/hybrid_knowledge_retrieval_service.py
app/services/vector_knowledge_retrieval.py
app/services/vector_retrieval_provider.py

目标：
app/services/knowledge/
├── __init__.py
├── contract.py
├── ingestion.py
├── registry.py
├── retrieval.py
├── indexing.py
├── embedding.py
└── evaluation.py
```

外部 Embedding / Vector Provider 适配优先评估进入 `infrastructure/providers/` 的边界；领域编排仍留在 `services/knowledge/`。

### 4.4 Memory

```text
当前：
app/services/memory_service.py
app/runtime/memory_context.py

目标：
app/services/memory/
├── __init__.py
├── service.py
└── ...

app/runtime/memory_context.py
```

`memory_context.py` 继续作为 Runtime 上下文能力，不与业务 Service 混合。

### 4.5 Workflow

```text
当前：
app/services/workflow_registry.py
app/services/workflow_execution.py
app/services/workflow_governance.py

app/runtime/workflow_runtime.py

目标：
app/services/workflow/
├── __init__.py
├── definition.py
├── execution.py
├── governance.py
├── registry.py
└── ...

app/runtime/workflow_runtime.py
```

Workflow Runtime 暂不移动到 Service；仅按职责继续收敛。

### 4.6 Trigger

```text
当前：
app/services/workflow_trigger.py
app/services/workflow_trigger_schedule.py
app/services/webhook_trigger.py

目标：
app/services/trigger/
├── __init__.py
├── contract.py
├── workflow.py
├── schedule.py
└── webhook.py
```

Scheduler 与 Trigger 保持独立领域边界。

### 4.7 Scheduler

当前已经存在：

```text
app/services/workflow_scheduler/
├── __init__.py
├── contract.py
├── models.py
├── time.py
├── lease.py
├── misfire.py
├── repository.py
└── runtime.py
```

该模块已经符合“领域子模块 + `__init__.py` 稳定入口”的目标模式。fileciteturn21file0L2-L2

目标先保持其内部结构稳定，再评估是否将目录名从 `workflow_scheduler` 收敛为 `scheduler`。这是兼容性风险较高的一项，不与其他模块同时机械迁移。

### 4.8 Organization / Governance

```text
当前：
app/services/organization.py
app/services/session_service.py
app/services/observability_service.py
app/services/usage_accounting.py

目标优先映射：
app/services/organization/
app/services/observability/
app/services/governance/
```

`session_service.py` 需要根据身份认证与 Session 生命周期进一步判断属于 Identity/Auth 还是 Runtime Context，暂不机械归类。

### 4.9 Tool

```text
当前：
app/services/tool_audit.py
app/services/tool_observability.py
app/services/tool_rbac.py
app/services/tool_repository.py
app/services/tool_runtime_service.py

app/tools/exceptions.py
app/tools/http_executor.py
app/tools/registry.py
app/tools/schema.py

目标：
app/services/tool/
├── __init__.py
├── audit.py
├── observability.py
├── rbac.py
├── repository.py
└── ...

app/tools/
├── registry.py
├── schema.py
├── http_executor.py
└── exceptions.py
```

`services/tool` 负责 Tool 领域业务规则；`app/tools` 负责 Tool 技术实现与注册机制，暂不合并。

## 5. Retrieval Evaluation 特别处理

当前：

```text
app/services/retrieval_evaluation.py
app/services/retrieval_evaluation_baseline.py
app/services/retrieval_evaluation_config.py
app/services/retrieval_evaluation_dataset.py
app/services/retrieval_evaluation_trace.py
```

目标优先归入：

```text
app/services/knowledge/evaluation.py
```

但 evaluation dataset/result 的实际文件继续位于 `backend/evaluation/`，不能把版本化评测数据迁入线上 Service。

## 6. Core / Dependencies / Models 映射

### Core

```text
app/core/config.py        → 保留
app/core/security.py      → 保留
app/core/auth.py          → 保留，后续评估与 Identity/Authorization 边界
app/core/alembic_compat.py → 保留，直到确认是否仍需要兼容
```

### Dependencies

```text
app/dependencies/db.py → 保留在 dependencies；数据库技术实现逐步下沉 infrastructure/db
```

推荐最终：

```text
dependencies/db.py
    ↓
infrastructure/db/session.py
```

Dependency 只负责向 FastAPI 暴露 Session，不直接拥有数据库基础设施实现。

### Models

当前 ORM 模型包括 Agent/Execution/Knowledge/Memory/Model Provider/Organization/Workflow/Trigger/Scheduler 等，整体继续保留 `app/models/`。本次目录重构不创建数据库 Migration。

## 7. Runtime 映射

当前：

```text
app/runtime/agent_runtime.py
app/runtime/memory_context.py
app/runtime/model_gateway.py
app/runtime/openai_provider.py
app/runtime/provider.py
app/runtime/workflow_runtime.py
```

目标：

```text
runtime/
├── agent/
├── workflow/
├── trigger/
└── ...
```

其中 Provider/Gateway 的归属必须基于调用关系决定：

- Runtime 编排仍留 Runtime；
- 领域治理留 Service；
- 外部 Provider 技术适配进入 Infrastructure。

## 8. API 映射

当前 API 为单文件模式：

```text
app/api/agents.py
auth.py
chat.py
knowledge.py
knowledge_ingestion.py
knowledge_retrieval.py
model_providers.py
organizations.py
runtime.py
tools.py
usage.py
webhooks.py
workflow_executions.py
workflows.py
```

目标逐步收敛为：

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

API 路径、HTTP Method、Request/Response Contract 不因目录迁移改变。

## 9. 不迁移项目

以下项目本次不做目录迁移：

- `backend/alembic/`；
- `backend/evaluation/`；
- `backend/tests/` 的四层结构；
- `backend/scripts/test/` 的 Gate 结构；
- `backend/scripts/evaluation/`；
- Frontend；
- 数据库表结构；
- 外部 Provider 配置。

## 10. 迁移顺序

```text
① 新建 middleware / infrastructure / utils 基础边界
 ↓
② Scheduler 保持现状作为参考模板
 ↓
③ Knowledge
 ↓
④ Model / Provider
 ↓
⑤ Tool
 ↓
⑥ Workflow
 ↓
⑦ Trigger
 ↓
⑧ Agent / Memory / Organization / Governance / Observability
 ↓
⑨ Runtime 分域整理
 ↓
⑩ API 按 Domain 收敛
 ↓
⑪ 全仓 import / 测试 / 文档校验
```

每一步都是独立可验证的迁移单元，不允许一次性批量移动所有文件。

## 11. 验收原则

目录迁移完成必须至少验证：

1. `uv run pytest -q`；
2. Alembic head/current 校验；
3. API Contract；
4. 受影响模块的真实 API；
5. 必要时执行 Tenant Safe Real API；
6. 全仓搜索旧 import 路径；
7. 确认没有新增公共目录零散业务文件；
8. 更新 Phase / Acceptance / Status。

纯目录迁移不产生 Alembic Migration，除非同时发生真实数据库结构变化。
