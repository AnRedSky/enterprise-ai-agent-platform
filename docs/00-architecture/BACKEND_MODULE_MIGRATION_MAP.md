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
│   └── v1/<domain>/
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
| Workflow | `app/services/workflow/` + `app/runtime/workflow/` | **已完成** | 已通过最终 Refactor Closure Gate |
| Trigger | `app/services/trigger/` | **已完成** | 已通过最终 Refactor Closure Gate |
| Organization | `app/services/organization/` | **已完成** | 已通过最终 Refactor Closure Gate |
| Observability | `app/services/observability/` | **已完成** | 已通过最终 Refactor Closure Gate |
| Retrieval Evaluation | `app/services/retrieval_evaluation/` | **已完成** | 已通过最终 Refactor Closure Gate |
| Runtime Query | `app/services/runtime_query/` | **已完成** | 已通过最终 Refactor Closure Gate |
| Session | `app/services/session_service/` | **已完成** | 已通过最终 Refactor Closure Gate |
| Tool | `app/services/tool/` + `app/tools/` | **已完成** | 删除重复 `app.tools.registry`；`app.tools` 仅保留 HTTP/Schema 技术实现 |
| Usage Accounting | `app/services/usage_accounting/` | **已完成** | 已通过最终 Refactor Closure Gate |
| Runtime | `app/runtime/<domain>/` | **已完成** | memory / model / workflow Runtime 边界与唯一入口已通过最终 Closure Gate |
| API v1 | `app/api/v1/<domain>/` | **已完成** | API v1 Module Gate 与最终 Closure Gate 均通过；路由前缀保持不变 |

## 5. API v1：本轮完成物理归位

正式结构：

```text
app/api/
├── __init__.py
└── v1/
    ├── __init__.py
    ├── auth/
    │   ├── __init__.py
    │   └── router.py
    ├── agents/
    │   ├── __init__.py
    │   ├── router.py
    │   └── chat.py
    ├── knowledge/
    │   ├── __init__.py
    │   ├── router.py
    │   ├── ingestion.py
    │   └── retrieval.py
    ├── model_providers/
    │   ├── __init__.py
    │   └── router.py
    ├── organizations/
    │   ├── __init__.py
    │   └── router.py
    ├── runtime/
    │   ├── __init__.py
    │   └── router.py
    ├── tools/
    │   ├── __init__.py
    │   └── router.py
    ├── usage/
    │   ├── __init__.py
    │   └── router.py
    ├── webhooks/
    │   ├── __init__.py
    │   └── router.py
    └── workflows/
        ├── __init__.py
        ├── router.py
        └── executions.py
```

本轮只改变 API 文件物理边界与 import 路径，`/api/v1/*` 路由前缀、HTTP 方法、Request / Response Contract 保持原定义；不创建旧 API 兼容转发模块。

每个 API 领域包通过 `__init__.py` 提供中文职责、边界和关键依赖说明；HTTP Router 本身只负责协议适配，领域业务继续由现有 Service / Runtime 承担，避免在 API 层产生第二套业务实现。

## 6. Workflow / Runtime / Tool 继续规则

Workflow Runtime 正式结构：

```text
app/runtime/workflow/
├── __init__.py
├── circuit_breaker.py
└── runtime.py
```

Tool 正式结构：

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

`app.services.tool` 负责 Tool 领域治理、执行编排、权限、审计、可观测性与持久化适配；`app.tools` 只负责 HTTP/Schema 等底层技术执行能力。

Runtime 正式边界：

```text
app/runtime/memory/   # 执行期 Memory 上下文构造
app/runtime/model/    # 唯一 Model Gateway 执行入口
app/runtime/workflow/ # Workflow 节点执行、重试、超时与熔断
```

Runtime 不负责 Model Provider 治理、路由策略或领域持久化；这些职责分别由 `app/services/model/`、对应领域 Service 与 Repository 承担。不得在 Runtime 中新增第二套 Provider / Governance / Service 实现。

## 7. 测试与脚本目录规则

- `backend/tests/` 根目录不得放置 `test_*.py`；测试必须归入 `tests/unit` 或 `tests/integration`。
- `backend/scripts/test/` 用于自动化测试脚本；开发/环境验证脚本进入 `backend/scripts/dev/`。
- API v1 迁移 Gate 固定入口：`scripts/test/module-refactor/03_backend_api_v1_module_gate.ps1`。
- Runtime 边界 Gate 固定入口：`scripts/test/module-refactor/04_backend_runtime_boundary_gate.ps1`。
- 全部重构最终静态收口 Gate：`scripts/test/module-refactor/05_backend_refactor_closure_gate.ps1`。

## 8. 每个迁移单元验收

1. 全仓搜索旧 import 路径，结果为 0；
2. 旧文件和旧目录已删除；
3. 不存在重复实现；
4. 生产代码只存在一个正式入口；
5. 受影响测试已切换；
6. 每个新增/重构模块有中文职责与边界说明；
7. targeted tests；
8. Backend Regression；
9. 必要时 Real API / Tenant Safe Real API；
10. Alembic `upgrade head` / `current`，确认没有因目录重构产生数据库变化；
11. 更新 Migration Map、PROJECT_STATUS 与必要的 Error 记录。

**当前所有既有领域已经完成代码迁移、import 清理、重复实现检查、模块说明与对应 Gate；最终 Refactor Closure Gate 已由开发者本地实际通过。因此模块化重构不再阻塞主线任务。**

## 9. 当前下一顺序

1. 保留 Refactor Closure Gate 作为后续回归检查；
2. 恢复 Phase 2.4 Durable Scheduler 主线，先执行 Scheduler Runtime Gate；
3. 若 Runtime Gate 暴露问题，只修复 canonical Scheduler 模块，不创建兼容垫片或第二实现；
4. Runtime Gate 通过后推进 Scheduler API Contract / 状态可观测性、tenant isolation / misfire integration；
5. 按 Phase 2.4 顺序执行 Tenant Safe Real API、Backend Regression，以及需要时 Frontend / E2E；
6. 根据实际本地结果更新 Phase、Acceptance、Status 与必要 Error 记录。
