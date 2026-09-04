# Operator Governance PostgreSQL Acceptance Fixture 校验记录

## 1. 问题

在扩展 Operator Governance PostgreSQL Acceptance 时，测试新增了真实 Workflow / WorkflowVersion / failed WorkflowExecution 前置事实。初版 fixture 使用空 `nodes` Definition，而 Workflow Runtime 的标准 Definition 校验默认要求 `nodes` 非空。

同时，最终化失败测试需要替换异步 `_audit` 行为，必须使用可等待的 AsyncMock，不能使用同步异常表达式替代异步函数。

本次真实 PostgreSQL 验收进一步发现：`Workflow` 与 `WorkflowVersion` 之间存在双向前置键依赖。fixture 先把 `Workflow.published_version_id` 指向尚未插入的 `WorkflowVersion`，会在 PostgreSQL flush 时触发 `fk_workflows_published_version_id` 外键错误。

## 2. 根因

- Retry 领域服务会调用 `WorkflowRuntime.validate_definition()`，该路径默认不允许空 `nodes`。
- Operator Governance `_audit()` 是 async 方法，测试替换必须保持 awaitable 契约，否则测试会把 fixture/Mock 错误误报为生产事务错误。
- `WorkflowVersion.workflow_id -> workflows.id` 与 `Workflow.published_version_id -> workflow_versions.id` 形成创建顺序约束；不能在 Workflow 尚未存在时插入 Version，也不能在 Version 尚未存在时把 published_version_id 写成其 ID。

## 3. 修复原则

- Acceptance fixture 应构造满足真实 Runtime Contract 的最小 Workflow Definition，而不是绕过生产校验。
- 异步领域方法的测试替身保持异步接口语义，使用 AsyncMock 表达最终化失败。
- 对双向外键 fixture 采用分阶段 flush：先创建 Workflow 且 `published_version_id=None`，再创建 WorkflowVersion，最后回填 `published_version_id`。
- 测试只验证真实数据库事务边界，不修改生产 Runtime 校验规则。

## 4. 验证入口

```powershell
cd backend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\database\01_operator_governance_idempotency_acceptance.ps1
```

该 Gate 由本地环境执行真实 PostgreSQL Acceptance；Gate 不创建、启动、重启或停止 PostgreSQL、API、Worker、Scheduler、Redis。

## 5. 当前结论

本次用户反馈确认 3 个幂等基础测试已经通过，新增 Retry replay / finalization rollback 两个测试仍因 Workflow fixture 的双向外键创建顺序失败。该错误属于 Acceptance fixture 数据构造错误，不改变 Operator Governance 生产实现。

修复后必须重新执行完整 Gate，只有实际本地结果通过后才能更新验收基线。

后续新增真实 PostgreSQL fixture 必须优先复用正式 Domain Contract，并显式处理外键依赖顺序，确保异步 Mock 与生产调用签名一致。
