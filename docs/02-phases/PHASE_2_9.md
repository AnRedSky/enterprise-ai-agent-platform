# Phase 2.9 Enterprise Integration / Event Infrastructure

## 1. 阶段目标

在 Phase 2.8 Runtime Integration 收口后，建立 Enterprise Integration / Event Infrastructure：冻结统一事件 Contract，建立 PostgreSQL Durable Event Fact，再实现可靠投递、Webhook Integration 和 Runtime Integration。Redis、Kafka、MQ 均不是 Durable Event Fact 的必要依赖。

## 2. 当前基线

- Phase 2.8 Multi-Agent Collaboration / Runtime Integration：已完成并通过本地 B6 Real Gate。
- Phase 2.9-A Event Contract：已实现。
- Phase 2.9-B Durable Event Persistence：已实现第一切片，数据库 Migration 已由开发者本地升级至 `0041`。
- Phase 2.9-C Reliable Delivery：第一切片已实现；第二切片已补齐真实 PostgreSQL 验收测试入口。最新本地 Gate 首次进入 Real Gate 时发现 pytest 默认 marker 过滤导致 5 个真实测试被 deselect，现已修复专用 Gate 的 marker 选择逻辑，等待开发者重新执行真实 PostgreSQL 验收。
- 当前任务：**2.9-C Reliable Delivery 第二切片：真实 PostgreSQL 并发验收**。

## 3. 2.9-A Event Contract

状态：**已实现**。统一事件信封包含 `event_id`、`tenant_id`、`event_type`、`schema_version`、`source`、`subject`、`idempotency_key`、`occurred_at`、`request_id`、`trace_id`、`payload`、`metadata`。

幂等作用域冻结为：

```text
tenant_id + source + event_type + idempotency_key
```

## 4. 2.9-B Durable Event Persistence

状态：**已实现第一切片；本地 Migration 已验收**。

实现：

```text
backend/app/models/integration_event.py
backend/app/services/integration/repository.py
backend/alembic/versions/0040_integration_events.py
backend/tests/unit/test_integration_event_persistence.py
```

持久化模型提供 Tenant 隔离、Event Contract 核心字段、`pending` 初始状态、attempt count、retry time、delivery time、错误信息、幂等唯一约束和稳定 pending 查询。

## 5. 2.9-C Reliable Delivery

状态：**第一切片已实现；第二切片 Real Gate 已实现，最新 Gate 的测试选择问题已修复，待开发者重新执行真实 PostgreSQL 验收**。

实现：

```text
backend/app/services/integration/delivery.py
backend/alembic/versions/0041_integration_event_delivery_lease.py
backend/tests/unit/test_integration_event_delivery.py
backend/tests/api_real/test_integration_event_delivery_postgres.py
backend/scripts/test/phase-2.9/01_reliable_delivery_postgres_gate.ps1
backend/.env.example
```

当前实现：

- PostgreSQL `FOR UPDATE SKIP LOCKED` 原子 Claim；
- `lease_owner` / `lease_expires_at` Worker 租约；
- 过期 running 事件可恢复领取；
- 每次 Claim 增加 `attempt_count`；
- 成功后进入 `delivered`；
- 失败后按有限次数进入 `pending` retry；
- 使用 capped exponential backoff；
- 超过最大尝试次数进入 `dead_letter`；
- 外部 Sender 通过依赖注入提供，当前不绑定 Webhook/MQ Provider；
- PostgreSQL 保持 Durable Event Fact 唯一事实源；
- Delivery Service 使用正式 `app.infrastructure.db` 数据库入口；
- Delivery Service 正确透传 `mark_delivered` / `mark_failed` 的租约结果，旧 Worker 失去 fencing 后不会被报告为成功；
- Real Gate 自动生成并清理测试租户和事件，不要求手工填写测试信息；
- Real Gate 不启动、不停止 API、Worker、Scheduler、Redis 或 PostgreSQL；
- `backend/.env.example` 作为统一无 Secret 本地测试配置基线，并由 Gate 从脚本位置可靠解析 `backend` 根目录；
- Real Gate 显式使用 `-m real_api`，覆盖 pytest 全局 `addopts = -m 'not real_api'`，确保真实 PostgreSQL 验收测试实际执行。

### 第二切片真实验收范围

1. 两个或以上 Worker 并发 Claim 时同一 Event 只能被一个租约持有者领取；
2. Worker 在租约内成功投递后只产生一个 `delivered` 事实；
3. Worker 崩溃/租约过期后事件可以被另一 Worker 恢复；
4. Sender 临时失败进入 retry，并按退避时间重新变为可领取状态；
5. 达到最大尝试次数后进入 `dead_letter`；
6. 不同 tenant 之间不能互相 Claim Event；
7. 失去租约的旧 Worker 不能覆盖新 Worker 的最终状态；
8. 整个过程不依赖后台 Scheduler 自动消费测试数据。

### 本轮工程修复

发现 Phase 2.9-C Real Gate 的 `$BackendRoot` 路径计算多向上一级：脚本位于 `backend/scripts/test/phase-2.9`，原实现向上四级导致实际根目录落到仓库根目录，进而把 `backend/.env.example` 错误检查为根目录 `.env.example`。已修正为向上三级，并将缺失文件的 Git 检查改为直接检查 `HEAD:backend/.env.example`，避免本地 Git index 状态造成误判。

本轮再次发现：Real Gate 执行真实 PostgreSQL 测试时继承 `pyproject.toml` 的 `addopts = -m 'not real_api'`，导致 5 个真实验收测试全部 `deselected`。已将专用 Gate 改为显式 `-m real_api`，保持全局 Backend regression 不自动执行 Real API 测试。

错误记录：

```text
docs/04-errors/2026-08-29-phase-2-9-env-example-working-tree-missing.md
docs/04-errors/2026-08-29-phase-2-9-real-gate-marker-filter-bypass.md
```

### 当前验收命令

```powershell
cd backend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\phase-2.9\01_reliable_delivery_postgres_gate.ps1
```

该 Gate 顺序为：

```text
① 检查 uv 与 backend/.env.example（不启动服务）
        ↓
② alembic upgrade head / current
        ↓
③ 真实 PostgreSQL 并发、租约恢复、fencing、tenant isolation、retry/dead-letter
        ↓
④ 2.9-C 定向 Unit Regression
```

只有开发者本地实际看到 5 个 Real Gate 测试执行并通过，才能把 2.9-C 第二切片标记为验收完成。

## 6. 2.9-D Webhook Integration

下一阶段：在现有 Webhook Trigger 基础上统一 endpoint 身份、签名、版本、幂等、回放和 delivery audit，不复制 Trigger Service。

## 7. 2.9-E Runtime Integration

将 Workflow / Agent / Scheduler 关键业务事实接入统一 Event Contract，同时保持既有 Runtime 状态机和 Execution Fact 语义。

## 8. 开发边界

- 不把 Redis、Kafka、MQ 作为 Durable Event Fact；
- 不复制已有 Webhook / Trigger / Audit / Trace 实现；
- 不修改已通过 Phase 2.8 B6 Gate 的 Delegation Runtime 主路径；
- 不用 GitHub Actions 结果替代本地验收事实；
- 涉及数据库必须先 Migration，再 Backend/Repository，再测试和 Real API；
- Real Gate 不自动启动或停止 Worker、Scheduler、API、PostgreSQL、Redis 等服务；依赖服务必须由开发者按项目环境预先提供，Gate 只负责检查前置条件并执行测试；
- 测试数据由脚本自动生成，不要求开发者手工填写租户、Event ID、幂等键或其他测试信息。
