# 产品需求与功能开发对比矩阵

> 基线：`main` @ `b5aeb9bab6b6eae63e8f20d45993caf9b3b7a784`
> 目的：将“产品能力目标、当前实现、验收证据、明确缺口、下一步决策”放在同一张可追溯矩阵中。
> 规则：`已实现` 只表示当前代码/Phase 已有对应能力；`已验收` 必须有项目实际 Acceptance 证据；`待决策` 不得直接转化为开发任务。

## 1. 总体对比

| 产品域 | 产品目标 | 当前实现 | 验收状态 | 差距 | 下一动作 |
|---|---|---|---|---|---|
| Identity / RBAC | 企业用户、角色、Tenant 隔离 | Auth、RBAC、Tenant scope | 已覆盖 | 完整组织/IAM 能力未定义 | 产品需求盘点 |
| Agent | 可配置、版本化、可治理 Agent | Agent + Version + Owner/RBAC | 已覆盖当前范围 | Marketplace、发布生态未定义 | 不直接开发 |
| Runtime | 稳定执行 Agent | Runtime + Session + Context + Model/Tool/Knowledge/Memory | 已验收 | 更复杂 orchestration 未定义 | 保持基线 |
| Model Gateway | Provider-neutral LLM 接入 | Mock/OpenAI-compatible、普通/流式 Contract | 已覆盖当前范围 | 高级路由/Fallback/成本治理是否需要待产品决策 | 需求盘点 |
| Tool Runtime | 安全、可审计工具调用 | Registry/Binding/Schema/HTTP Executor/Audit | 已覆盖当前范围 | 通用代码执行明确禁止 | 保持边界 |
| Memory | Session/用户/Agent 可见记忆 | PostgreSQL MemoryRecord/Service | 已覆盖当前范围 | 向量记忆、自动摘要等未纳入 | 需求盘点 |
| Observability | 可查询、可追踪、可审计 | Execution/Event/Trace/Audit + UI | 已验收当前范围 | 分布式 Observability 平台未定义 | 保持基线 |
| Knowledge | 企业文档知识库 | KB/Document/Version/Chunk/Ingestion | 已覆盖当前范围 | Parser/复杂文件类型等需真实需求验证 | 质量盘点 |
| Retrieval | 高质量企业检索 | Lexical/Vector/Hybrid/Citation/Debug/Evaluation | 已覆盖工程链路 | 真实 Embedding 语义质量仍需 Provider 验证 | Provider 质量评估 |
| Workflow | 可治理流程执行 | Definition/Version/Publish/Execution | 已验收 | 复杂 DAG/Saga/Engine 未实现 | 产品决策 |
| Governance | Tenant/RBAC/Audit/Trace/Reliability | 已形成闭环 | 已验收 | 高级 Policy DSL 未定义 | 不直接开发 |
| Circuit Breaker | Provider/Workflow 失败隔离 | CLOSED/OPEN/HALF_OPEN + persistence/drift | 已验收 | 无明确新缺口 | 只维护回归 |
| Manual Trigger | API 业务入口 | CRUD/Invoke/Lifecycle | 已验收 | 无明确新缺口 | 保持 |
| Scheduled Trigger | 时间驱动 Workflow | interval Scheduler + idempotency + recovery | 已验收 | 无 lease/misfire/next_run_at | 是否产品化需决策 |
| Webhook Trigger | 外部事件驱动 Workflow | Secret/Auth/Event identity/Idempotency | 已验收 | 通用 Event Bus 未实现且明确 Out of Scope | 产品决策 |
| Frontend | 管理、配置、调试 | Vue 3 + API Types + Governance UI | 已验收当前范围 | 产品体验仍可深化 | 结合产品需求 |
| Browser E2E | 真实用户链路验证 | Playwright Browser → Vue → Backend | 已验收 | 新功能需新增独立 E2E | 随新 Phase 执行 |

## 2. Phase 与产品能力映射

| Phase | 主要产品能力 | 当前状态 | 是否继续 |
|---|---|---|---|
| 1.0 | 项目初始化 / 最小基础 | 已完成 | 否 |
| 1.2 | 基础平台、Auth/RBAC、Agent、Session、Runtime、Model/Tool 基础 | 已完成 | 否 |
| 1.3 | Model Gateway、Tool Runtime、Memory、Observability | 已完成当前历史范围 | 否，除新需求/回归 |
| 1.4 | Knowledge / RAG / Retrieval | 已完成当前历史范围 | 只对真实 Provider 质量做新需求验证 |
| 1.5 | Workflow / Governance / Reliability / Circuit Breaker | 正式关闭 | 否，除新需求/回归 |
| 1.6 | Trigger Contract / Frontend / Browser | 正式关闭 | 否，除新需求/回归 |
| 1.7 | Scheduled Trigger / Scheduler | 正式关闭 | 否，除新需求/回归 |
| 1.8 | Webhook / Event Trigger | 正式关闭 | 否，除新需求/回归 |
| 1.9 | Runtime Reliability / Production Hardening | 正式关闭 | 否，除新需求/回归 |
| 新阶段 | 尚未正式定义 | 待产品/架构决策 | 下一步先做需求基线，不直接假定 Phase 2 |

## 3. 当前产品“完成”的判定标准

### P0 — 产品能力存在

代码已经提供领域对象、Service、API 或 UI 能力。

### P1 — Contract 完整

Backend API Contract、权限、Tenant、错误码、生命周期、数据模型边界已经明确。

### P2 — 自动化测试覆盖

Backend pytest / Frontend Vitest / 必要 Integration 与 API Contract tests 已覆盖关键行为。

### P3 — Real API 验证

真实 PostgreSQL/Redis/HTTP/Provider 边界按任务要求实际执行，而不是只运行 Mock。

### P4 — Browser E2E

涉及前后端用户链路时，通过真实 Browser → Vue → Backend HTTP 验证。

### P5 — Acceptance / Status 关闭

对应 Phase Acceptance、Project Status、错误记录已经同步，任务正式关闭。

当前 Phase 1.9 已达到 P5；不能因为还有长期产品目标，就将已关闭 Phase 标记为未完成。

## 4. 当前已确认的开发缺口

### G-01 文档基线一致性

仓库根 `README.md` 仍保留“当前推进 Phase 1.7”的历史描述，而 `PROJECT_STATUS.md` 已明确 Phase 1.9 正式关闭。该差异属于文档一致性问题，应在本次基线整理后修正，避免新开发者误判当前阶段。

### G-02 下一阶段尚未立项

当前没有正式的 Phase 2.x 规划文档。不得直接把历史 Out of Scope 条目转化为 Phase 2。

### G-03 真实 Retrieval Provider 质量

Phase 1.4 已完成当前工程范围，但明确保留真实 Embedding Provider 语义质量验证边界。若产品目标要求生产语义质量指标，应建立独立需求、数据集、Provider validation 与 Acceptance，而不是修改已有 Mock Quality Gate。

### G-04 Scheduler 产品化边界

当前 Scheduler 有意保持单体轻量设计，没有 `next_run_at`、lease、misfire、独立 scheduler state。只有当真实产品需求要求 durable scheduler semantics 时，才建立独立 Contract 与 Phase。

### G-05 Workflow 编排深度

当前 Workflow 已完成串行 Runtime 与 Trigger 治理，但复杂 DAG、并行、条件分支、Saga、Multi-Agent orchestration 等不属于当前 Phase。是否进入后续产品路线必须由需求决定。

### G-06 Enterprise IAM / Organization

当前已有 Auth/RBAC/Tenant scope，但系统文档长期目标中的“用户、组织、角色、权限”并不等同完整企业 IAM。组织层级、部门、用户生命周期、SSO/SCIM 等均未形成当前 Contract；不能未经需求确认直接开发。

## 5. 后续任务拆解规则

当下一阶段需求正式确定后，每个能力按以下任务模板拆解：

```text
Task N-A 需求 / Product Contract
Task N-B Backend Domain + API Contract
Task N-C Database Migration + Backend Tests
Task N-D Real API / Integration Validation
Task N-E Frontend API Types + Vitest
Task N-F Frontend UI
Task N-G Backend Regression Gate
Task N-H Frontend Regression Gate
Task N-I Browser E2E
Task N-J Acceptance + Project Status + Error Records
```

若任务不涉及数据库、Frontend 或 Browser，则不得为了形式强行新增对应任务；但验收边界必须在任务文档中明确。

## 6. 每项开发必须回答的产品问题

1. 解决哪个企业用户场景？
2. 现有能力为什么不足？
3. Backend Contract 是什么？
4. 数据是否需要新增/变更？
5. Tenant / RBAC 边界是什么？
6. Failure / Retry / Timeout / Idempotency 边界是什么？
7. Observability / Audit 如何追踪？
8. Frontend 是否只是展示后端规则？
9. Real API 如何证明真实链路？
10. Browser E2E 是否需要覆盖真实用户路径？
11. Acceptance 的关闭条件是什么？
12. 是否需要同步 `PROJECT_STATUS.md`、Phase、Acceptance、`docs/04-errors/`？

## 7. 结论

截至当前 `main`，项目已经完成从基础 Agent Runtime 到 Knowledge/RAG、Workflow/Governance、Trigger、Scheduler、Webhook 和 Runtime Reliability 的第一阶段工程闭环。当前最重要的不是继续重复增强已关闭 Phase，而是将“长期产品目标”和“已验证产品能力”重新建立一份可追溯基线。

在新的产品需求尚未正式确认前，项目保持 **Phase 1.9 已关闭 / 新 Phase 待立项** 状态。后续开发以该矩阵为入口，先确定需求与架构，再按照 `docs/01-governance/DEVELOPMENT.md` 的固定顺序拆解和执行。
