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
| Memory | `app/services/memory/` + `app/runtime/memory/` | **本次完成** | Service 与 Runtime 上下文均已迁移，旧 `memory_service.py` / `memory_context.py` 删除 |
| Model | `app/services/model/` + Provider | 待迁移 | 当前仍存在根目录旧 Service / Runtime Provider 组合 |
| Workflow | `app/services/workflow/` + `app/runtime/workflow/` | 待迁移 | Registry / Execution / Governance 仍待领域收敛 |
| Trigger | `app/services/trigger/` | 待迁移 | Scheduled / Webhook Trigger 仍待统一领域入口 |
| Organization / Governance / Observability | 对应领域子模块 | 待迁移 | 当前仍存在多个根目录 Service 文件 |
| Tool | `app/services/tool/` | 待迁移 | `app/tools/` 技术实现需与领域 Runtime 边界继续收敛 |
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

迁移要求已完成：

- 生产入口统一为 `app.services.memory`；
- Runtime 入口统一为 `app.runtime.memory`；
- 删除旧 Service / Runtime 文件，不保留兼容垫片；
- Memory 单元测试 import 已同步切换；
- Module Refactor Gate 已加入旧路径、目录和 Memory targeted tests 检查；
- 新增/重构模块补充中文职责、边界与关键依赖说明；
- 本轮未新增数据库 Migration，Memory 数据结构保持不变。

## 6. Agent：彻底迁移完成

```text
app/services/agent/
├── __init__.py
├── service.py
└── repository.py
```

原 `app/services/agent_registry.py` 与 `app/services/agent/registry.py` 已删除；生产代码直接使用 `app.services.agent`，不存在兼容垫片或双实现。

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

## 8. Model

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

## 9. Workflow / Trigger / Organization / Governance / Observability / Tool

这些领域继续遵循目标结构与“完整迁移、删除旧文件、旧路径搜索为 0、重复实现为 0”的统一验收规则。具体迁移必须基于当前实际职责，不机械归类。

## 10. 每个迁移单元验收

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
11. 更新 Migration Map、PROJECT_STATUS 与必要的 Error 记录。

**只有代码、import、测试、重复实现检查、模块说明和文档全部完成，才能将领域标记为迁移完成。**
