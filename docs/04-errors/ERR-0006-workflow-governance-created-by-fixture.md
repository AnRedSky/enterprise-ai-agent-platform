# ERR-0006 — Workflow Governance 测试夹具缺少 created_by

- Legacy ID: `003-workflow-execution-governance-test-fixture-created-by`
- Phase: 1.5-E

178 passed、2 failed；状态机测试 `SimpleNamespace` 缺少 `created_by`，Governance Trace 接入后真实 Domain Contract 已要求该字段。修复方式是补齐测试夹具 `created_by=uuid4()`，不在生产代码用 `getattr` 降级。修复后要求重新执行 pytest、migration 和 Phase 1.5-E validation。
