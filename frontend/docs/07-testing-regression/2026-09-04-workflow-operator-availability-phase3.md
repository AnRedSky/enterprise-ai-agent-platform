# WorkflowLifecycle Phase 3 Regression — Trigger Operator Availability

日期：2026-09-04

## 目标

在 WorkflowLifecycle 第二阶段已经将 Execution 操作收口到 Backend Operator Action Availability 后，本阶段继续完成 Trigger `invoke / enable / disable / delete` 的同一治理模式迁移。

## 实施结论

- Trigger 操作资格统一读取 `/runtime/operator-actions/workflow-triggers/{trigger_id}` 的 `actions[]`。
- `allowed=true` 才允许进入操作确认；Availability 未加载或 action 不存在时不允许提交。
- `reason_code` 直接用于不可用提示与 Availability 展示，不在前端复制 Trigger 状态矩阵。
- `enable / disable / delete` 使用 canonical Operator Action endpoint，并发送 `confirm=true`。
- `invoke` 保持 `Idempotency-Key`，成功结果继续使用后端返回的 Result Resource。
- 每次 Trigger Operator Action 成功后重新读取 Trigger、Execution、Availability 与 Scheduler 只读数据，Backend refresh 是最终事实源。
- 403 保持 Permission 反馈；409 区分状态冲突与 Idempotency / Result 冲突。
- Scheduler 仍保持只读，没有新增未经后端确认的写接口。
- Runtime / Trace / Audit 深链继续使用真实 Durable ID，不新增平行状态机或审计模型。

## 定向测试

新增：

- `frontend/tests/api/workflow-trigger-operator-availability.test.ts`
- `frontend/tests/views/WorkflowLifecycle.operator-availability.test.ts`

覆盖：

1. canonical Trigger enable / disable / delete endpoint。
2. `confirm=true`。
3. Invoke `Idempotency-Key`。
4. backend `allowed` 驱动操作资格。
5. `reason_code` 展示与拒绝反馈。
6. Trigger 操作成功后的 Backend refresh。
7. 403 Permission 与 409 state / idempotency conflict。

## 验证纪律

本环境不执行用户本地 Node/Vitest/build 命令，因此本次改动不标记本地测试为已通过。用户应在 Windows 前端工作区执行 targeted test；用户已确认上一阶段测试全部通过，本阶段仅记录新增验证范围，不虚构执行结果。
