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
| Workflow | `app/services/workflow/` + `app/runtime/workflow/` | 已完成代码迁移，待全量最终 Gate | WorkflowRuntime 已归位，旧根 Runtime 已删除 |
| Trigger | `app/services/trigger/` | 已完成代码迁移，待全量最终 Gate | Manual / Scheduled / Webhook 已统一 |
| Organization | `app/services/organization/` | 已完成代码迁移，待全量最终 Gate | 旧根 Service 已删除 |
| Observability | `app/services/observability/` | 已完成代码迁移，待全量最终 Gate | Service 已统一 |
| Retrieval Evaluation | `app/services/retrieval_evaluation/` | 已完成代码迁移，待全量最终 Gate | Trace / Dataset / Baseline / Config 已收敛 |
| Runtime Query | `app/services/runtime_query/` | 已完成代码迁移，待全量最终 Gate | 旧根 Service 已删除 |
| Session | `app/services/session_service/` | 已完成代码迁移，待全量最终 Gate | 旧根 Service 已删除 |
| Tool | `app/services/tool/` + `app/tools/` | 已完成代码迁移，待全量最终 Gate | 删除重复 `app.tools.registry`；`app.tools` 仅保留 HTTP/Schema 技术实现 |
| Usage Accounting | `app/services/usage_accounting/` | 已完成代码迁移，待全量最终 Gate | 旧根 Service 已删除 |
| Runtime | `app/runtime/<domain>/` | **边界收口中** | 当前仅保留 memory / model / workflow Runtime；新增 Runtime Boundary Gate，继续确认无根目录实现、旧 import 与 Governance 重复实现 |
| API v1 | `app/api/v1/<domain>/` | **代码迁移完成，Gate 已通过用户本地反馈** | 原 `app/api/*.py` 已按认证、Agent、Knowledge、Model Provider、Organization、Runtime、Tool、Usage、Webhook、Workflow 领域归位；路由前缀保持不变 |

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

**只有代码、import、测试、重复实现检查、模块说明和文档全部完成，才能将领域标记为“迁移完成”。**

## 9. 当前下一顺序

1. 本地同步最新 `main` 并执行 API v1 Module Gate；
2. 修复 Gate 暴露的生产/测试 import、模块说明、目录边界或重复实现问题；
3. 执行 Workflow / Tool / Runtime 全量最终 Gate；
4. **执行 Runtime Boundary Gate，完成 Runtime 与 Governance 职责边界收口；**
5. 完成全部重构领域的最终 Gate 后，执行一次全量 Backend Regression、旧路径/重复实现扫描；
6. 全部重构领域通过 Module Refactor Gate + Backend Regression 后，才能恢复主线任务。