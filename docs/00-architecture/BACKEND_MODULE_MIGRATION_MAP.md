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
│   ├── agent/ ├── model/ ├── tool/ ├── knowledge/ ├── memory/
│   ├── workflow/ ├── trigger/ ├── scheduler/ ├── organization/
│   ├── governance/ └── observability/
├── runtime/
│   ├── agent/ ├── workflow/ ├── memory/ └── trigger/
├── infrastructure/
│   ├── db/ ├── redis/ ├── providers/ └── http/
├── utils/
└── main.py
```

## 3. 重构规则

1. **禁止兼容垫片**：旧业务文件迁移完成后必须删除。
2. **禁止双实现**：同一业务能力只能存在一个正式实现。
3. **禁止仅改目录名**：领域迁移必须同时完成职责、依赖与测试归位。
4. **禁止业务行为变更**：不修改既有业务规则、API Contract、数据库结构和 Provider 配置。
5. **import 必须彻底切换**：全仓搜索确认旧路径不存在。
6. **测试跟随迁移**：测试直接切换到新入口，不保留旧 import 兼容层。
7. **数据库不因目录重构产生 Migration**。
8. **功能重复实现检查必须是每个迁移单元的 Gate**。
9. **模块说明必须随代码迁移**：新增/重构模块必须有中文职责、边界和必要依赖说明。

## 4. 当前迁移状态

| 领域 | 目标模块 | 状态 | 说明 |
|---|---|---|---|
| Agent | `app/services/agent/` | 已完成 | 旧 Registry 入口及失效 Runtime 残留已清理 |
| Knowledge | `app/services/knowledge/` + Provider | 已完成 | 领域与 Provider 已分离 |
| Memory | `app/services/memory/` + `app/runtime/memory/` | 已完成 | Service 与 Runtime 已收敛 |
| Model | `app/services/model/` + `app/runtime/model/` + Provider | 已完成 | Gateway / Governance / Routing / Provider 已收敛 |
| Workflow | `app/services/workflow/` + `app/runtime/workflow/` | **整改中，待最终 Gate** | WorkflowRuntime 已移入 canonical `app.runtime.workflow.runtime`，旧根 Runtime 已删除 |
| Trigger | `app/services/trigger/` | 代码迁移完成，待 Gate | Manual / Scheduled / Webhook 已统一 |
| Organization | `app/services/organization/` | 代码迁移完成，待 Gate | 旧根 Service 已删除 |
| Observability | `app/services/observability/` | 代码迁移完成，待 Gate | Service 已统一 |
| Retrieval Evaluation | `app/services/retrieval_evaluation/` | 代码迁移完成，待 Gate | Trace / Dataset / Baseline / Config 已收敛 |
| Runtime Query | `app/services/runtime_query/` | 代码迁移完成，待 Gate | 旧根 Service 已删除 |
| Session | `app/services/session_service/` | 代码迁移完成，待 Gate | 旧根 Service 已删除 |
| Tool | `app/services/tool/` + `app/tools/` | **整改中，待最终 Gate** | 删除重复 `app.tools.registry`；`app.tools` 仅保留 HTTP/Schema 技术实现 |
| Usage Accounting | `app/services/usage_accounting/` | 代码迁移完成，待 Gate | 旧根 Service 已删除 |
| Runtime | `app/runtime/<domain>/` | **整改中** | 删除失效 `agent_runtime.py`；Workflow Runtime 已归位，继续检查其余 Runtime 域 |
| API | `app/api/v1/<domain>/` | 待迁移 | 当前 Router 仍有 `app/api/*.py` |

## 5. Workflow：本轮继续整改

正式结构：

```text
app/runtime/workflow/
├── __init__.py
├── circuit_breaker.py
└── runtime.py
```

`WorkflowExecutionService` 现在直接使用 `app.runtime.workflow.WorkflowRuntime`，旧 `app/runtime/workflow_runtime.py` 已删除；`runtime.py` 继续复用统一 `ModelGateway`、模型治理服务和 Circuit Breaker，不新增第二套模型调用实现。

本轮必须继续完成：

- Module Refactor Gate；
- Workflow targeted tests；
- Backend Regression；
- 旧路径搜索与重复实现审查。

## 6. Runtime：失效实现清理

原 `app/runtime/agent_runtime.py` 为未被生产链路使用且引用已不存在的旧模型入口的残留实现。本轮直接删除，不创建新的兼容模块；当前 Agent Runtime 行为由实际生产执行链路承担，待后续 Runtime 领域审查确认是否需要独立 canonical module。

这符合“禁止双实现”和“不得为了目录结构制造空壳模块”的原则。

## 7. Tool：唯一领域入口

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

`app.services.tool` 负责 Tool 领域治理、执行编排、权限、审计、可观测性与持久化适配；`app.tools` 只负责 HTTP/Schema 等底层技术执行能力。原 `app/tools/registry.py` 与正式 Tool Service 存在重复注册抽象且未形成生产唯一入口，本轮已删除。

## 8. 测试与脚本目录规则

- `backend/tests/` 根目录不得放置 `test_*.py`；测试必须归入 `tests/unit` 或 `tests/integration`。
- 依赖边界测试已迁移至 `tests/unit/test_dependency_boundary.py`。
- `backend/scripts/test/` 用于自动化测试脚本；开发/环境验证脚本进入 `backend/scripts/dev/`。
- Ollama Embedding 本地验证已迁移为 `scripts/dev/validate_ollama_embedding.py`，不再使用 `scripts/test_ollama_embedding.py`。

## 9. 每个迁移单元验收

1. 全仓搜索旧 import 路径，结果为 0；
2. 旧文件和旧目录已删除；
3. 不存在重复实现；
4. 生产代码只存在一个正式入口；
5. 受影响测试已切换；
6. 每个新增/重构模块有中文职责与边界说明；
7. targeted tests；
8. Backend Regression；
9. 必要时 Real API / Tenant Safe Real API；
10. Alembic `upgrade heads` / `current`，确认没有因目录重构产生数据库变化；
11. 更新 Migration Map、PROJECT_STATUS 与必要的 Error 记录。

**只有代码、import、测试、重复实现检查、模块说明和文档全部完成，才能将领域标记为“迁移完成”。**

## 10. 当前下一顺序

1. 本地同步最新 `main` 并执行 Module Refactor Gate；
2. 修复 Gate 暴露的生产/测试 import、模块说明、目录边界或重复实现问题；
3. 完成 Workflow / Tool / Runtime 其余领域最终 Gate；
4. 继续 Governance 与 API `v1/<domain>` 收敛；
5. 全部重构领域通过 Module Refactor Gate + Backend Regression 后，才能恢复主线任务。
