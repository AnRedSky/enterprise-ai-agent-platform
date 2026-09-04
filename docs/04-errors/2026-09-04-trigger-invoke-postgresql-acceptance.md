# Trigger Invoke PostgreSQL Acceptance 边界补强

## 1. 背景

Operator Governance 的 Manual Trigger Invoke 已统一通过 `commit=False` 把 Execution Runtime、Result Resource、Idempotency、Audit 与 Trace 收敛到同一事务。仅有 Unit / API Contract 无法证明真实 PostgreSQL 下这些事实没有部分提交，因此需要独立 Acceptance。

## 2. 验证范围

- 成功 Invoke 写入 Workflow Execution 与 OperatorActionIdempotency；
- 同一 tenant + Idempotency-Key 重放复用同一 Result Resource；
- 重放不会生成第二个 Execution 或第二条 Operator Action Audit；
- 最终 Audit 失败时，Execution、OperatorActionIdempotency、Audit、Trace 与 Integration Event 全部回滚；
- Fixture 自动生成 Tenant/User/Workflow/WorkflowVersion/Trigger/Execution 上下文，不要求手工填写测试数据；
- Fixture 对 Workflow 与 WorkflowVersion 的双向外键依赖采用分阶段 flush，避免 `fk_workflows_published_version_id` 创建顺序错误。

## 3. Gate

```powershell
cd backend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\database\02_operator_trigger_invoke_acceptance.ps1
```

Gate 只检查/使用既有 PostgreSQL，不创建、启动、重启或停止 API、Worker、Scheduler、PostgreSQL、Redis。

## 4. 验收原则

Acceptance 的通过状态只能来自开发者本地实际执行结果。代码提交后应重新执行 Gate；在收到本地结果前不得把测试标记为通过。
