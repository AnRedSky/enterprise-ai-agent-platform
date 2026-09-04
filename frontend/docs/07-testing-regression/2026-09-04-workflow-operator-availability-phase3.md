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

## 2026-09-04 本地反馈回归修复

用户在最新 `frontend` 分支执行 `npm run build` 与 `npm run test:gate` 后发现两类阻塞：

### 1. TypeScript Contract 类型收窄

现象：

`OperatorActionName` 同时包含 Execution 与 Trigger action，而模板中的 `triggerActionText` 只覆盖 Trigger action。直接使用 `triggerActionText[item.action]` 会触发 TS7053。

根因：

Backend Availability 的 `actions[]` 类型是完整的 `OperatorActionName` 联合类型，不能把它直接当作 `TriggerAction` Record 的索引。

修复：

- 在 `WorkflowLifecycle.vue` 增加 `displayTriggerAction(action: OperatorActionName)` 展示边界函数。
- 模板统一通过该函数读取 Trigger action 文本。
- 不修改 Backend Contract、不扩张 Trigger action 枚举，也不复制第二套 action 映射。

提交：`fix: type workflow trigger action labels`

### 2. Trigger 管理测试与真实 Availability 门禁不一致

现象：

`WorkflowLifecycleTriggerManagement.test.ts` 中删除 Trigger 的测试收到 `ElMessage.warning is not a function`，随后无法进入确认态；此前测试 fixture 也没有提供 Trigger Operator Availability。

根因：

Phase 3 将 Trigger 删除操作改为后端 Availability 驱动。旧测试只 mock 旧的 Trigger CRUD 方法和 `ElMessage.success/error`，没有覆盖新增的 `triggerAvailability` API 及 warning 消息入口。

修复：

- 补齐 `workflowApi.triggerAvailability` mock，并返回允许 `invoke / enable / disable / delete` 的测试 Availability。
- 补齐 `workflowApi.executionAvailability` mock，使页面详情加载链完整且 deterministic。
- 补齐 `ElMessage.warning` mock。
- 保留原有删除确认、取消不提交、DELETE contract 以及 refresh 断言，不降低生产代码的 Availability 门禁。

提交：`fix: align trigger lifecycle test mocks`

## 验证纪律

本环境不执行用户本地 Node/Vitest/build 命令，因此本次改动不标记本地测试为已通过。用户应在 Windows 前端工作区执行 targeted test、全量 `npm test`、`npm run build` 与 `npm run test:gate`，并以实际终端结果作为验收事实。

建议验证顺序：

```powershell
npm test -- tests/api/workflows.test.ts tests/views/WorkflowLifecycle.test.ts tests/views/WorkflowLifecycleTriggerManagement.test.ts
npm test
npm run build
npm run test:gate
```

## 当前状态

- 代码修复：已提交。
- 测试 fixture 修复：已提交。
- 文档回归记录：已同步。
- 本地最终验证：等待用户执行上述命令确认，当前不能标记为通过。
