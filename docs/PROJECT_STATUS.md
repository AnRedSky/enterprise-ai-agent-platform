# Project Status

> 当前项目状态唯一入口。文档治理规则见 `docs/01-governance/DOCUMENTATION.md`，工程开发规则见 `docs/01-governance/DEVELOPMENT.md`。

## 1. 当前基线

- Repository: `AnRedSky/enterprise-ai-agent-platform`
- Branch: `main`
- 开发原则：所有任务直接基于最新 `main`，禁止 feature / task / 临时分支。
- 当前文档治理：Docs Governance Refactor 第二阶段已完成。
- 当前开发阶段：**Phase 1.9 — Runtime Reliability / Production Hardening**。

## 2. 整体功能开发进展评估

> 本节是当前产品能力的开发状态评估，不把历史 Phase Acceptance 的 PASS 扩大解释为“当前所有生产能力均已完成”。“已实现当前历史范围”表示已有代码、Contract 和历史验收证据；“待生产化”表示仍需要当前 main 上的真实场景、并发、失败恢复或跨层 Gate 重新验证。

| 功能域 | 当前状态 | 评估 |
|---|---|---|
| Identity / JWT / RBAC / Tenant | 已实现当前历史范围 | 已形成用户、角色、JWT、Tenant scope 与 Workflow 权限边界；仍需持续作为跨域回归门禁 |
| Agent / AgentVersion / Publish | 已实现当前历史范围 | 已有 Agent/Version、发布版本和 Runtime 使用已发布版本的约束 |
| Agent Chat / Model Gateway | 已实现当前历史范围 | 已形成 Provider Contract、Mock/OpenAI-compatible Provider、普通/流式调用和错误边界；真实 Provider 仍以本地 Real API 为准 |
| Tool Registry / HTTP Tool | 已实现当前历史范围 | 已形成 Registry、AgentTool 权限、Schema、Timeout、响应大小和 SSRF/网络安全边界 |
| Memory | 已实现当前历史范围 | PostgreSQL MemoryRecord/Service 与 Runtime Context 已形成；当前不扩展向量记忆/自动摘要等未纳入范围的能力 |
| Observability / Audit / Trace | 已实现当前历史范围 | Execution/Event/Trace/Token/Audit 已形成跨 Runtime / Workflow 关联 |
| Knowledge / Ingestion | 已实现当前历史范围 | Knowledge、Document/Version/Chunk ingestion 和权限边界已形成 |
| Retrieval / Vector / Hybrid | 已实现当前代码范围 | Lexical、Vector、Hybrid、Evaluation 与 Debug 已形成；真实 Embedding Provider 的语义质量不能由 Mock 结论替代 |
| Workflow Definition / Version / Execution | **1.9-C 当前被 Runtime orchestration 回归阻塞** | 已有 Definition、Publish、Execution State Machine；当前 Real API bootstrap 暴露 `WorkflowRuntime.execute` 缺失，修复等待本地验证 |
| Workflow Governance / Audit / Trace | 已实现当前历史范围 | Tenant/RBAC、Audit、Trace、Execution lineage 已形成 |
| Retry / Timeout / Idempotency / Deadline | **1.9-C 正在真实 API 可靠性验证** | 1.9-B focused scope 已验证；1.9-C 首轮发现 idempotency 并发 500，随后又发现 Runtime orchestration 500；均已有修复提交但尚未重新验证 |
| Circuit Breaker | **1.9-A/1.9-B focused scope 已验证** | 1.9-A 与 1.9-B stale Probe completion 修复均已通过本地专项/Backend/PostgreSQL/Real API 验证；Phase 1.9 尚未整体关闭 |
| Scheduled Trigger | **历史能力存在，当前受 WorkflowRuntime.execute 回归影响** | Backend 日志显示 Scheduled Trigger dispatch 同样触发 `WorkflowRuntime.execute` AttributeError；修复已提交，等待本地验证 |
| Webhook Trigger | 已实现当前历史范围 | Phase 1.8 已形成认证、durable idempotency、Workflow Execution 和 Browser E2E |
| Frontend Governance UI | 已实现当前历史范围 | Vue 管理端已覆盖 Agent/Workflow/Knowledge/Trigger 等历史范围 |
| Browser E2E | 已形成独立 Gate | 已有 Playwright 场景；当前继续作为跨层可靠性验证层 |
| Multi-Agent orchestration | **未纳入当前已完成范围** | 当前架构文档列为长期目标，不应宣称已经完成 |
| MQ/Kafka/Event Bus | **未纳入当前范围** | Phase 1.8 明确 Out of Scope |
| 分布式 Worker / Temporal | **未纳入当前范围** | 当前 Runtime 仍为现有单体边界，不宣称已有完整分布式调度系统 |

## 3. Phase 状态

| Phase | 状态 | 说明 |
|---|---|---|
| Phase 1.0 | 已完成 | 基础项目初始化与最小能力 |
| Phase 1.2 | 已完成 | 基础平台、Auth/RBAC、Agent、Session、Runtime、Model/Tool 基础能力 |
| Phase 1.3 | 已完成当前历史范围 | Model Gateway / Tool Runtime / Memory / Observability |
| Phase 1.4 | 已完成当前历史范围 | Knowledge / RAG / Retrieval；真实 Provider 语义质量保持验证边界 |
| Phase 1.5 | 已完成 / 正式关闭 | Workflow / Governance / Reliability / Circuit Breaker 基础能力 |
| Phase 1.6 | 已完成 / 正式关闭 | Trigger / Frontend / Browser 历史范围；未发现独立 1.6-D 正文，不补造 |
| Phase 1.7 | 已完成 / 正式关闭 | Scheduled Trigger / Governance / Browser E2E |
| Phase 1.8 | 已完成 / 正式关闭 | Event / Webhook Trigger Expansion |
| **Phase 1.9** | **进行中** | 1.9-A 已验证；1.9-B focused scope 已验证；1.9-C 当前被 ERR-0019 bootstrap blocker 阻塞 |

## 4. Phase 1.9 当前任务

### 1.9-A Circuit Breaker HALF_OPEN Concurrent Recovery

状态：**本地验证完成。**

```text
Targeted Circuit Breaker tests → 16 passed in 0.68s
Backend Regression → 262 passed, 20 deselected in 3.64s
Migration head → 0022_workflow_trigger (head)
Mandatory Real API → 20 passed in 32.99s
Standalone Real API → 20 passed in 33.26s
```

### 1.9-B Runtime Failure / Retry / Circuit Boundary Audit

状态：**focused scope 本地验证完成。**

```text
Focused runtime tests → 35 passed in 0.97s
Backend Regression → 264 passed, 20 deselected in 4.79s
Migration head → 0022_workflow_trigger (head)
Mandatory Real API → 20 passed in 40.74s
Standalone Real API → 20 passed in 31.38s
```

### 1.9-C Real API Reliability Scenarios

状态：**阻塞。**

首轮完整 Real API Gate：

```text
22 passed, 1 failed in 39.35s
Failure: concurrent idempotency request returned HTTP 500
```

ERR-0018 已记录并有修复提交，但尚未重新验证。

随后重新运行正式 Gate 时，bootstrap 暴露新的 Runtime orchestration blocker：

```text
POST /workflows/executions/{execution_id}/run
expected HTTP 404, got 500
{"detail":"Workflow Runtime 执行失败"}

AttributeError: 'WorkflowRuntime' object has no attribute 'execute'
```

同一问题同时出现在 Scheduled Trigger dispatch。

正式错误记录：

```text
docs/04-errors/ERR-0019-workflow-runtime-execute-missing.md
```

已提交修复：

```text
0cb983f979962d182a519a380511284cc11e2cda
fix: restore workflow runtime execution orchestration
```

修复恢复了 `WorkflowRuntime.execute()`，负责 sequential orchestration、node timeout、workflow deadline、retry policy、workflow retry budget、node state transitions 以及完成态收口。

**ERR-0019 仍为 Open：代码已修复，尚无本地验证证据。**

### 1.9-D Frontend / Browser Reliability Convergence

尚未执行。

### 1.9-E Final Acceptance

尚未执行。

## 5. 已完成文档治理整改

Docs Governance Refactor 第二阶段已经完成：

```text
docs/
├── README.md
├── PROJECT_STATUS.md
├── DOCS_MIGRATION_MATRIX.md
├── 00-architecture/
├── 01-governance/
├── 02-phases/
├── 03-acceptance/
└── 04-errors/
```

## 6. 当前 Phase 1.9 实际测试记录

```text
1.9-A Circuit Breaker targeted tests: 16 passed in 0.68s
1.9-A Backend Regression: 262 passed, 20 deselected in 3.64s
1.9-A Alembic head: 0022_workflow_trigger
1.9-A Real API via Backend Gate: 20 passed in 32.99s
1.9-A Standalone Real API Gate: 20 passed in 33.26s

1.9-B Focused runtime tests: 35 passed in 0.97s
1.9-B Backend Regression: 264 passed, 20 deselected in 4.79s
1.9-B Alembic head: 0022_workflow_trigger
1.9-B Real API via Backend Gate: 20 passed in 40.74s
1.9-B Standalone Real API Gate: 20 passed in 31.38s

1.9-C First Real API Gate: 22 passed, 1 failed in 39.35s
Failure: concurrent idempotency request returned HTTP 500

1.9-C Subsequent Real API bootstrap:
Workflow Runtime execute missing → HTTP 500
No new PASS result yet.
```

## 7. 当前风险 / 未完成范围

1. 1.9-A 已通过本地 Unit / Backend / PostgreSQL Migration / Real API Gate。
2. 1.9-B focused scope 已通过本地验证。
3. 1.9-C 当前存在两个尚未重新验证的修复边界：ERR-0018 Idempotency race、ERR-0019 WorkflowRuntime orchestration。
4. Scheduled Trigger 当前同样受到 ERR-0019 影响，必须通过本地验证确认修复没有回归。
5. Cross-Tenant isolation 尚未形成真实 API 测试上下文。
6. Frontend / Browser Reliability Convergence 尚未执行，因此不能关闭 Phase 1.9。
7. Multi-Agent orchestration、MQ/Kafka/Event Bus、Temporal/完整分布式 Worker 不属于当前已完成范围。

## 8. 下一步执行顺序

严格遵守 `docs/01-governance/DEVELOPMENT.md`：

1. **先执行 Workflow Runtime / Retry / Timeout 专项单元测试，验证 ERR-0019。**
2. **再执行完整 Real API Gate，同时验证 ERR-0018 与 ERR-0019。**
3. 如果 bootstrap 成功，继续完成 1.9-C 剩余 Real API Reliability 场景。
4. 发现新的阻塞问题立即进入 `docs/04-errors/`，不提前关闭当前错误。
5. 完成 Frontend Regression、Browser E2E 和 Frontend/Backend reliability convergence。
6. 最终同步 Acceptance 并关闭 Phase 1.9。
