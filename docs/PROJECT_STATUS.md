# 项目状态

## 1. 当前基线
- Repository：`AnRedSky/enterprise-ai-agent-platform`
- Branch：`main`
- 当前阶段：**Phase 2.10-II Enterprise Operations Console / Operator Governance 开发中**
- 当前任务：**Operator Action 幂等并发、租户隔离与事务结果事实一致性收敛**。
- 最近完成：**Scheduler Runtime Real API 最终验收**、Scheduled Trigger 多实例/恢复验收、#84 Durable Resume Operator Action 幂等审计收敛、Operator Governance 最终化 rollback 保护、AsyncMock warning 根因修复。

开发严格基于远端 `main`，不创建功能分支。

## 2. 最新本地验证

开发者最新 Backend default regression：

```text
1064 passed, 80 deselected in 160.03s (0:02:40)
```

执行命令：

```powershell
uv run pytest -q -W error -s
```

本次启用 `PYTHONTRACEMALLOC=25`，未再出现 AsyncMock 未等待协程 warning。

Tenant Safe Real API 最新反馈：

```text
78 passed, 1 skipped, 2 deselected in 96.18s (0:01:36)
```

服务 Gate 检测到 3 个 Worker 与 3 个 Scheduler；Gate 没有创建、启动、重启或停止保护服务。

Operator Governance transaction targeted test：`6 passed`。
Delegation timeout targeted test：`5 passed`。

## 3. 当前 Backend 开发状态

- Phase 2.7 Advanced Workflow 主线、Durable Workflow / Resume / Frontier / Scheduler 基础设施已完成；
- Phase 2.8 Delegation Contract、Durable Entity、Claim、Worker Bridge、generation fencing、timeout/cancel、Audit/Trace、B6 multi-worker Runtime 已完成对应真实验收；
- Phase 2.9 Event Contract、Durable Event Persistence、Reliable Delivery、Webhook、Runtime Integration 已完成；
- Phase 2.10-A/B/C/D Event、Delivery、Replay、Audit 运维能力已实现；
- Phase 2.10-E Operations Console 第一切片、Metrics/SLO、Dead Letter、Runtime Operational Acceptance 已实现；
- Phase 2.10-I Runtime Notification Lifecycle、Worker tenant/consumer-group Claim isolation、Retry/Dead Letter/Fallback、SLO/Metrics、Canonical Metrics Export、OpenTelemetry SDK Telemetry、Operational Audit 已完成；
- Phase 2.10-II / II-01 Operator Action Governance、II-02 Global Runtime Operations、II-03 Worker/Scheduler Diagnostics、II-04 Audit/Trace Correlation、II-05 Controlled Batch Operations、II-06/II-07 Runtime Audit Query 已完成对应 Backend 能力；
- Operator Audit Query 已具备 tenant-scoped 分页、精确过滤、时间窗口校验和 admin-only 访问治理；
- `0051_operator_audit_query_indexes` 与 `0055_operator_audit_operator_action_index` 已补齐 Canonical Operator Audit 查询索引；
- Retry Operator Action → Idempotency Result Resource → AuditLog → Workflow Execution → Workflow Trace 已具备真实 PostgreSQL 验收；
- Durable Resume 的确定性 Resume Execution 幂等键已收敛到 Operator Action Governance，重放复用同一 Result Resource，不重复生成 Operator Audit；
- Scheduler 多实例 lease、slot 幂等、tenant isolation、misfire 与 lease expiry recovery 已完成真实 PostgreSQL 验收；
- Scheduled Trigger 多 Scheduler Real API Gate 已完成；
- Operator Governance `run / cancel / retry / resume / trigger` 已统一采用治理事务提交边界，最终化失败和最终 commit 失败显式 rollback；
- AsyncMock warning 根因已修复，Backend default regression 在 `-W error` 下通过。

## 4. 当前新增实现

新增 `backend/tests/integration/test_operator_action_idempotency.py`，使用真实 PostgreSQL 验证：

1. 同一 tenant、同一 Idempotency-Key 的两个独立数据库事务并发 claim 只有一个 winner；
2. loser 能读取已提交的 started 幂等事实，而不会创建第二条记录；
3. 相同 Idempotency-Key 在不同 tenant 可以独立 claim；
4. 所有测试 Tenant、User、OperatorActionIdempotency 数据均由测试自动生成并在 `finally` 中清理。

新增 `backend/scripts/test/database/01_operator_governance_idempotency_acceptance.ps1`，执行 Alembic head 验证和上述 PostgreSQL Acceptance；脚本只探测依赖，不自动启动、停止或重启 PostgreSQL、API、Worker、Scheduler、Redis。

## 5. 下一执行顺序

```text
① 执行新增 Operator Action Idempotency PostgreSQL Acceptance
② 补齐同 key / 不同 resource / 不同 action 的冲突语义验收
③ 收敛 failed Idempotency-Key 的重试语义与 API Contract
④ 验证 Result Resource / OperatorActionIdempotency / AuditLog / Trace 的 partial-commit 回滚
⑤ Operator Governance Real PostgreSQL Acceptance
⑥ Backend Regression + Alembic head verification
⑦ 评估 Phase 2.10-II Backend Release Gate
⑧ 继续处理剩余 Worker / Delegation 多实例真实 Provider 缺口
```

## 6. Backend 验收规则

当前后端任务只以以下证据作为开发验收依据：

```text
Backend Unit
  ↓
API Contract
  ↓
必要时 Real PostgreSQL / Real API Acceptance
  ↓
Backend Regression
```

Frontend 页面回归、Frontend Build、Browser E2E 不作为 Backend 主线开发阻塞条件。

所有 Gate 均禁止自动创建、启动、重启或停止 API、Scheduler、Worker、PostgreSQL、Redis；真实 Acceptance 必须自动生成和清理测试身份与业务数据。
