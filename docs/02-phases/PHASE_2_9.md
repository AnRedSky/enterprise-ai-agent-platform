# Phase 2.9 Enterprise Integration / Event Infrastructure

## 1. 阶段目标
在 Phase 2.8 Runtime Integration 收口后，建立 Enterprise Integration / Event Infrastructure：冻结统一事件 Contract，建立 PostgreSQL Durable Event Fact，再实现可靠投递、Webhook Integration 和 Runtime Integration。Redis、Kafka、MQ 均不是 Durable Event Fact 的必要依赖。

## 2. 当前基线
- Phase 2.8 Multi-Agent Collaboration / Runtime Integration：已完成并通过本地 B6 Real Gate。
- Phase 2.9-A Event Contract：已实现。
- Phase 2.9-B Durable Event Persistence：已实现第一切片，数据库 Migration 已验收。
- Phase 2.9-C Reliable Delivery：第二切片已通过本地真实 PostgreSQL Gate。
- Phase 2.9-D Webhook Integration：Provider / Delivery Worker / Security / Audit / Replay 已落地，进入 Real Acceptance 收口。
- Phase 2.9-E Runtime Integration：已启动，第一切片完成 Workflow / Agent / Scheduler 到统一 Durable Event Contract 的生产接入。

## 3. 2.9-A Event Contract
状态：**已实现**。统一事件信封包含 `event_id`、`tenant_id`、`event_type`、`schema_version`、`source`、`subject`、`idempotency_key`、`occurred_at`、`request_id`、`trace_id`、`payload`、`metadata`。

## 4. 2.9-B Durable Event Persistence
状态：**已实现第一切片；数据库 Migration 已验收**。Durable Event Fact、Repository、0040 Migration、attempt/retry/delivery 字段和幂等约束已完成。

## 5. 2.9-C Reliable Delivery
状态：**已完成真实 PostgreSQL 验收**。

## 6. 2.9-D Webhook Integration

### 6.1 Provider / Destination / Subscription / Fan-out
已实现统一 Event → HTTP Webhook Provider、Destination、Subscription、Delivery Fact、tenant-scoped Fan-out，以及重复规划幂等。

### 6.2 Webhook Delivery Worker
已实现 PostgreSQL `FOR UPDATE SKIP LOCKED` Claim、lease fencing、retry/backoff、dead-letter、独立 Worker 进程和 HTTP Provider。

当前已进一步完成 Worker Runtime 工程化：
- `concurrency` 参数限制单进程 in-flight Delivery 数量；
- 不建立无界任务队列，空闲执行槽才允许继续 Claim，形成明确 backpressure 边界；
- `stop()` 后不再领取新任务；
- graceful shutdown 会 drain 已经 Claim 的 in-flight Delivery；
- `WEBHOOK_WORKER_CONCURRENCY`、`WEBHOOK_WORKER_POLL_INTERVAL`、`WEBHOOK_WORKER_LEASE_SECONDS`、`WEBHOOK_WORKER_MAX_ATTEMPTS` 可通过环境配置；
- 已接入既有 `run_worker.py` / Worker Service，同一 Worker 进程并行承载 Workflow Worker 与 Webhook Delivery Worker。

### 6.3 Secret Resolver
**已实现。**
- `SecretResolver` 抽象；
- `EnvironmentSecretResolver` 支持显式 `env://NAME`；
- `MappingSecretResolver` 支持测试/依赖注入；
- Destination 不保存 plaintext secret；
- Provider 在发送时解析 Secret。

后续可增加 Vault/KMS Resolver，不改变 Worker 状态机。

### 6.4 SSRF / Endpoint Security
**已实现第一安全切片。**
- 默认仅 HTTPS；
- 拒绝 URL credentials / fragment；
- 端口 allowlist；
- DNS 解析后拒绝 loopback、private、link-local、multicast、unspecified、reserved 地址；
- 支持显式 enterprise egress hostname allowlist；
- HTTP Provider 禁止自动 follow redirect。

应用层策略不替代生产网络层 egress firewall / proxy allowlist。

### 6.5 Delivery Audit / Replay
**已实现。**
- 新增 `webhook_delivery_audits` immutable audit facts；
- delivered / retry / dead-letter / replay 均形成审计事实；
- tenant-scoped Delivery 查询；
- Delivery Audit 查询；
- 仅 `delivered` / `dead_letter` 允许 replay；
- replay 将 Delivery 重置为 `pending`，保留全部历史 Audit；
- 新增 `GET /api/v1/webhooks/deliveries`；
- 新增 `GET /api/v1/webhooks/deliveries/{delivery_id}/audit`；
- 新增 `POST /api/v1/webhooks/deliveries/{delivery_id}/replay`。

### 6.6 Real Acceptance Gate
新增 `backend/scripts/test/phase-2.9/02_webhook_delivery_real_gate.ps1`。

Gate 顺序：
1. 验证 `uv` 与 `.env.example`，不启动任何服务；
2. Alembic upgrade/current；
3. Security + Provider + Worker Runtime 单元回归；
4. 真实 PostgreSQL + 本机 ephemeral HTTP receiver 验证 Worker、HMAC、状态落库、Audit、Replay、并发与 graceful drain；
5. targeted integration regression。

Gate 不启动、不停止 API、Worker、Scheduler、Redis 或 PostgreSQL；测试数据自动生成和清理，不要求人工填写测试信息。

### 6.7 当前收口项
Worker 并发/backpressure/graceful shutdown 已完成并接入既有 Worker Service；剩余收口项是执行 `02_webhook_delivery_real_gate.ps1` 的真实 PostgreSQL + HTTP Acceptance，并根据结果修正实际运行环境问题。Real Gate 通过后 2.9-D 才标记为最终完成。

## 7. 2.9-E Runtime Integration

### 7.1 事务内 Runtime Event Publisher
**已实现第一切片。** 新增 `RuntimeIntegrationEventPublisher`，所有 Runtime Event 使用统一 `IntegrationEvent` Contract，并在产生业务事实的数据库事务内写入 `integration_events`；Publisher 不自行提交事务，唯一键冲突通过 savepoint + 查询收敛。

### 7.2 Workflow Runtime
**已接入第一关键事实：`workflow.execution.completed`。** Durable Frontier 最终完成并 terminalize Execution 时，同一事务同时持久化 Integration Event；事件包含 tenant、workflow、version、execution、frontier、worker attempt 等可审计上下文，幂等键为 `workflow-execution:{execution_id}:completed`。

这保证 Webhook Delivery Worker 后续消费到的 Workflow completion event 与 Workflow Durable Fact 具有原子一致性，不存在“Execution 已完成但事件尚未持久化”的进程崩溃窗口。

### 7.3 Agent Runtime
**已接入第一生命周期切片。** `ObservabilityService` 在 Agent Execution 创建/完成阶段生产：
- `agent.execution.started`；
- `agent.execution.completed`；
- `agent.execution.failed`。

事件复用现有 request/trace/execution 标识，并通过 Agent owner → User → Tenant 解析租户，禁止生成无租户 Runtime Event。

### 7.4 Scheduler Runtime
**已接入 Scheduled Trigger dispatch 事实。** Scheduler 调用 `WorkflowTriggerService.invoke_scheduled` 创建 Durable Execution + Frontier 时，同时生成 `scheduler.trigger.dispatched`；事件与 Execution/Frontier 写入同一事务，幂等键复用 Scheduled Trigger slot idempotency key 空间。

### 7.5 下一切片
下一步不再扩展新的事件基础设施，而是继续补齐业务事实覆盖：
1. Workflow `created / started / failed / cancelled / retry_requested / resume_requested`；
2. Agent Tool / Retrieval / Model provider 关键事实与统一事件关联；
3. Scheduler `lease / contention / misfire / recovery` 结果事件；
4. Integration Event 查询/运维视图与 tenant-scoped replay 管理；
5. Workflow / Agent / Scheduler event schema/version 的稳定文档与 Real Acceptance。

## 8. 开发边界
- Redis、Kafka、MQ 不作为 Durable Event Fact；
- 不复制已有 Webhook / Trigger / Audit / Trace 实现；
- 不修改已通过 Phase 2.8 B6 Gate 的 Delegation Runtime 主路径；
- 涉及数据库必须先 Migration，再 Backend/Repository，再测试和 Real API；
- Real Gate 不自动启动或停止任何依赖服务；
- 测试数据由脚本自动生成，不要求开发者手工填写测试信息。