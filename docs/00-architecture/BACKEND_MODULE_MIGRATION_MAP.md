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
| Model | `app/services/model/` + `app/runtime/model/` + Provider | 已完成 | Service / Contract / Routing / Governance / Runtime Gateway / Provider 已收敛，旧 Service / Runtime Provider 入口删除 |
| Workflow | `app/services/workflow/` + `app/runtime/workflow/` | **整改中** | Canonical import 与循环依赖已修复，40 个 Workflow targeted tests 已在本地反馈通过；Module Refactor Gate 仍需本地最终验收 |
| Trigger | `app/services/trigger/` | **代码迁移完成，待 Gate 验收** | Manual / Scheduled / Webhook 已统一进入 Trigger 子模块；旧 Trigger Service、Schedule、Webhook 文件已删除；测试 import 已切换 |
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

## 8. Model：彻底迁移完成

### 原结构

```text
app/services/model_provider.py
app/services/model_provider_governance_contract.py
app/services/runtime_model_governance.py
app/runtime/model_gateway.py
app/runtime/provider.py
app/runtime/openai_provider.py
```

### 当前正式结构

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

迁移结论：

- `ModelProviderService` 已归入 `app.services.model.provider`；
- Provider Governance Contract、Fallback/Cost/Usage 领域值对象已归入 `app.services.model.contract`；
- Provider 路由筛选规则已归入 `app.services.model.routing`，不再由 API 或 Runtime 重复实现路由规则；
- `RuntimeModelGovernanceService` 已归入 `app.services.model.governance`；
- `ModelGateway` 已归入 `app.runtime.model.gateway`，作为 Runtime 唯一模型调用入口；
- OpenAI-compatible、Mock Provider 及统一 Provider Contract 已归入 `app.infrastructure.providers`；
- 已知生产/测试 import 已切换到新入口；
- 原 Service / Runtime Provider 文件已删除，不保留兼容垫片；
- Module Refactor Gate 已增加 Model 旧路径、旧 import、目录、Provider 文件和 targeted tests 检查；
- 新增/重构 Model 模块均补充中文职责、边界和关键依赖说明；
- 本轮未新增数据库 Migration，Model 数据结构保持不变。

## 9. Workflow：当前整改状态

Workflow 已完成旧入口物理删除与 canonical import 切换。随后发现 `WorkflowExecutionService -> WorkflowRuntime -> app.services.workflow` 的模块初始化循环，已通过 Runtime 仅在未注入 Execution Service 时延迟解析正式入口的方式修复；不恢复旧文件、不增加第二套实现。

当前用户本地反馈：

- `uv run python -c "from app.main import app; print('APP_IMPORT_OK')"`：`APP_IMPORT_OK`；
- Workflow targeted tests：`40 passed in 1.40s`；
- 旧 Workflow import grep：无输出；
- Module Refactor Gate：此前因 PowerShell ParserError 未执行；Gate 已再次收紧为全域 legacy path、重复实现、模块说明和 Trigger targeted test 的统一验收入口；
- Backend Regression：必须在 Gate 成功后重新执行并记录实际结果。

因此 Workflow 暂不能标记“迁移完成”。

## 10. Trigger：本轮物理迁移

### 原结构

```text
app/services/workflow_trigger.py
app/services/workflow_trigger_schedule.py
app/services/webhook_trigger.py
```

### 当前正式结构

```text
app/services/trigger/
├── __init__.py
├── service.py
├── schedule.py
└── webhook.py
```

迁移结论：

- `WorkflowTriggerService` 已归入 `app.services.trigger.service`；
- scheduled/webhook 配置契约与 Secret 校验统一归入 `app.services.trigger.schedule`；
- `WebhookTriggerService` 已归入 `app.services.trigger.webhook`；
- Workflow API、Webhook API 与 Trigger 测试均切换到 `app.services.trigger` 正式入口；
- 原三个根目录 Trigger 文件已删除，不保留兼容垫片；
- Trigger 模块新增/重构文件均补充中文职责、边界和关键依赖说明；
- 不新增数据库 Migration；
- 代码迁移完成后必须通过完整 Module Refactor Gate，才能将 Trigger 标记为“迁移完成”。

## 11. Organization / Governance / Observability / Tool / API / Runtime

这些领域继续遵循目标结构与“完整迁移、删除旧文件、旧路径搜索为 0、重复实现为 0”的统一验收规则。具体迁移必须基于当前实际职责，不机械归类。

## 12. 每个迁移单元验收

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

**只有代码、import、测试、重复实现检查、模块说明和文档全部完成，才能将领域标记为“迁移完成”。**
