# Operator Retry / Resume 并发验收清理 FK 错误

## 1. 现象

执行 `tests/integration/test_operator_execution_retry_resume_concurrency.py` 时，Retry 与 Resume 两个测试均在业务断言之后的 fixture 清理阶段失败。PostgreSQL 报告 `integration_events_tenant_id_fkey` 外键约束阻止删除测试 Tenant。

## 2. 根因

Operator Governance 成功执行会产生 `IntegrationEventRecord`，其 `tenant_id` 对 `Tenant` 使用受限外键。Retry / Resume 并发测试原清理顺序遗漏了 `IntegrationEventRecord`，因此即使业务测试事实已经正确落库，最终 `DELETE FROM tenants` 仍会触发 FK violation，并被 Gate 错误地呈现为测试失败。

这属于测试夹具数据生命周期不完整，不是 Retry / Resume 生产并发控制缺陷。

## 3. 修复

在并发验收清理流程中显式删除 `IntegrationEventRecord`，并保持依赖关系的逆拓扑清理顺序：Audit、Integration Event、Operator Idempotency、Trace、Checkpoint、Execution、Workflow Version、Workflow、User、Tenant。

同时补充 Retry / Resume 最终化失败的反向验收，验证 `_audit` 失败时新 Execution、OperatorActionIdempotency、AuditLog 不得形成部分提交。

## 4. 验证要求

本地 PostgreSQL 环境执行：

```powershell
$env:RUN_DATABASE_INTEGRATION="1"
uv run pytest -q -W error tests/integration/test_operator_execution_retry_resume_concurrency.py -s
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\database\01_operator_governance_idempotency_acceptance.ps1
```

若 PostgreSQL 未运行，测试按项目规则保持 `未执行/skip`，不得自动启动 PostgreSQL 或其他受保护服务。
