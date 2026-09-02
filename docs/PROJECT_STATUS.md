# 项目状态

## 1. 当前基线
- Repository：`AnRedSky/enterprise-ai-agent-platform`
- Branch：`main`
- 当前阶段：**Phase 2.10-II Enterprise Operations Console / Operator Governance 开发中**
- 当前任务：**Durable Resume Operator Action 幂等、Audit 与 Result Resource 治理闭环**。
- 最近完成：**II-09 Operator Action Result Lineage Acceptance**、Retry 事务边界收敛，以及 **#84 Durable Resume Operator Action 幂等审计收敛实现**。

开发严格基于远端 `main`，不创建功能分支。

## 2. 已完成能力
- Phase 2.7 Advanced Workflow 主线生产能力完成；
- Durable Workflow / Resume / Frontier / Scheduler 基础设施完成；
- Phase 2.8 Delegation Contract、Durable Entity、Claim、Worker Bridge、generation fencing、timeout/cancel、Audit/Trace、B6 multi-worker Runtime 已完成并通过本地 Real Gate；
- Phase 2.9-A Event Contract、2.9-B Durable Event Persistence、2.9-C Reliable Delivery、2.9-D Webhook Integration、2.9-E Runtime Integration 已完成对应真实验收；
- Phase 2.10-A/B/C/D Event、Delivery、Replay、Audit 运维能力已实现；
- Phase 2.10-E Operations Console 第一切片已实现；
- Phase 2.10-F Metrics / SLO 已增强到 Event Type + Destination + Provider 维度及确定性告警；
- Phase 2.10-G Dead Letter 已增强到批量 Replay；
- Phase 2.10-H Runtime Operational Acceptance Gate 已实现；
- Phase 2.10-I Runtime Notification Lifecycle、Worker tenant/consumer-group Claim isolation、Retry/Dead Letter/Fallback、SLO/Metrics、Canonical Metrics Export、OpenTelemetry SDK Telemetry、Operational Audit 已完成，并已通过本地实际 Real Gate；
- Phase 2.10-II / II-01 Operator Action Governance 已完成本地验证；
- Phase 2.10-II / II-02 Global Runtime Operations 已完成本地 Backend Unit / Real PostgreSQL 验证；
- Phase 2.10-II / II-03 Worker / Scheduler Diagnostics 第一切片已实现；
- Phase 2.10-II / II-04 Audit / Trace Correlation Backend 第一切片已实现；
- Phase 2.10-II / II-05 Controlled Batch Operations Backend 第一切片已实现，并已通过开发者本地 Unit / API Contract / Real PostgreSQL Acceptance 反馈；
- Phase 2.10-II / II-06 Runtime Audit Query Backend 第一切片与 `0050_runtime_audit_query_indexes` 查询性能强化已完成，并已通过开发者本地 Unit / API Contract / Real PostgreSQL Acceptance 反馈；
- Phase 2.10-II / II-07 Runtime Audit Query 主体、组合过滤及响应契约硬化已完成 Backend 实现；
- Runtime Audit / Trace Correlation 响应 Contract 已从 `list[Any]` 收紧为明确的 Trace / Audit Item 类型，并增加 Trace ID 输入边界；
- Runtime Audit / Trace Correlation 历史审计恢复路径已补齐：正式 `workflow_execution_id` 优先，缺失时通过 tenant-scoped `trace_id` 恢复当前 Workflow Execution，不猜测旧 `execution_id` 映射；
- Runtime Trace Resolution 已补齐重复 Trace Event 与跨 Execution 歧义保护：同一 Execution 的重复 Trace Event 使用唯一 Execution 映射，跨 Execution 的同 Trace ID 返回 409，不通过首行猜测；
- Operator Audit Query Service 已基于 AuditLog 唯一事实源实现 tenant-scoped 分页、精确过滤和时间窗口校验；
- Operator Audit Query API Contract 已实现，响应模型明确为 `OperatorAuditQueryResponse` / `OperatorAuditItem`；
- Operator Audit Query 已增加 admin-only 访问治理；
- `0051_operator_audit_query_indexes` 已将 Canonical Operator Audit 常用 tenant-scoped 查询索引正式落到 `audit_logs`；
- `0055_operator_audit_operator_action_index` 已为直接 Operator Action → AuditLog 查询补充 tenant-scoped 复合索引；
- Runtime Correlation 的 `AuditLogItem` 已暴露既有 `resource_type`、`resource_id`、`request_id`、`trace_id`，使 Execution / Trace / Audit / Operator Action 深链响应能够完整表达已有审计事实；
- **II-09 已新增 Retry Operator Action → Idempotency Result Resource → AuditLog → Workflow Execution → Workflow Trace 的真实 PostgreSQL 验收；**
- **#84 已将 Durable Resume 的底层确定性 Resume Execution 幂等键收敛到 Operator Action Governance，重放直接复用同一 Result Resource，不重复生成 Operator Audit。**

## 3. 最新本地反馈

开发者当前已反馈：

- Runtime Correlation Contract：`6 passed in 1.32s`；
- Retry Operator Action Result Lineage + Transaction Rollback Real PostgreSQL Acceptance：`2 passed in 1.87s`；
- Operator Action Result Lineage Gate：Runtime Contract、Retry Lineage、Rollback、服务边界均通过；
- Backend default regression：`1044 passed, 3 skipped, 79 deselected in 37.85s`。

上述结果对应 #75 完成后的基线。#84 新增 Resume 幂等实现后的最新 Resume Acceptance 尚未获得开发者本地实际输出，因此不得预填为通过。

## 4. 当前 Backend 修复 / 开发

- Retry / Resume 均支持由上层 Governance 控制事务提交边界；
- Retry Operator Action 在 Result Resource、Audit、Execution、Trace 全部完成后统一提交；
- Retry Audit 失败时不留下半提交 Retry Execution 或 Operator Action；
- **Resume Operator Action 在客户端未提供 Idempotency-Key 时，根据原始 Execution + Checkpoint sequence 生成稳定内部治理键；**
- **相同 Resume 请求重放时，在进入 Workflow Execution Resume 服务前复用已有 Operator Action Result Resource，避免重复 Audit；**
- 新增 `test_operator_action_resume_lineage_acceptance.py`，验证 Resume Result Resource、Operator Action、Audit、Execution、Trace 的幂等闭环；
- `25_operator_action_result_lineage_gate.ps1` 已纳入 Resume Real PostgreSQL Acceptance，并继续保持不自动启动任何受保护服务。

## 5. 下一执行顺序

```text
① 开发者同步远端 main 最新提交
② 执行 uv run alembic heads，确认仅有 0056_merge_legacy_audit_and_operator_governance_heads
③ 执行 uv run alembic upgrade head
④ 执行 Runtime Correlation Contract regression
⑤ 执行 #84 Durable Resume Operator Action Real PostgreSQL Acceptance / Result Lineage Gate
⑥ 扫描 Execution / Trace / Audit / Operator Action 端到端治理链剩余真实业务缺口
⑦ Backend-first 推进下一项 Operator Governance / Audit 能力
⑧ 前端测试与 Browser E2E 暂不作为当前 Backend 主线阻塞条件
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
