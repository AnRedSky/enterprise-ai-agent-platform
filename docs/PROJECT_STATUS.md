# 项目状态

## 当前阶段

- Repository: `AnRedSky/enterprise-ai-agent-platform`
- Branch: `main`
- Phase 2.7 Advanced Workflow Orchestration：主线生产代码已完成，当前 Real API / Migration / 人工验收存在阻塞，不能标记最终验收通过。
- Phase 2.8-A Multi-Agent Collaboration Contract：已冻结。
- 当前开发任务：**Phase 2.8 Backend Domain + API Contract**，已完成首版实现并等待本地验证。

## Phase 2.7 已完成主线能力

- Durable Resume / Recovery / Replay / Checkpoint lineage：完成。
- DAG Conditional Branch / Multi-frontier / Join：完成。
- Frontier claim / lease / heartbeat / fencing / stale-worker guard：完成。
- Frontier terminalization / duplicate completion / replay boundary：完成。
- Scheduler → Worker PostgreSQL durable execution：保持现有架构，不引入第二套可靠性状态机。

## 2026-08-28 开发者实际反馈

### Backend Unit / Default Regression

```text
uv run pytest -q
811 passed, 3 skipped, 41 deselected
```

该结果来自 `1917a15` 基线，说明上一轮 Unit / Default Regression 已通过。

### Phase 2.7 Real API Gate

开发者实际执行 tenant-safe Real API Gate：

```text
25 tests executed
15 failed, 25 total
```

主要现象：

- Runtime Governance fixture 使用 `edges: []`，与当前 DAG validator 的非空 `edges` Contract 漂移；
- Resume DAG 场景缺少预期 Node / Checkpoint fact；
- Webhook / Governance 出现 `Node 不允许从 completed 到 failed`；
- 多个 `/run` 场景出现 409 Worker claim / lifecycle 竞争结果。

以上结果是实际失败，不标记为 PASS。

## 本轮代码变更

### Phase 2.7 Real API blocker 修复

- `WorkflowNodeExecution` 增加 tenant durable identity；
- 新增 migration `0037_workflow_node_execution_tenant`，历史数据从 Execution tenant 回填；
- 新增 migration `0039_workflow_node_execution_tenant_trigger`，兼容现有只提供 execution_id 的 Node 写入路径并保持 tenant fail-closed。

### Phase 2.8-A Backend Domain + API Contract

新增：

- `AgentDelegation` Durable Entity；
- `AgentDelegationRepository`；
- `AgentDelegationService`；
- Delegation identity / budget 单一正式计算入口；
- `POST /workflows/{execution_id}/delegations`；
- `GET /workflows/{execution_id}/delegations`；
- `GET /workflows/{execution_id}/delegations/{delegation_id}`；
- `POST /workflows/{execution_id}/delegations/{delegation_id}/cancel`；
- migration `0038_agent_delegations`；
- Multi-Agent 治理默认配置：depth / active-count / timeout / model budget；
- Delegation Unit / Real API 测试与本地 Gate 脚本。

首版严格保持：tenant/version/permission fail-closed、稳定幂等、显式 context、预算边界、父子 Trace/Audit，不新增第二套 Retry / Recovery 状态机。

## 当前验证状态

本轮新增代码尚未由开发者本地重新执行，因此以下均不得标记 PASS：

- `uv run pytest -q`（包含本轮代码）；
- `uv run alembic upgrade head` / `uv run alembic current`，预期新 head 为 `0039_workflow_node_execution_tenant_trigger`；
- Phase 2.7 tenant-safe Real API Gate；
- Phase 2.8 Delegation Real API Gate；
- Worker / Scheduler 生命周期场景。

## 下一执行顺序

```text
1. 同步最新 main
2. uv run pytest -q
3. uv run alembic upgrade head
4. uv run alembic current
5. Phase 2.7 tenant-safe Real API Gate
6. Phase 2.8 Delegation Contract Gate
7. Worker / Scheduler 实际 Delegation Runtime 集成
8. Frontend API Types / UI（如需要）
9. Browser E2E（如需要）
10. Acceptance / Status / Error 收口
```

## 本地服务要求

Backend Unit 不需要外部服务。Migration / Real API / Runtime 手动验收需要：

- PostgreSQL：`localhost:5432`；
- Redis：`localhost:6379`（Scheduler / 既有缓存能力依赖）；
- API Service：`127.0.0.1:8000`；
- Scheduler Service：独立进程；
- Worker Service：至少 1 个独立进程；
- 若执行真实模型调用，再启动本地 Ollama / 配置真实 Provider。

服务必须由开发者单独启动；测试 Gate 不自动管理服务进程。
