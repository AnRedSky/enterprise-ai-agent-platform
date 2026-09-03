# RuntimeCorrelations UI-03 / UI-04 回归断言错误

- 日期：2026-09-03
- 范围：Frontend / RuntimeCorrelations
- 类型：测试契约错误

## 现象

用户本地 targeted Vitest 共 7 个测试文件、36 个测试，其中 35 个通过，唯一失败为：

```text
RuntimeCorrelations UI consistency > keeps correlation navigation driven by durable backend facts
```

失败断言要求源码包含 `audit.workflow_execution_id`。

## 根因

生产代码已经基于后端 Audit Durable Fact 使用 `focusedAudit.workflow_execution_id`，并将该真实 `WorkflowExecution` ID 用于 Workflow Lifecycle 深链。实现没有名为 `audit` 的局部变量，因此测试通过源码字符串匹配了一个不存在的变量命名，而不是验证实际 Contract 使用。

该问题属于回归测试断言与当前生产实现命名不一致，不属于 RuntimeCorrelations 业务逻辑缺陷。

## 修复

将回归断言调整为：

```ts
expect(source).toContain("focusedAudit.workflow_execution_id");
```

同时继续保留 `execution.id`、`trace.trace_id`、`audit.id` 以及禁止通过列表首项推导关联关系的断言，确保测试仍验证 Durable Fact 导航原则。

生产代码、API Contract、深链逻辑和运行时行为均不修改。

## 验证边界

本次修复来自用户本地实际失败反馈。远端 GitHub 工具环境未执行 Node/Vitest/build，因此不得把 targeted Vitest、全量 `npm test`、`npm run build` 或 `npm run test:gate` 标记为已通过。

本地应按前端规范执行 targeted regression → 全量测试 → build → test gate；需要真实后端时再执行 Real API / Browser E2E。

## 防止重复

后续 RuntimeCorrelations 测试应优先验证 Durable Fact 字段和导航语义，而不是要求生产源码采用特定局部变量名称。新增断言前先对照 `RuntimeCorrelationAudit` API 类型和页面正式 mapper / state source，避免形成第二套 Contract 假设。
