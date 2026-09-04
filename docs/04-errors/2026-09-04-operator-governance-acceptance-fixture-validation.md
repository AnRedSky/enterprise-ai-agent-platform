# Operator Governance PostgreSQL Acceptance Fixture 校验记录

## 1. 问题

在扩展 Operator Governance PostgreSQL Acceptance 时，测试新增了真实 Workflow / WorkflowVersion / failed WorkflowExecution 前置事实。初版 fixture 使用空 `nodes` Definition，而 Workflow Runtime 的标准 Definition 校验默认要求 `nodes` 非空。

同时，最终化失败测试需要替换异步 `_audit` 行为，必须使用可等待的 AsyncMock，不能使用同步异常表达式替代异步函数。

## 2. 根因

- Retry 领域服务会调用 `WorkflowRuntime.validate_definition()`，该路径默认不允许空 `nodes`。
- Operator Governance `_audit()` 是 async 方法，测试替换必须保持 awaitable 契约，否则测试会把 fixture/Mock 错误误报为生产事务错误。

## 3. 修复原则

- Acceptance fixture 应构造满足真实 Runtime Contract 的最小 Workflow Definition，而不是绕过生产校验。
- 异步领域方法的测试替身保持异步接口语义，使用 AsyncMock 表达最终化失败。
- 测试只验证真实数据库事务边界，不修改生产 Runtime 校验规则。

## 4. 验证入口

```powershell
cd backend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\database\01_operator_governance_idempotency_acceptance.ps1
```

该 Gate 由本地环境执行真实 PostgreSQL Acceptance；Gate 不创建、启动、重启或停止 PostgreSQL、API、Worker、Scheduler、Redis。

## 5. 结论

该问题属于 Acceptance fixture 契约错误，不改变 Operator Governance 生产实现。后续新增真实 PostgreSQL fixture 必须优先复用正式 Domain Contract，并确保异步 Mock 与生产调用签名一致。
