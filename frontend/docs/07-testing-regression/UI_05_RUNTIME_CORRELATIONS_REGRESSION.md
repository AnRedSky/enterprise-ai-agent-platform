# RuntimeCorrelations UI-03 / UI-04 回归记录

## 2026-09-03

### 问题
用户本地 targeted Vitest 中 `tests/views/RuntimeCorrelationsUI03UI04.test.ts` 仅有 1 项失败：

```text
keeps correlation navigation driven by durable backend facts
```

失败原因不是 RuntimeCorrelations 生产代码缺失 `workflow_execution_id`。页面实际通过 `focusedAudit.workflow_execution_id` 读取后端返回的 Audit Durable Fact，并在 Workflow Lifecycle 深链中使用该真实 Execution ID。

原回归断言要求源码出现 `audit.workflow_execution_id`，但当前实现没有名为 `audit` 的局部变量，因此产生了与实际实现语义无关的字符串匹配失败。

### 修复
将静态回归断言从：

```ts
expect(source).toContain("audit.workflow_execution_id");
```

调整为：

```ts
expect(source).toContain("focusedAudit.workflow_execution_id");
```

该修改只修正测试契约与当前生产实现之间的命名不一致，不改变 RuntimeCorrelations 运行时行为、API Contract 或导航逻辑。

同时保留对 `execution.id`、`trace.trace_id`、`audit.id` 以及禁止通过列表首项推导关系的断言，继续验证 Durable Fact 导航原则。

### 验证事实
用户反馈的基线为：7 个测试文件中 6 个通过、35/36 个测试通过，仅上述 1 项失败。

本次代码修复已提交；远端 GitHub 工具环境未执行 Node/Vitest/build，因此不得将 targeted Vitest、全量测试、build 或 test:gate 标记为已通过。应由本地依赖完整的 frontend 环境按项目标准执行验证。

### 后续
继续 UI-05 主线：优先完成 WorkflowLifecycle / RuntimeCorrelations / Trigger Management 的 targeted regression、build 和 test gate；不新增平行 API client、状态机或重复 Durable Fact 关系推导。
