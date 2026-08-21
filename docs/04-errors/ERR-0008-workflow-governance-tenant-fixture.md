# ERR-0008 — Workflow Governance 测试夹具缺少租户/Workflow 上下文

- Legacy ID: `004-workflow-execution-governance-test-fixture-tenant-context`
- Phase: 1.5-E

178 passed、2 failed；`SimpleNamespace` 缺少 `tenant_id`、`workflow_id`、`workflow_version_id` 等 Governance Trace 所需字段。根因是测试夹具仍停留在 Phase 1.5-C 简化 Domain Contract。修复为统一 `_execution()` 夹具补齐完整关联字段，禁止生产代码降级。要求重新 pytest、migration 和 validation。
